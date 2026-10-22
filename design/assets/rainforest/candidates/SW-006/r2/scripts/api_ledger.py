#!/usr/bin/env python3
"""
SW-006 R2 付费 API 尝试账本 (跨 revision 持久, 零 API).

为什么需要独立账本:
- SW-006 任务预算 8 次尝试是 **跨所有 revision 累计** 的 (R1 已用 0 次).
  SW-014 R3 / SW-015 R1 的 preflight 只校验 manifest 自报的
  `api_attempts_this_revision` / `api_attempts_total` 两个整数, 无法阻止"换 revision 重置".
- 协议要求: 发出请求前写持久账本, 并检查下一次调用是否会超限;
  失败/超时/重试同样计入; 账本与 state 不得回退或丢记录.

两个计数互相独立, 不得混淆:
  - sw006_attempts:            SW-006 任务级累计尝试数 (上限 8)
  - project_lifetime_attempts:  项目级累计尝试数 = baseline(14) + sw006_attempts

账本文件 (任务级, 位于 r1/r2 之上, 因此天然跨 revision):
  design/assets/rainforest/candidates/SW-006/api_ledger.json

state 文件 (交叉校验, 不得回退):
  docs/collaboration/state/minimax.json  -> cumulative_attempts / sw006_attempts

本模块不联网, 不调用任何生图服务, 只负责记账与预算裁决.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- 常量 ---

#: SW-006 任务级总尝试上限 (跨所有 revision)
SW006_ATTEMPTS_LIMIT = 8

#: 项目级历史基线 (SW-002 R1 全部 14 次, 已尽). 与 SW-006 任务计数分开.
PROJECT_LIFETIME_BASELINE = 14

#: 合法结局. 失败/超时同样计入预算.
OUTCOMES = ("success", "failed", "timeout")

#: 允许的 revision 标识 (仅用于账目可读性, 不参与预算计算)
REVISION_IDS = ("r1", "r2", "r3", "r4")

# --- 路径 ---

SCRIPT_DIR = Path(__file__).resolve().parent
#: scripts/ -> r2/ -> SW-006/ -> candidates/ -> rainforest/ -> assets/ -> design/ -> repo root
#: parents[0]=r2 [1]=SW-006 [2]=candidates [3]=rainforest [4]=assets [5]=design [6]=repo root
REPO_ROOT = SCRIPT_DIR.parents[6]

LEDGER_PATH = REPO_ROOT / "design" / "assets" / "rainforest" / "candidates" / "SW-006" / "api_ledger.json"
STATE_PATH = REPO_ROOT / "docs" / "collaboration" / "state" / "minimax.json"


class LedgerError(Exception):
    """账本被破坏或预算裁决失败."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_ledger() -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "task_id": "SW-006",
        "sw006_attempts_limit": SW006_ATTEMPTS_LIMIT,
        "project_lifetime_baseline": PROJECT_LIFETIME_BASELINE,
        "entries": [],
    }


def _is_int(value: Any) -> bool:
    # bool 是 int 的子类, 必须显式排除
    return isinstance(value, int) and not isinstance(value, bool)


def load_ledger(path: Optional[Path] = None) -> Dict[str, Any]:
    """读取并校验账本. 缺文件 => 空账本 (仅当 state 也确认从未用过时才允许)."""
    p = Path(path) if path else LEDGER_PATH
    if not p.is_file():
        return _default_ledger()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise LedgerError(f"账本不是合法 JSON: {p}: {e}") from e
    if not isinstance(data, dict):
        raise LedgerError(f"账本根不是 object: {p}")
    if data.get("schema_version") != 1:
        raise LedgerError(f"账本 schema_version != 1: {data.get('schema_version')!r}")
    if data.get("task_id") != "SW-006":
        raise LedgerError(f"账本 task_id != SW-006: {data.get('task_id')!r}")
    limit = data.get("sw006_attempts_limit")
    if not _is_int(limit) or limit <= 0:
        raise LedgerError(f"账本 sw006_attempts_limit 必须为正整数: {limit!r}")
    if limit != SW006_ATTEMPTS_LIMIT:
        raise LedgerError(f"账本上限与任务预算不一致: {limit} != {SW006_ATTEMPTS_LIMIT}")
    baseline = data.get("project_lifetime_baseline")
    if not _is_int(baseline) or baseline < 0:
        raise LedgerError(f"账本 project_lifetime_baseline 必须为非负整数: {baseline!r}")
    if baseline != PROJECT_LIFETIME_BASELINE:
        raise LedgerError(f"账本 baseline 与项目历史不一致: {baseline} != {PROJECT_LIFETIME_BASELINE}")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise LedgerError("账本 entries 必须是数组")
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise LedgerError(f"账本 entries[{i}] 不是 object")
        seq = e.get("seq")
        if not _is_int(seq) or seq < 1:
            raise LedgerError(f"账本 entries[{i}].seq 必须为正整数: {seq!r}")
        if seq != i + 1:
            raise LedgerError(f"账本 entries[{i}].seq 不连续: {seq} != {i + 1}")
        outcome = e.get("outcome")
        if outcome not in OUTCOMES and outcome != "reserved":
            raise LedgerError(f"账本 entries[{i}].outcome 非法: {outcome!r}")
        revision = e.get("revision")
        if revision not in REVISION_IDS:
            raise LedgerError(f"账本 entries[{i}].revision 非法: {revision!r}")
    return data


def save_ledger(data: Dict[str, Any], path: Optional[Path] = None) -> Path:
    p = Path(path) if path else LEDGER_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def sw006_attempts(data: Dict[str, Any]) -> int:
    """SW-006 任务级累计尝试数 = 已记账条目数 (reserved 也占位, 防止并发绕过)."""
    return len(data.get("entries", []))


def project_lifetime_attempts(data: Dict[str, Any]) -> int:
    return data.get("project_lifetime_baseline", PROJECT_LIFETIME_BASELINE) + sw006_attempts(data)


def read_state_counters(path: Optional[Path] = None) -> Dict[str, Any]:
    """读 state/minimax.json 的两个计数. 缺文件视为不可用 (返回 present=False)."""
    p = Path(path) if path else STATE_PATH
    if not p.is_file():
        return {"present": False, "cumulative_attempts": None, "sw006_attempts": None}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise LedgerError(f"state 不是合法 JSON: {p}: {e}") from e
    return {
        "present": True,
        "cumulative_attempts": data.get("cumulative_attempts"),
        "sw006_attempts": data.get("sw006_attempts"),
    }


def assert_consistent_with_state(data: Dict[str, Any], state_path: Optional[Path] = None) -> List[str]:
    """账本与 state 的 **致命** 不一致. 返回问题列表 (空 = 一致).

    致命条件 (回退 / 丢记录):
    - state.sw006_attempts > 账本已记条数  => 账本丢了记录
    - state.cumulative_attempts < 基线 14     => 项目级计数回退
    - state 计数缺失或非非负整数

    非致命 (lag): state 落后于账本. 账本是唯一真值来源, 允许短暂滞后,
    由 sync_state() 在交付前对齐; 不因此阻断生产调用.
    """
    problems: List[str] = []
    state = read_state_counters(state_path)
    if not state["present"]:
        return problems
    used = sw006_attempts(data)
    st_sw006 = state["sw006_attempts"]
    st_total = state["cumulative_attempts"]
    if st_sw006 is None or not _is_int(st_sw006) or st_sw006 < 0:
        problems.append(f"state.sw006_attempts 缺失或非非负整数: {st_sw006!r}")
    elif st_sw006 > used:
        problems.append(
            f"state.sw006_attempts={st_sw006} > 账本已记 {used} (账本丢失记录, 不得回退)"
        )
    if st_total is None or not _is_int(st_total) or st_total < 0:
        problems.append(f"state.cumulative_attempts 缺失或非非负整数: {st_total!r}")
    elif st_total < PROJECT_LIFETIME_BASELINE:
        problems.append(
            f"state.cumulative_attempts={st_total} < 项目历史基线 {PROJECT_LIFETIME_BASELINE} (不得回退)"
        )
    return problems


def state_lag_notes(data: Dict[str, Any], state_path: Optional[Path] = None) -> List[str]:
    """state 落后于账本的提示 (非致命)."""
    notes: List[str] = []
    state = read_state_counters(state_path)
    if not state["present"]:
        return notes
    used = sw006_attempts(data)
    lifetime = project_lifetime_attempts(data)
    st_sw006 = state["sw006_attempts"]
    st_total = state["cumulative_attempts"]
    if isinstance(st_sw006, int) and not isinstance(st_sw006, bool) and st_sw006 < used:
        notes.append(f"state.sw006_attempts={st_sw006} 落后于账本 {used} (交付前需 sync)")
    if isinstance(st_total, int) and not isinstance(st_total, bool) and st_total < lifetime:
        notes.append(f"state.cumulative_attempts={st_total} 落后于账本推算 {lifetime} (交付前需 sync)")
    return notes


def sync_state(data: Dict[str, Any], path: Optional[Path] = None,
               state_path: Optional[Path] = None) -> Dict[str, Any]:
    """把 state 的两个计数对齐到账本 (只前进, 不回退). 返回更新后的 state 计数."""
    p = Path(state_path) if state_path else STATE_PATH
    if not p.is_file():
        raise LedgerError(f"state 文件不存在: {p}")
    try:
        state = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise LedgerError(f"state 不是合法 JSON: {p}: {e}") from e
    used = sw006_attempts(data)
    lifetime = project_lifetime_attempts(data)
    cur_sw006 = state.get("sw006_attempts")
    cur_total = state.get("cumulative_attempts")
    if not _is_int(cur_sw006) or cur_sw006 < 0:
        raise LedgerError(f"state.sw006_attempts 非法, 拒绝自动修正: {cur_sw006!r}")
    if not _is_int(cur_total) or cur_total < 0:
        raise LedgerError(f"state.cumulative_attempts 非法, 拒绝自动修正: {cur_total!r}")
    if cur_sw006 > used:
        raise LedgerError(
            f"state.sw006_attempts={cur_sw006} > 账本 {used}: 账本丢记录, 拒绝覆盖 state"
        )
    if cur_total < PROJECT_LIFETIME_BASELINE:
        raise LedgerError(
            f"state.cumulative_attempts={cur_total} < 基线 {PROJECT_LIFETIME_BASELINE}, 拒绝覆盖"
        )
    state["sw006_attempts"] = used
    state["cumulative_attempts"] = lifetime
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"sw006_attempts": used, "cumulative_attempts": lifetime}


def check_next_call_allowed(data: Dict[str, Any], state_path: Optional[Path] = None) -> List[str]:
    """检查下一次调用是否会超限. 返回问题列表 (空 = 允许)."""
    problems = assert_consistent_with_state(data, state_path)
    used = sw006_attempts(data)
    if used >= SW006_ATTEMPTS_LIMIT:
        problems.append(
            f"下一次调用会超限: 已用 {used}/{SW006_ATTEMPTS_LIMIT} 次 SW-006 尝试"
        )
    return problems


def reserve(
    layer_id: str,
    revision: str,
    *,
    prompt_ref: str,
    source_resolution: str,
    request_meta: Optional[Dict[str, Any]] = None,
    path: Optional[Path] = None,
    state_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """在发出请求 **之前** 写盘占位.

    失败/超时/重试同样占额度: 额度在请求发出前就被锁定.
    """
    if revision not in REVISION_IDS:
        raise LedgerError(f"revision 非法: {revision!r}")
    if not layer_id or not isinstance(layer_id, str):
        raise LedgerError("layer_id 缺失")
    if not source_resolution or not isinstance(source_resolution, str):
        raise LedgerError("source_resolution 缺失 (必须记录调用来源分辨率)")

    data = load_ledger(path)
    problems = check_next_call_allowed(data, state_path)
    if problems:
        raise LedgerError("拒绝记账: " + "; ".join(problems))

    entry = {
        "seq": sw006_attempts(data) + 1,
        "revision": revision,
        "layer_id": layer_id,
        "outcome": "reserved",
        "prompt_ref": prompt_ref,
        "source_resolution": source_resolution,
        "reserved_at": _now(),
        "settled_at": None,
        "note": None,
    }
    if request_meta:
        entry["request_meta"] = request_meta
    data.setdefault("entries", []).append(entry)
    save_ledger(data, path)
    return entry


def settle(
    seq: int,
    outcome: str,
    *,
    note: Optional[str] = None,
    actual_resolution: Optional[str] = None,
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """把占位条目结算为真实结局 (success/failed/timeout).

    actual_resolution: 实际返回的来源分辨率 (reserve 时只有请求参数, 结算时补真实值).
    """
    if outcome not in OUTCOMES:
        raise LedgerError(f"outcome 非法: {outcome!r} (允许 {OUTCOMES})")
    data = load_ledger(path)
    entries = data["entries"]
    if not _is_int(seq) or seq < 1 or seq > len(entries):
        raise LedgerError(f"seq 不存在: {seq!r}")
    entry = entries[seq - 1]
    if entry.get("outcome") != "reserved":
        raise LedgerError(f"seq {seq} 已结算过 (outcome={entry.get('outcome')!r}), 不得重复结算")
    entry["outcome"] = outcome
    entry["settled_at"] = _now()
    if note:
        entry["note"] = note
    if actual_resolution:
        entry["actual_resolution"] = actual_resolution
    save_ledger(data, path)
    return entry


def summary(path: Optional[Path] = None, state_path: Optional[Path] = None) -> Dict[str, Any]:
    data = load_ledger(path)
    used = sw006_attempts(data)
    counts = {o: 0 for o in OUTCOMES}
    for e in data["entries"]:
        counts[e["outcome"]] = counts.get(e["outcome"], 0) + 1
    fatal = assert_consistent_with_state(data, state_path)
    lag = state_lag_notes(data, state_path)
    return {
        "sw006_attempts_used": used,
        "sw006_attempts_limit": SW006_ATTEMPTS_LIMIT,
        "sw006_attempts_remaining": SW006_ATTEMPTS_LIMIT - used,
        "project_lifetime_attempts": project_lifetime_attempts(data),
        "project_lifetime_baseline": PROJECT_LIFETIME_BASELINE,
        "outcomes": counts,
        "state_consistent": not fatal,
        "state_problems": fatal,
        "state_lag_notes": lag,
        "next_call_allowed": not check_next_call_allowed(data, state_path),
        "ledger_path": str(Path(path) if path else LEDGER_PATH),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="SW-006 R2 API 尝试账本 (零 API)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_summary = sub.add_parser("summary", help="打印账本摘要")
    p_summary.add_argument("--ledger", type=Path, default=None)
    p_summary.add_argument("--state", type=Path, default=None)

    p_reserve = sub.add_parser("reserve", help="请求前占位 (写盘)")
    p_reserve.add_argument("--layer-id", required=True)
    p_reserve.add_argument("--revision", required=True)
    p_reserve.add_argument("--prompt-ref", required=True)
    p_reserve.add_argument("--source-resolution", required=True)
    p_reserve.add_argument("--ledger", type=Path, default=None)
    p_reserve.add_argument("--state", type=Path, default=None)

    p_settle = sub.add_parser("settle", help="结算占位条目")
    p_settle.add_argument("--seq", type=int, required=True)
    p_settle.add_argument("--outcome", required=True, choices=list(OUTCOMES))
    p_settle.add_argument("--note", default=None)
    p_settle.add_argument("--actual-resolution", default=None, help="实际返回的来源分辨率")
    p_settle.add_argument("--ledger", type=Path, default=None)

    args = ap.parse_args()
    try:
        if args.cmd == "summary":
            print(json.dumps(summary(args.ledger, args.state), ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "reserve":
            entry = reserve(
                args.layer_id,
                args.revision,
                prompt_ref=args.prompt_ref,
                source_resolution=args.source_resolution,
                path=args.ledger,
                state_path=args.state,
            )
            print(json.dumps(entry, ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "settle":
            entry = settle(args.seq, args.outcome, note=args.note,
                           actual_resolution=args.actual_resolution, path=args.ledger)
            print(json.dumps(entry, ensure_ascii=False, indent=2))
            return 0
    except LedgerError as e:
        print(f"LEDGER_ERROR: {e}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
