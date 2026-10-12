# 慢行 · SenseWalk

帮助人找回感知与耐心的 Android 应用：从静默开始，再逐步加入脚步声、虫鸣与振动。场景包括森林漫步、沙漠独行、夜径，操作极简。

完整开发方案见 [DEVELOPMENT.md](./DEVELOPMENT.md)。

## Week 1 骨架（当前）

Kotlin + Jetpack Compose 单模块工程，可在 Android Studio 中打开并运行：

- **首页**：三张场景卡片（森林漫步 / 沙漠独行 / 夜径）→ 点选 →「开始」
- **会话**：近黑沉浸；纯静默计时；轻触显示/隐藏已用时间；**长按 1 秒**结束
- **结束页**：一句「你安静地走了 X 分钟」+「再走一次」/「回首页」
- **设置**：静默秒数（默认 60）、振动总开关（DataStore）；音效/振动引擎为 stub，静默会话可独立跑通
- **场景配置**：`app/src/main/assets/scenes/*.json`（与 DEVELOPMENT.md schema 一致）

## 在 Android Studio 中打开

1. 安装 [Android Studio](https://developer.android.com/studio)（建议 Ladybug / 2024.2+ 或更新），并安装 SDK 35 与对应 Build-Tools。
2. **File → Open**，选择本仓库根目录（含 `settings.gradle.kts` 的文件夹）。
3. 仓库已包含 `gradlew` 与 `gradle/wrapper`（Gradle 8.9）。首次打开请让 Android Studio 完成 Gradle Sync。
4. 等待 Gradle Sync 完成，选择模拟器或真机，点击 Run。

**包名**：`com.sensewalk.app`  
**显示名**：慢行  
**minSdk 26** · **target/compileSdk 35** · Compose BOM `2024.10.01`

## 工程结构（摘要）

```
app/src/main/
  java/com/sensewalk/app/
    MainActivity.kt
    SenseWalkApp.kt / SenseWalkViewModel.kt
    ui/home|session|settings|theme|navigation/
    domain/scene|audio|haptics/
    data/SceneRepository.kt / SettingsRepository.kt
  assets/scenes/{forest,desert,night_path}.json
  res/…
```

## 后续周次

见 DEVELOPMENT.md：Week 2 声音层、Week 3 环境音+振动、Week 4 打磨发布。
