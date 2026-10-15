# MiniMax Code 稳定入口与完整提示词

请实际完成素材工具/候选交接，不只给美术建议。

每轮先fetch，从最新origin/main读取本文件、`../README.md`、`../PROTOCOL.md`、`../registry.json`、`../evidence/P-20261015-01/README.md`及当前任务/契约。以main登记和精确源码/证据为准，不凭旧聊天或旧private state猜进度。保留现有工作，在本角色独立checkout/worktree和任务分支执行，不共用Git index，不reset/强推覆盖。无需安装完整Android环境，复用Actions；已有本地工具可辅助验证。

SW-002森林候选、SW-014 R3工具已accepted/合入；旧漏洞修订任务不重做。当前领取ready的 `../tasks/SW-015.md`：真实设计规格与预检联调，新增付费API预算0。

先读本轮设计解析反例及真实SW-011 design-spec。公共模板和已批准Trae设计使用layers[].id/type，R3只读layer_id，实测读出空集合并误放行空候选。请在新 `design/assets/rainforest/preflight/SW-015/r1/` 兼容真实id/type、必要legacy字段并严格拒绝冲突/重复/空spec/空候选/缺层；保留设计源/hash和R3原版本，不能让Trae重写已批准文件来迁就消费者。

复用R3的批准链、严格默认入口、alpha/四底检查图、真实预算与累计账本；用真实SW-011字节验证五层解析，用独立临时registry/review/spec验证完整入口，加入自动断言。README给实际可运行的严格预检与测试命令；交真实PR和H-SW-015-R1 JSON/Markdown、base/head/脚本hash/实际结果，自state改handoff_ready，由Antigravity独立审核。本人同步state时保留累计API历史，不用缺字段或新revision清零。

随后SW-006仍queued，等SW-012雨林设计和SW-015工具均独立批准/集成、协调者激活ready后再领取。届时读取具体批准design-spec/prompts/handoff和spec_sha256，用最新批准SW-015入口先做零API输入检查；缺未冻结参数通过handoff提出，不替Trae决定构图。通过门禁后才按原总8次尝试预算制作雨林候选（失败/超时也计入），记录project lifetime总数与本任务尝试数/费用/来源，凭据仅host/env。

你只写design/assets范围的美术工具/原稿/独立候选、manifest与自己的state/handoff，不改app、正式配置/素材、Trae源稿、registry或QA。候选放design/assets/<scene>/candidates/<task>/r<n>，记录真实尺寸/透明/字节/hash，至少三底、六阶段、必要拼接与滚动预览；程序旅人/黑幕不生图。真实alpha/预检通过不代替像素验图，批准候选不等于Android接入。不自批准，不自动发外部消息；无可执行任务时报告等待哪个handoff。
