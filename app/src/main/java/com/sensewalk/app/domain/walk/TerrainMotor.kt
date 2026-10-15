package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.scene.PathSegment
import com.sensewalk.app.domain.scene.TerrainKind

/**
 * 越坎马达（T07B / SW-005，DEVELOPMENT §5.6）——纯 Kotlin 状态机，JVM 可全测。
 *
 * 规则（v0.7 定稿，"失败绑定到急"）：
 * - gap 前 [APPROACH_METERS] 进入接近区：
 *   - 接近时摇杆在舒适区或更慢（deflection ≤ 0.72）→ 自动轻跳通过；
 *   - 接近时在紧张区（> 0.72）→「站稳」：目标速度钳到 [STABILIZE_SPEED]，
 *     停满 [STABILIZE_DURATION_MS] 后自动轻跳（无需任何操作）；
 *     本局第一次站稳触发一次温和提示（由消费者读取 [consumeHint]）；
 * - 站稳期间**不产生位移**（s_pos/meters 不增加——绝不刷距）；
 * - 跳跃期间不接受摇杆输入（消费者据此屏蔽），跳跃位移仍由外层
 *   速度帽/有效距离约束（本类只给出跳过段的时间预算，不给免费米数）；
 * - 无输入不能靠自动动作持续刷距：静止进入接近区不触发跳跃推进，
  *  跳跃推进只在有输入（deflection>0）的帧发生；
 * - 松手/取消（deflection=0）重置当前接近；暂停时冻结计时；恢复后
 *   站稳从剩余时长继续；终态后一切事件吸收；
 * - [reduceMotion] 由视觉层处理（关抖动/视差），本类不因 reduceMotion
 *   放宽任何门禁（跳/站稳判定不变）。
 *
 * **快照兼容（SW-005 决策）**：本类无持久状态——站稳/跳跃是瞬态表现态，
 * 被动中断后恢复时角色位于 s_pos，若在坎前会重新走接近流程（不把旧档
 * 静默当作"正在站稳"）。SessionSnapshot 无需新增字段或版本变化。
 */
class TerrainMotor {

    /** 地形姿态（供角色动画选择；不驱动距离） */
    enum class Gait { IDLE, WALK, TENSE, CLIMB, HOP }

    /** 当前越坎状态 */
    enum class Phase { FREE, APPROACH, STABILIZE, HOP }

    private var phase: Phase = Phase.FREE
    private var activeGap: PathSegment? = null
    private var stabilizeElapsedMs: Long = 0L
    private var hintShownThisSession = false
    private var hintPending = false
    private var terminal = false

    /** 当前步态（纯表现；FREE 下由调用方按地形段给 walk/climb） */
    fun gait(walking: Boolean, terrain: TerrainKind): Gait = when {
        !walking -> Gait.IDLE
        phase == Phase.HOP -> Gait.HOP
        phase == Phase.STABILIZE -> Gait.TENSE
        terrain == TerrainKind.SLOPE_UP -> Gait.CLIMB
        else -> Gait.WALK
    }

    val currentPhase: Phase get() = phase

    /** 本局首局站稳提示（一次性消费） */
    fun consumeHint(): Boolean {
        val h = hintPending
        hintPending = false
        return h
    }

    /**
     * 每帧推进（WALKING 状态才调用；dt 已受外层 MAX_FRAME_MS 约束）。
     * 返回本帧速度指令：
     * - [SpeedDirective.normal]：外层照常（曲线 × 地形系数）；
     * - [SpeedDirective.clamp]：目标速度上限（站稳减速 0.4 m/s）；
     * - [SpeedDirective.holdZero]：站稳中，本帧位移 0（不刷距）；
     * - [SpeedDirective.hop]：自动轻跳进行中（外层以钳速推进直到越过坎）。
     */
    fun step(
        dtMs: Long,
        sPos: Float,
        deflection: Float,
        gapAhead: PathSegment?,
        paused: Boolean,
    ): SpeedDirective {
        if (terminal) return SpeedDirective.normal()
        if (paused) return SpeedDirective.holdZero() // 暂停：冻结计时与位移
        val gap = activeGap ?: gapAhead
        if (gap != null && sPos >= gap.from - APPROACH_METERS && sPos < gap.to) {
            if (activeGap == null) activeGap = gap
        } else if (activeGap != null && sPos >= activeGap!!.to) {
            // 已越过：回到自由态
            reset()
        }

        return when (phase) {
            Phase.FREE -> {
                if (activeGap != null && sPos < activeGap!!.from) {
                    if (deflection <= 0f) {
                        // 静止待坎：不触发任何自动推进（无输入不刷距）
                        SpeedDirective.normal()
                    } else if (deflection <= COMFORT_DEFLECTION) {
                        phase = Phase.HOP
                        SpeedDirective.hop()
                    } else {
                        phase = Phase.APPROACH
                        SpeedDirective.clamp(STABILIZE_SPEED)
                    }
                } else if (activeGap != null && sPos >= activeGap!!.from) {
                    if (deflection <= 0f) {
                        // 惯性滑入坎内但已松手：挂起等待新输入（自动动作不得持续刷距）
                        SpeedDirective.normal()
                    } else {
                        // 有输入且在坎上（恢复/过渡落进段内）：直接跳过
                        phase = Phase.HOP
                        SpeedDirective.hop()
                    }
                } else {
                    SpeedDirective.normal()
                }
            }
            Phase.APPROACH -> {
                // 松手/取消：回到自由态重新接近
                if (deflection <= 0f) {
                    phase = Phase.FREE
                    return SpeedDirective.normal()
                }
                if (deflection <= COMFORT_DEFLECTION) {
                    // 途中放慢到舒适区：立即轻跳（无需等站稳）
                    phase = Phase.HOP
                    return SpeedDirective.hop()
                }
                phase = Phase.STABILIZE
                stabilizeElapsedMs = 0L
                hintPending = !hintShownThisSession
                hintShownThisSession = true
                SpeedDirective.clamp(STABILIZE_SPEED)
            }
            Phase.STABILIZE -> {
                if (deflection <= 0f) {
                    // 松手：解除站稳（不保留计时——重新接近会重新判定）
                    phase = Phase.FREE
                    stabilizeElapsedMs = 0L
                    return SpeedDirective.normal()
                }
                stabilizeElapsedMs += dtMs
                if (stabilizeElapsedMs >= STABILIZE_DURATION_MS) {
                    phase = Phase.HOP
                    SpeedDirective.hop()
                } else {
                    SpeedDirective.holdZero()
                }
            }
            Phase.HOP -> {
                if (deflection <= 0f) {
                    // 跳跃中松手/取消：中止自动推进回自由态（等新输入重新判定）
                    phase = Phase.FREE
                    SpeedDirective.normal()
                } else if (activeGap == null || sPos >= activeGap!!.to) {
                    reset()
                    SpeedDirective.normal()
                } else {
                    SpeedDirective.hop()
                }
            }
        }
    }

    /** 暂停（由外层在 pause 时调用）：站稳计时保持，供恢复继续 */
    fun pause() {
        // 计时不重置：恢复后从剩余时长继续（step 的 paused 分支冻结推进）
    }

    /** 会话放弃/通关：吸收一切后续 */
    fun markTerminal() {
        terminal = true
    }

    private fun reset() {
        phase = Phase.FREE
        activeGap = null
        stabilizeElapsedMs = 0L
    }

    /** 速度指令 */
    sealed interface SpeedDirective {
        data class normal(val dummy: Unit = Unit) : SpeedDirective
        data class clamp(val maxSpeed: Float) : SpeedDirective
        data class holdZero(val dummy: Unit = Unit) : SpeedDirective
        data class hop(val dummy: Unit = Unit) : SpeedDirective

        companion object {
            fun normal(): SpeedDirective = normal(Unit)
            fun holdZero(): SpeedDirective = holdZero(Unit)
            fun hop(): SpeedDirective = hop(Unit)
        }
    }

    companion object {
        /** 接近区宽度（gap 前 3 m） */
        const val APPROACH_METERS = 3f

        /** 紧张阈值：舒适曲线里 d ≤ 0.72 视为不急（§5.6） */
        const val COMFORT_DEFLECTION = 0.72f

        /** 站稳减速目标（m/s） */
        const val STABILIZE_SPEED = 0.4f

        /** 站稳时长（ms） */
        const val STABILIZE_DURATION_MS = 1_200L

        /** 轻跳推进速度（m/s）：跳跃本身有速度帽语义（不免费给米） */
        const val HOP_SPEED = 1.0f

        /** 找 sPos 前方最近的 gap_hop 段（接近区内才返回） */
        fun gapAhead(segments: List<PathSegment>, sPos: Float): PathSegment? =
            segments.firstOrNull { it.kind == TerrainKind.GAP_HOP && sPos >= it.from - APPROACH_METERS && sPos < it.to }
    }
}
