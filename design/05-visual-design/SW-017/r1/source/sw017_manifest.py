#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 SW-017 r1 design-manifest.json（枚举本任务全部 source/spec/prompt/preview/audit/
证据副本文件，记录相对仓库路径、sha256、字节数与 role；不列 manifest 自身）。

用法：python3 design/05-visual-design/SW-017/r1/source/sw017_manifest.py
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
R1 = HERE.parent
REPO = R1.parents[3]

ROLE = {
    "README.md": "doc",
    "integration-reference.json": "spec",
    "checklist.md": "doc",
    "prompts.md": "prompt",
}


def role_for(rel: str, name: str) -> str:
    if name in ROLE:
        return ROLE[name]
    if rel.startswith("source/"):
        return "source"
    if rel.startswith("previews/real_captures/"):
        return "evidence-copy"
    if rel.startswith("previews/findings/") and rel.endswith(".json"):
        return "audit"
    if rel.startswith("previews/"):
        return "preview"
    return "other"


def main() -> None:
    files = []
    for p in sorted(R1.rglob("*")):
        if not p.is_file() or p.name == "design-manifest.json" or p.name.startswith("."):
            continue
        rel = p.relative_to(R1).as_posix()
        b = p.read_bytes()
        files.append({
            "path": str(p.relative_to(REPO)),
            "sha256": hashlib.sha256(b).hexdigest(),
            "bytes": len(b),
            "role": role_for(rel, p.name),
        })

    manifest = {
        "schema_version": 1,
        "task_id": "SW-017",
        "revision": 1,
        "producer": "trae-design",
        "created_on": "2026-10-18",
        "updated_on": "2026-10-18",
        "spec_file": "design/05-visual-design/SW-017/r1/integration-reference.json",
        "kind": "integration_reference",
        "note": ("森林 800m 双模式应用验图参照；previews/real_captures 为 "
                 "H-SW-010-R1/H-SW-005-R2 作者证据逐字节副本；其余 png 为带角标设计模拟；"
                 "零付费/生图 API。"),
        "files": files,
    }
    (R1 / "design-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"listed {len(files)} files: {dict(Counter(f['role'] for f in files))}")


if __name__ == "__main__":
    main()
