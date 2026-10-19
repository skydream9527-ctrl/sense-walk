# SW-016 真实雨林声景准备清单（状态：Pending——未获取，不冒称）

本轮 0 新增付费服务；未下载/处理任何音频文件。以下为 SW-007 接入所需的
完整准备规格与候选来源方向（获取/处理/听辨须在 SW-007 或补充轮真实执行）。

## 需求清单（按 900m 相位）

| 用途 | 相位 | 规格 | 候选来源方向（须逐一核许可） |
| --- | --- | --- | --- |
| 湿叶/软泥步伐 | steps@90m | 6 变体 one-shot，0.4-0.8s，峰值 ≤-12dBFS，mono | Freesound CC0（搜索 wet leaves footsteps / mud steps）；Wikimedia Commons CC0/CC-BY 现场录音 |
| 环境底噪 loop | ambience@270m | 30-60s 无缝 loop，滴水+阔叶沙沙，克制（目标音量 0.30） | Freesound CC0 rainforest ambience / jungle drip；注意 CC-BY 需署名列 ASSETS |
| 深处虫鸣 loop | deep@675m | 30-60s loop，低频虫鸣+远处水声（目标 0.20） | 同上；与 ambience 层频段分离避免掩蔽 |
| 振动模式 | haptic@450m | footstep_soft 每 2 步（复用既有触觉模式，无音频） | 已有 |

## 处理规格（获取后执行）

- 采样率 44.1kHz / OGG Vorbis ~q5；响度归一 -18 LUFS（ambience）/-16 LUFS（步伐）
- 处理命令逐条记录（ffmpeg filtergraph 原样入 ASSETS：trim/loop-point/crossfade/loudnorm）
- 无缝 loop：首尾 2s 交叉淡化，听辨验证无接缝爆音
- 每 file 记录：来源 URL、作者、许可全文链接、下载字节 sha256、处理后字节 sha256、时长、声道、峰值

## 诚实声明

- 本轮**未获取任何音频**——无网络下载授权下的素材获取/许可核对/听辨无法在本轮诚实完成；
- 测试配置中的三层音频引用（footsteps_placeholder 等）指向**森林既有文件**，
  仅保证 loader/validator/相位链路可测，**不是雨林声景**，SW-007 必须替换；
- 不以重命名森林声景、程序合成音或生图 API 冒充现场录音；程序音如使用须如实
  标 procedural 并独立听辨验收（本轮未做）。

## 阻塞关系

正式声景缺失**阻塞最终 SW-007 验收**（底座 accepted ≠ 雨林完成）。
