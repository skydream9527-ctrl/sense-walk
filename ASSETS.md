# ASSETS.md · 素材清单与状态（T05 · 2026-10-13）

> 规则（DEVELOPMENT.md §14）：无许可不进包；测试音、静音、合成占位不得描述为真实素材；
> AI 生成图片按生成服务条款记录，不自行标为 CC0。素材是否可播放/渲染以实际文件与验证为准。

## 一、森林视觉素材（MiniMax 生成，v1/v2/v3 三批交付）

**状态：v3 后 5 层接入；traveler 三轮未达标保持程序绘制。**
交付三批：v1/v2（2026-10-12）+ v3 按 ASSETS.md 反馈重做（2026-10-13，
见 `docs/visual-assets-handoff.md`，生成 14 次、凭据 host-managed）。
逐层验证（覆盖率 = alpha>60 像素占比；验证脚本指标留档于交付记录）：

| 层 | 当前验证 | 结论 |
| --- | --- | --- |
| void | 纯色层（程序） | — |
| tree_outline | **v3**：覆盖 48%，上密（树冠带 0.55–0.92）下空，无地面溢出 | **合格，已接入**（82 KB） |
| tree_trunks | **v2**：覆盖 73%，全高树干中带密集 | **合格，已接入**（139 KB） |
| leaf_path | **v3**：覆盖 32%，上 70% 全空 + 底部 30% 地面带 | **合格，已接入**（97 KB） |
| light_shows | **v2**：覆盖 3%，稀疏光效 | **合格，已接入**（20 KB） |
| clearing | **v2**：覆盖 19%，30–50% 高度柔光 | **合格，已接入**（43 KB） |
| traveler_idle | **v3 仍 81% 满帧**（要求角色约占画布 30% 且四周留白；连续三轮未达） | 不合格，保持程序旅人；v1/v2 原图存 raw_v1/raw_v2 |
| style_ref / connectivity_test | 参考/连通性测试，非游戏层 | 不入包 |

- **视觉包体**：5 层 webp 共约 381 KB（预算 ≤2 MB/景 ✓）。
- **渲染方式**（`ForestShell`）：带 `asset` 的层解码一次、按高度 cover 铺满、
  透明度严格来自 SensoryState（米数纯函数）、parallax 层在图片超出屏幕的
  宽度内滑动；解码失败自动回退程序渲染。**已知限制**：单图非无缝，
  视差滑满后保持静态（待可平铺版本）。
- **授权**：MiniMax 图像生成服务输出（mcode-tools connector，凭据
  host-managed），按其服务条款记录；不得标 CC0。
- **遗留**：traveler 若第四轮交付仍满帧，建议改为「程序绘制为正式方案」
  或交付方提供局部裁剪的透明 PNG。

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
