# SW-021 r1 · 森林连续视差与界面精修设计

状态：`design_candidate`（Trae 只声明候选；Antigravity 独立批准后才是 approved design，SW-022 才开工）。
基线：`4f57659`（origin/main，2026-10-20 fetch），分支 `codex/trae-design/SW-021-forest-polish`，独立 worktree。
零新增付费 API：全部设计由本地 Python(PIL) + 手写 SVG 生成，所有预览标注「设计模拟 · 非 App 截图」。

## 1. 要解决的问题

SW-017 已量化确认（`SW-017/r1/integration-reference.json` P1/P2）：

- 1080×2400 下旧 cover 视差约 144m（叶层约 72m）即钳满，之后画面横移停止；钳满后右缘露出源图 30 个硬透明列，265/425/630m 有 **52px 黑带**。
- 旧素材是整幅画：`tree_outline.webp` 是满幅山水、`tree_trunks.webp` 烘焙了奶白终景圆盘，结构上无法平铺、也无法承担渐进揭示。
- UI 侧：禁用场景/模式只有一句「暂未开放」、themeColor 硬编码、放弃确认对比与危险语义弱、长按只有线性进度、结果落幕缺 ≥3s 退暗规范、关于页没有真实音频署名。

## 2. 设计方案概述

1. 五层 ID、80/240/400/600/760m、opacity .60/.70/.80/.65/.90、fadeMeters 20/25/25/30/25、parallax .3/.3/.6 全部冻结不变。
2. 仅 `tree_outline`/`tree_trunks`/`leaf_path` 重新设计为 **1080×1920 原生、repeat-x 数学无缝 tile**；`light_shows`/`clearing` 逐字节复用已批准 webp。
3. 接缝用 **3W 折叠法**：3240 宽画布上画全部 wrap 图元，三段 over 折叠回中央 tile；冠线 union mask 整体着色消除泡泡边界；树干改为屏外伸入、错落微锥、含一棵跨缝巨树；地面上缘用整周期正弦。缝差审计：trunks 0.025/max1、leaf_path 0.003/max3、outline 0.218（与内部自然差同量级）。
4. repeat-x 后任意米数、三个比例下周期宽度恒 ≥ 屏宽，黑带恒为 0（对拍见 `previews/composite/forest_continuous_compare_1080x2400.png`，数值见 `previews/sw021_preview_checks.json`）。
5. 旅人保持 x=.34/y=.865 程序绘制，给 7% 与 9% 屏高两方案比较，**推荐 9%**（小屏/暗背景辨识度更好），由 QA 真机定稿。
6. UI 精修 9 张模拟：首页单列（含小屏双列否决对比、大字号 ×1.5）、模式卡禁用原因常驻、暗色底部放弃确认、长按 1.5s 环形反馈、结果 ≥3s 退暗 + 用时折叠、关于页真实音频署名、字阶 token 表。

## 3. 文件结构

```text
r1/
  design-spec.json                 # 机器可读规范（canvas/tile/色板/相位/UI token/限制）
  prompts.md                       # MiniMax 三层逐层提示词 + 接缝条件 + 零 API 路线
  README.md                        # 本文件
  source/
    sw021_tile_model.py            # 三层 tile 可编辑模型（PIL/SVG 双后端，3W 折叠）
    sw021_previews.py              # 三底/拼接/接缝/六阶段×三比例合成/旧 cover 对拍
    sw021_ui_mocks.py              # 9 张 UI 精修模拟
    svg/forest_{tree_outline,tree_trunks,leaf_path}_tile.svg
  previews/
    sw021_preview_checks.json      # 几何/缝差/黑带数值
    tiles/                         # tile PNG + checks/(三底) + repeat/(三连拼) + seam/探针
    composite/                     # 三比例六阶段矩阵 + 新旧对拍
    traveler/traveler_size_compare.png
    ui/ui_*.png                    # 9 张
```

## 4. MiniMax 怎么消费

- 读 `prompts.md`（逐层主体/禁画/色板/接缝条件/负提示）与 `design-spec.json`，以 `previews/tiles/*`、`source/svg/*` 为结构参考。
- 只做三层可平铺正式候选（≤400KB/层）；light_shows/clearing 不重画；雨林不碰；不得借用雨林 8 次付费授权；零 API 路线见 prompts §4。
- 候选目录、候选 manifest（含 `design_ref` + 批准后的 spec sha256）按 visual-assets 契约自行维护；Trae 不代写候选。设计未独立批准前候选风险自担。

## 5. ZCode 怎么消费（SW-022，批准后）

- 渲染：给 `ForestShell` 增加 repeat-x 路径（建议 BitmapShader REPEAT 或双份 drawImage），规则与 K=6px/m 见 design-spec `tile_rendering_contract_for_zcode`；垂直按高铺满、底对齐；alpha 仍走 PhaseScheduler。**当前壳不支持平铺，不要直接把 tile 塞进 cover 路径。**
- 三层新素材入包后替换对应 webp；light_shows/clearing 不动；forest.json 的 ID/米数/opacity/parallax 不需要改。
- 旅人高度加 7%/9% 配置项，默认 9%，等 QA 真机目检。
- UI：首页单列 + 卡内不可用原因 + themeColor tint（随场景 palette，不全局硬套 forest）；模式卡禁用原因常驻 + 可读禁用按钮；放弃底部 sheet（危险色 #C94A3E 唯一）；长按 1.5s 环形（只表达确认，不产距离，reduceMotion 静态替代）；结果先冻结输入再 ≥3s 缓出退暗、用时/步幅默认折叠；关于页音频署名（入库前与实际音频 manifest 核对作者/许可）。

## 6. 方案比较与结论

- 旅人尺寸：7% 在大屏清楚、小屏融入暗部；9% 三档密度下都可辨且不侵操作区 → 推荐 9%，不作为 8–12% 硬标准。
- 首页布局：双列在 390×844 截断米数/分钟、无处放不可用原因、触控高度不足 → 单列；大字号下列高自适应。
- 退暗：采用 DEVELOPMENT §11.2 的 3s，不采用输入计划中的 1–2s。

## 7. 限制与待验证

- 全部为设计模拟，非 App 截图/真机证据；K=6px/m 的物理映射、9% 旅人、退暗观感待 SW-022 设备验证。
- tree_outline 存在个别抗锯齿像素 max 差 255（均值与自然差同量级、目检无缝）；正式素材以三底+三连拼+多偏移目检为准。
- 署名三条依据现有入包音频记录，真实元数据以入库素材 manifest 为准。
- 本 r1 不改 `app/`、forest.json、入包 webp，不改 SW-011/012/017 与 D-009 任何已发布字节。
