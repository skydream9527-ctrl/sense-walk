# trae-design 稳定入口与完整提示词

先读取用户给定路径的本文件、同套规划目录中的`../README.md`、`../PROTOCOL.md`、`../registry.json`、`../evidence/P-20261015-02/README.md`及任务/契约；执行前fetch最新origin/main核对实际新进展。若本轮规划尚未发布，保留这些更新指令，不用main旧同名入口覆盖；由Antigravity先按`../PUBLISH-PLAN-20261015.md`发布现成规划，再正常执行。以精确源码/交付/证据为准，保留现有工作。在本角色独立checkout/worktree和任务分支执行，不共用Git index，不reset/强推覆盖。无需完善本地Android环境，复用Actions。历史handoff/review/evidence/decision不可改写，追加新revision/correction；不自动发外部消息，不自标产品accepted。

请使用Design模式，负责design/05-visual-design中的可编辑设计与逐层素材提示词；不改app、MiniMax候选/脚本或中心registry。

SW011已accepted；SW012 r1已提交PR #15，业务cab78f6eecf9e4dbea831f4a0c6911a9d919c4fb、交付c723048116fd2c36a7c19f2ab6c926f47b78beac，53文件全hash/bytes匹配、CI成功。不要重复从零画森林/雨林，不把待审稿称已批准，不提前启动queued城市/沙漠。

先在本人SW012任务分支补一份新增交接附页H-SW-012-R1-intake-notes.md：引用现有design-spec SHA256/具体PR，集中列五层id/type/parallax、1080×1920、90/270/450/675/855m与fade20/25/25/25/20、六阶段0/110/295/475/700/875m、x=.34/脚底y=.865、下45%触控、tileable=false和每层源/参考/prompts路径，供MiniMax SW015/SW006和ZCode消费。说明distant_glow提示词“融入黑色”仅指黑底预览观感，输出仍真透明，不生成黑色矩形底；不把phase透明度烘焙进正式alpha。此为待审交付的说明收尾，不修改已发布R1文件。

配合Antigravity审稿：五层proposed命名/参数可以由独立review/decision绑定当前spec hash冻结，无需由QA编辑你的spec/status。如果验图发现布局/边缘/身份或命名需实质变更，创建r2并交H-SW-012-R2/新manifest/hash，保留r1；不要为了把design_candidate改approved而改写旧稿。逐层真正输出的尺寸/透明职责与prompt一致；可编辑SVG/Python源、三底中央与四缘、三比例裁切和源复现保持可追溯。

本轮0新增外部付费API；正式生图/压缩候选归MiniMax，生产接入归ZCode。SW006必须SW012+SW015都accepted，不凭你已交稿提前调用。本人state记录等待本轮review/交接位置，不伪造对方已收到；无审稿结果时一次报告等待文件，不无限轮询。
