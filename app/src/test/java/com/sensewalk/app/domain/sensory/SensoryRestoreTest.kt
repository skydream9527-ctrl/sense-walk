package com.sensewalk.app.domain.sensory

import com.sensewalk.app.domain.scene.TestScenes
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.walk.VirtualWalkController
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 感官恢复（T07A / SW-004）：按当前米数静态重建——
 * loop 满淡入直接落目标增益；一次性提示/旧脚步不重播；
 * 恢复的 loop 不被后续重复相位事件重启。
 */
class SensoryRestoreTest {

    private class FakeClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    private class RecordingBackend : SensoryBackend {
        val startLoopCalls = mutableListOf<String>()
        val gainCalls = mutableListOf<Pair<String, Float>>()
        val stepCalls = mutableListOf<String>()
        var released = false

        override fun startLoop(layerId: String) { startLoopCalls.add(layerId) }
        override fun setLoopGain(layerId: String, gain: Float) { gainCalls.add(layerId to gain) }
        override fun playStep(layerId: String, variant: Int, volume: Float, pitchFactor: Float) { stepCalls.add(layerId) }
        override fun pauseAll() {}
        override fun resumeAll() {}
        override fun releaseAll() { released = true }
        override fun vibrate(patternId: String) {}
        override fun stopVibrate() {}
    }

    /** 走过环境解锁门的感官目标（当前米数静态值） */
    private fun sensoryAt(meters: Float): Pair<VirtualWalkController, com.sensewalk.app.domain.phase.SensoryState> {
        val clock = FakeClock()
        val c = VirtualWalkController(TestScenes.validConfig(), clock)
        c.onStick(1f)
        while (c.snapshot().meters < meters) { clock.now += 50; c.frame() }
        return c to c.snapshot().sensory
    }

    @Test
    fun `restoreState 后 loop 直接落目标增益 - 不从零淡入`() {
        val (_, sensory) = sensoryAt(350f) // 已过 ambience@240 门
        val backend = RecordingBackend()
        val coordinator = SensoryCoordinator(TestScenes.validConfig(), backend)

        coordinator.restoreState(sensory)

        assertTrue("已解锁 loop 应启动", backend.startLoopCalls.isNotEmpty())
        val ambienceGain = backend.gainCalls.firstOrNull { it.first == "ambience" }
        assertTrue("ambience 应有增益调用", ambienceGain != null)
        assertEquals(
            "恢复直接落在目标增益（满淡入）",
            sensory.audioTargets["ambience"]?.toVolume ?: 0f,
            ambienceGain!!.second,
            1e-3f,
        )
    }

    @Test
    fun `restoreState 不重播旧脚步 - 新前进才出声`() {
        val (_, sensory) = sensoryAt(150f) // 已过 steps@80 门
        val backend = RecordingBackend()
        val coordinator = SensoryCoordinator(TestScenes.validConfig(), backend)

        coordinator.restoreState(sensory)
        assertEquals("恢复瞬间不得补播任何脚步", 0, backend.stepCalls.size)

        // 新前进 1 步幅（0.7m）后出一步声（脚步层已解锁）
        coordinator.onFrame(dtMs = 1000f, metersDelta = 0.7f, walking = true)
        assertEquals("新步伐应正常出声", 1, backend.stepCalls.size)
    }

    @Test
    fun `恢复层不被重复相位事件重启 - 与 onPhaseEvents 兼容`() {
        val (original, sensory) = sensoryAt(350f)
        val backend = RecordingBackend()
        val coordinator = SensoryCoordinator(TestScenes.validConfig(), backend)
        coordinator.restoreState(sensory)

        // 恢复会话若再次收到已触发相位事件（防御场景）：不重启已恢复层
        val ambPhase = TestScenes.validConfig().phases.first { it.id == "ambience" }
        coordinator.onPhaseEvents(listOf(com.sensewalk.app.domain.phase.PhaseEvent(ambPhase, 350f)))

        assertEquals("重复相位不得重启 loop", 1, backend.startLoopCalls.count { it == "ambience" })
    }
}
