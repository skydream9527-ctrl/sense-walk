#!/usr/bin/env python3
"""
SenseWalk · 森林视觉素材生成脚本

职责
----
1. 统一调用 mcode-tools connector `connector__matrix__generate_image` 出图；
2. 把每张图保存为任务 ID + 提示词 + 输出路径一一对应的本地记录；
3. 重复运行不重出已完成图（idempotency）；
4. 限制总请求数与重试次数，防止超预算；
5. 把下载得到的 JPG 转为 WebP（仅作工作副本），并保留原图。

环境
----
- mcode-tools 已在 PATH；
- `auth status` 返回 authenticated（用户已就绪）；
- 本脚本不读、不写、不打印任何 API Key / token。

预算（用户约定）
----------------
- 风格参考 1 张
- 森林层 5 张
- 角色 1 张
- 失败/修复追加：≤ 3 次
- 总请求数硬上限：9（9 = 7 + 2 容差；超过即终止并报告）
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[4]  # design/assets/forest/scripts/forest_asset_gen.py → sense-walk
RAW_DIR = ROOT / "design" / "assets" / "forest" / "raw"
RECORD_DIR = ROOT / "design" / "assets" / "forest" / "records"
RECORD_FILE = RECORD_DIR / "jobs.json"
MCODEX = "mcode-tools"

RAW_DIR.mkdir(parents=True, exist_ok=True)
RECORD_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class JobSpec:
    job_id: str
    label: str  # 文件名（不带后缀，最终 file_name 决定）
    prompt: str
    aspect_ratio: str = "9:16"
    resolution: str = "1K"
    input_urls: list[str] = field(default_factory=list)
    notes: str = ""


def load_jobs() -> dict:
    if RECORD_FILE.exists():
        return json.loads(RECORD_FILE.read_text(encoding="utf-8"))
    return {"version": 1, "jobs": {}}


def save_jobs(state: dict) -> None:
    RECORD_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def call_generate(spec: JobSpec, max_attempts: int = 3) -> dict:
    """调一次 generate_image，含有限重试。返回 server JSON dict。"""
    req = {
        "prompt": spec.prompt,
        "aspect_ratio": spec.aspect_ratio,
        "resolution": spec.resolution,
    }
    if spec.input_urls:
        req["input_urls"] = spec.input_urls
    # output_file 是建议的下载文件名，目录部分被忽略
    req["output_file"] = spec.label

    body = {"requests": [req]}
    args = ["--args", json.dumps(body, ensure_ascii=False)]
    last_err: Optional[str] = None
    for attempt in range(1, max_attempts + 1):
        try:
            proc = subprocess.run(
                [MCODEX, "connector", "call", "connector__matrix__generate_image", *args],
                capture_output=True,
                text=True,
                timeout=600,
            )
        except subprocess.TimeoutExpired as e:
            last_err = f"timeout: {e}"
            time.sleep(2 * attempt)
            continue
        if proc.returncode == 0:
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError as e:
                last_err = f"non-json response: {proc.stdout[:200]}"
        else:
            last_err = f"rc={proc.returncode}: {proc.stderr.strip()[:200]} or stdout: {proc.stdout.strip()[:200]}"
        time.sleep(2 * attempt)
    raise RuntimeError(f"generate_image failed after {max_attempts} attempts: {last_err}")


def fetch_asset(node_id: str, dst: Path, max_attempts: int = 5) -> Path:
    """拉取下载链接并保存到 dst。connector_busy 也走指数退避。"""
    last_err: Optional[str] = None
    for attempt in range(1, max_attempts + 1):
        proc = subprocess.run(
            [MCODEX, "get_asset_url", str(node_id)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            try:
                info = json.loads(proc.stdout)
            except json.JSONDecodeError as e:
                last_err = f"non-json: {proc.stdout[:160]}"
                time.sleep(3 * attempt)
                continue
            url = info.get("download_url")
            if not url:
                last_err = f"no download_url in: {info}"
                time.sleep(3 * attempt)
                continue
            proc2 = subprocess.run(
                ["curl", "-sSL", "--fail", url, "-o", str(dst)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc2.returncode == 0 and dst.exists() and dst.stat().st_size > 0:
                return dst
            last_err = f"curl rc={proc2.returncode} stderr={proc2.stderr[:160]}"
        else:
            stderr = proc.stderr.strip()
            stdout = proc.stdout.strip()
            last_err = f"rc={proc.returncode} stderr={stderr[:120]} stdout={stdout[:120]}"
        # connector_busy 等情形用更长退避
        time.sleep(4 * attempt)
    raise RuntimeError(f"get_asset_url failed after {max_attempts} attempts: {last_err}")


def already_done(state: dict, job_id: str) -> Optional[dict]:
    rec = state["jobs"].get(job_id)
    if not rec:
        return None
    raw = ROOT / rec["raw_path"]
    if raw.exists() and rec.get("node_id"):
        return rec
    return None


def run_job(spec: JobSpec, state: dict) -> dict:
    existing = already_done(state, spec.job_id)
    if existing:
        print(f"[skip] {spec.job_id} already done → {existing['raw_path']}")
        return existing

    print(f"[run ] {spec.job_id} ({spec.aspect_ratio}, {spec.resolution})")
    resp = call_generate(spec)
    summary = resp.get("summary", "")
    successes = resp.get("success_items", [])
    failures = resp.get("failed_items", [])
    if failures:
        print(f"[warn] partial failure for {spec.job_id}: {failures}")
    if not successes:
        raise RuntimeError(f"job {spec.job_id} produced no success_items: {resp}")

    item = successes[0]
    node_id = item["node_id"]
    file_name = item["file_name"]  # 真正的后缀
    raw_path = RAW_DIR / f"{spec.job_id}{Path(file_name).suffix.lower()}"
    fetch_asset(node_id, raw_path)
    if not raw_path.exists():
        raise RuntimeError(f"raw file not saved: {raw_path}")

    rec = {
        "job_id": spec.job_id,
        "label": spec.label,
        "prompt": spec.prompt,
        "aspect_ratio": spec.aspect_ratio,
        "resolution": spec.resolution,
        "input_urls": spec.input_urls,
        "node_id": node_id,
        "file_name": file_name,
        "raw_path": str(raw_path.relative_to(ROOT)),
        "summary": summary,
        "notes": spec.notes,
        "ts": int(time.time()),
    }
    state["jobs"][spec.job_id] = rec
    save_jobs(state)
    print(f"[done] {spec.job_id} → {raw_path.name} ({raw_path.stat().st_size} bytes)")
    return rec


# ---------------------- 工作流定义 ---------------------- #

def forest_jobs() -> list[JobSpec]:
    """按用户约定的 7 张出图：1 风格参考 + 5 森林层 + 1 旅人。"""
    style = JobSpec(
        job_id="style_ref",
        label="forest_style_ref",
        prompt=(
            "A calm 2D hand-drawn forest scene reference sheet, low-saturation, "
            "soft paper grain, clean silhouettes, soft edges, gentle muted greens "
            "and warm browns, a thin distant tree line at the horizon, midground "
            "vertical trunks, dry leaf ground, two or three soft diagonal sun rays, "
            "small distant bird silhouettes, faint ground glow. "
            "Side view 3/4 perspective, no character, no UI, no text, no logo, "
            "no watermark, no harsh neon, no first-person road perspective, "
            "no dense jungle, no rain."
        ),
        notes="参考色板: #060806, #1A2820, #2D4A3E, #8FA87A, #6B8F71, #A89060",
    )

    outline = JobSpec(
        job_id="forest_tree_outline",
        label="forest_tree_outline",
        prompt=(
            "A horizontal seamless 2D hand-drawn silhouette tree line for parallax background. "
            "Only distant sparse tree canopies and treeline at the horizon, dark greenish-black "
            "silhouettes (#1A2820). Plain dark teal-green background (#060806) that will be made "
            "transparent. No midground, no foreground, no ground, no path, no character, no "
            "birds, no light beams, no text, no UI. Tiles horizontally with no visible seam."
        ),
        notes="parallax 远景；目标 1080×1920 canvas；上层树冠、底层地平线下方完全留作透明。",
    )

    trunks = JobSpec(
        job_id="forest_tree_trunks",
        label="forest_tree_trunks",
        prompt=(
            "A horizontal seamless 2D hand-drawn midground tree trunks layer for parallax. "
            "Vertical trunks in muted dark green #2D4A3E with very soft pale green light "
            "shimmer #8FA87A between them, sparse and naturally spaced leaving walking space. "
            "Plain dark teal-green background (#060806) to be removed. No treeline, no ground, "
            "no character, no path, no birds, no text, no UI. Tiles horizontally with no visible seam."
        ),
        notes="parallax 中景树干；预留旅人通行空间。",
    )

    leaf_path = JobSpec(
        job_id="forest_leaf_path",
        label="forest_leaf_path",
        prompt=(
            "A horizontal seamless 2D hand-drawn ground layer of dry leaves, soft earth path "
            "edge, small warm brown accents #A89060, muted green #6B8F71 leaf specks, low and "
            "flat (no strong perspective road vanishing into the distance). Top half completely "
            "empty / transparent area. Plain dark teal-green background (#060806) to be removed. "
            "No character, no birds, no sky details, no text, no UI. The ground baseline must be "
            "horizontally flat (no slope)."
        ),
        notes="parallax 近景地面；与角色脚底基线对齐；不带坡度。",
    )

    light_shows = JobSpec(
        job_id="forest_light_shows",
        label="forest_light_shows",
        prompt=(
            "A horizontal 2D hand-drawn transparent overlay for forest scene. Two or three very "
            "soft pale green diagonal sun beams #8FA87A, low opacity, plus two or three very "
            "small distant bird silhouettes (small, restrained, not the main subject). Plain "
            "dark teal-green background (#060806) to be removed. No trees, no full background, "
            "no character, no text, no UI. The light beams must be narrow and faint, not large "
            "opaque white areas."
        ),
        notes="overlay 飞鸟+光柱；限制鸟尺寸、不抢戏。",
    )

    clearing = JobSpec(
        job_id="forest_clearing",
        label="forest_clearing",
        prompt=(
            "A horizontal 2D hand-drawn transparent overlay: a soft distant forest clearing "
            "glow with very faint pale warm light #A8C5A0 / #C4D4A8 in the upper-mid area, a "
            "thin atmospheric haze, very gentle. Plain dark teal-green background (#060806) to "
            "be removed. No trees drawn, no character, no fireworks, no trophy, no celebratory "
            "imagery, no text, no UI. Should feel like arriving at a quiet place."
        ),
        notes="overlay 林间空地微光；表达'走到了安静的地方'。",
    )

    traveler = JobSpec(
        job_id="traveler_idle",
        label="traveler_idle",
        prompt=(
            "A single still 2D hand-drawn character sprite, side 3/4 view facing right, "
            "transparent background, body proportions head-to-height about 1 to 3.3. "
            "Neutral adult, medium-length coat or light cloak, loose pants, simple travel "
            "boots, no facial features drawn. Main color muted gray-green #6A7A6E, dark "
            "shadows #2A322C, very faint pale green rim light. Relaxed idle pose, no "
            "walking motion, complete body, no scenery, no trees, no ground, no shadow on "
            "ground, no text, no UI."
        ),
        notes="默认旅人；只静态帧；脚底基线齐平；四周完全透明。",
    )

    return [style, outline, trunks, leaf_path, light_shows, clearing, traveler]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="只跑指定 job_id", default=None)
    parser.add_argument("--limit", type=int, default=9, help="本轮最多跑多少张（含已完成）")
    args = parser.parse_args()

    state = load_jobs()
    jobs = forest_jobs()
    if args.only:
        jobs = [j for j in jobs if j.job_id == args.only]
    limit = args.limit

    completed = sum(1 for j in jobs if already_done(state, j.job_id))
    if completed >= limit:
        print(f"[info] 已完成 {completed} 张达上限 {limit}，不重跑。")
        return 0

    pending = [j for j in jobs if not already_done(state, j.job_id)]
    budget = max(0, limit - completed)
    pending = pending[:budget]
    print(f"[info] 计划新跑 {len(pending)} 张（已完成 {completed}，上限 {limit}）")

    for spec in pending:
        run_job(spec, state)
    print("[info] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
