package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.TestScenes
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 实走会话控制器（T06）：counter 唯一计距、detector 只作 cue、
 * 暂停/恢复/通关/放弃与快照语义。
 */
class RealWalkControllerTest {

    private class FakeClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    private fun controller(required: Int = 100): Pair<RealWalkController, FakeClock> {
        val config = TestScenes.validConfig(required = required)
        val clock = FakeClock()
        return RealWalkController(config, clock) to clock
    }

    /** 按真实步行节奏（一步 ~700ms）注入 counter 事件 */
    private fun RealWalkController.walkSteps(from: Long, steps: Long, startMs: Long, perStepMs: Long = 700L): Float {
        var meters = 0f
        var count = from
        var t = startMs
        repeat(steps.toInt()) {
            count++; t += perStepMs
            meters += onCounterEvent(count, t).metersDelta
        }
        return meters
    }

    @Test
    fun `start 进入 WALKING - 首个 counter 事件只建基线`() {
        val (c, _) = controller()
        assertEquals(SessionState.READY, c.snapshot().session)
        c.start()
        assertEquals(SessionState.WALKING, c.snapshot().session)
        assertEquals(0f, c.onCounterEvent(1_000L, 100L).meters, 1e-4f)
    }

    @Test
    fun `counter 增量推进米数与相位 - detector 不计距`() {
        val (c, _) = controller(required = 200) // 不触门禁，检验计距本体
        c.start()
        c.onCounterEvent(0L, 0L) // 基线
        val walked = c.walkSteps(0, 150, 1_000L) // 150 步 ≈ 105m
        assertEquals("150 步 × 0.7 = 105m（封顶不触）", 105f, walked, 0.5f)
        assertTrue(c.snapshot().meters > 100f)
        assertTrue("相位照常触发", c.drainPhaseEvents().isNotEmpty())
        assertTrue(c.scheduler.firedPhaseIds.contains("steps"))

        // detector 只是 cue：不涨距
        val before = c.snapshot().meters
        assertTrue(c.onDetectorStep(200_000L))
        assertEquals(before, c.snapshot().meters, 1e-6f)
    }

    @Test
    fun `detector cue 节流 - 批量密集事件不密集补播`() {
        val (c, _) = controller()
        c.start()
        var fired = 0
        var t = 0L
        repeat(10) {
            t += 30L // 30ms 连发（模拟批量上报，总窗 300ms < 400ms 节流）
            if (c.onDetectorStep(t)) fired++
        }
        assertEquals("30ms 连发整个窗口内只出 1 个 cue（400ms 节流）", 1, fired)
        assertTrue(c.onDetectorStep(t + 500L))
        assertEquals(2, ++fired)
    }

    @Test
    fun `暂停冻结 - 恢复后立即回 WALKING 且不补算`() {
        val (c, _) = controller()
        c.start()
        c.onCounterEvent(0L, 0L)
        c.walkSteps(0, 20, 1_000L) // 14m
        c.pause()
        assertEquals(SessionState.PAUSED, c.snapshot().session)
        // 暂停期真实步数不补算
        c.onCounterEvent(120L, 60_000L)
        assertEquals(14f, c.snapshot().meters, 0.5f)
        c.resume()
        assertEquals("实走恢复即回 WALKING（不等摇杆）", SessionState.WALKING, c.snapshot().session)
        // 恢复后首事件只建基线
        c.onCounterEvent(121L, 61_000L)
        assertEquals(14f, c.snapshot().meters, 0.5f)
        c.walkSteps(121, 10, 61_700L)
        assertEquals(21f, c.snapshot().meters, 0.5f)
    }

    @Test
    fun `满距唯一通关 - 终态吸收后续步数`() {
        val (c, _) = controller(required = 20)
        c.start()
        c.onCounterEvent(0L, 0L)
        c.walkSteps(0, 30, 1_000L) // 21m ≥ 20m
        assertEquals(SessionState.COMPLETED, c.snapshot().session)
        val finalMeters = c.snapshot().meters
        c.onCounterEvent(10_000L, 500_000L)
        assertEquals("终态后不再涨距", finalMeters, c.snapshot().meters, 1e-6f)
    }

    @Test
    fun `放弃终态 - detector cue 停止`() {
        val (c, _) = controller()
        c.start()
        c.onCounterEvent(0L, 0L)
        c.walkSteps(0, 5, 1_000L)
        c.abandon()
        assertEquals(SessionState.ABANDONED, c.snapshot().session)
        assertFalse(c.onDetectorStep(999_999L))
        assertEquals(0f, c.onCounterEvent(100L, 1_000_000L).metersDelta, 1e-6f)
    }

    @Test
    fun `快照与虚走同型 - 字段语义诚实`() {
        val (c, _) = controller()
        c.start()
        c.onCounterEvent(0L, 0L)
        val snap = c.onCounterEvent(3L, 2_100L) // 3 步 2.1s = 2.1m
        assertEquals(2.1f, snap.meters, 1e-3f)
        assertEquals(2.1f, snap.metersDelta, 1e-3f)
        assertEquals(2_100f, snap.frameDtMs, 1e-3f)
        assertEquals("实走无摇杆", 0f, snap.deflection, 1e-6f)
        assertEquals("速度按事件间隔推导（展示用）", 1.0f, snap.velocity, 0.01f)
        assertEquals(com.sensewalk.app.domain.scene.TerrainKind.FLAT, snap.terrain)
        assertEquals(1f, snap.sensory.visualOpacities["void"]!!, 1e-6f)
    }
}
