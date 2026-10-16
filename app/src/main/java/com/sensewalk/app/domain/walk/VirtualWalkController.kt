package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.phase.PhaseEvent
import com.sensewalk.app.domain.phase.PhaseScheduler
import com.sensewalk.app.domain.phase.SensoryState
import com.sensewalk.app.domain.progress.CompletionGate
import com.sensewalk.app.domain.progress.ProgressAccumulator
import com.sensewalk.app.domain.scene.PathSegment
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.SceneDurationEstimator
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
    restore: Restore? = null,
) {

    /** T07A 恢复载荷：进度（s_pos/s_best 分开还原，S9 回退不重复计距）+ 已触发相位 +
     *  活跃时长 + stabilizeHintShown（R-SW-005-R1 P-02：同局恢复保持「站稳提示仅一次」） */
    data class Restore(
        val progress: com.sensewalk.app.domain.progress.ProgressSnapshot,
        val firedPhaseIds: Set<String>,
        val elapsedActiveMs: Long,
        val stabilizeHintShown: Boolean = false,
    )

    val stateMachine = SessionStateMachine(clock)
    val inertia = VelocityInertia()
    val accumulator = restore?.let { ProgressAccumulator.fromSnapshot(it.progress) }
        ?: ProgressAccumulator(config.requiredDistanceMeters.toFloat())
    val gate = CompletionGate(config.requiredDistanceMeters.toFloat())
    val scheduler = PhaseScheduler(config, restore?.firedPhaseIds ?: emptySet())

    /** 越坎马达（T07B / SW-005）：接近/站稳/轻跳；hintShown 随快照持久（P-02） */
    internal val terrainMotor = TerrainMotor()

    /** 本局首坎站稳提示（一次性消费；UI 轻提示） */
    fun consumeStabilizeHint(): Boolean = terrainMotor.consumeHint()

    init {
        // 显式建立黑幕：会话从 atMeters=0 的 void 相位开始；恢复构造时已触发相位
        // 不重复触发（黑幕 void 已在 fired 集合内则保持），感官按当前米数静态重建
        scheduler.update(0f)
        restore?.let {
            stateMachine.restoreElapsedActiveMs(it.elapsedActiveMs)
            terrainMotor.restoreHintShown(it.stabilizeHintShown)
        }
    }

    private val mapper = ComfortStickMapper()

    /** 当前摇杆输入（0..1）；仅 READY/WALKING 可写 */
    private var inputDeflection = 0f

    /** 上一帧时间基线；null 表示下一帧只建立基线 */
    private var lastFrameMs: Long? = null

    /** 已触发待消费的相位事件（感官协调器经 [drainPhaseEvents] 取走） */
    private var pendingEvents = mutableListOf<PhaseEvent>()



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
        /** 本帧有效步进时长（ms）；非行走帧为 0 */
        val frameDtMs: Float = 0f,
        /** 本帧新增有效米数（meters 增量） */
        val metersDelta: Float = 0f,
        /** 越坎步态（T07B 表现态：idle/walk/tense/climb/hop；不驱动距离） */
        val gait: TerrainMotor.Gait = TerrainMotor.Gait.IDLE,
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
        gait = terrainMotor.gait(
            walking = stateMachine.state == SessionState.WALKING,
            terrain = terrainAt(accumulator.sPos),
        ),
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
        terrainMotor.pause() // 站稳计时保持（恢复后从剩余时长继续），不重置
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
        terrainMotor.markTerminal()
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
        var dtMs = 0L
        var metersBefore = 0f
        if (stateMachine.state == SessionState.WALKING && last != null) {
            dtMs = (now - last).coerceIn(0L, MAX_FRAME_MS)
            if (dtMs > 0L) {
                metersBefore = accumulator.meters
                advance(dtMs)
            }
        }
        lastFrameMs = now
        val snap = snapshot()
        return if (dtMs > 0L) {
            snap.copy(frameDtMs = dtMs.toFloat(), metersDelta = snap.meters - metersBefore)
        } else snap
    }

    private fun advance(dtMs: Long) {
        // T07B：越坎马达先行判定（接近/站稳/轻跳），给出本帧速度指令
        val directive = terrainMotor.step(
            dtMs = dtMs,
            sPos = accumulator.sPos,
            deflection = inputDeflection,
            gapAhead = TerrainMotor.gapAhead(config.pathProfile.segments, accumulator.sPos),
            paused = false,
        )
        // §12.2：v_tgt = 曲线 × 地形系数（gap_hop 段内已由马达接管，系数不再叠加）
        val terrainFactor = if (directive is TerrainMotor.SpeedDirective.hop) 1f
        else terrainFactorAt(accumulator.sPos)
        val curve = mapper.targetSpeed(inputDeflection)
        val target = when (directive) {
            is TerrainMotor.SpeedDirective.clamp -> minOf(curve * terrainFactor, directive.maxSpeed)
            is TerrainMotor.SpeedDirective.holdZero -> 0f
            is TerrainMotor.SpeedDirective.hop -> TerrainMotor.HOP_SPEED
            is TerrainMotor.SpeedDirective.normal -> curve * terrainFactor
        }
        val v = inertia.step(dtMs / 1000f, target)
        // 站稳（holdZero）期间位移绝对冻结：不 advance（含惯性残余，§5.6 站稳不刷距）
        if (directive !is TerrainMotor.SpeedDirective.holdZero) {
            accumulator.advance(v * dtMs / 1000f)
        }
        pendingEvents += scheduler.update(accumulator.meters)
        // 跳跃期间不接受摇杆输入（§5.6）：状态机按当前有效速度收输入
        val effectiveInput = if (directive is TerrainMotor.SpeedDirective.hop) 0f else inputDeflection
        stateMachine.updateInput(effectiveInput, v)
        if (gate.onMeters(accumulator.meters)) {
            // 通关即终态：清空输入与惯性，停止一切前进（迟到事件由状态机吸收）
            inputDeflection = 0f
            inertia.reset()
            terrainMotor.markTerminal()
            stateMachine.dispatch(SessionEvent.Complete)
        }
    }

    /** 取出本会话已触发的相位事件（一次性消费；供感官协调器接音频/振动） */
    fun drainPhaseEvents(): List<PhaseEvent> {
        val events = pendingEvents
        pendingEvents = mutableListOf()
        return events
    }

    /**
     * 地形速度系数（§5.7）：平地 1.0；上坡 1−1.5×grade（下限 0.80）；
     * 下坡 0.95（不加速）；不平 0.95；gap_hop 在 T07 前按平地降级。
     * 段边界两侧 1.5 m 线性过渡，避免速度突变。
     */
    internal fun terrainFactorAt(meters: Float): Float {
        val segments = config.pathProfile.segments
        val idx = segments.indexOfFirst { meters >= it.from && meters < it.to }
        if (idx < 0) return 1f
        val cur = segmentFactor(segments[idx])
        var factor = cur
        // 左边界：与上一段在 [from, from+1.5] 混合
        if (idx > 0) {
            val prev = segmentFactor(segments[idx - 1])
            val from = segments[idx].from.toFloat()
            if (meters < from + TRANSITION_METERS) {
                val t = ((meters - from) / TRANSITION_METERS).coerceIn(0f, 1f)
                factor = prev + (cur - prev) * t
            }
        }
        // 右边界：与下一段在 [to-1.5, to] 混合
        if (idx < segments.size - 1) {
            val next = segmentFactor(segments[idx + 1])
            val to = segments[idx].to.toFloat()
            if (meters > to - TRANSITION_METERS) {
                val t = ((to - meters) / TRANSITION_METERS).coerceIn(0f, 1f)
                factor = next + (cur - next) * t
            }
        }
        return factor
    }

    private fun segmentFactor(segment: PathSegment): Float = when (segment.kind) {
        TerrainKind.GAP_HOP -> 1f // 开发降级：自动越坎（§5.6 站稳再跳）属 T07
        else -> SceneDurationEstimator.terrainSpeedFactor(segment.kind, segment.grade).toFloat()
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

        /** 段间地形速度系数线性过渡宽度（§5.7） */
        const val TRANSITION_METERS = 1.5f
    }
}
