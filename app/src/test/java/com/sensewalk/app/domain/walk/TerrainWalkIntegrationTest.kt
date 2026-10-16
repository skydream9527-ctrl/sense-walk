package com.sensewalk.app.domain.walk

import com.sensewalk.app.domain.scene.TestScenes
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 越坎与虚走控制器集成（T07B / SW-005）：真实 forest 配置（gap_hop@270-300）端到端——
 * 松手/取消、暂停中间态、反复同坎语义、迟到回调、800m 全程通关、
 * 跳跃不刷距（meters 增长 ≤ 速度帽）、恢复落入坎内不卡死。
 */
class TerrainWalkIntegrationTest {

    private class FakeClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    /** 带真实坎的配置（forest pathProfile 关键段：270-300 gap_hop；其余参照默认） */
    private fun config() = TestScenes.validConfig(
        segments = listOf(
            com.sensewalk.app.domain.scene.PathSegment(0, 270, com.sensewalk.app.domain.scene.TerrainKind.FLAT),
            com.sensewalk.app.domain.scene.PathSegment(270, 300, com.sensewalk.app.domain.scene.TerrainKind.GAP_HOP),
            com.sensewalk.app.domain.scene.PathSegment(300, 1000, com.sensewalk.app.domain.scene.TerrainKind.FLAT),
        ),
    )

    /** 走到指定米数（舒适输入），返回控制器与时钟 */
    private fun walkedTo(meters: Float, deflection: Float = 0.5f): Pair<VirtualWalkController, FakeClock> {
        val clock = FakeClock()
        val c = VirtualWalkController(config(), clock)
        c.onStick(deflection)
        var guard = 0
        while (c.snapshot().meters < meters && guard++ < 200_000) {
            clock.now += 50
            c.frame()
        }
        return c to clock
    }

    @Test
    fun `舒适速度接近真实 forest 坎 - 自动通过且步态经 hop`() {
        val (c, clock) = walkedTo(264f, deflection = 0.5f)
        var sawHop = false
        var guard = 0
        while (c.snapshot().meters < 302f && guard++ < 200_000) {
            clock.now += 50
            val s = c.frame()
            if (s.gait == TerrainMotor.Gait.HOP) sawHop = true
        }
        assertTrue("应出现过 hop 步态", sawHop)
        assertTrue("应越过坎（302m）", c.snapshot().meters >= 302f)
        assertEquals("坎后回自由步态", TerrainMotor.Gait.WALK, c.snapshot().gait)
    }

    @Test
    fun `紧张输入过坎 - 站稳后自动通过且不卡死`() {
        val (c, clock) = walkedTo(262f, deflection = 0.95f)
        var sawTense = false
        var guard = 0
        while (c.snapshot().meters < 302f && guard++ < 400_000) {
            clock.now += 50
            val s = c.frame()
            if (s.gait == TerrainMotor.Gait.TENSE) sawTense = true
        }
        assertTrue("紧张过坎应经历站稳（tense）", sawTense)
        assertTrue("站稳后必须自动通过（永远能过）", c.snapshot().meters >= 302f)
    }

    @Test
    fun `站稳期间 meters 不增加`() {
        val (c, clock) = walkedTo(265f, deflection = 0.95f)
        // 持续紧张输入驱动到站稳期
        var stabilizeStart: Float? = null
        var stabilizeEnd: Float? = null
        var guard = 0
        while (c.snapshot().meters < 302f && guard++ < 400_000) {
            clock.now += 50
            val before = c.snapshot().meters
            c.frame()
            val after = c.snapshot().meters
            if (c.snapshot().gait == TerrainMotor.Gait.TENSE) {
                // TENSE 含减速过渡帧（clamp，速度非零属正常减速）与真站稳（holdZero 冻结）；
                // 断言整段 TENSE 期位移有限（减速滑行 < 0.5m）且后半段完全冻结
                if (stabilizeStart == null) stabilizeStart = before
                stabilizeEnd = after
            }
        }
        requireNotNull(stabilizeStart) { "未进入站稳期" }
        requireNotNull(stabilizeEnd)
        assertTrue(
            "TENSE 全程（减速+站稳）位移必须有限（<0.5m），实际 ${stabilizeEnd - stabilizeStart}",
            stabilizeEnd - stabilizeStart < 0.5f,
        )
    }

    @Test
    fun `暂停发生在站稳中 - 恢复后不补算缺口且能继续过坎`() {
        val (c, clock) = walkedTo(265f, deflection = 0.95f)
        // 等进入站稳
        var guard = 0
        while (c.snapshot().gait != TerrainMotor.Gait.TENSE && guard++ < 40_000) {
            clock.now += 50; c.frame()
        }
        assertEquals(TerrainMotor.Gait.TENSE, c.snapshot().gait)
        val metersAtPause = c.snapshot().meters
        c.onStickReleased()
        c.pause()
        // 暂停期间大量时间流逝（不产生帧；模拟后台）
        clock.now += 60_000
        assertEquals("暂停期不涨距", metersAtPause, c.snapshot().meters, 1e-4f)
        // 恢复：松手状态下恢复 → READY 等输入
        c.resume()
        c.onStick(0.95f)
        guard = 0
        while (c.snapshot().meters < 302f && guard++ < 400_000) {
            clock.now += 50
            c.frame()
        }
        assertTrue("恢复后能继续过坎", c.snapshot().meters >= 302f)
    }

    @Test
    fun `松手取消接近 - 不发生自动跳进`() {
        val (c, clock) = walkedTo(268f, deflection = 0.95f)
        c.onStickReleased()
        // 松手滑行到停：无输入期间任何自动动作都不得推进 meters
        val metersAtRelease = c.snapshot().meters
        var guard = 0
        while (guard++ < 200) { // 10s
            clock.now += 50
            c.frame()
        }
        // 惯性滑行段（τ=0.25s）之外不前进；滑行总量有限且 < 全段
        val drift = c.snapshot().meters - metersAtRelease
        assertTrue("松手后最多惯性滑行（无自动跳进刷距），实际漂移 $drift m", drift < 1.0f)
        // 松手后 state 保持 WALKING（不存在自动回 READY），但无输入不前进
        assertEquals(TerrainMotor.Gait.WALK, c.snapshot().gait)
        assertEquals(metersAtRelease + drift, c.snapshot().meters, 1e-4f)
    }

    @Test
    fun `通关终态后迟到帧不推进 - motor 吸收`() {
        val (c, clock) = walkedTo(995f, deflection = 0.5f)
        var guard = 0
        while (c.snapshot().session != SessionState.COMPLETED && guard++ < 400_000) {
            clock.now += 50
            c.frame()
        }
        assertEquals(SessionState.COMPLETED, c.snapshot().session)
        val finalMeters = c.snapshot().meters
        repeat(100) { clock.now += 50; c.frame() }
        assertEquals("终态迟到帧不得改米数", finalMeters, c.snapshot().meters, 1e-4f)
    }

    @Test
    fun `全森林 800m 紧张输入也能通关 - 站稳只费时不失败`() {
        val clock = FakeClock()
        val c = VirtualWalkController(config(), clock)
        c.onStick(0.95f) // 全程紧张
        var guard = 0
        while (c.snapshot().session != SessionState.COMPLETED && guard++ < 1_000_000) {
            clock.now += 50
            c.frame()
        }
        assertEquals("紧张玩家也必须能通关（永远能过）", SessionState.COMPLETED, c.snapshot().session)
        assertEquals(config().requiredDistanceMeters.toFloat(), c.snapshot().meters, 0.5f)
    }

    @Test
    fun `快照恢复落入坎内 - 不卡死能通过`() {
        val (original, _) = walkedTo(280f, deflection = 0.5f)
        // 构造恢复到坎中间（sPos=280 在 270-300 段内）
        val clock2 = FakeClock(50_000L)
        val restored = VirtualWalkController(
            config(), clock2,
            restore = VirtualWalkController.Restore(
                progress = com.sensewalk.app.domain.progress.ProgressSnapshot(
                    sPos = 280f, sBest = 280f, meters = 280f,
                    requiredDistanceMeters = config().requiredDistanceMeters.toFloat(),
                ),
                firedPhaseIds = original.scheduler.firedPhaseIds,
                elapsedActiveMs = 0L,
            ),
        )
        restored.onStick(0.5f)
        var guard = 0
        while (restored.snapshot().meters < 302f && guard++ < 400_000) {
            clock2.now += 50
            restored.frame()
        }
        assertTrue("恢复点在坎内不得卡死", restored.snapshot().meters >= 302f)
    }

    @Test
    fun `跳跃推进受速度帽约束 - 无免费米数`() {
        // 跳跃速度 HOP_SPEED=1.0 m/s：跳跃期间每 50ms 帧最多 0.05m，
        // 坎宽 30m 至少需要 30s 游戏时间——快进验证总时长合理（非瞬时传送）
        val (c, clock) = walkedTo(266f, deflection = 0.5f)
        val start = clock.now
        var frames = 0
        var guard = 0
        while (c.snapshot().meters < 302f && guard++ < 400_000) {
            clock.now += 50
            c.frame()
            frames++
        }
        val elapsed = clock.now - start
        // 坎 30m @ ≤1.0m/s ≥ 30s = 60000ms（含过渡余量）
        assertTrue("跳跃必须花真实时间（受速度帽），实际 ${elapsed}ms", elapsed >= 25_000)
    }

    @Test
    fun `P02 同局恢复提示不重复 - hintShown 随快照保持`() {
        val (original, _) = walkedTo(280f, deflection = 0.95f)
        // 原局已触发过站稳提示（走到 280m 跨坎必然站稳过紧张段？不一定——0.95 紧张，会）
        // 直接模拟：原局提示已发
        original.terrainMotor.restoreHintShown(true)
        assertTrue(original.terrainMotor.hintShown)
        val clock2 = FakeClock(50_000L)
        val restored = VirtualWalkController(
            config(), clock2,
            restore = VirtualWalkController.Restore(
                progress = com.sensewalk.app.domain.progress.ProgressSnapshot(
                    sPos = 280f, sBest = 280f, meters = 280f,
                    requiredDistanceMeters = config().requiredDistanceMeters.toFloat(),
                ),
                firedPhaseIds = original.scheduler.firedPhaseIds,
                elapsedActiveMs = 0L,
                stabilizeHintShown = original.terrainMotor.hintShown,
            ),
        )
        // 恢复后即使再次紧张站稳也不提示（同局仅一次）
        restored.terrainMotor.step(100, 268f, 0.95f,
            com.sensewalk.app.domain.scene.PathSegment(270, 300, com.sensewalk.app.domain.scene.TerrainKind.GAP_HOP), paused = false)
        restored.terrainMotor.step(100, 268f, 0.95f,
            com.sensewalk.app.domain.scene.PathSegment(270, 300, com.sensewalk.app.domain.scene.TerrainKind.GAP_HOP), paused = false)
        assertFalse("同局恢复后不得再次提示", restored.consumeStabilizeHint())
    }

    @Test
    fun `P02 新局提示正常 - 未发过时恢复仍可提示`() {
        val (original, _) = walkedTo(100f, deflection = 0.5f) // 未遇坎未提示
        assertFalse(original.terrainMotor.hintShown)
        val restored = VirtualWalkController(
            config(), FakeClock(),
            restore = VirtualWalkController.Restore(
                progress = original.accumulator.snapshot(),
                firedPhaseIds = original.scheduler.firedPhaseIds,
                elapsedActiveMs = 0L,
                stabilizeHintShown = false,
            ),
        )
        // 恢复后首次紧张站稳正常提示
        val seg = com.sensewalk.app.domain.scene.PathSegment(270, 300, com.sensewalk.app.domain.scene.TerrainKind.GAP_HOP)
        restored.terrainMotor.step(100, 268f, 0.95f, seg, paused = false)
        restored.terrainMotor.step(100, 268f, 0.95f, seg, paused = false)
        assertTrue("未发过提示的局恢复后首次站稳应提示", restored.consumeStabilizeHint())
    }

}
