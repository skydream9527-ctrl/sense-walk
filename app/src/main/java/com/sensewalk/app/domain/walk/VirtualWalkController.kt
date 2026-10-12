package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.phase.PhaseScheduler
import com.sensewalk.app.domain.phase.SensoryState
import com.sensewalk.app.domain.progress.CompletionGate
import com.sensewalk.app.domain.progress.ProgressAccumulator
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.TerrainKind
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionEvent
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.session.SessionStateMachine
import com.sensewalk.app.domain.stick.ComfortStickMapper
import com.sensewalk.app.domain.stick.VelocityInertia

/**
 * 虚走会话控制器：组合 T03 领域组件，作为会话的唯一状态来源（T04）。
 *
 * UI 只做三件事：提交摇杆输入（[onStick]/[onStickReleased]）、驱动帧（[frame]）、
 * 触发生命周期事件（[pause]/[resume]/[abandon]/[onAppBackground]/[onAppForeground]）。
 * 距离、通关、相位、状态全部由本类与领域层决定，Compose 不另建任何行走逻辑。
 *
 * 帧与时间约定：
 * - 时间来自构造注入的单调时钟；[frame] 是唯一帧入口；
 * - 单帧有效 dt 上限 [MAX_FRAME_MS]（0.05 s），后台/卡顿不补算；
 * - 暂停/开始行走时丢弃帧基线，恢复后的第一帧只建立基线不前进；
 * - 只有 WALKING 状态累计有效距离（通关门禁唯一触发）；
 * - 终态后输入与帧处理全部无效（迟到事件由状态机吸收）。
 */
class VirtualWalkController(
    val config: SceneConfig,
    private val clock: MonotonicClock,
) {

    val stateMachine = SessionStateMachine(clock)
    val inertia = VelocityInertia()
    val accumulator = ProgressAccumulator(config.requiredDistanceMeters.toFloat())
    val gate = CompletionGate(config.requiredDistanceMeters.toFloat())
    val scheduler = PhaseScheduler(config)

    private val mapper = ComfortStickMapper()

    /** 当前摇杆输入（0..1）；仅 READY/WALKING 可写 */
    private var inputDeflection = 0f

    /** 上一帧时间基线；null 表示下一帧只建立基线 */
    private var lastFrameMs: Long? = null

    init {
        // 显式建立黑幕：会话从 atMeters=0 的 void 相位开始
        scheduler.update(0f)
    }

    data class Snapshot(
        val session: SessionState,
        val meters: Float,
        val sPos: Float,
        val velocity: Float,
        val deflection: Float,
        val sensory: SensoryState,
        val elapsedActiveMs: Long,
        /** 当前地形段（视觉姿态用）；gap_hop 在 T07 前按行走降级 */
        val terrain: TerrainKind = TerrainKind.FLAT,
    )

    fun snapshot(): Snapshot = Snapshot(
        session = stateMachine.state,
        meters = accumulator.meters,
        sPos = accumulator.sPos,
        velocity = inertia.velocity,
        deflection = inputDeflection,
        sensory = scheduler.sensoryState(accumulator.meters),
        elapsedActiveMs = stateMachine.elapsedActiveMs,
        terrain = terrainAt(accumulator.sPos),
    )

    /** 摇杆偏转输入（0..1，负值与 NaN 归 0）；READY 下非零输入即开始行走 */
    fun onStick(deflection: Float) {
        if (!acceptsInput()) return
        inputDeflection = when {
            deflection.isFinite() -> deflection.coerceIn(0f, 1f)
            else -> 0f
        }
        if (stateMachine.state == SessionState.READY && inputDeflection > 0f) {
            stateMachine.dispatch(SessionEvent.FirstForward)
            lastFrameMs = null // 行走从下一帧起算
        }
    }

    /** 松手 / 触摸取消：目标速度归零，按松手惯性（τ=0.25s）自然停稳 */
    fun onStickReleased() {
        if (!acceptsInput()) return
        inputDeflection = 0f
    }

    /** 暂停（对话框/手动暂停）：清输入、清惯性；帧基线丢弃 */
    fun pause() {
        if (isTerminal()) return
        stateMachine.dispatch(SessionEvent.Pause)
        inputDeflection = 0f
        inertia.reset()
        lastFrameMs = null
    }

    /** 恢复：回到 READY 等待新输入，不自动前进 */
    fun resume() {
        if (isTerminal()) return
        stateMachine.dispatch(SessionEvent.Resume)
        lastFrameMs = null
    }

    /** 未满距主动结束 */
    fun abandon() {
        if (isTerminal()) return
        inputDeflection = 0f
        inertia.reset()
        stateMachine.dispatch(SessionEvent.Abandon)
    }

    /** ON_STOP：清空输入并暂停（虚走进后台立即暂停） */
    fun onAppBackground() = pause()

    /** ON_START：回前台重置帧基线，恢复到可交互状态等待新输入 */
    fun onAppForeground() = resume()

    /**
     * 唯一帧入口。dt = now − lastFrame，钳制到 [0, MAX_FRAME_MS]；
     * 只有 WALKING 且有基线时推进。重复时间戳或时间回退不前进。
     */
    fun frame(): Snapshot {
        val now = clock.nowMs()
        val last = lastFrameMs
        if (stateMachine.state == SessionState.WALKING && last != null) {
            val dtMs = (now - last).coerceIn(0L, MAX_FRAME_MS)
            if (dtMs > 0L) advance(dtMs)
        }
        lastFrameMs = now
        return snapshot()
    }

    private fun advance(dtMs: Long) {
        val target = mapper.targetSpeed(inputDeflection)
        val v = inertia.step(dtMs / 1000f, target)
        accumulator.advance(v * dtMs / 1000f)
        scheduler.update(accumulator.meters)
        stateMachine.updateInput(inputDeflection, v)
        if (gate.onMeters(accumulator.meters)) {
            stateMachine.dispatch(SessionEvent.Complete)
        }
    }

    /** 当前地形段（视觉姿态用）；越界按平地 */
    fun terrainAt(meters: Float): TerrainKind =
        config.pathProfile.segmentAt(meters.toInt())?.kind ?: TerrainKind.FLAT

    private fun acceptsInput(): Boolean =
        stateMachine.state == SessionState.READY || stateMachine.state == SessionState.WALKING

    private fun isTerminal(): Boolean =
        stateMachine.state == SessionState.COMPLETED || stateMachine.state == SessionState.ABANDONED

    companion object {
        /** 单帧有效 dt 上限（§12.2） */
        const val MAX_FRAME_MS = 50L
    }
}
