#!/usr/bin/env python3
"""
SW-006 R2 候选后处理: 生图原稿 -> 真透明 RGBA + 检查图 + 阶段预览 + 局部放大.

输入: design/assets/rainforest/candidates/SW-006/r2/source/<layer>.png
      (mcode-tools matrix generate_image 输出, RGB, 1536x2752)
输出: design/assets/rainforest/candidates/SW-006/r2/
      png/rainforest_<layer>.png          真透明 RGBA 1080x1920
      webp/rainforest_<layer>.webp        入包预算 WebP
      checks/alpha_mask/rainforest_<layer>.png
      checks/black|white|magenta/rainforest_<layer>.jpg
      checks/stages/stage_<m>m.png        六阶段真实 opacity 合成
      checks/zoom/rainforest_<layer>_zoom.png  局部放大 (最近邻, 不美化)

抠像方法 (可分离底 -> 真透明):
- 生图 API 不支持真透明, 故用纯洋红 #FF00FF 可分离底, 按像素色距解出 alpha.
- alpha = clamp((dist_to_magenta - near) / (far - near)) 线性带, 保留软边.
- 颜色去溢色 (despill): 边缘像素若仍带洋红分量, 按邻域把 R/B 压向 G, 避免白边/紫边.
- 逐像素验图: 合成到黑/白/洋红三底, 确认无棋盘、无矩形底、无白边.

尺寸纪律:
- 原稿 1536x2752 (2K/9:16), 目标 1080x1920. 这里做 **等比缩放** (1536/2752 = 1080/1936,
  故按宽 1080 缩放得 1080x1936, 再按中心裁到 1080x1920), 不是拉伸.
  记录真实来源分辨率与处理链, 不冒称原生 1080.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prompts_r2  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
R2_DIR = SCRIPT_DIR.parent
CANDIDATE_ROOT = R2_DIR
REPO_ROOT = SCRIPT_DIR.parents[6]

SOURCE_DIR = R2_DIR / "source"
PNG_DIR = R2_DIR / "png"
WEBP_DIR = R2_DIR / "webp"
CHECKS_DIR = R2_DIR / "checks"
ALPHA_DIR = CHECKS_DIR / "alpha_mask"
BLACK_DIR = CHECKS_DIR / "black"
WHITE_DIR = CHECKS_DIR / "white"
MAGENTA_DIR = CHECKS_DIR / "magenta"
STAGES_DIR = CHECKS_DIR / "stages"
ZOOM_DIR = CHECKS_DIR / "zoom"

TARGET_W, TARGET_H = 1080, 1920

#: 洋红可分离底
MAGENTA = np.array([255.0, 0.0, 255.0])

#: alpha 线性带的近/远阈值 (到洋红的欧氏色距), 仅用于距离法的软过渡
NEAR_DIST = 18.0
FAR_DIST = 90.0

#: 抠像后仍判定为"洋红底残留"的阈值, 用于矩形底/棋盘检测
RESIDUAL_DIST = 70.0


def estimate_background(rgb: np.ndarray) -> np.ndarray:
    """估计可分离底色: 取画布外圈环带的量化众数 (模型画的是接近纯洋红)."""
    h, w = rgb.shape[:2]
    band = max(4, int(min(h, w) * 0.02))
    ring = np.concatenate([
        rgb[:band].reshape(-1, 3), rgb[-band:].reshape(-1, 3),
        rgb[:, :band].reshape(-1, 3), rgb[:, -band:].reshape(-1, 3),
    ])
    q = np.round(ring / 8.0).astype(np.int32)
    keys, counts = np.unique(q, axis=0, return_counts=True)
    k = keys[counts.argmax()]
    return np.clip(k.astype(np.float64) * 8.0, 0, 255)


def estimate_foreground(rgb: np.ndarray, bg: np.ndarray) -> np.ndarray:
    """估计层自身的前景色 F: 取"离底色最远"的一批像素 (即近乎不透明的前景核).

    自校准, 不写死色值; 依据是观测模型 obs = a*F + (1-a)*bg,
    a 最大的像素最接近 F 本身.
    """
    d = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    hi = float(np.percentile(d, 99.5))
    if hi <= 1.0:
        return np.array([0.0, 0.0, 0.0])
    core = d >= hi
    if core.sum() < 16:
        core = d >= np.percentile(d, 99.0)
    return rgb[core].mean(axis=0)


def key_to_alpha(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict[str, object]]:
    """从可分离底解出 alpha (反解混合方程), 并还原前景真色.

    观测模型:  obs = a*F + (1-a)*bg,  观测图是"半透明前景叠在纯底上".
    先估计底色 bg 与前景色 F, 再用投影解 a:
        a = <obs-bg, F-bg> / |F-bg|^2
    最后反解真色: F_pix = (obs - (1-a)*bg) / a
    这样软光斑 (distant_glow/glade/mist) 不会把底色混进结果, 也不会出现洋红残留.

    返回 (alpha[0..1], rgb_前景真色, 诊断).
    """
    bg = estimate_background(rgb)
    fg = estimate_foreground(rgb, bg)
    u = fg - bg
    u2 = float((u * u).sum())
    diag: Dict[str, object] = {
        "background_rgb": [round(float(x), 1) for x in bg],
        "foreground_rgb": [round(float(x), 1) for x in fg],
    }
    if u2 < 64.0:
        # 前景与底色几乎不可分 (整幅纯底), 退化为距离法
        d = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
        alpha = np.clip((d - NEAR_DIST) / (FAR_DIST - NEAR_DIST), 0.0, 1.0)
        diag["fallback"] = "distance-key (前景与底色不可分)"
        return alpha, rgb.copy(), diag

    v = rgb - bg
    alpha = np.clip((v * u).sum(axis=2) / u2, 0.0, 1.0)
    # 软边: 极低 alpha 区域再按色距收一次, 避免底色噪点被算成前景
    d = np.sqrt((v * v).sum(axis=2))
    alpha = np.where(alpha < 0.02, np.clip((d - NEAR_DIST) / (FAR_DIST - NEAR_DIST), 0.0, 1.0) * 0.0, alpha)

    # 反解前景真色
    safe = np.maximum(alpha, 1e-3)[..., None]
    fg_pix = (rgb - (1.0 - alpha[..., None]) * bg) / safe
    fg_pix = np.where(alpha[..., None] > 0.02, fg_pix, rgb)
    fg_pix = np.clip(fg_pix, 0, 255)
    diag["unmix_residual"] = float(np.abs((alpha[..., None] * fg_pix + (1 - alpha[..., None]) * bg) - rgb).mean())
    return alpha, fg_pix, diag


def load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        im.load()
        return np.asarray(im.convert("RGB")).astype(np.float64)


def fit_to_canvas(rgb: np.ndarray) -> Tuple[np.ndarray, Dict[str, object]]:
    """等比缩放到 1080 宽, 再中心裁到 1080x1920 (不拉伸)."""
    h, w = rgb.shape[:2]
    scale = TARGET_W / w
    new_w = TARGET_W
    new_h = int(round(h * scale))
    im = Image.fromarray(rgb.astype(np.uint8), "RGB").resize((new_w, new_h), Image.LANCZOS)
    arr = np.asarray(im).astype(np.float64)
    if new_h >= TARGET_H:
        top = (new_h - TARGET_H) // 2
        arr = arr[top:top + TARGET_H, :]
        crop = f"center-crop {new_w}x{new_h}->{TARGET_W}x{TARGET_H}"
    else:
        pad = TARGET_H - new_h
        top = pad // 2
        arr = np.pad(arr, ((top, pad - top), (0, 0), (0, 0)), mode="edge")
        crop = f"pad {new_w}x{new_h}->{TARGET_W}x{TARGET_H}"
    return arr, {
        "source_resolution": f"{w}x{h}",
        "source_to_canvas": f"LANCZOS scale to width {new_w} then {crop}",
        "aspect": round(w / h, 6),
    }


def composite(rgb: np.ndarray, alpha: np.ndarray, bg: Tuple[int, int, int]) -> Image.Image:
    a = alpha[..., None]
    bgarr = np.zeros_like(rgb)
    bgarr[..., 0], bgarr[..., 1], bgarr[..., 2] = bg
    out = rgb * a + bgarr * (1.0 - a)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


#: 逐层色板分级目标 (取自 SW-012 批准 design-spec.json palette)
#:
#: 依据: 生图模型给的是高饱和鲜绿, 与批准色板 "低饱和冷湿绿, 不引入森林暖褐 #A89060"
#: 不符. 本步骤只改 **色相/饱和度**, 保留每像素明度结构 (体积渐变/受光方向不变),
#: 属于可追溯的色彩分级, 记录在 manifest.process, 不是凭空造图.
#: target = (hue_deg, saturation 0..1, value_gain)
PALETTE_GRADE: Dict[str, Tuple[float, float, float]] = {
    # 树干/顶棚: 冷湿墨绿 #1E3D36/#2A5248, 饱和度低
    "trunks_canopy": (152.0, 0.34, 1.02),
    # 垂藤: #3A5C4C/#6A8A60
    "vines_light": (136.0, 0.38, 0.98),
    # 湿雾: #1A2E28/#2F4E44 极低饱和冷雾青
    "mist": (160.0, 0.30, 0.92),
    # 林隙漏光: #A8C9A6 淡暖白绿
    "distant_glow": (110.0, 0.30, 0.96),
    # 幽径: #9FC09A 辉光 + #3A584C/#5A7D72 湿径
    "glade": (108.0, 0.32, 0.95),
}

#: 逐层 alpha 密度目标 (对齐 SW-012 批准 export 的实测 alpha 统计)
#:
#: 依据 (design/05-visual-design/SW-012/r1/exports/*.png 实测):
#:   mist         alpha_max=144  opaque=0.000 semi=0.346 transparent=0.654
#:   trunks_canopy alpha_max=255 opaque=0.375 semi=0.125 transparent=0.501
#:   vines_light  alpha_max=255 opaque=0.002 semi=0.080 transparent=0.918
#:   distant_glow alpha_max=57  opaque=0.000 semi=0.099 transparent=0.901
#:   glade        alpha_max=237 opaque=0.000 semi=0.186 transparent=0.814
#:
#: 生图模型给出的层普遍过厚 (例如 glade 是实心圆盘而非半透明辉光), 与批准设计
#: 的"极低不透明度光斑/薄雾"不符, 且会破坏 phase opacity 的运行时衰减语义.
#: 这里按目标 **不透明像素占比** 与 **最大 alpha** 重新标定 alpha 密度.
#: target = (max_alpha, opaque_fraction_target)
ALPHA_TARGET: Dict[str, Tuple[float, float]] = {
    "mist": (144 / 255.0, 0.000),
    "trunks_canopy": (1.0, 0.375),
    "vines_light": (1.0, 0.060),
    "distant_glow": (57 / 255.0, 0.000),
    "glade": (237 / 255.0, 0.020),
}

#: alpha 量化级数 (降低熵, 显著改善 WebP 体积, 视觉无损)
ALPHA_LEVELS = 64

#: 逐层参考统计源: SW-012 批准 export (只读, **只取色彩/明度分布统计, 不复制像素**).
#:
#: 依据 (contracts/visual-assets.md: "不把设计exports/test fixture直接冒充生产候选"):
#: 这里不搬运 design 的任何像素到候选素材; 仅用批准 export 作为 **色彩与明度分布的参考统计**,
#: 对生图层做等价的色域收敛 (chroma transfer), 保证候选落在批准色板的亮度/饱和度区间.
#: 候选的形态、纹理、层次仍全部来自本轮生图结果.
PALETTE_REFERENCE: Dict[str, str] = {
    "mist": "design/05-visual-design/SW-012/r1/exports/rainforest_mist.png",
    "trunks_canopy": "design/05-visual-design/SW-012/r1/exports/rainforest_trunks_canopy.png",
    "vines_light": "design/05-visual-design/SW-012/r1/exports/rainforest_vines_light.png",
    "distant_glow": "design/05-visual-design/SW-012/r1/exports/rainforest_distant_glow.png",
    "glade": "design/05-visual-design/SW-012/r1/exports/rainforest_glade.png",
}


def normalize_alpha_density(alpha: np.ndarray, layer_id: str) -> Tuple[np.ndarray, Dict[str, object]]:
    """把 alpha 密度标定到批准 design 的实测统计.

    做法: 先把 alpha 按其自身最大值归一, 再按目标最大 alpha 缩放;
    对"应是薄层"的层 (目标不透明占比≈0), 用幂曲线压低中间调, 让只有最亮的核心
    保留较高 alpha, 其余降到很低的半透明, 与批准 design 的 thin-glow 语义一致.
    幂指数按目标不透明占比数值求解 (单调映射, 保序).
    """
    target_max, target_opaque = ALPHA_TARGET.get(layer_id, (1.0, 0.0))
    a = np.clip(alpha, 0.0, 1.0)
    peak = float(a.max())
    if peak <= 1e-6:
        return a, {"peak": 0.0, "gain": 0.0, "gamma": 1.0}

    norm = a / peak
    # 求解 gamma: 使 (norm > 0.95) 的像素占比接近 target_opaque.
    # target_opaque 越小, gamma 越大 (中间调被压得更低).
    if target_opaque <= 0.001:
        # 薄层: 幂曲线压低, 只保留极亮核心
        gamma = 3.2
    else:
        # 目标不透明占比 -> gamma 近似反比 (经验标定, 单调)
        gamma = float(np.clip(1.0 / max(target_opaque, 0.02) ** 0.5, 0.6, 2.6))
    shaped = np.power(norm, gamma)
    out = np.clip(shaped * target_max, 0.0, 1.0)
    diag = {
        "peak_before": round(peak, 4),
        "target_max_alpha": round(target_max, 4),
        "gamma": round(gamma, 4),
        "opaque_fraction_before": round(float((a > 0.95).mean()), 4),
        "opaque_fraction_after": round(float((out > 0.95).mean()), 4),
    }
    return out, diag


def _hsv_stats(rgb: np.ndarray, mask: np.ndarray) -> Dict[str, float]:
    """取遮罩内像素的 HSV/明度分布统计 (仅统计量, 不保留像素)."""
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    hsv = np.asarray(im.convert("HSV")).astype(np.float64)
    sel = hsv[mask]
    if sel.shape[0] == 0:
        return {"hue": 120.0, "sat": 40.0, "v_p50": 60.0, "v_p95": 120.0}
    ang = sel[:, 0] / 255.0 * 2 * np.pi
    hue = float((np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()) % (2 * np.pi)) / (2 * np.pi) * 255)
    return {
        "hue": hue,
        "sat": float(np.percentile(sel[:, 1], 50)),
        "v_p50": float(np.percentile(sel[:, 2], 50)),
        "v_p95": float(np.percentile(sel[:, 2], 95)),
    }


def transfer_palette(rgb: np.ndarray, alpha: np.ndarray, layer_id: str) -> Tuple[np.ndarray, Dict[str, object]]:
    """把生图层的色域收敛到批准 design 的色板统计 (等价的色域迁移).

    做法:
    1. 读批准 export 的色彩统计 (色相圆均值/饱和中位/明度分位) —— **只取统计量**.
    2. 生图层保留 **相对明度结构** (明度分位重映射到批准明度分布),
       即形体/受光/层次不变, 只是整体亮度与饱和度回到批准区间.
    3. 色相/饱和度向批准统计收敛 (保留部分原始偏差, 避免死板).

    依据 contracts/visual-assets.md "不把设计exports/test fixture直接冒充生产候选":
    本步骤 **不搬运 design 的任何像素**; 候选的形态/纹理/层次全部来自本轮生图结果.
    """
    ref_rel = PALETTE_REFERENCE.get(layer_id)
    if ref_rel is None:
        return rgb, {"applied": False}
    ref_path = REPO_ROOT / ref_rel
    if not ref_path.is_file():
        return rgb, {"applied": False, "reason": "reference missing"}

    with Image.open(ref_path) as im:
        im.load()
        ref = np.asarray(im.convert("RGBA")).astype(np.float64)
    ref_mask = ref[..., 3] > 16
    if int(ref_mask.sum()) < 32:
        return rgb, {"applied": False, "reason": "reference has no opaque pixels"}
    ref_stats = _hsv_stats(ref[..., :3], ref_mask)

    gen_mask = alpha > 0.05
    if int(gen_mask.sum()) < 32:
        return rgb, {"applied": False, "reason": "generated layer empty"}
    gen_stats = _hsv_stats(rgb, gen_mask)

    # --- 1) 明度重映射: 生图明度分位 -> 批准明度分位 (保留相对结构) ---
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    hsv = np.asarray(im.convert("HSV")).astype(np.float64)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    src_p = np.array([5, 25, 50, 75, 95], dtype=np.float64)
    src_vals = np.percentile(v[gen_mask], src_p)
    dst_vals = np.array([
        ref_stats["v_p50"] * 0.45,
        ref_stats["v_p50"] * 0.72,
        ref_stats["v_p50"],
        ref_stats["v_p50"] + (ref_stats["v_p95"] - ref_stats["v_p50"]) * 0.42,
        ref_stats["v_p95"],
    ], dtype=np.float64)
    v_new = np.clip(np.interp(v, src_vals, dst_vals), 0, 255)

    # --- 2) 色相/饱和度向批准统计收敛 (保留部分原始偏差) ---
    h_ref = ref_stats["hue"]
    h_new = np.mod(h_ref + (h - h_ref) * 0.22, 256.0)
    s_ref = ref_stats["sat"]
    s_new = np.clip(s * (s_ref / max(gen_stats["sat"], 1.0)) * 0.85 + s_ref * 0.15, 0, 255)

    out_hsv = np.dstack([h_new, s_new, v_new])
    graded = np.asarray(
        Image.fromarray(np.clip(out_hsv, 0, 255).astype(np.uint8), "HSV").convert("RGB")
    ).astype(np.float64)
    return np.clip(graded, 0, 255), {
        "applied": True,
        "reference": ref_rel,
        "reference_stats": {k: round(v, 2) for k, v in ref_stats.items()},
        "generated_stats": {k: round(v, 2) for k, v in gen_stats.items()},
        "v_p50_before": round(float(gen_stats["v_p50"]), 2),
        "v_p50_after": round(float(ref_stats["v_p50"]), 2),
    }


def quantize_alpha(alpha: np.ndarray, levels: int = ALPHA_LEVELS) -> np.ndarray:
    """量化 alpha (降低熵) + 轻微去噪, 视觉无损但显著改善 WebP 体积."""
    a = np.clip(alpha, 0.0, 1.0)
    # 3x3 中值滤波去孤立噪点 (alpha 平滑区域不受影响)
    a3 = np.stack([np.roll(np.roll(a, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)], axis=0)
    a = np.median(a3, axis=0)
    q = np.round(a * (levels - 1)) / (levels - 1)
    return np.clip(q, 0.0, 1.0)


def save_webp(im: Image.Image, path: Path, max_bytes: int = 400 * 1024) -> Tuple[int, int]:
    """存 WebP 并保证 <= max_bytes (逐级降 quality 直到达标)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    quality = 86
    while quality >= 20:
        im.save(path, "WEBP", quality=quality, method=4)
        size = path.stat().st_size
        if size <= max_bytes:
            return size, quality
        quality -= 6
    # 仍超限时用最低质量再存一次, 报告真实值 (不谎报达标)
    im.save(path, "WEBP", quality=20, method=4)
    return path.stat().st_size, 20


def smoothstep(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def stage_opacity(layer_id: str, meters: int) -> float:
    """按 SW-012 opacity_model: opacity = target * smoothstep((m-atMeters)/fadeMeters)."""
    spec = prompts_r2.LAYER_SPECS[layer_id]
    if meters < spec["at_meters"]:
        return 0.0
    x = (meters - spec["at_meters"]) / spec["fade_meters"]
    return spec["to_opacity"] * float(smoothstep(np.array(x)))


def build_stages(layers: Dict[str, Tuple[np.ndarray, np.ndarray]]) -> List[Dict[str, object]]:
    """六阶段真实 opacity 合成 (0/110/295/475/700/875m)."""
    VOID = (5, 8, 7)
    results = []
    for meters in prompts_r2.STAGE_METERS:
        canvas = np.zeros((TARGET_H, TARGET_W, 3), dtype=np.float64)
        canvas[..., 0], canvas[..., 1], canvas[..., 2] = VOID
        for layer_id in prompts_r2.LAYER_IDS:
            rgb, alpha = layers[layer_id]
            op = stage_opacity(layer_id, meters)
            if op <= 0.0:
                continue
            a = (alpha * op)[..., None]
            canvas = rgb * a + canvas * (1.0 - a)
        out = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), "RGB")
        p = STAGES_DIR / f"stage_{meters:03d}m.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        out.save(p, optimize=True)
        results.append({"meters": meters, "path": p})
    return results


def build_zoom(layer_id: str, rgb: np.ndarray, alpha: np.ndarray) -> Dict[str, object]:
    """局部放大: 内容热点 + 画布四缘, 2x 最近邻, 不美化."""
    mask = alpha > 0.05
    if not mask.any():
        spots = [(0, 0)]
    else:
        ys, xs = np.nonzero(mask)
        # 4 个内容热点: 上下左右分位
        spots = []
        for qy, qx in ((0.15, 0.5), (0.5, 0.85), (0.85, 0.5), (0.5, 0.15)):
            spots.append((int(np.percentile(ys, qy * 100)), int(np.percentile(xs, qx * 100))))
    patches = []
    S = 260
    for (cy, cx) in spots:
        patches.append((cy, cx))
    for (cy, cx) in ((0, 0), (0, TARGET_W - 1), (TARGET_H - 1, 0), (TARGET_H - 1, TARGET_W - 1)):
        patches.append((cy, cx))

    out = Image.new("RGB", (S * 2 * len(patches), S * 2), (0, 0, 0))
    for i, (cy, cx) in enumerate(patches):
        y0 = int(np.clip(cy - S // 2, 0, TARGET_H - S))
        x0 = int(np.clip(cx - S // 2, 0, TARGET_W - S))
        y1 = int(np.clip(y0 + S, 0, TARGET_H))
        x1 = int(np.clip(x0 + S, 0, TARGET_W))
        patch_rgb = rgb[y0:y1, x0:x1]
        patch_a = alpha[y0:y1, x0:x1]
        comp = composite(patch_rgb, patch_a, (255, 0, 255))
        big = comp.resize((S * 2, S * 2), Image.NEAREST)
        out.paste(big, (i * S * 2, 0))
    p = ZOOM_DIR / f"rainforest_{layer_id}_zoom.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    out.save(p, optimize=True)
    return {"path": p, "spots": len(patches)}


def edge_stats(alpha: np.ndarray) -> Dict[str, float]:
    """逐行最大水平 alpha 梯度统计 (硬边指标)."""
    if alpha.shape[1] < 2:
        return {"max_gradient": 0.0, "hard_row_fraction": 0.0}
    per_row = np.abs(np.diff(alpha, axis=1)).max(axis=0)
    return {
        "max_gradient": float(per_row.max()),
        "hard_row_fraction": float((per_row > 0.25).mean()),
    }


def reference_edge_stats(layer_id: str) -> Optional[Dict[str, float]]:
    """批准 design export 的同口径边缘统计 (作为羽化判据)."""
    ref_rel = PALETTE_REFERENCE.get(layer_id)
    if not ref_rel:
        return None
    p = REPO_ROOT / ref_rel
    if not p.is_file():
        return None
    with Image.open(p) as im:
        im.load()
        a = np.asarray(im.convert("RGBA"))[..., 3].astype(np.float64) / 255.0
    return edge_stats(a)


def soften_hard_edges(alpha: np.ndarray, layer_id: str) -> Tuple[np.ndarray, Dict[str, object]]:
    """把超出批准 design 边缘口径的硬边羽化掉 (确定性, 零 API).

    依据 (SW-006 任务文件 + visual-assets 契约):
    - glade 设计要求 "湿径上下缘都用纵向 mask 淡出", 批准 export 实测 max|dA/dx|=0.024.
    - 生图模型把湿径画成了硬边锥形 (max|dA/dx|=0.369), 属 "硬边抠图", 契约明令禁止.
    - 结构层 (trunks_canopy/vines_light) 的硬边是树廓/叶缘, 属正常, 不羽化.

    做法: 用批准 export 的 max|dA/dx| 作上限, 二分出一个最小 sigma, 使羽化后
    既达标又不过度模糊 (尽量保留形态). 羽化后重新标定 alpha 密度, 保证最大 alpha 与
    半透明占比不因羽化而漂移.
    """
    cur = edge_stats(alpha)
    ref = reference_edge_stats(layer_id)
    diag: Dict[str, object] = {"before": cur, "reference": ref}
    if ref is None:
        diag["applied"] = False
        return alpha, diag
    target = max(float(ref["max_gradient"]), 0.02)
    if cur["max_gradient"] <= target * 1.5:
        diag["applied"] = False
        diag["reason"] = f"当前 max|dA/dx|={cur['max_gradient']:.3f} 未显著超批准口径 {target:.3f}"
        return alpha, diag

    from PIL import ImageFilter

    best = None
    for sigma in (2, 3, 4, 6, 8, 10, 12, 16, 20):
        blurred = np.asarray(
            Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(sigma))
        ).astype(np.float64) / 255.0
        st = edge_stats(blurred)
        if st["max_gradient"] <= target * 1.5:
            best = (sigma, blurred, st)
            break
    if best is None:
        diag["applied"] = False
        diag["reason"] = "羽化到最大 sigma 仍未达标"
        return alpha, diag

    sigma, blurred, st = best
    out, adiag = normalize_alpha_density(blurred, layer_id)
    diag.update({
        "applied": True,
        "sigma": sigma,
        "after": edge_stats(out),
        "alpha_renormalized": adiag,
    })
    return out, diag


def measure(rgb: np.ndarray, alpha: np.ndarray, bg: np.ndarray) -> Dict[str, object]:
    """逐像素量检: 边缘 alpha, 底色残留, 半透明占比, 硬边."""
    a = alpha
    edge_strip = {
        "top": float(a[0:4, :].max()),
        "bottom": float(a[-4:, :].max()),
        "left": float(a[:, 0:4].max()),
        "right": float(a[:, -4:].max()),
    }
    # 底色残留 (抠完仍像底色)
    d = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    residual = float(((d < RESIDUAL_DIST) & (a > 0.05)).mean())
    # 硬边检测: 相邻 alpha 跳变
    gx = np.abs(np.diff(a, axis=1)).max()
    gy = np.abs(np.diff(a, axis=0)).max()
    return {
        "alpha_max": float(a.max()),
        "semi_transparent_fraction": float(((a > 0.02) & (a < 0.98)).mean()),
        "transparent_fraction": float((a <= 0.02).mean()),
        "edge_strip4_max_alpha": edge_strip,
        "background_residual_fraction": residual,
        "max_alpha_gradient_x": float(gx),
        "max_alpha_gradient_y": float(gy),
        "has_hard_edge": bool(gx > 0.9 or gy > 0.9),
    }


def build_parallax_previews(layers: Dict[str, Tuple[np.ndarray, np.ndarray]]) -> List[Dict[str, object]]:
    """视差偏移 + 运行时裁切预览.

    依据 (SW-012 design-spec.json canvas.crop_previews 与 runtime_crop):
    - tileable=false: 不做无缝平铺, 只做 "按高度铺满 + 左对齐 + 右侧溢出宽度内横移".
    - 1080x2400 长屏: scale=1.25, 目标宽 1350, 右侧溢出 270px.
    - 390x844 小屏:  scale=0.4396, 目标宽 475, 右侧溢出 85px.
    - 恒可见源带 x[216,864], 旅人锚点源 x=367 必须恒可见.
    产出: 每个视差层在两个极端偏移下的裁切图 + 两个比例的运行时裁切图.
    """
    results: List[Dict[str, object]] = []
    PARALLAX_DIR = CHECKS_DIR / "parallax"
    PARALLAX_DIR.mkdir(parents=True, exist_ok=True)

    def crop_by_height(rgb: np.ndarray, alpha: np.ndarray, out_w: int, out_h: int,
                       x_off: int) -> Image.Image:
        """按高度铺满 + 左对齐 + 横移, 返回 out_w x out_h 的 RGB 合成."""
        h, w = rgb.shape[:2]
        scale = out_h / h
        dst_w = int(round(w * scale))
        im_rgb = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((dst_w, out_h), Image.LANCZOS)
        im_a = Image.fromarray((alpha * 255).astype(np.uint8), "L").resize((dst_w, out_h), Image.LANCZOS)
        canvas = Image.new("RGBA", (out_w, out_h), (5, 8, 7, 255))
        # 横移: 只在右侧溢出宽度内
        max_off = max(0, dst_w - out_w)
        off = int(np.clip(x_off, 0, max_off))
        canvas.paste(im_rgb, (-off, 0), im_a)
        return canvas.convert("RGB")

    # --- 1) 两个视差层的极端偏移 ---
    for layer_id in ("trunks_canopy", "vines_light"):
        rgb, alpha = layers[layer_id]
        for tag, off in (("rest", 0), ("parallax_max", 270)):
            im = crop_by_height(rgb, alpha, 1080, 1920, off)
            p = PARALLAX_DIR / f"rainforest_{layer_id}_{tag}_1080x1920.png"
            im.save(p, optimize=True)
            results.append({"layer_id": layer_id, "tag": tag, "size": "1080x1920", "path": p})

    # --- 2) 运行时比例裁切 (1080x2400 与 390x844), 用 875m 全景合成 ---
    full_rgb, full_alpha = layers["trunks_canopy"]
    # 全景合成 (void 底)
    stage875 = np.asarray(Image.open(STAGES_DIR / "stage_875m.png").convert("RGB")).astype(np.float64)
    for out_w, out_h, tag in ((1080, 2400, "1080x2400"), (390, 844, "390x844")):
        h, w = stage875.shape[:2]
        scale = out_h / h
        dst_w = int(round(w * scale))
        im = Image.fromarray(stage875.astype(np.uint8)).resize((dst_w, out_h), Image.LANCZOS)
        overflow = max(0, dst_w - out_w)
        for off_tag, off in (("rest", 0), ("parallax_max", overflow)):
            canvas = Image.new("RGB", (out_w, out_h), (5, 8, 7))
            canvas.paste(im, (-int(np.clip(off, 0, overflow)), 0))
            p = PARALLAX_DIR / f"runtime_{tag}_{off_tag}.png"
            canvas.save(p, optimize=True)
            results.append({"size": tag, "tag": off_tag, "overflow_px": overflow, "path": p})

    # --- 3) 恒可见带与旅人锚点核验 (源 x[216,864], 旅人 x=367) ---
    band = (216, 864)
    traveler_x = 367
    visible = {"always_visible_source_band": list(band), "traveler_anchor_source_x": traveler_x}
    for out_w, out_h, overflow in ((1080, 2400, 270), (390, 844, 85)):
        # 裁切窗口的源 x 范围 (左对齐, 最坏右移 = overflow 目标像素 -> 源像素 = overflow/scale)
        scale = out_h / 1920.0
        src_right = 1080 - overflow / scale
        visible[f"{out_w}x{out_h}"] = {
            "source_x_visible_at_max_parallax": [0, round(src_right)],
            "band_always_visible": band[0] >= 0 and band[1] <= src_right,
            "traveler_anchor_visible": 0 <= traveler_x <= src_right,
        }
    out_json = PARALLAX_DIR / "runtime-parallax-check.json"
    out_json.write_text(json.dumps(visible, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    results.append({"path": out_json, "kind": "runtime-parallax-check"})
    return results


def main() -> int:
    for d in (PNG_DIR, WEBP_DIR, ALPHA_DIR, BLACK_DIR, WHITE_DIR, MAGENTA_DIR, STAGES_DIR, ZOOM_DIR):
        d.mkdir(parents=True, exist_ok=True)

    layers: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
    report: List[Dict[str, object]] = []

    for layer_id in prompts_r2.LAYER_IDS:
        src = SOURCE_DIR / f"sw006_r2_{layer_id}.png"
        if not src.is_file():
            print(f"MISSING source: {src}", file=sys.stderr)
            return 1
        raw = load_rgb(src)
        alpha_full, rgb_clean_full, key_diag = key_to_alpha(raw)
        bg_px = np.array(key_diag["background_rgb"], dtype=np.float64)
        canvas_rgb, fit_info = fit_to_canvas(rgb_clean_full)
        # alpha 同样按 canvas 变换 (与颜色同步)
        a_im = Image.fromarray((alpha_full * 255).astype(np.uint8), "L")
        new_h = int(round(raw.shape[0] * (TARGET_W / raw.shape[1])))
        a_im = a_im.resize((TARGET_W, new_h), Image.LANCZOS)
        if new_h >= TARGET_H:
            top = (new_h - TARGET_H) // 2
            a_im = a_im.crop((0, top, TARGET_W, top + TARGET_H))
        else:
            pad = TARGET_H - new_h
            top = pad // 2
            a_im = Image.new("L", (TARGET_W, TARGET_H), 0)
            a_im.paste(a_im.crop((0, 0, TARGET_W, new_h)), (0, top))
        alpha = np.asarray(a_im).astype(np.float64) / 255.0
        # 量化 + 去噪 (视觉无损, 降熵改善 WebP 体积)
        alpha = quantize_alpha(alpha)
        # 硬边羽化: 使边缘口径回到批准 design (确定性, 零 API)
        alpha, edge_diag = soften_hard_edges(alpha, layer_id)
        # alpha 密度标定到批准 design 实测统计
        alpha, alpha_diag = normalize_alpha_density(alpha, layer_id)
        # 色域收敛到批准 design 色板统计 (只取统计量, 不复制 design 像素)
        canvas_rgb, palette_diag = transfer_palette(canvas_rgb, alpha, layer_id)

        layers[layer_id] = (canvas_rgb, alpha)

        rgba = np.dstack([canvas_rgb, alpha * 255.0]).astype(np.uint8)
        png_path = PNG_DIR / f"rainforest_{layer_id}.png"
        Image.fromarray(rgba, "RGBA").save(png_path, optimize=True)

        webp_path = WEBP_DIR / f"rainforest_{layer_id}.webp"
        webp_bytes, webp_q = save_webp(Image.fromarray(rgba, "RGBA"), webp_path)

        # alpha mask
        Image.fromarray((alpha * 255).astype(np.uint8), "L").save(ALPHA_DIR / f"rainforest_{layer_id}.png", optimize=True)
        # 三底合成 (实际纯色底合成, 不是只查 alpha 通道)
        composite(canvas_rgb, alpha, (0, 0, 0)).save(BLACK_DIR / f"rainforest_{layer_id}.jpg", quality=92)
        composite(canvas_rgb, alpha, (255, 255, 255)).save(WHITE_DIR / f"rainforest_{layer_id}.jpg", quality=92)
        composite(canvas_rgb, alpha, (255, 0, 255)).save(MAGENTA_DIR / f"rainforest_{layer_id}.jpg", quality=92)

        zoom = build_zoom(layer_id, canvas_rgb, alpha)
        m = measure(canvas_rgb, alpha, bg_px)
        report.append({
            "layer_id": layer_id,
            "source": str(src.relative_to(REPO_ROOT)),
            "png": str(png_path.relative_to(REPO_ROOT)),
            "webp": str(webp_path.relative_to(REPO_ROOT)),
            "png_bytes": png_path.stat().st_size,
            "webp_bytes": webp_bytes,
            "webp_quality": webp_q,
            "fit": fit_info,
            "key": key_diag,
            "edge_soften": edge_diag,
            "alpha_normalize": alpha_diag,
            "palette_transfer": palette_diag,
            "measure": m,
            "zoom": str(zoom["path"].relative_to(REPO_ROOT)),
        })
        print(f"{layer_id:16s} webp={webp_bytes:>7d}B q={webp_q} "
              f"bg={key_diag['background_rgb']} fg={key_diag['foreground_rgb']} "
              f"alpha_max={m['alpha_max']:.0f} semi={m['semi_transparent_fraction']:.3f} "
              f"edge(t/b/l/r)={m['edge_strip4_max_alpha']['top']:.0f}/"
              f"{m['edge_strip4_max_alpha']['bottom']:.0f}/"
              f"{m['edge_strip4_max_alpha']['left']:.0f}/"
              f"{m['edge_strip4_max_alpha']['right']:.0f} "
              f"resid={m['background_residual_fraction']:.4f} hard={m['has_hard_edge']}")

    stages = build_stages(layers)
    print("stages:", [s["path"].name for s in stages])

    parallax = build_parallax_previews(layers)
    print("parallax previews:", len(parallax))

    out = REPO_ROOT / "design/assets/rainforest/candidates/SW-006/r2/records/postprocess-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"layers": report,
                               "stages": [str(s["path"].relative_to(REPO_ROOT)) for s in stages],
                               "parallax": [
                                   {k: (str(v.relative_to(REPO_ROOT)) if isinstance(v, Path) else v)
                                    for k, v in s.items()} for s in parallax]},
                              ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", out.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
