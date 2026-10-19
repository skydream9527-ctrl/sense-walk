# Antigravity 阶段收口队列

2026-10-18；先读STAGE-CLOSEOUT与实际发布档案。本轮已打包冻结的森林双模式main，既有accepted保留；不用重复发布同一包或重做SW016。

| 顺序 | 入口 | 退出条件 |
| --- | --- | --- |
| 安装测试包 | 发布档案/Release准确tag、commit、APK/source/hash/云端原XML | 交用户可下载、范围/已知项/步骤齐备；用户安装/实体结果到前Pending |
| 阶段问题 | ZCode SW018 / 用户FEEDBACK | SW-018已accepted合入main(d27b710)，补齐时序缺证，0源码改动；待命接收用户FEEDBACK |
| 提示补证 | 已有源码/旧hint-shown未证明显示 | ZCode实测截获H2-hint-appear与H2-hint-gone闭环时序；同局恢复不重复已由单测保障 |
| PR25 QA红灯 | 最新d71d627根路径/通配符已修，8e73b13 supplement转交CI红灯 | PR#28已合入main(e02b2e8)，测试隔离与防御校验全绿(31/31)；产出R-SW-006-R1-correction |
| 素材草案 | SW006 rework R2 | 0API草案观察收尾，等待下一阶段沿用8次授权执行真实生图R2，不入当前森林包 |
| 视觉收口 | Trae SW017 ready | SW-017已accepted合入main(0d050bc)，44项哈希全符，量化审计F7 Void黑带52px成因 |
| 后续雨林 | SW016底座accepted，SW007仍queued | 森林安装测试收口后启动SW-006 R2真实候选与真实声景，再激活SW-007组合 |

实体counter/锁屏15min/耳机来电/物理重启与真人体验仍Pending。中心registry/BOARD/review/必要发布由QA顺序维护，各作者state本人消费。没有新交付一次报告等待项，无无限轮询/自动消息/商店发布。
