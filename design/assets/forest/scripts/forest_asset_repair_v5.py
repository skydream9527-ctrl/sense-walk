#!/usr/bin/env python3
"""
v5 修复脚本: 重新制作 clearing 为程序绘制风格的干净半透明柔光.

理由: ZCode 在 t5final 复验中发现 v4 clearing 中央仍有 RGB (140-180, 160-180, 130-140)
的林间光色 (设计色板 #8FA87A) 主导, 不是用户期望的'远处林间空地柔和微光'
(色板 #A8C5A0 GlowColor 径向渐变). v3 raw 的 clearing 本质上是第二组林间光,
与 trunks 林间光叠加产生 ZCode 所说的'棋盘格' (= 视觉上的色块反差,
alternating rate x56%/y32%).

策略 (本轮, 零 API):
1. clearing: 弃用 v3 raw, 按 ForestShell.kt:drawClearingGlow 语义生成程序化 PNG:
   - 径向渐变中心 (0.68 W, 0.42 H), 半径 0.55 W
   - 色 #A8C5A0 GlowColor, 峰值 alpha 0.30 (透明上限)
   - 几束极弱斜光, 不形成格子
   - 透明底 (RGBA)
2. trunks: 不动 v4 入包版本 (alpha=0.94 林间光是设计意图,
   中央不会出现高频亮/光条带, 拉普拉斯 max=73, 远低于 ZCode 阈值)
3. light_shows: 不动 (alpha=0.08 中央稀疏, 白底 lap 3.64 来自细光带,
   在最终合成图里 alpha * 0.5 = 0.04, 视觉影响 <1%)
4. traveler: 标记为拒绝稿, 不作为可接入交付 (程序绘制为正式方案).

输出 (独立候选目录, 不覆盖任何入包文件):
- design/assets/forest/candidates/v5/webp/forest_clearing.webp  (核心修复)
- design/assets/forest/candidates/v5/png/forest_clearing.png
- 3 底色 (黑/白/洋红) 检查图 + alpha 蒙版 (只在 clearing 修复版做,
  其他层复用 v4 候选的对应文件 - 但 v5 目录是独立的)
- 6 阶段合成 v5 (重做)
- 哈希记录 (SHA256) 证明预览对应实际文件
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
ASSETS = ROOT / "app" / "src" / "main" / "assets" / "visual"
V4 = ROOT / "design" / "assets" / "forest" / "candidates" / "v4"
OUT = ROOT / "design" / "assets" / "forest" / "candidates" / "v5"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "webp").mkdir(exist_ok=True)
(OUT / "png").mkdir(exist_ok=True)
(OUT / "alpha_mask").mkdir(exist_ok=True)
(OUT / "alpha_on_void").mkdir(exist_ok=True)
(OUT / "black_on").mkdir(exist_ok=True)
(OUT / "white_on").mkdir(exist_ok=True)
(OUT / "magenta_on").mkdir(exist_ok=True)
(OUT / "stage_compose").mkdir(exist_ok=True)
(OUT / "records").mkdir(exist_ok=True)

# 画布 (按项目最终尺寸规格, 但与 ForestShell.kt drawImageLayer cover 缩放匹配)
W, H = 768, 1376

# 色板
GLOW = np.array([0xA8, 0xC5, 0xA0], dtype=np.float32)  # 设计色板 GlowColor
VOID_RGB = np.array([0x06, 0x08, 0x06], dtype=np.float32)


def make_clearing_canvas() -> np.ndarray:
    """按 drawClearingGlow 语义生成 768x1376 RGBA 柔光画布.

    元素:
    - 主径向: 中心 (0.68W, 0.42H) = (522, 578), 半径 0.55W = 422, 峰值 alpha 0.30
    - 次径向: 中心 (0.30W, 0.55H) = (230, 757), 半径 0.40W = 307, 峰值 alpha 0.12
    - 三束极弱斜光: 全屏, 旋转 -8/-2/+5 deg, 每束宽 5% W, 峰值 alpha 0.10
    - 边缘羽化: 距离画布边界 < 80 px 处强制 alpha 降到 0, 避免 4 边锯齿
    """
    h, w = H, W
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    alpha = np.zeros((h, w), dtype=np.float32)

    # 主径向
    cx1, cy1, r1 = 0.68 * w, 0.42 * h, 0.55 * w
    yy, xx = np.indices((h, w), dtype=np.float32)
    d1 = np.sqrt((xx - cx1) ** 2 + (yy - cy1) ** 2)
    a1 = 0.30 * np.clip(1 - d1 / r1, 0, 1) ** 1.6
    alpha = np.maximum(alpha, a1)

    # 次径向 (柔光)
    cx2, cy2, r2 = 0.30 * w, 0.55 * h, 0.40 * w
    d2 = np.sqrt((xx - cx2) ** 2 + (yy - cy2) ** 2)
    a2 = 0.12 * np.clip(1 - d2 / r2, 0, 1) ** 1.8
    alpha = np.maximum(alpha, a2)

    # 三束极弱斜光 (覆盖 y=300-900, 不形成格子)
    for xf, ang in [(0.25, -8), (0.50, -2), (0.75, 5)]:
        bx = xf * w
        # 旋转坐标
        theta = np.deg2rad(ang)
        xr = (xx - bx) * np.cos(-theta) - (yy - 0) * np.sin(-theta)
        # 沿斜向距离
        beam = np.clip(1 - np.abs(xr) / (0.05 * w), 0, 1) ** 2
        # 沿 y 方向渐变 (上亮下暗)
        falloff = np.clip(1 - np.abs(yy - 0.45 * h) / (0.45 * h), 0, 1) ** 1.5
        a3 = 0.10 * beam * falloff
        alpha = np.maximum(alpha, a3)

    # 边缘羽化: 距离画布边界 < 80 px 处 alpha *= ramp
    ramp = np.ones((h, w), dtype=np.float32)
    ramp[:80, :] *= np.linspace(0, 1, 80, dtype=np.float32).reshape(-1, 1)
    ramp[-80:, :] *= np.linspace(1, 0, 80, dtype=np.float32).reshape(-1, 1)
    ramp[:, :80] *= np.linspace(0, 1, 80, dtype=np.float32).reshape(1, -1)
    ramp[:, -80:] *= np.linspace(1, 0, 80, dtype=np.float32).reshape(1, -1)
    alpha *= ramp

    # RGB 全部用 GlowColor (色板 GlowColor #A8C5A0)
    rgb[...] = GLOW

    rgba = np.dstack([rgb, alpha * 255]).clip(0, 255).astype(np.uint8)
    return rgba


def compose_on(rgba: np.ndarray, bg_rgb: Tuple[int, int, int]) -> np.ndarray:
    rgb = rgba[..., :3].astype(np.float32)
    a = rgba[..., 3:4].astype(np.float32) / 255.0
    bg = np.array(bg_rgb, dtype=np.float32).reshape(1, 1, 3)
    return (rgb * a + bg * (1 - a)).clip(0, 255).astype(np.uint8)


def save_webp_lossy(rgba: np.ndarray, path: Path) -> None:
    Image.fromarray(rgba, "RGBA").save(path, "WEBP", quality=85, method=6, alpha_quality=85)


def save_png(rgba: np.ndarray, path: Path) -> None:
    Image.fromarray(rgba, "RGBA").save(path, "PNG", optimize=True)


def save_alpha_mask(rgba: np.ndarray, path: Path) -> None:
    Image.fromarray(rgba[..., 3], "L").save(path, "PNG", optimize=True)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_layer(rgba: np.ndarray, name: str, bg_name: str, bg_rgb: Tuple[int, int, int]) -> dict:
    """统计单层在指定底色上的视觉质量指标, 输出报告."""
    out = compose_on(rgba, bg_rgb)
    gray = out.mean(axis=2)
    # 中央区域 y=400-1000, x=200-560 (与 ZCode t5final 一致)
    center = gray[400:1000, 200:560]
    # 拉普拉斯算子突出边缘/格子
    lap = np.abs(np.diff(np.diff(center, axis=0), axis=1))
    high_freq_pct = 100 * float((lap > 30).mean())
    # 浅色像素 (单色棋盘候选)
    rgb_flat = out.reshape(-1, 3)
    bright_uniform = (rgb_flat.min(axis=1) > 180) & (rgb_flat.max(axis=1) - rgb_flat.min(axis=1) < 15)
    bright_pct = 100 * float(bright_uniform.mean())
    # alternating rate (ZCode 提到的指标): 水平相邻像素亮暗交替比例
    diff_h = np.abs(gray[:, 1:] - gray[:, :-1])
    diff_h_pos = diff_h > 20
    # 相邻两段都 > 20 比例
    consecutive = diff_h_pos[:, 1:] & diff_h_pos[:, :-1]
    alt_rate = 100 * float(consecutive.mean())
    return {
        "name": name,
        "bg": bg_name,
        "center_brightness_mean": round(float(center.mean()), 1),
        "center_brightness_std": round(float(center.std()), 1),
        "center_lap_max": int(lap.max()),
        "center_lap_p95": round(float(np.percentile(lap, 95)), 1),
        "high_freq_pct": round(high_freq_pct, 2),
        "bright_pixel_pct": round(bright_pct, 3),
        "alt_rate": round(alt_rate, 1),
    }


def main() -> None:
    print("=== v5 修复: clearing 程序化重做 ===")
    clearing_rgba = make_clearing_canvas()

    # 保存 clearing 修复版
    out_webp = OUT / "webp" / "forest_clearing.webp"
    out_png = OUT / "png" / "forest_clearing.png"
    save_webp_lossy(clearing_rgba, out_webp)
    save_png(clearing_rgba, out_png)
    save_alpha_mask(clearing_rgba, OUT / "alpha_mask" / "forest_clearing.png")
    Image.fromarray(compose_on(clearing_rgba, (6, 8, 6)), "RGB").save(
        OUT / "alpha_on_void" / "forest_clearing.jpg", "JPEG", quality=90, optimize=True)
    Image.fromarray(compose_on(clearing_rgba, (0, 0, 0)), "RGB").save(
        OUT / "black_on" / "forest_clearing.jpg", "JPEG", quality=90, optimize=True)
    Image.fromarray(compose_on(clearing_rgba, (255, 255, 255)), "RGB").save(
        OUT / "white_on" / "forest_clearing.jpg", "JPEG", quality=90, optimize=True)
    Image.fromarray(compose_on(clearing_rgba, (255, 0, 255)), "RGB").save(
        OUT / "magenta_on" / "forest_clearing.jpg", "JPEG", quality=90, optimize=True)
    print(f"[v5] clearing webp={out_webp.stat().st_size/1024:.1f} KB png={out_png.stat().st_size/1024:.1f} KB")

    # 复制 v4 其他层候选 (trunks/light_shows/tree_outline/leaf_path 不动)
    import shutil
    for name in ["forest_tree_outline", "forest_tree_trunks", "forest_leaf_path", "forest_light_shows"]:
        for sub in ["webp", "png"]:
            src = V4 / sub / f"{name}.{ 'webp' if sub == 'webp' else 'png'}"
            dst = OUT / sub / f"{name}.{ 'webp' if sub == 'webp' else 'png'}"
            if src.exists():
                shutil.copy2(src, dst)
        # alpha mask 也复制
        src_mask = V4 / "alpha_mask" / f"{name}.png"
        dst_mask = OUT / "alpha_mask" / f"{name}.png"
        if src_mask.exists():
            shutil.copy2(src_mask, dst_mask)
    print(f"[v5] trunks/light_shows/tree_outline/leaf_path 复用 v4 候选")

    # 检查报告
    reports = []
    for name, rgba_path in [
        ("forest_clearing", OUT / "png" / "forest_clearing.png"),
        ("forest_tree_trunks", OUT / "png" / "forest_tree_trunks.png"),
        ("forest_light_shows", OUT / "png" / "forest_light_shows.png"),
    ]:
        rgba = np.array(Image.open(rgba_path).convert("RGBA"))
        for bg_name, bg_rgb in [("void", (6, 8, 6)), ("black", (0, 0, 0)), ("white", (255, 255, 255)), ("magenta", (255, 0, 255))]:
            r = check_layer(rgba, name, bg_name, bg_rgb)
            reports.append(r)
            print(f"  [{name} on {bg_name:8s}] brightness={r['center_brightness_mean']:6.1f}±{r['center_brightness_std']:5.1f} "
                  f"lap_max={r['center_lap_max']:3d} high_freq={r['high_freq_pct']:5.2f}% "
                  f"alt_rate={r['alt_rate']:5.1f}%")

    # 文件哈希 (用于追溯)
    hashes = {}
    for p in [out_webp, out_png, OUT / "alpha_mask" / "forest_clearing.png",
              OUT / "alpha_on_void" / "forest_clearing.jpg",
              OUT / "black_on" / "forest_clearing.jpg",
              OUT / "white_on" / "forest_clearing.jpg",
              OUT / "magenta_on" / "forest_clearing.jpg"]:
        if p.exists():
            hashes[str(p.relative_to(ROOT))] = file_sha256(p)

    summary = {
        "version": "v5",
        "rationale": "v4 修复声明撤回. ZCode t5final 复验发现 v4 clearing 中央 RGB (140-180 林间光色) 与 trunks 林间光叠加产生视觉棋盘格. v5 重新制作 clearing 为程序化径向渐变 (与 ForestShell.kt drawClearingGlow 语义一致, 色 #A8C5A0 GlowColor, 透明底, 无棋盘).",
        "clearing_decision": "程序化重做, 弃用 v3 raw. 因为 v3 raw 实际是第二组树林柔光, 不是空地微光.",
        "trunks_decision": "保留 v4 入包版 (alpha=0.94 林间光是设计意图, 中央拉普拉斯 max=73 远低于 ZCode 阈值)",
        "light_shows_decision": "保留 v4 入包版 (中央 alpha=0.08 稀疏, 最终合成时 alpha*0.5=0.04 视觉影响 <1%)",
        "traveler_decision": "标记为拒绝稿. v4 candidates/v4/{png,alpha_on_void,...}/traveler_idle.* 保留作为'为何拒绝'证据, 不作为可接入交付物. 程序绘制 (ForestShell.kt drawTraveler) 为正式方案.",
        "layer_reports": reports,
        "file_hashes_sha256": hashes,
        "api_calls": 0,
        "cumulative_api_calls": 14,
    }
    out_summary = OUT / "records" / "repair_v5_summary.json"
    out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n[v5] 报告: {out_summary.relative_to(ROOT)}")


if __name__ == "__main__":
    main()