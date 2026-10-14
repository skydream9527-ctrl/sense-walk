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
import android.hardware.SensorManager
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.os.Binder
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import com.sensewalk.app.MainActivity
import com.sensewalk.app.data.SceneRepository
import com.sensewalk.app.data.SettingsRepository
import com.sensewalk.app.domain.scene.SceneLoadState
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.sensory.AudioFocusGate
import com.sensewalk.app.domain.sensory.SensoryCoordinator
import com.sensewalk.app.domain.walk.RealWalkController
import com.sensewalk.app.domain.walk.VirtualWalkController
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
        val hasDetector: Boolean get() = sensors?.hasDetector == true

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
    private var finished = false

    /** debug 构建冒烟用：跳过硬件检查（服务生命周期验证，不构成计步验证） */
    private var debugStubSensor = false

    private val clock = MonotonicClock { System.nanoTime() / 1_000_000 }
    private var audioManager: AudioManager? = null
    private var focusRequest: AudioFocusRequest? = null
    private var noisyReceiver: BroadcastReceiver? = null
    private val focusGate = AudioFocusGate()
    private var audioResumed = false

    override fun onBind(intent: Intent): IBinder = binder

    /** debug 冒烟入口仅限可调试构建（release 不生成注入路径） */
    private fun isDebuggable(): Boolean =
        (applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                abandonSession()
                return START_NOT_STICKY
            }
            ACTION_DEBUG_STEP -> {
                // debug 构建专用：adb 注入 counter 读数冒烟（服务生命周期/渲染/UI），
                // 不构成真实计步验证；release 构建不可达
                if (isDebuggable() && controller != null) {
                    val count = intent.getLongExtra(EXTRA_DEBUG_COUNT, 0L)
                    onCounterEvent(count, clock.nowMs())
                }
                return START_STICKY
            }
            else -> {
                startAsForeground() // startForegroundService 后 5s 内必须进前台
                val sceneId = intent?.getStringExtra(EXTRA_SCENE_ID)
                debugStubSensor = DebugWalkSmoke.enabled(this)
                if (controller == null && sceneId != null && !finished) {
                    setupSession(sceneId)
                }
                return START_STICKY // 系统重建保住前台身份；会话快照恢复属 T07（不假装已支持）
            }
        }
    }

    // ---- 会话装配（仅一次；重复 onStartCommand 不重建，保证单一引擎）----

    private fun setupSession(sceneId: String) {
        val app = applicationContext
        scope.launch {
            when (val state = SceneRepository(app).loadAll()) {
                is SceneLoadState.Ready -> {
                    val config = state.scenes.firstOrNull { it.id == sceneId }
                    if (config == null) {
                        uiState.value = UiState.Error("场景不可用：'$sceneId'")
                        stopSelfClean()
                        return@launch
                    }
                    val sensorSource = StepSensorSource(
                        sensorManager = app.getSystemService(SensorManager::class.java),
                        onCounter = ::onCounterEvent,
                        onDetectorStep = ::onDetectorStep,
                    )
                    if (!sensorSource.canCountDistance && !debugStubSensor) {
                        uiState.value = UiState.Error("此设备没有计步传感器（TYPE_STEP_COUNTER），请改用虚走")
                        stopSelfClean()
                        return@launch
                    }
                    sceneName = config.name
                    val real = RealWalkController(config, clock)
                    val sensory = SensoryCoordinator(
                        config = config,
                        backend = AndroidSensoryBackend(app, config),
                    )
                    // detector（若存在）负责步伐音/振；counter 只管计距与淡入——不双份出声
                    sensory.stepAudioFromDistance = !sensorSource.hasDetector
                    sensory.onPhaseEvents(real.drainPhaseEvents())
                    controller = real
                    coordinator = sensory
                    sensors = sensorSource
                    sensorSource.start()
                    real.start()
                    setupAudioFocus()
                    observeVibrationSetting(app)
                    walk.value = real.snapshot()
                    uiState.value = UiState.Ready(config.name)
                }
                is SceneLoadState.Error -> {
                    uiState.value = UiState.Error("场景配置加载失败：\n${state.diagnostics.joinToString("\n")}")
                    stopSelfClean()
                }
                SceneLoadState.Loading -> Unit
            }
        }
    }

    private fun onCounterEvent(stepCount: Long, eventTimeMs: Long) {
        val real = controller ?: return
        val snap = real.onCounterEvent(stepCount, eventTimeMs)
        coordinator?.let { sensory ->
            sensory.onPhaseEvents(real.drainPhaseEvents())
            sensory.onFrame(
                dtMs = snap.frameDtMs,
                metersDelta = snap.metersDelta,
                walking = snap.session == SessionState.WALKING,
            )
        }
        if (snap.session == SessionState.COMPLETED || snap.session == SessionState.ABANDONED) {
            finishSession()
        }
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
    }

    fun resumeSession() {
        val real = controller ?: return
        real.resume()
        attemptAudioResume()
        walk.value = real.snapshot()
    }

    fun abandonSession() {
        val real = controller ?: return
        if (real.stateMachine.state != SessionState.COMPLETED) {
            real.abandon()
        }
        finishSession()
        walk.value = real.snapshot()
    }

    private fun finishSession() {
        if (finished) return
        finished = true
        sensors?.stop()
        coordinator?.release()
        teardownAudioFocus()
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
            stopSelfClean()
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
        sensors?.stop()
        coordinator?.release()
        teardownAudioFocus()
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        const val EXTRA_SCENE_ID = "sceneId"
        const val ACTION_STOP = "com.sensewalk.action.STOP_WALK"
        private const val CHANNEL_ID = "real_walk"
        private const val NOTIFICATION_ID = 4601

        // debug 冒烟专用（release 不可达）：跳过硬件检查启动 + 注入 counter 读数
        const val ACTION_DEBUG_STEP = "com.sensewalk.action.DEBUG_STEP"
        const val EXTRA_DEBUG_STUB_SENSOR = "debugStubSensor"
        const val EXTRA_DEBUG_COUNT = "debugCount"

        /** 只从可见 Activity 调用（前台启动前台服务的合法路径；后台启动受系统限制） */
        fun start(context: Context, sceneId: String) {
            val intent = Intent(context, WalkForegroundService::class.java)
                .putExtra(EXTRA_SCENE_ID, sceneId)
            ContextCompat.startForegroundService(context, intent)
        }
    }
}
