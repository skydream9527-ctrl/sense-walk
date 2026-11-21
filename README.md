# 慢行 · SenseWalk

一款节奏舒缓的角色操控游戏。先选场景，用虚拟摇杆带旅人沿路径前进。有效距离带来脚步声、环境音和景色变化，走满要求距离完成关卡。Android 另有户外实走模式。

- [当前进展与下一步](docs/CURRENT_STATUS.md) 汇总两端功能、验证结果、遗留任务与历史资料位置。
- [单 Agent 开发入口](AGENTS.md) 用于后续工程接手。
- [最新 Android 测试版](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-232-51a2b33) 提供森林 800 米双模式安装包。
- [产品规则](DEVELOPMENT.md) · [正式素材与授权](ASSETS.md) · [设计文档](design/README.md) · [历史协作档案](docs/collaboration/README.md)

## 构建

Android 工程位于 `app/`，使用 Kotlin 和 Jetpack Compose。[GitHub Actions](https://github.com/skydream9527-ctrl/sense-walk/actions/workflows/android.yml) 执行 JVM 单测、Lint 和 debug APK 构建，并提供源码归档与测试报告。本地构建说明见 [docs/BUILD.md](docs/BUILD.md)。iPadOS 原生工程列入下一阶段。
