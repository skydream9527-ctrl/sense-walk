# SenseWalk 多 agent 协作

这套系统把开发安排、交付、审核与证据保存到 GitHub。无需额外服务、自动调度器或完整本地 Android 环境。

## 只需发送的四条入口提示词

- ZCode：`请先 fetch 最新 origin/main，从该版本读取并执行 docs/collaboration/roles/zcode.md；保留现有工作。`
- MiniMax Code：`请先 fetch 最新 origin/main，从该版本读取并执行 docs/collaboration/roles/minimax.md；保留现有工作。`
- Trae Design：`请使用 Design 模式，先 fetch 最新 origin/main，从该版本读取并执行 docs/collaboration/roles/trae-design.md；保留已有设计草稿。`
- Antigravity：`请先 fetch 最新 origin/main，从该版本读取并执行 docs/collaboration/roles/antigravity.md；保留现有工作。`

同一角色后续继续使用同一句。角色入口不绑定旧提交；每次都查询任务登记与最新交接。四个入口由用户交给对应工具。

## 2026-10-15进展与当前分工

main基准6104e3d：可靠性SW-001、快照SW-004、53文件森林设计SW-011、预检R3/SW-014均已独立验收合入。最新build-109含可靠性/恢复，云端274项通过；森林正式接图SW-010仅approved，PR #3仍有作者state冲突，尚未入main/测试包。详见 [本轮核查](evidence/P-20261015-01/README.md)。

| 角色 | 本轮任务 | 交付与门禁 |
| --- | --- | --- |
| ZCode | 先同步已approved的SW-010/PR #3，再独立实现ready的[SW-005地形](tasks/SW-005.md) | 作者合并自己的state信息；QA复核接图后集成。地形/站稳/轻跳不刷距且保持快照恢复 |
| Trae Design | ready的[SW-012雨林900m设计](tasks/SW-012.md) | 使用canonical id/type规格、fade完成点/三比例/源/逐层提示词，交设计审核 |
| MiniMax Code | ready的[SW-015真实设计与预检联调](tasks/SW-015.md)，0 API | 真实Trae id/type解析、空集合/空候选拒绝、保留原保护与历史版本，交独立审核 |
| Antigravity | [常驻队列](queues/antigravity.md)：SW-010集成，随到审SW-005/SW-012/SW-015 | 精确review/merge/CI与组合测试包；SW-012/SW-015均accepted才激活SW-006 |

本轮实测发现R3只识别layer_id，真实已批准规格id被读成空集合并放行空候选，所以新增零API联调任务与付费制作前置。SW-014既有批准保留，不重做R3旧fixture范围。森林设计已共享，不能继续按旧聊天重交草稿。生产者state由本人消费accepted后更新；registry为准。真机/真人仍Pending，工具启动/消息由用户分别执行。

## 文件导航

- [任务看板](BOARD.md)：由 registry 生成，可在 GitHub 浏览。
- [最新进展与下一轮规划](evidence/P-20261015-01/README.md)：main/PR/本机草稿分别核对。
- [常驻验收队列](queues/antigravity.md)：精确待验提交；协调轮完成后继续消费交付。
- [上一轮交付核查](evidence/P-20261014-03/README.md)、[早期交付核查](evidence/P-20261014-02/README.md) 与 [初版源码核查](evidence/P-20261014-01/README.md)：历史记录保持当时head/证据。
- [协作协议](PROTOCOL.md)：隔离、所有权、领取、交接、退回与集成。
- [整体路线](ROADMAP.md)：T07 拆成快照、地形、雨林三个可验收步骤。
- [基线核查](evidence/B-20261013-01/README.md)：8056e11、217 项云端测试、素材与 T06 风险。
- [初始独立审阅](reviews/R-BASE-001.md)：已识别的问题和证据类型。
- [会话快照契约](contracts/session-snapshot.md)、[图片设计规范](contracts/visual-design.md)、[视觉素材交付契约](contracts/visual-assets.md)。
- [交付模板](templates/HANDOFF.md)、[审核模板](templates/REVIEW.md)、[决策模板](templates/DECISION.md)。
- [状态与交付校验工具](../../tools/collaboration.py)：仅 Python 标准库，CI 也执行。

## 文件系统

```text
docs/collaboration/
  roles/              # 四个稳定入口，完整执行提示词
  queues/             # 常驻审核队列，远端交付定位/待审内容
  tasks/              # 按任务 ID 保存范围、前置、验收和完整工作要求
  registry.json       # 任务状态/依赖/当前审核；Antigravity 单写
  BOARD.md            # 生成的人类可读看板
  state/              # 每个生产者自己的领取/状态文件
  contracts/          # 跨角色接口；版本变更留决策记录
  handoffs/<agent>/   # 每轮 JSON + Markdown，不覆盖历史轮次
  reviews/            # 独立审核 JSON + Markdown；与交付分开
  decisions/          # 规则/接口/范围变化的依据
  evidence/<id>/      # 可长期保留的最小证据，不依赖本机隐藏目录
  templates/          # 报告结构，不能填充虚构通过项
```

协作登记管理“谁下一步做什么”；`DEVELOPMENT.md` 管产品规则；`ASSETS.md` 管已入包素材；候选 manifest 管候选素材。四者不能互相代替。
