package com.sensewalk.app.domain.walk

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import com.sensewalk.app.domain.scene.SceneJsonParser
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionState

/**
 * T04 验收：真实森林配置（assets/scenes/forest.json，标准 800 m）
 * 在模拟时间下完整通关——不缩短距离、不快进门禁。
 */
class ForestFullWalkTest {

    private class FakeClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    private fun assetsDir(): File =
        listOf(File("src/main/assets"), File("app/src/main/assets"))
            .firstOrNull { it.isDirectory }
            ?: error("找不到 src/main/assets")

    private fun forestConfig(): SceneConfig =
        SceneJsonParser.parse(File(assetsDir(), "scenes/forest.json").readText())

    @Test
    fun `真实森林 800m 甜点速度完整通关`() {
        val config = forestConfig()
        assertEquals("标准距离不得改动", 800, config.requiredDistanceMeters)

        val clock = FakeClock()
        val controller = VirtualWalkController(config, clock)

        // 初始：黑幕与静音
        assertEquals(SessionState.READY, controller.snapshot().session)
        assertEquals(1f, controller.snapshot().sensory.visualOpacities["void"]!!, 1e-6f)
        assertTrue(controller.snapshot().sensory.audioTargets.isEmpty())

        // 甜点偏转持续行走；帧间隔 50ms（约 60fps 的保守上限）
        controller.onStick(0.55f)
        var frames = 0
        while (controller.snapshot().session != SessionState.COMPLETED && frames < 60_000) {
            clock.now += 50
            controller.frame()
            frames++
        }

        assertEquals("应在模拟 40 分钟内通关，实际 ${frames * 50}ms", SessionState.COMPLETED, controller.snapshot().session)
        assertEquals("meters 精确钳制到 800", 800f, controller.snapshot().meters, 1e-3f)
        assertTrue(controller.gate.isCompleted)

        // 全部相位按配置顺序各触发一次（含同距离多通道与 95% 抵达相位）
        val expectedOrder = config.phases.map { it.id }
        assertEquals(expectedOrder.toSet(), controller.scheduler.firedPhaseIds)
        assertEquals(expectedOrder.size, controller.scheduler.firedPhaseIds.size)

        // 通关时长落在合理区间：约 700–850 s（甜点 ~1.1 m/s，忽略起步）
        val elapsedMs = controller.snapshot().elapsedActiveMs
        assertTrue("通关用时异常: ${elapsedMs}ms", elapsedMs in 600_000..900_000)

        // 终景：抵达相位（clearing, 760m, fade 25m）在 800m 已满值
        val sensory = controller.snapshot().sensory
        assertEquals(0.9f, sensory.visualOpacities["clearing"]!!, 1e-4f)
        assertEquals(1f, sensory.visualOpacities["void"]!!, 1e-6f)
        // 75% 深层音频已解锁
        assertTrue(sensory.audioTargets.containsKey("deep_birds"))
        // 50% 振动规则已激活
        assertTrue(sensory.hapticRules.any { it.pattern == "footstep_soft" })
    }

    @Test
    fun `真实森林 800m 中途放弃 - 未满距不通关`() {
        val config = forestConfig()
        val clock = FakeClock()
        val controller = VirtualWalkController(config, clock)
        controller.onStick(0.55f)
        repeat(2_000) { clock.now += 50; controller.frame() } // 100s ≈ 110m（已越过 80m 脚步/轮廓树）

        val walked = controller.snapshot().meters
        assertTrue("应走了约百米，实际 $walked", walked in 80f..160f)
        assertTrue(walked < 800f)

        controller.abandon()
        assertEquals(SessionState.ABANDONED, controller.snapshot().session)
        assertTrue(!controller.gate.isCompleted)
        // 已触发的相位保留（脚步/轮廓树在 80m 已解锁），后续相位不再触发
        val fired = controller.scheduler.firedPhaseIds
        assertTrue(fired.containsAll(listOf("void", "steps", "tree_outline")))
        assertTrue("240m 相位不应触发", !fired.contains("ambience"))
        assertTrue(!fired.contains("clearing"))
    }

    @Test
    fun `真实森林 - 拉满慢于甜点（控制器级验证）`() {
        fun distanceIn(seconds: Int, deflection: Float): Float {
            val clock = FakeClock()
            val controller = VirtualWalkController(forestConfig(), clock)
            controller.onStick(deflection)
            repeat(seconds * 20) { clock.now += 50; controller.frame() }
            return controller.snapshot().meters
        }
        val sweet = distanceIn(120, 0.55f)
        val full = distanceIn(120, 1.00f)
        assertTrue("甜点 2 分钟应走 $sweet m > 拉满 $full m", sweet > full * 1.2f)
    }

    @Test
    fun `森林地形系数 - gap_hop 开发降级为平地且坡段生效`() {
        val clock = FakeClock()
        val controller = VirtualWalkController(forestConfig(), clock)
        // 0-140 平地；140-240 上坡 0.07；240-270 gap_hop（T07 前降级平地）；270-400 不平
        assertEquals(1.0f, controller.terrainFactorAt(70f), 1e-4f)
        assertEquals(0.895f, controller.terrainFactorAt(190f), 1e-4f)
        assertEquals("gap_hop 降级为平地系数", 1.0f, controller.terrainFactorAt(255f), 1e-4f)
        assertEquals(0.95f, controller.terrainFactorAt(300f), 1e-4f)
    }
}
