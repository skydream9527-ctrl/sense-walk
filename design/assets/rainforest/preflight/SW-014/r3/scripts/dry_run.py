#!/usr/bin/env python3
"""
SW-014 R3 dry-run: 严格批准链 + fixture-mode 隔离.

R3 相对 R2:
- fixture_mode 必须由 --fixture-mode CLI 旗标驱动, 不再读 manifest._fixture_mode
- 严格核对 registry.latest_handoff + latest_review, 与 design_ref.handoff/spec_sha256 必须完全一致
- registry.latest_review.verdict == approved
- registry.latest_review.reviewed_commit == registry.latest_handoff.head_commit
- spec_sha256 与实际 spec 文件 SHA256 一致
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Optional

from preflight import (
    file_sha256,
    ROOT,
    find_repo_root,
    safe_repo_path,
    load_registry,
)


def check_design_ref(design_ref: dict, fixture_mode: bool = False) -> dict:
    """严格批准链 design_ref 验证, R3 版本不接受 _fixture_mode 字段 (改为 CLI flag)."""
    if not isinstance(design_ref, dict):
        return {"ok": False, "reason": f"design_ref 必须是 dict, 实际 {type(design_ref).__name__}", "checks": []}
    checks = []

    # R3-01: 严格拒绝 manifest 内 _fixture_mode/_expected_registry_status 字段 (除非 CLI 显式 fixture-mode)
    if not fixture_mode:
        for key in ("_fixture_mode", "_expected_registry_status"):
            if key in design_ref:
                checks.append({"ok": False, "name": f"design_ref_{key}_forbidden", "detail": f"真实模式禁止 {key} 字段; 仅 --fixture-mode CLI 旗标启用时允许"})

    # task_id
    ref_task = design_ref.get("task_id", "")
    if not ref_task.startswith("SW-"):
        checks.append({"ok": False, "name": "task_id", "detail": f"异常 task_id: {ref_task}"})
    else:
        checks.append({"ok": True, "name": "task_id", "detail": ref_task})

    # handoff
    handoff = design_ref.get("handoff", "")
    handoff_data = None
    if not handoff or not isinstance(handoff, str):
        checks.append({"ok": False, "name": "handoff", "detail": f"handoff 缺失: {handoff!r}"})
        handoff_path = None
    else:
        handoff_path = safe_repo_path(handoff, Path("."))
        if handoff_path is None:
            checks.append({"ok": False, "name": "handoff_path", "detail": f"越界/绝对/不存在: {handoff}"})
        else:
            try:
                handoff_data = json.loads(handoff_path.read_text())
                h_producer = handoff_data.get("producer", "")
                if h_producer not in ("trae-design", "antigravity"):
                    checks.append({"ok": False, "name": "handoff_producer", "detail": f"非设计/协调者: {h_producer}"})
                else:
                    checks.append({"ok": True, "name": "handoff_producer", "detail": f"{h_producer}"})
                h_head = handoff_data.get("head_commit", "")
                if not h_head or not re.fullmatch(r"[0-9a-f]{40}", h_head):
                    checks.append({"ok": False, "name": "handoff_head", "detail": f"head_commit 不是 40-char SHA: {h_head!r}"})
                else:
                    checks.append({"ok": True, "name": "handoff_head", "detail": h_head[:12]})
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
        spec_path = safe_repo_path(spec_file, Path("."))
        if spec_path is None:
            checks.append({"ok": False, "name": "spec_file_path", "detail": f"越界/不存在: {spec_file}"})
        else:
            actual_sha = file_sha256(spec_path)
            if spec_sha_expected and actual_sha != spec_sha_expected:
                checks.append({"ok": False, "name": "spec_sha_mismatch", "detail": f"manifest {spec_sha_expected[:16]} != 实际 {actual_sha[:16]}"})
            else:
                checks.append({"ok": True, "name": "spec_sha", "detail": actual_sha[:16]})

    # registry task 全链条
    reg = load_registry()
    task_entry = next((t for t in reg.get("tasks", []) if t.get("id") == ref_task), None)
    if not task_entry:
        checks.append({"ok": False, "name": "registry_task", "detail": f"无 task {ref_task}"})
    else:
        actual_status = task_entry.get("status")
        if actual_status != "accepted":
            checks.append({"ok": False, "name": "registry_status", "detail": f"{actual_status} != accepted (R3 真实模式不接受 queued/in_progress)"})
        else:
            checks.append({"ok": True, "name": "registry_status", "detail": "accepted"})
        # registry.latest_handoff 必须存在且 head 与设计引用 handoff head 一致
        approved_handoff_rel = task_entry.get("latest_handoff")
        approved_review_rel = task_entry.get("latest_review")
        if approved_handoff_rel and handoff_data:
            ap = safe_repo_path(approved_handoff_rel, Path("."))
            if ap is None or not ap.is_file():
                checks.append({"ok": False, "name": "approval_handoff_missing", "detail": f"registry latest_handoff 不存在: {approved_handoff_rel}"})
            else:
                try:
                    ap_data = json.loads(ap.read_text())
                    ap_head = ap_data.get("head_commit", "")
                    in_head = handoff_data.get("head_commit", "")
                    if in_head != ap_head:
                        checks.append({"ok": False, "name": "approval_chain_handoff_head", "detail": f"design_ref.handoff.head {in_head[:12]} != registry.latest_handoff.head {ap_head[:12]}"})
                    else:
                        checks.append({"ok": True, "name": "approval_chain_handoff_head", "detail": f"匹配 {in_head[:12]}"})
                except json.JSONDecodeError:
                    checks.append({"ok": False, "name": "approval_handoff_json", "detail": "approved handoff 非 JSON"})
        elif approved_handoff_rel is None:
            checks.append({"ok": False, "name": "approval_handoff_null", "detail": f"task {ref_task} registry.latest_handoff=null"})
        # registry.latest_review
        if approved_review_rel:
            rp = safe_repo_path(approved_review_rel, Path("."))
            if rp is None or not rp.is_file():
                checks.append({"ok": False, "name": "approval_review_missing", "detail": f"registry latest_review 不存在: {approved_review_rel}"})
            else:
                try:
                    rv = json.loads(rp.read_text())
                    if rv.get("verdict") != "approved":
                        checks.append({"ok": False, "name": "approval_review_verdict", "detail": f"verdict={rv.get('verdict')!r} != approved"})
                    else:
                        checks.append({"ok": True, "name": "approval_review_verdict", "detail": "approved"})
                    rv_reviewed = rv.get("reviewed_commit", "")
                    in_head = (handoff_data or {}).get("head_commit", "")
                    if in_head and rv_reviewed != in_head:
                        checks.append({"ok": False, "name": "approval_review_head", "detail": f"reviewed_commit {rv_reviewed[:12]} != handoff head {in_head[:12]}"})
                    else:
                        checks.append({"ok": True, "name": "approval_review_head", "detail": f"匹配 {rv_reviewed[:12]}"})
                except json.JSONDecodeError:
                    checks.append({"ok": False, "name": "approval_review_json", "detail": "approved review 非 JSON"})
        elif approved_review_rel is None:
            checks.append({"ok": False, "name": "approval_review_null", "detail": f"task {ref_task} registry.latest_review=null"})

    # 综合
    all_ok = all(c["ok"] for c in checks)
    if all_ok:
        reason = f"全部 {len(checks)} 项通过"
    else:
        failed_names = [c["name"] for c in checks if not c["ok"]]
        reason = f"失败: {', '.join(failed_names)}"
    return {"ok": all_ok, "reason": reason, "checks": checks}


def main() -> int:
    ap = argparse.ArgumentParser(description="SW-014 R3 dry-run (严格批准链 + CLI fixture 旗标)")
    ap.add_argument("--design-ref-json", type=Path, required=True, help="design_ref JSON 文件路径 (或 manifest.json, 自动提取 design_ref 字段)")
    ap.add_argument("--fixture-mode", action="store_true", help="启用 fixture 模式 (允许 _fixture_mode 字段, 仅测试)")
    ap.add_argument("--out", type=Path, default=None, help="输出报告路径")
    args = ap.parse_args()

    if not args.design_ref_json.is_file():
        print(f"ERROR: design_ref JSON 不存在: {args.design_ref_json}", file=sys.stderr)
        return 2
    obj = json.loads(args.design_ref_json.read_text())
    if "design_ref" in obj and isinstance(obj["design_ref"], dict):
        design_ref = obj["design_ref"]
    else:
        design_ref = obj

    result = check_design_ref(design_ref, fixture_mode=args.fixture_mode)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())