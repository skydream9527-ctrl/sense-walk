package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.progress.ProgressSnapshot
import com.sensewalk.app.domain.scene.TestScenes
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 实走恢复（T07A / SW-004）：恢复后 counter 重新建基线、中断/跨 boot 缺口不补算；
 * 米数/相位从快照起继续；终态迟到吸收不变。
 */
class RealWalkRestoreTest {

    private class FakeClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    private fun config() = TestScenes.validConfig()

    @Test
    fun `恢复后首 counter 事件只建基线 - 中断期步数不补`() {
        val clock = FakeClock()
        val snap = ProgressSnapshot(sPos = 300f, sBest = 300f, meters = 300f, requiredDistanceMeters = config().requiredDistanceMeters.toFloat())
        val fired = setOf("void", "steps", "tree_outline", "ambience", "tree_trunks")
        val r = RealWalkController(config(), clock, restore = VirtualWalkController.Restore(snap, fired, 200_000L))

        assertEquals(300f, r.snapshot().meters, 1e-4f)
        r.start()
        // 中断期间真实走了 60 步（counter 从 500 涨到 560）——不得补算
        val first = r.onCounterEvent(560L, 1_000L)
        assertEquals("恢复后首事件只建基线", 0f, first.metersDelta, 1e-6f)
        assertEquals(300f, first.meters, 1e-4f)
        // 之后正常计距：+2 步/秒 → 1.4m
        val second = r.onCounterEvent(562L, 2_000L)
        assertEquals(1.4f, second.metersDelta, 1e-3f)
        assertEquals(301.4f, second.meters, 1e-3f)
    }

    @Test
    fun `恢复点相位与活跃时长还原 - 已触发相位不重播`() {
        val fired = setOf("void", "steps", "tree_outline", "ambience", "tree_trunks", "haptic_steps", "leaf_path")
        val snap = ProgressSnapshot(sPos = 450f, sBest = 450f, meters = 450f, requiredDistanceMeters = config().requiredDistanceMeters.toFloat())
        val r = RealWalkController(config(), FakeClock(), restore = VirtualWalkController.Restore(snap, fired, 333_000L))

        assertEquals(fired, r.scheduler.firedPhaseIds)
        assertEquals(333_000L, r.stateMachine.elapsedActiveMs)
        assertTrue("恢复点已过相位不得重触发", r.drainPhaseEvents().isEmpty())
    }

    @Test
    fun `恢复会话能继续走完 - gate 与 scheduler 正常`() {
        val snap = ProgressSnapshot(sPos = 780f, sBest = 780f, meters = 780f, requiredDistanceMeters = config().requiredDistanceMeters.toFloat())
        val fired = setOf("void", "steps", "tree_outline", "ambience", "tree_trunks", "haptic_steps", "leaf_path", "deep_birds", "light_shows")
        val clock = FakeClock()
        val r = RealWalkController(config(), clock, restore = VirtualWalkController.Restore(snap, fired, 0L))
        r.start()
        r.onCounterEvent(1000L, 0L) // 基线
        var count = 1000L
        var t = 0L
        var s = r.onCounterEvent(count, t)
        var guard = 0
        while (s.session != SessionState.COMPLETED && guard++ < 10_000) {
            count += 2
            t += 1000
            s = r.onCounterEvent(count, t)
        }
        assertEquals(config().requiredDistanceMeters.toFloat(), s.meters, 0.5f)
        // 终态迟到事件吸收
        assertEquals(0f, r.onCounterEvent(count + 100, t + 1000).metersDelta, 1e-6f)
    }
}
