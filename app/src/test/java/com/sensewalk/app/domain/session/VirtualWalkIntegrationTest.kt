package com.sensewalk.app.domain.session

import com.sensewalk.app.domain.phase.PhaseEvent
import com.sensewalk.app.domain.phase.PhaseScheduler
import com.sensewalk.app.domain.progress.CompletionGate
import com.sensewalk.app.domain.progress.ProgressAccumulator
import com.sensewalk.app.domain.scene.PathProfile
import com.sensewalk.app.domain.scene.PathSegment
import com.sensewalk.app.domain.scene.Phase
import com.sensewalk.app.domain.scene.PhaseChannel
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.TerrainKind
import com.sensewalk.app.domain.scene.TestScenes
import com.sensewalk.app.domain.stick.ComfortStickMapper
import com.sensewalk.app.domain.stick.VelocityInertia
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 领域全链路集成（S1–S4、S9）：
 * 摇杆 → 惯性 → 有效距离 → 门禁 → 相位 → 状态机 的最小会话闭环。
 * 模拟 T04 会话控制器的用法：只有 Walking 状态消费输入产生距离。
 */
class VirtualWalkIntegrationTest {

    private class MutableClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    /** 100m 小场景：里程碑 10/30/50/75/95%（结构与 TestScenes 相同，距离缩放） */
    private fun smallConfig(): SceneConfig {
        val layers = TestScenes.defaultLayers()
        val visual = TestScenes.defaultVisualLayers()
        return SceneConfig(
            schemaVersion = 2,
            id = "small",
            name = "小场景",
            requiredDistanceMeters = 100,
            phases = listOf(
                Phase("void", 0, PhaseChannel.VISUAL, "void", toOpacity = 1f),
                Phase("steps", 10, PhaseChannel.AUDIO, "footsteps", toVolume = 0.25f, fadeMs = 8000),
                Phase("outline", 10, PhaseChannel.VISUAL, "outline", toOpacity = 0.6f, fadeMeters = 2),
                Phase("ambience", 30, PhaseChannel.AUDIO, "ambience", toVolume = 0.35f, fadeMs = 12000),
                Phase("main_body", 30, PhaseChannel.VISUAL, "main_body", toOpacity = 0.7f, fadeMeters = 3),
                Phase("haptic", 50, PhaseChannel.HAPTIC, pattern = "footstep_soft", everyNSteps = 2),
                Phase("detail", 50, PhaseChannel.VISUAL, "detail", toOpacity = 0.8f, fadeMeters = 3),
                Phase("deep", 75, PhaseChannel.AUDIO, "deep", toVolume = 0.2f, fadeMs = 10000),
                Phase("far_view", 75, PhaseChannel.VISUAL, "far_view", toOpacity = 0.65f, fadeMeters = 3),
                Phase("arrival", 95, PhaseChannel.VISUAL, "arrival", toOpacity = 0.9f, fadeMeters = 3),
            ),
            pathProfile = PathProfile(listOf(PathSegment(0, 100, TerrainKind.FLAT))),
            layers = layers,
            visualLayers = visual,
        )
    }

    private class Harness(config: SceneConfig, private val clock: MutableClock) {
        val sm = SessionStateMachine(clock)
        val mapper = ComfortStickMapper()
        val inertia = VelocityInertia()
        val acc = ProgressAccumulator(config.requiredDistanceMeters.toFloat())
        val gate = CompletionGate(config.requiredDistanceMeters.toFloat())
        val scheduler = PhaseScheduler(config)
        val firedEvents = mutableListOf<PhaseEvent>()

        init {
            firedEvents += scheduler.update(0f)
        }

        fun stick(deflection: Float) {
            if (sm.state == SessionState.READY && deflection > 0f) {
                sm.dispatch(SessionEvent.FirstForward)
            }
            sm.updateInput(deflection, inertia.velocity)
        }

        /** 一帧 50ms：只有 Walking 消费输入产生距离（计时本身不产生距离） */
        fun frame() {
            clock.now += 50
            if (sm.state != SessionState.WALKING) return
            val target = mapper.targetSpeed(sm.stickDeflection)
            val v = inertia.step(0.05f, target)
            sm.updateInput(sm.stickDeflection, v)
            acc.advance(v * 0.05f)
            firedEvents += scheduler.update(acc.meters)
            if (gate.onMeters(acc.meters)) {
                sm.dispatch(SessionEvent.Complete)
            }
        }
    }

    @Test
    fun `甜点速度完整通关 - 门禁唯一触发且相位各一次`() {
        val clock = MutableClock()
        val harness = Harness(smallConfig(), clock)
        harness.stick(0.55f)
        var frames = 0
        while (harness.sm.state != SessionState.COMPLETED && frames < 20_000) {
            harness.frame()
            frames++
        }
        assertEquals(SessionState.COMPLETED, harness.sm.state)
        assertEquals("meters 钳制到门禁", 100f, harness.acc.meters, 1e-4f)
        assertTrue("应在几百秒内完成，实际 ${frames * 0.05f}s", frames < 20_000)

        // 每个相位恰好触发一次，顺序与配置一致
        assertEquals(
            listOf("void", "steps", "outline", "ambience", "main_body", "haptic", "detail", "deep", "far_view", "arrival"),
            harness.firedEvents.map { it.phase.id },
        )
        assertTrue("通关时 elapsedActive 应为正", harness.sm.elapsedActiveMs > 0)
    }

    @Test
    fun `未满距主动结束为 Abandoned - 迟到通关被吸收`() {
        val clock = MutableClock()
        val harness = Harness(smallConfig(), clock)
        harness.stick(0.55f)
        repeat(50) { harness.frame() } // 2.5s ≈ 2m，远未满 100m
        assertTrue(harness.acc.meters < 100f)

        assertEquals(DispatchOutcome.ACCEPTED, harness.sm.dispatch(SessionEvent.Abandon))
        assertEquals(SessionState.ABANDONED, harness.sm.state)

        // 终态后的帧与迟到通关都被吸收，米数冻结
        val frozen = harness.acc.meters
        repeat(100) { harness.frame() }
        assertEquals(frozen, harness.acc.meters, 1e-6f)
        assertEquals(DispatchOutcome.ABSORBED_TERMINAL, harness.sm.dispatch(SessionEvent.Complete))
        assertEquals(SessionState.ABANDONED, harness.sm.state)
        assertTrue("放弃后门禁不得触发", !harness.gate.isCompleted)
    }

    @Test
    fun `暂停不偷跑 - 回前台等待新输入`() {
        val clock = MutableClock()
        val harness = Harness(smallConfig(), clock)
        harness.stick(0.55f)
        repeat(20) { harness.frame() }
        val beforePause = harness.acc.meters
        assertTrue(beforePause > 0f)

        harness.sm.dispatch(SessionEvent.Pause)
        repeat(100) { harness.frame() } // 暂停期间 5 秒的帧
        assertEquals("暂停期间不得累计距离", beforePause, harness.acc.meters, 1e-6f)
        assertEquals(0f, harness.sm.velocity, 1e-6f)

        harness.sm.dispatch(SessionEvent.Resume)
        assertEquals(SessionState.READY, harness.sm.state)
        repeat(50) { harness.frame() } // 回前台但无新输入：不自动前进
        assertEquals("回前台不自动行走", beforePause, harness.acc.meters, 1e-6f)

        harness.stick(0.55f)
        repeat(20) { harness.frame() }
        assertTrue("新输入后继续累计", harness.acc.meters > beforePause)
    }

    @Test
    fun `S1 拉满比甜点慢 - 同样帧数拉满走得更少`() {
        fun walkedMeters(deflection: Float): Float {
            val harness = Harness(smallConfig(), MutableClock())
            harness.stick(deflection)
            repeat(600) { harness.frame() } // 30s
            return harness.acc.meters
        }
        val sweet = walkedMeters(0.55f)
        val full = walkedMeters(1.00f)
        assertTrue("甜点 $sweet 应明显多于拉满 $full", sweet > full * 1.2f)
    }

    @Test
    fun `S9 单次批量进度跨多个阈值全部按序触发一次`() {
        val clock = MutableClock()
        val harness = Harness(smallConfig(), clock)
        // 直接注入一次大位移（例如传感器批量上报的等价物）
        harness.acc.advance(60f)
        val events = harness.scheduler.update(harness.acc.meters)
        assertEquals(
            "一次跨过 10/30/50 三个阈值：全部按配置顺序触发",
            listOf("steps", "outline", "ambience", "main_body", "haptic", "detail"),
            events.map { it.phase.id },
        )
        assertTrue(harness.scheduler.update(60f).isEmpty())
        assertEquals(60f, harness.acc.meters, 1e-6f)
    }

    @Test
    fun `S2 回退重走不重复计距 - 全链路视角`() {
        val clock = MutableClock()
        val harness = Harness(smallConfig(), clock)
        harness.stick(0.55f)
        repeat(400) { harness.frame() } // 20s ≈ 18m，超过回退量
        val forward = harness.acc.meters
        assertTrue(forward > 10f)

        // 回退 5m 再走回：调度器不得回退，米数不得重复累计
        val sBestBefore = harness.acc.sBest
        harness.acc.advance(-5f)
        val stateDuringRetreat = harness.scheduler.sensoryState(harness.acc.meters)
        assertEquals(forward, harness.acc.meters, 1e-6f)
        harness.acc.advance(5f)
        assertEquals("走回旧位置米数不变", forward, harness.acc.meters, 1e-6f)
        assertEquals(sBestBefore, harness.acc.sBest, 1e-6f)
        // 米数不变 → 感官目标不变（S4）
        assertEquals(stateDuringRetreat, harness.scheduler.sensoryState(harness.acc.meters))
    }
}
