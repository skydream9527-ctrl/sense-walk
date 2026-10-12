# 慢行 · SenseWalk

帮助人找回感知与耐心的 Android 应用：**走满关卡距离才能通关**——手机里控角色走，或户外真的走。路上感官由静默逐渐回到脚步、环境音与振动。不可跳过、不可加速、不可提前通关。

## 产品计划（推荐先看）

**[打开可视化计划页 →](./docs/plan.html)**（单文件 HTML，可双击离线打开，支持深/浅色）

完整 Markdown 方案见 [DEVELOPMENT.md](./DEVELOPMENT.md)（**v0.3**：距离门禁 + 双模式行走）。

## 核心规则（v0.3）

- **双模式**：手机控角色（虚走）或户外实走（计步 / 可选 GPS）
- **距离门禁**：进度 = 有效距离；未满要求米数不能通关
- **长按 = 放弃**（不通关），不是「提前完成」
- 感官层随 **路程**（`atMeters`）展开，不是用时间刷完

## Week 1 骨架（当前代码）

Kotlin + Jetpack Compose 单模块工程，可在 Android Studio 中打开并运行：

- **首页**：三张场景卡片 →「开始」
- **会话**：近黑沉浸；纯静默计时；轻触显隐时间；长按结束（**计划将改为「放弃」**）
- **结束页 / 设置 / 场景 JSON**：见仓库；音效与振动为 stub

> 下一周（计划）：距离引擎、虚走、CompletionGate。音频仍延后到 Week 3。详见计划页。

## 在 Android Studio 中打开

1. 安装 [Android Studio](https://developer.android.com/studio)（建议 Ladybug / 2024.2+），安装 SDK 35。
2. **File → Open** 本仓库根目录（含 `settings.gradle.kts`）。
3. Gradle Sync 后选模拟器或真机 Run。

**包名**：`com.sensewalk.app` · **显示名**：慢行 · **minSdk 26** · **targetSdk 35**

## 工程结构（摘要）

```
app/src/main/java/com/sensewalk/app/   # Week 1 骨架
app/src/main/assets/scenes/            # forest / desert / night_path
docs/plan.html                         # 可视化计划 v0.3
docs/plan-preview.png
DEVELOPMENT.md                         # 方案源码真理
```

## 后续周次

见 [docs/plan.html](./docs/plan.html)：Week 2 距离门禁 + 虚走 → Week 3 实走 + 音频/振动 → Week 4 打磨发布。
