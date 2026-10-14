package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.session.MonotonicClock
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 实走计距引擎（T06，S5/S8）：counter 唯一计距源的全部边界。
 */
class RealWalkEngineTest {

    private class FakeClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    private fun engine(stride: Float = 0.70f) = RealWalkEngine(FakeClock(), stride)

    @Test
    fun `S8 首次事件只建立基线 - 不涨距`() {
        val e = engine()
        assertEquals(0f, e.onCounterEvent(5_000L, 100L).meters, 1e-6f)
        // 第二事件起才计距：1 步 × 0.7
        assertEquals(0.70f, e.onCounterEvent(5_001L, 700L).meters, 1e-3f)
    }

    @Test
    fun `正常步进 - 增量乘步长`() {
        val e = engine()
        e.onCounterEvent(0L, 0L)
        assertEquals(7.0f, e.onCounterEvent(10L, 10_000L).meters, 1e-3f) // 10 步 10s → 7m（未触顶）
    }

    @Test
    fun `S5 作弊序列 - 1 秒 10 步只得 1_4 米`() {
        val e = engine()
        e.onCounterEvent(0L, 0L)
        val d = e.onCounterEvent(10L, 1_000L)
        assertEquals("10×0.7=7m 应被封顶到 1.4×1s", 1.4f, d.meters, 1e-3f)
        assertEquals(1_000L, d.intervalMs)
    }

    @Test
    fun `S5 封顶按有效间隔线性 - 2 秒 20 步 2_8 米`() {
        val e = engine()
        e.onCounterEvent(0L, 0L)
        assertEquals(2.8f, e.onCounterEvent(20L, 2_000L).meters, 1e-3f)
    }

    @Test
    fun `S8 重复读数忽略 - 不涨距也不推进时间基线`() {
        val e = engine()
        e.onCounterEvent(100L, 0L)
        assertEquals(0f, e.onCounterEvent(100L, 5_000L).meters, 1e-6f)
        // 重复事件不该把时间基线推到 5s：此后 10 步于 6s 仍按 0→6s 间隔封顶（宽）
        val d = e.onCounterEvent(110L, 6_000L)
        assertEquals(7.0f, d.meters, 1e-3f) // 10 步 6s：raw 7m < cap 8.4m
    }

    @Test
    fun `S8 读数下降重建基线 - 不涨距`() {
        val e = engine()
        e.onCounterEvent(500L, 0L)
        assertEquals(0.7f, e.onCounterEvent(501L, 700L).meters, 1e-3f)
        // 设备重启 counter 重置：下降事件本身即重建基线（0 增量）
        assertEquals(0f, e.onCounterEvent(3L, 8_000L).meters, 1e-6f)
        // 基线之后的步数正常计距（下降不吞掉真实增量）
        assertEquals(0.7f, e.onCounterEvent(4L, 9_000L).meters, 1e-3f)
        assertEquals(0.7f, e.onCounterEvent(5L, 9_700L).meters, 1e-3f)
    }

    @Test
    fun `S8 时间回退的乱序事件忽略`() {
        val e = engine()
        e.onCounterEvent(0L, 10_000L)
        assertEquals(0f, e.onCounterEvent(5L, 9_000L).meters, 1e-6f) // 乱序：忽略
        assertEquals(3.5f, e.onCounterEvent(5L, 15_000L).meters, 1e-3f) // 正常恢复
    }

    @Test
    fun `S5 F001 同刻事件零计距 - 1_4 乘 0 秒等于 0`() {
        val e = engine()
        e.onCounterEvent(0L, 1_000L)
        assertEquals("基线(0,1000) 后同刻 (100,1000) 必须 0 米", 0f, e.onCounterEvent(100L, 1_000L).meters, 1e-6f)
        assertEquals("再同刻 (200,1000) 仍 0 米——同刻序列刷不出进度", 0f, e.onCounterEvent(200L, 1_000L).meters, 1e-6f)
    }

    @Test
    fun `F001 连续 100 批同刻读数零进度 - 合并步数由下一正间隔事件封顶带回`() {
        val e = engine()
        e.onCounterEvent(0L, 5_000L)
        var count = 0L
        repeat(100) { i ->
            count += 10
            assertEquals("第 ${i + 1} 批同刻必须 0 米", 0f, e.onCounterEvent(count, 5_000L).meters, 1e-6f)
        }
        // 时间推进后的第一个事件：合并的 1000 步一次性计距，受 1.4×2s 封顶
        count += 10
        val d = e.onCounterEvent(count, 7_000L)
        assertEquals("1010 步 ×0.7=707m 封顶到 1.4×2s=2.8m", 2.8f, d.meters, 1e-3f)
    }

    @Test
    fun `F001 同刻合并不丢真实批量 - 合并步数由下一正间隔事件带回`() {
        val e = engine()
        e.onCounterEvent(0L, 0L)
        // (1,1000) 正常事件 0.7m；(2,1000) 与上一接受同刻 → 合并 0m；
        // (4,2000) 相对计数基线 2 步、时间基线 1000ms：raw 1.4 = cap 1.4
        assertEquals(0.7f, e.onCounterEvent(1L, 1_000L).meters, 1e-3f)
        assertEquals(0f, e.onCounterEvent(2L, 1_000L).meters, 1e-6f)
        assertEquals(1.4f, e.onCounterEvent(4L, 2_000L).meters, 1e-3f)
    }

    @Test
    fun `F001 下降与乱序组合 - 各自重建或忽略且不重复累计`() {
        val e = engine()
        e.onCounterEvent(1_000L, 10_000L)
        assertEquals(0.7f, e.onCounterEvent(1_001L, 10_700L).meters, 1e-3f)
        // 乱序（时间回退、读数更高）：忽略，不累计
        assertEquals(0f, e.onCounterEvent(1_005L, 9_500L).meters, 1e-6f)
        // 读数下降：重建基线
        assertEquals(0f, e.onCounterEvent(2L, 11_000L).meters, 1e-6f)
        // 被乱序忽略的步数不重复累计：下降基线后从 2 起算
        assertEquals(0.7f, e.onCounterEvent(3L, 11_700L).meters, 1e-3f)
        // 再乱序 + 再下降交替
        assertEquals(0f, e.onCounterEvent(50L, 11_500L).meters, 1e-6f)
        assertEquals(0f, e.onCounterEvent(1L, 12_000L).meters, 1e-6f)
        assertEquals(0.7f, e.onCounterEvent(2L, 12_700L).meters, 1e-3f)
    }

    @Test
    fun `F001 正常重启 - 重注册基线与读数下降基线都不吞后续增量`() {
        val e = engine()
        e.onCounterEvent(0L, 0L)
        assertEquals(0.7f, e.onCounterEvent(1L, 700L).meters, 1e-3f)
        // 传感器重注册（服务重启接管）：下一事件只建基线
        e.restartBaseline()
        assertEquals(0f, e.onCounterEvent(10L, 2_000L).meters, 1e-6f)
        assertEquals(0.7f, e.onCounterEvent(11L, 2_700L).meters, 1e-3f)
        // 设备重启 counter 重置：读数下降重建基线，后续正常
        assertEquals(0f, e.onCounterEvent(3L, 8_000L).meters, 1e-6f)
        assertEquals(0.7f, e.onCounterEvent(4L, 8_700L).meters, 1e-3f)
    }

    @Test
    fun `F001 步长非有限值被拒绝 - 不污染 meters`() {
        val e = engine(0.70f)
        e.strideMeters = Float.NaN
        assertEquals("NaN 步长保持原值", 0.70f, e.strideMeters, 1e-4f)
        e.strideMeters = Float.POSITIVE_INFINITY
        assertEquals("Infinity 步长保持原值", 0.70f, e.strideMeters, 1e-4f)
        // 构造参数非有限：回退默认，而不是把 NaN 写进字段
        val bad = engine(Float.NaN)
        assertEquals(RealWalkEngine.DEFAULT_STRIDE_METERS, bad.strideMeters, 1e-4f)
        // 正常计距不受影响
        bad.onCounterEvent(0L, 0L)
        assertEquals(0.70f, bad.onCounterEvent(1L, 700L).meters, 1e-3f)
    }

    @Test
    fun `S8 暂停期间不补算 - 恢复后首事件只建基线`() {
        val e = engine()
        e.onCounterEvent(0L, 0L)
        e.onCounterEvent(10L, 7_000L)
        e.pause()
        // 暂停期间真实走了 50 步（通知栏/后台暂停）——不得补算
        assertEquals(0f, e.onCounterEvent(60L, 20_000L).meters, 1e-6f)
        e.resume()
        assertEquals("恢复后首事件仍只建基线", 0f, e.onCounterEvent(61L, 21_000L).meters, 1e-6f)
        assertEquals(0.7f, e.onCounterEvent(62L, 21_700L).meters, 1e-3f)
    }

    @Test
    fun `S8 暂停时未收到事件 - 恢复后同样不补算缺口`() {
        val e = engine()
        e.onCounterEvent(0L, 0L)
        e.onCounterEvent(10L, 7_000L)
        e.pause()
        e.resume() // 暂停期间传感器未上报
        assertEquals("恢复后第一事件不得把暂停期步数补回", 0f, e.onCounterEvent(60L, 20_000L).meters, 1e-6f)
    }

    @Test
    fun `传感器重注册 - 下一事件只建基线`() {
        val e = engine()
        e.onCounterEvent(0L, 0L)
        assertEquals(0.7f, e.onCounterEvent(1L, 700L).meters, 1e-3f)
        e.restartBaseline()
        assertEquals(0f, e.onCounterEvent(10L, 2_000L).meters, 1e-6f)
        assertEquals(0.7f, e.onCounterEvent(11L, 2_700L).meters, 1e-3f)
    }

    @Test
    fun `步长设置钳制到 0_45 - 0_95`() {
        val e = engine(0.2f)
        assertEquals(0.45f, e.strideMeters, 1e-4f)
        e.strideMeters = 1.5f
        assertEquals(0.95f, e.strideMeters, 1e-4f)
        e.strideMeters = 0.8f
        assertEquals(0.8f, e.strideMeters, 1e-4f)
    }

    @Test
    fun `终态后一切事件零增量`() {
        val e = engine()
        e.onCounterEvent(0L, 0L)
        e.markTerminal()
        assertEquals(0f, e.onCounterEvent(1_000L, 60_000L).meters, 1e-6f)
        assertTrue(e.isTerminal)
    }

    @Test
    fun `detector 事件只是 cue - 不参与计距且受状态约束`() {
        val e = engine()
        assertTrue(e.onDetectorStep())
        e.pause()
        assertFalse("暂停期不出 cue", e.onDetectorStep())
        e.resume()
        assertTrue(e.onDetectorStep())
        e.markTerminal()
        assertFalse(e.onDetectorStep())
    }
}
