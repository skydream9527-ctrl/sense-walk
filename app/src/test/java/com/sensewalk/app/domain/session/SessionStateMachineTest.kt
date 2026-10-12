package com.sensewalk.app.domain.session

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** 会话状态机（§12.3 / S9）：六状态、终态吸收、暂停清零、elapsedActive 只算 Walking */
class SessionStateMachineTest {

    private class FakeClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    private fun walkingMachine(clock: FakeClock = FakeClock()): Pair<SessionStateMachine, FakeClock> {
        val sm = SessionStateMachine(clock)
        sm.dispatch(SessionEvent.FirstForward)
        return sm to clock
    }

    @Test
    fun `初始状态为 Ready`() {
        assertEquals(SessionState.READY, SessionStateMachine(FakeClock()).state)
    }

    @Test
    fun `首次前进进入 Walking`() {
        val (sm, _) = walkingMachine()
        assertEquals(SessionState.WALKING, sm.state)
    }

    @Test
    fun `暂停清零输入与速度`() {
        val (sm, _) = walkingMachine()
        sm.updateInput(0.55f, 1.18f)
        assertEquals(0.55f, sm.stickDeflection, 1e-6f)

        sm.dispatch(SessionEvent.Pause)
        assertEquals(SessionState.PAUSED, sm.state)
        assertEquals("暂停应清零摇杆输入", 0f, sm.stickDeflection, 1e-6f)
        assertEquals("暂停应清零速度", 0f, sm.velocity, 1e-6f)
    }

    @Test
    fun `暂停后输入上报被忽略`() {
        val (sm, _) = walkingMachine()
        sm.dispatch(SessionEvent.Pause)
        sm.updateInput(0.55f, 1.0f)
        assertEquals(0f, sm.stickDeflection, 1e-6f)
        assertEquals(0f, sm.velocity, 1e-6f)
    }

    @Test
    fun `恢复回到 Ready 并等待新输入`() {
        val (sm, _) = walkingMachine()
        sm.dispatch(SessionEvent.Pause)
        assertEquals(
            DispatchOutcome.ACCEPTED,
            sm.dispatch(SessionEvent.Resume),
        )
        assertEquals("恢复后是 Ready 而非自动 Walking", SessionState.READY, sm.state)
        // 新的有效输入才继续前进
        assertEquals(DispatchOutcome.ACCEPTED, sm.dispatch(SessionEvent.FirstForward))
        assertEquals(SessionState.WALKING, sm.state)
    }

    @Test
    fun `通关进入 Completed 终态`() {
        val (sm, _) = walkingMachine()
        assertEquals(DispatchOutcome.ACCEPTED, sm.dispatch(SessionEvent.Complete))
        assertEquals(SessionState.COMPLETED, sm.state)
    }

    @Test
    fun `S9 Completed 吸收迟到事件不重复通关`() {
        val (sm, _) = walkingMachine()
        sm.dispatch(SessionEvent.Complete)
        assertEquals(DispatchOutcome.ABSORBED_TERMINAL, sm.dispatch(SessionEvent.Complete))
        assertEquals(DispatchOutcome.ABSORBED_TERMINAL, sm.dispatch(SessionEvent.Pause))
        assertEquals(DispatchOutcome.ABSORBED_TERMINAL, sm.dispatch(SessionEvent.FirstForward))
        assertEquals(3, sm.absorbedLateEventCount)
        assertEquals("终态不可被迟到事件改变", SessionState.COMPLETED, sm.state)
    }

    @Test
    fun `S9 Abandoned 吸收迟到的通关事件`() {
        val (sm, _) = walkingMachine()
        sm.dispatch(SessionEvent.Abandon)
        assertEquals(SessionState.ABANDONED, sm.state)
        assertEquals(DispatchOutcome.ABSORBED_TERMINAL, sm.dispatch(SessionEvent.Complete))
        assertEquals(SessionState.ABANDONED, sm.state)
    }

    @Test
    fun `Ready 也可直接放弃`() {
        val sm = SessionStateMachine(FakeClock())
        assertEquals(DispatchOutcome.ACCEPTED, sm.dispatch(SessionEvent.Abandon))
        assertEquals(SessionState.ABANDONED, sm.state)
    }

    @Test
    fun `中断进入 Interrupted 可恢复或放弃`() {
        val (sm, _) = walkingMachine()
        sm.dispatch(SessionEvent.Interrupt)
        assertEquals(SessionState.INTERRUPTED, sm.state)
        assertEquals(0f, sm.velocity, 1e-6f)

        assertEquals(DispatchOutcome.ACCEPTED, sm.dispatch(SessionEvent.AcceptRecovery))
        assertEquals(SessionState.READY, sm.state)
    }

    @Test
    fun `Interrupted 也可选择放弃`() {
        val (sm, _) = walkingMachine()
        sm.dispatch(SessionEvent.Interrupt)
        sm.dispatch(SessionEvent.Abandon)
        assertEquals(SessionState.ABANDONED, sm.state)
    }

    @Test
    fun `非法转换被拒绝且状态不变`() {
        val sm = SessionStateMachine(FakeClock())
        assertEquals(DispatchOutcome.REJECTED, sm.dispatch(SessionEvent.Complete)) // Ready 不能直接通关
        assertEquals(DispatchOutcome.REJECTED, sm.dispatch(SessionEvent.Resume)) // Ready 无需恢复
        assertEquals(SessionState.READY, sm.state)

        val (walking, _) = walkingMachine()
        assertEquals(DispatchOutcome.REJECTED, walking.dispatch(SessionEvent.FirstForward)) // 已在行走
        assertEquals(DispatchOutcome.REJECTED, walking.dispatch(SessionEvent.AcceptRecovery))
        assertEquals(SessionState.WALKING, walking.state)

        val (paused, _) = walkingMachine()
        paused.dispatch(SessionEvent.Pause)
        assertEquals(DispatchOutcome.REJECTED, paused.dispatch(SessionEvent.FirstForward)) // 暂停中无前进
        assertEquals(DispatchOutcome.REJECTED, paused.dispatch(SessionEvent.Complete)) // 暂停中不通关
        assertEquals(SessionState.PAUSED, paused.state)
    }

    @Test
    fun `elapsedActive 只累计 Walking 时长`() {
        val clock = FakeClock(0L)
        val sm = SessionStateMachine(clock)
        sm.dispatch(SessionEvent.FirstForward) // walkingSince=0

        clock.now = 1_000
        sm.dispatch(SessionEvent.Pause) // +1000ms
        assertEquals(1_000L, sm.elapsedActiveMs)

        clock.now = 6_000 // 暂停的 5 秒不计
        sm.dispatch(SessionEvent.Resume)
        assertEquals("暂停时长不计入 elapsedActive", 1_000L, sm.elapsedActiveMs)

        clock.now = 6_500
        sm.dispatch(SessionEvent.FirstForward)
        clock.now = 7_000
        sm.dispatch(SessionEvent.Complete) // +500ms
        assertEquals(1_500L, sm.elapsedActiveMs)
    }

    @Test
    fun `中断期间时长不计入 elapsedActive`() {
        val clock = FakeClock(0L)
        val sm = SessionStateMachine(clock)
        sm.dispatch(SessionEvent.FirstForward)
        clock.now = 500
        sm.dispatch(SessionEvent.Interrupt) // +500
        clock.now = 100_000 // 中断很久
        sm.dispatch(SessionEvent.AcceptRecovery)
        assertEquals(500L, sm.elapsedActiveMs)
    }

    @Test
    fun `updateInput 的 NaN 归零且偏转钳制`() {
        val sm = SessionStateMachine(FakeClock())
        sm.updateInput(Float.NaN, Float.NaN)
        assertEquals(0f, sm.stickDeflection, 1e-6f)
        assertEquals(0f, sm.velocity, 1e-6f)

        sm.updateInput(1.7f, -0.5f)
        assertEquals("偏转钳制到 1", 1f, sm.stickDeflection, 1e-6f)
        assertEquals("速度不取负", 0f, sm.velocity, 1e-6f)
    }

    @Test
    fun `终态后输入上报被忽略`() {
        val (sm, _) = walkingMachine()
        sm.dispatch(SessionEvent.Complete)
        sm.updateInput(0.55f, 1.0f)
        assertEquals(0f, sm.stickDeflection, 1e-6f)
        assertTrue(sm.state == SessionState.COMPLETED)
    }
}
