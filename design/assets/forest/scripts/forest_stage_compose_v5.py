#!/usr/bin/env python3
"""
v5 阶段合成预览: 使用 v5 候选 webp 重做 0/100/265/425/630/785m 六阶段.
参照 forest.json §visualLayers 的 phase 配置 + SensoryState.visualOpacities 纯函数.
输出 1080x1920 全分辨率 + 0.5x JPEG + 文件 SHA256 用于追溯.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
CAND = ROOT / "design" / "assets" / "forest" / "candidates" / "v5" / "webp"
OUT = ROOT / "design" / "assets" / "forest" / "candidates" / "v5" / "stage_compose"
OUT.mkdir(parents=True, exist_ok=True)
RECORDS = ROOT / "design" / "assets" / "forest" / "candidates" / "v5" / "records"
RECORDS.mkdir(parents=True, exist_ok=True)

# 真实 phase 配置 (来自 forest.json §phases)
PHASES = {
    "void":         {"atMeters": 0,   "toOpacity": 1.00, "fadeMeters": 1},
    "tree_outline": {"atMeters": 80,  "toOpacity": 0.60, "fadeMeters": 20},
    "tree_trunks":  {"atMeters": 240, "toOpacity": 0.70, "fadeMeters": 25},
    "leaf_path":    {"atMeters": 400, "toOpacity": 0.80, "fadeMeters": 25},
    "light_shows":  {"atMeters": 600, "toOpacity": 0.50, "fadeMeters": 30},
    "clearing":     {"atMeters": 760, "toOpacity": 0.90, "fadeMeters": 25},
}
LAYERS_BY_METER = {
    0:   [],
    100: ["tree_outline"],
    265: ["tree_outline", "tree_trunks"],
    425: ["tree_outline", "tree_trunks", "leaf_path"],
    630: ["tree_outline", "tree_trunks", "leaf_path", "light_shows"],
    785: ["tree_outline", "tree_trunks", "leaf_path", "light_shows", "clearing"],
}
VOID_RGB = np.array([6, 8, 6], dtype=np.float32)
CANVAS = (1080, 1920)  # 期望最终尺寸


def phase_opacity(layer_id: str, meters: float) -> float:
    p = PHASES[layer_id]
    if meters < p["atMeters"]:
        return 0.0
    span = meters - p["atMeters"]
    if span >= p["fadeMeters"]:
        return p["toOpacity"]
    return p["toOpacity"] * span / p["fadeMeters"]


def load_layer(layer_id: str) -> np.ndarray:
    src = CAND / f"forest_{layer_id}.webp"
    img = Image.open(src).convert("RGBA")
    h, w = np.array(img).shape[:2]
    cw, ch = CANVAS
    scale = ch / h
    dst_w = int(round(w * scale))
    img2 = img.resize((dst_w, ch), Image.LANCZOS)
    out = np.array(img2)
    if out.shape[1] > cw:
        x_off = (out.shape[1] - cw) // 2
        out = out[:, x_off:x_off + cw]
    elif out.shape[1] < cw:
        pad = np.zeros((ch, cw - out.shape[1], 4), dtype=np.uint8)
        pad[..., 0:3] = 6
        out = np.concatenate([out, pad], axis=1)
    return out


def compose(meters: float, layer_ids: list[str]) -> np.ndarray:
    h, w = CANVAS[1], CANVAS[0]
    cur = np.zeros((h, w, 4), dtype=np.float32)
    cur[..., 0:3] = VOID_RGB / 255.0
    cur[..., 3] = 1.0
    for ln in layer_ids:
        rgba = load_layer(ln)
        a_l = phase_opacity(ln, meters)
        if a_l <= 0:
            continue
        a = rgba[..., 3:4].astype(np.float32) / 255.0 * a_l
        rgb = rgba[..., :3].astype(np.float32) / 255.0
        out_a = a + cur[..., 3:4] * (1 - a)
        safe = np.where(out_a > 1e-6, 1.0 / np.maximum(out_a, 1e-6), 0)
        out_rgb = (rgb * a + cur[..., :3] * cur[..., 3:4] * (1 - a)) * safe
        cur = np.dstack([out_rgb, out_a])
    return cur


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def diagnose_center(img: np.ndarray) -> dict:
    """诊断中央区域是否有棋盘格."""
    gray = img.mean(axis=2)
    # 中央 y=600-1300, x=300-780 (1080x1920 中央 600x500 区)
    center = gray[600:1300, 300:780]
    lap = np.abs(np.diff(np.diff(center, axis=0), axis=1))
    # 棋盘格候选: 高频像素
    high_freq_pct = 100 * float((lap > 30).mean())
    # 浅色像素
    rgb_flat = img.reshape(-1, 3)
    bright_uniform = (rgb_flat.min(axis=1) > 180) & (rgb_flat.max(axis=1) - rgb_flat.min(axis=1) < 15)
    bright_pct = 100 * float(bright_uniform.mean())
    # alternating rate
    diff_h = np.abs(gray[:, 1:] - gray[:, :-1])
    diff_h_pos = diff_h > 20
    consecutive = diff_h_pos[:, 1:] & diff_h_pos[:, :-1]
    alt_rate = 100 * float(consecutive.mean())
    return {
        "center_brightness_mean": round(float(center.mean()), 1),
        "center_brightness_std": round(float(center.std()), 1),
        "lap_max": int(lap.max()),
        "lap_p95": round(float(np.percentile(lap, 95)), 1),
        "high_freq_pct": round(high_freq_pct, 2),
        "bright_pixel_pct": round(bright_pct, 3),
        "alt_rate": round(alt_rate, 1),
    }


def main() -> None:
    rows = []
    for m in [0, 100, 265, 425, 630, 785]:
        ids = LAYERS_BY_METER[m]
        comp = compose(m, ids)
        out8 = (np.clip(comp, 0, 1) * 255).astype(np.uint8)
        full = Image.fromarray(out8, "RGBA")
        bg = Image.new("RGB", full.size, tuple(int(c) for c in VOID_RGB))
        bg.paste(full, mask=full.split()[3])
        full_png = OUT / f"stage_{m:03d}m_full.png"
        bg.save(full_png, "PNG", optimize=True)
        small = bg.resize((540, 960), Image.LANCZOS)
        small_jpg = OUT / f"stage_{m:03d}m_540x960.jpg"
        small.save(small_jpg, "JPEG", quality=90, optimize=True)

        # 中央诊断
        bg_arr = np.array(bg)
        diag = diagnose_center(bg_arr)

        rows.append({
            "meters": m,
            "layers": ids,
            "opacities": {ln: round(phase_opacity(ln, m), 3) for ln in ids},
            "full": str(full_png.relative_to(ROOT)),
            "full_sha256": file_sha256(full_png),
            "small": str(small_jpg.relative_to(ROOT)),
            "small_sha256": file_sha256(small_jpg),
            "diagnose_center": diag,
        })
        print(f"[v5 compose] {m}m: layers={ids}, brightness={diag['center_brightness_mean']}±{diag['center_brightness_std']}, "
              f"lap_max={diag['lap_max']}, alt_rate={diag['alt_rate']}%")

    out = RECORDS / "stage_compose_v5.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"\n[v5] 合成记录: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()