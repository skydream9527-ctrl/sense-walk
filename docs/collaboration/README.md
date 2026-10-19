# SenseWalk 协作入口与阶段收口

2026-10-18：本轮先交**森林800m双模式阶段测试包**，再回收真实安装问题；雨林底座已入main，但正式候选和真实声景未齐，保持未开放。完整范围/包绑定commit/四方收尾见 [STAGE-CLOSEOUT](STAGE-CLOSEOUT.md)、[发布档案](../releases/2026-10-18-forest-beta/README.md) 与 [最新实核](evidence/P-20261018-01/README.md)。

## 四条稳定提示词

- ZCode：`先fetch最新origin/main，读取并执行docs/collaboration/roles/zcode.md，保留现有工作。`
- MiniMax Code：`先fetch最新origin/main，读取并执行docs/collaboration/roles/minimax.md，保留现有工作。`
- Trae Design：`使用Design模式，先fetch最新origin/main，读取并执行docs/collaboration/roles/trae-design.md，保留已有设计稿。`
- Antigravity：`先fetch最新origin/main，读取并执行docs/collaboration/roles/antigravity.md，保留现有工作。`

| 角色 | 本轮收尾 | 下一阶段 |
| --- | --- | --- |
| ZCode | ready SW018安装/启动/森林双模式与确认的阻断缺陷；无缺陷可0源码交付 | 雨林真实声景与SW007最终组合 |
| MiniMax | rework SW006草案/guard/交接；最新路径已修，QA fixture红交QA | 原总8次授权的正式雨林候选，不重置预算/重复索授权 |
| Trae | ready SW017先当前森林App视觉清单/参照/问题标注 | 保留已有雨林应用参照后续续做 |
| Antigravity | 现成阶段包/用户反馈、提示时序补证、独立回归与PR25 QA隔离 | 雨林候选+声音齐后独立组合验收 |

主线已accepted：可靠性/恢复、正式森林光效、地形R2、雨林设计/规格工具/底座；不用重复开发或导入旧规划包。PR25仍未合/未批准，其零API占位不进入本阶段包。所有阶段设备/真人项如实Pending，阶段包可下载不等于最终MVP完成。

## 事实与文件系统

registry是协调单写状态，BOARD由render生成，任务/角色入口/阶段范围说明安排；源码/commit/证据高于完成声明。独立worktree与单写角色所有权见 [PROTOCOL](PROTOCOL.md)，旧handoff/review/evidence/decision只追加。各作者state本人消费，不由协调者代写；用户转发文件提示词不等于工具已自动收到消息。

[看板](BOARD.md) · [整体路线](ROADMAP.md) · [QA队列](queues/antigravity.md) · [快照契约](contracts/session-snapshot.md) · [设计契约](contracts/visual-design.md) · [素材契约](contracts/visual-assets.md) · [交接模板](templates/HANDOFF.md) · [审核模板](templates/REVIEW.md) · [校验工具](../../tools/collaboration.py)。历史阶段报告保持当时事实，旧网络发布交接文件无需重跑。
