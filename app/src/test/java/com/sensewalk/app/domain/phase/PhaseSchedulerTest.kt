package com.sensewalk.app.domain.phase

import com.sensewalk.app.domain.scene.TestScenes
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** 相位调度（S4 / S9）：唯一触发、同距离多通道、跨阈值批量、米数驱动 opacity */
class PhaseSchedulerTest {

    private val config = TestScenes.validConfig()
    private val phaseIds = config.phases.map { it.id }

    @Test
    fun `初始化 update 0 触发黑幕相位`() {
        val scheduler = PhaseScheduler(config)
        val events = scheduler.update(0f)
        assertEquals(listOf("void"), events.map { it.phase.id })
        assertTrue(scheduler.firedPhaseIds.contains("void"))
    }

    @Test
    fun `同距离多通道相位在同一次 update 全部触发`() {
        val scheduler = PhaseScheduler(config)
        scheduler.update(0f)
        // steps(audio) 与 outline(visual) 都在 atMeters=100
        val events = scheduler.update(100f)
        assertEquals(listOf("steps", "outline"), events.map { it.phase.id })
        assertEquals(0.25f, (events[0].phase.toVolume)!!, 1e-6f)
    }

    @Test
    fun `S9 单次进度跨多个阈值不漏相位`() {
        val scheduler = PhaseScheduler(config)
        scheduler.update(0f)
        val events = scheduler.update(500f)
        // 0~500 之间全部相位按配置顺序：steps outline ambience main_body haptic detail
        assertEquals(
            listOf("steps", "outline", "ambience", "main_body", "haptic", "detail"),
            events.map { it.phase.id },
        )
    }

    @Test
    fun `每个相位只触发一次`() {
        val scheduler = PhaseScheduler(config)
        scheduler.update(0f)
        scheduler.update(100f)
        assertTrue(scheduler.update(100f).isEmpty())
        assertTrue(scheduler.update(120f).isEmpty())
        assertEquals(listOf("ambience", "main_body"), scheduler.update(300f).map { it.phase.id })
        // 一次跳到终点：剩余全部按序触发，各一次
        assertEquals(
            listOf("haptic", "detail", "deep", "far_view", "arrival"),
            scheduler.update(2000f).map { it.phase.id },
        )
    }

    @Test
    fun `米数回落的 update 不触发也不回退`() {
        val scheduler = PhaseScheduler(config)
        scheduler.update(300f)
        val after = scheduler.update(50f)
        assertTrue(after.isEmpty())
        assertEquals(setOf("void", "steps", "outline", "ambience", "main_body"), scheduler.firedPhaseIds)
    }

    @Test
    fun `S4 opacity 是米数纯函数 - meters 不变输出不变`() {
        val scheduler = PhaseScheduler(config)
        scheduler.update(300f) // outline(100, fade 20, to 0.6) 已触发
        val first = scheduler.sensoryState(110f)
        val second = scheduler.sensoryState(110f)
        assertEquals(first.visualOpacities, second.visualOpacities)
        assertEquals(first.audioTargets, second.audioTargets)
    }

    @Test
    fun `视觉 opacity 按 fadeMeters smoothstep 展开`() {
        val scheduler = PhaseScheduler(config)
        scheduler.update(300f)
        val op = { m: Float -> scheduler.sensoryState(m).visualOpacities["outline"]!! }
        assertEquals(0f, op(100f), 1e-6f)      // 刚触发
        assertEquals(0.3f, op(110f), 1e-4f)    // 中点 smoothstep(0.5)=0.5 → 0.6×0.5
        assertEquals(0.6f, op(120f), 1e-6f)    // 淡入完成
        assertEquals(0.6f, op(400f), 1e-6f)    // 保持
    }

    @Test
    fun `黑幕层 fadeMeters 缺省为阶跃`() {
        val scheduler = PhaseScheduler(config)
        scheduler.update(0f)
        val state = scheduler.sensoryState(0f)
        assertEquals(1f, state.visualOpacities["void"]!!, 1e-6f)
    }

    @Test
    fun `未触发视觉层 opacity 为 0`() {
        val scheduler = PhaseScheduler(config)
        scheduler.update(100f)
        val state = scheduler.sensoryState(200f)
        assertEquals(0f, state.visualOpacities["main_body"]!!, 1e-6f)
    }

    @Test
    fun `音频目标只含已触发层`() {
        val scheduler = PhaseScheduler(config)
        scheduler.update(100f)
        assertEquals(setOf("footsteps"), scheduler.sensoryState(150f).audioTargets.keys)
        scheduler.update(300f)
        val audio = scheduler.sensoryState(350f).audioTargets
        assertEquals(setOf("footsteps", "ambience"), audio.keys)
        assertEquals(0.35f, audio["ambience"]!!.toVolume, 1e-6f)
        assertEquals(12000, audio["ambience"]!!.fadeMs)
    }

    @Test
    fun `振动规则在对应米数出现`() {
        val scheduler = PhaseScheduler(config)
        scheduler.update(0f)
        assertTrue(scheduler.sensoryState(400f).hapticRules.isEmpty())
        scheduler.update(500f)
        val haptics = scheduler.sensoryState(600f).hapticRules
        assertEquals(1, haptics.size)
        assertEquals("footstep_soft", haptics[0].pattern)
        assertEquals(2, haptics[0].everyNSteps)
    }

    @Test
    fun `S9 恢复 - 预置已触发相位不重播事件`() {
        // 模拟 T07 快照恢复：void/steps/outline/ambience/main_body 已触发
        val scheduler = PhaseScheduler(
            config,
            preFiredPhaseIds = setOf("void", "steps", "outline", "ambience", "main_body"),
        )
        assertTrue("已触发相位不应重播", scheduler.update(0f).isEmpty())
        val events = scheduler.update(400f) // 下一未触发是 haptic(500)
        assertTrue(events.isEmpty())

        val next = scheduler.update(500f)
        assertEquals(listOf("haptic", "detail"), next.map { it.phase.id })
    }

    @Test
    fun `S9 恢复 - 感官目标按当前米数直接重建静态值`() {
        val scheduler = PhaseScheduler(
            config,
            preFiredPhaseIds = setOf("void", "steps", "outline", "ambience", "main_body"),
        )
        val state = scheduler.sensoryState(400f)
        // main_body(300, fade 25, to 0.7)：恢复时 400-300 ≥ 25 → 直接满值
        assertEquals(0.7f, state.visualOpacities["main_body"]!!, 1e-6f)
        // outline(100, fade 20, to 0.6) 同样满值
        assertEquals(0.6f, state.visualOpacities["outline"]!!, 1e-6f)
        assertTrue(state.audioTargets.containsKey("ambience"))
    }

    @Test
    fun `NaN 米数不触发不崩溃`() {
        val scheduler = PhaseScheduler(config)
        assertTrue(scheduler.update(Float.NaN).isEmpty())
        // 之后的合法调用仍正常
        assertEquals(listOf("void"), scheduler.update(0f).map { it.phase.id })
    }

    @Test
    fun `全部相位按配置顺序最终各触发一次`() {
        val scheduler = PhaseScheduler(config)
        val all = mutableListOf<String>()
        var m = 0f
        while (m <= 1000f) {
            all += scheduler.update(m).map { it.phase.id }
            m += 50f
        }
        assertEquals(phaseIds, all)
    }
}
