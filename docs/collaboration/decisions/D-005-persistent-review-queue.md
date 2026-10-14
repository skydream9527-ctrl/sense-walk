# D-005 第三轮交付收口与常驻验收队列

日期：2026-10-14（America/Los_Angeles）。状态：adopted；用户要求核查并继续四角色分工。记录者Codex，bootstrap计划维护，无产品独立批准。

依据 [P-20261014-02](../evidence/P-20261014-02/README.md)：R2/正式接图/预检工具已有远端交付，Trae仍未共享；SW-013协调已accepted，但当前入口仍写执行SW-013，容易让QA停下或重复派启动任务。

- 新增稳定 `queues/antigravity.md`，保存精确已观察交付入口及待验动作；Antigravity持续审稿/登记/集成不需要每轮新增coordination ID。SW-003/SW-013原accepted及历史依据保持。
- SW-001、SW-010登记handoff_ready，表示观察到发布的R2/R1，独立验收未完成；旧正式review保持原head/verdict。registry可增 `observed_delivery`（远端分支/head/handoff路径/PR/来源报告）；它是核查定位，不替代本地latest_handoff或accepted条件。协调者消费原交付后再更新正式指针，不伪造作者文件。
- SW-014登记rework，依据本轮实际零API复现PF-01～04，允许MiniMax直接修r2。此为用户授权的bootstrap派工，非冒充Antigravity changes_requested；正式review由Antigravity记录，复验R2后才可accepted。
- ZCode顺序处理PR #1/#3同步冲突，不同时抢同一checkout/index。角色private state可追加 `deliveries` 对象（task ID→branch/business head/delivery head/handoff path/PR），保留多个待验任务定位；这是辅助索引，不作为中心状态或批准。只有本人维护，协调者不代写；当前工具不会验证该扩展字段，仍须人工核对。同步main产生冲突时合并信息而非选择一方抹掉另一任务。
- 已发布的handoff误述、缺PR URL、base SHA笔误用新revision/correction追加，不回写历史。PR标题/描述应反映当前最终变更，可正常更新。
- 不增加图片API预算，不改变产品米数/相位/opacity；终景强度由独立app验图与设计意图评估，若需重制走原所有权链和新哈希审核。

未来城市/沙漠仍在启用SW-008前拆设计/候选/接入子任务与依赖；当前优先消化已有交付，再推进快照/地形/雨林。此文件系统仍由用户把入口交给外部工具，没有自动消息或调度。
