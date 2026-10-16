#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SW-012 r1 · 雨林双后端渲染/导出（Trae Design）

输入：sw012_model 的同一图元模型
输出（design/05-visual-design/SW-012/r1/）：
  source/svg/rainforest_*.svg        可编辑矢量源（5 层 + master）
  exports/rainforest_*.png           五层 1080×1920 RGBA 透明导出
  previews/rainforest_style_reference.png   875m 终景风格参考
  previews/stages/stage_*.png        0/110/295/475/700/875m 六阶段（fade 完成点取值）
  previews/layer_checks/*.jpg        每层黑/白/洋红底（540×960）
  previews/crops/*.png               1080×1920 / 1080×2400 / 390×844 裁切+安全区标注
  previews/layer_map.png             五层分层标注
  previews/composition_guide.png     雨林色板/构图/与森林差异说明

PIL 后端 2× 超采样后 LANCZOS 缩放；纯离线，无付费 API。图元后端与 SW-011 同构。
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import sw012_model as M

SS = 2
HERE = os.path.dirname(os.path.abspath(__file__))
R1 = os.path.dirname(HERE)
SVG_DIR = os.path.join(HERE, "svg")
EXPORT_DIR = os.path.join(R1, "exports")
PREV_DIR = os.path.join(R1, "previews")
STAGE_DIR = os.path.join(PREV_DIR, "stages")
CHK_DIR = os.path.join(PREV_DIR, "layer_checks")
CROP_DIR = os.path.join(PREV_DIR, "crops")
FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"

for d in (SVG_DIR, EXPORT_DIR, STAGE_DIR, CHK_DIR, CROP_DIR):
    os.makedirs(d, exist_ok=True)

FINAL_METERS = 875  # glade fade 完成点，≤ 900m 终点


def font(sz):
    return ImageFont.truetype(FONT_PATH, sz)


# ==========================================================================
# PIL 后端（与 sw011_render 同构，消费同一图元语义）
# ==========================================================================
def _stops_lut(stops, n):
    xs = np.linspace(0, 1, n)
    out = np.zeros((n, 4), dtype=float)
    pos = [s[0] for s in stops]
    col = np.array([s[1] for s in stops], dtype=float)
    for k in range(4):
        out[:, k] = np.interp(xs, pos, col[:, k])
    out[:, 3] *= 255
    return out


def _new(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def _q_points(p0, c, p1, n=26):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t ** 2 * p1[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t ** 2 * p1[1]
        pts.append((x, y))
    return pts


def _draw_shape(dst, op, s):
    kind = op[0]
    d = ImageDraw.Draw(dst)
    if kind == "e":
        _, cx, cy, rx, ry, color, a = op
        x0, y0, x1, y1 = (cx - rx) * s, (cy - ry) * s, (cx + rx) * s, (cy + ry) * s
        if a >= 1:
            d.ellipse([x0, y0, x1, y1], fill=(*color, 255))
        else:
            sub = _new(dst.size[0], dst.size[1])
            ImageDraw.Draw(sub).ellipse([x0, y0, x1, y1], fill=(*color, 255))
            sub.putalpha(sub.getchannel("A").point(lambda v: int(v * a)))
            dst.alpha_composite(sub)
        return
    if kind == "p":
        _, pts, color, al = op
        xs = [p[0] * s for p in pts]
        ys = [p[1] * s for p in pts]
        if al >= 1:
            d.polygon(list(zip(xs, ys)), fill=(*color, 255))
        else:
            sub = _new(dst.size[0], dst.size[1])
            ImageDraw.Draw(sub).polygon(list(zip(xs, ys)), fill=(*color, 255))
            sub.putalpha(sub.getchannel("A").point(lambda v: int(v * al)))
            dst.alpha_composite(sub)
        return
    if kind == "r":
        _, (x0, y0, x1, y1), rad, color, al = op
        xx0, yy0, xx1, yy1 = x0 * s, y0 * s, x1 * s, y1 * s
        if al >= 1:
            d.rounded_rectangle([xx0, yy0, xx1, yy1], radius=rad * s, fill=(*color, 255))
        else:
            sub = _new(dst.size[0], dst.size[1])
            ImageDraw.Draw(sub).rounded_rectangle([xx0, yy0, xx1, yy1], radius=rad * s, fill=(*color, 255))
            sub.putalpha(sub.getchannel("A").point(lambda v: int(v * al)))
            dst.alpha_composite(sub)
        return
    if kind in ("l", "q"):
        w = op[3 if kind == "l" else 4] * s
        color = op[4 if kind == "l" else 5]
        al = op[5 if kind == "l" else 6]
        if kind == "l":
            p0, p1 = op[1], op[2]
            pts = [(p0[0] * s, p0[1] * s), (p1[0] * s, p1[1] * s)]
        else:
            pts = [(x * s, y * s) for x, y in _q_points(op[1], op[2], op[3])]
        wd = max(1, int(w))
        if al >= 1:
            d.line(pts, fill=(*color, 255), width=wd, joint="curve")
            for x, y in (pts[0], pts[-1]):
                d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=(*color, 255))
        else:
            sub = _new(dst.size[0], dst.size[1])
            sd = ImageDraw.Draw(sub)
            sd.line(pts, fill=(*color, 255), width=wd, joint="curve")
            for x, y in (pts[0], pts[-1]):
                sd.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=(*color, 255))
            sub.putalpha(sub.getchannel("A").point(lambda v: int(v * al)))
            dst.alpha_composite(sub)
        return
    raise ValueError(kind)


def _apply_ramp(img, stops, s):
    if not stops:
        return img
    ys = np.array([y / M.H for y, v in stops])
    vs = np.array([v for y, v in stops])
    lut = np.interp(np.linspace(0, 1, M.H), ys, vs)
    factor = np.repeat(lut, s)
    arr = np.array(img).astype(float)
    arr[:, :, 3] *= factor[: arr.shape[0], None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def _rotate_about(img, deg, px, py, s):
    W2, H2 = img.size
    th = math.radians(deg)
    c, sn = math.cos(th), math.sin(th)
    px, py = px * s, py * s
    a, b = c, sn
    d, e = -sn, c
    cc = px - c * px - sn * py
    f = py + sn * px - c * py
    return img.transform(
        (W2, H2), Image.AFFINE, (a, b, cc, d, e, f), resample=Image.BICUBIC
    )


def render(ops, w=M.W, h=M.H, ss=SS, full=False):
    W2, H2 = w * ss, h * ss
    dst = _new(W2, H2)
    for op in ops:
        kind = op[0]
        if kind == "g":
            _, children, mask, blur, opacity, rot = op
            sub = render(children, w, h, ss, full=True)
            if mask:
                sub = _apply_ramp(sub, mask, ss)
            if blur:
                sub = sub.filter(ImageFilter.GaussianBlur(blur * ss))
            if opacity < 1:
                sub.putalpha(sub.getchannel("A").point(lambda v: int(v * opacity)))
            if rot:
                sub = _rotate_about(sub, rot[0], rot[1], rot[2], ss)
            dst = Image.alpha_composite(dst, sub)
        elif kind in ("vgrad", "hgrad"):
            _, (x0, y0, x1, y1), stops = op
            bw, bh = int((x1 - x0) * ss), int((y1 - y0) * ss)
            lut = _stops_lut(stops, bh if kind == "vgrad" else bw)
            if kind == "vgrad":
                arr = np.repeat(lut[:, None, :], bw, axis=1)
            else:
                arr = np.repeat(lut[None, :, :], bh, axis=0)
            sub = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
            dst.alpha_composite(sub, (int(x0 * ss), int(y0 * ss)))
        elif kind == "rad":
            _, (cx, cy), r, stops = op
            x0, y0 = max(0, int(cx - r)), max(0, int(cy - r))
            x1, y1 = min(w, int(cx + r)), min(h, int(cy + r))
            bw, bh = (x1 - x0) * ss, (y1 - y0) * ss
            xx, yy = np.meshgrid(np.arange(x1 - x0), np.arange(y1 - y0))
            dist = np.sqrt((xx - (cx - x0)) ** 2 + (yy - (cy - y0)) ** 2) / r
            t = np.clip(dist, 0, 1).ravel()
            pos = [s_[0] for s_ in stops]
            cols = np.array([s_[1] for s_ in stops], dtype=float)
            rgba = np.zeros((t.size, 4))
            for k in range(4):
                rgba[:, k] = np.interp(t, pos, cols[:, k])
            rgba[:, 3] *= 255
            arr = rgba.reshape(y1 - y0, x1 - x0, 4)
            arr = np.repeat(np.repeat(arr, ss, axis=0), ss, axis=1)
            sub = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
            dst.alpha_composite(sub, (x0 * ss, y0 * ss))
        elif kind == "erad":
            _, (cx, cy), (erx, ery), stops = op
            x0, y0 = max(0, int(cx - erx)), max(0, int(cy - ery))
            x1, y1 = min(w, int(cx + erx) + 1), min(h, int(cy + ery) + 1)
            if x1 > x0 and y1 > y0:
                xx, yy = np.meshgrid(np.arange(x1 - x0), np.arange(y1 - y0))
                dist = np.sqrt(
                    ((xx - (cx - x0)) / erx) ** 2 + ((yy - (cy - y0)) / ery) ** 2
                )
                t = np.clip(dist, 0, 1).ravel()
                pos = [s_[0] for s_ in stops]
                cols = np.array([s_[1] for s_ in stops], dtype=float)
                rgba = np.zeros((t.size, 4))
                for k in range(4):
                    rgba[:, k] = np.interp(t, pos, cols[:, k])
                rgba[:, 3] *= 255
                arr = rgba.reshape(y1 - y0, x1 - x0, 4)
                arr = np.repeat(np.repeat(arr, ss, axis=0), ss, axis=1)
                sub = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
                dst.alpha_composite(sub, (x0 * ss, y0 * ss))
        elif kind == "polygrad":
            _, pts, (yy0, yy1), stops = op
            mask = Image.new("L", (W2, H2), 0)
            ImageDraw.Draw(mask).polygon(
                [(p[0] * ss, p[1] * ss) for p in pts], fill=255
            )
            pos = [s_[0] for s_ in stops]
            scol = np.array([s_[1] for s_ in stops], dtype=float)
            scol[:, 3] = np.where(scol[:, 3] <= 1.0, scol[:, 3] * 255, scol[:, 3])
            tt = np.clip((np.arange(h) - yy0) / max(1.0, (yy1 - yy0)), 0, 1)
            lut = np.zeros((h, 4))
            for k in range(4):
                lut[:, k] = np.interp(tt, pos, scol[:, k])
            cols = np.repeat(lut[:, None, :], w, axis=1)
            cols = np.repeat(np.repeat(cols, ss, axis=0), ss, axis=1)
            alpha = (np.array(mask).astype(float) * cols[:, :, 3] / 255).astype(np.uint8)
            rgb = cols[:, :, :3].astype(np.uint8)
            sub = Image.merge("RGBA", [
                Image.fromarray(rgb[:, :, 0]), Image.fromarray(rgb[:, :, 1]),
                Image.fromarray(rgb[:, :, 2]), Image.fromarray(alpha),
            ])
            dst = Image.alpha_composite(dst, sub)
        else:
            _draw_shape(dst, op, ss)
    if ss != 1 and not full:
        return dst.resize((w, h), Image.LANCZOS)
    return dst


# ==========================================================================
# SVG 后端
# ==========================================================================
def _hexc(color, a=None):
    h = "#%02X%02X%02X" % tuple(color[:3])
    if a is None:
        return h, None
    return h, round(float(a), 4)


class Svg:
    def __init__(self, prefix):
        self.p = prefix
        self.n = 0
        self.defs = []

    def _id(self, key):
        self.n += 1
        return f"{self.p}-{key}-{self.n}"

    def emit(self, ops, indent=1):
        pad = "  " * indent
        out = []
        for op in ops:
            k = op[0]
            if k == "e":
                _, cx, cy, rx, ry, c, a = op
                fill, ao = _hexc(c, a)
                out.append(
                    f'{pad}<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
                    f'fill="{fill}"' + (f' fill-opacity="{ao}"/>' if ao and ao < 1 else "/>")
                )
            elif k == "p":
                _, pts, c, a = op
                fill, ao = _hexc(c, a)
                points = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                out.append(
                    f'{pad}<polygon points="{points}" fill="{fill}"'
                    + (f' fill-opacity="{ao}"/>' if ao and ao < 1 else "/>")
                )
            elif k == "r":
                _, (x0, y0, x1, y1), rad, c, a = op
                fill, ao = _hexc(c, a)
                out.append(
                    f'{pad}<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" '
                    f'rx="{rad}" ry="{rad}" fill="{fill}"'
                    + (f' fill-opacity="{ao}"/>' if ao and ao < 1 else "/>")
                )
            elif k in ("l", "q"):
                if k == "l":
                    p0, p1, wd, c, a = op[1], op[2], op[3], op[4], op[5]
                    d = f"M {p0[0]},{p0[1]} L {p1[0]},{p1[1]}"
                else:
                    p0, cc, p1, wd, c, a = op[1], op[2], op[3], op[4], op[5], op[6]
                    d = f"M {p0[0]},{p0[1]} Q {cc[0]},{cc[1]} {p1[0]},{p1[1]}"
                stroke, ao = _hexc(c, a)
                out.append(
                    f'{pad}<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{wd}" '
                    f'stroke-linecap="round"'
                    + (f' stroke-opacity="{ao}"/>' if ao and ao < 1 else "/>")
                )
            elif k in ("vgrad", "hgrad"):
                _, (x0, y0, x1, y1), stops = op
                gid = self._id("lg")
                vert = k == "vgrad"
                grad = (
                    f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                    f'x1="{x0}" y1="{y0}" x2="{x0 if vert else x1}" y2="{y1 if vert else y0}">'
                )
                for t, c in stops:
                    col, ao = _hexc(c[:3], c[3] / 255 if c[3] > 1 else c[3])
                    grad += f'<stop offset="{round(t,3)}" stop-color="{col}" stop-opacity="{round(ao,3)}"/>'
                grad += "</linearGradient>"
                self.defs.append(grad)
                out.append(
                    f'{pad}<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="url(#{gid})"/>'
                )
            elif k == "rad":
                _, (cx, cy), rr, stops = op
                gid = self._id("rg")
                grad = (
                    f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                    f'cx="{cx}" cy="{cy}" r="{rr}">'
                )
                for t, c in stops:
                    col, ao = _hexc(c[:3], c[3] / 255 if c[3] > 1 else c[3])
                    grad += f'<stop offset="{round(t,3)}" stop-color="{col}" stop-opacity="{round(ao,3)}"/>'
                grad += "</radialGradient>"
                self.defs.append(grad)
                out.append(f'{pad}<rect x="0" y="0" width="{M.W}" height="{M.H}" fill="url(#{gid})"/>')
            elif k == "erad":
                _, (cx, cy), (erx, ery), stops = op
                gid = self._id("eg")
                sx = erx / ery
                grad = (
                    f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                    f'cx="{cx}" cy="{cy}" r="{ery}" '
                    f'gradientTransform="matrix({sx:.5f},0,0,1,{cx*(1-sx):.3f},0)">'
                )
                for t, c in stops:
                    col, ao = _hexc(c[:3], c[3] / 255 if c[3] > 1 else c[3])
                    grad += f'<stop offset="{round(t,3)}" stop-color="{col}" stop-opacity="{round(ao,3)}"/>'
                grad += "</radialGradient>"
                self.defs.append(grad)
                out.append(f'{pad}<rect x="0" y="0" width="{M.W}" height="{M.H}" fill="url(#{gid})"/>')
            elif k == "polygrad":
                _, pts, (yy0, yy1), stops = op
                gid = self._id("pg")
                grad = (
                    f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                    f'x1="0" y1="{yy0}" x2="0" y2="{yy1}">'
                )
                for t, c in stops:
                    col, ao = _hexc(c[:3], c[3] / 255 if c[3] > 1 else c[3])
                    grad += f'<stop offset="{round(t,3)}" stop-color="{col}" stop-opacity="{round(ao,3)}"/>'
                grad += "</linearGradient>"
                self.defs.append(grad)
                points = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                out.append(f'{pad}<polygon points="{points}" fill="url(#{gid})"/>')
            elif k == "g":
                _, children, mask, blur, opacity, rot = op
                attrs = []
                if blur:
                    fid = self._id("blur")
                    self.defs.append(
                        f'<filter id="{fid}" x="-60%" y="-60%" width="220%" height="220%">'
                        f'<feGaussianBlur stdDeviation="{blur}"/></filter>'
                    )
                    attrs.append(f'filter="url(#{fid})"')
                if mask:
                    mid = self._id("mask")
                    gid = mid + "-g"
                    grad = (
                        f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                        f'x1="0" y1="0" x2="0" y2="{M.H}">'
                    )
                    for y, v in mask:
                        grad += f'<stop offset="{round(y/M.H,4)}" stop-color="#fff" stop-opacity="{v}"/>'
                    grad += "</linearGradient>"
                    self.defs.append(grad)
                    self.defs.append(
                        f'<mask id="{mid}"><rect width="{M.W}" height="{M.H}" fill="url(#{gid})"/></mask>'
                    )
                    attrs.append(f'mask="url(#{mid})"')
                if opacity < 1:
                    attrs.append(f'opacity="{opacity}"')
                if rot:
                    attrs.append(f'transform="rotate({rot[0]} {rot[1]} {rot[2]})"')
                out.append(f'{pad}<g ' + " ".join(attrs) + ">")
                out.append(self.emit(children, indent + 1))
                out.append(f"{pad}</g>")
        return "\n".join(out)

    def document(self, ops):
        body = self.emit(ops)
        defs = "<defs>\n" + "\n".join(self.defs) + "\n</defs>" if self.defs else ""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{M.W}" height="{M.H}" '
            f'viewBox="0 0 {M.W} {M.H}">\n{defs}\n{body}\n</svg>\n'
        )


# ==========================================================================
# 合成
# ==========================================================================
def void(w=M.W, h=M.H):
    return Image.new("RGBA", (w, h), (*M.VOID, 255))


def smooth_opacity(name, meters):
    at, target, fade = M.PHASE[name]
    if meters < at:
        return 0.0
    x = min(1.0, max(0.0, (meters - at) / fade))
    return target * x * x * (3 - 2 * x)


def traveler_ops(cx, gy, color=M.TRAVELER):
    body_b, body_t = gy - 14, gy - 74
    return [
        M.line((cx - 2, body_b), (cx - 10, gy), 6, color),
        M.line((cx + 2, body_b), (cx + 10, gy), 6, color),
        M.rrect(cx - 10, body_t, cx + 10, body_b, 10, color),
        M.ellipse(cx, body_t - 12, 9, 9, color),
    ]


def compose(meters, layer_imgs, w=M.W, h=M.H):
    """按 App 语义：void → 各层（cover=按高度铺满、左对齐）→ 程序旅人。"""
    img = void(w, h)
    scale = h / M.H
    for name, _ in M.LAYERS:
        a = smooth_opacity(name, meters)
        if a <= 0:
            continue
        layer = layer_imgs[name]
        if (w, h) != (M.W, M.H):
            layer = layer.resize((max(1, round(M.W * scale)), h), Image.LANCZOS)
        if a < 1:
            layer = layer.copy()
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(layer, (0, 0))
    t = render(traveler_ops(w * M.TRAVELER_X, h * M.GROUND_Y), w, h)
    img.alpha_composite(t)
    return img


# ==========================================================================
# 标注图
# ==========================================================================
CYAN = (79, 216, 224)
YELLOW = (240, 214, 116)
WHITE = (238, 244, 238)


def _dashed_h(d, x0, x1, y, color, dash=18, gap=12, width=3):
    x = x0
    while x < x1:
        d.line([(x, y), (min(x + dash, x1), y)], fill=color, width=width)
        x += dash + gap


def _dashed_v(d, x, y0, y1, color, dash=18, gap=12, width=3):
    y = y0
    while y < y1:
        d.line([(x, y), (x, min(y + dash, y1))], fill=color, width=width)
        y += dash + gap


def annotate(img, title):
    img = img.convert("RGBA")
    overlay = _new(*img.size)
    d = ImageDraw.Draw(overlay)
    w, h = img.size
    sc = h / M.H
    zone = Image.new("RGBA", (w, int(h * 0.45)), (79, 216, 224, 26))
    overlay.alpha_composite(zone, (0, int(h * 0.55)))
    _dashed_h(d, 0, w, int(h * 0.55), CYAN)
    for x in (0.10, 0.90):
        _dashed_v(d, int(w * x), int(h * 0.12), int(h * 0.92), (255, 255, 255, 120))
    _dashed_h(d, 0, w, int(h * 0.865), YELLOW)
    d.line([(int(w * 0.34), 0), (int(w * 0.34), h)], fill=(*YELLOW, 90), width=2)
    d.ellipse([w * 0.34 - 8, h * 0.865 - 8, w * 0.34 + 8, h * 0.865 + 8],
              outline=YELLOW, width=3)
    img = Image.alpha_composite(img, overlay)
    d = ImageDraw.Draw(img)
    fs = max(12, int(25 * sc))
    f, fb = font(fs), font(int(fs * 0.78))
    d.rectangle([0, 0, w, int(56 * sc)], fill=(5, 8, 7, 190))
    d.text((14, int(10 * sc)), title, font=f, fill=WHITE)
    d.text((14, int(h * 0.55 + 8 * sc)), "下方 45% 摇杆触控区 · 素材不烘焙 UI / 湿雾低对比",
           font=fb, fill=CYAN)
    d.text((int(w * 0.34 + 8), int(h * 0.865 - 34 * sc)), "旅人 x=.34 / 脚底 y=.865",
           font=fb, fill=YELLOW)
    d.text((14, int(h * 0.10)), "米数 / 暂停 / 放弃", font=fb, fill=(*WHITE, 200))
    return img


def checker(size, sq=12):
    img = Image.new("RGB", (size, size), (205, 205, 205))
    d = ImageDraw.Draw(img)
    for y in range(0, size, sq):
        for x in range(0, size, sq):
            if (x // sq + y // sq) % 2 == 0:
                d.rectangle([x, y, x + sq, y + sq], fill=(150, 150, 150))
    return img


def make_layer_map(layer_imgs):
    Wc, Hc = 1500, 1080
    canvas = Image.new("RGBA", (Wc, Hc), (240, 243, 239, 255))
    d = ImageDraw.Draw(canvas)
    d.text((40, 30), "雨林五层分层标注 · SW-012 r1（棋盘格=真透明；layer IDs 为 proposed）",
           font=font(32), fill=(30, 40, 34))
    meta = [
        ("mist", "90m · opacity .55 · fade20", "overlay · 贴地湿雾+飘雾，软衰减无矩形底"),
        ("trunks_canopy", "270m · opacity .85 · fade25", "parallax 0.30 · 板根粗干+阔叶顶棚，留林隙"),
        ("vines_light", "450m · opacity 1.0 · fade25", "parallax 0.60 · 垂藤/阔叶+暖绿光斑"),
        ("distant_glow", "675m · opacity .85 · fade25", "overlay · 林隙透光+流动水汽"),
        ("glade", "855m · opacity .90 · fade20", "overlay · 幽径辉光+湿径反光"),
    ]
    card_w, card_h, gap = 250, 356, 36
    x0 = 40
    chk = checker(20, 10)
    for i, (name, line1, line2) in enumerate(meta):
        x = x0 + i * (card_w + gap)
        y = 110
        d.rounded_rectangle([x - 12, y - 12, x + card_w + 12, y + card_h + 120],
                            radius=14, fill=(255, 255, 255, 255), outline=(200, 208, 198), width=2)
        thumb = layer_imgs[name].resize((card_w, card_h), Image.LANCZOS).convert("RGBA")
        bg = chk.resize((card_w, card_h)).convert("RGBA")
        bg.alpha_composite(thumb)
        canvas.alpha_composite(bg, (x, y))
        d.text((x, y + card_h + 14), name, font=font(22), fill=(22, 46, 40))
        d.text((x, y + card_h + 46), line1, font=font(16), fill=(80, 96, 86))
        maxc = 19
        lines = [line2[i:i + maxc] for i in range(0, len(line2), maxc)]
        for j, ln in enumerate(lines[:2]):
            d.text((x, y + card_h + 72 + j * 22), ln, font=font(15), fill=(104, 116, 106))
    d.text((40, 1020), "统一：画布 1080×1920 · 光源右上 · 黑幕/旅人程序绘制 · 锚点 x=.34/y=.865 · 900m 终点",
           font=font(20), fill=(86, 98, 90))
    canvas.save(os.path.join(PREV_DIR, "layer_map.png"))


def make_composition_guide(master):
    Wc, Hc = 1600, 1980
    canvas = Image.new("RGBA", (Wc, Hc), (240, 243, 239, 255))
    d = ImageDraw.Draw(canvas)
    ink = (28, 38, 32)
    sub = (88, 100, 92)
    d.text((50, 40), "SenseWalk 雨林 · 900m 湿绿视觉语言", font=font(46), fill=ink)
    d.text((50, 104), "潮湿浓绿 · 轻雾裹身 · 阔叶遮天 · 藤蔓光斑 · 水气温润；与森林干叶通透明确区分",
           font=font(25), fill=sub)

    phone = master.resize((540, 960), Image.LANCZOS)
    canvas.alpha_composite(phone, (60, 180))
    d.rectangle([60, 180, 600, 1140], outline=(176, 186, 178), width=3)
    d.text((60, 1156), "终景参考（875m fade 完成点，目标透明度合成；900m 不切屏）", font=font(22), fill=sub)

    x = 700
    d.text((x, 190), "色板（rainforest.md §2 + 派生）", font=font(30), fill=ink)
    swatches = [
        ("void", M.VOID, "近黑偏绿黑幕"),
        ("mist", M.MIST, "雾气层"),
        ("bark", M.BARK, "板根树干"),
        ("canopy", M.CANOPY, "树冠受光"),
        ("leaf_deep", M.LEAF_DEEP, "后排深阔叶"),
        ("leaf_mid", M.LEAF_MID, "中排阔叶"),
        ("moss", M.MOSS, "树干苔藓"),
        ("vine", M.VINE, "垂藤"),
        ("glow_vine", M.GLOW_VINE, "藤蔓光斑"),
        ("glow_soft", M.GLOW_SOFT, "林隙柔光"),
        ("water", M.WATER, "水气/湿面"),
        ("glade", M.GLADE, "幽径微光"),
    ]
    for i, (name, c, use) in enumerate(swatches):
        col = i % 2
        row = i // 2
        sx = x + col * 430
        sy = 250 + row * 78
        d.rounded_rectangle([sx, sy, sx + 60, sy + 60], radius=9, fill=(*c, 255),
                            outline=(186, 194, 186), width=1)
        hexc = "#%02X%02X%02X" % c
        d.text((sx + 74, sy + 4), name, font=font(22), fill=ink)
        d.text((sx + 74, sy + 33), f"{hexc} · {use}", font=font(16), fill=sub)

    y = 780
    d.text((x, y), "构图与坐标（沿用通用规范）", font=font(30), fill=ink)
    rules = [
        "基准 1080×1920；补 1080×2400 与 390×844 裁切。",
        "旅人 x=.34、脚底 y=.865；黑幕与旅人程序绘制。",
        "下方 45% 摇杆触控区：湿雾低对比、不烘焙 UI。",
        "光源统一右上；阔叶顶棚上中部留两处林隙接 675m 透光。",
        "板根/藤蔓避开旅人竖线；关键内容收中央 80% 宽。",
    ]
    for i, t in enumerate(rules):
        d.text((x, y + 48 + i * 40), "· " + t, font=font(21), fill=(56, 66, 58))

    y = 1030
    d.text((x, y), "雨林 vs 森林（不是换色相）", font=font(30), fill=ink)
    contrasts = [
        "湿绿冷调+雾青/苔色，不用森林暖褐 #A89060 与干叶。",
        "粗大板根+遮天阔叶顶棚；森林是细高疏干+通透树荫。",
        "垂藤与斑驳漏光；森林是斜射光束+远鸟。",
        "贴地湿雾/流动水汽/湿径反光；森林是干爽土路落叶。",
    ]
    for i, t in enumerate(contrasts):
        d.text((x, y + 48 + i * 38), "· " + t, font=font(20), fill=(56, 66, 58))

    y = 1240
    d.text((x, y), "做 / 不做", font=font(30), fill=ink)
    do = ["湿雾、阔叶、藤蔓、水气、苔藓", "柔边漏光与单一幽径辉光", "浓而不闷、可呼吸的暗部留白"]
    dont = ["干叶/暖褐/土路、远鸟斜光束", "棋盘/同心环/矩形底/第二套背景", "雷暴惊吓、闪光、HUD、文字、人物"]
    d.text((x + 50, y + 52), "做", font=font(24), fill=(60, 110, 74))
    for i, t in enumerate(do):
        d.text((x + 50, y + 88 + i * 36), "✓ " + t, font=font(19), fill=(52, 84, 62))
    d.text((x + 470, y + 52), "不做", font=font(24), fill=(150, 80, 70))
    for i, t in enumerate(dont):
        d.text((x + 470, y + 88 + i * 36), "× " + t, font=font(19), fill=(120, 70, 62))

    d.text((50, 1880), "依据：contracts/visual-design.md · design/01-scenes-terrain/rainforest.md · DEVELOPMENT.md §7.1/§7.7/§12.4",
           font=font(19), fill=sub)
    canvas.save(os.path.join(PREV_DIR, "composition_guide.png"))


# ==========================================================================
# 主流程
# ==========================================================================
def main():
    layer_imgs = {}
    for name, builder in M.LAYERS:
        ops = builder()
        svg = Svg(name).document(ops)
        with open(os.path.join(SVG_DIR, f"rainforest_{name}.svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        img = render(ops)
        img.save(os.path.join(EXPORT_DIR, f"rainforest_{name}.png"))
        layer_imgs[name] = img

    # master SVG（引用五层，按目标 opacity）
    master_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{M.W}" height="{M.H}" '
        f'viewBox="0 0 {M.W} {M.H}">\n'
        f'<rect width="{M.W}" height="{M.H}" fill="#%02X%02X%02X"/>\n' % M.VOID
    )
    for name, target in [
        ("mist", 0.55), ("trunks_canopy", 0.85), ("vines_light", 1.0),
        ("distant_glow", 0.85), ("glade", 0.90),
    ]:
        master_svg += (
            f'<image href="rainforest_{name}.svg" x="0" y="0" width="{M.W}" '
            f'height="{M.H}" opacity="{target}"/>\n'
        )
    cx, gy = M.W * M.TRAVELER_X, M.H * M.GROUND_Y
    bb, bt = gy - 14, gy - 74
    col = "#%02X%02X%02X" % M.TRAVELER
    master_svg += (
        f'<g stroke="{col}" fill="{col}" stroke-linecap="round">'
        f'<line x1="{cx-2}" y1="{bb}" x2="{cx-10}" y2="{gy}" stroke-width="6"/>'
        f'<line x1="{cx+2}" y1="{bb}" x2="{cx+10}" y2="{gy}" stroke-width="6"/>'
        f'<rect x="{cx-10}" y="{bt}" width="20" height="{bb-bt}" rx="10" stroke="none"/>'
        f'<circle cx="{cx}" cy="{bt-12}" r="9" stroke="none"/></g>\n</svg>\n'
    )
    with open(os.path.join(SVG_DIR, "rainforest_master.svg"), "w", encoding="utf-8") as f:
        f.write(master_svg)

    # 风格参考（875m 终景）
    master = compose(FINAL_METERS, layer_imgs)
    master.save(os.path.join(PREV_DIR, "rainforest_style_reference.png"))

    # 六阶段（fade 完成点）
    for meters in M.PREVIEW_METERS:
        compose(meters, layer_imgs).save(
            os.path.join(STAGE_DIR, f"stage_{meters:03d}m.png")
        )

    # 分层黑/白/洋红底检查
    bgs = {"black": (0, 0, 0), "white": (255, 255, 255), "magenta": (255, 0, 255)}
    for name, _ in M.LAYERS:
        for bg_name, rgb in bgs.items():
            canvas = Image.new("RGBA", (M.W, M.H), (*rgb, 255))
            canvas.alpha_composite(layer_imgs[name])
            canvas.convert("RGB").resize((540, 960), Image.LANCZOS).save(
                os.path.join(CHK_DIR, f"rainforest_{name}_{bg_name}.jpg"), quality=88
            )

    # 三种比例裁切 + 标注
    annotate(compose(FINAL_METERS, layer_imgs, 1080, 1920),
             "1080×1920 基准 · 875m · 按高度铺满、左对齐（drawImageLayer 语义）").save(
        os.path.join(CROP_DIR, "crop_1080x1920.png"))
    annotate(compose(FINAL_METERS, layer_imgs, 1080, 2400),
             "1080×2400 长屏 · 按高铺满后宽 1350，右侧溢出 270px 作视差余量").save(
        os.path.join(CROP_DIR, "crop_1080x2400.png"))
    annotate(compose(FINAL_METERS, layer_imgs, 390, 844),
             "390×844 小屏 · 按高铺满后宽 475，左对齐、右侧溢出 85px 供横向视差").save(
        os.path.join(CROP_DIR, "crop_390x844.png"))

    make_layer_map(layer_imgs)
    make_composition_guide(master)
    print("all rainforest exports written under", R1)


if __name__ == "__main__":
    main()
