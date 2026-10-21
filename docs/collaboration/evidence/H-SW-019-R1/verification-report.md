# SW-019 R1 验证报告（zcode）

- 任务：SW-019 会话渲染与异步加载
- base：`4f57659e00e0267be03a0a7b966cacba8387c5ee`（origin/main，PR #32 合并点）
- 业务 head：`a666b76793a77039df9e435d7877bb6fd55a4aec`
- 业务提交：
  - `2f46993` feat(render): SW-019 会话渲染与异步加载
  - `a666b76` fix(render): SW-019 single-flight 只加入仍活跃的加载
- PR：https://github.com/skydream9527-ctrl/sense-walk/pull/36
- 本地环境：macOS arm64，ANDROID_HOME=/opt/homebrew/share/android-commandlinetools，JDK 21（CI 为 JDK 17）
- 模拟器：AVD api36_test（Pixel 6 / API 36 / arm64，serial emulator-5554，GPU=emulation，无 TYPE_STEP_COUNTER、无振动 HAL）

## 一、变更范围（13 个文件）

| 变更 | 文件 |
| --- | --- |
| 新增 | `data/SceneCatalogCache.kt`（纯 Kotlin 单值缓存：single-flight/失败不缓存/可 reload） |
| 新增 | `data/SceneCatalog.kt`（Android 端单例：SupervisorJob+Default 作用域接 SceneRepository） |
| 新增 | `ui/session/LayerImageCache.kt`（图层通用 LRU 字节预算缓存 + `layerSampleSize` 两段采样） |
| 新增 | `ui/session/ForestLayerImages.kt`（32MiB 预算 bounds 缓存 + inSampleSize 解码，IO 线程） |
| 修改 | `ui/session/ForestShell.kt`（图层位图异步装载；快照与位图读取全部下沉到 draw lambda） |
| 修改 | `ui/session/SessionScreen.kt`（`State<Snapshot?>` 直传 + `derivedStateOf` 降频；`MetersReadout` 仅显示时订阅整数米） |
| 修改 | `ui/session/RealWalkContent.kt`（删除 RealWalkVisualCache；场景配置异步装载） |
| 修改 | `ui/session/RealWalkSessionScreen.kt`（同上快照模式） |
| 修改 | `session/SessionViewModel.kt`、`SenseWalkViewModel.kt`、`service/WalkForegroundService.kt`（入口预热/重试走 `SceneCatalog.reload`） |
| 新增测试 | `SceneCatalogCacheTest.kt`（6 例）、`LayerImageCacheTest.kt`（11 例，含 3 万轮竞态回归锁） |

domain/ 包保持零协程依赖（缓存类落在 data/ 与 ui/session/）。`drainPhaseEvents` 已是 swap-not-clear 语义，未做未度量的 Path/Brush 池化（按任务书"不做没有度量的池化"）。

## 二、本地 JVM 验证

命令（worktree 根目录）：

```
ANDROID_HOME=/opt/homebrew/share/android-commandlinetools ./gradlew :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
```

结果：

- `testDebugUnitTest`：**329 通过 / 0 失败 / 0 跳过**（base 为 312，新增 17：SceneCatalogCacheTest 6 + LayerImageCacheTest 11）
- `lintDebug`：0 错误 / 23 警告（均为既有类别；`ForestShell` 的 ModifierParameter 警告随签名调整消除，较主干 −1）
- `assembleDebug`：成功
- release 无调试接收器门禁（既有测试）通过

## 三、CI（GitHub Actions，.github/workflows/android.yml）

| run | 提交 | 结论 | 说明 |
| --- | --- | --- | --- |
| [39433774837](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/39433774837) | 2f46993 | **failure** | `LayerImageCacheTest.failedDecodeIsNotCachedAndRetriesOnNextRequest` 1/328 失败（竞态，见下节） |
| [39535896841](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/39535896841) | a666b76 | success | 修复后推送 |
| [39536480966](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/39536480966) | a666b76 | success | PR #36 打开触发 |

## 四、真实竞态的发现与修复（a666b76）

CI 一次性失败无法在本地串行复现（8 次全绿）。写 10 万轮压力复现器（带噪声 coroutine 干扰）在第 440 轮捕获：第二次 `get` 重新 join 了**已完成但清理回调尚未执行**的失败 Deferred。

机制：kotlinx.coroutines 的 Deferred 完成时先 CAS 终态，**后**执行 `invokeOnCompletion` 回调（我们的 inFlight 清理）；`await()` 快路径可在回调前返回。窗口期内新请求看到 inFlight 仍指向已失败项 → 加入失败等待 → 重试语义失效。

修复（SceneCatalogCache 与 LayerImageCache 同构）：加入前检查 `isActive`——

```kotlin
val existing = inFlight
if (existing != null && existing.isActive) return existing   // 已完成（含失败）的不重复加入
```

验证：修复后 10 万轮压力干净；新增永久回归锁 `failedDecodeRetriesUnderSchedulingPressure`（3 万轮 + 噪声调度），随 329 例全绿进 CI。

## 五、模拟器功能冒烟（新构建 a666b76）

流程：安装新 APK → `pm grant ACTIVITY_RECOGNITION` → `settings put global sensewalk_debug_stub 1` → 森林卡 → 实走 → 开始 → 显式广播 `com.sensewalk.action.DEBUG_STEP_BROADCAST`（`-n com.sensewalk.app/.service.DebugStepReceiver`）按 ~2 步/s 限速注入（尊重引擎 1.4 m/s 硬顶，单次大数量注入会被截断）。

截图（`screens/`，sha256）：

| 文件 | 内容 | sha256 |
| --- | --- | --- |
| `R0-entry-0m.png` | 入场 0 m：黑幕 void + 旅人剪影 + “轻触查看米数”，无渲染异常 | `7c30db88…d5fe5c9` |
| `S1-130m-outline.jpg` | ~130 m：`tree_outline` 图层以**位图质感**（手绘锯齿轮廓/枝干细节，非程序三角形）半透明透出 | `6f166097…dae82ba` |
| `S2-280m-trunks.jpg` | 288 m（uiautomator 读数“已走 288 米”）：树干层叠加，远/中/近层次自然，无接缝/黑块/错位 | `1b388451…5783fa` |

三图均经图像实看核验（非仅统计）。S1/S2 原始截图位图熵显著（389 KB / 900 KB PNG，压缩为 810px JPEG 入库），对照基线程序渲染截图 ~53 KB——位图异步解码路径在实走链路上真实出图。

清理：走查后放弃会话、force-stop、`sensewalk_debug_stub` 置 0、`pm revoke` ACTIVITY_RECOGNITION。

## 六、gfxinfo 前后对照：已执行，模拟器上不可分辨（不宣称收益）

脚本 `measure-script.py`（adb 驱动 uiautomator 导航 + `dumpsys gfxinfo <pkg> framestats/summary`），净机串行执行（无并行构建干扰），原始输出见 `measure-clean-gfxinfo.txt`。协议：每 APK 虚走/实走入场冷 1 次 + 暖 3 次（结果页“再走一次”）+ 虚走 30 s。

P50/P90（ms）：

| 场景 | 基线 4f57659 | 新 a666b76 |
| --- | --- | --- |
| 虚走入场冷 | 350 / 1650 | 300 / 1900 |
| 虚走 30 s | 350 / 450（190 帧） | 400 / 550（167 帧） |
| 虚走入场暖 ×3 | 500/2950 · 350/1550 · 550/2550 | 300/1350 · 350/2100 · 300/1950 |
| 实走入场暖 ×3 | 600/950 · 550/900 · 500/700 | 550/1050 · 500/800 · 300/800 |
| 实走入场冷 | 300 / 1050 | 500 / 1150 |

结论（诚实标注）：

- 该模拟器 GPU=emulation 下**两侧都只有 ~3–6 fps、~100% jank**（"Slow issue draw commands"全员命中），帧预算完全被软件渲染支配；
- 同构建轮间方差（入场 max 818–3261 ms）大于构建间差异（如 30 s 行走 P50 差 50 ms）；
- 因此**既不宣称帧率收益，也不认定回归**；本任务书要求的"每个优化标注测量方法与前后对照"在模拟器上无法分辨，设备级对照列 Pending（建议与 SW-024 性能基准任务同环境执行）。
- 功能无回归证据：30 s 行走/入场导航/结果页往返在两侧均正常完成。

首次测量作废说明：早前一轮 gfxinfo 与本机 Gradle 压力循环并行，模拟器被压到 ~5 fps 且结果反转，整轮丢弃后净机重测（上述数据）。

## 七、Pending（不冒充已验证）

1. 设备级前后帧指标（入场/行走 P50/P90、jank%）：模拟器不可分辨，待真机或与 SW-024 基准方法对齐后补测；
2. 真机真实计步、锁屏 15 min、来电/耳机、缺 sensor 设备路径（沿袭仓库全局 Pending，非本任务新增回归证据）；
3. 32 MiB 图层缓存在真机内存档位（lowRamDevice）下的适配：当前为统一预算，未按设备分级。

## 八、自我声明

以上命令与结果均为实际执行记录；未执行的项目一律列 Pending。功能/素材作者不自判 accepted，等 Antigravity 独立审核。
