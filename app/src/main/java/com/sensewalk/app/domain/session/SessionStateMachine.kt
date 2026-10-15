package com.sensewalk.app.domain.session

/**
 * 会话状态机（§12.3 / S9）。纯 Kotlin，不依赖 Android / Compose / Service。
 *
 * Ready ─FirstForward→ Walking；Walking ─Pause→ Paused ─Resume→ Ready（等待新输入）；
 * Walking ─Complete(门禁)→ Completed；任何活动态 ─Abandon→ Abandoned、─Interrupt→ Interrupted；
 * Interrupted ─AcceptRecovery→ Ready（30 分钟时限与快照恢复属 T07，本阶段只做状态转换）。
 *
 * - Completed / Abandoned 为终态：吸收一切迟到事件，不重启会话、不重复通关；
 * - 暂停/中断/终态进入时清零输入与速度；恢复后等待新的有效输入（不自动行走）；
 * - elapsedActive 只累计 Walking 状态时长；时间来自可注入的 [MonotonicClock]。
 */
enum class SessionState { READY, WALKING, PAUSED, COMPLETED, ABANDONED, INTERRUPTED }

sealed interface SessionEvent {
    /** 首次有效前进（Ready → Walking） */
    data object FirstForward : SessionEvent

    /** 虚走进后台 / 来电（→ Paused） */
    data object Pause : SessionEvent

    /** 回到前台 / 通话结束（Paused → Ready，等待新输入） */
    data object Resume : SessionEvent

    /** 门禁满足（Walking → Completed） */
    data object Complete : SessionEvent

    /** 主动放弃（未满距结束） */
    data object Abandon : SessionEvent

    /** 进程被杀等被动中断 */
    data object Interrupt : SessionEvent

    /** 被动中断后用户选择恢复（Interrupted → Ready） */
    data object AcceptRecovery : SessionEvent
}

enum class DispatchOutcome { ACCEPTED, REJECTED, ABSORBED_TERMINAL }

/** 可注入单调时钟（生产用 SystemClock/System.nanoTime，测试用假时钟） */
fun interface MonotonicClock {
    fun nowMs(): Long
}

class SessionStateMachine(private val clock: MonotonicClock) {

    var state: SessionState = SessionState.READY
        private set

    /** 只统计 Walking 状态的时间（§12.3） */
    var elapsedActiveMs: Long = 0L
        private set

    /** T07A 恢复入口：还原中断前的累计活跃时长（只此一处可写） */
    fun restoreElapsedActiveMs(ms: Long) {
        if (ms >= 0L) elapsedActiveMs = ms
    }

    /** 终态后吸收的迟到事件计数（供调试/测试断言） */
    var absorbedLateEventCount: Int = 0
        private set

    /** 控制器上报的当前输入与速度；暂停/中断/终态进入时被清零 */
    var stickDeflection: Float = 0f
        private set
    var velocity: Float = 0f
        private set

    private var walkingSinceMs: Long = -1L

    /** 仅 Ready/Walking 接受输入上报；NaN 归零，偏转钳制 [0,1]，速度非负 */
    fun updateInput(deflection: Float, velocity: Float) {
        if (state != SessionState.READY && state != SessionState.WALKING) return
        stickDeflection = if (deflection.isFinite()) deflection.coerceIn(0f, 1f) else 0f
        this.velocity = if (velocity.isFinite()) velocity.coerceAtLeast(0f) else 0f
    }

    fun dispatch(event: SessionEvent): DispatchOutcome {
        if (state == SessionState.COMPLETED || state == SessionState.ABANDONED) {
            absorbedLateEventCount++
            return DispatchOutcome.ABSORBED_TERMINAL
        }
        val now = clock.nowMs()
        return when (state) {
            SessionState.READY -> when (event) {
                SessionEvent.FirstForward -> transition(SessionState.WALKING, now)
                SessionEvent.Pause -> transition(SessionState.PAUSED, now)
                SessionEvent.Abandon -> transition(SessionState.ABANDONED, now)
                SessionEvent.Interrupt -> transition(SessionState.INTERRUPTED, now)
                else -> DispatchOutcome.REJECTED
            }
            SessionState.WALKING -> when (event) {
                SessionEvent.Pause -> transition(SessionState.PAUSED, now)
                SessionEvent.Complete -> transition(SessionState.COMPLETED, now)
                SessionEvent.Abandon -> transition(SessionState.ABANDONED, now)
                SessionEvent.Interrupt -> transition(SessionState.INTERRUPTED, now)
                else -> DispatchOutcome.REJECTED
            }
            SessionState.PAUSED -> when (event) {
                SessionEvent.Resume -> transition(SessionState.READY, now)
                SessionEvent.Abandon -> transition(SessionState.ABANDONED, now)
                SessionEvent.Interrupt -> transition(SessionState.INTERRUPTED, now)
                else -> DispatchOutcome.REJECTED
            }
            SessionState.INTERRUPTED -> when (event) {
                SessionEvent.AcceptRecovery -> transition(SessionState.READY, now)
                SessionEvent.Abandon -> transition(SessionState.ABANDONED, now)
                else -> DispatchOutcome.REJECTED
            }
            // COMPLETED / ABANDONED 已在上面提前吸收，此处仅为穷尽
            SessionState.COMPLETED, SessionState.ABANDONED -> DispatchOutcome.ABSORBED_TERMINAL
        }
    }

    private fun transition(target: SessionState, now: Long): DispatchOutcome {
        if (state == SessionState.WALKING && walkingSinceMs >= 0L) {
            elapsedActiveMs += (now - walkingSinceMs).coerceAtLeast(0L)
            walkingSinceMs = -1L
        }
        state = target
        if (target == SessionState.WALKING) {
            walkingSinceMs = now
        }
        if (target == SessionState.PAUSED || target == SessionState.INTERRUPTED ||
            target == SessionState.COMPLETED || target == SessionState.ABANDONED
        ) {
            stickDeflection = 0f
            velocity = 0f
        }
        return DispatchOutcome.ACCEPTED
    }
}
