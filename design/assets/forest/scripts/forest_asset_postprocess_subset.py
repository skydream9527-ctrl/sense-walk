#!/usr/bin/env python3
"""
部分后处理：只跑已经被认可的 4 张
（forest_tree_trunks / forest_leaf_path / forest_clearing / style_ref）
其余 3 张等 v2 修复图到位再合并跑。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
RAW_DIR = ROOT / "design" / "assets" / "forest" / "raw"
ART_DIR = ROOT / "design" / "assets" / "forest" / "artwork"
PREVIEW_DIR = ROOT / "design" / "assets" / "forest" / "previews"
ASSETS_VISUAL = ROOT / "app" / "src" / "main" / "assets" / "visual"

ART_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_VISUAL.mkdir(parents=True, exist_ok=True)

VOID_RGB = np.array([0x06, 0x08, 0x06], dtype=np.float32)
ONLY = ["style_ref", "forest_tree_trunks", "forest_leaf_path", "forest_clearing"]


def compute_alpha(rgb, role):
    diff = rgb.astype(np.float32) - VOID_RGB[None, None, :]
    dist = np.sqrt((diff * diff).sum(axis=2))
    dist_thr_lo, dist_thr_hi = 22.0, 60.0
    alpha = np.clip((dist - dist_thr_lo) / (dist_thr_hi - dist_thr_lo), 0.0, 1.0)
    alpha = (alpha * 255).astype(np.uint8)
    h, w = alpha.shape
    if role == "character":
        et, eb, el, er = 0.06, 0.04, 0.05, 0.05
    else:
        et, eb, el, er = 0.04, 0.04, 0.04, 0.04
    t, b, l, r = int(h*et), int(h*eb), int(w*el), int(w*er)
    alpha[:t, :] = 0
    alpha[h-b:, :] = 0
    alpha[:, :l] = 0
    alpha[:, w-r:] = 0
    return alpha


def main():
    state = json.loads((ROOT / "design" / "assets" / "forest" / "records" / "jobs.json").read_text(encoding="utf-8"))
    for jid in ONLY:
        rec = state["jobs"][jid]
        role = "reference" if jid == "style_ref" else (
            "parallax-bg" if jid in ("forest_tree_outline", "forest_tree_trunks")
            else "parallax-fg" if jid == "forest_leaf_path"
            else "overlay"
        )
        base = rec["label"]
        raw = ROOT / rec["raw_path"]
        if not raw.exists():
            print(f"[skip] {base} raw missing")
            continue
        img = Image.open(raw).convert("RGB")
        rgb = np.asarray(img, dtype=np.uint8)
        alpha = compute_alpha(rgb, role)
        rgba = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
        png = ART_DIR / f"{base}.png"
        webp = ASSETS_VISUAL / f"{base}.webp"
        rgba.save(png, format="PNG", optimize=True)
        rgba.save(webp, format="WEBP", quality=90, method=6)
        print(f"[ok ] {base}: {raw.stat().st_size/1024:.0f}KB raw → {webp.stat().st_size/1024:.0f}KB webp, {rgba.size}")


if __name__ == "__main__":
    main()
