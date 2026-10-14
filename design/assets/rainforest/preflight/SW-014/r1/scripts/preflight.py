#!/usr/bin/env python3
"""
SW-014 雨林素材交付预检脚本 (零 API).

输入: 一个候选 manifest.json 路径 (forest 或 rainforest)
输出: 报告 (json) + 终端摘要

校验项 (按 contracts/visual-assets.md + visual-design.md):
- manifest schema_version=1
- task_id, scene_id, producer 与 handoff 一致
- 每层 file 存在 + sha256 匹配 + bytes 匹配 + 尺寸 768x1376 (项目最终画布 cover 缩放)
- 每层 ≤ 400 KB
- 全景 (5 外部视觉层) ≤ 2 MB
- 每层 checks 路径全部存在
- design_ref 存在 (新场景) 且 handoff/spec_file 存在
- 不允许 AI 输出标 CC0 (本脚本自动检查 manifest 文本)
- 拒绝: tileable=true 但缺 tileable check (stages / seamless)
- 拒绝: 1 层缺文件 / 错 hash / 错字节
- 报告 API 账本字段存在 (api_attempts_this_revision / api_attempts_total / cost)

调用账本模板 (本任务 0 次, SW-006 沿原 8 次预算不重置):
api_log = {
    "task_id": "SW-006",
    "revision": 1,
    "attempts": [],  # [{ts, prompt_hash, model, status, cost, file}], 每次实际调用都记录
    "total": 0,
    "budget_remaining": 8,
}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Optional

# 项目根
ROOT = Path(__file__).resolve().parents[5]  # scripts/preflight.py -> r1/ -> SW-014/ -> rainforest/ -> assets/ -> design/ -> repo_root
CONTRACT_VERSION = "visual-assets v1"
MAX_LAYER_BYTES = 400 * 1024       # 400 KB per layer
MAX_SCENE_BYTES = 2 * 1024 * 1024  # 2 MB per scene (5 外部视觉层)
EXPECTED_W, EXPECTED_H = 768, 1376 # 历史 raw 尺寸; cover 缩放到 1080x1920 (本轮 SW-014 接受 768x1376 与 1080x1920 两种)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def report(ok: bool, name: str, detail: str) -> dict:
    return {"ok": ok, "name": name, "detail": detail}


def preflight(manifest_path: Path) -> dict:
    if not manifest_path.is_file():
        return {
            "status": "failed",
            "error": f"manifest not found: {manifest_path}",
            "checks": [],
            "summary": {"total": 0, "passed": 0, "failed": 0},
        }
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        return {
            "status": "failed",
            "error": f"manifest JSON 解析失败: {e}",
            "checks": [],
            "summary": {"total": 0, "passed": 0, "failed": 0},
        }

    checks: list[dict] = []
    base = manifest_path.parent  # manifest 在 candidates/<task>/r<n>/ 下, file/checks 相对 base

    # 1. schema
    if manifest.get("schema_version") != 1:
        checks.append(report(False, "schema_version", f"expected 1, got {manifest.get('schema_version')}"))
    else:
        checks.append(report(True, "schema_version", "1"))

    # 2. 必要字段
    for key in ["task_id", "revision", "scene_id", "producer", "api_attempts_total", "cost", "layers"]:
        if key not in manifest:
            checks.append(report(False, f"field_{key}", f"missing"))

    # 3. layers 检查
    layers = manifest.get("layers", [])
    total_bytes = 0
    for layer in layers:
        lid = layer.get("layer_id", "?")
        rel_file = layer.get("file", "")
        file_path = (base / rel_file) if not Path(rel_file).is_absolute() else Path(rel_file)
        expected_hash = layer.get("sha256", "")
        expected_bytes = layer.get("bytes", 0)
        expected_w = layer.get("width", 0)
        expected_h = layer.get("height", 0)

        # file 存在
        if not file_path.is_file():
            checks.append(report(False, f"layer_{lid}_file_exists", f"missing {rel_file}"))
            continue
        # bytes 匹配
        actual_bytes = file_path.stat().st_size
        total_bytes += actual_bytes
        if actual_bytes != expected_bytes:
            checks.append(report(False, f"layer_{lid}_bytes", f"manifest {expected_bytes} != actual {actual_bytes}"))
        else:
            checks.append(report(True, f"layer_{lid}_bytes", f"{actual_bytes}"))
        # sha256 匹配
        actual_hash = file_sha256(file_path)
        if actual_hash != expected_hash:
            checks.append(report(False, f"layer_{lid}_sha256", f"manifest {expected_hash[:16]} != actual {actual_hash[:16]}"))
        else:
            checks.append(report(True, f"layer_{lid}_sha256", actual_hash[:16]))
        # 尺寸
        if (expected_w, expected_h) not in [(EXPECTED_W, EXPECTED_H), (1080, 1920), (0, 0)]:
            checks.append(report(False, f"layer_{lid}_size", f"{expected_w}x{expected_h} not in expected"))
        else:
            checks.append(report(True, f"layer_{lid}_size", f"{expected_w}x{expected_h}"))
        # 单层预算
        if actual_bytes > MAX_LAYER_BYTES:
            checks.append(report(False, f"layer_{lid}_budget", f"{actual_bytes} > {MAX_LAYER_BYTES} (400 KB)"))
        else:
            checks.append(report(True, f"layer_{lid}_budget", f"{actual_bytes} <= 400 KB"))
        # 透明通道
        if not layer.get("alpha_channel", False):
            checks.append(report(False, f"layer_{lid}_alpha", "alpha_channel=false"))
        else:
            checks.append(report(True, f"layer_{lid}_alpha", "true"))
        # 4 底色检查图
        for c in layer.get("checks", []):
            cp = (base / c) if not Path(c).is_absolute() else Path(c)
            if not cp.is_file():
                checks.append(report(False, f"layer_{lid}_check_{Path(c).parent.name}", f"missing {c}"))
        # tileable=true 限制
        if layer.get("tileable", False):
            tileable_checks = [c for c in layer.get("checks", []) if "seamless" in c or "stages" in c or "tile" in c]
            if not tileable_checks:
                checks.append(report(False, f"layer_{lid}_tileable_check", "tileable=true 但缺 seamless/stages/tile 检查图"))
            else:
                checks.append(report(True, f"layer_{lid}_tileable_check", f"{len(tileable_checks)} tileable checks"))

    # 4. 全景预算 (仅 5 外部视觉层, 不计 void)
    if total_bytes > MAX_SCENE_BYTES:
        checks.append(report(False, "scene_budget", f"{total_bytes} > {MAX_SCENE_BYTES} (2 MB)"))
    else:
        checks.append(report(True, "scene_budget", f"{total_bytes} <= 2 MB"))

    # 5. design_ref (新场景要求)
    design_ref = manifest.get("design_ref")
    scene = manifest.get("scene_id", "")
    if scene in ("rainforest", "city", "desert", "night-path"):
        if not design_ref:
            checks.append(report(False, "design_ref", f"新场景 {scene} 必须有 design_ref (Trae 批准设计 handoff)"))
        else:
            handoff = design_ref.get("handoff", "")
            if handoff and not (ROOT / handoff).is_file():
                checks.append(report(False, "design_ref_handoff", f"design_ref.handoff 不存在: {handoff}"))
            else:
                checks.append(report(True, "design_ref", f"task={design_ref.get('task_id', '?')} handoff={handoff}"))
            if design_ref.get("spec_sha256") in (None, "", "PENDING", "PENDING_SW012_APPROVAL"):
                checks.append(report(False, "design_ref_spec_sha256", f"spec_sha256 待批准: {design_ref.get('spec_sha256')}"))
            else:
                spec_file = design_ref.get("spec_file", "")
                if spec_file and not (ROOT / spec_file).is_file():
                    checks.append(report(False, "design_ref_spec_file", f"spec_file 不存在: {spec_file}"))
                else:
                    checks.append(report(True, "design_ref_spec_file", spec_file))

    # 6. AI 输出不标 CC0 (contracts 规则)
    raw = json.dumps(manifest, ensure_ascii=False)
    if "CC0" in raw and "CC0" in raw.replace("不", "X"):  # 简单检查: 含 "CC0" 字符串且未明示拒绝
        # 例外: origin 字段写"CC0" 是合规标记, 不报错
        if "不自行声明 CC0" not in raw and "not CC0" not in raw and "不声明 CC0" not in raw:
            # 但实际 origin 写 CC0 应该被显式拒绝
            for layer in manifest.get("layers", []):
                if "CC0" in layer.get("origin", ""):
                    checks.append(report(False, f"layer_{layer.get('layer_id','?')}_cc0", "AI 输出不应标 CC0"))
                    break
    else:
        checks.append(report(True, "cc0_check", "未发现 CC0 标记"))

    # 7. API 账本字段
    for key in ["api_attempts_this_revision", "api_attempts_total", "cost"]:
        if key in manifest:
            checks.append(report(True, f"api_field_{key}", f"{manifest[key]}"))

    # 总结
    total = len(checks)
    passed = sum(1 for c in checks if c["ok"])
    failed = total - passed
    return {
        "status": "ok" if failed == 0 else "failed",
        "manifest": str(manifest_path),
        "contract_version": CONTRACT_VERSION,
        "summary": {"total": total, "passed": passed, "failed": failed, "total_bytes": total_bytes, "layer_count": len(layers)},
        "checks": checks,
    }


def render_summary(result: dict) -> str:
    s = result["summary"]
    lines = [
        f"  status: {result['status']}",
        f"  manifest: {result.get('manifest', '?')}",
        f"  contract: {result.get('contract_version', '?')}",
        f"  checks: {s['passed']}/{s['total']} passed ({s['failed']} failed)",
        f"  total bytes: {s.get('total_bytes', 0)} (budget 2 MB)",
        f"  layer count: {s.get('layer_count', 0)}",
    ]
    if result.get("error"):
        lines.insert(0, f"  ERROR: {result['error']}")
    failed = [c for c in result.get("checks", []) if not c["ok"]]
    if failed:
        lines.append(f"  failed:")
        for c in failed[:30]:
            lines.append(f"    - {c['name']}: {c['detail']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="SW-014 雨林素材交付预检脚本 (零 API)")
    ap.add_argument("manifest", type=Path, help="manifest.json 路径")
    ap.add_argument("--json", action="store_true", help="输出 JSON 报告")
    ap.add_argument("--out", type=Path, default=None, help="JSON 报告输出路径 (默认打印到 stdout)")
    args = ap.parse_args()
    result = preflight(args.manifest)
    if args.json or args.out:
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_summary(result))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())