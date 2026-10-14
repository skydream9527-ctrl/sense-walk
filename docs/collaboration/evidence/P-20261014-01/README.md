# 2026-10-14 进展核查与下一轮安排

本次记录者：Codex，按用户要求核查与维护协作计划（bootstrap）。这是源码/证据观察，不代替Antigravity的正式approved，也不替任何生产者声明新交付。

## 核查基准与实际结果

- GitHub main：`da9bd247bd4537787c1b6c0e26b966c38d46f22d`。此前未推送的5a129d4现已在main历史中，其 [协作CI](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38521697748) 已通过。
- main的 [协作CI](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38524651338) 和 [Android测试/lint/打包](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38524651350) 已通过。
- [ZCode PR #1](https://github.com/skydream9527-ctrl/sense-walk/pull/1) OPEN、可合并但未合入：最新head `bdb1ea7fab82855fd2e836e4454c0092451d4bef`，交接业务head仍为`2dba5ebbb4897a7a6b9f05e562a9bf6b5bebb39c`。
- 下载并解析PR的 [云端报告](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38529040737)：21份JUnit XML，**238 tests / 0 failures / 0 errors / 0 skipped**。原始文件与哈希保存于本目录 [test-summary.json](test-summary.json)。这是PR merge checkout `f22b9c7860447416d80c474a1f33db62ed55d319`的结果，不能说main已有238项修复后的验证。
- 本次在main基准独立工作区执行协作check与31项协议测试，全部通过；没有安装SDK、重跑Android本地构建、真机或真人测试。
- 最新测试Release仍为 [build-41-8ef1446](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-41-8ef1446)，早于候选交付与PR #1。不能用这个APK验收新修复或宣称包含新图。

## 四角色真实进展

| 角色 | 已观察到 | 尚未完成 |
| --- | --- | --- |
| ZCode | T06补强PR #1；作者提交了本地/模拟器记录，云端238项实际通过 | 下述新反例修订、独立review与集成；SW-010正式光效接入；T07快照/地形 |
| MiniMax | SW-002候选和独立approved记录已在main，两个WebP哈希与review一致；本轮零API | 雨林SW-006等待批准设计；可先做SW-014零API预检 |
| Antigravity | SW-003基线报告、历史风险检查及SW-002候选审核已合入 | PR #1完整head复验、SW-010应用审核、消费新Trae交付和更新中心登记 |
| Trae Design | 独立worktree已有SW-011草稿：SVG/Python源、五层导出、六阶段、三比例、逐层提示词；43份manifest文件哈希/字节数核对一致 | 草稿未提交、无handoff/批准；局部放大检查与真实runtime裁切复核；其后才做SW-012雨林 |

Trae草稿是本机未提交观察，main与GitHub无该设计包。观察摘要及manifest哈希见 [source-snapshot.json](source-snapshot.json)；不能把43份文件哈希一致当作设计已获视觉审核。它的`.gitignore`改动由协调维护范围处理，Trae提交只包含自己的设计/state/handoff。

## 森林“候选入库”与“应用入包”的区别

`a5ad6dd`的标题写了integrate，但它的实际diff只带入候选/检查图/交接文件，**没有修改生产forest.json或正式WebP**。当前配置的light_shows/clearing均只有`type: overlay`，无asset字段，仍用程序降级。生产目录残留的旧图均与批准候选字节及解码像素不同，且当前未被配置启用。

| 层 | 批准候选SHA256 | 正式目录残留SHA256 | 当前接入 |
| --- | --- | --- | --- |
| clearing | `1dcda4f7b61b038f4f9fddfa3351dcfd5d0679167388148f47b841153169ca33` | `c15064a9fd89cb38a7a74144cf930783182869f5082a90582259aa2882c50346` | 程序降级 |
| light_shows | `1973a1f594f1edd0a801e57251192c7629f7f802e621a2a95874328e257466f0` | `e03d587d232707456a4d7f0f16b5e23c712e095acce23a1c0412b13dd120b613` | 程序降级 |

本次只目检了候选785m缩略合成，没有运行Android视觉走查。SW-002 accepted仅指候选获批；**SW-010仍需实际接入、逐字节校验和应用证据**。MiniMax私有状态中“ZCode已经入包”的观察与实际diff不符，请生产者下一轮自行追加纠正，不覆写历史handoff/review。

## PR #1需要新增复验的具体问题

### P-01 · detector存在但注册失败时，距离脚步音回退被关闭

在PR head的 [StepSensorSource.kt](https://github.com/skydream9527-ctrl/sense-walk/blob/bdb1ea7fab82855fd2e836e4454c0092451d4bef/app/src/main/java/com/sensewalk/app/engine/sensor/StepSensorSource.kt) 中，hasDetector仍表示硬件存在，registerDetector返回false没有被保存。服务用`isStarted && hasDetector`决定关闭`stepAudioFromDistance`。counter注册成功、detector硬件存在但注册失败时：isStarted=true、hasDetector=true；detector不会发cue，距离也不再发脚步音。

ZCode应暴露实际detector注册状态并由服务据此选择cue来源；新增从传感器注册结果到SensoryCoordinator的调用链用例，证明counter-only回退确实出声、无双计距/双cue。当前端口测试仅证明start成功，未覆盖该服务接线。

### P-02 · “同刻合并步数带回”的说明与实际计数基线不一致

[RealWalkEngine.kt](https://github.com/skydream9527-ctrl/sense-walk/blob/bdb1ea7fab82855fd2e836e4454c0092451d4bef/app/src/main/java/com/sensewalk/app/domain/walk/RealWalkEngine.kt) 同刻分支直接更新lastAcceptedCount，未保留pending步数；下一正间隔只按新读数减去这个已更新基线计算。源码推演：`(0,0) → (1,1000) → (2,1000) → (3,2000)`返回`0,.7,0,.7`，与“合并步数带回、真实批量不丢”的交付说明不符。若按带回策略，最后应为1.4m，仍满足速度帽。

已有“大批量带回”测试的新增10步本身就超过cap，无法区分带回与丢弃。ZCode应采用一致的合并语义，补低步数、未被封顶掩盖的用例及暂停/重置清理；Antigravity独立执行反例。此条为源码推演，本次没有在本地编译执行该Kotlin反例。

### P-03 · 审核必须包含业务head之后的工具改动

`2dba5eb..bdb1ea7`除交接/evidence/state外，还修改了`tools/collaboration.py`。R1的业务head不能自动覆盖此变更。Antigravity需单独审核该维护修正，或要求R2绑定完整的新业务head；工具修正的所有权处理留协调记录，不能只称后续提交“全部是文档”。R1的云端pending也应以新revision/审核补记，不能回填旧文件。

## 协作CI红灯的实际范围

MiniMax旧分支e3d45ed的 [协作运行38530240493](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38530240493) 为failure，错误为临时fixture缺少SW-002 manifest，30项error。main的Antigravity提交已使fixture复制design/tools，main及PR #1对应最新协作检查均为success。这是旧分支测试工具版本落后，不能据此判定批准候选坏掉，也不能让MiniMax改app。下一轮同步main后按具体日志复验；仍失败才交Antigravity处理工具。

## 下一轮路线

1. **并行收口**：ZCode修订SW-001 R2，随后SW-010真正接入；Trae完成SW-011并提交；MiniMax做SW-014预检准备；Antigravity执行SW-013审阅/登记/集成队列。
2. **恢复与雨林设计并行**：SW-001获批后ZCode做SW-004；SW-011获批后Trae做SW-012。MiniMax在SW-012及SW-014获批后才制作SW-006，不提前付费生图。
3. **第二景闭环**：ZCode完成SW-005与SW-007；Antigravity核对恢复、地形与雨林双模式的真实应用证据。
4. **扩四景**：SW-008启用前按城市/沙漠拆设计→素材→接线→验收任务，不混成一个大PR；真机测试可从森林提前执行，SW-009最后汇总。

用户继续只发roles文件入口。登记状态是本次观察/计划，不代表已向外部工具发送消息或它们已领取新任务。
