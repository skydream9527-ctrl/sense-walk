#!/usr/bin/env python3
"""
SW-014 R3 fixture 构建 (零 API, 全部 PIL 程序化).

R3 相对 R2 的关键差异:
- 正例 default 不带 _fixture_mode 字段, 需 --fixture-mode CLI 旗标才能通过
- 反例 13 个全部按 R3-01~R3-07 真实缺陷触发, 每个仅 1 改动
- 新增 R3-08 negative_wrong_approval_chain：写一个完全合法的 manifest，但 design_ref 引用的 handoff head_commit != registry.latest_handoff.head (批准链错配)
- 新增 R3-09 negative_negative_api_cumulative：api_attempts_total = -1 + 比 state/minimax.json cumulative 小 (R3-04)
- 新增 R3-10 negative_dynamic_spec_mismatch：manifest 用 SW-006 rainforest 但 design_spec 声明 layers=["mist","clearing_glow"] 而非 5 层 (R3-06 动态读取)
- 真实超预算 R3-07: negative_real_oversize_layer 单图实际 > 400 KB (实际生成大图), negative_real_oversize_scene 全景 > 2 MB
- 写 state/minimax.json 历史账本 (R3-04 跨 revision 累计)
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

R3 = ROOT / "design" / "assets" / "rainforest" / "preflight" / "SW-014" / "r3"
FIX = R3 / "fixtures"

W, H = 768, 1376  # 接受集合 (768x1376) + (1080x1920) 见 ACCEPTED_DIMENSIONS

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
    """生成 RGBA 雨林 fixture (透明底, 含主体, 半透明像素)."""
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    a = np.zeros((h, w), dtype=np.float32)
    yy, xx = np.indices((h, w), dtype=np.float32)
    if layer_id == "mist":
        cx, cy, r = w / 2, h * 0.5, w * 0.6
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        a = (200 * np.clip(1 - d / r, 0, 1) ** 1.5).astype(np.float32)  # alpha 200 = 半透明 (alpha<127 在 R3-02)
        rgb[...] = MIST
    elif layer_id == "trunks_canopy":
        for xc in [w * 0.2, w * 0.4, w * 0.6, w * 0.8]:
            trunk_w = 16
            mask = np.abs(xx - xc) < trunk_w
            a = np.maximum(a, mask.astype(np.float32) * 200)
        rgb[...] = TRUNK
    elif layer_id == "vines_light":
        for cx, cy in [(w * 0.3, h * 0.3), (w * 0.6, h * 0.5), (w * 0.7, h * 0.7)]:
            d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            a = np.maximum(a, 220 * np.clip(1 - d / 30, 0, 1) ** 2)
        rgb[...] = VINE
    elif layer_id == "far_glow":
        cx, cy, r = w * 0.5, h * 0.3, w * 0.4
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        a = (210 * np.clip(1 - d / r, 0, 1) ** 1.3).astype(np.float32)
        rgb[...] = TRUNK2
    elif layer_id == "clearing_glow":
        cx, cy, r = w * 0.5, h * 0.6, w * 0.5
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        a = (180 * np.clip(1 - d / r, 0, 1) ** 1.4).astype(np.float32)
        rgb[...] = VINE
    # 边缘羽化
    ramp = np.ones((h, w), dtype=np.float32)
    ramp[:30, :] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(-1, 1)
    ramp[-30:, :] *= np.linspace(1, 0, 30, dtype=np.float32).reshape(-1, 1)
    ramp[:, :30] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(1, -1)
    ramp[:, -30:] *= np.linspace(1, 0, 30, dtype=np.float32).reshape(1, -1)
    a *= ramp
    return np.dstack([rgb, a]).clip(0, 255).astype(np.uint8)


def write_layer_artifacts(layer_id: str, out_dir: Path, rgba: np.ndarray) -> dict:
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
        "origin": "R3 fixture: PIL 程序化自制小样本, 非雨林正式图",
        "process": "make_layer_png (SW-014 R3 build_fixtures.py)",
    }


def write_design_ref_assets(out_dir: Path, *, use_design_spec_layers: bool = True) -> dict:
    """为正例 fixture 写设计参考三件套: handoff + review + spec (含 layers 列表).
    use_design_spec_layers=True (默认): spec 用 5 层完整集合, 模拟 SW-012 真实已批设计.
    """
    design_dir = out_dir / "_design"
    design_dir.mkdir(exist_ok=True)
    handoff_path = design_dir / "H-SW-012-R1-FAKE.json"
    handoff_path.write_text(json.dumps({
        "schema_version": 1,
        "id": "H-SW-012-R1-FAKE",
        "task_id": "SW-012",
        "revision": 1,
        "producer": "trae-design",
        "recipient": "antigravity",
        "head_commit": "a" * 40,  # 40-char SHA, 仅供 fixture 批准链核对
        "base_commit": "0" * 40,
    }, ensure_ascii=False, indent=2))
    spec_path = design_dir / "spec.json"
    spec_layers = RAINFOREST_LAYERS if use_design_spec_layers else ["mist", "clearing_glow"]
    spec_data = {
        "schema_version": 1,
        "task_id": "SW-012",
        "revision": 1,
        "scene_id": "rainforest",
        "canvas": {"width": 1080, "height": 1920},
        "layers": [{"layer_id": lid, "render_role": "parallax" if lid in ("mist", "trunks_canopy") else "overlay"} for lid in spec_layers],
    }
    spec_path.write_text(json.dumps(spec_data, ensure_ascii=False, indent=2))
    spec_sha = file_sha256(spec_path)
    return {
        "task_id": "SW-012",
        "handoff": str(handoff_path.relative_to(ROOT)),
        "spec_file": str(spec_path.relative_to(ROOT)),
        "spec_sha256": spec_sha,
    }


def write_manifest(out_dir: Path, layers: list[dict], design_ref=None, task_id="SW-006", revision=1, api_attempts_this_revision: int = 0, api_attempts_total: int = 14) -> Path:
    manifest_path = out_dir / "manifest.json"
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
        layer.setdefault("limitations", ["R3 fixture: PIL 程序化自制小样本, 非雨林正式图"])
    manifest = {
        "schema_version": 1,
        "task_id": task_id,
        "revision": revision,
        "scene_id": "rainforest",
        "producer": "minimax",
        "api_attempts_this_revision": api_attempts_this_revision,
        "api_attempts_total": api_attempts_total,
        "cost": "unknown",
        "layers": layers,
        "design_ref": design_ref,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest_path


# === fixture 构建器 ===

def fixture_dirs() -> dict:
    FIX.mkdir(parents=True, exist_ok=True)
    names = [
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
        "negative_real_oversize_layer",
        "negative_real_oversize_scene",
        "negative_wrong_design_ref",
        "negative_stale_spec_sha",
        "negative_negative_api_cumulative",
        "negative_dynamic_spec_mismatch",
        "negative_wrong_approval_chain",
        "negative_manifest_fixture_key",
    ]
    for n in names:
        d = FIX / n
        d.mkdir(parents=True, exist_ok=True)
        (d / "webp").mkdir(exist_ok=True)
        (d / "png").mkdir(exist_ok=True)
        (d / "checks" / "black").mkdir(parents=True, exist_ok=True)
        (d / "checks" / "white").mkdir(parents=True, exist_ok=True)
        (d / "checks" / "magenta").mkdir(parents=True, exist_ok=True)
        (d / "checks" / "alpha_mask").mkdir(parents=True, exist_ok=True)
    return {n: FIX / n for n in names}


def write_state_history():
    """写 state/minimax.json 历史账本, R3-04 用."""
    state_path = ROOT / "docs" / "collaboration" / "state" / "minimax.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if not state_path.is_file():
        state_data = {
            "agent": "minimax",
            "schema_version": 1,
            "cumulative_attempts": 14,  # SW-002 R1 14 次累计 (基线)
            "revisions": [
                {"task_id": "SW-002", "revision": 1, "attempts": 14, "status": "accepted"},
            ],
            "fixture_state": {
                "r3_uses_history_baseline": True,
                "note": "R3 fixture 测试默认以累计 14 为基线; 真实 cumulative 必须 >= 14",
            },
        }
        state_path.write_text(json.dumps(state_data, ensure_ascii=False, indent=2))


# === 13 fixture (R3 升级版: 含 6 反例组 + 1 正例) ===

def gen_positive_ok(dirs):
    """成功正例 (默认严格: 含完整 5 层 + spec 5 层 + 验收脚本对比 + CLI --fixture-mode 旗标才通过).
    默认 mode 不带 _fixture_mode 字段, 让 R3-01 默认入口拒绝。
    """
    out = dirs["positive_ok"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        layers.append(write_layer_artifacts(lid, out, rgba))
    design_ref = write_design_ref_assets(out, use_design_spec_layers=True)
    # 默认不放 _fixture_mode, 必须 CLI 旗标
    write_manifest(out, layers, design_ref=design_ref, api_attempts_this_revision=0, api_attempts_total=14)


def gen_negative_not_image(dirs):
    out = dirs["negative_not_image"]
    payload = b"SW-014 R3 AUDIT FIXTURE: this is not an image\n"
    (out / "webp" / "rainforest_mist.webp").write_bytes(payload)
    (out / "png" / "rainforest_mist.png").write_bytes(payload)
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
    out = dirs["negative_zero_size"]
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
        "width": 0, "height": 0,
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
    """R3-02 反例: alpha=255 全不透明 (R2 中会被误判 100% 透明, R3 应被拒)."""
    out = dirs["negative_opaque_layer"]
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., 0:3] = 100
    rgba[..., 3] = 255  # 全不透明
    Image.fromarray(rgba, "RGBA").save(out / "webp" / "rainforest_mist.webp", "WEBP", quality=85, method=6, alpha_quality=85)
    Image.fromarray(rgba, "RGBA").save(out / "png" / "rainforest_mist.png", "PNG", optimize=True)
    Image.fromarray(rgba[..., 3], "L").save(out / "checks" / "alpha_mask" / "rainforest_mist.png", "PNG", optimize=True)
    for bg_name, bg_rgb in [("black", (0,0,0)), ("white", (255,255,255)), ("magenta", (255,0,255))]:
        composed = np.full((H, W, 3), 100, dtype=np.uint8)
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
    out = dirs["negative_empty_layers"]
    design_ref = write_design_ref_assets(out)
    write_manifest(out, [], design_ref=design_ref)


def gen_negative_unknown_layer(dirs):
    out = dirs["negative_unknown_layer"]
    rgba = make_layer_png("vines_light")
    layers = [write_layer_artifacts("foo_bar", out, rgba)]
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_duplicate_layer(dirs):
    out = dirs["negative_duplicate_layer"]
    rgba1 = make_layer_png("mist")
    write_layer_artifacts("mist", out, rgba1)
    rgba2 = make_layer_png("mist")
    Image.fromarray(rgba2, "RGBA").save(out / "webp" / "rainforest_mist_2.webp", "WEBP", quality=85, method=6, alpha_quality=85)
    layers = [
        {"layer_id": "mist", "file": "webp/rainforest_mist.webp", "width": W, "height": H, "bytes": (out/"webp/rainforest_mist.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False},
        {"layer_id": "mist", "file": "webp/rainforest_mist_2.webp", "width": W, "height": H, "bytes": (out/"webp/rainforest_mist_2.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False},
    ]
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_missing_file(dirs):
    out = dirs["negative_missing_file"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": 0, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)
    (out / "webp" / "rainforest_mist.webp").unlink()


def gen_negative_wrong_hash(dirs):
    out = dirs["negative_wrong_hash"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out/f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)
    manifest_path = out / "manifest.json"
    m = json.loads(manifest_path.read_text())
    m["layers"][0]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(m, ensure_ascii=False, indent=2))


def gen_negative_missing_check(dirs):
    """R3-03 反例: 即使 manifest.checks=[] 也要被 R3-03 强制 4 底色检查图完备性发现."""
    out = dirs["negative_missing_check"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out/f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    # 删除一个 alpha_mask 图
    (out / "checks" / "alpha_mask" / "rainforest_mist.png").unlink()
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_real_oversize_layer(dirs):
    """R3-07 反例: 单层真实 > 400 KB.
    写一张 768x1376 PNG, 不压缩, 实际字节数 > 400 KB.
    """
    out = dirs["negative_real_oversize_layer"]
    # 用 R3 接受尺寸 1080x1920 (大) + 随机 noise, 实际 PNG 字节 > 400 KB
    big_w, big_h = 1080, 1920
    rng = np.random.RandomState(2026)
    rgb = rng.randint(0, 255, (big_h, big_w, 3), dtype=np.uint8)
    # alpha 半透明 (避免触发 R3-02)
    a = np.full((big_h, big_w), 100, dtype=np.uint8)
    rgba = np.dstack([rgb, a])
    Image.fromarray(rgba, "RGBA").save(out / "webp" / "rainforest_mist.webp", "WEBP", quality=100, method=0, alpha_quality=100, lossless=False)
    Image.fromarray(rgba, "RGBA").save(out / "png" / "rainforest_mist.png", "PNG", optimize=False, compress_level=0)
    Image.fromarray(a, "L").save(out / "checks" / "alpha_mask" / "rainforest_mist.png", "PNG", optimize=False)
    for bg_name, bg_rgb in [("black", (0, 0, 0)), ("white", (255, 255, 255)), ("magenta", (255, 0, 255))]:
        bg = np.array(bg_rgb, dtype=np.uint8).reshape(1, 1, 3)
        composed = (rgb.astype(np.float32) * (a.astype(np.float32) / 255.0)[..., None] + bg.astype(np.float32) * (1 - a.astype(np.float32) / 255.0)[..., None]).clip(0, 255).astype(np.uint8)
        Image.fromarray(composed, "RGB").save(out / "checks" / bg_name / "rainforest_mist.jpg", "JPEG", quality=95)
    layers = [{
        "layer_id": "mist",
        "file": "webp/rainforest_mist.webp",
        "width": big_w, "height": big_h,
        "bytes": (out / "webp" / "rainforest_mist.webp").stat().st_size,
        "alpha_channel": True,
        "render_role": "overlay",
        "tileable": False,
    }]
    # 其他 4 层正常 (但仍要凑齐 spec 5 层)
    for lid in RAINFOREST_LAYERS[1:]:
        rgba2 = make_layer_png(lid)
        layers.append(write_layer_artifacts(lid, out, rgba2))
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_real_oversize_scene(dirs):
    """R3-07 反例: 全景真实 > 2 MB.
    每层都用 1080x1920 全 RGB 噪声 PNG 不压缩, 5 层总 > 2 MB.
    """
    out = dirs["negative_real_oversize_scene"]
    big_w, big_h = 1080, 1920
    rng = np.random.RandomState(7)
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgb = rng.randint(0, 255, (big_h, big_w, 3), dtype=np.uint8)
        a = np.full((big_h, big_w), 100, dtype=np.uint8)
        rgba = np.dstack([rgb, a])
        webp = out / "webp" / f"rainforest_{lid}.webp"
        png = out / "png" / f"rainforest_{lid}.png"
        Image.fromarray(rgba, "RGBA").save(webp, "WEBP", quality=100, method=0, alpha_quality=100)
        Image.fromarray(rgba, "RGBA").save(png, "PNG", optimize=False, compress_level=0)
        Image.fromarray(a, "L").save(out / "checks" / "alpha_mask" / f"rainforest_{lid}.png", "PNG", optimize=False)
        for bg_name, bg_rgb in [("black", (0, 0, 0)), ("white", (255, 255, 255)), ("magenta", (255, 0, 255))]:
            bg = np.array(bg_rgb, dtype=np.uint8).reshape(1, 1, 3)
            composed = (rgb.astype(np.float32) * (a.astype(np.float32) / 255.0)[..., None] + bg.astype(np.float32) * (1 - a.astype(np.float32) / 255.0)[..., None]).clip(0, 255).astype(np.uint8)
            Image.fromarray(composed, "RGB").save(out / "checks" / bg_name / f"rainforest_{lid}.jpg", "JPEG", quality=95)
        layers.append({
            "layer_id": lid,
            "file": f"webp/rainforest_{lid}.webp",
            "width": big_w, "height": big_h,
            "bytes": webp.stat().st_size,
            "alpha_channel": True,
            "render_role": "overlay",
            "tileable": False,
        })
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_wrong_design_ref(dirs):
    out = dirs["negative_wrong_design_ref"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out / f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    bad_ref = {
        "task_id": "SW-012",
        "handoff": "docs/collaboration/handoffs/trae-design/THIS_PATH_DOES_NOT_EXIST.json",
        "spec_file": "design/05-visual-design/SW-012/this_spec_does_not_exist.md",
        "spec_sha256": "0" * 64,
    }
    write_manifest(out, layers, design_ref=bad_ref)


def gen_negative_stale_spec_sha(dirs):
    out = dirs["negative_stale_spec_sha"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out / f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    design_ref = write_design_ref_assets(out)
    design_ref["spec_sha256"] = "stale_sha_actually_different_from_real_spec_" + "f" * 24
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_negative_api_cumulative(dirs):
    """R3-04 反例: api_attempts_total = -1 (R2 仅检查 key 存在, R3 必须非负整数 + 跨 revision)."""
    out = dirs["negative_negative_api_cumulative"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out / f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    design_ref = write_design_ref_assets(out)
    write_manifest(out, layers, design_ref=design_ref, api_attempts_this_revision=0, api_attempts_total=-1)


def gen_negative_dynamic_spec_mismatch(dirs):
    """R3-06 反例: design_spec 声明 layers 只含 2 个, 但 manifest 含 5 个; 缺 3 层应失败."""
    out = dirs["negative_dynamic_spec_mismatch"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out / f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    # design_spec 只含 2 层 (mismatch: 实际 5 层 manifest vs spec 2 层)
    design_ref = write_design_ref_assets(out, use_design_spec_layers=False)
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_wrong_approval_chain(dirs):
    """R3-05 反例: design_ref 引用的 handoff head 与 registry.latest_handoff head 不一致.
    用真实的临时 handoff (head_commit='b'*40), 但 registry.latest_handoff 指向 head_commit='a'*40 (R3 build_fixtures 写).
    由于 R3 不修改真实 registry, 用 fixture_mode 仅能绕 status; 但 head mismatch 应被 R3-05 严格拒绝.
    这里用 fixture_mode + 直接修改 design_ref.handoff 让其指向一个 head_commit='b'*40 的 handoff (而 registry 引用 head='a'*40).
    """
    out = dirs["negative_wrong_approval_chain"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out / f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    # 写一个 head_commit='b'*40 的 handoff, 不匹配 registry.latest_handoff='a'*40
    handoff_path = out / "_design" / "H-SW-012-R1-FAKE.json"
    handoff_path.parent.mkdir(exist_ok=True)
    handoff_path.write_text(json.dumps({
        "schema_version": 1,
        "id": "H-SW-012-R1-FAKE",
        "task_id": "SW-012",
        "revision": 1,
        "producer": "trae-design",
        "recipient": "antigravity",
        "head_commit": "b" * 40,
        "base_commit": "0" * 40,
    }, ensure_ascii=False, indent=2))
    spec_path = out / "_design" / "spec.json"
    spec_data = {
        "schema_version": 1,
        "task_id": "SW-012",
        "revision": 1,
        "scene_id": "rainforest",
        "canvas": {"width": 1080, "height": 1920},
        "layers": [{"layer_id": lid, "render_role": "parallax" if lid in ("mist", "trunks_canopy") else "overlay"} for lid in RAINFOREST_LAYERS],
    }
    spec_path.write_text(json.dumps(spec_data, ensure_ascii=False, indent=2))
    design_ref = {
        "task_id": "SW-012",
        "handoff": str(handoff_path.relative_to(ROOT)),
        "spec_file": str(spec_path.relative_to(ROOT)),
        "spec_sha256": file_sha256(spec_path),
    }
    write_manifest(out, layers, design_ref=design_ref)


def gen_negative_manifest_fixture_key(dirs):
    """R3-01 反例: manifest 内 _fixture_mode=true + _expected_registry_status=queued 试图绕过.
    在 fixture_mode=False 默认入口下应被拒.
    """
    out = dirs["negative_manifest_fixture_key"]
    layers = []
    for lid in RAINFOREST_LAYERS:
        rgba = make_layer_png(lid)
        write_layer_artifacts(lid, out, rgba)
        layers.append({"layer_id": lid, "file": f"webp/rainforest_{lid}.webp", "width": W, "height": H, "bytes": (out / f"webp/rainforest_{lid}.webp").stat().st_size, "alpha_channel": True, "render_role": "overlay", "tileable": False})
    design_ref = write_design_ref_assets(out)
    design_ref["_fixture_mode"] = True
    design_ref["_expected_registry_status"] = "queued"
    write_manifest(out, layers, design_ref=design_ref)


# === 主流程 ===

def main() -> None:
    print("=== SW-014 R3 fixture 构建 (升级版) ===")
    write_state_history()
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
        ("negative_real_oversize_layer", gen_negative_real_oversize_layer),
        ("negative_real_oversize_scene", gen_negative_real_oversize_scene),
        ("negative_wrong_design_ref", gen_negative_wrong_design_ref),
        ("negative_stale_spec_sha", gen_negative_stale_spec_sha),
        ("negative_negative_api_cumulative", gen_negative_negative_api_cumulative),
        ("negative_dynamic_spec_mismatch", gen_negative_dynamic_spec_mismatch),
        ("negative_wrong_approval_chain", gen_negative_wrong_approval_chain),
        ("negative_manifest_fixture_key", gen_negative_manifest_fixture_key),
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