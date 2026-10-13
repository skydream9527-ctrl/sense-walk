package com.sensewalk.app.engine.sensory

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.media.SoundPool
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log
import com.sensewalk.app.domain.scene.AudioLayerDef
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.sensory.ActiveStepStreams
import com.sensewalk.app.domain.sensory.LoopPlayerState
import com.sensewalk.app.domain.sensory.SensoryBackend
import com.sensewalk.app.domain.sensory.StepLayerLoadState
import java.util.concurrent.atomic.AtomicBoolean

/**
 * 感官后端的 Android 实现（T05 收尾版）：
 * - 脚步 one-shot：SoundPool；异步加载状态跟踪（[StepLayerLoadState]）——
 *   未加载完成不播放，加载失败给明确诊断日志；
 * - 环境 loop：每层一个 MediaPlayer，**prepareAsync**（不阻塞主线程），
 *   生命周期由 [LoopPlayerState] 管理：准备期暂停/释放、迟到 OnPrepared 吸收；
 * - 暂停/中断：停止活跃脚步流（[ActiveStepStreams]），恢复不补播旧脚步；
 * - 振动：Vibrator 波形（模式表见 [vibrationEffect]）。
 *
 * 素材现状（见 ASSETS.md）：场景配置的音频层若仍为显式开发占位
 * （placeholder，无 file）则跳过并记日志，不伪造声音。
 */
class AndroidSensoryBackend(
    private val context: Context,
    private val config: SceneConfig,
) : SensoryBackend {

    private val soundPool: SoundPool = SoundPool.Builder()
        .setMaxStreams(MAX_STREAMS)
        .setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_GAME)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build(),
        )
        .build()

    /** layerId → 异步加载状态 */
    private val stepLayers = mutableMapOf<String, StepLayerLoadState>()

    /** layerId → (MediaPlayer, 生命周期状态) */
    private data class LoopEntry(val player: MediaPlayer, val state: LoopPlayerState)

    private val loops = mutableMapOf<String, LoopEntry>()
    private val stepStreams = ActiveStepStreams()
    private val released = AtomicBoolean(false)

    private val vibrator: Vibrator? = resolveVibrator()

    init {
        // SoundPool 只有单个全局加载监听器：统一分发给各层（在 load 之前注册）
        soundPool.setOnLoadCompleteListener { _, sampleId, status ->
            stepLayers.values.forEach { it.onLoadComplete(sampleId, status == 0) }
            if (status != 0) Log.w(TAG, "脚步素材 soundId=$sampleId 异步加载失败 (status=$status)")
        }
        // 异步预加载脚步变体；占位层（无 files）记录后跳过
        for ((layerId, def) in config.layers) {
            if (def is AudioLayerDef.StepOneShot && def.files.isNotEmpty()) {
                val fileById = mutableMapOf<Int, String>()
                for (file in def.files) {
                    val id = loadSound(file)
                    if (id != null) fileById[id] = file
                }
                if (fileById.isEmpty()) {
                    Log.i(TAG, "脚步层 '$layerId' 素材未入库（占位），静默跳过")
                } else {
                    stepLayers[layerId] = StepLayerLoadState(layerId, fileById.keys.toList(), fileById)
                }
            }
        }
    }

    override fun startLoop(layerId: String) {
        if (released.get() || loops.containsKey(layerId)) return
        val def = config.layers[layerId] as? AudioLayerDef.Loop ?: return
        val file = def.file ?: run {
            Log.i(TAG, "环境层 '$layerId' 为开发占位（无 file），本轮不播放")
            return
        }
        try {
            val afd = context.assets.openFd(file)
            val player = MediaPlayer()
            val entry = LoopEntry(player, LoopPlayerState())
            player.setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
            afd.close()
            player.isLooping = true
            player.setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build(),
            )
            player.setOnPreparedListener { p ->
                if (p !== player) return@setOnPreparedListener
                entry.state.onPrepared()
                if (entry.state.isPrepared) {
                    // 就绪后应用缓存的增益；新层从 0 淡入
                    p.setVolume(entry.state.gain, entry.state.gain)
                    if (entry.state.phase == LoopPlayerState.Phase.PLAYING) p.start()
                }
                if (entry.state.phase == LoopPlayerState.Phase.RELEASED) {
                    // 准备期间已终态：迟到回调只做清理
                    runCatching { p.release() }
                }
            }
            player.setOnErrorListener { p, what, extra ->
                Log.w(TAG, "环境层 '$layerId' 播放错误 (what=$what extra=$extra)，释放该层")
                entry.state.onError()
                runCatching { p.release() }
                loops.remove(layerId)
                true
            }
            // 异步准备，不阻塞主线程；初始按"应播放"登记
            entry.state.requestStart()
            player.prepareAsync()
            loops[layerId] = entry
        } catch (e: Exception) {
            Log.w(TAG, "环境层 '$layerId' 启动失败（$file）：${e.message}")
        }
    }

    override fun setLoopGain(layerId: String, gain: Float) {
        val entry = loops[layerId] ?: return
        entry.state.setGain(gain)
        if (entry.state.isPrepared) {
            entry.player.setVolume(entry.state.gain, entry.state.gain)
        }
    }

    override fun playStep(layerId: String, variant: Int, volume: Float, pitchFactor: Float) {
        val layer = stepLayers[layerId] ?: return // 占位层：无声（ASSETS.md 记录）
        val soundId = layer.playableVariant(variant) ?: return // 变体未加载完成：跳过本次
        val streamId = soundPool.play(soundId, volume, volume, 1, 0, pitchFactor.coerceIn(0.5f, 2f))
        stepStreams.onStreamStarted(streamId)
        if (streamId == 0) Log.w(TAG, "脚步播放失败（layer=$layerId variant=$variant）")
    }

    override fun pauseAll() {
        // 环境 loop：播放中的暂停（准备中的登记为就绪后暂停）
        loops.values.forEach { entry ->
            val wasPlaying = entry.state.phase == LoopPlayerState.Phase.PLAYING
            entry.state.requestPause()
            if (wasPlaying) runCatching { entry.player.pause() }
        }
        // 脚步：停止所有在播流；恢复不补播
        stepStreams.stopAll().forEach { streamId ->
            runCatching { soundPool.stop(streamId) }
        }
    }

    override fun resumeAll() {
        if (released.get()) return
        loops.values.forEach { entry ->
            val wasPausedPrepared = entry.state.phase == LoopPlayerState.Phase.PAUSED
            entry.state.requestStart()
            if (wasPausedPrepared) runCatching { entry.player.start() }
        }
        // 脚步流不恢复：新步伐重新开始（不补播旧脚步）
    }

    override fun releaseAll() {
        if (!released.compareAndSet(false, true)) return
        loops.values.forEach { entry ->
            entry.state.release()
            runCatching {
                entry.player.stop()
                entry.player.release()
            }
        }
        loops.clear()
        stepStreams.stopAll().forEach { streamId ->
            runCatching { soundPool.stop(streamId) }
        }
        runCatching { soundPool.release() }
    }

    override fun vibrate(patternId: String) {
        val effect = vibrationEffect(patternId) ?: return
        vibrator?.vibrate(effect)
    }

    override fun stopVibrate() {
        vibrator?.cancel()
    }

    private fun loadSound(file: String): Int? = try {
        val afd = context.assets.openFd(file)
        val id = soundPool.load(afd, 1)
        afd.close()
        if (id != 0) id else null // 0 = 同步失败
    } catch (e: Exception) {
        Log.w(TAG, "脚步素材加载失败（$file）：${e.message}")
        null
    }

    private fun resolveVibrator(): Vibrator? =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager)?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        }

    /** 振动模式表（§7 各景单页定义；力度轻、跟步伐） */
    private fun vibrationEffect(patternId: String): VibrationEffect? = when (patternId) {
        "footstep_soft" -> VibrationEffect.createOneShot(24L, 90)
        "footstep_sand" -> VibrationEffect.createOneShot(32L, 70)
        "pulse_slow" -> VibrationEffect.createWaveform(longArrayOf(0L, 40L), intArrayOf(0, 60), -1)
        else -> {
            Log.i(TAG, "未知振动模式 '$patternId'，跳过")
            null
        }
    }

    private companion object {
        const val TAG = "SensoryBackend"
        const val MAX_STREAMS = 4
    }
}
