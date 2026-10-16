#!/usr/bin/env python3
"""
SW-015 R1 fixture 构建器 (零 API, 全部 PIL 程序化).

新增 8 个 fixture (基于 SW-014 R3 18 fixture, SW-015 R1 新增 8 个):

正例 (2):
- sw015_positive_rainforest_canonical: 5 层 SW-012 proposed id + type (mist/overlay, trunks_canopy/parallax, vines_light/parallax, distant_glow/overlay, glade/overlay)
- sw015_positive_forest_legacy_alias: 5 层 SW-011 已批 id + type (tree_outline/parallax, tree_trunks/parallax, leaf_path/parallax, light_shows/overlay, clearing/overlay)

反例 (6):
- sw015_negative_empty_spec: spec.layers=[]
- sw015_negative_duplicate_layer_id: spec 含两个 trunks_canopy (duplicate)
- sw015_negative_unknown_type: spec 含 type="background" (未知 type)
- sw015_negative_wrong_canvas: spec canvas width=768 (非 1080x1920)
- sw015_negative_layer_id_mismatch: manifest 含 spec 未声明的 layer_id ("random_layer")
- sw015_negative_legacy_alias_mismatch: manifest 用 legacy render_role "mist_layer" 但 spec 期望 "overlay"

写 state/minimax.json 历史 (保留 14 baseline + SW-006 8 次单独).
"""

from __future__ import annotations

import hashlib
import json
import shutil
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

R15 = ROOT / "design" / "assets" / "rainforest" / "preflight" / "SW-015" / "r1"
FIX = R15 / "fixtures"

W, H = 768, 1376

# 雨林色板 (rainforest.md §2)
MIST = np.array([0x1A, 0x2E, 0x28], dtype=np.float32)
TRUNK = np.array([0x1E, 0x3D, 0x36], dtype=np.float32)
VINE = np.array([0xC4, 0xD4, 0xA8], dtype=np.float32)
GLOW = np.array([0xA8, 0xC9, 0xA6], dtype=np.float32)

# 森林色板 (forest.md)
OUTLINE = np.array([0x1A, 0x28, 0x20], dtype=np.float32)
TRUNK_F = np.array([0x2D, 0x4A, 0x3E], dtype=np.float32)
LEAF = np.array([0x6B, 0x8F, 0x71], dtype=np.float32)
LIGHT = np.array([0x8F, 0xA8, 0x7A], dtype=np.float32)
WARM = np.array([0xA8, 0x90, 0x60], dtype=np.float32)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_rgba(layer_id: str, color: np.ndarray) -> np.ndarray:
    """生成 RGBA 半透明 RGBA 雨林 fixture."""
    rgb = np.zeros((H, W, 3), dtype=np.float32)
    a = np.zeros((H, W), dtype=np.float32)
    yy, xx = np.indices((H, W), dtype=np.float32)
    cx, cy, r = W / 2, H * 0.5, W * 0.6
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    a = (200 * np.clip(1 - d / r, 0, 1) ** 1.5).astype(np.float32)
    rgb[...] = color
    # 边缘羽化
    ramp = np.ones((H, W), dtype=np.float32)
    ramp[:30, :] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(-1, 1)
    ramp[-30:, :] *= np.linspace(1, 0, 30, dtype=np.float32).reshape(-1, 1)
    ramp[:, :30] *= np.linspace(0, 1, 30, dtype=np.float32).reshape(1, -1)
    ramp[:, -30:] *= np.linspace(1, 0, 30, dtype=np.float32).reshape(1, -1)
    a *= ramp
    return np.dstack([rgb, a]).clip(0, 255).astype(np.uint8)


def write_layer_artifacts(layer_id: str, out_dir: Path, rgba: np.ndarray, scene: str) -> dict:
    """检查图按 R3 推断命名: checks/<bg>/<layer_id>.<ext> (优先) 或 rainforest_<layer_id>."""
    webp = out_dir / "webp" / f"{scene}_{layer_id}.webp"
    png = out_dir / "png" / f"{scene}_{layer_id}.png"
    Image.fromarray(rgba, "RGBA").save(webp, "WEBP", quality=85, method=6, alpha_quality=85)
    Image.fromarray(rgba, "RGBA").save(png, "PNG", optimize=True)
    # alpha_mask: 既给 <layer_id> 也给 <scene>_<layer_id> (兼容 R3 两种命名推断)
    Image.fromarray(rgba[..., 3], "L").save(out_dir / "checks" / "alpha_mask" / f"{layer_id}.png", "PNG", optimize=True)
    Image.fromarray(rgba[..., 3], "L").save(out_dir / "checks" / "alpha_mask" / f"{scene}_{layer_id}.png", "PNG", optimize=True)
    for bg_name, bg_rgb in [("black", (0, 0, 0)), ("white", (255, 255, 255)), ("magenta", (255, 0, 255))]:
        rgb = rgba[..., :3].astype(np.float32)
        a = rgba[..., 3:4].astype(np.float32) / 255.0
        bg = np.array(bg_rgb, dtype=np.float32).reshape(1, 1, 3)
        composed = (rgb * a + bg * (1 - a)).clip(0, 255).astype(np.uint8)
        Image.fromarray(composed, "RGB").save(out_dir / "checks" / bg_name / f"{layer_id}.jpg", "JPEG", quality=90, optimize=True)
        Image.fromarray(composed, "RGB").save(out_dir / "checks" / bg_name / f"{scene}_{layer_id}.jpg", "JPEG", quality=90, optimize=True)
    return {
        "file": f"webp/{scene}_{layer_id}.webp",
        "width": rgba.shape[1], "height": rgba.shape[0],
        "bytes": webp.stat().st_size,
        "alpha_channel": True,
        "tileable": False,
        "origin": "R15 fixture: PIL 程序化自制小样本",
        "process": "make_rgba (SW-015 R1 build_fixtures.py)",
    }


def write_design_ref_spec(out_dir: Path, spec: dict) -> dict:
    """写 spec.json + H-SW-016-FAKE.json + R-SW-016-FAKE.json (temp review) 到 _design/, 返回 design_ref dict."""
    design_dir = out_dir / "_design"
    design_dir.mkdir(exist_ok=True)
    spec_path = design_dir / "spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2))
    spec_sha = file_sha256(spec_path)
    handoff_path = design_dir / "H-SW-FAKE.json"
    handoff_path.write_text(json.dumps({
        "schema_version": 1,
        "id": "H-SW-FAKE",
        "task_id": spec.get("task_id", "SW-FAKE"),
        "revision": 1,
        "producer": "trae-design",
        "recipient": "antigravity",
        "head_commit": "a" * 40,
        "base_commit": "0" * 40,
    }, ensure_ascii=False, indent=2))
    return {
        "task_id": spec.get("task_id", "SW-FAKE"),
        "handoff": str(handoff_path.relative_to(ROOT)),
        "spec_file": str(spec_path.relative_to(ROOT)),
        "spec_sha256": spec_sha,
    }


def write_manifest(out_dir: Path, layers: list[dict], design_ref: dict, task_id: str = "SW-006", scene_id: str = "rainforest", api_attempts_total: int = 14) -> Path:
    manifest_path = out_dir / "manifest.json"
    for layer in layers:
        p = ROOT / layer["file"] if not Path(layer["file"]).is_absolute() else Path(layer["file"])
        if not p.is_file():
            p = out_dir / layer["file"]
        layer["sha256"] = file_sha256(p)
        layer["checks"] = [
            f"checks/alpha_mask/{Path(layer['file']).stem}.png",
            f"checks/black/{Path(layer['file']).stem}.jpg",
            f"checks/white/{Path(layer['file']).stem}.jpg",
            f"checks/magenta/{Path(layer['file']).stem}.jpg",
        ]
        layer.setdefault("limitations", ["R15 fixture"])
    manifest = {
        "schema_version": 1,
        "task_id": task_id,
        "revision": 1,
        "scene_id": scene_id,
        "producer": "minimax",
        "api_attempts_this_revision": 0,
        "api_attempts_total": api_attempts_total,
        "cost": "unknown",
        "layers": layers,
        "design_ref": design_ref,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest_path


def fixture_dirs() -> dict:
    FIX.mkdir(parents=True, exist_ok=True)
    names = [
        "sw015_positive_rainforest_canonical",
        "sw015_positive_forest_legacy_alias",
        "sw015_negative_empty_spec",
        "sw015_negative_duplicate_layer_id",
        "sw015_negative_unknown_type",
        "sw015_negative_wrong_canvas",
        "sw015_negative_layer_id_mismatch",
        "sw015_negative_legacy_alias_mismatch",
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
    """写 state/minimax.json 历史, R15 累计 baseline 14 + SW-006 单独 8 次."""
    state_path = ROOT / "docs" / "collaboration" / "state" / "minimax.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if not state_path.is_file():
        state_data = {
            "schema_version": 1,
            "agent": "minimax",
            "current_task": None,
            "previous_task": "SW-002",
            "status": "waiting",
            "branch": "codex/minimax/SW-002-clearing-lightshow",
            "head_commit": "f512d20316fab8cec588f2a7c6d94cec20979614",
            "cumulative_attempts": 14,  # project lifetime 历史 14 (SW-002 R1)
            "sw006_attempts": 0,       # SW-006 单任务 8 次单独预算
            "sw006_attempts_limit": 8,
            "sw015_attempts": 0,        # SW-015 零 API
            "revisions": [
                {"task_id": "SW-002", "revision": 1, "attempts": 14, "status": "accepted", "integrated_commit": "a5ad6dd634ab"},
            ],
            "fixture_state": {
                "r1_uses_history_baseline": True,
                "note": "R1 fixture 测试默认以累计 14 为基线; SW-006 单独 8 次预算; SW-015 0 API",
            },
        }
        state_path.write_text(json.dumps(state_data, ensure_ascii=False, indent=2))


# === fixture 生成 ===

def gen_positive_rainforest_canonical(dirs):
    """5 层 SW-012 proposed canonical id + type."""
    out = dirs["sw015_positive_rainforest_canonical"]
    layers_spec = [
        {"id": "mist", "type": "overlay", "parallax": 0.0, "at_meters": 90, "to_opacity": 0.55, "fade_meters": 20, "id_status": "proposed"},
        {"id": "trunks_canopy", "type": "parallax", "parallax": 0.3, "at_meters": 270, "to_opacity": 0.85, "fade_meters": 25, "id_status": "proposed"},
        {"id": "vines_light", "type": "parallax", "parallax": 0.6, "at_meters": 450, "to_opacity": 1.0, "fade_meters": 25, "id_status": "proposed"},
        {"id": "distant_glow", "type": "overlay", "parallax": 0.0, "at_meters": 675, "to_opacity": 0.85, "fade_meters": 25, "id_status": "proposed"},
        {"id": "glade", "type": "overlay", "parallax": 0.0, "at_meters": 855, "to_opacity": 0.9, "fade_meters": 20, "id_status": "proposed"},
    ]
    spec = {
        "schema_version": 1,
        "task_id": "SW-012",
        "revision": 1,
        "scene_id": "rainforest",
        "canvas": {"width": 1080, "height": 1920},
        "layers": layers_spec,
    }
    layers = []
    for ls in layers_spec:
        color = MIST if ls["id"] == "mist" else (TRUNK if ls["id"] == "trunks_canopy" else (VINE if ls["id"] == "vines_light" else (GLOW if ls["id"] == "distant_glow" else VINE)))
        rgba = make_rgba(ls["id"], color)
        art = write_layer_artifacts(ls["id"], out, rgba, "rainforest")
        art["layer_id"] = ls["id"]
        art["render_role"] = ls["type"]
        layers.append(art)
    design_ref = write_design_ref_spec(out, spec)
    write_manifest(out, layers, design_ref)


def gen_positive_forest_legacy_alias(dirs):
    """5 层 SW-011 已批 (公共模板同款) id + type."""
    out = dirs["sw015_positive_forest_legacy_alias"]
    layers_spec = [
        {"id": "tree_outline", "type": "parallax", "at_meters": 80, "to_opacity": 0.6, "fade_meters": 20, "id_status": "approved"},
        {"id": "tree_trunks", "type": "parallax", "at_meters": 240, "to_opacity": 0.7, "fade_meters": 25, "id_status": "approved"},
        {"id": "leaf_path", "type": "parallax", "at_meters": 400, "to_opacity": 0.8, "fade_meters": 25, "id_status": "approved"},
        {"id": "light_shows", "type": "overlay", "at_meters": 600, "to_opacity": 0.65, "fade_meters": 30, "id_status": "approved"},
        {"id": "clearing", "type": "overlay", "at_meters": 760, "to_opacity": 0.9, "fade_meters": 25, "id_status": "approved"},
    ]
    spec = {
        "schema_version": 1,
        "task_id": "SW-011",
        "revision": 1,
        "scene_id": "forest",
        "canvas": {"width": 1080, "height": 1920},
        "layers": layers_spec,
    }
    colors = [OUTLINE, TRUNK_F, LEAF, LIGHT, WARM]
    layers = []
    for ls, color in zip(layers_spec, colors):
        rgba = make_rgba(ls["id"], color)
        art = write_layer_artifacts(ls["id"], out, rgba, "forest")
        art["layer_id"] = ls["id"]
        art["render_role"] = ls["type"]
        layers.append(art)
    design_ref = write_design_ref_spec(out, spec)
    write_manifest(out, layers, design_ref, task_id="SW-002", scene_id="forest")


def gen_negative_empty_spec(dirs):
    out = dirs["sw015_negative_empty_spec"]
    spec = {
        "schema_version": 1,
        "task_id": "SW-012",
        "revision": 1,
        "scene_id": "rainforest",
        "canvas": {"width": 1080, "height": 1920},
        "layers": [],  # 空 spec
    }
    # 仍写 1 个真实 layer 让预检走到 spec 校验步骤
    rgba = make_rgba("mist", MIST)
    art = write_layer_artifacts("mist", out, rgba, "rainforest")
    art["layer_id"] = "mist"
    art["render_role"] = "overlay"
    design_ref = write_design_ref_spec(out, spec)
    write_manifest(out, [art], design_ref)


def gen_negative_duplicate_layer_id(dirs):
    out = dirs["sw015_negative_duplicate_layer_id"]
    # spec 含 duplicate id: trunks_canopy 出现两次
    spec = {
        "schema_version": 1,
        "task_id": "SW-012",
        "revision": 1,
        "scene_id": "rainforest",
        "canvas": {"width": 1080, "height": 1920},
        "layers": [
            {"id": "mist", "type": "overlay", "parallax": 0.0, "at_meters": 90, "to_opacity": 0.55, "fade_meters": 20, "id_status": "proposed"},
            {"id": "trunks_canopy", "type": "parallax", "at_meters": 270, "to_opacity": 0.85, "fade_meters": 25, "id_status": "proposed"},
            {"id": "trunks_canopy", "type": "parallax", "at_meters": 280, "to_opacity": 0.9, "fade_meters": 25, "id_status": "proposed"},  # duplicate
            {"id": "vines_light", "type": "parallax", "at_meters": 450, "to_opacity": 1.0, "fade_meters": 25, "id_status": "proposed"},
        ],
    }
    layers = []
    for ls in spec["layers"][:1] + [spec["layers"][2]] + [spec["layers"][3]]:
        rgba = make_rgba(ls["id"], MIST if ls["id"] == "mist" else (TRUNK if ls["id"] == "trunks_canopy" else VINE))
        art = write_layer_artifacts(ls["id"] + "_dup" if ls["id"] == "trunks_canopy" and ls["at_meters"] == 280 else ls["id"], out, rgba, "rainforest")
        art["layer_id"] = ls["id"]
        art["render_role"] = ls["type"]
        layers.append(art)
    design_ref = write_design_ref_spec(out, spec)
    write_manifest(out, layers, design_ref)


def gen_negative_unknown_type(dirs):
    out = dirs["sw015_negative_unknown_type"]
    spec = {
        "schema_version": 1,
        "task_id": "SW-012",
        "revision": 1,
        "scene_id": "rainforest",
        "canvas": {"width": 1080, "height": 1920},
        "layers": [
            {"id": "mist", "type": "background", "parallax": 0.0, "at_meters": 90, "to_opacity": 0.55, "fade_meters": 20, "id_status": "proposed"},  # 未知 type
            {"id": "trunks_canopy", "type": "parallax", "at_meters": 270, "to_opacity": 0.85, "fade_meters": 25, "id_status": "proposed"},
        ],
    }
    rgba1 = make_rgba("mist", MIST)
    art1 = write_layer_artifacts("mist", out, rgba1, "rainforest")
    art1["layer_id"] = "mist"
    art1["render_role"] = "background"  # 未知 render_role 也跟着错
    rgba2 = make_rgba("trunks_canopy", TRUNK)
    art2 = write_layer_artifacts("trunks_canopy", out, rgba2, "rainforest")
    art2["layer_id"] = "trunks_canopy"
    art2["render_role"] = "parallax"
    design_ref = write_design_ref_spec(out, spec)
    write_manifest(out, [art1, art2], design_ref)


def gen_negative_wrong_canvas(dirs):
    out = dirs["sw015_negative_wrong_canvas"]
    spec = {
        "schema_version": 1,
        "task_id": "SW-012",
        "revision": 1,
        "scene_id": "rainforest",
        "canvas": {"width": 768, "height": 1376},  # 错 canvas
        "layers": [
            {"id": "mist", "type": "overlay", "at_meters": 90, "to_opacity": 0.55, "fade_meters": 20, "id_status": "proposed"},
        ],
    }
    rgba = make_rgba("mist", MIST)
    art = write_layer_artifacts("mist", out, rgba, "rainforest")
    art["layer_id"] = "mist"
    art["render_role"] = "overlay"
    design_ref = write_design_ref_spec(out, spec)
    write_manifest(out, [art], design_ref)


def gen_negative_layer_id_mismatch(dirs):
    out = dirs["sw015_negative_layer_id_mismatch"]
    spec = {
        "schema_version": 1,
        "task_id": "SW-012",
        "revision": 1,
        "scene_id": "rainforest",
        "canvas": {"width": 1080, "height": 1920},
        "layers": [
            {"id": "mist", "type": "overlay", "at_meters": 90, "to_opacity": 0.55, "fade_meters": 20, "id_status": "proposed"},
            {"id": "trunks_canopy", "type": "parallax", "at_meters": 270, "to_opacity": 0.85, "fade_meters": 25, "id_status": "proposed"},
        ],
    }
    # manifest 含 spec 未声明的 random_layer
    rgba1 = make_rgba("mist", MIST)
    art1 = write_layer_artifacts("mist", out, rgba1, "rainforest")
    art1["layer_id"] = "mist"
    art1["render_role"] = "overlay"
    rgba2 = make_rgba("trunks_canopy", TRUNK)
    art2 = write_layer_artifacts("trunks_canopy", out, rgba2, "rainforest")
    art2["layer_id"] = "trunks_canopy"
    art2["render_role"] = "parallax"
    rgba3 = make_rgba("random_layer", VINE)
    art3 = write_layer_artifacts("random_layer", out, rgba3, "rainforest")
    art3["layer_id"] = "random_layer"
    art3["render_role"] = "overlay"
    design_ref = write_design_ref_spec(out, spec)
    write_manifest(out, [art1, art2, art3], design_ref)


def gen_negative_legacy_alias_mismatch(dirs):
    out = dirs["sw015_negative_legacy_alias_mismatch"]
    spec = {
        "schema_version": 1,
        "task_id": "SW-012",
        "revision": 1,
        "scene_id": "rainforest",
        "canvas": {"width": 1080, "height": 1920},
        "layers": [
            {"id": "mist", "type": "overlay", "at_meters": 90, "to_opacity": 0.55, "fade_meters": 20, "id_status": "proposed"},
            {"id": "trunks_canopy", "type": "parallax", "at_meters": 270, "to_opacity": 0.85, "fade_meters": 25, "id_status": "proposed"},
        ],
    }
    rgba1 = make_rgba("mist", MIST)
    art1 = write_layer_artifacts("mist", out, rgba1, "rainforest")
    art1["layer_id"] = "mist"
    art1["render_role"] = "mist_layer"  # legacy render_role 错误, 不在 CANONICAL_TYPES
    rgba2 = make_rgba("trunks_canopy", TRUNK)
    art2 = write_layer_artifacts("trunks_canopy", out, rgba2, "rainforest")
    art2["layer_id"] = "trunks_canopy"
    art2["render_role"] = "parallax"
    design_ref = write_design_ref_spec(out, spec)
    write_manifest(out, [art1, art2], design_ref)


def main() -> None:
    print("=== SW-015 R1 fixture 构建 ===")
    write_state_history()
    dirs = fixture_dirs()
    builders = [
        ("sw015_positive_rainforest_canonical", gen_positive_rainforest_canonical),
        ("sw015_positive_forest_legacy_alias", gen_positive_forest_legacy_alias),
        ("sw015_negative_empty_spec", gen_negative_empty_spec),
        ("sw015_negative_duplicate_layer_id", gen_negative_duplicate_layer_id),
        ("sw015_negative_unknown_type", gen_negative_unknown_type),
        ("sw015_negative_wrong_canvas", gen_negative_wrong_canvas),
        ("sw015_negative_layer_id_mismatch", gen_negative_layer_id_mismatch),
        ("sw015_negative_legacy_alias_mismatch", gen_negative_legacy_alias_mismatch),
    ]
    for name, fn in builders:
        try:
            fn(dirs)
            manifest_path = dirs[name] / "manifest.json"
            if manifest_path.exists():
                m = json.loads(manifest_path.read_text())
                layers_count = len(m.get("layers", []))
                print(f"  {name}: {layers_count} 层")
            else:
                print(f"  {name}: manifest 不存在")
        except Exception as e:
            print(f"  {name}: ERROR {e}")
            raise
    print(f"\nfixture root: {FIX.relative_to(ROOT)}")
    print(f"  total fixture dirs: {len(dirs)}")


if __name__ == "__main__":
    main()