# SenseWalk 多 agent 协作

这套系统把开发安排、交付、审核与证据保存到 GitHub。无需额外服务、自动调度器或完整本地 Android 环境。

## 只需发送的四条入口提示词

- ZCode：`请读取并执行 docs/collaboration/roles/zcode.md。`
- MiniMax Code：`请读取并执行 docs/collaboration/roles/minimax.md。`
- Trae Design：`请使用 Design 模式读取并执行 docs/collaboration/roles/trae-design.md。`
- Antigravity：`请读取并执行 docs/collaboration/roles/antigravity.md。`

同一角色后续继续使用同一句。角色入口不绑定旧提交；每次都查询任务登记与最新交接。四个入口由用户交给对应工具。

## 2026-10-14进展与当前分工

本轮完整核查、238项PR云端JUnit原始证据、源码反例及阶段规划见 [进展报告](evidence/P-20261014-01/README.md)。本机当前分支可能属于别的角色或落后于main；每轮先fetch，再从最新origin/main读取登记/入口，保留本角色未交付工作同步到独立分支，不能reset覆盖别人工作。

| 角色 | 当前任务 | 结果去向 |
| --- | --- | --- |
| ZCode | [SW-001修订PR #1的R2](tasks/SW-001.md)，随后 [SW-010正式光效接入](tasks/SW-010.md) | 具体新反例修正 + 分别提交应用证据 → 独立审核 |
| MiniMax Code | [SW-014：零API素材预检准备](tasks/SW-014.md) | 脚本/fixture/账本 → 审核；雨林制作等待SW-012 |
| Trae Design | [SW-011：完成既有森林设计草稿交付](tasks/SW-011.md) | 真实提交/manifest/handoff → 独立审核，之后SW-012 |
| Antigravity | [SW-013：第二轮复验与交接收口](tasks/SW-013.md) | 完整head审查、应用验图、设计审稿、顺序登记/集成 |

SW-002候选与SW-003启动已accepted；候选进main不等于正式入包，当前森林两层光效仍程序降级。PR #1云端238项通过但未合入且有待修正反例；Trae已有本机草稿但未提交。新的SW-013/014仅已安排，本系统未向执行工具发消息。雨林按 Trae设计 → 审核 → MiniMax素材 → 验图 → ZCode接入 → Android复验推进。

## 文件导航

- [任务看板](BOARD.md)：由 registry 生成，可在 GitHub 浏览。
- [最新进展与下一轮规划](evidence/P-20261014-01/README.md)：main/PR/本机草稿分别核对。
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
