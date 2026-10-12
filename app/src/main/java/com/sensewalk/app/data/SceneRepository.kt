package com.sensewalk.app.data

import android.content.Context
import com.sensewalk.app.domain.scene.Layer
import com.sensewalk.app.domain.scene.Phase
import com.sensewalk.app.domain.scene.Scene
import org.json.JSONObject

/**
 * Loads scene JSON from assets/scenes/.
 */
class SceneRepository(private val context: Context) {

    fun loadAll(): List<Scene> {
        val ids = listOf("forest", "desert", "night_path")
        return ids.mapNotNull { id ->
            runCatching { load(id) }.getOrNull()
        }
    }

    fun load(sceneId: String): Scene {
        val path = "scenes/$sceneId.json"
        val text = context.assets.open(path).bufferedReader().use { it.readText() }
        return parseScene(text)
    }

    companion object {
        fun parseScene(jsonText: String): Scene {
            val root = JSONObject(jsonText)
            val phasesJson = root.getJSONArray("phases")
            val phases = buildList {
                for (i in 0 until phasesJson.length()) {
                    val p = phasesJson.getJSONObject(i)
                    add(
                        Phase(
                            atSec = p.getInt("atSec"),
                            action = p.getString("action"),
                            layer = p.optionalString("layer"),
                            toVolume = if (p.has("toVolume")) p.getDouble("toVolume").toFloat() else null,
                            fadeMs = if (p.has("fadeMs")) p.getInt("fadeMs") else null,
                            pattern = p.optionalString("pattern"),
                            intervalMs = if (p.has("intervalMs")) p.getInt("intervalMs") else null,
                        )
                    )
                }
            }
            val layersObj = root.getJSONObject("layers")
            val layers = buildMap {
                val keys = layersObj.keys()
                while (keys.hasNext()) {
                    val key = keys.next()
                    val layerJson = layersObj.getJSONObject(key)
                    put(
                        key,
                        Layer(
                            file = layerJson.getString("file"),
                            loop = layerJson.optBoolean("loop", true),
                        )
                    )
                }
            }
            return Scene(
                id = root.getString("id"),
                name = root.getString("name"),
                suggestedMinutes = root.getInt("suggestedMinutes"),
                phases = phases,
                layers = layers,
            )
        }

        private fun JSONObject.optionalString(key: String): String? =
            if (has(key) && !isNull(key)) getString(key) else null
    }
}
