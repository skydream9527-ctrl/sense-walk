# 2026-10-15 进展核查与下一阶段分工

Codex负责bootstrap核查/计划维护。基准main：`6104e3d4967dcca64ed02a26c484bffc564b61f9`，日期按America/Los_Angeles。本轮记录实际来源，不新增产品批准、不代表外部执行工具已接到消息。精确状态见 [source-snapshot.json](source-snapshot.json)。

## 已完成的进展

| 范围 | 实际证据与结果 | 后续 |
| --- | --- | --- |
| SW-001可靠性 | PR #1合入，R-SW-001-R2 approved，registry accepted；集成`1e238812c62c97486e96fa68c2eecbf450e160a0` | 不重复旧补强；真机计步/锁屏/耳机来电仍Pending |
| SW-004会话快照 | PR #9合入，R-SW-004-R1 approved/accepted，集成`814fc78f72017c643ce43cbf4b3ced6d89c1f5bd`；新增实际快照存取、恢复入口与25项JVM回归 | SW-005已ready，推进地形及恢复联动 |
| SW-011森林设计 | PR #7合入，R-SW-011-R1 approved/accepted；本轮53文件hash/bytes全部匹配，可编辑源/三比例/局部图/runtime裁切已共享 | SW-012已ready，推进雨林900m设计；参考设计不等于生产素材入包 |
| SW-014预检R3 | PR #8合入，R-SW-014-R3 approved/accepted；本轮重跑18fixture/6探针与预期吻合 | 原范围保留，新增真实设计接口联调SW-015，0 API |
| Antigravity | PR #6/#10/#11记录独立审核/集成与依赖激活，已发布新测试包 | 收口SW-010，再验地形/雨林设计/联调新交付 |
| SW-010森林接图 | R-SW-010-R1已approved，柔光意图已有裁定；PR #3尚OPEN，head `2a7121677ee7579da1955dd0352631ec0525a566` | 当前与main仅`state/zcode.json`冲突，需作者同步，QA复核新head/CI后集成 |

源码实际存在SessionSnapshot/Store、PendingRestore、控制器/感官重建和服务恢复接线，当前main/测试包确已包含可靠性与快照。森林两层light_shows/clearing在main仍没有asset字段，继续程序降级；批准接图不等于已进入main。

## 测试包和证据

当前可下载：[build-109-6104e3d](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-109-6104e3d)，来自 [run 38714429274](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38714429274)，commit与基准main一致。已下载原始报告并计数：[26份JUnit XML/274项](test-summary.json)，0失败/错误/跳过；lint/debug build/发布成功。前一个main push被新的dispatch取消，不是业务测试失败。

本轮下载APK并实算SHA256，与GitHub asset digest匹配：`ae84c3de620e0cd96b2ae975a9bc8ec1795ba3d7bcd1032db5c9758f3137e8b0`，20,246,962 bytes，详见 [APK核对](release-apk-verification.json)。未在本轮安装运行，不把下载/hash等同真机验收。此包不含未合入的SW-010。

预检R3重跑见 [sw014-r3-rerun.json](sw014-r3-rerun.json)：严格模式1正例ok/17负例failed；显式fixture模式允许测试标记样本，2项ok/16项failed；6回归探针5拒绝/1允许，符合各自预期。运行脚本只读main来源，在临时目录修改fixture，不写真实SW-012批准，不调用API。

QA现有`test_pr9_r1_verification.py`是Python规格/模型测试；真正Kotlin覆盖以本轮26份JVM XML与对应源码用例为据。模型、源审、作者模拟器证据、独立设备复验分别记录。physical-device/真人结果仍Pending，M1/M2/MVP不据此宣称完成。

## 新发现：真实设计交接接口需要联调

已批准SW-011和公共design-spec模板都用`layers[].id/type`，R3的`extract_spec_layers`只读`layer_id`。本轮直接调用真实函数：两个五层输入都返回空数组；临时批准链匹配的测试中，空候选搭配canonical-id规格或空spec均被默认预检判`ok`，因为空集合跳过必需层检查。

复现脚本 [probe_design_intake.py](probe_design_intake.py)、输入/输出 [design-intake-results.json](design-intake-results.json)。命令：`python3 -B docs/collaboration/evidence/P-20261015-01/probe_design_intake.py <仓库checkout> --out <本地结果.json>`。只有临时fixture含模拟SW-012批准，真实registry仍ready；无源稿/正式素材改动。

因此新增 **SW-015真实设计规格与素材预检联调**（minimax/code/0 API），依赖已accepted的SW-011/SW-014，设ready；与SW-012设计并行。保留SW-014原验收及字节，在新版本做消费者字段适配、空/重复/冲突输入和缺层严格校验，使用真实设计schema作为回归输入。SW-006新增SW-015前置，等雨林设计与联调工具分别独立批准后才开原8次预算的制作。此安排不是代替Antigravity正式review，也不要求Trae改已批准规格迁就脚本。

## 本轮四角色执行

| 角色 | 现在做 | 完成条件 |
| --- | --- | --- |
| ZCode | 先在原SW-010分支同步main/合并本人state信息，交新head/CI给QA；随后独立分支做ready的SW-005 | 接图获准集成；地形站稳/轻跳不刷距，暂停/后台/快照/reduceMotion有真实回归与交接 |
| Trae Design | 领取ready的SW-012，不重复森林包 | 900m雨林分层、canonical id/type、fade完成点/三比例/局部/源/逐层prompts、manifest与handoff；由QA冻结映射 |
| MiniMax Code | 领取SW-015，0 API联调真实规格与门禁 | 实际五层解析/空候选拒绝、旧保护回归、明确严格入口与自动断言，提交PR/H-SW-015-R1供独立审核 |
| Antigravity | 消费已批准SW-010的新同步head并集成，随到审SW-015/SW-012/SW-005 | 记录精确review/merge/CI；SW-012/SW-015都accepted才激活SW-006，接图合入后发布新的组合包 |

整体顺序：可靠性/快照已完成代码阶段→地形；森林设计已共享→雨林设计→候选→双模式接入；地形与候选均通过后SW-007；城市/沙漠在SW-008启用前拆成设计/候选/接入；SW-009汇总真实设备与5–8人内测。真机测试可提前进行，不拖到最后。

本轮同时把session-snapshot的过期“草案/尚未实现”摘要对齐已冻结模型，整理中心登记/看板/四入口；生产者private state由本人消费批准通知，不代写。旧SW-011 review Markdown的merge SHA与实际registry/PR有笔误差异，由Antigravity追加correction。源码ZIP当前约197.9MB，后续可另立打包优化，将确定性大型fixture与日常开发包分开，保持历史证据可追溯；不与本轮地形/雨林接入混交。

完整工作要求已保存到角色入口和任务文件。用户分别发送稳定入口提示词即可；没有新建调度服务、自动消息、付费生图或商店发布。
