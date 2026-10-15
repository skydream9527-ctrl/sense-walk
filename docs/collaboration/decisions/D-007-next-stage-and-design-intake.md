# D-007 转入地形/雨林设计与真实接口联调

日期2026-10-15（America/Los_Angeles）；状态adopted。用户要求继续核查并安排四角色。Codex作bootstrap计划维护，不新增产品批准。

依据 [P-20261015-01](../evidence/P-20261015-01/README.md)：SW-001/SW-004/SW-011/SW-014已独立验收合入；SW-005/SW-012已ready；SW-010仅approved未集成，PR #3与main冲突在作者state。build-109已发布，main274项通过。

- 保留全部既有accepted/review/集成SHA，不重复补强、恢复、森林设计或R3旧修订。ZCode先顺序同步SW-010自己的分支并解决state冲突，Antigravity复核当前head/CI后合入；ZCode在另一任务分支实现ready的SW-005。Trae领取ready的SW-012雨林900m设计。
- 新增SW-015（minimax/code/0 API），依赖SW-011/SW-014并设ready，专做真实设计到预检的字段联调。已批准Trae规格/公共模板用id/type，R3只读layer_id，实测提取空集合并误放行空候选；不能仅靠原fixture通过跳过此交接缺口。
- SW-006新增SW-015前置，仍等SW-012设计approved/集成与SW-015工具approved/集成；原SW-014 accepted只代表其原交付范围获批。新消费者版本保留原R3/历史批准，不覆写旧脚本与证据；正式候选使用最新批准入口。此门禁不新增付费预算，原8次总尝试保持。
- 将已获SW-004独立审核冻结的具体字段补入session-snapshot契约，替换过期“尚未实现”摘要；不改产品恢复语义。SW-005扩展持久字段时先追加具体兼容决策，不能破坏已批准恢复或用动画位移刷距。
- 各角色本人消费accepted通知后更新private state，bootstrap不代写。Antigravity队列以SW-010集成、地形/雨林设计/联调新交付及组合CI为主；已发布build-109不被宣称包含未合入SW-010。独立QA的Python模型与实际Kotlin/Android证据分别记录。

不增加调度器/重复协调启动任务；用户仍分别发送稳定roles入口，文档发布不等于外部工具已接收。真机/真人Pending、标准距离/相位/opacity及商店发布边界保持。
