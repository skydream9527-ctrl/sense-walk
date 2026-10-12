package com.sensewalk.app.domain.scene

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

/** schema v2 解析器：结构/类型/版本门槛（JVM 运行，不依赖 org.json） */
class SceneJsonParserTest {

    @Test
    fun `合法 v2 JSON 完整解析`() {
        val config = SceneJsonParser.parse(TestScenes.VALID_JSON)
        assertEquals(2, config.schemaVersion)
        assertEquals("json_scene", config.id)
        assertEquals("JSON 场景", config.name)
        assertEquals(1000, config.requiredDistanceMeters)
        assertEquals(10, config.phases.size)
        assertEquals("comfort_v1", config.stickCurveId) // 缺省值
        assertEquals(3, config.layers.size)
        assertEquals(6, config.visualLayers.size)
        val void = config.phases.first()
        assertEquals(PhaseChannel.VISUAL, void.channel)
        assertEquals(0, void.atMeters)
        assertEquals(1f, void.toOpacity!!, 1e-6f)
        val steps = config.phases[1]
        assertEquals(PhaseChannel.AUDIO, steps.channel)
        assertEquals("footsteps", steps.layer)
        assertEquals(0.25f, steps.toVolume!!, 1e-6f)
        val haptic = config.phases.first { it.id == "haptic" }
        assertEquals(PhaseChannel.HAPTIC, haptic.channel)
        assertEquals("footstep_soft", haptic.pattern)
        assertEquals(2, haptic.everyNSteps)
        assertTrue(config.layers["footsteps"] is AudioLayerDef.StepOneShot)
        val ambience = config.layers["ambience"]
        assertNotNull(ambience)
        assertEquals("dev_tone:test_amb", (ambience as AudioLayerDef.Loop).placeholder)
        assertTrue(config.visualLayers["void"] is VisualLayerDef.Solid)
    }

    @Test
    fun `坏 JSON 语法给出明确诊断`() {
        try {
            SceneJsonParser.parse("""{ "schemaVersion": 2, """)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("JSON 语法错误"))
        }
    }

    @Test
    fun `根元素不是对象给出明确诊断`() {
        try {
            SceneJsonParser.parse("""[1, 2, 3]""")
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("根元素必须是对象"))
        }
    }

    @Test
    fun `未知 schemaVersion 被拒绝`() {
        val json = TestScenes.VALID_JSON.replace("\"schemaVersion\": 2", "\"schemaVersion\": 99")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("99"))
            assertTrue(e.message!!.contains("不受支持"))
        }
    }

    @Test
    fun `缺失 schemaVersion 被拒绝`() {
        val json = TestScenes.VALID_JSON.replace("\"schemaVersion\": 2,", "")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("schemaVersion"))
        }
    }

    @Test
    fun `旧 v1 格式被拒绝并提示迁移`() {
        val legacy = """{
          "id": "forest", "name": "森林漫步", "suggestedMinutes": 15,
          "phases": [ { "atSec": 0, "action": "silence" } ],
          "layers": { "footsteps": { "file": "audio/forest_steps.ogg", "loop": true } }
        }""".trimIndent()
        try {
            SceneJsonParser.parse(legacy)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("旧 v1 格式"))
            assertTrue(e.message!!.contains("迁移"))
        }
    }

    @Test
    fun `未知通道给出带路径诊断`() {
        val json = TestScenes.VALID_JSON.replace("\"channel\": \"audio\"", "\"channel\": \"smell\"")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("未知通道"))
            assertTrue(e.message!!.contains("smell"))
            assertTrue(e.message!!.contains("phases[1]"))
        }
    }

    @Test
    fun `未知地形给出带路径诊断`() {
        val json = TestScenes.VALID_JSON.replace("\"kind\": \"flat\"", "\"kind\": \"lava\"")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("未知地形"))
            assertTrue(e.message!!.contains("lava"))
        }
    }

    @Test
    fun `未知音频层类型给出诊断`() {
        val json = TestScenes.VALID_JSON.replace("\"type\": \"loop\"", "\"type\": \"chorus\"")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("未知音频层类型"))
            assertTrue(e.message!!.contains("chorus"))
        }
    }

    @Test
    fun `file 与 placeholder 互斥`() {
        val json = TestScenes.VALID_JSON.replace(
            "\"ambience\": { \"type\": \"loop\", \"placeholder\": \"dev_tone:test_amb\" }",
            "\"ambience\": { \"type\": \"loop\", \"file\": \"audio/amb.ogg\", \"placeholder\": \"dev_tone:test_amb\" }",
        )
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("互斥"))
            assertTrue(e.message!!.contains("layers.ambience"))
        }
    }

    @Test
    fun `stepOneShot 无文件无占位被拒绝`() {
        val json = TestScenes.VALID_JSON.replace(
            "\"footsteps\": { \"type\": \"stepOneShot\", \"placeholder\": \"dev_tone_variants:test_step\" }",
            "\"footsteps\": { \"type\": \"stepOneShot\" }",
        )
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("stepOneShot 需要 files"))
        }
    }

    @Test
    fun `数值字段类型错误给出实际值`() {
        val json = TestScenes.VALID_JSON.replace("\"toVolume\": 0.25", "\"toVolume\": \"loud\"")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("必须是数值"))
            assertTrue(e.message!!.contains("loud"))
        }
    }

    @Test
    fun `v2 中出现的未知字段按向前兼容忽略`() {
        // suggestedMinutes 在 v2 中已删除；若残留不构成解析失败，但配置不再消费它
        val json = TestScenes.VALID_JSON.replace("\"schemaVersion\": 2,", "\"schemaVersion\": 2, \"futureField\": 1,")
        val config = SceneJsonParser.parse(json)
        assertEquals("json_scene", config.id)
    }

    // ---- 严格类型边界：区分缺失 / null / 字符串 / 布尔 / 对象 / 数组 ----

    @Test
    fun `数值字段不接受字符串冒充`() {
        val json = TestScenes.VALID_JSON.replace("\"toVolume\": 0.25", "\"toVolume\": \"0.25\"")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!, e.message!!.contains("必须是数值"))
            assertTrue(e.message!!.contains("字符串"))
            assertTrue(e.message!!.contains("0.25"))
        }
    }

    @Test
    fun `数值字段不接受对象冒充`() {
        val json = TestScenes.VALID_JSON.replace("\"toVolume\": 0.35", "\"toVolume\": { \"v\": 1 }")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("必须是数值"))
            assertTrue(e.message!!.contains("对象"))
        }
    }

    @Test
    fun `数值字段不接受数组冒充`() {
        val json = TestScenes.VALID_JSON.replace("\"atMeters\": 100,", "\"atMeters\": [100],")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("必须是数值"))
            assertTrue(e.message!!.contains("数组"))
        }
    }

    @Test
    fun `数值字段不接受布尔冒充`() {
        val json = TestScenes.VALID_JSON.replace("\"requiredDistanceMeters\": 1000", "\"requiredDistanceMeters\": true")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("必须是数值"))
            assertTrue(e.message!!.contains("布尔"))
        }
    }

    @Test
    fun `溢出为 Infinity 的数值被拒绝`() {
        val json = TestScenes.VALID_JSON.replace("\"toVolume\": 0.25", "\"toVolume\": 1e999")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("有限数值"))
        }
    }

    @Test
    fun `整数字段不接受小数`() {
        val json = TestScenes.VALID_JSON.replace("\"schemaVersion\": 2", "\"schemaVersion\": 2.5")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("必须是整数"))
        }
    }

    @Test
    fun `字符串字段不接受数字冒充`() {
        val json = TestScenes.VALID_JSON.replace("\"name\": \"JSON 场景\"", "\"name\": 42")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("必须是字符串"))
        }
    }

    @Test
    fun `字符串字段不接受布尔冒充`() {
        val json = TestScenes.VALID_JSON.replace("\"name\": \"JSON 场景\"", "\"name\": true")
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("必须是字符串"))
            assertTrue(e.message!!.contains("布尔"))
        }
    }

    @Test
    fun `stepOneShot 的 files 元素必须是字符串`() {
        val json = TestScenes.VALID_JSON.replace(
            "\"footsteps\": { \"type\": \"stepOneShot\", \"placeholder\": \"dev_tone_variants:test_step\" }",
            "\"footsteps\": { \"type\": \"stepOneShot\", \"files\": [\"audio/a.ogg\", 5] }",
        )
        try {
            SceneJsonParser.parse(json)
            fail("应当抛出解析异常")
        } catch (e: SceneConfigParseException) {
            assertTrue(e.message!!.contains("files[1]"))
            assertTrue(e.message!!.contains("必须是字符串"))
        }
    }
}
