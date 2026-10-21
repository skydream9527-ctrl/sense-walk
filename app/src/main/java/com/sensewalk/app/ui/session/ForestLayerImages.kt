package com.sensewalk.app.ui.session

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.graphics.asImageBitmap
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.withContext
import java.util.concurrent.ConcurrentHashMap

/**
 * 进程级图层位图入口（SW-019 #1）：assets 读取与解码全部在 IO 线程，组合期零解码。
 *
 * 预算 [BUDGET_BYTES]：森林五层 768×1376 ARGB_8888 ≈ 21 MiB，32 MiB 可容纳一整个场景
 * 并留换景余量；换景按 LRU 淘汰旧场景层，不会无界增长。
 */
object ForestLayerImages {
    const val BUDGET_BYTES: Long = 32L * 1024 * 1024

    private class SourceBounds(val width: Int, val height: Int)

    @Volatile
    private var cache: LayerImageCache<ImageBitmap>? = null

    /** 素材原始尺寸（只读边界，极小）；读取失败不记录，下次可重试 */
    private val sourceBounds = ConcurrentHashMap<String, SourceBounds>()

    private fun cache(app: Context): LayerImageCache<ImageBitmap> =
        cache ?: synchronized(this) {
            cache ?: LayerImageCache<ImageBitmap>(
                budgetBytes = BUDGET_BYTES,
                scope = CoroutineScope(SupervisorJob() + Dispatchers.IO),
                sizeOf = { it.asAndroidBitmap().allocationByteCount.toLong() },
                decode = { key -> decodeLayer(app, key) },
            ).also { cache = it }
        }

    /**
     * 按目标高度选择采样后解码；返回 null 表示读取/解码失败，调用方回退程序层。
     * 等待方被取消不会中断解码，结果仍进缓存。
     */
    suspend fun load(context: Context, sceneId: String, assetPath: String, targetHeightPx: Int): ImageBitmap? {
        val app = context.applicationContext
        val bounds = sourceBounds[assetPath]
            ?: readBounds(app, assetPath)?.also { sourceBounds[assetPath] = it }
            ?: return null
        val sample = layerSampleSize(bounds.height, targetHeightPx)
        return cache(app).get(LayerImageKey(sceneId, assetPath, sample))
    }

    private suspend fun readBounds(app: Context, assetPath: String): SourceBounds? = withContext(Dispatchers.IO) {
        runCatching {
            val opts = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            app.assets.open(assetPath).use { BitmapFactory.decodeStream(it, null, opts) }
            SourceBounds(opts.outWidth, opts.outHeight).takeIf { it.width > 0 && it.height > 0 }
        }.getOrNull()
    }

    /** 在缓存的 IO scope 内执行；损坏文件/OOM 一律返回 null，不向上抛 */
    private fun decodeLayer(app: Context, key: LayerImageKey): ImageBitmap? = runCatching {
        val opts = BitmapFactory.Options().apply {
            inSampleSize = key.sampleSize
            inPreferredConfig = Bitmap.Config.ARGB_8888
        }
        app.assets.open(key.assetPath).use { BitmapFactory.decodeStream(it, null, opts) }?.asImageBitmap()
    }.getOrNull()
}
