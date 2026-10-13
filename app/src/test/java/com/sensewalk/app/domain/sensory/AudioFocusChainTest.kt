package com.sensewalk.app.domain.sensory

import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.TestScenes
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.walk.VirtualWalkController
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 音频焦点门控调用链测试（T05 定点修复 1）：
 * 控制器 → 相位事件 → 协调器 → 后端，与 SessionViewModel 相同的驱动顺序。
 *
 * 不只验证 AudioFocusGate 的布尔值——用记录型假后端验证**实际出声调用**：
 * 焦点未获准时跨过脚步/环境解锁门也不出声；获准后只播新步伐、
 * 环境层不重复创建；距离与相位照常推进（静默不阻塞行走）。
 */
class AudioFocusChainTest {

    private class FakeClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    /** 记录型后端：按序记录一切出声相关调用 */
    private class RecordingBackend : SensoryBackend {
        val startLoopCalls = mutableListOf<String>()
        val gainCalls = mutableListOf<Pair<String, Float>>()
        val stepCalls = mutableListOf<String>()
        val vibrateCalls = mutableListOf<String>()
        var pauseCalls = 0
        var resumeCalls = 0
        var released = false

        override fun startLoop(layerId: String) {
            startLoopCalls.add(layerId)
        }

        override fun setLoopGain(layerId: String, gain: Float) {
            gainCalls.add(layerId to gain)
        }

        override fun playStep(layerId: String, variant: Int, volume: Float, pitchFactor: Float) {
            stepCalls.add(layerId)
        }

        override fun pauseAll() {
            pauseCalls++
        }

        override fun resumeAll() {
            resumeCalls++
        }

        override fun releaseAll() {
            released = true
        }

        override fun vibrate(patternId: String) {
            vibrateCalls.add(patternId)
        }

        override fun stopVibrate() {}
    }

    /** 与 SessionViewModel.onFrame 相同的调用链 */
    private class Chain(
        val config: SceneConfig,
        val backend: RecordingBackend,
        val coordinator: SensoryCoordinator,
        val controller: VirtualWalkController,
        private val clock: FakeClock,
    ) {
        val gate = AudioFocusGate()

        /** 申请焦点并按结果同步协调器许可（VM.setupAudioInterruptionHandling 的领域侧） */
        fun requestFocus(result: Int) {
            gate.onRequestResult(result)
            coordinator.setAudioAllowed(gate.canResumeAudio())
        }

        fun focusLost() {
            gate.onFocusLoss()
            coordinator.setAudioAllowed(false)
            controller.pause()
            coordinator.pause()
        }

        /** VM.attemptAudioResume 的领域侧：重申请并按结果恢复 */
        fun attemptAudioResume() {
            if (gate.canResumeAudio()) {
                coordinator.setAudioAllowed(true)
                coordinator.resume()
            } else {
                coordinator.setAudioAllowed(false)
            }
        }

        fun frames(n: Int) {
            repeat(n) {
                clock.now += FRAME_MS
                // 与 VM 相同：必须用 frame() 的返回值（snapshot() 的 frameDtMs/metersDelta 恒为 0）
                val s = controller.frame()
                coordinator.onPhaseEvents(controller.drainPhaseEvents())
                coordinator.onFrame(
                    dtMs = s.frameDtMs,
                    metersDelta = s.metersDelta,
                    walking = s.session == SessionState.WALKING,
                )
                if (s.session == SessionState.COMPLETED || s.session == SessionState.ABANDONED) {
                    coordinator.release()
                }
            }
        }

        fun meters(): Float = controller.snapshot().meters

        companion object {
            const val FRAME_MS = 50L

            fun create(): Chain {
                val config = TestScenes.validConfig()
                val backend = RecordingBackend()
                val clock = FakeClock()
                return Chain(
                    config = config,
                    backend = backend,
                    coordinator = SensoryCoordinator(config, backend),
                    controller = VirtualWalkController(config, clock),
                    clock = clock,
                )
            }
        }
    }

    // ---- 场景 1：首次申请被拒，跨 100/300/750m 解锁门仍无任何出声调用 ----

    @Test
    fun `首次焦点被拒 - 跨脚步与环境解锁门仍完全静默，距离相位照常推进`() {
        val chain = Chain.create()
        chain.requestFocus(0) // AUDIOFOCUS_REQUEST_FAILED
        chain.controller.onStick(0.55f)

        // 走过 100m（脚步）/300m（环境）/500m（振动）全部解锁门（留足余量，未到 750m/终点）
        chain.frames(9_500) // ≈540-560m
        assertTrue("应已跨过脚步/环境/振动解锁门，实际 ${chain.meters()}m", chain.meters() > 500f)

        assertTrue("焦点被拒不得播放任何脚步", chain.backend.stepCalls.isEmpty())
        assertTrue("焦点被拒不得启动任何环境层", chain.backend.startLoopCalls.isEmpty())
        assertTrue("未启动的层不得有增益调用", chain.backend.gainCalls.isEmpty())
        // 距离与相位照常推进：500m 的振动层已触发（振动不受音频焦点约束）
        assertTrue("振动照常跟随步伐", chain.backend.vibrateCalls.isNotEmpty())
        val fired = chain.controller.scheduler.firedPhaseIds
        assertTrue("相位调度照常推进", fired.containsAll(listOf("steps", "ambience", "haptic")))
    }

    // ---- 场景 2：中断后重申请被拒，继续行走仍静默（不新增出声调用） ----

    @Test
    fun `中断后重申请被拒 - 继续行走不新增脚步也不启动环境层`() {
        val chain = Chain.create()
        chain.requestFocus(AudioFocusGate.REQUEST_GRANTED)
        chain.controller.onStick(0.55f)
        chain.frames(2_200) // ≈125-135m：跨过 100m 脚步门并已出声
        val stepsBeforeLoss = chain.backend.stepCalls.size
        assertTrue("中断前应有脚步", stepsBeforeLoss > 0)

        // 外部中断（来电）：焦点丢失 → 暂停；「继续走」后重申请被拒
        chain.focusLost()
        chain.controller.resume() // 回 READY 等新输入（不自动行走）
        chain.requestFocus(0) // 重申请被拒
        chain.attemptAudioResume()
        chain.controller.onStick(0.55f) // 新输入开始行走（静默）
        chain.frames(6_000) // 再走 ≈340-390m：跨过 300m 环境解锁门（ambience 处于待启）

        assertEquals("被拒期间不得新增脚步", stepsBeforeLoss, chain.backend.stepCalls.size)
        assertTrue("被拒期间不得启动环境层", chain.backend.startLoopCalls.isEmpty())
        assertTrue("相位照常触发（ambience@300m）",
            chain.controller.scheduler.firedPhaseIds.contains("ambience"))
    }

    // ---- 场景 3：获准后仅播放新步伐；拒绝期激活的待启层按当前淡入进度恢复且只创建一次 ----

    @Test
    fun `获准后只播新步伐不补播 - 待启环境层按当前淡入进度启动且只创建一次`() {
        val chain = Chain.create()
        chain.requestFocus(0)
        chain.controller.onStick(0.55f)
        chain.frames(6_000) // ≈340-390m：静默跨过脚步门与 300m 环境门，ambience 处于待启
        val metersAtGrant = chain.meters()
        assertTrue("拒绝期应已跨过 300m 环境门", metersAtGrant > 300f)
        assertTrue("拒绝期不得有任何出声调用", chain.backend.stepCalls.isEmpty() && chain.backend.startLoopCalls.isEmpty())

        // 重申请获准：待启的 ambience 立即启动，且淡入已在拒绝期走完（>12s 行走）→ 直接落目标增益
        chain.requestFocus(AudioFocusGate.REQUEST_GRANTED)
        chain.attemptAudioResume()
        assertEquals("获准后 ambience 只启动一次", 1,
            chain.backend.startLoopCalls.count { it == "ambience" })
        val firstGain = chain.backend.gainCalls.first { it.first == "ambience" }.second
        assertTrue("待启层按当前淡入进度启动（首增益 $firstGain 应接近目标 0.35）", firstGain >= 0.3f)

        // 新脚步 ≈ 获准后距离/步幅：不得补播拒绝期间的 ~500 步
        chain.frames(500)
        val stepsAfterGrant = chain.backend.stepCalls.size
        val expectedNew = (chain.meters() - metersAtGrant) / 0.7f
        assertTrue(
            "新脚步 ${stepsAfterGrant} 应 ≈ 获准后距离/步幅 ${expectedNew.toInt()}（不补播拒绝期积累）",
            stepsAfterGrant in expectedNew.toInt() - 2..expectedNew.toInt() + 3,
        )

        // 幂等：重复放开许可不重复创建层
        chain.coordinator.setAudioAllowed(true)
        assertEquals("重复 setAudioAllowed(true) 不得重复创建层", 1,
            chain.backend.startLoopCalls.count { it == "ambience" })
    }

    // ---- 场景 4：准备期焦点丢失 / 暂停 / 终态均吸收迟到回调 ----

    @Test
    fun `准备期焦点丢失 - 迟到 onPrepared 不自动播放`() {
        val state = LoopPlayerState()
        state.requestStart() // startLoop：PREPARING，期望就绪后播放
        state.setGain(0.3f)
        state.requestPause() // 焦点丢失 → pauseAll：准备期登记为就绪后暂停
        state.onPrepared() // 迟到的 OnPrepared
        assertEquals(LoopPlayerState.Phase.PAUSED, state.phase)
        assertTrue("就绪后应用缓存增益", state.gain > 0f && state.isPrepared)
    }

    @Test
    fun `准备期终态释放 - 迟到 onPrepared 与后续请求全部吸收`() {
        val state = LoopPlayerState()
        state.requestStart()
        state.release() // 会话终态：releaseAll
        state.onPrepared()
        state.requestStart()
        state.requestPause()
        assertEquals(LoopPlayerState.Phase.RELEASED, state.phase)
    }

    @Test
    fun `协调器终态后放开许可也不得启动待启层`() {
        val chain = Chain.create()
        chain.requestFocus(0)
        chain.controller.onStick(0.55f)
        chain.frames(6_000) // 静默跨过 300m 环境门，ambience 处于待启
        assertTrue(chain.controller.scheduler.firedPhaseIds.contains("ambience"))
        chain.controller.abandon()
        chain.coordinator.release()
        assertTrue(chain.backend.released)
        chain.coordinator.setAudioAllowed(true) // 终态后放开许可
        assertTrue("终态吸收一切：不得启动任何层", chain.backend.startLoopCalls.isEmpty())
    }
}
