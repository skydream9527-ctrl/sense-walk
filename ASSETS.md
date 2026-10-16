# ASSETS.md · 素材清单与状态（T05 · 2026-10-13）

> 规则（DEVELOPMENT.md §14）：无许可不进包；测试音、静音、合成占位不得描述为真实素材；
> AI 生成图片按生成服务条款记录，不自行标为 CC0。素材是否可播放/渲染以实际文件与验证为准。

## 一、森林视觉素材（MiniMax 生成，v1/v2/v3/v4 四批交付）

**状态（2026-10-14，SW-010）：light_shows/clearing 两层改用 SW-002 R1 批准候选逐字节入包（哈希一致，无棋盘格/AI生图瑕疵）；outline/trunks/leaf_path 三层真实图继续入包。但两层候选素材 alpha 偏低，真实游玩画面可见度弱，详见下方「SW-010 入包记录」，不冒称视觉验收满分。**

**撤回经过（2026-10-13，T06 前定点修复）**：a235bf1 曾依据程序化统计（8px 相位差、块交替率、四边 alpha）判定 v4 五层合格。用户以实际图像复核指出 785m 合成图**中央仍有明显棋盘格**——统计阈值未能替代图像检查（此前的检验只针对 8px 周期与符号交替，漏掉了 **32px 周期对角纹理**）。补充频域检验：合成图中心 32px 对角分量能量 26.65%；逐层隔离后 **light_shows 55.10%**（16px 谐波 11.3%，v2 起沿用未重制）、移除后 785m（新增 clearing）仍 21.78%；而仅含 outline/trunks/leaf_path 的 265–630m 阶段为 0.46%（干净）。据此两个 overlay 层判定为问题层，从 forest.json 移除 asset 走程序降级（`drawLightShows`/`drawClearingGlow`），**不以降透明度隐藏问题**；等 MiniMax 新修复稿后按本节标准重新验收候选与入包文件并重生成六阶段合成。角色维持程序绘制正式方案。

| 层 | 当前入包 | 结论 |
| --- | --- | --- |
| void | 纯色层（程序） | — |
| tree_outline | v4 真实图，覆盖 49% | **入包**（对角能量 ≤5%，内容带干净） |
| tree_trunks | v4 真实图，覆盖 80%（32px 轴向条纹为树干自然结构，非棋盘） | **入包** |
| leaf_path | v4 真实图，覆盖 32% | **入包** |
| light_shows | SW-002 R1 候选真实图入包（哈希一致，三束斜光+2鸟剪影，程序算法生成非AI生图） | **入包**（**但 alpha 峰值仅 54.9%，可见度弱，见下方记录**） |
| clearing | SW-002 R1 候选真实图入包（哈希一致，径向渐变光斑，程序算法生成非AI生图） | **入包**（**但 alpha 峰值仅 29.8%，可见度弱，见下方记录**） |
| traveler_idle | v1–v3 均 81% 满帧不合格 | **程序绘制为正式方案**（合格静态角色也不冒充动画） |
| style_ref / connectivity_test | 参考/连通性测试，非游戏层 | 不入包 |

- **六阶段合成（T06 修复稿，历史记录）**：`.local-verify/t6fix/stages/stage_{000,100,265,425,630,785}m.png`——265m 起各阶段中心对角能量均 0.46%（干净），100m 为 5.8%（淡入低反差噪声），0m 纯黑幕。
- **复验方法备忘**：① 实际图像目检（不可只用统计阈值）；② 8px 与 **32px** 双周期相位/频域检验；③ 逐层内容带中心而非图像几何中心（clearing 带外曾致漏检）；④ 候选与入包文件逐字节一致；⑤ 真机/模拟器六阶段合成重生成。

### SW-010 入包记录（2026-10-14）

将 SW-002 R1 批准候选逐字节复制入 `app/src/main/assets/visual/`，forest.json 的
`light_shows`/`clearing` 两个 overlay 层补回 `asset` 字段（相位 atMeters/toOpacity/
fadeMeters 等产品参数未改动）。模拟器真实展示（emulator-5554，冒烟注入驱动真实
RealWalkEngine/RealWalkController/ForestShell 渲染链，非截图伪造）六阶段
0/100/265/425/630/785m 全程无棋盘格、无接缝暴露、停止后画面逐像素冻结
（见 evidence/H-SW-010-R1/stages/freeze-a.png 与 freeze-b.png，画面主体哈希一致，
仅状态栏时钟像素有差异）。

**哈希核对**（候选 manifest ↔ 正式入包文件，sha256 完全一致）：
- `forest_clearing.webp`：`1dcda4f7b61b038f4f9fddfa3351dcfd5d0679167388148f47b841153169ca33`
- `forest_light_shows.webp`：`1973a1f594f1edd0a801e57251192c7629f7f802e621a2a95874328e257466f0`

**但发现视觉强度问题**（evidence/H-SW-010-R1/alpha-visibility-analysis.txt 完整数据）：
两张候选素材自身 alpha 峰值偏低（light_shows 54.9%、clearing 29.8%，均为候选设计
阶段的保守取值，非本轮引入），叠加 forest.json 相位目标 toOpacity（0.65/0.9）后，
合成透明度峰值约 35.7%/26.8%。实机对比 630m（light_shows 早已满淡入）与 785m
（clearing 刚满淡入）两张截图，画面主体区域逐像素差异 mean=1.4%、max=12.5%——
连续游玩时该变化并不显著，玩家大概率察觉不到两层新内容的揭示。

这不是棋盘格/AI生图瑕疵类问题，是候选素材本身视觉强度是否达标的产品判断，
**本轮不自行判定合格或打回**，留给 Antigravity 独立复验裁定（可能结论：接受当前
强度 / 要求 MiniMax 提高 alpha 后出新候选 / 调整 forest.json 的 toOpacity 作为临时
缓解，但后者属产品参数变更需先登记契约差异，不在本次任务范围内擅自改动）。
- **视觉包体**：真实图 3 层 webp 共 214 KB（预算 ≤2 MB/景 ✓）。
- **渲染方式**（`ForestShell`）：带 `asset` 的层解码一次、按高度 cover 铺满、
  透明度严格来自 SensoryState（米数纯函数）、parallax 层在图片超出屏幕的
  宽度内滑动；无 `asset` 或解码失败自动回退程序渲染。**已知限制**：单图非无缝，
  视差滑满后保持静态。
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
