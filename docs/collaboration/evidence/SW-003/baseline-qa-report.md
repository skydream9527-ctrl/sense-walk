# SW-003 · 独立基线验收与风险复测报告

- 记录角色：antigravity（独立 QA 与协作协调者）
- 依据基线：`B-20261013-01` · 基线提交 `8056e11b2b366d958132dfa0d5674dbaa8577db1`
- 对应初审：[R-BASE-001](../../reviews/R-BASE-001.md)
- 执行测试套件：`tools/qa/test_baseline_risks.py`（7 项全部通过）及 `tools/qa/test_collaboration.py`（31 项全部通过）

---

## 一、基线测试产物与云端报告核对

1. **历史云端 CI 核查**：
   - GitHub Actions 运行记录：[Run 38502107619](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38502107619)，结论为 success。
   - 测试构建：Release [build-37-8056e11](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-37-8056e11)。
2. **入库 JUnit XML 审计**：
   - 目录 `docs/collaboration/evidence/B-20261013-01/junit/` 下全部 19 份原始 XML 报告经 `BaselineEvidenceAudit` 自动化校验，SHA256 与 `test-summary.json` 记录完全一致。
   - 统计结果：共 217 个测试用例，0 failures、0 errors、0 skipped。
   - **证据性质说明**：此 217 项测试为历史云端 JVM 单元测试与领域模拟测试，不代表真实 Android 传感器或硬件仪器测试；本轮未宣称亲自执行云端 Actions 重跑。

---

## 二、R-BASE-001 风险项独立源码路径与反例建立

通过独立 QA 测试套件 `tools/qa/test_baseline_risks.py` 对已识别风险建立严格路径与断言模型：

### F-001（P1）：同刻事件可刷距离（已建立数学/算法失败反例）
- **源码定位**：`app/src/main/java/com/sensewalk/app/domain/walk/RealWalkEngine.kt:85`
  ```kotlin
  val capMeters = if (intervalMs <= 0L) strideMeters else MAX_SPEED_MPS * intervalMs / 1000f
  val delta = min(raw, capMeters).coerceAtLeast(0f)
  ```
- **失败反例机制**：
  当底层传感器驱动以批处理（batching）方式在同一毫秒交付多个步数事件时（例如硬件唤醒后上报），`intervalMs == 0`。当前代码判定 `intervalMs <= 0L` 时将上限设置为 `strideMeters`（0.7m）。连续 5 个事件在同刻上报即可累积 `5 × 0.7 = 3.5m`，在 $\Delta t = 0$ 时瞬时速度无穷大，完全突破 $1.4\text{ m/s}$ 的物理速度门限。
- **复现证明**：`test_f001_zero_interval_step_burst_speed_cap_bypass` 验证了该缺陷逻辑。
- **给 ZCode 的修复要求**：在 SW-001 中，当 `intervalMs <= 0L` 时有效位移必须为 0，且不能因同刻事件破坏物理速度硬顶。

### F-002（P1）：START_STICKY 空重启残留前台通知（源码路径确认）
- **源码定位**：`app/src/main/java/com/sensewalk/app/service/WalkForegroundService.kt:120-128`
  ```kotlin
  startAsForeground()
  val sceneId = intent?.getStringExtra(EXTRA_SCENE_ID)
  debugStubSensor = DebugWalkSmoke.enabled(this)
  if (controller == null && sceneId != null && !finished) {
      setupSession(sceneId)
  }
  return START_STICKY
  ```
- **路径确认**：系统在杀进程后空 Intent 重启服务（`intent == null`），`startAsForeground()` 立即弹出前台通知；但因 `sceneId == null`，`setupSession` 不会被触发，`controller` 保持 `null`。服务返回 `START_STICKY` 导致前台变成僵尸状态，无任何行走会话却永久常驻通知栏。
- **复现证明**：`test_f002_start_sticky_empty_restart_path_confirmed` 静态分析确认。
- **给 ZCode 的修复要求**：若无法恢复会话（T07 前），空重启应安全停止服务并移除通知（`stopSelfClean()`），返回 `START_NOT_STICKY`。

### F-003（P1）：硬件存在被当作注册成功（源码路径确认）
- **源码定位**：`app/src/main/java/com/sensewalk/app/engine/sensor/StepSensorSource.kt:40-47`
  ```kotlin
  val counter = sensorManager.getDefaultSensor(Sensor.TYPE_STEP_COUNTER)
  if (counter != null) {
      sensorManager.registerListener(this, counter, SensorManager.SENSOR_DELAY_UI, mainHandler)
  }
  registered = counter != null
  ```
  以及 `WalkForegroundService.kt:167`：
  ```kotlin
  sensorSource.start()
  real.start()
  ```
- **路径确认**：`sensorManager.registerListener` 返回 `Boolean`（权限受阻、驱动故障或资源不足时返回 `false`）。代码完全忽略该返回值，仅凭 `counter != null` 将 `registered` 赋为 `true`。同时服务层丢弃 `sensorSource.start()` 结果，盲目进入 `UiState.Ready`。
- **复现证明**：`test_f003_hardware_check_vs_registration_result` 确认。
- **给 ZCode 的修复要求**：检查实际注册返回值；注册失败时主动清理并回退，向用户报出明确错误状态。

### F-004（P2）：异步会话装配并发风险（待实测验证）
- **源码定位**：`WalkForegroundService.kt:124-137`
  `setupSession` 启动协程并挂起于 `SceneRepository.loadAll()`，在此期间 `controller` 保持为 `null`。若外部快速连续触发 `onStartCommand`，将绕过 `if (controller == null)` 保护，导致多个装配协程并发运行。
- **复现证明**：`test_f004_async_session_setup_concurrent_invocation_risk`。

---

## 三、实走关键边界机制核验

1. **Debug 注入安全隔离**：
   `test_security_debug_step_injection_restricted_to_debuggable` 确认 `ACTION_DEBUG_STEP` 带有严格的 `isDebuggable()` 守卫（检查 `FLAG_DEBUGGABLE`），Release 构建中该入口自动禁用，不可被外部 adb 伪造计步。
2. **Counter 与 Detector 隔离防双计**：
   `test_counter_and_detector_audio_segregation` 确认 `sensory.stepAudioFromDistance = !sensorSource.hasDetector`，Detector 仅用于脚步音频节奏同步，唯一距离源严格绑定 Counter，不存在双份距离或双重出声。

---

## 四、真机验证待测矩阵（当前全部保留为 Pending）

| 验证项 | 验证级别 | 当前状态 | 依赖与说明 |
| --- | --- | --- | --- |
| 森林 800m 真实手动步行走查 | 真人 (Human) | **Pending** | 需真实行走测试全流程与感官淡入 |
| 真实 TYPE_STEP_COUNTER 步数准确度 | 真机 (Physical Device) | **Pending** | 需对比物理计步器与系统传感器读数 |
| 锁屏 15 分钟持续前台保活 | 真机 (Physical Device) | **Pending** | 需真机系统省电策略与 Doze 模式测试 |
| 实体耳机插拔、来电与音频焦点打断 | 真机 (Physical Device) | **Pending** | 需硬件音频通路与蓝牙/有线耳机打断 |
| 振动马达真实触感与节拍同步 | 真机 (Physical Device) | **Pending** | 模拟器无硬件触觉 HAL 支持 |
| 运行时动态权限拒绝与诚实降级 | 真机 (Physical Device) | **Pending** | ACTIVITY_RECOGNITION 权限撤销流转 |

> **门禁声明**：当前代码阶段不因缺乏真机而阻塞集成；但上述 Pending 项在实际真机与真人测试通过前，不得将 M1/M2/MVP 判定为已完成。
