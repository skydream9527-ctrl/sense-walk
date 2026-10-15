package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.progress.ProgressSnapshot
import com.sensewalk.app.domain.scene.TestScenes
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 虚走恢复（T07A / SW-004，S7/S9）：
 * 恢复后 READY 等新输入；s_best 回退往返不重复计距；
 * 已触发相位不重播、感官静态重建；活跃时长延续；能继续走完。
 */
class VirtualWalkRestoreTest {

    private class FakeClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    private fun config() = TestScenes.validConfig()

    /** 走到指定米数的控制器（摇杆满偏） */
    private fun walkedTo(meters: Float): Pair<VirtualWalkController, FakeClock> {
        val clock = FakeClock()
        val c = VirtualWalkController(config(), clock)
        c.onStick(1f)
        while (c.snapshot().meters < meters) {
            clock.now += 50
            c.frame()
        }
        c.onStickReleased()
        return c to clock
    }

    private fun restorePayload(c: VirtualWalkController) = VirtualWalkController.Restore(
        progress = c.accumulator.snapshot(),
        firedPhaseIds = c.scheduler.firedPhaseIds,
        elapsedActiveMs = c.stateMachine.elapsedActiveMs,
    )

    @Test
    fun `S7 恢复后 READY 等新输入 - 不给输入帧不前进`() {
        val (original, _) = walkedTo(120f)
        val clock = FakeClock(10_000L)
        val restored = VirtualWalkController(config(), clock, restore = restorePayload(original))

        assertEquals(SessionState.READY, restored.stateMachine.state)
        val metersAtRestore = restored.snapshot().meters
        repeat(50) { clock.now += 50; restored.frame() } // 无输入地驱动帧
        assertEquals("恢复后无输入不得前进", metersAtRestore, restored.snapshot().meters, 1e-4f)
    }

    @Test
    fun `S7 恢复进度与相位完整还原`() {
        val (original, _) = walkedTo(300f)
        val restored = VirtualWalkController(config(), FakeClock(), restore = restorePayload(original))

        assertEquals(original.snapshot().meters, restored.snapshot().meters, 1e-4f)
        assertEquals(original.accumulator.sBest, restored.accumulator.sBest, 1e-4f)
        assertEquals(original.scheduler.firedPhaseIds, restored.scheduler.firedPhaseIds)
        assertEquals(original.stateMachine.elapsedActiveMs, restored.stateMachine.elapsedActiveMs)
    }

    @Test
    fun `S9 回退快照恢复 - 走回旧位置不重复计距`() {
        val (original, clock) = walkedTo(200f)
        // 模拟合法回退：s_pos 回到 150，s_best 仍 200（重试段落）
        val backedUp = original.accumulator.snapshot().let {
            ProgressSnapshot(sPos = 150f, sBest = 200f, meters = it.meters, requiredDistanceMeters = it.requiredDistanceMeters)
        }
        val restored = VirtualWalkController(
            config(), FakeClock(),
            restore = VirtualWalkController.Restore(backedUp, original.scheduler.firedPhaseIds, original.stateMachine.elapsedActiveMs),
        )
        // 恢复后从 s_pos=150 前进：到 200 前不新增米数
        val rClock = FakeClock(0L)
        val r = VirtualWalkController(config(), rClock, restore = VirtualWalkController.Restore(backedUp, original.scheduler.firedPhaseIds, 0L))
        r.onStick(1f)
        while (r.accumulator.sPos < 199f) { rClock.now += 50; r.frame() }
        assertEquals("回退段内米数保持快照值（不重复计距）", backedUp.meters, r.accumulator.meters, 1e-3f)
        while (r.accumulator.sPos < 210f) { rClock.now += 50; r.frame() }
        assertEquals("超越 s_best 后只计新增", backedUp.meters + 10f, r.accumulator.meters, 0.5f)
    }

    @Test
    fun `恢复不重播一次性提示 - 同米数相位无新事件、感官静态一致`() {
        val (original, _) = walkedTo(420f)
        val fired = original.scheduler.firedPhaseIds
        val restored = VirtualWalkController(
            config(), FakeClock(),
            restore = VirtualWalkController.Restore(original.accumulator.snapshot(), fired, 0L),
        )
        // 恢复构造时 init 已 update(0)：未触发的新相位为空集（0 < 恢复米数）
        assertTrue("恢复点已过相位不得再次触发", restored.drainPhaseEvents().isEmpty())
        // 静态感官：恢复点 sensoryState 与原会话同米数一致（纯函数）
        val m = original.snapshot().meters
        assertEquals(
            original.scheduler.sensoryState(m).visualOpacities,
            restored.scheduler.sensoryState(m).visualOpacities,
        )
    }

    @Test
    fun `恢复后可继续行走并通关`() {
        val (original, _) = walkedTo(700f)
        val clock = FakeClock(100_000L)
        val restored = VirtualWalkController(config(), clock, restore = restorePayload(original))
        restored.onStick(1f)
        var guard = 0
        while (restored.snapshot().session != SessionState.COMPLETED && guard++ < 100_000) {
            clock.now += 50
            restored.frame()
        }
        assertEquals("恢复会话应能走完", SessionState.COMPLETED, restored.snapshot().session)
        assertEquals(config().requiredDistanceMeters.toFloat(), restored.snapshot().meters, 0.5f)
    }
}
