#!/usr/bin/env python3
"""
SW-014 R2 dry-run: 严格 design_ref 验证, 模拟 SW-006 未来启动检查.

R2 改进 (相对 R1):
- ROOT 用 find_repo_root 探测 (拒绝 parents[N] 错位)
- 拒绝 dummy 文件 / 缺 spec / 错 spec_sha256 / dummy 存在即 approved
- 实际读 registry.json, 验证 task accepted
- 验证 handoff JSON producer 在 trae-design / antigravity
- 验证 handoff head_commit 存在
- 验证 spec_file 实际存在 + spec_sha256 匹配
- 设计更新后旧引用 (被 registry 改 accepted 后) 必须失败
- fixture 模式支持: _fixture_mode + _expected_registry_status (用于测试预检行为)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Optional

from preflight import file_sha256, ROOT, find_repo_root, safe_repo_path


def find_repo_path(rel_or_abs: str) -> Optional[Path]:
    """预检脚本同款路径解析. 拒绝越界/绝对/不存在."""
    return safe_repo_path(rel_or_abs, Path("."))


def check_design_ref(design_ref: dict) -> dict:
    """严格 design_ref 验证, 返回 {ok: bool, reason: str, checks: [...]}."""
    if not isinstance(design_ref, dict):
        return {"ok": False, "reason": f"design_ref 必须是 dict, 实际 {type(design_ref).__name__}", "checks": []}
    checks = []

    # task_id
    ref_task = design_ref.get("task_id", "")
    if not ref_task.startswith("SW-") and not ref_task.startswith("T0"):
        checks.append({"ok": False, "name": "task_id", "detail": f"异常 task_id: {ref_task}"})
    else:
        checks.append({"ok": True, "name": "task_id", "detail": ref_task})

    # handoff
    handoff = design_ref.get("handoff", "")
    if not handoff or not isinstance(handoff, str):
        checks.append({"ok": False, "name": "handoff", "detail": f"handoff 缺失: {handoff!r}"})
        handoff_path = None
    else:
        handoff_path = find_repo_path(handoff)
        if handoff_path is None:
            checks.append({"ok": False, "name": "handoff_path", "detail": f"越界/绝对/不存在: {handoff}"})
        else:
            try:
                h = json.loads(handoff_path.read_text())
                h_producer = h.get("producer", "")
                if h_producer not in ("trae-design", "antigravity"):
                    checks.append({"ok": False, "name": "handoff_producer", "detail": f"非设计/协调者: {h_producer}"})
                else:
                    checks.append({"ok": True, "name": "handoff_producer", "detail": f"{h_producer}"})
                if not h.get("head_commit"):
                    checks.append({"ok": False, "name": "handoff_head_commit", "detail": "handoff 缺 head_commit"})
                else:
                    checks.append({"ok": True, "name": "handoff_head_commit", "detail": h["head_commit"][:12]})
            except json.JSONDecodeError:
                checks.append({"ok": False, "name": "handoff_json", "detail": f"非 JSON: {handoff}"})

    # spec_file
    spec_file = design_ref.get("spec_file", "")
    spec_sha_expected = design_ref.get("spec_sha256", "")
    if spec_sha_expected in (None, "", "PENDING", "PENDING_SW012_APPROVAL"):
        checks.append({"ok": False, "name": "spec_sha_stale", "detail": f"占位: {spec_sha_expected!r}"})
    if not spec_file:
        checks.append({"ok": False, "name": "spec_file", "detail": "缺失"})
    else:
        spec_path = find_repo_path(spec_file)
        if spec_path is None:
            checks.append({"ok": False, "name": "spec_file_path", "detail": f"越界/不存在: {spec_file}"})
        else:
            actual_sha = file_sha256(spec_path)
            if spec_sha_expected and actual_sha != spec_sha_expected:
                checks.append({"ok": False, "name": "spec_sha_mismatch", "detail": f"manifest {spec_sha_expected[:16]} != 实际 {actual_sha[:16]}"})
            else:
                checks.append({"ok": True, "name": "spec_sha", "detail": actual_sha[:16]})

    # registry task
    if ref_task:
        reg_path = ROOT / "docs" / "collaboration" / "registry.json"
        if not reg_path.is_file():
            checks.append({"ok": False, "name": "registry_file", "detail": f"不存在: {reg_path}"})
        else:
            try:
                reg = json.loads(reg_path.read_text())
                task_entry = next((t for t in reg.get("tasks", []) if t.get("id") == ref_task), None)
                if not task_entry:
                    checks.append({"ok": False, "name": "registry_task", "detail": f"无 task {ref_task}"})
                else:
                    actual_status = task_entry.get("status")
                    # fixture 模式
                    fixture_mode = design_ref.get("_fixture_mode") is True
                    if fixture_mode:
                        expected = design_ref.get("_expected_registry_status", "accepted")
                        if actual_status != expected:
                            checks.append({"ok": False, "name": "registry_status", "detail": f"fixture 模式: {actual_status} != 期望 {expected}"})
                        else:
                            checks.append({"ok": True, "name": "registry_status", "detail": f"fixture 模式: {expected} (实际)"})
                    else:
                        if actual_status != "accepted":
                            checks.append({"ok": False, "name": "registry_status", "detail": f"{actual_status} != accepted (真实模式)"})
                        else:
                            checks.append({"ok": True, "name": "registry_status", "detail": "accepted"})
            except json.JSONDecodeError:
                checks.append({"ok": False, "name": "registry_json", "detail": f"registry.json 非 JSON"})

    # 综合
    all_ok = all(c["ok"] for c in checks)
    if all_ok:
        reason = f"全部 {len(checks)} 项通过"
    else:
        failed_names = [c["name"] for c in checks if not c["ok"]]
        reason = f"失败: {', '.join(failed_names)}"
    return {"ok": all_ok, "reason": reason, "checks": checks}


def main() -> int:
    ap = argparse.ArgumentParser(description="SW-014 R2 dry-run (严格 design_ref 验证)")
    ap.add_argument("--design-ref-json", type=Path, required=True, help="design_ref JSON 文件路径 (或 manifest.json, 自动提取 design_ref 字段)")
    ap.add_argument("--out", type=Path, default=None, help="输出报告路径")
    args = ap.parse_args()

    if not args.design_ref_json.is_file():
        print(f"ERROR: design_ref JSON 不存在: {args.design_ref_json}", file=sys.stderr)
        return 2
    obj = json.loads(args.design_ref_json.read_text())
    # 如果传的是 manifest, 提取 design_ref 字段
    if "design_ref" in obj and isinstance(obj["design_ref"], dict):
        design_ref = obj["design_ref"]
    else:
        design_ref = obj

    result = check_design_ref(design_ref)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())