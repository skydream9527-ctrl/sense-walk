#!/usr/bin/env python3
"""Read-only bootstrap audit of SW-014 R1; not a producer fix or formal review.

Run against an isolated checkout of the published MiniMax head. Inputs below are
explicit synthetic fixtures, never approved designs. No network/API/image edits.
"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    scripts = root / "design/assets/rainforest/preflight/SW-014/r1/scripts"
    preflight = load(scripts / "preflight.py", "sw014_audit_preflight")
    dry = load(scripts / "dry_run.py", "sw014_audit_dry")
    results = {
        "audit_kind": "bootstrap-observation-not-independent-approval",
        "source_head": subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "script_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(scripts.glob("*.py"))},
        "root_resolution": {"expected_repo_root": str(root),
                            "actual_preflight_root": str(preflight.ROOT),
                            "actual_dry_run_root": str(dry.ROOT),
                            "matches": preflight.ROOT == root and dry.ROOT == root},
        "cases": [],
    }
    with tempfile.TemporaryDirectory(prefix="sw014-audit-") as tmp:
        base = Path(tmp)
        payload = b"SW-014 AUDIT FIXTURE: this is not an image\n"
        (base / "fake.webp").write_bytes(payload)
        manifest = {
            "schema_version": 1, "task_id": "SW-006", "revision": 1,
            "scene_id": "rainforest", "producer": "minimax",
            "api_attempts_this_revision": 0, "api_attempts_total": 0, "cost": 0,
            "design_ref": {"task_id": "SW-012", "handoff": "", "spec_file": "",
                           "spec_sha256": "0" * 64},
            "layers": [{"layer_id": "unknown_layer", "file": "fake.webp",
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "bytes": len(payload), "width": 0, "height": 0,
                        "alpha_channel": True, "tileable": False, "checks": []}],
        }
        path = base / "manifest.json"
        path.write_text(json.dumps(manifest))
        results["cases"].append({
            "id": "PF-01", "input": json.loads(json.dumps(manifest)), "expected": "failed",
            "reason": "non-image, zero dimensions, no checks, unknown layer, missing approved design",
            "actual": preflight.preflight(path),
        })
        manifest["layers"] = []
        path.write_text(json.dumps(manifest))
        results["cases"].append({
            "id": "PF-02", "input": json.loads(json.dumps(manifest)), "expected": "failed",
            "reason": "empty scene and missing approved design",
            "actual": preflight.preflight(path),
        })
        # An arbitrary local file is not an approved handoff. Absolute input is
        # intentional: shows that merely existing can bypass ROOT/approval.
        dummy = base / "NOT_AN_APPROVED_HANDOFF.json"
        dummy.write_text('{"fixture_only": true}')
        ref = {"task_id": "SW-012", "handoff": str(dummy), "spec_file": "",
               "spec_sha256": "not-a-sha"}
        results["cases"].append({
            "id": "PF-03", "input": ref, "expected": {"ok": False},
            "reason": "dummy file, absent spec and invalid hash; no review/registry approval",
            "actual": dry.check_design_ref(ref),
        })
    approved = root / "design/assets/forest/candidates/SW-002/r1/manifest.json"
    if not approved.is_file():
        candidates = sorted((root / "design/assets/forest").glob("candidates/**/manifest.json"))
        approved = next(p for p in candidates if json.loads(p.read_text()).get("task_id") == "SW-002")
    results["cases"].append({
        "id": "PF-04", "input_file": str(approved.relative_to(root)),
        "expected": "repo-root paths resolve to existing approved candidate files",
        "reason": "contract paths are repo-root-relative, not manifest-directory-relative",
        "actual": preflight.preflight(approved),
    })
    results["reproduction_only"] = True
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"root_matches": results["root_resolution"]["matches"],
                      "cases": [{"id": c["id"], "expected": c["expected"],
                                 "actual": c["actual"].get("status", c["actual"].get("ok"))}
                                for c in results["cases"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
