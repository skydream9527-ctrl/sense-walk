# 慢行 · SenseWalk

帮助人**培养耐心、缓解压力**的 Android 应用：先选场景（雨林 / 森林 / 沙漠 / 城市等），再虚走或实走；**走满距离才能通关**，感官与景色层随路程渐渐解锁（从黑幕层层展开）。虚走摇杆教你找**舒适节奏**（拉满≠最快）；路径有起伏，角色随地形爬坡、跳跃。不可跳过、不可加速。

## 产品计划（推荐先看）

**[打开可视化计划页 →](./docs/plan.html)**（单文件 HTML，可双击离线打开，支持深/浅色）

完整 Markdown 方案见 [DEVELOPMENT.md](./DEVELOPMENT.md)（**v0.8**）：[当前代码进度](./DEVELOPMENT.md)、[分阶段交付与验收](./DEVELOPMENT.md#13-里程碑)、[完善与改进建议](./DEVELOPMENT.md#20-完善与改进v08)。产品规则保留 v0.7，进度以源码与验证记录为准。

**三 agent 协作入口**：见 [协作首页与任务看板](./docs/collaboration/README.md)。ZCode 负责功能/入包，MiniMax Code 负责候选素材，Antigravity 负责独立验收/集成；完整提示词与实际交付均通过文件 handoff 保存。后续只需让各工具读取 [ZCode](./docs/collaboration/roles/zcode.md)、[MiniMax](./docs/collaboration/roles/minimax.md)、[Antigravity](./docs/collaboration/roles/antigravity.md) 对应入口。

旧 [T01–T09 提示词](./docs/zcode-handoff.md) 保留作阶段参考，具体下一任务以协作登记为准。

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

## 当前状态（2026-10-13）

Kotlin + Jetpack Compose。**T01–T04 已完成**：云端打包与 CI；schema v2 配置契约（严格类型校验/加载态/重试）；纯 Kotlin 领域层（comfort_v1 保形曲线、s_pos/s_best 有效距离、门禁、相位调度、状态机，含 §5.7 地形速度系数）；**森林 800 m 虚走 UI 闭环**（模式选择、浮动摇杆、长按放弃、黑幕层层展开、后台不偷跑，仅森林虚走开放）。**T05 感官机制与收尾已完成**：步伐驱动脚步/淡入冻结/everyNSteps 振动 + SoundPool/MediaPlayer/Vibrator 真实引擎 + 音频焦点/耳机断连中断边界（暂停拒绝摇杆、恢复仅凭新输入、终态释放，可注入单测）；**森林真实音频素材已入库**（落叶脚步 ×6 + 虫鸣/远鸟循环，CC0/CC BY 授权可查，`REQUIRE_REAL_ASSETS` 发布策略放行，来源与处理记录见 ASSETS.md）；视觉真实图三层入包（outline/trunks/leaf_path）；light_shows 与 clearing 检出 32px 对角棋盘纹理，已程序降级待 MiniMax 重制（曾以 8px 统计误判 v4 五层合格并撤回，见 DEVELOPMENT §20.10 与 ASSETS.md）；旅人为程序绘制正式方案。模拟器 800 m 全程走查已通过（静默起点、80 m 脚步解锁、240/600 m 环境音、停走逐像素冻结、来电中断「已暂停」、通关即释放全部播放器）；**标准 800 m 真人手动验收与真机耳机/来电验证仍待执行，M1 不据此宣布完成**。**T06 森林实走已实现**：TYPE_STEP_COUNTER 唯一计距（首事件基线、1.4 m/s 封顶、暂停不补算）、health 前台服务（单一会话源、通知返回/停止）、权限与无传感器诚实回退虚走；真实计步与锁屏 15 分钟待真机验证。快照恢复与四景属后续阶段；HTML demo 是设计原型。

接下来按验收推进：M0 工程与 schema v2 → M1 森林 800 m 虚走闭环 → M2 实走、前台服务和恢复 → M3 四景内容与内测。GPS 辅助等放后续。具体任务及构建验证状态见开发计划。

## GitHub 云端打包

本地无需准备完整 Android 环境。代码提交后由 [GitHub Actions](https://github.com/skydream9527-ctrl/sense-walk/actions/workflows/android.yml) 执行测试/lint/构建，提供 APK、报告与源码交接 ZIP（Artifacts 保留 30 天）。

在 main 手动运行工作流并勾选 `publish_release`，检查通过后将 APK 与源码 ZIP 放到 [GitHub Releases](https://github.com/skydream9527-ctrl/sense-walk/releases)，供开发接手和用户测试。本轮核查的最新 Pre-release 为 [`build-37-8056e11`](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-37-8056e11)（含森林实走；217 项云端单测通过，真机/真人待验证；完整核查与 T06 补强任务见 [协作基线](./docs/collaboration/evidence/B-20261013-01/README.md)）。版本矩阵、本地构建步骤与已知网络问题见 [docs/BUILD.md](./docs/BUILD.md)。

## 打开工程（可选，本地开发时）

Android Studio 打开仓库根目录 · 包名 `com.sensewalk.app` · minSdk 26 · targetSdk 35

```
docs/plan.html          # 可视化计划 v0.8
DEVELOPMENT.md          # 方案源码真理
design/                 # PRD 级设计包（场景→角色→PRD→演示）
app/src/main/assets/scenes/
```
