package com.sensewalk.app.ui.session

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import com.sensewalk.app.domain.phase.SensoryState
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.TerrainKind
import com.sensewalk.app.domain.scene.VisualLayerDef
import com.sensewalk.app.domain.walk.TerrainMotor
import com.sensewalk.app.domain.walk.VirtualWalkController
import kotlinx.coroutines.launch
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.random.Random

/** 已交付的真实视觉层（asset 路径 + 视差因子；overlay 为 0） */
data class ForestImageLayer(val assetPath: String, val parallax: Float) {
    companion object {
        /** 从场景配置提取带 asset 的层；placeholder/solid 层不在列，保持程序降级 */
        fun fromConfig(config: SceneConfig): Map<String, ForestImageLayer> = buildMap {
            config.visualLayers.forEach { (id, def) ->
                val asset = when (def) {
                    is VisualLayerDef.Parallax -> def.asset
                    is VisualLayerDef.Overlay -> def.asset
                    is VisualLayerDef.Solid -> null
                }
                if (asset != null) {
                    put(id, ForestImageLayer(asset, (def as? VisualLayerDef.Parallax)?.parallax ?: 0f))
                }
            }
        }
    }
}

private val EMPTY_SENSORY = SensoryState(emptyMap(), emptyMap(), emptyList())

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
 * 读取与加载（SW-019）：
 * - [walk] 是快照提供者，只在 Canvas 绘制期调用——每帧快照变化只触发本层重绘，
 *   不重组任何上层文字/弹框/操作容器；
 * - 图层位图在 IO 线程异步解码并按层就绪逐个发布（[ForestLayerImages]）；
 *   未就绪前该层走程序降级，就绪与否不影响可见性——可见性仍由 opacity 门控，
 *   图片晚到不会提前揭示；场景/层/尺寸键变化即丢弃旧请求结果，不串场景。
 *
 * 图片层已知限制（待素材方提供可平铺版本后完善）：单图非无缝，
 * 视差滑动范围钳制在图片超出屏幕的宽度内，滑满后保持静态。
 */
@Composable
fun ForestShell(
    walk: () -> VirtualWalkController.Snapshot?,
    reduceMotion: Boolean,
    modifier: Modifier = Modifier,
    imageLayers: Map<String, ForestImageLayer> = emptyMap(),
    /** 场景标识（SW-016）：驱动色板与层降级分派；缺省森林保持既有表现 */
    sceneId: String = "forest",
) {
    val palette = ScenePalette.of(sceneId)
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
    val context = LocalContext.current

    BoxWithConstraints(modifier.fillMaxSize()) {
        // cover 按高度铺满，目标高度决定采样率；无界约束按原图采样
        val targetHeightPx = if (constraints.hasBoundedHeight) constraints.maxHeight else 0
        // 真实图层：IO 线程异步解码，按层就绪逐个发布；remember 以场景/层/尺寸为键，
        // 键变化即重建空 State 并取消旧加载，旧场景/旧尺寸的层不残留
        val layerBitmaps = remember(sceneId, imageLayers, targetHeightPx) {
            mutableStateOf<Map<String, ImageBitmap>>(emptyMap())
        }
        LaunchedEffect(sceneId, imageLayers, targetHeightPx) {
            for ((layerId, spec) in imageLayers) {
                launch {
                    val bitmap = ForestLayerImages.load(context, sceneId, spec.assetPath, targetHeightPx)
                    if (bitmap != null) layerBitmaps.value = layerBitmaps.value + (layerId to bitmap)
                }
            }
        }

        Canvas(Modifier.fillMaxSize()) {
            // 高频状态只在绘制期读取
            val snap = walk()
            val sensory = snap?.sensory ?: EMPTY_SENSORY
            val sPos = snap?.sPos ?: 0f
            val velocity = snap?.velocity ?: 0f
            val terrain = snap?.terrain ?: TerrainKind.FLAT
            val gait = snap?.gait ?: TerrainMotor.Gait.IDLE
            val bitmaps = layerBitmaps.value

            fun a(layer: String): Float = sensory.visualOpacities[layer] ?: 0f
            fun imageParallaxPx(layerId: String): Float {
                val spec = imageLayers[layerId] ?: return 0f
                return if (spec.parallax > 0f) parallaxOffset(sPos, spec.parallax, reduceMotion) else 0f
            }

            // 1. void 黑幕（起点即黑；其他层长出后仍然作为底色）
            drawRect(palette.voidColor)

            // 2. tree_outline 远景树冠轮廓线（真实图层；无图回退程序剪影）
            val outlineAlpha = a("tree_outline")
            if (outlineAlpha > 0.01f) {
                val bitmap = bitmaps["tree_outline"]
                if (bitmap != null) {
                    drawImageLayer(bitmap, outlineAlpha, imageParallaxPx("tree_outline"))
                } else {
                    drawTreeline(outlineTrees, outlineAlpha, parallaxOffset(sPos, 0.3f, reduceMotion), size)
                }
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

            // 4. leaf_path 落叶与路径细节（真实图层；无图回退程序近景）
            val pathAlpha = a("leaf_path")
            if (pathAlpha > 0.01f) {
                val bitmap = bitmaps["leaf_path"]
                if (bitmap != null) {
                    drawImageLayer(bitmap, pathAlpha, imageParallaxPx("leaf_path"))
                } else {
                    drawLeafGround(leaves, pathAlpha, parallaxOffset(sPos, 0.6f, reduceMotion), size)
                }
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

            // 7. 非森林专用层（SW-016 雨林五层等）：真实图优先，无图走**通用程序降级**
            //    （类型驱动：overlay 柔光带 / parallax 视差剪影带；米数纯函数、停走冻结不变）
            for ((layerId, alpha) in sensory.visualOpacities) {
                if (layerId == "void") continue
                if (layerId in FOREST_SPECIFIC_LAYERS) continue
                if (alpha <= 0.01f) continue
                val bitmap = bitmaps[layerId]
                val spec = imageLayers[layerId]
                if (bitmap != null) {
                    drawImageLayer(bitmap, alpha, spec?.parallax?.let { parallaxOffset(sPos, it, reduceMotion) } ?: 0f)
                } else {
                    drawGenericLayerFallback(layerId, alpha, spec?.parallax ?: 0f, sPos, reduceMotion, size, palette)
                }
            }

            // 8. 旅人剪影（姿态：静止/行走/上坡攀爬；交付图待重做，保持程序绘制）
            drawTraveler(sPos, velocity, terrain, reduceMotion, gait, palette.traveler, size)
        }
    }
}

/** 森林专用层（既有批准降级绘制逐一保留；这些层不再走 SW-016 通用绘制） */
private val FOREST_SPECIFIC_LAYERS = setOf("tree_outline", "tree_trunks", "leaf_path", "light_shows", "clearing")

/** 通用程序降级（SW-016）：overlay=柔和光带；parallax=竖向剪影带（带固定种子，会话内稳定） */
private fun DrawScope.drawGenericLayerFallback(
    layerId: String,
    alpha: Float,
    parallaxFactor: Float,
    sPos: Float,
    reduceMotion: Boolean,
    size: Size,
    palette: ScenePalette = ScenePalette.FOREST,
) {
    val seed = layerId.hashCode()
    val rng = kotlin.random.Random(seed)
    if (parallaxFactor > 0f) {
        // 剪影带：若干竖条代表树干/藤蔓，随 sPos 视差横移（有限视差；reduceMotion 冻结）
        val offset = if (reduceMotion) 0f else (sPos * parallaxFactor * 6f) % (size.width / 3f)
        val bands = 6 + seed % 4
        repeat(bands) { i ->
            val x = ((i * size.width / bands + offset) % (size.width + 120f)) - 60f
            val w = 24f + rng.nextFloat() * 40f
            drawRect(
                color = palette.silhouetteMid.copy(alpha = alpha * 0.5f),
                topLeft = androidx.compose.ui.geometry.Offset(x, size.height * 0.25f),
                size = Size(w, size.height * 0.62f),
            )
        }
    } else {
        // 柔光带：上部光晕（mist/distant_glow/glade 语义），中下部留白（触控保护区）
        drawRect(
            color = palette.glow.copy(alpha = alpha * 0.16f),
            topLeft = androidx.compose.ui.geometry.Offset(0f, 0f),
            size = Size(size.width, size.height * 0.55f),
        )
        val cx = size.width * (0.35f + (seed % 30) / 100f)
        drawCircle(
            color = palette.glow.copy(alpha = alpha * 0.22f),
            radius = size.width * 0.42f,
            center = androidx.compose.ui.geometry.Offset(cx, size.height * 0.34f),
        )
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
    gait: com.sensewalk.app.domain.walk.TerrainMotor.Gait,
    travelerColor: Color,
    size: Size,
) {
    val cx = size.width * 0.34f
    val groundY = size.height * 0.865f
    val moving = velocity > 0.05f
    val stridePhase = (sPos / 0.7f) * (2f * Math.PI).toFloat()
    // hop：跳跃腾空（语义必要动作，reduceMotion 只压小幅度不抹除）
    // tense：站稳微蹲稳住（不做抖动）
    val hopLift = when {
        gait == com.sensewalk.app.domain.walk.TerrainMotor.Gait.HOP ->
            if (reduceMotion) 10f else 26f
        else -> 0f
    }
    val tenseDuck = if (gait == com.sensewalk.app.domain.walk.TerrainMotor.Gait.TENSE) 6f else 0f
    val bob = if (!reduceMotion && moving && hopLift == 0f) sin(stridePhase) * 5f else 0f
    val tilt = if (terrain == TerrainKind.SLOPE_UP) -10f else 0f

    rotate(degrees = tilt, pivot = Offset(cx, groundY)) {
        val bodyBottom = groundY - 14f + bob - hopLift + tenseDuck
        val bodyTop = groundY - 74f + bob - hopLift + tenseDuck
        // 腿：行走交替；跳跃收腿并拢；站稳外撑
        val legSpread = when {
            hopLift > 0f -> 0f
            gait == com.sensewalk.app.domain.walk.TerrainMotor.Gait.TENSE -> 8f
            moving && !reduceMotion -> sin(stridePhase) * 10f
            else -> 4f
        }
        // 跳跃时腿离地（与身体一致抬高）
        val footY = groundY - hopLift
        drawLine(
            travelerColor,
            start = Offset(cx - 2f, bodyBottom),
            end = Offset(cx - 6f - legSpread, footY),
            strokeWidth = 6f,
        )
        drawLine(
            travelerColor,
            start = Offset(cx + 2f, bodyBottom),
            end = Offset(cx + 6f + legSpread, footY),
            strokeWidth = 6f,
        )
        // 身体
        drawRoundRect(
            travelerColor,
            topLeft = Offset(cx - 10f, bodyTop),
            size = Size(20f, bodyBottom - bodyTop),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(10f),
        )
        // 头
        drawCircle(travelerColor, radius = 9f, center = Offset(cx, bodyTop - 12f))
        // 攀爬时前倾的手臂
        if (terrain == TerrainKind.SLOPE_UP) {
            drawLine(
                travelerColor,
                start = Offset(cx + 6f, bodyTop + 18f),
                end = Offset(cx + 18f, bodyTop + 2f),
                strokeWidth = 5f,
            )
        }
    }
}
