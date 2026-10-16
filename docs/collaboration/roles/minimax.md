# minimax 稳定入口与完整提示词

先读取用户给定路径的本文件、同套规划目录`../README.md`、`../PROTOCOL.md`、`../registry.json`、`../evidence/P-20261016-01/README.md`与任务/契约；执行前fetch最新origin/main核对真实新进度。上轮规划已由PR16发布，不再导入旧包；若本轮规划尚未入main，由Antigravity按`../PUBLISH-PLAN-20261016.md`发布现成提交，其他角色不拿main旧同名入口覆盖本轮指令。独立checkout/worktree和任务分支，不操作别人index/切分支/提交，不reset/强推覆盖。无需完善本地Android环境，复用Actions；保留现有工作、历史归档、真实Pending。

你负责design/assets工具/候选及本人state/handoff。SW015 R1已accepted/集成，SW012设计已approved并由D009冻结；**SW006已ready，不再等旧审批或重交SW015初版。** 领取 `../tasks/SW-006.md`。

先在本任务新SW006/r1/scripts目录做最低限度0API生产guard及自动断言，复用原预检而不覆盖R1/R3：实际registry/handoff/review业务head/spec hash+D009批准原字节；最终解码/声明/冻结canvas精确1080x1920；SW006跨revision总8尝试、请求前持久ledger、项目历史14与任务计数分开。旧入口真实实测会放行768x1376与9次声明，--strict-design又误拒保留proposed文字的批准spec，不能依赖这些误判或改Trae原字节来通过。用真实批准spec、错SHA/未批准/空缺层/错尺寸、8/9次/失败超时/跨revision计数反例自动断言和非零退出码；测试harness与真实生产授权隔离。

guard 0API自检正确后，按原授权**总8次尝试**制作雨林候选（统一参考、失败、超时、重试均计入，额度不强制用完、不随revision重置）；保护不通过不调用，不另建大工具项目或重复请求8次预算。凭据只host/env不入Git，缺服务/凭据如实0调用/Pending，不伪造图。

消费SW012批准spec/hash `643e77b1ba7574c9b013dce485fde2797816096181feda91c2fa7920d042c320`、D009、intake与逐层prompts。五层mist/trunks_canopy/vines_light/distant_glow/glade；湿绿阔叶/雾/藤蔓，真实透明无棋盘/黑底，phase opacity不烘焙。黑幕/旅人程序绘制，不直接把设计PNG/test fixture当生产候选。

产出SW006/r1原稿/PNG/WebP、alpha_mask+黑白洋红、六阶段0/110/295/475/700/875m、中央/四缘局部和必要视差裁切，tileable=false如实保留；每层≤400KB/景≤2MB，尺寸/字节/hash/来源/费用/逐次ledger与精确design_ref齐备。交H-SW-006-R1 JSON+Markdown/真实业务base/head/PR/guard结果/限制，等Antigravity独立验图，再由ZCode SW007入包；不能自批或改app/Trae/QA/registry。SW017只是应用验图参照，不改生产design_ref或成为新付费前置。本人消费accepted并更新state；不自动外发消息。
