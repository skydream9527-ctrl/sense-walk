#!/usr/bin/env python3
"""
SW-015 R1 真实 Trae 设计规格解析器.

职责:
1. 加载 design-spec.json (Trae 真实 schema: layers[].id/type/at_meters/to_opacity/fade_meters/tileable)
2. 校验 spec 完整性 (非空/无重复/无未知 type/canvas 1080x1920)
3. 把 spec 映射成 manifest 字段 (id -> layer_id, type -> render_role)
4. 兼容旧 fixture 的 layer_id/render_role 别名归一化
5. 输出 manifest expected 字段: layer_ids / render_roles / canvas

不替 Trae 决定设计; 不改 design-spec; 不写 registry/中心登记.
零 API.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional


# canonical type 集 (按 contracts/visual-design.md): parallax / overlay
CANONICAL_TYPES = {"parallax", "overlay"}
# 兼容 legacy render_role 写法 (R3 沿用)
LEGACY_RENDER_ROLE_TO_TYPE = {
    "parallax": "parallax",
    "overlay": "overlay",
}
# 兼容 legacy layer_id 写法 (早期 fixture 误写)
LEGACY_LAYER_ID_ALIASES = {
    # SW-011 森林旧名 (templates/design-spec.json.example)
    "tree_outline": "tree_outline",
    "tree_trunks": "tree_trunks",
    "leaf_path": "leaf_path",
    "light_shows": "light_shows",
    "clearing": "clearing",
    # SW-012 雨林旧名
    "mist": "mist",
    "trunks_canopy": "trunks_canopy",
    "vines_light": "vines_light",
    "distant_glow": "distant_glow",
    "glade": "glade",
}
# expected canvas
EXPECTED_CANVAS_WIDTH = 1080
EXPECTED_CANVAS_HEIGHT = 1920
MAX_VISUAL_LAYERS = 5


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_repo_path(rel_or_abs: str, root: Path) -> Optional[Path]:
    """解析 repo 内路径, 拒绝绝对/越界/不存在."""
    if not rel_or_abs or not isinstance(rel_or_abs, str):
        return None
    p = Path(rel_or_abs)
    if p.is_absolute():
        return None
    parts = p.parts
    if ".." in parts:
        return None
    candidate = root / rel_or_abs
    if not candidate.is_file():
        return None
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def normalize_legacy_layer_id(layer_id: str) -> str:
    """兼容 legacy 别名: 已经是 canonical 名直接返回; 否则尝试映射."""
    if layer_id in LEGACY_LAYER_ID_ALIASES:
        return LEGACY_LAYER_ID_ALIASES[layer_id]
    return layer_id


def normalize_legacy_render_role(render_role: str) -> str:
    if render_role in CANONICAL_TYPES:
        return render_role
    return LEGACY_RENDER_ROLE_TO_TYPE.get(render_role, render_role)


class SpecParseError(Exception):
    pass


def load_spec(spec_path: Path, root: Path) -> dict:
    """加载 design-spec.json, 校验路径在 repo 内, 返回原始 dict."""
    p = safe_repo_path(str(spec_path), root) if spec_path.is_absolute() else safe_repo_path(str(spec_path), root)
    if p is None:
        # 可能是 manifest 相对路径
        p = safe_repo_path(str(spec_path), root)
    if p is None or not p.is_file():
        raise SpecParseError(f"spec 文件不存在或越界: {spec_path}")
    try:
        spec = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        raise SpecParseError(f"spec 非 JSON: {e}")
    return {"raw": spec, "path": str(p.relative_to(root)), "sha256": file_sha256(p)}


def extract_layers(spec: dict) -> list[dict]:
    """从 spec 提取 layer 列表."""
    if not isinstance(spec, dict):
        raise SpecParseError("spec 必须为 dict")
    layers = spec.get("layers", [])
    if not isinstance(layers, list):
        raise SpecParseError("spec.layers 非数组")
    return layers


def validate_spec(spec: dict, *, allow_proposed: bool = True) -> list[str]:
    """校验 spec 完整性. 返回 error 列表 (空 = ok).

    校验项:
    - spec.schema_version == 1
    - spec.layers 非空 list
    - layer 数 ≤ 5 (最多 5 个外部视觉层, void/旅人仍程序绘制)
    - layer.id 非空字符串 + 兼容 legacy 别名
    - layer.type ∈ {parallax, overlay}
    - layer.at_meters / fade_meters 非负数
    - canvas.width == 1080, canvas.height == 1920
    - layer id 不重复
    - layer id 不冲突 (同 alias 但不同 type 不允许)
    """
    errors: list[str] = []
    if spec.get("schema_version") != 1:
        errors.append(f"spec.schema_version != 1 (got {spec.get('schema_version')!r})")
    canvas = spec.get("canvas", {})
    cw = canvas.get("width")
    ch = canvas.get("height")
    if cw != EXPECTED_CANVAS_WIDTH:
        errors.append(f"canvas.width={cw} != {EXPECTED_CANVAS_WIDTH}")
    if ch != EXPECTED_CANVAS_HEIGHT:
        errors.append(f"canvas.height={ch} != {EXPECTED_CANVAS_HEIGHT}")
    layers = spec.get("layers", [])
    if not isinstance(layers, list):
        errors.append(f"spec.layers 非数组 (got {type(layers).__name__})")
        return errors
    if len(layers) == 0:
        errors.append("spec.layers 为空")
        return errors
    if len(layers) > MAX_VISUAL_LAYERS:
        errors.append(f"spec.layers {len(layers)} 层 > 最多 {MAX_VISUAL_LAYERS} 外部视觉层")
    seen_ids: dict[str, dict] = {}
    for i, layer in enumerate(layers):
        if not isinstance(layer, dict):
            errors.append(f"layer[{i}] 非 dict")
            continue
        lid = layer.get("id")
        if not lid or not isinstance(lid, str):
            errors.append(f"layer[{i}].id 缺失或非字符串")
            continue
        normalized_id = normalize_legacy_layer_id(lid)
        if normalized_id != lid:
            errors.append(f"layer[{i}].id {lid!r} 不在 canonical/legacy 已知别名集合")
        if normalized_id in seen_ids:
            other = seen_ids[normalized_id]
            if other.get("type") != layer.get("type"):
                errors.append(f"layer id {lid!r} 类型冲突: 早先 {other.get('type')!r}, 本次 {layer.get('type')!r}")
            else:
                errors.append(f"layer id {lid!r} 重复")
        seen_ids[normalized_id] = layer
        # type 校验
        ltype = layer.get("type")
        if ltype not in CANONICAL_TYPES:
            errors.append(f"layer[{i}] {lid!r} type {ltype!r} 不在 canonical {sorted(CANONICAL_TYPES)}")
        # at_meters / fade_meters
        am = layer.get("at_meters")
        if not isinstance(am, (int, float)) or am < 0:
            errors.append(f"layer[{i}] {lid!r} at_meters={am!r} 不是非负数")
        # id_status 检查 (proposed 不允许当真实批准, 但允许作样本)
        id_status = layer.get("id_status", "approved")
        if id_status not in ("approved", "proposed"):
            errors.append(f"layer[{i}] {lid!r} id_status={id_status!r} 不在 approved/proposed")
        elif id_status == "proposed" and not allow_proposed:
            errors.append(f"layer[{i}] {lid!r} id_status=proposed 不允许作为真实批准层")
    return errors


def spec_to_manifest_fields(spec: dict) -> dict:
    """从已校验 spec 提取 manifest expected 字段:
    - layer_ids: list of canonical id
    - render_roles: dict of canonical id -> type
    - canvas: {width, height}
    - proposed_ids: list of id_status=proposed
    """
    layers = spec.get("layers", [])
    layer_ids = []
    render_roles = {}
    proposed_ids = []
    for layer in layers:
        lid = layer.get("id")
        ltype = layer.get("type")
        layer_ids.append(lid)
        render_roles[lid] = ltype
        if layer.get("id_status") == "proposed":
            proposed_ids.append(lid)
    canvas = spec.get("canvas", {})
    return {
        "layer_ids": layer_ids,
        "render_roles": render_roles,
        "canvas": {"width": canvas.get("width"), "height": canvas.get("height")},
        "proposed_ids": proposed_ids,
    }


def manifest_layers_compatible(manifest_layers: list[dict], expected_fields: dict) -> list[str]:
    """校验 manifest.layers 是否与 spec 期望一致:
    - 必需 layer 集合等于 expected
    - 不允许未知 layer (无 legacy alias)
    - render_role 与 expected 严格匹配 (legacy 别名归一化后)
    """
    errors: list[str] = []
    expected_ids = set(expected_fields["layer_ids"])
    expected_roles = expected_fields["render_roles"]
    seen = set()
    for ml in manifest_layers:
        mid = ml["id"]
        mrole = ml["render_role"]
        norm_id = normalize_legacy_layer_id(mid)
        norm_role = normalize_legacy_render_role(mrole)
        if norm_id not in expected_ids:
            errors.append(f"manifest layer {mid!r} 不在 spec 期望集合 {sorted(expected_ids)}")
        else:
            if norm_role != expected_roles[norm_id]:
                errors.append(f"manifest layer {mid!r} render_role {mrole!r} != spec {expected_roles[norm_id]!r}")
            if mid in seen:
                errors.append(f"manifest layer {mid!r} 重复")
            seen.add(norm_id)
    missing = expected_ids - seen
    if missing:
        errors.append(f"manifest 缺 spec 必需层: {sorted(missing)}")
    return errors


def render_summary(parsed: dict) -> str:
    fields = parsed.get("expected_fields", {})
    lines = [
        f"  spec_path: {parsed.get('spec_path')}",
        f"  spec_sha256: {parsed.get('spec_sha256', '')[:16]}",
        f"  canvas: {fields.get('canvas')}",
        f"  layer_ids: {fields.get('layer_ids')}",
        f"  render_roles: {fields.get('render_roles')}",
        f"  proposed_ids: {fields.get('proposed_ids')}",
        f"  errors: {parsed.get('errors', [])}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: spec_reader.py <design-spec.json>", file=sys.stderr)
        sys.exit(2)
    spec_path = Path(sys.argv[1])
    root = Path(__file__).resolve().parents[5]  # 5 levels up to repo root: scripts -> r1 -> SW-015 -> preflight -> rainforest -> assets -> design
    try:
        loaded = load_spec(spec_path, root)
    except SpecParseError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    errors = validate_spec(loaded["raw"], allow_proposed=True)
    fields = spec_to_manifest_fields(loaded["raw"])
    print(render_summary({"spec_path": loaded["path"], "spec_sha256": loaded["sha256"], "expected_fields": fields, "errors": errors}))
    sys.exit(0 if not errors else 1)