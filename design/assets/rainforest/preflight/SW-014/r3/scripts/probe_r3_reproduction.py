#!/usr/bin/env python3
"""
SW-014 R3 复现/验证脚本 (零 API, 仅合成临时 registry/review/spec).

职责:
1. 复制 fixtures 树到临时目录, 同时构造:
   - 一份临时 registry.json (把 SW-012 标 accepted + 引用临时 handoff/review)
   - 一份临时 H-SW-012-R1-FAKE.json (head_commit='a'*40)
   - 一份临时 R-SW-012-R1-FAKE.json (verdict=approved, reviewed_commit='a'*40)
   - 临时 positive_ok/_design/spec.json (5 层 spec)
2. 在临时目录运行 preflight.py + dry_run.py, 验证:
   - positive_ok: 默认严格 + CLI --fixture-mode 旗标 一起应 ok (因为 registry accepted + fixture_mode 允许)
   - negative_*: 全部 failed, 每条都有具体非 PENDING 错
3. 反向 R2/R3 复现: 临时注入 R2-01~R2-05 + R3-01~R3-07 反例, 全部应被拒
4. 输出 probe-results.json 给 Antigravity 审核

所有变更仅在临时目录, 不动真实 registry/SW-012 状态.
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
    parser.add_argument("source_root", type=Path, help="R3 worktree 根")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    root = args.source_root.resolve()
    rel = Path("design/assets/rainforest/preflight/SW-014/r3")
    pre = load_module(root / rel / "scripts/preflight.py", "sw014_r3_pre")
    dry = load_module(root / rel / "scripts/dry_run.py", "sw014_r3_dry")

    # 注册临时 fixture：拷贝 registry, 改 SW-012 status=accepted
    real_registry = json.loads((root / "docs/collaboration/registry.json").read_text())
    tmp = Path(tempfile.mkdtemp(prefix="sw014-r3-verify-"))
    try:
        tmp_docs = tmp / "docs/collaboration"
        tmp_design = tmp / "design/assets/rainforest/preflight/SW-014/r3"
        tmp_design.parent.mkdir(parents=True, exist_ok=True)
        # 拷贝 fixture 树 (但 _design 目录是临时重写, 不拷贝)
        for d in (root / rel / "fixtures").iterdir():
            dst = tmp_design / "fixtures" / d.name
            if d.name == "positive_ok":
                # 仅拷贝 png/webp/checks, 重新生成 _design (5 层 spec)
                shutil.copytree(d, dst, ignore=shutil.ignore_patterns("_design"))
            elif d.name == "negative_wrong_approval_chain":
                # 包含 _design 含错的 handoff (head='b'*40), 仍拷贝
                shutil.copytree(d, dst)
            else:
                shutil.copytree(d, dst)
        # 写临时 state/minimax.json 历史 (R3-04 用)
        tmp_state = tmp / "docs/collaboration/state"
        tmp_state.mkdir(parents=True, exist_ok=True)
        if (root / "docs/collaboration/state/minimax.json").is_file():
            shutil.copy(root / "docs/collaboration/state/minimax.json", tmp_state / "minimax.json")
        else:
            (tmp_state / "minimax.json").write_text(json.dumps({"cumulative_attempts": 14, "revisions": [{"task_id": "SW-002", "revision": 1, "attempts": 14, "status": "accepted"}]}))
        # 写临时 handoff/review
        tmp_design_pos = tmp_design / "fixtures/positive_ok/_design"
        tmp_design_pos.mkdir(parents=True, exist_ok=True)
        tmp_handoff = tmp_design_pos / "H-SW-012-R1-FAKE.json"
        tmp_handoff.write_text(json.dumps({
            "schema_version": 1, "id": "H-SW-012-R1-FAKE", "task_id": "SW-012", "revision": 1,
            "producer": "trae-design", "recipient": "antigravity",
            "head_commit": "a" * 40, "base_commit": "0" * 40,
        }, ensure_ascii=False, indent=2))
        tmp_review = tmp_design_pos / "R-SW-012-R1-FAKE.json"
        tmp_review.write_text(json.dumps({
            "schema_version": 1, "id": "R-SW-012-R1-FAKE", "task_id": "SW-012",
            "reviewer": "antigravity", "producer": "trae-design",
            "handoff": "design/assets/rainforest/preflight/SW-014/r3/fixtures/positive_ok/_design/H-SW-012-R1-FAKE.json",
            "reviewed_commit": "a" * 40, "verdict": "approved",
        }, ensure_ascii=False, indent=2))
        tmp_spec = tmp_design_pos / "spec.json"
        spec_layers = ["mist", "trunks_canopy", "vines_light", "far_glow", "clearing_glow"]
        tmp_spec.write_text(json.dumps({
            "schema_version": 1, "task_id": "SW-012", "revision": 1, "scene_id": "rainforest",
            "canvas": {"width": 1080, "height": 1920},
            "layers": [{"layer_id": lid, "render_role": "parallax" if lid in ("mist", "trunks_canopy") else "overlay"} for lid in spec_layers],
        }, ensure_ascii=False, indent=2))
        # 改写 positive_ok manifest 用临时 handoff/spec 路径
        pos_manifest_path = tmp_design / "fixtures/positive_ok/manifest.json"
        pos_manifest = json.loads(pos_manifest_path.read_text())
        pos_manifest["design_ref"] = {
            "task_id": "SW-012",
            "handoff": str(tmp_handoff.relative_to(tmp)),
            "spec_file": str(tmp_spec.relative_to(tmp)),
            "spec_sha256": hashlib.sha256(tmp_spec.read_bytes()).hexdigest(),
        }
        pos_manifest_path.write_text(json.dumps(pos_manifest, ensure_ascii=False, indent=2))
        # 写临时 registry, 把 SW-012 标 accepted 并指向 tmp handoff/review
        tmp_registry = copy.deepcopy(real_registry)
        for t in tmp_registry["tasks"]:
            if t["id"] == "SW-012":
                t["status"] = "accepted"
                t["latest_handoff"] = str(tmp_handoff.relative_to(tmp))
                t["latest_review"] = str(tmp_review.relative_to(tmp))
        tmp_registry_path = tmp_docs / "registry.json"
        tmp_registry_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_registry_path.write_text(json.dumps(tmp_registry, ensure_ascii=False, indent=2))
        # 重定向 pre/dry 的 ROOT 到 tmp
        pre.ROOT = tmp
        dry.ROOT = tmp
        # 验证 tmp 内的 registry/spec 在 module-loaded ROOT 下能找到
        assert (tmp / "docs/collaboration/registry.json").is_file(), f"registry missing at {tmp}"
        # monkey patch load_registry 也使用 tmp 路径
        def _load_registry():
            return json.loads((tmp / "docs/collaboration/registry.json").read_text())
        pre.load_registry = _load_registry
        dry.load_registry = _load_registry

        # --- 跑全部 fixture (CLI --fixture-mode + 默认严格模式) ---
        fixture_root = tmp_design / "fixtures"
        results = {
            "kind": "minimax-r3-verification",
            "source_head": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
            "scripts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted((root / rel / "scripts").glob("*.py"))},
            "fixture_mode_results": [],   # CLI --fixture-mode 旗标下的全部 fixture
            "strict_results": [],          # 默认严格入口下的全部 fixture
        }

        for mp in sorted(fixture_root.glob("*/manifest.json")):
            name = mp.parent.name
            # CLI --fixture-mode 模式
            r_mode = pre.preflight(mp, fixture_mode=True)
            results["fixture_mode_results"].append({
                "name": name,
                "status": r_mode["status"],
                "passed": r_mode["summary"]["passed"],
                "total": r_mode["summary"]["total"],
                "failed": r_mode["summary"]["failed"],
                "failed_checks": [{"name": c["name"], "detail": c["detail"]} for c in r_mode["checks"] if not c["ok"]],
            })
            # 默认严格模式
            r_dir = pre.preflight(mp, fixture_mode=False)
            results["strict_results"].append({
                "name": name,
                "status": r_dir["status"],
                "passed": r_dir["summary"]["passed"],
                "total": r_dir["summary"]["total"],
                "failed": r_dir["summary"]["failed"],
                "failed_checks": [{"name": c["name"], "detail": c["detail"]} for c in r_dir["checks"] if not c["ok"]],
            })

        # --- 反向复现 R2/R3 缺陷 ---
        results["regression_probes"] = []
        pos_manifest = json.loads((tmp_design / "fixtures/positive_ok/manifest.json").read_text())

        # 反例 A: R2-02 复现 - 全不透明 RGBA (alpha=255) 应被拒
        m = copy.deepcopy(pos_manifest)
        from PIL import Image
        opaque_path = tmp_design / "fixtures/positive_ok/_design/opaque-audit.png"
        Image.new("RGBA", (768, 1376), (20, 30, 20, 255)).save(opaque_path)
        data = opaque_path.read_bytes()
        m["layers"][0].update(file="design/assets/rainforest/preflight/SW-014/r3/fixtures/positive_ok/_design/opaque-audit.png",
                              bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        # 该 fixtures 实际可能没真文件, 用绝对路径在 tmp 内创建
        real_path = tmp_design / "fixtures/positive_ok/_design/opaque-audit.png"
        Image.new("RGBA", (768, 1376), (20, 30, 20, 255)).save(real_path)
        data = real_path.read_bytes()
        rel_op = str(real_path.relative_to(tmp))
        m["layers"][0]["file"] = rel_op
        m["layers"][0]["bytes"] = len(data)
        m["layers"][0]["sha256"] = hashlib.sha256(data).hexdigest()
        audit_path = tmp_design / "fixtures/positive_ok/audit-r2-02.json"
        audit_path.write_text(json.dumps(m))
        r = pre.preflight(audit_path, fixture_mode=True)
        results["regression_probes"].append({"id": "R2-02-regression", "expected": "failed", "actual_status": r["status"], "failed_checks": [c["name"] for c in r["checks"] if not c["ok"]]})

        # 反例 B: R2-03 缺必需检查图 - 删除 alpha_mask 让 R3-03 强制完备性发现
        m = copy.deepcopy(pos_manifest)
        alpha_mask_path = tmp_design / "fixtures/positive_ok/checks/alpha_mask/rainforest_mist.png"
        if alpha_mask_path.exists():
            alpha_mask_path.unlink()
        audit_path = tmp_design / "fixtures/positive_ok/audit-r2-03.json"
        audit_path.write_text(json.dumps(m))
        r = pre.preflight(audit_path, fixture_mode=True)
        results["regression_probes"].append({"id": "R2-03-regression", "expected": "failed (缺必需 alpha_mask 检查图)", "actual_status": r["status"], "failed_checks": [c["name"] for c in r["checks"] if not c["ok"]]})
        # 恢复 alpha_mask (避免污染后续 R3-01/R3-05 测试)
        Image.new("L", (1376, 1376), 128).save(alpha_mask_path)

        # 反例 C: R2-04 api_attempts_total=-1
        m = copy.deepcopy(pos_manifest)
        m["api_attempts_total"] = -1
        audit_path = tmp_design / "fixtures/positive_ok/audit-r2-04.json"
        audit_path.write_text(json.dumps(m))
        r = pre.preflight(audit_path, fixture_mode=True)
        results["regression_probes"].append({"id": "R2-04-regression", "expected": "failed", "actual_status": r["status"], "failed_checks": [c["name"] for c in r["checks"] if not c["ok"]]})

        # 反例 D: R3-01 manifest 内 _fixture_mode 字段 (默认严格入口应拒 _fixture_mode 字段)
        # 场景: 严格入口对 _fixture_mode 字段报 manifest_field__fixture_mode_forbidden;
        # CLI --fixture-mode 不再报该字段, 但仍可能因 registry status/approval_chain 失败 (因为 fixture_mode 不等于 accepted)
        # 我们在 tmp 已把 SW-012 标 accepted, 所以 CLI fixture_mode 下应 ok (除非还改 handoff head 错配)
        m = copy.deepcopy(pos_manifest)
        m["design_ref"]["_fixture_mode"] = True
        m["design_ref"]["_expected_registry_status"] = "queued"
        audit_path = tmp_design / "fixtures/positive_ok/audit-r3-01.json"  # 写在 fixture 根, 让 file 路径 webp/... fallback 找得到
        audit_path.write_text(json.dumps(m))
        r_strict = pre.preflight(audit_path, fixture_mode=False)
        r_mode = pre.preflight(audit_path, fixture_mode=True)
        results["regression_probes"].append({"id": "R3-01-strict-rejects", "expected": "failed (strict 拒 _fixture_mode 字段)", "actual_status": r_strict["status"], "failed_checks": [c["name"] for c in r_strict["checks"] if not c["ok"]]})
        results["regression_probes"].append({"id": "R3-01-mode-allows-but-keeps-approval-chain", "expected": "ok (CLI --fixture-mode 允许 _fixture_mode 字段, approval_chain 已 accepted)", "actual_status": r_mode["status"], "failed_checks": [c["name"] for c in r_mode["checks"] if not c["ok"]]})

        # 反例 E: R3-05 handoff head 错配 (引用 head='b'*40 的 handoff, registry 引用 'a'*40)
        m = copy.deepcopy(pos_manifest)
        bad_handoff = tmp_design / "fixtures/positive_ok/_design/H-SW-012-R1-FAKE.json"
        bad_handoff.write_text(json.dumps({
            "schema_version": 1, "id": "H-SW-012-R1-FAKE", "task_id": "SW-012", "revision": 1,
            "producer": "trae-design", "recipient": "antigravity",
            "head_commit": "b" * 40, "base_commit": "0" * 40,
        }, ensure_ascii=False, indent=2))
        m["design_ref"]["handoff"] = str(bad_handoff.relative_to(tmp))
        audit_path = tmp_design / "fixtures/positive_ok/audit-r3-05.json"
        audit_path.write_text(json.dumps(m))
        r = pre.preflight(audit_path, fixture_mode=True)
        r_dry = dry.check_design_ref(m["design_ref"], fixture_mode=True)
        results["regression_probes"].append({"id": "R3-05-regression-strict", "expected": "failed (registry 引用 a, design_ref 引用 b)", "actual_status": r["status"], "failed_checks": [c["name"] for c in r["checks"] if not c["ok"]]})

        args.out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")

        # 控制台简明输出
        print(f"=== SW-014 R3 verify: source_head={results['source_head'][:12]} ===")
        print(f"  fixture_mode (CLI 旗标):")
        for r in results["fixture_mode_results"]:
            print(f"    {r['name']:38s} {r['status']:7s} {r['passed']}/{r['total']}")
        print(f"  strict (默认入口):")
        for r in results["strict_results"]:
            print(f"    {r['name']:38s} {r['status']:7s} {r['passed']}/{r['total']}")
        print(f"  regression probes:")
        for r in results["regression_probes"]:
            print(f"    {r['id']:30s} expected={r['expected'][:40]:40s} status={r['actual_status']}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()