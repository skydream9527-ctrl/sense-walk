# 慢行 · SenseWalk

帮助人找回感知与耐心的 Android 应用：先选场景（雨林 / 森林 / 沙漠 / 城市等），再虚走或实走；**走满距离才能通关**，感官层随路程渐渐解锁。不可跳过、不可加速。

## 产品计划（推荐先看）

**[打开可视化计划页 →](./docs/plan.html)**（单文件 HTML，可双击离线打开，支持深/浅色）

完整 Markdown 方案见 [DEVELOPMENT.md](./DEVELOPMENT.md)（**v0.4**：多场景声音身份 + 距离门禁 + 双模式）。

## 核心规则

- **先选场景**：各景有独立声音身份（脚步 / 环境 / 振动不同），解锁机制相同
- **双模式**：手机控角色（虚走）或户外实走（计步 / 可选 GPS）
- **距离门禁**：进度 = 有效距离；未满要求米数不能通关；长按 = 放弃
- 感官层随 **`atMeters`** 展开

## Week 1 骨架（当前代码）

Kotlin + Jetpack Compose：首页三景卡片、静默会话、设置、stub 音效/振动。  
计划下周：距离门禁、选景→选模式流程、补雨林/城市配置。详见计划页。

## 打开工程

Android Studio 打开仓库根目录 · 包名 `com.sensewalk.app` · minSdk 26 · targetSdk 35

```
docs/plan.html          # 可视化计划 v0.4
DEVELOPMENT.md          # 方案源码真理
app/src/main/assets/scenes/
```
