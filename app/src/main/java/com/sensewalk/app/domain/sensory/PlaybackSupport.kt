package com.sensewalk.app.domain.sensory

/**
 * 单个环境 loop 的播放器生命周期状态机（纯 Kotlin，供 Android 后端驱动）。
 *
 * 背景：MediaPlayer.prepare() 是同步阻塞，改用 prepareAsync 后，
 * 「准备中暂停 / 准备中释放 / 迟到的 OnPrepared 回调」都需要明确语义：
 * - 准备期间请求暂停 → 就绪后保持暂停（不自动播放）；
 * - 准备期间请求开始 → 就绪后播放；
 * - RELEASED 之后的一切回调与请求全部吸收（不重新播放）；
 * - 增益在就绪前缓存，就绪后应用。
 */
class LoopPlayerState {

    enum class Phase { PREPARING, PLAYING, PAUSED, RELEASED }

    var phase: Phase = Phase.PREPARING
        private set

    /** 当前有效增益（就绪前缓存） */
    var gain: Float = 0f
        private set

    private var startWhenPrepared = false

    /** OnPreparedListener 回调：迟到（已释放）时吸收 */
    fun onPrepared() {
        if (phase == Phase.PREPARING) {
            phase = if (startWhenPrepared) Phase.PLAYING else Phase.PAUSED
        }
    }

    /** OnErrorListener 后调用；已释放时吸收 */
    fun onError() {
        release()
    }

    fun requestStart() {
        when (phase) {
            Phase.PREPARING -> startWhenPrepared = true
            Phase.PAUSED -> phase = Phase.PLAYING
            Phase.PLAYING, Phase.RELEASED -> Unit
        }
    }

    fun requestPause() {
        when (phase) {
            Phase.PREPARING -> startWhenPrepared = false
            Phase.PLAYING -> phase = Phase.PAUSED
            Phase.PAUSED, Phase.RELEASED -> Unit
        }
    }

    /** 就绪前缓存，由后端在 PREPARED 状态下应用到播放器 */
    fun setGain(value: Float) {
        gain = value.coerceIn(0f, 1f)
    }

    fun release() {
        phase = Phase.RELEASED
    }

    val isPrepared: Boolean get() = phase == Phase.PLAYING || phase == Phase.PAUSED
}

/**
 * 脚步层异步加载状态（纯 Kotlin）。
 * SoundPool.load 是异步的：未加载完成的变体不可播放；
 * 加载失败给明确诊断（层名 + 文件 + soundId），不静默丢弃。
 */
class StepLayerLoadState(
    val layerId: String,
    val soundIds: List<Int>,
    private val fileBySoundId: Map<Int, String>,
) {

    private val loaded = mutableSetOf<Int>()
    private val failed = mutableMapOf<Int, String>()

    /** SoundPool OnLoadCompleteListener 回调 */
    fun onLoadComplete(soundId: Int, success: Boolean) {
        if (soundId !in soundIds) return
        if (success) loaded.add(soundId) else failed[soundId] = fileBySoundId[soundId] ?: "?"
    }

    /**
     * 指定变体对应的可播 soundId；未加载完成时轮换到其他已加载变体，
     * 全部未就绪返回 null（跳过本次脚步，不阻塞步伐）。
     */
    fun playableVariant(variant: Int): Int? {
        if (loaded.isEmpty()) return null
        if (soundIds.isEmpty()) return null
        val ordered = soundIds.filter { it in loaded }
        if (ordered.isEmpty()) return null
        return ordered[variant.mod(ordered.size)]
    }

    /** 加载失败诊断（供日志/ASSETS 核对） */
    val failureDiagnostics: List<String>
        get() = failed.map { (id, file) -> "脚步层 '$layerId' 素材加载失败: $file (soundId=$id)" }

    val loadedCount: Int get() = loaded.size
}

/**
 * 音频焦点门（纯 Kotlin）：恢复播放前必须确认焦点已获准；
 * 未获准时不得恢复音频。焦点恢复/耳机重连不自动行走也不自动恢复播放。
 */
class AudioFocusGate {

    var granted: Boolean = false
        private set

    fun onRequestResult(result: Int) {
        granted = result == REQUEST_GRANTED
    }

    fun onFocusLoss() {
        granted = false
    }

    /** 恢复音频的前置检查 */
    fun canResumeAudio(): Boolean = granted

    companion object {
        /** AudioManager.AUDIOFOCUS_REQUEST_GRANTED（避免 Android 依赖） */
        const val REQUEST_GRANTED = 1
    }
}

/**
 * 活跃脚步流跟踪（纯 Kotlin）：暂停/中断时停止所有在播脚步流；
 * 恢复不补播旧脚步——新步伐重新开始。
 */
class ActiveStepStreams {

    private val active = mutableSetOf<Int>()

    /** SoundPool.play 返回的 streamId（0 表示失败，忽略） */
    fun onStreamStarted(streamId: Int) {
        if (streamId != 0) active.add(streamId)
    }

    /** 返回需要停止的流并清空跟踪；调用方对每个 id 执行 soundPool.stop */
    fun stopAll(): List<Int> {
        val toStop = active.toList()
        active.clear()
        return toStop
    }

    /** 恢复播放：不恢复旧流（无补播语义）；返回 null 表示无事可做 */
    fun resumeStreams(): List<Int>? = null

    val activeCount: Int get() = active.size
}
