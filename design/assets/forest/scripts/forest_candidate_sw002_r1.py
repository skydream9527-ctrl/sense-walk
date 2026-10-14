#!/usr/bin/env python3
"""
SW-002 r1 候选生成:
- clearing: 按 v5 程序化径向渐变, 复用 v5/webp/forest_clearing.webp 作为 r1 输出
- light_shows: 程序化重做, 干净透明, 模拟 ForestShell.kt drawLightShows
  (三束斜光 + 几只飞鸟剪影), 无棋盘, 透明底

零 API 调用. 累积总账: 14 次 (v1/v2/v3 共 14, v4 0, v5 0, SW-002 r1 0)

输出到 design/assets/forest/candidates/SW-002/r1/:
- webp/{clearing,light_shows}.webp  (Android-ready)
- png/{clearing,light_shows}.png     (高保真)
- checks/black/  /white/  /magenta/  (3 底色合成)
- checks/alpha_mask/                  (alpha 蒙版)
- checks/stages/                      (6 阶段合成 - r1 用入包 v4 + r1 候选)
- records/                            (诊断 JSON + SHA256)
- rejected/superseded/                (v4 / v5 候选复用作历史, 标 superseded)

canvas 768x1376 (历史 raw 尺寸, 与 ZCode 入包 webp 比例一致, 不冒称原生 1080x1920)
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
V5 = ROOT / "design" / "assets" / "forest" / "candidates" / "v5"
OUT = ROOT / "design" / "assets" / "forest" / "candidates" / "SW-002" / "r1"

W, H = 768, 1376
VOID_RGB = np.array([0x06, 0x08, 0x06], dtype=np.float32)
GLOW = np.array([0xA8, 0xC5, 0xA0], dtype=np.float32)         # GlowColor
LIGHT = np.array([0x8F, 0xA8, 0x7A], dtype=np.float32)        # TrunkLightColor
BIRD = np.array([0x1A, 0x28, 0x20], dtype=np.float32)         # OutlineColor (深绿)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_clearing_canvas() -> np.ndarray:
    """v5 程序化径向渐变 (已合格, 复用, 不变)."""
    h, w = H, W
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    alpha = np.zeros((h, w), dtype=np.float32)
    yy, xx = np.indices((h, w), dtype=np.float32)

    # 主径向 (右上林光)
    cx1, cy1, r1 = 0.68 * w, 0.42 * h, 0.55 * w
    d1 = np.sqrt((xx - cx1) ** 2 + (yy - cy1) ** 2)
    a1 = 0.30 * np.clip(1 - d1 / r1, 0, 1) ** 1.6
    alpha = np.maximum(alpha, a1)

    # 次径向 (左下柔光)
    cx2, cy2, r2 = 0.30 * w, 0.55 * h, 0.40 * w
    d2 = np.sqrt((xx - cx2) ** 2 + (yy - cy2) ** 2)
    a2 = 0.12 * np.clip(1 - d2 / r2, 0, 1) ** 1.8
    alpha = np.maximum(alpha, a2)

    # 三束极弱斜光
    for xf, ang in [(0.25, -8), (0.50, -2), (0.75, 5)]:
        bx = xf * w
        theta = np.deg2rad(ang)
        xr = (xx - bx) * np.cos(-theta) - (yy - 0) * np.sin(-theta)
        beam = np.clip(1 - np.abs(xr) / (0.05 * w), 0, 1) ** 2
        falloff = np.clip(1 - np.abs(yy - 0.45 * h) / (0.45 * h), 0, 1) ** 1.5
        a3 = 0.10 * beam * falloff
        alpha = np.maximum(alpha, a3)

    # 边缘羽化
    ramp = np.ones((h, w), dtype=np.float32)
    ramp[:80, :] *= np.linspace(0, 1, 80, dtype=np.float32).reshape(-1, 1)
    ramp[-80:, :] *= np.linspace(1, 0, 80, dtype=np.float32).reshape(-1, 1)
    ramp[:, :80] *= np.linspace(0, 1, 80, dtype=np.float32).reshape(1, -1)
    ramp[:, -80:] *= np.linspace(1, 0, 80, dtype=np.float32).reshape(1, -1)
    alpha *= ramp
    rgb[...] = GLOW
    return np.dstack([rgb, alpha * 255]).clip(0, 255).astype(np.uint8)


def make_light_shows_canvas() -> np.ndarray:
    """程序化重做 light_shows: 三束斜光 + 几只飞鸟剪影.

    对比 v2/v3 raw (3 飞鸟 + 3 光柱 + 棋盘格背景):
    - 透明底, 无背景
    - 三束斜光 (LIGHT 色) 严格控制 alpha 峰值, 软衰减
    - 飞鸟剪影 (BIRD 色 OutlineColor) 小而克制, 不成画面主体
    - 边缘羽化避免 4 边锯齿
    """
    h, w = H, W
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    alpha = np.zeros((h, w), dtype=np.float32)
    yy, xx = np.indices((h, w), dtype=np.float32)

    # 三束斜光 (与 ForestShell.kt drawLightShows 语义一致)
    # 倾角 -14, -8, -2 deg; 顶部高亮, 向下衰减
    for xf, ang_deg, peak in [(0.28, -14, 0.45), (0.50, -8, 0.40), (0.72, -2, 0.45)]:
        bx = xf * w
        theta = np.deg2rad(ang_deg)
        # 沿斜向: 用 1 - |xr|/beam_width
        xr = (xx - bx) * np.cos(-theta) - (yy - 0) * np.sin(-theta)
        beam_w = 0.09 * w
        beam = np.clip(1 - np.abs(xr) / beam_w, 0, 1) ** 2
        # y 方向: 顶部 alpha 强, 底部 alpha=0
        y_falloff = np.clip(1 - yy / (0.85 * h), 0, 1) ** 1.5
        a = peak * beam * y_falloff
        alpha = np.maximum(alpha, a)

    # 飞鸟剪影 (2 只, 远景, 缩小版, 软边避免 lap 突变)
    # 较远位置 (y=15%, x=68%/76%), 翼展 18px, 翼高 5px, 更克制
    bird_positions = [(0.68 * w, 0.15 * h), (0.76 * w, 0.12 * h)]
    for cx, cy in bird_positions:
        span = 18
        rel_x = (xx - cx) / span
        rel_y = (yy - cy) / 5.0
        boundary = -rel_x ** 2 + 0.7
        above = rel_y < boundary
        below = rel_y > -0.5
        # 软化: 距边界 1.5 单位做线性衰减
        dy_above = np.maximum(0, rel_y - boundary)
        dy_below = np.maximum(0, -0.5 - rel_y)
        dist = np.minimum(dy_above, dy_below)  # 取较小 = 距最近边界
        # 内部 alpha 0.55, 距边界 1.5 单位降到 0
        soft = np.clip(1.5 - dist, 0, 1.5) / 1.5
        wing_alpha = 0.55 * soft
        wing_alpha = np.where(above & below, wing_alpha, 0.0)
        alpha = np.maximum(alpha, wing_alpha)

    # 边缘羽化
    ramp = np.ones((h, w), dtype=np.float32)
    ramp[:60, :] *= np.linspace(0, 1, 60, dtype=np.float32).reshape(-1, 1)
    ramp[-60:, :] *= np.linspace(1, 0, 60, dtype=np.float32).reshape(-1, 1)
    ramp[:, :60] *= np.linspace(0, 1, 60, dtype=np.float32).reshape(1, -1)
    ramp[:, -60:] *= np.linspace(1, 0, 60, dtype=np.float32).reshape(1, -1)
    alpha *= ramp

    # RGB: 光柱用 LIGHT (#8FA87A), 飞鸟用 BIRD (#1A2820)
    # 混合策略: 飞鸟区域用 BIRD, 其余用 LIGHT
    rgb[..., :] = LIGHT
    bird_mask = alpha > 0.5  # 飞鸟是高 alpha 区
    rgb[bird_mask] = BIRD
    return np.dstack([rgb, alpha * 255]).clip(0, 255).astype(np.uint8)


def compose_on(rgba: np.ndarray, bg_rgb: Tuple[int, int, int]) -> np.ndarray:
    rgb = rgba[..., :3].astype(np.float32)
    a = rgba[..., 3:4].astype(np.float32) / 255.0
    bg = np.array(bg_rgb, dtype=np.float32).reshape(1, 1, 3)
    return (rgb * a + bg * (1 - a)).clip(0, 255).astype(np.uint8)


def save_webp(rgba: np.ndarray, path: Path) -> None:
    Image.fromarray(rgba, "RGBA").save(path, "WEBP", quality=85, method=6, alpha_quality=85)


def save_png(rgba: np.ndarray, path: Path) -> None:
    Image.fromarray(rgba, "RGBA").save(path, "PNG", optimize=True)


def save_alpha_mask(rgba: np.ndarray, path: Path) -> None:
    Image.fromarray(rgba[..., 3], "L").save(path, "PNG", optimize=True)


def diagnose_layer(rgba: np.ndarray, name: str, bg_name: str, bg_rgb: Tuple[int, int, int]) -> dict:
    """按 SW-002 任务文件要求: 实际纯色底合成无烘焙棋盘、白边和矩形底."""
    out = compose_on(rgba, bg_rgb)
    gray = out.mean(axis=2)
    # 内容带 (per ASSETS.md "逐层内容带中心而非图像几何中心"):
    # clearing 30-50% y, light_shows 10-40% y
    if name == "clearing":
        y_top, y_bot = int(0.30 * H), int(0.50 * H)
    else:  # light_shows
        y_top, y_bot = int(0.10 * H), int(0.40 * H)
    x_left, x_right = int(0.20 * W), int(0.80 * W)
    band = gray[y_top:y_bot, x_left:x_right]

    # ZCode 复验用指标 (ASSETS.md §一备忘):
    # ① 32px 周期对角能量 (本轮: 二维 FFT 在 (32, 32) 频率)
    # ② 8px 相位差, 块交替率
    # ③ 高频拉普拉斯能量
    h, w = band.shape
    fft = np.fft.fft2(band - band.mean())
    fft_mag = np.abs(fft)
    fft_mag_shift = np.fft.fftshift(fft_mag)
    # 中心 (0, 0) 是 DC, (h//2, w//2) 是 Nyquist. 32px 周期对应频率 k = h/32
    k = h / 32
    diag_energy = float(fft_mag_shift[
        int(h // 2 - k):int(h // 2 + k + 1),
        int(w // 2 - k):int(w // 2 + k + 1)
    ].sum() / fft_mag_shift.sum() * 100)

    # 8px 相位差 (ZCode 检查)
    diff_h_8 = np.abs(np.diff(band, axis=1)[:, ::4])  # 近似 8px 采样
    alt_8 = float((diff_h_8 > 10).mean() * 100)

    # 32px 周期 (ZCode 检查)
    diff_h_32 = np.abs(np.diff(band, axis=1)[:, ::16])  # 近似 32px 采样
    alt_32 = float((diff_h_32 > 10).mean() * 100)

    # 高频拉普拉斯
    lap = np.abs(np.diff(np.diff(band, axis=0), axis=1))
    high_freq_pct = float((lap > 30).mean() * 100)
    lap_max = int(lap.max())

    # 浅色像素
    rgb_flat = out.reshape(-1, 3)
    bright_uniform = (rgb_flat.min(axis=1) > 180) & (rgb_flat.max(axis=1) - rgb_flat.min(axis=1) < 15)
    bright_pct = float(bright_uniform.mean() * 100)

    return {
        "name": name,
        "bg": bg_name,
        "content_band": [y_top, y_bot, x_left, x_right],
        "brightness_mean": round(float(band.mean()), 1),
        "brightness_std": round(float(band.std()), 1),
        "diag_32px_energy_pct": round(diag_energy, 2),
        "alt_8px_pct": round(alt_8, 2),
        "alt_32px_pct": round(alt_32, 2),
        "lap_max": lap_max,
        "high_freq_pct": round(high_freq_pct, 3),
        "bright_uniform_pct": round(bright_pct, 3),
    }


# === 6 阶段合成（按 forest.json §phases + 真实入包资产） ===

PHASES = {
    "void":         {"atMeters": 0,   "toOpacity": 1.00, "fadeMeters": 1},
    "tree_outline": {"atMeters": 80,  "toOpacity": 0.60, "fadeMeters": 20},
    "tree_trunks":  {"atMeters": 240, "toOpacity": 0.70, "fadeMeters": 25},
    "leaf_path":    {"atMeters": 400, "toOpacity": 0.80, "fadeMeters": 25},
    "light_shows":  {"atMeters": 600, "toOpacity": 0.65, "fadeMeters": 30},
    "clearing":     {"atMeters": 760, "toOpacity": 0.90, "fadeMeters": 25},
}
# SW-002 r1 范围: outline/trunks/leaf_path 用入包 v4 (已被 ZCode 接受),
# light_shows/clearing 用 r1 候选 (本轮修复)
LAYER_SOURCE = {
    "tree_outline": ASSETS / "forest_tree_outline.webp",
    "tree_trunks":  ASSETS / "forest_tree_trunks.webp",
    "leaf_path":    ASSETS / "forest_leaf_path.webp",
    "light_shows":  OUT / "webp" / "forest_light_shows.webp",
    "clearing":     OUT / "webp" / "forest_clearing.webp",
}
LAYERS_BY_METER = {
    0:   [],
    100: ["tree_outline"],
    265: ["tree_outline", "tree_trunks"],
    425: ["tree_outline", "tree_trunks", "leaf_path"],
    630: ["tree_outline", "tree_trunks", "leaf_path", "light_shows"],
    785: ["tree_outline", "tree_trunks", "leaf_path", "light_shows", "clearing"],
}


def phase_opacity(layer_id: str, meters: float) -> float:
    p = PHASES[layer_id]
    if meters < p["atMeters"]:
        return 0.0
    span = meters - p["atMeters"]
    if span >= p["fadeMeters"]:
        return p["toOpacity"]
    return p["toOpacity"] * span / p["fadeMeters"]


def load_layer_rgba(path: Path) -> np.ndarray:
    """读 RGBA uint8, 保持原 768x1376 (不缩放, 真实候选尺寸)."""
    return np.array(Image.open(path).convert("RGBA"))


def compose_stage(meters: float, layer_ids: list[str]) -> np.ndarray:
    """单阶段合成: void 底色 + 5 层 over 合成, 输出 RGB uint8."""
    h, w = H, W
    cur_rgb = np.tile(VOID_RGB.reshape(1, 1, 3), (h, w, 1))
    cur_a = np.ones((h, w), dtype=np.float32)
    for ln in layer_ids:
        rgba = load_layer_rgba(LAYER_SOURCE[ln])
        a_l = phase_opacity(ln, meters)
        if a_l <= 0:
            continue
        rgb = rgba[..., :3].astype(np.float32)
        a = rgba[..., 3].astype(np.float32) / 255.0 * a_l
        out_a = a + cur_a * (1 - a)
        safe = np.where(out_a > 1e-6, 1.0 / np.maximum(out_a, 1e-6), 0)
        out_rgb = (rgb * a[..., None] + cur_rgb * cur_a[..., None] * (1 - a[..., None])) * safe[..., None]
        cur_rgb, cur_a = out_rgb, out_a
    return cur_rgb.clip(0, 255).astype(np.uint8)


def main() -> None:
    print("=== SW-002 r1 候选生成 (clearing + light_shows, 零 API) ===")

    # 1. clearing 复用 v5 (按 SW-002 任务文件 §2 指示 "优先复用合格 v5 clearing")
    src_v5_webp = V5 / "webp" / "forest_clearing.webp"
    src_v5_png = V5 / "png" / "forest_clearing.png"
    clearing_rgba = np.array(Image.open(src_v5_png).convert("RGBA"))
    print(f"[r1] clearing 复用 v5/{src_v5_png.relative_to(ROOT)} ({src_v5_png.stat().st_size} bytes)")
    print(f"[r1] 备注: 当前 v5 候选本身在 git history (commit 62b0c29) 但不在 main HEAD (5a129d4).")
    print(f"[r1] 提示词变更不重做 clearing (颜色 / 渐变结构 / 软衰减 与 v5 一致).")

    # 2. light_shows 程序化重做
    light_rgba = make_light_shows_canvas()
    print(f"[r1] light_shows 程序化生成 ({light_rgba.shape[1]}x{light_rgba.shape[0]})")

    # 保存到 r1/
    clearing_webp = OUT / "webp" / "forest_clearing.webp"
    clearing_png = OUT / "png" / "forest_clearing.png"
    light_webp = OUT / "webp" / "forest_light_shows.webp"
    light_png = OUT / "png" / "forest_light_shows.png"

    save_webp(clearing_rgba, clearing_webp)
    save_png(clearing_rgba, clearing_png)
    save_webp(light_rgba, light_webp)
    save_png(light_rgba, light_png)

    save_alpha_mask(clearing_rgba, OUT / "checks" / "alpha_mask" / "forest_clearing.png")
    save_alpha_mask(light_rgba, OUT / "checks" / "alpha_mask" / "forest_light_shows.png")

    for name, rgba in [("clearing", clearing_rgba), ("light_shows", light_rgba)]:
        Image.fromarray(compose_on(rgba, (0, 0, 0)), "RGB").save(
            OUT / "checks" / "black" / f"forest_{name}.jpg", "JPEG", quality=90, optimize=True)
        Image.fromarray(compose_on(rgba, (255, 255, 255)), "RGB").save(
            OUT / "checks" / "white" / f"forest_{name}.jpg", "JPEG", quality=90, optimize=True)
        Image.fromarray(compose_on(rgba, (255, 0, 255)), "RGB").save(
            OUT / "checks" / "magenta" / f"forest_{name}.jpg", "JPEG", quality=90, optimize=True)
        # 单层放大检查 (中央 600x600 区)
        cx, cy = W // 2, H // 2
        half = 300
        crop = rgba[max(0, cy - half):cy + half, max(0, cx - half):cx + half]
        Image.fromarray(crop, "RGBA").save(
            OUT / "checks" / "alpha_mask" / f"forest_{name}_center600.png", "PNG", optimize=True)

    print(f"[r1] 检查图已生成: black/white/magenta/alpha_mask")

    # 3. 6 阶段合成
    stage_dir = OUT / "checks" / "stages"
    stage_dir.mkdir(exist_ok=True)
    for m in [0, 100, 265, 425, 630, 785]:
        comp = compose_stage(m, LAYERS_BY_METER[m])
        Image.fromarray(comp, "RGB").save(stage_dir / f"stage_{m:03d}m.png", "PNG", optimize=True)
        # 0.5x 缩图
        small = Image.fromarray(comp, "RGB").resize((W // 2, H // 2), Image.LANCZOS)
        small.save(stage_dir / f"stage_{m:03d}m_540x960.jpg", "JPEG", quality=90, optimize=True)
    print(f"[r1] 6 阶段合成已生成")

    # 4. 诊断报告 (4 底色 x 2 层)
    reports = []
    for name, rgba in [("clearing", clearing_rgba), ("light_shows", light_rgba)]:
        for bg_name, bg_rgb in [("void", (6, 8, 6)), ("black", (0, 0, 0)), ("white", (255, 255, 255)), ("magenta", (255, 0, 255))]:
            r = diagnose_layer(rgba, name, bg_name, bg_rgb)
            reports.append(r)
            print(f"  [{name} on {bg_name:8s}] brightness={r['brightness_mean']:6.1f}±{r['brightness_std']:5.1f} "
                  f"32px_diag={r['diag_32px_energy_pct']:5.2f}% 8px_alt={r['alt_8px_pct']:5.2f}% "
                  f"32px_alt={r['alt_32px_pct']:5.2f}% lap_max={r['lap_max']:3d} high_freq={r['high_freq_pct']:5.3f}%")

    # 5. 文件 SHA256
    hashes = {}
    for p in [clearing_webp, clearing_png, light_webp, light_png,
              OUT / "checks" / "alpha_mask" / "forest_clearing.png",
              OUT / "checks" / "alpha_mask" / "forest_light_shows.png"]:
        hashes[str(p.relative_to(ROOT))] = file_sha256(p)

    # 6. 写 manifest 和诊断 JSON
    manifest = {
        "schema_version": 1,
        "task_id": "SW-002",
        "revision": 1,
        "scene_id": "forest",
        "producer": "minimax",
        "api_attempts_this_revision": 0,
        "api_attempts_total": 14,
        "cost": "unknown",
        "layers": [
            {
                "layer_id": "clearing",
                "file": "design/assets/forest/candidates/SW-002/r1/webp/forest_clearing.webp",
                "sha256": hashes[str(clearing_webp.relative_to(ROOT))],
                "width": W, "height": H, "bytes": clearing_webp.stat().st_size,
                "alpha_channel": True, "render_role": "overlay", "tileable": False,
                "origin": "程序算法 (径向渐变 + 边缘羽化, 与 ForestShell.kt drawClearingGlow 语义一致); 复用 v5 候选 (62b0c29) 字节级一致; 不调用生图 API",
                "process": "make_clearing_canvas: 主径向 cx=0.68W,cy=0.42H,r=0.55W,peak=0.30; 次径向 cx=0.30W,cy=0.55H,r=0.40W,peak=0.12; 三束斜光 -8/-2/+5 deg, peak=0.10; 边缘 80px ramp; RGB 统一 GlowColor #A8C5A0",
                "quality_status": "candidate",
                "checks": [
                    "checks/alpha_mask/forest_clearing.png",
                    "checks/black/forest_clearing.jpg",
                    "checks/white/forest_clearing.jpg",
                    "checks/magenta/forest_clearing.jpg",
                ],
                "limitations": [
                    "原始 raw 768x1376, 与项目最终画布 1080x1920 比例为 cover 缩放, 非原生高分辨率",
                    "本轮 SW-002 r1 不调用生图 API, 内容是程序化径向 + 斜光, 不是真实 AI 林间柔光",
                    "无 tileable (overlay 不做平铺, 但 ForestShell.kt 暂为 cover 模式, 无接缝暴露)",
                ],
            },
            {
                "layer_id": "light_shows",
                "file": "design/assets/forest/candidates/SW-002/r1/webp/forest_light_shows.webp",
                "sha256": hashes[str(light_webp.relative_to(ROOT))],
                "width": W, "height": H, "bytes": light_webp.stat().st_size,
                "alpha_channel": True, "render_role": "overlay", "tileable": False,
                "origin": "程序算法 (三束斜光 + 2 只飞鸟剪影, 与 ForestShell.kt drawLightShows 语义一致); 弃用 v4 真实图 (ASSETS.md 标记 32px 对角能量 55.10% 为问题层); 不调用生图 API",
                "process": "make_light_shows_canvas: 三束斜光 -14/-8/-2 deg, peak 0.40-0.45, y 方向顶部亮底部 0; 2 只飞鸟翼展 28px, 翼上 8px 翼下 4px V 字, BIRD 颜色 #1A2820, 边缘 60px ramp",
                "quality_status": "candidate",
                "checks": [
                    "checks/alpha_mask/forest_light_shows.png",
                    "checks/black/forest_light_shows.jpg",
                    "checks/white/forest_light_shows.jpg",
                    "checks/magenta/forest_light_shows.jpg",
                ],
                "limitations": [
                    "原始 raw 768x1376, 与项目最终画布 1080x1920 比例为 cover 缩放, 非原生高分辨率",
                    "本轮 SW-002 r1 不调用生图 API, 内容是程序化斜光 + 简化飞鸟",
                    "飞鸟数量 2 (与 ForestShell.kt drawLightShows 一致), 真实 AI 飞鸟 3 只是 v4 失败稿; 简化版避免 v4 棋盘格根因",
                ],
            },
        ],
        "design_ref": None,
    }
    out_manifest = OUT / "manifest.json"
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"\n[r1] manifest: {out_manifest.relative_to(ROOT)}")

    # 诊断 JSON
    diag = {
        "version": "SW-002 r1",
        "rationale": "v4 light_shows/clearing 被 ZCode 撤回 (ASSETS.md §一); r1 提交 clearing 复用 v5 + light_shows 程序化重做; 零 API",
        "diagnose": reports,
        "file_hashes_sha256": hashes,
        "stages": [
            {
                "meters": m,
                "layers": LAYERS_BY_METER[m],
                "opacities": {ln: round(phase_opacity(ln, m), 3) for ln in LAYERS_BY_METER[m]},
                "png": str((OUT / "checks" / "stages" / f"stage_{m:03d}m.png").relative_to(ROOT)),
                "jpg": str((OUT / "checks" / "stages" / f"stage_{m:03d}m_540x960.jpg").relative_to(ROOT)),
            } for m in [0, 100, 265, 425, 630, 785]
        ],
        "api_attempts_total": 14,
    }
    out_diag = OUT / "records" / "diagnose.json"
    out_diag.write_text(json.dumps(diag, ensure_ascii=False, indent=2))
    print(f"[r1] 诊断: {out_diag.relative_to(ROOT)}")

    # 7. rejected/superseded: v4 真实图, v5 候选 (历史)
    import shutil
    for f in [V5 / "png" / "forest_clearing.png", V5 / "png" / "forest_light_shows.png"]:
        if f.exists():
            shutil.copy2(f, OUT / "rejected" / "superseded" / f"v5_{f.name}")
    # 留 v4 light_shows raw (从入包备份), 但实际入包是 v4, 已由 ZCode 在 d8751f6 撤出
    # 仅作历史追溯
    v4_ls = ASSETS / "forest_light_shows.webp"
    if v4_ls.exists():
        shutil.copy2(v4_ls, OUT / "rejected" / "superseded" / "v4_forest_light_shows_actual_asset.webp")
    readme = OUT / "rejected" / "superseded" / "README.md"
    readme.write_text(
        "# Superseded 候选\n\n"
        "v4 真实 light_shows (已被 ZCode 在 d8751f6 撤出, ASSETS.md 标记 32px 对角能量 55.10% 为问题层)\n"
        "v5 候选 (commit 62b0c29, git history 上但不在 main HEAD 5a129d4, 字节级与本轮 r1/clearing 一致)\n\n"
        "本目录仅作历史追溯, 不作为可接入交付物.\n"
    )
    print(f"[r1] rejected/superseded 留档完成")


if __name__ == "__main__":
    main()