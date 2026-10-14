package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.session.MonotonicClock
import kotlin.math.min

/**
 * 实走计距引擎（T06 / SW-001 F-001 修订版，§3.3 实走 / S5 / S8）。
 *
 * TYPE_STEP_COUNTER 是**唯一**计距源；首事件只建立基线，此后
 * 距离 = 步数增量 × 步长；**单次有效事件增量 ≤ 1.4 m/s × 有效事件间隔**
 * ——零/负有效间隔的增量恒为 0（1.4×0=0），任何同刻事件序列都刷不出进度。
 *
 * 事件时间语义：调用方传入的事件时间必须来自**同一单调基准**
 * （Android 侧使用 elapsedRealtime 基准，见 StepSensorSource/服务说明；
 * 系统休眠不停表，设备重启基准归零且 counter 同步重置 → 走读数下降路径）。
 *
 * S8 边界：
 * - 首次事件/重注册后/暂停恢复后首事件只设基线，不涨距；
 * - 重复读数（同值）整体忽略，不推进时间基线；
 * - 读数下降（传感器/设备重启重置）重建基线，不涨距、不吞后续真实增量；
 * - 时间回退（早于上一接受事件）的乱序事件整体忽略——其步数会在下一个
 *   正常事件中按计数差自然带回，且受该事件的间隔封顶；
 * - **同刻合并**：与上一接受事件同刻（间隔 0）的高读数只推进计数基线、
 *   不动时间基线、本事件 0 米；被合并的步数在下一个正间隔事件中一次性
 *   计距并封顶（连续同刻刷量无效，真实批量不丢）；
 * - 暂停期间不补算：暂停即武装重定基线，暂停期与恢复后的第一个事件都只建基线；
 * - 步长非有限值（NaN/Infinity）被拒绝并保持原值，不污染 meters。
 *
 * 纯 Kotlin：时钟可注入，全部行为可 JVM 单测（S5/S8）。
 */
class RealWalkEngine(
    private val clock: MonotonicClock,
    strideMeters: Float = DEFAULT_STRIDE_METERS,
) {

    /** 有效步长（米）；钳制到 [MIN_STRIDE_METERS, MAX_STRIDE_METERS]；非有限值被拒绝 */
    var strideMeters: Float = sanitizeStride(strideMeters, DEFAULT_STRIDE_METERS)
        set(value) {
            field = sanitizeStride(value, field)
        }

    /** counter 累计读数基线；null = 尚未建立（下一事件只建基线） */
    private var baselineCount: Long? = null

    /** 上一个被接受事件的读数与时间（用于增量与有效间隔） */
    private var lastAcceptedCount: Long = -1
    private var lastAcceptedMs: Long = Long.MIN_VALUE

    /** 暂停/恢复/重注册后：下一事件只重建基线 */
    private var rebasePending = true

    private var paused = false
    private var terminal = false

    /**
     * counter 事件处理：返回本次**有效新增米数**与有效间隔
     * （0 米 = 基线/重复/乱序/同刻合并/暂停/终态）。[stepCount] 为系统累计
     * 步数（只增），[eventTimeMs] 为同一单调基准的事件时间戳。
     */
    fun onCounterEvent(stepCount: Long, eventTimeMs: Long): StepDelta {
        if (terminal) return StepDelta(0f, 0L)
        if (paused) {
            // 暂停期间不补算：持续把基线推到最新读数，恢复后从当前起步
            baselineCount = stepCount
            rebasePending = true
            return StepDelta(0f, 0L)
        }
        if (rebasePending || baselineCount == null) {
            baselineCount = stepCount
            lastAcceptedCount = stepCount
            lastAcceptedMs = eventTimeMs
            rebasePending = false
            return StepDelta(0f, 0L)
        }
        if (stepCount == lastAcceptedCount) return StepDelta(0f, 0L) // 重复读数：整体忽略
        if (stepCount < lastAcceptedCount) {
            // 读数下降（设备/传感器重置重启）：重建基线，不涨距
            baselineCount = stepCount
            lastAcceptedCount = stepCount
            lastAcceptedMs = eventTimeMs
            return StepDelta(0f, 0L)
        }
        if (eventTimeMs < lastAcceptedMs) {
            // 时间回退的乱序事件：整体忽略；其步数由下一正常事件的计数差自然带回
            return StepDelta(0f, 0L)
        }

        val steps = stepCount - lastAcceptedCount
        val intervalMs = eventTimeMs - lastAcceptedMs
        if (intervalMs <= 0L) {
            // 同刻合并：本事件 0 米（1.4×0=0）；只推进计数基线，时间基线不动——
            // 被合并的步数在下一个正间隔事件中统一计距并封顶
            lastAcceptedCount = stepCount
            return StepDelta(0f, 0L)
        }
        val raw = steps * strideMeters
        val capMeters = MAX_SPEED_MPS * intervalMs / 1000f
        val delta = min(raw, capMeters).coerceAtLeast(0f)

        lastAcceptedCount = stepCount
        lastAcceptedMs = eventTimeMs
        return StepDelta(delta, intervalMs)
    }

    /** detector 单步事件：只用于已解锁的脚步音/振同步，绝不计距 */
    fun onDetectorStep(): Boolean = !terminal && !paused

    /** 暂停：立即武装重定基线（暂停期与恢复后首事件不补算） */
    fun pause() {
        paused = true
        rebasePending = true
    }

    /** 恢复：保持武装，下一事件只建基线 */
    fun resume() {
        paused = false
        rebasePending = true
    }

    /** 传感器重注册/会话接管：下一事件只建基线 */
    fun restartBaseline() {
        rebasePending = true
    }

    /** 终态：此后一切事件零增量 */
    fun markTerminal() {
        terminal = true
    }

    val isTerminal: Boolean get() = terminal
    val isPaused: Boolean get() = paused

    private fun sanitizeStride(value: Float, fallback: Float): Float =
        if (value.isFinite()) value.coerceIn(MIN_STRIDE_METERS, MAX_STRIDE_METERS) else fallback

    /** counter 事件的有效结果：增量米数 + 计算封顶所用有效间隔 */
    data class StepDelta(val meters: Float, val intervalMs: Long)

    companion object {
        /** 虚走/实走统一步长默认（§3.3） */
        const val DEFAULT_STRIDE_METERS = 0.70f
        const val MIN_STRIDE_METERS = 0.45f
        const val MAX_STRIDE_METERS = 0.95f

        /** §4.3 硬顶：单事件距离上限速率（Δd ≤ 1.4 m/s × 有效间隔；间隔 0 ⇒ 0） */
        const val MAX_SPEED_MPS = 1.4f
    }
}
