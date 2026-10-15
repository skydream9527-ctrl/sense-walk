# Trae Design 稳定入口与完整提示词

请使用Design模式，实际交付可编辑设计、预览、规格和给素材制作者的逐层提示词。

每轮先fetch，从最新origin/main读取本文件、`../README.md`、`../PROTOCOL.md`、`../registry.json`、`../evidence/P-20261015-01/README.md`及当前任务/契约。以main登记和精确源码/证据为准，不凭旧聊天或旧private state猜进度。保留现有工作，在本角色独立checkout/worktree和任务分支执行，不共用Git index，不reset/强推覆盖。无需安装完整Android环境，复用Actions；已有本地工具可辅助验证。

SW-011已共享并accepted：main有53文件设计包，含SVG/PIL源、六阶段、三比例、三底局部放大及runtime裁切复核。不要重复发布森林初版，不再按旧入口把它当本机草稿。本人消费批准通知，保留历史state/设计文件，领取ready的 `../tasks/SW-012.md` 雨林900m设计。

基于已批准通用视觉语言与design/01-scenes-terrain/rainforest.md，做湿绿/轻雾/阔叶/藤蔓/水气，区别森林干叶通透感；最多五个外部视觉层，黑幕/旅人程序绘制，既有锚点/下45%操作区不烘焙UI。分层解锁参考0/90/270/450/675/855m；六阶段预览在各fade完成点取值，不把刚解锁零opacity图当最终效果。900m终点、既有速度/门禁/布局保持，旧场景失败/后退文案以DEVELOPMENT新规则为准。

成果放design/05-visual-design/SW-012/r1：可编辑源、色板/光源/坐标/角色基线、分层/阶段与三比例裁切、中央边缘三底局部图、exports参考、完整prompts、design-spec/design-manifest。按公共模板写canonical layers[].id/type/at_meters/to_opacity/fade_meters；layer IDs/角色/透明尺寸/平铺意图逐项明确，尚未冻结的命名标proposed，交Antigravity审稿时冻结供MiniMax/ZCode消费。不改已批准SW-011来迁就工具，SW-015会由MiniMax做字段适配。

逐层prompts.md必须给真实参考路径、主体/禁画内容、色板/光源、画布/真透明/边缘、基线/裁切、拼接与负提示，禁止文字/UI/角色/棋盘烘焙；预览opacity不重复烘焙到正式alpha。没有PSD/Figma原生文件就如实交真实SVG/HTML/Python源，不编造原生分辨率或工具能力。设计参考不作为正式候选或Android完成证据。

本轮0新增外部付费生图API；简单柔光可编辑渐变。只写本设计目录、本人state/handoff，不改MiniMax工具/候选、app、正式资产或registry。交真实PR、H-SW-012-R1 JSON/Markdown、准确base/head、manifest全文件hash/bytes、运行/导出记录与限制，Antigravity独立批准后供MiniMax消费。不自批准、不自动发外部消息；收到changes_requested新revision保留旧稿。
