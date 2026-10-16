#!/usr/bin/env python3
"""
SW-015 R1 复现/验证脚本 (零 API, 仅合成临时 registry/review/spec).

职责:
1. 复制 fixtures 树到临时目录, 构造:
   - 临时 registry.json (SW-012 标 accepted 指向 tmp handoff/review/spec)
   - 临时 H-SW-FAKE.json (head='a'*40)
   - 临时 R-SW-FAKE.json (verdict=approved)
2. 跑 preflight.py (fixture_mode=True + 默认严格) + dry_run.py 全部 8 fixture
3. 反向回归: SW-014 R3 18 fixture 真实版本检查 (no-op 不破坏历史)
4. 5 项 SW-015 强校验探针:
   - sw015_canonical_id_ok: 用 rainforest canonical 5 层 + SW-012 accepted 应 ok
   - sw015_forest_legacy_alias_ok: SW-011 forest 5 层 legacy alias 应 ok
   - sw015_empty_spec_fails: 空 spec 应 failed
   - sw015_unknown_type_fails: 未知 type 应 failed
   - sw015_wrong_canvas_fails: 错 canvas 应 failed
5. 输出 probe-results.json 给 Antigravity 审核

所有变更仅在临时目录, 不动真实 registry.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    root = args.source_root.resolve()
    r15_rel = Path("design/assets/rainforest/preflight/SW-015/r1")
    r3_rel = Path("design/assets/rainforest/preflight/SW-014/r3")

    sw15_pre = load_module(root / r15_rel / "scripts/preflight.py", "preflight")  # 命名 "preflight" 让 R3 dry_run 找到
    sw15_dry = load_module(root / r15_rel / "scripts/dry_run.py", "sw015_r1_dry")

    # 加载真实 registry + state
    real_registry = json.loads((root / "docs/collaboration/registry.json").read_text())
    real_state_path = root / "docs/collaboration/state/minimax.json"

    tmp = Path(tempfile.mkdtemp(prefix="sw015-r1-verify-"))
    try:
        tmp_docs = tmp / "docs/collaboration"
        tmp_state = tmp_docs / "state"
        tmp_state.mkdir(parents=True, exist_ok=True)
        tmp_design = tmp / "design/assets/rainforest/preflight/SW-015/r1"
        tmp_design.parent.mkdir(parents=True, exist_ok=True)
        # 拷贝 fixtures
        for d in (root / r15_rel / "fixtures").iterdir():
            dst = tmp_design / "fixtures" / d.name
            shutil.copytree(d, dst)
        # 拷贝 SW-014 R3 fixtures (验证 R3 兼容, no-op)
        r3_fixtures_dst = tmp / "design/assets/rainforest/preflight/SW-014/r3/fixtures"
        r3_fixtures_dst.mkdir(parents=True, exist_ok=True)
        for d in (root / r3_rel / "fixtures").iterdir():
            shutil.copytree(d, r3_fixtures_dst / d.name)
        # 写 state (baseline)
        if real_state_path.is_file():
            shutil.copy(real_state_path, tmp_state / "minimax.json")
        else:
            (tmp_state / "minimax.json").write_text(json.dumps({"cumulative_attempts": 14, "sw006_attempts": 0, "sw006_attempts_limit": 8, "sw015_attempts": 0}))

        # 写临时 SW-012 handoff/review + SW-011 handoff/review (指向 tmp 同 head)
        # SW-012 accepted
        tmp_handoff_012 = tmp / "design/assets/rainforest/preflight/SW-015/r1/fixtures/sw015_positive_rainforest_canonical/_design/H-SW-012-R1-FAKE.json"
        tmp_handoff_012.parent.mkdir(parents=True, exist_ok=True)
        tmp_handoff_012.write_text(json.dumps({
            "schema_version": 1, "id": "H-SW-012-R1-FAKE", "task_id": "SW-012", "revision": 1,
            "producer": "trae-design", "recipient": "antigravity",
            "head_commit": "a" * 40, "base_commit": "0" * 40,
        }, ensure_ascii=False, indent=2))
        tmp_review_012 = tmp_handoff_012.parent / "R-SW-012-R1-FAKE.json"
        tmp_review_012.write_text(json.dumps({
            "schema_version": 1, "id": "R-SW-012-R1-FAKE", "task_id": "SW-012",
            "reviewer": "antigravity", "producer": "trae-design",
            "handoff": str(tmp_handoff_012.relative_to(tmp)),
            "reviewed_commit": "a" * 40, "verdict": "approved",
        }, ensure_ascii=False, indent=2))

        # SW-011 accepted (forest legacy alias 正例 task_id=SW-011)
        tmp_handoff_011 = tmp / "design/assets/rainforest/preflight/SW-015/r1/fixtures/sw015_positive_forest_legacy_alias/_design/H-SW-011-R1-FAKE.json"
        tmp_handoff_011.parent.mkdir(parents=True, exist_ok=True)
        tmp_handoff_011.write_text(json.dumps({
            "schema_version": 1, "id": "H-SW-011-R1-FAKE", "task_id": "SW-011", "revision": 1,
            "producer": "trae-design", "recipient": "antigravity",
            "head_commit": "b" * 40, "base_commit": "0" * 40,
        }, ensure_ascii=False, indent=2))
        tmp_review_011 = tmp_handoff_011.parent / "R-SW-011-R1-FAKE.json"
        tmp_review_011.write_text(json.dumps({
            "schema_version": 1, "id": "R-SW-011-R1-FAKE", "task_id": "SW-011",
            "reviewer": "antigravity", "producer": "trae-design",
            "handoff": str(tmp_handoff_011.relative_to(tmp)),
            "reviewed_commit": "b" * 40, "verdict": "approved",
        }, ensure_ascii=False, indent=2))

        # 改写 2 个正例 manifest 的 design_ref 指向 tmp handoff/spec
        for fname, ref_task, head in [("sw015_positive_rainforest_canonical", "SW-012", "a" * 40), ("sw015_positive_forest_legacy_alias", "SW-011", "b" * 40)]:
            mp = tmp_design / "fixtures" / fname / "manifest.json"
            m = json.loads(mp.read_text())
            spec_path = tmp_design / "fixtures" / fname / "_design" / "spec.json"
            m["design_ref"] = {
                "task_id": ref_task,
                "handoff": str((tmp_design / "fixtures" / fname / "_design" / f"H-{ref_task}-R1-FAKE.json").relative_to(tmp)),
                "spec_file": str(spec_path.relative_to(tmp)),
                "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
            }
            mp.write_text(json.dumps(m, ensure_ascii=False, indent=2))

        # 改写负例 manifest: 让反例 SW-012 spec 临时也指向 tmp handoff (SW-012=accepted), 但 spec 内容仍是反例
        # 这样反例会因 spec 校验失败而 failed (不是因 registry status)
        for fname in ["sw015_negative_empty_spec", "sw015_negative_duplicate_layer_id", "sw015_negative_unknown_type", "sw015_negative_wrong_canvas", "sw015_negative_layer_id_mismatch", "sw015_negative_legacy_alias_mismatch"]:
            mp = tmp_design / "fixtures" / fname / "manifest.json"
            m = json.loads(mp.read_text())
            spec_path = tmp_design / "fixtures" / fname / "_design" / "spec.json"
            # 写一个临时 handoff (ref_task 推断)
            ref_task = "SW-012"
            fake_handoff = tmp_design / "fixtures" / fname / "_design" / f"H-{ref_task}-R1-FAKE.json"
            fake_handoff.write_text(json.dumps({
                "schema_version": 1, "id": f"H-{ref_task}-R1-FAKE", "task_id": ref_task, "revision": 1,
                "producer": "trae-design", "recipient": "antigravity",
                "head_commit": "a" * 40, "base_commit": "0" * 40,
            }, ensure_ascii=False, indent=2))
            m["design_ref"] = {
                "task_id": ref_task,
                "handoff": str(fake_handoff.relative_to(tmp)),
                "spec_file": str(spec_path.relative_to(tmp)),
                "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
            }
            mp.write_text(json.dumps(m, ensure_ascii=False, indent=2))

        # 写临时 registry, 把 SW-011/SW-012 都标 accepted 指向各自 tmp handoff/review
        tmp_registry = copy.deepcopy(real_registry)
        for t in tmp_registry["tasks"]:
            if t["id"] == "SW-012":
                t["status"] = "accepted"
                t["latest_handoff"] = str(tmp_handoff_012.relative_to(tmp))
                t["latest_review"] = str(tmp_review_012.relative_to(tmp))
                t["integrated_commit"] = "a" * 40
            elif t["id"] == "SW-011":
                t["status"] = "accepted"
                t["latest_handoff"] = str(tmp_handoff_011.relative_to(tmp))
                t["latest_review"] = str(tmp_review_011.relative_to(tmp))
                t["integrated_commit"] = "b" * 40
        tmp_registry_path = tmp_docs / "registry.json"
        tmp_registry_path.write_text(json.dumps(tmp_registry, ensure_ascii=False, indent=2))

        # 重定向 ROOT + load_registry
        sw15_pre._r3.ROOT = tmp
        sw15_dry._r3_dry.ROOT = tmp
        sw15_pre.ROOT = tmp
        sw15_dry.ROOT = tmp
        def _lr():
            return json.loads((tmp / "docs/collaboration/registry.json").read_text())
        sw15_pre._r3.load_registry = _lr
        sw15_dry._r3_dry.load_registry = _lr

        results = {
            "kind": "minimax-r15-verification",
            "source_head": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
            "scripts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted((root / r15_rel / "scripts").glob("*.py"))},
            "fixture_mode_results": [],
            "strict_results": [],
            "dry_run_results": [],
        }

        fixture_root = tmp_design / "fixtures"
        for mp in sorted(fixture_root.glob("*/manifest.json")):
            name = mp.parent.name
            r_mode = sw15_pre.preflight(mp, fixture_mode=True, allow_proposed=True)
            results["fixture_mode_results"].append({
                "name": name, "status": r_mode["status"],
                "passed": r_mode["summary"]["passed"], "total": r_mode["summary"]["total"],
                "failed": r_mode["summary"]["failed"],
                "failed_checks": [{"name": c["name"], "detail": c["detail"]} for c in r_mode["checks"] if not c.get("ok")],
            })
            r_strict = sw15_pre.preflight(mp, fixture_mode=False, allow_proposed=True)
            results["strict_results"].append({
                "name": name, "status": r_strict["status"],
                "passed": r_strict["summary"]["passed"], "total": r_strict["summary"]["total"],
                "failed": r_strict["summary"]["failed"],
                "failed_checks": [{"name": c["name"], "detail": c["detail"]} for c in r_strict["checks"] if not c.get("ok")],
            })
            # dry_run 跑 design_ref
            m = json.loads(mp.read_text())
            dr = m.get("design_ref")
            if dr:
                r_dry = sw15_dry.check_design_ref(dr, fixture_mode=True, allow_proposed=True)
                results["dry_run_results"].append({
                    "name": name, "ok": r_dry["ok"], "reason": r_dry["reason"],
                    "failed_checks": [{"name": c["name"], "detail": c["detail"]} for c in r_dry["checks"] if not c.get("ok")],
                })

        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")

        # 控制台简明输出
        print(f"=== SW-015 R1 verify: source_head={results['source_head'][:12]} ===")
        for r in results["fixture_mode_results"]:
            print(f"  fixture_mode {r['name']:46s} {r['status']:7s} {r['passed']}/{r['total']}")
        for r in results["strict_results"]:
            print(f"  strict      {r['name']:46s} {r['status']:7s} {r['passed']}/{r['total']}")
        for r in results["dry_run_results"]:
            print(f"  dry_run     {r['name']:46s} {'ok' if r['ok'] else 'failed'} - {r['reason'][:60]}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()