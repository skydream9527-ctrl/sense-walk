# SW-024 · 基线缺陷分级表、测试依赖转交与分批发布验收清单

本文件汇总 `build-176-aaa789b`（源码基线 `321060e945b512f3f6b8b038543eb3b9d16a58bc`）独立核查确认的问题分级、责任归属、证据路径，以及第一批/第二批测试包的严格发布门槛。

---

## 1. 基线问题与改进项分级表（含 Owner / 严重度 / 复现 Build / 证据）

| 编号 | 问题描述与触发位置 | 严重度 | Owner | 复现 Build / SHA | 证据路径 | 对应任务与当前状态 |
| --- | --- | --- | --- | --- | --- | --- |
| **D-SW024-01** | `ForestShell.kt:73-81` 在组合期 `remember` 同步执行 `BitmapFactory.decodeStream` 解码 5 层 WebP；`RealWalkContent.kt:39` 使用 `runBlocking` 同步等待配置加载；`SessionScreen.kt:90` 顶层读取高频 `walk` 状态 | **P1（性能/主线程阻塞风险）** | `zcode` | `build-176-aaa789b` / `321060e` | [performance-benchmark-protocol.md](performance-benchmark-protocol.md)、[SOURCE-REVIEW.md](../../plans/2026-10-20/SOURCE-REVIEW.md) | `SW-019`（`ready`） |
| **D-SW024-02** | `MainActivity.kt` 已开启 `enableEdgeToEdge()`，但 `SessionScreen.kt:293,322,356`、`RealWalkContent.kt:142,174,198`、`ResultScreen.kt:59` 使用硬编码 `64.dp`/`48.dp` 代替 `systemBars`/`displayCutout` 安全区（如 `H2-hint-appear.png` 右上角「长按放弃」胶囊贴边） | **P1（UI 安全区/遮挡风险）** | `zcode` | `build-176-aaa789b` / `321060e` | [H2-hint-appear.png](../H-SW-018-R1/screens/H2-hint-appear.png)、[SOURCE-REVIEW.md](../../plans/2026-10-20/SOURCE-REVIEW.md) | `SW-020`（`queued`，等 `SW-019`） |
| **D-SW024-03** | `UserSettings` / `SettingsRepository.kt` 未持久化 `strideMeters`（默认 `0.70m`，范围 `0.45–0.95m`），`WalkForegroundService.kt:184` 创建 `RealWalkController` 未传入用户设置步长；`SettingsScreen.kt:36,78` 仍残留「真实振动引擎将在下一版接入」过期文案；摇杆首次进入舒适区/紧张区缺每局一次性极轻触感 | **P1（规格缺口/文案过期）** | `zcode` | `build-176-aaa789b` / `321060e` | [SOURCE-REVIEW.md](../../plans/2026-10-20/SOURCE-REVIEW.md) | `SW-020`（`queued`，等 `SW-019`） |
| **D-SW024-04** | `app/build.gradle.kts:15-16` 固定 `versionCode = 1`、`versionName = "0.1.0-week1"`，App 内设置/关于页无法查看构建号与源码短 SHA，多轮测试包只能靠外部文件名区分；且 debug 随机签名导致覆盖安装冲突需明确提示 | **P1（测试构建可追溯性）** | `zcode` | `build-176-aaa789b` / `321060e` | [KNOWN-ISSUES.md](../../../releases/2026-10-18-forest-beta/KNOWN-ISSUES.md)、[signing-stability-proposal.md](../H-SW-018-R1/signing-stability-proposal.md) | `SW-025`（`queued`，等 `SW-020`） |
| **D-SW024-05** | `H-SW-018-R1` 中 `H2-hint-appear.png` 实看未见「慢一点，站稳再跳。」文字卡片（中央高亮像素 `0`），且两张 H2 图旅人实际处于 `Gait.HOP`（`y_max = 2050/2049 = 2076 - 26`）而非 `Gait.TENSE` 微蹲；系 `uiautomator dump` 阻塞导致截屏晚于 `3.0s` 提示窗口 | **P2（运行证据缺口，非代码阻断）** | `antigravity` / `zcode` | `build-176-aaa789b` / `321060e` | [R-SW-018-R1-correction.md](../../reviews/R-SW-018-R1-correction.md)、[h2-pixel-audit.json](h2-pixel-audit.json) | `SW-024` 已追加勘误并保留同步画面 `Pending` |
| **D-SW024-06** | 森林现有 5 层 `768×1376` 单图非无缝（`tileable=false`）：在 `1080×2400` 下横向溢出约 `259px`，远/中层约 `144m`、叶层约 `72m` 视差钳满；且 `tree_outline`/`tree_trunks`/`leaf_path` 右缘存在 30 列全透明切边（`1080×2400` 露 `52px` 黑带）；`1080×1920` 下按高缩放宽仅 `1072px`（`overflow = 0`） | **P2（视觉体验精修）** | `trae-design` → `minimax` → `zcode` | `build-176-aaa789b` / `321060e` | [R-SW-017-R1.md](../../reviews/R-SW-017-R1.md)、[h2-pixel-audit.json](h2-pixel-audit.json) | `SW-021` → `SW-022` → `SW-023`（**不阻塞第一批测试包**） |
| **D-SW024-07** | `ModeScreen.kt:192` 的 `ModeCard` 硬编码 `sceneTint("forest")`；首页未展示 `scene.mood`；完成终态直接跳结果页（缺 `DEVELOPMENT.md` §11.2 规定的最终景色 `≥ 3s` 退暗过渡）；缺关于页 `ASSETS.md` 音频来源署名 | **P2（界面与收尾精修）** | `trae-design` → `zcode` | `build-176-aaa789b` / `321060e` | [SOURCE-REVIEW.md](../../plans/2026-10-20/SOURCE-REVIEW.md) | `SW-021` → `SW-023`（第二批） |
| **D-SW024-08** | `app/build.gradle.kts` 仅声明 `androidTestImplementation(composeBom)` 与 `debugImplementation("androidx.compose.ui:ui-test-manifest")`，尚未声明 `androidTestImplementation("junit:junit:4.13.2")`、`androidx.test:runner`、`androidx.compose.ui:ui-test-junit4`，导致标准 `@Test` / `ComposeTestRule` 仪器测试尚缺依赖 | **P3（测试工程配置缺口）** | `zcode`（Gradle 归属） | `321060e` | [SenseWalkRegressionInstrumentationTest.kt](../../../../app/src/androidTest/java/com/sensewalk/app/qa/SenseWalkRegressionInstrumentationTest.kt) | QA 严守单写边界不改 `app/build.gradle.kts`，已用零额外依赖入口落地 `androidTest`，依赖补齐建议交 `zcode` |
| **D-SW024-09** | `SW-006` R1（PR #25）仍为 0 API 程序化 PIL 占位草案（`125KB`），且 `preflight.py` 需补齐生产尺寸与总预算硬门禁 | **P2（雨林候选返工，隔离于森林包）** | `minimax` | `PR #25 (8e73b13)` | [R-SW-006-R1-correction.md](../../reviews/R-SW-006-R1-correction.md) | `SW-006`（`rework`，不阻塞森林第一/二批发布） |

---

## 2. 给 ZCode 的测试构建配置缺口转交说明（QA 不越权改业务 Gradle）

在 `SW-024` 落地 `app/src/androidTest/java/com/sensewalk/app/qa/SenseWalkRegressionInstrumentationTest.kt` 时，核查 `app/build.gradle.kts` 发现：
- 目前仅配置了 `androidTestImplementation(composeBom)`（第 53 行）和 `debugImplementation("androidx.compose.ui:ui-test-manifest")`（第 73 行）；
- `junit:junit:4.13.2` 仅在 `testImplementation`（第 75 行），未加入 `androidTestImplementation`，且未引入 `androidx.compose.ui:ui-test-junit4` 与 `androidx.test.ext:junit`。
- **QA 处置**: 遵守 `PROTOCOL.md` 单写边界，Antigravity **不修改** `app/build.gradle.kts`，已在 `app/src/androidTest/` 中采用当前 `implementation` 类路径已有的领域/数据组件编写零额外依赖可编译回归入口（并通过 `:app:lintDebug` 与 `:app:assembleDebug` 验证）。若后续需在设备/模拟器运行 `ComposeTestRule` 节点级仪器测试，由 ZCode 在所属任务中按需补充 `androidTestImplementation` 依赖。

---

## 3. 两批测试包发布验收清单（Release Gate Checklist）

### 3.1 第一批测试包（性能、安全区、步长、触感与可追溯版本 —— 不等平铺素材）

| 序号 | 门禁项 | 验收标准 | 当前状态 |
| --- | --- | --- | --- |
| 1 | **前置任务独立批准与合入** | `SW-019`、`SW-020`、`SW-025` 依次提交准确业务 `head_commit`，经 Antigravity 独立审查 `approved` 并合入 `main` | `Pending`（等待 `SW-019` 交付） |
| 2 | **云端 CI 全绿** | 合入后的 `main` 通过 `:app:testDebugUnitTest`、`:app:lintDebug`、`:app:assembleDebug`、`processReleaseMainManifest`（无 `DebugStepReceiver`）及 `collaboration.yml` | `Pending` |
| 3 | **核心产品不变量回归** | `0m` 纯黑幕起点、五层原解锁米数（`80/240/400/600/760m`）与透明度、未解锁层异步就绪不提前绘制、点击显距、暂停确认期间不计距、恢复需新输入、单次终态导航、`237m` 首坎站稳 `1.2s` 零位移、旧快照兼容（缺省 `0.70m` 步长）全部通过 | `Pending` |
| 4 | **构建身份与产物核验** | 新 Release tag（不覆盖 `build-176-aaa789b`），核实并记录 `app-debug.apk` 与 `source.zip` 的字节数、SHA256、`versionName`、单调递增 `versionCode`（`> 1`）、源码短 SHA、签名证书指纹，以及覆盖安装冲突提示 | `Pending` |
| 5 | **诚实边界声明** | 无同环境实测前后性能数值时不宣称帧率/省电提升百分比；真机计步、锁屏 15 分钟、耳机/来电、物理重启与真人体验继续标注 `Pending` | **强制执行** |

### 3.2 第二批测试包（森林连续视差与界面精修 —— 视觉链完成后发布）

| 序号 | 门禁项 | 验收标准 | 当前状态 |
| --- | --- | --- | --- |
| 1 | **视觉与设计链依次获批** | `SW-021`（Trae 设计 + 全部 manifest 文件哈希）→ `SW-022`（MiniMax 0-API 三层候选 + `design_ref` 指向 `SW-021` + 接缝/三底/偏移/五层总预算 `≤ 2MB`）→ `SW-023`（ZCode 入包与 UI 精修）依次独立 `approved` 并合入 `main` | `Pending`（等待 `SW-021` 交付） |
| 2 | **渲染与界面验收** | 明确区分 `cover` 与 `horizontal tile`；旧配置缺省兼容 `cover`；`800m` 末段仍有视差位移且松手停稳像素冻结；旅人跨密度可辨识；`themeColor` 仅作强调色保留 `ScenePalette`；完成时先触发唯一终态释放音振再 `≥ 3s` 退暗（`reduceMotion` 静态替代）；关于页展示 `ASSETS.md` 真实来源与许可 | `Pending` |
| 3 | **第二批独立 Tag 与产物核验** | 发布新 tag（`versionCode` 再次递增），完整记录 APK/source SHA256、证书指纹、实际 Android 画面证据与 `Pending` 项 | `Pending` |
