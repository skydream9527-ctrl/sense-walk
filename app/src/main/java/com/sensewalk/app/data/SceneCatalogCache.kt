package com.sensewalk.app.data

import com.sensewalk.app.domain.scene.SceneLoadState
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.async

/**
 * 进程级场景目录缓存（SW-019 #2）：纯 Kotlin，不依赖 Android，JVM 可测。
 *
 * - 并发首次请求共享同一次加载（single-flight），assets 只读一遍；
 * - 只记住 [SceneLoadState.Ready]；[SceneLoadState.Error] 原样返回但不缓存，
 *   下一次 [load]/[reload] 会重新加载——失败不会被永久当成成功；
 * - 加载在缓存自己的 [scope] 内执行：等待方被取消只影响等待方，
 *   进行中的加载照常完成并填充缓存，半途取消不会污染状态；
 * - [peek] 同步返回已就绪目录，供组合期零等待消费（未就绪返回 null，由调用方异步 [load]）。
 */
class SceneCatalogCache(
    private val scope: CoroutineScope,
    private val loader: suspend () -> SceneLoadState,
) {
    private val lock = Any()

    @Volatile
    private var ready: SceneLoadState.Ready? = null

    /** 进行中的加载（guarded by [lock]）；完成后由回调自行清除 */
    private var inFlight: Deferred<SceneLoadState>? = null

    fun peek(): SceneLoadState.Ready? = ready

    /** 已就绪直接返回；否则加入进行中的加载或发起唯一一次新加载 */
    suspend fun load(): SceneLoadState = ready ?: startOrJoin(useReady = true).await()

    /** 显式重试：忽略已缓存结果，加入进行中的加载或发起新加载；成功后替换缓存 */
    suspend fun reload(): SceneLoadState = startOrJoin(useReady = false).await()

    private fun startOrJoin(useReady: Boolean): Deferred<SceneLoadState> = synchronized(lock) {
        if (useReady) ready?.let { return CompletableDeferred<SceneLoadState>(it) }
        inFlight?.let { return it }
        // LAZY：先登记再启动，保证完成回调清理时登记已存在（即便 dispatcher 立即执行）
        val deferred = scope.async(start = CoroutineStart.LAZY) { runLoader() }
        inFlight = deferred
        deferred.invokeOnCompletion {
            synchronized(lock) { if (inFlight === deferred) inFlight = null }
        }
        deferred.start()
        deferred
    }

    private suspend fun runLoader(): SceneLoadState {
        val result = try {
            loader()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            SceneLoadState.Error(listOf("场景目录加载异常：${e.message ?: e.javaClass.simpleName}"))
        }
        if (result is SceneLoadState.Ready) ready = result
        return result
    }
}
