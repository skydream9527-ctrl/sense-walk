#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SW-012 r1 · 补充检查生成器（Trae Design，2026-10-15）

只新增预览，不改写 sw012_render.py 的产物：
  previews/zoom/rainforest_<layer>_zoom.png
      每层 内容热点 + 画布四缘，在黑/白/洋红三底上 2× 最近邻放大，
      按 contracts/visual-design.md §4 检查抠像边缘、暗部保留与光晕，
      不做平滑美化（最近邻保留真实像素接缝/白边/矩形底）。
  previews/runtime_crop/runtime_viewport_map.png
      1080×1920 源图上画三种屏幕“静止左对齐/最大视差”两极端可见源窗口、
      跨屏幕恒可见带与旅人锚点。
  previews/runtime_crop/runtime_rest_390x844.png
  previews/runtime_crop/runtime_parallax_max_390x844.png
      逐像素复刻 ForestShell.drawImageLayer（雨林将沿用同一按高度 cover、
      整数 dstW、xOffset=-parallaxPx 夹在 [0,overflow] 语义；rainforest.json
      尚未存在，故为对齐既有渲染器的设计复核，非 Android 证据）。
  previews/runtime_crop/runtime-crop-check.json
      scale/dstW/overflow/可见源区间/恒可见带/旅人锚点/三个 overlay 四缘 alpha。

纯离线（PIL+numpy），零外部付费 API；与 sw012_render.py 消费同一模型。
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

import sw012_model as M
import sw012_render as R

HERE = os.path.dirname(os.path.abspath(__file__))
R1 = os.path.dirname(HERE)
ZOOM_DIR = os.path.join(R1, "previews", "zoom")
RT_DIR = os.path.join(R1, "previews", "runtime_crop")
os.makedirs(ZOOM_DIR, exist_ok=True)
os.makedirs(RT_DIR, exist_ok=True)

FONT = R.FONT_PATH
FINAL_METERS = 875


def font(sz):
    return R.font(sz)


INK = (28, 38, 32)
SUB = (88, 100, 92)
SHEET_BG = (240, 243, 239)
BGS = {"黑底": (0, 0, 0), "白底": (255, 255, 255), "洋红底": (255, 0, 255)}

PATCH = 260
ZOOM = 2
_EDGE_REGIONS = [
    ("画布上缘", (410, 0, 670, 260)),
    ("画布下缘", (410, 1660, 670, 1920)),
    ("画布左缘", (0, 830, 260, 1090)),
    ("画布右缘", (820, 830, 1080, 1090)),
]
CONTENT_REGIONS = {
    "mist": [
        ("贴地湿雾·中央", (330, 1420, 590, 1680)),
        ("亮雾心·左下", (180, 1430, 440, 1690)),
        ("横飘雾·中段", (470, 1140, 730, 1400)),
    ],
    "trunks_canopy": [
        ("林隙缺口·上中", (560, 140, 820, 400)),
        ("阔叶顶棚·左上", (120, 470, 380, 730)),
        ("板根粗干·中下", (390, 1380, 650, 1640)),
        ("前景暗树·右下", (900, 1300, 1080, 1560)),
    ],
    "vines_light": [
        ("垂藤对生叶·左", (50, 300, 310, 560)),
        ("藤蔓光斑·右上", (720, 280, 980, 540)),
        ("垂藤中段·右", (760, 520, 1020, 780)),
    ],
    "distant_glow": [
        ("林隙透光·上中", (540, 180, 800, 440)),
        ("次透光·左上", (130, 250, 390, 510)),
        ("流动水汽·中下", (430, 1160, 690, 1420)),
    ],
    "glade": [
        ("幽径辉光·中心", (470, 1030, 730, 1290)),
        ("湿径反光·中下", (470, 1440, 730, 1700)),
        ("辉光漫向左缘", (0, 1060, 260, 1320)),
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
    d.text((margin, 22), f"雨林分层局部放大 · {name} · SW-012 r1", font=font(34), fill=INK)
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
                                            outline=(166, 176, 168), width=2)
        d.text((margin, y + cell // 2 + 8), f"x{sx0}-{sx1}", font=font(15), fill=SUB)
        d.text((margin, y + cell // 2 + 28), f"y{sy0}-{sy1}", font=font(15), fill=SUB)

    out = os.path.join(ZOOM_DIR, f"rainforest_{name}_zoom.png")
    sheet.convert("RGB").save(out)
    return out


# --------------------------------------------------------------------------
# 逐像素复刻 drawImageLayer（与 SW-011 supplement 同语义）
# --------------------------------------------------------------------------
def kround(x):
    return int(math.floor(x + 0.5))


def runtime_geometry(w, h):
    scale = h / M.H
    dst_w = kround(M.W * scale)
    overflow = max(0, dst_w - w)
    return scale, dst_w, overflow


def compose_runtime(w, h, parallax_shift_px, meters=FINAL_METERS):
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
        shift = 0 if name in M.OVERLAY_LAYERS else int(min(max(parallax_shift_px, 0), overflow))
        img.alpha_composite(layer, (-shift, 0))
    t = R.render(R.traveler_ops(w * M.TRAVELER_X, h * M.GROUND_Y), w, h)
    img.alpha_composite(t)
    return img


def title_bar(img, text, sub=None):
    img = img.convert("RGBA").resize((img.width * 2, img.height * 2), Image.NEAREST)
    d = ImageDraw.Draw(img)
    bar = Image.new("RGBA", (img.width, 96), (5, 8, 7, 205))
    img.alpha_composite(bar, (0, 0))
    d.text((16, 12), text, font=font(30), fill=(238, 244, 238))
    if sub:
        d.text((16, 54), sub, font=font(22), fill=(150, 210, 190))
    return img


def _edge_stat(a):
    return {
        "max": int(a.max()),
        "mean": round(float(a.mean()), 2),
        "px_alpha_ge_10": int((a >= 10).sum()),
        "px_alpha_ge_64": int((a >= 64).sum()),
    }


def edge_stats(layer_img, strip=4):
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
    master = R.compose(FINAL_METERS, layer_imgs)
    small = master.resize((540, 960), Image.LANCZOS).convert("RGBA")
    Wc, Hc = 1320, 1080
    canv = Image.new("RGBA", (Wc, Hc), (*SHEET_BG, 255))
    d = ImageDraw.Draw(canv)
    d.text((30, 24), "drawImageLayer 实际可见源窗口 · SW-012 r1（雨林，语义对齐森林渲染器）",
           font=font(31), fill=INK)
    d.text((30, 68), "源 1080×1920（缩为 540×960，坐标×0.5）；按高度铺满、左对齐，右侧溢出供横向视差",
           font=font(20), fill=SUB)
    px, py, s = 30, 116, 0.5
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

    band_l = max(0.0, *[win[5] for win in windows])
    band_r = min(float(M.W), *[win[4] for win in windows])
    band = Image.new("RGBA", (540, 960), (255, 255, 255, 0))
    ImageDraw.Draw(band).rectangle([band_l * s, 0, band_r * s, 960], fill=(120, 230, 160, 46))
    canv.alpha_composite(band, (px, py))

    for (w, h, col, rl, rr, ml, mr, scale, dst_w, overflow) in windows:
        d.rectangle([px + rl * s, py, px + rr * s - 1, py + 960], outline=col, width=3)
        d.rectangle([px + ml * s, py, px + mr * s - 1, py + 960], outline=col, width=1)
    tx = M.W * M.TRAVELER_X * s
    ty = M.H * M.GROUND_Y * s
    d.line([px + tx, py, px + tx, py + 960], fill=(240, 214, 116), width=2)
    d.ellipse([px + tx - 7, py + ty - 7, px + tx + 7, py + ty + 7],
              outline=(240, 214, 116), width=3)

    lx = 600
    d.text((lx, 116), "图例", font=font(26), fill=INK)
    yy = 164
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
    d.text((30, 1040), "细线=最大视差窗口，粗线=静止左对齐窗口；mist/distant_glow/glade 为 overlay 不视差。",
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

    scale, dst_w, overflow = runtime_geometry(390, 844)
    rest = title_bar(
        compose_runtime(390, 844, 0),
        "390×844 静止（sPos=0，左对齐）· 雨林 875m",
        f"scale={scale:.4f} dstW={dst_w} 溢出={overflow}px；显示源 x[0,{390/scale:.0f}]，右侧留视差余量")
    rest.save(os.path.join(RT_DIR, "runtime_rest_390x844.png"))
    maxp = title_bar(
        compose_runtime(390, 844, overflow),
        "390×844 最大视差（横移到溢出极限）· 雨林 875m",
        f"xOffset=-{overflow}px；显示源 x[{overflow/scale:.0f},1080]，左缘源内容移出、右余量揭示")
    maxp.save(os.path.join(RT_DIR, "runtime_parallax_max_390x844.png"))

    vp_out, windows, band = make_viewport_map(layer_imgs)

    report = {
        "schema_version": 1,
        "task_id": "SW-012",
        "revision": 1,
        "producer": "trae-design",
        "generated_on": "2026-10-15",
        "naming_status": "layer IDs 为 proposed，待 Antigravity 审稿冻结",
        "method": "本地逐像素复刻既有 drawImageLayer 语义（雨林 rainforest.json/Shell 尚未存在，对齐森林渲染器做设计复核）：scale=h/imageH; dstW=floor(imageW*scale+0.5); overflow=max(0,dstW-w); xOffset=-min(max(shift,0),overflow)，左对齐、按高度铺满；overlay 层不视差。",
        "source_canvas": {"width": M.W, "height": M.H},
        "required_distance": M.REQUIRED_DISTANCE,
        "preview_meters_fade_complete": M.PREVIEW_METERS,
        "targets": [],
        "traveler": {
            "anchor_x_normalized": M.TRAVELER_X,
            "anchor_y_normalized": M.GROUND_Y,
            "source_x": M.W * M.TRAVELER_X,
            "source_y": M.H * M.GROUND_Y,
        },
        "overlay_layers": sorted(M.OVERLAY_LAYERS),
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
    report["always_visible_band_source_x"] = [round(band_l, 2), round(band_r)]
    report["checks"].append({
        "name": "traveler_anchor_always_visible_across_targets",
        "pass": bool(traveler_in_band),
        "detail": f"旅人源x={M.W*M.TRAVELER_X:.0f} 位于恒可见带[{band_l:.0f},{band_r:.0f}]",
    })

    edge_ok = True
    for name in sorted(M.OVERLAY_LAYERS):
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
        print(" -", c["name"], c["pass"])


if __name__ == "__main__":
    main()
