package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.session.MonotonicClock
import kotlin.math.min

/**
 * 实走计距引擎（T06，§3.3 实走 / S5 / S8）。
 *
 * TYPE_STEP_COUNTER 是**唯一**计距源；首事件只建立基线，此后
 * 距离 = 步数增量 × 步长；单次事件增量不超过 `1.4 m/s × 有效事件间隔`
 * （与 §4.3 硬顶一致，注入「1 秒 10 步」的作弊序列也只得 ≤ 1.4 m）。
 *
 * S8 边界：
 * - 首次事件只设基线，不涨距；
 * - 重复读数（同值）忽略；读数下降（传感器/设备重启重置）重建基线，不涨距；
 * - 时间回退的乱序事件忽略；
 * - 同刻批量（间隔 0）按单步封顶，不密集刷距；
 * - 暂停期间不补算：暂停即武装重定基线，暂停期与恢复后的第一个事件都只建基线；
 * - 传感器重注册（服务重启等）调用 [restartBaseline]，下一事件只建基线。
 *
 * 步长默认 0.70 m，可设范围 0.45–0.95 m（越界钳制）。
 * 纯 Kotlin：时钟可注入，全部行为可 JVM 单测（S5/S8）。
 */
class RealWalkEngine(
    private val clock: MonotonicClock,
    strideMeters: Float = DEFAULT_STRIDE_METERS,
) {

    /** 有效步长（米）；设置钳制到 [MIN_STRIDE_METERS, MAX_STRIDE_METERS] */
    var strideMeters: Float = strideMeters.coerceIn(MIN_STRIDE_METERS, MAX_STRIDE_METERS)
        set(value) {
            field = value.coerceIn(MIN_STRIDE_METERS, MAX_STRIDE_METERS)
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

    /** counter 事件的有效结果：增量米数 + 计算封顶所用有效间隔 */
    data class StepDelta(val meters: Float, val intervalMs: Long)

    /**
     * counter 事件处理：返回本次**有效新增米数**与有效间隔
     * （0 米 = 基线/重复/乱序/暂停/终态）。[stepCount] 为系统累计步数（只增），
     * [eventTimeMs] 为事件时间戳。
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
        if (stepCount == lastAcceptedCount) return StepDelta(0f, 0L) // 重复读数：忽略（不推进时间基线）
        if (stepCount < lastAcceptedCount) {
            // 读数下降（设备/传感器重置重启）：重建基线，不涨距
            baselineCount = stepCount
            lastAcceptedCount = stepCount
            lastAcceptedMs = eventTimeMs
            return StepDelta(0f, 0L)
        }
        if (eventTimeMs < lastAcceptedMs) return StepDelta(0f, 0L) // 时间回退的乱序事件：忽略

        val steps = stepCount - lastAcceptedCount
        val intervalMs = eventTimeMs - lastAcceptedMs
        val raw = steps * strideMeters
        // 封顶：1.4 m/s × 有效间隔；同刻批量（间隔 0）按单步封顶（保守，只少算不多算）
        val capMeters = if (intervalMs <= 0L) strideMeters else MAX_SPEED_MPS * intervalMs / 1000f
        val delta = min(raw, capMeters).coerceAtLeast(0f)

        lastAcceptedCount = stepCount
        lastAcceptedMs = eventTimeMs
        return StepDelta(delta, intervalMs)
    }

    /** detector 单步事件：只用于已解锁的脚步音/振同步，绝不计距（返回 false 提示调用方仅作 cue） */
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

    companion object {
        /** 虚走/实走统一步长默认（§3.3） */
        const val DEFAULT_STRIDE_METERS = 0.70f
        const val MIN_STRIDE_METERS = 0.45f
        const val MAX_STRIDE_METERS = 0.95f

        /** §4.3 硬顶：作弊序列/异常间隔下的单事件距离上限速率 */
        const val MAX_SPEED_MPS = 1.4f
    }
}
