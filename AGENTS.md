# SenseWalk 协作入口

本仓库由 ZCode、MiniMax Code、Antigravity 通过文件交接开发。用户直接指令优先。

1. 先读 `docs/collaboration/README.md` 和 `docs/collaboration/PROTOCOL.md`。
2. 按用户指定角色读取 `docs/collaboration/roles/zcode.md`、`minimax.md` 或 `antigravity.md`；从该入口查当前任务，禁止凭旧聊天猜进度。
3. 产品规则以 `DEVELOPMENT.md` 为准；任务状态以 `docs/collaboration/registry.json` 为准，`BOARD.md` 是生成视图。源码、提交与实际证据高于完成声明。
4. 三个 agent 使用独立 checkout/worktree 与任务分支。禁止多个 agent 同时操作同一 checkout 的 Git index、切分支或提交。共享 checkout 只读审阅；不能因抢文件而 reset/覆盖已有工作。
5. 功能代码/正式入包素材由 ZCode 接线；MiniMax 只交付候选；Antigravity 独立验收并集成。跨角色需求写入 handoff，不擅改别人拥有的文件。
6. 交付必须填写 JSON 元数据和 Markdown 报告，精确记录 base/head SHA、实际测试、素材哈希、待验证项。功能/素材作者不能自判 accepted；协调任务完成语义见协议。
7. 无需完善本地 Android 环境。复用 GitHub Actions；缺真机不阻塞独立开发，也不能伪造真实计步、锁屏或真人验收。
8. 用户已授权项目提交/推送及 GitHub 测试预发布；遵守分支保护，不强推，不提交密钥，不发布应用商店。
9. 当前协作文件系统的设计/维护属于本轮 bootstrap 工作，不代表三位执行 agent 已经接到消息或开始任务。
