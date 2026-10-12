package com.sensewalk.app.domain.progress

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** 有效前进会计（S2 / S9）：s_pos 与 s_best 分离、回退不重复计距 */
class ProgressAccumulatorTest {

    @Test
    fun `前进累计距离`() {
        val acc = ProgressAccumulator(100f)
        acc.advance(10f)
        acc.advance(20f)
        assertEquals(30f, acc.meters, 1e-6f)
        assertEquals(30f, acc.sPos, 1e-6f)
        assertEquals(30f, acc.sBest, 1e-6f)
    }

    @Test
    fun `S2 回退不减少有效米数`() {
        val acc = ProgressAccumulator(100f)
        acc.advance(50f)
        acc.advance(-30f)
        assertEquals(50f, acc.meters, 1e-6f)
        assertEquals(20f, acc.sPos, 1e-6f)
        assertEquals(50f, acc.sBest, 1e-6f)
    }

    @Test
    fun `S2 S9 走回旧位置不重复累计`() {
        val acc = ProgressAccumulator(100f)
        acc.advance(50f)
        acc.advance(-30f)
        acc.advance(30f) // 回到 50，全是旧位置
        assertEquals("回到历史最远不应增加米数", 50f, acc.meters, 1e-6f)
        acc.advance(10f) // 只有超过 50 的新地面才计
        assertEquals(60f, acc.meters, 1e-6f)
    }

    @Test
    fun `反复来回同一区间不刷距`() {
        val acc = ProgressAccumulator(100f)
        acc.advance(40f)
        repeat(10) {
            acc.advance(-15f)
            acc.advance(15f)
        }
        assertEquals(40f, acc.meters, 1e-6f)
    }

    @Test
    fun `回退不越过起点`() {
        val acc = ProgressAccumulator(100f)
        acc.advance(20f)
        acc.advance(-100f)
        assertEquals(0f, acc.sPos, 1e-6f)
        assertEquals(20f, acc.meters, 1e-6f)
        acc.advance(25f)
        assertEquals(25f, acc.meters, 1e-6f)
    }

    @Test
    fun `米数钳制到门禁距离`() {
        val acc = ProgressAccumulator(100f)
        acc.advance(150f)
        assertEquals(100f, acc.meters, 1e-6f)
        assertEquals(150f, acc.sBest, 1e-6f)
        acc.advance(30f) // 终点后继续走也不再涨
        assertEquals(100f, acc.meters, 1e-6f)
        assertEquals(0f, acc.remaining, 1e-6f)
    }

    @Test
    fun `NaN 与 Infinity 增量被忽略`() {
        val acc = ProgressAccumulator(100f)
        acc.advance(10f)
        acc.advance(Float.NaN)
        acc.advance(Float.POSITIVE_INFINITY)
        assertEquals(10f, acc.meters, 1e-6f)
        assertEquals(10f, acc.sPos, 1e-6f)
    }

    @Test
    fun `S9 快照往返保留 s_best - 回退后恢复不重复计距`() {
        val acc = ProgressAccumulator(200f)
        acc.advance(100f)
        acc.advance(-40f) // sPos=60, sBest=100, meters=100

        val restored = ProgressAccumulator.fromSnapshot(acc.snapshot())
        assertEquals(60f, restored.sPos, 1e-6f)
        assertEquals(100f, restored.sBest, 1e-6f)
        assertEquals(100f, restored.meters, 1e-6f)

        restored.advance(40f) // 走回旧最远位置
        assertEquals("恢复后走回旧位置不应重复计距", 100f, restored.meters, 1e-6f)
        restored.advance(10f)
        assertEquals(110f, restored.meters, 1e-6f)
    }

    @Test(expected = IllegalArgumentException::class)
    fun `非法门禁距离拒绝构造`() {
        ProgressAccumulator(0f)
    }

    @Test
    fun `remaining 反映剩余`() {
        val acc = ProgressAccumulator(800f)
        acc.advance(300f)
        assertEquals(500f, acc.remaining, 1e-6f)
        assertTrue(acc.meters < acc.requiredDistanceMeters)
    }
}
