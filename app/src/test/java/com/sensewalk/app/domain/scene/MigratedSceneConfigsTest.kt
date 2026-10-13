package com.sensewalk.app.domain.scene

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 仓库内三份真实迁移配置（S6 前置）：从 assets 读取实际文件，
 * 走完整 解析→校验 链路；占位策略如实报告（当前全部为开发占位，未达发布条件）。
 */
class MigratedSceneConfigsTest {

    /** 单测工作目录可能是模块目录或仓库根目录，两者都探测 */
    private fun assetsDir(): File =
        listOf(File("src/main/assets"), File("app/src/main/assets"))
            .firstOrNull { it.isDirectory }
            ?: error("找不到 src/main/assets（单测需在 app 模块下运行）")

    /** 基于真实文件系统的素材定位器 */
    private class FileAssetLocator(root: File) : SceneValidator.AssetLocator {
        private val files = mutableSetOf<String>()

        init {
            collect(root, "")
        }

        private fun collect(dir: File, prefix: String) {
            dir.listFiles()?.forEach { f ->
                val rel = if (prefix.isEmpty()) f.name else "$prefix/${f.name}"
                if (f.isDirectory) collect(f, rel) else files.add(rel)
            }
        }

        override fun exists(path: String): Boolean = path in files
    }

    private fun loadScene(id: String): SceneConfig {
        val file = File(assetsDir(), "scenes/$id.json")
        assertTrue("场景文件应存在: $file", file.isFile)
        return SceneJsonParser.parse(file.readText())
    }

    private fun validateReal(config: SceneConfig): SceneValidator.ValidationResult =
        SceneValidator.validate(config, FileAssetLocator(assetsDir()))

    @Test
    fun `森林 800m 配置通过完整校验`() {
        val forest = loadScene("forest")
        assertEquals(800, forest.requiredDistanceMeters)
        val result = validateReal(forest)
        assertTrue("意外错误: ${result.errors}", result.valid)
        // 相位里程碑与 §7.2 一致
        assertEquals(
            listOf(0, 80, 80, 240, 240, 400, 400, 600, 600, 760),
            forest.phases.map { it.atMeters },
        )
        assertEquals("footstep_soft", forest.phases.first { it.channel == PhaseChannel.HAPTIC }.pattern)
        // 地形含缓坡与越坎（§5 森林单页），gap_hop 位于 30% 处而非黑幕区
        val kinds = forest.pathProfile.segments.map { it.kind }
        assertTrue(kinds.contains(TerrainKind.SLOPE_UP))
        assertTrue(kinds.contains(TerrainKind.GAP_HOP))
        assertTrue(forest.pathProfile.segments.first { it.kind == TerrainKind.GAP_HOP }.from >= 80)
    }

    @Test
    fun `沙漠 1200m 配置通过完整校验`() {
        val desert = loadScene("desert")
        assertEquals(1200, desert.requiredDistanceMeters)
        val result = validateReal(desert)
        assertTrue("意外错误: ${result.errors}", result.valid)
        assertEquals(
            listOf(0, 120, 120, 360, 360, 600, 600, 900, 900, 1140),
            desert.phases.map { it.atMeters },
        )
        // 沙漠振动更疏（everyNSteps=3）
        assertEquals(3, desert.phases.first { it.channel == PhaseChannel.HAPTIC }.everyNSteps)
    }

    @Test
    fun `夜径 700m 配置通过完整校验`() {
        val night = loadScene("night_path")
        assertEquals(700, night.requiredDistanceMeters)
        val result = validateReal(night)
        assertTrue("意外错误: ${result.errors}", result.valid)
        assertEquals(
            listOf(0, 70, 70, 200, 200, 350, 350, 525, 525, 665),
            night.phases.map { it.atMeters },
        )
    }

    @Test
    fun `三景时长推导与 §6_1 校准表一致`() {
        assertEquals(13, SceneDurationEstimator.estimatedVirtualMinutes(loadScene("forest")))
        assertEquals(19, SceneDurationEstimator.estimatedVirtualMinutes(loadScene("desert")))
        assertEquals(11, SceneDurationEstimator.estimatedVirtualMinutes(loadScene("night_path")))
    }

    @Test
    fun `配置不再包含时间字段`() {
        listOf("forest", "desert", "night_path").forEach { id ->
            val raw = File(assetsDir(), "scenes/$id.json").readText()
            assertFalse("$id 不应再有 suggestedMinutes", raw.contains("suggestedMinutes"))
            assertFalse("$id 不应再有 atSec", raw.contains("atSec"))
            assertFalse("$id 不应再有 intervalMs", raw.contains("intervalMs"))
        }
    }

    @Test
    fun `占位状态如实分层 - 森林全真实素材发布放行，其他景占位不放行`() {
        // 森林（T05 收尾）：五个视觉层 + 三个音频层全部为真实素材（Wikimedia
        // CC0/CC BY，见 ASSETS.md），无占位；发布策略应放行
        val forest = loadScene("forest")
        val forestDev = validateReal(forest)
        assertTrue("森林开发策略应通过: ${forestDev.errors}", forestDev.valid)
        assertTrue("森林不应再有占位: ${forestDev.placeholders}", forestDev.placeholders.isEmpty())
        val forestRelease = SceneValidator.validate(
            forest,
            FileAssetLocator(assetsDir()),
            SceneValidator.AssetsPolicy.REQUIRE_REAL_ASSETS,
        )
        assertTrue("森林发布策略应放行（素材齐全）: ${forestRelease.errors}", forestRelease.valid)

        // 沙漠/夜径：素材未入库，仍为显式占位；发布策略不放行
        listOf("desert", "night_path").forEach { id ->
            val config = loadScene(id)
            val dev = validateReal(config)
            assertTrue("$id 开发策略应通过: ${dev.errors}", dev.valid)
            assertTrue("$id 应报告占位清单", dev.placeholders.isNotEmpty())

            val release = SceneValidator.validate(
                config,
                FileAssetLocator(assetsDir()),
                SceneValidator.AssetsPolicy.REQUIRE_REAL_ASSETS,
            )
            assertFalse("$id 发布策略不应放行（素材未齐）", release.valid)
            assertTrue(release.errors.any { it.contains("开发占位") })
        }
    }

    @Test
    fun `场景加载器对真实 assets 目录产出 Ready`() {
        val dir = assetsDir()
        val source = object : SceneSource {
            override fun availableSceneIds(): List<String> =
                File(dir, "scenes").listFiles()!!
                    .filter { it.name.endsWith(".json") }
                    .map { it.name.removeSuffix(".json") }
                    .sorted()

            override fun readScene(sceneId: String): String = File(dir, "scenes/$sceneId.json").readText()
        }
        val state = SceneLoader(source, FileAssetLocator(dir)).loadAll()
        assertTrue("意外状态: $state", state is SceneLoadState.Ready)
        val scenes = (state as SceneLoadState.Ready).scenes
        assertEquals(3, scenes.size)
        assertEquals(listOf(700, 800, 1200), scenes.map { it.requiredDistanceMeters })
    }
}
