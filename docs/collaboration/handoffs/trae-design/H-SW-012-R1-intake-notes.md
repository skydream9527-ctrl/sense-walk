# H-SW-012-R1 下游消费附页（intake notes）

- 任务：SW-012「雨林 900m 图片设计包」；作者：trae-design
- 性质：**R1 已批准交付的只读说明附页（新增文件）**。不修改、不覆盖任何已发布 R1 文件（`H-SW-012-R1.json/.md` 与 `design/01-visual-design/SW-012/r1/` 全部 53 文件保持 main 原字节），不是新 revision，不改变批准结论。
- 消费对象：MiniMax SW-015（规格解析/预检联调）、MiniMax SW-006（正式素材候选）、ZCode（配置契约与运行时消费）。
- 批准链路（均在 main）：
  - 交付 PR：[#15](https://github.com/skydream9527-ctrl/sense-walk/pull/15)，merge commit `bb05b035f1109d974790a9e576a77a539c2e43ed`
  - 独立评审：`docs/collaboration/reviews/R-SW-012-R1.json` / `.md`，结论 **approved**
  - 参数冻结决策：`docs/collaboration/decisions/D-009-freeze-rainforest-design-spec.md`
  - 任务状态：`registry.json` 中 SW-012 = **accepted**（状态以 registry 为准）

## 1. 冻结规格哈希（design_ref 必须绑定）

- 规格：`design/05-visual-design/SW-012/r1/design-spec.json`
  SHA-256 `643e77b1ba7574c9b013dce485fde2797816096181feda91c2fa7920d042c320`
- 清单：`design/05-visual-design/SW-012/r1/design-manifest.json`
  SHA-256 `8cbbdd8d374ace50e71756a410482596592d0e8c61d595207521c841399872ac`
- 业务交付 head：`cab78f6eecf9e4dbea831f4a0c6911a9d919c4fb`；交付 PR head：`c723048116fd2c36a7c19f2ab6c926f47b78beac`
- SW-006 候选素材 manifest 的 `design_ref` 必须指向本批准 handoff（`H-SW-012-R1.json`）与上述 design-spec 精确哈希；若未来出 R2 改参数，须重新独立审稿并生成新决策记录后再绑定新哈希。

## 2. 五层 canonical 参数（D-009 已冻结，不再是 proposed）

统一画布 `1080×1920`、PNG 真实 RGBA 透明、归一化坐标 0–1；光源统一**右上**（俯角 12–20°），共享脚底基线 `y=.865`。

| 顺序 | layer id | type | parallax | 解锁 at_meters | 目标 to_opacity | 淡入 fade_meters | fade 完成点 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `mist` | overlay | 0.0 | 90 | 0.55 | 20 | 110m |
| 2 | `trunks_canopy` | parallax | 0.30 | 270 | 0.85 | 25 | 295m |
| 3 | `vines_light` | parallax | 0.60 | 450 | 1.00 | 25 | 475m |
| 4 | `distant_glow` | overlay | 0.0 | 675 | 0.85 | 25 | 700m |
| 5 | `glade` | overlay | 0.0 | 855 | 0.90 | 20 | 875m |

- 总目标路程 `900m`：875m 全层完全显现，900m 保持景色完整、不切屏不闪光；停走冻结。
- 透明度运行时公式：`opacity = to_opacity · smoothstep((m − at_meters) / fade_meters)`，由 app 按米数衰减；0m 除程序旅人外无风景提前揭示。
- 六阶段检查图取值米数（fade 完成点）：`0 / 110 / 295 / 475 / 700 / 875`。
- 旅人锚点：`traveler_x=0.34`、脚底 `ground_y=0.865`；旅人/void 由程序绘制，**任何素材不得画人**。
- 触控保护区：下方 45%（`y ≥ .55`）只允许低对比贴地湿雾，不烘焙按钮/文字/图标/摇杆/米数/暂停标志。
- 拼接：五层全部 `tileable=false`，不做无缝平铺；按高度铺满、左对齐，在右侧溢出宽度内做有限横向视差，关键主体收在中央安全宽；跨屏恒可见源带 `x∈[216,864]`（1080 源坐标），旅人源锚点 x=367 在静止与最大视差两极端恒可见。

## 3. 每层源 / 参考 / 提示词路径（包根 `design/05-visual-design/SW-012/r1/`）

逐层提示词与正/负向措辞统一在 `prompts.md`（§1–§5 对应五层，§6 为阶段合成与交付提醒）。

| layer | 单层导出 | 可编辑矢量源 | 三底检查（黑/白/洋红） | 热点+四缘 2× 放大 | prompts.md |
| --- | --- | --- | --- | --- | --- |
| `mist` | `exports/rainforest_mist.png` | `source/svg/rainforest_mist.svg` | `previews/layer_checks/rainforest_mist_{black,white,magenta}.jpg` | `previews/zoom/rainforest_mist_zoom.png` | §1 |
| `trunks_canopy` | `exports/rainforest_trunks_canopy.png` | `source/svg/rainforest_trunks_canopy.svg` | `previews/layer_checks/rainforest_trunks_canopy_{black,white,magenta}.jpg` | `previews/zoom/rainforest_trunks_canopy_zoom.png` | §2 |
| `vines_light` | `exports/rainforest_vines_light.png` | `source/svg/rainforest_vines_light.svg` | `previews/layer_checks/rainforest_vines_light_{black,white,magenta}.jpg` | `previews/zoom/rainforest_vines_light_zoom.png` | §3 |
| `distant_glow` | `exports/rainforest_distant_glow.png` | `source/svg/rainforest_distant_glow.svg` | `previews/layer_checks/rainforest_distant_glow_{black,white,magenta}.jpg` | `previews/zoom/rainforest_distant_glow_zoom.png` | §4 |
| `glade` | `exports/rainforest_glade.png` | `source/svg/rainforest_glade.svg` | `previews/layer_checks/rainforest_glade_{black,white,magenta}.jpg` | `previews/zoom/rainforest_glade_zoom.png` | §5 |

- 图元/渲染/复核可编辑源：`source/sw012_model.py`（五层图元、湿绿色板、相位，固定随机种子）、`source/sw012_render.py`（SVG+PIL 双后端共享同一模型）、`source/sw012_supplement.py`（三底放大与运行时裁切复核）；master 矢量 `source/svg/rainforest_master.svg`。
- 全局风格/构图参考：`previews/rainforest_style_reference.png`（875m 终景）、`previews/composition_guide.png`（色板/构图/雨林 vs 森林差异）、`previews/layer_map.png`（五层分层标注）。
- 六阶段：`previews/stages/stage_{000m,110m,295m,475m,700m,875m}.png`。
- 三比例裁切：`previews/crops/crop_{1080x1920,1080x2400,390x844}.png`。
- 运行时裁切复核（对齐已批准 `drawImageLayer` 语义的设计期逐像素验证，非 Android 证据）：`previews/runtime_crop/runtime-crop-check.json`（all_pass=true）、`runtime_viewport_map.png`、`runtime_rest_390x844.png`、`runtime_parallax_max_390x844.png`。
- 场景身份依据：`design/01-scenes-terrain/rainforest.md`（§2 色板、§4 时间轴）；契约：`docs/collaboration/contracts/visual-design.md`、`visual-assets.md`。

## 4. 透明职责（给制作与接入的硬约束）

1. **真透明，不是黑底**：每层只画该层内容，林隙/树间/藤蔓间隙/光与辉光之外一律 alpha=0；禁止黑色或深色矩形底、白边、抠图光晕、投影硬边、棋盘/方格/同心环/重复网纹。
2. **关于 distant_glow 提示词中的“融入黑色”**：`prompts.md` §4 正向提示里“边缘完全柔化融入黑色”仅描述该层在**黑底预览图上的观感**（漏光边缘在 void 黑幕前看起来隐入黑暗）；正式输出必须是**真实 RGBA 透明、边缘 alpha 平滑归零**，不得因此生成或烘焙任何黑色矩形底。该句与同段“背景纯透明无任何填充”一致，黑/白/洋红三底上都应只见柔和光斑与水汽、看不到矩形边界（设计稿该层四边 strip4 实测 alpha 全 0）。
3. **不烘焙相位透明度**：每层按其自身完整不透明度出图（层内固有明暗对比除外），六阶段的 `to_opacity·smoothstep` 衰减由运行时按米数计算，禁止把 110/295/…/875m 各阶段的层透明度烤进单层 PNG 的 RGB 或 alpha。
4. overlay 软度基线：设计稿四边 strip4 无 alpha≥64 实色边、外缘不亮于内邻（实测边缘 max alpha：mist 12 / distant_glow 0 / glade 仅底缘 4），正式素材应达到同等软度，并保留黑/白/洋红三底与中心/四缘放大检查图。
5. 雨林身份：冷湿绿（雾青 `#2F4E44`、苔 `#60764A`、冷青湿面 `#5A7D72`、藤蔓暖绿光斑 `#C4D4A8`）；**禁止**森林暖褐 `#A89060`、干叶色、干爽土路、鸟群、右上到左下的长斜光束。
6. 入包预算与候选结构以 `prompts.md` §6 与 visual-assets 契约现行模板为准（每层 ≤400KB、五层合计 ≤2MB webp 预算；宽目标 1080，记录真实原始尺寸，不得放大低分辨率素材冒称原生 1080）。

## 5. 门禁提醒

- SW-015（MiniMax）：本包可作真实五层**只读解析样本**，须严格按上表校验 id/type/参数与空/缺/重复/错规格拒绝；设计格式 `layers[].id/type/...` 与素材 manifest 的 `layer_id/render_role` 在消费者内映射，不得要求改动已批准 spec 字节。
- SW-006（MiniMax 正式素材）：**必须 SW-012 与 SW-015 均 accepted 后**才由 Antigravity 激活；激活前零付费调用，原总 8 次尝试预算不重置。候选仍须独立完成三档 OOM/计时、真机与视觉盲检，设计批准不等于素材或 Android 验收。
- ZCode：雨林 `rainforest.json`/Shell 尚不存在；本附页参数供后续配置契约消费，接入与真机证据归 ZCode/Antigravity，本附页不构成接入完成声明。
