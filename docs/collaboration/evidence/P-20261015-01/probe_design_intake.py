#!/usr/bin/env python3
"""Read-only cross-role schema audit; all approval metadata below is temporary.

No real design, source, registry, approval or image is modified; no API calls.
This is bootstrap observation, not a replacement for an independent QA review.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    source = root / "design/assets/rainforest/preflight/SW-014/r3/scripts/preflight.py"
    spec_loader = importlib.util.spec_from_file_location("sw014_intake_audit", source)
    pre = importlib.util.module_from_spec(spec_loader)
    spec_loader.loader.exec_module(pre)
    actual_spec = json.loads((root / "design/05-visual-design/SW-011/r1/design-spec.json").read_text())
    template = json.loads((root / "docs/collaboration/templates/design-spec.json.example").read_text())
    results = {
        "kind": "bootstrap-cross-role-intake-observation-not-independent-review",
        "source_head": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "script_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "schema_cases": [],
    }
    for name, spec in [("approved-SW-011", actual_spec), ("published-design-template", template)]:
        results["schema_cases"].append({
            "name": name, "input_ids": [l["id"] for l in spec["layers"]],
            "expected_layer_count": len(spec["layers"]),
            "actual_extracted_layers": pre.extract_spec_layers(spec),
        })
    with tempfile.TemporaryDirectory(prefix="sw-design-intake-audit-") as tmp:
        test_root = Path(tmp)
        design = test_root / "design/test-only"
        docs = test_root / "docs/collaboration"
        design.mkdir(parents=True)
        docs.mkdir(parents=True)
        # Synthetic acceptance chain exists only in this temporary directory.
        hp, rp, sp = "design/test-only/handoff.json", "design/test-only/review.json", "design/test-only/spec.json"
        handoff = {"fixture_only": True, "task_id": "SW-012", "producer": "trae-design", "head_commit": "a" * 40}
        review = {"fixture_only": True, "task_id": "SW-012", "reviewer": "antigravity", "producer": "trae-design", "handoff": hp, "reviewed_commit": "a" * 40, "verdict": "approved"}
        (test_root / hp).write_text(json.dumps(handoff))
        (test_root / rp).write_text(json.dumps(review))
        (docs / "registry.json").write_text(json.dumps({"fixture_only": True, "tasks": [{
            "id": "SW-012", "owner": "trae-design", "kind": "design", "status": "accepted",
            "latest_handoff": hp, "latest_review": rp,
        }]}))
        pre.ROOT = test_root
        pre.load_minimax_history = lambda: {"cumulative_attempts": 14, "revisions": []}
        results["empty_candidate_cases"] = []
        for name, layers in [("published-id-type-shape", actual_spec["layers"]), ("empty-spec-layers", [])]:
            synthetic_spec = {"fixture_only": True, "task_id": "SW-012", "scene_id": "rainforest", "layers": copy.deepcopy(layers)}
            (test_root / sp).write_text(json.dumps(synthetic_spec))
            manifest = {"schema_version": 1, "task_id": "SW-006", "revision": 1, "producer": "minimax", "scene_id": "rainforest",
                        "api_attempts_this_revision": 0, "api_attempts_total": 14, "cost": 0, "layers": [],
                        "design_ref": {"task_id": "SW-012", "handoff": hp, "spec_file": sp,
                                       "spec_sha256": hashlib.sha256((test_root / sp).read_bytes()).hexdigest()}}
            mp = design / "manifest.json"
            mp.write_text(json.dumps(manifest))
            results["empty_candidate_cases"].append({
                "name": name, "fixture_only": True, "expected_status": "failed",
                "input_spec": synthetic_spec, "input_manifest": manifest,
                "actual": pre.preflight(mp),
            })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"schema_cases": [(x["name"], x["expected_layer_count"], len(x["actual_extracted_layers"])) for x in results["schema_cases"]],
                      "empty_candidate_cases": [(x["name"], x["actual"]["status"]) for x in results["empty_candidate_cases"]]}))


if __name__ == "__main__":
    main()
