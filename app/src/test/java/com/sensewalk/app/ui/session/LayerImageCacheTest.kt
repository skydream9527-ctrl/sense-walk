package com.sensewalk.app.ui.session

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
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNotSame
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Test
import java.util.concurrent.atomic.AtomicInteger

/**
 * SW-019 #1：有界图层缓存的采样选择、single-flight、LRU、失败回退与场景隔离。
 * V 用轻量假值代替 ImageBitmap；门控用 CompletableDeferred，不依赖调度时机。
 */
class LayerImageCacheTest {

    private data class Fake(val name: String, val bytes: Long)

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    @After
    fun tearDown() {
        scope.cancel()
    }

    @Test
    fun sampleSizeNeverUpscalesAndPicksLargestPowerOfTwoThatStillCovers() {
        // 森林素材 768×1376 在常见手机高度上按原图采样，放大交给绘制期
        assertEquals(1, layerSampleSize(1376, 2400))
        assertEquals(1, layerSampleSize(1376, 1376))
        assertEquals(1, layerSampleSize(1376, 1280))
        // 目标够小才降采样：取仍能覆盖目标高度的最大 2 的幂
        assertEquals(2, layerSampleSize(1376, 688))
        assertEquals(2, layerSampleSize(1376, 400))
        assertEquals(4, layerSampleSize(1376, 344))
        // 无效尺寸一律原图
        assertEquals(1, layerSampleSize(1376, 0))
        assertEquals(1, layerSampleSize(0, 1000))
    }

    @Test
    fun concurrentRequestsForSameKeyDecodeOnce() = runBlocking {
        val calls = AtomicInteger()
        val started = CompletableDeferred<Unit>()
        val gate = CompletableDeferred<Unit>()
        val cache = LayerImageCache<Fake>(budgetBytes = 1_000, scope = scope, sizeOf = { it.bytes }) { key ->
            calls.incrementAndGet()
            started.complete(Unit)
            gate.await()
            Fake(key.assetPath, 100)
        }
        val key = LayerImageKey("forest", "visual/a.webp", 1)

        val waiters = List(3) { async(Dispatchers.Default) { cache.get(key) } }
        started.await()
        gate.complete(Unit)

        val results = waiters.awaitAll()
        assertEquals(1, calls.get())
        results.forEach { assertSame(results[0], it) }
        assertEquals(1, cache.entryCount)
        assertEquals(100L, cache.sizeBytes)
    }

    @Test
    fun sameAssetUnderDifferentScenesAreSeparateEntries() = runBlocking {
        val cache = LayerImageCache<Fake>(budgetBytes = 1_000, scope = scope, sizeOf = { it.bytes }) { key ->
            Fake("${key.sceneId}:${key.assetPath}", 10)
        }

        val forest = cache.get(LayerImageKey("forest", "visual/x.webp", 1))!!
        val rainforest = cache.get(LayerImageKey("rainforest", "visual/x.webp", 1))!!

        assertNotSame(forest, rainforest)
        assertEquals("forest:visual/x.webp", forest.name)
        assertEquals("rainforest:visual/x.webp", rainforest.name)
        assertEquals(2, cache.entryCount)
        assertSame(forest, cache.peek(LayerImageKey("forest", "visual/x.webp", 1)))
    }

    @Test
    fun sameAssetUnderDifferentSampleSizesAreSeparateEntries() = runBlocking {
        val cache = LayerImageCache<Fake>(budgetBytes = 1_000, scope = scope, sizeOf = { it.bytes }) { key ->
            Fake("${key.assetPath}@${key.sampleSize}", 10)
        }
        val full = cache.get(LayerImageKey("forest", "visual/x.webp", 1))!!
        val half = cache.get(LayerImageKey("forest", "visual/x.webp", 2))!!
        assertNotSame(full, half)
        assertEquals(2, cache.entryCount)
    }

    @Test
    fun evictsLeastRecentlyUsedWhenOverBudget() = runBlocking {
        val cache = LayerImageCache<Fake>(budgetBytes = 100, scope = scope, sizeOf = { it.bytes }) { key ->
            Fake(key.assetPath, key.assetPath.substringAfter('@').toLong())
        }
        val a = LayerImageKey("s", "a@60", 1)
        val b = LayerImageKey("s", "b@30", 1)
        val c = LayerImageKey("s", "c@30", 1)

        cache.get(a)
        cache.get(b)
        assertEquals(90L, cache.sizeBytes)

        cache.peek(a) // 触达 a，b 成为最久未用
        cache.get(c) // 120 > 100 → 淘汰 b

        assertNull(cache.peek(b))
        assertNotNull(cache.peek(a))
        assertNotNull(cache.peek(c))
        assertEquals(90L, cache.sizeBytes)
        assertEquals(2, cache.entryCount)
    }

    @Test
    fun oversizedValueIsReturnedButNotCached() = runBlocking {
        val cache = LayerImageCache<Fake>(budgetBytes = 50, scope = scope, sizeOf = { it.bytes }) { Fake("big", 80) }
        assertNotNull(cache.get(LayerImageKey("s", "big", 1)))
        assertEquals(0, cache.entryCount)
        assertEquals(0L, cache.sizeBytes)
    }

    @Test
    fun failedDecodeIsNotCachedAndRetriesOnNextRequest() = runBlocking {
        val calls = AtomicInteger()
        val cache = LayerImageCache<Fake>(budgetBytes = 1_000, scope = scope, sizeOf = { it.bytes }) { key ->
            if (calls.incrementAndGet() == 1) null else Fake(key.assetPath, 10)
        }
        val key = LayerImageKey("s", "a", 1)

        assertNull("首次解码失败返回 null（调用方走程序降级）", cache.get(key))
        assertEquals(0, cache.entryCount)

        assertNotNull(cache.get(key))
        assertEquals(2, calls.get())
        assertEquals(1, cache.entryCount)
    }

    @Test
    fun decodeExceptionYieldsNullWithoutCaching() = runBlocking {
        val calls = AtomicInteger()
        val cache = LayerImageCache<Fake>(budgetBytes = 1_000, scope = scope, sizeOf = { it.bytes }) { key ->
            if (calls.incrementAndGet() == 1) throw IllegalStateException("corrupt") else Fake(key.assetPath, 10)
        }
        val key = LayerImageKey("s", "a", 1)
        assertNull(cache.get(key))
        assertEquals(0, cache.entryCount)
        assertNotNull(cache.get(key))
        assertEquals(2, calls.get())
    }

    @Test
    fun cancellingWaiterKeepsDecodeAndCachesResult() = runBlocking {
        val calls = AtomicInteger()
        val started = CompletableDeferred<Unit>()
        val gate = CompletableDeferred<Unit>()
        val cache = LayerImageCache<Fake>(budgetBytes = 1_000, scope = scope, sizeOf = { it.bytes }) { key ->
            calls.incrementAndGet()
            started.complete(Unit)
            gate.await()
            Fake(key.assetPath, 10)
        }
        val key = LayerImageKey("forest", "visual/a.webp", 1)

        val waiter = launch(Dispatchers.Default) { cache.get(key) }
        started.await()
        waiter.cancelAndJoin()
        assertNull("等待方取消时解码仍在进行", cache.peek(key))

        gate.complete(Unit)
        assertNotNull(cache.get(key))
        assertEquals("等待方取消不触发第二次解码", 1, calls.get())
        assertEquals(1, cache.entryCount)
    }

    @Test
    fun clearDropsEntriesAndBytes() = runBlocking {
        val cache = LayerImageCache<Fake>(budgetBytes = 1_000, scope = scope, sizeOf = { it.bytes }) { key ->
            Fake(key.assetPath, 10)
        }
        cache.get(LayerImageKey("s", "a", 1))
        cache.get(LayerImageKey("s", "b", 1))
        assertEquals(2, cache.entryCount)

        cache.clear()
        assertEquals(0, cache.entryCount)
        assertEquals(0L, cache.sizeBytes)
        assertNull(cache.peek(LayerImageKey("s", "a", 1)))
    }
}
