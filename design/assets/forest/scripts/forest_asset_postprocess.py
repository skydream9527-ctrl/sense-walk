#!/usr/bin/env python3
"""
森林素材后处理（向量化版）：

1. 把每张 raw JPG 转成 PNG（带 alpha）；
2. 对每张图把 #060806（黑幕色）做柔和抠图，低于阈值 → alpha=0；
3. 上下两端的"全画布留白"区域按提示词应该已经透明，做一次收紧
   —— 任何贴近 #060806 的像素透明度都到 0；
4. 转成 WebP（无损/质量 90），交付到 app/src/main/assets/visual/ 与
   design/assets/forest/artwork/；
5. 生成各层的纯 alpha 黑白预览（用于透明检查）；
6. 输出素材联系表 Markdown 片段。

注意：模型只输出 JPG，alpha 是后处理模拟。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]  # design/assets/forest/scripts → sense-walk
RAW_DIR = ROOT / "design" / "assets" / "forest" / "raw"
ART_DIR = ROOT / "design" / "assets" / "forest" / "artwork"
PREVIEW_DIR = ROOT / "design" / "assets" / "forest" / "previews"
ASSETS_VISUAL = ROOT / "app" / "src" / "main" / "assets" / "visual"

ART_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_VISUAL.mkdir(parents=True, exist_ok=True)

VOID_RGB = np.array([0x06, 0x08, 0x06], dtype=np.float32)  # #060806 黑幕

LAYER_FILES = {
    "style_ref": ("style_ref", "reference"),
    "forest_tree_outline": ("forest_tree_outline", "parallax-bg"),
    "forest_tree_trunks": ("forest_tree_trunks", "parallax-bg"),
    "forest_leaf_path": ("forest_leaf_path", "parallax-fg"),
    "forest_light_shows": ("forest_light_shows", "overlay"),
    "forest_clearing": ("forest_clearing", "overlay"),
    "traveler_idle": ("traveler_idle", "character"),
}


def compute_alpha(rgb: np.ndarray, role: str) -> np.ndarray:
    """rgb: H×W×3 uint8。返回 H×W uint8 alpha。"""
    diff = rgb.astype(np.float32) - VOID_RGB[None, None, :]
    dist = np.sqrt((diff * diff).sum(axis=2))

    dist_thr_lo = 22.0
    dist_thr_hi = 60.0
    alpha = np.clip((dist - dist_thr_lo) / (dist_thr_hi - dist_thr_lo), 0.0, 1.0)
    alpha = (alpha * 255).astype(np.uint8)

    # 角色周围更大边带
    h, w = alpha.shape
    if role == "character":
        edge_t, edge_b, edge_l, edge_r = 0.06, 0.04, 0.05, 0.05
    else:
        edge_t, edge_b, edge_l, edge_r = 0.04, 0.04, 0.04, 0.04
    t = int(h * edge_t)
    b = int(h * edge_b)
    l = int(w * edge_l)
    r = int(w * edge_r)
    alpha[:t, :] = 0
    alpha[h - b:, :] = 0
    alpha[:, :l] = 0
    alpha[:, w - r:] = 0
    return alpha


def save_artwork(rgba: Image.Image, base: str):
    art_png = ART_DIR / f"{base}.png"
    rgba.save(art_png, format="PNG", optimize=True)
    webp = ASSETS_VISUAL / f"{base}.webp"
    rgba.save(webp, format="WEBP", quality=90, method=6)
    return art_png, webp


def make_alpha_preview(rgba: Image.Image, base: str) -> Path:
    bg = Image.new("RGB", rgba.size, tuple(int(c) for c in VOID_RGB))
    bg.paste(rgba, mask=rgba.split()[3])
    out = PREVIEW_DIR / f"{base}_alpha_on_void.jpg"
    bg.convert("RGB").save(out, format="JPEG", quality=82)
    return out


def make_alpha_mask(rgba: Image.Image, base: str) -> Path:
    a = rgba.split()[3]
    out = PREVIEW_DIR / f"{base}_alpha_mask.png"
    a.save(out, format="PNG")
    return out


def make_tile_preview(rgba: Image.Image, base: str, repeat: int = 2) -> Path:
    w, h = rgba.size
    canvas = Image.new("RGBA", (w * repeat, h), (6, 8, 6, 255))
    a = rgba.split()[3]
    for i in range(repeat):
        canvas.paste(rgba, (i * w, 0), mask=a)
    out = PREVIEW_DIR / f"{base}_tile_x{repeat}.jpg"
    canvas.convert("RGB").save(out, format="JPEG", quality=82)
    return out


def main() -> int:
    jobs_path = ROOT / "design" / "assets" / "forest" / "records" / "jobs.json"
    if not jobs_path.exists():
        print("[error] jobs.json missing", file=sys.stderr)
        return 1
    state = json.loads(jobs_path.read_text(encoding="utf-8"))

    summary = []
    for job_id, (base, role) in LAYER_FILES.items():
        rec = state["jobs"].get(job_id)
        if not rec:
            print(f"[skip] {job_id} 没有 record")
            continue
        raw_path = ROOT / rec["raw_path"]
        if not raw_path.exists():
            print(f"[skip] {job_id} raw 缺失: {raw_path}")
            continue
        img = Image.open(raw_path).convert("RGB")
        rgb = np.asarray(img, dtype=np.uint8)
        alpha = compute_alpha(rgb, role)
        rgba = np.dstack([rgb, alpha])
        rgba_img = Image.fromarray(rgba, mode="RGBA")
        art_png, webp = save_artwork(rgba_img, base)
        alpha_p = make_alpha_preview(rgba_img, base)
        mask_p = make_alpha_mask(rgba_img, base)
        tile_p = make_tile_preview(rgba_img, base) if role in ("parallax-bg", "parallax-fg") else None
        size_info = {
            "raw_bytes": raw_path.stat().st_size,
            "png_bytes": art_png.stat().st_size,
            "webp_bytes": webp.stat().st_size,
            "width": rgba_img.size[0],
            "height": rgba_img.size[1],
        }
        summary.append(
            {
                "job_id": job_id,
                "base": base,
                "role": role,
                "raw": str(raw_path.relative_to(ROOT)),
                "artwork_png": str(art_png.relative_to(ROOT)),
                "android_webp": str(webp.relative_to(ROOT)),
                "alpha_on_void": str(alpha_p.relative_to(ROOT)),
                "alpha_mask": str(mask_p.relative_to(ROOT)),
                "tile_preview": str(tile_p.relative_to(ROOT)) if tile_p else None,
                **size_info,
            }
        )
        print(
            f"[ok ] {base}: raw={size_info['raw_bytes']/1024:.0f}KB → "
            f"webp={size_info['webp_bytes']/1024:.0f}KB, {size_info['width']}x{size_info['height']}"
        )

    out = ROOT / "design" / "assets" / "forest" / "records" / "postprocess_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[info] {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
