# D-001 文件交接协作方案

日期：2026-10-13（America/Los_Angeles）。状态：adopted，协作配置。
依据：用户要求由 ZCode、MiniMax Code、Antigravity 分工，任务和提示词落盘，后续只引用入口文件，所有交接可追溯。

采用 repo 文件协议 + 独立 checkout + GitHub PR/CI。ZCode 单写业务/入包；MiniMax 单写候选；Antigravity 独立验收与顺序集成。任务状态单一登记，生产者 private state/append-only handoff，审核与交付分开，跨角色接口有版本。暂不引入自动代理服务、自动付费调用、自动消息或轮询调度。

当前实现为文档与轻量标准库校验工具，不增加 app 运行时依赖。没有代表用户声称三个 agent 已开工，也没有假装已完成真机验收。产品标准距离、玩法、恢复规则保持 DEVELOPMENT 的现有版本；本方案只重排交付粒度与责任。

后续接口变化留新的决策 ID；历史声明被撤回时保留原文件/提交与撤回依据，而不是删除失败证据。
