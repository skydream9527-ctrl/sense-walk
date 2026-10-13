package com.sensewalk.app.domain.sensory

import com.sensewalk.app.domain.phase.PhaseEvent
import com.sensewalk.app.domain.scene.AudioLayerDef
import com.sensewalk.app.domain.scene.PhaseChannel
import com.sensewalk.app.domain.scene.SceneConfig
import kotlin.math.min
import kotlin.random.Random

/**
 * 感官协调器（T05，§8.2 / §12.1 SensoryState 的执行侧）。
 *
 * 消费会话控制器给出的相位事件与帧增量，驱动 [SensoryBackend]：
 * - 脚步：由**有效距离**按步幅（0.7 m）积累触发，不按渲染帧、不靠时间；
 *   静止（无新增米数）、暂停、终态不产生新脚步；变体与音量/音高随机避免机械感；
 * - 环境 loop：相位触发后开始（每层只启动一次），按 fadeMs 时间淡入；
 *   **淡入只在有新增有效距离时推进**（§8.2 停走冻结增益）；暂停冻结在当前值，
 *   恢复继续，不重启轨道、不重置相位；
 * - 音频焦点门控（[setAudioAllowed]）：焦点未获准时**不出声**——脚步只积累
 *   步幅不调用后端（获准后不补播旧脚步），新解锁的环境层记为待启不 startLoop；
 *   距离、相位、淡入进度照常推进。获准后按当前淡入进度启动待启层，
 *   已启动过的层不重复创建；
 * - 振动：已解锁的 everyNSteps 规则跟步伐；尊重 vibrationEnabled；
 * - 终态 [release] 后一切后端调用停止。
 *
 * 纯 Kotlin：随机源可注入，全部行为可 JVM 单测。
 */
class SensoryCoordinator(
    private val config: SceneConfig,
    private val backend: SensoryBackend,
    private val random: Random = Random.Default,
    private val strideMeters: Float = DEFAULT_STRIDE_METERS,
) {

    private data class StepLayer(val volume: Float, val variants: Int)

    private data class LoopFade(val target: Float, val fadeMs: Float, var elapsedMs: Float)

    private val stepLayers = LinkedHashMap<String, StepLayer>()
    private val loops = LinkedHashMap<String, LoopFade>()

    /** 已真正 startLoop 的层（与 [loops] 分离：焦点未获准时层可能只是"待启"） */
    private val startedLoops = HashSet<String>()
    private var hapticPattern: String? = null
    private var hapticEveryN = 1L

    private var stepAccumMeters = 0f
    private var stepCount = 0L
    private var vibrationEnabled = true
    private var released = false

    /** 音频许可（音频焦点已获准）。默认 true：由持有者在会话建立时按首次申请结果置位。 */
    private var audioAllowed = true

    /** 相位事件（来自控制器 drainPhaseEvents）；重复事件不会重启已启动的层 */
    fun onPhaseEvents(events: List<PhaseEvent>) {
        if (released) return
        for (event in events) {
            val phase = event.phase
            when (phase.channel) {
                PhaseChannel.AUDIO -> {
                    val layerId = phase.layer ?: continue
                    when (val def = config.layers[layerId]) {
                        is AudioLayerDef.StepOneShot -> {
                            if (layerId !in stepLayers) {
                                val variants = def.files.size.coerceAtLeast(1)
                                stepLayers[layerId] = StepLayer(phase.toVolume ?: 0.25f, variants)
                            }
                        }
                        is AudioLayerDef.Loop -> {
                            if (layerId !in loops) {
                                val target = (phase.toVolume ?: 0.3f).coerceIn(0f, 1f)
                                val fadeMs = (phase.fadeMs ?: 0).toFloat()
                                loops[layerId] = LoopFade(target, fadeMs, 0f)
                                if (audioAllowed) {
                                    startLoopNow(layerId)
                                }
                                // 焦点未获准：层记入 loops 但不出声，待 setAudioAllowed(true) 启动
                            }
                        }
                        null -> Unit // 校验器已保证引用存在；这里防御性忽略
                    }
                }
                PhaseChannel.HAPTIC -> {
                    hapticPattern = phase.pattern
                    hapticEveryN = (phase.everyNSteps ?: 1).coerceAtLeast(1).toLong()
                }
                PhaseChannel.VISUAL -> Unit // 视觉由 SensoryState 直接驱动 UI，不经后端
            }
        }
    }

    /**
     * 每帧调用（与控制器同一帧）。
     * [metersDelta] 为本帧新增**有效**米数：> 0 表示在前进——
     * 站立、回退、暂停、终态时为 0，淡入与脚步都随之冻结。
     */
    fun onFrame(dtMs: Float, metersDelta: Float, walking: Boolean) {
        if (released || !walking) return
        val moving = metersDelta > 0f
        if (moving && dtMs > 0f) {
            // 环境淡入只在实际前进时推进（停走冻结当前增益）；
            // 焦点未获准的层也照常积累进度，获准启动时直接落在当前增益
            for ((layerId, fade) in loops) {
                if (fade.fadeMs > 0f && fade.elapsedMs < fade.fadeMs) {
                    fade.elapsedMs = min(fade.elapsedMs + dtMs, fade.fadeMs)
                    if (layerId in startedLoops) {
                        backend.setLoopGain(layerId, fade.target * (fade.elapsedMs / fade.fadeMs))
                    }
                }
            }
        }
        if (moving && stepLayers.isNotEmpty()) {
            stepAccumMeters += metersDelta
            while (stepAccumMeters >= strideMeters) {
                stepAccumMeters -= strideMeters
                stepCount++
                if (audioAllowed) {
                    for ((layerId, step) in stepLayers) {
                        val variant = if (step.variants > 1) random.nextInt(step.variants) else 0
                        val volume = (step.volume * (0.9f + random.nextFloat() * 0.2f)).coerceIn(0f, 1f)
                        val pitch = 0.97f + random.nextFloat() * 0.06f
                        backend.playStep(layerId, variant, volume, pitch)
                    }
                }
                if (vibrationEnabled && stepCount % hapticEveryN == 0L) {
                    hapticPattern?.let { backend.vibrate(it) }
                }
            }
        }
    }

    /**
     * 音频许可门控（音频焦点申请/丢失/重申请的结果）。
     * false：脚步与待启 loop 全部不出声（距离/相位/淡入照常推进，振动不受影响）；
     * true：按当前淡入进度启动尚未启动的层（已启动的不重复创建，也不补播旧脚步）。
     */
    fun setAudioAllowed(allowed: Boolean) {
        if (released || allowed == audioAllowed) return
        audioAllowed = allowed
        if (allowed) {
            for ((layerId, _) in loops) {
                if (layerId !in startedLoops) startLoopNow(layerId)
            }
        }
    }

    /** 真正启动一个 loop 并落到当前淡入进度对应的增益 */
    private fun startLoopNow(layerId: String) {
        val fade = loops[layerId] ?: return
        startedLoops.add(layerId)
        backend.startLoop(layerId)
        backend.setLoopGain(layerId, currentGain(fade))
    }

    private fun currentGain(fade: LoopFade): Float =
        if (fade.fadeMs <= 0f) fade.target else fade.target * (fade.elapsedMs / fade.fadeMs)

    /** 暂停（对话框/后台/音频焦点丢失/耳机断连）：停播不释放，淡入进度冻结 */
    fun pause() {
        if (released) return
        backend.pauseAll()
        backend.stopVibrate()
    }

    /** 恢复播放（淡入从冻结值继续，不重启轨道） */
    fun resume() {
        if (released) return
        backend.resumeAll()
    }

    /** 终态（通关/放弃/离开会话）：停止并释放一切资源，之后的调用全部无效 */
    fun release() {
        if (released) return
        released = true
        backend.releaseAll()
        backend.stopVibrate()
    }

    fun setVibrationEnabled(enabled: Boolean) {
        vibrationEnabled = enabled
        if (!enabled) backend.stopVibrate()
    }

    /** 已触发的脚步事件数（调试/测试） */
    val stepEventCount: Long get() = stepCount

    companion object {
        /** 虚走统一步幅（§8.2，与 strideMeters 设置一致） */
        const val DEFAULT_STRIDE_METERS = 0.7f
    }
}
