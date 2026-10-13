#!/usr/bin/env python3
"""
森林景色分层合成预览（开发文档用，不进 APK）。

按真实 forest.json 的目标 opacity + fadeMeters，输出 6 阶段的合成图：
  0m    黑幕（仅 void）
  100m  仅 tree_outline（fadeMeters=20, at 80m, 0.6 目标）
  265m  + tree_trunks（at 240m, 0.7 目标）
  425m  + leaf_path（at 400m, 0.8 目标）
  630m  + light_shows（at 600m, 0.65 目标）
  785m  + clearing（at 760m, 0.9 目标）

合成在 1080×1920 画布上，最终以 0.5× 缩到 540×960 存为预览图。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]  # design/assets/forest/scripts → sense-walk
ASSETS_VISUAL = ROOT / "app" / "src" / "main" / "assets" / "visual"
PREVIEW_DIR = ROOT / "design" / "assets" / "forest" / "previews"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

# 来自 forest.json 的视觉相位
LAYER_PHASES = {
    "void": {"atMeters": 0, "toOpacity": 1.0, "fadeMeters": 0},
    "tree_outline": {"atMeters": 80, "toOpacity": 0.60, "fadeMeters": 20},
    "tree_trunks": {"atMeters": 240, "toOpacity": 0.70, "fadeMeters": 25},
    "leaf_path": {"atMeters": 400, "toOpacity": 0.80, "fadeMeters": 25},
    "light_shows": {"atMeters": 600, "toOpacity": 0.65, "fadeMeters": 30},
    "clearing": {"atMeters": 760, "toOpacity": 0.90, "fadeMeters": 25},
}
LAYER_FILE = {
    "tree_outline": "forest_tree_outline.webp",
    "tree_trunks": "forest_tree_trunks.webp",
    "leaf_path": "forest_leaf_path.webp",
    "light_shows": "forest_light_shows.webp",
    "clearing": "forest_clearing.webp",
}

STAGES = [
    ("00_void_0m", 0, []),
    ("01_outline_100m", 100, ["tree_outline"]),
    ("02_trunks_265m", 265, ["tree_outline", "tree_trunks"]),
    ("03_leafpath_425m", 425, ["tree_outline", "tree_trunks", "leaf_path"]),
    ("04_lightshows_630m", 630, ["tree_outline", "tree_trunks", "leaf_path", "light_shows"]),
    ("05_clearing_785m", 785, ["tree_outline", "tree_trunks", "leaf_path", "light_shows", "clearing"]),
]

VOID_RGB = np.array([0x06, 0x08, 0x06], dtype=np.float32)
CANVAS = (1080, 1920)


def phase_opacity(layer: str, meters: float) -> float:
    p = LAYER_PHASES[layer]
    if meters <= p["atMeters"]:
        return 0.0
    if p["fadeMeters"] <= 0:
        return p["toOpacity"]
    t = (meters - p["atMeters"]) / p["fadeMeters"]
    return min(p["toOpacity"], max(0.0, t) * p["toOpacity"])


def load_layer(name: str) -> np.ndarray:
    p = ASSETS_VISUAL / LAYER_FILE[name]
    img = Image.open(p).convert("RGBA")
    return np.asarray(img, dtype=np.float32) / 255.0  # H×W×4


def compose(stage_meters: float, layers: list[str]) -> np.ndarray:
    h, w = CANVAS[1], CANVAS[0]
    bg = np.zeros((h, w, 4), dtype=np.float32)
    bg[..., 0:3] = VOID_RGB / 255.0
    bg[..., 3] = 1.0

    cur = bg
    for ln in layers:
        rgba = load_layer(ln)
        a_l = phase_opacity(ln, stage_meters)
        if a_l <= 0:
            continue
        # 把该层缩放到画布：先把 RGB 预乘 alpha（pre-multiplied），
        # LANCZOS 缩放后再除以 alpha——避免透明像素的 RGB 在 LANCZOS 中"渗透"到邻近像素
        if rgba.shape[:2] != (h, w):
            arr8 = (rgba * 255).astype(np.uint8)
            a8 = arr8[..., 3].astype(np.float32) / 255.0
            rgb8 = arr8[..., 0:3].astype(np.float32) / 255.0
            # 预乘
            premul = (rgb8 * a8[..., None]).clip(0, 1)
            premul_img = Image.fromarray((premul * 255).astype(np.uint8), "RGB").resize((w, h), Image.LANCZOS)
            a_img = Image.fromarray((a8 * 255).astype(np.uint8), "L").resize((w, h), Image.LANCZOS)
            premul = np.asarray(premul_img, dtype=np.float32) / 255.0
            a_new = np.asarray(a_img, dtype=np.float32) / 255.0
            # alpha 阈值化：LANCZOS 会在 alpha=0 边界外推微小值；这里强制 < 32 → 0
            a_new = np.where(a_new < 32/255, 0.0, a_new)
            # 反预乘：alpha=0 处 RGB=0
            safe = np.where(a_new[..., None] > 1e-3, 1.0 / np.maximum(a_new[..., None], 1e-3), 0)
            rgb_new = (premul * safe).clip(0, 1)
            rgba = np.dstack([rgb_new, a_new])
        # 源 alpha × phase alpha
        a = rgba[..., 3] * a_l
        # 标准 over 合成
        out_a = a + cur[..., 3] * (1 - a)
        safe = np.where(out_a[..., None] > 1e-6, 1.0 / np.maximum(out_a[..., None], 1e-6), 0)
        out_rgb = (rgba[..., 0:3] * a[..., None] + cur[..., 0:3] * cur[..., 3][..., None] * (1 - a[..., None])) * safe
        cur = np.dstack([out_rgb, out_a])
    return cur


def main() -> int:
    rows = []
    for tag, m, layers in STAGES:
        comp = compose(m, layers)
        out8 = (np.clip(comp, 0, 1) * 255).astype(np.uint8)
        full = Image.fromarray(out8, "RGBA")
        # 始终先与 #060806 合成，再以 RGB 存图，避免透明区域显示为透明/棋盘
        void_bg = Image.new("RGB", full.size, tuple(int(c) for c in VOID_RGB))
        void_bg.paste(full, mask=full.split()[3])
        void_bg.save(PREVIEW_DIR / f"stage_{tag}_full.png", "PNG", optimize=True)
        # 0.5× 缩图，便于文档
        small = void_bg.resize((540, 960), Image.LANCZOS)
        small.save(PREVIEW_DIR / f"stage_{tag}_540x960.jpg", "JPEG", quality=85)
        rows.append(
            {
                "tag": tag,
                "meters": m,
                "layers": layers,
                "opacities": {ln: phase_opacity(ln, m) for ln in layers},
                "full": f"design/assets/forest/previews/stage_{tag}_full.png",
                "small": f"design/assets/forest/previews/stage_{tag}_540x960.jpg",
            }
        )
        print(f"[ok ] {tag} 0.5x → {small.size}")
    out = ROOT / "design" / "assets" / "forest" / "records" / "stage_compose.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[info] {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
