#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SW-021 R1 · 森林三层连续视差 tile 图元模型（可编辑源）
=================================================================
交付角色：trae-design → MiniMax（候选制作输入）/ ZCode（运行时映射输入）

本模块只定义三层 tile 的图元模型与两种可编辑/可消费后端：
  1. PIL RGBA 渲染（PNG 预览以 PIL 后端为准，与 SW-011 同约定）
  2. SVG 矢量导出（真可编辑源，消费同一图元描述；渐变/模糊为近似图元，
     MiniMax 可在矢量软件中直接修改后导出 1080×1920 RGBA PNG/WebP）

无缝保证（核心方法，给 MiniMax 的零 API 手工路线也用同一技巧）：
  所有图元先画在 3W 宽画布（坐标 +W），再把左右各一个 tile 宽折回中央：
      tile = center over left over right   （两段跨过 x=0/W 接缝的图元被折回拼合）
  垂直方向不 wrap（repeat 轴只有 x；上缘/底部垂直 mask 在折叠后施加）。
  地面上缘是整周期正弦（f=1,2 周/tile，f=0 分量恒定），首尾 y 相同且斜率相同。

规则对齐：
  - 契约 visual-design.md 六色板 + SW-011 extended 派生色（不引入新色相）
  - 五层 ID / 80/240/400/600/760m / opacity .6/.7/.8/.65/.9 / fade 不变
  - 仅 tree_outline/tree_trunks/leaf_path 为 repeat_x tile；
    light_shows/clearing 复用 SW-002 R1 已批准 webp（本模型不重画）
  - 0m 近黑、不加绕过门禁的天空/雾/地面；素材峰值强度不烘焙相位透明度
  - 统一光源右上斜射；旅人锚点 x=.34 / 脚底 y=.865（合成脚本消费）

输出（由 main / sw021_render_previews.py 调用）：
  source/svg/forest_{layer}_tile.svg            可编辑矢量源
  previews/tiles/forest_{layer}_tile.png        PIL 后端 1080×1920 RGBA
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# 画布与色板（契约六色；extended 派生自 SW-011 accepted spec，未引入新色相）
# ---------------------------------------------------------------------------
TILE_W, TILE_H = 1080, 1920
SEAM_SAFE_PX = 96  # 孤立硬边缘主体中心离缝安全距离（叶/枝等 wrap 软元素除外）

VOID = (6, 8, 6, 255)
OUTLINE = (0x1A, 0x28, 0x20, 255)
TRUNKS = (0x2D, 0x4A, 0x3E, 255)
LIGHT = (0x8F, 0xA8, 0x7A, 255)
LEAF = (0x6B, 0x8F, 0x71, 255)
WARM = (0xA8, 0x90, 0x60, 255)

# SW-011 extended
OUTLINE_BACK = (0x22, 0x33, 0x2A, 255)
OUTLINE_LIT = (0x26, 0x38, 0x2E, 255)
TRUNK_DARK = (0x24, 0x40, 0x36, 255)
TRUNK_FG = (0x24, 0x3A, 0x30, 255)
TRUNK_RIM = (0x8F, 0xA8, 0x7A, 0)  # 边光按 alpha 发射
EARTH_TOP = (0x4A, 0x40, 0x30, 0)
EARTH_MID = (0x3A, 0x32, 0x26, 255)
EARTH_BOTTOM = (0x31, 0x2A, 0x1F, 255)
PATH_EARTH = (0x6A, 0x5B, 0x42, 0)
TWIG = (0x5A, 0x4E, 0x38, 0)
GLOW = (0xA8, 0xC5, 0xA0, 0)


def with_a(color, a):
    """返回指定 alpha 的 RGBA；a 为 0..1 不透明度，若原色自带 alpha 则相乘。"""
    r, g, b, oa = color
    return (r, g, b, int(round(a * oa)))


# ---------------------------------------------------------------------------
# 图元中间表示（IR）—— PIL / SVG 两个 renderer 消费同一份
# ---------------------------------------------------------------------------
@dataclass
class Op:
    kind: str
    args: dict = field(default_factory=dict)


# 冠线分组：同组球团以二元 union 着色（避免半透明重叠产生"泡泡"边界），
# 组色 + 整体不透明度；lit 组为 clip 在主组 mask 内的受光柔光。
GROUP_COLORS = {
    "outline_back": (OUTLINE_BACK, 0.92),
    "outline_back_lit": (OUTLINE_LIT, 0.40),
    "outline_front": (OUTLINE, 0.96),
    "outline_front_lit": (OUTLINE_LIT, 0.45),
}
GROUP_CLIP = {
    "outline_back_lit": "outline_back",
    "outline_front_lit": "outline_front",
}
GROUP_BLUR = {
    "outline_back_lit": 18,
    "outline_front_lit": 14,
}


@dataclass
class TileModel:
    layer_id: str
    width: int = TILE_W
    height: int = TILE_H
    ops: list[Op] = field(default_factory=list)
    vertical_mask: tuple | None = None  # (top0, top1, bottom1, bottom0) 归一化 y
    blur_radius: int = 0

    # -- 工厂方法 -----------------------------------------------------------
    def ellipse(self, x, y, w, h, fill, wrap=False, blur=0, group=None):
        self.ops.append(Op("ellipse", dict(x=x, y=y, w=w, h=h, fill=fill,
                                           wrap=wrap, blur=blur, group=group)))

    def rrect(self, x, y, w, h, radius, fill, wrap=False, blur=0):
        self.ops.append(Op("rrect", dict(x=x, y=y, w=w, h=h, radius=radius,
                                         fill=fill, wrap=wrap, blur=blur)))

    def rect(self, x, y, w, h, fill, wrap=False, blur=0):
        self.ops.append(Op("rect", dict(x=x, y=y, w=w, h=h, fill=fill,
                                        wrap=wrap, blur=blur)))

    def polygon(self, pts, fill, wrap=False, blur=0):
        self.ops.append(Op("polygon", dict(pts=pts, fill=fill,
                                           wrap=wrap, blur=blur)))

    def line(self, x1, y1, x2, y2, width, fill, wrap=False, blur=0):
        self.ops.append(Op("line", dict(x1=x1, y1=y1, x2=x2, y2=y2,
                                        width=width, fill=fill,
                                        wrap=wrap, blur=blur)))

    def ground(self, top_fn, fill_top_a, fill_mid, fill_bottom, blur=0):
        """从周期上缘函数 top_fn(x_norm 0..1)->y_px 到底部的填充。"""
        self.ops.append(Op("ground", dict(top_fn=top_fn, a_top=fill_top_a,
                                          mid=fill_mid, bottom=fill_bottom,
                                          blur=blur)))


# ---------------------------------------------------------------------------
# PIL renderer（使用 3W 折叠法保证 wrap 无缝）
# ---------------------------------------------------------------------------
def _draw_op_pil(draw_or_layer, op: Op, origin_x=0):
    a = op.args
    kind = op.kind
    if kind == "ellipse":
        x, y, w, h = a["x"] + origin_x, a["y"], a["w"], a["h"]
        draw_or_layer.ellipse([x, y, x + w, y + h], fill=a["fill"])
    elif kind == "rrect":
        x, y, w, h = a["x"] + origin_x, a["y"], a["w"], a["h"]
        draw_or_layer.rounded_rectangle([x, y, x + w, y + h],
                                        radius=a["radius"], fill=a["fill"])
    elif kind == "rect":
        x, y, w, h = a["x"] + origin_x, a["y"], a["w"], a["h"]
        draw_or_layer.rounded_rectangle([x, y, x + w, y + h],
                                        radius=2, fill=a["fill"])
    elif kind == "polygon":
        pts = [(x + origin_x, y) for x, y in a["pts"]]
        draw_or_layer.polygon(pts, fill=a["fill"])
    elif kind == "line":
        draw_or_layer.line([a["x1"] + origin_x, a["y1"],
                            a["x2"] + origin_x, a["y2"]],
                           fill=a["fill"], width=a["width"])
    elif kind == "ground":
        W3 = draw_or_layer.im.size[0]
        fn = a["top_fn"]
        H = draw_or_layer.im.size[1]
        pts = []
        for x in range(0, W3 + 1, 6):
            pts.append((x, fn((x - TILE_W) / TILE_W)))
        pts += [(W3, H), (0, H)]
        draw_or_layer.polygon(pts, fill=a["bottom"])


def _vertical_gradient_mask(w, h, bands):
    """bands: [(y0,y1,a0,a1), ...] 分段线性 alpha；返回 L 模式 mask。"""
    mask = Image.new("L", (w, h), 0)
    px = mask.load()
    for (y0, y1, a0, a1) in bands:
        y0i, y1i = int(y0), int(y1)
        for y in range(max(0, y0i), min(h, y1i + 1)):
            t = 0 if y1i == y0i else (y - y0i) / (y1i - y0i)
            px_y = int(round(a0 + (a1 - a0) * t))
            for x in range(w):
                px[x, y] = max(px[x, y], px_y)
    return mask


def render_pil(model: TileModel) -> Image.Image:
    W, H = model.width, model.height
    big = Image.new("RGBA", (W * 3, H), (0, 0, 0, 0))

    def mask_shape(draw, op: Op, ox):
        """把图元形状画到 L mask 上（二元 255）。"""
        a = op.args
        if a["kind_union"] == "ellipse":
            x, y, w, h = a["x"] + ox, a["y"], a["w"], a["h"]
            draw.ellipse([x, y, x + w, y + h], fill=255)

    # --- 冠线分组（union mask 着色，先于其他图元，顺序固定） ---
    group_masks: dict[str, Image.Image] = {}
    for gname in GROUP_COLORS:
        gmask = Image.new("L", (W * 3, H), 0)
        gd = ImageDraw.Draw(gmask)
        for op in model.ops:
            if op.args.get("group") != gname:
                continue
            shape = dict(op.args, kind_union=op.kind)
            dummy = Op(op.kind, dict(op.args, kind_union=op.kind))
            for ox in (0, W, W * 2):
                mask_shape(gd, dummy, ox)
        if gname in GROUP_BLUR:
            gmask = gmask.filter(ImageFilter.GaussianBlur(GROUP_BLUR[gname]))
        group_masks[gname] = gmask

    clip_masks = {}
    for gname in GROUP_COLORS:
        gmask = group_masks[gname]
        if gname in GROUP_CLIP:
            clip = group_masks[GROUP_CLIP[gname]]
            gmask = Image.composite(gmask, Image.new("L", (W * 3, H), 0), clip)
        clip_masks[gname] = gmask
        col, ga = GROUP_COLORS[gname]
        layer = Image.new("RGBA", (W * 3, H),
                          (col[0], col[1], col[2], int(round(ga * 255))))
        layer.putalpha(gmask.point(lambda v: int(v * ga)))
        big = Image.alpha_composite(big, layer)

    # 非模糊图元直接画；模糊图元进独立层后模糊再合成（按 op 单独模糊，避免糊到缝外）
    # wrap 图元在 0 / +W / +2W 各画一份，折叠后跨缝部分回到中央 tile（数学无缝）
    sharp = Image.new("RGBA", (W * 3, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(sharp)
    blur_layers = []
    for op in model.ops:
        if op.kind == "ground" or op.args.get("group"):
            continue  # ground 与分组图元走各自通路
        origins = (0, W, W * 2) if op.args.get("wrap") else (W,)
        if op.args.get("blur"):
            for ox in origins:
                layer = Image.new("RGBA", (W * 3, H), (0, 0, 0, 0))
                ld = ImageDraw.Draw(layer)
                _draw_op_pil(ld, op, origin_x=ox)
                blur_layers.append(layer.filter(
                    ImageFilter.GaussianBlur(op.args["blur"])))
        else:
            for ox in origins:
                _draw_op_pil(d, op, origin_x=ox)
    big = Image.alpha_composite(big, sharp)
    for blurred in blur_layers:
        big = Image.alpha_composite(big, blurred)

    # ground 渐变：在 0/+W/+2W 各画一份周期地面，用按上缘生成的纵向 mask 着色
    grounds = [op for op in model.ops if op.kind == "ground"]
    if grounds:
        gbase = Image.new("RGBA", (W * 3, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gbase)
        for ox in (0, W, W * 2):
            for op in grounds:
                _draw_op_pil(gd, op, origin_x=ox)
        # 上缘透明 → .79h 全强度；用分段 mask（ground 内不区分 mid/bottom，
        # 另叠加一层 mid→bottom 的深色竖向渐变增加体积）
        gmask = Image.new("L", (W * 3, H), 0)
        gpx = gmask.load()
        fn = grounds[0].args["top_fn"]
        for x in range(W * 3):
            top = fn((x - W) / W)
            for y in range(int(top), int(top) + 150):
                if 0 <= y < H:
                    t = min(1.0, (y - top) / 150.0)
                    av = int(255 * t * t)
                    if av > gpx[x, y]:
                        gpx[x, y] = av
            for y in range(int(top) + 150, H):
                gpx[x, y] = 255
        # 底部加深：mid→bottom
        deepen = Image.new("RGBA", (W * 3, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(deepen)
        dd.rectangle([0, int(H * 0.80), W * 3, H],
                     fill=with_a(EARTH_BOTTOM, 0.55))
        deepen.putalpha(Image.composite(deepen.getchannel("A"),
                                        Image.new("L", (W * 3, H), 0),
                                        gmask))
        gbase.putalpha(gmask)
        big = Image.alpha_composite(big, gbase)
        big = Image.alpha_composite(big, deepen)

    # 折叠：center 为基，left/right 折回（alpha over）
    left = big.crop((0, 0, W, H))
    center = big.crop((W, 0, W * 2, H))
    right = big.crop((W * 2, 0, W * 3, H))
    tile = Image.alpha_composite(center, left)
    tile = Image.alpha_composite(tile, right)

    # 垂直 mask（折叠后施加，不 wrap）
    if model.vertical_mask:
        y0, y1, y2, y3 = model.vertical_mask
        bands = [(0, int(y0 * H), 0, 0),
                 (int(y0 * H), int(y1 * H), 0, 255),
                 (int(y1 * H), int(y2 * H), 255, 255),
                 (int(y2 * H), int(y3 * H), 255, 0),
                 (int(y3 * H), H, 0, 0)]
        m = _vertical_gradient_mask(W, H, bands)
        tile.putalpha(Image.composite(tile.getchannel("A"),
                                      Image.new("L", (W, H), 0), m))
    return tile


# ---------------------------------------------------------------------------
# SVG renderer（可编辑矢量近似；PIL 为预览准绳）
# ---------------------------------------------------------------------------
def _rgba(color):
    r, g, b, a = color
    return f"rgba({r},{g},{b},{a / 255:.3f})"


def render_svg(model: TileModel) -> str:
    W, H = model.width, model.height
    used_blurs = sorted({op.args.get("blur") for op in model.ops
                         if op.args.get("blur")} |
                        {v for v in GROUP_BLUR.values()})
    defs = ['<clipPath id="tileclip"><rect x="0" y="0" '
            f'width="{W}" height="{H}"/></clipPath>']
    for r in used_blurs:
        defs.append(f'<filter id="b{int(r)}" x="-30%" y="-30%" '
                    f'width="160%" height="160%"><feGaussianBlur '
                    f'stdDeviation="{r}"/></filter>')
    body = []

    def emit(op, ox):
        a = op.args
        flt = f' filter="url(#b{int(a["blur"])})"' if a.get("blur") else ""
        if op.kind == "ellipse":
            body.append(f'<ellipse cx="{a["x"]+ox+a["w"]/2:.1f}" '
                        f'cy="{a["y"]+a["h"]/2:.1f}" rx="{a["w"]/2:.1f}" '
                        f'ry="{a["h"]/2:.1f}" fill="{_rgba(a["fill"])}"{flt}/>')
        elif op.kind == "rrect":
            body.append(f'<rect x="{a["x"]+ox:.1f}" y="{a["y"]:.1f}" '
                        f'width="{a["w"]:.1f}" height="{a["h"]:.1f}" '
                        f'rx="{a["radius"]:.1f}" fill="{_rgba(a["fill"])}"{flt}/>')
        elif op.kind == "rect":
            body.append(f'<rect x="{a["x"]+ox:.1f}" y="{a["y"]:.1f}" '
                        f'width="{a["w"]:.1f}" height="{a["h"]:.1f}" '
                        f'fill="{_rgba(a["fill"])}"{flt}/>')
        elif op.kind == "polygon":
            pts = " ".join(f"{x+ox:.1f},{y:.1f}" for x, y in a["pts"])
            body.append(f'<polygon points="{pts}" fill="{_rgba(a["fill"])}"{flt}/>')
        elif op.kind == "line":
            body.append(f'<line x1="{a["x1"]+ox:.1f}" y1="{a["y1"]:.1f}" '
                        f'x2="{a["x2"]+ox:.1f}" y2="{a["y2"]:.1f}" '
                        f'stroke-width="{a["width"]}" stroke="{_rgba(a["fill"])}"'
                        f' stroke-linecap="round"{flt}/>')
        elif op.kind == "ground":
            fn = a["top_fn"]
            pts = [f"M {ox:.1f},{fn(0):.1f}"]
            for i in range(0, W + 1, 12):
                pts.append(f"L {i+ox:.1f},{fn(i / W):.1f}")
            pts.append(f"L {W+ox:.1f},{H} L {ox:.1f},{H} Z")
            body.append(f'<path d="{" ".join(pts)}" fill="{_rgba(a["bottom"])}"/>')

    # 冠线分组：SVG 中同色不透明椭圆重叠无叠加变化（等同 union），
    # lit 组用半透明柔椭圆（feGaussianBlur）近似 PIL clip 受光。
    for gname, (col, ga) in GROUP_COLORS.items():
        is_lit = gname in GROUP_CLIP
        for op in model.ops:
            if op.args.get("group") != gname or op.kind != "ellipse":
                continue
            a = op.args
            flt = (f' filter="url(#b{GROUP_BLUR[gname]})"' if is_lit else "")
            fill_op = ga if is_lit else 1.0
            for ox in (-W, 0, W):
                body.append(
                    f'<ellipse cx="{a["x"]+ox+a["w"]/2:.1f}" '
                    f'cy="{a["y"]+a["h"]/2:.1f}" rx="{a["w"]/2:.1f}" '
                    f'ry="{a["h"]/2:.1f}" fill="rgba({col[0]},{col[1]},{col[2]},'
                    f'{fill_op:.3f})"{flt}/>')

    for op in model.ops:
        if op.args.get("group"):
            continue
        if op.kind == "ground" or op.args.get("wrap"):
            for ox in (-W, 0, W):
                emit(op, ox)
        else:
            emit(op, 0)

    # tile 裁剪 + 可选垂直 mask
    mask_block = ""
    if model.vertical_mask:
        y0, y1, y2, y3 = model.vertical_mask
        defs.append(
            '<linearGradient id="vmaskg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="{y0:.3f}" stop-color="#000" stop-opacity="0"/>'
            f'<stop offset="{y1:.3f}" stop-color="#fff" stop-opacity="1"/>'
            f'<stop offset="{y2:.3f}" stop-color="#fff" stop-opacity="1"/>'
            f'<stop offset="{y3:.3f}" stop-color="#000" stop-opacity="0"/>'
            '</linearGradient>')
        defs.append('<mask id="vmask"><rect x="0" y="0" '
                    f'width="{W}" height="{H}" fill="url(#vmaskg)"/></mask>')
        mask_block = ' mask="url(#vm)"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">\n'
        f'<defs>{"".join(defs)}</defs>\n'
        f'<g clip-path="url(#tileclip)"{mask_block}>\n' + "\n".join(body) +
        '\n</g>\n</svg>\n')


# ---------------------------------------------------------------------------
# 三层模型定义
# ---------------------------------------------------------------------------
def model_tree_outline() -> TileModel:
    """远处两排阔叶冠线：柔圆团簇，只占 y≈.50–.88 冠线带，上/树间真透明。

    同排球团走 union mask 整体着色（重叠不变深、无"泡泡"边界）；
    lit 组是 clip 在冠线内的右上受光柔光。
    """
    m = TileModel("tree_outline", vertical_mask=(0.52, 0.66, 0.84, 0.92))

    # 后排：4 团，大间距、强高低差（y 差约 190px）形成林窗与起伏天际线
    back = [
        (140, 1290, 168, 132), (430, 1168, 182, 142),
        (712, 1262, 158, 124), (962, 1136, 172, 136),
    ]
    for cx, cy, rx, ry in back:
        for dx, dy, sx, sy in [
            (0, 0, 1.0, 1.0), (-0.62, 0.18, 0.62, 0.62),
            (0.60, 0.20, 0.66, 0.64), (-0.18, -0.52, 0.60, 0.66),
            (0.34, -0.40, 0.52, 0.56),
        ]:
            m.ellipse(cx + dx * rx, cy + dy * ry, rx * 2 * sx, ry * 2 * sy,
                     (0, 0, 0, 0), wrap=True, group="outline_back")
        # 顶部受光（团簇右上）
        m.ellipse(cx + rx * 0.10, cy - ry * 0.66, rx * 0.95, ry * 0.7,
                  (0, 0, 0, 0), wrap=True, group="outline_back_lit")

    # 前排：5 团更深，压在后排缝间；与后排错开高度，破除水平墙感
    front = [
        (40, 1360, 128, 108), (318, 1300, 122, 104), (586, 1368, 132, 110),
        (830, 1290, 120, 102), (1052, 1340, 128, 108),
    ]
    for cx, cy, rx, ry in front:
        for dx, dy, sx, sy in [
            (0, 0, 1.0, 1.0), (-0.66, 0.16, 0.60, 0.60),
            (0.62, 0.22, 0.62, 0.60), (-0.10, -0.55, 0.58, 0.62),
        ]:
            m.ellipse(cx + dx * rx, cy + dy * ry, rx * 2 * sx, ry * 2 * sy,
                     (0, 0, 0, 0), wrap=True, group="outline_front")
        m.ellipse(cx + rx * 0.06, cy - ry * 0.62, rx * 0.85, ry * 0.62,
                  (0, 0, 0, 0), wrap=True, group="outline_front_lit")
    return m


def model_tree_trunks() -> TileModel:
    """中景树干 + 右上细边光 + 极弱林间竖光；不画地面，顶/底淡入淡出。

    树干为上窄下宽微锥多边形（非等距圆柱），错落高低/粗细/微倾；
    最右一棵为跨缝树（中心在缝上，拼回是完整一棵），属合法跨缝硬主体。
    """
    # 上端从黑暗中渐次浮现（y0–.30 淡入，像没入林冠暗影，不在屏缘硬切）；
    # 下端在地面上缘（≈.722）前淡出，不穿过叶层地面
    m = TileModel("tree_trunks", vertical_mask=(0.0, 0.30, 0.685, 0.728))

    # 林间竖光：宽扁大柔斑（α≤.07），落在树间空隙，避免竖向光柱感
    for cx, cy, rx, ry, a in [
        (235, 760, 230, 300, 0.06), (560, 640, 210, 280, 0.07),
        (800, 800, 240, 300, 0.05),
    ]:
        m.ellipse(cx - rx, cy - ry, rx * 2, ry * 2, with_a(LIGHT, a),
                  wrap=True, blur=60)

    # 近林视角：5 棵/tile——2 巨树（其一跨缝）+ 2 中树 + 1 细树，
    # 留两处大林窗；粗细差约 5:1，明显倾侧与锥度，破除等距条纹。
    # cx, bottom_w, taper(顶宽/底宽), top_y, lean_px, kind
    B = 1560
    trunks = [
        (152,  66, 0.58, -120, -22, "normal"),
        (392, 158, 0.52, -240, -30, "fg"),      # 巨树一
        (470,  40, 0.66,  -70,  12, "thin"),    # 紧贴巨树成对
        (742,  78, 0.58, -130,  24, "normal"),
        (1052, 168, 0.50, -290,  28, "fg"),     # 巨树二：跨缝
    ]
    for cx, bw, taper, top, lean, kind in trunks:
        tw = bw * taper
        base = TRUNK_FG if kind == "fg" else TRUNKS
        # 微锥 + 中段轻微弯曲（六点多边形），顶部在屏外、底端在地面后淡出
        bottom = B
        mid_y = (top + bottom) * 0.46
        bend = lean * 0.5
        m.polygon([
            (cx - tw / 2 + lean, top), (cx + tw / 2 + lean, top),
            (cx + bw * 0.56 + bend, mid_y),
            (cx + bw / 2, bottom), (cx - bw / 2, bottom),
            (cx - bw * 0.56 + bend, mid_y),
        ], with_a(base, 0.99), wrap=True)
        if kind != "fg":
            # 左暗侧体积（沿弯曲微缩）
            m.polygon([
                (cx - tw / 2 + lean + 3, top + 10),
                (cx - tw / 2 + lean + tw * 0.42, top + 10),
                (cx - bw * 0.56 + bend + bw * 0.14, mid_y),
                (cx - bw / 2 + bw * 0.30, bottom - 6),
                (cx - bw / 2 + 3, bottom - 6),
                (cx - bw * 0.56 + bend - 2, mid_y),
            ], with_a(TRUNK_DARK, 0.5), wrap=True)
        else:
            # 前景最暗纯剪影：仅一条极暗轮廓提示体积
            m.polygon([
                (cx - tw / 2 + lean + 3, top + 10),
                (cx - tw / 2 + lean + tw * 0.30, top + 10),
                (cx - bw * 0.56 + bend + bw * 0.10, mid_y),
                (cx - bw / 2 + bw * 0.24, bottom - 8),
                (cx - bw / 2 + 3, bottom - 8),
                (cx - bw * 0.56 + bend - 2, mid_y),
            ], with_a((0x13, 0x24, 0x1D, 255), 0.6), wrap=True)
        # 细边光只给中树（normal），更细更暗，避免竖条阵列
        if kind == "normal":
            m.rrect(cx + tw * 0.10 + lean * 0.8, 110, max(4, tw * 0.10),
                    980, 3, with_a(LIGHT, 0.11), wrap=True, blur=5)
    return m


def _leaf_ground_top(x_norm: float) -> float:
    """地面上缘：整周期正弦（1、2 周/tile），首尾 y 与斜率连续。"""
    return (TILE_H * 0.722
            + 26.0 * math.sin(2 * math.pi * x_norm + 0.7)
            + 14.0 * math.sin(4 * math.pi * x_norm + 2.1))


def model_leaf_path() -> TileModel:
    """下部干叶土坡：周期上缘地面体 + 极弱土路弥散光 + 干叶/细枝；上部全透明。"""
    m = TileModel("leaf_path")  # 地面自身上缘渐隐，不用矩形垂直 mask

    # 地面体（PIL 端按上缘 150px alpha 渐入；SVG 端实底，MiniMax 导出须保上缘软）
    m.ground(_leaf_ground_top, 0.0, EARTH_MID, EARTH_BOTTOM)

    # 极弱土路弥散光：两个水平拉长的柔斑，跨 tile 周期重复，不做透视纵线
    for cx, cy, rx, ry, a in [
        (300, 1620, 300, 96, 0.10), (760, 1700, 320, 104, 0.08),
    ]:
        m.ellipse(cx - rx, cy - ry, rx * 2, ry * 2, with_a(PATH_EARTH, a),
                  wrap=True, blur=30)

    # 干叶：确定性分布；避开旅人前方 x∈[.28,.50] 的高对比叶（触控/脚底稀疏区）
    rng = lcg(20261020)
    for _ in range(96):
        x = rng() * TILE_W
        y = 1408 + rng() * 482
        in_quiet = TILE_W * 0.28 <= x <= TILE_W * 0.50 and y < 1760
        if in_quiet and rng() < 0.72:
            continue
        pick = rng()
        col = WARM if pick < 0.60 else (LEAF if pick < 0.88 else TWIG)
        lw, lh = (6 + rng() * 8, 3.5 + rng() * 4.5)
        a = 0.38 + rng() * 0.36
        m.ellipse(x, y, lw, lh, with_a(col, a), wrap=True)
    # 叶簇：6 组 4–6 片聚集（靠地面上缘，暖褐为主，强化干叶身份）
    rng_c = lcg(44121)
    for _ in range(6):
        cx = rng_c() * TILE_W
        cy = 1430 + rng_c() * 230
        if TILE_W * 0.28 <= cx <= TILE_W * 0.50 and cy < 1600:
            continue
        for _ in range(5):
            x = cx + (rng_c() - 0.5) * 56
            y = cy + (rng_c() - 0.5) * 34
            col = WARM if rng_c() < 0.72 else LEAF
            m.ellipse(x, y, 9 + rng_c() * 7, 5 + rng_c() * 4,
                      with_a(col, 0.45 + rng_c() * 0.3), wrap=True)
    # 细枝：11 根短斜线段
    rng2 = lcg(7721)
    for _ in range(11):
        x = rng2() * TILE_W
        y = 1490 + rng2() * 390
        ln = 26 + rng2() * 34
        m.line(x, y, x + ln, y + 8 + rng2() * 10, width=3,
               fill=with_a(TWIG, 0.45), wrap=True)
    return m


def lcg(seed: int):
    """确定性线性同余，跨后端无关（仅 PIL 用；SVG 同步发射坐标一致）。"""
    state = {"s": seed & 0xFFFFFFFF}

    def nxt():
        state["s"] = (state["s"] * 1664525 + 1013904223) & 0xFFFFFFFF
        return state["s"] / 0xFFFFFFFF

    return nxt


MODELS = {
    "tree_outline": model_tree_outline,
    "tree_trunks": model_tree_trunks,
    "leaf_path": model_leaf_path,
}


def render_all(out_dir: str, svg_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(svg_dir, exist_ok=True)
    paths = {}
    for layer_id, factory in MODELS.items():
        model = factory()
        png_path = os.path.join(out_dir, f"forest_{layer_id}_tile.png")
        svg_path = os.path.join(svg_dir, f"forest_{layer_id}_tile.svg")
        render_pil(model).save(png_path)
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(render_svg(model))
        paths[layer_id] = {"png": png_path, "svg": svg_path}
        print(f"[tile] {layer_id}: {png_path} / {svg_path}")
    return paths


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    render_all(os.path.join(root, "previews", "tiles"),
               os.path.join(root, "source", "svg"))
