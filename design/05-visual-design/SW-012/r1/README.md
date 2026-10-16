# SW-012 r1 · 雨林 900m 图片设计（design_candidate）

- 任务/负责人：SW-012「雨林 900m 图片设计」/ trae-design
- 接收者：antigravity（独立审核）；批准后启用 SW-006，供 MiniMax 制作正式素材
- 基线 commit：`904ab019dbc31a9a84a00d410b85868c3ddfb9b9`（已 fetch 最新 origin/main 并从该提交建任务分支；SW-011 53 文件设计包已 accepted 并入 main）
- 依据：`docs/collaboration/contracts/visual-design.md`、`docs/collaboration/contracts/visual-assets.md`、`design/01-scenes-terrain/rainforest.md`、`DEVELOPMENT.md` §7.1/§7.7/§12.4、已批准的 `design/05-visual-design/SW-011/r1/`
- 状态：**design_candidate**（设计稿，不是素材候选，也不是 Android 接入/真机证据）
- 命名：五层 layer ID / parallax 均为 **proposed**，由 Antigravity 审稿冻结后供 MiniMax/ZCode 消费；仓库当前不存在 `rainforest.json` 与雨林 Shell，本稿不伪造其已存在。

## 这一轮做了什么

在不改动任何 app 源码、不改动已批准 SW-011、不新增外部付费 API 的前提下，复用 SW-011 的图元模型契约与渲染/复核结构，交付一套**可编辑、可复现**的雨林五层视觉设计：

1. 统一图元模型 `source/sw012_model.py`（1080×1920 逻辑像素，固定随机种子），两个后端消费同一模型：
   - 手写可编辑 SVG（`source/svg/*.svg`，五层 + 一张 master 合成）；
   - 本地 Python（PIL+numpy）2× 超采样渲染真实 RGBA PNG（`exports/`）与全部预览（`previews/`），零外部网络/付费 API。
2. 风格/色板/构图与「雨林 vs 森林」差异说明：`previews/composition_guide.png`；875m 终景风格参考：`previews/rainforest_style_reference.png`。
3. 五层分层标注：`previews/layer_map.png`；每层黑/白/洋红三底检查：`previews/layer_checks/`。
4. **fade 完成点**六阶段合成：`previews/stages/`（0/110/295/475/700/875m，透明度按 smoothstep 与各层 fadeMeters 真实计算，最后一张 ≤ 900m 终点）。
5. 1080×1920 / 1080×2400 / 390×844 三比例裁切参考（标注安全区、45% 触控区、旅人 x=.34/脚底 y=.865）：`previews/crops/`。
6. 每层内容热点+画布四缘 × 三底 2× 最近邻放大：`previews/zoom/`。
7. 逐像素对齐已批准 `drawImageLayer` 语义（按高度铺满/左对齐/右侧溢出）的运行时裁切复核：`previews/runtime_crop/`（视口窗口图、390×844 静止/最大视差两极端、量化 JSON）。
8. 给 MiniMax 的逐层生产提示词与负提示：`prompts.md`；机器可读规格 `design-spec.json`；文件哈希清单 `design-manifest.json`。

## 五层与时间轴（id 为 proposed）

| 解锁 m | layer（proposed） | type | parallax | 目标 opacity | fade m | 预览（fade 完成点） |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | void（程序） | — | — | 1.0 | — | 0m |
| 90 | `mist` | overlay | 0.0 | .55 | 20 | 110m |
| 270 | `trunks_canopy` | parallax | 0.30 | .85 | 25 | 295m |
| 450 | `vines_light` | parallax | 0.60 | 1.00 | 25 | 475m |
| 675 | `distant_glow` | overlay | 0.0 | .85 | 25 | 700m |
| 855 | `glade` | overlay | 0.0 | .90 | 20 | 875m |

900m 终点保持景色完整、不切屏炫技；停走即冻结揭示，禁止一键显示全部。

## 设计决策与理由

- **美术身份（不是森林换色相）**：潮湿浓绿、轻雾裹身、阔叶遮天、藤蔓光斑、水气温润。色板全部低饱和冷湿绿（雾青/苔色/冷青湿面 + 藤蔓暖绿点光），全稿不出现森林暖褐 `#A89060`、干叶与干爽土路。
- **结构差异化**：雨林用带**板根的粗壮湿干 + 连片阔叶顶棚（留两处林隙）**，森林是细高疏干与通透树荫；雨林前景是**垂藤/对生叶/藤蔓点状光斑**，森林是斜射长光束与远鸟（雨林不画鸟）；雨林用贴地湿雾、流动水汽与幽径**湿径反光**表达湿度。
- **五层职责严格分离**：`mist` 只给雾/湿气；`trunks_canopy` 只给板根湿干与阔叶顶棚（不画地面）；`vines_light` 只给前景垂藤/叶/光斑；`distant_glow` 只给林隙斑驳漏光与水汽；`glade` 只给单一幽径辉光与湿径。没有一层夹带整套背景。
- **overlay 全部为纯解析软渐变**：雾、漏光、幽径辉光都由椭圆径向/柔化椭圆构成，末端 stop alpha=0，从生成方式上杜绝棋盘/同心环/矩形底；飘雾与水汽带几何上收进屏内，给大半径模糊留扩散余量。
- **触控区保护**：垂藤最长止于 y≈.39，湿雾在下 45% 保持低对比，旅人 x=.34 竖线避开板根与藤蔓；所有标注只出现在预览，不进入 `exports/` 单层图。

## 坐标、相位与运行时对齐

- 画布 1080×1920，归一化坐标；旅人 x=.34、脚底 y=.865（程序绘制，素材不画人）；下方 45% 触控区；关键内容收中央 80% 宽、y=.12–.92；光源统一右上。
- 相位取 `rainforest.md §4` 时间轴：90/.55/20、270/.85/25、450/1.0/25、675/.85/25、855/.90/20；`opacity=target·smoothstep((m-at)/fade)`。
- 裁切/视差沿用已批准语义：按**高度**铺满（scale=screenH/imageH）、左对齐，仅在右侧溢出宽度内横移；parallax 0.30/0.60，三个 overlay 不视差。雨林 Shell 尚未存在，故这是对齐森林渲染器的**设计复核**，非 Android 证据。预览透明度不烘焙进单层 RGB/alpha。

## 自检与量化证据

- 三比例几何：1080×1920 scale=1/溢出 0；1080×2400 scale=1.25/dstW 1350/溢出 270；390×844 scale≈0.4396/dstW 475/溢出 85。跨三屏**恒可见源带 x[216,864]**，旅人源锚点 x=367 在静止与最大视差两极端恒可见（`runtime-crop-check.json` 全部 pass）。
- overlay 接缝（四边最外/内邻各 4px）：三层均**无 alpha≥64 实色边像素**、外缘不亮于内邻；实测边缘最大 alpha 为 mist 12（底/左/右）、distant_glow 0、glade 4（底），均为连续软渐变，配合三底放大目检无白边/矩形底/棋盘/同心环。
- 六阶段实渲演进连续；0m 仅程序旅人；雨林终景与 SW-011 森林终景并排目检，干湿/色温/林相/景深明确可分。

## 如何复现

```bash
cd design/05-visual-design/SW-012/r1/source
python3 sw012_render.py       # 重新生成 source/svg、exports、previews 主产物
python3 sw012_supplement.py   # 生成 previews/zoom 与 previews/runtime_crop 复核
```

仅依赖 Python3 + Pillow + numpy（本地，无外部/付费 API）。固定随机种子，重复运行结果确定。

## 明确未做 / 待验证

- 不修改 `app/`、registry、MiniMax 工具/候选与正式 assets；不出角色 sprite/动画；不做音频（`rainforest.md §3` 声景）；不做 app 接线或真实素材验收；不改 900m 距离、速度/门禁/布局与失败后退文案规则。
- 这些是**设计参考导出**，不放入 `app/assets`，不满足每层 ≤400KB/每景 ≤2MB 的入包预算（正式压缩由 MiniMax SW-006 完成）。
- 两个视差层标 `tileable=false`：当前渲染语义只支持右侧溢出宽度内有限滑动，本稿不做也不宣称无缝平铺。
- 未提供 PSD/Figma（工具不具备，不虚构）；真实可编辑源为 SVG + Python 图元模型。
- 最终视觉合格性以 Antigravity 独立目检/量检与后续 MiniMax 候选、真机走查为准；设计 approved 不等于素材或 Android 完成。

## 目录

```text
r1/
  README.md / design-spec.json / design-manifest.json / prompts.md
  source/
    sw012_model.py · sw012_render.py · sw012_supplement.py
    svg/rainforest_{mist,trunks_canopy,vines_light,distant_glow,glade,master}.svg
  exports/rainforest_<layer>.png          # 五层真实 RGBA 单层导出（参考，非入包素材）
  previews/
    rainforest_style_reference.png · composition_guide.png · layer_map.png
    stages/stage_{000,110,295,475,700,875}m.png
    crops/crop_{1080x1920,1080x2400,390x844}.png
    layer_checks/rainforest_<layer>_{black,white,magenta}.jpg
    zoom/rainforest_<layer>_zoom.png                 # 内容热点+四缘 × 三底 2× 放大
    runtime_crop/runtime_viewport_map.png            # 三屏静止/最大视差源窗口
    runtime_crop/runtime_{rest,parallax_max}_390x844.png
    runtime_crop/runtime-crop-check.json             # 逐像素裁切量化结果
```
