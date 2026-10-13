# ASSETS.md · 素材清单与状态（T05 · 2026-10-13）

> 规则（DEVELOPMENT.md §14）：无许可不进包；测试音、静音、合成占位不得描述为真实素材；
> AI 生成图片按生成服务条款记录，不自行标为 CC0。素材是否可播放/渲染以实际文件与验证为准。

## 一、森林视觉素材（MiniMax 生成，2026-10-12/13 两批交付）

**状态：部分合格，已接入 3 层；其余保持程序剪影降级。**
交付分两批（19:4x 与 20:00），第二批修复了首批的主要问题。逐层验证（指标见
`design/assets/forest/previews/` 与本轮记录；覆盖率 = alpha>60 像素占比）：

| 层 | 第二批验证 | 结论 |
| --- | --- | --- |
| tree_trunks | 覆盖 73%，中带 0.85–0.92 密集，全高树干合理 | **合格，已接入**（`asset: visual/forest_tree_trunks.webp`，139 KB） |
| light_shows | 覆盖 3%（首批 58% 的问题已修复），稀疏光效 | **合格，已接入**（20 KB） |
| clearing | 覆盖 19%，集中于 30–50% 高度带的柔光 | **合格，已接入**（43 KB） |
| tree_outline | 顶部透明合格，但可见内容仅 ~2%（远山树线过稀） | 不合格（内容过稀），保持程序剪影，待重生成 |
| leaf_path | 覆盖 85%，顶部 92% 可见（近景地面层不应占满画面上部） | 不合格（内容溢出），保持程序近景，待重生成 |
| traveler_idle | 覆盖 80%——角色应只占画布小部分，非全幅 | 不合格（尺寸/构图），保持程序旅人，待重生成 |
| style_ref / connectivity_test | 参考/连通性测试，非游戏层 | 不入包 |

- **渲染方式**（`ForestShell`）：带 `asset` 的层解码一次、按高度 cover 铺满、
  透明度严格来自 SensoryState、parallax 层在图片超出屏幕的宽度内滑动；
  解码失败自动回退程序渲染。**已知限制**：单图非无缝，视差滑满后保持静态
  （待素材方提供可水平平铺版本后完善，见下）。
- **通用问题（遗留）**：JPEG 无原生透明，后处理以 #060806 软抠图模拟 alpha
  （`design/assets/forest/scripts/forest_asset_postprocess.py`）；左右 4% 边带被裁成
  全透明，水平拼接时会出现周期性空隙——**无缝拼接声明不成立**，需要交付方按
  提示词重生成可平铺版本或提供拼接方案。
- **授权**：MiniMax 图像生成服务输出，按其服务条款记录；不得标 CC0。
- **对交付方的重生成要求**：顶部/底部留白区必须为纯 #060806；overlay 层稀疏内容；
  角色层只含居中小幅角色；parallax 层左右边缘内容连续可平铺。

## 二、森林音频素材

**状态：未取得，待补。** `app/src/main/assets/audio/` 仅有 .gitkeep。
场景配置的音频层全部为显式开发占位（`placeholder: "dev_tone*"`），
`SceneValidator` 的 `REQUIRE_REAL_ASSETS` 策略不放行（有测试锁定）。

| 需求 | 规格（§14.1） | 来源要求 |
| --- | --- | --- |
| 环境 loop（insects / birds） | ogg Vorbis 96 kbps · 48 kHz · 立体声 · 60–120 s · 首尾交叉淡化无缝 · −26~−23 LUFS · 真峰值 ≤ −3 dBTP | 自采或可验证 CC0；逐条记录来源链接与授权 |
| 脚步 one-shot ×4–6（落叶土路） | ogg · 单声道 · ≤400 ms · 比环境层高 3–6 dB | 同上 |

- **播放机制已就绪**（T05）：`AndroidSensoryBackend`（SoundPool 脚步变体 +
  MediaPlayer 环境 loop + Vibrator 波形）会跳过占位层并在日志说明，不伪造声音；
  素材入库后无需改代码。
- **预算**：每场景音频 ≤3 MB + 视觉 ≤2 MB；当前 APK 约 16.8 MB。

## 三、振动

无外部素材；`AndroidSensoryBackend.vibrationEffect` 内置波形模式表
（footstep_soft 24ms/90、footstep_sand 32ms/70、pulse_slow 波形），
遵循 vibrationEnabled 设置，暂停/终态停止。

## 四、占位与真实素材的区分（校验层）

- 配置中 `placeholder: "dev_*"` 为显式开发占位；`SceneValidator` 在
  `ALLOW_PLACEHOLDERS`（开发）下合法但列入占位清单，`REQUIRE_REAL_ASSETS`
  （发布）下报错不放行——防止把占位当素材齐备（有单测锁定）。
