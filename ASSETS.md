# ASSETS.md · 素材清单与状态（T05 · 2026-10-13）

> 规则（DEVELOPMENT.md §14）：无许可不进包；测试音、静音、合成占位不得描述为真实素材；
> AI 生成图片按生成服务条款记录，不自行标为 CC0。素材是否可播放/渲染以实际文件与验证为准。

## 一、森林视觉素材（MiniMax 生成，v1/v2/v3 三批交付）

**状态：v3 后 5 层入包（待复验）；traveler 三轮未达标保持程序绘制。**
（2026-10-13：交付方正在修复棋盘格残留与透明蒙版；当前包内文件经棋盘格相位检测未见异常，但以修复稿复验为最终结论，暂不宣称五层全部合格。）
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

## 二、森林音频素材（2026-10-13 入包，真实素材）

**状态：已取得并接入**（来源 Wikimedia Commons，逐条授权如下）；
`forest.json` 三个音频层已用真实 `files`/`file` 替换占位，
`REQUIRE_REAL_ASSETS` 发布策略对森林放行（有测试锁定）。

| 层 | 包内文件 | 来源（Wikimedia Commons） | 授权 | 加工 |
| --- | --- | --- | --- | --- |
| footsteps | audio/forest_step_01..06.ogg（各 ~13 KB，400 ms） | [Walking through leaves (Gravity Sound)](https://commons.wikimedia.org/wiki/File:Walking_through_leaves_(Gravity_Sound).wav) + [leaves and sticks (Gravity Sound)](https://commons.wikimedia.org/wiki/File:Walking_through_leaves_and_sticks_(Gravity_Sound).wav) | **CC BY 4.0**（gravitysound.studio） | onset 检测切 6 变体（5×sticks+1×leaves），8ms 淡入淡出，−18.1 LUFS（比环境高 ~6 dB） |
| ambience | audio/forest_insects.ogg（1.22 MB，63 s） | [Waidachswald Oberschefflenz Abend 20250616 2005](https://commons.wikimedia.org/wiki/File:Waidachswald_Oberschefflenz_Abend_20250616_2005.ogg)（傍晚森林，User:Karlunun） | **CC0** | 60 s 段 + 3 s 首尾三角交叉淡化无缝循环；两遍 loudnorm −24.0 LUFS；真峰值 −6.3 dBTP |
| deep_birds | audio/forest_birds.ogg（0.87 MB，63 s） | [Dawn chorus at Glencairnie](https://commons.wikimedia.org/wiki/File:Dawn_chorus_at_Glencairnie_big_bungalow_Craigmore_DM.ogg)（黎明鸟合唱，DivyaCM） | **CC BY 4.0** | 取 40–100 s 温和段同上处理；−24.0 LUFS；真峰值 −8.5 dBTP |

- **规格符合（§14.1）**：ogg Vorbis；63 s；循环无缝；−24.0 LUFS（区间内）；
  真峰值 −4.4~−8.5 dBTP（≤−3）；总 2360 KB ≤ 3 MB。
- **已知偏差**：本机 ffmpeg 无 libvorbis，用原生 Vorbis（qscale 3）；脚步因原生
  编码器仅双声道而用同相复制（听感等同单声道）。后续可换 libvorbis 重编码。
- **致谢义务**：CC BY 4.0 两项须在发布说明署名（gravitysound.studio、DivyaCM）；
  CC0 无署名义务。关于页接入属后续打磨。
- **待真机验证**：实际听感、锁屏播放、焦点切换行为。

## 三、振动

无外部素材；`AndroidSensoryBackend.vibrationEffect` 内置波形模式表
（footstep_soft 24ms/90、footstep_sand 32ms/70、pulse_slow 波形），
遵循 vibrationEnabled 设置，暂停/终态停止。

## 四、占位与真实素材的区分（校验层）

- 配置中 `placeholder: "dev_*"` 为显式开发占位；`SceneValidator` 在
  `ALLOW_PLACEHOLDERS`（开发）下合法但列入占位清单，`REQUIRE_REAL_ASSETS`
  （发布）下报错不放行——防止把占位当素材齐备（有单测锁定）。
