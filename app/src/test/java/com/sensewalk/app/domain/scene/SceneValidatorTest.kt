package com.sensewalk.app.domain.scene

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** SceneValidator 规则覆盖：ID 唯一、排序、边界、引用、路径、占位与素材策略 */
class SceneValidatorTest {

    private fun validate(
        config: SceneConfig,
        locator: SceneValidator.AssetLocator = TestScenes.locator,
        policy: SceneValidator.AssetsPolicy = SceneValidator.AssetsPolicy.ALLOW_PLACEHOLDERS,
    ) = SceneValidator.validate(config, locator, policy)

    @Test
    fun `基准配置通过校验`() {
        val result = validate(TestScenes.validConfig())
        assertTrue("意外错误: ${result.errors}", result.valid)
    }

    @Test
    fun `相位 id 重复被拒绝`() {
        // 把 detail 改成已存在的 main_body，制造重复
        val phases = TestScenes.defaultPhases().map { if (it.id == "detail") it.copy(id = "main_body") else it }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("相位 id 重复") && it.contains("main_body") })
    }

    @Test
    fun `相位 atMeters 乱序被拒绝`() {
        val phases = TestScenes.defaultPhases().let { it.swap(2, 3) }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("非递减") })
    }

    private fun <T> List<T>.swap(i: Int, j: Int): List<T> = toMutableList().apply {
        val t = this[i]; this[i] = this[j]; this[j] = t
    }

    @Test
    fun `相位越过终点被拒绝`() {
        val phases = TestScenes.defaultPhases().map {
            if (it.id == "arrival") it.copy(atMeters = 1100) else it
        }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("超过终点") && it.contains("arrival") })
    }

    @Test
    fun `audio 相位引用未定义层被拒绝`() {
        val phases = TestScenes.defaultPhases().map {
            if (it.id == "steps") it.copy(layer = "ghost_layer") else it
        }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("ghost_layer") && it.contains("未在 layers 中定义") })
    }

    @Test
    fun `visual 相位引用未定义层被拒绝`() {
        val phases = TestScenes.defaultPhases().map {
            if (it.id == "outline") it.copy(layer = "ghost_visual") else it
        }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("ghost_visual") && it.contains("未在 visualLayers 中定义") })
    }

    @Test
    fun `视觉淡入越过终点被拒绝`() {
        val phases = TestScenes.defaultPhases().map {
            if (it.id == "arrival") it.copy(fadeMeters = 200) else it // 950 + 200 > 1000
        }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("淡入越过终点") })
    }

    @Test
    fun `音量越界被拒绝`() {
        val phases = TestScenes.defaultPhases().map {
            if (it.id == "steps") it.copy(toVolume = 1.5f) else it
        }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("toVolume=1.5") && it.contains("[0,1]") })
    }

    @Test
    fun `透明度越界被拒绝`() {
        val phases = TestScenes.defaultPhases().map {
            if (it.id == "outline") it.copy(toOpacity = -0.1f) else it
        }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("toOpacity=-0.1") })
    }

    @Test
    fun `everyNSteps 小于 1 被拒绝`() {
        val phases = TestScenes.defaultPhases().map {
            if (it.id == "haptic") it.copy(everyNSteps = 0) else it
        }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("everyNSteps=0") })
    }

    @Test
    fun `缺少黑幕相位被拒绝`() {
        val phases = TestScenes.defaultPhases().filterNot { it.id == "void" }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("黑幕") })
    }

    @Test
    fun `pathProfile 中段空缺被拒绝`() {
        val segments = listOf(
            PathSegment(0, 400, TerrainKind.FLAT),
            PathSegment(500, 1000, TerrainKind.FLAT),
        )
        val result = validate(TestScenes.validConfig(segments = segments))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("不连续") })
    }

    @Test
    fun `pathProfile 重叠被拒绝`() {
        val segments = listOf(
            PathSegment(0, 600, TerrainKind.FLAT),
            PathSegment(400, 1000, TerrainKind.FLAT),
        )
        val result = validate(TestScenes.validConfig(segments = segments))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("不连续") })
    }

    @Test
    fun `pathProfile 不从 0 开始被拒绝`() {
        val segments = listOf(PathSegment(50, 1000, TerrainKind.FLAT))
        val result = validate(TestScenes.validConfig(segments = segments))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("从 0 开始") })
    }

    @Test
    fun `pathProfile 终点与门禁不一致被拒绝`() {
        val segments = listOf(PathSegment(0, 900, TerrainKind.FLAT))
        val result = validate(TestScenes.validConfig(segments = segments))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("未覆盖全程") })
    }

    @Test
    fun `前 10% 出现 gap_hop 被拒绝`() {
        val segments = listOf(
            PathSegment(0, 50, TerrainKind.GAP_HOP),
            PathSegment(50, 1000, TerrainKind.FLAT),
        )
        val result = validate(TestScenes.validConfig(segments = segments))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("前 10%") && it.contains("gap_hop") })
    }

    @Test
    fun `30% 处的 gap_hop 合法`() {
        val segments = listOf(
            PathSegment(0, 300, TerrainKind.FLAT),
            PathSegment(300, 340, TerrainKind.GAP_HOP),
            PathSegment(340, 1000, TerrainKind.FLAT),
        )
        val result = validate(TestScenes.validConfig(segments = segments))
        assertTrue("意外错误: ${result.errors}", result.valid)
    }

    @Test
    fun `缺少 75% 音频里程碑被拒绝`() {
        val phases = TestScenes.defaultPhases().filterNot { it.id == "deep" }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("audio 通道缺少 ~75%") })
    }

    @Test
    fun `缺少 95% 视觉里程碑被拒绝`() {
        val phases = TestScenes.defaultPhases().filterNot { it.id == "arrival" }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("visual 通道缺少 ~95%") })
    }

    @Test
    fun `缺失素材文件被拒绝`() {
        val strictLocator = SceneValidator.AssetLocator { false }
        val result = validate(TestScenes.validConfig(), locator = strictLocator)
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("素材不存在") && it.contains("audio/test_step_01.ogg") })
    }

    @Test
    fun `开发占位在开发策略下合法但被记录`() {
        val layers = mapOf(
            "footsteps" to AudioLayerDef.StepOneShot(emptyList(), "dev_tone_variants:test_step"),
            "ambience" to AudioLayerDef.Loop(null, "dev_tone:test_amb"),
            "deep" to AudioLayerDef.Loop(null, "dev_tone:test_deep"),
        )
        val visualLayers = TestScenes.defaultVisualLayers().toMutableMap()
        visualLayers["outline"] = VisualLayerDef.Parallax(placeholder = "dev_silhouette:test_outline")
        val result = validate(TestScenes.validConfig(layers = layers, visualLayers = visualLayers))
        assertTrue("意外错误: ${result.errors}", result.valid)
        assertTrue(result.placeholders.any { it.contains("dev_tone_variants:test_step") })
        assertTrue(result.placeholders.any { it.contains("visualLayers.outline") })
    }

    @Test
    fun `发布策略把开发占位当错误`() {
        val layers = mapOf(
            "footsteps" to AudioLayerDef.StepOneShot(emptyList(), "dev_tone_variants:test_step"),
            "ambience" to AudioLayerDef.Loop(null, "dev_tone:test_amb"),
            "deep" to AudioLayerDef.Loop(null, "dev_tone:test_deep"),
        )
        val result = validate(
            TestScenes.validConfig(layers = layers),
            policy = SceneValidator.AssetsPolicy.REQUIRE_REAL_ASSETS,
        )
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("发布配置不允许开发占位") })
    }

    @Test
    fun `真实素材在发布策略下通过`() {
        val result = validate(
            TestScenes.validConfig(),
            policy = SceneValidator.AssetsPolicy.REQUIRE_REAL_ASSETS,
        )
        assertTrue("意外错误: ${result.errors}", result.valid)
        assertTrue(result.placeholders.isEmpty())
    }

    // ---- 直接构造领域模型的 finite 检查（不经过 JSON，NaN/Infinity 也要拦截）----

    @Test
    fun `模型直接构造 toVolume 为 NaN 被拒绝`() {
        val phases = TestScenes.defaultPhases().map {
            if (it.id == "steps") it.copy(toVolume = Float.NaN) else it
        }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("toVolume") && it.contains("非有限") })
    }

    @Test
    fun `模型直接构造 toOpacity 为 Infinity 被拒绝`() {
        val phases = TestScenes.defaultPhases().map {
            if (it.id == "outline") it.copy(toOpacity = Float.POSITIVE_INFINITY) else it
        }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("toOpacity") && it.contains("非有限") })
    }

    @Test
    fun `模型直接构造 grade 为 NaN 被拒绝`() {
        val segments = listOf(PathSegment(0, 500, TerrainKind.SLOPE_UP, Float.NaN), PathSegment(500, 1000, TerrainKind.FLAT))
        val result = validate(TestScenes.validConfig(segments = segments))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("grade") && it.contains("非有限") })
    }

    @Test
    fun `模型直接构造 parallax 为 NaN 被拒绝`() {
        val visualLayers = TestScenes.defaultVisualLayers().toMutableMap()
        visualLayers["outline"] = VisualLayerDef.Parallax(asset = "visual/test_outline.webp", parallax = Float.NaN)
        val result = validate(TestScenes.validConfig(visualLayers = visualLayers))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("parallax") && it.contains("非有限") })
    }

    // ---- void 黑幕相位严格化 ----

    @Test
    fun `atMeters 0 的视觉相位引用非 void 层不能充当黑幕`() {
        // 黑幕相位改成引用 outline 层：atMeters=0 但不是主计划定义的 void 黑幕
        val phases = TestScenes.defaultPhases().map {
            if (it.id == "void") it.copy(layer = "outline") else it
        }
        val result = validate(TestScenes.validConfig(phases = phases))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("void 黑幕视觉相位") })
    }

    @Test
    fun `void 层不是 solid 类型被拒绝`() {
        val visualLayers = TestScenes.defaultVisualLayers().toMutableMap()
        visualLayers["void"] = VisualLayerDef.Parallax(placeholder = "dev_silhouette:void")
        val result = validate(TestScenes.validConfig(visualLayers = visualLayers))
        assertFalse(result.valid)
        assertTrue(result.errors.any { it.contains("void 黑幕视觉相位") && it.contains("solid") })
    }
}
