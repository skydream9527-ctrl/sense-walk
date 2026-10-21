package com.sensewalk.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.os.Binder
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import com.sensewalk.app.MainActivity
import com.sensewalk.app.data.SceneCatalog
import com.sensewalk.app.data.SessionSnapshotStore
import com.sensewalk.app.domain.session.SessionSnapshot
import com.sensewalk.app.data.SettingsRepository
import com.sensewalk.app.domain.scene.SceneLoadState
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.sensory.AudioFocusGate
import com.sensewalk.app.domain.sensory.SensoryCoordinator
import com.sensewalk.app.domain.walk.RealWalkController
import com.sensewalk.app.domain.walk.VirtualWalkController
import com.sensewalk.app.engine.sensor.AndroidSensorPort
import com.sensewalk.app.engine.sensor.StepSensorSource
import com.sensewalk.app.engine.sensory.AndroidSensoryBackend
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * 实走前台服务（T06，M2 §"前台服务"）：
 * - **会话唯一持有者**：RealWalkController + SensoryCoordinator + 传感器源都在服务里，
 *   UI（Activity/ViewModel）只经 Binder 观察与发命令——Activity 重建不创建第二套计距引擎；
 * - foregroundServiceType="health"（计步场景的官方类型；Android 14+ 需
 *   FOREGROUND_SERVICE_HEALTH 权限 + ACTIVITY_RECOGNITION 运行时权限，均已在清单/流程声明）；
 * - 通知提供「回到会话」与「停止」（停止=放弃，与 UI 长按放弃同一终态）；
 * - 终态（通关/放弃）：注销传感器、释放音振、放弃音频焦点、移除前台并停止自身；
 * - 音频焦点丢失/耳机断连 → 暂停会话与播放，不自动恢复（与虚走同规则）。
 *
 * 服务生命周期以模拟器验证（通知/停止/无传感器回退）；真实计步与锁屏 15 分钟为真机待验证项。
 */
class WalkForegroundService : android.app.Service() {

    sealed interface UiState {
        data object Loading : UiState
        data class Ready(val sceneName: String) : UiState
        data class Error(val message: String) : UiState
    }

    inner class LocalBinder : Binder() {
        val uiState: StateFlow<UiState> get() = this@WalkForegroundService.uiState
        val walk: StateFlow<VirtualWalkController.Snapshot?> get() = this@WalkForegroundService.walk
        val hasDetector: Boolean get() = sensors?.detectorActive == true

        fun pauseForDialog() = this@WalkForegroundService.pauseSession()
        fun resumeFromDialog() = this@WalkForegroundService.resumeSession()
        fun abandon() = this@WalkForegroundService.abandonSession()
        fun setVibrationEnabled(enabled: Boolean) {
            coordinator?.setVibrationEnabled(enabled)
        }
    }

    private val binder = LocalBinder()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val uiState = MutableStateFlow<UiState>(UiState.Loading)
    private val walk = MutableStateFlow<VirtualWalkController.Snapshot?>(null)

    private var controller: RealWalkController? = null
    private var coordinator: SensoryCoordinator? = null
    private var sensors: StepSensorSource? = null
    private var sceneName: String = ""

    /** 生命周期仲裁（F-002/F-004）：空重启、单飞装配、迟到协程丢弃 */
    private val arbiter = SessionArbiter()

    /** debug 构建冒烟用：跳过硬件检查（服务生命周期验证，不构成计步验证） */
    private var debugStubSensor = false

    // 事件时间基准：elapsedRealtime（休眠不停表，与 SensorEvent.timestamp 同系）——
    // 见 StepSensorSource/AndroidSensorPort 与 SW-001 handoff 的时间基准核查
    private val clock = MonotonicClock { SystemClock.elapsedRealtime() }
    private var audioManager: AudioManager? = null
    private var focusRequest: AudioFocusRequest? = null
    private var noisyReceiver: BroadcastReceiver? = null
    private val focusGate = AudioFocusGate()
    private var audioResumed = false

    // ---- T07A 会话快照（SW-004）----
    private val snapshotStore by lazy { SessionSnapshotStore(applicationContext) }
    private var sessionId: String = ""
    private var saveTicker: Job? = null
    private var lastCounterReading: Long? = null
    private var lastCounterEventMs: Long? = null

    override fun onBind(intent: Intent): IBinder = binder

    /** debug 冒烟入口仅限可调试构建（release 不生成注入路径） */
    private fun isDebuggable(): Boolean =
        (applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val sceneId = intent?.getStringExtra(EXTRA_SCENE_ID)
        return when (arbiter.onCommand(intent?.action, sceneId != null)) {
            SessionArbiter.Decision.ABANDON_AND_FINISH -> {
                abandonSession()
                START_NOT_STICKY
            }
            SessionArbiter.Decision.STOP_CLEAN -> {
                // F-002：START_STICKY 空重启/无有效会话——不进前台、不留空通知，
                // 清掉可能残留的前台身份后干净退出。T07A 恢复仍只由用户在 UI 显式选择，
                // 空重启不自动恢复会话
                stopSelfClean()
                START_NOT_STICKY
            }
            SessionArbiter.Decision.FORWARD_DEBUG_STEP -> {
                // debug 构建专用：adb 注入 counter 读数冒烟（服务生命周期/渲染/UI），
                // 不构成真实计步验证；release 构建不可达
                if (isDebuggable() && controller != null) {
                    val count = intent?.getLongExtra(EXTRA_DEBUG_COUNT, 0L) ?: 0L
                    onCounterEvent(count, clock.nowMs())
                }
                START_STICKY
            }
            SessionArbiter.Decision.START_FOREGROUND_AND_SETUP -> {
                startAsForeground() // startForegroundService 后 5s 内必须进前台
                debugStubSensor = DebugWalkSmoke.enabled(this)
                setupSession(sceneId!!, intent?.getStringExtra(EXTRA_RESTORE_JSON))
                START_STICKY
            }
            SessionArbiter.Decision.NONE ->
                // F-004：装配中/活动中的重复 start——单飞，绝不建第二套引擎
                START_STICKY
        }
    }

    // ---- 会话装配（仅一次；重复 onStartCommand 不重建，保证单一引擎）----

    private fun setupSession(sceneId: String, restoreJson: String? = null) {
        val app = applicationContext
        scope.launch {
            // 进程级目录缓存（SW-019 #2）：与 UI 共用同一 SceneConfig 实例，实走视觉层无需再读
            when (val state = SceneCatalog.load(app)) {
                is SceneLoadState.Ready -> {
                    val config = state.scenes.firstOrNull { it.id == sceneId }
                    if (config == null) {
                        uiState.value = UiState.Error("场景不可用：'$sceneId'")
                        failSetup()
                        return@launch
                    }
                    val port = AndroidSensorPort(app)
                    val sensorSource = StepSensorSource(
                        port = port,
                        onCounter = ::onCounterEvent,
                        onDetectorStep = ::onDetectorStep,
                    )
                    if (!sensorSource.canCountDistance && !debugStubSensor) {
                        uiState.value = UiState.Error("此设备没有计步传感器（TYPE_STEP_COUNTER），请改用虚走")
                        failSetup()
                        return@launch
                    }
                    sceneName = config.name
                    // T07A 恢复（SW-004）：UI 层已校验；此处防御性解析，失败按新会话
                    val restore = parseRestore(restoreJson, config)
                    sessionId = restore?.snapshot?.sessionId ?: java.util.UUID.randomUUID().toString()
                    val real = RealWalkController(config, clock, restore = restore?.toControllerRestore())
                    val sensory = SensoryCoordinator(
                        config = config,
                        backend = AndroidSensoryBackend(app, config),
                    )
                    // F-003：以真实注册结果为准（硬件存在 ≠ 注册成功）
                    val registered = debugStubSensor || sensorSource.start()
                    if (!registered) {
                        sensory.release()
                        uiState.value = UiState.Error(
                            "计步传感器注册失败（可能因权限变化或传感器暂不可用）。请重试，或改用虚走。",
                        )
                        failSetup()
                        return@launch
                    }
                    // F-004：装配期间服务可能已被停止/终态——迟到协程一律丢弃，
                    // 释放本次临时创建的资源，不发布第二套会话
                    if (!arbiter.onSetupCompleted(active = true)) {
                        sensorSource.stop()
                        sensory.release()
                        return@launch
                    }
                    // detector 真正注册成功才负责步伐音/振；注册失败或无硬件时
                    // 回退按距离出声——按注册结果而非硬件存在选择 cue 源（P-01）
                    sensory.stepAudioFromDistance = sensorSource.cueAudioFromDistance
                    if (restore != null) {
                        // 恢复：按当前米数静态重建感官（loop 满淡入、不重播一次性提示）
                        sensory.restoreState(real.snapshot().sensory)
                    } else {
                        sensory.onPhaseEvents(real.drainPhaseEvents())
                    }
                    controller = real
                    coordinator = sensory
                    sensors = sensorSource
                    real.start()
                    setupAudioFocus()
                    observeVibrationSetting(app)
                    walk.value = real.snapshot()
                    uiState.value = UiState.Ready(config.name)
                    hasActiveSession = true
                    startSnapshotTicker()
                }
                is SceneLoadState.Error -> {
                    uiState.value = UiState.Error("场景配置加载失败：\n${state.diagnostics.joinToString("\n")}")
                    failSetup()
                }
                SceneLoadState.Loading -> Unit
            }
        }
    }

    // ---- 快照保存/清除（T07A：每 5s + 越相位 + 状态转换；主动结束清除）----

    /** 防御性解析（UI 已校验过）；损坏 JSON 不阻塞新会话 */
    private fun parseRestore(json: String?, config: com.sensewalk.app.domain.scene.SceneConfig): ParsedRestore? {
        if (json == null) return null
        val snap = SessionSnapshot.fromJson(json) ?: return null
        if (snap.sceneId != config.id) return null
        return ParsedRestore(
            snapshot = snap,
            toControllerRestore = {
                VirtualWalkController.Restore(
                    progress = com.sensewalk.app.domain.progress.ProgressSnapshot(
                        sPos = snap.sPos, sBest = snap.sBest, meters = snap.meters,
                        requiredDistanceMeters = config.requiredDistanceMeters.toFloat(),
                    ),
                    firedPhaseIds = snap.firedPhaseIds.toSet(),
                    elapsedActiveMs = snap.elapsedActiveMs,
                )
            },
        )
    }

    private class ParsedRestore(
        val snapshot: SessionSnapshot,
        val toControllerRestore: () -> VirtualWalkController.Restore,
    )

    private fun startSnapshotTicker() {
        saveTicker?.cancel()
        saveTicker = scope.launch {
            while (true) {
                kotlinx.coroutines.delay(SAVE_INTERVAL_MS)
                persistSnapshot()
            }
        }
    }

    /** 状态转换/越相位时立即保存（节流外的补充时机） */
    private fun saveSnapshotNow() {
        scope.launch { persistSnapshot() }
    }

    private suspend fun persistSnapshot() {
        val real = controller ?: return
        val state = real.stateMachine.state
        // 终态由 finish/abandon 清除，这里不再写（终态快照不是恢复候选）
        if (state == SessionState.COMPLETED || state == SessionState.ABANDONED) return
        val acc = real.accumulator.snapshot()
        snapshotStore.save(
            SessionSnapshot(
                snapshotVersion = SessionSnapshot.SNAPSHOT_VERSION,
                sessionId = sessionId,
                mode = "real",
                sceneId = real.config.id,
                sceneSchemaVersion = real.config.schemaVersion,
                state = state.name,
                savedAtWallMs = System.currentTimeMillis(),
                bootCount = SessionSnapshotStore.bootCount(applicationContext),
                meters = acc.meters,
                sPos = acc.sPos,
                sBest = acc.sBest,
                firedPhaseIds = real.scheduler.firedPhaseIds.toList(),
                elapsedActiveMs = real.stateMachine.elapsedActiveMs,
                lastCounterReading = lastCounterReading,
                lastCounterEventMs = lastCounterEventMs,
            ),
        )
    }

    /** 装配失败：仲裁记终态并干净退出（不残留前台/通知/监听） */
    private fun failSetup() {
        arbiter.onFinish()
        stopSelfClean()
    }

    private fun onCounterEvent(stepCount: Long, eventTimeMs: Long) {
        val real = controller ?: return
        lastCounterReading = stepCount
        lastCounterEventMs = eventTimeMs
        val snap = real.onCounterEvent(stepCount, eventTimeMs)
        var firedPhases = false
        coordinator?.let { sensory ->
            val events = real.drainPhaseEvents()
            if (events.isNotEmpty()) {
                firedPhases = true
                sensory.onPhaseEvents(events)
            }
            sensory.onFrame(
                dtMs = snap.frameDtMs,
                metersDelta = snap.metersDelta,
                walking = snap.session == SessionState.WALKING,
            )
        }
        if (snap.session == SessionState.COMPLETED || snap.session == SessionState.ABANDONED) {
            finishSession()
        }
        if (firedPhases) saveSnapshotNow() // 越相位即存（契约）
        if (snap != walk.value) walk.value = snap
    }

    private fun onDetectorStep(eventTimeMs: Long) {
        val real = controller ?: return
        if (real.onDetectorStep(eventTimeMs)) {
            coordinator?.onStepCue()
        }
    }

    // ---- 会话命令（UI/通知共用；全部主线程）----

    fun pauseSession() {
        val real = controller ?: return
        real.pause()
        coordinator?.pause()
        walk.value = real.snapshot()
        saveSnapshotNow() // 状态转换即存（契约）
    }

    fun resumeSession() {
        val real = controller ?: return
        real.resume()
        attemptAudioResume()
        walk.value = real.snapshot()
        saveSnapshotNow()
    }

    fun abandonSession() {
        val real = controller
        if (real != null && real.stateMachine.state != SessionState.COMPLETED) {
            real.abandon()
            walk.value = real.snapshot()
        }
        // 装配中（controller 尚未发布）也可被通知「停止」：仲裁记终态，
        // 迟到的装配协程会自行丢弃
        finishSession()
    }

    private fun finishSession() {
        if (arbiter.phase == SessionArbiter.Phase.FINISHED) {
            stopSelfClean()
            return
        }
        arbiter.onFinish()
        sensors?.stop()
        coordinator?.release()
        teardownAudioFocus()
        // 主动结束（放弃/通关）：清除恢复候选（契约：只有被动中断可恢复）
        hasActiveSession = false
        saveTicker?.cancel()
        sessionId = ""
        scope.launch { snapshotStore.clear() }
        stopSelfClean()
    }

    // ---- 前台通知 ----

    private fun startAsForeground() {
        val nm = getSystemService(NotificationManager::class.java)
        if (nm.getNotificationChannel(CHANNEL_ID) == null) {
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "实走会话", NotificationManager.IMPORTANCE_LOW).apply {
                    description = "实走进行中的常驻通知：返回会话或停止"
                    setShowBadge(false)
                },
            )
        }
        val notification = buildNotification()
        // 服务类型依据（SW-001 F-005 核查）：本服务的持续前台职责是"计步锻炼会话"
        // （TYPE_STEP_COUNTER），官方归类为 FOREGROUND_SERVICE_TYPE_HEALTH，API 34+
        // 需 FOREGROUND_SERVICE_HEALTH + 下列运行时权限之一（我们持有 ACTIVITY_RECOGNITION）。
        // 会话中的环境音播放是该健康会话的一部分，不是独立的媒体服务职责，
        // 故不机械追加 mediaPlayback 类型；若后续把音频拆成独立常驻播放服务再另行评估。
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ServiceCompat.startForeground(
                    this, NOTIFICATION_ID, notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_HEALTH,
                )
            } else {
                startForeground(NOTIFICATION_ID, notification)
            }
        } catch (e: SecurityException) {
            // API 34+：health 类型要求运行时已持有 ACTIVITY_RECOGNITION 等（"any of"）；
            // 权限被拒/在设置中被撤回的竞态下诚实降级为不可实走，不崩溃
            uiState.value = UiState.Error("缺少活动识别权限，无法开始实走。可在系统设置授权后重试，或改用虚走。")
            failSetup()
        }
    }

    private fun buildNotification(): Notification {
        val open = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val stop = PendingIntent.getService(
            this, 1,
            Intent(this, WalkForegroundService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_menu_directions)
            .setContentTitle("慢行 · 实走中")
            .setContentText(sceneName.ifEmpty { "手机收进口袋，走你的路" })
            .setContentIntent(open)
            .setOngoing(true)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .addAction(0, "停止", stop)
            .build()
    }

    private fun stopSelfClean() {
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    // ---- 音频焦点 / 耳机断连（与虚走 SessionViewModel 同规则）----

    private fun setupAudioFocus() {
        audioManager = getSystemService(AudioManager::class.java) ?: return
        val request = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build(),
            )
            .setOnAudioFocusChangeListener { change ->
                when (change) {
                    AudioManager.AUDIOFOCUS_LOSS,
                    AudioManager.AUDIOFOCUS_LOSS_TRANSIENT,
                    AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK,
                    -> {
                        focusGate.onFocusLoss()
                        audioResumed = false
                        coordinator?.setAudioAllowed(false)
                        pauseSession()
                    }
                }
            }
            .build()
        focusRequest = request
        val result = audioManager?.requestAudioFocus(request) ?: 0
        focusGate.onRequestResult(result)
        audioResumed = focusGate.canResumeAudio()
        // 首次申请被拒也必须静默（与虚走同一门控）
        coordinator?.setAudioAllowed(focusGate.canResumeAudio())

        val receiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context?, intent: Intent?) {
                if (intent?.action == AudioManager.ACTION_AUDIO_BECOMING_NOISY) {
                    focusGate.onFocusLoss()
                    audioResumed = false
                    coordinator?.setAudioAllowed(false)
                    pauseSession()
                }
            }
        }
        noisyReceiver = receiver
        ContextCompat.registerReceiver(
            this,
            receiver,
            IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY),
            ContextCompat.RECEIVER_NOT_EXPORTED,
        )
    }

    private fun attemptAudioResume() {
        if (audioResumed) {
            coordinator?.resume()
            return
        }
        val request = focusRequest ?: return
        val result = audioManager?.requestAudioFocus(request) ?: 0
        focusGate.onRequestResult(result)
        if (focusGate.canResumeAudio()) {
            audioResumed = true
            coordinator?.setAudioAllowed(true)
            coordinator?.resume()
        } else {
            audioResumed = false
            coordinator?.setAudioAllowed(false)
        }
    }

    private fun teardownAudioFocus() {
        focusRequest?.let { audioManager?.abandonAudioFocusRequest(it) }
        focusRequest = null
        noisyReceiver?.let { runCatching { unregisterReceiver(it) } }
        noisyReceiver = null
    }

    private fun observeVibrationSetting(app: Context) {
        scope.launch {
            SettingsRepository(app).settings
                .map { it.vibrationEnabled }
                .distinctUntilChanged()
                .collect { enabled -> coordinator?.setVibrationEnabled(enabled) }
        }
    }

    override fun onDestroy() {
        arbiter.onFinish()
        sensors?.stop()
        coordinator?.release()
        teardownAudioFocus()
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        /** 进程内活会话标志（T07A 竞争仲裁）：服务装配成功后置 true、主动结束置 false。
         *  进程死亡即失真为 false（与服务同生死）——MODE 层据此区分「重绑现有会话」
         *  与「从快照恢复」，避免对活服务再起一套恢复引擎。 */
        @Volatile
        var hasActiveSession: Boolean = false

        const val EXTRA_SCENE_ID = "sceneId"
        const val EXTRA_RESTORE_JSON = "restoreJson"
        const val ACTION_STOP = "com.sensewalk.action.STOP_WALK"
        private const val CHANNEL_ID = "real_walk"
        private const val NOTIFICATION_ID = 4601

        /** 快照周期（契约：每 5s） */
        private const val SAVE_INTERVAL_MS = 5_000L

        // debug 冒烟专用（release 不可达）：跳过硬件检查启动 + 注入 counter 读数
        const val ACTION_DEBUG_STEP = "com.sensewalk.action.DEBUG_STEP"
        const val EXTRA_DEBUG_STUB_SENSOR = "debugStubSensor"
        const val EXTRA_DEBUG_COUNT = "debugCount"

        /** 只从可见 Activity 调用（前台启动前台服务的合法路径；后台启动受系统限制） */
        fun start(context: Context, sceneId: String, restoreJson: String? = null) {
            val intent = Intent(context, WalkForegroundService::class.java)
                .putExtra(EXTRA_SCENE_ID, sceneId)
            if (restoreJson != null) intent.putExtra(EXTRA_RESTORE_JSON, restoreJson)
            ContextCompat.startForegroundService(context, intent)
        }
    }
}
