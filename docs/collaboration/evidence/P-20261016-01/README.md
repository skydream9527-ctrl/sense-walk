# P-20261016-01 · 从森林收口转入雨林制作与接入

客户端日期2026-10-16；本轮main基准 **2339333afe447fddd0ef34c50cfc42f886da3b46**。这是用户授权的bootstrap核查/规划，不代替Antigravity独立产品审核，不代表已向外部四工具发过消息。共享根checkout只读；改动在本次已附规划worktree/独立codex分支。

## 已核实的新进展

| 项目 | 实际交付/集成 | 当前结论 |
| --- | --- | --- |
| 上轮规划 | PR16，merge bcb1bfbefc1cf80a9b4388930b25e7574fb6d634 | 上轮离线交付已由Antigravity发布，不能继续提示“尚未发布”或重导旧包 |
| SW010森林正式接图 | PR3，merge2b47f01aa64262433b52c1a071ddfec2ba4ee249；两张WebP批准hash匹配 | accepted/在main，旧归档门禁已修，不重做 |
| SW005地形R2 | PR14，业务b92144e07f9318f1e14f7f18e0a1a28b0115f0d7，交付c14958638d7d92c19e449ad151d1290cf8e087c2，merge70ebfc7587cf4e8e07dc4979ee0c18deb1616436；R-SW-005-R2 approved | UI状态消费、提示卡片、HOP/TENSE与死区.08、同局提示快照已在main；代码accepted，物理与部分视觉时序证据仍Pending |
| SW012雨林设计 | PR15，mergebb05b035f1109d974790a9e576a77a539c2e43ed，R-SW-012-R1 approved/D009冻结；PR19附页merge16f89867f0d192042438f7061b4adccbd16d714e | accepted；53文件全hash/bytes匹配，逐层制作输入已共享，不再等设计批准 |
| SW015真实规格解析 | PR18，业务81fbf2d21e7cdc3131618f9ba6450109a3420f58，交付9c4ef5a8f9691b6de8ff5038d146a4afb5eaf846，mergea235f7376f6103c6c02bef3f4c4306dd6f0cc3d5；R-SW-015-R1 approved | accepted；既有批准保留。但真实生产尺寸/总预算检查有下述实测缺口，不把原fixture通过推广为完整生产保护 |
| 协调登记 | PR20，merge2339333，激活SW006 ready | 雨林制作前置已满足；main尚无SW006正式候选/交接或rainforest.json，雨林App未完成 |

main Android run **38847512206** 与协作run **38847512200**均success；工作流已有report/APK/source artifacts，预发布job为skipped。作者SW005工作区已有28份JUnit XML **303项，0失败/错误/跳过**，本轮只读核算并归档，不是本轮自己运行Android/JVM，也不冒充下载的云端XML。主线cloud ZIP未取得字节，artifact digest是ZIP哈希，不是APK内部文件哈希。当前可见测试Release最新按published_at为build109-6104e3d，仍不含新接图/地形组合；不是main没有生成APK。

## 实际制作前核查：不再重复抽象fixture

[零API探针](probe_production_gate.py) 使用main真实registry/review/handoff与D009冻结spec；候选图片只复制现有测试fixture，未改图片、未调用API。所有改动在临时.local-verify目录，测试的9次只是声明，实际消耗0。

| 输入 | 期望 | 真实结果 |
| --- | --- | --- |
| 实际SW012批准链+原spec，默认dry_run | 通过 | ok/exit0，实际批准链可用 |
| 完全相同输入加--strict-design | D009已冻结的原字节应可用 | failed/exit1；原文件仍proposed，工具错误要求改成approved，与不可改原字节约定冲突 |
| 真实批准1080x1920设计+解码768x1376测试图 | 雨林应拒绝森林旧尺寸例外 | 默认preflight ok/exit0，无失败项 |
| 上述样本，声明本任务本轮9次、项目总23次 | 超过SW006总8次应拒绝 | 默认preflight ok/exit0，无失败项 |
| 独立直接调用预算函数，9次/总23，无任何图片输入 | 超预算拒绝 | 全部check为ok，独立确认预算函数未执行总8次门禁 |

源码显示：R3允许集合包含历史768尺寸；SW015只核spec canvas，没有与每张解码尺寸比较；预算只核非负与不回退，没按sw006_attempts/limit拒第9次。图片尺寸与独立预算函数分别实测定位；新生产guard必须分别加入独立负例，不能只依赖同时含两错的样本。结果/每项完整check与脚本hash见 [production-gate-results.json](production-gate-results.json)。

解决范围压在SW006制作任务内：新目录加最小production_guard/请求前ledger与自动断言，0API自检正确后继续原总8次授权制作。**不再新建一轮大预检项目，不要求重批SW012、重交旧SW015或增加预算。** 旧R1与设计原字节保持；真实批准链/D009/hash为准，不用错误strict标志迫使改原稿。若保护或服务凭据不可用，交0调用/Pending，不伪造图。

## 补证与审计元数据

- 提示源码链已接（VM→SessionScreen→ForestShell gait），说明旧缺口修复；但本轮实际阅读 `docs/collaboration/evidence/H-SW-005-R2/hint-shown.png` 未看到“慢一点，站稳再跳。”卡片。不能凭文件名与作者报告称截图已经证明显示；此前3s消失本就Pending。由QA补同步视频/短间隔截图+UI hierarchy与准确App/head，不能运行仍Pending。此为证据范围问题，不自行推翻原代码accepted，也未自己启动模拟器。
- R-SW-015-R1.json/.md delivery_head写9c4ef5a8f4cffb0948cbb391306b4bdafd3c64c1，实际PR18交付为9c4ef5a8f9691b6de8ff5038d146a4afb5eaf846；business reviewed_commit 81fbf2d正确，结构check仍可通过。Antigravity新增correction，不覆盖历史审核。
- 快照契约摘要补已approved的stabilizeHintShown可选Boolean/旧档false/同session一次，版本仍1；依据H-SW005-R2与R-SW005-R2记录已有实现，不自行新批字段。

## 本轮四方分工与退出条件

| 角色 | 可并行执行 | 交付/不越界条件 |
| --- | --- | --- |
| MiniMax | 已ready SW006：0API生产保护→原总8次候选制作 | 真1080x1920五层/四检查图/六阶段/来源费用hash/ledger/manifest精确design_ref→独立验图，不把fixture或设计exports直接当候选 |
| ZCode | 新ready SW016：900m运行时底座/配置/渲染抽象/真实声景准备 | 复用双模式/Service/门禁/恢复、合法声音来源与听辨；候选未到不开放假完成选景或破坏全局加载；实际Kotlin/cloud→QA |
| Trae Design | 新ready SW017：应用上下文验图参照 | 复用原设计做两模式/阶段/尺寸/代表状态与验图标准，明确设计模拟；source/spec/prompt/preview manifest→QA，不改D009/素材design_ref |
| Antigravity | 发布本轮规划、现main组合测试Release/提示补证、随到审三路 | 精确head/hash/范围与实际merge，SW006+SW016各accepted才启用SW007；设备/真人Pending |

SW007增加已拆SW016依赖，最终仍等SW006生产候选；SW017不是新增素材前置。雨林完成后才拆SW008城市/沙漠各自设计→候选→接入/预算。真机标准距离/锁屏15min/耳机来电/重启与5–8人内测仍Pending，不能因303项与accepted数量宣称MVP完成。没有新后台调度器/自动消息/重复协调启动任务。路线依据 [D010](../../decisions/D-010-rainforest-parallel-production.md)。

## 证据导航与本轮发布限制

- [GitHub快照](github-snapshot.json)：实时connector查询main/PR/CI/job/artifact/release；终端DNS失败不影响connector实际读取。当前open PR列表为空。
- [源码/哈希/作者XML汇总](source-results.json)、[作者已有原始XML](author-junit)：森林/雨林各53文件全匹配，303项，准确来源和范围。
- [实际生产命令探针与完整结果](production-gate-results.json)：0API，真实批准链，原图复制未编辑；不伪造生产交付/消费记录。
- [本轮计划验证](planning-checks.json)：结构/依赖/历史/hash、31项协议回归与HTML/diff结果，产品Android未运行。

本轮终端仍不能解析GitHub，connector create_branch返回403写权限不足，**本轮尚未创建远端规划PR/合入main**。现成提交与交付包供Antigravity按 [20261016发布交接](../../PUBLISH-PLAN-20261016.md) 导入、标准PR/CI后发布；准确最终base/head/tree/hash在交付包DELIVERY.json。本轮限制不改变“上轮已由PR16发布”的事实。用户只需分别转发四个入口文件提示词，不需要手动拼接任务内容。
