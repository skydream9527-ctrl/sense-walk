# SenseWalk 多 agent 协作

这套系统把开发安排、交付、审核与证据保存到 GitHub。无需额外服务、自动调度器或完整本地 Android 环境。

## 只需发送的四条入口提示词

- ZCode：`请先 fetch 最新 origin/main，从该版本读取并执行 docs/collaboration/roles/zcode.md；保留现有工作。`
- MiniMax Code：`请先 fetch 最新 origin/main，从该版本读取并执行 docs/collaboration/roles/minimax.md；保留现有工作。`
- Trae Design：`请使用 Design 模式，先 fetch 最新 origin/main，从该版本读取并执行 docs/collaboration/roles/trae-design.md；保留已有设计草稿。`
- Antigravity：`请先 fetch 最新 origin/main，从该版本读取并执行 docs/collaboration/roles/antigravity.md；保留现有工作。`

同一角色后续继续使用同一句。角色入口不绑定旧提交；每次都查询任务登记与最新交接。四个入口由用户交给对应工具。

## 2026-10-14进展与当前分工

第四轮核查、最新PR合并checkout原始JUnit、MiniMax R2五个新反例与分工见 [最新进展报告](evidence/P-20261014-03/README.md)。本机当前分支可能属于别的角色或落后于main；每轮先fetch，再从最新origin/main读取登记/入口，保留本角色未交付工作同步到独立分支，不能reset覆盖别人工作。

| 角色 | 当前任务 | 结果去向 |
| --- | --- | --- |
| ZCode | [SW-001 R2](tasks/SW-001.md)/[SW-010 PR #3](tasks/SW-010.md)已同步解冲突并补证据，不重复已做动作 | 响应独立QA；SW-001 accepted后SW-004快照 |
| MiniMax Code | [SW-014 R3零API修订](tasks/SW-014.md)，R2已推送但有新误放行 | 修R2-01～05/spec读取/实际预算与累计账本，交真实PR/handoff |
| Trae Design | [SW-011：发布既有43文件森林设计草稿](tasks/SW-011.md) | 推送真实源/manifest/handoff → 独立审核，之后SW-012 |
| Antigravity | [常驻验收队列](queues/antigravity.md)，优先SW-001 R2独立结论 | 通过即顺序集成/激活SW-004，再森林接图/预检最新revision/收到的设计；交组合包 |

SW-002候选、SW-003/SW-013协调已accepted；两个工作PR现均MERGEABLE/CLEAN，最新PR合并checkout分别249/217项通过，但仍未独立验收/合入main。MiniMax R2根定位/解码已修、13原fixture结果吻合，新五个反例仍需R3；Trae仍无共享交付。近期目标是可靠性/森林独立验收→合入→组合CI/新测试包，以及共享设计/合格预检工具。main两层光效仍程序降级，旧build-41不含工作PR；真机/真人仍Pending。observed_delivery只定位远端交付，本系统未向执行工具发消息。

## 文件导航

- [任务看板](BOARD.md)：由 registry 生成，可在 GitHub 浏览。
- [最新进展与下一轮规划](evidence/P-20261014-03/README.md)：main/PR/本机草稿分别核对。
- [常驻验收队列](queues/antigravity.md)：精确待验提交；协调轮完成后继续消费交付。
- [上一轮交付核查](evidence/P-20261014-02/README.md) 与 [初版源码核查](evidence/P-20261014-01/README.md)：保留各轮当时证据与修订依据。
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
