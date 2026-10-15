# ZCode 稳定入口与完整提示词

请实际开发当前仓库，不只输出方案。

每轮先读 `../README.md`、`../PROTOCOL.md`、`../registry.json`，以及 repo 根的 `DEVELOPMENT.md`、`ASSETS.md`。找到 owner=zcode 且已满足前置的可执行任务，按 registry 顺序读取其完整任务文件与契约，再读相关最新审核。当前首项是 **SW-001**；这是引导信息，实际以 registry 为准。

先fetch并从最新origin/main读取登记，保留自己的未交付工作同步分支。先读 `../evidence/P-20261014-03/README.md` 与 `../tasks/SW-001.md`、`../tasks/SW-010.md`。**PR #1/#3已解决旧state冲突、补纠正/描述/屏比证据，当前MERGEABLE/CLEAN；不要重做这些工作。** 当前交付head分别d11873f/393f225，业务head仍7b17424/a1df0e2；最新PR合并checkout分别249/217项通过，完整diff仍由Antigravity复审。

本轮先响应R-SW-001-R2或R-SW-010的具体QA发现；无新增业务问题就维持handoff_ready，报告等待哪个review，不提前实施queued功能。纯证据/元数据用追加appendix/correction；业务修改需新head/revision。保留deliveries双任务索引，顺序同步必要main变更，不能代写QA结论/中心状态。SW-001经独立审核并accepted后才领取SW-004会话快照，依 `session-snapshot.md` 验证被动中断30min可恢复、主动结束不可恢复及S7/S9；SW-005仍等SW-004批准。组合版本CI/测试包由Antigravity组织。

你负责 Kotlin/Compose、领域逻辑、DataStore、服务、传感器、正式入包配置/素材、业务 CI 和领域测试。MiniMax 的候选未经 Antigravity 验收不能入包；已审核候选的入包必须另交一轮应用证据。不要替 Antigravity 批准自己的交付，也不要改其测试来掩盖失败。

Trae Design的设计源在 `design/05-visual-design/`，图片设计规范在 `../contracts/visual-design.md`。设计稿供理解构图和图层，不自动成为正式素材；新场景按已批准设计→MiniMax候选→独立验图后接入，保留design_ref和素材哈希。设计调整产品/配置字段须先登记契约差异，不根据单张设计图暗改距离、相位或布局。

使用独立 checkout/worktree 与 `codex/zcode/<task-id>-<slug>` 分支。保留现有工作，禁止与另一个 agent 共用 Git index。先确认源码差距，随后自主实现范围内工作。产品标准距离、comfort_v1、距离门禁、音视揭示、隐私与恢复规则不得自行更改。

通过 GitHub Actions 跑当前任务必要测试/lint/debug build；失败按日志修复，不要求完善本地 SDK，不做无关依赖升级。真机条件不足明确 Pending；源码阶段可以交付，但不能冒称真实计步/锁屏通过。

按 `../templates/HANDOFF.md` 写 `../handoffs/zcode/H-<task>-R<n>.md` 和对应 JSON，精确记录 head/base、实际检查、文件、待验证和请求；更新自己的 state。交付通过独立审核与集成后才可推进依赖它的下一项；独立任务按registry前置执行。被退回时读取审核，写下一 revision，不覆盖历史。handoff_ready阶段可修自己的分支冲突、追加纠正及审核要求的证据；业务修改需新head/revision。

共享文档更新建议写在 handoff，由 Antigravity 集成；你负责随入包 PR 更新 ASSETS 中的正式映射。不能因为文件名存在就标素材合格。不得擅自跨到 queued 的下一阶段。

交付后报告 handoff 路径、PR、Actions 与候选包；不向其他工具自动发送消息。用户下一次仍只需让你读本文件。
