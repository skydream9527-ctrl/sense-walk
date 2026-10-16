# SenseWalk 多 agent 协作

这套系统把开发安排、交付、审核与证据保存到 GitHub。无需额外服务、自动调度器或完整本地 Android 环境。

## 只需发送的四条入口提示词

- ZCode：`请先 fetch 最新 origin/main，从该版本读取并执行 docs/collaboration/roles/zcode.md；保留现有工作。`
- MiniMax Code：`请先 fetch 最新 origin/main，从该版本读取并执行 docs/collaboration/roles/minimax.md；保留现有工作。`
- Trae Design：`请使用 Design 模式，先 fetch 最新 origin/main，从该版本读取并执行 docs/collaboration/roles/trae-design.md；保留已有设计草稿。`
- Antigravity：`请先 fetch 最新 origin/main，从该版本读取并执行 docs/collaboration/roles/antigravity.md；保留现有工作。`

同一角色后续继续使用同一句。角色入口不绑定旧提交；每次都查询任务登记与最新交接。四个入口由用户交给对应工具。

## 2026-10-15本轮进展与当前分工

main基准904ab01。新交付：[地形PR #14](https://github.com/skydream9527-ctrl/sense-walk/pull/14)、[雨林设计PR #15](https://github.com/skydream9527-ctrl/sense-walk/pull/15)均已发布且云端CI成功；地形提示/gait尚无UI消费者，雨林53文件hash/bytes匹配但未审。森林接图PR #3原approved，Git冲突已解决，当前协作CI因改写旧交接附录失败。MiniMax SW015未见远端新交付。详见 [本轮核查](evidence/P-20261015-02/README.md)。

| 角色 | 下一步 | 退出条件 |
| --- | --- | --- |
| ZCode | 修SW010归档门禁；补SW005 R2界面/提示/步态/恢复回归 | 独立任务分支、新文件说明不改旧记录；真实App证据+全部CI，交QA |
| MiniMax Code | 执行ready的SW015，0 API；读取真实SW011和PR15作解析样本 | 严格id/type/空集合/错规格/批准链/累计账本自动断言，交真实PR |
| Trae Design | SW012补下游消费附页、配合审稿/参数冻结 | 保留R1原字节；实质修改出R2，不重复从零画或直接生图 |
| Antigravity | 收口PR3，审PR15、SW005 R2及SW015，顺序集成/出组合包 | 精确head/hash/CI；SW012+SW015都accepted才激活SW006 |

SW001/SW004/SW011/SW014既有accepted保留。当前main/已确认build109不含这些未合PR功能；作者local XML296/0与云端CI成功分别记录，不冒充本轮运行Android。真机/真人Pending。bootstrap维护不代表已向外部工具发消息，用户继续转发上方稳定入口即可。

## 文件导航

- [任务看板](BOARD.md)：由 registry 生成，可在 GitHub 浏览。
- [最新进展与下一轮规划](evidence/P-20261015-02/README.md)：main/PR/本机草稿分别核对。
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
