#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SW-017 R1 · 右缘 Void 带独立像素审计（F7 量化证据）。

只读：
  1. 当前 main 入包生产 webp：app/src/main/assets/visual/forest_*.webp
     统计每层右缘「全透明连续列数」(alpha 全列 == 0)。
  2. 作者真实截图：docs/collaboration/evidence/H-SW-010-R1/stages/stage-265m.png
     按 ForestShell 几何推算视差钳满时透明带对齐的屏 x 区间，采样该区间像素，
     判定是否等于 Void 纯色 #060806。
  3. 三档任务书比例下 cover 几何（scale/dst_w/overflow/静态右缘暗带宽）。

不修改任何文件；输出 JSON 到 previews/findings/edge-audit.json。
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
R1 = HERE.parent
REPO = R1.parent.parent.parent.parent  # r1 -> SW-017 -> 05-visual-design -> design -> repo
ASSETS = REPO / "app/src/main/assets"
EVID = REPO / "docs/collaboration/evidence"
OUT = R1 / "previews/findings/edge-audit.json"

SRC_W, SRC_H = 768, 1376
VOID = (6, 8, 6)
LAYERS = ["tree_outline", "tree_trunks", "leaf_path", "light_shows", "clearing"]
PARALLAX = {"tree_outline": 0.3, "tree_trunks": 0.3, "leaf_path": 0.6,
            "light_shows": 0.0, "clearing": 0.0}
PX_PER_M = 6.0
DEVICES = [(1080, 1920), (1080, 2400), (390, 844)]
STAGE_265 = 265


def _transparent_columns(a, w, h, side: str) -> int:
    n = 0
    xs = range(w - 1, -1, -1) if side == "right" else range(w)
    for x in xs:
        if any(a.getpixel((x, y)) != 0 for y in range(h)):
            break
        n += 1
    return n


def _soft_columns(a, w, h, side: str, thr: int) -> int:
    """该侧连续「整列最大 alpha < thr」的列数。"""
    n = 0
    xs = range(w - 1, -1, -1) if side == "right" else range(w)
    for x in xs:
        if max(a.getpixel((x, y)) for y in range(h)) >= thr:
            break
        n += 1
    return n


def edge_profile(img: Image.Image) -> dict:
    a = img.getchannel("A")
    w, h = img.size
    return {
        "left_transparent_columns": _transparent_columns(a, w, h, "left"),
        "right_transparent_columns": _transparent_columns(a, w, h, "right"),
        "right_soft_columns_alpha_lt_8": _soft_columns(a, w, h, "right", 8),
        "right_soft_columns_alpha_lt_32": _soft_columns(a, w, h, "right", 32),
        "right_soft_columns_alpha_lt_64": _soft_columns(a, w, h, "right", 64),
        "edge_max_alpha_4px": {
            "left": max(a.getpixel((x, y)) for x in range(4) for y in range(h)),
            "right": max(a.getpixel((x, y)) for x in range(w - 4, w) for y in range(h)),
        },
    }


def cover_geometry(w: int, h: int) -> dict:
    scale = h / SRC_H
    dst_w = SRC_W * scale
    return {"scale": round(scale, 6), "dst_w": round(dst_w, 2),
            "overflow": round(max(0.0, dst_w - w), 2),
            "uncovered_right": round(max(0.0, w - dst_w), 2)}


def parallax_offset(w: int, h: int, layer: str, meters: int) -> float:
    g = cover_geometry(w, h)
    return min(meters * PARALLAX[layer] * PX_PER_M, g["overflow"])


def scan_void_band(cap_path: Path) -> dict:
    """stage-265m 作者截图全带扫描：钳满层(tree_outline)透明列对齐屏右缘。

    扫描估计带及其左右各 20px、每 4 行采样一次，逐列统计与 Void(6,8,6)
    最大通道偏差 ≤2 的像素占比；另从屏右缘向左找首个「非 Void 列」确定实测带宽。
    """
    img = Image.open(cap_path).convert("RGB")
    cw, ch = img.size
    scale = ch / SRC_H
    geo = cover_geometry(cw, ch)
    trans_px = 30 * scale  # tree_outline 实测 30 列
    off = parallax_offset(cw, ch, "tree_outline", STAGE_265)
    est_x0 = int(round(cw - trans_px))

    # 只扫画面中段：避开右上放弃/暂停控件（y<~460）、底部实走文案与手势条，
    # 也避开旅人竖线（x=.34 与右缘无关）。
    rows = range(int(ch * 0.25), int(ch * 0.62), 4)

    def col_dev(x: int) -> int:
        return max(max(abs(img.getpixel((x, y))[c] - VOID[c]) for c in range(3)) for y in rows)

    def void_frac(x0: int, x1: int) -> float:
        total, hit = 0, 0
        for x in range(x0, x1 + 1):
            for y in rows:
                total += 1
                p = img.getpixel((x, y))
                if max(abs(p[c] - VOID[c]) for c in range(3)) <= 2:
                    hit += 1
        return round(hit / total, 4)

    # 从右缘向左：首个最大偏差 >2 的列
    measured_x0 = cw
    for x in range(cw - 1, -1, -1):
        if col_dev(x) > 2:
            measured_x0 = x + 1
            break

    probe = {}
    for x in list(range(est_x0 - 20, est_x0)) + list(range(est_x0, cw, 7)):
        if 0 <= x < cw:
            probe[str(x)] = col_dev(x)

    return {
        "capture": str(cap_path.relative_to(REPO)),
        "capture_size": [cw, ch],
        "scale": round(scale, 4),
        "overflow": geo["overflow"],
        "offset_clamped": round(off, 2),
        "clamped": abs(off - geo["overflow"]) < 0.01,
        "estimated_band_x0": est_x0,
        "estimated_band_px": round(trans_px, 1),
        "measured_void_band_x0": measured_x0,
        "measured_void_band_px": cw - measured_x0,
        "void_fraction_in_estimated_band": void_frac(est_x0, cw - 1),
        "void_fraction_left_of_band_20px": void_frac(est_x0 - 20, est_x0 - 1),
        "column_max_deviation_probe": probe,
    }


def band_scan(cap_path: Path) -> dict:
    """任意作者截图：中段 ROI 内右/左纯 Void 边缘带宽度与占比。"""
    img = Image.open(cap_path).convert("RGB")
    cw, ch = img.size
    rows = range(int(ch * 0.25), int(ch * 0.62), 4)

    def is_void(x: int, y: int) -> bool:
        p = img.getpixel((x, y))
        return max(abs(p[c] - VOID[c]) for c in range(3)) <= 2

    def col_dev(x: int) -> int:
        return max(max(abs(img.getpixel((x, y))[c] - VOID[c]) for c in range(3)) for y in rows)

    rx0 = cw
    for x in range(cw - 1, -1, -1):
        if col_dev(x) > 2:
            rx0 = x + 1
            break
    lx1 = 0
    for x in range(0, cw):
        if col_dev(x) > 2:
            lx1 = x
            break
    right_px = cw - rx0
    left_px = lx1
    rfrac = (sum(1 for x in range(rx0, cw) for y in rows if is_void(x, y))
             / max(1, right_px * len(rows))) if right_px else 0.0
    lfrac = (sum(1 for x in range(0, lx1) for y in rows if is_void(x, y))
             / max(1, left_px * len(rows))) if left_px else 0.0
    return {"capture_size": [cw, ch],
            "right_void_band_px": right_px, "right_void_fraction": round(rfrac, 4),
            "left_void_band_px": left_px, "left_void_fraction": round(lfrac, 4)}


def main() -> None:
    layers_report = {}
    for lid in LAYERS:
        p = ASSETS / "visual" / f"forest_{lid}.webp"
        img = Image.open(p).convert("RGBA")
        layers_report[lid] = {
            "file": str(p.relative_to(REPO)),
            "size": list(img.size),
            "parallax": PARALLAX[lid],
            **edge_profile(img),
        }

    devices = {f"{w}x{h}": cover_geometry(w, h) for w, h in DEVICES}
    band_rows = []
    for w, h in DEVICES:
        g = cover_geometry(w, h)
        for lid in ("tree_outline", "tree_trunks", "leaf_path"):
            tc = layers_report[lid]["right_transparent_columns"]
            trans_px = round(tc * g["scale"], 1)
            band_rows.append({
                "device": f"{w}x{h}", "layer": lid,
                "static_band_px": round(trans_px + g["uncovered_right"], 1),
                "clamped_band_px": trans_px,
                "clamp_after_meters_est": round(
                    g["overflow"] / (PARALLAX[lid] * PX_PER_M), 1) if PARALLAX[lid] else None,
            })

    cap = EVID / "H-SW-010-R1/stages/stage-265m.png"
    capture_report = scan_void_band(cap) if cap.exists() else {"missing": str(cap)}

    # 六阶段作者截图边缘带演变（同 ROI）：看 light_shows/clearing 如何遮盖右缘
    stage_scan = {}
    stages_dir = EVID / "H-SW-010-R1/stages"
    for m in (0, 100, 265, 425, 630, 785):
        p = stages_dir / f"stage-{m:03d}m.png"
        if p.exists():
            stage_scan[f"{m}m"] = {
                "file": str(p.relative_to(REPO)),
                **band_scan(p),
            }

    report = {
        "schema_version": 1,
        "task_id": "SW-017",
        "purpose": "F7 右缘 Void 黑带独立像素审计（只读生产素材与作者截图，不改任何文件）",
        "void_rgb": list(VOID),
        "void_match_tolerance_per_channel": 2,
        "scan_roi": "y in [0.25h, 0.62h)（避开右上控件与底部文案），每 4 行采样",
        "source_size": [SRC_W, SRC_H],
        "layers": layers_report,
        "cover_geometry": devices,
        "band_estimates": band_rows,
        "author_capture_265m": capture_report,
        "author_stage_band_scan": stage_scan,
        "all_pass": None,
    }
    cr = capture_report
    s = stage_scan
    all_pass = bool(
        all(layers_report[l]["right_transparent_columns"] == 30
            for l in ("tree_outline", "tree_trunks", "leaf_path"))
        and cr.get("clamped") is True
        and cr.get("void_fraction_in_estimated_band", 0) >= 0.99
        and abs(cr.get("measured_void_band_px", 0) - cr.get("estimated_band_px", 0)) <= 4
        and all(abs(s[f"{m}m"]["right_void_band_px"] - 52) <= 4 for m in (265, 425))
        and 0 < s["630m"]["right_void_band_px"] < 52
        and s["785m"]["right_void_band_px"] == 0
    )
    report["all_pass"] = all_pass
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "all_pass": all_pass,
        "transparent_cols_right": {l: layers_report[l]["right_transparent_columns"] for l in LAYERS},
        "transparent_cols_left": {l: layers_report[l]["left_transparent_columns"] for l in LAYERS},
        "measured_band_px": cr.get("measured_void_band_px"),
        "estimated_band_px": cr.get("estimated_band_px"),
        "void_fraction": cr.get("void_fraction_in_estimated_band"),
        "stage_right_bands": {m: stage_scan[m]["right_void_band_px"] for m in stage_scan},
        "out": str(OUT),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
