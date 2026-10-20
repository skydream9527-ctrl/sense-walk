package com.sensewalk.app.ui.session

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.async

/** 图层位图缓存键：场景 + 素材 + 采样率（同素材不同采样是不同位图；含场景身份杜绝串场景） */
data class LayerImageKey(val sceneId: String, val assetPath: String, val sampleSize: Int)

/**
 * 按目标高度选 `BitmapFactory.inSampleSize`（2 的幂）：取使 srcHeight/sample ≥ targetHeight 的最大 sample。
 * 源图不比目标小时为 1——绝不为大屏预放大，放大交给 drawImage 的 dstSize 在绘制期完成。
 */
fun layerSampleSize(srcHeight: Int, targetHeight: Int): Int {
    if (srcHeight <= 0 || targetHeight <= 0) return 1
    var sample = 1
    while (srcHeight / (sample * 2) >= targetHeight) sample *= 2
    return sample
}

/**
 * 有界图层位图缓存（SW-019 #1）。V 泛型以便 JVM 单测（生产为 ImageBitmap）。
 *
 * - LRU，按字节预算淘汰；单项超预算则只返回不缓存；
 * - 同键并发请求共享一次解码（single-flight），解码在缓存自己的 [scope] 内执行：
 *   等待方取消不取消解码，解码结果仍进入缓存供下次复用；
 * - 解码失败/返回 null 不缓存（下次请求可重试），调用方按程序层降级且仍受原 opacity 门控。
 */
class LayerImageCache<V : Any>(
    private val budgetBytes: Long,
    private val scope: CoroutineScope,
    private val sizeOf: (V) -> Long,
    private val decode: suspend (LayerImageKey) -> V?,
) {
    private val lock = Any()

    /** accessOrder=true：迭代顺序即 LRU → MRU */
    private val entries = LinkedHashMap<LayerImageKey, V>(16, 0.75f, true)
    private var usedBytes = 0L
    private val inFlight = HashMap<LayerImageKey, Deferred<V?>>()

    val sizeBytes: Long get() = synchronized(lock) { usedBytes }
    val entryCount: Int get() = synchronized(lock) { entries.size }

    fun peek(key: LayerImageKey): V? = synchronized(lock) { entries[key] }

    /** 命中直接返回；否则加入进行中的解码或发起唯一一次新解码。失败返回 null。 */
    suspend fun get(key: LayerImageKey): V? = peek(key) ?: startOrJoin(key).await()

    private fun startOrJoin(key: LayerImageKey): Deferred<V?> = synchronized(lock) {
        entries[key]?.let { return CompletableDeferred<V?>(it) }
        inFlight[key]?.let { return it }
        val deferred = scope.async(start = CoroutineStart.LAZY) {
            val value = try {
                decode(key)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                null
            }
            if (value != null) put(key, value)
            value
        }
        inFlight[key] = deferred
        deferred.invokeOnCompletion {
            synchronized(lock) { if (inFlight[key] === deferred) inFlight.remove(key) }
        }
        deferred.start()
        deferred
    }

    private fun put(key: LayerImageKey, value: V) = synchronized(lock) {
        val size = sizeOf(value)
        if (size > budgetBytes) return
        entries.remove(key)?.let { usedBytes -= sizeOf(it) }
        entries[key] = value
        usedBytes += size
        val iterator = entries.entries.iterator()
        while (usedBytes > budgetBytes && iterator.hasNext()) {
            val eldest = iterator.next()
            if (eldest.key == key) continue
            iterator.remove()
            usedBytes -= sizeOf(eldest.value)
        }
    }

    fun clear() = synchronized(lock) {
        entries.clear()
        usedBytes = 0L
    }
}
