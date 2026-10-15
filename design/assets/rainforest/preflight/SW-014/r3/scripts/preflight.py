#!/usr/bin/env python3
"""
SW-014 R3 预检 (零 API, 修复 R2-01~R2-05 + R3-06~R3-07).

R3 相对 R2 的关键差异:
- 硬编码 KNOWN_LAYERS 改为动态读取 design-spec.json 的 layers[*].layer_id 集合
- 默认入口严格: 拒绝 manifest 含 _fixture_mode / _expected_registry_status 字段
  (测试 fixture 模式必须显式 --fixture-mode CLI 旗标)
- alpha 像素: 统计 alpha<127 的真实半透明像素 (而非 alpha>0)
- 检查图清单强制完整 (黑/白/洋红/alpha_mask 4 件套必须存在)
- API 账本非负整数 + 跨 revision 累计 (读 state/minimax.json 历史账本)
- dry_run 严格批准链: registry 引用 latest_handoff + latest_review, 核对当前 head
  commit / spec sha256 / registry status 都匹配
- 真实超预算隔离反例: 写 >=400KB 单图 + >=2MB 全景

R1/R2 历史保留不动 (R2-01~R2-05 留作 R3 对比基线).
不替 Trae 决定雨林构图/色板.
不重置 R1/R2 已发生账本尝试 (累计账本读 state/minimax.json).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PIL import Image
import numpy as np

# --- repo 根定位 ---

def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(20):
        if (cur / "docs" / "collaboration").is_dir() and (cur / "design" / "assets").is_dir():
            return cur
        if cur.parent == cur:
            raise RuntimeError(f"repo 根未找到, 起点 {start}")
        cur = cur.parent
    raise RuntimeError(f"repo 根路径过深, 起点 {start}")


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = find_repo_root(SCRIPT_DIR)
try:
    git_root = subprocess.check_output(["git", "-C", str(SCRIPT_DIR), "rev-parse", "--show-toplevel"], text=True).strip()
except Exception:
    git_root = None
if git_root and Path(git_root).resolve() != ROOT:
    raise RuntimeError(f"ROOT 推导与 git toplevel 不一致: {ROOT} vs {git_root}")


# --- 协议常量 ---

CONTRACT_VERSION = "visual-assets v1"
MAX_LAYER_BYTES = 400 * 1024       # 400 KB per layer
MAX_SCENE_BYTES = 2 * 1024 * 1024  # 2 MB per scene
ACCEPTED_DIMENSIONS = {(768, 1376), (1080, 1920)}  # 接受 768x1376 森林历史 + 1080x1920 项目基准
ALPHA_HALF_TRANSPARENT_THRESHOLD = 127  # alpha < 127 视为半透明/透明 (R3-02 修正)
MIN_ALPHA_HALF_TRANSPARENT_FRACTION = 0.001  # 至少 0.1% 半透明像素

# 必需检查图 4 件套 (R3-03 强制)
REQUIRED_CHECK_BACKGROUNDS = ("alpha_mask", "black", "white", "magenta")

# 任务范围 + scene 合法性检查
TASK_SCENE_VALID = {
    "SW-002": {"forest"},
    "SW-006": {"rainforest"},
    "SW-014": {"rainforest"},  # 预检工具
}

# task_id 与 scene_id 必需 layers / 尺寸的 fallback (无 design-spec 时用, 仅 SW-002 森林)
# R3-06: SW-006 雨林图层集合必须从 design-spec 动态读取, 不再硬编码
KNOWN_LAYERS_FALLBACK = {
    ("SW-002", "forest"): {"clearing", "light_shows"},  # SW-002 森林仅修图, 2 层
}

# 历史账本 (R3-04 跨 revision 累计验证)
MINIMAX_STATE_PATH = ROOT / "docs" / "collaboration" / "state" / "minimax.json"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_repo_path(rel_or_abs: str, manifest_dir: Path) -> Optional[Path]:
    if not rel_or_abs or not isinstance(rel_or_abs, str):
        return None
    p = Path(rel_or_abs)
    if p.is_absolute():
        return None
    parts = p.parts
    if ".." in parts:
        return None
    candidate = ROOT / rel_or_abs
    if not candidate.is_file():
        candidate = manifest_dir / rel_or_abs
        if not candidate.is_file():
            return None
    try:
        candidate.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return None
    return candidate


def real_decode_image(path: Path) -> dict:
    """R3-02: alpha 像素按 alpha<127 半透明统计 (非 alpha>0)."""
    try:
        img = Image.open(path)
        img.verify()
        img = Image.open(path)
        img.load()
        w, h = img.size
        half_transparent_frac = 0.0
        if img.mode in ("RGBA", "LA"):
            arr = np.asarray(img.convert("RGBA"))
            a = arr[..., 3]
            if a.size > 0:
                # R3-02 修正: 真正半透明 alpha < 127 像素比例
                half_transparent_frac = float((a < ALPHA_HALF_TRANSPARENT_THRESHOLD).sum()) / a.size
        return {
            "is_image": True,
            "mode": img.mode,
            "width": w,
            "height": h,
            "half_transparent_fraction": half_transparent_frac,
        }
    except Exception as e:
        return {"is_image": False, "error": str(e)}


def load_design_spec(design_ref: dict, manifest_dir: Path) -> Optional[dict]:
    """R3-06: 从 design_ref.spec_file 读 design-spec.json, 取得 layers 集合 + 基准尺寸.
    失败返回 None.
    """
    spec_file = design_ref.get("spec_file")
    spec_sha_expected = design_ref.get("spec_sha256")
    if not spec_file or spec_sha_expected in (None, "", "PENDING", "PENDING_SW012_APPROVAL"):
        return None
    sp = safe_repo_path(spec_file, manifest_dir)
    if sp is None or not sp.is_file():
        return None
    try:
        spec = json.loads(sp.read_text())
        if file_sha256(sp) != spec_sha_expected:
            return None
        return spec
    except json.JSONDecodeError:
        return None


def extract_spec_layers(spec: dict) -> list[dict]:
    """从 design-spec.json 提取 layer 列表.
    兼容两种 schema:
    - design-spec.json: {"layers": [{"layer_id": "..."}, ...]}
    - design-spec.json: {"layers": {"layer_id": "..."}} (dict 形式)
    """
    if not spec or not isinstance(spec, dict):
        return []
    layers = spec.get("layers", [])
    out = []
    if isinstance(layers, list):
        for l in layers:
            if isinstance(l, dict):
                lid = l.get("layer_id")
                if lid:
                    out.append(l)
    elif isinstance(layers, dict):
        for lid, info in layers.items():
            out.append({"layer_id": lid, **(info or {})})
    return out


def load_registry() -> dict:
    return json.loads((ROOT / "docs" / "collaboration" / "registry.json").read_text())


def load_minimax_history() -> dict:
    """读 state/minimax.json 历史账本 (R3-04 跨 revision 累计)."""
    if not MINIMAX_STATE_PATH.is_file():
        return {"revisions": [], "cumulative_attempts": 0}
    try:
        return json.loads(MINIMAX_STATE_PATH.read_text())
    except json.JSONDecodeError:
        return {"revisions": [], "cumulative_attempts": 0}


def report(ok: bool, name: str, detail: str = "") -> dict:
    return {"ok": ok, "name": name, "detail": detail}


def reject_manifest_fixture_keys(manifest: dict, checks: list[dict]) -> None:
    """R3-01: 生产入口严格拒绝 _fixture_mode / _expected_registry_status 字段.
    测试 fixture 模式必须显式 --fixture-mode CLI 旗标.
    """
    for key in ("_fixture_mode", "_expected_registry_status"):
        if key in manifest:
            checks.append(report(False, f"manifest_field_{key}_forbidden", f"生产入口禁止 {key} 字段, 必须用 --fixture-mode CLI 旗标"))
        elif key in (manifest.get("design_ref") or {}):
            checks.append(report(False, f"design_ref_field_{key}_forbidden", f"生产入口禁止 design_ref.{key} 字段, 必须用 --fixture-mode CLI 旗标"))


def check_required_checks(layer: dict, layer_id: str, manifest_dir: Path, checks: list[dict]) -> None:
    """R3-03: 强制检查 4 底色检查图全部存在. 即使 manifest.checks=[] 也按 layer_id + REQUIRED_CHECK_BACKGROUNDS 推算必备集合."""
    declared = layer.get("checks", [])
    declared_paths = {str(c) for c in declared if isinstance(c, str)}
    # 推算必备路径 (按 visual-assets 合同命名: checks/<bg>/rainforest_<lid>.<ext>)
    ext_map = {"alpha_mask": "png", "black": "jpg", "white": "jpg", "magenta": "jpg"}
    for bg in REQUIRED_CHECK_BACKGROUNDS:
        ext = ext_map[bg]
        # 兼容各种命名: rainforest_<lid>.<ext> 或 <lid>.<ext>
        candidate_names = [
            f"checks/{bg}/rainforest_{layer_id}.{ext}",
            f"checks/{bg}/{layer_id}.{ext}",
        ]
        # 先看 manifest 是否声明了
        found = None
        for name in candidate_names:
            if name in declared_paths:
                found = name
                break
        # 即便 manifest 没声明, 也按文件名约定校验实际存在 (强制完备性)
        if found is None:
            for name in candidate_names:
                p = safe_repo_path(name, manifest_dir)
                if p is not None and p.is_file():
                    found = name
                    break
        if found is None:
            checks.append(report(False, f"layer_{layer_id}_check_required_missing", f"缺必需 {bg} 检查图 (按 visual-assets 合同/搜索)"))
        elif not safe_repo_path(found, manifest_dir):
            checks.append(report(False, f"layer_{layer_id}_check_required_path", f"必需 {bg} 检查图路径越界/不存在: {found}"))
        else:
            checks.append(report(True, f"layer_{layer_id}_check_{bg}", f"存在: {found}"))


def check_api_budget(manifest: dict, checks: list[dict]) -> None:
    """R3-04: API 账本非负整数 + 跨 revision 累计验证."""
    for key in ("api_attempts_this_revision", "api_attempts_total"):
        v = manifest.get(key)
        if key not in manifest:
            checks.append(report(False, f"api_field_{key}", "缺失"))
        elif not isinstance(v, int) or v < 0:
            checks.append(report(False, f"api_field_{key}", f"必须为非负整数, 实际 {v!r}"))
        else:
            checks.append(report(True, f"api_field_{key}", f"{v}"))
    cost = manifest.get("cost")
    if "cost" not in manifest:
        checks.append(report(False, "api_field_cost", "缺失"))
    else:
        checks.append(report(True, "api_field_cost", f"{cost}"))

    # 跨 revision 累计: 读 state/minimax.json 历史
    this_rev = manifest.get("api_attempts_this_revision")
    declared_total = manifest.get("api_attempts_total")
    if isinstance(this_rev, int) and isinstance(declared_total, int) and this_rev < 0:
        # 已 defensive
        pass
    state = load_minimax_history()
    history_total = state.get("cumulative_attempts", 0)
    # 累计声明必须 >= 历史账本 (不容许重置, 也不容许负数/小于历史)
    if isinstance(declared_total, int) and declared_total < history_total:
        checks.append(report(False, "api_cumulative_regression", f"累计 api_attempts_total={declared_total} < state/minimax.json 历史 {history_total} (不允许重置)"))
    elif isinstance(declared_total, int) and isinstance(this_rev, int) and declared_total < this_rev:
        checks.append(report(False, "api_cumulative_consistency", f"累计 {declared_total} < 本轮 {this_rev} (累计必须 >= 本轮本数)"))
    else:
        checks.append(report(True, "api_cumulative_check", f"累计={declared_total}, 历史={history_total}, 本轮={this_rev}"))


def check_approval_chain(design_ref: dict, manifest_dir: Path, checks: list[dict]) -> None:
    """R3-05: 严格批准链.
    验证:
    - handoff 路径存在 + producer in (trae-design, antigravity)
    - handoff head_commit 是 40-char SHA
    - spec_file 存在 + spec_sha256 匹配实际文件
    - registry task status == accepted
    - registry task.latest_handoff 指向的 handoff head 与 design_ref.handoff 引用的 handoff head 一致
    - registry task.latest_review 指向的 review verdict == approved + reviewed_commit 与 handoff head 一致
    """
    if not isinstance(design_ref, dict):
        checks.append(report(False, "design_ref_type", f"expected dict, got {type(design_ref).__name__}"))
        return
    # task_id (R3 修正: 用 SW-0xx 完整格式正则匹配, 接受 SW-001~SW-099)
    ref_task = design_ref.get("task_id", "")
    if not re.fullmatch(r"SW-0\d{2}", ref_task):
        checks.append(report(False, "design_ref_task_id", f"task_id 异常 (非 SW-0xx 格式): {ref_task}"))
    else:
        checks.append(report(True, "design_ref_task_id", ref_task))
    # handoff 路径
    handoff = design_ref.get("handoff", "")
    handoff_data = None
    if not handoff or not isinstance(handoff, str):
        checks.append(report(False, "design_ref_handoff_missing", f"handoff 缺失: {handoff!r}"))
    else:
        hp = safe_repo_path(handoff, manifest_dir)
        if hp is None:
            checks.append(report(False, "design_ref_handoff_path", f"handoff 路径越界/不存在/绝对: {handoff}"))
        elif not hp.is_file():
            checks.append(report(False, "design_ref_handoff_file", f"handoff 文件不存在: {handoff}"))
        else:
            try:
                handoff_data = json.loads(hp.read_text())
                h_producer = handoff_data.get("producer", "")
                if h_producer not in ("trae-design", "antigravity"):
                    checks.append(report(False, "design_ref_handoff_producer", f"handoff producer 异常: {h_producer}"))
                else:
                    checks.append(report(True, "design_ref_handoff_producer", h_producer))
                h_head = handoff_data.get("head_commit", "")
                if not h_head or not re.fullmatch(r"[0-9a-f]{40}", h_head):
                    checks.append(report(False, "design_ref_handoff_head", f"handoff head_commit 不是 40-char SHA: {h_head!r}"))
                else:
                    checks.append(report(True, "design_ref_handoff_head", h_head[:12]))
            except json.JSONDecodeError:
                checks.append(report(False, "design_ref_handoff_json", f"handoff 不是 JSON: {handoff}"))
    # spec_file
    spec_file = design_ref.get("spec_file", "")
    spec_sha_expected = design_ref.get("spec_sha256", "")
    if spec_sha_expected in (None, "", "PENDING", "PENDING_SW012_APPROVAL"):
        checks.append(report(False, "design_ref_spec_sha_stale", f"spec_sha256 是占位: {spec_sha_expected!r}"))
    if not spec_file or not isinstance(spec_file, str):
        checks.append(report(False, "design_ref_spec_file_missing", f"spec_file 缺失: {spec_file!r}"))
    else:
        sp = safe_repo_path(spec_file, manifest_dir)
        if sp is None:
            checks.append(report(False, "design_ref_spec_file_path", f"spec_file 路径越界/不存在: {spec_file}"))
        elif not sp.is_file():
            checks.append(report(False, "design_ref_spec_file_missing", f"spec_file 不存在: {spec_file}"))
        else:
            actual_sha = file_sha256(sp)
            if spec_sha_expected and actual_sha != spec_sha_expected:
                checks.append(report(False, "design_ref_spec_sha_mismatch", f"manifest {spec_sha_expected[:16]} != 实际 {actual_sha[:16]}"))
            else:
                checks.append(report(True, "design_ref_spec_sha", actual_sha[:16]))
    # registry task 全链条
    reg = load_registry()
    task_entry = next((t for t in reg.get("tasks", []) if t.get("id") == ref_task), None)
    if not task_entry:
        checks.append(report(False, "design_ref_registry_task", f"registry 无 task {ref_task}"))
        return
    actual_status = task_entry.get("status")
    if actual_status != "accepted":
        checks.append(report(False, "design_ref_registry_status", f"task {ref_task} status={actual_status} != accepted (R3 真实模式)"))
    # 当前批准 handoff head
    approved_handoff_rel = task_entry.get("latest_handoff")
    approved_review_rel = task_entry.get("latest_review")
    if approved_handoff_rel and handoff_data:
        ap = safe_repo_path(approved_handoff_rel, manifest_dir)
        if ap is None or not ap.is_file():
            checks.append(report(False, "design_ref_approval_handoff_missing", f"registry latest_handoff 不存在: {approved_handoff_rel}"))
        else:
            try:
                ap_data = json.loads(ap.read_text())
                ap_head = ap_data.get("head_commit", "")
                in_head = handoff_data.get("head_commit", "")
                if in_head != ap_head:
                    checks.append(report(False, "design_ref_approval_chain_handoff_head", f"当前 handoff head {in_head[:12]} != registry 已批准 handoff head {ap_head[:12]} (批准链不匹配)"))
                else:
                    checks.append(report(True, "design_ref_approval_chain_handoff_head", f"匹配 approved handoff head {in_head[:12]}"))
            except json.JSONDecodeError:
                checks.append(report(False, "design_ref_approval_handoff_json", f"approved handoff 非 JSON"))
    elif approved_handoff_rel is None:
        checks.append(report(False, "design_ref_approval_handoff_null", f"task {ref_task} registry.latest_handoff=null (无批准 handoff)"))
    if approved_review_rel:
        rp = safe_repo_path(approved_review_rel, manifest_dir)
        if rp is None or not rp.is_file():
            checks.append(report(False, "design_ref_approval_review_missing", f"registry latest_review 不存在: {approved_review_rel}"))
        else:
            try:
                rv = json.loads(rp.read_text())
                if rv.get("verdict") != "approved":
                    checks.append(report(False, "design_ref_approval_review_verdict", f"review verdict={rv.get('verdict')!r} != approved"))
                else:
                    checks.append(report(True, "design_ref_approval_review_verdict", "approved"))
                rv_reviewed = rv.get("reviewed_commit", "")
                in_head = (handoff_data or {}).get("head_commit", "")
                if in_head and rv_reviewed != in_head:
                    checks.append(report(False, "design_ref_approval_review_head", f"review reviewed_commit {rv_reviewed[:12]} != handoff head {in_head[:12]}"))
                else:
                    checks.append(report(True, "design_ref_approval_review_head", f"匹配 reviewed_commit {rv_reviewed[:12]}"))
            except json.JSONDecodeError:
                checks.append(report(False, "design_ref_approval_review_json", f"approved review 非 JSON"))
    elif approved_review_rel is None:
        checks.append(report(False, "design_ref_approval_review_null", f"task {ref_task} registry.latest_review=null (无批准 review)"))


# --- 主预检 ---

def preflight(manifest_path: Path, fixture_mode: bool = False) -> dict:
    """预检 manifest.
    fixture_mode=True: 允许 manifest 含 _fixture_mode/_expected_registry_status, 用于测试 harness.
    fixture_mode=False (默认): 严格拒绝这些字段 (R3-01).
    """
    if not manifest_path.is_file():
        return {"status": "failed", "error": f"manifest not found: {manifest_path}", "checks": [], "summary": {"total": 0, "passed": 0, "failed": 0}, "fixture_mode": fixture_mode}

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        return {"status": "failed", "error": f"manifest JSON 解析失败: {e}", "checks": [], "summary": {"total": 0, "passed": 0, "failed": 0}, "fixture_mode": fixture_mode}

    checks: list[dict] = []
    manifest_dir = manifest_path.parent

    # 1. schema_version
    if manifest.get("schema_version") != 1:
        checks.append(report(False, "schema_version", f"expected 1, got {manifest.get('schema_version')}"))
    else:
        checks.append(report(True, "schema_version", "1"))

    # 2. producer 必须是 minimax
    if manifest.get("producer") != "minimax":
        checks.append(report(False, "field_producer", f"expected minimax, got {manifest.get('producer')}"))
    else:
        checks.append(report(True, "field_producer", "minimax"))

    # R3-01: fixture 模式隔离. 默认入口拒绝 _fixture_mode/_expected_registry_status.
    if not fixture_mode:
        reject_manifest_fixture_keys(manifest, checks)
    else:
        # fixture 模式: 显式标注, 不算违规
        checks.append(report(True, "fixture_mode", "启用 --fixture-mode CLI 旗标"))

    # 3. task_id 范围 + scene_id
    task_id = manifest.get("task_id", "")
    scene_id = manifest.get("scene_id", "")
    if task_id in TASK_SCENE_VALID:
        if scene_id not in TASK_SCENE_VALID[task_id]:
            checks.append(report(False, "task_scene_mismatch", f"task {task_id} 不允许 scene {scene_id}"))
        else:
            checks.append(report(True, "task_scene", f"{task_id} + {scene_id}"))
    else:
        checks.append(report(False, "task_id_unknown", f"task {task_id} 不在 minimax 范围 {list(TASK_SCENE_VALID.keys())}"))

    # R3-06: 动态读取 design-spec 决定 layer 集合
    design_ref = manifest.get("design_ref")
    spec_layers_dict: Optional[list[str]] = None
    if scene_id == "rainforest" and task_id == "SW-006" and isinstance(design_ref, dict):
        spec = load_design_spec(design_ref, manifest_dir)
        if spec is not None:
            spec_layers_dict = [l["layer_id"] for l in extract_spec_layers(spec)]
            checks.append(report(True, "design_spec_dynamic_read", f"spec layers={spec_layers_dict}"))
        else:
            # SW-006 rainforest 必须从 spec 读 (不能 fallback)
            checks.append(report(False, "design_spec_dynamic_required", f"SW-006 rainforest 必须 design-spec 含 layers 字段; 但 spec 加载失败 (SHA 不匹配或路径错)"))

    # fallback 集合 (仅 SW-002 森林)
    fallback_layers = KNOWN_LAYERS_FALLBACK.get((task_id, scene_id), set())
    if spec_layers_dict is not None:
        known_for_task = set(spec_layers_dict)
    else:
        known_for_task = fallback_layers

    # 4. layers 检查
    layers = manifest.get("layers", [])
    layer_ids_seen: set[str] = set()
    total_bytes = 0

    for layer in layers:
        lid = layer.get("layer_id", "?")
        if not lid or lid == "?":
            checks.append(report(False, "layer_id_missing", "layer_id 字段缺失"))
            continue
        if lid in layer_ids_seen:
            checks.append(report(False, f"layer_{lid}_duplicate", f"layer_id 重复: {lid}"))
        layer_ids_seen.add(lid)

        if known_for_task and lid not in known_for_task:
            checks.append(report(False, f"layer_{lid}_unknown", f"layer_id 不在已知集合 {sorted(known_for_task)}"))

        rel_file = layer.get("file", "")
        file_path = safe_repo_path(rel_file, manifest_dir)
        if file_path is None:
            checks.append(report(False, f"layer_{lid}_file_missing", f"文件不存在 / 越界 / 绝对路径: {rel_file}"))
            # 仍跑检查图/R3-03 (按 layer_id 推断必备检查图)
            check_required_checks(layer, lid, manifest_dir, checks)
            continue
        actual_bytes = file_path.stat().st_size
        total_bytes += actual_bytes
        expected_bytes = layer.get("bytes", 0)
        if expected_bytes != actual_bytes:
            checks.append(report(False, f"layer_{lid}_bytes", f"manifest {expected_bytes} != actual {actual_bytes}"))
        else:
            checks.append(report(True, f"layer_{lid}_bytes", f"{actual_bytes}"))
        actual_hash = file_sha256(file_path)
        expected_hash = layer.get("sha256", "")
        if expected_hash != actual_hash:
            checks.append(report(False, f"layer_{lid}_sha256", f"manifest {expected_hash[:16]} != actual {actual_hash[:16]}"))
        else:
            checks.append(report(True, f"layer_{lid}_sha256", actual_hash[:16]))

        info = real_decode_image(file_path)
        if not info.get("is_image"):
            checks.append(report(False, f"layer_{lid}_decode", f"非图/坏图: {info.get('error', '?')}"))
            check_required_checks(layer, lid, manifest_dir, checks)
            continue
        checks.append(report(True, f"layer_{lid}_decode", f"{info['mode']} {info['width']}x{info['height']}"))
        checks.append(report(True, f"layer_{lid}_decode", f"{info['mode']} {info['width']}x{info['height']}"))
        actual_w, actual_h = info["width"], info["height"]
        manifest_w, manifest_h = layer.get("width", 0), layer.get("height", 0)
        if (actual_w, actual_h) != (manifest_w, manifest_h):
            checks.append(report(False, f"layer_{lid}_size_manifest", f"实际 {actual_w}x{actual_h} != manifest {manifest_w}x{manifest_h}"))
        if (actual_w, actual_h) not in ACCEPTED_DIMENSIONS:
            checks.append(report(False, f"layer_{lid}_size_unsupported", f"{actual_w}x{actual_h} 不在 {ACCEPTED_DIMENSIONS}"))
        else:
            checks.append(report(True, f"layer_{lid}_size", f"{actual_w}x{actual_h}"))
        # R3-07: 真实超 400 KB 单图 (旁路 fail 条件: 当 bytes > MAX_LAYER_BYTES)
        if actual_bytes > MAX_LAYER_BYTES:
            checks.append(report(False, f"layer_{lid}_budget_real", f"实际 {actual_bytes} > {MAX_LAYER_BYTES} (400 KB) [真实预算隔离]"))
        else:
            checks.append(report(True, f"layer_{lid}_budget", f"{actual_bytes} <= 400 KB"))
        if not layer.get("alpha_channel", False):
            checks.append(report(False, f"layer_{lid}_alpha_channel", "alpha_channel=false"))
        else:
            checks.append(report(True, f"layer_{lid}_alpha_channel", "true"))
        if layer.get("alpha_channel", False):
            af = info.get("half_transparent_fraction", 0.0)
            if af < MIN_ALPHA_HALF_TRANSPARENT_FRACTION:
                checks.append(report(False, f"layer_{lid}_opaque_real", f"半透明像素 {af*100:.2f}% < {MIN_ALPHA_HALF_TRANSPARENT_FRACTION*100:.1f}% (R3-02 真不透明层)"))
            else:
                checks.append(report(True, f"layer_{lid}_alpha_pixels", f"半透明 {af*100:.2f}% (alpha<127)"))

        # R3-03: 强制 4 底色检查图完备性
        check_required_checks(layer, lid, manifest_dir, checks)

        if layer.get("tileable", False):
            tileable_checks = [c for c in layer.get("checks", []) if any(k in c for k in ("seamless", "stages", "tile"))]
            if not tileable_checks:
                checks.append(report(False, f"layer_{lid}_tileable_check", "tileable=true 但缺 seamless/stages/tile 检查图"))
            else:
                checks.append(report(True, f"layer_{lid}_tileable_check", f"{len(tileable_checks)} tileable checks"))

    # 5. 必需 layer 集合
    if known_for_task and task_id in ("SW-002", "SW-006"):
        missing = known_for_task - layer_ids_seen
        if missing:
            checks.append(report(False, "missing_required_layers", f"缺必需层: {sorted(missing)}"))
        else:
            checks.append(report(True, "required_layers", f"全部 {len(known_for_task)} 层齐 (来源: {'design-spec' if spec_layers_dict is not None else 'fallback'})"))

    # 6. 全景预算
    if total_bytes > MAX_SCENE_BYTES:
        checks.append(report(False, "scene_budget_real", f"实际 {total_bytes} > {MAX_SCENE_BYTES} (2 MB) [真实预算隔离]"))
    else:
        checks.append(report(True, "scene_budget", f"{total_bytes} <= 2 MB"))

    # 7. design_ref 批准链 (R3-05)
    if scene_id == "rainforest" and task_id in ("SW-006",):
        if not design_ref:
            checks.append(report(False, "design_ref", f"新场景 {scene_id} task {task_id} 必须有 design_ref"))
        else:
            if fixture_mode and isinstance(design_ref, dict):
                # fixture 模式下，registry status 允许 _expected_registry_status 指定, 但仍要核对批准链 handoff/review 完整
                # 这里只跳过"status 必须 accepted"这一条, 仍走严格批准链
                pass
            check_approval_chain(design_ref, manifest_dir, checks)
    elif scene_id == "forest" and task_id == "SW-002":
        # SW-002 森林为修复任务, design_ref 可为 null (按 contracts/visual-assets §3 例外)
        if design_ref:
            check_approval_chain(design_ref, manifest_dir, checks)
        else:
            checks.append(report(True, "design_ref_skipped", "SW-002 森林机械修复任务, 按合同可空"))

    # 8. API 账本 (R3-04)
    check_api_budget(manifest, checks)

    # 9. CC0 检查
    cc0_found = False
    for layer in layers:
        origin = layer.get("origin", "")
        if "CC0" in origin:
            checks.append(report(False, f"layer_{layer.get('layer_id','?')}_cc0", f"AI 输出不应标 CC0: {origin[:60]}"))
            cc0_found = True
            break
    if not cc0_found:
        checks.append(report(True, "cc0_check", "origin 字段无 CC0 标记"))

    total = len(checks)
    passed = sum(1 for c in checks if c["ok"])
    failed = total - passed
    return {
        "status": "ok" if failed == 0 else "failed",
        "manifest": str(manifest_path),
        "contract_version": CONTRACT_VERSION,
        "fixture_mode": fixture_mode,
        "summary": {"total": total, "passed": passed, "failed": failed, "total_bytes": total_bytes, "layer_count": len(layers)},
        "checks": checks,
    }


def render_summary(result: dict) -> str:
    s = result["summary"]
    lines = [
        f"  status: {result['status']}",
        f"  manifest: {result.get('manifest', '?')}",
        f"  contract: {result.get('contract_version', '?')}",
        f"  fixture_mode: {result.get('fixture_mode', False)}",
        f"  checks: {s['passed']}/{s['total']} passed ({s['failed']} failed)",
        f"  total bytes: {s.get('total_bytes', 0)}",
        f"  layer count: {s.get('layer_count', 0)}",
    ]
    if result.get("error"):
        lines.insert(0, f"  ERROR: {result['error']}")
    failed = [c for c in result.get("checks", []) if not c["ok"]]
    if failed:
        lines.append(f"  failed ({len(failed)}):")
        for c in failed[:40]:
            lines.append(f"    - {c['name']}: {c['detail'][:140]}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="SW-014 R3 预检 (修复 R2-01~R2-05 + R3-06~R3-07)")
    ap.add_argument("manifest", type=Path, help="manifest.json 路径")
    ap.add_argument("--fixture-mode", action="store_true", help="启用 fixture 模式 (允许 manifest 含 _fixture_mode 字段, 仅供测试 harness)")
    ap.add_argument("--json", action="store_true", help="输出 JSON 报告")
    ap.add_argument("--out", type=Path, default=None, help="JSON 报告输出路径")
    args = ap.parse_args()
    result = preflight(args.manifest, fixture_mode=args.fixture_mode)
    if args.json or args.out:
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_summary(result))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())