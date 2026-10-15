# SW-011 r1 · 森林图片设计与通用视觉规范（design_candidate）

- 任务/负责人：SW-011「森林图片设计与通用视觉规范」/ trae-design
- 接收者：antigravity（独立审核）；批准后供 MiniMax 制作正式素材
- 基线 commit：`17a8663b0b6f3312a4d2dcc1637458e9ed0fc799`（已从最新 origin/main 快进；初稿模型与相位经该基线 ForestShell/forest.json 复核一致）
- 依据：`docs/collaboration/contracts/visual-design.md`、`app/src/main/assets/scenes/forest.json`、`app/src/main/java/com/sensewalk/app/ui/session/ForestShell.kt`、`ASSETS.md`、`design/01-scenes-terrain/forest.md`
- 状态：**design_candidate**（设计稿，不是素材候选，也不是 Android 接入/真机证据）

## 这一轮做了什么

在不改动任何 app 源码、`forest.json`、现有 layer ID/相位/parallax/旅人程序绘制与布局基线的前提下，交付一套**可编辑、可复现**的森林五层视觉设计：

1. 一个统一的图元模型 `source/sw011_model.py`（1080×1920 逻辑像素，固定随机种子），两个后端 `source/sw011_render.py` 消费同一模型：
   - 手写可编辑 SVG（`source/svg/*.svg`，含五层 + 一张 master 合成）；
   - 本地 Python（PIL+numpy）2× 超采样渲染真实 RGBA PNG（`exports/`）与全部预览（`previews/`）。
   - 矢量源与栅格导出共享同一几何/色板/相位，保证一致。
2. 统一风格/色板/构图说明：`previews/composition_guide.png` 与终景风格参考 `previews/forest_style_reference.png`。
3. 五层分层标注：`previews/layer_map.png`；每层黑/白/洋红三底检查：`previews/layer_checks/`。
4. 0/100/265/425/630/785m 六阶段合成：`previews/stages/`，透明度按既有 smoothstep 与 `fadeMeters` 真实计算。
5. 1080×1920 / 1080×2400 / 390×844 三比例裁切参考（标注安全区、45% 触控区、旅人 x=.34/脚底 y=.865）：`previews/crops/`。
6. 给 MiniMax 的逐层生产提示词与负提示：`prompts.md`；机器可读规格 `design-spec.json`；文件哈希清单 `design-manifest.json`。
7. 2026-10-14 按第四轮核查补的两类复核（不重画既有产物，仅新增）：
   - 每层**内容热点 + 画布四缘 × 黑/白/洋红底 2× 最近邻放大**：`previews/zoom/forest_<layer>_zoom.png`，最近邻不美化，用于看抠像边缘、暗部保留、光晕是否有白边/矩形底/32px 重复；
   - **逐像素复刻 `ForestShell.drawImageLayer` 的运行时裁切复核**：`previews/runtime_crop/`（视口窗口图、390×844 静止/最大视差两极端实渲、量化 `runtime-crop-check.json`）。生成器 `source/sw011_supplement.py` 与主渲染共享同一模型。

## 设计决策与理由

- **美术身份**：安静二维插画、干净剪影、低饱和、柔和林光、适量留白；干叶通透的落叶林，明确避开湿雾浓密雨林。旅人向右、侧视、始终小于景，不抢戏（角色本轮仍由程序绘制，素材中不画人）。
- **五层职责严格分离**，避免历史上"整景重复/每层夹带完整背景"：
  - `tree_outline` 只给远处阔叶冠线；`tree_trunks` 只给中景竖干、细边光与极弱林间空气光，不画地面；`leaf_path` 只给下部干叶土坡；`light_shows` 只给三束斜射体积光与三只远鸟；`clearing` 只给单一空地辉光。
- **针对历史棋盘残留的结构性修正**（ASSETS.md 记录 light_shows 32px 对角能量 55%、clearing 21.8%）：两个 overlay 层改为纯解析渐变——光束用**纵向拉伸的椭圆径向辉光**（光源移出画面、峰值低、四边平滑衰减到 0），空地用**单一椭圆径向辉光**。两者都不含任何可重复的位图纹理、多边形硬边、同心环或矩形底，从生成方式上消除周期纹理。
- **树干体积感**：竖向渐变（两端没入暗部、中上受光）+ 一根最暗前景剪影树；林间竖光压到 alpha≤.11 并大半径柔化，只作空气感，不形成旧版那种等距亮柱。
- **触控区保护**：`leaf_path` 在中央纵向带与旅人脚底附近刻意稀疏，45% 操作区保持低对比；所有标注只出现在预览，不进入 `exports/` 单层图。

## 坐标、相位与运行时对齐

- 画布 1080×1920，归一化坐标；旅人 x=.34、脚底 y=.865；下方 45% 触控区；关键内容收在中央 80% 宽、y=.12–.92。
- 相位与 `forest.json` 完全一致：outline 80m/.60/20、trunks 240m/.70/25、leaf_path 400m/.80/25、light_shows 600m/.65/30、clearing 760m/.90/25；`opacity=target·smoothstep((m-at)/fade)`，停走即冻结。
- 裁切/视差与 `ForestShell.drawImageLayer` 对齐：按**高度**铺满（scale=screenH/imageH）、左对齐，仅在右侧溢出宽度内横移；parallax 0.3/0.3/0.6，两 overlay 不视差。预览透明度不烘焙进单层 RGB/alpha。

## 中央/边缘放大与运行时裁切复核（2026-10-14 补）

- **局部放大（contracts §4）**：每层给 2–3 个真正框住主体/渐变中心的内容热点，外加画布上/下/左/右四缘，在黑/白/洋红底上 2× 最近邻放大（不做平滑，避免美化掉接缝）。重点层结论：`light_shows` 右上光束是连续斜向柔渐变、远鸟为细弧 V 形，三底无白边；`clearing` 辉光中心平滑、向右以低 alpha 连续漫出，无同心环；两历史问题层在放大下均无 32px 对角重复。
- **运行时裁切逐像素复核**：用与 `drawImageLayer` 相同的整数运算（`dstW=floor(1080*scale+0.5)`、`overflow=max(0,dstW-w)`、`xOffset=-clamp(shift,0,overflow)`）实渲最小屏 390×844 的静止与最大视差两极端。量化结果（`runtime-crop-check.json`）：
  - 1080×1920 scale=1.0 / 溢出 0；1080×2400 scale=1.25 / dstW 1350 / 溢出 270；390×844 scale≈0.4396 / dstW 475 / 溢出 85。
  - 跨三屏**恒可见源带 x[216,864]**；旅人源锚点 x=367 落在带内，任何视差位置都不被移出屏幕。
  - overlay 接缝判据（四边最外/内邻各 4px）：两 overlay 均**无 alpha≥64 的实色边像素**、外缘不亮于内邻（无白边光晕/矩形硬底）；`light_shows` 仅上缘 max α=15、`clearing` 仅右缘 max α=21 的连续软渐变，属柔光自然漫到屏边，屏外为设备边框不可见，非接缝缺陷。

## 如何复现

```bash
cd design/05-visual-design/SW-011/r1/source
python3 sw011_render.py       # 重新生成 source/svg、exports、previews 主产物
python3 sw011_supplement.py   # 仅新增 previews/zoom 与 previews/runtime_crop 复核
```

仅依赖 Python3 + Pillow + numpy（本地，无外部/付费 API）。固定随机种子，重复运行结果确定。

## 明确未做 / 待验证

- 不修改 `app/`、`forest.json`、registry、MiniMax 候选与正式 assets；不出角色 sprite/动画；不重制其余场景；不新增外部付费生图 API（本轮零外部调用）。
- 这些是**设计参考导出**，不放入 `app/assets`，不满足每层 ≤400KB/每景 ≤2MB 的入包预算（正式压缩由 MiniMax 完成）。
- 三层 parallax 标 `tileable=false`：当前运行时只支持右侧溢出宽度内有限滑动，本稿不做也不宣称无缝平铺。
- 未提供 PSD/Figma（工具不具备，不虚构）；contracts §4 建议的中央/边缘局部放大与运行时实际裁切复核已于 2026-10-14 补齐（见 `previews/zoom/`、`previews/runtime_crop/`）。
- 0m 已用像素统计确认仅含程序旅人（非背景像素 1780 个，全在旅人包围盒），无层提前揭示；最终视觉合格性仍以 Antigravity 独立目检与后续真机走查为准。

## 目录

```text
r1/
  README.md / design-spec.json / design-manifest.json / prompts.md
  source/
    sw011_model.py · sw011_render.py · sw011_supplement.py
    svg/forest_{tree_outline,tree_trunks,leaf_path,light_shows,clearing,master}.svg
  exports/forest_<layer>.png            # 五层真实 RGBA 单层导出（参考，非入包素材）
  previews/
    forest_style_reference.png · composition_guide.png · layer_map.png
    stages/stage_{000,100,265,425,630,785}m.png
    crops/crop_{1080x1920,1080x2400,390x844}.png
    layer_checks/forest_<layer>_{black,white,magenta}.jpg
    zoom/forest_<layer>_zoom.png                 # 内容热点+四缘 × 三底 2× 放大
    runtime_crop/runtime_viewport_map.png        # 三屏静止/最大视差源窗口
    runtime_crop/runtime_{rest,parallax_max}_390x844.png
    runtime_crop/runtime-crop-check.json         # 逐像素裁切量化结果
```
