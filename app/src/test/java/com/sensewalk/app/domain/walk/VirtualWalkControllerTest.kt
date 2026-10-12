package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.scene.PathProfile
import com.sensewalk.app.domain.scene.PathSegment
import com.sensewalk.app.domain.scene.Phase
import com.sensewalk.app.domain.scene.PhaseChannel
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.TerrainKind
import com.sensewalk.app.domain.scene.TestScenes
import com.sensewalk.app.domain.session.DispatchOutcome
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionEvent
import com.sensewalk.app.domain.session.SessionState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 会话控制器（T04）：初始化黑幕、暂停清惯性、后台不偷跑、
 * 重复帧防护、dt 上限、未满放弃、满距唯一通关、终态迟到事件与新会话重置。
 */
class VirtualWalkControllerTest {

    private class FakeClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    /** 100m 小场景：里程碑 10/30/50/75/95%，地形含缓坡段 */
    private fun config(
        required: Int = 100,
        segments: List<PathSegment> = listOf(
            PathSegment(0, 30, TerrainKind.FLAT),
            PathSegment(30, 60, TerrainKind.SLOPE_UP, 0.07f),
            PathSegment(60, 100, TerrainKind.FLAT),
        ),
    ): SceneConfig = SceneConfig(
        schemaVersion = 2,
        id = "controller_test",
        name = "控制器测试",
        requiredDistanceMeters = required,
        phases = listOf(
            Phase("void", 0, PhaseChannel.VISUAL, "void", toOpacity = 1f),
            Phase("steps", 10, PhaseChannel.AUDIO, "footsteps", toVolume = 0.25f, fadeMs = 8000),
            Phase("outline", 10, PhaseChannel.VISUAL, "outline", toOpacity = 0.6f, fadeMeters = 2),
            Phase("ambience", 30, PhaseChannel.AUDIO, "ambience", toVolume = 0.35f, fadeMs = 12000),
            Phase("main_body", 30, PhaseChannel.VISUAL, "main_body", toOpacity = 0.7f, fadeMeters = 3),
            Phase("haptic", 50, PhaseChannel.HAPTIC, pattern = "soft", everyNSteps = 2),
            Phase("detail", 50, PhaseChannel.VISUAL, "detail", toOpacity = 0.8f, fadeMeters = 3),
            Phase("deep", 75, PhaseChannel.AUDIO, "deep", toVolume = 0.2f, fadeMs = 10000),
            Phase("far_view", 75, PhaseChannel.VISUAL, "far_view", toOpacity = 0.65f, fadeMeters = 3),
            Phase("arrival", 95, PhaseChannel.VISUAL, "arrival", toOpacity = 0.9f, fadeMeters = 3),
        ),
        pathProfile = PathProfile(segments),
        layers = TestScenes.defaultLayers(),
        visualLayers = TestScenes.defaultVisualLayers(),
    )

    private fun newController(required: Int = 100): Pair<VirtualWalkController, FakeClock> {
        val clock = FakeClock()
        return VirtualWalkController(config(required), clock) to clock
    }

    /** 推动摇杆并推进 n 帧（每帧 50ms） */
    private fun walk(controller: VirtualWalkController, clock: FakeClock, frames: Int, deflection: Float = 0.55f) {
        controller.onStick(deflection)
        repeat(frames) {
            clock.now += 50
            controller.frame()
        }
    }

    @Test
    fun `初始化即黑幕 - void 相位已触发且其余层为 0`() {
        val (controller, _) = newController()
        val snapshot = controller.snapshot()
        assertEquals(SessionState.READY, snapshot.session)
        assertEquals(0f, snapshot.meters, 1e-6f)
        assertEquals(1f, snapshot.sensory.visualOpacities["void"]!!, 1e-6f)
        assertEquals(0f, snapshot.sensory.visualOpacities["outline"]!!, 1e-6f)
        assertTrue(snapshot.sensory.audioTargets.isEmpty())
        assertEquals(setOf("void"), controller.scheduler.firedPhaseIds)
    }

    @Test
    fun `非零摇杆输入触发首次前进`() {
        val (controller, _) = newController()
        controller.onStick(0f)
        assertEquals("零输入不开始行走", SessionState.READY, controller.snapshot().session)
        controller.onStick(0.55f)
        assertEquals(SessionState.WALKING, controller.snapshot().session)
    }

    @Test
    fun `暂停清零输入与惯性 - 暂停期间不累计`() {
        val (controller, clock) = newController()
        walk(controller, clock, frames = 40) // 2s
        assertTrue(controller.snapshot().velocity > 0.5f)
        val metersAtPause = controller.snapshot().meters

        controller.pause()
        val paused = controller.snapshot()
        assertEquals(SessionState.PAUSED, paused.session)
        assertEquals("暂停清零速度", 0f, paused.velocity, 1e-6f)
        assertEquals("暂停清零输入", 0f, paused.deflection, 1e-6f)

        repeat(100) { clock.now += 50; controller.frame() } // 暂停 5 秒
        assertEquals("暂停期间不累计", metersAtPause, controller.snapshot().meters, 1e-6f)
    }

    @Test
    fun `后台返回不偷跑 - 不补算后台时间且不自动前进`() {
        val (controller, clock) = newController()
        walk(controller, clock, frames = 40)
        val metersBefore = controller.snapshot().meters

        controller.onAppBackground() // ON_STOP
        assertEquals(SessionState.PAUSED, controller.snapshot().session)
        clock.now += 600_000 // 后台 10 分钟
        repeat(10) { clock.now += 50; controller.frame() }
        assertEquals("后台期间不累计", metersBefore, controller.snapshot().meters, 1e-6f)

        controller.onAppForeground() // ON_START
        assertEquals("回前台回到可交互状态", SessionState.READY, controller.snapshot().session)
        repeat(20) { clock.now += 50; controller.frame() } // 无新输入：不前进
        assertEquals("回前台不自动前进", metersBefore, controller.snapshot().meters, 1e-6f)

        controller.onStick(0.55f) // 新输入才继续
        repeat(4) { clock.now += 50; controller.frame() }
        assertTrue("新输入后继续累计", controller.snapshot().meters > metersBefore)
    }

    @Test
    fun `单帧 dt 上限 0_05 秒 - 卡顿帧不追进度`() {
        val (controller, clock) = newController()
        controller.onStick(0.55f)
        clock.now += 50
        controller.frame() // 建立速度基线
        clock.now += 5_000 // 一帧卡了 5 秒
        controller.frame()
        // 只按 0.05s 推进：速度尚在起步段，位移远小于 5 秒步行距离
        assertTrue("5 秒帧只前进 0.05s，实际 ${controller.snapshot().meters}", controller.snapshot().meters < 0.2f)
    }

    @Test
    fun `重复帧源不重复计距`() {
        val (controller, clock) = newController()
        walk(controller, clock, frames = 10)
        val meters = controller.snapshot().meters
        // 同一时刻被两个帧循环各调用一次：dt=0，不前进
        repeat(3) { controller.frame() }
        assertEquals(meters, controller.snapshot().meters, 1e-6f)
        clock.now += 50
        controller.frame()
        controller.frame() // 第二次 dt=0
        assertEquals("同帧双调用不双计", meters + controller.snapshot().velocity * 0.05f, controller.snapshot().meters, 0.02f)
    }

    @Test
    fun `未满距主动放弃 - 门禁不触发且米数冻结`() {
        val (controller, clock) = newController()
        walk(controller, clock, frames = 40) // ≈2m，未满 100m
        val meters = controller.snapshot().meters
        assertTrue(meters < 100f)

        controller.abandon()
        assertEquals(SessionState.ABANDONED, controller.snapshot().session)
        assertFalse(controller.gate.isCompleted)

        repeat(50) { clock.now += 50; controller.frame() }
        assertEquals("终态后米数冻结", meters, controller.snapshot().meters, 1e-6f)
        controller.onStick(0.55f) // 终态输入被忽略
        repeat(10) { clock.now += 50; controller.frame() }
        assertEquals(meters, controller.snapshot().meters, 1e-6f)

        // 迟到的通关事件被吸收
        assertEquals(DispatchOutcome.ABSORBED_TERMINAL, controller.stateMachine.dispatch(SessionEvent.Complete))
        assertEquals(SessionState.ABANDONED, controller.snapshot().session)
    }

    @Test
    fun `满距唯一通关 - 门禁只触发一次`() {
        val (controller, clock) = newController()
        var frames = 0
        while (controller.snapshot().session != SessionState.COMPLETED && frames < 10_000) {
            clock.now += 50
            controller.frame()
            if (controller.snapshot().deflection == 0f) controller.onStick(0.55f)
            frames++
        }
        assertEquals(SessionState.COMPLETED, controller.snapshot().session)
        assertEquals("meters 钳制到门禁", 100f, controller.snapshot().meters, 1e-4f)
        assertTrue(controller.gate.isCompleted)

        val finalMeters = controller.snapshot().meters
        repeat(100) { clock.now += 50; controller.frame() }
        assertEquals("通关后米数不变", finalMeters, controller.snapshot().meters, 1e-6f)
        assertEquals("迟到事件吸收", DispatchOutcome.ABSORBED_TERMINAL, controller.stateMachine.dispatch(SessionEvent.Complete))
        assertEquals(SessionState.COMPLETED, controller.snapshot().session)
    }

    @Test
    fun `新会话全新状态 - 不沿用旧门禁与已触发相位`() {
        val (first, clock) = newController()
        walk(first, clock, frames = 100_000 / 50)
        while (first.snapshot().session != SessionState.COMPLETED) {
            clock.now += 50
            first.frame()
        }

        val (second, secondClock) = newController()
        val snapshot = second.snapshot()
        assertEquals(SessionState.READY, snapshot.session)
        assertEquals(0f, snapshot.meters, 1e-6f)
        assertFalse(second.gate.isCompleted)
        assertEquals("新会话只触发黑幕", setOf("void"), second.scheduler.firedPhaseIds)
        walk(second, secondClock, frames = 10)
        assertTrue(second.snapshot().meters > 0f)
        assertTrue(second.snapshot().meters < first.snapshot().meters)
    }

    @Test
    fun `松手按惯性停稳 - 不立即冻结`() {
        val (controller, clock) = newController()
        walk(controller, clock, frames = 40) // ≈2s，v≈0.96
        val vBefore = controller.snapshot().velocity
        controller.onStickReleased()
        clock.now += 50
        controller.frame()
        assertTrue("松手后第一帧仍在滑行", controller.snapshot().velocity > vBefore * 0.5f)
        repeat(24) { clock.now += 50; controller.frame() } // 1.2s
        assertTrue("约 1 秒内停稳", controller.snapshot().velocity < 0.05f)
    }

    @Test
    fun `NaN 输入归零不污染状态`() {
        val (controller, _) = newController()
        controller.onStick(Float.NaN)
        assertEquals(SessionState.READY, controller.snapshot().session)
        assertEquals(0f, controller.snapshot().deflection, 1e-6f)
        controller.onStick(0.55f)
        assertEquals(0.55f, controller.snapshot().deflection, 1e-6f)
    }

    @Test
    fun `暂停中的输入被忽略`() {
        val (controller, clock) = newController()
        walk(controller, clock, frames = 10)
        controller.pause()
        controller.onStick(0.9f)
        assertEquals("暂停中不接受输入", 0f, controller.snapshot().deflection, 1e-6f)
    }

    @Test
    fun `地形查询与快照姿态`() {
        val (controller, _) = newController()
        assertEquals(TerrainKind.FLAT, controller.terrainAt(10f))
        assertEquals(TerrainKind.SLOPE_UP, controller.terrainAt(45f))
        assertEquals(TerrainKind.FLAT, controller.terrainAt(80f))
        assertEquals("越界按平地", TerrainKind.FLAT, controller.terrainAt(999f))
    }
}
