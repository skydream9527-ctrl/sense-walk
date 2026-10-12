package com.sensewalk.app.domain.phase

import com.sensewalk.app.domain.scene.Phase
import com.sensewalk.app.domain.scene.SceneConfig

/** 一次相位触发事件（含触发时的米数，供调试/快照记录） */
data class PhaseEvent(val phase: Phase, val firedAtMeters: Float)

/** 音频层目标（真实淡入由 T05 音频引擎按 fadeMs 执行；本阶段只输出目标） */
data class AudioTarget(val toVolume: Float, val fadeMs: Int)

/** 振动规则：跟步伐，每 N 步触发一次 */
data class HapticRule(val pattern: String, val everyNSteps: Int)

/**
 * 当前米数下的各通道感官目标（§12.1 SensoryState）。
 * 视觉 opacity 是米数的纯函数：meters 不变 → 输出不变（S4）。
 */
data class SensoryState(
    /** layerId → 当前 opacity（未触发的视觉层为 0） */
    val visualOpacities: Map<String, Float>,
    /** layerId → 目标音量（仅已触发的音频层；后触发的相位覆盖同层旧目标） */
    val audioTargets: Map<String, AudioTarget>,
    /** 已触发的振动规则 */
    val hapticRules: List<HapticRule>,
)

/**
 * 相位调度器（§8 / S4 / S9）。
 *
 * - 按 atMeters 触发、按配置顺序输出事件；每个 phase id 只触发一次；
 * - 同一距离的多通道相位在同一次 update 全部处理；
 * - 单次进度跨多个阈值时按序全部触发，不漏相位；
 * - 构造时先 update(0) 触发 atMeters=0 的黑幕相位；
 * - [preFiredPhaseIds] 供 T07 恢复用：已触发的不重复触发，
 *   感官目标直接按当前米数重建静态值（恢复不重播一次性提示）。
 *
 * 不持有时间、不接音频/振动引擎——只产生目标与事件。
 */
class PhaseScheduler(
    private val config: SceneConfig,
    preFiredPhaseIds: Set<String> = emptySet(),
) {

    private val fired = LinkedHashSet<String>(preFiredPhaseIds)

    /** 更新当前米数，返回本次新触发的事件（配置顺序；不依赖 phases 已排序，扫描全部） */
    fun update(meters: Float): List<PhaseEvent> {
        if (!meters.isFinite()) return emptyList()
        val events = mutableListOf<PhaseEvent>()
        for (phase in config.phases) {
            if (phase.id in fired) continue
            if (phase.atMeters.toFloat() <= meters) {
                fired.add(phase.id)
                events.add(PhaseEvent(phase, meters))
            }
        }
        return events
    }

    val firedPhaseIds: Set<String> get() = fired.toSet()

    /** 当前米数下的感官目标；纯函数，meters 不变时两次调用结果一致 */
    fun sensoryState(meters: Float): SensoryState {
        val m = if (meters.isFinite()) meters else 0f
        val visual = mutableMapOf<String, Float>()
        val audio = mutableMapOf<String, AudioTarget>()
        val haptics = mutableListOf<HapticRule>()

        config.visualLayers.keys.forEach { visual[it] = 0f }
        config.phases.forEach { p ->
            if (p.id !in fired) return@forEach
            when (p.channel) {
                com.sensewalk.app.domain.scene.PhaseChannel.VISUAL ->
                    visual[p.layer ?: return@forEach] = visualOpacity(p, m)
                com.sensewalk.app.domain.scene.PhaseChannel.AUDIO ->
                    audio[p.layer ?: return@forEach] = AudioTarget(p.toVolume ?: 0f, p.fadeMs ?: 0)
                com.sensewalk.app.domain.scene.PhaseChannel.HAPTIC ->
                    haptics.add(HapticRule(p.pattern ?: return@forEach, p.everyNSteps ?: 1))
            }
        }
        return SensoryState(visual, audio, haptics)
    }

    /** opacity = toOpacity × smoothstep((meters − atMeters) / fadeMeters)；fade=0 为阶跃 */
    private fun visualOpacity(p: Phase, meters: Float): Float {
        val target = p.toOpacity ?: return 0f
        if (!target.isFinite() || target <= 0f) return 0f
        val fade = p.fadeMeters ?: 0
        if (fade <= 0) return if (meters >= p.atMeters.toFloat()) target else 0f
        val x = ((meters - p.atMeters) / fade).coerceIn(0f, 1f)
        val smooth = x * x * (3f - 2f * x)
        return target * smooth
    }
}
