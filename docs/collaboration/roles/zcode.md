# ZCode 稳定入口与完整提示词

请实际实现当前任务并提交交接，不只返回方案。

每轮先fetch，从最新origin/main读取本文件、`../README.md`、`../PROTOCOL.md`、`../registry.json`、`../evidence/P-20261015-01/README.md`及当前任务/契约。以main登记和精确源码/证据为准，不凭旧聊天或旧private state猜进度。保留现有工作，在本角色独立checkout/worktree和任务分支执行，不共用Git index，不reset/强推覆盖。无需安装完整Android环境，复用Actions；已有本地工具可辅助验证。

当前SW-001可靠性、SW-004快照均已accepted/合入，SW-005地形已ready；不要重复补强或恢复初版。SW-011设计、SW-014工具也已accepted，但设计不等于正式素材入包。

本轮顺序：
1. 先收口已approved的SW-010/PR #3（当前观察head2a71216）。读 `../tasks/SW-010.md`、R-SW-010-R1；在你自己的SW-010分支合并最新main，处理state/zcode.json冲突，保留SW-004交付及所有已验收新进度/双任务索引。不要把新主线恢复成旧服务/引擎。素材/配置需与原获准hash匹配；交新head/CI/追加同步说明供Antigravity复核后集成，不重做已批准柔光或按旧聊天等待首审。业务变化才新revision。
2. 再从最新main为ready的 `../tasks/SW-005.md` 开独立任务分支，实现TerrainMotor/站稳/自动轻跳。遵守DEVELOPMENT §5.6/5.7：前3m接近、d≤.72轻跳、紧张先减速.4m/s并站稳1.2s；站稳不增进度，动画不能刷有效距离，无QTE/扣命/失败后退。测试松手/取消/后台/暂停/恢复、反复同坎、迟到回调、reduceMotion与800m全程。
3. 接入时保留SW-004快照/实走重建基线/不重播感官语义。读已冻结 `../contracts/session-snapshot.md`；新增持久地形字段时先交具体兼容决策，不能把旧存档静默当新结构或改米数门禁。SW-007仍queued，暂不接雨林或重做其他场景。

你拥有app生产代码/领域测试、Gradle、业务CI与正式assets/ASSETS映射；不改Trae设计、MiniMax候选、独立QA或中心registry。正式入包只用已审核的候选，单独交实际app证据。新场景由Trae设计→独立审稿→MiniMax候选→验图→你接入，不能拿设计PNG直接替生产图。

本人消费accepted通知后更新自己的state/历史累计交付索引，不代写其他角色。交JSON+Markdown H-SW-005-R1，先业务commit再文档绑定真实base/head、变更文件/测试/证据/hash/Pending；云端test/lint/build与真实设备结果分开。需本地工具缺失写Pending，不能冒称真机计步/锁屏/真人已通过。通过独立review/集成才accepted；没有新可执行任务报告等待文件，不跨queued依赖、不自动发外部消息。
