#!/usr/bin/env python3
"""
森林素材后处理（v2 — 收紧 alpha，区分 role）。

主要改进：
- leaf_path 增加"上半 / 中段远景雾"额外 mask：上半 55% 区域，
  灰度低、饱和度低的淡色雾当背景处理 → 透明。
- overlay 角色（light_shows、clearing）允许更宽的亮度阈值，避免
  把淡光柱误杀。
- character 角色：保留 4 周小边带 + 极严的颜色阈值。
- 同时输出 alpha_on_void 预览与 alpha_mask，供检查。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
RAW_DIR = ROOT / "design" / "assets" / "forest" / "raw"
ART_DIR = ROOT / "design" / "assets" / "forest" / "artwork"
PREVIEW_DIR = ROOT / "design" / "assets" / "forest" / "previews"
ASSETS_VISUAL = ROOT / "app" / "src" / "main" / "assets" / "visual"

ART_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_VISUAL.mkdir(parents=True, exist_ok=True)

VOID_RGB = np.array([0x06, 0x08, 0x06], dtype=np.float32)

LAYER_FILES = {
    "style_ref": ("forest_style_ref", "reference"),
    "forest_tree_outline": ("forest_tree_outline", "parallax-bg"),
    "forest_tree_trunks": ("forest_tree_trunks", "parallax-bg"),
    "forest_leaf_path": ("forest_leaf_path", "parallax-fg"),
    "forest_light_shows": ("forest_light_shows", "overlay"),
    "forest_clearing": ("forest_clearing", "overlay"),
    "traveler_idle": ("traveler_idle", "character"),
}

# 不放入 app/src/main/assets/visual/ 的层（仅留 design 留档）
SKIP_ANDROID_PUBLISH = {"style_ref"}


def _color_distance(rgb, target):
    diff = rgb.astype(np.float32) - target[None, None, :]
    return np.sqrt((diff * diff).sum(axis=2))


def compute_alpha(rgb, role):
    dist = _color_distance(rgb, VOID_RGB)
    h, w = dist.shape

    if role == "reference":
        # 风格参考保持原图，不抠
        return np.full((h, w), 255, dtype=np.uint8)

    if role == "character":
        lo, hi = 26.0, 70.0
    elif role == "parallax-bg":
        # 远景 #1A2820 vs #060806 距离 ≈ 46；需要让树线可见
        lo, hi = 12.0, 35.0
    elif role == "parallax-fg":
        # 叶路径：要识别落叶（暖褐/绿叶）vs 远景雾（淡灰绿）
        lo, hi = 18.0, 50.0
    else:  # overlay
        lo, hi = 14.0, 45.0

    alpha = np.clip((dist - lo) / max(hi - lo, 1e-3), 0.0, 1.0)
    alpha = (alpha * 255).astype(np.uint8)

    # 边带强制透明
    if role == "character":
        et, eb, el, er = 0.06, 0.04, 0.05, 0.05
    else:
        et, eb, el, er = 0.04, 0.04, 0.04, 0.04
    t, b, l, r = int(h*et), int(h*eb), int(w*el), int(w*er)
    alpha[:t, :] = 0
    alpha[h-b:, :] = 0
    alpha[:, :l] = 0
    alpha[:, w-r:] = 0

    # leaf_path 专属：
    # - 上 12% 强制全透明（"上部留白"安全带）
    # - 12%~50% 区域的"远景淡雾"（低饱和度）按颜色距离收紧透明度，
    #   距离 #060806 远 + 饱和度低 → 大幅透明化（保留 ~10% alpha）
    if role == "parallax-fg":
        top_mask = np.zeros((h, w), dtype=bool)
        top_mask[: int(h*0.12), :] = True
        alpha[top_mask] = 0
        mid_mask = np.zeros((h, w), dtype=bool)
        mid_mask[int(h*0.12):int(h*0.50), :] = True
        sat = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
        is_foggy_mid = (sat < 25)
        # 远景雾透明度乘 0.15（仅留一抹暗示，不抢主景）
        alpha[mid_mask & is_foggy_mid] = np.minimum(alpha[mid_mask & is_foggy_mid], 40)

    # overlay 角色：背景（暗绿 #1A2820 附近）也要当透明，
    # 只保留"明显主体像素"（亮度高或饱和度高或与 #060806 距离大）
    if role == "overlay":
        lum = rgb.mean(axis=2)
        sat = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
        is_subject = (lum > 65) | (sat > 40) | (dist > 80)
        # 主体外的像素强制为透明（暗绿背景）
        alpha[~is_subject] = 0
        # 飞鸟：纯黑剪影，但紧贴主体（光柱）的小区域保留弱透明
        from scipy import ndimage
        try:
            mask = is_subject.astype(np.uint8)
            dil = ndimage.binary_dilation(mask, iterations=3)
            keep = dil & (lum < 60) & (sat < 25)
            alpha[keep] = np.maximum(alpha[keep], 70)
        except Exception:
            pass

    return alpha


def save_artwork(rgba_img, base):
    png = ART_DIR / f"{base}.png"
    webp = ASSETS_VISUAL / f"{base}.webp"
    rgba_img.save(png, format="PNG", optimize=True)
    rgba_img.save(webp, format="WEBP", quality=90, method=6)
    return png, webp


def make_alpha_preview(rgba_img, base):
    bg = Image.new("RGB", rgba_img.size, tuple(int(c) for c in VOID_RGB))
    bg.paste(rgba_img, mask=rgba_img.split()[3])
    out = PREVIEW_DIR / f"{base}_alpha_on_void.jpg"
    bg.convert("RGB").save(out, format="JPEG", quality=82)
    return out


def make_alpha_mask(rgba_img, base):
    out = PREVIEW_DIR / f"{base}_alpha_mask.png"
    rgba_img.split()[3].save(out, format="PNG")
    return out


def make_tile_preview(rgba_img, base, repeat=2):
    w, h = rgba_img.size
    canvas = Image.new("RGBA", (w * repeat, h), (6, 8, 6, 255))
    a = rgba_img.split()[3]
    for i in range(repeat):
        canvas.paste(rgba_img, (i * w, 0), mask=a)
    out = PREVIEW_DIR / f"{base}_tile_x{repeat}.jpg"
    canvas.convert("RGB").save(out, format="JPEG", quality=82)
    return out


def main():
    jobs_path = ROOT / "design" / "assets" / "forest" / "records" / "jobs.json"
    state = json.loads(jobs_path.read_text(encoding="utf-8"))

    summary = []
    for jid, (base, role) in LAYER_FILES.items():
        rec = state["jobs"].get(jid)
        if not rec:
            print(f"[skip] {jid} 没有 record")
            continue
        raw = ROOT / rec["raw_path"]
        if not raw.exists():
            print(f"[skip] {jid} raw 缺失: {raw}")
            continue
        img = Image.open(raw).convert("RGB")
        rgb = np.asarray(img, dtype=np.uint8)
        alpha = compute_alpha(rgb, role)
        rgba_arr = np.dstack([rgb, alpha])
        rgba_img = Image.fromarray(rgba_arr, "RGBA")
        png, webp = save_artwork(rgba_img, base)
        aov = make_alpha_preview(rgba_img, base)
        am = make_alpha_mask(rgba_img, base)
        tp = make_tile_preview(rgba_img, base) if role in ("parallax-bg", "parallax-fg", "overlay") else None
        size_info = {
            "raw_bytes": raw.stat().st_size,
            "png_bytes": png.stat().st_size,
            "webp_bytes": webp.stat().st_size,
            "width": rgba_img.size[0],
            "height": rgba_img.size[1],
            "alpha_zero_pct": float((alpha < 5).mean() * 100),
            "alpha_full_pct": float((alpha > 250).mean() * 100),
        }
        summary.append({
            "job_id": jid, "base": base, "role": role,
            "raw": str(raw.relative_to(ROOT)),
            "artwork_png": str(png.relative_to(ROOT)),
            "android_webp": str(webp.relative_to(ROOT)),
            "alpha_on_void": str(aov.relative_to(ROOT)),
            "alpha_mask": str(am.relative_to(ROOT)),
            "tile_preview": str(tp.relative_to(ROOT)) if tp else None,
            **size_info,
        })
        print(
            f"[ok ] {base} ({role}): {size_info['raw_bytes']/1024:.0f}KB raw → "
            f"{size_info['webp_bytes']/1024:.0f}KB webp, "
            f"α0={size_info['alpha_zero_pct']:.1f}% α255={size_info['alpha_full_pct']:.1f}%"
        )

    out = ROOT / "design" / "assets" / "forest" / "records" / "postprocess_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[info] {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
