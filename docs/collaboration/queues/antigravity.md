# Antigravity 阶段收口队列

2026-10-18；先读STAGE-CLOSEOUT与实际发布档案。本轮已打包冻结的森林双模式main，既有accepted保留；不用重复发布同一包或重做SW016。

| 顺序 | 入口 | 退出条件 |
| --- | --- | --- |
| 安装测试包 | 发布档案/Release准确tag、commit、APK/source/hash/云端原XML | 交用户可下载、范围/已知项/步骤齐备；用户安装/实体结果到前Pending |
| 阶段问题 | ZCode SW018 / 用户FEEDBACK | 确认复现→最小patch→独立复验/新tag；无缺陷不强造源码改动/空测试 |
| 提示补证 | 已有源码/旧hint-shown未证明显示 | 同步App出现→约3s消失与同局恢复不重复；精确APK/步骤，没条件Pending |
| PR25 QA红灯 | 最新d71d627根路径/通配符已修，8e73b13 supplement转交CI红灯 | QA已完成tools隔离与缺manifest防御，31/31全绿；不skip/禁严格批准hash，不代改作者候选；产出R-SW-006-R1-correction闭环 |
| 素材草案 | SW006 rework R2 | 0API稿/guard/交接准确，不自批生产；正式图下一阶段原总8尝试，不入当前森林包 |
| 视觉收口 | Trae SW017 ready | 当前森林App/作者截图来源/设计模拟区分、必要验图清单与有依据问题；保留已有雨林稿 |
| 后续雨林 | SW016底座accepted，SW007仍queued | 正式候选与真实声景齐后再组合，不以占位/底座替完成 |

实体counter/锁屏15min/耳机来电/物理重启与真人体验仍Pending。中心registry/BOARD/review/必要发布由QA顺序维护，各作者state本人消费。没有新交付一次报告等待项，无无限轮询/自动消息/商店发布。
