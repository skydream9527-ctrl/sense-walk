#!/usr/bin/env python3
"""
SW-006 调用账本模板 (零 API 写入, 仅结构示例).

SW-006 沿原 8 次总尝试预算 (6 正常 + 2 失败/质量修复).
本模板由 SW-014 预检脚本读取 + 验证 SW-006 实际账本.
不在 R1 重置, 不允许重命名轮次重置.

字段:
- task_id: SW-006
- revision: 1
- attempts: [每次实际生图 API 调用的记录, 包括超时/失败]
- total: 当前累计 (含成功/失败/超时)
- budget_initial: 8
- budget_remaining: budget_initial - total
- cost_usd: 实际累计费用 (unknown if 未返回)

每条 attempt:
- ts: ISO 8601 时间戳
- layer_id: 哪一层 (mist / trunks_canopy / vines_light / far_glow / clearing_glow)
- prompt_sha256: 提示词 SHA256 (避免记录完整 prompt)
- model: 模型名 (例如 "MiniMax-xxx" 或 mcode-tools connector 返回的 model 字段)
- input_refs: 参考图 URL 列表 (input_urls)
- output_node_id: mcode-tools 返回的 node_id
- output_file_name: 实际文件名
- output_url: 短时下载 URL
- local_path: 落地路径
- size_bytes: 文件字节
- sha256: 文件 SHA256
- status: success / failed / timeout
- cost_usd: 单次费用 (unknown if 未返回)
- error: 失败原因 (status != success)
- note: 重试次数 / 备注
"""

import json
from pathlib import Path
from datetime import datetime, timezone

# 模板 - 在 SW-006 第一次调用时由 minimax 实例化
TEMPLATE = {
    "task_id": "SW-006",
    "revision": 1,
    "schema_version": 1,
    "budget_initial": 8,
    "budget_remaining": 8,
    "total": 0,
    "cost_usd": "unknown",
    "attempts": [],
    "_note": "此模板由 SW-014 预检脚本产出的 fixture; SW-006 实际调用时 minimax 自己实例化, 不复用此文件.",
    "_created_at": datetime.now(timezone.utc).isoformat(),
}


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "fixtures" / "api_log_template.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(TEMPLATE, ensure_ascii=False, indent=2))
    print(f"模板已写入: {out.relative_to(Path.cwd())}")
    print(json.dumps(TEMPLATE, ensure_ascii=False, indent=2))