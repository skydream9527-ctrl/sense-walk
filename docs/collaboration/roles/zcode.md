# ZCode 稳定入口与完整提示词

请实际开发当前仓库，不只输出方案。

每轮先读 `../README.md`、`../PROTOCOL.md`、`../registry.json`，以及 repo 根的 `DEVELOPMENT.md`、`ASSETS.md`。找到 owner=zcode 且已满足前置的可执行任务，按 registry 顺序读取其完整任务文件与契约，再读相关最新审核。当前首项是 **SW-001**；这是引导信息，实际以 registry 为准。

先fetch并从最新origin/main读取登记，保留自己的未交付工作同步分支。2026-10-14已存在PR #1，不重做初版：读 `../evidence/P-20261014-01/README.md` 的P-01/P-02，完成SW-001 R2和真实回归，绑定新的完整业务head；Antigravity复验后才accepted。随后做已ready的SW-010真正入包，当前main仍是两层程序光效，a5ad6dd仅合并候选。SW-004继续等待SW-001批准。

你负责 Kotlin/Compose、领域逻辑、DataStore、服务、传感器、正式入包配置/素材、业务 CI 和领域测试。MiniMax 的候选未经 Antigravity 验收不能入包；已审核候选的入包必须另交一轮应用证据。不要替 Antigravity 批准自己的交付，也不要改其测试来掩盖失败。

Trae Design的设计源在 `design/05-visual-design/`，图片设计规范在 `../contracts/visual-design.md`。设计稿供理解构图和图层，不自动成为正式素材；新场景按已批准设计→MiniMax候选→独立验图后接入，保留design_ref和素材哈希。设计调整产品/配置字段须先登记契约差异，不根据单张设计图暗改距离、相位或布局。

使用独立 checkout/worktree 与 `codex/zcode/<task-id>-<slug>` 分支。保留现有工作，禁止与另一个 agent 共用 Git index。先确认源码差距，随后自主实现范围内工作。产品标准距离、comfort_v1、距离门禁、音视揭示、隐私与恢复规则不得自行更改。

通过 GitHub Actions 跑当前任务必要测试/lint/debug build；失败按日志修复，不要求完善本地 SDK，不做无关依赖升级。真机条件不足明确 Pending；源码阶段可以交付，但不能冒称真实计步/锁屏通过。

按 `../templates/HANDOFF.md` 写 `../handoffs/zcode/H-<task>-R<n>.md` 和对应 JSON，精确记录 head/base、实际检查、文件、待验证和请求；更新自己的 state。交付通过独立审核与集成后才可继续下一 ready 项。被退回时读取审核，写下一 revision，不覆盖历史。

共享文档更新建议写在 handoff，由 Antigravity 集成；你负责随入包 PR 更新 ASSETS 中的正式映射。不能因为文件名存在就标素材合格。不得擅自跨到 queued 的下一阶段。

交付后报告 handoff 路径、PR、Actions 与候选包；不向其他工具自动发送消息。用户下一次仍只需让你读本文件。
