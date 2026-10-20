package com.sensewalk.app.data

import com.sensewalk.app.domain.scene.SceneLoadState
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.cancel
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.atomic.AtomicInteger

/**
 * SW-019 #2：进程级目录缓存的竞态/取消/失败重试语义。
 * 全部用 CompletableDeferred 门控排序，不依赖 sleep 或调度时机。
 */
class SceneCatalogCacheTest {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    @After
    fun tearDown() {
        scope.cancel()
    }

    @Test
    fun concurrentFirstRequestsShareOneLoad() = runBlocking {
        val calls = AtomicInteger()
        val started = CompletableDeferred<Unit>()
        val gate = CompletableDeferred<Unit>()
        val ready = SceneLoadState.Ready(emptyList())
        val cache = SceneCatalogCache(scope) {
            calls.incrementAndGet()
            started.complete(Unit)
            gate.await()
            ready
        }

        val waiters = List(4) { async(Dispatchers.Default) { cache.load() } }
        started.await()
        assertEquals(1, calls.get())
        gate.complete(Unit)

        waiters.awaitAll().forEach { assertSame(ready, it) }
        assertEquals("并发首次请求只加载一次", 1, calls.get())
        assertSame(ready, cache.peek())
    }

    @Test
    fun errorIsNotCachedAndNextLoadRetries() = runBlocking {
        val calls = AtomicInteger()
        val error = SceneLoadState.Error(listOf("场景目录为空"))
        val ready = SceneLoadState.Ready(emptyList())
        val cache = SceneCatalogCache(scope) { if (calls.incrementAndGet() == 1) error else ready }

        assertSame(error, cache.load())
        assertNull("失败不得被缓存为已就绪", cache.peek())

        assertSame(ready, cache.load())
        assertEquals(2, calls.get())
        assertSame(ready, cache.peek())

        assertSame(ready, cache.load())
        assertEquals("就绪后不再重复加载", 2, calls.get())
    }

    @Test
    fun loaderExceptionBecomesErrorAndIsNotCached() = runBlocking {
        val calls = AtomicInteger()
        val ready = SceneLoadState.Ready(emptyList())
        val cache = SceneCatalogCache(scope) {
            if (calls.incrementAndGet() == 1) throw IllegalStateException("assets unavailable") else ready
        }

        val first = cache.load()
        assertTrue(first is SceneLoadState.Error)
        assertTrue((first as SceneLoadState.Error).diagnostics.single().contains("assets unavailable"))
        assertNull(cache.peek())

        assertSame(ready, cache.load())
        assertEquals(2, calls.get())
    }

    @Test
    fun cancellingWaiterKeepsLoadRunningAndCachesResult() = runBlocking {
        val calls = AtomicInteger()
        val started = CompletableDeferred<Unit>()
        val gate = CompletableDeferred<Unit>()
        val ready = SceneLoadState.Ready(emptyList())
        val cache = SceneCatalogCache(scope) {
            calls.incrementAndGet()
            started.complete(Unit)
            gate.await()
            ready
        }

        val waiter = launch(Dispatchers.Default) { cache.load() }
        started.await()
        waiter.cancelAndJoin()
        assertNull("等待方取消时加载仍在进行，尚未就绪", cache.peek())

        gate.complete(Unit)
        assertSame(ready, cache.load())
        assertEquals("等待方取消不触发第二次加载", 1, calls.get())
        assertSame(ready, cache.peek())
    }

    @Test
    fun reloadBypassesCacheAndReplacesReady() = runBlocking {
        val calls = AtomicInteger()
        val first = SceneLoadState.Ready(emptyList())
        val second = SceneLoadState.Ready(emptyList())
        val cache = SceneCatalogCache(scope) { if (calls.incrementAndGet() == 1) first else second }

        assertSame(first, cache.load())
        assertSame(first, cache.load())
        assertEquals(1, calls.get())

        assertSame(second, cache.reload())
        assertEquals(2, calls.get())
        assertSame(second, cache.peek())
        assertSame(second, cache.load())
    }

    @Test
    fun reloadErrorKeepsPreviousReadyAvailable() = runBlocking {
        val calls = AtomicInteger()
        val ready = SceneLoadState.Ready(emptyList())
        val error = SceneLoadState.Error(listOf("transient"))
        val cache = SceneCatalogCache(scope) { if (calls.incrementAndGet() == 1) ready else error }

        assertSame(ready, cache.load())
        assertSame(error, cache.reload())
        assertSame("重试失败不覆盖已有有效目录", ready, cache.peek())
    }
}
