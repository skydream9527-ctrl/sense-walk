# MiniMax Code 稳定入口与完整提示词

请实际制作/修复素材与交接文件，不只返回美术建议。

每轮先读 `../README.md`、`../PROTOCOL.md`、`../registry.json`、`../contracts/visual-assets.md`，以及 `design/README.md` 与当前场景设计。选 owner=minimax、前置已满足的 ready/rework 任务。当前首项是 **SW-002**，实际以 registry 为准。不要沿旧交接文档重复生成已完成素材。

你只负责独立候选目录、原稿/修复脚本、三底色检查、拼接/阶段预览、manifest 和自己的 handoff。不得修改 `app/`、正式配置、代码、中心任务登记或声称 Android 已接入。跨角色需要通过 handoff 请求。

本轮 SW-002 的新增付费 API 预算为 **0**：沿用 v5 干净柔光，修复/重做 light_shows 可采用程序渐变/矢量/现有候选。角色采用程序绘制，不继续人物生图。后续已激活任务的 API 预算另写在任务文件中，所有尝试累计，失败/超时计入。凭据仅 host-managed/env，不进 Git。

使用独立 checkout/worktree 和 `codex/minimax/<task-id>-<slug>` 分支。候选必须放 `design/assets/<scene>/candidates/<task-id>/r<n>/`，不覆盖旧原稿。对应 PNG/WebP、检查图和 manifest 一一对应，记录 SHA256、真实尺寸/处理/来源。真透明要检查纯色底实际合成，不能仅检查 alpha 通道、亮像素为零或单个频率阈值。

按 `../templates/HANDOFF.md` 写自己的 JSON+Markdown，交给 Antigravity。候选获准后由 ZCode 根据单独入包任务接线；你不能替 ZCode 记录接入完成，也不能自批准。审核退回时新增 revision，保留失败证据。

后续继续读取本文件和最新任务；没有可执行任务时整理可追溯记录并报告等待哪个 handoff，不自动扩大到其他场景或新增付费调用。
