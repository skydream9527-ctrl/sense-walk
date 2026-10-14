#!/usr/bin/env python3
"""
SW-014 dry-run 入口 - 模拟未来 SW-006 实际调用.

不做的事:
- 不调用生图 API
- 不替 Trae 决定雨林构图/色板
- 不伪造已批准 design (PENDING_SW012_APPROVAL 视为不通过)

做的事:
- 接收 design_ref + layer_ids, 预检 design_ref 存在性
- 输出"未来 SW-006 实际生成时应做的步骤"清单
- 输出实际 API 账本 (本任务 0 次)

SW-006 启动时: minimax 替换本脚本为真实生成逻辑.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]


def check_design_ref(design_ref: dict) -> dict:
    if not design_ref:
        return {"ok": False, "reason": "design_ref 缺失"}
    handoff = design_ref.get("handoff", "")
    spec = design_ref.get("spec_file", "")
    spec_sha = design_ref.get("spec_sha256", "")
    if not handoff or not (ROOT / handoff).is_file():
        return {"ok": False, "reason": f"design_ref.handoff 不存在: {handoff}"}
    if spec and not (ROOT / spec).is_file():
        return {"ok": False, "reason": f"design_ref.spec_file 不存在: {spec}"}
    if spec_sha in (None, "", "PENDING", "PENDING_SW012_APPROVAL"):
        return {"ok": False, "reason": f"design_ref.spec_sha256 待批准: {spec_sha}"}
    return {"ok": True, "reason": f"task={design_ref.get('task_id', '?')} approved"}


def main() -> int:
    ap = argparse.ArgumentParser(description="SW-014 dry-run - 模拟 SW-006 未来启动检查")
    ap.add_argument("--design-ref-json", type=Path, required=True, help="design_ref JSON 文件路径 (含 task_id/handoff/spec_file/spec_sha256)")
    ap.add_argument("--layer-ids", nargs="+", default=["mist", "trunks_canopy", "vines_light", "far_glow", "clearing_glow"], help="计划生成的雨林 5 层 ID")
    ap.add_argument("--out", type=Path, default=None, help="dry-run 报告输出路径")
    args = ap.parse_args()

    if not args.design_ref_json.is_file():
        print(f"ERROR: design_ref JSON 不存在: {args.design_ref_json}", file=sys.stderr)
        return 2
    design_ref = json.loads(args.design_ref_json.read_text())

    design_check = check_design_ref(design_ref)
    report = {
        "task_id": "SW-006",
        "dry_run": True,
        "api_attempts_this_dry_run": 0,
        "design_ref_check": design_check,
        "planned_layer_ids": args.layer_ids,
        "next_steps_for_sw006": [
            "1. 等待 SW-012 design handoff approved by Antigravity",
            "2. 切到独立 worktree codex/minimax/SW-006-rainforest-batch",
            "3. 实例化 api_log_template.json (revision=1, budget_remaining=8)",
            "4. 按 layer_ids 顺序生图, 每次写 attempt 到 api_log.attempts",
            "5. 后处理 + 4 底色检查 + 6 阶段合成 (沿 forest 脚本复用)",
            "6. 写 manifest.json (含 design_ref) + 提交独立 worktree 分支",
            "7. 写 H-SW-006-R1.json + .md, 等 Antigravity 独立审核",
            "8. 通过后由 ZCode 在 SW-007 单独入包 (不在本任务范围)",
        ],
        "forbidden_in_sw006": [
            "不替 Trae 决定雨林构图/色板/光效",
            "不绕过 design_ref 调生图 API",
            "不重置账本 (R1/R2/R3 累计 8 次, 不重命名轮次清零)",
            "不写 CC0 / 不转售",
        ],
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if design_check["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())