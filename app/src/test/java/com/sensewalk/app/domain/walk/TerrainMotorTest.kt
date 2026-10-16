package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.scene.PathSegment
import com.sensewalk.app.domain.scene.TerrainKind
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 越坎马达单测（T07B / SW-005，DEVELOPMENT §5.6/5.7）。
 * 纯 Kotlin 状态机：接近分流/站稳不刷距/轻跳/松手取消/暂停冻结/迟到吸收。
 */
class TerrainMotorTest {

    private val gap = PathSegment(from = 100, to = 130, kind = TerrainKind.GAP_HOP)

    private fun motor() = TerrainMotor()

    /** 无坎自由态 */
    private fun free(m: TerrainMotor, dt: Long = 50, defl: Float = 0.5f) =
        m.step(dt, 50f, defl, null, paused = false)

    /** 接近区内推进（默认 sPos=97 在 [from-3, from)） */
    private fun approach(m: TerrainMotor, sPos: Float = 97f, defl: Float = 0.5f, dt: Long = 50) =
        m.step(dt, sPos, defl, gap, paused = false)

    @Test
    fun `舒适区接近 - 直接轻跳`() {
        val m = motor()
        // sPos=98 在接近区（100-3=97），d=0.5 ≤ 0.72
        val d = m.step(50, 98f, 0.5f, gap, paused = false)
        assertTrue("舒适区接近应轻跳，实际 $d", d is TerrainMotor.SpeedDirective.hop)
        assertEquals(TerrainMotor.Phase.HOP, m.currentPhase)
    }

    @Test
    fun `紧张区接近 - 先减速进入站稳`() {
        val m = motor()
        // d=0.9 > 0.72：接近帧先 clamp
        val d1 = approach(m, sPos = 98f, defl = 0.9f)
        assertTrue("紧张接近应先钳速，实际 $d1", d1 is TerrainMotor.SpeedDirective.clamp)
        assertEquals(0.4f, (d1 as TerrainMotor.SpeedDirective.clamp).maxSpeed, 1e-6f)
        // 减速过渡帧（APPROACH→STABILIZE 转换）仍为 clamp；其后进入站稳 holdZero
        val d2 = approach(m, sPos = 98f, defl = 0.9f)
        assertTrue(d2 is TerrainMotor.SpeedDirective.clamp)
        val d3 = approach(m, sPos = 98f, defl = 0.9f)
        assertTrue("站稳期间应 holdZero，实际 $d3", d3 is TerrainMotor.SpeedDirective.holdZero)
        assertEquals(TerrainMotor.Phase.STABILIZE, m.currentPhase)
    }

    @Test
    fun `站稳 1_2 秒后自动轻跳 - 无需操作`() {
        val m = motor()
        approach(m, sPos = 98f, defl = 0.9f) // APPROACH
        // 累计 1200ms 的 holdZero
        var elapsed = 0L
        var last: TerrainMotor.SpeedDirective = TerrainMotor.SpeedDirective.holdZero()
        while (elapsed <= TerrainMotor.STABILIZE_DURATION_MS + 200) {
            last = approach(m, sPos = 98f, defl = 0.9f, dt = 100)
            elapsed += 100
            if (last is TerrainMotor.SpeedDirective.hop) break
        }
        assertTrue("站满 1.2s 应自动跳，实际 $last", last is TerrainMotor.SpeedDirective.hop)
    }

    @Test
    fun `站稳期间不刷距 - holdZero 持续整段`() {
        val m = motor()
        approach(m, sPos = 98f, defl = 0.9f)  // FREE→APPROACH
        approach(m, sPos = 98f, defl = 0.9f)  // APPROACH→STABILIZE（减速过渡帧）
        repeat(11) { // 11×100ms=1.1s 站稳中
            val d = approach(m, sPos = 98f, defl = 0.9f, dt = 100)
            assertTrue("站稳中每帧都应 holdZero，实际 $d", d is TerrainMotor.SpeedDirective.holdZero)
        }
        // 第 12 帧（累计 1.2s）自动轻跳
        val dHop = approach(m, sPos = 98f, defl = 0.9f, dt = 100)
        assertTrue("站满 1.2s 应自动跳", dHop is TerrainMotor.SpeedDirective.hop)
    }

    @Test
    fun `首局站稳提示只发一次`() {
        val m = motor()
        assertFalse(m.consumeHint())
        approach(m, sPos = 98f, defl = 0.9f) // 进 APPROACH
        approach(m, sPos = 98f, defl = 0.9f) // 进 STABILIZE → hint 置位
        assertTrue("第一次站稳应发提示", m.consumeHint())
        assertFalse("提示只发一次", m.consumeHint())
    }

    @Test
    fun `站稳中松手 - 回自由态不保留计时`() {
        val m = motor()
        approach(m, sPos = 98f, defl = 0.9f)
        approach(m, sPos = 98f, defl = 0.9f) // STABILIZE, 100ms
        approach(m, sPos = 98f, defl = 0.9f, dt = 100) // 200ms
        // 松手
        val d = approach(m, sPos = 98f, defl = 0f)
        assertEquals(TerrainMotor.Phase.FREE, m.currentPhase)
        // 重新紧张接近：从 0 重新计时（不是从 300ms 继续）
        approach(m, sPos = 98f, defl = 0.9f) // APPROACH
        approach(m, sPos = 98f, defl = 0.9f) // STABILIZE 重新开始
        var elapsed = 0L
        var hopSeen = false
        while (elapsed < TerrainMotor.STABILIZE_DURATION_MS + 200) {
            val dd = approach(m, sPos = 98f, defl = 0.9f, dt = 100)
            elapsed += 100
            if (dd is TerrainMotor.SpeedDirective.hop) { hopSeen = true; break }
            // 前 1100ms 内不应跳（证明计时重置）
            if (elapsed <= 1100) assertTrue("重置后须重新站满 1.2s", dd is TerrainMotor.SpeedDirective.holdZero)
        }
        assertTrue("重新站稳后仍能跳", hopSeen)
    }

    @Test
    fun `接近途中放慢到舒适区 - 立即轻跳不等站稳`() {
        val m = motor()
        approach(m, sPos = 98f, defl = 0.9f) // APPROACH（紧张）
        // 还没进 STABILIZE 就放慢
        val d = approach(m, sPos = 98f, defl = 0.5f)
        assertTrue("途中放慢应立即跳，实际 $d", d is TerrainMotor.SpeedDirective.hop)
    }

    @Test
    fun `跳跃中越过坎尾 - 回自由态`() {
        val m = motor()
        m.step(50, 98f, 0.5f, gap, paused = false) // HOP
        assertEquals(TerrainMotor.Phase.HOP, m.currentPhase)
        // 推进到坎尾之后
        val d = m.step(50, 131f, 0.5f, null, paused = false)
        assertEquals(TerrainMotor.Phase.FREE, m.currentPhase)
        assertTrue(d is TerrainMotor.SpeedDirective.normal)
    }

    @Test
    fun `恢复落入坎段内 - 直接跳过不卡死`() {
        val m = motor()
        // sPos=105 已在坎内（快照恢复场景）
        val d = m.step(50, 105f, 0.5f, gap, paused = false)
        assertTrue("恢复点在坎内应直接跳，实际 $d", d is TerrainMotor.SpeedDirective.hop)
    }

    @Test
    fun `暂停帧冻结 - holdZero 不推进站稳计时`() {
        val m = motor()
        approach(m, sPos = 98f, defl = 0.9f)
        approach(m, sPos = 98f, defl = 0.9f) // STABILIZE
        // 暂停 5 秒的帧（外层暂停时 advance 不跑，防御性验证 step(paused=true)）
        val d = m.step(5_000, 98f, 0.9f, gap, paused = true)
        assertTrue("暂停应 holdZero，实际 $d", d is TerrainMotor.SpeedDirective.holdZero)
        // 恢复后仍需站满剩余时长（计时未被 5s 暂停推进）
        var elapsed = 0L
        var hopAt: Long? = null
        while (elapsed < TerrainMotor.STABILIZE_DURATION_MS + 200) {
            val dd = approach(m, sPos = 98f, defl = 0.9f, dt = 100)
            elapsed += 100
            if (dd is TerrainMotor.SpeedDirective.hop) { hopAt = elapsed; break }
        }
        assertTrue("恢复后站满剩余时长才跳", hopAt != null && hopAt <= TerrainMotor.STABILIZE_DURATION_MS)
    }

    @Test
    fun `终态吸收 - abandon 后一切 normal`() {
        val m = motor()
        m.markTerminal()
        val d = m.step(50, 98f, 0.9f, gap, paused = false)
        assertTrue(d is TerrainMotor.SpeedDirective.normal)
    }

    @Test
    fun `无坎时始终 normal`() {
        val m = motor()
        repeat(20) { dt ->
            val d = free(m, dt = 50, defl = 0.9f)
            assertTrue(d is TerrainMotor.SpeedDirective.normal)
        }
    }

    @Test
    fun `步态映射 - 站稳tense 跳hop 上坡climb`() {
        val m = motor()
        assertEquals(TerrainMotor.Gait.IDLE, m.gait(walking = false, terrain = TerrainKind.FLAT))
        assertEquals(TerrainMotor.Gait.WALK, m.gait(walking = true, terrain = TerrainKind.FLAT))
        assertEquals(TerrainMotor.Gait.CLIMB, m.gait(walking = true, terrain = TerrainKind.SLOPE_UP))
        // 站稳中 → tense
        approach(m, sPos = 98f, defl = 0.9f)
        approach(m, sPos = 98f, defl = 0.9f)
        assertEquals(TerrainMotor.Gait.TENSE, m.gait(walking = true, terrain = TerrainKind.GAP_HOP))
    }

    // ---- SW-005 R2：死区边界（comfort_v1 死区 0–0.08，规划要求 d=.01/.08 实测）----

    @Test
    fun `R2 死区输入 d0_01 接近坎 - 不触发跳跃（速度为0等同无输入）`() {
        val m = motor()
        val d = m.step(50, 98f, 0.01f, gap, paused = false)
        assertTrue("死区输入不得触发自动跳跃，实际 $d", d is TerrainMotor.SpeedDirective.normal)
        assertEquals(TerrainMotor.Phase.FREE, m.currentPhase)
    }

    @Test
    fun `R2 死区内 d0_079 - 同样不触发`() {
        val m = motor()
        val d = m.step(50, 98f, 0.079f, gap, paused = false)
        assertTrue(d is TerrainMotor.SpeedDirective.normal)
    }

    @Test
    fun `R2 死区上沿 d0_08 - 正常进入越坎流程`() {
        val m = motor()
        // d=0.08 处曲线速度仍为 0，但已达有效输入阈值：≤0.72 → 舒适轻跳
        val d = m.step(50, 98f, 0.08f, gap, paused = false)
        assertTrue("死区上沿是有效输入，应轻跳，实际 $d", d is TerrainMotor.SpeedDirective.hop)
    }

    @Test
    fun `R2 站稳中输入降到死区 - 等同松手回 FREE`() {
        val m = motor()
        approach(m, sPos = 98f, defl = 0.9f)
        approach(m, sPos = 98f, defl = 0.9f) // STABILIZE
        val d = approach(m, sPos = 98f, defl = 0.05f) // 死区
        assertEquals(TerrainMotor.Phase.FREE, m.currentPhase)
        assertTrue(d is TerrainMotor.SpeedDirective.normal)
    }

    @Test
    fun `R2 HOP 中输入降到死区 - 中止自动推进`() {
        val m = motor()
        m.step(50, 98f, 0.5f, gap, paused = false) // HOP
        val d = m.step(50, 99f, 0.01f, gap, paused = false)
        assertEquals(TerrainMotor.Phase.FREE, m.currentPhase)
        assertTrue("死区输入必须中止跳跃推进", d is TerrainMotor.SpeedDirective.normal)
    }
}
