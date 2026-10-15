#!/usr/bin/env python3
"""Bootstrap observations against published R2; never a formal approval.

Only read the producer checkout. All mutations are synthetic fixtures in a
temporary directory; no real registry, design or image is changed. No API calls.
"""
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

from PIL import Image

sys.dont_write_bytecode = True


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    rel = Path("design/assets/rainforest/preflight/SW-014/r2")
    pre = load(root / rel / "scripts/preflight.py", "preflight")
    dry = load(root / rel / "scripts/dry_run.py", "sw014_r2_audit_dry")
    fixture_rel = rel / "fixtures/positive_ok"
    original = root / fixture_rel / "manifest.json"
    original_manifest = json.loads(original.read_text())
    registry = json.loads((root / "docs/collaboration/registry.json").read_text())
    results = {
        "kind": "bootstrap-observation-not-independent-review",
        "source_head": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "scripts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((root / rel / "scripts").glob("*.py"))},
        "root_matches": pre.ROOT == root,
        "published_fixtures": [], "cases": [],
    }
    for p in sorted((root / rel / "fixtures").glob("*/manifest.json")):
        r = pre.preflight(p)
        results["published_fixtures"].append({
            "name": p.parent.name, "status": r["status"], "summary": r["summary"],
            "failed_checks": [c for c in r["checks"] if not c["ok"]],
        })
    results["cases"].append({
        "id": "R2-01", "reason": "Default entry accepts manifest-controlled fixture flag while actual SW-012 is queued",
        "expected": "failed outside an explicit isolated test harness",
        "input_design_ref": original_manifest["design_ref"],
        "actual_preflight": pre.preflight(original),
        "actual_dry_run": dry.check_design_ref(original_manifest["design_ref"]),
    })
    with tempfile.TemporaryDirectory(prefix="sw014-r2-audit-") as tmp:
        test_root = Path(tmp)
        test_fixture = test_root / fixture_rel
        shutil.copytree(root / fixture_rel, test_fixture)
        reg_path = test_root / "docs/collaboration/registry.json"
        reg_path.parent.mkdir(parents=True)
        reg_path.write_text(json.dumps(registry))
        # Only redirect globals in this Python process to a temporary fixture repo.
        pre.ROOT = dry.ROOT = test_root

        def run_case(case_id, manifest, reason):
            path = test_fixture / "audit-manifest.json"
            path.write_text(json.dumps(manifest))
            results["cases"].append({
                "id": case_id, "reason": reason, "expected": "failed",
                "fixture_only": True, "input": copy.deepcopy(manifest),
                "actual_preflight": pre.preflight(path),
                "actual_dry_run": dry.check_design_ref(manifest["design_ref"]),
            })

        m = copy.deepcopy(original_manifest)
        # New synthetic solid RGBA PNG, not an edit to any design or candidate.
        image_path = test_fixture / "webp/opaque-audit-fixture.png"
        Image.new("RGBA", (768, 1376), (20, 30, 20, 255)).save(image_path)
        data = image_path.read_bytes()
        m["layers"][0].update(file="webp/opaque-audit-fixture.png", bytes=len(data),
                              sha256=hashlib.sha256(data).hexdigest())
        run_case("R2-02", m, "Fully opaque RGBA alpha=255 is accepted as 100% transparent; code counts alpha>0")

        m = copy.deepcopy(original_manifest)
        m["layers"][0]["checks"] = []
        run_case("R2-03", m, "Empty required background-check list is accepted")

        m = copy.deepcopy(original_manifest)
        m["api_attempts_total"] = -1
        run_case("R2-04", m, "Negative cumulative API attempts accepted; only field existence checked")

        # This approval exists only in our temporary TEST registry. Its declared
        # current handoff/review are A; candidate input instead references B.
        test_registry = copy.deepcopy(registry)
        approved_handoff_rel = str(fixture_rel / "_design/CURRENT-APPROVED-A.json")
        approved_review_rel = str(fixture_rel / "_design/CURRENT-APPROVED-REVIEW-A.json")
        approved_handoff = {"fixture_only": True, "task_id": "SW-012",
                            "producer": "trae-design", "head_commit": "a" * 40}
        approved_review = {"fixture_only": True, "task_id": "SW-012",
                           "reviewer": "antigravity", "verdict": "approved",
                           "reviewed_commit": "a" * 40, "handoff": approved_handoff_rel}
        (test_root / approved_handoff_rel).write_text(json.dumps(approved_handoff))
        (test_root / approved_review_rel).write_text(json.dumps(approved_review))
        for t in test_registry["tasks"]:
            if t["id"] == "SW-012":
                t.update(status="accepted", latest_handoff=approved_handoff_rel,
                         latest_review=approved_review_rel, integrated_commit="b" * 40)
        reg_path.write_text(json.dumps(test_registry))
        m = copy.deepcopy(original_manifest)
        m["design_ref"].pop("_fixture_mode")
        m["design_ref"].pop("_expected_registry_status")
        hp = test_root / m["design_ref"]["handoff"]
        hp.write_text(json.dumps({"fixture_only": True, "producer": "trae-design",
                                  "task_id": "SW-999", "head_commit": "not-a-sha"}))
        run_case("R2-05", m, "Registry approves handoff/review A but input references B with wrong task and malformed head; both pass without fixture flag")
        results["cases"][-1]["approval_fixture_context"] = {
            "latest_handoff": approved_handoff_rel, "latest_review": approved_review_rel,
            "expected_handoff": approved_handoff, "expected_review": approved_review,
            "note": "Synthetic temporary test metadata, not a real design approval",
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"root_matches": results["root_matches"],
                      "published_fixtures": [(x["name"], x["status"]) for x in results["published_fixtures"]],
                      "cases": [(x["id"], x["actual_preflight"]["status"], x["actual_dry_run"]["ok"])
                                for x in results["cases"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
