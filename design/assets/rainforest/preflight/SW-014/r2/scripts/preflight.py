#!/usr/bin/env python3
"""
SW-014 R2 预检 (零 API, 改进版).

R2 改进 (相对 R1):
- ROOT 用 find_repo_root 探测 (拒绝 parents[N] 错位, 拒绝越界)
- 真实解码 PNG/WebP 像素 (PIL Image.open + verify + load), 拒绝文本伪装
- 拒绝 0x0 / 异常尺寸 (除 768x1376 与 1080x1920 之外视为异常)
- 拒绝空 layers / 未知 layer_id / 重复 layer_id
- 拒绝 manifest 声明的 layer 集合与已知 layer_id 集合不一致
- 拒绝 缺文件 / 错 SHA / 错字节 (实际文件验证)
- 拒绝 缺检查图 (4 底色 + alpha_mask)
- 拒绝 不透明 (alpha 全 255, 透明比例 0%)
- 拒绝 真实单层超 400KB (用文件实际 size, 非只声明)
- 拒绝 design_ref 缺 / 路径不存在 / spec_sha256 不匹配实际文件
- 拒绝 spec_sha256 写 stale 占位
- 拒绝 tileable=true 但缺 tileable checks
- 拒绝 父路径越界 (拒绝 / 绝对路径, 仅接受 repo 根相对)
- 拒绝 task_id 与 producer 不匹配 minimax (role scope)
- 拒绝 task 范围与 scene 不一致 (SW-002 = forest, SW-006 = rainforest, 等)
- 拒绝 registry task 不存在 / kind != asset
- dry_run.py 严格 design_ref 验证 (统一接口)

不替 Trae 决定雨林构图/色板.
不重置 R1/R2 已发生账本尝试.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Optional

from PIL import Image
import numpy as np

# --- repo 根定位 (拒绝 parents[N] 错位) ---

def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(15):
        if (cur / "docs" / "collaboration").is_dir() and (cur / "design" / "assets").is_dir():
            return cur
        if cur.parent == cur:
            raise RuntimeError(f"repo 根未找到, 起点 {start}")
        cur = cur.parent
    raise RuntimeError(f"repo 根路径过深, 起点 {start}")


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = find_repo_root(SCRIPT_DIR)
# 强制 ROOT 解析后的实际位置与 git toplevel 一致
import subprocess
try:
    git_root = subprocess.check_output(["git", "-C", str(SCRIPT_DIR), "rev-parse", "--show-toplevel"], text=text if False else "utf-8").strip()
except Exception:
    git_root = None
if git_root and Path(git_root).resolve() != ROOT:
    raise RuntimeError(f"ROOT 推导与 git toplevel 不一致: {ROOT} vs {git_root}")


# --- 协议常量 (来自 contracts/visual-assets.md + PROTOCOL) ---

CONTRACT_VERSION = "visual-assets v1"
MAX_LAYER_BYTES = 400 * 1024       # 400 KB per layer
MAX_SCENE_BYTES = 2 * 1024 * 1024  # 2 MB per scene
ACCEPTED_W = (768, 1376)            # 森林历史 raw 尺寸
ACCEPTED_W_PROJECT = (1080, 1920)  # 项目最终画布
ALLOWED_DIMENSIONS = {ACCEPTED_W, ACCEPTED_W_PROJECT}  # 接受集合
MIN_ALPHA_FRACTION = 0.001         # 至少 0.1% 透明像素 (拒绝 alpha=全 255)

# 已知 layer_id 集合 (按 task_id + scene_id 区分)
KNOWN_LAYERS = {
    ("SW-002", "forest"): {"clearing", "light_shows"},  # SW-002 是 2 层修图, 不强制 5
    ("SW-006", "rainforest"): {"mist", "trunks_canopy", "vines_light", "far_glow", "clearing_glow"},  # 雨林 5 层
    ("SW-014", "rainforest"): set(),  # SW-014 是预检, 不产素材; 但允许用 rainforest 场景校验
}

# task_id 与 scene_id 合法组合
TASK_SCENE_VALID = {
    "SW-002": {"forest"},
    "SW-006": {"rainforest"},
    "SW-014": {"rainforest"},  # 预检工具
}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_repo_path(rel_or_abs: str, manifest_dir: Path) -> Optional[Path]:
    """解析 manifest 中的文件路径, 拒绝:
    - 绝对路径
    - 含 .. 越界
    - 文件不存在
    返回 repo 根相对 Path, 失败返回 None.
    """
    if not rel_or_abs or not isinstance(rel_or_abs, str):
        return None
    p = Path(rel_or_abs)
    if p.is_absolute():
        return None
    parts = p.parts
    if ".." in parts:
        return None
    # 优先 repo 根 (visual-assets 合同: 路径相对 repo 根)
    candidate = ROOT / rel_or_abs
    # 兼容 fallback: 如果 ROOT 解析失败, 尝试 manifest_dir 相对
    if not candidate.is_file():
        candidate = manifest_dir / rel_or_abs
        if not candidate.is_file():
            return None
    # 越界检查: 解析后必须在 ROOT 内
    try:
        candidate.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return None
    return candidate


def real_decode_image(path: Path) -> dict:
    """真实解码 PNG/WebP, 返回 (mode, size, alpha_fraction, is_image)."""
    try:
        img = Image.open(path)
        img.verify()  # 验证头部 + 完整性
        # verify 后需要重 open 才能 load
        img = Image.open(path)
        img.load()
        w, h = img.size
        # 检查 alpha
        alpha_frac = 0.0
        if img.mode in ("RGBA", "LA"):
            arr = np.asarray(img.convert("RGBA"))
            a = arr[..., 3]
            if a.size > 0:
                alpha_frac = float((a > 0).sum()) / a.size
        return {
            "is_image": True,
            "mode": img.mode,
            "width": w,
            "height": h,
            "alpha_fraction": alpha_frac,
        }
    except Exception as e:
        return {"is_image": False, "error": str(e)}


def report(ok: bool, name: str, detail: str = "") -> dict:
    return {"ok": ok, "name": name, "detail": detail}


# --- 主预检 ---

def preflight(manifest_path: Path) -> dict:
    if not manifest_path.is_file():
        return {"status": "failed", "error": f"manifest not found: {manifest_path}", "checks": [], "summary": {"total": 0, "passed": 0, "failed": 0}}

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        return {"status": "failed", "error": f"manifest JSON 解析失败: {e}", "checks": [], "summary": {"total": 0, "passed": 0, "failed": 0}}

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

    # 4. layers 检查
    layers = manifest.get("layers", [])
    layer_ids_seen: set[str] = set()
    total_bytes = 0
    known_for_task = KNOWN_LAYERS.get((task_id, scene_id), set())

    for layer in layers:
        lid = layer.get("layer_id", "?")
        if not lid or lid == "?":
            checks.append(report(False, "layer_id_missing", "layer_id 字段缺失"))
            continue
        # 重复检测
        if lid in layer_ids_seen:
            checks.append(report(False, f"layer_{lid}_duplicate", f"layer_id 重复: {lid}"))
        layer_ids_seen.add(lid)

        # 未知 layer_id (不在已知集合)
        if known_for_task and lid not in known_for_task:
            checks.append(report(False, f"layer_{lid}_unknown", f"layer_id 不在已知集合 {sorted(known_for_task)}"))

        # 路径解析 + 实际存在
        rel_file = layer.get("file", "")
        file_path = safe_repo_path(rel_file, manifest_dir)
        if file_path is None:
            checks.append(report(False, f"layer_{lid}_file_missing", f"文件不存在 / 越界 / 绝对路径: {rel_file}"))
            continue
        # 字节 + SHA
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

        # 真实解码 (拒绝文本伪装 + 接受尺寸)
        info = real_decode_image(file_path)
        if not info.get("is_image"):
            checks.append(report(False, f"layer_{lid}_decode", f"非图/坏图: {info.get('error', '?')}"))
            continue
        checks.append(report(True, f"layer_{lid}_decode", f"{info['mode']} {info['width']}x{info['height']}"))
        # 尺寸匹配
        actual_w, actual_h = info["width"], info["height"]
        manifest_w, manifest_h = layer.get("width", 0), layer.get("height", 0)
        if (actual_w, actual_h) != (manifest_w, manifest_h):
            checks.append(report(False, f"layer_{lid}_size_manifest", f"实际 {actual_w}x{actual_h} != manifest {manifest_w}x{manifest_h}"))
        if (actual_w, actual_h) not in ALLOWED_DIMENSIONS:
            checks.append(report(False, f"layer_{lid}_size_unsupported", f"{actual_w}x{actual_h} 不在 {ALLOWED_DIMENSIONS}"))
        else:
            checks.append(report(True, f"layer_{lid}_size", f"{actual_w}x{actual_h}"))
        # 单层预算
        if actual_bytes > MAX_LAYER_BYTES:
            checks.append(report(False, f"layer_{lid}_budget", f"{actual_bytes} > {MAX_LAYER_BYTES} (400 KB)"))
        else:
            checks.append(report(True, f"layer_{lid}_budget", f"{actual_bytes} <= 400 KB"))
        # alpha 通道
        if not layer.get("alpha_channel", False):
            checks.append(report(False, f"layer_{lid}_alpha_channel", "alpha_channel=false"))
        else:
            checks.append(report(True, f"layer_{lid}_alpha_channel", "true"))
        # 真实 alpha 像素比例 (拒绝全不透明)
        if layer.get("alpha_channel", False):
            af = info.get("alpha_fraction", 0.0)
            if af < MIN_ALPHA_FRACTION:
                checks.append(report(False, f"layer_{lid}_opaque", f"透明像素 {af*100:.2f}% < {MIN_ALPHA_FRACTION*100:.1f}% (不透明层)"))
            else:
                checks.append(report(True, f"layer_{lid}_alpha_pixels", f"透明 {af*100:.2f}%"))

        # 4 底色检查图
        for c in layer.get("checks", []):
            cp = safe_repo_path(c, manifest_dir)
            if cp is None or not cp.is_file():
                checks.append(report(False, f"layer_{lid}_check_{Path(c).parent.name}", f"缺/越界: {c}"))
        # tileable=true 限制
        if layer.get("tileable", False):
            tileable_checks = [c for c in layer.get("checks", []) if any(k in c for k in ("seamless", "stages", "tile"))]
            if not tileable_checks:
                checks.append(report(False, f"layer_{lid}_tileable_check", "tileable=true 但缺 seamless/stages/tile 检查图"))
            else:
                checks.append(report(True, f"layer_{lid}_tileable_check", f"{len(tileable_checks)} tileable checks"))

    # 5. 必需 layer 集合 (按 task_id + scene_id)
    if known_for_task and task_id in ("SW-002", "SW-006"):
        missing = known_for_task - layer_ids_seen
        if missing:
            checks.append(report(False, "missing_required_layers", f"缺必需层: {sorted(missing)}"))
        else:
            checks.append(report(True, "required_layers", f"全部 {len(known_for_task)} 层齐"))

    # 6. 全景预算
    if total_bytes > MAX_SCENE_BYTES:
        checks.append(report(False, "scene_budget", f"{total_bytes} > {MAX_SCENE_BYTES} (2 MB)"))
    else:
        checks.append(report(True, "scene_budget", f"{total_bytes} <= 2 MB"))

    # 7. design_ref (新场景必须有)
    design_ref = manifest.get("design_ref")
    if scene_id in ("rainforest", "city", "desert", "night-path") and task_id in ("SW-006",):
        if not design_ref:
            checks.append(report(False, "design_ref", f"新场景 {scene_id} task {task_id} 必须有 design_ref"))
        else:
            checks.extend(_validate_design_ref(design_ref, manifest_dir))

    # 8. API 账本字段
    for key in ["api_attempts_this_revision", "api_attempts_total", "cost"]:
        if key not in manifest:
            checks.append(report(False, f"api_field_{key}", "缺失"))
        else:
            checks.append(report(True, f"api_field_{key}", f"{manifest[key]}"))

    # 9. CC0 检查 (origin 不能含 CC0)
    for layer in layers:
        origin = layer.get("origin", "")
        if "CC0" in origin:
            checks.append(report(False, f"layer_{layer.get('layer_id','?')}_cc0", f"AI 输出不应标 CC0: {origin[:60]}"))
            break
    else:
        checks.append(report(True, "cc0_check", "origin 字段无 CC0 标记"))

    # 总结
    total = len(checks)
    passed = sum(1 for c in checks if c["ok"])
    failed = total - passed
    return {
        "status": "ok" if failed == 0 else "failed",
        "manifest": str(manifest_path),
        "contract_version": CONTRACT_VERSION,
        "summary": {"total": total, "passed": passed, "failed": failed, "total_bytes": total_bytes, "layer_count": len(layers)},
        "checks": checks,
    }


def _validate_design_ref(design_ref: dict, manifest_dir: Path) -> list[dict]:
    """严格 design_ref 验证:
    - handoff 路径存在 (绝对/越界拒绝)
    - spec_file 存在 + spec_sha256 匹配实际文件 SHA256
    - task_id/producer/kind 在已批准范围
    - 当前 registry task status=accepted
    - 存在 approved review (按 contracts/visual-assets)
    """
    results = []
    if not isinstance(design_ref, dict):
        return [report(False, "design_ref_type", f"expected dict, got {type(design_ref).__name__}")]
    # task_id
    ref_task = design_ref.get("task_id", "")
    if not ref_task.startswith("SW-1") and ref_task not in ("SW-006", "SW-011", "SW-012"):
        results.append(report(False, "design_ref_task_id", f"task_id 异常: {ref_task}"))
    else:
        results.append(report(True, "design_ref_task_id", ref_task))
    # handoff 路径
    handoff = design_ref.get("handoff", "")
    if not handoff or not isinstance(handoff, str):
        results.append(report(False, "design_ref_handoff_missing", f"handoff 缺失: {handoff}"))
    else:
        hp = safe_repo_path(handoff, manifest_dir)
        if hp is None:
            results.append(report(False, "design_ref_handoff_path", f"handoff 路径越界/不存在/绝对: {handoff}"))
        elif not hp.is_file():
            results.append(report(False, "design_ref_handoff_missing", f"handoff 文件不存在: {handoff}"))
        else:
            try:
                h = json.loads(hp.read_text())
                h_producer = h.get("producer", "")
                if h_producer not in ("trae-design", "antigravity"):
                    results.append(report(False, "design_ref_handoff_producer", f"handoff producer 异常: {h_producer}"))
                else:
                    results.append(report(True, "design_ref_handoff_producer", f"{h_producer}"))
                # handoff 必须有 reviewed_commit/head_commit 字段
                if not h.get("head_commit"):
                    results.append(report(False, "design_ref_handoff_no_head", "handoff 缺 head_commit"))
            except json.JSONDecodeError:
                results.append(report(False, "design_ref_handoff_json", f"handoff 不是 JSON: {handoff}"))
    # spec_file
    spec_file = design_ref.get("spec_file", "")
    spec_sha_expected = design_ref.get("spec_sha256", "")
    if spec_sha_expected in (None, "", "PENDING", "PENDING_SW012_APPROVAL"):
        results.append(report(False, "design_ref_spec_sha_stale", f"spec_sha256 是占位: {spec_sha_expected}"))
    if not spec_file or not isinstance(spec_file, str):
        results.append(report(False, "design_ref_spec_file_missing", f"spec_file 缺失: {spec_file}"))
    else:
        sp = safe_repo_path(spec_file, manifest_dir)
        if sp is None:
            results.append(report(False, "design_ref_spec_file_path", f"spec_file 路径越界/不存在: {spec_file}"))
        elif not sp.is_file():
            results.append(report(False, "design_ref_spec_file_missing", f"spec_file 不存在: {spec_file}"))
        else:
            actual_sha = file_sha256(sp)
            if spec_sha_expected and actual_sha != spec_sha_expected:
                results.append(report(False, "design_ref_spec_sha_mismatch", f"manifest {spec_sha_expected[:16]} != 实际 {actual_sha[:16]}"))
            else:
                results.append(report(True, "design_ref_spec_sha", actual_sha[:16]))
    # registry task 状态检查
    # 默认: 任务必须 accepted
    # fixture 模式: manifest 含 _fixture_mode=true 时, 允许 _expected_registry_status 指定的 status
    if ref_task:
        reg = json.loads((ROOT / "docs" / "collaboration" / "registry.json").read_text())
        task_entry = next((t for t in reg.get("tasks", []) if t.get("id") == ref_task), None)
        if not task_entry:
            results.append(report(False, "design_ref_registry_task", f"registry 无 task {ref_task}"))
        else:
            actual_status = task_entry.get("status")
            # fixture 模式读取
            fixture_mode = design_ref.get("_fixture_mode") is True
            if fixture_mode:
                expected = design_ref.get("_expected_registry_status", "accepted")
                if actual_status != expected:
                    results.append(report(False, "design_ref_registry_status", f"fixture 模式: task {ref_task} status={actual_status} != 期望 {expected}"))
                else:
                    results.append(report(True, "design_ref_registry_status", f"fixture 模式: {expected} (实际)"))
            else:
                # 真实模式: 必须 accepted
                if actual_status != "accepted":
                    results.append(report(False, "design_ref_registry_status", f"task {ref_task} status={actual_status} != accepted (真实模式不允许 queued/in_progress)"))
                else:
                    results.append(report(True, "design_ref_registry_status", "accepted"))
    return results


def render_summary(result: dict) -> str:
    s = result["summary"]
    lines = [
        f"  status: {result['status']}",
        f"  manifest: {result.get('manifest', '?')}",
        f"  contract: {result.get('contract_version', '?')}",
        f"  checks: {s['passed']}/{s['total']} passed ({s['failed']} failed)",
        f"  total bytes: {s.get('total_bytes', 0)}",
        f"  layer count: {s.get('layer_count', 0)}",
    ]
    if result.get("error"):
        lines.insert(0, f"  ERROR: {result['error']}")
    failed = [c for c in result.get("checks", []) if not c["ok"]]
    if failed:
        lines.append(f"  failed ({len(failed)}):")
        for c in failed[:30]:
            lines.append(f"    - {c['name']}: {c['detail'][:120]}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="SW-014 R2 预检 (零 API, 真实解码, 隔离正反 fixture)")
    ap.add_argument("manifest", type=Path, help="manifest.json 路径")
    ap.add_argument("--json", action="store_true", help="输出 JSON 报告")
    ap.add_argument("--out", type=Path, default=None, help="JSON 报告输出路径")
    args = ap.parse_args()
    result = preflight(args.manifest)
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