package com.sensewalk.app.domain.stick

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

/**
 * comfort_v1 曲线（§4.3.1）与映射（S1）：
 * 连续性测试明确采样间距 [SAMPLE_STEP]；无过冲按控制点分段范围验证。
 */
class ComfortStickMapperTest {

    private val mapper = ComfortStickMapper()

    /** S1 连续性采样间距（覆盖 [0,1] 共 501 个采样点） */
    private val sampleStep = 0.002f

    /** comfort_v1 控制点（§4.3.1 定稿表） */
    private val controlD = floatArrayOf(0.00f, 0.08f, 0.15f, 0.35f, 0.45f, 0.55f, 0.65f, 0.75f, 0.90f, 1.00f)
    private val controlV = floatArrayOf(0.00f, 0.00f, 0.45f, 0.90f, 1.08f, 1.18f, 1.10f, 1.00f, 0.85f, 0.65f)

    @Test
    fun `控制点精确求值`() {
        assertEquals(0f, mapper.targetSpeed(0f), 1e-6f)
        assertEquals(0f, mapper.targetSpeed(0.08f), 1e-6f) // 死区
        assertEquals(0.45f, mapper.targetSpeed(0.15f), 1e-6f)
        assertEquals(0.90f, mapper.targetSpeed(0.35f), 1e-6f)
        assertEquals(1.18f, mapper.targetSpeed(0.55f), 1e-6f) // 甜点峰值
        assertEquals(0.65f, mapper.targetSpeed(1.00f), 1e-6f) // 拉满
    }

    @Test
    fun `S1 曲线连续 - 密集采样相邻差小于 0_05`() {
        var prev = mapper.targetSpeed(0f)
        var d = sampleStep
        while (d <= 1f) {
            val v = mapper.targetSpeed(d)
            assertTrue("相邻采样差超限: d=$d diff=${v - prev}", abs(v - prev) < 0.05f)
            prev = v
            d += sampleStep
        }
    }

    @Test
    fun `S1 分段保形无过冲 - 段内值不越过端点范围`() {
        val step = 0.001f
        for (i in 0 until controlD.size - 1) {
            val lo = kotlin.math.min(controlV[i], controlV[i + 1])
            val hi = kotlin.math.max(controlV[i], controlV[i + 1])
            val eps = 1e-5f
            var d = controlD[i]
            while (d <= controlD[i + 1] + eps) {
                val v = mapper.targetSpeed(d)
                assertTrue(
                    "段 [$i] d=$d 过冲: v=$v 不在 [$lo, $hi]",
                    v >= lo - eps && v <= hi + eps,
                )
                d += step
            }
        }
    }

    @Test
    fun `S1 全程速度不超过 1_4 硬顶且峰值就是 1_18`() {
        var max = 0f
        var d = 0f
        while (d <= 1f) {
            val v = mapper.targetSpeed(d)
            assertTrue("d=$d v=$v 超 1.4 硬顶", v <= ComfortStickMapper.SPEED_HARD_CAP)
            if (v > max) max = v
            d += 0.001f
        }
        assertTrue("峰值应严格等于 1.18（保形无过冲），实际 $max", abs(max - 1.18f) < 1e-4f)
    }

    @Test
    fun `S1 拉满明显慢于甜点`() {
        val peak = mapper.targetSpeed(ComfortStickMapper.SWEET_SPOT_DEFLECTION)
        val full = mapper.targetSpeed(1.0f)
        assertTrue("v(1.0)=$full 应明显小于 v(0.55)=$peak", full < peak)
        assertTrue("v(1.0)/v(0.55) ≈ 0.55，实际 ${full / peak}", full / peak < 0.7f)
    }

    @Test
    fun `整条曲线先升后降`() {
        // [0, 0.55] 非递减；[0.55, 1] 非递增
        var d = 0f
        var prev = mapper.targetSpeed(0f)
        while (d < 0.55f) {
            d += 0.005f
            val v = mapper.targetSpeed(d)
            assertTrue("上升段在 d=$d 出现下降", v >= prev - 1e-6f)
            prev = v
        }
        prev = mapper.targetSpeed(0.55f)
        while (d < 1f) {
            d += 0.005f
            val v = mapper.targetSpeed(d)
            assertTrue("下降段在 d=$d 出现上升", v <= prev + 1e-6f)
            prev = v
        }
    }

    @Test
    fun `左推不产生前进目标速度`() {
        assertEquals(0f, mapper.targetSpeed(-0.5f), 1e-6f)
        assertEquals(0f, mapper.targetSpeed(-0.01f), 1e-6f)
    }

    @Test
    fun `NaN 输入返回 0 且不污染后续求值`() {
        assertEquals(0f, mapper.targetSpeed(Float.NaN), 1e-6f)
        assertEquals(1.18f, mapper.targetSpeed(0.55f), 1e-6f)
        assertEquals(0f, mapper.targetSpeed(Float.NaN), 1e-6f)
    }

    @Test
    fun `超出 1 的偏转钳制到端点`() {
        assertEquals(mapper.targetSpeed(1f), mapper.targetSpeed(1.5f), 1e-6f)
        assertEquals(mapper.targetSpeed(1f), mapper.targetSpeed(7f), 1e-6f)
    }

    @Test
    fun `死区在 0_08 内无速度`() {
        assertEquals(0f, mapper.targetSpeed(0.05f), 1e-4f)
        assertEquals(0f, mapper.targetSpeed(0.08f), 1e-6f)
        assertTrue("越过死区应有速度", mapper.targetSpeed(0.12f) > 0f)
    }
}
