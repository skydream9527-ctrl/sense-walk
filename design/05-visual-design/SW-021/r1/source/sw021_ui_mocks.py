#!/usr/bin/env python3
"""SW-021 R1 · UI 精修设计模拟（PIL 绘制，非 App 截图）。

输出 previews/ui/：
  ui_home_layout_1080x2400.png       首页现状 vs 提案（单列 + 字阶/间距）
  ui_home_small_390x844.png         小屏单列 vs 双列对比
  ui_home_largefont_1080x2400.png   大字号 ×1.5 单列不截断
  ui_mode_cards_1080x2400.png       ModeCard：场景中性色 + 清晰不可用原因
  ui_abandon_confirm_1080x2400.png  暗色底部确认（危险动作明确）
  ui_longpress_ring_1080x2400.png   长按 1.5s 环形反馈三帧
  ui_result_dim_1080x2400.png       结果景色 ≥3s 退暗 + 用时折叠
  ui_about_credits_1080x2400.png    关于页真实音频署名
  ui_type_scale_1080x2400.png       字阶/字距/行高 token 表

零网络、零付费 API；所有图均标注「设计模拟 · 非 App 截图」。
颜色取自 app/ui/theme/Theme.kt 与 forest.json themeColor，不虚构新色板。
"""
from __future__ import annotations

import os
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
R1 = os.path.dirname(HERE)
OUT = os.path.join(R1, "previews/ui")

# Theme.kt 实采
BLACK = (0x0A, 0x0A, 0x0A, 255)
SURFACE = (0x14, 0x14, 0x14, 255)
ON = (0xE8, 0xE4, 0xD9, 255)
MUTED = (0x8A, 0x86, 0x80, 255)
FOREST_TINT = (0x2D, 0x4A, 0x3E, 255)
ACCENT = (0xA8, 0xC5, 0xA0, 255)
THEME_FOREST = (0x1F, 0x2A, 0x22, 255)  # forest.json themeColor
DANGER = (0xC9, 0x8A, 0x7E, 255)


def blend(c, bg=BLACK):
    """PIL ImageDraw 不做 alpha 混合；把固定深底上的半透明色预乘成不透明色。"""
    if len(c) == 3 or c[3] == 255:
        return c if len(c) == 4 else (c[0], c[1], c[2], 255)
    a = c[3] / 255.0
    return tuple(round(c[i] * a + bg[i] * (1 - a)) for i in range(3)) + (255,)


LINE = blend((255, 255, 255, 26))
CARD_SOFT = blend((255, 255, 255, 10), SURFACE)
FOREST_CARD = blend(THEME_FOREST + (120,))
FOREST_CARD_OFF = blend(THEME_FOREST + (42,))
FOREST_CARD_MODE = blend(THEME_FOREST + (96,))
BADGE_ON = blend((0xA8, 0xC5, 0xA0, 34), SURFACE)
BADGE_OFF = blend((0x8A, 0x86, 0x80, 26), SURFACE)
RING_TRACK = blend((255, 255, 255, 40))
RING_HIT = blend((255, 255, 255, 12))

FONT_REG = "/System/Library/Fonts/STHeiti Light.ttc"
FONT_MED = "/System/Library/Fonts/STHeiti Medium.ttc"


def F(size: int, weight: str = "regular"):
    p = FONT_MED if weight in ("medium", "semibold") else FONT_REG
    try:
        return ImageFont.truetype(p, size)
    except Exception:
        return ImageFont.load_default()


def wrap_cjk(d: ImageDraw.ImageDraw, text: str, fnt, max_w: int):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        if d.textlength(cur + ch, font=fnt) <= max_w:
            cur += ch
        else:
            lines.append(cur); cur = ch
    if cur:
        lines.append(cur)
    return lines


def text(d, xy, s, size, color=ON, weight="regular", max_w=None,
         lh_mult=1.42, ls=0):
    fnt = F(size, weight)
    x, y = xy
    lines = wrap_cjk(d, s, fnt, max_w) if max_w else s.split("\n")
    lh = int(size * lh_mult)
    for ln in lines:
        if ls:
            cx = x
            for ch in ln:
                d.text((cx, y), ch, font=fnt, fill=color)
                cx += d.textlength(ch, font=fnt) + ls
        else:
            d.text((x, y), ln, font=fnt, fill=color)
        y += lh
    return y


def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def badge(d, x, y, s, fg, bg_, size=22, pad_x=14, pad_y=5):
    fnt = F(size, "medium")
    tw = d.textlength(s, font=fnt)
    rrect(d, [x, y, x + tw + pad_x * 2, y + size + pad_y * 2], 12, fill=bg_)
    d.text((x + pad_x, y + pad_y - 1), s, font=fnt, fill=fg)
    return tw + pad_x * 2


def phone(w=1080, h=2400):
    im = Image.new("RGBA", (w, h), BLACK)
    return im, ImageDraw.Draw(im, "RGBA")


def status_bar(d, w, dark_icons=False):
    col = ON
    d.text((52, 34), "9:41", font=F(30, "semibold"), fill=col)
    # 信号/wifi/电池 简形
    x = w - 220
    for i, hgt in enumerate((14, 20, 26)):
        d.rounded_rectangle([x + i * 14, 60 - hgt, x + i * 14 + 9, 60],
                            4, fill=col)
    d.arc([x + 52, 30, x + 92, 62], 200, 340, fill=col, width=4)
    d.rounded_rectangle([x + 104, 38, x + 156, 58], 7, outline=col, width=3)
    d.rounded_rectangle([x + 159, 44, x + 165, 52], 2, fill=col)
    d.rounded_rectangle([x + 108, 42, x + 140, 54], 4, fill=col)


def watermark(im):
    d = ImageDraw.Draw(im, "RGBA")
    f = F(20)
    s = "设计模拟 · 非 App 截图"
    d.text((im.width - d.textlength(s, font=f) - 20, im.height - 40),
           s, font=f, fill=(232, 228, 217, 110))


def header(d, title, sub=None, back=False):
    x = 52
    if back:
        d.line([(60, 76), (40, 96), (60, 116)], fill=ON, width=5)
        x = 110
    text(d, (x, 58), title, 44, ON, "medium")
    if sub:
        text(d, (x, 122), sub, 24, MUTED)


def scene_card(d, box, name, meters, minutes, open_, selected,
               reason=None, theme=THEME_FOREST):
    x0, y0, x1, y1 = box
    fill = FOREST_CARD if open_ else FOREST_CARD_OFF
    rrect(d, box, 32, fill=fill,
          outline=ACCENT if selected else LINE,
          width=4 if selected else 2)
    if selected:
        d.ellipse([x1 - 78, y0 + 28, x1 - 34, y0 + 72], outline=ACCENT, width=4)
        d.line([x1 - 66, y0 + 50, x1 - 57, y0 + 60], fill=ACCENT, width=4)
        d.line([x1 - 57, y0 + 60, x1 - 45, y0 + 42], fill=ACCENT, width=4)
    text(d, (x0 + 36, y1 - 118), name, 40, ON if open_ else MUTED, "medium")
    tag = "可虚走" if open_ else "暂未开放"
    tag_w = badge(d, x0 + 36 + d.textlength(name, font=F(40, "medium")) + 20,
                  y1 - 112, tag,
                  ACCENT if open_ else MUTED,
                  BADGE_ON if open_ else BADGE_OFF, size=22)
    info = f"{meters} m · 约 {minutes} 分钟"
    text(d, (x0 + 36, y1 - 58), info, 26,
         (0xE8, 0xE4, 0xD9, 190) if open_ else (0x8A, 0x86, 0x80, 180))
    if not open_ and reason:
        text(d, (x0 + 36, y0 + 30), reason, 24, MUTED, max_w=x1 - x0 - 72)


def ensure():
    os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------------------
def ui_home_layout():
    """现状 vs 提案：同屏 2 台 1080 宽手机并排。"""
    gap = 40
    W, H = 1080, 2400
    sheet = Image.new("RGBA", (W * 2 + gap * 3, H + 220), (20, 20, 20, 255))
    d0 = ImageDraw.Draw(sheet, "RGBA")
    text(d0, (gap, 40), "首页精修：现状（左）→ 提案（右，单列 + 字阶/间距/署名入口）",
         36, ON, "medium")

    # ---- 左：现状复刻（HomeScreen.kt 语义）----
    im, d = phone(W, H)
    status_bar(d, W)
    text(d, (52, 120), "慢行", 42, ON, "medium")
    text(d, (52, 178), "SenseWalk", 26, MUTED)
    d.ellipse([W - 130, 128, W - 78, 180], outline=ON, width=3)
    text(d, (52, 268), "选一个场景，安静地走一会儿", 28, MUTED)
    cards = [("森林", 800, 14, True, True), ("雨林", 900, 16, False, False),
             ("夜径", 800, 14, False, False)]
    y = 340
    for name, m, mn, op, sel in cards:
        scene_card(d, (52, y, W - 52, y + 230), name, m, mn, op, sel,
                   reason=None)
        y += 256
    rrect(d, [52, H - 190, W - 52, H - 92], 28, fill=ACCENT)
    text(d, (52, H - 165), "下一步 · 怎么走", 34, BLACK, "semibold")
    # 标注
    d.line([(W - 60, 400), (W - 20, 400)], fill=(255, 210, 80, 255), width=4)
    text(d, (W - 420, 340), "不可用仅一句\n「暂未开放」", 24,
         (255, 210, 80, 255), max_w=340)
    watermark(im)
    sheet.alpha_composite(im, (gap, 150))

    # ---- 右：提案 ----
    im2, d = phone(W, H)
    status_bar(d, W)
    text(d, (52, 120), "慢行", 46, ON, "semibold")
    text(d, (52, 188), "选一个场景，安静地走一会儿", 28, MUTED)
    # 场景卡：可用卡用 themeColor 低透明；不可用卡给原因
    y = 280
    scene_card(d, (52, y, W - 52, y + 260), "森林", 800, 14, True, True)
    y += 286
    scene_card(d, (52, y, W - 52, y + 260), "雨林", 900, 16, False, False,
               reason="声音与地形仍在准备，完成后会在这里开放。")
    y += 286
    scene_card(d, (52, y, W - 52, y + 260), "夜径", 800, 14, False, False,
               reason="夜间安全路线还没走完验收，暂不开放。")
    rrect(d, [52, H - 300, W - 52, H - 202], 28, fill=ACCENT)
    text(d, (52, H - 275), "下一步 · 怎么走", 34, BLACK, "semibold")
    text(d, (52, H - 150), "素材署名与许可", 26, MUTED)
    text(d, (52, H - 102), "关于 SenseWalk", 26, MUTED)
    # 标注
    text(d, (W - 380, 580), "不可用卡保留位置，\n原因直接写在卡内。", 24,
         (255, 210, 80, 255), max_w=320)
    watermark(im2)
    sheet.alpha_composite(im2, (W + gap * 2, 150))
    sheet.save(os.path.join(OUT, "ui_home_layout_1080x2400.png"))


def ui_home_small():
    """390×844 @3x：单列 vs 双列。"""
    ss = 3
    w, h = 390 * ss, 844 * ss
    gap = 28
    sheet = Image.new("RGBA", (w * 2 + gap * 3, h + 150), (20, 20, 20, 255))
    dd = ImageDraw.Draw(sheet, "RGBA")
    text(dd, (gap, 30), "小屏（390×844）：单列可点（左）vs 双列挤压（右，否决）",
         28, ON, "medium")
    for col, double in ((0, False), (1, True)):
        im = Image.new("RGBA", (w, h), BLACK)
        d = ImageDraw.Draw(im, "RGBA")
        text(d, (40, 36), "慢行", 38, ON, "semibold")
        if double:
            x0, x1, cw = 40, w // 2 - 10, w // 2 - 50
            meta = [("森林", True), ("雨林", False)]
            y = 110
            for i, (name, op) in enumerate(meta):
                box = (x0 + i * (cw + 20), y, x0 + i * (cw + 20) + cw, y + 230)
                rrect(d, box, 24, fill=FOREST_CARD if op else FOREST_CARD_OFF,
                      outline=LINE, width=2)
                text(d, (box[0] + 20, box[3] - 90), name, 30,
                     ON if op else MUTED, "medium")
                text(d, (box[0] + 20, box[3] - 46),
                     "800 m" if op else "900 m", 22, MUTED)
            rrect(d, [40, h - 150, w - 40, h - 80], 20, fill=None,
                  outline=(255, 255, 255, 50), width=2)
            text(d, (60, h - 132), "下一步", 26, MUTED, "semibold")
            text(d, (40, 380), "双列后：米数/分钟被截、\n原因无处可放、触控高度不足",
                 24, (255, 210, 80, 255), max_w=w - 80)
        else:
            y = 110
            for name, m, mn, op, reason in [
                ("森林", 800, 14, True, None),
                ("雨林", 900, 16, False, "声音与地形仍在准备。"),
            ]:
                scene_card(d, (40, y, w - 40, y + 210), name, m, mn, op,
                           op and True, reason=reason)
                y += 232
            rrect(d, [40, h - 140, w - 40, h - 74], 22, fill=ACCENT)
            text(d, (60, h - 124), "下一步 · 怎么走", 28, BLACK, "semibold")
        watermark(im)
        sheet.alpha_composite(im, (gap + col * (w + gap), 110))
    sheet.save(os.path.join(OUT, "ui_home_small_390x844.png"))


def ui_home_largefont():
    W, H = 1080, 2400
    im, d = phone()
    status_bar(d, W)
    text(d, (52, 120), "慢行", 60, ON, "semibold")
    text(d, (52, 210), "选一个场景，安静地走一会儿", 38, MUTED)
    y = 310
    scene_card(d, (52, y, W - 52, y + 320), "森林", 800, 14, True, True)
    y += 348
    scene_card(d, (52, y, W - 52, y + 320), "雨林", 900, 16, False, False,
               reason="声音与地形仍在准备，完成后会在这里开放。")
    rrect(d, [52, H - 260, W - 52, H - 150], 30, fill=ACCENT)
    text(d, (52, H - 228), "下一步 · 怎么走", 44, BLACK, "semibold")
    text(d, (52, 60), "大字号 ×1.5：单列自适应增高，信息不截断", 26,
         (255, 210, 80, 255))
    watermark(im)
    im.save(os.path.join(OUT, "ui_home_largefont_1080x2400.png"))


def ui_mode_cards():
    W, H = 1080, 2400
    im, d = phone()
    status_bar(d, W)
    header(d, "怎么走", back=True)
    text(d, (110, 210), "森林 · 800 m · 约 14 分钟", 28, MUTED)

    def mode_card(box, title, sub, enabled, selected, reason=None):
        x0, y0, x1, y1 = box
        fill = FOREST_CARD_MODE if enabled else None
        rrect(d, box, 32, fill=fill, outline=ACCENT if selected else LINE,
              width=4 if selected else 2)
        if not enabled:
            d.ellipse([x1 - 86, y0 + 34, x1 - 42, y0 + 78], outline=MUTED,
                      width=3)
            d.line([x1 - 74, y0 + 70, x1 - 54, y0 + 50], fill=MUTED, width=3)
        text(d, (x0 + 36, y0 + 34), title, 38,
             ON if enabled else MUTED, "medium")
        text(d, (x0 + 36, y0 + 100), sub, 27,
             (0xE8, 0xE4, 0xD9, 190) if enabled else MUTED, max_w=x1 - x0 - 160)
        if reason:
            rrect(d, [x0 + 36, y1 - 78, x1 - 36, y1 - 24], 14,
                  fill=CARD_SOFT)
            text(d, (x0 + 54, y1 - 68), reason, 24, MUTED,
                 max_w=x1 - x0 - 110)

    mode_card((52, 300, W - 52, 470), "虚走 · 手机上走",
              "摇杆控制角色，找舒服的节奏", True, True)
    mode_card((52, 510, W - 52, 720), "实走 · 出门走",
              "计步算距离，锁屏也能走", False, False,
              reason="当前版本先在虚走里体验；实走在完成权限与计步验收后开放。")
    rrect(d, [52, H - 260, W - 52, H - 150], 30, fill=None,
          outline=(255, 255, 255, 60), width=2)
    text(d, (52, H - 228), "开始", 40, MUTED, "semibold")
    text(d, (52, H - 110), "禁用态：文字保持可读对比，原因常驻卡片，不藏进 Toast。",
         24, (255, 210, 80, 255), max_w=W - 104)
    watermark(im)
    im.save(os.path.join(OUT, "ui_mode_cards_1080x2400.png"))


def ui_abandon():
    W, H = 1080, 2400
    im, d = phone()
    # 背景：暗色虚走画面
    bg = Image.new("RGBA", (W, H), (10, 14, 11, 255))
    bgd = ImageDraw.Draw(bg, "RGBA")
    for i, x in enumerate((120, 420, 760, 1000)):
        bgd.rounded_rectangle([x, -100, x + 120 + i * 30, 1500], 60,
                              fill=blend((28, 48, 39, 120), (10, 14, 11)))
    bgd.rectangle([0, 1500, W, H], fill=(30, 26, 19, 255))
    im = Image.alpha_composite(im, bg)
    # 遮罩必须走独立 overlay 才能真正与画面 alpha 混合
    im = Image.alpha_composite(im, Image.new("RGBA", (W, H), (0, 0, 0, 150)))
    d = ImageDraw.Draw(im, "RGBA")
    status_bar(d, W)
    # 底部 sheet
    sheet_box = [0, H - 880, W, H]
    rrect(d, [0, H - 900, W, H], 56, fill=SURFACE)
    d.rounded_rectangle([W // 2 - 60, H - 850, W // 2 + 60, H - 838], 6,
                        fill=(0x8A, 0x86, 0x80, 120))
    text(d, (60, H - 780), "放弃这趟森林？", 46, ON, "semibold")
    text(d, (60, H - 690),
         "已经走的 312 m 不会计入这趟，也不会解锁新的声音。\n可以随时再开一趟，进度按每趟重新计算。",
         28, MUTED, max_w=W - 120, lh_mult=1.5)
    rrect(d, [60, H - 460, W - 60, H - 350], 30, fill=(0xC9, 0x4A, 0x3E, 255))
    text(d, (60, H - 428), "放弃这趟", 38, (255, 236, 230, 255), "semibold")
    rrect(d, [60, H - 310, W - 60, H - 200], 30, outline=LINE, width=2)
    text(d, (60, H - 278), "继续走", 38, ON, "medium")
    text(d, (60, H - 140), "危险动作使用暖色区分；暗色底上文字对比保持清晰。",
         24, (255, 210, 80, 255), max_w=W - 120)
    watermark(im)
    im.save(os.path.join(OUT, "ui_abandon_confirm_1080x2400.png"))


def ui_longpress():
    W = 1080
    gap = 30
    cell = (W - gap * 4) // 3
    sheet = Image.new("RGBA", (W, cell + 330), (20, 20, 20, 255))
    dd = ImageDraw.Draw(sheet, "RGBA")
    text(dd, (gap, 30), "长按 1.5s 环形反馈：0s → 0.75s → 满环触发（触觉同点）",
         32, ON, "medium")
    text(dd, (gap, 82),
         "环形只表达按住确认，不产生距离；松开取消，不成为计距捷径。reduceMotion 下改静态「按住确认」文字。",
         24, MUTED, max_w=W - gap * 2)
    for i, (prog, lab) in enumerate(((0.0, "按下 0.0s"), (0.5, "保持 0.75s"),
                                     (1.0, "1.5s 触发"))):
        label_h = 120
        im = Image.new("RGBA", (cell, cell + label_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im, "RGBA")
        d.rectangle([0, 0, cell, cell], fill=(10, 14, 11, 255))
        cx, cy, r = cell // 2, int(cell * 0.44), 130
        d.ellipse([cx - r - 22, cy - r - 22, cx + r + 22, cy + r + 22],
                  fill=RING_HIT)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(31, 42, 34, 255),
                 outline=RING_TRACK, width=10)
        if prog > 0:
            d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * prog,
                  fill=ACCENT, width=10)
        if prog >= 1:
            d.line([cx - 34, cy + 2, cx - 8, cy + 28], fill=ACCENT, width=9)
            d.line([cx - 8, cy + 28, cx + 42, cy - 30], fill=ACCENT, width=9)
        f1, f2 = F(30, "medium"), F(23)
        sub = "按住确认行走" if prog < 1 else "已确认"
        d.text((cx - d.textlength(lab, font=f1) / 2, cell + 16),
                lab, font=f1, fill=ON)
        d.text((cx - d.textlength(sub, font=f2) / 2, cell + 56),
               sub, font=f2, fill=MUTED)
        sheet.alpha_composite(im, (gap + i * (cell + gap), 150))
    f = F(20)
    s = "设计模拟 · 非 App 截图"
    dd.text((W - dd.textlength(s, font=f) - gap, sheet.height - 44),
            s, font=f, fill=(232, 228, 217, 110))
    sheet.save(os.path.join(OUT, "ui_longpress_ring_1080x2400.png"))


def ui_result_dim():
    W, H = 1080, 2400
    gap = 24
    cell_w = (W - gap * 4) // 3
    ch = int(cell_w * H / W)
    sheet = Image.new("RGBA", (W, ch + 200), (20, 20, 20, 255))
    dd = ImageDraw.Draw(sheet, "RGBA")
    text(dd, (gap, 30), "结果落幕：终景先冻结输入，再用 ≥3s 缓慢退暗揭示；用时默认折叠",
         28, ON, "medium")
    stages = [
        (0.0, "0s · 刚走完", (0, 0, 0, 0), False),
        (0.5, "1.5s · 退暗中", (0, 0, 0, 96), False),
        (1.0, "≥3s · 终景+卡片", (0, 0, 0, 168), True),
    ]
    forest_bg = (12, 16, 12, 255)
    for i, (p, lab, veil, card) in enumerate(stages):
        im = Image.new("RGBA", (cell_w, ch), forest_bg)
        d = ImageDraw.Draw(im, "RGBA")
        # 终景：林间暖光 + 地面（预乘到深底）
        for x, wd, a in ((60, 70, 90), (300, 110, 70), (560, 80, 80)):
            d.rounded_rectangle([x, -40, x + wd, ch], 30,
                                fill=blend((34, 54, 44, a), forest_bg))
        d.ellipse([cell_w * 0.42, ch * 0.18, cell_w * 1.05, ch * 0.62],
                  fill=blend((168, 197, 160, 60), forest_bg))
        d.rectangle([0, int(ch * 0.66), cell_w, ch], fill=(40, 33, 24, 255))
        # 退暗遮罩走 overlay 真正混合
        if veil[3]:
            im = Image.alpha_composite(
                im, Image.new("RGBA", (cell_w, ch), veil))
            d = ImageDraw.Draw(im, "RGBA")
        if card:
            bx0, by0, bx1, by1 = 20, ch - 430, cell_w - 20, ch - 36
            rrect(d, [bx0, by0, bx1, by1], 28,
                  fill=blend((18, 20, 18, 235), (7, 10, 8)),
                  outline=LINE, width=2)
            text(d, (bx0 + 28, by0 + 28), "走完 800 m", 34, ON, "semibold")
            text(d, (bx0 + 28, by0 + 88), "森林慢慢亮起来了", 23, MUTED)
            text(d, (bx0 + 28, by0 + 146), "用时与步幅", 21,
                 (0x8A, 0x86, 0x80, 200))
            cx, cyc = bx1 - 44, by0 + 157
            d.line([(cx - 9, cyc - 6), (cx, cyc + 4), (cx + 9, cyc - 6)],
                   fill=(0x8A, 0x86, 0x80, 220), width=3)
            rrect(d, [bx0 + 28, by1 - 72, bx1 - 28, by1 - 20], 18,
                  fill=ACCENT)
            text(d, (bx0 + 48, by1 - 62), "再走一趟", 25, BLACK, "semibold")
        text(d, (20, 18), lab, 22, ON, "medium")
        sheet.alpha_composite(im, (gap + i * (cell_w + gap), 120))
    f = F(20)
    s = "设计模拟 · 非 App 截图"
    dd.text((W - dd.textlength(s, font=f) - gap, ch + 150),
            s, font=f, fill=(232, 228, 217, 110))
    sheet.save(os.path.join(OUT, "ui_result_dim_1080x2400.png"))


def ui_about():
    W, H = 1080, 2400
    im, d = phone()
    status_bar(d, W)
    header(d, "关于", back=True)
    y = 230
    text(d, (52, y), "SenseWalk", 40, ON, "semibold"); y += 66
    text(d, (52, y), "版本 0.1.0（测试预览）", 26, MUTED); y += 90
    rrect(d, [40, y, W - 40, y + 2], 1, fill=LINE); y += 50

    text(d, (52, y), "声音素材署名", 32, ON, "medium"); y += 70
    credits = [
        ("脚步 · Walking through leaves / leaves and sticks",
         "Gravity Sound（gravitysound.studio）", "CC BY 4.0",
         "Wikimedia Commons，已切分与响度处理"),
        ("环境虫鸣 · Waidachswald Oberschefflenz Abend",
         "User:Karlunun", "CC0",
         "Wikimedia Commons，60s 无缝循环"),
        ("远处鸟鸣 · Dawn chorus at Glencairnie",
         "DivyaCM", "CC BY 4.0",
         "Wikimedia Commons，取温和段"),
    ]
    for title, who, lic, note in credits:
        rrect(d, [40, y, W - 40, y + 250], 28, fill=CARD_SOFT)
        text(d, (72, y + 28), title, 27, ON, "medium", max_w=W - 144)
        text(d, (72, y + 108), f"作者：{who}", 25, MUTED, max_w=W - 144)
        badge(d, 72, y + 158, lic, ACCENT, BADGE_ON, size=22)
        text(d, (230, y + 163), note, 23, MUTED, max_w=W - 300)
        y += 274
    text(d, (52, y + 6),
         "CC BY 4.0 要求保留署名；完整链接与许可证文本见「素材署名与许可」。",
         23, MUTED, max_w=W - 104)
    watermark(im)
    im.save(os.path.join(OUT, "ui_about_credits_1080x2400.png"))


def ui_type_scale():
    W, H = 1080, 2400
    im, d = phone()
    status_bar(d, W)
    header(d, "字阶与间距 token（提案）")
    rows = [
        ("display", 56, "semibold", "走完 800 m", 1.25, 0),
        ("title-1", 46, "semibold", "放弃这趟森林？", 1.3, 0),
        ("title-2", 40, "medium", "慢行 / 怎么走", 1.35, 0),
        ("title-3", 34, "medium", "虚走 · 手机上走", 1.4, 0),
        ("body", 28, "regular", "选一个场景，安静地走一会儿", 1.5, 0),
        ("body-s", 26, "regular", "800 m · 约 14 分钟", 1.45, 0),
        ("caption", 24, "regular", "声音与地形仍在准备。", 1.4, 0.5),
        ("label", 22, "medium", "可虚走 / CC BY 4.0", 1.3, 1),
    ]
    y = 240
    for name, size, wt, sample, lh, ls in rows:
        text(d, (52, y), f"{name} · {size}sp/{lh}", 24, MUTED, "medium")
        text(d, (420, y - (size - 28) // 2), sample, size, ON, wt,
             max_w=W - 470, lh_mult=lh, ls=ls)
        y += max(96, int(size * lh) + 44)
        rrect(d, [40, y - 26, W - 40, y - 24], 1, fill=(255, 255, 255, 12))
    text(d, (52, H - 150),
         "中文正文行高 ≥1.45；caption/label 加 0.5–1sp 字距改善暗底可读性。",
         24, MUTED, max_w=W - 104)
    watermark(im)
    im.save(os.path.join(OUT, "ui_type_scale_1080x2400.png"))


def main():
    ensure()
    ui_home_layout()
    ui_home_small()
    ui_home_largefont()
    ui_mode_cards()
    ui_abandon()
    ui_longpress()
    ui_result_dim()
    ui_about()
    ui_type_scale()
    print("[sw021] UI mocks done ->", OUT)


if __name__ == "__main__":
    main()
