#!/usr/bin/env python3
"""
v4 阶段合成预览: 使用 v4 候选 webp 重做 0/100/265/425/630/785m 六阶段.
参考 forest.json 的 phase 配置 + SensoryState.visualOpacities 纯函数.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
CAND = ROOT / "design" / "assets" / "forest" / "candidates" / "v4" / "webp"
OUT = ROOT / "design" / "assets" / "forest" / "candidates" / "v4" / "stage_compose"
OUT.mkdir(parents=True, exist_ok=True)

# 复制 forest.json §visualLayers 的 phase 配置
# atMeters: 开始淡入距离; toOpacity: 目标 opacity; fadeMeters: 淡入跨度
PHASES = {
    "void":        {"atMeters": 0,    "toOpacity": 1.00, "fadeMeters": 1},
    "tree_outline":{"atMeters": 80,   "toOpacity": 0.60, "fadeMeters": 20},
    "tree_trunks": {"atMeters": 240,  "toOpacity": 0.70, "fadeMeters": 25},
    "leaf_path":   {"atMeters": 400,  "toOpacity": 0.80, "fadeMeters": 25},
    "light_shows": {"atMeters": 600,  "toOpacity": 0.50, "fadeMeters": 30},
    "clearing":    {"atMeters": 760,  "toOpacity": 0.90, "fadeMeters": 25},
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

# 最终画布 (按 DEVELOPMENT.md §14.1 期望 1080x1920, v4 raw 768x1376 -> cover 到 1080x1920)
CANVAS = (1080, 1920)


def phase_opacity(layer_id: str, meters: float) -> float:
    p = PHASES[layer_id]
    if meters < p["atMeters"]:
        return 0.0
    span = meters - p["atMeters"]
    if span >= p["fadeMeters"]:
        return p["toOpacity"]
    return p["toOpacity"] * span / p["fadeMeters"]


def load_layer(layer_id: str) -> np.ndarray:
    """读 v4 webp (RGBA uint8), cover 到 1080x1920."""
    src = CAND / f"forest_{layer_id}.webp"
    img = Image.open(src).convert("RGBA")
    h, w = np.array(img).shape[:2]
    cw, ch = CANVAS
    scale = ch / h
    dst_w = int(round(w * scale))
    img2 = img.resize((dst_w, ch), Image.LANCZOS)
    out = np.array(img2)
    # 居中或左对齐截取到 cw
    if out.shape[1] > cw:
        x_off = (out.shape[1] - cw) // 2
        out = out[:, x_off:x_off + cw]
    elif out.shape[1] < cw:
        # pad with void
        pad = np.zeros((ch, cw - out.shape[1], 4), dtype=np.uint8)
        pad[..., 0:3] = 6
        out = np.concatenate([out, pad], axis=1)
    assert out.shape == (ch, cw, 4), f"bad shape: {out.shape}"
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


def main() -> None:
    rows = []
    for m in [0, 100, 265, 425, 630, 785]:
        ids = LAYERS_BY_METER[m]
        comp = compose(m, ids)
        out8 = (np.clip(comp, 0, 1) * 255).astype(np.uint8)
        full = Image.fromarray(out8, "RGBA")
        # 投到 #060806 底色
        bg = Image.new("RGB", full.size, tuple(int(c) for c in VOID_RGB))
        bg.paste(full, mask=full.split()[3])
        # 全分辨率 PNG
        full_png = OUT / f"stage_{m:03d}m_full.png"
        bg.save(full_png, "PNG", optimize=True)
        # 0.5x JPEG 便于文档
        small = bg.resize((540, 960), Image.LANCZOS)
        small_jpg = OUT / f"stage_{m:03d}m_540x960.jpg"
        small.save(small_jpg, "JPEG", quality=85, optimize=True)
        rows.append({
            "meters": m,
            "layers": ids,
            "opacities": {ln: round(phase_opacity(ln, m), 3) for ln in ids},
            "full": str(full_png.relative_to(ROOT)),
            "small": str(small_jpg.relative_to(ROOT)),
        })
        print(f"[v4 compose] {m}m: layers={ids}, opacities={ {ln: round(phase_opacity(ln,m),2) for ln in ids} }")
    (ROOT / "design" / "assets" / "forest" / "records" / "stage_compose_v4.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()