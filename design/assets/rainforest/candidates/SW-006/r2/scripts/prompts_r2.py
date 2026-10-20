#!/usr/bin/env python3
"""
SW-006 R2 五层生图提示词 (可追溯生产输入, 由 SW-012 R1 批准 prompts.md 派生).

派生规则 (与 D-009 / SW-006 任务文件一致):
- 主体/禁画/色板/构图/负提示 逐层沿用 SW-012 批准 prompts.md (只读, 不改原字节).
- **唯一必要改动**: 生图 API 不支持真透明 (SW-006 任务文件: "API返回不支持真透明,
  使用可分离底/蒙版并逐像素验图, 不让模型画棋盘"). 因此把 prompts.md 里的
  "背景纯透明" 改写为 "完全均匀的纯洋红 #FF00FF 可分离底", 由 produce_r2.py
  做逐像素抠像 + 去洋红溢色, 得到真透明 RGBA.
  原始 prompts.md 的负提示保留, 并追加 "纯色平涂底, 不画阴影/渐变/噪点".
- phase opacity 不烘焙: 每层按自身完整不透明度出图, 运行时由 app 按米数衰减.

prompt_ref 用 "文件#键" 形式, 供 manifest.call.prompt_ref 精确回指.
"""

from __future__ import annotations

# 所有层共用的负提示 (SW-012 prompts.md §0 通用负提示, 原文保留)
COMMON_NEGATIVE = (
    "棋盘格, 方格, 同心环, 重复几何纹理, 32px/8px 对角网纹, 马赛克, 噪点颗粒, "
    "矩形底色, 硬边抠图, 白边, 描边外发光, 文字, 水印, logo, UI, 按钮, 图标, 人物, 旅人, "
    "建筑, 道路指示牌, 高对比, 霓虹, 闪光, 雷暴, 闪电, 恐怖元素, 惊吓, 暖褐色调, 干叶, "
    "干爽土路, 落叶林, 鸟群, 斜射长条光束, HUD"
)

# 可分离底 (统一) —— 雨林色板全为冷湿绿, 洋红 #FF00FF 与之色相最远, 抠像最干净
SEPARABLE_BG = (
    "背景为完全均匀的纯洋红色 #FF00FF 平涂底色, 无渐变, 无噪点, 无暗角, "
    "主体边缘不向背景投任何阴影, 背景上不出现任何其他元素"
)

#: 孤立层 (抠图) 强制框架 —— 放在提示词最前面.
#:
#: 依据: 探针尝试 (ledger seq=1) 证明模型会把 "雨林深处…" 理解成整幅场景,
#: 底色只出现在天空缺口, 无法抠像. 故本轮把 "素材图层/抠图/四周留白" 提到
#: 提示词最前, 明确禁止场景/天空/地面/环境.
CUTOUT_FRAME = (
    "素材图层抠图, 单层孤立图元, 像贴纸素材表: "
    "画面里只有下面描述的这一层内容, "
    "除这一层以外的所有区域 (上下左右四周、所有空隙、所有树间空隙) "
    "一律是纯粹平涂的纯洋红色 #FF00FF, "
    "不画场景, 不画环境, 不画天空, 不画地面, 不画远景, 不画第二套树林, 不画地平线, "
    "没有背景风景, 没有全景构图。"
)

#: 铺满画布 (不画"贴纸卡片") —— 探针 seq=3 证明模型默认把内容缩进一圈,
#: 四周留洋红边, 形成可见的矩形硬边 (visual-assets 契约: 实际纯色底合成不得有矩形底).
CUTOUT_FILL = (
    "这一层的内容必须铺满整张画布: 画布的四条边就是元素被裁切的位置, "
    "元素直接顶到并越过画布边缘, 不要在画布内侧留一圈空隙或洋红边框, "
    "不要把内容缩成画布中央的一个矩形色块, 不要画任何外框、描边、卡片底或圆角边框。"
)

#: 通用孤立层收尾约束
CUTOUT_TAIL = (
    "以上只有这一层, 元素四周留出大片纯洋红空隙, 空隙处必须完全是平涂洋红, "
    "不得有渐变、纹理、噪点或暗角。"
)

#: 逐层边缘语义 —— 结构层必须被画布裁切 (出血), 发光层必须四周归零.
#:
#: 依据 (SW-012 批准 design-spec.json 各层 transparent_regions):
#: - trunks_canopy: "树干可超出顶部; 横向铺满略超宽" -> 顶/左右出血, 底不画地面
#: - vines_light:  "两端可超出画布宽" -> 左右/顶部出血, 底部留空
#: - mist/distant_glow/glade: 四边 alpha 平滑归零, 无矩形底 -> 四周必须淡出为洋红
#:
#: 探针 (ledger seq=3) 证明模型默认会画成"贴纸卡片": 内容缩进一圈, 四周留洋红边,
#: 形成矩形硬边. 卡片式边框在运行时是可见的矩形硬边, 违反 visual-assets 契约, 故
#: 逐层显式规定边缘行为.
EDGE_RULES: dict[str, str] = {
    "trunks_canopy": (
        "树干和树冠必须从画布上边缘和左右边缘被直接裁切 (出血), "
        "树冠顶到画面上边, 树干一直延伸到左右边缘外, 画布上不出现任何边框、留白或卡片外框。"
    ),
    "vines_light": (
        "垂藤从画布上边缘垂下并被上边缘裁切, 部分藤条延伸到左右边缘外被裁切, "
        "画布上不出现任何边框、留白或卡片外框。"
    ),
    "mist": (
        "雾气在画布四周自然淡出到完全透明, 洋红从边缘向内柔和过渡, "
        "不出现任何硬边、边框、卡片外框或矩形轮廓。"
    ),
    "distant_glow": (
        "漏光与水汽在画布四周自然淡出到完全透明, 洋红从边缘向内柔和过渡, "
        "不出现任何硬边、边框、卡片外框或矩形轮廓。"
    ),
    "glade": (
        "辉光与湿径在画布四周自然淡出到完全透明, 洋红从边缘向内柔和过渡, "
        "不出现任何硬边、边框、卡片外框或矩形轮廓。"
    ),
}

# 参考图 (SW-012 批准 export, 仅作风格/构图参考输入, 不作为生产候选)
REFERENCE_FILES = {
    "mist": "design/05-visual-design/SW-012/r1/exports/rainforest_mist.png",
    "trunks_canopy": "design/05-visual-design/SW-012/r1/exports/rainforest_trunks_canopy.png",
    "vines_light": "design/05-visual-design/SW-012/r1/exports/rainforest_vines_light.png",
    "distant_glow": "design/05-visual-design/SW-012/r1/exports/rainforest_distant_glow.png",
    "glade": "design/05-visual-design/SW-012/r1/exports/rainforest_glade.png",
}

#: SW-012 批准 prompts.md §1-5 的正向提示词主体 (逐字沿用), 追加可分离底改写
PROMPTS: dict[str, str] = {
    "mist": (
        "安静二维扁平插画，雨林贴地湿雾与几缕横向飘雾，冷雾青绿色 #1A2E28/#2F4E44 很低不透明度，"
        "边缘完全柔化，左下角一团略亮雾心，潮湿空气感，无硬边无矩形底无纹理，"
        "竖构图 9:16，大面积暗部留白，宁静。"
        "画面只有贴地湿雾这一层内容，雾团之外就是底色，不画树干树叶藤蔓光柱地面路径人物。"
        + SEPARABLE_BG
    ),
    "trunks_canopy": (
        "安静二维插画，雨林深处数根带巨大板根的粗壮湿润树干，竖向柔和明暗渐变，右上微妙边光，"
        "少量苔藓质感，上方连片层叠的巨大阔叶树冠形成顶棚并留出两处不规则天空缺口，"
        "低饱和冷湿墨绿 #1E3D36/#2A5248/#1C4236，树间与林隙为空，"
        "竖构图 9:16，浓密但暗部有呼吸留白，无地面无人物。"
        "画面只有树干与顶棚这一层内容，不要第二套树林。"
        + SEPARABLE_BG
    ),
    "vines_light": (
        "安静二维插画，雨林前景从画面顶部垂下的数条细长弯曲藤蔓与对生小叶，藤尖少量水珠，"
        "藤叶之间散落柔和的暖绿色点状光斑 #C4D4A8（叶隙漏光，圆形柔斑非光束），"
        "低饱和湿绿 #3A5C4C/#6A8A60，藤蔓集中在画面上中部不到一半，下方留空，"
        "竖构图 9:16，干净，空气湿润。"
        "画面只有垂藤与光斑这一层内容，不画树干顶棚，不画成束斜射光。"
        + SEPARABLE_BG
    ),
    "distant_glow": (
        "极简安静的雨林冠隙漏光，两三团近椭圆的柔和斑驳光斑从顶棚缺口透下，"
        "淡暖白绿 #A8C9A6 很低不透明度，边缘完全柔化，无直线无几何边界，"
        "下方几缕横向极淡青绿水汽，竖构图 9:16，干净，潮湿空气感，无长斜射光束无鸟。"
        "画面只有漏光与水汽这一层内容，不画树林不画天空填充。"
        + SEPARABLE_BG
    ),
    "glade": (
        "极简单一柔和径向辉光，雨林深处一条湿润反光的小径通向一团安静淡绿光 #9FC09A，"
        "冷青湿面微光 #5A7D72，椭圆辉光中心柔和最亮、边缘无缝淡出，"
        "小径上下缘淡出、画面底边无硬边，无环无光线无纹理，竖构图 9:16，"
        "大面积暗部留白，宁静，将至终点但不炫技。"
        "画面只有辉光与湿径这一层内容，不画树林不画干叶干爽土路。"
        + SEPARABLE_BG
    ),
}

#: 禁止绘制内容 (SW-012 prompts.md 各层"禁画", 逐层保留)
FORBIDDEN: dict[str, str] = {
    "mist": "禁画: 树干、树叶、藤蔓、光柱、地面路径、人物、整片背景填充、任何纹理/网格。",
    "trunks_canopy": "禁画: 干叶土坡、土路、藤蔓、漏光光束、鸟、人物、第二套树林、树皮照片纹理。",
    "vines_light": "禁画: 树干顶棚主体、成束斜射光、鸟、人物、文字 UI、串珠式等距重复斑点。",
    "distant_glow": "禁画: 长梯形/多边形光束硬边、光束轮廓线、放射光线阵列、十字星芒、镜头眩光、第二套树林或背景、天空填充、远鸟。",
    "glade": "禁画: 同心圆环、光圈、放射光线、第二套树林、干叶、干爽土路、道路标线/脚印、亮斑阵列、终点大门建筑闪光庆祝。",
}

#: 层参数 (D-009 冻结 canonical 参数, 供 manifest / 合成阶段使用)
LAYER_SPECS: dict[str, dict] = {
    "mist":         {"render_role": "overlay",  "parallax": 0.0, "at_meters": 90,  "to_opacity": 0.55, "fade_meters": 20},
    "trunks_canopy": {"render_role": "parallax", "parallax": 0.30, "at_meters": 270, "to_opacity": 0.85, "fade_meters": 25},
    "vines_light":  {"render_role": "parallax", "parallax": 0.60, "at_meters": 450, "to_opacity": 1.00, "fade_meters": 25},
    "distant_glow": {"render_role": "overlay",  "parallax": 0.0, "at_meters": 675, "to_opacity": 0.85, "fade_meters": 25},
    "glade":        {"render_role": "overlay",  "parallax": 0.0, "at_meters": 855, "to_opacity": 0.90, "fade_meters": 20},
}

#: 阶段预览米数 (fade 完成点, SW-012 phase_table.preview_meters)
STAGE_METERS = [0, 110, 295, 475, 700, 875]

#: 目标画布 (D-009 冻结)
CANVAS = (1080, 1920)

LAYER_IDS = ["mist", "trunks_canopy", "vines_light", "distant_glow", "glade"]


def build_prompt(layer_id: str) -> str:
    """最终正向提示词 = 孤立层框架 + 铺满画布 + 主体 + 边缘语义 + 禁画 + 负提示."""
    return (
        f"{CUTOUT_FRAME}\n"
        f"{CUTOUT_FILL}\n"
        f"{PROMPTS[layer_id]}\n"
        f"{EDGE_RULES[layer_id]}\n"
        f"{FORBIDDEN[layer_id]}\n"
        f"{CUTOUT_TAIL}\n"
        f"负提示: {COMMON_NEGATIVE}"
    )


def prompt_ref(layer_id: str) -> str:
    return (
        "design/assets/rainforest/candidates/SW-006/r2/scripts/prompts_r2.py#"
        f"{layer_id} (派生自 design/05-visual-design/SW-012/r1/prompts.md §"
        f"{LAYER_IDS.index(layer_id) + 1}, 仅背景改写为可分离洋红底)"
    )


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps({lid: build_prompt(lid) for lid in LAYER_IDS}, ensure_ascii=False, indent=2))
    sys.exit(0)
