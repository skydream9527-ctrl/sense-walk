#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SW-017 R1 · 森林 800m 双模式「应用上下文设计模拟」生成器。

定位（任务书 SW-017）：只做应用验图参照，不重画生产美术、不新增生产层、不调付费 API。
合成素材一律只读当前 main 已验收入包的生产图（MiniMax 交付、SW-010 验收）：
  app/src/main/assets/visual/forest_{tree_outline,tree_trunks,leaf_path,light_shows,clearing}.webp
  （768×1376 RGBA；commit a235bf1 / 1baef18 / a1df0e2 入包）
渲染语义逐行对齐当前 main 源码（base 422451e）：
  app/src/main/assets/scenes/forest.json            相位 at/target/fade/parallax
  app/.../domain/phase/PhaseScheduler.kt            opacity=toOpacity×smoothstep((m-at)/fade)
  app/.../ui/session/ForestShell.kt                 cover 按高铺满、视差钳制溢出宽、旅人 .34/.865
  app/.../ui/session/SessionScreen.kt               虚走：上55%米数/控件，下45%浮动摇杆，卡片文案
  app/.../ui/session/RealWalkContent.kt             实走：下45%状态文案（无摇杆）
  app/.../ui/session/Joystick.kt                    底座56dp/拇指22dp/甜点0.45–0.65 需 rhythmHint
  app/.../ui/session/AbandonControl.kt              长按1.5s + 72dp 进度条
  app/.../ui/theme/Theme.kt                         SenseBlack/OnSurface/Muted/AccentSoft
输出全部带「设计模拟」角标：不是 Android 截图，不是真机停走/计步证据。
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent            # .../SW-017/r1/source
R1 = HERE.parent                                   # .../SW-017/r1
VISUAL = R1.parent.parent                          # .../05-visual-design
REPO = VISUAL.parent.parent                        # 仓库根
ASSETS = REPO / "app/src/main/assets"
PREV = R1 / "previews"
EVID = REPO / "docs/collaboration/evidence"

FONT_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
]
FONT_PATH = next(p for p in FONT_CANDIDATES if os.path.exists(p))

# ---- 主题（Theme.kt / ScenePalette.kt 逐字节取值） -----------------------------
VOID = (6, 8, 6)                 # 0xFF060806
SENSE_BLACK = (10, 10, 10)       # 页面 Box 底色（ForestShell 自身先画 void）
ON_SURFACE = (232, 228, 217)     # 0xFFE8E4D9
MUTED = (138, 134, 128)          # 0xFF8A8680
ACCENT = (168, 197, 160)         # 0xFFA8C5A0
TRAVELER = (122, 133, 124)       # 0xFF7A857C
BOARD_BG = (10, 13, 11)
WARN = (224, 138, 120)
WARM = (206, 196, 166)

# ---- forest.json 冻结相位（layer, parallax, atMeters, toOpacity, fadeMeters） ---
LAYERS = [
    ("tree_outline", 0.3, 80, 0.60, 20),
    ("tree_trunks",  0.3, 240, 0.70, 25),
    ("leaf_path",    0.6, 400, 0.80, 25),
    ("light_shows",  0.0, 600, 0.65, 30),
    ("clearing",     0.0, 760, 0.90, 25),
]
STAGE_METERS = [0, 100, 265, 425, 630, 785]
# 任务书指定三比例；(输出px, 输出px, density, 内部渲染倍率, 标签)
# 390×844 是 dp 点坐标框：真机物理像素≈1170×2532（@3x），固定 px 几何
# （旅人 74px、视差 6px/m）必须在物理空间渲染后降采样，否则比例失真。
DEVICES = [
    # (pxW, pxH, density, render_scale, 标签)
    (1080, 1920, 3.0, 1, "基准 1080×1920（9:16，d≈3）"),
    (390, 844, 3.0, 3, "小屏 390×844 点（物理 1170×2532 @3x 渲染后降采样）"),
    (1080, 2400, 3.0, 1, "长屏 1080×2400（20:9，d≈3，同作者证据）"),
]
PX_PER_M = 6.0  # ForestShell.PX_PER_METER

_cache: dict[str, Image.Image] = {}


def font(size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size=max(9, int(round(size))))


def smoothstep(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def layer_image(layer_id: str) -> Image.Image:
    if layer_id not in _cache:
        _cache[layer_id] = Image.open(ASSETS / "visual" / f"forest_{layer_id}.webp").convert("RGBA")
    return _cache[layer_id]


# =========================================================================== 场景
class Device:
    def __init__(self, w: int, h: int, d: float, tag: str, fs: float = 1.0):
        self.w, self.h, self.d, self.tag, self.fs = w, h, d, tag, fs

    def dp(self, v: float) -> int:
        # dp 只随 density，不随系统 fontScale 变化（与真实 Android 一致）
        return int(round(v * self.d))

    def sp(self, v: float) -> int:
        return int(round(v * self.d * self.fs))


def layer_opacity(layer_id: str, meters: int) -> float:
    for lid, _, at, target, fade in LAYERS:
        if lid == layer_id:
            return target * smoothstep((meters - at) / fade)
    return 0.0


def composite(dev: Device, meters: int, s_pos: float | None = None,
              reduce_motion: bool = False, with_traveler: bool = True) -> Image.Image:
    """复刻 ForestShell.drawImageLayer：按高 cover，视差= sPos×parallax×6，钳制溢出宽。"""
    w, h = w0, h0 = dev.w, dev.h
    canvas = Image.new("RGBA", (w, h), VOID + (255,))
    if s_pos is None:
        s_pos = float(meters)  # 行走常态：sPos≈累计米
    src0 = layer_image("tree_outline")
    scale = h / src0.height
    dst_w = src0.width * scale
    overflow = max(0.0, dst_w - w)
    for layer_id, parallax, _, _, _ in LAYERS:
        a = layer_opacity(layer_id, meters)
        if a <= 0.01:
            continue
        src = layer_image(layer_id).resize((round(dst_w), h), Image.LANCZOS)
        if reduce_motion or parallax <= 0:
            off = 0.0
        else:
            off = min(s_pos * parallax * PX_PER_M, overflow)
        alpha = src.split()[3].point(lambda v: int(v * a))
        src.putalpha(alpha)
        canvas.alpha_composite(src, (int(-off), 0))
    if with_traveler:
        draw_traveler(canvas, w * 0.34, h * 0.865)
    return canvas


def draw_traveler(img: Image.Image, cx: float, ground_y: float) -> None:
    """IDLE 姿态，几何逐值对齐 ForestShell.drawTraveler（原始 Compose px，不乘 dp）。"""
    d = ImageDraw.Draw(img)
    cx, gy = int(cx), int(ground_y)
    col = TRAVELER + (255,)
    body_bottom, body_top = gy - 14, gy - 74
    d.line([(cx - 2, body_bottom), (cx - 10, gy)], fill=col, width=6)
    d.line([(cx + 2, body_bottom), (cx + 10, gy)], fill=col, width=6)
    d.rounded_rectangle([cx - 10, body_top, cx + 10, body_bottom], radius=10, fill=col)
    d.ellipse([cx - 9, body_top - 21, cx + 9, body_top - 3], fill=col)


# =========================================================================== Chrome
def _txt(d, xy, text, fnt, fill, anchor="la", shadow=True):
    x, y = xy
    if shadow:
        d.text((x + 1, y + 2), text, font=fnt, fill=(0, 0, 0, 150), anchor=anchor)
    d.text((x, y), text, font=fnt, fill=fill, anchor=anchor)


def overlay_for(base: Image.Image) -> Image.Image:
    """PIL ImageDraw 直接替换 RGBA 而非 source-over；所有半透明 UI 先画在透明层再合成。"""
    return Image.new("RGBA", base.size, (0, 0, 0, 0))


def draw_status_bar(d, dev: Device):
    """示意状态栏（非精确系统 UI，仅帮助核对顶部避让；所有图均带设计模拟角标）。"""
    w = dev.w
    y = dev.dp(14)
    _txt(d, (dev.dp(24), y), "2:28", font(dev.sp(14)), (232, 228, 217, 235), shadow=False)
    ix = w - dev.dp(28)
    # 电池
    d.rounded_rectangle([ix - dev.dp(26), y - 2, ix - dev.dp(4), y + dev.dp(16)],
                        radius=3, outline=(232, 228, 217, 220), width=2)
    d.rectangle([ix - dev.dp(3), y + 3, ix, y + dev.dp(11)], fill=(232, 228, 217, 220))
    # 信号三角 + wifi 弧（极简示意）
    d.polygon([(ix - dev.dp(64), y + dev.dp(14)), (ix - dev.dp(48), y + dev.dp(14)),
               (ix - dev.dp(56), y + 2)], fill=(232, 228, 217, 220))
    d.arc([ix - dev.dp(44), y - 2, ix - dev.dp(20), y + dev.dp(18)], 200, 340,
          fill=(232, 228, 217, 220), width=2)


def draw_home_indicator(d, dev: Device):
    w, h = dev.w, dev.h
    y = h - dev.dp(18)
    d.rounded_rectangle([w // 2 - dev.dp(72), y, w // 2 + dev.dp(72), y + dev.dp(4)],
                        radius=dev.dp(2), fill=(255, 255, 255, 200))


def sim_badge(d, dev: Device, extra: str = ""):
    txt = "设计模拟 · 非 App 截图" + (f" · {extra}" if extra else "")
    x0, y0 = dev.dp(10), dev.dp(40)
    pad = dev.dp(6)
    max_w = dev.w - x0 - dev.dp(10) - pad * 2
    fs = dev.sp(11)
    f = font(fs)
    while fs > 14 and d.textlength(txt, font=f) > max_w:
        fs -= 1
        f = font(fs)
    d.rounded_rectangle([x0, y0, x0 + d.textlength(txt, font=f) + pad * 2,
                         y0 + f.size + pad * 2 - 3],
                        radius=dev.dp(6), fill=(0, 0, 0, 128),
                        outline=tuple(ACCENT) + (190,), width=1)
    _txt(d, (x0 + pad, y0 + pad - 2), txt, f, tuple(ACCENT) + (255,), shadow=False)


def draw_top_chrome(d, dev: Device, meters: int | None, paused_available: bool = True):
    """SessionScreen/RealWalkContent 共用：上 55% 轻触米数 + 右上控件。"""
    # 米数列：top=64dp 居中
    cx = dev.w // 2
    if meters is None:
        _txt(d, (cx, dev.dp(64)), "轻触查看米数", font(dev.sp(11)),
             tuple(MUTED) + (128,), anchor="ma")
    else:
        _txt(d, (cx, dev.dp(60)), f"{meters} m", font(dev.sp(45)),
             tuple(ON_SURFACE) + (230,), anchor="ma")
        _txt(d, (cx, dev.dp(122)), "已走", font(dev.sp(11)),
             tuple(MUTED) + (255,), anchor="ma")
    # 右上控件列：top=48dp end=16dp spacing=8dp
    rx = dev.w - dev.dp(16)
    y = dev.dp(48)
    # AbandonControl：padding h16/v10 + labelMedium(13sp) + 进度条(top6,72×3dp)
    f_btn = font(dev.sp(13))
    tw = d.textlength("长按放弃", font=f_btn)
    box_w = int(tw) + dev.dp(32)
    box_h = dev.dp(20) + f_btn.size + dev.dp(9) + dev.dp(3)
    d.rounded_rectangle([rx - box_w, y, rx, y + box_h], radius=dev.dp(20),
                        fill=(255, 255, 255, 15))
    _txt(d, (rx - box_w // 2, y + dev.dp(10) - 1), "长按放弃", f_btn,
         tuple(MUTED) + (255,), anchor="ma")
    by = y + dev.dp(10) + f_btn.size + dev.dp(6)
    d.rounded_rectangle([rx - box_w // 2 - dev.dp(36), by,
                         rx - box_w // 2 + dev.dp(36), by + dev.dp(3)],
                        radius=2, fill=(255, 255, 255, 30))
    y += box_h + dev.dp(8)
    tw2 = d.textlength("暂停", font=f_btn)
    bw2 = int(tw2) + dev.dp(32)
    bh2 = dev.dp(20) + f_btn.size
    if paused_available:
        d.rounded_rectangle([rx - bw2, y, rx, y + bh2], radius=dev.dp(20),
                            fill=(255, 255, 255, 15))
        _txt(d, (rx - bw2 // 2, y + dev.dp(10) - 1), "暂停", f_btn,
             tuple(MUTED) + (255,), anchor="ma")


def dashed_rect(d, box, fill, dash=16, width=2):
    x0, y0, x1, y1 = box
    for x in range(x0, x1, dash * 2):
        d.line([(x, y0), (min(x + dash, x1), y0)], fill=fill, width=width)
        d.line([(x, y1), (min(x + dash, x1), y1)], fill=fill, width=width)
    for y in range(y0, y1, dash * 2):
        d.line([(x0, y), (x0, min(y + dash, y1))], fill=fill, width=width)
        d.line([(x1, y), (x1, min(y + dash, y1))], fill=fill, width=width)


def draw_zone_labels(d, dev: Device, mode: str):
    top = int(dev.h * 0.55)
    if mode == "virtual":
        dashed_rect(d, [3, top, dev.w - 3, dev.h - 3], tuple(ACCENT) + (150,))
        _txt(d, (dev.dp(10), top + dev.dp(6)), "下 45% 浮动摇杆操作区（仅按住时出现）",
             font(dev.sp(11)), tuple(ACCENT) + (235,))
    else:
        dashed_rect(d, [3, top, dev.w - 3, dev.h - 3], tuple(WARM) + (150,))
        _txt(d, (dev.dp(10), top + dev.dp(6)),
             "下 45% 实走状态区（无摇杆 · 计步由前台服务驱动）",
             font(dev.sp(11)), tuple(WARM) + (235,))


def draw_joystick(d, dev: Device, cx_frac=0.50, cy_frac=0.80, sweet=True, hint=True):
    base_r = dev.dp(56)
    thumb_r = dev.dp(22)
    cx, cy = int(dev.w * cx_frac), int(dev.h * cy_frac)
    d.ellipse([cx - base_r, cy - base_r, cx + base_r, cy + base_r],
              fill=(255, 255, 255, 26))
    d.ellipse([cx - base_r, cy - base_r, cx + base_r, cy + base_r],
              outline=(255, 255, 255, 41), width=max(2, dev.dp(1)))
    tx = cx + int(base_r * (0.55 if sweet else 0.9))
    col = tuple(ACCENT) + (217,) if (sweet and hint) else (255, 255, 255, 115)
    d.ellipse([tx - thumb_r, cy - thumb_r, tx + thumb_r, cy + thumb_r], fill=col)
    _txt(d, (cx, cy + base_r + dev.dp(12)),
         "按住向右推 · 甜点 0.45–0.65（需 rhythmHint 才变绿）",
         font(dev.sp(11)), tuple(ON_SURFACE) + (210,), anchor="ma")


def draw_real_status(d, dev: Device, state: str):
    title = {
        "ready": "收进口袋，走吧",
        "slow": "在走了 · 手机收好",
        "good": "走得刚刚好 · 就这样",
        "paused": "已暂停 · 走动时点「继续走」",
    }[state]
    # Column 垂直居中于下45%区，bottom=96dp
    cx = dev.w // 2
    cy = int(dev.h * 0.55 + (dev.h * 0.45 - dev.dp(96)) / 2)
    _txt(d, (cx, cy - dev.dp(16)), title, font(dev.sp(16)),
         tuple(ON_SURFACE) + (217,), anchor="mm")
    _txt(d, (cx, cy + dev.dp(20)), "森林", font(dev.sp(11)),
         tuple(MUTED) + (179,), anchor="mm")


def render_frame(dev: Device, meters: int, mode: str, *, zones=True, joystick=True,
                 real_state="good", show_meters=True, reduce_motion=False,
                 s_pos: float | None = None, chrome=True, status_bar=True,
                 home=True) -> Image.Image:
    img = composite(dev, meters, s_pos=s_pos, reduce_motion=reduce_motion)
    ov = overlay_for(img)
    d = ImageDraw.Draw(ov)
    if chrome:
        draw_top_chrome(d, dev, meters if (show_meters and meters >= 400) else None)
    if zones:
        draw_zone_labels(d, dev, mode)
    if mode == "virtual" and joystick:
        draw_joystick(d, dev)
    if mode == "real":
        draw_real_status(d, dev, real_state)
    if status_bar:
        draw_status_bar(d, dev)
    if home:
        draw_home_indicator(d, dev)
    sim_badge(d, dev)
    img.alpha_composite(ov)
    return img


# =========================================================================== 状态图
def state_paused(dev: Device) -> Image.Image:
    img = composite(dev, 785)
    ov = overlay_for(img)
    d = ImageDraw.Draw(ov)
    draw_top_chrome(d, dev, 785, paused_available=False)
    cx = dev.w // 2
    y = int(dev.h * 0.40)
    _txt(d, (cx, y), "已暂停", font(dev.sp(20)), tuple(ON_SURFACE) + (255,), anchor="ma")
    _txt(d, (cx, y + dev.dp(34)), "点「继续走」后，摇杆重新给输入才会前进",
         font(dev.sp(12)), tuple(MUTED) + (255,), anchor="ma")
    bx0, bx1 = cx - dev.w // 2 + dev.dp(48), cx + dev.w // 2 - dev.dp(48)
    by0, by1 = y + dev.dp(60), y + dev.dp(60) + dev.dp(52)
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=dev.dp(14), fill=tuple(ACCENT) + (255,))
    _txt(d, (cx, (by0 + by1) // 2), "继续走", font(dev.sp(16)),
         SENSE_BLACK + (255,), anchor="mm", shadow=False)
    draw_status_bar(d, dev)
    draw_home_indicator(d, dev)
    sim_badge(d, dev, "暂停卡片")
    img.alpha_composite(ov)
    return img


def _center_card(d, dev, lines, y_frac=0.46, bg_alpha=26, pad_frac=0.12):
    w = dev.w
    x0, x1 = int(w * pad_frac), int(w * (1 - pad_frac))
    lh = dev.dp(30)
    y0 = int(dev.h * y_frac) - (lh * len(lines)) // 2 - dev.dp(18)
    y1 = y0 + lh * len(lines) + dev.dp(36)
    d.rounded_rectangle([x0, y0, x1, y1], radius=dev.dp(16), fill=(255, 255, 255, bg_alpha))
    yy = y0 + dev.dp(18)
    for text, sp, col in lines:
        _txt(d, (w // 2, yy), text, font(dev.sp(sp)), col + (255,), anchor="ma")
        yy += lh
    return y0, y1


def state_stabilize_hint(dev: Device) -> Image.Image:
    # 触发点：首坎 gap 240–270 前 APPROACH_METERS=3m，约 237m（此时 tree_outline 满显）
    img = composite(dev, 237)
    ov = overlay_for(img)
    d = ImageDraw.Draw(ov)
    draw_top_chrome(d, dev, None)
    _, y1 = _center_card(d, dev, [("慢一点，站稳再跳。", 16, ON_SURFACE)],
                          y_frac=0.50, bg_alpha=26, pad_frac=0.12)
    note_f = font(dev.sp(10))
    for i, line in enumerate([
        "首局一次 · 约 3s 自动消失 · 触发≈首坎前 3m（237m）",
        "出现/消失时序待真机同步取证（现有 hint-shown 截图无卡片）",
    ]):
        _txt(d, (dev.w // 2, y1 + dev.dp(16) + i * dev.dp(20)), line, note_f,
             tuple(MUTED) + (230,), anchor="ma")
    draw_status_bar(d, dev)
    draw_home_indicator(d, dev)
    sim_badge(d, dev, "站稳提示")
    img.alpha_composite(ov)
    return img


def state_intro(dev: Device) -> Image.Image:
    img = composite(dev, 0)
    ov = overlay_for(img)
    d = ImageDraw.Draw(ov)
    draw_top_chrome(d, dev, None)
    # 对齐 SessionScreen：margin 36dp、alpha .06、radius16、padding20dp；
    # bodyLarge×2 + 8dp + bodySmall×2，卡片高度按内容自适应后整体居中
    x0, x1 = dev.dp(36), dev.w - dev.dp(36)
    card_h = dev.dp(20 + 26 * 2 + 8 + 20 * 2 + 20)
    y0 = dev.h // 2 - card_h // 2
    y1 = y0 + card_h
    d.rounded_rectangle([x0, y0, x1, y1], radius=dev.dp(16), fill=(255, 255, 255, 15))
    cx = dev.w // 2
    ty = y0 + dev.dp(20)
    _txt(d, (cx, ty), "推满不会更快。", font(dev.sp(16)),
         tuple(ON_SURFACE) + (255,), anchor="ma")
    ty += dev.dp(26)
    _txt(d, (cx, ty), "松一点，找舒服的节奏。", font(dev.sp(16)),
         tuple(ON_SURFACE) + (255,), anchor="ma")
    ty += dev.dp(26) + dev.dp(8)
    _txt(d, (cx, ty), "走着走着，声音和风景会慢慢出现。", font(dev.sp(12)),
         tuple(MUTED) + (255,), anchor="ma")
    ty += dev.dp(20)
    _txt(d, (cx, ty), "（轻点此处关闭）", font(dev.sp(12)),
         tuple(MUTED) + (255,), anchor="ma")
    draw_status_bar(d, dev)
    draw_home_indicator(d, dev)
    sim_badge(d, dev, "首局说明卡片")
    img.alpha_composite(ov)
    return img


def state_abandon(dev: Device) -> Image.Image:
    img = composite(dev, 425).filter(ImageFilter.GaussianBlur(1.4))
    img.alpha_composite(Image.new("RGBA", img.size, (0, 0, 0, 96)))
    ov = overlay_for(img)
    d = ImageDraw.Draw(ov)
    w, h = dev.w, dev.h
    x0, x1 = int(w * 0.07), int(w * 0.93)
    y0, y1 = int(h * 0.30), int(h * 0.55)
    d.rounded_rectangle([x0, y0, x1, y1], radius=dev.dp(20), fill=(26, 30, 27, 252))
    _txt(d, (x0 + dev.dp(24), y0 + dev.dp(28)), "要放弃这段路吗？", font(dev.sp(20)),
         tuple(ON_SURFACE) + (255,))
    _txt(d, (x0 + dev.dp(24), y0 + dev.dp(84)), "现在停下来，这一局就到这里了。",
         font(dev.sp(13)), tuple(MUTED) + (255,))
    _txt(d, (x0 + dev.dp(24), y0 + dev.dp(116)), "想走的时候随时再来。",
         font(dev.sp(13)), tuple(MUTED) + (255,))
    # Material TextButton 行：confirm 在右、dismiss 在左，底部对齐
    by1 = y1 - dev.dp(18)
    _txt(d, (x1 - dev.dp(24), by1), "继续走", font(dev.sp(14)),
         tuple(ACCENT) + (255,), anchor="ra")
    _txt(d, (x1 - dev.dp(130), by1), "放弃这段路", font(dev.sp(14)),
         tuple(MUTED) + (255,), anchor="ra")
    draw_status_bar(d, dev)
    sim_badge(d, dev, "放弃确认（Material 对话框示意）")
    img.alpha_composite(ov)
    return img


def state_large_font(dev: Device) -> Image.Image:
    """系统 fontScale≈1.5（app 无独立字号开关，跟随系统）；dp 不变仅 sp 放大，检查文案避让。"""
    big = Device(dev.w, dev.h, dev.d, dev.tag + " · fontScale≈1.5", fs=1.5)
    img = composite(big, 785)
    ov = overlay_for(img)
    d = ImageDraw.Draw(ov)
    draw_top_chrome(d, big, 785)
    draw_real_status(d, big, "good")
    draw_status_bar(d, big)
    draw_home_indicator(d, big)
    sim_badge(d, big, "大字号 ×1.5")
    img.alpha_composite(ov)
    return img


def state_reduce_motion(dev: Device) -> Image.Image:
    """reduceMotion：视差/起伏冻结；对比行走常态（视差已钳制在溢出宽）。

    dev 给输出点尺寸（390×844）；帧按 @3x 物理空间渲染后降采样，保证固定 px 几何比例正确。
    """
    rdev = Device(dev.w * 3, dev.h * 3, dev.d, dev.tag + " @3x")
    rest = render_frame(rdev, 785, "virtual", reduce_motion=True, joystick=False,
                        zones=False, home=True).resize((dev.w, dev.h), Image.LANCZOS)
    walk = render_frame(rdev, 785, "virtual", reduce_motion=False, joystick=False,
                        zones=False, home=True).resize((dev.w, dev.h), Image.LANCZOS)
    pad, gap = 30, 26
    W = pad * 2 + dev.w * 2 + gap
    H = 250 + dev.h + 80
    board = Image.new("RGBA", (W, H), BOARD_BG + (255,))
    ov = overlay_for(board)
    d = ImageDraw.Draw(ov)
    _txt(d, (pad, 26), "reduceMotion 代表图 · 390×844 · 785m", font(36),
         tuple(ON_SURFACE) + (255,))
    _txt(d, (pad, 82), "左：开启动效减弱 → 视差横移/旅人起伏冻结（sPos 偏移=0）",
         font(23), tuple(ACCENT) + (255,))
    _txt(d, (pad, 118), "右：正常行走 785m → 视差早已钳制在右溢出端（1170 物理宽溢出约 243px）",
         font(23), tuple(WARM) + (255,))
    y = 160
    board.alpha_composite(rest, (pad, y))
    board.alpha_composite(walk, (pad + dev.w + gap, y))
    _txt(d, (pad + dev.w // 2, y + dev.h + 18), "A 冻结（offset=0）", font(24),
         tuple(ACCENT) + (255,), anchor="ma")
    _txt(d, (pad + dev.w + gap + dev.w // 2, y + dev.h + 18),
         "B 行走钳制端（offset=溢出宽）", font(24), tuple(WARM) + (255,), anchor="ma")
    _txt(d, (pad, H - 56),
         "验图须真机各走同一路段录屏对比；HOP 腾空是语义动作，",
         font(21), tuple(MUTED) + (255,))
    _txt(d, (pad, H - 28),
         "reduceMotion 下仅从 26px 压到 10px，不抹除。",
         font(21), tuple(MUTED) + (255,))
    board.alpha_composite(ov)
    return board


# =========================================================================== 矩阵/分区
def matrix(mode: str) -> Image.Image:
    tw, th = 320, 711  # 1080×2400 同证据比例
    pad, gap, header = 40, 30, 168
    W = pad * 2 + tw * 3 + gap * 2
    H = header + (th + gap) * 2 + 104
    board = Image.new("RGBA", (W, H), BOARD_BG + (255,))
    ov = overlay_for(board)
    d = ImageDraw.Draw(ov)
    mode_name = "虚走 · 下 45% 浮动摇杆" if mode == "virtual" else "实走 · 下 45% 状态文案（无摇杆）"
    _txt(d, (pad, 24), f"森林 800m 双模式验图 · {mode_name}", font(36),
         tuple(ON_SURFACE) + (255,))
    _txt(d, (pad, 80),
         "六阶段=forest.json 各视觉层 fade 完成点 0/100/265/425/630/785m",
         font(22), tuple(MUTED) + (255,))
    _txt(d, (pad, 112),
         "合成自入包生产 webp（768×1376）+ 当前 app 几何；缩略图为设计模拟，非 App 截图",
         font(22), tuple(MUTED) + (255,))
    dev = Device(1080, 2400, 3.0, "long")
    for i, m in enumerate(STAGE_METERS):
        r, c = divmod(i, 3)
        x = pad + c * (tw + gap)
        y = header + r * (th + gap)
        frame = render_frame(
            dev, m, mode,
            joystick=(mode == "virtual"),
            real_state=("ready" if m == 0 else "good"),
            show_meters=False,
        )
        frame = frame.resize((tw, th), Image.LANCZOS)
        board.alpha_composite(frame, (x, y))
        d.rectangle([x, y, x + tw - 1, y + th - 1], outline=(255, 255, 255, 45), width=1)
        lab = f"{m} m"
        lf = font(28)
        lw = d.textlength(lab, font=lf)
        d.rounded_rectangle([x + 8, y + 66, x + 8 + lw + 20, y + 66 + 40],
                            radius=8, fill=(0, 0, 0, 150))
        _txt(d, (x + 18, y + 72), lab, lf, tuple(ACCENT) + (255,), shadow=False)
    fy = H - 84
    _txt(d, (pad, fy),
         "0m 纯黑仅程序旅人；米数不变揭示不变（smoothstep 纯函数）；800m 终点保持完整不切屏。",
         font(21), tuple(MUTED) + (255,))
    _txt(d, (pad, fy + 32),
         "虚走浮动摇杆无任何作者截图证据，本列全部为设计模拟，须 QA 真机补证。",
         font(21), tuple(WARN) + (255,))
    board.alpha_composite(ov)
    return board


def zones(mode: str) -> Image.Image:
    dev = Device(1080, 1920, 3.0, "base")
    img = composite(dev, 785)
    ov = overlay_for(img)
    d = ImageDraw.Draw(ov)
    # 上 55% 边界
    top = int(dev.h * 0.55)
    dashed_rect(d, [3, 3, dev.w - 3, top], tuple(ACCENT) + (110,))
    _txt(d, (dev.dp(10), top - dev.dp(30)),
         "上 55%：轻触切换米数显示 · 右上 暂停/长按放弃(1.5s)",
         font(dev.sp(11)), tuple(ACCENT) + (255,))
    draw_zone_labels(d, dev, mode)
    draw_top_chrome(d, dev, 785)
    if mode == "virtual":
        draw_joystick(d, dev)
    else:
        draw_real_status(d, dev, "good")
    # 旅人锚点
    ax, ay = int(dev.w * 0.34), int(dev.h * 0.865)
    d.line([(ax - 26, ay), (ax + 26, ay)], fill=tuple(WARN) + (255,), width=3)
    d.line([(ax, ay - 26), (ax, ay + 26)], fill=tuple(WARN) + (255,), width=3)
    _txt(d, (ax, ay - 44), "旅人锚点 x=.34 / y=.865（程序绘制）",
         font(dev.sp(11)), tuple(WARN) + (255,), anchor="ma")
    # 右缘 Void 带（完整证据见 findings F7）：半透明底+两行右对齐，放在黑带左侧
    scale = dev.h / layer_image("tree_outline").height
    dst_w = layer_image("tree_outline").width * scale
    webp_gap = int(round(30 * scale))
    band = webp_gap + int(round(max(0.0, dev.w - dst_w)))
    x_mark = dev.w - band
    d.line([(x_mark, 0), (x_mark, dev.h)], fill=tuple(WARN) + (220,), width=2)
    d.line([(dev.w - 1, 0), (dev.w - 1, dev.h)], fill=tuple(WARN) + (220,), width=2)
    bx1 = x_mark - dev.dp(10)
    bx0 = dev.dp(16)
    by0, by1 = dev.dp(150), dev.dp(206)
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=dev.dp(8), fill=(0, 0, 0, 150))
    _txt(d, (bx1 - dev.dp(8), by0 + dev.dp(8)),
         f"右缘约 {band}px Void 带（本机静态）",
         font(dev.sp(10)), tuple(WARN) + (255,), anchor="ra")
    _txt(d, (bx1 - dev.dp(8), by0 + dev.dp(30)),
         "长屏视差钳满露 52px · 像素证据见 findings F7",
         font(dev.sp(10)), tuple(WARN) + (255,), anchor="ra")
    draw_status_bar(d, dev)
    draw_home_indicator(d, dev)
    sim_badge(d, dev, "分区/锚点标注")
    img.alpha_composite(ov)
    return img


# =========================================================================== 真实证据
REAL_CAPTURES = [
    ("H-SW-010-R1/stages/stage-000m.png", "capture_real_stage_000m.png"),
    ("H-SW-010-R1/stages/stage-100m.png", "capture_real_stage_100m.png"),
    ("H-SW-010-R1/stages/stage-265m.png", "capture_real_stage_265m.png"),
    ("H-SW-010-R1/stages/stage-425m.png", "capture_real_stage_425m.png"),
    ("H-SW-010-R1/stages/stage-630m.png", "capture_real_stage_630m.png"),
    ("H-SW-010-R1/stages/stage-785m.png", "capture_real_stage_785m.png"),
    ("H-SW-010-R1/stages/freeze-a.png", "capture_real_freeze_a_785m.png"),
    ("H-SW-010-R1/stages/freeze-b.png", "capture_real_freeze_b_785m.png"),
    ("H-SW-010-R1/sizes/720x1280-785m.png", "capture_real_size_720x1280_785m.png"),
    ("H-SW-010-R1/sizes/1080x2880-785m.png", "capture_real_size_1080x2880_785m.png"),
    ("H-SW-005-R2/hint-shown.png", "capture_real_hint_shown_no_card.png"),
    ("H-SW-005-R2/after-hint-389m.png", "capture_real_after_hint_389m_no_card.png"),
]


def copy_captures():
    out = PREV / "real_captures"
    out.mkdir(parents=True, exist_ok=True)
    for src_rel, dst_name in REAL_CAPTURES:
        shutil.copyfile(EVID / src_rel, out / dst_name)


def findings_sheet() -> Image.Image:
    items = [
        ("capture_real_stage_265m.png", "F1 待设备确认 · 层缘硬分界",
         "240–400m（leaf_path 未揭示）tree_trunks 层亮拱下缘约 y=.70 出现横向暗分界；\n"
         "425m 后被 leaf_path 覆盖。需设备多档确认是 webp 边缘过硬还是 JPEG 观感，\n"
         "不由设计自判缺陷；若返工属 SW-012 生产层变更，须另走 R2。"),
        ("capture_real_hint_shown_no_card.png", "F2 证据缺口 · Pending",
         "作者文件名 hint-shown，但画面无「慢一点，站稳再跳。」卡片；\n"
         "after-hint-389m 也无卡片（可能 3s 已消失）。提示出现/消失时序缺同步证据，\n"
         "不能凭文件名当已正确显示；QA 需短视频或 ≤1s 间隔连拍 + UI hierarchy + head SHA。"),
        ("capture_real_stage_785m.png", "F3 待设备确认 · 文案叠印",
         "实走状态文案（titleMedium）位于下 45% 居中（约 y=.71/.74），785m 时压在亮地面与\n"
         "旅人竖线上；默认字号截图可读，需补系统大字号/高对比/亮阶段背景下的可读性核对。"),
        ("capture_real_stage_100m.png", "F4 供复核 · 观感差异记录",
         "入包 tree_outline 实机为尖顶针叶冠线；SW-011 设计稿文字描述柔圆团簇阔叶。\n"
         "该素材已 SW-010 验收入包，本任务仅记录意图与实际观感差异；是否返工由\n"
         "QA/MiniMax 评估，设计不自批。"),
        ("capture_real_stage_000m.png", "F5 证据缺口 · 覆盖维度",
         "现有作者证据全部来自实走（下 45% 状态文案）；虚走浮动摇杆、暂停卡片、\n"
         "站稳提示卡片、首局说明、放弃对话框、大字号、reduceMotion 均无 App 截图，\n"
         "本包对应画面全部是设计模拟，须 QA 真机/模拟器补证。"),
        ("capture_real_size_720x1280_785m.png", "F6 设备覆盖说明",
         "作者尺寸证据为 720×1280（16:9）与 1080×2880（2.67:1）；任务书参照比例\n"
         "390×844 / 1080×2400 无直接证据，本包以同渲染语义模拟给出，裁切结论须在\n"
         "对应真实分辨率上复核。"),
        ("capture_real_stage_265m.png", "F7 像素级证据 · 右缘 Void 带",
         "入包 webp 硬切右缘全透明列实测（edge-audit.json，all_pass=true）：\n"
         "tree_outline/tree_trunks/leaf_path 各 30 列，light_shows 133 列，clearing 4 列。\n"
         "1080×2400 cover 后 30 列≈52px，sPos≥144m 视差钳满即露 Void(060806)；\n"
         "作者截图实测：265/425m 右缘 52px 纯 Void(x=1028..1079,占比1.0)，\n"
         "630m 被光束遮到 12px，785m clearing 遮盖(合成alpha峰值仅≈27%仍需目检)；\n"
         "1080×1920 cover 宽不足：溢出0→视差失效，左42+右50px 静态暗带，待设备取证。\n"
         "素材层返工属 SW-012 变更轮次；设计只提交证据，不自判修法。"),
    ]
    pad = 36
    card_w, card_h = 1180, 430
    rows = (len(items) + 1) // 2
    W = card_w * 2 + pad * 3
    H = 150 + (card_h + pad) * rows
    board = Image.new("RGBA", (W, H), BOARD_BG + (255,))
    d0 = ImageDraw.Draw(board)
    _txt(d0, (pad, 28), "森林安装测试包 · 作者真实截图走查标注", font(40),
         tuple(ON_SURFACE) + (255,))
    _txt(d0, (pad, 88),
         "来源：H-SW-010-R1（作者模拟器 1080×2400 等）与 H-SW-005-R2；Trae 只读目检，"
         "未在本轮运行 App；缺陷判定与最终批准归 Antigravity/设备",
         font(22), tuple(MUTED) + (255,))
    ov = overlay_for(board)
    d = ImageDraw.Draw(ov)
    for i, (cap_name, tag, desc) in enumerate(items):
        r, c = divmod(i, 2)
        x = pad + c * (card_w + pad)
        y = 140 + r * (card_h + pad)
        d0.rounded_rectangle([x, y, x + card_w, y + card_h], radius=18,
                             fill=(18, 22, 19, 255))
        d.rounded_rectangle([x, y, x + card_w, y + card_h], radius=18,
                            outline=(255, 255, 255, 36), width=1)
        cap = Image.open(PREV / "real_captures" / cap_name).convert("RGBA")
        cap.thumbnail((290, card_h - 40), Image.LANCZOS)
        board.alpha_composite(cap, (x + 20, y + 20))
        tx = x + 330
        tag_col = WARN if ("缺口" in tag or "确认" in tag) else WARM
        _txt(d, (tx, y + 22), tag, font(28), tag_col + (255,))
        yy = y + 74
        for line in desc.split("\n"):
            _txt(d, (tx, yy), line, font(21), tuple(ON_SURFACE) + (235,), shadow=False)
            yy += 32
    board.alpha_composite(ov)
    return board


# =========================================================================== main
def main():
    for sub in ["matrix", "crops", "states", "zones", "parallax", "real_captures", "findings"]:
        (PREV / sub).mkdir(parents=True, exist_ok=True)

    def save(img: Image.Image, rel: str):
        p = PREV / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGBA").save(p)

    save(matrix("virtual"), "matrix/forest_virtual_six_stages.png")
    save(matrix("real"), "matrix/forest_real_six_stages.png")
    save(zones("virtual"), "zones/virtual_zones_1080x1920.png")
    save(zones("real"), "zones/real_zones_1080x1920.png")

    for w, h, dens, rscale, tag in DEVICES:
        rw, rh = w * rscale, h * rscale
        dev = Device(rw, rh, dens, tag)
        for name, frame in [
            ("virtual_785m", render_frame(dev, 785, "virtual")),
            ("real_785m", render_frame(dev, 785, "real")),
            ("real_100m", render_frame(dev, 100, "real", show_meters=False)),
            ("real_265m", render_frame(dev, 265, "real", show_meters=False)),
        ]:
            if rscale != 1:
                frame = frame.resize((w, h), Image.LANCZOS)
            save(frame, f"crops/{name.split('_')[0]}_{w}x{h}_{name.split('_', 1)[1]}.png")

    base_dev = Device(1080, 1920, 3.0, "base")
    save(state_paused(base_dev), "states/state_paused_1080x1920.png")
    save(state_stabilize_hint(base_dev), "states/state_stabilize_hint_1080x1920.png")
    save(state_intro(base_dev), "states/state_intro_card_1080x1920.png")
    save(state_abandon(base_dev), "states/state_abandon_confirm_1080x1920.png")
    long_dev = Device(1080, 2400, 3.0, "long")
    save(state_large_font(long_dev), "states/state_large_font_1080x2400.png")
    save(state_reduce_motion(Device(390, 844, 1.0, "small")),
         "states/state_reduce_motion_390x844.png")

    # 视差钳制说明对拍（长屏，最明显）
    a = render_frame(long_dev, 785, "virtual", reduce_motion=True, zones=False,
                     joystick=False, home=True)
    b = render_frame(long_dev, 785, "virtual", reduce_motion=False, zones=False,
                     joystick=False, home=True)
    pad, gap = 30, 26
    W = pad * 2 + 1080 * 2 + gap
    H = 250 + 2400 + 70
    board = Image.new("RGBA", (W, H), BOARD_BG + (255,))
    dd = ImageDraw.Draw(board)
    _txt(dd, (pad, 26), "有限视差钳制 · 1080×2400 · 785m", font(36), tuple(ON_SURFACE) + (255,))
    _txt(dd, (pad, 84), "左 reduceMotion/静止 offset=0；右行走常态 offset 钳在右溢出宽≈259px",
         font(23), tuple(MUTED) + (255,))
    y = 150
    board.alpha_composite(a, (pad, y))
    board.alpha_composite(b, (pad + 1080 + gap, y))
    save(board, "parallax/parallax_clamp_pair_1080x2400.png")

    copy_captures()
    save(findings_sheet(), "findings/evidence_findings_sheet.png")

    count = sum(1 for _ in PREV.rglob("*.png"))
    print(f"generated {count} png files under {PREV}")


if __name__ == "__main__":
    main()
