package com.sensewalk.app.service

import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.TestScenes
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.sensory.SensoryBackend
import com.sensewalk.app.domain.sensory.SensoryCoordinator
import com.sensewalk.app.domain.walk.RealWalkController
import com.sensewalk.app.engine.sensor.SensorPort
import com.sensewalk.app.engine.sensor.StepSensorSource
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * P-01 调用链测试：传感器**注册结果** → 服务接线 → 感官协调器 → 后端实际出声。
 *
 * 端口级测试只证明 start() 成败；这里按 WalkForegroundService.setupSession /
 * onCounterEvent / onDetectorStep 的**同一接线顺序**驱动，验证：
 * - detector 硬件在但注册失败 → cue 回退距离驱动且**真实出声**（不再双双静音）；
 * - detector 注册成功 → 距离不出脚步音，detector cue 出声，无双份；
 * - 两种来源下计距都只来自 counter（无双计距）。
 */
class SensorCueWiringTest {

    private class FakeClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    private class FakePort(
        override val hasCounter: Boolean = true,
        override val hasDetector: Boolean = true,
        private val counterRegisterOk: Boolean = true,
        private val detectorRegisterOk: Boolean = true,
    ) : SensorPort {
        val counterEvents = mutableListOf<(Long, Long) -> Unit>()
        val detectorEvents = mutableListOf<(Long) -> Unit>()

        override fun registerCounter(onEvent: (Long, Long) -> Unit): Boolean {
            counterEvents.add(onEvent)
            return counterRegisterOk
        }

        override fun registerDetector(onEvent: (Long) -> Unit): Boolean {
            if (!detectorRegisterOk) return false
            detectorEvents.add(onEvent)
            return true
        }

        override fun unregisterAll() {
            counterEvents.clear()
            detectorEvents.clear()
        }
    }

    private class RecordingBackend : SensoryBackend {
        val startLoopCalls = mutableListOf<String>()
        val stepCalls = mutableListOf<String>()
        val vibrateCalls = mutableListOf<String>()

        override fun startLoop(layerId: String) {
            startLoopCalls.add(layerId)
        }

        override fun setLoopGain(layerId: String, gain: Float) {}

        override fun playStep(layerId: String, variant: Int, volume: Float, pitchFactor: Float) {
            stepCalls.add(layerId)
        }

        override fun pauseAll() {}

        override fun resumeAll() {}

        override fun releaseAll() {}

        override fun vibrate(patternId: String) {
            vibrateCalls.add(patternId)
        }

        override fun stopVibrate() {}
    }

    /** 与 WalkForegroundService 相同的接线与事件处理顺序 */
    private class Wiring(port: FakePort) {
        val config: SceneConfig = TestScenes.validConfig()
        val backend = RecordingBackend()
        val clock = FakeClock()
        val controller = RealWalkController(config, clock)
        val coordinator = SensoryCoordinator(config, backend)
        val source = StepSensorSource(
            port = port,
            onCounter = ::onCounterEvent,
            onDetectorStep = ::onDetectorStep,
        )

        /** 服务 setupSession 的接线片段 */
        fun startSession(): Boolean {
            if (!source.start()) return false
            coordinator.stepAudioFromDistance = source.cueAudioFromDistance
            coordinator.onPhaseEvents(controller.drainPhaseEvents())
            controller.start()
            return true
        }

        /** 服务 onCounterEvent 的同序调用链 */
        fun onCounterEvent(stepCount: Long, eventTimeMs: Long) {
            val snap = controller.onCounterEvent(stepCount, eventTimeMs)
            coordinator.onPhaseEvents(controller.drainPhaseEvents())
            coordinator.onFrame(
                dtMs = snap.frameDtMs,
                metersDelta = snap.metersDelta,
                walking = snap.session == SessionState.WALKING,
            )
        }

        /** 服务 onDetectorStep 的同序调用链 */
        fun onDetectorStep(eventTimeMs: Long) {
            if (controller.onDetectorStep(eventTimeMs)) {
                coordinator.onStepCue()
            }
        }

        fun meters(): Float = controller.snapshot().meters

        /** 按物理节奏注入 counter 事件：每秒 +2 步 = 1.4 m/s（封顶值） */
        fun walkSeconds(seconds: Int, startCount: Long = 0L, startMs: Long = 1_000L) {
            onCounterEvent(startCount, startMs) // 基线
            var count = startCount
            var t = startMs
            repeat(seconds) {
                count += 2
                t += 1_000
                onCounterEvent(count, t)
            }
        }
    }

    @Test
    fun `P01 detector 注册失败 - 回退距离脚步音且跨解锁门后真实出声`() {
        val port = FakePort(hasDetector = true, detectorRegisterOk = false)
        val w = Wiring(port)
        assertTrue(w.startSession())
        assertTrue("注册失败必须回退距离驱动", w.source.cueAudioFromDistance)
        assertTrue("接线必须采用注册结果", w.coordinator.stepAudioFromDistance)
        assertEquals("detector 未注册成功不得挂监听", 0, port.detectorEvents.size)

        w.walkSeconds(seconds = 150) // 210m：跨过 100m 脚步解锁门
        assertTrue("应已跨过脚步解锁门", w.meters() > 100f)
        assertTrue("counter-only 回退必须真实出声（P-01 核心回归）", w.backend.stepCalls.isNotEmpty())
        assertEquals("计距只来自 counter 事件注入", 210f, w.meters(), 0.5f)
    }

    @Test
    fun `P01 detector 注册成功 - 距离不再出脚步音而 detector cue 出声`() {
        val port = FakePort()
        val w = Wiring(port)
        assertTrue(w.startSession())
        assertFalse(w.source.cueAudioFromDistance)
        assertFalse("接线必须采用注册结果", w.coordinator.stepAudioFromDistance)

        w.walkSeconds(seconds = 150) // 210m：跨过 100m 脚步解锁门
        assertTrue(w.meters() > 100f)
        assertTrue("计距照常来自 counter", port.counterEvents.isNotEmpty())
        assertEquals("detector 在岗时距离不得再出脚步音", 0, w.backend.stepCalls.size)

        // detector 步伐事件（>节流间隔）→ 脚步音来自 cue，且不双份
        port.detectorEvents.last().invoke(151_000L)
        port.detectorEvents.last().invoke(152_000L)
        assertEquals("detector cue 必须真实出声", 2, w.backend.stepCalls.size)
        assertEquals("计距不受 detector 影响（无双计距）", 210f, w.meters(), 0.5f)
    }

    @Test
    fun `P01 无 detector 硬件 - counter-only 距离驱动出声`() {
        val port = FakePort(hasDetector = false)
        val w = Wiring(port)
        assertTrue(w.startSession())
        assertTrue(w.coordinator.stepAudioFromDistance)
        w.walkSeconds(seconds = 150)
        assertTrue("无硬件时距离脚步音可用", w.backend.stepCalls.isNotEmpty())
    }
}
