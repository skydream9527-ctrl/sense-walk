package com.sensewalk.app.data

import android.content.Context
import com.sensewalk.app.domain.scene.SceneLoadState
import com.sensewalk.app.domain.scene.SceneLoader
import com.sensewalk.app.domain.scene.SceneSource
import com.sensewalk.app.domain.scene.SceneValidator
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * 场景配置仓库：assets 适配层。
 *
 * 解析与校验在纯 Kotlin 的 [SceneLoader] 中完成（JVM 可测）；
 * 本类只提供 assets 数据源与素材定位器，并在 IO 线程执行读取。
 */
class SceneRepository(context: Context) {

    private val appContext = context.applicationContext

    private val source = object : SceneSource {
        override fun availableSceneIds(): List<String> =
            appContext.assets.list(SCENES_DIR)
                ?.filter { it.endsWith(".json") }
                ?.map { it.removeSuffix(".json") }
                .orEmpty()
                .sorted()

        override fun readScene(sceneId: String): String =
            appContext.assets.open("$SCENES_DIR/$sceneId.json").bufferedReader().use { it.readText() }
    }

    private val assetLocator = SceneValidator.AssetLocator { path ->
        val dir = path.substringBeforeLast('/', "")
        val name = path.substringAfterLast('/', "")
        appContext.assets.list(dir)?.contains(name) == true
    }

    private val loader = SceneLoader(source, assetLocator)

    suspend fun loadAll(): SceneLoadState = withContext(Dispatchers.IO) {
        loader.loadAll()
    }

    private companion object {
        const val SCENES_DIR = "scenes"
    }
}
