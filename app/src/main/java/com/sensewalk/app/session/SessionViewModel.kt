package com.sensewalk.app.session

import android.app.Application
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.core.content.ContextCompat
import com.sensewalk.app.data.SceneRepository
import com.sensewalk.app.data.SessionSnapshotStore
import com.sensewalk.app.domain.session.SessionSnapshot
import com.sensewalk.app.data.SettingsRepository
import com.sensewalk.app.data.UserSettings
import com.sensewalk.app.domain.scene.SceneLoadState
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.sensory.AudioFocusGate
import com.sensewalk.app.domain.sensory.SensoryCoordinator
import com.sensewalk.app.domain.walk.VirtualWalkController
import com.sensewalk.app.engine.sensory.AndroidSensoryBackend
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * 会话 ViewModel（T04/T05）：
 * - 持有 [VirtualWalkController] 作为唯一状态来源；
 * - 持有 [SensoryCoordinator]（真实引擎后端）：每帧消费相位事件与距离增量，
 *   脚步/淡入/振动全部由会话状态驱动，不另起计时器；
 * - 音频焦点丢失（来电/切音乐）与耳机断连（ACTION_AUDIO_BECOMING_NOISY）
 *   → 暂停会话与播放；**恢复不自动行走**，等待用户新输入；
 * - 终态/销毁释放全部音频与振动资源。
 */
class SessionViewModel(
    application: Application,
    private val sceneId: String,
    restoreSnapshot: SessionSnapshot? = null,
) : AndroidViewModel(application) {

    sealed interface UiState {
        data object Loading : UiState
        data class Ready(val controller: VirtualWalkController) : UiState
        data class Error(val message: String) : UiState
    }

    private val app = application
    private val sceneRepository = SceneRepository(application)
    private val settingsRepository = SettingsRepository(application)

    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    /** 每帧/每次输入后的会话快照；null = 会话未就绪 */
    private val _walk = MutableStateFlow<VirtualWalkController.Snapshot?>(null)
    val walk: StateFlow<VirtualWalkController.Snapshot?> = _walk.asStateFlow()

    val settings: StateFlow<UserSettings> = settingsRepository.settings
        .stateIn(viewModelScope, SharingStarted.Eagerly, UserSettings())

    private val systemClock = MonotonicClock { System.nanoTime() / 1_000_000 }

    private companion object {
        /** 快照周期（契约：每 5s） */
        const val SAVE_INTERVAL_MS = 5_000L
    }

    private var coordinator: SensoryCoordinator? = null

    // ---- T07A 会话快照（SW-004）----
    private val snapshotStore = SessionSnapshotStore(application)
    private val restoredSnapshot = restoreSnapshot
    private var sessionId: String = restoreSnapshot?.sessionId ?: java.util.UUID.randomUUID().toString()
    private var saveTicker: kotlinx.coroutines.Job? = null
    private var snapshotCleared = false

    // 音频焦点与耳机断连
    private var audioManager: AudioManager? = null
    private var focusRequest: AudioFocusRequest? = null
    private var noisyReceiver: BroadcastReceiver? = null
    private var focusRegistered = false
    private val focusGate = AudioFocusGate()
    private var audioResumed = false

    init {
        viewModelScope.launch {
            when (val state = sceneRepository.loadAll()) {
                is SceneLoadState.Error -> _uiState.value = UiState.Error(
                    "场景配置加载失败：\n" + state.diagnostics.joinToString("\n"),
                )
                is SceneLoadState.Ready -> {
                    val config = state.scenes.firstOrNull { it.id == sceneId }
                    if (config == null) {
                        _uiState.value = UiState.Error("场景不可用：'$sceneId' 不在已加载的场景中")
                    } else {
                        // T07A 恢复（SW-004）：UI 已校验；VM 只负责透传（防御性场景校验）
                        val restore = restoredSnapshot?.takeIf { it.sceneId == config.id }?.let { snap ->
                            VirtualWalkController.Restore(
                                progress = com.sensewalk.app.domain.progress.ProgressSnapshot(
                                    sPos = snap.sPos, sBest = snap.sBest, meters = snap.meters,
                                    requiredDistanceMeters = config.requiredDistanceMeters.toFloat(),
                                ),
                                firedPhaseIds = snap.firedPhaseIds.toSet(),
                                elapsedActiveMs = snap.elapsedActiveMs,
                            )
                        }
                        val controller = VirtualWalkController(config, systemClock, restore)
                        val sensory = SensoryCoordinator(
                            config = config,
                            backend = AndroidSensoryBackend(app, config),
                        )
                        coordinator = sensory
                        _uiState.value = UiState.Ready(controller)
                        _walk.value = controller.snapshot()
                        setupAudioInterruptionHandling()
                        if (restore != null) {
                            // 恢复：静态重建感官（loop 满淡入；一次性提示/旧脚步不重播）
                            sensory.restoreState(controller.snapshot().sensory)
                        } else {
                            // 相位事件（含初始化黑幕）交给协调器；振动偏好实时跟随设置
                            sensory.onPhaseEvents(controller.drainPhaseEvents())
                        }
                        observeVibrationSetting()
                        startSnapshotTicker()
                    }
                }
                SceneLoadState.Loading -> Unit
            }
        }
    }

    private fun withController(block: (VirtualWalkController) -> Unit) {
        (uiState.value as? UiState.Ready)?.let { block(it.controller) }
    }

    // ---- 快照保存/清除（T07A：每 5s + 越相位/状态转换；主动结束清除）----

    private fun startSnapshotTicker() {
        saveTicker?.cancel()
        saveTicker = viewModelScope.launch {
            while (true) {
                kotlinx.coroutines.delay(SAVE_INTERVAL_MS)
                persistSnapshot()
            }
        }
    }

    private fun saveSnapshotNow() {
        viewModelScope.launch { persistSnapshot() }
    }

    private suspend fun persistSnapshot() {
        if (snapshotCleared) return
        val controller = (uiState.value as? UiState.Ready)?.controller ?: return
        val state = controller.stateMachine.state
        if (state == SessionState.COMPLETED || state == SessionState.ABANDONED) return
        val acc = controller.accumulator.snapshot()
        snapshotStore.save(
            SessionSnapshot(
                snapshotVersion = SessionSnapshot.SNAPSHOT_VERSION,
                sessionId = sessionId,
                mode = "virtual",
                sceneId = sceneId,
                sceneSchemaVersion = controller.config.schemaVersion,
                state = state.name,
                savedAtWallMs = System.currentTimeMillis(),
                bootCount = SessionSnapshotStore.bootCount(app),
                meters = acc.meters,
                sPos = acc.sPos,
                sBest = acc.sBest,
                firedPhaseIds = controller.scheduler.firedPhaseIds.toList(),
                elapsedActiveMs = controller.stateMachine.elapsedActiveMs,
            ),
        )
    }

    /** 主动结束（放弃/通关）：清除恢复候选 */
    private fun clearSnapshot() {
        snapshotCleared = true
        saveTicker?.cancel()
        viewModelScope.launch { snapshotStore.clear() }
    }

    /** 唯一帧驱动入口：控制器步进 → 相位事件 → 感官协调器。
     *  快照无变化（静止/暂停/终态）时不推送，避免空闲期 60fps 全树重组。 */
    private val _stabilizeHint = MutableStateFlow(false)
    /** 本局首坎站稳提示（一次性事件：UI 消费后调 [consumeStabilizeHintDone]） */
    val stabilizeHint: StateFlow<Boolean> = _stabilizeHint.asStateFlow()

    fun consumeStabilizeHintDone() { _stabilizeHint.value = false }

    fun onFrame() = withController { controller ->
        val snapshot = controller.frame()
        // T07B：首坎站稳提示（一次性；恢复局同 sessionId 提示可再发——见 R2 说明）
        if (controller.consumeStabilizeHint()) _stabilizeHint.value = true
        coordinator?.let { sensory ->
            val events = controller.drainPhaseEvents()
            sensory.onPhaseEvents(events)
            if (events.isNotEmpty()) saveSnapshotNow() // 越相位即存（契约）
            sensory.onFrame(
                dtMs = snapshot.frameDtMs,
                metersDelta = snapshot.metersDelta,
                walking = snapshot.session == SessionState.WALKING,
            )
            if (snapshot.session == SessionState.COMPLETED || snapshot.session == SessionState.ABANDONED) {
                sensory.release() // 终态：释放音频与振动，迟到帧不再发声
                clearSnapshot() // 通关：清除恢复候选
            }
        }
        if (snapshot != _walk.value) {
            _walk.value = snapshot
        }
    }

    fun onStick(deflection: Float) = withController {
        it.onStick(deflection)
        val snapshot = it.snapshot()
        // 焦点丢失暂停后的新输入：行走由新输入驱动（不自动前进）；
        // 音频恢复前必须确认焦点已获准
        if (snapshot.session == SessionState.WALKING) attemptAudioResume()
        _walk.value = snapshot
    }

    fun onStickReleased() = withController {
        it.onStickReleased()
        _walk.value = it.snapshot()
    }

    fun onAppBackground() = withController {
        it.onAppBackground()
        coordinator?.pause()
        _walk.value = it.snapshot()
        saveSnapshotNow() // 进入后台即存（不依赖 onDestroy）
    }

    fun onAppForeground() = withController {
        it.onAppForeground()
        // 播放不自动恢复行走；等新输入时 onStick 再 resume
        _walk.value = it.snapshot()
    }

    fun pauseForDialog() = withController {
        it.pause()
        coordinator?.pause()
        _walk.value = it.snapshot()
        saveSnapshotNow() // 状态转换即存
    }

    fun resumeFromDialog() = withController {
        it.resume()
        attemptAudioResume()
        _walk.value = it.snapshot()
        saveSnapshotNow()
    }

    /**
     * 外部中断（来电/焦点丢失/耳机断连/后台）后的「继续」入口：
     * 回到 READY 等待新输入；音频恢复以焦点重新获准为前提，
     * 未获准则静默继续（不外放、不阻塞行走）。
     */
    fun resumeAfterInterruption() = withController {
        it.resume()
        attemptAudioResume()
        _walk.value = it.snapshot()
    }

    fun abandon() = withController {
        it.abandon()
        coordinator?.release()
        _walk.value = it.snapshot()
        clearSnapshot() // 主动放弃：清除恢复候选
    }

    override fun onCleared() {
        coordinator?.release()
        teardownAudioInterruptionHandling()
        super.onCleared()
    }

    // ---- 音频焦点 / 耳机断连（§3.2.3 音频中断；真机验证见 ASSETS/验收文档） ----

    private fun setupAudioInterruptionHandling() {
        audioManager = app.getSystemService(AudioManager::class.java) ?: return
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
                        onExternalAudioInterruption()
                    }
                    // AUDIOFOCUS_GAIN：不自动行走、不自动恢复播放——由用户新输入驱动
                }
            }
            .build()
        focusRequest = request
        val result = audioManager?.requestAudioFocus(request) ?: 0
        focusGate.onRequestResult(result)
        audioResumed = focusGate.canResumeAudio()
        // 首次申请被拒也必须静默：协调器从此不放脚步、不启 loop（距离照常推进）
        coordinator?.setAudioAllowed(focusGate.canResumeAudio())
        focusRegistered = true

        // 耳机断连：立即暂停播放，避免突然外放（系统广播 ACTION_AUDIO_BECOMING_NOISY）
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context?, intent: Intent?) {
                if (intent?.action == AudioManager.ACTION_AUDIO_BECOMING_NOISY) {
                    focusGate.onFocusLoss()
                    audioResumed = false
                    coordinator?.setAudioAllowed(false)
                    onExternalAudioInterruption()
                }
            }
        }
        noisyReceiver = receiver
        ContextCompat.registerReceiver(
            app,
            receiver,
            IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY),
            ContextCompat.RECEIVER_NOT_EXPORTED,
        )
    }

    /**
     * 恢复音频的前置：重新申请焦点并检查结果；
     * 未获准不得出声——脚步与待启环境层全部静默（[SensoryCoordinator.setAudioAllowed]），
     * 距离与相位照常推进，不阻塞行走。
     */
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
            coordinator?.setAudioAllowed(true) // 先放开许可：待启层按当前相位/淡入启动
            coordinator?.resume()
        } else {
            audioResumed = false // 焦点被拒：保持静默（脚步不播、loop 不启、不补播）
            coordinator?.setAudioAllowed(false)
        }
    }

    /** 来电/切音乐/拔耳机：暂停会话与播放；不自动恢复 */
    private fun onExternalAudioInterruption() {
        withController { controller ->
            if (controller.stateMachine.state == SessionState.WALKING ||
                controller.stateMachine.state == SessionState.READY
            ) {
                controller.pause()
                coordinator?.pause()
                _walk.value = controller.snapshot()
            }
        }
    }

    private fun teardownAudioInterruptionHandling() {
        if (focusRegistered) {
            focusRequest?.let { audioManager?.abandonAudioFocusRequest(it) }
            focusRegistered = false
        }
        noisyReceiver?.let { runCatching { app.unregisterReceiver(it) } }
        noisyReceiver = null
    }

    private fun observeVibrationSetting() {
        viewModelScope.launch {
            settingsRepository.settings
                .map { it.vibrationEnabled }
                .distinctUntilChanged()
                .collect { enabled -> coordinator?.setVibrationEnabled(enabled) }
        }
    }
}
