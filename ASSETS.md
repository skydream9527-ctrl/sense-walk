# ASSETS.md · 素材清单与状态（T05 · 2026-10-13）

> 规则（DEVELOPMENT.md §14）：无许可不进包；测试音、静音、合成占位不得描述为真实素材；
> AI 生成图片按生成服务条款记录，不自行标为 CC0。素材是否可播放/渲染以实际文件与验证为准。

## 一、森林视觉素材（MiniMax 生成，v1/v2/v3/v4 四批交付）

**状态：v4 五层复验合格、已替换入包（260 KB）；traveler 采纳程序绘制为正式方案。**
（历史：v3 入包时标记「待复验」；2026-10-13 v4 修复轮交付 alpha 内容约束版——trunks 底部 y>950 alpha ≤ 主体 max×35%、clearing 限 y=200–650 中带 + 40px 羽化——ZCode 按 §14 复验标准程序化检验全部通过后替换，见下方复验记录。）
交付批次：v1/v2（2026-10-12）+ v3 按 ASSETS.md 反馈重做 + v4 内容修正轮（2026-10-13，
见 `docs/visual-assets-handoff.md`，生成 14 次、v4 纯后处理 0 次调用、凭据 host-managed）。

| 层 | 当前入包（v4） | 结论 |
| --- | --- | --- |
| void | 纯色层（程序） | — |
| tree_outline | 覆盖 49%，上密下空，无地面溢出 | **复验合格**（66 KB） |
| tree_trunks | 覆盖 80%，全高树干；底部 alpha 已按 35% 上限约束（实测 89≤89） | **复验合格**（85 KB） |
| leaf_path | 覆盖 32%，上 70% 全空 + 底部地面带 | **复验合格**（63 KB） |
| light_shows | 覆盖 3.4%，稀疏光柱 | **复验合格**（17 KB） |
| clearing | 覆盖 17.7%，带外 alpha=0 实测，中带柔光 | **复验合格**（30 KB） |
| traveler_idle | v1–v3 均 81% 满帧不合格 | **程序绘制为正式方案**（`ForestShell.drawTraveler`；合格静态角色也不冒充动画） |
| style_ref / connectivity_test | 参考/连通性测试，非游戏层 | 不入包 |

**v4 复验记录（ZCode 程序化检验，2026-10-13）**：
- 棋盘格：五层同/跨相位 8px 差均 <3.2 或同相≥跨相；合成图梯度符号交替率 x 56% / y 32%（棋盘特征需 >90%）；频谱峰值在整幅纵向渐变（k=(1,0)）而非 8px 频率——**无棋盘格残留**。
- 白边/矩形底：五层四边 alpha 均值全 0.00；785m 全层合成于 #060806 后边缘亮度 7.2（≈void 6.6）、边缘 >30 亮度像素 0——**无白边、无矩形底**。
- 层内容重复：两两亮度 Pearson r ∈ [−0.22, +0.30]——**无重复层**。
- 合成预览：`.local-verify/t5final/v4-composite-785m.png`（本地验证件）；交付方另有 6 阶段合成（`candidates/v4/stage_compose/`）。
- 待复核（不阻塞）：真机/真人最终视觉走查归入 M1 待验证清单。

- **视觉包体**：5 层 webp 共 260 KB（预算 ≤2 MB/景 ✓，较 v3 381 KB 再省 121 KB）。
- **渲染方式**（`ForestShell`）：带 `asset` 的层解码一次、按高度 cover 铺满、
  透明度严格来自 SensoryState（米数纯函数）、parallax 层在图片超出屏幕的
  宽度内滑动；解码失败自动回退程序渲染。**已知限制**：单图非无缝，
  视差滑满后保持静态；v4 另附 tileable 版候选未启用（当前 cover 模式 overflow≈0，见交付记录 §7.2）。
- **授权**：MiniMax 图像生成服务输出（mcode-tools connector，凭据
  host-managed），按其服务条款记录；不得标 CC0。

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
