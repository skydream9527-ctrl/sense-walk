#!/usr/bin/env python3
"""
SW-006 R2 候选 manifest 生成器 (零 API).

从 r2 目录的真实产物生成 manifest.json:
- 每层: layer_id/file/sha256/width/height/bytes/alpha_channel/render_role/tileable/
  origin/process/quality_status/checks/limitations
- 额外字段 (供 production_guard 校验): source_resolution / call
- design_ref 精确指向 D-009 冻结的 SW-012 批准链
- api_attempts_* 与持久账本一致

所有路径相对 repo 根. 哈希与尺寸由实际文件重算, 不抄写旧值.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prompts_r2  # noqa: E402
import api_ledger  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
R2_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[6]

MANIFEST_PATH = R2_DIR / "manifest.json"
REPORT_PATH = R2_DIR / "records" / "postprocess-report.json"

DESIGN_TASK = "SW-012"
DESIGN_HANDOFF = "docs/collaboration/handoffs/trae-design/H-SW-012-R1.json"
DESIGN_SPEC = "design/05-visual-design/SW-012/r1/design-spec.json"
DESIGN_SPEC_SHA = "643e77b1ba7574c9b013dce485fde2797816096181feda91c2fa7920d042c320"

#: 生图服务与调用参数 (真实记录, 不写 CC0)
SERVICE = "mcode-tools connector__matrix__generate_image (MiniMax matrix 托管生图服务)"
SERVICE_TERMS = "host-managed 托管服务, 凭据仅 host/env, 不入 Git; 单次调用消耗 SW-006 任务预算 1 次"
COST_NOTE = "unknown (托管服务未按次返回费用数值)"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def main() -> int:
    if not REPORT_PATH.is_file():
        print(f"缺 {REPORT_PATH}, 请先跑 postprocess_r2.py", file=sys.stderr)
        return 1
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    by_layer = {r["layer_id"]: r for r in report["layers"]}

    ledger = api_ledger.load_ledger()
    used = api_ledger.sw006_attempts(ledger)
    lifetime = api_ledger.project_lifetime_attempts(ledger)
    this_rev = sum(1 for e in ledger["entries"] if e.get("revision") == "r2")

    layers: List[Dict[str, Any]] = []
    for layer_id in prompts_r2.LAYER_IDS:
        r = by_layer[layer_id]
        spec = prompts_r2.LAYER_SPECS[layer_id]
        png_abs = REPO_ROOT / r["png"]
        webp_abs = REPO_ROOT / r["webp"]
        src_abs = REPO_ROOT / r["source"]
        m = r["measure"]
        fit = r["fit"]
        key = r["key"]
        adiag = r["alpha_normalize"]
        pdiag = r.get("palette_transfer", {})

        layers.append({
            "layer_id": layer_id,
            "file": rel(webp_abs),
            "png_file": rel(png_abs),
            "source_file": rel(src_abs),
            "width": 1080,
            "height": 1920,
            "bytes": webp_abs.stat().st_size,
            "sha256": sha256_of(webp_abs),
            "png_sha256": sha256_of(png_abs),
            "source_resolution": fit["source_resolution"],
            "alpha_channel": True,
            "render_role": spec["render_role"],
            "parallax": spec["parallax"],
            "at_meters": spec["at_meters"],
            "to_opacity": spec["to_opacity"],
            "fade_meters": spec["fade_meters"],
            "tileable": False,
            "origin": (
                f"{SERVICE} 生成的单层素材 (image-to-image, 参考 SW-012 批准 export); "
                f"非公有领域素材, 条款: {SERVICE_TERMS}"
            ),
            "process": (
                f"postprocess_r2.py: 可分离洋红底反解混合方程求 alpha (bg={key.get('background_rgb')}, "
                f"F={key.get('foreground_rgb')}) -> 等比 LANCZOS 缩放并中心裁切至 1080x1920 "
                f"({fit['source_to_canvas']}, 来源 {fit['source_resolution']}) -> "
                f"alpha 密度标定到 SW-012 批准 design 实测统计 (gamma={adiag.get('gamma')}, "
                f"目标最大 alpha={adiag.get('target_max_alpha')}) -> "
                f"色域收敛到批准色板统计 (只取批准 export 的色彩/明度分布统计量, 未复制任何 design 像素) -> "
                f"alpha 量化 {prompts_r2 and 64} 级 + 3x3 中值去噪 -> PNG(RGBA) + WebP(quality={r['webp_quality']})"
            ),
            "quality_status": "candidate",
            "call": {
                "service": "connector__matrix__generate_image",
                "model_family": "MiniMax matrix 托管生图",
                "prompt_ref": prompts_r2.prompt_ref(layer_id),
                "reference_input": prompts_r2.REFERENCE_FILES[layer_id],
                "aspect_ratio": "9:16",
                "resolution": "2K",
                "returned_resolution": fit["source_resolution"],
                "ledger_seq": None,
            },
            "checks": [
                rel(REPO_ROOT / r["png"]),
                rel(REPO_ROOT / f"design/assets/rainforest/candidates/SW-006/r2/checks/alpha_mask/rainforest_{layer_id}.png"),
                rel(REPO_ROOT / f"design/assets/rainforest/candidates/SW-006/r2/checks/black/rainforest_{layer_id}.jpg"),
                rel(REPO_ROOT / f"design/assets/rainforest/candidates/SW-006/r2/checks/white/rainforest_{layer_id}.jpg"),
                rel(REPO_ROOT / f"design/assets/rainforest/candidates/SW-006/r2/checks/magenta/rainforest_{layer_id}.jpg"),
                rel(REPO_ROOT / r["zoom"]),
            ] + [
                rel(REPO_ROOT / p["path"])
                for p in report.get("parallax", [])
                if p.get("layer_id") == layer_id
            ],
            "measurements": {
                "alpha_max": m["alpha_max"],
                "semi_transparent_fraction": m["semi_transparent_fraction"],
                "transparent_fraction": m["transparent_fraction"],
                "edge_strip4_max_alpha": m["edge_strip4_max_alpha"],
                "background_residual_fraction": m["background_residual_fraction"],
                "max_alpha_gradient_x": m["max_alpha_gradient_x"],
                "max_alpha_gradient_y": m["max_alpha_gradient_y"],
                "has_hard_edge": m["has_hard_edge"],
                "webp_bytes": r["webp_bytes"],
                "webp_quality": r["webp_quality"],
                "palette_transfer": pdiag,
            },
            "limitations": [
                "候选, 未入包; 需 Antigravity 独立审核后由 ZCode 按单独入包任务接线",
                "tileable=false: 当前渲染语义仅右侧溢出宽度内有限横向滑动, 未做无缝平铺, 不宣称可平铺",
                f"来源分辨率 {fit['source_resolution']}, 经等比缩放+中心裁切得到 1080x1920, 非原生 1080",
                "alpha 由洋红可分离底反解得到, 边缘为反解软边, 极细发丝处可能有 1-2px 精度损失",
            ],
        })

    # 绑定账本 seq: 每层取 **最后一次成功** 的尝试 (同层可有被拒的早期探针)
    seq_by_layer: Dict[str, int] = {}
    for e in ledger["entries"]:
        if e.get("revision") != "r2" or e.get("layer_id") not in prompts_r2.LAYER_IDS:
            continue
        if e.get("outcome") == "success":
            seq_by_layer[e["layer_id"]] = e["seq"]
    # 无成功记录时退回该层最后一次尝试 (如实记录, 不谎称成功)
    for e in ledger["entries"]:
        if e.get("revision") == "r2" and e.get("layer_id") in prompts_r2.LAYER_IDS:
            seq_by_layer.setdefault(e["layer_id"], e["seq"])
    for layer in layers:
        seq = seq_by_layer.get(layer["layer_id"])
        layer["call"]["ledger_seq"] = seq

    manifest = {
        "schema_version": 1,
        "task_id": "SW-006",
        "revision": 2,
        "scene_id": "rainforest",
        "producer": "minimax",
        "api_attempts_this_revision": this_rev,
        "api_attempts_total": lifetime,
        "cost": COST_NOTE,
        "canvas": {"width": 1080, "height": 1920},
        "layers": layers,
        "design_ref": {
            "task_id": DESIGN_TASK,
            "handoff": DESIGN_HANDOFF,
            "spec_file": DESIGN_SPEC,
            "spec_sha256": DESIGN_SPEC_SHA,
            "decision": "docs/collaboration/decisions/D-009-freeze-rainforest-design-spec.md",
        },
        "api_ledger": {
            "ledger_file": rel(api_ledger.LEDGER_PATH),
            "sw006_attempts_used": used,
            "sw006_attempts_limit": api_ledger.SW006_ATTEMPTS_LIMIT,
            "project_lifetime_baseline": api_ledger.PROJECT_LIFETIME_BASELINE,
            "project_lifetime_attempts": lifetime,
            "outcomes": {
                o: sum(1 for e in ledger["entries"] if e.get("outcome") == o)
                for o in api_ledger.OUTCOMES
            },
            "entries": ledger["entries"],
        },
        "stage_checks": [f"design/assets/rainforest/candidates/SW-006/r2/checks/stages/stage_{m:03d}m.png"
                         for m in prompts_r2.STAGE_METERS],
        "parallax_checks": [
            f"design/assets/rainforest/candidates/SW-006/r2/checks/parallax/{n}"
            for n in (
                "rainforest_trunks_canopy_rest_1080x1920.png",
                "rainforest_trunks_canopy_parallax_max_1080x1920.png",
                "rainforest_vines_light_rest_1080x1920.png",
                "rainforest_vines_light_parallax_max_1080x1920.png",
                "runtime_1080x2400_rest.png",
                "runtime_1080x2400_parallax_max.png",
                "runtime_390x844_rest.png",
                "runtime_390x844_parallax_max.png",
                "runtime-parallax-check.json",
            )
        ],
        "limitations": [
            "本轮 SW-006 共 8 次尝试预算已用尽 (含 2 次被拒的探针与 1 次需重做的卡片式构图); 账本逐次可追溯",
            "未做真机/模拟器/Android 渲染验证; 候选仅在本地像素级与阶段合成层验证",
            "不声明 approved_candidate / integrated / app_verified; 审核与入包由 Antigravity / ZCode 负责",
        ],
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {rel(MANIFEST_PATH)}")
    print(f"  layers={len(layers)} api_this_rev={this_rev} api_total={lifetime} "
          f"webp_total={sum(l['bytes'] for l in layers)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
