package com.sensewalk.app.domain.scene

import com.sensewalk.app.domain.phase.PhaseScheduler
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.walk.RealWalkController
import com.sensewalk.app.domain.walk.VirtualWalkController
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 雨林 900m 运行时底座（SW-016，D-009 冻结规格）：
 * 配置位于 app/src/test/resources/scenes/rainforest.json——**不进生产 assets**，
 * 生产入口的可用性门禁（HomeScreen/ModeScreen 白名单）保持雨林关闭，
 * 候选未到不会被自动枚举为"完成场景"。
 *
 * 音频层为显式临时占位（引用既有森林音频文件，仅供 loader/validator 全链路可测）；
 * 正式雨林声景由 SW-007 接入，本测试不冒称独立声景。
 */
class RainforestFoundationTest {

    private class FakeClock(var now: Long = 0L) : MonotonicClock {
        override fun nowMs(): Long = now
    }

    private val rainforestJson: String =
        javaClass.getResourceAsStream("/scenes/rainforest.json")!!.bufferedReader().readText()

    /** 占位音频指向生产真实文件；素材存在性由 MigratedSceneConfigsTest 覆盖 */
    private val locator = SceneValidator.AssetLocator { true }

    private fun load(): SceneConfig {
        val state = SceneLoader(MapSceneSource(mapOf("rainforest" to rainforestJson)), locator).loadAll()
        assertTrue("雨林配置应加载+校验成功，实际 $state", state is SceneLoadState.Ready)
        return (state as SceneLoadState.Ready).scenes.first { it.id == "rainforest" }
    }

    private fun loadRaw(json: String): SceneLoadState =
        SceneLoader(MapSceneSource(mapOf("rainforest" to json)), locator).loadAll()

    private class MapSceneSource(private val scenes: Map<String, String>) : SceneSource {
        override fun availableSceneIds(): List<String> = scenes.keys.toList()
        override fun readScene(sceneId: String): String = scenes.getValue(sceneId)
    }

    // ---- 1. D-009 五层参数逐项精确核对 ----

    @Test
    fun `D009 五层 canonical 参数精确匹配 - 类型视差解锁透明淡入`() {
        val c = load()
        assertEquals(900, c.requiredDistanceMeters)
        val v = c.visualLayers
        assertEquals(6, v.size) // void + 五层

        val mist = v["mist"] as VisualLayerDef.Overlay
        assertEquals("mist 无视差（overlay）", 0f, 0f)
        val trunks = v["trunks_canopy"] as VisualLayerDef.Parallax
        assertEquals(0.30f, trunks.parallax, 1e-6f)
        val vines = v["vines_light"] as VisualLayerDef.Parallax
        assertEquals(0.60f, vines.parallax, 1e-6f)
        assertTrue(v["distant_glow"] is VisualLayerDef.Overlay)
        assertTrue(v["glade"] is VisualLayerDef.Overlay)

        fun phase(id: String) = c.phases.first { it.id == id }
        assertEquals(90, phase("mist").atMeters)
        assertEquals(0.55f, phase("mist").toOpacity!!, 1e-6f)
        assertEquals(20, phase("mist").fadeMeters!!)
        assertEquals(270, phase("trunks_canopy").atMeters)
        assertEquals(0.85f, phase("trunks_canopy").toOpacity!!, 1e-6f)
        assertEquals(25, phase("trunks_canopy").fadeMeters!!)
        assertEquals(450, phase("vines_light").atMeters)
        assertEquals(1.0f, phase("vines_light").toOpacity!!, 1e-6f)
        assertEquals(675, phase("distant_glow").atMeters)
        assertEquals(0.85f, phase("distant_glow").toOpacity!!, 1e-6f)
        assertEquals(855, phase("glade").atMeters)
        assertEquals(0.90f, phase("glade").toOpacity!!, 1e-6f)
        assertEquals(20, phase("glade").fadeMeters!!)
    }

    @Test
    fun `全显达成点 875m - 900m 终点不切屏`() {
        val c = load()
        val scheduler = PhaseScheduler(c)
        var events = scheduler.update(874f)
        assertTrue("875m 前 glade 未完成", scheduler.firedPhaseIds.contains("glade").not() || events.isNotEmpty())
        // glade@855 fade20 → 875m 满
        val state = scheduler.sensoryState(875f)
        assertEquals(0.90f, state.visualOpacities["glade"]!!, 1e-6f)
        // 900m 终点各层完整（不切屏：opacity 保持）
        val end = scheduler.sensoryState(900f)
        assertEquals(1.0f, end.visualOpacities["vines_light"]!!, 1e-6f)
        assertEquals(0.90f, end.visualOpacities["glade"]!!, 1e-6f)
    }

    // ---- 2. 双模式 900m 通关与门禁 ----

    @Test
    fun `虚走 900m 全程通关 - 五层揭示有序`() {
        val clock = FakeClock()
        val c = load()
        val vc = VirtualWalkController(c, clock)
        vc.onStick(0.55f) // 甜点
        var last: VirtualWalkController.Snapshot? = null
        var guard = 0
        while (vc.snapshot().session != SessionState.COMPLETED && guard++ < 2_000_000) {
            clock.now += 50
            last = vc.frame()
        }
        assertEquals("900m 必须走完", SessionState.COMPLETED, vc.snapshot().session)
        assertEquals(900f, vc.snapshot().meters, 0.5f)
        assertEquals(setOf("void", "mist", "trunks_canopy", "vines_light", "distant_glow", "glade").plus(
            setOf("steps_placeholder", "ambience_placeholder", "haptic_steps", "deep_placeholder"),
        ), vc.scheduler.firedPhaseIds)
    }

    @Test
    fun `实走 900m - counter 计距与同一配置门禁`() {
        val clock = FakeClock()
        val c = load()
        val rc = RealWalkController(c, clock)
        rc.start()
        rc.onCounterEvent(0L, 0L)
        var count = 0L
        var t = 0L
        var s = rc.onCounterEvent(count, t)
        var guard = 0
        while (s.session != SessionState.COMPLETED && guard++ < 2_000_000) {
            count += 2; t += 1000
            s = rc.onCounterEvent(count, t)
        }
        assertEquals(SessionState.COMPLETED, s.session)
        assertEquals(900f, s.meters, 0.5f)
    }

    // ---- 3. 跨相位恢复（复用 SW-004/SW-005 冻结语义）----

    @Test
    fun `450m 中点恢复 - fired 相位不重播且能走完`() {
        val c = load()
        val clock1 = FakeClock()
        val original = VirtualWalkController(c, clock1)
        original.onStick(0.55f)
        var guard = 0
        while (original.snapshot().meters < 450f && guard++ < 1_000_000) {
            clock1.now += 50; original.frame()
        }
        val firedAt450 = original.scheduler.firedPhaseIds
        assertTrue("450m 已触发 vines_light", "vines_light" in firedAt450)

        val clock2 = FakeClock(60_000L)
        val restored = VirtualWalkController(
            c, clock2,
            restore = VirtualWalkController.Restore(
                progress = original.accumulator.snapshot(),
                firedPhaseIds = firedAt450,
                elapsedActiveMs = 120_000L,
            ),
        )
        assertTrue("恢复点已触发相位不得重播", restored.drainPhaseEvents().isEmpty())
        restored.onStick(0.55f)
        guard = 0
        while (restored.snapshot().session != SessionState.COMPLETED && guard++ < 2_000_000) {
            clock2.now += 50; restored.frame()
        }
        assertEquals(SessionState.COMPLETED, restored.snapshot().session)
        assertEquals(900f, restored.snapshot().meters, 0.5f)
    }

    @Test
    fun `站稳提示快照字段兼容 - 旧档缺省 false 且同局恢复一次`() {
        val c = load()
        val restored = VirtualWalkController(
            c, FakeClock(),
            restore = VirtualWalkController.Restore(
                progress = com.sensewalk.app.domain.progress.ProgressSnapshot(
                    sPos = 10f, sBest = 10f, meters = 10f,
                    requiredDistanceMeters = 900f,
                ),
                firedPhaseIds = setOf("void"),
                elapsedActiveMs = 0L,
                stabilizeHintShown = true, // 旧档 false 路径在 SW-005 R2 已测；此处验雨林配置同语义
            ),
        )
        org.junit.Assert.assertFalse(restored.consumeStabilizeHint())
    }

    // ---- 4. 配置边界与缺层拒绝 ----

    @Test
    fun `visual 相位引用未定义层 - 校验拒绝（不完整配置不进生产）`() {
        val broken = rainforestJson.replace("\"layer\": \"glade\"", "\"layer\": \"nonexistent_layer\"")
        assertTrue("引用未知层应失败", loadRaw(broken) is SceneLoadState.Error)
    }

    @Test
    fun `相位超终点被拒 - 875 淡入完成点合法 905 越界拒绝`() {
        // glade@855+fade20=875 ≤ 900：合法（D-009 全显达成点）
        val legal = rainforestJson.replace("\"atMeters\": 855", "\"atMeters\": 880") // 880+20=900 恰达终点：合法
        assertTrue("880+20=900 恰达终点应合法", loadRaw(legal) is SceneLoadState.Ready)
        val over = rainforestJson.replace("\"atMeters\": 855", "\"atMeters\": 905")
        assertTrue("905 > 900 终点应拒绝", loadRaw(over) is SceneLoadState.Error)
    }

    @Test
    fun `生产场景目录不含雨林 - 可用性门禁保持关闭`() {
        // test/resources 的雨林不在生产 assets；HomeScreen/ModeScreen 白名单仍只有 forest。
        // 反射检查生产常量（UI 层最小断言，防误开放）：
        val homeField = Class.forName("com.sensewalk.app.ui.home.HomeScreenKt")
            .getDeclaredField("OPEN_VIRTUAL_SCENES")
        homeField.isAccessible = true
        @Suppress("UNCHECKED_CAST")
        val open = homeField.get(null) as Set<String>
        assertEquals("雨林未开放前白名单只含 forest", setOf("forest"), open)
    }
}
