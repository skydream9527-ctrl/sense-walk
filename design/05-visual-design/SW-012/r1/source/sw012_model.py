#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SW-012 r1 · 雨林五层场景模型（Trae Design）

与已批准 SW-011 共享同一套“图元模型”契约（ellipse/poly/rrect/line/quad/
vgrad/hgrad/radial/erad/polygrad/group），由 sw012_render.py 同时输出：
  - 可编辑 SVG（source/svg/*.svg）
  - 真实导出 PNG（exports/ 与 previews/，2× 超采样后 LANCZOS 缩回）
两个后端消费同一模型；无外部付费 API、无位图素材。

场景身份（contracts/visual-design.md §1 + design/01-scenes-terrain/rainforest.md）：
  湿绿、轻雾、阔叶、藤蔓、水气；与森林“干叶/通透树荫/暖褐”明确区分——
  不使用森林的暖褐 #A89060 与干叶土坡，改用冷湿深绿、雾青、苔色与藤蔓暖绿光斑。

五层（ID 为 proposed，待 Antigravity 审稿冻结供 SW-006/SW-007 消费）：
  mist           90m  .55/20  overlay  雾/湿气（贴地湿雾 + 飘雾，软衰减无矩形底）
  trunks_canopy  270m .85/25  parallax .30  粗壮板根湿干 + 连片阔叶顶棚（留林隙）
  vines_light    450m 1.0/25  parallax .60  前景垂藤/阔叶 + 藤蔓暖绿光斑
  distant_glow   675m .85/25  overlay  林隙透光 + 中景流动水汽
  glade          855m .90/20  overlay  幽径空地微光 + 湿径反光（终点不炫技）
void 与旅人程序绘制；旅人锚点 x=.34 / 脚底 y=.865 与森林一致，本轮不改。
"""
import math
import random

W, H = 1080, 1920
REQUIRED_DISTANCE = 900

# —— 雨林色板 token（rainforest.md §2 + 其明暗组织派生，全部低饱和冷湿绿）——
VOID = (5, 8, 7)            # #050807 近黑偏绿（黑幕）
MIST = (26, 46, 40)         # #1A2E28 雾气主色
MIST_HI = (47, 78, 68)      # #2F4E44 亮雾/飘雾
BARK = (30, 61, 54)         # #1E3D3D->#1E3D36 树干树冠主色
BARK_DARK = (22, 46, 40)    # #162E28 树干暗部
BARK_FG = (18, 38, 33)      # #122621 前景最暗纯剪影树
CANOPY = (42, 82, 72)       # #2A5248 树冠受光
LEAF_DEEP = (28, 66, 54)    # #1C4236 后排深阔叶
LEAF_MID = (51, 96, 79)     # #33604F 中排阔叶
LEAF_HI = (74, 107, 79)     # #4A6B4F 冠缘受光阔叶
MOSS = (96, 118, 74)        # #60764A 树干苔藓（低饱和苔绿）
VINE = (58, 92, 76)         # #3A5C4C 藤蔓
VINE_HI = (106, 138, 96)    # #6A8A60 藤叶受光
GLOW_VINE = (196, 212, 168) # #C4D4A8 藤蔓光斑（rainforest.md 点缀色）
GLOW_SOFT = (168, 201, 166) # #A8C9A6 林隙柔光
WATER = (90, 125, 114)      # #5A7D72 水气/湿面冷青
GLADE = (159, 192, 154)     # #9FC09A 幽径空地微光
PATH_WET = (58, 88, 76)     # #3A584C 湿径
TRAVELER = (122, 133, 124)  # 程序旅人（与森林示意同色，正式由 App 绘制）


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
    """椭圆径向渐变（归一化椭圆距离），末端 stop alpha=0 保证无矩形硬边。"""
    return ("erad", (cx, cy), (rx, ry), stops)


def polygrad(pts, y0, y1, stops):
    return ("polygrad", pts, (y0, y1), stops)


def group(children, mask=None, blur=0.0, opacity=1.0, rot=None):
    return ("g", children, mask, blur, opacity, rot)


# --------------------------------------------------------------------------
# 1) mist · 雾/湿气（overlay）
# --------------------------------------------------------------------------
def mist():
    out = []
    # 贴地湿雾：大扁椭圆，重心 y≈.79；四边（尤其屏底/左右）软衰减到近 0，
    # 不允许矩形底。stop 在归一化 .78 后迅速归零。
    out.append(
        erad(
            540, 1520, 600, 440,
            [(0.0, (*MIST, 0.50)),
             (0.45, (*MIST, 0.32)),
             (0.78, (*MIST, 0.10)),
             (1.0, (*MIST, 0.0))],
        )
    )
    # 地面附近更亮的一团湿雾心（托住旅人脚底，但仍是暗色低 α）
    out.append(
        erad(
            470, 1560, 360, 250,
            [(0.0, (*MIST_HI, 0.16)),
             (0.6, (*MIST_HI, 0.07)),
             (1.0, (*MIST_HI, 0.0))],
        )
    )
    # 三缕横向飘雾（细长、大柔化，只在中段高度；几何上收进屏内，
    # 留出 blur 扩散余量，不把恒定 alpha 区送到左右屏边）
    wisps = []
    for cx, cy, rx, ry, a in [
        (300, 1070, 250, 86, 0.12),
        (760, 1260, 240, 104, 0.14),
        (470, 1400, 300, 72, 0.10),
    ]:
        wisps.append(ellipse(cx, cy, rx, ry, MIST_HI, a))
    out.append(group(wisps, blur=34))
    # 上部极薄弥漫雾感（一整团很淡的空气雾，边缘归零）
    out.append(
        erad(
            560, 770, 560, 520,
            [(0.0, (*MIST, 0.07)),
             (0.7, (*MIST, 0.03)),
             (1.0, (*MIST, 0.0))],
        )
    )
    return out


# --------------------------------------------------------------------------
# 2) trunks_canopy · 板根湿干 + 连片阔叶顶棚（parallax .30）
# --------------------------------------------------------------------------
def _broadleaf_row(r, fill, base_y, x0, x1, gap, rmin, rmax, notches=()):
    """大尺度阔叶团簇；notches=( (cx0,cx1,y0,y1,skip_prob), ... ) 区域留林隙。"""
    shapes = []
    x = x0
    while x < x1:
        cx = x + r.uniform(-24, 24)
        cy = base_y + r.uniform(-54, 54)
        in_notch = False
        for n0, n1, ny0, ny1, prob in notches:
            if n0 <= cx <= n1 and ny0 <= cy <= ny1 and r.random() < prob:
                in_notch = True
                break
        if not in_notch:
            for _ in range(r.randint(4, 7)):
                shapes.append(
                    ellipse(
                        cx + r.uniform(-86, 86), cy + r.uniform(-66, 48),
                        r.uniform(rmin, rmax), r.uniform(rmin * 0.82, rmax * 1.12),
                        fill,
                    )
                )
            for _ in range(2):
                shapes.append(
                    ellipse(
                        cx + r.uniform(-48, 48), cy - r.uniform(80, 128),
                        r.uniform(40, 72), r.uniform(46, 78), fill,
                    )
                )
        x += r.uniform(gap[0], gap[1])
    return shapes


def _buttress_trunk(cx, wtop, wbot, ytop, ybot, lean, n=16):
    """带明显板根扩张的粗壮雨林树干多边形（底部展开比落叶林更大）。"""
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        sway = lean * (2 * t * (1 - t)) * 0.9 + lean * 0.10 * t
        # 板根：最下 18% 段向外张开
        flare = 1.0
        if t > 0.82:
            u = (t - 0.82) / 0.18
            flare += 0.55 * u * u
        w = (wtop + (wbot - wtop) * t) * flare
        y = ytop + (ybot - ytop) * t
        left.append((cx - w / 2 + sway, y))
        right.append((cx + w / 2 + sway, y))
    pts = left + [(cx, ybot + wbot * 0.10)] + list(reversed(right))
    return pts


def trunks_canopy():
    r = random.Random(900270)
    inside = []

    # —— 阔叶顶棚：三排，由深到亮；上中部留两处林隙给 675m distant_glow ——
    notches = ((585, 735, 40, 380, 0.82), (180, 285, 120, 420, 0.72))
    crowns = _broadleaf_row(r, LEAF_DEEP, 560, -120, 1200, (170, 235), 104, 168, notches)
    crowns += _broadleaf_row(r, CANOPY, 690, -100, 1180, (185, 250), 118, 188, notches)
    crowns += _broadleaf_row(r, LEAF_MID, 818, -80, 1160, (170, 225), 92, 150)
    inside.append(group(crowns))

    # 冠缘垂落的叶串（阔叶层叠感）
    drapes = []
    for _ in range(26):
        cx = r.uniform(-40, 1120)
        # 林隙位置少垂叶
        if (585 <= cx <= 735 or 180 <= cx <= 285) and r.random() < 0.7:
            continue
        top = r.uniform(800, 900)
        for k in range(r.randint(2, 4)):
            drapes.append(
                ellipse(cx + r.uniform(-26, 26), top + k * r.uniform(34, 52),
                        r.uniform(26, 44), r.uniform(34, 58),
                        LEAF_HI if r.random() < 0.4 else LEAF_MID,
                        r.uniform(0.5, 0.9))
            )
    inside.append(group(drapes))

    # —— 粗壮板根树干 ——
    specs = [
        (132, 44, 86, 300, 1660, -8, BARK),
        (300, 30, 54, 430, 1620, 6, BARK),
        (505, 52, 96, 250, 1690, -10, BARK),
        (690, 34, 64, 360, 1640, 8, BARK),
        (882, 44, 80, 210, 1670, -6, BARK),
        (1042, 66, 124, 120, 1740, -14, BARK_FG),
    ]
    trunks, rims, moss, bch = [], [], [], []
    for i, (cx, wt, wb, yt, yb, lean, color) in enumerate(specs):
        pts = _buttress_trunk(cx, wt, wb, yt, yb, lean)
        if color == BARK_FG:
            trunks.append(poly(pts, BARK_FG))
        else:
            trunks.append(
                polygrad(
                    pts, yt, yb,
                    [(0.0, (*BARK_DARK, 1.0)),
                     (0.40, (*BARK, 1.0)),
                     (1.0, (*BARK_DARK, 0.94))],
                )
            )
            # 右侧细边光（右上光源）
            rims.append(
                quad(
                    (cx + wt / 2 - 6, yt + 110),
                    (cx + wb / 2 - 12 - lean * 0.5, (yt + yb) / 2),
                    (cx + wb / 2 - 16 - lean, yb - 220),
                    6, GLOW_SOFT, 0.18,
                )
            )
            # 树干苔藓：中上段贴几片低 α 苔绿柔斑（湿气身份）
            for _ in range(3):
                moss.append(
                    ellipse(cx + r.uniform(-wt * 0.28, wt * 0.28),
                            r.uniform(yt + 180, yt + 620),
                            r.uniform(12, 30), r.uniform(18, 40),
                            MOSS, r.uniform(0.08, 0.16))
                )
        # 少量粗枝接入顶棚
        if i in (2, 4):
            bch.append(
                quad((cx + lean, yt + 120), (cx + 90, yt + 70), (cx + 170, yt + 30),
                     11, BARK_DARK, 0.95)
            )
    inside.append(group(trunks))
    if bch:
        inside.append(group(bch))
    inside.append(group(moss, blur=8))
    inside.append(group(rims))

    # 顶棚允许顶到上缘（冠隙真透明）；底部在触到地面前淡出，不画地面
    return [group(inside, mask=[(0, 1), (1560, 1), (1790, 0)])]


# --------------------------------------------------------------------------
# 3) vines_light · 前景垂藤/阔叶 + 藤蔓光斑（parallax .60）
# --------------------------------------------------------------------------
def _quad_point(p0, c, p1, t):
    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t ** 2 * p1[0]
    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t ** 2 * p1[1]
    return x, y


def vines_light():
    r = random.Random(450675)
    vines, leaves, drops = [], [], []
    # x 起点 / 藤长 / 摆动 / 粗；两端超出画布宽，最长藤止于 y≈.39，不进下 45% 触控区
    specs = [
        (-20, 430, 46, 6), (118, 760, 72, 7), (238, 560, -52, 5),
        (476, 680, 62, 6), (648, 520, -48, 5), (824, 700, 56, 6),
        (978, 600, -62, 7), (1100, 470, -44, 6),
    ]
    for x0, length, sway, wd in specs:
        p0 = (x0, -20)
        c = (x0 + sway * 0.5, -20 + length * 0.52)
        p1 = (x0 + sway, -20 + length)
        vines.append(quad(p0, c, p1, wd, VINE, 0.96))
        # 对生小叶
        nleaf = int(length // 120)
        for k in range(nleaf):
            t = 0.18 + k * (0.7 / max(1, nleaf - 1))
            qx, qy = _quad_point(p0, c, p1, t)
            tan = (c[0] - p0[0], c[1] - p0[1]) if t < 0.5 else (p1[0] - c[0], p1[1] - c[1])
            side = -1 if k % 2 else 1
            lx = qx + side * (wd + 13)
            ly = qy + 6
            col = VINE_HI if r.random() < 0.5 else LEAF_MID
            leaves.append(ellipse(lx, ly, r.uniform(7, 11), r.uniform(15, 23), col,
                                  r.uniform(0.65, 0.92)))
        # 藤尖偶发一颗水珠（少量、克制）
        if r.random() < 0.4:
            drops.append(ellipse(p1[0], p1[1] + 8, 4.5, 6.5, WATER, 0.55))

    # 藤蔓暖绿光斑：漏在藤间与冠隙的柔斑（本层身份核心）
    glows = []
    made = 0
    while made < 20:
        cx = r.uniform(40, 1040)
        cy = r.uniform(140, 940)
        rr = r.uniform(16, 52)
        a = r.uniform(0.30, 0.72)
        glows.append(ellipse(cx, cy, rr, rr, GLOW_VINE, a))
        made += 1

    return [group(glows, blur=15), group(vines), group(leaves), group(drops, blur=2)]


# --------------------------------------------------------------------------
# 4) distant_glow · 林隙透光 + 流动水汽（overlay）
# --------------------------------------------------------------------------
def distant_glow():
    out = []
    # 林隙透光：位置与 trunks_canopy 顶棚缺口呼应；近竖椭圆的斑驳漏光（非长斜光束）
    beams = [
        (655, 300, 150, 268, 0.26),
        (232, 366, 108, 205, 0.18),
        (892, 232, 92, 172, 0.14),
    ]
    for cx, cy, rx, ry, peak in beams:
        out.append(group([
            erad(
                cx, cy, rx, ry,
                [(0.0, (*GLOW_SOFT, peak)),
                 (0.5, (*GLOW_SOFT, peak * 0.55)),
                 (0.82, (*GLOW_SOFT, peak * 0.14)),
                 (1.0, (*GLOW_SOFT, 0.0))],
            )
        ], blur=22))
    # 中景流动水汽：几条横向拉长、左右错开的极淡柔带；
    # 收进屏内并给 blur 留扩散余量，避免恒定 alpha 区压到屏边
    vapors = []
    for cx, cy, rx, ry, col, a in [
        (390, 1080, 290, 80, WATER, 0.08),
        (730, 1272, 270, 92, MIST_HI, 0.10),
        (400, 1418, 290, 70, WATER, 0.07),
    ]:
        vapors.append(ellipse(cx, cy, rx, ry, col, a))
    out.append(group(vapors, blur=32))
    return out


# --------------------------------------------------------------------------
# 5) glade · 幽径空地微光 + 湿径反光（overlay）
# --------------------------------------------------------------------------
def glade():
    out = []
    # 幽径辉光：中心偏右前方（x≈.56,y≈.60），椭圆径向，四边归零
    out.append(
        erad(
            600, 1160, 470, 400,
            [(0.0, (*GLADE, 0.24)),
             (0.45, (*GLADE, 0.12)),
             (0.8, (*GLADE, 0.04)),
             (1.0, (*GLADE, 0.0))],
        )
    )
    # 湿径：自画面底中偏右收窄向幽径的柔带，上下缘都淡出（屏底 alpha=0 无矩形边）
    path_pts = [(452, 1920), (706, 1920), (650, 1300), (612, 1252), (558, 1300)]
    wet = [
        poly(path_pts, PATH_WET, 0.9),
        # 湿径表面冷青微光
        poly([(498, 1900), (660, 1900), (626, 1330), (612, 1306), (592, 1330)],
             WATER, 0.22),
    ]
    # 湿径上零星横向反光
    for cx, cy, rx, a in [(606, 1580, 72, 0.26), (616, 1452, 52, 0.22), (600, 1360, 36, 0.18)]:
        wet.append(ellipse(cx, cy, rx, 13, GLOW_SOFT, a))
    out.append(group(wet, blur=20,
                     mask=[(1230, 0), (1330, 1), (1680, 1), (1900, 0.02), (1920, 0)]))
    return out


# --------------------------------------------------------------------------
# 程序旅人（构图示意；正式由 App 绘制，数值与森林 drawTraveler 一致）
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
    ("mist", mist),
    ("trunks_canopy", trunks_canopy),
    ("vines_light", vines_light),
    ("distant_glow", distant_glow),
    ("glade", glade),
]

# rainforest.md §4 时间轴（proposed layer IDs / parallax 供审稿冻结）
PHASE = {
    "mist": (90, 0.55, 20),
    "trunks_canopy": (270, 0.85, 25),
    "vines_light": (450, 1.00, 25),
    "distant_glow": (675, 0.85, 25),
    "glade": (855, 0.90, 20),
}
PARALLAX = {
    "mist": 0.0,
    "trunks_canopy": 0.30,
    "vines_light": 0.60,
    "distant_glow": 0.0,
    "glade": 0.0,
}
OVERLAY_LAYERS = {"mist", "distant_glow", "glade"}
# 六阶段预览一律取在各层 fade 完成点（最后 875m ≤ 900m 终点）
PREVIEW_METERS = [0, 110, 295, 475, 700, 875]
UNLOCK_METERS = [0, 90, 270, 450, 675, 855]
