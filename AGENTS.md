# SenseWalk 单 Agent 开发入口

1. 开始前同步 GitHub 的 `main`，读取 [当前进展](docs/CURRENT_STATUS.md)、[产品规则](DEVELOPMENT.md) 和 [素材清单](ASSETS.md)。以源码、准确提交及实际测试证据确认进度。
2. 一个 Agent 按当前进展中的优先级顺序负责实现、素材接入、测试、文档和交付。日常以 `main` 和一个 checkout 为基线。需要 PR 时使用短期 `codex/<task>` 分支，合入后回到 `main`。
3. 产品核心是触屏控制旅人。保留选景、舒适摇杆曲线、800 米森林门禁、有效前进计距、按距离展开心境与声景、暂停恢复及 Android 实走。规格以 `DEVELOPMENT.md` 为准。
4. 每批交付更新 [当前进展](docs/CURRENT_STATUS.md)，记录基线与交付 SHA、改动、实际命令、测试结果、构建链接及待验证项。素材入包记录来源、授权和 SHA-256。区分源码检查、单测、构建、模拟器、真机及真人证据。
5. Android 优先复用 GitHub Actions。每次业务改动验证相应单测、Lint 和构建。真机、锁屏、计步、触感和真人验证缺证据时标待验证。GitHub 测试预发布沿用现有授权，按分支保护合入。
6. [历史协作档案](docs/collaboration/README.md) 保留既有任务、验收结论与可追溯证据。历史记录保持原始字节，需要更正时追加记录。仍可运行 `python3 tools/collaboration.py check` 验证档案。
7. 正式素材进入 `app/src/main/assets/` 前按场景规格验图、验声和核对授权。可重建的构建产物、大型生成样本和本地验证包放在忽略目录或 GitHub 测试工件中。将凭据与正式签名配置留在授权的私密环境。
