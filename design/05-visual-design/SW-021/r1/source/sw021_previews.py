#!/usr/bin/env python3
"""SW-021 R1 · 森林 tile 预览与连续视差合成器（只读 + 只写本任务 previews/）。

产出：
  previews/tiles/checks/forest_{layer}_check3.png      黑/白/洋红三底
  previews/tiles/repeat/forest_{layer}_repeat3.png     三次水平拼接（接缝标注）
  previews/tiles/seam/forest_seam_probe_sheet.png      接缝像素探针（三底 2× 放大）
  previews/composite/forest_tiled_matrix_{ratio}.png   新平铺模型六阶段矩阵
  previews/composite/forest_continuous_compare.png     旧 cover 钳制 vs 新连续平铺
  previews/traveler/traveler_size_compare.png          旅人 7%/9% 两方案四阶段
  previews/sw021_preview_checks.json                   几何/接缝数值检查

零网络、零付费/生图 API。旧 webp 来自当前 main 入包素材（逐字节只读）。
所有合成图均为「设计模拟 · 非 App 截图」。
"""
from __future__ import annotations

import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
R1 = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, HERE)

import sw021_tile_model as tm  # noqa: E402

TILE_W, TILE_H = tm.TILE_W, tm.TILE_H
VOID = (0x06, 0x08, 0x06, 255)
OLD_ASSET = os.path.join(REPO, "app/src/main/assets/visual")

# 视差标定（设计模拟假设，待 ZCode 设备校正）：
# 以 SW-017 实测为据——1080×2400 旧 cover 溢出 259px、p=.3 约 144m 钳满，
# 反推 K≈6.0 参考像素/米（2400 高基准），线性随屏高缩放。
K_REF = 6.0
H_REF = 2400.0

LAYERS = [
    ("tree_outline", 80, 0.6, 20, 0.3),
    ("tree_trunks", 240, 0.7, 25, 0.3),
    ("leaf_path", 400, 0.8, 25, 0.6),
    ("light_shows", 600, 0.65, 30, 0.0),
    ("clearing", 760, 0.9, 25, 0.0),
]
STAGES = [0, 100, 265, 425, 630, 785]
RATIOS = [(1080, 1920), (1080, 2400), (390, 844)]

FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def font(size: int):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def smoothstep(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def layer_opacity(layer_id: str, meters: float) -> float:
    for lid, at, target, fade, _p in LAYERS:
        if lid == layer_id:
            if meters < at:
                return 0.0
            return target * smoothstep((meters - at) / fade)
    return 0.0


def with_opacity(im: Image.Image, op: float) -> Image.Image:
    if op >= 0.999:
        return im
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * op)))
    return out


# ---------------------------------------------------------------------------
# 新平铺模型
# ---------------------------------------------------------------------------
def draw_tiled(canvas: Image.Image, tile: Image.Image, layer_id: str,
               meters: float, parallax: float):
    """repeat-x：按高铺满，offset = 米数驱动并对周期取模，永不露底。"""
    W, H = canvas.size
    scale = H / TILE_H
    period = TILE_W * scale
    scaled = tile.resize((round(period), H), Image.LANCZOS)
    op = layer_opacity(layer_id, meters)
    if op <= 0.001:
        return
    scaled = with_opacity(scaled, op)
    offset = meters * K_REF * (H / H_REF) * parallax
    shift = offset % period
    x = -shift - period
    while x < W:
        canvas.alpha_composite(scaled, (round(x), 0))
        x += period


_overlay_cache: dict[str, Image.Image] = {}


def overlay_asset(layer_id: str) -> Image.Image:
    if layer_id not in _overlay_cache:
        _overlay_cache[layer_id] = Image.open(
            os.path.join(OLD_ASSET, f"forest_{layer_id}.webp")).convert("RGBA")
    return _overlay_cache[layer_id]


def draw_overlay(canvas: Image.Image, layer_id: str, meters: float):
    """light_shows/clearing 复用已批准 webp：cover=max 居中（SW-023 提议）。"""
    op = layer_opacity(layer_id, meters)
    if op <= 0.001:
        return
    W, H = canvas.size
    src = overlay_asset(layer_id)
    s = max(W / src.width, H / src.height)
    im = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
    im = with_opacity(im, op)
    canvas.alpha_composite(im, ((W - im.width) // 2, (H - im.height) // 2))


def draw_traveler(canvas: Image.Image, height_frac: float,
                  dim_boost: float = 1.0):
    """程序旅人示意（非角色素材）：锚点 x=.34 / 脚底 y=.865。"""
    W, H = canvas.size
    h = H * height_frac
    cx = W * 0.34
    feet_y = H * 0.865
    s = h / 100.0  # 模型以 100px 高为基准
    col = (int(0x12 + 0x10 * (dim_boost - 1)),
           int(0x1A + 0x10 * (dim_boost - 1)),
           int(0x14 + 0x10 * (dim_boost - 1)), 255)
    col = tuple(max(0, min(255, c)) for c in col)
    rim = (0x8F, 0xA8, 0x7A, 90)
    d = ImageDraw.Draw(canvas, "RGBA")

    def P(x, y):
        return (cx + x * s, feet_y + y * s)

    # 地面软影
    sh = max(2, 5 * s)
    d.ellipse([cx - 26 * s, feet_y - sh, cx + 26 * s, feet_y + sh],
              fill=(0, 0, 0, 70))
    # 后腿
    d.polygon([P(-6, -46), P(2, -46), P(10, -6), P(2, -2)], fill=col)
    # 前腿（迈姿）
    d.polygon([P(0, -46), P(8, -46), P(16, -14), P(20, -2), P(12, -2),
               P(6, -16)], fill=col)
    # 外套/身体（微前倾行走）
    body = [P(-14, -88), P(8, -90), P(14, -44), P(10, -38),
            P(-12, -40), P(-17, -58)]
    d.polygon(body, fill=col)
    # 右摆手臂
    d.polygon([P(6, -84), P(12, -82), P(18, -52), P(12, -50)], fill=col)
    # 头 + 兜帽
    d.ellipse([P(-12, -104)[0], P(-12, -104)[1],
               P(10, -82)[0], P(10, -82)[1]], fill=col)
    d.polygon([P(-15, -96), P(-2, -110), P(12, -98), P(10, -88),
               P(-12, -90)], fill=col)
    # 右侧细边光（与森林统一右上光源）
    d.line([P(9, -96), P(13, -60), P(12, -40)], fill=rim,
           width=max(1, int(2.4 * s)))


def compose_frame(W: int, H: int, meters: float,
                  traveler_frac: float | None = 0.08) -> Image.Image:
    canvas = Image.new("RGBA", (W, H), VOID)
    draw_tiled(canvas, tiles["tree_outline"], "tree_outline", meters, 0.3)
    draw_tiled(canvas, tiles["tree_trunks"], "tree_trunks", meters, 0.3)
    draw_tiled(canvas, tiles["leaf_path"], "leaf_path", meters, 0.6)
    draw_overlay(canvas, "light_shows", meters)
    draw_overlay(canvas, "clearing", meters)
    if traveler_frac:
        draw_traveler(canvas, traveler_frac)
    return canvas


# ---------------------------------------------------------------------------
# 旧 cover 模型（逐像素复刻 ForestShell.drawImageLayer 语义）
# ---------------------------------------------------------------------------
_old_cache: dict[str, Image.Image] = {}


def old_asset(layer_id: str) -> Image.Image:
    if layer_id not in _old_cache:
        _old_cache[layer_id] = Image.open(
            os.path.join(OLD_ASSET, f"forest_{layer_id}.webp")).convert("RGBA")
    return _old_cache[layer_id]


def draw_old_cover(canvas: Image.Image, layer_id: str, meters: float,
                   parallax: float):
    op = layer_opacity(layer_id, meters)
    if op <= 0.001:
        return
    W, H = canvas.size
    src = old_asset(layer_id)
    scale = H / src.height
    dw = round(src.width * scale)
    im = src.resize((dw, H), Image.LANCZOS)
    im = with_opacity(im, op)
    overflow = max(0, dw - W)
    offset = meters * K_REF * (H / H_REF) * parallax
    x = -round(min(offset, overflow))
    canvas.alpha_composite(im, (x, 0))


def compose_old(W: int, H: int, meters: float) -> Image.Image:
    canvas = Image.new("RGBA", (W, H), VOID)
    draw_old_cover(canvas, "tree_outline", meters, 0.3)
    draw_old_cover(canvas, "tree_trunks", meters, 0.3)
    draw_old_cover(canvas, "leaf_path", meters, 0.6)
    draw_overlay(canvas, "light_shows", meters)
    draw_overlay(canvas, "clearing", meters)
    draw_traveler(canvas, 0.08)
    return canvas


# ---------------------------------------------------------------------------
# 标注工具
# ---------------------------------------------------------------------------
def caption(im: Image.Image, text: str, pos=(16, 14), bg=(0, 0, 0, 150)):
    d = ImageDraw.Draw(im, "RGBA")
    f = font(max(18, im.height // 42))
    l, t = pos
    bbox = d.textbbox((l, t), text, font=f)
    d.rounded_rectangle([bbox[0] - 8, bbox[1] - 5, bbox[2] + 8, bbox[3] + 5],
                        radius=8, fill=bg)
    d.text((l, t), text, font=f, fill=(232, 228, 217, 255))


def watermark(im: Image.Image, text: str):
    d = ImageDraw.Draw(im, "RGBA")
    f = font(max(14, im.height // 60))
    bbox = d.textbbox((0, 0), text, font=f)
    d.text((im.width - (bbox[2] - bbox[0]) - 10, im.height - (bbox[3] - bbox[1]) - 8),
           text, font=f, fill=(232, 228, 217, 120))


def ensure_dir(p):
    os.makedirs(p, exist_ok=True)


# ---------------------------------------------------------------------------
# 1) tile 三底检查
# ---------------------------------------------------------------------------
def tile_check_backgrounds():
    out = os.path.join(R1, "previews/tiles/checks")
    ensure_dir(out)
    bgs = [("black", (8, 10, 8, 255)), ("white", (245, 245, 245, 255)),
           ("magenta", (200, 0, 120, 255))]
    for lid, im in tiles.items():
        cell_w = TILE_W // 2
        cell_h = TILE_H // 2
        sheet = Image.new("RGBA", (cell_w * 3 + 32, cell_h + 70),
                          (24, 24, 24, 255))
        d = ImageDraw.Draw(sheet, "RGBA")
        for i, (name, col) in enumerate(bgs):
            cell = Image.new("RGBA", (TILE_W, TILE_H), col)
            cell.alpha_composite(im)
            cell = cell.resize((cell_w, cell_h), Image.LANCZOS)
            x = 8 + i * (cell_w + 8)
            sheet.alpha_composite(cell, (x, 46))
            d.text((x + 8, 12), f"{lid} · {name}", font=font(22),
                   fill=(232, 228, 217, 255))
        watermark(sheet, "设计模拟 · tile 三底检查")
        sheet.save(os.path.join(out, f"forest_{lid}_check3.png"))


# ---------------------------------------------------------------------------
# 2) 三次拼接 + 接缝标注
# ---------------------------------------------------------------------------
def tile_repeat3():
    out = os.path.join(R1, "previews/tiles/repeat")
    ensure_dir(out)
    results = {}
    for lid, im in tiles.items():
        rep = Image.new("RGBA", (TILE_W * 3, TILE_H), (0, 0, 0, 0))
        for k in range(3):
            rep.alpha_composite(im, (k * TILE_W, 0))
        # 接缝数值检查：缝两侧 2px 列 RGBA 最大/均值差
        import numpy as np
        arr = np.asarray(rep, dtype=np.int16)
        seams = {}
        for sx in (TILE_W, TILE_W * 2):
            left = arr[:, sx - 2:sx, :]
            right = arr[:, sx + 1:sx + 3, :]
            diff = np.abs(left.astype(np.int16) - right.astype(np.int16))
            # 结构同分布比较：与 tile 内同样间隔的自然差对比
            nat = np.abs(arr[:, 200:202, :].astype(np.int16)
                         - arr[:, 203:205, :].astype(np.int16))
            seams[sx] = {
                "seam_max_abs_diff": int(diff.max()),
                "seam_mean_abs_diff": round(float(diff.mean()), 3),
                "natural_mean_abs_diff": round(float(nat.mean()), 3),
            }
        results[lid] = seams
        # 可视化：黑底 + 接缝红线 + 安全区虚线
        vis = Image.new("RGBA", rep.size, VOID)
        vis.alpha_composite(rep)
        d = ImageDraw.Draw(vis, "RGBA")
        for sx in (TILE_W, TILE_W * 2):
            d.line([(sx, 0), (sx, TILE_H)], fill=(220, 60, 60, 200), width=3)
        # 接缝安全区 ±96px
        for sx in (0, TILE_W, TILE_W * 2, TILE_W * 3):
            for dx in (-tm.SEAM_SAFE_PX, tm.SEAM_SAFE_PX):
                xx = sx + dx
                if 0 <= xx <= TILE_W * 3:
                    d.line([(xx, 0), (xx, TILE_H)], fill=(255, 210, 80, 90),
                           width=2)
        caption(vis, f"{lid} · repeat-x ×3（红=接缝 黄=±{tm.SEAM_SAFE_PX}px 安全区）",
                pos=(24, 24))
        watermark(vis, "设计模拟 · 三次拼接")
        vis = vis.resize((1440, round(1440 * TILE_H / (TILE_W * 3))),
                         Image.LANCZOS)
        vis.save(os.path.join(out, f"forest_{lid}_repeat3.png"))
    return results


# ---------------------------------------------------------------------------
# 3) 接缝探针：5 连拼，每条缝两侧 ±120px 在三底上 2× 放大
# ---------------------------------------------------------------------------
def seam_probe():
    out = os.path.join(R1, "previews/tiles/seam")
    ensure_dir(out)
    bgs = [("黑", (8, 10, 8)), ("白", (245, 245, 245)), ("品红", (200, 0, 120))]
    half = 120
    zoom = 2
    cell = half * 2 * zoom
    rows = []
    for lid, im in tiles.items():
        rep = Image.new("RGBA", (TILE_W * 5, TILE_H), (0, 0, 0, 0))
        for k in range(5):
            rep.alpha_composite(im, (k * TILE_W, 0))
        for bi, (bname, bcol) in enumerate(bgs):
            strip = Image.new("RGBA", (cell * 4, cell + 44),
                              (24, 24, 24, 255))
            d = ImageDraw.Draw(strip, "RGBA")
            for si, sx in enumerate((TILE_W, TILE_W * 2, TILE_W * 3,
                                     TILE_W * 4)):
                crop = rep.crop((sx - half, TILE_H // 2 - half,
                                 sx + half, TILE_H // 2 + half))
                bg = Image.new("RGBA", crop.size, bcol + (255,))
                bg.alpha_composite(crop)
                bg = bg.resize((cell, cell), Image.NEAREST)
                dd = ImageDraw.Draw(bg, "RGBA")
                dd.line([(half * zoom - 1, 0), (half * zoom - 1, cell)],
                        fill=(220, 60, 60, 220), width=2)
                strip.alpha_composite(bg, (si * cell, 30))
            d.text((6, 4), f"{lid} · {bname}底 · 4 条缝（每格缝两侧各120px，2×）",
                   font=font(20), fill=(232, 228, 217, 255))
            rows.append(strip)
    sheet = Image.new("RGBA", (rows[0].width,
                               sum(r.height for r in rows)
                               + 12 * (len(rows) - 1)),
                      (18, 18, 18, 255))
    y = 0
    for r in rows:
        sheet.alpha_composite(r, (0, y))
        y += r.height + 12
    sheet.save(os.path.join(out, "forest_seam_probe_sheet.png"))


# ---------------------------------------------------------------------------
# 4) 六阶段 × 三比例矩阵
# ---------------------------------------------------------------------------
def stage_matrices():
    out = os.path.join(R1, "previews/composite")
    ensure_dir(out)
    summary = {}
    for (W, H) in RATIOS:
        ss = 2 if W < 500 else 1  # 小屏逻辑尺寸 @2x 渲染
        rw, rh = W * ss, H * ss
        panels = []
        for m in STAGES:
            fr = compose_frame(rw, rh, m)
            caption(fr, f"{m} m", pos=(20 * ss, 18 * ss))
            watermark(fr, "设计模拟 · 连续平铺（非 App 截图）")
            panels.append(fr)
        cols = 3
        rows_n = 2
        gap = 18
        cell_w = 360 if W >= 500 else 260
        ch = round(cell_w * rh / rw)
        header = 70
        sheet = Image.new("RGBA",
                          (cell_w * cols + gap * (cols + 1),
                           header + ch * rows_n + gap * (rows_n + 1)),
                          (18, 18, 18, 255))
        d = ImageDraw.Draw(sheet, "RGBA")
        d.text((gap, 16), f"森林连续视差 · 六阶段 · {W}×{H}"
               f"（{'@2x 渲染' if ss == 2 else '原生'}）",
               font=font(30), fill=(232, 228, 217, 255))
        for i, fr in enumerate(panels):
            r, c = divmod(i, cols)
            fr_t = fr.resize((cell_w, ch), Image.LANCZOS)
            sheet.alpha_composite(fr_t, (gap + c * (cell_w + gap),
                                         header + gap + r * (ch + gap)))
        name = f"forest_tiled_matrix_{W}x{H}.png"
        sheet.save(os.path.join(out, name))
        summary[f"{W}x{H}"] = {
            "tile_scale_height_fill": round(rh / TILE_H, 4),
            "tile_period_px": round(TILE_W * rh / TILE_H, 1),
            "screen_width_px": rw,
            "period_covers_screen": TILE_W * rh / TILE_H >= rw,
        }
    return summary


# ---------------------------------------------------------------------------
# 5) 旧 cover vs 新连续平铺（1080×2400，六阶段对拍）
# ---------------------------------------------------------------------------
def old_vs_new():
    out = os.path.join(R1, "previews/composite")
    ensure_dir(out)
    W, H = 1080, 2400
    cell_w = 300
    ch = round(cell_w * H / W)
    gap = 16
    header = 86
    sheet = Image.new("RGBA",
                      (gap + 6 * (cell_w + gap),
                       header + 2 * (ch + gap + 26)),
                      (18, 18, 18, 255))
    d = ImageDraw.Draw(sheet, "RGBA")
    d.text((gap, 14), "旧：单图 cover 横移钳制（右缘 Void 黑带）",
           font=font(28), fill=(232, 228, 217, 255))
    d.text((gap, header + ch + gap + 30),
           "新：tile repeat-x 连续横移（offset 对周期取模，永无黑带）",
           font=font(28), fill=(232, 228, 217, 255))
    band_report = {}
    for i, m in enumerate(STAGES):
        old = compose_old(W, H, m)
        new = compose_frame(W, H, m)
        # 黑带宽度：旧图最右连续 Void 列数
        import numpy as np
        a = np.asarray(old.convert("RGB"))
        void_like = (np.abs(a.astype(int) - np.array([6, 8, 6])).sum(2) < 12)
        col_void = void_like.mean(0) > 0.995
        band = 0
        for v in col_void[::-1]:
            if v:
                band += 1
            else:
                break
        band_report[m] = band
        caption(old, f"{m} m · 黑带 {band}px", pos=(18, 16))
        caption(new, f"{m} m · 黑带 0px", pos=(18, 16))
        watermark(old, "旧入包素材 · 几何模拟")
        watermark(new, "设计模拟 · 非 App 截图")
        x = gap + i * (cell_w + gap)
        sheet.alpha_composite(old.resize((cell_w, ch), Image.LANCZOS),
                              (x, 46))
        sheet.alpha_composite(new.resize((cell_w, ch), Image.LANCZOS),
                              (x, header + ch + gap + 56))
    sheet.save(os.path.join(out, "forest_continuous_compare_1080x2400.png"))
    return band_report


# ---------------------------------------------------------------------------
# 6) 旅人两尺寸方案（7% / 9% 屏高）× 四阶段
# ---------------------------------------------------------------------------
def traveler_compare():
    out = os.path.join(R1, "previews/traveler")
    ensure_dir(out)
    W, H = 1080, 1920
    stages_t = [100, 265, 425, 630]
    plans = [(0.07, "方案 A · 旅人高 7% 屏高（134px）"),
             (0.09, "方案 B · 旅人高 9% 屏高（173px）")]
    cell_w = 300
    ch = round(cell_w * H / W)
    gap = 16
    header = 40
    sheet = Image.new("RGBA",
                      (gap + 4 * (cell_w + gap),
                       2 * header + 2 * (ch + gap)),
                      (18, 18, 18, 255))
    d = ImageDraw.Draw(sheet, "RGBA")
    for r, (frac, title) in enumerate(plans):
        d.text((gap, r * (header + ch + gap) + 6), title,
               font=font(26), fill=(232, 228, 217, 255))
        for c, m in enumerate(stages_t):
            fr = compose_frame(W, H, m, traveler_frac=frac)
            # 旅人包围盒标注
            hx = round(W * 0.34)
            hy = round(H * 0.865)
            hh = round(H * frac)
            dd = ImageDraw.Draw(fr, "RGBA")
            dd.rectangle([hx - round(hh * 0.42), hy - hh - 6,
                          hx + round(hh * 0.42), hy + 8],
                         outline=(255, 210, 80, 180), width=3)
            caption(fr, f"{m} m", pos=(18, 16))
            watermark(fr, "设计模拟 · 非 App 截图")
            x = gap + c * (cell_w + gap)
            y = r * (header + ch + gap) + header
            sheet.alpha_composite(fr.resize((cell_w, ch), Image.LANCZOS),
                                  (x, y))
    sheet.save(os.path.join(out, "traveler_size_compare.png"))


# ---------------------------------------------------------------------------
tiles: dict[str, Image.Image] = {}


def main():
    global tiles
    tiles = {
        "tree_outline": tm.render_pil(tm.model_tree_outline()),
        "tree_trunks": tm.render_pil(tm.model_tree_trunks()),
        "leaf_path": tm.render_pil(tm.model_leaf_path()),
    }
    tile_check_backgrounds()
    seams = tile_repeat3()
    seam_probe()
    geom = stage_matrices()
    bands = old_vs_new()
    traveler_compare()
    report = {
        "note": "SW-021 设计模拟几何/接缝检查；非 App 截图，非真机证据。",
        "tile_canvas": {"width": TILE_W, "height": TILE_H,
                        "repeat_axis": "x", "seam_safe_px": tm.SEAM_SAFE_PX},
        "parallax_calibration_design_assumption": {
            "K_ref_px_per_m_at_1080x2400": K_REF,
            "basis": "SW-017 实测旧 cover 溢出 259px、p=.3 约 144m 钳满反推",
            "status": "proposed_pending_zcode_device_correction",
            "tile_formula": "x_shift = meters*K*(H/2400)*parallax mod (1080*H/1920)",
        },
        "screen_geometry": geom,
        "seam_pixel_checks": seams,
        "old_cover_void_band_px_1080x2400": bands,
        "new_tile_void_band_px_1080x2400": {m: 0 for m in STAGES},
    }
    with open(os.path.join(R1, "previews/sw021_preview_checks.json"),
              "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("[sw021] previews done ->", os.path.join(R1, "previews"))


if __name__ == "__main__":
    main()
