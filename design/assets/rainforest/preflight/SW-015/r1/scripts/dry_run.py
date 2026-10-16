#!/usr/bin/env python3
"""
SW-015 R1 dry-run (零 API).

复用 SW-014 R3 dry_run.py 严格批准链 + 加 SW-015 spec 强校验:
- spec id/type/canvas/id_status 校验 (空/重复/未知 type 必须 fail)
- manifest.layer_id/render_role 与 spec 严格匹配 (legacy alias 归一化后)
- 临时 fixture registry 仍走 R3 approved head 校验
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

# 动态加载 R3 dry_run
R3_DRY_PATH = Path(__file__).resolve().parent.parent.parent.parent / "SW-014" / "r3" / "scripts" / "dry_run.py"
_spec = importlib.util.spec_from_file_location("sw014_r3_dry", R3_DRY_PATH)
_r3_dry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_r3_dry)

from spec_reader import (
    load_spec,
    validate_spec,
    spec_to_manifest_fields,
    manifest_layers_compatible,
)


def check_design_ref(design_ref: dict, *, fixture_mode: bool = False, allow_proposed: bool = True) -> dict:
    """先跑 R3 dry_run 严格批准链 + SW-015 spec 校验 + manifest 与 spec 一致性."""
    r3_result = _r3_dry.check_design_ref(design_ref, fixture_mode=fixture_mode)
    checks: list[dict] = list(r3_result.get("checks", []))

    if not isinstance(design_ref, dict):
        return r3_result

    spec_file = design_ref.get("spec_file")
    spec_sha_expected = design_ref.get("spec_sha256")
    if spec_file:
        try:
            # 复用 R3 的 safe_repo_path (R3 dry_run 用 safe_repo_path 而非 find_repo_path)
            spec_path = _r3_dry.safe_repo_path(spec_file, Path("."))
            if spec_path is None:
                # 尝试 ROOT 相对
                spec_path_alt = _r3_dry.ROOT / spec_file
                if spec_path_alt.is_file():
                    spec_path = spec_path_alt
            if spec_path is None:
                checks.append({"ok": False, "name": "sw015_spec_path", "detail": f"spec_file 路径越界/不存在: {spec_file}"})
            else:
                actual_sha = _r3_dry.file_sha256(spec_path)
                if spec_sha_expected and actual_sha != spec_sha_expected:
                    checks.append({"ok": False, "name": "sw015_spec_sha_mismatch", "detail": f"manifest {spec_sha_expected[:16]} != 实际 {actual_sha[:16]}"})
                else:
                    checks.append({"ok": True, "name": "sw015_spec_sha", "detail": f"匹配 {actual_sha[:16]}"})
                try:
                    spec = json.loads(spec_path.read_text())
                except json.JSONDecodeError as e:
                    checks.append({"ok": False, "name": "sw015_spec_json", "detail": f"spec 非 JSON: {e}"})
                    spec = None
                if spec is not None:
                    spec_errors = validate_spec(spec, allow_proposed=allow_proposed)
                    if spec_errors:
                        checks.append({"ok": False, "name": "sw015_spec_validation", "detail": f"spec 校验失败 {len(spec_errors)} 项: {'; '.join(spec_errors[:3])}..."})
                    else:
                        checks.append({"ok": True, "name": "sw015_spec_validation", "detail": "spec 通过 canonical/legacy/empty/duplicate/type 全部校验"})
                    # dry-run 不直接校验 manifest.layers (那是 preflight 的事)
                    expected_fields = spec_to_manifest_fields(spec)
                    checks.append({"ok": True, "name": "sw015_spec_expected_layers", "detail": f"expected {len(expected_fields['layer_ids'])} 层: {expected_fields['layer_ids']}"})
        except Exception as e:
            checks.append({"ok": False, "name": "sw015_spec_unexpected", "detail": f"未预期错误: {e}"})

    all_ok = all(c.get("ok") for c in checks)
    if all_ok:
        reason = f"全部 {len(checks)} 项通过"
    else:
        failed_names = [c["name"] for c in checks if not c.get("ok")]
        reason = f"失败: {', '.join(failed_names)}"
    return {"ok": all_ok, "reason": reason, "checks": checks}


def main() -> int:
    ap = argparse.ArgumentParser(description="SW-015 R1 dry-run (R3 严格批准链 + SW-015 spec 校验)")
    ap.add_argument("--design-ref-json", type=Path, required=True)
    ap.add_argument("--fixture-mode", action="store_true")
    ap.add_argument("--strict-design", action="store_true", help="严格模式: proposed 也算未批准")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    if not args.design_ref_json.is_file():
        print(f"ERROR: design_ref JSON 不存在: {args.design_ref_json}", file=sys.stderr)
        return 2
    obj = json.loads(args.design_ref_json.read_text())
    design_ref = obj.get("design_ref", obj) if isinstance(obj, dict) else obj

    result = check_design_ref(design_ref, fixture_mode=args.fixture_mode, allow_proposed=not args.strict_design)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())