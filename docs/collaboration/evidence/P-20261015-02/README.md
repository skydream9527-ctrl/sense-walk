# P-20261015-02 · 新交付核查与下一轮分工

日期2026-10-15；main基准 **904ab019dbc31a9a84a00d410b85868c3ddfb9b9**。本轮是用户授权的bootstrap观察/计划维护，不代替Antigravity独立批准，不代表向四个工具发过消息。

## 实际变化

| 角色/任务 | 精确进展 | 本轮判断/下一步 |
| --- | --- | --- |
| ZCode / SW-010 | PR #3 head e7441a2fb9ba04178e806a0675fa584e04ba90e5，原R1 approved保留；相对main仅6文件delta，两张生产WebP与批准hash一致，merge-tree无冲突 | 旧state冲突已消失。Android run38736953424成功，但协作run38736953399失败：作者在已归档appendix末尾追加同步说明。先修历史门禁，再由QA集成 |
| ZCode / SW-005 | PR #14 head9541f62e59e7dbff3c8b3105f4b7c5ecd0723e36；业务9a791b55db032ce0d48b8762f146cc5c98cec23f；TerrainMotor/控制器+22新测试、作者模拟器800m证据已交。PR Android/协作CI均成功 | 实际生产改动只有两个domain文件，没有UI消费者；提示与gait仅暴露接口，作者也列为Pending。bootstrap登记rework，要求R2补齐当期功能，不挪到SW-007 |
| Trae / SW-012 | PR #15 headc723048116fd2c36a7c19f2ab6c926f47b78beac，业务cab78f6eecf9e4dbea831f4a0c6911a9d919c4fb；53文件全hash/bytes匹配、无漏列，PR Android/协作CI成功 | handoff_ready，待QA审稿/冻结；不是仍等开工，也不是已accepted或可直接生图 |
| MiniMax / SW-015 | 远端分支清单、最近PR及main中未见SW-015交付 | ready，当前关键依赖。马上执行零API接口适配；外部工具本机是否开工未知，不能从旧state猜测 |
| Antigravity | PR #13已合入904ab01，追加SW-011 merge SHA纠错；旧记录保持 | 纠错已完成，无需重复。仍需审/集成三路交付，不能只做文档纠错后停止队列 |

保留已accepted的SW-001/SW-004/SW-011/SW-014和原审核，不重复开发。当前main未包含SW-010接图、SW-005地形或SW-012雨林设计。已确认build-109-6104e3d仍存在，包含可靠性/快照，不含这些未合入业务。

## 两项明确收口

1. **PR #3历史文件改写**：GitHub真实日志原句为 `history: existing record changed/deleted docs/collaboration/handoffs/zcode/H-SW-010-R1-appendix-sizes.md; add a new revision/correction instead`。作者在本人分支把该旧文件恢复为main原字节，保留新增说明到新 `H-SW-010-R1-sync-20261015.md`，追加提交，不reset/强推、不豁免历史检查。源素材/产品参数未变，不需要重做已批准柔光。最新head全CI绿且QA复核后才集成。
2. **SW-005界面缺口**：源码搜索UI无 `consumeStabilizeHint`、`TerrainMotor.Gait`、`snapshot.gait`/`snap.gait`消费者，PR仅改TerrainMotor.kt/VirtualWalkController.kt及测试。DEVELOPMENT §5.6/5.7要求首局提示、站稳动作、轻跳/攀坡/步态，不是后续雨林才可见。ZCode交R2，把控制器状态接到ViewModel/SessionScreen/ForestShell；UI动画不驱动距离，reduceMotion关非必要动态；暂停/后台/取消/恢复/终态及时停表现。追加兼容说明/精确head及实际App证据，旧R1不改。

快照R1提出“无新增字段、恢复按s_pos重建”可供QA审查，不能等同已批准新契约。恢复仍是同sessionId，首局提示再次出现是否符合产品由QA明确裁定；不要用“新局”措辞自行放宽既有不重播承诺。另请QA增加死区d=.01/.08接近坎的实际Kotlin边界用例，确认自动动作与输入/速度规则一致；当前未执行该用例，不预判失败。

## 雨林设计与下游

候选五层：mist(overlay,90m,.55,fade20)、trunks_canopy(parallax .30,270m,.85,25)、vines_light(parallax .60,450m,1.0,25)、distant_glow(overlay,675m,.85,25)、glade(overlay,855m,.90,20)。1080×1920；实际fade完成点0/110/295/475/700/875m；900m终点；旅人x=.34/脚底y=.865；下45%触控。命名与parallax仍proposed。

读取终景、小屏裁切、glade三底局部预览：湿绿/藤蔓/雾与柔光参考已可查看。此为抽样图像阅读，不是全层独立验图、Android或真机验收。QA须检查53文件、全部三底/边缘/裁切/源复现，批准记录绑定原spec字节/hash；**冻结当前参数用新review/decision，不由QA改Trae spec或manifest**。若命名/布局需改，由Trae出R2再审。设计包status/id_status是当时提案状态，不通过编辑旧稿“刷成approved”。

Trae本轮补下游消费说明（新增交接附页、引用现有spec/hash/逐层参考），澄清光效提示词“融入黑色”只指预览观感，实际文件必须真透明，不能烘焙黑底；设计/alpha/构图改动则新revision。MiniMax现在可把PR15作为只读解析样本，不能当真实批准链。SW-015必须真实五层解析与空/错/重复规格拒绝，保留严格批准/累计预算/alpha/四检查图；0 API。SW-012与SW-015都accepted/集成后才SW-006，原总8次尝试不重置。

## 整体执行顺序

- 并行A：ZCode修PR3归档门禁，补SW005 R2界面/恢复回归；两个独立任务分支顺序维护本人state/deliveries。
- 并行B：MiniMax完成SW015；Trae配合SW012审稿与消费说明，实质设计变更新revision；Antigravity先收口PR3、审SW012并随到审SW015/SW005。
- 门禁后：SW006雨林候选 → 独立验图 → SW007 900m双模式/真实雨林声景/生产素材接入；SW007仍等SW005+SW006 accepted。
- 雨林稳定后：SW008启用前拆城市/沙漠各自设计→候选→接入子任务，预算/接口/所有者明确后再并行；不提前混入当前任务。
- QA持续整理设备矩阵与组合main测试Release；真机计步/锁屏15min/耳机来电/重启及最终5–8人体验保留Pending，无本地完整Android环境前置。

四个稳定入口及完整执行要求见 [角色入口](../../README.md)，用户仍只需转发一行文件提示词。没有新增自动调度器、自动消息或重复协调启动任务。

## 证据与范围

- [远端快照](source-snapshot.json)：GitHub connector实际查询main、PR3/14/15、Actions及准确build109 release；PR状态/mergeable只是查询时值。终端DNS无法解析GitHub，改用已连接GitHub工具完成远端读取，未因此把缓存ref当实时GitHub。
- [可重跑源码核查](audit_sources.py) 与 [结果](source-results.json)：精确Git对象、53文件全hash、UI调用点、PR3合并/归档改写/两张素材hash。
- [作者本地JUnit原始文件](author-junit)：只读复制作者SW005 worktree已有28份XML，296项/0失败/0错误/0跳过；不是本轮自己执行测试，也不是下载的云端XML。云端run38744519423另核为success，报告artifact11978655122对应临时合并bdea9c674d34a363fba0118cc7a4b2b74700e0a5；因本机DNS未取得ZIP字节，不把作者XML冒充云端原件。
- 未自己启动模拟器/Android或paid API，没有物理设备/真人结论。作者800m截图/手势声明仍由QA独立复验。
- 本轮计划检查结果见 [planning-checks.json](planning-checks.json)。历史review/evidence/handoff/decision保持不变；新rework为bootstrap观察，正式review仍归Antigravity。
