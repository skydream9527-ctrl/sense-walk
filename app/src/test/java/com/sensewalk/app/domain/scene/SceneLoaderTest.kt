package com.sensewalk.app.domain.scene

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.FileNotFoundException

/** SceneLoader：可注入数据源验证 Ready/Error 与重试语义 */
class SceneLoaderTest {

    private class MapSceneSource(private val scenes: Map<String, String>) : SceneSource {
        override fun availableSceneIds(): List<String> = scenes.keys.toList()
        override fun readScene(sceneId: String): String =
            scenes[sceneId] ?: throw FileNotFoundException("scenes/$sceneId.json")
    }

    /** 可变源：先坏后好，模拟「修复配置后重试成功」 */
    private class MutableSceneSource(private var scenes: Map<String, String>) : SceneSource {
        override fun availableSceneIds(): List<String> = scenes.keys.toList()
        override fun readScene(sceneId: String): String =
            scenes[sceneId] ?: throw FileNotFoundException("scenes/$sceneId.json")
        fun replace(newScenes: Map<String, String>) {
            scenes = newScenes
        }
    }

    @Test
    fun `全部合法时进入 Ready 并按距离升序`() {
        // 把 1000m 基准整体缩放为 700m（相位/地形同步缩放，保持里程碑与终点合法）
        val short = TestScenes.VALID_JSON
            .replace("\"id\": \"json_scene\"", "\"id\": \"json_short\"")
            .replace("\"requiredDistanceMeters\": 1000", "\"requiredDistanceMeters\": 700")
            .replace("\"atMeters\": 100,", "\"atMeters\": 70,")
            .replace("\"atMeters\": 100 ", "\"atMeters\": 70 ")
            .replace("\"atMeters\": 300,", "\"atMeters\": 200,")
            .replace("\"atMeters\": 300 ", "\"atMeters\": 200 ")
            .replace("\"atMeters\": 500,", "\"atMeters\": 350,")
            .replace("\"atMeters\": 500 ", "\"atMeters\": 350 ")
            .replace("\"atMeters\": 750,", "\"atMeters\": 525,")
            .replace("\"atMeters\": 750 ", "\"atMeters\": 525 ")
            .replace("\"atMeters\": 950,", "\"atMeters\": 665,")
            .replace("\"to\": 1000", "\"to\": 700")
        val source = MapSceneSource(mapOf("night" to short, "forest" to TestScenes.VALID_JSON))
        val state = SceneLoader(source, TestScenes.locator).loadAll()
        assertTrue("意外状态: $state", state is SceneLoadState.Ready)
        val scenes = (state as SceneLoadState.Ready).scenes
        assertEquals(listOf(700, 1000), scenes.map { it.requiredDistanceMeters })
    }

    @Test
    fun `坏 JSON 汇总为 Error 且指明场景`() {
        val source = MapSceneSource(
            mapOf(
                "forest" to TestScenes.VALID_JSON,
                "broken" to "{ not-json",
            ),
        )
        val state = SceneLoader(source, TestScenes.locator).loadAll()
        assertTrue(state is SceneLoadState.Error)
        val diagnostics = (state as SceneLoadState.Error).diagnostics
        assertTrue(diagnostics.any { it.contains("broken") && it.contains("JSON 语法错误") })
    }

    @Test
    fun `校验失败汇总为 Error 不静默丢场景`() {
        // 去掉黑幕相位（首个数组元素，带尾逗号）→ 校验失败；不能静默从列表里消失
        val invalid = TestScenes.VALID_JSON.replace(
            """{ "id": "void", "atMeters": 0, "channel": "visual", "layer": "void", "toOpacity": 1.0 },""",
            "",
        )
        assertTrue("替换未生效：void 相位仍在", !invalid.contains("\"id\": \"void\""))
        val source = MapSceneSource(mapOf("forest" to invalid))
        val state = SceneLoader(source, TestScenes.locator).loadAll()
        assertTrue(state is SceneLoadState.Error)
        val diagnostics = (state as SceneLoadState.Error).diagnostics
        assertTrue(diagnostics.any { it.contains("forest") && it.contains("校验失败") })
    }

    @Test
    fun `读取失败（文件缺失）给出可解释结果`() {
        val missing = object : SceneSource {
            override fun availableSceneIds(): List<String> = listOf("forest", "ghost")
            override fun readScene(sceneId: String): String =
                if (sceneId == "ghost") throw FileNotFoundException("scenes/ghost.json")
                else TestScenes.VALID_JSON
        }
        val state = SceneLoader(missing, TestScenes.locator).loadAll()
        assertTrue(state is SceneLoadState.Error)
        assertTrue(
            (state as SceneLoadState.Error).diagnostics.any { it.contains("ghost") && it.contains("读取失败") },
        )
    }

    @Test
    fun `空场景目录给出可解释错误`() {
        val state = SceneLoader(MapSceneSource(emptyMap()), TestScenes.locator).loadAll()
        assertTrue(state is SceneLoadState.Error)
        assertTrue((state as SceneLoadState.Error).diagnostics.any { it.contains("场景目录为空") })
    }

    @Test
    fun `场景 id 重复被拒绝`() {
        val twinSource = MapSceneSource(mapOf("a" to TestScenes.VALID_JSON, "b" to TestScenes.VALID_JSON))
        val state = SceneLoader(twinSource, TestScenes.locator).loadAll()
        assertTrue(state is SceneLoadState.Error)
        assertTrue((state as SceneLoadState.Error).diagnostics.any { it.contains("场景 id 重复") })
    }

    @Test
    fun `修复配置后重试进入 Ready`() {
        val source = MutableSceneSource(mapOf("forest" to "{ broken"))
        val loader = SceneLoader(source, TestScenes.locator)
        val first = loader.loadAll()
        assertTrue(first is SceneLoadState.Error)

        source.replace(mapOf("forest" to TestScenes.VALID_JSON))
        val second = loader.loadAll()
        assertTrue("重试后应 Ready: $second", second is SceneLoadState.Ready)
        assertEquals(1, (second as SceneLoadState.Ready).scenes.size)
    }

    // ---- 目录枚举异常：可解释、可重试，不静默变成空列表 ----

    private class FlakyDirectorySource(private var fail: Boolean) : SceneSource {
        override fun availableSceneIds(): List<String> {
            if (fail) throw RuntimeException("assets 目录不可读 (模拟 IO 异常)")
            return listOf("forest")
        }

        override fun readScene(sceneId: String): String = TestScenes.VALID_JSON
    }

    @Test
    fun `目录枚举异常转为可解释 Error`() {
        val state = SceneLoader(FlakyDirectorySource(fail = true), TestScenes.locator).loadAll()
        assertTrue(state is SceneLoadState.Error)
        val diagnostics = (state as SceneLoadState.Error).diagnostics
        assertTrue(diagnostics.any { it.contains("场景目录读取失败") && it.contains("模拟 IO 异常") })
    }

    @Test
    fun `目录枚举失败修复后重试成功`() {
        val source = FlakyDirectorySource(fail = true)
        val loader = SceneLoader(source, TestScenes.locator)
        assertTrue(loader.loadAll() is SceneLoadState.Error)

        source.fail = false
        val second = loader.loadAll()
        assertTrue("重试后应 Ready: $second", second is SceneLoadState.Ready)
        assertEquals(1, (second as SceneLoadState.Ready).scenes.size)
    }
}
