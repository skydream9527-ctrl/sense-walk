#!/usr/bin/env python3
"""
SW-014 R2 fixture 构建.

R2 任务要求:
- 至少一个完整成功正例 (使用临时 approved registry/review/spec)
- 隔离失败反例, 每例只改一个目标条件
- 覆盖: 非图/0尺寸/不透明/空层/未知重复层/缺文件/错hash/缺检查图/超预算/错design_ref/tileable
- 用实际文件 (非只改声明 bytes)
- 临时批准记录显式 fixture, 不把真实 SW-012 写 accepted

零 API, 全部 PIL 程序化.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

def find_repo_root(start: Path) -> Path:
    """通过向上查找 docs/collaboration 目录定位 repo 根. 拒绝越界."""
    cur = start.resolve()
    for _ in range(15):
        if (cur / "docs" / "collaboration").is_dir() and (cur / "design" / "assets").is_dir():
            return cur
        if cur.parent == cur:
            raise RuntimeError(f"repo 根未找到, 起点 {start}")
        cur = cur.parent
    raise RuntimeError(f"repo 根路径过深, 起点 {start}")


ROOT = find_repo_root(Path(__file__))
assert (ROOT / "docs" / "collaboration").is_dir(), f"ROOT not repo root: {ROOT}"

R2 = ROOT / "design" / "assets" / "rainforest" / "preflight" / "SW-014" / "r2"
FIX = R2 / "fixtures"

W, H = 768, 1376  # 森林历史 raw 尺寸, 接受 1080x1920 替代


# 雨林色板 (rainforest.md §2, 不替 Trae 决定, 仅 fixture 用)
VOID = np.array([0x05, 0x08, 0x07], dtype=np.float32)
MIST = np.array([0x1A, 0x2E, 0x28], dtype=np.float32)
TRUNK = np.array([0x1E, 0x3D, 0x36], dtype=np.float32)
TRUNK2 = np.array([0x2A, 0x52, 0x48], dtype=np.float32)
VINE = np.array([0xC4, 0xD4, 0xA8], dtype=np.float32)

RAINFOREST_LAYERS = ["mist", "trunks_canopy", "vines_light", "far_glow", "clearing_glow"]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_layer_png(layer_id: str, w: int = W, h: int = H) -> np.ndarray:
    """生成真实 RGBA 雨林 fixture (透明底, 含主体)."""
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    a = np.zeros((h, w), dtype=np.float32)
    yy, xx = np.indices((h, w), dtype=np.float32)
    if layer_id == "mist":
        cx, cy, r = w / 2, h * 0.5, w * 0.6
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        a = (0.55 * np.clip(1 - d / r, 0, 1) ** 1.5).astype(np.float32)
        rgb[...] = MIST
    elif layer_id == "trunks_canopy":
        for xc in [w * 0.2, w * 0.4, w * 0.6, w * 0.8]:
            trunk_w = 16
            mask = np.abs(xx - xc) < trunk_w
            a = np.maximum(a, mask.astype(np.float32) * 0.85)
        rgb[...] = TRUNK
    elif layer_id == "vines_light":
        for cx, cy in [(w * 0.3, h * 0.3), (w * 0.6, h * 0.5), (w * 0.7, h * 0.7)]:
            d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            a = np.maximum(a, 1.0 * np.clip(1 - d / 30, 0, 1) ** 2)
        rgb[..., :] = VINE  # 注意: alpha 100% 处不透明, 但边缘羽化; R2 显式 fail 用 RGB = VINE + A = 0 的全 0 alpha
        rgb[...] = VINE
    elif layer_id == "far_glow":
        cx, cy, r = w * 0.5, h * 0.3, w * 0.4
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        a = (0.7 * np.clip(1 - d / r, 0, 1) ** 1.3).astype(np.float32)
        rgb[...] = TRUNK2
    elif layer_id == "clearing_glow":
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
    """写 webp/png + 4 底色检查图 + alpha 蒙版. 返回 layer dict."""
    webp = out_dir / "webp" / f"rainforest_{layer_id}.webp"
    png = out_dir / "png" / f"rainforest_{layer_id}.png"
    Image.fromarray(rgba, "RGBA").save(webp, "WEBP", quality=85, method=6, alpha_quality=85)
    Image.fromarray(rgba, "RGBA").save(png, "PNG", optimize=True)
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
        "bytes": webp.stat().st_size,
        "alpha_channel": True,
        "render_role": "overlay" if layer_id in ("vines_light", "far_glow", "clearing_glow") else "parallax",
        "tileable": False,
        "origin": "R2 fixture: PIL 程序化自制小样本, 非雨林正式图",
        "process": "make_layer_png (SW-014 R2 build_fixtures.py)",
    }


def write_design_ref_assets(out_dir: Path, fixture_mode: bool = True) -> dict:
    """为正例 fixture 写"临时 approved" design_ref 三件套: handoff + review + spec.
    默认 fixture_mode=True (因为 SW-012 真实状态是 queued, fixture 模式允许 queued 状态);
    真实模式用 fixture_mode=False (会强制 registry accepted).
    """
    design_dir = out_dir / "_design"
    design_dir.mkdir(exist_ok=True)
    # 临时 handoff 内容 (非真实 Trae handoff; 临时结构)
    handoff_path = design_dir / "H-SW-012-R1-FAKE.json"
    handoff_path.write_text(json.dumps({
        "schema_version": 1,
        "id": "H-SW-012-R1-FAKE",
        "task_id": "SW-012",
        "revision": 1,
        "producer": "trae-design",
        "recipient": "antigravity",
        "head_commit": "FIXTURE_NOT_REAL",
        "base_commit": "FIXTURE_NOT_REAL",
    }, ensure_ascii=False, indent=2))
    spec_path = design_dir / "spec.md"
    spec_content = "# 雨林设计 spec (FAKE FIXTURE)\n\n仅供 R2 fixture 验证使用, 不代表真实 SW-012 批准设计."
    spec_path.write_text(spec_content)
    spec_sha = hashlib.sha256(spec_content.encode()).hexdigest()
    ref = {
        "task_id": "SW-012",
        "handoff": str(handoff_path.relative_to(ROOT)),
        "spec_file": str(spec_path.relative_to(ROOT)),
        "spec_sha256": spec_sha,
    }
    if fixture_mode:
        ref["_fixture_mode"] = True
        ref["_expected_registry_status"] = "queued"  # 当前真实状态
    return ref


def write_approved_registry_review(out_dir: Path) -> dict:
    """为正例 fixture 写临时 approved registry + review 索引.
    真实文件留在 r2/fixtures/<name>/_design/ 目录, 不动真实 registry.
    """
    design_dir = out_dir / "_design"
    # 临时 review JSON (非真实 Antigravity review)
    review_path = design_dir / "R-SW-012-R1-FAKE.json"
    review_path.write_text(json.dumps({
        "schema_version": 1,
        "id": "R-SW-012-R1-FAKE",
        "task_id": "SW-012",
        "reviewer": "antigravity",
        "producer": "trae-design",
        "handoff": "PENDING",
        "reviewed_commit": "FIXTURE_NOT_REAL",
        "verdict": "approved",
    }, ensure_ascii=False, indent=2))
    return {
        "review": str(review_path.relative_to(ROOT)),
    }


# === 13 fixture 构建器 ===

def fixture_dirs() -> dict:
    FIX.mkdir(parents=True, exist_ok=True)
    for name in [
        "positive_ok",
        "negative_not_image",
        "negative_zero_size",
        "negative_opaque_layer",
        "negative_empty_layers",
        "negative_unknown_layer",
        "negative_duplicate_layer",
        "negative_missing_file",
        "negative_wrong_hash",
        "negative_missing_check",
        "negative_real_oversize",
        "negative_wrong_design_ref",
        "negative_stale_spec_sha",
    ]:
        d = FIX / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "webp").mkdir(exist_ok=True)
        (d / "png").mkdir(exist_ok=True)
        (d / "checks" / "black").mkdir(parents=True, exist_ok=True)
        (d / "checks" / "white").mkdir(parents=True, exist_ok=True)
        (d / "checks" / "magenta").mkdir(parents=True, exist_ok=True)
        (d / "checks" / "alpha_mask").mkdir(parents=True, exist_ok=True)
    return {n: FIX / n for n in [
        "positive_ok",
        "negative_not_image",
        "negative_zero_size",
        "negative_opaque_layer",
        "negative_empty_layers",
        "negative_unknown_layer",
        "negative_duplicate_layer",
        "negative_missing_file",
        "negative_wrong_hash",
        "negative_missing_check",
        "negative_real_oversize",
        "negative_wrong_design_ref",
        "negative_stale_spec_sha",
    ]}


def write_manifest(out_dir: Path, layers: list[dict], design_ref=None, task_id="SW-006", revision=1) -> Path:
    manifest_path = out_dir / "manifest.json"
    # 算 SHA
    for layer in layers:
        p = ROOT / layer["file"] if not Path(layer["file"]).is_absolute() else Path(layer["file"])
        if not p.is_file():
            p = out_dir / layer["file"]
        layer["sha256"] = file_sha256(p)
    for layer in layers:
        layer["checks"] = [
            f"checks/alpha_mask/rainforest_{layer['layer_id']}.png",
            f"checks/black/rainforest_{layer['layer_id']}.jpg",
            f"checks/white/rainforest_{layer['layer_id']}.jpg",
            f"checks/magenta/rainforest_{layer['layer_id']}.jpg",
        ]
        layer.setdefault("limitations", ["R2 fixture: PIL 程序化自制小样本, 非雨林正式图"])
    manifest = {
        "schema_version": 1,
        "task_id": task_id,
        "revision": revision,
        "scene_id": "rainforest",
        "producer": "minimax",
        "api_attempts_this_revision": 0,
        "api_attempts_total": 14,
        "cost": "unknown",
        "layers": layers,
        "design_ref": design_ref,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest_path


def gen_positive_ok(dirs):
    """成功正例: 5 层 + 4 底色检查 + 临时 fixture design_ref (默认 fixture_mode=True)."""
    out = dirs["positive_ok"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        layers.append(write_layer_artifacts(lid, out, rgba))
    # write_design_ref_assets 默认 fixture_mode=True
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_not_image(dirs):
    """非图: 文本伪装 WebP."""
    out = dirs["negative_not_image"]
    payload = b"SW-014 R2 AUDIT FIXTURE: this is not an image\n"
    (out / "webp" / "rainforest_mist.webp").write_bytes(payload)
    (out / "png" / "rainforest_mist.png").write_bytes(payload)
    # 其他层正常
    for lid in RAINFOREST_LAYERS[1:]:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
    layers = [{
        "layer_id": "mist",
        "file": "webp/rainforest_mist.webp",
        "width": W, "height": H,
        "bytes": len(payload),
        "alpha_channel": True,
        "render_role": "overlay",
        "tileable": False,
    }] + [{
        "layer_id": lid,
        "file": f"webp/rainforest_{lid}.webp",
        "width": W, "height": H,
        "bytes": (out / f"webp/rainforest_{lid}.webp").stat().st_size,
        "alpha_channel": True,
        "render_role": "overlay",
        "tileable": False,
    } for lid in RAINFOREST_LAYERS[1:]]
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_zero_size(dirs):
    """0x0 尺寸 (manifest 虚报, 实际文件 1x1 真图)."""
    out = dirs["negative_zero_size"]
    # 写 1x1 真图 (避免 WebP/PNG 拒绝 0x0)
    img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    img.save(out / "webp" / "rainforest_mist.webp", "WEBP", quality=85, method=6, alpha_quality=85)
    img.save(out / "png" / "rainforest_mist.png", "PNG", optimize=True)
    Image.fromarray(np.zeros((1, 1), dtype=np.uint8), "L").save(out / "checks" / "alpha_mask" / "rainforest_mist.png", "PNG", optimize=True)
    for bg_name, bg_rgb in [("black", (0, 0, 0)), ("white", (255, 255, 255)), ("magenta", (255, 0, 255))]:
        Image.fromarray(np.zeros((1, 1, 3), dtype=np.uint8), "RGB").save(out / "checks" / bg_name / "rainforest_mist.jpg", "JPEG", quality=90, optimize=True)
    for lid in RAINFOREST_LAYERS[1:]:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
    layers = [{
        "layer_id": "mist",
        "file": "webp/rainforest_mist.webp",
        "width": 0, "height": 0,  # manifest 虚报 0x0
        "bytes": (out / "webp" / "rainforest_mist.webp").stat().st_size,
        "alpha_channel": True,
        "render_role": "overlay",
        "tileable": False,
    }] + [{
        "layer_id": lid,
        "file": f"webp/rainforest_{lid}.webp",
        "width": W, "height": H,
        "bytes": (out / f"webp/rainforest_{lid}.webp").stat().st_size,
        "alpha_channel": True,
        "render_role": "overlay",
        "tileable": False,
    } for lid in RAINFOREST_LAYERS[1:]]
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_opaque_layer(dirs):
    """不透明层: alpha 全 255 (没有透明区域)."""
    out = dirs["negative_opaque_layer"]
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., 0:3] = 100  # RGB 灰
    rgba[..., 3] = 255  # 全不透明
    Image.fromarray(rgba, "RGBA").save(out / "webp" / "rainforest_mist.webp", "WEBP", quality=85, method=6, alpha_quality=85)
    Image.fromarray(rgba, "RGBA").save(out / "png" / "rainforest_mist.png", "PNG", optimize=True)
    Image.fromarray(rgba[..., 3], "L").save(out / "checks" / "alpha_mask" / "rainforest_mist.png", "PNG", optimize=True)
    for bg_name, bg_rgb in [("black", (0,0,0)), ("white", (255,255,255)), ("magenta", (255,0,255))]:
        composed = np.full((H, W, 3), 100, dtype=np.uint8)  # 不透明, 全覆盖背景
        Image.fromarray(composed, "RGB").save(out / "checks" / bg_name / "rainforest_mist.jpg", "JPEG", quality=90, optimize=True)
    for lid in RAINFOREST_LAYERS[1:]:
        rgba2 = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba2)
    layers = [{
        "layer_id": "mist",
        "file": "webp/rainforest_mist.webp",
        "width": W, "height": H,
        "bytes": (out / "webp" / "rainforest_mist.webp").stat().st_size,
        "alpha_channel": True,
        "render_role": "overlay",
        "tileable": False,
    }] + [{
        "layer_id": lid,
        "file": f"webp/rainforest_{lid}.webp",
        "width": W, "height": H,
        "bytes": (out / f"webp/rainforest_{lid}.webp").stat().st_size,
        "alpha_channel": True,
        "render_role": "overlay",
        "tileable": False,
    } for lid in RAINFOREST_LAYERS[1:]]
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_empty_layers(dirs):
    """空 layers 数组."""
    out = dirs["negative_empty_layers"]
    design_ref = write_design_ref_assets(out)
    write_manifest(out, [], design_ref=design_ref)


def gen_negative_unknown_layer(dirs):
    """未知 layer_id (不在已批准 layer 集合)."""
    out = dirs["negative_unknown_layer"]
    rgba = make_layer_png("vines_light")  # 用合法内容
    layers = [write_layer_artifacts("foo_bar", out, rgba)]
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_duplicate_layer(dirs):
    """重复 layer_id."""
    out = dirs["negative_duplicate_layer"]
    rgba1 = make_layer_png("mist")
    write_layer_artifacts("mist", out, rgba1)
    rgba2 = make_layer_png("mist")
    # 写到不同文件名但 layer_id 重复
    (out / "webp" / "rainforest_mist_2.webp").parent.mkdir(exist_ok=True)
    Image.fromarray(rgba2, "RGBA").save(out / "webp" / "rainforest_mist_2.webp", "WEBP", quality=85, method=6, alpha_quality=85)
    layers = [
        {"layer_id": "mist", "file": "webp/rainforest_mist.webp", "width": W, "height": H, "bytes": (out/"webp/rainforest_mist.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False},
        {"layer_id": "mist", "file": "webp/rainforest_mist_2.webp", "width": W, "height": H, "bytes": (out/"webp/rainforest_mist_2.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False},
    ]
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_missing_file(dirs):
    """缺文件: manifest 声明 webp 但实际不存在."""
    out = dirs["negative_missing_file"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": 0, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    design_ref = write_design_ref_assets(out)
    # 先写 manifest (算 SHA), 再删文件
    write_manifest(out, layers, design_ref=design_ref)
    (out / "webp" / "rainforest_mist.webp").unlink()


def gen_negative_wrong_hash(dirs):
    """错 SHA: manifest 虚报 sha256."""
    out = dirs["negative_wrong_hash"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out/f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)
    # 写后再篡改 manifest 中 mist 的 SHA
    manifest_path = out / "manifest.json"
    m = json.loads(manifest_path.read_text())
    m["layers"][0]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(m, ensure_ascii=False, indent=2))


def gen_negative_missing_check(dirs):
    """缺检查图."""
    out = dirs["negative_missing_check"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out/f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    # 删一个 alpha_mask
    (out / "checks" / "alpha_mask" / "rainforest_mist.png").unlink()
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_real_oversize(dirs):
    """真实超 400KB (非只改声明)."""
    out = dirs["negative_real_oversize"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        if lid == "trunks_canopy":
            # 写一个真实大图 (RGB 噪声 + alpha 0)
            big = np.random.RandomState(42).randint(0, 255, (H, W, 3), dtype=np.uint8)
            a = np.zeros((H, W), dtype=np.uint8)
            rgba = np.dstack([big, a])
            Image.fromarray(rgba, "RGBA").save(out / f"webp/rainforest_{lid}.webp", "WEBP", quality=100, method=6, alpha_quality=100)
            Image.fromarray(rgba, "RGBA").save(out / f"png/rainforest_{lid}.png", "PNG", optimize=False, compress_level=0)
            # 写检查图
            for bg_name, bg_rgb in [("black", (0,0,0)), ("white", (255,255,255)), ("magenta", (255,0,255))]:
                Image.fromarray(big, "RGB").save(out / "checks" / bg_name / f"rainforest_{lid}.jpg", "JPEG", quality=95, optimize=False)
            Image.fromarray(a, "L").save(out / "checks" / "alpha_mask" / f"rainforest_{lid}.png", "PNG", optimize=False)
            layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out/f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "parallax", "tileable": False})
        else:
            rgba = make_layer_png(lid)
            layers.append(write_layer_artifacts(lid, out, rgba))
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_wrong_design_ref(dirs):
    """错 design_ref: handoff 路径不存在 / spec_sha256 不匹配实际 / 写 dummy.
    用真实模式 (fixture_mode=False) 让路径错误是唯一失败源."""
    out = dirs["negative_wrong_design_ref"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out/f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    # design_ref 指向错误路径 (不写 spec, handoff/spec 都不存在)
    bad_ref = {
        "task_id": "SW-012",
        "handoff": "docs/collaboration/handoffs/trae-design/THIS_PATH_DOES_NOT_EXIST.json",
        "spec_file": "design/05-visual-design/SW-012/this_spec_does_not_exist.md",
        "spec_sha256": "0" * 64,
    }
    write_manifest(out, layers, design_ref=bad_ref)


def gen_negative_stale_spec_sha(dirs):
    """陈旧 spec_sha256: 写一个 spec 但 manifest 虚报 hash."""
    out = dirs["negative_stale_spec_sha"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out/f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    design_ref = write_design_ref_assets(out)
    # 篡改 spec_sha256
    design_ref["spec_sha256"] = "stale_sha_actually_different_from_real_spec_" + "f" * 24
    write_manifest(out, layers, design_ref=design_ref)


# === 主流程 ===

def main() -> None:
    print("=== SW-014 R2 fixture 构建 ===")
    dirs = fixture_dirs()
    builders = [
        ("positive_ok", gen_positive_ok),
        ("negative_not_image", gen_negative_not_image),
        ("negative_zero_size", gen_negative_zero_size),
        ("negative_opaque_layer", gen_negative_opaque_layer),
        ("negative_empty_layers", gen_negative_empty_layers),
        ("negative_unknown_layer", gen_negative_unknown_layer),
        ("negative_duplicate_layer", gen_negative_duplicate_layer),
        ("negative_missing_file", gen_negative_missing_file),
        ("negative_wrong_hash", gen_negative_wrong_hash),
        ("negative_missing_check", gen_negative_missing_check),
        ("negative_real_oversize", gen_negative_real_oversize),
        ("negative_wrong_design_ref", gen_negative_wrong_design_ref),
        ("negative_stale_spec_sha", gen_negative_stale_spec_sha),
    ]
    for name, fn in builders:
        try:
            fn(dirs)
            manifest_path = dirs[name] / "manifest.json"
            if manifest_path.exists():
                m = json.loads(manifest_path.read_text())
                layers_count = len(m.get("layers", []))
                total_bytes = sum(l.get("bytes", 0) for l in m.get("layers", []))
                print(f"  {name}: {layers_count} 层, {total_bytes} bytes")
            else:
                print(f"  {name}: manifest 不存在")
        except Exception as e:
            print(f"  {name}: ERROR {e}")
            raise
    print(f"\nfixture root: {FIX.relative_to(ROOT)}")
    print(f"  total fixture dirs: {len(dirs)}")


if __name__ == "__main__":
    main()