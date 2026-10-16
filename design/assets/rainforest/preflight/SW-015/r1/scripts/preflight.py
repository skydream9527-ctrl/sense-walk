#!/usr/bin/env python3
"""
SW-015 R1 预检 (零 API, 真实 Trae 设计规格解析 + 兼容 legacy).

相对 SW-014 R3 增量:
- 调用 spec_reader 强校验 design-spec (空/重复/未知 type/canvas/legacy alias)
- 校验 manifest.layer_id/render_role 与 spec 期望严格匹配
- 保留 R3 严格入口: 真 alpha/4 检查图/实际预算/累计账本/批准链
- 复用 R3 脚本 (root 解析 + find_repo_root + 真实解码)

不替 Trae 决定设计; 不改 design-spec; 不写 registry.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Optional

# --- 动态加载 R3 preflight 模块 (复用 find_repo_root/file_sha256/safe_repo_path/real_decode_image/load_registry/load_minimax_history) ---
# scripts/r1/SW-015/preflight/rainforest/assets/design/<repo> -> 7 层 parent (scripts->r1->SW-015->preflight->rainforest->assets->design)
R3_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent.parent / "SW-014" / "r3" / "scripts" / "preflight.py"
_spec = importlib.util.spec_from_file_location("sw014_r3_pre", R3_SCRIPT_PATH)
_r3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_r3)

from spec_reader import (
    load_spec,
    validate_spec,
    spec_to_manifest_fields,
    manifest_layers_compatible,
    render_summary as render_spec_summary,
    SpecParseError,
)

# 导出 R3 工具函数, 让本模块对外像 "preflight" (供 R3 dry_run.py 复用)
file_sha256 = _r3.file_sha256
safe_repo_path = _r3.safe_repo_path
ROOT = _r3.ROOT
find_repo_root = _r3.find_repo_root
load_registry = _r3.load_registry
load_minimax_history = _r3.load_minimax_history
real_decode_image = _r3.real_decode_image
MAX_LAYER_BYTES = _r3.MAX_LAYER_BYTES
MAX_SCENE_BYTES = _r3.MAX_SCENE_BYTES
ACCEPTED_DIMENSIONS = _r3.ACCEPTED_DIMENSIONS

# SW-015 扩展 R3 KNOWN_LAYERS_FALLBACK, 加入 SW-011 已批 5 层 (避免 R3 硬编码 layer_id_unknown 误拒)
_r3.KNOWN_LAYERS_FALLBACK = {
    ("SW-002", "forest"): {"clearing", "light_shows", "tree_outline", "tree_trunks", "leaf_path"},  # SW-011 已批
}

# --- 主预检 ---

def preflight(manifest_path: Path, fixture_mode: bool = False, allow_proposed: bool = True) -> dict:
    """在 R3 严格入口基础上加 SW-015 spec 强校验.
    fixture_mode: 透传给 R3 (允许 _fixture_mode 字段)
    allow_proposed: True (默认) 允许 spec.id_status=proposed 当样本解析 (PR15 阶段); False 用于已批 design 真实批准
    """
    # 1. 跑 R3 严格入口 (复用 11+ 检查项)
    r3_result = _r3.preflight(manifest_path, fixture_mode=fixture_mode)
    checks: list[dict] = list(r3_result.get("checks", []))
    summary = dict(r3_result.get("summary", {}))

    # 2. SW-015 增量: design-spec 强校验 + manifest-layer 与 spec 一致性
    manifest_dir = manifest_path.parent
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError:
        return r3_result

    design_ref = manifest.get("design_ref")
    if isinstance(design_ref, dict):
        spec_file = design_ref.get("spec_file")
        spec_sha_expected = design_ref.get("spec_sha256")
        if spec_file:
            # 加载 spec (从 manifest_dir 或 ROOT 相对)
            try:
                # 用 R3 的 safe_repo_path 但 ROOT 已 monkey-patch 到 sw015-r1 worktree 根
                # spec_file 通常是 repo 根相对, 这里手动解析
                spec_path = _r3.safe_repo_path(spec_file, manifest_dir)
                if spec_path is None:
                    # 尝试 ROOT 相对
                    spec_path = _r3.ROOT / spec_file if not (spec_file).startswith("/") else None
                    if spec_path is not None and not spec_path.is_file():
                        spec_path = None
                if spec_path is None:
                    checks.append({"ok": False, "name": "sw015_spec_path", "detail": f"spec_file 路径越界/不存在: {spec_file}"})
                else:
                    actual_sha = _r3.file_sha256(spec_path)
                    if spec_sha_expected and actual_sha != spec_sha_expected:
                        checks.append({"ok": False, "name": "sw015_spec_sha_mismatch", "detail": f"manifest {spec_sha_expected[:16]} != 实际 {actual_sha[:16]}"})
                    else:
                        checks.append({"ok": True, "name": "sw015_spec_sha", "detail": f"匹配 {actual_sha[:16]}"})
                    # 解析 spec 内容
                    try:
                        spec = json.loads(spec_path.read_text())
                    except json.JSONDecodeError as e:
                        checks.append({"ok": False, "name": "sw015_spec_json", "detail": f"spec 非 JSON: {e}"})
                        spec = None
                    if spec is not None:
                        # 强校验
                        spec_errors = validate_spec(spec, allow_proposed=allow_proposed)
                        if spec_errors:
                            checks.append({"ok": False, "name": "sw015_spec_validation", "detail": f"spec 校验失败 {len(spec_errors)} 项: {'; '.join(spec_errors[:3])}..."})
                        else:
                            checks.append({"ok": True, "name": "sw015_spec_validation", "detail": "spec 通过 canonical/legacy/empty/duplicate/type 全部校验"})
                        # manifest 与 spec 一致性
                        expected = spec_to_manifest_fields(spec)
                        manifest_layers = []
                        for ml in manifest.get("layers", []):
                            manifest_layers.append({"id": ml.get("layer_id", ""), "render_role": ml.get("render_role", "")})
                        compat_errors = manifest_layers_compatible(manifest_layers, expected)
                        if compat_errors:
                            checks.append({"ok": False, "name": "sw015_manifest_spec_consistency", "detail": f"manifest 与 spec 不一致 {len(compat_errors)} 项: {'; '.join(compat_errors[:3])}..."})
                        else:
                            checks.append({"ok": True, "name": "sw015_manifest_spec_consistency", "detail": f"manifest 5 层与 spec 严格匹配 (canvas {expected['canvas']['width']}x{expected['canvas']['height']})"})
            except SpecParseError as e:
                checks.append({"ok": False, "name": "sw015_spec_load", "detail": str(e)})
            except Exception as e:
                checks.append({"ok": False, "name": "sw015_spec_unexpected", "detail": f"未预期错误: {e}"})

    # 3. 重算 summary
    total = len(checks)
    passed = sum(1 for c in checks if c.get("ok"))
    failed = total - passed
    return {
        "status": "ok" if failed == 0 else "failed",
        "manifest": str(manifest_path),
        "contract_version": r3_result.get("contract_version", "visual-assets v1"),
        "fixture_mode": fixture_mode,
        "allow_proposed": allow_proposed,
        "summary": {**summary, "total": total, "passed": passed, "failed": failed},
        "checks": checks,
    }


def render_summary(result: dict) -> str:
    s = result["summary"]
    lines = [
        f"  status: {result['status']}",
        f"  manifest: {result.get('manifest', '?')}",
        f"  contract: {result.get('contract_version', '?')}",
        f"  fixture_mode: {result.get('fixture_mode', False)}",
        f"  allow_proposed: {result.get('allow_proposed', True)}",
        f"  checks: {s['passed']}/{s['total']} passed ({s['failed']} failed)",
    ]
    failed = [c for c in result.get("checks", []) if not c.get("ok")]
    if failed:
        lines.append(f"  failed ({len(failed)}):")
        for c in failed[:50]:
            lines.append(f"    - {c['name']}: {c['detail'][:140]}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="SW-015 R1 预检 (真实 Trae 设计规格 + R3 严格入口)")
    ap.add_argument("manifest", type=Path, help="manifest.json 路径")
    ap.add_argument("--fixture-mode", action="store_true", help="启用 fixture 模式 (允许 _fixture_mode 字段)")
    ap.add_argument("--strict-design", action="store_true", help="严格模式: spec.id_status=proposed 也算未批准 (用于已批 design 真实场景)")
    ap.add_argument("--json", action="store_true", help="输出 JSON 报告")
    ap.add_argument("--out", type=Path, default=None, help="JSON 报告输出路径")
    args = ap.parse_args()
    result = preflight(args.manifest, fixture_mode=args.fixture_mode, allow_proposed=not args.strict_design)
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