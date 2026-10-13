package com.sensewalk.app.domain.sensory

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Android 播放后端的可注入回归（纯状态组件，非协调器冒充）：
 * 焦点拒绝、准备期暂停/释放、加载失败诊断、暂停停止活跃脚步、终态吸收迟到回调。
 */
class PlaybackSupportTest {

    // ---- LoopPlayerState：异步 prepare 生命周期 ----

    @Test
    fun `准备期间请求暂停 - 就绪后保持暂停不自动播放`() {
        val state = LoopPlayerState()
        state.requestStart() // 先请求开始
        state.requestPause() // 准备中又暂停（如刚启动就来电）
        state.onPrepared()
        assertEquals(LoopPlayerState.Phase.PAUSED, state.phase)
        assertFalse("不得自动播放", state.phase == LoopPlayerState.Phase.PLAYING)
    }

    @Test
    fun `准备期间请求开始 - 就绪后播放`() {
        val state = LoopPlayerState()
        state.requestStart()
        state.onPrepared()
        assertEquals(LoopPlayerState.Phase.PLAYING, state.phase)
    }

    @Test
    fun `准备期间释放 - 迟到的 onPrepared 被吸收`() {
        val state = LoopPlayerState()
        state.requestStart()
        state.release() // 准备中用户放弃（终态）
        state.onPrepared() // 迟到回调
        assertEquals("终态吸收迟到回调", LoopPlayerState.Phase.RELEASED, state.phase)
    }

    @Test
    fun `释放后请求与增益全部无效`() {
        val state = LoopPlayerState()
        state.onPrepared()
        state.release()
        state.requestStart()
        state.setGain(0.5f)
        state.onPrepared()
        assertEquals(LoopPlayerState.Phase.RELEASED, state.phase)
    }

    @Test
    fun `就绪前增益被缓存 - 就绪后可应用`() {
        val state = LoopPlayerState()
        state.setGain(0.35f)
        state.onPrepared()
        assertTrue(state.isPrepared)
        assertEquals(0.35f, state.gain, 1e-6f)
        state.setGain(0.7f)
        assertEquals("就绪后仍可更新", 0.7f, state.gain, 1e-6f)
    }

    @Test
    fun `播放中暂停再恢复 - 不需要重新准备`() {
        val state = LoopPlayerState()
        state.onPrepared()
        state.requestStart()
        state.requestPause()
        assertEquals(LoopPlayerState.Phase.PAUSED, state.phase)
        state.requestStart()
        assertEquals(LoopPlayerState.Phase.PLAYING, state.phase)
    }

    @Test
    fun `错误回调等同释放`() {
        val state = LoopPlayerState()
        state.requestStart()
        state.onError()
        assertEquals(LoopPlayerState.Phase.RELEASED, state.phase)
    }

    // ---- StepLayerLoadState：异步加载 ----

    @Test
    fun `未加载完成的变体不可播放`() {
        val state = StepLayerLoadState("footsteps", listOf(1, 2, 3), mapOf(1 to "a.ogg", 2 to "b.ogg", 3 to "c.ogg"))
        assertNull("全部未加载时跳过", state.playableVariant(0))
        state.onLoadComplete(2, true)
        assertEquals("轮换到已加载变体", 2, state.playableVariant(0))
        assertEquals(2, state.playableVariant(1)) // 只有一个可用
    }

    @Test
    fun `加载失败给出明确诊断`() {
        val state = StepLayerLoadState("footsteps", listOf(1, 2), mapOf(1 to "step_01.ogg", 2 to "step_02.ogg"))
        state.onLoadComplete(1, false)
        state.onLoadComplete(2, true)
        assertEquals(listOf(2), listOf(state.playableVariant(0)))
        assertEquals(1, state.failureDiagnostics.size)
        assertTrue(state.failureDiagnostics[0].contains("step_01.ogg"))
        assertTrue(state.failureDiagnostics[0].contains("footsteps"))
    }

    @Test
    fun `未知 soundId 的回调被忽略`() {
        val state = StepLayerLoadState("footsteps", listOf(1), mapOf(1 to "a.ogg"))
        state.onLoadComplete(99, true)
        assertEquals(0, state.loadedCount)
        assertNull(state.playableVariant(0))
    }

    // ---- AudioFocusGate：恢复播放的焦点前置 ----

    @Test
    fun `焦点未获准不得恢复音频`() {
        val gate = AudioFocusGate()
        assertFalse(gate.canResumeAudio())
        gate.onRequestResult(0) // AUDIOFOCUS_REQUEST_FAILED
        assertFalse("焦点被拒 → 不得恢复", gate.canResumeAudio())
    }

    @Test
    fun `获准后可恢复 - 丢失后再次拒绝`() {
        val gate = AudioFocusGate()
        gate.onRequestResult(AudioFocusGate.REQUEST_GRANTED)
        assertTrue(gate.canResumeAudio())
        gate.onFocusLoss() // 来电/切音乐
        assertFalse(gate.canResumeAudio())
    }

    @Test
    fun `中断后重新申请获准则恢复`() {
        val gate = AudioFocusGate()
        gate.onRequestResult(AudioFocusGate.REQUEST_GRANTED)
        gate.onFocusLoss()
        assertFalse(gate.canResumeAudio())
        gate.onRequestResult(AudioFocusGate.REQUEST_GRANTED) // 用户操作触发重申
        assertTrue(gate.canResumeAudio())
    }

    // ---- ActiveStepStreams：脚步流管理 ----

    @Test
    fun `暂停停止活跃脚步流 - 恢复不补播旧流`() {
        val streams = ActiveStepStreams()
        streams.onStreamStarted(101)
        streams.onStreamStarted(102)
        streams.onStreamStarted(0) // 失败流忽略
        assertEquals(2, streams.activeCount)
        val stopped = streams.stopAll()
        assertEquals(setOf(101, 102), stopped.toSet())
        assertEquals("停止后无活跃流", 0, streams.activeCount)
        assertNull("恢复不补播旧脚步", streams.resumeStreams())
    }
}
