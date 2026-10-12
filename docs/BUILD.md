# 构建与环境说明（T01 · 2026-10-12）

> 交付模式（用户确认）：**编译、测试、lint 和 APK 打包全部在 GitHub Actions 上执行**；本地只需能编辑/提交源码，不要求安装完整 Android 开发环境。本文同时记录云端与本地两条路径，便于任何人在干净环境复现。

## 工具链版本矩阵（实测核查）

| 项 | 版本 | 说明 |
| --- | --- | --- |
| Gradle Wrapper | 8.9 | 仓库自带，CI 与本地统一使用 `./gradlew` |
| Android Gradle Plugin | 8.7.3 | 要求 Gradle ≥ 8.9、JDK ≥ 17，当前组合兼容 |
| Kotlin | 2.0.21 | 含 `kotlin.plugin.compose` |
| JVM 目标 | 17 | `sourceCompatibility`/`jvmTarget` 均为 17；CI 用 Temurin JDK 17 运行 |
| compileSdk / targetSdk | 35 / 35 | CI 由 sdkmanager 安装 `platforms;android-35` + `build-tools;35.0.0` |
| minSdk | 26 | — |
| Compose BOM | 2024.10.01 | Navigation 2.8.4 · DataStore 1.1.1 · lifecycle 2.8.7 |
| CI Runner | ubuntu-24.04 | JDK: `actions/setup-java` Temurin 17 |

**升级原则**（沿用 T01 约束）：先定位具体失败再修复，不做与阶段无关的批量升降级；lint 的 `GradleDependency`/`OldTargetApi` 警告因此保留观察。

## 路径 A：云端构建（推荐，当前唯一打包入口）

工作流：`.github/workflows/android.yml`（无需本地环境）。

1. 推送到 `main`（或对 `main` 发 PR）自动触发；也可在 Actions 页手动 `workflow_dispatch`。
2. 执行内容：`./gradlew :app:testDebugUnitTest :app:lintDebug :app:assembleDebug --no-daemon`。
3. 产物（按 commit SHA 命名，保留 30 天）：
   - `sensewalk-apk-<sha>` — 可安装 debug APK（约 16.9 MB）
   - `sensewalk-reports-<sha>` — lint 报告与测试结果
   - `sensewalk-source-<sha>` — 完整源码交接 ZIP
4. 需要稳定下载链接时：手动触发并勾选 `publish_release`，在 main 生成 GitHub 预发布（如 `build-4-f8e606b`）。无签名发布流程。

验证基线（2026-10-12，run 38223104937 / commit f8e606b）：构建全绿，lint 0 errors / 20 warnings（均为信息级）。`testDebugUnitTest` 暂无测试源，为空集通过——**不构成行为覆盖**，真实测试自 T02/T03 起。

## 路径 B：本地构建（可选，按需）

前置：

1. **JDK 17+**（17 或 21 均可；本机实测 Temurin 21 可编译 JVM 17 目标）。
2. **Android SDK**，含 platform 35 与 build-tools 35.0.0。Android Studio 默认路径（macOS `~/Library/Android/sdk`）会被自动探测；其他位置在仓库根新建 `local.properties`（**已被 .gitignore 排除，绝不提交**）：

   ```properties
   sdk.dir=/你的/SDK/路径
   ```

3. 首次运行会下载 Gradle 8.9 分发包（约 136 MB）与全部依赖。

命令：

```bash
./gradlew :app:assembleDebug          # 产物 app/build/outputs/apk/debug/app-debug.apk
./gradlew :app:lintDebug              # 报告 app/build/reports/
./gradlew :app:testDebugUnitTest      # T02/T03 起有实际测试
```

### 已知网络问题（2026-10-12 本机实测）

- 本机网络经 **Java HTTPS** 下载 `services.gradle.org` 分发包可能反复 SSL 中断（`SSL peer shut down incorrectly`；DEVELOPMENT.md §20.4 与 §20.5 均有记录）。这是**下载层网络问题，不是编译失败**。
- 规避：用 curl 断点续传把分发包放到 wrapper 期望的位置后再正常使用 `./gradlew`：

  ```bash
  DIST=~/.gradle/wrapper/dists/gradle-8.9-bin/90cnw93cvbtalezasaz0blq0a
  curl -L -C - --retry 8 -o "$DIST/gradle-8.9-bin.zip" \
    https://services.gradle.org/distributions/gradle-8.9-bin.zip
  unzip -q "$DIST/gradle-8.9-bin.zip" -d "$DIST" && touch "$DIST/gradle-8.9-bin.zip.ok"
  ```

- 结论：日常开发**优先路径 A**；本地仅在需要调试构建细节时按需启用。

## Kotlin 注释规范（本次事故教训）

Kotlin 块注释**支持嵌套**：注释文本中出现 `/*`（如 glob 写法 `scenes/*.json`）会被视为新嵌套注释起点，单个 `*/` 无法闭合外层，导致整个文件被吞（CI 首跑 66 个级联错误的根因，修复见 f8e606b）。注释里避免出现 `/*` 序列；路径示例写 `assets/scenes` 而不是 `assets/scenes/*.json`。
