package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.phase.PhaseEvent
import com.sensewalk.app.domain.phase.PhaseScheduler
import com.sensewalk.app.domain.progress.CompletionGate
import com.sensewalk.app.domain.progress.ProgressAccumulator
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionEvent
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.session.SessionStateMachine

/**
 * 实走会话控制器（T06）：TYPE_STEP_COUNTER 唯一计距，[RealWalkEngine] 负责规则。
 *
 * 与 [VirtualWalkController] 共享同一组领域组件（进度/门禁/相位/状态机），
 * 快照复用其 [VirtualWalkController.Snapshot]，UI 无需区分两套类型。
 * 差异（诚实语义）：
 * - 无摇杆/惯性/地形系数——真实地形未知，不做虚拟减速；
 * - 行走从 [start]（按下「开始」即 FirstForward）起算，米数只来自 counter 增量；
 * - detector 事件只产出「步伐 cue」（已解锁脚步音/振同步），**不二次计距**，
 *   且节流 [MIN_CUE_INTERVAL_MS]——批量/密集 detector 事件不密集补播脚步。
 */
class RealWalkController(
    val config: SceneConfig,
    private val clock: MonotonicClock,
    strideMeters: Float = RealWalkEngine.DEFAULT_STRIDE_METERS,
) {

    val stateMachine = SessionStateMachine(clock)
    val accumulator = ProgressAccumulator(config.requiredDistanceMeters.toFloat())
    val gate = CompletionGate(config.requiredDistanceMeters.toFloat())
    val scheduler = PhaseScheduler(config)
    val engine = RealWalkEngine(clock, strideMeters)

    private var pendingEvents = mutableListOf<PhaseEvent>()
    private var lastCueMs: Long = Long.MIN_VALUE

    init {
        scheduler.update(0f) // 黑幕起点
    }

    /** 会话开始：按下「开始出门」即视为前行意图，进入 WALKING 等待步数 */
    fun start() {
        if (stateMachine.state == SessionState.READY) {
            stateMachine.dispatch(SessionEvent.FirstForward)
        }
    }

    /**
     * counter 事件（主线程调用）。返回本事件后的快照：
     * [VirtualWalkController.Snapshot.frameDtMs] 为有效事件间隔、
     * metersDelta 为本事件有效米数（供感官协调器淡入与步伐同步）。
     */
    fun onCounterEvent(stepCount: Long, eventTimeMs: Long): VirtualWalkController.Snapshot {
        val metersBefore = accumulator.meters
        val step = engine.onCounterEvent(stepCount, eventTimeMs)
        if (stateMachine.state == SessionState.WALKING && step.meters > 0f && !engine.isTerminal) {
            accumulator.advance(step.meters)
            pendingEvents += scheduler.update(accumulator.meters)
            if (gate.onMeters(accumulator.meters)) {
                // 通关唯一触发：清引擎、终态吸收后续事件
                engine.markTerminal()
                stateMachine.dispatch(SessionEvent.Complete)
            }
        }
        return snapshot(step.meters, step.intervalMs.toFloat(), metersBefore)
    }

    /**
     * detector 单步事件：返回是否应播放步伐 cue（音/振同步）。
     * 不计距；WALKING 之外或距上一 cue 不足 [MIN_CUE_INTERVAL_MS] 时抑制。
     */
    fun onDetectorStep(eventTimeMs: Long): Boolean {
        if (!engine.onDetectorStep()) return false
        if (stateMachine.state != SessionState.WALKING) return false
        if (lastCueMs != Long.MIN_VALUE && eventTimeMs - lastCueMs < MIN_CUE_INTERVAL_MS) return false
        lastCueMs = eventTimeMs
        return true
    }

    /** 暂停（对话框/通知/后台返回）：暂停期与恢复后首事件不补算（引擎重定基线） */
    fun pause() {
        if (isTerminal()) return
        stateMachine.dispatch(SessionEvent.Pause)
        engine.pause()
    }

    /** 恢复：回 WALKING（实走无摇杆可等，「继续走」即恢复计步），步数从当前重新起步 */
    fun resume() {
        if (isTerminal()) return
        stateMachine.dispatch(SessionEvent.Resume)
        if (stateMachine.state == SessionState.READY) {
            stateMachine.dispatch(SessionEvent.FirstForward)
        }
        engine.resume()
    }

    /** 未满距主动结束（通知「停止」/长按放弃） */
    fun abandon() {
        if (isTerminal()) return
        engine.markTerminal()
        stateMachine.dispatch(SessionEvent.Abandon)
    }

    fun drainPhaseEvents(): List<PhaseEvent> {
        val events = pendingEvents
        pendingEvents = mutableListOf()
        return events
    }

    fun snapshot(): VirtualWalkController.Snapshot = snapshot(0f, 0f, accumulator.meters)

    private fun snapshot(
        metersDelta: Float,
        frameDtMs: Float,
        metersBefore: Float,
    ): VirtualWalkController.Snapshot = VirtualWalkController.Snapshot(
        session = stateMachine.state,
        meters = accumulator.meters,
        sPos = accumulator.sPos,
        velocity = if (frameDtMs > 0f) metersDelta * 1000f / frameDtMs else 0f,
        deflection = 0f,
        sensory = scheduler.sensoryState(accumulator.meters),
        elapsedActiveMs = stateMachine.elapsedActiveMs,
        terrain = com.sensewalk.app.domain.scene.TerrainKind.FLAT,
        frameDtMs = frameDtMs,
        metersDelta = accumulator.meters - metersBefore,
    )

    private fun isTerminal(): Boolean =
        stateMachine.state == SessionState.COMPLETED || stateMachine.state == SessionState.ABANDONED

    companion object {
        /** 步伐 cue 节流下限（ms）：批量 detector 事件不密集补播 */
        const val MIN_CUE_INTERVAL_MS = 400L
    }
}
