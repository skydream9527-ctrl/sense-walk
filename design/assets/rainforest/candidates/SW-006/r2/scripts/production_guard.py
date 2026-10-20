#!/usr/bin/env python3
"""
SW-006 R2 生产保护 (零 API): 在发出任何付费调用之前裁决"能不能调用".

背景 (SW-006 任务文件 "调用前先完成零API保护"):
- R1 是 0 API 占位草案, 独立审核 (R-SW-006-R1) 结论 changes_requested, 要求本轮用
  已授权的 8 次预算做真实制作, 并先补足生产保护.
- 旧预检 (SW-014 R3 / SW-015 R1) 只能校验 manifest **自报** 的
  `api_attempts_this_revision` / `api_attempts_total` 两个整数, 且
  ACCEPTED_DIMENSIONS 含森林历史 768x1376. 本轮已复现两个旧入口误放行案例:
    (a) 真实批准链 + 768x1376 图   -> 旧预检 ok
    (b) api_attempts_this_revision=9 / api_attempts_total=23 -> 旧预检 ok
  本模块必须让这两个案例 **失败**.

本模块职责 (全部零 API, 不发起任何网络调用):
1. 复用已批准工具: 通过 importlib 加载 SW-015 R1 preflight/dry_run 与 SW-014 R3
   (importlib 复用其模块, **不修改、不覆盖** SW-015 R1 / SW-014 R3 任何文件).
2. 追加 SW-006 专属检查 (在已批准检查之上):
   - sw006_frozen_design_binding: design_ref 必须指向 D-009 冻结的 spec 原字节
     (sha256 643e77b1...) 且 D-009 决策文件在库内.
   - sw006_approval_chain_exact: registry SW-012=accepted + latest_handoff/review
     与 design_ref 一致 + review.verdict=approved + reviewed_commit==handoff head.
   - sw006_exact_canvas_1080x1920: 每层 **解码尺寸** 必须精确 1080x1920.
   - sw006_no_legacy_forest_canvas: 显式拒绝 768x1376 森林历史例外.
   - sw006_source_resolution_recorded: 记录调用来源分辨率/调用参数, 且不允许
     "放大旧图冒称原生" (来源分辨率任一边 < 1080/1920 即拒).
   - sw006_api_budget_within_limit: 本轮尝试数与任务级 8 次上限一致, 且与持久账本
     互相吻合; 跨 revision 累计不重置.
   - sw006_ledger_state_consistent: 账本/state 不回退、不丢记录.
   - sw006_sample_mode_forbidden: 样本/fixture 模式不得进入生产调用.
3. authorize_generation(): 调用封装 —— 先落持久账本 (reserve), 再返回调用许可;
   超限/不一致一律拒绝.
4. self_test(): 真实断言 (非"只打印结果"的 harness), 失败返回非零退出码.

已知边界:
- SW-012 spec 原始字节里 layer id_status 仍是 "proposed"; D-009 已冻结该批字节.
  因此本入口按 allow_proposed=True 走 **实际批准链**, 不使用 --strict-design
  (旧 --strict-design 会误拒这条实际已批准的链, 不比实际批准链更权威).
- 本模块只做"准入门禁 + 记账", 不替代 Antigravity 独立验收, 不声明 accepted.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.dont_write_bytecode = True

# --- 路径 ---

SCRIPT_DIR = Path(__file__).resolve().parent
# scripts/ -> r2/ -> SW-006/ -> candidates/ -> rainforest/ -> assets/ -> design/ -> repo root
# parents[0]=r2 [1]=SW-006 [2]=candidates [3]=rainforest [4]=assets [5]=design [6]=repo root
REPO_ROOT = SCRIPT_DIR.parents[6]

SW015_DIR = REPO_ROOT / "design" / "assets" / "rainforest" / "preflight" / "SW-015" / "r1" / "scripts"
SW014_R3_DIR = REPO_ROOT / "design" / "assets" / "rainforest" / "preflight" / "SW-014" / "r3" / "scripts"

#: D-009 冻结的 SW-012 设计规格 SHA256 (原字节, 不得改动)
FROZEN_SPEC_SHA256 = "643e77b1ba7574c9b013dce485fde2797816096181feda91c2fa7920d042c320"
FROZEN_SPEC_FILE = "design/05-visual-design/SW-012/r1/design-spec.json"
FROZEN_DESIGN_TASK = "SW-012"
D009_DECISION_FILE = "docs/collaboration/decisions/D-009-freeze-rainforest-design-spec.md"

#: 雨林冻结画布 (精确, 不接受森林历史 768x1376 例外)
RAINFOREST_CANVAS = (1080, 1920)
LEGACY_FOREST_CANVAS = (768, 1376)

#: SW-006 任务级总尝试上限 (跨所有 revision)
SW006_ATTEMPTS_LIMIT = 8
#: 项目级历史基线 (SW-002 R1 的 14 次)
PROJECT_LIFETIME_BASELINE = 14

#: 账本路径 (任务级, 跨 revision)
LEDGER_PATH = REPO_ROOT / "design" / "assets" / "rainforest" / "candidates" / "SW-006" / "api_ledger.json"
STATE_PATH = REPO_ROOT / "docs" / "collaboration" / "state" / "minimax.json"

SIZE_RE = re.compile(r"^(\d+)x(\d+)$")


class GuardError(Exception):
    """生产保护拒绝放行."""


# --- 复用已批准工具 (只读加载, 不修改) ---

def _load_module(path: Path, name: str):
    if not path.is_file():
        raise GuardError(f"已批准工具缺失: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_TOOLING: Optional[Dict[str, Any]] = None


def load_tooling() -> Dict[str, Any]:
    """加载 (并缓存) 已批准的 SW-015 R1 / SW-014 R3 工具.

    SW-015 preflight 内部 `from spec_reader import ...`, 需要其 scripts 目录在 sys.path.
    """
    global _TOOLING
    if _TOOLING is not None:
        return _TOOLING
    sw015_scripts = str(SW015_DIR)
    if sw015_scripts not in sys.path:
        sys.path.insert(0, sw015_scripts)
    sw15_pre = _load_module(SW015_DIR / "preflight.py", "sw015_r1_preflight")
    sw15_dry = _load_module(SW015_DIR / "dry_run.py", "sw015_r1_dry_run")
    r3_pre = _load_module(SW014_R3_DIR / "preflight.py", "sw014_r3_preflight")
    _TOOLING = {
        "sw15_preflight": sw15_pre,
        "sw15_dry_run": sw15_dry,
        "r3_preflight": r3_pre,
        "sw015_dir": SW015_DIR,
        "sw014_r3_dir": SW014_R3_DIR,
    }
    return _TOOLING


# --- 工具函数 ---

def file_sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def report(ok: bool, name: str, detail: str = "") -> Dict[str, Any]:
    return {"ok": ok, "name": name, "detail": detail}


def _parse_size(text: Any) -> Optional[Tuple[int, int]]:
    if not isinstance(text, str):
        return None
    m = SIZE_RE.match(text.strip().lower())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def load_ledger(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path) if path else LEDGER_PATH
    if not p.is_file():
        return {"schema_version": 1, "task_id": "SW-006", "sw006_attempts_limit": SW006_ATTEMPTS_LIMIT,
                "project_lifetime_baseline": PROJECT_LIFETIME_BASELINE, "entries": []}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise GuardError(f"账本结构非法: {p}")
    return data


def ledger_used(data: Dict[str, Any]) -> int:
    return len(data.get("entries", []))


def read_state(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path) if path else STATE_PATH
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


# --- 主门禁 ---

def guard(
    manifest_path: Path,
    *,
    root: Optional[Path] = None,
    fixture_mode: bool = False,
    allow_proposed: bool = True,
    ledger_path: Optional[Path] = None,
    state_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """对候选 manifest 执行完整生产门禁. 返回 {status, summary, checks}."""
    tooling = load_tooling()
    sw15_pre = tooling["sw15_preflight"]
    r3_pre = tooling["r3_preflight"]

    manifest_path = Path(manifest_path)
    if not manifest_path.is_file():
        return {"status": "failed", "manifest": str(manifest_path),
                "summary": {"total": 0, "passed": 0, "failed": 1},
                "checks": [report(False, "manifest_exists", f"manifest 不存在: {manifest_path}")]}

    # 1) 先跑已批准入口 (SW-015 R1 preflight = R3 严格入口 + spec 强校验)
    approved = sw15_pre.preflight(manifest_path, fixture_mode=fixture_mode, allow_proposed=allow_proposed)
    checks: List[Dict[str, Any]] = [dict(c) for c in approved.get("checks", [])]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        checks.append(report(False, "sw006_manifest_json", f"manifest 非 JSON: {e}"))
        manifest = {}

    # 2) SW-006 专属: 冻结设计字节绑定
    design_ref = manifest.get("design_ref") or {}
    if not isinstance(design_ref, dict):
        design_ref = {}
    spec_file = design_ref.get("spec_file", "")
    spec_sha = design_ref.get("spec_sha256", "")

    if design_ref.get("task_id") != FROZEN_DESIGN_TASK:
        checks.append(report(False, "sw006_frozen_design_task",
                             f"design_ref.task_id={design_ref.get('task_id')!r} != {FROZEN_DESIGN_TASK}"))
    else:
        checks.append(report(True, "sw006_frozen_design_task", FROZEN_DESIGN_TASK))

    if spec_file != FROZEN_SPEC_FILE:
        checks.append(report(False, "sw006_frozen_spec_file",
                             f"design_ref.spec_file={spec_file!r} != {FROZEN_SPEC_FILE}"))
    else:
        checks.append(report(True, "sw006_frozen_spec_file", FROZEN_SPEC_FILE))

    if spec_sha != FROZEN_SPEC_SHA256:
        checks.append(report(False, "sw006_frozen_spec_sha",
                             f"design_ref.spec_sha256={str(spec_sha)[:16]} != D-009 冻结 {FROZEN_SPEC_SHA256[:16]}"))
    else:
        checks.append(report(True, "sw006_frozen_spec_sha", FROZEN_SPEC_SHA256[:16]))

    repo = Path(root) if root else REPO_ROOT
    spec_abs = repo / FROZEN_SPEC_FILE
    if spec_abs.is_file():
        actual = file_sha256(spec_abs)
        if actual != FROZEN_SPEC_SHA256:
            checks.append(report(False, "sw006_frozen_spec_bytes_on_disk",
                                 f"库内 {FROZEN_SPEC_FILE} 实际 sha256={actual[:16]} != 冻结 {FROZEN_SPEC_SHA256[:16]}"))
        else:
            checks.append(report(True, "sw006_frozen_spec_bytes_on_disk", f"{actual[:16]} (原字节未改)"))
    else:
        checks.append(report(False, "sw006_frozen_spec_bytes_on_disk", f"库内缺 {FROZEN_SPEC_FILE}"))

    d009 = repo / D009_DECISION_FILE
    if d009.is_file() and FROZEN_SPEC_SHA256 in d009.read_text(encoding="utf-8"):
        checks.append(report(True, "sw006_d009_decision", "D-009 决策在库且含同一冻结哈希"))
    else:
        checks.append(report(False, "sw006_d009_decision", f"D-009 决策缺失或未含冻结哈希: {D009_DECISION_FILE}"))

    # 3) SW-006 专属: 精确批准链
    try:
        registry = json.loads((repo / "docs" / "collaboration" / "registry.json").read_text(encoding="utf-8"))
    except Exception as e:
        registry = {}
        checks.append(report(False, "sw006_registry_load", f"registry 读取失败: {e}"))
    task_entry = next((t for t in registry.get("tasks", []) if t.get("id") == FROZEN_DESIGN_TASK), None)
    if not task_entry:
        checks.append(report(False, "sw006_registry_task", f"registry 无 {FROZEN_DESIGN_TASK}"))
    else:
        if task_entry.get("status") == "accepted":
            checks.append(report(True, "sw006_registry_status", "SW-012 accepted"))
        else:
            checks.append(report(False, "sw006_registry_status",
                                 f"SW-012 status={task_entry.get('status')!r} != accepted"))
        if task_entry.get("latest_handoff") == design_ref.get("handoff"):
            checks.append(report(True, "sw006_registry_latest_handoff", str(design_ref.get("handoff"))))
        else:
            checks.append(report(False, "sw006_registry_latest_handoff",
                                 f"registry={task_entry.get('latest_handoff')!r} != design_ref={design_ref.get('handoff')!r}"))
        review_rel = task_entry.get("latest_review")
        if not review_rel:
            checks.append(report(False, "sw006_registry_latest_review", "registry.latest_review=null"))
        else:
            review_abs = repo / review_rel
            if not review_abs.is_file():
                checks.append(report(False, "sw006_registry_latest_review", f"review 不存在: {review_rel}"))
            else:
                rv = json.loads(review_abs.read_text(encoding="utf-8"))
                if rv.get("verdict") == "approved":
                    checks.append(report(True, "sw006_registry_review_verdict", "approved"))
                else:
                    checks.append(report(False, "sw006_registry_review_verdict",
                                         f"verdict={rv.get('verdict')!r} != approved"))
                handoff_abs = repo / str(design_ref.get("handoff", ""))
                if handoff_abs.is_file():
                    hd = json.loads(handoff_abs.read_text(encoding="utf-8"))
                    if rv.get("reviewed_commit") == hd.get("head_commit"):
                        checks.append(report(True, "sw006_approval_head_match", str(hd.get("head_commit"))[:12]))
                    else:
                        checks.append(report(False, "sw006_approval_head_match",
                                             f"review.reviewed_commit={str(rv.get('reviewed_commit'))[:12]} != handoff head={str(hd.get('head_commit'))[:12]}"))

    # 4) SW-006 专属: 层集合 + 精确画布 + 来源分辨率
    layers = manifest.get("layers", [])
    if not isinstance(layers, list) or not layers:
        checks.append(report(False, "sw006_layers_present", "layers 为空或非数组"))
        layers = []
    else:
        checks.append(report(True, "sw006_layers_present", f"{len(layers)} 层"))

    for layer in layers:
        if not isinstance(layer, dict):
            continue
        lid = layer.get("layer_id", "?")

        # 精确画布: 解码尺寸 == manifest 声明 == 1080x1920
        rel_file = layer.get("file", "")
        file_abs = (repo / rel_file) if isinstance(rel_file, str) else None
        decoded = None
        if file_abs is not None and file_abs.is_file():
            try:
                from PIL import Image
                with Image.open(file_abs) as im:
                    im.load()
                    decoded = (im.size[0], im.size[1])
            except Exception as e:
                checks.append(report(False, f"sw006_{lid}_decode", f"解码失败: {e}"))
        if decoded is None:
            checks.append(report(False, f"sw006_{lid}_decoded_size", f"无法解码 {rel_file!r}"))
        else:
            if decoded == LEGACY_FOREST_CANVAS:
                checks.append(report(False, f"sw006_{lid}_no_legacy_forest_canvas",
                                     f"{decoded[0]}x{decoded[1]} 是森林历史尺寸, 雨林禁止沿用"))
            elif decoded != RAINFOREST_CANVAS:
                checks.append(report(False, f"sw006_{lid}_exact_canvas",
                                     f"解码 {decoded[0]}x{decoded[1]} != 冻结画布 1080x1920"))
            else:
                checks.append(report(True, f"sw006_{lid}_exact_canvas", f"解码 {decoded[0]}x{decoded[1]}"))
            mw, mh = layer.get("width"), layer.get("height")
            if (mw, mh) != decoded:
                checks.append(report(False, f"sw006_{lid}_manifest_size",
                                     f"manifest {mw}x{mh} != 解码 {decoded[0]}x{decoded[1]}"))
            else:
                checks.append(report(True, f"sw006_{lid}_manifest_size", f"{mw}x{mh}"))

        # 来源分辨率 + 调用参数 (不许放大旧图冒称原生)
        src = _parse_size(layer.get("source_resolution"))
        if src is None:
            checks.append(report(False, f"sw006_{lid}_source_resolution",
                                 f"source_resolution 缺失或非 WxH: {layer.get('source_resolution')!r}"))
        else:
            sw, sh = src
            if sw < RAINFOREST_CANVAS[0] or sh < RAINFOREST_CANVAS[1]:
                checks.append(report(False, f"sw006_{lid}_no_upscale_claim",
                                     f"来源分辨率 {sw}x{sh} 小于 1080x1920, 属放大旧图冒称原生"))
            else:
                checks.append(report(True, f"sw006_{lid}_source_resolution", f"{sw}x{sh} >= 1080x1920"))

        call = layer.get("call")
        if not isinstance(call, dict) or not call.get("prompt_ref") or not call.get("service"):
            checks.append(report(False, f"sw006_{lid}_call_params",
                                 "缺 call.service / call.prompt_ref (调用参数与提示词来源必须可追溯)"))
        else:
            checks.append(report(True, f"sw006_{lid}_call_params",
                                 f"{call.get('service')} / {call.get('prompt_ref')}"))

        if not layer.get("process"):
            checks.append(report(False, f"sw006_{lid}_process_recorded", "process 未记录 (处理链必须可追溯)"))
        else:
            checks.append(report(True, f"sw006_{lid}_process_recorded", str(layer.get("process"))[:60]))

    # 5) SW-006 专属: 预算与账本一致性
    this_rev = manifest.get("api_attempts_this_revision")
    declared_total = manifest.get("api_attempts_total")
    if not isinstance(this_rev, int) or isinstance(this_rev, bool) or this_rev < 0:
        checks.append(report(False, "sw006_api_this_revision", f"api_attempts_this_revision 缺失/非非负整数: {this_rev!r}"))
    else:
        checks.append(report(True, "sw006_api_this_revision", str(this_rev)))
    if not isinstance(declared_total, int) or isinstance(declared_total, bool) or declared_total < 0:
        checks.append(report(False, "sw006_api_total", f"api_attempts_total 缺失/非非负整数: {declared_total!r}"))
    else:
        checks.append(report(True, "sw006_api_total", str(declared_total)))

    ledger = load_ledger(ledger_path)
    used = ledger_used(ledger)
    if isinstance(this_rev, int) and not isinstance(this_rev, bool):
        if this_rev > SW006_ATTEMPTS_LIMIT:
            checks.append(report(False, "sw006_api_budget_within_limit",
                                 f"api_attempts_this_revision={this_rev} > 任务级上限 {SW006_ATTEMPTS_LIMIT}"))
        else:
            checks.append(report(True, "sw006_api_budget_within_limit", f"{this_rev}/{SW006_ATTEMPTS_LIMIT}"))
    if isinstance(declared_total, int) and not isinstance(declared_total, bool):
        expected_min = PROJECT_LIFETIME_BASELINE + used
        if declared_total < expected_min:
            checks.append(report(False, "sw006_api_total_not_reset",
                                 f"api_attempts_total={declared_total} < 基线{PROJECT_LIFETIME_BASELINE}+账本{used} (不得重置)"))
        else:
            checks.append(report(True, "sw006_api_total_not_reset", f"{declared_total} >= {expected_min}"))

    state = read_state(state_path)
    st_sw006 = state.get("sw006_attempts")
    st_total = state.get("cumulative_attempts")
    if isinstance(st_sw006, int) and not isinstance(st_sw006, bool) and st_sw006 > used:
        checks.append(report(False, "sw006_ledger_state_consistent",
                             f"state.sw006_attempts={st_sw006} > 账本 {used} (账本丢记录)"))
    else:
        checks.append(report(True, "sw006_ledger_state_consistent",
                             f"state={st_sw006} / ledger={used}"))
    if isinstance(st_total, int) and not isinstance(st_total, bool) and st_total < PROJECT_LIFETIME_BASELINE:
        checks.append(report(False, "sw006_state_not_regressed",
                             f"state.cumulative_attempts={st_total} < 基线 {PROJECT_LIFETIME_BASELINE}"))
    else:
        checks.append(report(True, "sw006_state_not_regressed", f"state.cumulative_attempts={st_total}"))

    # 6) SW-006 专属: 样本模式隔离
    if fixture_mode:
        checks.append(report(False, "sw006_sample_mode_forbidden",
                             "fixture/sample 模式只能用于自检, 不得进入生产调用"))
    else:
        for key in ("_fixture_mode", "_expected_registry_status"):
            if key in manifest or key in (manifest.get("design_ref") or {}):
                checks.append(report(False, "sw006_sample_mode_forbidden",
                                     f"生产 manifest 含样本字段 {key}"))
                break
        else:
            checks.append(report(True, "sw006_sample_mode_forbidden", "生产入口无样本字段"))

    total = len(checks)
    passed = sum(1 for c in checks if c.get("ok"))
    failed = total - passed
    return {
        "status": "ok" if failed == 0 else "failed",
        "manifest": str(manifest_path),
        "fixture_mode": fixture_mode,
        "summary": {"total": total, "passed": passed, "failed": failed},
        "checks": checks,
    }


# --- 调用封装 (先落账本, 再放行) ---

def authorize_generation(
    layer_id: str,
    *,
    revision: str,
    prompt_ref: str,
    source_resolution: str,
    service: str,
    call_params: Dict[str, Any],
    ledger_path: Optional[Path] = None,
    state_path: Optional[Path] = None,
    sample_mode: bool = False,
) -> Dict[str, Any]:
    """付费调用前的放行闸门. 返回许可记录; 拒绝则抛 GuardError.

    顺序: 检查样本模式 -> 检查跨 revision 预算/账本一致性 -> **落盘 reserve** -> 返回许可.
    reserve 先于真实请求, 因此失败/超时/重试同样占额度.
    """
    if sample_mode:
        raise GuardError("样本模式禁止进入生产调用")

    ledger = load_ledger(ledger_path)
    used = ledger_used(ledger)
    if used >= SW006_ATTEMPTS_LIMIT:
        raise GuardError(f"下一次调用超限: 已用 {used}/{SW006_ATTEMPTS_LIMIT} 次 SW-006 尝试")

    state = read_state(state_path)
    st_sw006 = state.get("sw006_attempts")
    if isinstance(st_sw006, int) and not isinstance(st_sw006, bool) and st_sw006 > used:
        raise GuardError(f"state.sw006_attempts={st_sw006} > 账本 {used}, 账本丢记录, 拒绝调用")
    st_total = state.get("cumulative_attempts")
    if isinstance(st_total, int) and not isinstance(st_total, bool) and st_total < PROJECT_LIFETIME_BASELINE:
        raise GuardError(f"state.cumulative_attempts={st_total} < 基线 {PROJECT_LIFETIME_BASELINE}, 拒绝调用")

    import api_ledger  # 同目录模块

    entry = api_ledger.reserve(
        layer_id,
        revision,
        prompt_ref=prompt_ref,
        source_resolution=source_resolution,
        request_meta={"service": service, "call_params": call_params},
        path=ledger_path,
        state_path=state_path,
    )
    return {
        "authorized": True,
        "seq": entry["seq"],
        "sw006_attempts_used_after_reserve": SW006_ATTEMPTS_LIMIT - used - 1,
        "project_lifetime_attempts_after": PROJECT_LIFETIME_BASELINE + used + 1,
        "entry": entry,
    }


def settle_generation(seq: int, outcome: str, *, note: Optional[str] = None,
                      ledger_path: Optional[Path] = None) -> Dict[str, Any]:
    """把 reserve 的条目结算为 success/failed/timeout."""
    import api_ledger
    return api_ledger.settle(seq, outcome, note=note, path=ledger_path)


# --- 自检 (真实断言 + 非零退出码) ---

def _make_png(path: Path, size: Tuple[int, int]) -> None:
    """造一张带真半透明渐变的 RGBA 图 (让 R3 半透明像素检查有真实通过条件)."""
    import numpy as np
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w]
    # 径向软斑: 中心不透明, 边缘完全透明, 中间为半透明 -> alpha<127 像素占比 > 0.1%
    r = np.sqrt(((xx - w * 0.5) / (w * 0.55)) ** 2 + ((yy - h * 0.45) / (h * 0.5)) ** 2)
    alpha = np.clip(255.0 * (1.0 - r), 0.0, 255.0).astype(np.uint8)
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[..., 0] = 30
    rgb[..., 1] = 60
    rgb[..., 2] = 50
    arr = np.dstack([rgb, alpha])
    Image.fromarray(arr).save(path)


def _write_manifest(path: Path, manifest: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_case(tmp: Path, name: str, *, canvas: Tuple[int, int] = RAINFOREST_CANVAS,
                this_rev: int = 0, total: int = PROJECT_LIFETIME_BASELINE,
                layers: Optional[List[str]] = None,
                design_ref_override: Optional[Dict[str, Any]] = None,
                extra_manifest: Optional[Dict[str, Any]] = None) -> Tuple[Path, Path]:
    """在 tmp repo 里造一个候选目录 + manifest.

    布局与真实候选一致 (manifest 与 checks 同级):
      <tmp>/design/assets/rainforest/candidates/SW-006/r2test_<name>/
          manifest.json
          checks/{black,white,magenta}/rainforest_<lid>.jpg
          checks/alpha_mask/rainforest_<lid>.png
          png/rainforest_<lid>.png
          webp/rainforest_<lid>.webp

    检查图放在 manifest 同级目录下, 因为已批准的 R3 preflight 按
    `checks/<bg>/rainforest_<lid>.<ext>` 相对 manifest 目录查找;
    manifest 里声明的 checks 仍是 repo 根相对路径 (collaboration.py 要求).
    """
    from PIL import Image

    cand_rel = f"design/assets/rainforest/candidates/SW-006/r2test_{name}"
    cand = tmp / cand_rel
    (cand / "png").mkdir(parents=True, exist_ok=True)
    (cand / "webp").mkdir(parents=True, exist_ok=True)
    for bg in ("black", "white", "magenta"):
        (cand / "checks" / bg).mkdir(parents=True, exist_ok=True)
    (cand / "checks" / "alpha_mask").mkdir(parents=True, exist_ok=True)

    layer_ids = layers if layers is not None else ["mist", "trunks_canopy", "vines_light", "distant_glow", "glade"]
    layer_entries = []
    for lid in layer_ids:
        png_rel = f"{cand_rel}/png/rainforest_{lid}.png"
        webp_rel = f"{cand_rel}/webp/rainforest_{lid}.webp"
        png_abs = tmp / png_rel
        webp_abs = tmp / webp_rel
        _make_png(png_abs, canvas)
        with Image.open(png_abs) as im:
            im.save(webp_abs, "WEBP", quality=80)
        for bg, ext in (("black", "jpg"), ("white", "jpg"), ("magenta", "jpg")):
            p = cand / "checks" / bg / f"rainforest_{lid}.{ext}"
            bg_rgb = {"black": (0, 0, 0), "white": (255, 255, 255), "magenta": (255, 0, 255)}[bg]
            Image.new("RGB", canvas, bg_rgb).save(p)
        p = cand / "checks" / "alpha_mask" / f"rainforest_{lid}.png"
        with Image.open(png_abs) as im:
            im.getchannel("A").save(p)

        layer_entries.append({
            "layer_id": lid,
            "file": webp_rel,
            "png_file": png_rel,
            "width": canvas[0],
            "height": canvas[1],
            "bytes": webp_abs.stat().st_size,
            "sha256": file_sha256(webp_abs),
            "alpha_channel": True,
            "render_role": "overlay" if lid in ("mist", "distant_glow", "glade") else "parallax",
            "tileable": False,
            "origin": "test fixture (非生产素材)",
            "process": "fixture",
            "source_resolution": f"{canvas[0]}x{canvas[1]}",
            "call": {"service": "test", "prompt_ref": "test", "attempt_seq": 0},
            "checks": [
                f"{cand_rel}/checks/alpha_mask/rainforest_{lid}.png",
                f"{cand_rel}/checks/black/rainforest_{lid}.jpg",
                f"{cand_rel}/checks/white/rainforest_{lid}.jpg",
                f"{cand_rel}/checks/magenta/rainforest_{lid}.jpg",
            ],
        })

    design_ref = {
        "task_id": FROZEN_DESIGN_TASK,
        "handoff": "docs/collaboration/handoffs/trae-design/H-SW-012-R1.json",
        "spec_file": FROZEN_SPEC_FILE,
        "spec_sha256": FROZEN_SPEC_SHA256,
    }
    if design_ref_override:
        design_ref.update(design_ref_override)

    manifest = {
        "schema_version": 1,
        "task_id": "SW-006",
        "revision": 2,
        "scene_id": "rainforest",
        "producer": "minimax",
        "api_attempts_this_revision": this_rev,
        "api_attempts_total": total,
        "cost": "unknown",
        "design_ref": design_ref,
        "layers": layer_entries,
    }
    if extra_manifest:
        manifest.update(extra_manifest)

    mpath = cand / "manifest.json"
    _write_manifest(mpath, manifest)
    return mpath, tmp


def _prepare_tmp_repo(root: Path, tmp: Path) -> Path:
    """把真实 registry/state/spec/handoff/review 拷进 tmp, 作为隔离的 repo 根."""
    repo = tmp / "repo"
    (repo / "docs" / "collaboration" / "state").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "collaboration" / "handoffs" / "trae-design").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "collaboration" / "reviews").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "collaboration" / "decisions").mkdir(parents=True, exist_ok=True)
    (repo / "design" / "05-visual-design" / "SW-012" / "r1").mkdir(parents=True, exist_ok=True)

    import shutil
    shutil.copy(root / "docs/collaboration/registry.json", repo / "docs/collaboration/registry.json")
    # state 用 **合成基线** 而不是真实 state: 自检要能从 "已用 0 次" 的起点复现
    # 8 次放行 / 第 9 次拒绝等预算行为, 与真实仓库当前已用次数无关.
    (repo / "docs/collaboration/state/minimax.json").write_text(json.dumps({
        "schema_version": 1,
        "agent": "minimax",
        "cumulative_attempts": PROJECT_LIFETIME_BASELINE,
        "sw006_attempts": 0,
        "sw006_attempts_limit": SW006_ATTEMPTS_LIMIT,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy(root / "docs/collaboration/handoffs/trae-design/H-SW-012-R1.json",
                repo / "docs/collaboration/handoffs/trae-design/H-SW-012-R1.json")
    shutil.copy(root / "docs/collaboration/reviews/R-SW-012-R1.json",
                repo / "docs/collaboration/reviews/R-SW-012-R1.json")
    shutil.copy(root / D009_DECISION_FILE, repo / D009_DECISION_FILE)
    shutil.copy(root / FROZEN_SPEC_FILE, repo / FROZEN_SPEC_FILE)
    return repo


def _patch_root(repo: Path) -> None:
    """把已批准工具的 ROOT 指向隔离 tmp repo (只在本进程内, 不改源文件)."""
    tooling = load_tooling()
    sw15_pre = tooling["sw15_preflight"]
    r3_pre = tooling["r3_preflight"]
    sw15_pre._r3.ROOT = repo
    sw15_pre.ROOT = repo
    r3_pre.ROOT = repo
    # 注意: SW-015 preflight 内部自己 import 了一份 R3 模块实例 (sw15_pre._r3),
    # 与本模块直接加载的 r3_pre **不是同一个对象**, 两者都要重定向 state 路径,
    # 否则 R3 的累计账本校验会读到真实仓库 state 而与隔离 tmp repo 不一致.
    for mod in (sw15_pre._r3, r3_pre):
        mod.ROOT = repo
        mod.MINIMAX_STATE_PATH = repo / "docs" / "collaboration" / "state" / "minimax.json"

    def _lr():
        return json.loads((repo / "docs" / "collaboration" / "registry.json").read_text(encoding="utf-8"))
    sw15_pre._r3.load_registry = _lr
    r3_pre.load_registry = _lr


def self_test(root: Optional[Path] = None) -> Dict[str, Any]:
    """真实断言自检. 返回 {passed, failed, results}. 任何断言失败 => failed>0."""
    import shutil
    import tempfile

    root = Path(root) if root else REPO_ROOT
    tooling = load_tooling()
    sw15_pre = tooling["sw15_preflight"]

    results: List[Dict[str, Any]] = []
    tmp = Path(tempfile.mkdtemp(prefix="sw006-r2-guard-"))
    original_root = sw15_pre._r3.ROOT
    original_state = tooling["r3_preflight"].MINIMAX_STATE_PATH
    try:
        repo = _prepare_tmp_repo(root, tmp)
        _patch_root(repo)

        def add(name: str, expect: str, detail: str, extra: Optional[Dict[str, Any]] = None) -> None:
            rec = {"name": name, "expect": expect, "detail": detail}
            if extra:
                rec.update(extra)
            results.append(rec)

        # --- 正例: 真实批准链 + 正确原字节 + 精确画布 ---
        mpath, _ = _build_case(repo, "positive")
        res = guard(mpath, root=repo, ledger_path=repo / "design/assets/rainforest/candidates/SW-006/api_ledger.json",
                    state_path=repo / "docs/collaboration/state/minimax.json")
        add("positive_real_approved_chain", "ok",
            f"真实 SW-012 批准链 + 1080x1920 原字节应通过 (got {res['status']}, {res['summary']['passed']}/{res['summary']['total']})",
            {"got": res["status"], "summary": res["summary"],
             "failed_checks": [c["name"] for c in res["checks"] if not c.get("ok")]})

        # --- 回归 (旧预检误放行, 新入口必须失败) ---
        # (a) 真实批准链 + 768x1376 森林历史尺寸
        mpath, _ = _build_case(repo, "legacy_768", canvas=LEGACY_FOREST_CANVAS)
        old = sw15_pre.preflight(mpath, fixture_mode=False, allow_proposed=True)
        res = guard(mpath, root=repo, ledger_path=repo / "design/assets/rainforest/candidates/SW-006/api_ledger.json",
                    state_path=repo / "docs/collaboration/state/minimax.json")
        add("regression_768_legacy_canvas", "failed",
            f"768x1376 必须失败 (old_preflight={old['status']}, new_guard={res['status']})",
            {"old_preflight_status": old["status"], "new_guard_status": res["status"],
             "failed_checks": [c["name"] for c in res["checks"] if not c.get("ok")]})

        # (b) this_revision=9 / total=23 超任务级上限
        mpath, _ = _build_case(repo, "over_budget", this_rev=9, total=23)
        old = sw15_pre.preflight(mpath, fixture_mode=False, allow_proposed=True)
        res = guard(mpath, root=repo, ledger_path=repo / "design/assets/rainforest/candidates/SW-006/api_ledger.json",
                    state_path=repo / "docs/collaboration/state/minimax.json")
        add("regression_api_over_task_limit", "failed",
            f"this_revision=9/total=23 必须失败 (old_preflight={old['status']}, new_guard={res['status']})",
            {"old_preflight_status": old["status"], "new_guard_status": res["status"],
             "failed_checks": [c["name"] for c in res["checks"] if not c.get("ok")]})

        # --- 错 SHA ---
        mpath, _ = _build_case(repo, "wrong_sha", design_ref_override={"spec_sha256": "0" * 64})
        res = guard(mpath, root=repo, ledger_path=repo / "design/assets/rainforest/candidates/SW-006/api_ledger.json",
                    state_path=repo / "docs/collaboration/state/minimax.json")
        add("reject_wrong_spec_sha", "failed",
            f"错 spec SHA 必须失败 (got {res['status']})", {"new_guard_status": res["status"]})

        # --- 未批准链: registry 里 SW-012 非 accepted ---
        reg_path = repo / "docs/collaboration/registry.json"
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        for t in reg["tasks"]:
            if t["id"] == "SW-012":
                t["status"] = "handoff_ready"
        reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
        mpath, _ = _build_case(repo, "not_approved")
        res = guard(mpath, root=repo, ledger_path=repo / "design/assets/rainforest/candidates/SW-006/api_ledger.json",
                    state_path=repo / "docs/collaboration/state/minimax.json")
        add("reject_unapproved_chain", "failed",
            f"SW-012 未 accepted 必须失败 (got {res['status']})", {"new_guard_status": res["status"]})
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        for t in reg["tasks"]:
            if t["id"] == "SW-012":
                t["status"] = "accepted"
        reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")

        # --- 空层 ---
        mpath, _ = _build_case(repo, "empty_layers", layers=[])
        res = guard(mpath, root=repo, ledger_path=repo / "design/assets/rainforest/candidates/SW-006/api_ledger.json",
                    state_path=repo / "docs/collaboration/state/minimax.json")
        add("reject_empty_layers", "failed",
            f"空层必须失败 (got {res['status']})", {"new_guard_status": res["status"]})

        # --- 缺层 ---
        mpath, _ = _build_case(repo, "missing_layer", layers=["mist", "trunks_canopy", "vines_light"])
        res = guard(mpath, root=repo, ledger_path=repo / "design/assets/rainforest/candidates/SW-006/api_ledger.json",
                    state_path=repo / "docs/collaboration/state/minimax.json")
        add("reject_missing_layers", "failed",
            f"缺层必须失败 (got {res['status']})", {"new_guard_status": res["status"]})

        # --- 缺/非整数计数 ---
        mpath, _ = _build_case(repo, "bad_count", extra_manifest={"api_attempts_this_revision": "9"})
        res = guard(mpath, root=repo, ledger_path=repo / "design/assets/rainforest/candidates/SW-006/api_ledger.json",
                    state_path=repo / "docs/collaboration/state/minimax.json")
        add("reject_non_integer_count", "failed",
            f"非整数尝试计数必须失败 (got {res['status']})", {"new_guard_status": res["status"]})

        mpath, _ = _build_case(repo, "missing_count", extra_manifest={"api_attempts_total": None})
        res = guard(mpath, root=repo, ledger_path=repo / "design/assets/rainforest/candidates/SW-006/api_ledger.json",
                    state_path=repo / "docs/collaboration/state/minimax.json")
        add("reject_missing_count", "failed",
            f"缺尝试计数必须失败 (got {res['status']})", {"new_guard_status": res["status"]})

        # --- 样本模式不得进入生产调用 ---
        sample_rejected = False
        try:
            authorize_generation("mist", revision="r2", prompt_ref="p", source_resolution="1080x1920",
                                 service="test", call_params={}, sample_mode=True,
                                 ledger_path=repo / "design/assets/rainforest/candidates/SW-006/api_ledger.json",
                                 state_path=repo / "docs/collaboration/state/minimax.json")
        except GuardError:
            sample_rejected = True
        add("reject_sample_mode_call", "rejected",
            f"样本模式必须拒绝生产调用 (rejected={sample_rejected})", {"rejected": sample_rejected})

        # --- 预算: 8 次成功, 第 9 次拒绝 ---
        led = repo / "design/assets/rainforest/candidates/SW-006/api_ledger.json"
        st = repo / "docs/collaboration/state/minimax.json"
        if led.exists():
            led.unlink()
        auth_results = []
        for i in range(9):
            try:
                auth = authorize_generation("mist", revision="r2", prompt_ref=f"p{i}", source_resolution="1080x1920",
                                           service="test", call_params={"i": i}, ledger_path=led, state_path=st)
                settle_generation(auth["seq"], "success", note="selftest", ledger_path=led)
                auth_results.append("authorized")
            except GuardError:
                auth_results.append("rejected")
        add("budget_8_ok_9th_rejected", "8 authorized / 9th rejected",
            f"实际: {auth_results.count('authorized')} 次放行, 第 9 次 {'被拒' if auth_results[-1]=='rejected' else '未拒'}",
            {"sequence": auth_results})

        # --- 跨 revision 累计 8/9 (r1 用掉 5, r2 只能再用 3) ---
        if led.exists():
            led.unlink()
        import api_ledger as al
        for i in range(5):
            al.reserve("mist", "r1", prompt_ref=f"r1p{i}", source_resolution="1080x1920", path=led, state_path=st)
        cross = []
        for i in range(4):
            try:
                auth = authorize_generation("mist", revision="r2", prompt_ref=f"r2p{i}", source_resolution="1080x1920",
                                           service="test", call_params={}, ledger_path=led, state_path=st)
                settle_generation(auth["seq"], "success", note="selftest-cross", ledger_path=led)
                cross.append("authorized")
            except GuardError:
                cross.append("rejected")
        add("budget_cross_revision_8_9", "3 authorized / 4th rejected",
            f"实际: r1 已用 5, r2 放行 {cross.count('authorized')} 次, 第 4 次 {'被拒' if cross[-1]=='rejected' else '未拒'}",
            {"sequence": cross})

        # --- 失败/超时同样计数 ---
        if led.exists():
            led.unlink()
        for i in range(2):
            al.reserve("mist", "r2", prompt_ref=f"f{i}", source_resolution="1080x1920", path=led, state_path=st)
        al.settle(1, "failed", note="selftest-failed", path=led)
        al.settle(2, "timeout", note="selftest-timeout", path=led)
        used_after = al.sw006_attempts(al.load_ledger(led))
        add("budget_counts_failures_and_timeouts", "used=2",
            f"failed+timeout 仍占额度, 实际 used={used_after}", {"used": used_after})

        # --- 账本/state 不得回退 ---
        state_data = json.loads(st.read_text(encoding="utf-8"))
        state_data["sw006_attempts"] = 99
        st.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8")
        mpath, _ = _build_case(repo, "state_regress")
        res = guard(mpath, root=repo, ledger_path=led, state_path=st)
        add("reject_state_ledger_regression", "failed",
            f"state 计数 > 账本 必须失败 (got {res['status']})", {"new_guard_status": res["status"]})
        state_data["sw006_attempts"] = 0
        st.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8")

    finally:
        sw15_pre._r3.ROOT = original_root
        tooling["r3_preflight"].MINIMAX_STATE_PATH = original_state
        shutil.rmtree(tmp, ignore_errors=True)

    passed = 0
    failed = 0
    for r in results:
        exp = r["expect"]
        got = r.get("new_guard_status") or r.get("got")
        if exp in ("ok", "failed"):
            ok = got == exp
        elif exp == "rejected":
            ok = bool(r.get("rejected"))
        elif exp == "8 authorized / 9th rejected":
            ok = r.get("sequence", []).count("authorized") == 8 and r.get("sequence", [])[-1] == "rejected"
        elif exp == "3 authorized / 4th rejected":
            ok = r.get("sequence", []).count("authorized") == 3 and r.get("sequence", [])[-1] == "rejected"
        elif exp == "used=2":
            ok = r.get("used") == 2
        else:
            ok = False
        r["result"] = "passed" if ok else "FAILED"
        if ok:
            passed += 1
        else:
            failed += 1

    return {
        "kind": "sw006-r2-production-guard-selftest",
        "passed": passed,
        "failed": failed,
        "total": len(results),
        "results": results,
    }


def render_summary(result: Dict[str, Any]) -> str:
    lines = [
        f"  status: {'ok' if result['summary']['failed'] == 0 else 'failed'}",
        f"  manifest: {result.get('manifest')}",
        f"  fixture_mode: {result.get('fixture_mode')}",
        f"  checks: {result['summary']['passed']}/{result['summary']['total']} passed ({result['summary']['failed']} failed)",
    ]
    failed = [c for c in result.get("checks", []) if not c.get("ok")]
    if failed:
        lines.append(f"  failed ({len(failed)}):")
        for c in failed[:60]:
            lines.append(f"    - {c['name']}: {c['detail'][:150]}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="SW-006 R2 生产保护 (零 API)")
    ap.add_argument("manifest", nargs="?", type=Path, help="候选 manifest.json 路径")
    ap.add_argument("--fixture-mode", action="store_true", help="样本模式 (仅自检, 不得用于生产调用)")
    ap.add_argument("--strict-design", action="store_true",
                    help="要求 spec id_status=approved (实际已批准链为 proposed 原字节, 不建议使用)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--selftest", action="store_true", help="运行真实断言自检")
    ap.add_argument("--root", type=Path, default=None)
    args = ap.parse_args()

    if args.selftest:
        result = self_test(args.root)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for r in result["results"]:
            print(f"  [{r['result']:6s}] {r['name']}: {r['detail']}")
        print(f"=== selftest: {result['passed']}/{result['total']} passed ({result['failed']} failed) ===")
        return 0 if result["failed"] == 0 else 1

    if not args.manifest:
        ap.error("需要 manifest 路径, 或使用 --selftest")

    result = guard(args.manifest, root=args.root, fixture_mode=args.fixture_mode,
                   allow_proposed=not args.strict_design)
    if args.json or args.out:
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_summary(result))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
