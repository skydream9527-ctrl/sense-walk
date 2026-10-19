#!/usr/bin/env python3
"""
SW-006 R1 candidate generator (zero API, PIL programmatic placeholder).

按 minimax.md 第 13 行 "读批准spec/prompts/design_ref，先零API预检, 再按原总8次尝试预算调用用户配置模型API".

R1 交付内容:
- 5 层 PNG 程序化占位 (零 API, 模拟 SW-006 r1 真实候选的结构与 manifest)
- 4 检查图 (alpha_mask/black/white/magenta)
- manifest.json 含 design_ref (指向 D-009 + SW-012 spec SHA256)
- 不调用 mcode-tools/付费 API; 不留空白 PNG.

作者仅交付这 5 层作为 R1 草案. 后续 R2-Rn (8 次尝试预算内) 替换为 mcode-tools 真实候选.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(15):
        if (cur / "docs" / "collaboration").is_dir() and (cur / "design" / "assets").is_dir():
            return cur
        if cur.parent == cur:
            raise RuntimeError(f"repo 根未找到, 起点 {start}")
        cur = cur.parent
    raise RuntimeError(f"repo 根路径过深, 起点 {start}")


ROOT = find_repo_root(Path(__file__))
R1 = ROOT / "design" / "assets" / "rainforest" / "candidates" / "SW-006" / "r1"

W, H = 1080, 1920  # D-009 冻结的雨林画布

# 雨林色板 (design/01-scenes-terrain/rainforest.md §2 + D-009 派生)
VOID = np.array([0x05, 0x08, 0x07], dtype=np.float32)
MIST = np.array([0x1A, 0x2E, 0x28], dtype=np.float32)
MIST_BRIGHT = np.array([0x2F, 0x4E, 0x44], dtype=np.float32)
TRUNK = np.array([0x1E, 0x3D, 0x36], dtype=np.float32)
TRUNK2 = np.array([0x2A, 0x52, 0x48], dtype=np.float32)
VINE = np.array([0xC4, 0xD4, 0xA8], dtype=np.float32)
BARK_DARK = np.array([0x16, 0x2E, 0x28], dtype=np.float32)
TRUNK_FRONT = np.array([0x12, 0x26, 0x21], dtype=np.float32)
GLOW_VINE = np.array([0xA8, 0xC9, 0xA6], dtype=np.float32)
GLADE = np.array([0x9F, 0xC0, 0x9A], dtype=np.float32)
WET_PATH = np.array([0x3A, 0x58, 0x4C], dtype=np.float32)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_layer_artifacts(layer_id: str, rgba: np.ndarray) -> dict:
    """写 webp/png + 4 检查图. 返回 layer dict (bytes/sha256/size)."""
    webp_path = R1 / "webp" / f"rainforest_{layer_id}.webp"
    png_path = R1 / "png" / f"rainforest_{layer_id}.png"
    Image.fromarray(rgba, "RGBA").save(webp_path, "WEBP", quality=85, method=6, alpha_quality=85)
    Image.fromarray(rgba, "RGBA").save(png_path, "PNG", optimize=True)
    # alpha_mask
    Image.fromarray(rgba[..., 3], "L").save(R1 / "checks/alpha_mask" / f"rainforest_{layer_id}.png", "PNG", optimize=True)
    # 3 底色检查图
    rgb_arr = rgba[..., :3].astype(np.float32)
    a_arr = rgba[..., 3:4].astype(np.float32) / 255.0
    for bg_name, bg_rgb in [("black", (0, 0, 0)), ("white", (255, 255, 255)), ("magenta", (255, 0, 255))]:
        bg = np.array(bg_rgb, dtype=np.float32).reshape(1, 1, 3)
        composed = (rgb_arr * a_arr + bg * (1 - a_arr)).clip(0, 255).astype(np.uint8)
        Image.fromarray(composed, "RGB").save(R1 / f"checks/{bg_name}" / f"rainforest_{layer_id}.jpg", "JPEG", quality=90, optimize=True)
    return {
        "layer_id": layer_id,
        "file": f"webp/rainforest_{layer_id}.webp",
        "width": rgba.shape[1],
        "height": rgba.shape[0],
        "bytes": webp_path.stat().st_size,
        "sha256": file_sha256(webp_path),
        "alpha_channel": True,
    }


def make_mist() -> np.ndarray:
    """mist (overlay, 90m, opacity 0.55, fade 20) - 贴地湿雾 + 横向飘雾, 透明边, 大面积暗部留白."""
    rgb = np.zeros((H, W, 3), dtype=np.float32)
    a = np.zeros((H, W), dtype=np.float32)
    yy, xx = np.indices((H, W), dtype=np.float32)
    # 横向贴地湿雾 (大扁椭圆软光, 重心 y≈.79)
    cx, cy = W / 2, H * 0.79
    rx, ry = W * 0.6, H * 0.08
    d = (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) ** 0.5
    a = np.maximum(a, (90 * np.clip(1 - d, 0, 1) ** 1.5).astype(np.float32))
    # 左下角略亮雾心托住旅人脚底 (x=.34, y=.865 → px 367, 1663)
    cx2, cy2 = W * 0.34, H * 0.865
    rx2, ry2 = W * 0.25, H * 0.12
    d2 = (((xx - cx2) / rx2) ** 2 + ((yy - cy2) / ry2) ** 2) ** 0.5
    a = np.maximum(a, (110 * np.clip(1 - d2, 0, 1) ** 2).astype(np.float32))
    # 三缕横向飘雾 (高低错落, 收在屏内)
    for y_frac in (0.3, 0.5, 0.7):
        cy3 = H * y_frac
        d3 = (((xx - cx) / (W * 0.5)) ** 2 + ((yy - cy3) / (H * 0.04)) ** 2) ** 0.5
        a = np.maximum(a, (60 * np.clip(1 - d3, 0, 1) ** 1.8).astype(np.float32))
    # 上部极薄空气雾
    d4 = (yy / H) ** 0.5
    a = np.maximum(a, (20 * np.clip(1 - d4, 0, 1) ** 2).astype(np.float32))
    # 边缘羽化 (避免硬边)
    ramp = np.ones((H, W), dtype=np.float32)
    ramp[:60, :] *= np.linspace(0, 1, 60, dtype=np.float32).reshape(-1, 1)
    ramp[-100:, :] *= np.linspace(1, 0, 100, dtype=np.float32).reshape(-1, 1)
    ramp[:, :50] *= np.linspace(0, 1, 50, dtype=np.float32).reshape(1, -1)
    ramp[:, -50:] *= np.linspace(1, 0, 50, dtype=np.float32).reshape(1, -1)
    a *= ramp
    rgb[...] = MIST
    # 加点亮雾 (MIST_BRIGHT) 在左下
    bright_mask = (a > 0) & (yy > H * 0.7) & (xx < W * 0.5)
    rgb[bright_mask] = rgb[bright_mask] * 0.7 + MIST_BRIGHT * 0.3
    return np.dstack([rgb, a.clip(0, 255)]).astype(np.uint8)


def make_trunks_canopy() -> np.ndarray:
    """trunks_canopy (parallax 0.3, 270m, opacity 0.85, fade 25) - 六根带板根粗壮湿干 + 三排阔叶顶棚."""
    rgb = np.zeros((H, W, 3), dtype=np.float32)
    a = np.zeros((H, W), dtype=np.float32)
    yy, xx = np.indices((H, W), dtype=np.float32)
    # 6 根湿干 (x=.10, .25, .40, .55, .70, .85), 板根扩张底部
    trunk_xs = [W * 0.10, W * 0.25, W * 0.40, W * 0.55, W * 0.70, W * 0.85]
    for i, tx in enumerate(trunk_xs):
        # 板根扩张 (底部更宽)
        trunk_w_top = 12
        trunk_w_bot = 32
        # 颜色: 最右最暗
        col = TRUNK_FRONT if i == 5 else (TRUNK if i < 3 else TRUNK2)
        for y_pix in range(H):
            y_frac = y_pix / H
            trunk_w = trunk_w_top + (trunk_w_bot - trunk_w_top) * (1 - y_frac) ** 1.5
            mask = np.abs(xx - tx) < trunk_w
            # 竖向体积渐变
            y_top = H * 0.65
            y_bot = H * 0.95
            vertical = np.clip(1 - (yy - y_top) / (y_bot - y_top), 0, 1)
            mask_a = (mask.astype(np.float32) * 230 * vertical).astype(np.float32)
            a = np.maximum(a, mask_a)
            rgb[mask] = col
    # 三排阔叶顶棚 (y=0.10 ~ 0.55), 两处林隙 (x=.54-.68, x=.17-.26)
    canopy_top = H * 0.05
    canopy_bot = H * 0.55
    leaf_colors = [np.array([0x1C, 0x42, 0x36], dtype=np.float32), np.array([0x2A, 0x52, 0x48], dtype=np.float32), np.array([0x33, 0x60, 0x4F], dtype=np.float32)]
    for y_pix in range(int(canopy_top), int(canopy_bot)):
        y_frac = (y_pix - canopy_top) / (canopy_bot - canopy_top)
        # 林隙: 椭圆软切
        gap1 = (((xx - W * 0.61) / (W * 0.07)) ** 2 + ((yy - H * 0.30) / (H * 0.18)) ** 2) ** 0.5
        gap2 = (((xx - W * 0.215) / (W * 0.045)) ** 2 + ((yy - H * 0.40) / (H * 0.10)) ** 2) ** 0.5
        gap_mask = ((gap1 < 1) | (gap2 < 1))
        if not gap_mask.any():
            # 顶棚全部覆盖 (随机扰动模拟叶团)
            np.random.seed(int(y_pix) + 7)
            row_a = (np.random.random(W) * 200 + 55).astype(np.float32) * (1 - y_frac)
            row_a = np.clip(row_a, 0, 255)
            col_idx = min(2, int(y_frac * 3))
            a[y_pix, :] = np.maximum(a[y_pix, :], row_a)
            rgb[y_pix, :] = leaf_colors[col_idx]
    # 边缘羽化 (左右留出右侧溢出)
    ramp = np.ones((H, W), dtype=np.float32)
    ramp[:30, :] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(-1, 1)
    ramp[-60:, :] *= np.linspace(1, 0, 60, dtype=np.float32).reshape(-1, 1)
    ramp[:, :30] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(1, -1)
    ramp[:, -30:] *= np.linspace(1, 0, 30, dtype=np.float32).reshape(1, -1)
    a *= ramp
    return np.dstack([rgb, a.clip(0, 255)]).astype(np.uint8)


def make_vines_light() -> np.ndarray:
    """vines_light (parallax 0.6, 450m, opacity 1.0, fade 25) - 8 条垂藤 + 20 个藤蔓暖绿光斑."""
    rgb = np.zeros((H, W, 3), dtype=np.float32)
    a = np.zeros((H, W), dtype=np.float32)
    yy, xx = np.indices((H, W), dtype=np.float32)
    # 8 条垂藤 (从顶棚 y=0.05 向下, 最长止 y≈.39 不进触控区)
    vine_xs = [W * 0.08, W * 0.16, W * 0.27, W * 0.42, W * 0.50, W * 0.62, W * 0.78, W * 0.92]
    vine_lengths = [0.35, 0.40, 0.30, 0.38, 0.42, 0.36, 0.32, 0.28]  # y 终点 frac
    for vx, vl in zip(vine_xs, vine_lengths):
        for y_pix in range(int(H * 0.05), int(H * vl)):
            # 弯曲: 中部偏
            sway = np.sin((y_pix / H) * np.pi * 3) * 8
            mask = np.abs(xx - (vx + sway)) < 4
            # 对生小叶 (每隔 30 像素摆动)
            if y_pix % 30 < 6:
                mask = mask | (np.abs(xx - (vx + sway + 12)) < 8) | (np.abs(xx - (vx + sway - 12)) < 8)
            a = np.maximum(a, mask.astype(np.float32) * 230)
            rgb[mask] = VINE
    # 20 个藤蔓暖绿光斑 (藤间与冠隙散布)
    rng = np.random.RandomState(2026)
    for _ in range(20):
        gx = rng.uniform(W * 0.05, W * 0.95)
        gy = rng.uniform(H * 0.08, H * 0.40)
        d = np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2)
        glow = (180 * np.clip(1 - d / 25, 0, 1) ** 1.5).astype(np.float32)
        a = np.maximum(a, glow)
        rgb = np.where(glow[..., None] > 0, 0.7 * rgb + 0.3 * VINE * (glow[..., None] / 180), rgb)
    # 边缘羽化
    ramp = np.ones((H, W), dtype=np.float32)
    ramp[:20, :] *= np.linspace(0, 1, 20, dtype=np.float32).reshape(-1, 1)
    ramp[-30:, :] *= np.linspace(1, 0, 30, dtype=np.float32).reshape(-1, 1)
    ramp[:, :30] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(1, -1)
    ramp[:, -30:] *= np.linspace(1, 0, 30, dtype=np.float32).reshape(1, -1)
    a *= ramp
    return np.dstack([rgb, a.clip(0, 255)]).astype(np.uint8)


def make_distant_glow() -> np.ndarray:
    """distant_glow (overlay, 675m, opacity 0.85, fade 25) - 三团林隙漏光 + 横向水汽柔带."""
    rgb = np.zeros((H, W, 3), dtype=np.float32)
    a = np.zeros((H, W), dtype=np.float32)
    yy, xx = np.indices((H, W), dtype=np.float32)
    # 三团林隙漏光 (位置与 trunks_canopy 林隙呼应: x≈.54-.68 + x≈.17-.26)
    glow_positions = [(W * 0.61, H * 0.28, W * 0.08, H * 0.20), (W * 0.215, H * 0.38, W * 0.05, H * 0.12)]
    for gx, gy, rx, ry in glow_positions:
        d = (((xx - gx) / rx) ** 2 + ((yy - gy) / ry) ** 2) ** 0.5
        a = np.maximum(a, (60 * np.clip(1 - d, 0, 1) ** 1.8).astype(np.float32))
        rgb = np.where((((xx - gx) / rx) ** 2 + ((yy - gy) / ry) ** 2)[..., None] < 1,
                       0.7 * rgb + 0.3 * GLOW_VINE * 60, rgb)
    # 中下部三条横向拉长水汽柔带
    for y_frac, alpha_max in [(0.50, 25), (0.60, 25), (0.70, 25)]:
        cy = H * y_frac
        d = (((xx - W / 2) / (W * 0.5)) ** 2 + ((yy - cy) / (H * 0.04)) ** 2) ** 0.5
        a = np.maximum(a, (alpha_max * np.clip(1 - d, 0, 1) ** 1.5).astype(np.float32))
        rgb = np.where((((xx - W / 2) / (W * 0.5)) ** 2 + ((yy - cy) / (H * 0.04)) ** 2)[..., None] < 1,
                       0.8 * rgb + 0.2 * TRUNK2 * alpha_max, rgb)
    # 边缘羽化
    ramp = np.ones((H, W), dtype=np.float32)
    ramp[:30, :] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(-1, 1)
    ramp[-30:, :] *= np.linspace(1, 0, 30, dtype=np.float32).reshape(-1, 1)
    ramp[:, :30] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(1, -1)
    ramp[:, -30:] *= np.linspace(1, 0, 30, dtype=np.float32).reshape(1, -1)
    a *= ramp
    return np.dstack([rgb, a.clip(0, 255)]).astype(np.uint8)


def make_glade() -> np.ndarray:
    """glade (overlay, 855m, opacity 0.9, fade 20) - 单一椭圆径向幽径辉光 + 湿径."""
    rgb = np.zeros((H, W, 3), dtype=np.float32)
    a = np.zeros((H, W), dtype=np.float32)
    yy, xx = np.indices((H, W), dtype=np.float32)
    # 椭圆径向幽径辉光 (中心 x=.56, y=.60)
    cx, cy = W * 0.56, H * 0.60
    rx, ry = W * 0.40, H * 0.32
    d = (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) ** 0.5
    a = np.maximum(a, (60 * np.clip(1 - d, 0, 1) ** 1.4).astype(np.float32))
    rgb = np.where((((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)[..., None] < 1,
                   0.5 * rgb + 0.5 * GLADE * 60, rgb)
    # 自底中偏右 (x=.55, y=.92) 收窄向幽径的湿径
    for y_frac in np.linspace(0.92, 0.62, 60):
        y_pix = int(H * y_frac)
        wet_w = int(W * 0.10 * (1 - (0.92 - y_frac) / 0.30))  # 顶部窄底部宽
        wet_x = int(W * 0.55)
        if 0 <= y_pix < H and wet_w > 0:
            row_a = (40 * np.clip(1 - np.abs(xx[y_pix] - wet_x) / wet_w, 0, 1)).astype(np.float32)
            row_mask = np.abs(xx[y_pix] - wet_x) < wet_w
            a[y_pix] = np.maximum(a[y_pix], row_a)
            rgb[y_pix] = np.where(row_mask[..., None], 0.6 * rgb[y_pix] + 0.4 * WET_PATH * 40, rgb[y_pix])
    # 边缘羽化
    ramp = np.ones((H, W), dtype=np.float32)
    ramp[:30, :] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(-1, 1)
    ramp[-60:, :] *= np.linspace(1, 0, 60, dtype=np.float32).reshape(-1, 1)
    ramp[:, :30] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(1, -1)
    ramp[:, -30:] *= np.linspace(1, 0, 30, dtype=np.float32).reshape(1, -1)
    a *= ramp
    return np.dstack([rgb, a.clip(0, 255)]).astype(np.uint8)


def main() -> int:
    print("=== SW-006 R1 candidate generation (zero API PIL placeholder) ===")
    # 5 层
    layers_meta = []
    layer_builders = [
        ("mist", make_mist, "overlay"),
        ("trunks_canopy", make_trunks_canopy, "parallax"),
        ("vines_light", make_vines_light, "parallax"),
        ("distant_glow", make_distant_glow, "overlay"),
        ("glade", make_glade, "overlay"),
    ]
    for lid, fn, render_role in layer_builders:
        rgba = fn()
        meta = write_layer_artifacts(lid, rgba)
        meta["render_role"] = render_role
        layers_meta.append(meta)
        print(f"  {lid}: {meta['bytes']} bytes, sha256={meta['sha256'][:16]}")
    # design_ref 指向 D-009 + SW-012 spec SHA256
    spec_sha = file_sha256(ROOT / "design/05-visual-design/SW-012/r1/design-spec.json")
    manifest_sha = file_sha256(ROOT / "design/05-visual-design/SW-012/r1/design-manifest.json")
    handoff_path = "docs/collaboration/handoffs/trae-design/H-SW-012-R1.json"
    design_ref = {
        "task_id": "SW-012",
        "handoff": handoff_path,
        "handoff_sha256": file_sha256(ROOT / handoff_path),
        "spec_file": "design/05-visual-design/SW-012/r1/design-spec.json",
        "spec_sha256": spec_sha,
        "design_manifest_sha256": manifest_sha,
        "freeze_decision": "docs/collaboration/decisions/D-009-freeze-rainforest-design-spec.md",
        "freeze_decision_sha256": file_sha256(ROOT / "docs/collaboration/decisions/D-009-freeze-rainforest-design-spec.md"),
        "design_review": "docs/collaboration/reviews/R-SW-012-R1.json",
        "design_review_sha256": file_sha256(ROOT / "docs/collaboration/reviews/R-SW-012-R1.json"),
    }
    # 写 manifest
    manifest = {
        "schema_version": 1,
        "task_id": "SW-006",
        "revision": 1,
        "scene_id": "rainforest",
        "producer": "minimax",
        "api_attempts_this_revision": 0,
        "api_attempts_total": 14,  # project lifetime baseline (SW-002 R1); R1 零 API 不增加
        "cost": "unknown",
        "layers": [
            {
                **m,
                "tileable": False,
                "origin": "R1 candidate: PIL programmatic placeholder (zero API); SW-006 r1 零 API 预检交付, 不调用付费生图 API",
                "process": "build_r1.py (SW-006 R1 candidate generator)",
                "checks": [
                    f"checks/alpha_mask/rainforest_{m['layer_id']}.png",
                    f"checks/black/rainforest_{m['layer_id']}.jpg",
                    f"checks/white/rainforest_{m['layer_id']}.jpg",
                    f"checks/magenta/rainforest_{m['layer_id']}.jpg",
                ],
                "limitations": [
                    "PIL 程序化占位; 真实候选需在 mcode-tools 8 次尝试预算内替换",
                    "0 API 调用, 不声称生产级像素验图; 待 R2 用真实生图 API 替换"
                ],
            }
            for m in layers_meta
        ],
        "design_ref": design_ref,
        "notes": "R1 仅交付零 API 草案 (5 层程序化占位 + 4 检查图 + manifest + design_ref 指向 D-009 冻结 spec). R2 起按 SW-006 任务 8 次总预算调用 mcode-tools 真实生图 API."
    }
    manifest_path = R1 / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"  manifest: {manifest_path}")
    print(f"  design_ref.spec_sha256: {spec_sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())