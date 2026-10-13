package com.sensewalk.app.ui.session

import android.graphics.BitmapFactory
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import com.sensewalk.app.domain.phase.SensoryState
import com.sensewalk.app.domain.scene.TerrainKind
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.random.Random

/** 已交付的真实视觉层（asset 路径 + 视差因子；overlay 为 0） */
data class ForestImageLayer(val assetPath: String, val parallax: Float)

/**
 * 森林 VisualShell：分层景色（T04 程序剪影 + T05 真实图层接入）。
 *
 * 规则（不可违反）：
 * - 每层透明度严格取自 [SensoryState.visualOpacities]（米数的纯函数），
 *   米数不变 → 揭示程度不变；不使用任何时间驱动的展开；
 * - 起点是黑幕（void 层），未解锁层完全不绘制；
 * - 配置带 `asset` 的层（MiniMax 交付且验收合格）渲染真实图片；
 *   仍为 `placeholder` 的层保持程序剪影/渐变降级（ASSETS.md 记录状态）；
 * - 视差按 sPos × parallax 横移（图片层在可用溢出范围内滑动）；
 *   reduceMotion 时冻结视差与角色起伏。
 *
 * 图片层已知限制（待素材方提供可平铺版本后完善）：单图非无缝，
 * 视差滑动范围钳制在图片超出屏幕的宽度内，滑满后保持静态。
 */
@Composable
fun ForestShell(
    sensory: SensoryState,
    sPos: Float,
    velocity: Float,
    terrain: TerrainKind,
    reduceMotion: Boolean,
    imageLayers: Map<String, ForestImageLayer> = emptyMap(),
    modifier: Modifier = Modifier,
) {
    // 固定种子生成剪影特征，保证同一会话内景致稳定
    val outlineTrees = remember {
        Random(42).let { r -> List(24) { Triple(r.nextFloat(), 0.5f + r.nextFloat() * 0.5f, 0.6f + r.nextFloat() * 0.4f) } }
    }
    val trunks = remember {
        Random(7).let { r -> List(14) { Triple(r.nextFloat(), 0.6f + r.nextFloat() * 0.4f, r.nextFloat()) } }
    }
    val leaves = remember {
        Random(11).let { r -> List(40) { Triple(r.nextFloat(), r.nextFloat(), r.nextFloat()) } }
    }

    // 真实图层：从 assets 解码一次；解码失败自动回退程序渲染
    val context = LocalContext.current
    val bitmaps = remember(imageLayers) {
        imageLayers.mapValues { (_, spec) ->
            runCatching {
                context.assets.open(spec.assetPath).use { input ->
                    BitmapFactory.decodeStream(input)?.asImageBitmap()
                }
            }.getOrNull()
        }
    }

    Canvas(modifier.fillMaxSize()) {
        fun a(layer: String): Float = sensory.visualOpacities[layer] ?: 0f
        fun imageParallaxPx(layerId: String): Float {
            val spec = imageLayers[layerId] ?: return 0f
            return if (spec.parallax > 0f) parallaxOffset(sPos, spec.parallax, reduceMotion) else 0f
        }

        // 1. void 黑幕（起点即黑；其他层长出后仍然作为底色）
        drawRect(VoidColor)

        // 2. tree_outline 远景树冠轮廓线（交付图过稀，保持程序剪影）
        val outlineAlpha = a("tree_outline")
        if (outlineAlpha > 0.01f) {
            drawTreeline(outlineTrees, outlineAlpha, parallaxOffset(sPos, 0.3f, reduceMotion), size)
        }

        // 3. tree_trunks 树干与林间光（真实图层；无图回退程序剪影）
        val trunkAlpha = a("tree_trunks")
        if (trunkAlpha > 0.01f) {
            val bitmap = bitmaps["tree_trunks"]
            if (bitmap != null) {
                drawImageLayer(bitmap, trunkAlpha, imageParallaxPx("tree_trunks"))
            } else {
                drawTrunks(trunks, trunkAlpha, parallaxOffset(sPos, 0.3f, reduceMotion), size)
            }
        }

        // 4. leaf_path 落叶与路径细节（交付图内容溢出，保持程序近景）
        val pathAlpha = a("leaf_path")
        if (pathAlpha > 0.01f) {
            drawLeafGround(leaves, pathAlpha, parallaxOffset(sPos, 0.6f, reduceMotion), size)
        }

        // 5. light_shows 飞鸟剪影与透光光柱（真实图层；无图回退程序绘制）
        val lightAlpha = a("light_shows")
        if (lightAlpha > 0.01f) {
            val bitmap = bitmaps["light_shows"]
            if (bitmap != null) {
                drawImageLayer(bitmap, lightAlpha, 0f)
            } else {
                drawLightShows(lightAlpha, size)
            }
        }

        // 6. clearing 林间空地微光（真实图层；无图回退程序渐变）
        val clearingAlpha = a("clearing")
        if (clearingAlpha > 0.01f) {
            val bitmap = bitmaps["clearing"]
            if (bitmap != null) {
                drawImageLayer(bitmap, clearingAlpha, 0f)
            } else {
                drawClearingGlow(clearingAlpha, size)
            }
        }

        // 7. 旅人剪影（姿态：静止/行走/上坡攀爬；交付图待重做，保持程序绘制）
        drawTraveler(sPos, velocity, terrain, reduceMotion, size)
    }
}

/** 图片层：按高度铺满（cover），在超出屏幕的宽度内做视差滑动 */
private fun DrawScope.drawImageLayer(image: ImageBitmap, alpha: Float, parallaxPx: Float) {
    if (alpha <= 0.01f) return
    val scale = size.height / image.height
    val dstW = image.width * scale
    val overflow = (dstW - size.width).coerceAtLeast(0f)
    val xOffset = -parallaxPx.coerceIn(0f, overflow)
    drawImage(
        image = image,
        srcOffset = IntOffset.Zero,
        srcSize = IntSize(image.width, image.height),
        dstOffset = IntOffset(xOffset.roundToInt(), 0),
        dstSize = IntSize(dstW.roundToInt(), size.height.roundToInt()),
        alpha = alpha.coerceIn(0f, 1f),
    )
}

// 色板（design/01-scenes-terrain/forest.md）
private val VoidColor = Color(0xFF060806)
private val OutlineColor = Color(0xFF1A2820)
private val TrunkColor = Color(0xFF2D4A3E)
private val TrunkLightColor = Color(0xFF8FA87A)
private val LeafColor = Color(0xFF6B8F71)
private val LeafWarmColor = Color(0xFFA89060)
private val GlowColor = Color(0xFFA8C5A0)
private val TravelerColor = Color(0xFF7A857C)

/** 视觉比例尺：1 m ≈ 6 px（视差远层实际移动 pxPerM × parallax） */
private const val PX_PER_METER = 6f

private fun parallaxOffset(sPos: Float, factor: Float, reduceMotion: Boolean): Float =
    if (reduceMotion) 0f else sPos * factor * PX_PER_METER

private fun DrawScope.drawTreeline(
    trees: List<Triple<Float, Float, Float>>,
    alpha: Float,
    offsetPx: Float,
    size: Size,
) {
    val horizon = size.height * 0.52f
    val pattern = size.width + 200f
    trees.forEach { (seedX, heightFactor, widthFactor) ->
        val x = ((seedX * pattern - offsetPx) % pattern + pattern) % pattern - 100f
        val w = 60f * widthFactor
        val h = 90f * heightFactor
        val path = Path().apply {
            moveTo(x - w, horizon)
            lineTo(x, horizon - h)
            lineTo(x + w, horizon)
            close()
        }
        drawPath(path, OutlineColor.copy(alpha = alpha))
    }
}

private fun DrawScope.drawTrunks(
    trunks: List<Triple<Float, Float, Float>>,
    alpha: Float,
    offsetPx: Float,
    size: Size,
) {
    val pattern = size.width + 160f
    trunks.forEach { (seedX, heightFactor, lightSeed) ->
        val x = ((seedX * pattern - offsetPx) % pattern + pattern) % pattern - 80f
        val topY = size.height * 0.10f * (2f - heightFactor)
        val bottomY = size.height * 0.82f
        val trunkW = 26f + 14f * lightSeed
        drawRoundRect(
            color = TrunkColor.copy(alpha = alpha),
            topLeft = Offset(x - trunkW / 2f, topY),
            size = Size(trunkW, bottomY - topY),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(trunkW / 3f),
        )
        // 林间光：亮色竖向细条
        if (lightSeed > 0.45f) {
            drawRect(
                color = TrunkLightColor.copy(alpha = alpha * 0.22f),
                topLeft = Offset(x + trunkW * 0.15f, topY + 40f),
                size = Size(trunkW * 0.28f, (bottomY - topY) * 0.7f),
            )
        }
    }
}

private fun DrawScope.drawLeafGround(
    leaves: List<Triple<Float, Float, Float>>,
    alpha: Float,
    offsetPx: Float,
    size: Size,
) {
    val groundTop = size.height * 0.84f
    drawRect(
        brush = Brush.verticalGradient(
            colors = listOf(
                TrunkColor.copy(alpha = alpha * 0.0f),
                LeafColor.copy(alpha = alpha * 0.28f),
            ),
            startY = groundTop - size.height * 0.08f,
            endY = size.height,
        ),
        topLeft = Offset(0f, groundTop - size.height * 0.08f),
        size = Size(size.width, size.height * 0.16f),
    )
    val pattern = size.width + 60f
    leaves.forEach { (seedX, seedY, warmSeed) ->
        val x = ((seedX * pattern - offsetPx) % pattern + pattern) % pattern - 30f
        val y = groundTop + seedY * (size.height - groundTop) * 0.85f
        val color = if (warmSeed > 0.6f) LeafWarmColor else LeafColor
        drawCircle(color.copy(alpha = alpha * 0.5f), radius = 3f + warmSeed * 3f, center = Offset(x, y))
    }
}

private fun DrawScope.drawLightShows(alpha: Float, size: Size) {
    // 三道斜向光柱
    listOf(0.28f, 0.5f, 0.72f).forEachIndexed { i, xf ->
        val beamW = size.width * 0.09f
        val x = size.width * xf
        rotate(degrees = -14f + i * 6f, pivot = Offset(x, 0f)) {
            drawRect(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        TrunkLightColor.copy(alpha = alpha * 0.16f),
                        Color.Transparent,
                    ),
                    startY = 0f,
                    endY = size.height * 0.85f,
                ),
                topLeft = Offset(x - beamW / 2f, 0f),
                size = Size(beamW, size.height * 0.85f),
            )
        }
    }
    // 两只飞鸟剪影
    listOf(Offset(size.width * 0.62f, size.height * 0.18f), Offset(size.width * 0.7f, size.height * 0.14f))
        .forEach { c ->
            val wing = Path().apply {
                moveTo(c.x - 14f, c.y)
                quadraticBezierTo(c.x - 7f, c.y - 9f, c.x, c.y - 2f)
                quadraticBezierTo(c.x + 7f, c.y - 9f, c.x + 14f, c.y)
            }
            drawPath(wing, TrunkLightColor.copy(alpha = alpha * 0.7f), style = androidx.compose.ui.graphics.drawscope.Stroke(width = 2.5f))
        }
}

private fun DrawScope.drawClearingGlow(alpha: Float, size: Size) {
    drawCircle(
        brush = Brush.radialGradient(
            colors = listOf(
                GlowColor.copy(alpha = alpha * 0.30f),
                Color.Transparent,
            ),
            center = Offset(size.width * 0.68f, size.height * 0.42f),
            radius = size.width * 0.55f,
        ),
        radius = size.width * 0.55f,
        center = Offset(size.width * 0.68f, size.height * 0.42f),
    )
}

/** 旅人剪影：静止/行走/攀爬三姿态；bob 与步幅相位由 sPos 决定 */
private fun DrawScope.drawTraveler(
    sPos: Float,
    velocity: Float,
    terrain: TerrainKind,
    reduceMotion: Boolean,
    size: Size,
) {
    val cx = size.width * 0.34f
    val groundY = size.height * 0.865f
    val moving = velocity > 0.05f
    val stridePhase = (sPos / 0.7f) * (2f * Math.PI).toFloat()
    val bob = if (!reduceMotion && moving) sin(stridePhase) * 5f else 0f
    val tilt = if (terrain == TerrainKind.SLOPE_UP) -10f else 0f

    rotate(degrees = tilt, pivot = Offset(cx, groundY)) {
        val bodyBottom = groundY - 14f + bob
        val bodyTop = groundY - 74f + bob
        // 腿：行走时交替
        val legSpread = if (moving && !reduceMotion) sin(stridePhase) * 10f else 4f
        drawLine(
            TravelerColor,
            start = Offset(cx - 2f, bodyBottom),
            end = Offset(cx - 6f - legSpread, groundY),
            strokeWidth = 6f,
        )
        drawLine(
            TravelerColor,
            start = Offset(cx + 2f, bodyBottom),
            end = Offset(cx + 6f + legSpread, groundY),
            strokeWidth = 6f,
        )
        // 身体
        drawRoundRect(
            TravelerColor,
            topLeft = Offset(cx - 10f, bodyTop),
            size = Size(20f, bodyBottom - bodyTop),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(10f),
        )
        // 头
        drawCircle(TravelerColor, radius = 9f, center = Offset(cx, bodyTop - 12f))
        // 攀爬时前倾的手臂
        if (terrain == TerrainKind.SLOPE_UP) {
            drawLine(
                TravelerColor,
                start = Offset(cx + 6f, bodyTop + 18f),
                end = Offset(cx + 18f, bodyTop + 2f),
                strokeWidth = 5f,
            )
        }
    }
}
