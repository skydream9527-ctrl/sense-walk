package com.sensewalk.app.domain.scene

/** 校验器/加载器测试共用的可变基准配置（required=1000，全部里程碑齐备） */
object TestScenes {

    const val REQUIRED = 1000

    /** 测试用素材定位器：承认 audio/ 与 visual/ 前缀的引用 */
    val locator = SceneValidator.AssetLocator { it.startsWith("audio/") || it.startsWith("visual/") }

    fun validConfig(
        id: String = "test_scene",
        name: String = "测试场景",
        required: Int = REQUIRED,
        phases: List<Phase> = defaultPhases(),
        segments: List<PathSegment> = defaultSegments(required),
        layers: Map<String, AudioLayerDef> = defaultLayers(),
        visualLayers: Map<String, VisualLayerDef> = defaultVisualLayers(),
    ): SceneConfig = SceneConfig(
        schemaVersion = 2,
        id = id,
        name = name,
        mood = "测试",
        themeColor = "#000000",
        requiredDistanceMeters = required,
        stickCurveId = "comfort_v1",
        phases = phases,
        pathProfile = PathProfile(segments),
        layers = layers,
        visualLayers = visualLayers,
    )

    fun defaultPhases(): List<Phase> = listOf(
        Phase("void", 0, PhaseChannel.VISUAL, layer = "void", toOpacity = 1f),
        Phase("steps", 100, PhaseChannel.AUDIO, layer = "footsteps", toVolume = 0.25f, fadeMs = 8000),
        Phase("outline", 100, PhaseChannel.VISUAL, layer = "outline", toOpacity = 0.6f, fadeMeters = 20),
        Phase("ambience", 300, PhaseChannel.AUDIO, layer = "ambience", toVolume = 0.35f, fadeMs = 12000),
        Phase("main_body", 300, PhaseChannel.VISUAL, layer = "main_body", toOpacity = 0.7f, fadeMeters = 25),
        Phase("haptic", 500, PhaseChannel.HAPTIC, layer = null, pattern = "footstep_soft", everyNSteps = 2),
        Phase("detail", 500, PhaseChannel.VISUAL, layer = "detail", toOpacity = 0.8f, fadeMeters = 25),
        Phase("deep", 750, PhaseChannel.AUDIO, layer = "deep", toVolume = 0.2f, fadeMs = 10000),
        Phase("far_view", 750, PhaseChannel.VISUAL, layer = "far_view", toOpacity = 0.65f, fadeMeters = 30),
        Phase("arrival", 950, PhaseChannel.VISUAL, layer = "arrival", toOpacity = 0.9f, fadeMeters = 30),
    )

    fun defaultSegments(required: Int = REQUIRED): List<PathSegment> =
        listOf(PathSegment(0, required, TerrainKind.FLAT))

    fun defaultLayers(): Map<String, AudioLayerDef> = mapOf(
        "footsteps" to AudioLayerDef.StepOneShot(listOf("audio/test_step_01.ogg", "audio/test_step_02.ogg")),
        "ambience" to AudioLayerDef.Loop("audio/test_ambience.ogg"),
        "deep" to AudioLayerDef.Loop("audio/test_deep.ogg"),
    )

    fun defaultVisualLayers(): Map<String, VisualLayerDef> = mapOf(
        "void" to VisualLayerDef.Solid("#000000"),
        "outline" to VisualLayerDef.Parallax(asset = "visual/test_outline.webp", parallax = 0.3f),
        "main_body" to VisualLayerDef.Parallax(asset = "visual/test_body.webp", parallax = 0.3f),
        "detail" to VisualLayerDef.Parallax(asset = "visual/test_detail.webp", parallax = 0.6f),
        "far_view" to VisualLayerDef.Overlay(asset = "visual/test_far.webp"),
        "arrival" to VisualLayerDef.Overlay(asset = "visual/test_arrival.webp"),
    )

    /** 一份可直接解析的合法 v2 JSON（使用占位素材，不依赖任何文件） */
    const val VALID_JSON = """{
      "schemaVersion": 2,
      "id": "json_scene",
      "name": "JSON 场景",
      "mood": "测试",
      "themeColor": "#101010",
      "requiredDistanceMeters": 1000,
      "phases": [
        { "id": "void", "atMeters": 0, "channel": "visual", "layer": "void", "toOpacity": 1.0 },
        { "id": "steps", "atMeters": 100, "channel": "audio", "layer": "footsteps", "toVolume": 0.25, "fadeMs": 8000 },
        { "id": "outline", "atMeters": 100, "channel": "visual", "layer": "outline", "toOpacity": 0.6, "fadeMeters": 20 },
        { "id": "ambience", "atMeters": 300, "channel": "audio", "layer": "ambience", "toVolume": 0.35, "fadeMs": 12000 },
        { "id": "main_body", "atMeters": 300, "channel": "visual", "layer": "main_body", "toOpacity": 0.7, "fadeMeters": 25 },
        { "id": "haptic", "atMeters": 500, "channel": "haptic", "pattern": "footstep_soft", "everyNSteps": 2 },
        { "id": "detail", "atMeters": 500, "channel": "visual", "layer": "detail", "toOpacity": 0.8, "fadeMeters": 25 },
        { "id": "deep", "atMeters": 750, "channel": "audio", "layer": "deep", "toVolume": 0.2, "fadeMs": 10000 },
        { "id": "far_view", "atMeters": 750, "channel": "visual", "layer": "far_view", "toOpacity": 0.65, "fadeMeters": 30 },
        { "id": "arrival", "atMeters": 950, "channel": "visual", "layer": "arrival", "toOpacity": 0.9, "fadeMeters": 30 }
      ],
      "pathProfile": { "segments": [ { "from": 0, "to": 1000, "kind": "flat" } ] },
      "layers": {
        "footsteps": { "type": "stepOneShot", "placeholder": "dev_tone_variants:test_step" },
        "ambience": { "type": "loop", "placeholder": "dev_tone:test_amb" },
        "deep": { "type": "loop", "placeholder": "dev_tone:test_deep" }
      },
      "visualLayers": {
        "void": { "type": "solid", "color": "#000000" },
        "outline": { "type": "parallax", "placeholder": "dev_silhouette:test_outline", "parallax": 0.3 },
        "main_body": { "type": "parallax", "placeholder": "dev_silhouette:test_body", "parallax": 0.3 },
        "detail": { "type": "parallax", "placeholder": "dev_silhouette:test_detail", "parallax": 0.6 },
        "far_view": { "type": "overlay", "placeholder": "dev_gradient:test_far" },
        "arrival": { "type": "overlay", "placeholder": "dev_gradient:test_arrival" }
      }
    }"""
}
