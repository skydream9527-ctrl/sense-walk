package com.sensewalk.app.domain.scene

/**
 * 场景数据源抽象：生产实现读 assets，测试注入内存数据。
 * 任何读取失败都抛出，由 [SceneLoader] 转成可解释诊断，不静默吞错。
 */
interface SceneSource {
    fun availableSceneIds(): List<String>
    fun readScene(sceneId: String): String
}

/** 首页可观察的场景加载状态（I06：Loading / Ready / Error，不出现无解释空列表） */
sealed interface SceneLoadState {
    data object Loading : SceneLoadState
    data class Ready(val scenes: List<SceneConfig>) : SceneLoadState
    data class Error(val diagnostics: List<String>) : SceneLoadState
}

/**
 * 读取 → 解析 → 校验 全链路加载器。纯 Kotlin、同步、可 JVM 单测。
 *
 * 任一场景解析或校验失败都会以 [SceneLoadState.Error] 汇总返回，
 * 不静默丢弃场景；全部通过才进入 Ready。
 */
class SceneLoader(
    private val source: SceneSource,
    private val assetLocator: SceneValidator.AssetLocator,
) {

    fun loadAll(policy: SceneValidator.AssetsPolicy = SceneValidator.AssetsPolicy.ALLOW_PLACEHOLDERS): SceneLoadState {
        val diagnostics = mutableListOf<String>()
        val scenes = mutableListOf<SceneConfig>()
        val ids = try {
            source.availableSceneIds()
        } catch (e: Exception) {
            // 目录枚举失败（存储/IO 异常）也要可解释、可重试，不静默变成空列表
            return SceneLoadState.Error(listOf("场景目录读取失败：${e.message ?: e.javaClass.simpleName}"))
        }
        if (ids.isEmpty()) {
            return SceneLoadState.Error(listOf("场景目录为空：没有可加载的 scenes 配置"))
        }

        for (id in ids) {
            try {
                val text = source.readScene(id)
                val config = SceneJsonParser.parse(text)
                val result = SceneValidator.validate(config, assetLocator, policy)
                if (!result.valid) {
                    diagnostics.add("场景 '$id' 校验失败：\n" + result.errors.joinToString("\n") { "  - $it" })
                } else {
                    scenes.add(config)
                }
            } catch (e: SceneConfigParseException) {
                diagnostics.add("场景 '$id' 解析失败：${e.message}")
            } catch (e: Exception) {
                diagnostics.add("场景 '$id' 读取失败：${e.message}")
            }
        }

        // 场景 id 唯一
        scenes.groupBy { it.id }.filterValues { it.size > 1 }.forEach { (id, dup) ->
            diagnostics.add("场景 id 重复: '$id' 出现 ${dup.size} 次")
        }
        if (diagnostics.isNotEmpty()) return SceneLoadState.Error(diagnostics)

        return SceneLoadState.Ready(scenes.sortedBy { it.requiredDistanceMeters })
    }
}
