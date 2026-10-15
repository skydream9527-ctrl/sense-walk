#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SW-011 r1 · 森林五层场景模型（Trae Design）

五层共享同一套“图元模型”，由 sw011_render.py 同时输出：
  - 可编辑 SVG（source/svg/*.svg）
  - 真实导出 PNG（exports/ 与 previews/，2× 超采样后缩放）
两个后端消费同一模型，保证矢量源与导出图一致；无外部付费 API、无位图素材。

图元：
  ellipse(cx,cy,rx,ry,color,a=1)
  poly(pts,color,a=1)
  rrect(x0,y0,x1,y1,r,color,a=1)
  line(p0,p1,w,color,a=1)
  quad(p0,c,p1,w,color,a=1)          二次贝塞尔描边
  vgrad(box, stops)                  竖向线性渐变（stops: (t,(r,g,b,a))）
  hgrad(box, stops)                  横向线性渐变
  radial(cx,cy,r,stops)
  polygrad(pts, y0, y1, stops)       按轮廓蒙版 + 竖向渐变（地面体）
  group(children, mask=None, blur=0, opacity=1, rot=None)
      mask: [(y, 0..1), ...] 纵向透明度 ramp；blur: 高斯 σ；rot: (deg, px, py)
"""
import math
import random

W, H = 1080, 1920

# —— 契约色板 token ——
VOID = (6, 8, 6)
OUTLINE = (26, 40, 32)
OUTLINE_BACK = (34, 51, 42)
TRUNK = (45, 74, 62)
TRUNK_DARK = (36, 64, 54)
TRUNK_FG = (36, 58, 48)
LIGHT = (143, 168, 122)
LEAF = (107, 143, 113)
WARM = (168, 144, 96)
GLOW = (168, 197, 160)
EARTH_TOP = (74, 64, 48)
EARTH_BOTTOM = (49, 42, 31)
PATH_EARTH = (106, 91, 66)
TWIG = (90, 78, 56)
TRAVELER = (122, 133, 124)


def ellipse(cx, cy, rx, ry, color, a=1.0):
    return ("e", cx, cy, rx, ry, color, a)


def poly(pts, color, a=1.0):
    return ("p", pts, color, a)


def rrect(x0, y0, x1, y1, rad, color, a=1.0):
    return ("r", (x0, y0, x1, y1), rad, color, a)


def line(p0, p1, w, color, a=1.0):
    return ("l", p0, p1, w, color, a)


def quad(p0, c, p1, w, color, a=1.0):
    return ("q", p0, c, p1, w, color, a)


def vgrad(box, stops):
    return ("vgrad", box, stops)


def hgrad(box, stops):
    return ("hgrad", box, stops)


def radial(cx, cy, r, stops):
    return ("rad", (cx, cy), r, stops)


def erad(cx, cy, rx, ry, stops):
    """椭圆径向渐变（归一化椭圆距离）。"""
    return ("erad", (cx, cy), (rx, ry), stops)


def polygrad(pts, y0, y1, stops):
    return ("polygrad", pts, (y0, y1), stops)


def group(children, mask=None, blur=0.0, opacity=1.0, rot=None):
    return ("g", children, mask, blur, opacity, rot)


# --------------------------------------------------------------------------
# 1) tree_outline
# --------------------------------------------------------------------------
def _crown_row(r, fill, base_y, x0, x1, gap, rmin, rmax):
    shapes = []
    x = x0
    while x < x1:
        cx = x + r.uniform(-18, 18)
        cy = base_y + r.uniform(-46, 46)
        for _ in range(r.randint(4, 7)):
            shapes.append(
                ellipse(
                    cx + r.uniform(-70, 70), cy + r.uniform(-55, 40),
                    r.uniform(rmin, rmax), r.uniform(rmin * 0.8, rmax * 1.15),
                    fill,
                )
            )
        for _ in range(2):
            shapes.append(
                ellipse(
                    cx + r.uniform(-40, 40), cy - r.uniform(70, 110),
                    r.uniform(34, 60), r.uniform(40, 66), fill,
                )
            )
        x += r.uniform(gap[0], gap[1])
    return shapes


def tree_outline():
    r = random.Random(20261013)
    crowns = _crown_row(r, OUTLINE_BACK, 1180, -80, 1160, (150, 210), 58, 96)
    crowns += _crown_row(r, OUTLINE, 1300, -60, 1140, (170, 235), 78, 128)
    return [group(crowns, mask=[(1230, 1), (1600, 0)])]


# --------------------------------------------------------------------------
# 2) tree_trunks
# --------------------------------------------------------------------------
def _trunk_poly(cx, wtop, wbot, ytop, ybot, lean, n=14):
    """微摆、带根扩的树干多边形点列（左右各 n 段）。"""
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        # 平滑的轻微摆动（sin 弯）
        sway = lean * (2 * t * (1 - t)) * 0.9 + lean * 0.10 * t
        w = wtop + (wbot - wtop) * t
        y = ytop + (ybot - ytop) * t
        left.append((cx - w / 2 + sway, y))
        right.append((cx + w / 2 + sway, y))
    pts = left + [(cx, ybot + wbot * 0.16)] + list(reversed(right))
    return pts


def tree_trunks():
    r = random.Random(112358)
    inside = []

    # 林间竖光（树干之后；极弱、大柔斑，避免光柱感）
    shafts = []
    for cx, rx, a in [(235, 110, 0.09), (560, 140, 0.11), (905, 95, 0.07)]:
        shafts.append(ellipse(cx, 820, rx, 700, LIGHT, a))
    inside.append(group(shafts, blur=44))

    specs = [
        (118, 30, 46, -60, 1640, -8, TRUNK),
        (250, 24, 36, 120, 1600, 6, TRUNK),
        (408, 40, 62, -40, 1670, -10, TRUNK),
        (566, 26, 42, 200, 1580, 8, TRUNK),
        (720, 46, 74, -80, 1680, -6, TRUNK),
        (876, 24, 38, 90, 1600, 10, TRUNK),
        (1024, 60, 104, -120, 1720, -12, TRUNK_FG),
    ]
    branches = {
        2: [((408, 360), (350, 330), (300, 300)), ((412, 470), (355, 460), (300, 430))],
        4: [((724, 300), (668, 272), (612, 250))],
        6: [((1030, 240), (965, 205), (900, 180)), ((1018, 420), (960, 405), (905, 380))],
    }

    trunks, rims, bch, bch_fg = [], [], [], []
    for i, (cx, wt, wb, yt, yb, lean, color) in enumerate(specs):
        # 竖向体积渐变：中上部最亮，上下两端没入暗部（只用契约色板 token）
        # 前景最暗树保持纯剪影，不做提亮
        if color == TRUNK_FG:
            trunks.append(poly(_trunk_poly(cx, wt, wb, yt, yb, lean), TRUNK_FG))
        else:
            trunks.append(
                polygrad(
                    _trunk_poly(cx, wt, wb, yt, yb, lean), yt, yb,
                    [(0.0, (*TRUNK_DARK, 1.0)),
                     (0.42, (*TRUNK, 1.0)),
                     (1.0, (*TRUNK_DARK, 0.92))],
                )
            )
        # 右上光：右侧细边光
        rims.append(
            quad(
                (cx + wt / 2 - 5, yt + 90),
                (cx + wb / 2 - 9 - lean * 0.5, (yt + yb) / 2),
                (cx + wb / 2 - 12 - lean, yb - 150),
                5, LIGHT, 0.22,
            )
        )
        for p0, c, p1 in branches.get(i, []):
            (bch if color != TRUNK_FG else bch_fg).append(quad(p0, c, p1, 8, color))

    inside.append(group(trunks))
    if bch:
        inside.append(group(bch))
    if bch_fg:
        inside.append(group(bch_fg))
    inside.append(group(rims))

    # 上下缘柔化（树干从黑幕里淡入、到地面之前淡出，不画地面）
    return [group(inside, mask=[(0, 0), (307, 1), (1536, 1), (1766, 0)])]


# --------------------------------------------------------------------------
# 3) leaf_path
# --------------------------------------------------------------------------
def _leaf_shape(x, y, length, w, ang):
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux
    x1, y1 = x - ux * length / 2, y - uy * length / 2
    x2, y2 = x + ux * length / 2, y + uy * length / 2
    return [
        (x1, y1),
        (x + px * w, y + py * w),
        (x2, y2),
        (x - px * w, y - py * w),
    ]


def leaf_path():
    r = random.Random(314159)
    g = []

    # 地面体：和缓起伏的落叶土坡，竖向渐变（轮廓蒙版）
    pts = [(-40, H), (-40, 1372)]
    x = -40
    while x <= W + 40:
        y = 1406 + 34 * math.sin(x / 205.0) + 16 * math.sin(x / 77.0 + 1.3)
        pts.append((x, y))
        x += 70
    pts += [(W + 40, H)]
    g.append(
        polygrad(
            pts, 1360, 1920,
            [(0.0, (*EARTH_TOP, 0.0)),
             (0.22, (*EARTH_TOP, 0.95)),
             (1.0, (*EARTH_BOTTOM, 1.0))],
        )
    )

    # 中央极弱土路光带
    ribbon = [
        poly([(470, 1920), (610, 1920), (586, 1560), (540, 1500), (506, 1560)],
             PATH_EARTH, 0.16)
    ]
    g.append(group(ribbon, blur=24))

    # 两侧落叶堆（柔斑）
    mounds = []
    for cx, cy, rx, ry, a in [
        (150, 1820, 200, 70, 0.14), (950, 1840, 230, 80, 0.15),
        (120, 1620, 150, 46, 0.10), (980, 1600, 160, 50, 0.10),
        (560, 1880, 260, 60, 0.08),
    ]:
        mounds.append(ellipse(cx, cy, rx, ry, WARM, a))
    g.append(group(mounds, blur=10))

    # 干叶：中心触控带与旅人脚底保持稀疏
    leaves, twigs = [], []
    made, attempts = 0, 0
    while made < 66 and attempts < 400:
        attempts += 1
        cx, cy = r.uniform(40, 1040), r.uniform(1490, 1900)
        if 300 < cx < 770 and 1520 < cy and r.random() > 0.40:
            continue
        if (cx - 367) ** 2 + (cy - 1661) ** 2 < 150 ** 2 and r.random() > 0.35:
            continue
        color = WARM if r.random() < 0.62 else LEAF
        if r.random() < 0.12:
            color = (87, 76, 54)
        leaves.append(
            poly(
                _leaf_shape(cx, cy, r.uniform(11, 26), r.uniform(3.5, 7),
                            r.uniform(-42, 42)),
                color, r.uniform(0.42, 0.85),
            )
        )
        made += 1
    g.append(group(leaves))

    for _ in range(9):
        x0, y0 = r.uniform(60, 1020), r.uniform(1560, 1900)
        if 330 < x0 < 720 and r.random() > 0.5:
            continue
        a = math.radians(r.uniform(-25, 25))
        L = r.uniform(24, 52)
        twigs.append(line((x0, y0), (x0 + L * math.cos(a), y0 + L * math.sin(a)),
                          2.4, TWIG, 0.5))
    g.append(group(twigs))

    return [group(g, mask=[(1280, 0), (1500, 1)])]


# --------------------------------------------------------------------------
# 4) light_shows
# --------------------------------------------------------------------------
def light_shows():
    beam_col = (221, 231, 196)
    out = []
    # 体积光束：纵向拉伸的椭圆径向辉光（四边自然衰减到 0，无几何硬边），
    # 再绕画面外右上的光源点倾斜。屏内只保留柔和的中段光带。
    for pivot_x, w, deg, length, peak, a, src_y in [
        (1000, 150, 16.5, 1760, 0.20, 0.95, -320),
        (902, 100, 20.0, 1620, 0.14, 0.75, -320),
        (1090, 72, 12.5, 1500, 0.10, 0.60, -300),
    ]:
        rx = w * 0.5
        ry = length * 0.55
        cy = src_y + ry * 0.92
        beam = [
            erad(
                pivot_x, cy, rx, ry,
                # 椭圆纵向拉伸；缓衰减让中段柔、边缘化入黑幕，无几何硬边
                [(0.0, (*beam_col, peak)),
                 (0.45, (*beam_col, peak * 0.55)),
                 (0.78, (*beam_col, peak * 0.16)),
                 (1.0, (*beam_col, 0.0))],
            )
        ]
        out.append(group([group(beam, blur=24)], rot=(deg, pivot_x, src_y), opacity=a))

    birds = []
    for cx, cy, s, a in [(648, 330, 1.0, 0.7), (734, 262, 0.72, 0.6), (702, 360, 0.55, 0.5)]:
        birds.append(
            quad(
                (cx - 15 * s, cy), (cx - 7 * s, cy - 10 * s), (cx, cy - 2 * s),
                5 * s, LIGHT, a,
            )
        )
        birds.append(
            quad(
                (cx, cy - 2 * s), (cx + 7 * s, cy - 10 * s), (cx + 15 * s, cy),
                5 * s, LIGHT, a,
            )
        )
    out.append(group(birds))
    return out


# --------------------------------------------------------------------------
# 5) clearing
# --------------------------------------------------------------------------
def clearing():
    g = [
        radial(
            713, 768, 600,
            [(0.0, (*GLOW, 0.30)),
             (0.45, (*GLOW, 0.12)),
             (1.0, (*GLOW, 0.0))],
        )
    ]
    opening = [ellipse(668, 1126, 392, 92, (199, 212, 178), 0.10)]
    g.append(group(opening, blur=26))
    return g


# --------------------------------------------------------------------------
# 程序旅人（构图示意；正式由 ForestShell.drawTraveler 绘制，数值与其一致）
# --------------------------------------------------------------------------
TRAVELER_X = 0.34
GROUND_Y = 0.865


def traveler():
    cx = W * TRAVELER_X
    gy = H * GROUND_Y
    body_b, body_t = gy - 14, gy - 74
    return [
        group([
            line((cx - 2, body_b), (cx - 10, gy), 6, TRAVELER),
            line((cx + 2, body_b), (cx + 10, gy), 6, TRAVELER),
            rrect(cx - 10, body_t, cx + 10, body_b, 10, TRAVELER),
            ellipse(cx, body_t - 12, 9, 9, TRAVELER),
        ])
    ]


LAYERS = [
    ("tree_outline", tree_outline),
    ("tree_trunks", tree_trunks),
    ("leaf_path", leaf_path),
    ("light_shows", light_shows),
    ("clearing", clearing),
]

# 与 forest.json 一致的揭示参数
PHASE = {
    "tree_outline": (80, 0.60, 20),
    "tree_trunks": (240, 0.70, 25),
    "leaf_path": (400, 0.80, 25),
    "light_shows": (600, 0.65, 30),
    "clearing": (760, 0.90, 25),
}
PREVIEW_METERS = [0, 100, 265, 425, 630, 785]
