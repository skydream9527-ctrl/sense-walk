#!/usr/bin/env python3
"""
v4 修复脚本 — 基于 v3 入包 webp 的 RGBA 做内容修正,不动现有入包文件。

策略:
- 直接读 v3 webp (RGBA), v3 的 alpha 已被 ZCode 接受且分布干净
- trunks: 底部 y>950 区域的 alpha 衰减到主体最大 alpha 的 35%,
  避免与 clearing overlay 叠加出"灰雾"棋盘格
- clearing: 顶部 y<200 和底部 y>650 区域的 alpha 强制为 0,
  把柔光收到中带 30-50% 高度,避免与 trunks 底部林间光叠加
- traveler: 不动 (程序绘制为正式方案, ASSETS.md 已声明), 仅生成检查图
- parallax 三层 (tree_outline / tree_trunks / leaf_path): 生成可平铺版本
  (左右边缘像素混合 + 3x 拼接预览 + 滚动预览)

零 API 调用。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[4]
ASSETS = ROOT / "app" / "src" / "main" / "assets" / "visual"
RAW = ROOT / "design" / "assets" / "forest" / "raw"
OUT = ROOT / "design" / "assets" / "forest" / "candidates" / "v4"
OUT.mkdir(parents=True, exist_ok=True)

SRC_W, SRC_H = 768, 1376

LAYERS = {
    "forest_tree_outline": {"role": "parallax", "src": "v3_webp"},
    "forest_tree_trunks":  {"role": "parallax", "src": "v3_webp"},
    "forest_leaf_path":    {"role": "parallax", "src": "v3_webp"},
    "forest_light_shows":  {"role": "overlay", "src": "v3_webp"},
    "forest_clearing":     {"role": "overlay", "src": "v3_webp"},
}


def compose_on(rgba: np.ndarray, bg_rgb: Tuple[int, int, int]) -> np.ndarray:
    """RGBA uint8 + 纯色底 -> RGB uint8."""
    rgb = rgba[..., :3].astype(np.float32)
    a = rgba[..., 3:4].astype(np.float32) / 255.0
    bg = np.array(bg_rgb, dtype=np.float32).reshape(1, 1, 3)
    return (rgb * a + bg * (1 - a)).clip(0, 255).astype(np.uint8)


def constrain_trunks_alpha(rgba: np.ndarray) -> np.ndarray:
    """trunks: 限制底部 y>950 的 alpha 不超过主体最大值的 35%."""
    rgba = rgba.copy()
    a = rgba[..., 3].astype(np.float32)
    h = a.shape[0]
    body_top = int(h * 200 / 1376)
    body_bot = int(h * 950 / 1376)
    if body_bot >= h:
        return rgba
    body_max = a[body_top:body_bot].max()
    if body_max <= 0:
        return rgba
    # 衰减曲线: 从 body_bot 处的 0.35 平滑降到 0
    target_frac = 0.35
    fade_len = h - body_bot
    for y in range(body_bot, h):
        t = (y - body_bot) / max(1, fade_len)
        decay = target_frac * (1 - t)
        a[y] = np.minimum(a[y], body_max * decay)
    rgba[..., 3] = a.clip(0, 255).astype(np.uint8)
    return rgba


def constrain_clearing_alpha(rgba: np.ndarray) -> np.ndarray:
    """clearing: 限制 alpha 在 y=200-650 中带 (35% 高度), 上下强制为 0."""
    rgba = rgba.copy()
    a = rgba[..., 3].astype(np.float32)
    h = a.shape[0]
    top = int(h * 200 / 1376)
    bot = int(h * 650 / 1376)
    feather = int(h * 40 / 1376)  # 顶部和底部各 40px 羽化
    new_a = np.zeros_like(a)
    # 中带保留
    new_a[top + feather:bot - feather] = a[top + feather:bot - feather]
    # 顶部羽化
    for y in range(top, top + feather):
        if y < h:
            t = (y - top) / max(1, feather)
            new_a[y] = a[y] * t
    # 底部羽化
    for y in range(bot - feather, bot):
        if y < h:
            t = (bot - y) / max(1, feather)
            new_a[y] = a[y] * t
    rgba[..., 3] = new_a.clip(0, 255).astype(np.uint8)
    return rgba


def make_tileable(rgba: np.ndarray, overlap_px: int = 64) -> np.ndarray:
    """左右边缘像素混合, 让图可水平循环平铺."""
    rgba = rgba.copy()
    h, w, _ = rgba.shape
    ov = min(overlap_px, w // 2)
    if ov < 4:
        return rgba
    left = rgba[:, :ov, :].astype(np.float32)
    right = rgba[:, w - ov:, :].astype(np.float32)
    ramp = np.linspace(0, 1, ov, dtype=np.float32).reshape(1, -1, 1)
    blended = left * (1 - ramp) + right * ramp
    rgba[:, :ov, :] = blended.clip(0, 255).astype(np.uint8)
    rgba[:, w - ov:, :] = blended.clip(0, 255).astype(np.uint8)
    return rgba


def save_seamless_preview(rgba: np.ndarray, repeats: int, path: Path,
                          bg_rgb: Tuple[int, int, int]) -> None:
    """3x 横向拼接预览 (投到 bg_rgb 底色)."""
    composed = compose_on(rgba, bg_rgb)
    h, w, _ = composed.shape
    out = np.tile(composed, (1, repeats, 1))
    Image.fromarray(out, "RGB").save(path, "JPEG", quality=85, optimize=True)


def save_scroll_preview(rgba: np.ndarray, scroll_px: int, path: Path,
                        canvas_w: int = 1080, canvas_h: int = 1920,
                        bg_rgb: Tuple[int, int, int] = (6, 8, 6)) -> None:
    """模拟滚动预览: 把图缩放到 canvas_h, 投到 bg_rgb, 取 scroll_px 偏移处一张 1080x1920."""
    h, w, _ = rgba.shape
    scale = canvas_h / h
    dst_w = int(w * scale)
    img = Image.fromarray(rgba, "RGBA").resize((dst_w, canvas_h), Image.LANCZOS)
    tile = np.array(img)
    # 重复到足够宽
    canvas = np.tile(tile, (1, (canvas_w + scroll_px) // dst_w + 2, 1))
    composed = compose_on(canvas, bg_rgb)
    sub = composed[:, scroll_px:scroll_px + canvas_w]
    Image.fromarray(sub, "RGB").save(path, "JPEG", quality=85, optimize=True)


def save_webp_lossy(rgba: np.ndarray, path: Path) -> None:
    """RGBA -> WebP (lossy, quality 80, 保留 alpha)."""
    Image.fromarray(rgba, "RGBA").save(path, "WEBP", quality=80, method=6, alpha_quality=80)


def save_png(rgba: np.ndarray, path: Path) -> None:
    Image.fromarray(rgba, "RGBA").save(path, "PNG", optimize=True)


def save_alpha_mask(rgba: np.ndarray, path: Path) -> None:
    a = rgba[..., 3]
    Image.fromarray(a, "L").save(path, "PNG", optimize=True)


def process_layer(name: str, role: str) -> dict:
    src_path = ASSETS / f"{name}.webp"
    rgba = np.array(Image.open(src_path).convert("RGBA"))
    info = {"name": name, "role": role, "src": str(src_path.relative_to(ROOT))}

    if name == "forest_tree_trunks":
        rgba = constrain_trunks_alpha(rgba)
    elif name == "forest_clearing":
        rgba = constrain_clearing_alpha(rgba)
    # 其他层直接复制 v3

    out_webp = OUT / "webp" / f"{name}.webp"
    out_png = OUT / "png" / f"{name}.png"
    save_webp_lossy(rgba, out_webp)
    save_png(rgba, out_png)
    save_alpha_mask(rgba, OUT / "alpha_mask" / f"{name}.png")

    # 三色底
    Image.fromarray(compose_on(rgba, (6, 8, 6)), "RGB").save(
        OUT / "alpha_on_void" / f"{name}.jpg", "JPEG", quality=85, optimize=True)
    Image.fromarray(compose_on(rgba, (0, 0, 0)), "RGB").save(
        OUT / "black_on" / f"{name}.jpg", "JPEG", quality=85, optimize=True)
    Image.fromarray(compose_on(rgba, (255, 255, 255)), "RGB").save(
        OUT / "white_on" / f"{name}.jpg", "JPEG", quality=85, optimize=True)
    Image.fromarray(compose_on(rgba, (255, 0, 255)), "RGB").save(
        OUT / "magenta_on" / f"{name}.jpg", "JPEG", quality=85, optimize=True)

    # parallax 三层做真拼接 + 滚动预览
    if role == "parallax":
        tileable = make_tileable(rgba, overlap_px=64)
        tile_webp = OUT / "webp" / f"{name}_tileable.webp"
        save_webp_lossy(tileable, tile_webp)
        save_seamless_preview(tileable, 3,
                              OUT / "seamless_tile" / f"{name}_x3.jpg", (6, 8, 6))
        # 滚动预览: 偏移 0、1/4、1/2、3/4 周期, 检验左右接缝
        for frac, tag in [(0.0, "0"), (0.25, "q1"), (0.5, "half"), (0.75, "q3")]:
            px = int(tileable.shape[1] * frac)
            save_scroll_preview(tileable, px,
                               OUT / "scroll_preview" / f"{name}_scroll_{tag}.jpg")

    info["out_png"] = str(out_png.relative_to(ROOT))
    info["out_webp"] = str(out_webp.relative_to(ROOT))
    info["size_kb_png"] = round(out_png.stat().st_size / 1024, 1)
    info["size_kb_webp"] = round(out_webp.stat().st_size / 1024, 1)
    info["alpha_coverage"] = round(float((rgba[..., 3] > 60).mean()) * 100, 1)
    info["alpha_255_ratio"] = round(float((rgba[..., 3] == 255).mean()) * 100, 1)
    return info


def process_traveler_check() -> dict:
    """traveler: 程序绘制为正式方案 (ForestShell.kt drawTraveler + ASSETS.md §一备注).
    本轮生成 v3 棋盘背景诊断图, 确认 81% 满帧的构成."""
    raw = np.array(Image.open(RAW / "traveler_idle.jpg").convert("RGB"))
    gray = raw.mean(axis=2)
    # 棋盘色像素: 亮度 ~120-130 (灰) 或 ~50-60 (暗灰)
    bright = (gray > 100) & (gray < 140)
    dark = (gray > 40) & (gray < 70)
    # 棋盘特征: bright/dark 邻接规律
    n_bright = int(bright.sum())
    n_dark = int(dark.sum())
    info = {
        "name": "traveler_idle",
        "role": "character",
        "src": str((RAW / "traveler_idle.jpg").relative_to(ROOT)),
        "decision": "程序绘制为正式方案 (ForestShell.kt drawTraveler + ASSETS.md)",
        "v3_webp_in_assets": "0 bytes (ZCode 已在 1baef18 移除)",
        "v3_raw_checker_bright_pixels": n_bright,
        "v3_raw_checker_dark_pixels": n_dark,
        "v3_raw_checker_total_ratio": round(100 * (n_bright + n_dark) / gray.size, 1),
    }
    # 保存棋盘特征图
    mask = np.zeros_like(raw)
    mask[bright] = [255, 0, 0]   # 红 = 浅棋盘格
    mask[dark] = [0, 0, 255]     # 蓝 = 深棋盘格
    Image.fromarray(mask, "RGB").save(
        OUT / "magenta_on" / "traveler_idle_checker_mask.jpg", "JPEG", quality=85, optimize=True)
    return info


def main() -> None:
    summary = []
    for name, spec in LAYERS.items():
        info = process_layer(name, spec["role"])
        summary.append(info)
        print(f"[v4] {name}: webp={info['size_kb_webp']} KB, alpha>60={info['alpha_coverage']}%")

    traveler_info = process_traveler_check()
    summary.append(traveler_info)
    print(f"[v4] traveler_idle: 程序绘制, 棋盘像素 {traveler_info['v3_raw_checker_total_ratio']}%")

    out_json = ROOT / "design" / "assets" / "forest" / "records" / "repair_v4_summary.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n[v4] 总结: {out_json.relative_to(ROOT)}")


if __name__ == "__main__":
    main()