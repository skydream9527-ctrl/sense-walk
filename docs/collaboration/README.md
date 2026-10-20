# SenseWalk 四角色开发入口

2026-10-20：已阅读并逐条筛选三份计划，当前执行[合并开发计划](plans/2026-10-20/README.md)。[采纳与修正](plans/2026-10-20/SOURCE-REVIEW.md) · [原文与哈希](plans/2026-10-20/inputs/index.json) · [四份完整提示词](plans/2026-10-20/PROMPTS.md)。这是任务安排，尚未自动向外部agent发消息。

## 四条稳定入口

- ZCode：`先fetch最新origin/main，在独立checkout读取并执行docs/collaboration/roles/zcode.md。`
- MiniMax Code：`先fetch最新origin/main，在独立checkout读取并执行docs/collaboration/roles/minimax.md。`
- Trae Design：`使用Design模式，先fetch最新origin/main，在独立checkout读取并执行docs/collaboration/roles/trae-design.md。`
- Antigravity：`先fetch最新origin/main，在独立checkout读取并执行docs/collaboration/roles/antigravity.md。`

## 现在做什么

| 角色 | 当前可执行 | 后续按依赖开启 |
| --- | --- | --- |
| ZCode | SW019渲染与异步加载 | SW020安全区/步长/触感→SW025构建追溯；SW023等批准设计/候选 |
| Trae Design | SW021森林连续视差与界面精修设计 | 给MiniMax和ZCode分别交准确规范，不改冻结雨林设计 |
| MiniMax Code | SW006原有零API保护/准确R2交接 | SW021 accepted后SW022森林平铺候选；本轮森林0付费 |
| Antigravity | SW024独立基准/提示缺证复核 | 持续独立审核、启用queued、分两批集成/测试发布 |

SW017/018已accepted，旧入口的ready安排已过时；不重做快照/越坎/光效/雨林底座。SW018提示截图仍有证据范围疑点，交SW024追加correction，不抹掉历史approved或虚构真机通过。PR28的QA隔离已修，PR25程序占位仍未approved/入包。

现有[森林800m双模式测试包](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-176-aaa789b)继续可安装；312项云端测试。第一批性能/操作/构建身份改进不等新美术，第二批才接平铺与UI设计。真实计步、锁屏15min和真人仍Pending。完整旧阶段范围见[STAGE-CLOSEOUT](STAGE-CLOSEOUT.md)。

## 规则与导航

registry是协调单写状态，[BOARD](BOARD.md)由render生成；实际源码/head/哈希/证据高于完成声明。产品规则以DEVELOPMENT为准。独立worktree、所有权、历史不可覆盖与交接要求见[PROTOCOL](PROTOCOL.md)。无完整本地Android环境也可通过Actions开发验证。

[ROADMAP](ROADMAP.md) · [QA队列](queues/antigravity.md) · [快照契约](contracts/session-snapshot.md) · [设计契约](contracts/visual-design.md) · [素材契约](contracts/visual-assets.md) · [交接模板](templates/HANDOFF.md) · [审核模板](templates/REVIEW.md) · [校验工具](../../tools/collaboration.py)。各作者state本人维护；此系统不自动调度、发信或唤醒agent。
