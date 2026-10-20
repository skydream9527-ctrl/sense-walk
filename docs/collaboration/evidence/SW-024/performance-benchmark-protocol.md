# SW-024 · 同环境性能基准与前后比较协议

本协议固定 `SW-019`（会话渲染与异步加载）及后续批次的前后性能对照规则，杜绝不同设备、不同构建类型或无基线数据的主观「流畅/60fps/节电」宣告。

---

## 1. 参照基线（Frozen Reference）

| 参照维度 | 固定值 | 说明 |
| --- | --- | --- |
| **安装测试包参照** | [build-176-aaa789b](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-176-aaa789b) | APK SHA256 `cbe827bfff555939871e94e0b785bd89ac2780275d8a1c5fe81320fdc3c40a67`（冻结源码 `aaa789b3afd789d121eb6f0c96189fe9835d3e3c`） |
| **主干源码参照** | `321060e945b512f3f6b8b038543eb3b9d16a58bc`（规划合入后 `4f57659e00e0267be03a0a7b966cacba8387c5ee`） | 与 `aaa789b` 之间 `app/` 生产源码零改动 |
| **构建类型约束** | `debug` 对 `debug`，或 `release` 对 `release` | **严禁混比** `debug` 与 `release` 数据，严禁跨设备/跨模拟器 AVD 混比 |

---

## 2. 固定环境与启动条件

每次采集前后对照数据时，必须在报告中完整记录以下环境字段：

1. **硬件/模拟器身份**: 设备型号或 AVD 名称（如 `api36_test` / 真机型号）、CPU 架构（`arm64-v8a`）、Android API 级别与系统版本、屏幕物理分辨率（如 `1080×2400` / `1080×1920`）、density（`dpi`）与刷新率（`60Hz` / `120Hz`）。
2. **构建身份**: `versionName`、`versionCode`、构建类型（`debug`）、源码 Git SHA、APK SHA256。
3. **冷启动（Cold Start）定义**:
   - 执行 `adb shell am force-stop com.sensewalk.app`；
   - 首次进入森林会话前清除内存缓存，记录从点按「开始」到首帧 `SessionContent` / `RealWalkContent` 可交互且五层位图就绪的耗时。
4. **热启动/二次入场（Warm Re-entry）定义**:
   - 同一进程内从会话返回首页后再次进入森林会话，验证进程级配置缓存与图层位图缓存命中行为，以及切换 `sceneId` 时不串图、不越界增长。

---

## 3. 同一行走脚本与阶段采样点

前后比较必须使用相同的距离推进序列与操作点（虚走统一使用甜点偏转 `deflection = 0.55` 推进，越坎测试段使用 `deflection = 0.90`）：

| 阶段点 | 米数 / 条件 | 必测观察项 |
| --- | --- | --- |
| **S0 入场与起点** | `0 m`（冷/热入场） | 组合期主线程阻塞时长、位图解码线程归属、`0m` 纯黑幕（`void = 1.0`，未解锁层即使异步解码完成也不提前绘制） |
| **S1 首层轮廓淡入** | `80 m → 100 m` | `tree_outline` 解锁与视差滑动、脚步声触发期间帧时间 |
| **S2 上坡与首坎站稳/轻跳** | `235 m → 242 m → 265 m` | `237m` 紧张输入触发 `STABILIZE`（`1.2s` 位移归零 + 提示卡片）→ `HOP` 越坎 → `240m` `tree_trunks` 淡入 |
| **S3 中段林间路径** | `400 m → 425 m` | `leaf_path` 解锁 + 脚步软触感触发期帧稳定性 |
| **S4 深林光柱** | `600 m → 630 m` | `light_shows` 叠加层淡入 + 四层同屏合成耗时 |
| **S5 林间空地与末段** | `760 m → 785 m → 800 m` | 五层全开合成、末段视差位移（第一批 cover 钳满现状 vs 第二批 tile 连续位移）、`800m` 唯一终态触发 |
| **S6 松手停稳与暂停恢复** | `31 m` 松手停稳 `5s` + 暂停弹窗 `5s` | 停稳后（`velocity == 0`）与暂停期间 `onFrame` 快照去重、UI 零多余重组、不偷跑米数 |

---

## 4. 基线实测事实（源码级已核）与运行时待采集项（Pending）

### 4.1 基线 `321060e` 已核实的静态/源码基准事实（Passed - Source Audit）

| 指标项 | 基线 `321060e` 现状与精确位置 | 目标改进方向（SW-019） |
| --- | --- | --- |
| **图层位图解码路径** | `ForestShell.kt:73-81` 在 `remember(imageLayers)` 组合期同步调用 `BitmapFactory.decodeStream` 解码 5 张 `768×1376` WebP（未缩放 `RGBA_8888` 理论像素缓冲 `5 × 768 × 1376 × 4 = 21,135,360 B ≈ 20.16 MiB`，磁盘文件合计 `88,974 B`） | 移出组合期同步路径，后台协程按目标尺寸采样解码 + 有限容量缓存 + 失败安全回退程序层 |
| **实走配置加载等待** | `RealWalkContent.kt:39` 在 `remember(sceneId)` 组合期调用 `kotlinx.coroutines.runBlocking { SceneRepository(context).loadAll() }` 阻塞 UI 线程等待 IO | 消除 `runBlocking`，复用已加载配置或轻量进程级异步缓存，保留错误态与显式重试 |
| **高频状态读取作用域** | `SessionScreen.kt:90` 与 `RealWalkSessionScreen.kt:192` 在顶层收集每帧更新的 `walk` 快照并向下传参；顶部米数文字（仅 `showMeters` 时需整数米）与操作区跟随意念重绘作用域偏大 | 下沉高频 `walk`/`sensory` 读取至绘制消费处，顶部整数米数按需衍生消费，不降低 `withFrameNanos` 采样精度 |

### 4.2 运行时设备/模拟器可观察指标（当前无同环境对比运行数据，诚实记 `Pending`）

| 采集项 | 标准采集命令 / 方法 | 基线 `build-176-aaa789b` 数值 | SW-019 候选数值 | 当前状态 |
| --- | --- | --- | --- | --- |
| **帧时间分布（P50 / P90 / P95 / P99 / Janky%）** | `adb shell dumpsys gfxinfo com.sensewalk.app reset` → 执行 S0–S6 脚本 → `adb shell dumpsys gfxinfo com.sensewalk.app framestats` | `Pending`（待与候选同机同轮采集） | `Pending` | **`Pending`** |
| **冷/热入场首帧与位图解码耗时（ms）** | 计时点或 `Logcat` / Trace 记录 5 层解码总耗时与主线程阻塞时长 | `Pending` | `Pending` | **`Pending`** |
| **进程内存占用（PSS / Graphics / Native Heap）** | `adb shell dumpsys meminfo com.sensewalk.app`（S0 入场前、S5 五层全开、二次重入后） | `Pending` | `Pending` | **`Pending`** |
| **可观察重组计数（SessionContent / TopBar / Joystick）** | Compose Layout Inspector 或测试计数器在 S1 行走 10s（~600 帧）内的重组次数 | `Pending` | `Pending` | **`Pending`** |

> **严格门禁约定**：在未采集同环境运行前/后实测数值前，审核报告与发布说明只能表述为「已完成后台异步解码、消除 `runBlocking` 与高频状态读取下沉改造」，**严禁宣称具体帧率提升百分比、零分配或省电百分比**。
