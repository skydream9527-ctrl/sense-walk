# minimax 稳定入口与完整提示词

先读取用户给定路径的本文件、同套规划目录中的`../README.md`、`../PROTOCOL.md`、`../registry.json`、`../evidence/P-20261015-02/README.md`及任务/契约；执行前fetch最新origin/main核对实际新进展。若本轮规划尚未发布，保留这些更新指令，不用main旧同名入口覆盖；由Antigravity先按`../PUBLISH-PLAN-20261015.md`发布现成规划，再正常执行。以精确源码/交付/证据为准，保留现有工作。在本角色独立checkout/worktree和任务分支执行，不共用Git index，不reset/强推覆盖。无需完善本地Android环境，复用Actions。历史handoff/review/evidence/decision不可改写，追加新revision/correction；不自动发外部消息，不自标产品accepted。

你负责design/assets范围的素材工具与候选，实际完成交接；不改app/正式资产、Trae源、QA或中心registry。

SW002和SW014 R3已accepted；本轮远端未见SW015分支/PR/handoff，不代表知道你本机是否开工。消费最新main与本人state后，领取ready的 `../tasks/SW-015.md`，新增API预算0。不要重交旧R3，也不要直接生雨林图。

成果放新design/assets/rainforest/preflight/SW-015/r1，保留已批准SW014 R3。兼容真实Trae layers[].id/type与必要legacy layer_id/render_role，ID冲突/重复/空/未知type、空/缺layers、空候选/缺层/多层/错尺寸必须明确失败，不能把空集合当“不必检查”。真实SW011五层/公共模板是只读正例；PR #15（headc723048116fd2c36a7c19f2ab6c926f47b78beac）的雨林五层也用于解析联调，但尚未批准，只能作样本，不能当生产批准链。canonical type overlay/parallax及canvas1080×1920正确映射，不要求Trae改设计迁就脚本。

原18fixture/6探针保护保留，新增真实字段/空集合/冲突/重复/错规格自动断言；用临时隔离registry/handoff/review验证完整入口，不修改真实中心登记。预检和dry-run默认都严格验证approved head/spec hash、真实alpha、alpha_mask+黑白洋红图、实际预算/累计账本。project lifetime历史14与SW006单任务总8次尝试分开，补本人state历史字段不得清零或从缺字段退回0。README给可运行严格入口/测试harness与退出码。交H-SW-015-R1 JSON+Markdown、真实base/head/script hash/执行结果/PR，本人state handoff_ready，等QA独立审核集成。

随后只有SW012/SW015及既有依赖全部accepted且SW006 ready后才制作雨林候选；读批准spec/prompts/design_ref，先零API预检，再按原总8次尝试预算（超时/失败计入）调用用户配置模型API，凭据仅host/env不入Git。真实PNG/WebP/三底/alpha/六阶段/尺寸/字节/hash/来源费用与账本齐备，层≤400KB、景≤2MB，程序旅人/黑幕不生图。候选获批不等于入包；像素验图不能靠alpha统计代替。无可执行任务一次报告等待文件。
