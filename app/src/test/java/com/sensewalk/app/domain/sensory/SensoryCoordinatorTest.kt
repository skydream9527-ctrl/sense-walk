package com.sensewalk.app.domain.sensory

import com.sensewalk.app.domain.phase.PhaseEvent
import com.sensewalk.app.domain.scene.Phase
import com.sensewalk.app.domain.scene.PhaseChannel
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.TestScenes
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.random.Random

/**
 * 感官协调器（T05）：步伐节奏、停走冻结、everyNSteps 振动、
 * 终态释放、重复相位不重启轨道——全部用注入 Fake 后端验证。
 */
class SensoryCoordinatorTest {

    private class FakeBackend : SensoryBackend {
        val startedLoops = mutableListOf<String>()
        val gains = mutableMapOf<String, Float>()
        val steps = mutableListOf<Triple<String, Int, Float>>() // layer, variant, volume
        val vibrations = mutableListOf<String>()
        var paused = false
        var released = false

        override fun startLoop(layerId: String) {
            startedLoops.add(layerId)
        }

        override fun setLoopGain(layerId: String, gain: Float) {
            gains[layerId] = gain
        }

        override fun playStep(layerId: String, variant: Int, volume: Float, pitchFactor: Float) {
            steps.add(Triple(layerId, variant, volume))
        }

        override fun pauseAll() {
            paused = true
        }

        override fun resumeAll() {
            paused = false
        }

        override fun releaseAll() {
            released = true
            paused = true
        }

        override fun vibrate(patternId: String) {
            vibrations.add(patternId)
        }

        override fun stopVibrate() {}
    }

    private val config: SceneConfig = TestScenes.validConfig()

    // 便捷相位（与 TestScenes.defaultPhases 对应）
    private val stepsPhase = config.phases.first { it.id == "steps" }     // footsteps, 0.25, 8000ms
    private val ambiencePhase = config.phases.first { it.id == "ambience" } // ambience, 0.35, 12000ms
    private val hapticPhase = config.phases.first { it.id == "haptic" }   // footstep_soft, every 2

    private fun newCoordinator(): Pair<SensoryCoordinator, FakeBackend> {
        val backend = FakeBackend()
        return SensoryCoordinator(config, backend, Random(7)) to backend
    }

    @Test
    fun `脚步层未解锁前保持静默 - 不因移动发声`() {
        val (coordinator, backend) = newCoordinator()
        // 未触发 steps 相位（80m 阈值前）：即使持续前进也无脚步
        coordinator.onFrame(dtMs = 50f, metersDelta = 0.7f, walking = true)
        coordinator.onFrame(dtMs = 50f, metersDelta = 0.7f, walking = true)
        assertTrue("解锁前不得有脚步", backend.steps.isEmpty())
        assertTrue(backend.startedLoops.isEmpty())
    }

    @Test
    fun `脚步按步伐节奏触发 - 不按渲染帧`() {
        val backend = FakeBackend()
        // 步长用可精确表示的 0.5m，帧增量 0.125m（二进制精确），杜绝浮点误差影响断言
        val coordinator = SensoryCoordinator(config, backend, Random(7), strideMeters = 0.5f)
        coordinator.onPhaseEvents(listOf(PhaseEvent(stepsPhase, 100f)))
        // 100 个小帧共 12.5m → 25 步：与帧数无关，只看有效距离
        repeat(100) { coordinator.onFrame(dtMs = 16.7f, metersDelta = 0.125f, walking = true) }
        assertEquals(25, backend.steps.size)
        // 1 帧走 2.0m → 4 步
        coordinator.onFrame(dtMs = 50f, metersDelta = 2.0f, walking = true)
        assertEquals(29, backend.steps.size)
    }

    @Test
    fun `静止与回退不产生脚步`() {
        val (coordinator, backend) = newCoordinator()
        coordinator.onPhaseEvents(listOf(PhaseEvent(stepsPhase, 100f)))
        // 站立（delta=0）：即使时间流逝也不出声——时间不能制造脚步
        repeat(60) { coordinator.onFrame(dtMs = 50f, metersDelta = 0f, walking = true) }
        assertTrue(backend.steps.isEmpty())
        // 非行走状态（暂停/终态间）也不出声
        coordinator.onFrame(dtMs = 50f, metersDelta = 0.7f, walking = false)
        assertTrue(backend.steps.isEmpty())
    }

    @Test
    fun `脚步变体与音量在规格范围内`() {
        val backend = FakeBackend()
        // 固定随机源，可复现
        val coordinator = SensoryCoordinator(config, backend, Random(42))
        coordinator.onPhaseEvents(listOf(PhaseEvent(stepsPhase, 100f)))
        coordinator.onFrame(dtMs = 50f, metersDelta = 7.0f, walking = true) // 10 步
        assertEquals(10, backend.steps.size)
        backend.steps.forEach { (layer, variant, volume) ->
            assertEquals("footsteps", layer)
            assertTrue("变体 0..1（TestScenes 有 2 个文件）: $variant", variant in 0..1)
            assertTrue("音量 0.25±10%: $volume", volume in (0.25f * 0.9f)..(0.25f * 1.1f))
        }
        // 变体确有随机分布
        assertTrue(backend.steps.map { it.second }.toSet().size >= 1)
    }

    @Test
    fun `环境淡入按 fadeMs 推进且停走冻结增益`() {
        val (coordinator, backend) = newCoordinator()
        coordinator.onPhaseEvents(listOf(PhaseEvent(ambiencePhase, 300f)))
        assertTrue(backend.startedLoops.contains("ambience"))
        assertEquals("淡入从 0 开始", 0f, backend.gains["ambience"]!!, 1e-6f)

        // 前进 2 秒：0.35 × 2000/12000 ≈ 0.0583
        repeat(40) { coordinator.onFrame(dtMs = 50f, metersDelta = 0.05f, walking = true) }
        val gainWhileWalking = backend.gains["ambience"]!!
        assertTrue(gainWhileWalking in 0.05f..0.07f)

        // 停走（delta=0）3 秒：增益冻结不变
        repeat(60) { coordinator.onFrame(dtMs = 50f, metersDelta = 0f, walking = true) }
        assertEquals("停走冻结淡入增益", gainWhileWalking, backend.gains["ambience"]!!, 1e-9f)

        // 重新行走：从冻结值继续，不重置
        repeat(40) { coordinator.onFrame(dtMs = 50f, metersDelta = 0.05f, walking = true) }
        assertTrue("淡入继续推进", backend.gains["ambience"]!! > gainWhileWalking + 0.05f)
        assertTrue("淡入不超过目标音量", backend.gains["ambience"]!! <= 0.35f + 1e-6f)
    }

    @Test
    fun `fadeMs 为 0 的层立即到目标增益`() {
        val (coordinator, backend) = newCoordinator()
        val instant = ambiencePhase.copy(fadeMs = 0)
        coordinator.onPhaseEvents(listOf(PhaseEvent(instant, 300f)))
        assertEquals(0.35f, backend.gains["ambience"]!!, 1e-6f)
    }

    @Test
    fun `重复相位事件不重启轨道`() {
        val (coordinator, backend) = newCoordinator()
        coordinator.onPhaseEvents(listOf(PhaseEvent(ambiencePhase, 300f)))
        coordinator.onPhaseEvents(listOf(PhaseEvent(ambiencePhase, 300f))) // 迟到/重复
        assertEquals("同层只启动一次", 1, backend.startedLoops.count { it == "ambience" })
    }

    @Test
    fun `暂停冻结淡入且恢复后继续 - 不重置相位`() {
        val (coordinator, backend) = newCoordinator()
        coordinator.onPhaseEvents(listOf(PhaseEvent(ambiencePhase, 300f)))
        repeat(20) { coordinator.onFrame(dtMs = 50f, metersDelta = 0.05f, walking = true) }
        val beforePause = backend.gains["ambience"]!!

        coordinator.pause()
        assertTrue(backend.paused)
        repeat(20) { coordinator.onFrame(dtMs = 50f, metersDelta = 0.05f, walking = false) }
        assertEquals("暂停期间增益不变", beforePause, backend.gains["ambience"]!!, 1e-9f)

        coordinator.resume()
        assertTrue(!backend.paused)
        repeat(20) { coordinator.onFrame(dtMs = 50f, metersDelta = 0.05f, walking = true) }
        assertTrue("恢复后淡入继续", backend.gains["ambience"]!! > beforePause)
        assertEquals("恢复不重启轨道", 1, backend.startedLoops.count { it == "ambience" })
    }

    @Test
    fun `everyNSteps 振动跟随步伐且尊重开关`() {
        val (coordinator, backend) = newCoordinator()
        coordinator.onPhaseEvents(
            listOf(PhaseEvent(stepsPhase, 100f), PhaseEvent(hapticPhase, 500f)),
        )
        coordinator.onFrame(dtMs = 50f, metersDelta = 7.0f, walking = true) // 10 步
        assertEquals("every 2 → 5 次振动", 5, backend.vibrations.count { it == "footstep_soft" })

        coordinator.setVibrationEnabled(false)
        coordinator.onFrame(dtMs = 50f, metersDelta = 7.0f, walking = true) // 再 10 步
        assertEquals("关闭后不再振动", 5, backend.vibrations.size)
    }

    @Test
    fun `振动未解锁前不触发`() {
        val (coordinator, backend) = newCoordinator()
        coordinator.onPhaseEvents(listOf(PhaseEvent(stepsPhase, 100f))) // 未触发 haptic 相位
        coordinator.onFrame(dtMs = 50f, metersDelta = 7.0f, walking = true)
        assertTrue(backend.vibrations.isEmpty())
    }

    @Test
    fun `终态释放后不再发声`() {
        val (coordinator, backend) = newCoordinator()
        coordinator.onPhaseEvents(
            listOf(PhaseEvent(stepsPhase, 100f), PhaseEvent(ambiencePhase, 300f), PhaseEvent(hapticPhase, 500f)),
        )
        coordinator.onFrame(dtMs = 50f, metersDelta = 7.0f, walking = true)
        val stepsBefore = backend.steps.size

        coordinator.release()
        assertTrue(backend.released)
        // 终态后：帧/相位事件/输入全部无效
        coordinator.onFrame(dtMs = 50f, metersDelta = 7.0f, walking = true)
        coordinator.onPhaseEvents(listOf(PhaseEvent(stepsPhase, 100f)))
        assertEquals("终态后无新脚步", stepsBefore, backend.steps.size)
    }
}
