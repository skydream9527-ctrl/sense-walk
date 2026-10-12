package com.sensewalk.app.domain.progress

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** 距离门禁（S3）：满距只触发一次，迟到事件不再通关 */
class CompletionGateTest {

    @Test
    fun `未满距不触发`() {
        val gate = CompletionGate(800f)
        assertFalse(gate.onMeters(0f))
        assertFalse(gate.onMeters(799.99f))
        assertFalse(gate.isCompleted)
    }

    @Test
    fun `恰好满距触发一次`() {
        val gate = CompletionGate(800f)
        assertTrue("meters == required 应触发", gate.onMeters(800f))
        assertTrue(gate.isCompleted)
        assertFalse("重复上报不再触发", gate.onMeters(800f))
        assertFalse("迟到更高值不再触发", gate.onMeters(900f))
    }

    @Test
    fun `越过满距触发一次`() {
        val gate = CompletionGate(800f)
        assertTrue(gate.onMeters(1234f))
        assertFalse(gate.onMeters(9999f))
    }

    @Test
    fun `触发前米数回落再上涨只在真正满距时触发`() {
        val gate = CompletionGate(100f)
        assertFalse(gate.onMeters(99f))
        assertFalse(gate.onMeters(50f))
        assertTrue(gate.onMeters(100f))
    }

    @Test
    fun `NaN 米数不触发`() {
        val gate = CompletionGate(100f)
        assertFalse(gate.onMeters(Float.NaN))
        assertFalse(gate.onMeters(Float.POSITIVE_INFINITY))
        assertFalse(gate.isCompleted)
    }

    @Test(expected = IllegalArgumentException::class)
    fun `非法门禁距离拒绝构造`() {
        CompletionGate(-1f)
    }
}
