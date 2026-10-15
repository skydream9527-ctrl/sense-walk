package com.sensewalk.app.engine.sensor

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 传感器源注册边界（SW-001 F-003）：以假端口验证真实注册结果、
 * 部分注册清理与重复停止——不把硬件存在当注册成功。
 */
class StepSensorSourceTest {

    private class FakePort(
        override val hasCounter: Boolean = true,
        override val hasDetector: Boolean = true,
        var counterRegisterOk: Boolean = true,
        var detectorRegisterOk: Boolean = true,
    ) : SensorPort {
        var counterRegistered = false
        var detectorRegistered = false
        var unregisterCalls = 0
        val counterEvents = mutableListOf<(Long, Long) -> Unit>()
        val detectorEvents = mutableListOf<(Long) -> Unit>()

        override fun registerCounter(onEvent: (Long, Long) -> Unit): Boolean {
            if (!counterRegisterOk) return false
            counterRegistered = true
            counterEvents.add(onEvent)
            return true
        }

        override fun registerDetector(onEvent: (Long) -> Unit): Boolean {
            if (!detectorRegisterOk) return false
            detectorRegistered = true
            detectorEvents.add(onEvent)
            return true
        }

        override fun unregisterAll() {
            unregisterCalls++
            counterRegistered = false
            detectorRegistered = false
            counterEvents.clear()
            detectorEvents.clear()
        }
    }

    private fun source(port: FakePort) = StepSensorSource(
        port = port,
        onCounter = { _, _ -> },
        onDetectorStep = { },
    )

    @Test
    fun `counter 注册失败 - 返回 false 且不留任何监听`() {
        val port = FakePort(counterRegisterOk = false)
        val src = source(port)
        assertFalse("注册失败不得被当作成功", src.start())
        assertFalse(src.isStarted)
        assertEquals("失败路径必须清理（哪怕只注册了部分）", 1, port.unregisterCalls)
        assertFalse(port.counterRegistered)
        assertFalse(port.detectorRegistered)
    }

    @Test
    fun `counter 失败 detector 成功 - 部分注册被清理`() {
        val port = FakePort(counterRegisterOk = false, detectorRegisterOk = true)
        val src = source(port)
        assertFalse(src.start())
        assertEquals(1, port.unregisterCalls)
        assertFalse("已注册的 detector 不得残留", port.detectorRegistered)
    }

    @Test
    fun `detector 注册失败 - counter-only 仍可实走`() {
        val port = FakePort(detectorRegisterOk = false)
        val src = source(port)
        assertTrue(src.start())
        assertTrue(src.isStarted)
        assertTrue(port.counterRegistered)
        assertFalse(port.detectorRegistered)
        assertEquals("整体成功时不做多余清理", 0, port.unregisterCalls)
    }

    @Test
    fun `权限变化场景 - 曾成功的注册失败后提供 false 而非沿用存在性`() {
        val port = FakePort()
        val src = source(port)
        assertTrue(src.start())
        src.stop()
        // 权限被撤后重注册：registerListener 实际返回 false
        port.counterRegisterOk = false
        assertFalse(src.start())
        assertFalse(src.isStarted)
    }

    @Test
    fun `重复 stop 幂等 - 只注销一次`() {
        val port = FakePort()
        val src = source(port)
        assertTrue(src.start())
        src.stop()
        src.stop()
        src.stop()
        assertEquals(1, port.unregisterCalls)
    }

    @Test
    fun `无 counter 硬件 - 直接不可计距且不触碰注册`() {
        val port = FakePort(hasCounter = false)
        val src = source(port)
        assertFalse(src.canCountDistance)
        assertFalse(src.start())
        assertEquals("未注册即无清理对象，但不应崩溃", 0, port.unregisterCalls)
    }

    @Test
    fun `P01 detector 硬件在但注册失败 - cue 回退距离驱动`() {
        val port = FakePort(hasDetector = true, detectorRegisterOk = false)
        val src = source(port)
        assertTrue(src.start())
        assertTrue("硬件存在", port.hasDetector)
        assertFalse("注册未成功", src.detectorActive)
        assertTrue("注册失败必须回退距离脚步音（P-01：不得因硬件存在而静音）", src.cueAudioFromDistance)
    }

    @Test
    fun `P01 detector 注册成功 - cue 由 detector 驱动`() {
        val port = FakePort()
        val src = source(port)
        assertTrue(src.start())
        assertTrue(src.detectorActive)
        assertFalse("detector 在岗时距离不再出脚步音（避免双份）", src.cueAudioFromDistance)
    }

    @Test
    fun `P01 无 detector 硬件 - counter-only 同样距离驱动`() {
        val port = FakePort(hasDetector = false)
        val src = source(port)
        assertTrue(src.start())
        assertFalse(src.detectorActive)
        assertTrue(src.cueAudioFromDistance)
    }

    @Test
    fun `P01 stop 重置 detector 注册态 - 不残留上次的注册结果`() {
        val port = FakePort()
        val src = source(port)
        assertTrue(src.start())
        assertTrue(src.detectorActive)
        src.stop()
        assertFalse(src.detectorActive)
        assertFalse("停止后不提供任何 cue 来源", src.cueAudioFromDistance)
    }

    @Test
    fun `注册成功后回调链路保持 - counter 事件到达监听`() {
        val port = FakePort()
        var received: Long = -1
        val src = StepSensorSource(port, onCounter = { c, _ -> received = c }, onDetectorStep = { })
        assertTrue(src.start())
        port.counterEvents.last().invoke(42L, 1_000L)
        assertEquals(42L, received)
    }
}
