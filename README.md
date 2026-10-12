# 慢行 · SenseWalk

帮助人**培养耐心、缓解压力**的 Android 应用：先选场景（雨林 / 森林 / 沙漠 / 城市等），再虚走或实走；**走满距离才能通关**，感官与景色层随路程渐渐解锁（从黑幕层层展开）。虚走摇杆教你找**舒适节奏**（拉满≠最快）；路径有起伏，角色随地形爬坡、跳跃。不可跳过、不可加速。

## 产品计划（推荐先看）

**[打开可视化计划页 →](./docs/plan.html)**（单文件 HTML，可双击离线打开，支持深/浅色）

完整 Markdown 方案见 [DEVELOPMENT.md](./DEVELOPMENT.md)（**v0.8**）：[当前代码进度](./DEVELOPMENT.md#0-当前进度仓库核查2026-10-12)、[分阶段交付与验收](./DEVELOPMENT.md#13-里程碑)、[完善与改进建议](./DEVELOPMENT.md#20-完善与改进v08)。产品规则保留 v0.7，进度以源码与验证记录为准。

**交给 ZCode 开发**：见 [开发任务与可复制提示词](./docs/zcode-handoff.md)（总提示词 + T01–T09 分阶段提示词 + 验收清单）。

**完整设计包（PRD 级）**见 [`design/`](./design/)：场景与地形 → 角色 → PRD → [交互演示](./design/04-interaction-mockups/demo/index.html)。阅读顺序以 `design/README.md` 为准。


## 核心规则

- **耐心与减压**：用慢感官行走练习放松，而非刷关或冲刺
- **先选场景**：各景有独立声音与景色身份；解锁机制相同（距离门禁）
- **舒适节奏摇杆**（虚走）：中段偏转 ≈ 舒适步速；拉满变钝/变慢，教你别急
- **地形联动**：路径非平地；爬坡、跳跃等动作贴合场景；仅有效前进计距
- **景色层层展开**：关卡内从黑幕起，按路程逐步丰富该场景风景
- **双模式**：手机控角色（虚走）或户外实走（计步 / 可选 GPS）
- **距离门禁**：进度 = 有效距离；未满要求米数不能通关；长按 = 放弃
- 感官与视觉层随 **`atMeters`** 展开；耳目同程、不可加速揭示

## 当前状态（2026-10-12）

Kotlin + Jetpack Compose：森林/沙漠/夜径卡片、静默计时会话、设置和音效/振动 stub 已有源码。**T02 已完成**：场景配置迁移到 schema v2（距离相位 + pathProfile + 显式开发占位）、解析与 SceneValidator 校验、可观察加载状态（错误可诊断可重试）、时长按距离推导，53 个 JVM 单测在 CI 执行。距离门禁、模式选择、摇杆、计步、分层景色渲染和真实音频仍待实现；HTML demo 是设计原型。

接下来按验收推进：M0 工程与 schema v2 → M1 森林 800 m 虚走闭环 → M2 实走、前台服务和恢复 → M3 四景内容与内测。GPS 辅助等放后续。具体任务及构建验证状态见开发计划。

## GitHub 云端打包

本地无需准备完整 Android 环境。代码提交后由 [GitHub Actions](https://github.com/skydream9527-ctrl/sense-walk/actions/workflows/android.yml) 执行测试/lint/构建，提供 APK、报告与源码交接 ZIP（Artifacts 保留 30 天）。

在 main 手动运行工作流并勾选 `publish_release`，检查通过后将 APK 与源码 ZIP 放到 [GitHub Releases](https://github.com/skydream9527-ctrl/sense-walk/releases)，供 ZCode 接手和用户测试。当前 APK 仍为 Week 1 骨架，后续按 T02–T09 开发。版本矩阵、本地构建步骤与已知网络问题见 [docs/BUILD.md](./docs/BUILD.md)。

## 打开工程（可选，本地开发时）

Android Studio 打开仓库根目录 · 包名 `com.sensewalk.app` · minSdk 26 · targetSdk 35

```
docs/plan.html          # 可视化计划 v0.8
DEVELOPMENT.md          # 方案源码真理
design/                 # PRD 级设计包（场景→角色→PRD→演示）
app/src/main/assets/scenes/
```
