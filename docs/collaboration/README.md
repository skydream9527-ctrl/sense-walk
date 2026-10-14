# SenseWalk 多 agent 协作

这套系统把开发安排、交付、审核与证据保存到 GitHub。无需额外服务、自动调度器或完整本地 Android 环境。

## 只需发送的四条入口提示词

- ZCode：`请读取并执行 docs/collaboration/roles/zcode.md。`
- MiniMax Code：`请读取并执行 docs/collaboration/roles/minimax.md。`
- Trae Design：`请使用 Design 模式读取并执行 docs/collaboration/roles/trae-design.md。`
- Antigravity：`请读取并执行 docs/collaboration/roles/antigravity.md。`

同一角色后续继续使用同一句。角色入口不绑定旧提交；每次都查询任务登记与最新交接。四个入口由用户交给对应工具。

## 现在可以并行做什么

| 角色 | 当前任务 | 结果去向 |
| --- | --- | --- |
| ZCode | [SW-001：T06 可靠性补强](tasks/SW-001.md) | 功能 PR → Antigravity 审核 |
| MiniMax Code | [SW-002：森林光效候选收尾](tasks/SW-002.md) | 带哈希候选 → Antigravity 验收 → ZCode 入包 |
| Trae Design | [SW-011：森林图片设计与通用规范](tasks/SW-011.md) | 设计稿/提示词 → 独立审核 → MiniMax 制作 |
| Antigravity | [SW-003：独立基线验收与协作集成](tasks/SW-003.md) | 审核、证据、任务登记与测试发布 |

开始前必须核对真实 main；四项是**已安排、尚未执行**的任务，不把历史成果伪装成新 agent 交付。当前森林机械修图继续原范围；雨林等新图按 Trae 设计 → Antigravity 审核 → MiniMax 素材 → 再审核 → ZCode 接入 → Android 复验推进。

## 文件导航

- [任务看板](BOARD.md)：由 registry 生成，可在 GitHub 浏览。
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
