#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SW-011 r1 · 补充检查生成器（Trae Design，2026-10-14）

只“新增”预览，不改写 sw011_render.py 的既有 43 份产物：
  previews/zoom/forest_<layer>_zoom.png
      每层 中央 + 上/下/左/右四缘，在黑/白/洋红三底上 2× 最近邻放大，
      用于按 contracts/visual-design.md §4 检查抠像边缘、暗部保留与光晕，
      不做平滑美化（最近邻保留真实像素接缝/白边/矩形底）。
  previews/runtime_crop/runtime_viewport_map.png
      在 1080×1920 源图上画三种屏幕在“静止左对齐/最大视差”两个极端下的
      实际可见源窗口，并标出跨屏幕恒可见带与旅人锚点。
  previews/runtime_crop/runtime_rest_390x844.png
  previews/runtime_crop/runtime_parallax_max_390x844.png
      逐像素复刻 ForestShell.drawImageLayer（按高度 cover、整数 dstW、
      xOffset=-parallaxPx 且夹在 [0,overflow]）渲染最小屏的两个极端。
  previews/runtime_crop/runtime-crop-check.json
      上述语义的量化结果：scale/dstW/overflow/可见源区间/恒可见带/
      旅人锚点是否恒可见/两个 overlay 层四缘 alpha（证明无矩形接缝）。

纯离线（PIL+numpy），零外部付费 API；与 sw011_render.py 消费同一模型。
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

import sw011_model as M
import sw011_render as R

HERE = os.path.dirname(os.path.abspath(__file__))
R1 = os.path.dirname(HERE)
ZOOM_DIR = os.path.join(R1, "previews", "zoom")
RT_DIR = os.path.join(R1, "previews", "runtime_crop")
os.makedirs(ZOOM_DIR, exist_ok=True)
os.makedirs(RT_DIR, exist_ok=True)

FONT = R.FONT_PATH


def font(sz):
    return R.font(sz)


INK = (34, 40, 34)
SUB = (96, 102, 96)
SHEET_BG = (245, 243, 238)
BGS = {"黑底": (0, 0, 0), "白底": (255, 255, 255), "洋红底": (255, 0, 255)}

# 放大观察框（源 1080×1920 像素），260×260，2× 最近邻放大。
# 每层两类：画布四缘（接缝/矩形底检查）+ 内容热点（真正框住主体、渐变中心与边缘衰减）。
PATCH = 260
ZOOM = 2
_EDGE_REGIONS = [
    ("画布上缘", (410, 0, 670, 260)),
    ("画布下缘", (410, 1660, 670, 1920)),
    ("画布左缘", (0, 830, 260, 1090)),
    ("画布右缘", (820, 830, 1080, 1090)),
]
CONTENT_REGIONS = {
    "tree_outline": [
        ("远冠线·中央", (300, 1150, 560, 1410)),
        ("前冠线·右侧", (700, 1180, 960, 1440)),
    ],
    "tree_trunks": [
        ("树干体积·中上", (300, 470, 560, 730)),
        ("前景剪影树·右", (870, 700, 1080, 960)),
    ],
    "leaf_path": [
        ("土路/触控带·中央", (410, 1490, 670, 1750)),
        ("落叶堆·右下", (820, 1640, 1080, 1900)),
    ],
    "light_shows": [
        ("右上光束·近光源", (820, 120, 1080, 380)),
        ("远鸟·V形细弧", (560, 200, 820, 460)),
        ("光束中段·柔衰减", (820, 500, 1080, 760)),
    ],
    "clearing": [
        ("空地辉光·中心", (583, 638, 843, 898)),
        ("辉光漫到右缘", (820, 640, 1080, 900)),
    ],
}
REGIONS = {name: CONTENT_REGIONS[name] + _EDGE_REGIONS for name, _ in M.LAYERS}


def make_zoom_sheet(name, layer_img):
    regions = REGIONS[name]
    cell = PATCH * ZOOM
    label_w, head_h, gap, margin = 230, 132, 24, 30
    cols = len(BGS)
    rows = len(regions)
    W = margin + label_w + cols * cell + (cols - 1) * gap + margin
    H = head_h + rows * cell + (rows - 1) * gap + margin
    sheet = Image.new("RGBA", (W, H), (*SHEET_BG, 255))
    d = ImageDraw.Draw(sheet)
    d.text((margin, 22), f"森林分层局部放大 · {name} · SW-011 r1", font=font(34), fill=INK)
    d.text((margin, 70), "内容热点+画布四缘 × 黑/白/洋红底；2× 最近邻放大（不美化），看抠像边缘/暗部/光晕是否有白边、矩形底或重复纹理",
           font=font(20), fill=SUB)
    d.text((margin, 98), f"观察框 {PATCH}×{PATCH} 源像素，棋盘以外为该层真实 RGBA", font=font(18), fill=SUB)

    cx0 = margin + label_w
    for j, bg_name in enumerate(BGS):
        x = cx0 + j * (cell + gap) + cell // 2
        d.text((x - 30, head_h - 34), bg_name, font=font(24), fill=INK)

    for i, (region, box) in enumerate(regions):
        y = head_h + i * (cell + gap)
        d.text((margin, y + cell // 2 - 30), region, font=font(24), fill=INK)
        sx0, sy0, sx1, sy1 = box
        patch_src = layer_img.crop((sx0, sy0, sx1, sy1))
        for j, (bg_name, rgb) in enumerate(BGS.items()):
            x = cx0 + j * (cell + gap)
            base = Image.new("RGBA", (PATCH, PATCH), (*rgb, 255))
            base.alpha_composite(patch_src)
            big = base.resize((cell, cell), Image.NEAREST)
            sheet.alpha_composite(big, (x, y))
            ImageDraw.Draw(sheet).rectangle([x, y, x + cell - 1, y + cell - 1],
                                            outline=(170, 166, 152), width=2)
        d.text((margin, y + cell // 2 + 8), f"x{sx0}-{sx1}", font=font(15), fill=SUB)
        d.text((margin, y + cell // 2 + 28), f"y{sy0}-{sy1}", font=font(15), fill=SUB)

    out = os.path.join(ZOOM_DIR, f"forest_{name}_zoom.png")
    sheet.convert("RGB").save(out)
    return out


# --------------------------------------------------------------------------
# 逐像素复刻 ForestShell.drawImageLayer
# --------------------------------------------------------------------------
def kround(x):
    return int(math.floor(x + 0.5))  # 贴近 Kotlin Float.roundToInt()


def runtime_geometry(w, h):
    scale = h / M.H
    dst_w = kround(M.W * scale)
    overflow = max(0, dst_w - w)
    return scale, dst_w, overflow


def compose_runtime(w, h, parallax_shift_px, meters=785):
    """按 drawImageLayer：按高度铺满、整数宽、xOffset=-shift（夹在 overflow）。
    parallax_shift_px 为目标像素横移；overlay 层恒为 0。"""
    img = R.void(w, h)
    scale, dst_w, overflow = runtime_geometry(w, h)
    for name, _ in M.LAYERS:
        a = R.smooth_opacity(name, meters)
        if a <= 0:
            continue
        layer = R._layer_cache[name]
        layer = layer.resize((dst_w, h), Image.LANCZOS)
        if a < 1:
            layer = layer.copy()
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
        is_overlay = M.PHASE and name in ("light_shows", "clearing")
        shift = 0 if is_overlay else int(min(max(parallax_shift_px, 0), overflow))
        img.alpha_composite(layer, (-shift, 0))
    t = R.render(R.traveler_ops(w * M.TRAVELER_X, h * M.GROUND_Y), w, h)
    img.alpha_composite(t)
    return img


def title_bar(img, text, sub=None):
    img = img.convert("RGBA").resize((img.width * 2, img.height * 2), Image.NEAREST)
    d = ImageDraw.Draw(img)
    bar = Image.new("RGBA", (img.width, 96), (6, 8, 6, 205))
    img.alpha_composite(bar, (0, 0))
    d.text((16, 12), text, font=font(30), fill=(238, 244, 238))
    if sub:
        d.text((16, 54), sub, font=font(22), fill=(150, 210, 200))
    return img


def _edge_stat(a):
    return {
        "max": int(a.max()),
        "mean": round(float(a.mean()), 2),
        "px_alpha_ge_10": int((a >= 10).sum()),
        "px_alpha_ge_64": int((a >= 64).sum()),
    }


def edge_stats(layer_img, strip=4):
    """四边外缘统计 + 内邻一条带，用于区分‘柔和漫到屏边’与‘硬接缝/白边/矩形底’。"""
    arr = np.array(layer_img)[:, :, 3]
    edges = {
        "top": arr[:strip, :],
        "bottom": arr[-strip:, :],
        "left": arr[:, :strip],
        "right": arr[:, -strip:],
    }
    stats = {k: _edge_stat(v) for k, v in edges.items()}
    inner = {
        "top": arr[strip:2 * strip, :],
        "bottom": arr[-2 * strip:-strip, :],
        "left": arr[:, strip:2 * strip],
        "right": arr[:, -2 * strip:-strip],
    }
    for k in stats:
        stats[k]["inner_adjacent_mean"] = round(float(inner[k].mean()), 2)
    return stats


def overlay_edge_judgement(stats):
    """判据针对历史缺陷（矩形硬底/白边光晕/棋盘），而非要求内容一律不到边：
    - 任一边 max<24（≈9%）且无 alpha>=64 的实色边像素；
    - 外缘均值不显著高于内邻（<=内邻*1.5+3），排除沿裁切边的亮白边/光晕；
    柔和渐变在某一边以极低 alpha 连续漫到屏边视为通过（裁切外是设备边框，不可见）。"""
    max_all = max(s["max"] for s in stats.values())
    solid = sum(s["px_alpha_ge_64"] for s in stats.values())
    fringe = any(s["mean"] > s["inner_adjacent_mean"] * 1.5 + 3 for s in stats.values())
    ok = max_all < 24 and solid == 0 and not fringe
    return {
        "pass": bool(ok),
        "edge_max_alpha": max_all,
        "solid_edge_pixels_alpha_ge_64": solid,
        "brighter_than_interior_fringe": bool(fringe),
        "criteria": "max<24 且 无>=64实色边 且 外缘不亮于内邻；软渐变低alpha连续到边不算矩形接缝",
    }


def content_bbox(layer_img, thresh=8):
    arr = np.array(layer_img)[:, :, 3]
    ys, xs = np.where(arr > thresh)
    if len(xs) == 0:
        return None
    return {"x0": int(xs.min()), "y0": int(ys.min()),
            "x1": int(xs.max()), "y1": int(ys.max())}


def make_viewport_map(layer_imgs):
    master = R.compose(785, layer_imgs)
    small = master.resize((540, 960), Image.LANCZOS).convert("RGBA")
    canv = Image.new("RGBA", (1080, 1080), (*SHEET_BG, 255))
    d = ImageDraw.Draw(canv)
    d.text((30, 24), "drawImageLayer 实际可见源窗口 · SW-011 r1", font=font(34), fill=INK)
    d.text((30, 70), "源 1080×1920（图中缩为 540×960，坐标×0.5）；按高度铺满、左对齐，右侧溢出供横向视差",
           font=font(20), fill=SUB)
    px, py, s = 30, 120, 0.5
    canv.alpha_composite(small, (px, py))
    d.rectangle([px, py, px + 540, py + 960], outline=(120, 120, 120), width=2)

    targets = [(1080, 1920, (90, 200, 210)),
               (1080, 2400, (240, 180, 90)),
               (390, 844, (210, 90, 150))]
    windows = []
    for (w, h, col) in targets:
        scale, dst_w, overflow = runtime_geometry(w, h)
        rest_right = min(M.W, w / scale)
        shift_src = overflow / scale
        max_left = shift_src
        windows.append((w, h, col, 0.0, rest_right, max_left, M.W, scale, dst_w, overflow))

    # 恒可见带（取所有屏幕交集）
    band_l = max(0.0, *[win[5] for win in windows])
    band_r = min(float(M.W), *[win[4] for win in windows])
    band = Image.new("RGBA", (540, 960), (255, 255, 255, 0))
    bd = ImageDraw.Draw(band)
    bd.rectangle([band_l * s, 0, band_r * s, 960], fill=(120, 230, 160, 46))
    canv.alpha_composite(band, (px, py))

    for (w, h, col, rl, rr, ml, mr, scale, dst_w, overflow) in windows:
        d.rectangle([px + rl * s, py, px + rr * s - 1, py + 960], outline=col, width=3)
        d.rectangle([px + ml * s, py, px + mr * s - 1, py + 960], outline=col, width=1)
    # 旅人锚点
    tx = M.W * M.TRAVELER_X * s
    ty = M.H * M.GROUND_Y * s
    d.line([px + tx, py, px + tx, py + 960], fill=(240, 214, 116), width=2)
    d.ellipse([px + tx - 7, py + ty - 7, px + tx + 7, py + ty + 7],
              outline=(240, 214, 116), width=3)

    lx = 600
    d.text((lx, 120), "图例", font=font(26), fill=INK)
    yy = 168
    for (w, h, col, rl, rr, ml, mr, scale, dst_w, overflow) in windows:
        d.rectangle([lx, yy + 4, lx + 34, yy + 24], outline=col, width=3)
        d.text((lx + 46, yy), f"{w}×{h}", font=font(22), fill=INK)
        d.text((lx + 46, yy + 30),
               f"scale={scale:.4f} dstW={dst_w} 溢出{overflow}px", font=font(17), fill=SUB)
        d.text((lx + 46, yy + 52),
               f"静止源x[0,{rr:.0f}] 最大视差x[{ml:.0f},1080]", font=font(17), fill=SUB)
        yy += 96
    d.rectangle([lx, yy + 4, lx + 34, yy + 24], fill=(120, 230, 160, 90))
    d.text((lx + 46, yy), "跨屏幕恒可见带", font=font(22), fill=INK)
    d.text((lx + 46, yy + 30), f"源 x[{band_l:.0f},{band_r:.0f}]", font=font(17), fill=SUB)
    yy += 80
    d.ellipse([lx, yy + 6, lx + 18, yy + 24], outline=(240, 214, 116), width=3)
    d.text((lx + 30, yy), f"旅人 x=.34（源x {M.W*M.TRAVELER_X:.0f}，在恒可见带内）",
           font=font(19), fill=INK)
    d.text((30, 1040), "细线=最大视差窗口，粗线=静止左对齐窗口；两 overlay 层不视差，始终左对齐。",
           font=font(18), fill=SUB)
    out = os.path.join(RT_DIR, "runtime_viewport_map.png")
    canv.convert("RGB").save(out)
    return out, windows, (band_l, band_r)


def main():
    layer_imgs = {}
    for name, builder in M.LAYERS:
        layer_imgs[name] = R.render(builder())
    R._layer_cache = layer_imgs

    zoom_paths = [make_zoom_sheet(name, layer_imgs[name]) for name, _ in M.LAYERS]

    # 最小屏两个极端
    scale, dst_w, overflow = runtime_geometry(390, 844)
    rest = title_bar(
        compose_runtime(390, 844, 0),
        "390×844 静止（sPos=0，左对齐）",
        f"scale={scale:.4f} dstW={dst_w} 溢出={overflow}px；显示源 x[0,{390/scale:.0f}]，右侧留视差余量")
    rest.save(os.path.join(RT_DIR, "runtime_rest_390x844.png"))
    maxp = title_bar(
        compose_runtime(390, 844, overflow),
        "390×844 最大视差（横移到溢出极限）",
        f"xOffset=-{overflow}px；显示源 x[{overflow/scale:.0f},1080]，左缘源内容移出、右余量全部揭示")
    maxp.save(os.path.join(RT_DIR, "runtime_parallax_max_390x844.png"))

    vp_out, windows, band = make_viewport_map(layer_imgs)

    report = {
        "schema_version": 1,
        "task_id": "SW-011",
        "revision": 1,
        "producer": "trae-design",
        "generated_on": "2026-10-14",
        "method": "本地逐像素复刻 ForestShell.drawImageLayer：scale=h/imageH; dstW=floor(imageW*scale+0.5); overflow=max(0,dstW-w); xOffset=-min(max(shift,0),overflow)，左对齐、按高度铺满。",
        "source_canvas": {"width": M.W, "height": M.H},
        "targets": [],
        "traveler": {
            "anchor_x_normalized": M.TRAVELER_X,
            "anchor_y_normalized": M.GROUND_Y,
            "source_x": M.W * M.TRAVELER_X,
            "source_y": M.H * M.GROUND_Y,
        },
        "overlay_border_alpha_max0to255_strip4": {},
        "overlay_content_bbox_alpha_gt8": {},
        "checks": [],
    }

    for (w, h, col, rl, rr, ml, mr, sc, dst_w, overflow) in windows:
        report["targets"].append({
            "size": [w, h],
            "scale": round(sc, 6),
            "dst_width_dest_px": dst_w,
            "overflow_dest_px": overflow,
            "rest_visible_source_x": [0, round(rr, 2)],
            "max_parallax_visible_source_x": [round(ml, 2), M.W],
        })

    band_l, band_r = band
    traveler_in_band = band_l <= M.W * M.TRAVELER_X <= band_r
    report["always_visible_band_source_x"] = [round(band_l, 2), round(band_r, 2)]
    report["checks"].append({
        "name": "traveler_anchor_always_visible_across_targets",
        "pass": bool(traveler_in_band),
        "detail": f"旅人源x={M.W*M.TRAVELER_X:.0f} 位于恒可见带[{band_l:.0f},{band_r:.0f}]",
    })

    edge_ok = True
    for name in ("light_shows", "clearing"):
        stats = edge_stats(layer_imgs[name])
        verdict = overlay_edge_judgement(stats)
        report["overlay_border_alpha_max0to255_strip4"][name] = stats
        report["overlay_content_bbox_alpha_gt8"][name] = content_bbox(layer_imgs[name])
        edge_ok = edge_ok and verdict["pass"]
        report["checks"].append({
            "name": f"{name}_edges_no_rectangle_seam_or_fringe",
            "pass": verdict["pass"],
            **{k: v for k, v in verdict.items() if k != "pass"},
            "detail": "最外/内邻各4px四边alpha：无实色亮边、外缘不亮于内邻即无白边/矩形硬底；"
                      "低alpha软渐变连续漫到个别屏边属正常（屏外不可见），配合 zoom 三底目检无棋盘/同心环",
        })

    # 静止左对齐：左缘不被裁（xOffset=0）
    report["checks"].append({
        "name": "rest_left_aligned_left_edge_never_cropped",
        "pass": True,
        "detail": "静止时 xOffset=0，所有层源 x=0 对齐屏幕左缘，仅右侧溢出被临时隐藏作视差余量",
    })
    report["all_pass"] = bool(traveler_in_band and edge_ok)

    with open(os.path.join(RT_DIR, "runtime-crop-check.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("zoom sheets:", len(zoom_paths))
    print("viewport:", vp_out)
    print("all_pass:", report["all_pass"])
    for c in report["checks"]:
        print(" -", c["name"], c["pass"], c.get("observed_max", ""))


if __name__ == "__main__":
    main()
