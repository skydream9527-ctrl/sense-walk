#!/usr/bin/env python3
"""
SW-014 fixture 生成器 - 用自制小样本覆盖预检脚本的合法/非法场景.

不调用生图 API; 全部用 PIL 程序化生成. SW-014 任务"使用明确标为 fixture 的自制小样本".

输出到 ../fixtures/ 下:
- manifest_ok/         合法: 5 层 + 透明 + 预算内 + tileable=false + 4 底色检查图齐
- manifest_oversize/   1 层 > 400KB 字节
- manifest_wrong_hash/ 1 层实际 SHA256 与 manifest 不一致
- manifest_missing/    1 层实际文件不存在
- manifest_not_tileable/ 1 层 tileable=true 但 manifest 没 tileable 检查图
- manifest_no_design/  manifest 缺 design_ref (用于测缺设计的报错)

每个 fixture 目录都有:
- manifest.json
- webp/forest_*.webp
- checks/black/forest_*.jpg
- checks/white/forest_*.jpg
- checks/magenta/forest_*.jpg
- checks/alpha_mask/forest_*.png
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]  # SW-014/r1/
FIX = ROOT / "fixtures"


# 雨林色板 (rainforest.md §2, 不替 Trae 决定, 仅 fixture 用)
VOID = np.array([0x05, 0x08, 0x07], dtype=np.float32)
MIST = np.array([0x1A, 0x2E, 0x28], dtype=np.float32)
TRUNK = np.array([0x1E, 0x3D, 0x36], dtype=np.float32)
TRUNK2 = np.array([0x2A, 0x52, 0x48], dtype=np.float32)
VINE = np.array([0xC4, 0xD4, 0xA8], dtype=np.float32)

LAYER_IDS = ["mist", "trunks_canopy", "vines_light", "far_glow", "clearing_glow"]


def make_layer_png(layer_id: str, w: int = 768, h: int = 1376) -> np.ndarray:
    """生成小样本 320x568 RGBA fixture (雨林色板, 透明底, 含主体色)."""
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    a = np.zeros((h, w), dtype=np.float32)
    yy, xx = np.indices((h, w), dtype=np.float32)
    if layer_id == "mist":
        # 软雾径向
        cx, cy, r = w / 2, h * 0.5, w * 0.6
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        a = (0.55 * np.clip(1 - d / r, 0, 1) ** 1.5).astype(np.float32)
        rgb[...] = MIST
    elif layer_id == "trunks_canopy":
        # 树干竖条
        for xc in [w * 0.2, w * 0.4, w * 0.6, w * 0.8]:
            trunk_w = 16
            mask = np.abs(xx - xc) < trunk_w
            a = np.maximum(a, mask.astype(np.float32) * 0.85)
        rgb[...] = TRUNK
    elif layer_id == "vines_light":
        # 藤蔓光斑 (3 点)
        for cx, cy in [(w * 0.3, h * 0.3), (w * 0.6, h * 0.5), (w * 0.7, h * 0.7)]:
            d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            a = np.maximum(a, 1.0 * np.clip(1 - d / 30, 0, 1) ** 2)
        rgb[...] = VINE
    elif layer_id == "far_glow":
        # 远方透光
        cx, cy, r = w * 0.5, h * 0.3, w * 0.4
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        a = (0.7 * np.clip(1 - d / r, 0, 1) ** 1.3).astype(np.float32)
        rgb[...] = TRUNK2
    elif layer_id == "clearing_glow":
        # 幽径空地微光
        cx, cy, r = w * 0.5, h * 0.6, w * 0.5
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        a = (0.5 * np.clip(1 - d / r, 0, 1) ** 1.4).astype(np.float32)
        rgb[...] = VINE
    # 边缘羽化
    ramp = np.ones((h, w), dtype=np.float32)
    ramp[:30, :] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(-1, 1)
    ramp[-30:, :] *= np.linspace(1, 0, 30, dtype=np.float32).reshape(-1, 1)
    ramp[:, :30] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(1, -1)
    ramp[:, -30:] *= np.linspace(1, 0, 30, dtype=np.float32).reshape(1, -1)
    a *= ramp
    return np.dstack([rgb, a * 255]).clip(0, 255).astype(np.uint8)


def write_layer_artifacts(layer_id: str, out_dir: Path, rgba: np.ndarray) -> dict:
    """写 webp/png + 4 底色检查图 + alpha 蒙版. 返回 layer dict (用于 manifest)."""
    webp_path = out_dir / "webp" / f"rainforest_{layer_id}.webp"
    png_path = out_dir / "png" / f"rainforest_{layer_id}.png"
    Image.fromarray(rgba, "RGBA").save(webp_path, "WEBP", quality=85, method=6, alpha_quality=85)
    Image.fromarray(rgba, "RGBA").save(png_path, "PNG", optimize=True)
    Image.fromarray(rgba[..., 3], "L").save(out_dir / "checks" / "alpha_mask" / f"rainforest_{layer_id}.png", "PNG", optimize=True)
    for bg_name, bg_rgb in [("black", (0, 0, 0)), ("white", (255, 255, 255)), ("magenta", (255, 0, 255))]:
        rgb = rgba[..., :3].astype(np.float32)
        a = rgba[..., 3:4].astype(np.float32) / 255.0
        bg = np.array(bg_rgb, dtype=np.float32).reshape(1, 1, 3)
        composed = (rgb * a + bg * (1 - a)).clip(0, 255).astype(np.uint8)
        Image.fromarray(composed, "RGB").save(out_dir / "checks" / bg_name / f"rainforest_{layer_id}.jpg", "JPEG", quality=90, optimize=True)
    return {
        "layer_id": layer_id,
        "file": f"webp/rainforest_{layer_id}.webp",
        "width": rgba.shape[1], "height": rgba.shape[0],
        "bytes": webp_path.stat().st_size,
        "alpha_channel": True,
        "render_role": "overlay" if layer_id in ("vines_light", "far_glow", "clearing_glow") else "parallax",
        "tileable": False,
    }


def build_manifest(out_dir: Path, layers: list[dict], design_ref=None, fake_hash_layer: str = None) -> None:
    import hashlib
    for layer in layers:
        if "sha256" not in layer:
            p = out_dir / layer["file"]
            layer["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    if fake_hash_layer:
        for layer in layers:
            if layer["layer_id"] == fake_hash_layer:
                layer["sha256"] = "0" * 64
                break
    manifest = {
        "schema_version": 1,
        "task_id": "SW-006",
        "revision": 1,
        "scene_id": "rainforest",
        "producer": "minimax",
        "api_attempts_this_revision": 0,
        "api_attempts_total": 0,
        "cost": "unknown",
        "layers": layers,
        "design_ref": design_ref,
    }
    for layer in manifest["layers"]:
        layer["origin"] = "fixture (自制小样本, 非雨林正式图)"
        layer["process"] = "SW-014 gen_fixtures.py 程序化生成"
        layer["quality_status"] = "fixture"
        layer["checks"] = [
            f"checks/alpha_mask/rainforest_{layer['layer_id']}.png",
            f"checks/black/rainforest_{layer['layer_id']}.jpg",
            f"checks/white/rainforest_{layer['layer_id']}.jpg",
            f"checks/magenta/rainforest_{layer['layer_id']}.jpg",
        ]
        layer["limitations"] = ["fixture: 用于 SW-014 预检脚本验证, 不作为雨林正式图"]
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))


def gen_manifest_ok() -> None:
    out = FIX / "manifest_ok"
    (out / "webp").mkdir(parents=True, exist_ok=True)
    (out / "png").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "black").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "white").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "magenta").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "alpha_mask").mkdir(parents=True, exist_ok=True)
    layers = [write_layer_artifacts(lid, out, make_layer_png(lid)) for lid in LAYER_IDS]
    design_ref = {
        "task_id": "SW-012",
        "handoff": "docs/collaboration/handoffs/trae-design/H-SW-012-R1.json",
        "spec_file": "design/05-visual-design/SW-012/r1/spec.md",
        "spec_sha256": "PENDING_SW012_APPROVAL",
    }
    build_manifest(out, layers, design_ref=design_ref)


def gen_manifest_oversize() -> None:
    """1 层 > 400KB (bytes 字段虚报)."""
    out = FIX / "manifest_oversize"
    (out / "webp").mkdir(parents=True, exist_ok=True)
    (out / "png").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "black").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "white").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "magenta").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "alpha_mask").mkdir(parents=True, exist_ok=True)
    layers = [write_layer_artifacts(lid, out, make_layer_png(lid)) for lid in LAYER_IDS]
    # 篡改 mist bytes 字段
    for layer in layers:
        if layer["layer_id"] == "mist":
            layer["bytes"] = 500_000  # 实际文件 ~几 KB
    build_manifest(out, layers, design_ref=None)


def gen_manifest_wrong_hash() -> None:
    """1 层实际 hash 与 manifest 不一致."""
    out = FIX / "manifest_wrong_hash"
    (out / "webp").mkdir(parents=True, exist_ok=True)
    (out / "png").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "black").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "white").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "magenta").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "alpha_mask").mkdir(parents=True, exist_ok=True)
    layers = [write_layer_artifacts(lid, out, make_layer_png(lid)) for lid in LAYER_IDS]
    build_manifest(out, layers, design_ref=None, fake_hash_layer="vines_light")


def gen_manifest_missing() -> None:
    """1 层 webp 文件不存在."""
    out = FIX / "manifest_missing"
    (out / "webp").mkdir(parents=True, exist_ok=True)
    (out / "png").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "black").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "white").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "magenta").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "alpha_mask").mkdir(parents=True, exist_ok=True)
    layers = [write_layer_artifacts(lid, out, make_layer_png(lid)) for lid in LAYER_IDS]
    # 先 build manifest (会算 SHA), 再删除 far_glow webp 触发"file 不存在"
    build_manifest(out, layers, design_ref=None)
    (out / "webp" / "rainforest_far_glow.webp").unlink()


def gen_manifest_not_tileable() -> None:
    """1 层 tileable=true 但缺 tileable checks (stages / seamless)."""
    out = FIX / "manifest_not_tileable"
    (out / "webp").mkdir(parents=True, exist_ok=True)
    (out / "png").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "black").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "white").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "magenta").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "alpha_mask").mkdir(parents=True, exist_ok=True)
    layers = [write_layer_artifacts(lid, out, make_layer_png(lid)) for lid in LAYER_IDS]
    # trunks_canopy 标 tileable=true 但不写 tileable checks
    for layer in layers:
        if layer["layer_id"] == "trunks_canopy":
            layer["tileable"] = True
    build_manifest(out, layers, design_ref=None)


def gen_manifest_no_design() -> None:
    """缺 design_ref (用于测 dry-run 拒绝)."""
    out = FIX / "manifest_no_design"
    (out / "webp").mkdir(parents=True, exist_ok=True)
    (out / "png").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "black").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "white").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "magenta").mkdir(parents=True, exist_ok=True)
    (out / "checks" / "alpha_mask").mkdir(parents=True, exist_ok=True)
    layers = [write_layer_artifacts(lid, out, make_layer_png(lid)) for lid in LAYER_IDS]
    build_manifest(out, layers, design_ref=None)


def main() -> None:
    print("=== SW-014 fixture 生成 ===")
    for fn in [gen_manifest_ok, gen_manifest_oversize, gen_manifest_wrong_hash,
               gen_manifest_missing, gen_manifest_not_tileable, gen_manifest_no_design]:
        name = fn.__name__.replace("gen_", "")
        fn()
        out = FIX / name
        manifest = json.loads((out / "manifest.json").read_text())
        print(f"  {name}: {len(manifest['layers'])} 层, total bytes={sum(l['bytes'] for l in manifest['layers'])}")
    print(f"\nfixture root: {FIX.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()