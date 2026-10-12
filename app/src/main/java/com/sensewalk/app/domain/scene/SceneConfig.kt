package com.sensewalk.app.domain.scene

/**
 * SceneConfig schema v2（DEVELOPMENT.md §12.4）。
 *
 * 纯 Kotlin 领域模型：不依赖 Android，可在 JVM 单测中直接解析与校验。
 * 进度真相是距离：所有相位按 [Phase.atMeters] 触发，配置中不存在时间字段。
 */
data class SceneConfig(
    val schemaVersion: Int,
    val id: String,
    val name: String,
    val mood: String? = null,
    val themeColor: String? = null,
    val requiredDistanceMeters: Int,
    val stickCurveId: String = DEFAULT_STICK_CURVE,
    val phases: List<Phase>,
    val pathProfile: PathProfile,
    val layers: Map<String, AudioLayerDef>,
    val visualLayers: Map<String, VisualLayerDef>,
) {
    companion object {
        const val DEFAULT_STICK_CURVE = "comfort_v1"
    }
}

enum class PhaseChannel { AUDIO, VISUAL, HAPTIC }

data class Phase(
    val id: String,
    val atMeters: Int,
    val channel: PhaseChannel,
    /** audio / visual 相位引用的层名；haptic 相位为 null */
    val layer: String? = null,
    /** audio：目标音量 [0,1] */
    val toVolume: Float? = null,
    /** visual：目标不透明度 [0,1] */
    val toOpacity: Float? = null,
    /** audio：按时间淡入时长（ms） */
    val fadeMs: Int? = null,
    /** visual：按路程淡入宽度（m），atMeters + fadeMeters 不得越过终点 */
    val fadeMeters: Int? = null,
    /** haptic：振动模式名（各场景单页定义） */
    val pattern: String? = null,
    /** haptic：每 N 步触发一次，≥ 1 */
    val everyNSteps: Int? = null,
)

/**
 * 音频层定义。真实素材用 file / files；尚缺素材时必须用显式开发占位
 * （[placeholder] 非空），校验器会把占位与真实素材区分开，发布检查不放行占位。
 */
sealed interface AudioLayerDef {
    val placeholder: String?

    /** 脚步一次性音效（4–6 个变体，DEVELOPMENT.md §8.2） */
    data class StepOneShot(val files: List<String>, override val placeholder: String? = null) : AudioLayerDef

    /** 环境 loop */
    data class Loop(val file: String?, override val placeholder: String? = null) : AudioLayerDef
}

/** 视觉层定义。同样区分真实 asset 与显式开发占位。 */
sealed interface VisualLayerDef {
    /** 纯色层（黑幕等），不需要素材 */
    data class Solid(val color: String) : VisualLayerDef {
        override val placeholder: String? = null
    }

    data class Parallax(
        val asset: String? = null,
        override val placeholder: String? = null,
        val parallax: Float = 0.3f,
    ) : VisualLayerDef

    data class Overlay(
        val asset: String? = null,
        override val placeholder: String? = null,
    ) : VisualLayerDef

    val placeholder: String?
}

data class PathProfile(val segments: List<PathSegment>) {
    fun segmentAt(meters: Int): PathSegment? = segments.firstOrNull { meters >= it.from && meters < it.to }
}

enum class TerrainKind { FLAT, SLOPE_UP, SLOPE_DOWN, GAP_HOP, UNEVEN }

data class PathSegment(
    val from: Int,
    val to: Int,
    val kind: TerrainKind,
    /** 坡度，仅 slope_up / slope_down 使用；缺省按 [SceneValidator] 约定 */
    val grade: Float? = null,
)
