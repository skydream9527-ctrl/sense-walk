package com.sensewalk.app.data

import android.content.Context
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.SceneLoadState
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

/**
 * 进程级场景目录入口（SW-019 #2）：首页 VM、虚走会话 VM、实走服务与实走视觉层
 * 共用同一份 [SceneCatalogCache]，不再各自新建 [SceneRepository] 重复读 assets，
 * 也不再在 UI 线程 runBlocking 等待。只持有 applicationContext。
 */
object SceneCatalog {

    @Volatile
    private var cache: SceneCatalogCache? = null

    private fun get(context: Context): SceneCatalogCache =
        cache ?: synchronized(this) {
            cache ?: SceneCatalogCache(
                scope = CoroutineScope(SupervisorJob() + Dispatchers.Default),
                loader = SceneRepository(context.applicationContext)::loadAll,
            ).also { cache = it }
        }

    /** 已就绪直接返回，否则等待唯一一次加载；Error 不缓存 */
    suspend fun load(context: Context): SceneLoadState = get(context).load()

    /** 首页错误态的显式重试：重新走一遍 读取→解析→校验 */
    suspend fun reload(context: Context): SceneLoadState = get(context).reload()

    /** 同步读取已就绪目录（未就绪为 null），供组合期无等待消费 */
    fun peek(context: Context): SceneLoadState.Ready? = get(context).peek()

    fun peekScene(context: Context, sceneId: String): SceneConfig? =
        peek(context)?.scenes?.firstOrNull { it.id == sceneId }
}
