package com.sensewalk.app.domain.stick

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** 速度惯性（§4.3.2）：τ 选择、dt 防护与时间常数行为 */
class VelocityInertiaTest {

    private fun walk(inertia: VelocityInertia, seconds: Float, target: Float, dt: Float = 0.05f) {
        var t = 0f
        while (t < seconds) {
            inertia.step(dt, target)
            t += dt
        }
    }

    @Test
    fun `加速 τ 0_60 - 从静止约 2 秒接近甜点速度`() {
        val inertia = VelocityInertia()
        walk(inertia, 1.0f, 1.18f)
        val v1s = inertia.velocity
        // 1.18 × (1 − e^(−1/0.6)) ≈ 0.957
        assertTrue("1 秒应到约 0.96，实际 $v1s", v1s in 0.90f..1.00f)

        walk(inertia, 1.0f, 1.18f)
        val v2s = inertia.velocity
        assertTrue("2 秒应接近 1.18，实际 $v2s", v2s > 1.00f)
        assertTrue("速度不得超目标", v2s <= 1.18f)
    }

    @Test
    fun `减速 τ 0_35 - 从甜点到拉满目标慢慢掉下去`() {
        val inertia = VelocityInertia(1.18f)
        walk(inertia, 1.0f, 0.65f)
        val v = inertia.velocity
        // 0.65 + 0.53×e^(−1/0.35) ≈ 0.68：约 1 秒缓慢接近拉满速度
        assertTrue("1 秒后应接近 0.65，实际 $v", v in 0.65f..0.75f)
    }

    @Test
    fun `松手 τ 0_25 - 约 1 秒内停稳`() {
        val inertia = VelocityInertia(1.18f)
        walk(inertia, 1.05f, 0f)
        assertTrue("松手 1 秒后应基本停稳，实际 ${inertia.velocity}", inertia.velocity < 0.05f)
    }

    @Test
    fun `dt 上限 0_05 - 大 dt 不追补后台时间`() {
        val capped = VelocityInertia()
        capped.step(10_000f, 1.18f) // 假装后台回来传了 10000 秒

        val reference = VelocityInertia()
        reference.step(0.05f, 1.18f)

        assertEquals("大 dt 只按 0.05s 步进", reference.velocity, capped.velocity, 1e-6f)
    }

    @Test
    fun `负 dt 不改变速度`() {
        val inertia = VelocityInertia(0.5f)
        assertEquals(0.5f, inertia.step(-1f, 1.18f), 1e-6f)
        assertEquals(0.5f, inertia.velocity, 1e-6f)
    }

    @Test
    fun `NaN dt 不改变速度`() {
        val inertia = VelocityInertia(0.5f)
        assertEquals(0.5f, inertia.step(Float.NaN, 1.18f), 1e-6f)
    }

    @Test
    fun `Infinity dt 不改变速度`() {
        val inertia = VelocityInertia(0.5f)
        assertEquals(0.5f, inertia.step(Float.POSITIVE_INFINITY, 1.18f), 1e-6f)
    }

    @Test
    fun `NaN 目标速度按松手处理`() {
        val inertia = VelocityInertia(1.18f)
        inertia.step(0.05f, Float.NaN)
        assertTrue("NaN 目标应按 0 处理并减速，实际 ${inertia.velocity}", inertia.velocity < 1.18f)
    }

    @Test
    fun `reset 清零速度`() {
        val inertia = VelocityInertia(1.0f)
        inertia.reset()
        assertEquals(0f, inertia.velocity, 1e-6f)
    }

    @Test
    fun `初始速度非法值归零`() {
        assertEquals(0f, VelocityInertia(-3f).velocity, 1e-6f)
        assertEquals(0f, VelocityInertia(Float.NaN).velocity, 1e-6f)
    }
}
