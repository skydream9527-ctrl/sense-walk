package com.sensewalk.app.domain.scene

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject

/** 场景配置解析失败。message 携带字段路径，供首页错误态直接展示诊断。 */
class SceneConfigParseException(message: String) : Exception(message)

/**
 * SceneConfig schema v2 解析器（DEVELOPMENT.md §12.4）。
 *
 * 纯 Kotlin + kotlinx.serialization JsonElement：可在 JVM 单测运行，
 * 不依赖 Android org.json。只做结构/类型解析；跨字段规则见 [SceneValidator]。
 * 未知字段按向前兼容忽略；旧 v1（atSec / suggestedMinutes）在这里被明确拒绝。
 */
object SceneJsonParser {

    const val SUPPORTED_SCHEMA_VERSION = 2

    private val json = Json { ignoreUnknownKeys = true }

    fun parse(text: String): SceneConfig {
        val element = try {
            json.parseToJsonElement(text)
        } catch (e: Exception) {
            throw SceneConfigParseException("JSON 语法错误: ${e.message}")
        }
        val root = try {
            element.jsonObject
        } catch (e: IllegalArgumentException) {
            throw SceneConfigParseException("JSON 根元素必须是对象")
        }

        if (!root.has("schemaVersion")) {
            val legacy = root.has("atSec") || root.has("suggestedMinutes")
            throw SceneConfigParseException(
                if (legacy) {
                    "schemaVersion 缺失：文件是旧 v1 格式（atSec / suggestedMinutes），需按 §12.4 迁移为距离相位"
                } else {
                    "schemaVersion 缺失（本版本仅支持 $SUPPORTED_SCHEMA_VERSION）"
                },
            )
        }
        val schemaVersion = root.reqInt("schemaVersion", "\$")
        if (schemaVersion != SUPPORTED_SCHEMA_VERSION) {
            val legacy = schemaVersion <= 1 || root.has("suggestedMinutes") || root.has("atSec")
            val hint = if (legacy) {
                "；文件可能仍是旧 v1 格式（atSec / suggestedMinutes），需要按 §12.4 迁移为距离相位"
            } else ""
            throw SceneConfigParseException(
                "schemaVersion=$schemaVersion 不受支持（本版本仅支持 $SUPPORTED_SCHEMA_VERSION）$hint",
            )
        }

        val id = root.reqString("id", "\$")
        val name = root.reqString("name", "\$")
        val required = root.reqInt("requiredDistanceMeters", "\$")

        val phasesJson = root.reqArray("phases", "\$")
        val phases = phasesJson.mapIndexed { i, el ->
            val p = el.asObject("\$.phases[$i]")
            val channel = parseChannel(p.reqString("channel", "\$.phases[$i]"), i)
            Phase(
                id = p.reqString("id", "\$.phases[$i]"),
                atMeters = p.reqInt("atMeters", "\$.phases[$i]"),
                channel = channel,
                layer = p.optNotBlankString("layer", "\$.phases[$i]"),
                toVolume = p.optFloat("toVolume", "\$.phases[$i]"),
                toOpacity = p.optFloat("toOpacity", "\$.phases[$i]"),
                fadeMs = p.optInt("fadeMs", "\$.phases[$i]"),
                fadeMeters = p.optInt("fadeMeters", "\$.phases[$i]"),
                pattern = p.optNotBlankString("pattern", "\$.phases[$i]"),
                everyNSteps = p.optInt("everyNSteps", "\$.phases[$i]"),
            )
        }

        val pathJson = root.reqObject("pathProfile", "\$")
        val segments = pathJson.reqArray("segments", "\$.pathProfile").mapIndexed { i, el ->
            val s = el.asObject("\$.pathProfile.segments[$i]")
            PathSegment(
                from = s.reqInt("from", "\$.pathProfile.segments[$i]"),
                to = s.reqInt("to", "\$.pathProfile.segments[$i]"),
                kind = parseTerrainKind(s.reqString("kind", "\$.pathProfile.segments[$i]"), i),
                grade = s.optFloat("grade", "\$.pathProfile.segments[$i]"),
            )
        }

        return SceneConfig(
            schemaVersion = schemaVersion,
            id = id,
            name = name,
            mood = root.optNotBlankString("mood", "\$"),
            themeColor = root.optNotBlankString("themeColor", "\$"),
            requiredDistanceMeters = required,
            stickCurveId = root.optNotBlankString("stickCurveId", "\$") ?: SceneConfig.DEFAULT_STICK_CURVE,
            phases = phases,
            pathProfile = PathProfile(segments),
            layers = parseAudioLayers(root.reqObject("layers", "\$")),
            visualLayers = parseVisualLayers(root.reqObject("visualLayers", "\$")),
        )
    }

    private fun parseAudioLayers(root: JsonObject): Map<String, AudioLayerDef> {
        val result = LinkedHashMap<String, AudioLayerDef>()
        for ((key, el) in root) {
            val path = "\$.layers.$key"
            val obj = el.asObject(path)
            when (val type = obj.reqString("type", path)) {
                "stepOneShot" -> {
                    val files = (obj.get("files") as? JsonArray)?.mapIndexed { i, f ->
                        if (f !is JsonPrimitive || !f.isString) {
                            throw SceneConfigParseException("$path.files[$i] 必须是字符串，实际为${f.describeKind()}")
                        }
                        f.content
                    }.orEmpty()
                    val placeholder = obj.optNotBlankString("placeholder", path)
                    if (files.isEmpty() && placeholder == null) {
                        throw SceneConfigParseException("$path: stepOneShot 需要 files（≥1 个变体）或显式 placeholder")
                    }
                    if (files.isNotEmpty() && placeholder != null) {
                        throw SceneConfigParseException("$path: files 与 placeholder 互斥，占位必须显式且唯一")
                    }
                    result[key] = AudioLayerDef.StepOneShot(files, placeholder)
                }
                "loop" -> {
                    val file = obj.optNotBlankString("file", path)
                    val placeholder = obj.optNotBlankString("placeholder", path)
                    if (file == null && placeholder == null) {
                        throw SceneConfigParseException("$path: loop 需要 file 或显式 placeholder")
                    }
                    if (file != null && placeholder != null) {
                        throw SceneConfigParseException("$path: file 与 placeholder 互斥，占位必须显式且唯一")
                    }
                    result[key] = AudioLayerDef.Loop(file, placeholder)
                }
                else -> throw SceneConfigParseException("$path.type: 未知音频层类型 '$type'（支持 stepOneShot / loop）")
            }
        }
        return result
    }

    private fun parseVisualLayers(root: JsonObject): Map<String, VisualLayerDef> {
        val result = LinkedHashMap<String, VisualLayerDef>()
        for ((key, el) in root) {
            val path = "\$.visualLayers.$key"
            val obj = el.asObject(path)
            when (val type = obj.reqString("type", path)) {
                "solid" -> result[key] = VisualLayerDef.Solid(obj.reqString("color", path))
                "parallax" -> {
                    val asset = obj.optNotBlankString("asset", path)
                    val placeholder = obj.optNotBlankString("placeholder", path)
                    checkAssetOrPlaceholder(path, asset, placeholder)
                    result[key] = VisualLayerDef.Parallax(asset, placeholder, obj.optFloat("parallax", path) ?: 0.3f)
                }
                "overlay" -> {
                    val asset = obj.optNotBlankString("asset", path)
                    val placeholder = obj.optNotBlankString("placeholder", path)
                    checkAssetOrPlaceholder(path, asset, placeholder)
                    result[key] = VisualLayerDef.Overlay(asset, placeholder)
                }
                else -> throw SceneConfigParseException("$path.type: 未知视觉层类型 '$type'（支持 solid / parallax / overlay）")
            }
        }
        return result
    }

    /** 视觉层必须真实素材与显式开发占位二选一，不允许两者皆有或皆无 */
    private fun checkAssetOrPlaceholder(path: String, asset: String?, placeholder: String?) {
        if (asset != null && placeholder != null) {
            throw SceneConfigParseException("$path: asset 与 placeholder 互斥，占位必须显式且唯一")
        }
        if (asset == null && placeholder == null) {
            throw SceneConfigParseException("$path: 需要 asset 或显式 placeholder，不能两者皆无")
        }
    }

    private fun parseChannel(raw: String, index: Int): PhaseChannel =
        when (raw) {
            "audio" -> PhaseChannel.AUDIO
            "visual" -> PhaseChannel.VISUAL
            "haptic" -> PhaseChannel.HAPTIC
            else -> throw SceneConfigParseException("\$.phases[$index].channel: 未知通道 '$raw'（支持 audio / visual / haptic）")
        }

    private fun parseTerrainKind(raw: String, index: Int): TerrainKind =
        when (raw) {
            "flat" -> TerrainKind.FLAT
            "slope_up" -> TerrainKind.SLOPE_UP
            "slope_down" -> TerrainKind.SLOPE_DOWN
            "gap_hop" -> TerrainKind.GAP_HOP
            "uneven" -> TerrainKind.UNEVEN
            else -> throw SceneConfigParseException("\$.pathProfile.segments[$index].kind: 未知地形 '$raw'（支持 flat / slope_up / slope_down / gap_hop / uneven）")
        }

    // ---- 带路径的基础提取（严格类型：缺失/null/类型冒充分别诊断）----

    private fun JsonObject.has(key: String): Boolean = get(key) != null && get(key) !is JsonNull

    private fun JsonElement.asObject(path: String): JsonObject =
        this as? JsonObject ?: throw SceneConfigParseException("$path 必须是对象")

    private fun JsonElement.describeKind(): String = when (this) {
        is JsonNull -> "null"
        is JsonPrimitive -> when {
            isString -> "字符串 '$content'"
            content == "true" || content == "false" -> "布尔值 $content"
            else -> "数值 $content"
        }
        is JsonArray -> "数组"
        is JsonObject -> "对象"
    }

    /**
     * 数值字段：只接受 JSON number（字符串/布尔/对象/数组冒充一律拒绝），且必须有限
     * （NaN / Infinity / 1e999 溢出均拒绝）。
     */
    private fun JsonObject.reqFiniteNumber(key: String, path: String): Double {
        val el = get(key) ?: throw SceneConfigParseException("$path.$key 缺失")
        if (el !is JsonPrimitive || el.isString) {
            throw SceneConfigParseException("$path.$key 必须是数值，实际为${el.describeKind()}")
        }
        val d = el.content.toDoubleOrNull()
        if (d == null || !d.isFinite()) {
            throw SceneConfigParseException("$path.$key 必须是有限数值，实际为 '${el.content}'")
        }
        return d
    }

    private fun JsonObject.reqInt(key: String, path: String): Int {
        val d = reqFiniteNumber(key, path)
        if (d != kotlin.math.floor(d) || d < Int.MIN_VALUE.toDouble() || d > Int.MAX_VALUE.toDouble()) {
            throw SceneConfigParseException("$path.$key 必须是整数，实际为 '$d'")
        }
        return d.toInt()
    }

    private fun JsonObject.optInt(key: String, path: String): Int? {
        if (!has(key)) return null
        return reqInt(key, path)
    }

    private fun JsonObject.optFloat(key: String, path: String): Float? {
        if (!has(key)) return null
        return reqFloat(key, path)
    }

    private fun JsonObject.reqFloat(key: String, path: String): Float {
        val d = reqFiniteNumber(key, path)
        if (d > Float.MAX_VALUE.toDouble() || d < -Float.MAX_VALUE.toDouble()) {
            throw SceneConfigParseException("$path.$key 超出 Float 表示范围，实际为 '$d'")
        }
        return d.toFloat()
    }

    /** 字符串字段：只接受 JSON string（数字/布尔冒充拒绝） */
    private fun JsonObject.reqStringElement(key: String, path: String): String {
        val el = get(key) ?: throw SceneConfigParseException("$path.$key 缺失")
        if (el !is JsonPrimitive || !el.isString) {
            throw SceneConfigParseException("$path.$key 必须是字符串，实际为${el.describeKind()}")
        }
        return el.content
    }

    private fun JsonObject.reqString(key: String, path: String): String {
        val value = reqStringElement(key, path).trim()
        if (value.isEmpty()) throw SceneConfigParseException("$path.$key 缺失或为空白字符串")
        return value
    }

    private fun JsonObject.optNotBlankString(key: String, path: String): String? {
        if (!has(key)) return null
        return reqStringElement(key, path).trim().ifEmpty { null }
    }

    private fun JsonObject.reqArray(key: String, path: String): JsonArray =
        get(key) as? JsonArray ?: throw SceneConfigParseException("$path.$key 必须是数组")

    private fun JsonObject.reqObject(key: String, path: String): JsonObject =
        get(key) as? JsonObject ?: throw SceneConfigParseException("$path.$key 必须是对象")
}
