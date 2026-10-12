package com.sensewalk.app.domain.scene

/**
 * 场景配置校验器（DEVELOPMENT.md §12.4）。
 *
 * 纯 Kotlin，输入 [SceneConfig]，输出错误与开发占位清单；不抛异常。
 * 规则覆盖：数值范围、ID 唯一、相位排序与边界、层引用、视觉淡入不越终点、
 * pathProfile 连续覆盖、前 10% 无 gap_hop、起点黑幕、叙事里程碑覆盖、素材存在性。
 */
object SceneValidator {

    /** 判断配置引用的素材文件是否存在（生产实现查 assets，测试可注入内存表） */
    fun interface AssetLocator {
        fun exists(path: String): Boolean
    }

    /** 素材策略：开发期允许显式占位；发布检查把占位当错误，不放行占位配置 */
    enum class AssetsPolicy { ALLOW_PLACEHOLDERS, REQUIRE_REAL_ASSETS }

    data class ValidationResult(
        val valid: Boolean,
        val errors: List<String>,
        /** 开发占位清单（如 "layers.ambience → dev_tone:forest_insects"）；不算错误，但发布前必须清零 */
        val placeholders: List<String>,
    )

    /** 叙事里程碑（§8.1）：各通道需要覆盖的进度比例，允许 ±5% 偏差 */
    private val AUDIO_MILESTONES = listOf(0.10, 0.30, 0.75)
    private val HAPTIC_MILESTONES = listOf(0.50)
    private val VISUAL_MILESTONES = listOf(0.0, 0.10, 0.30, 0.50, 0.75, 0.95)
    private const val MILESTONE_TOLERANCE = 0.05

    fun validate(
        config: SceneConfig,
        assetLocator: AssetLocator,
        policy: AssetsPolicy = AssetsPolicy.ALLOW_PLACEHOLDERS,
    ): ValidationResult {
        val errors = mutableListOf<String>()
        val placeholders = mutableListOf<String>()

        validateBasics(config, errors)
        validatePhases(config, errors)
        validatePathProfile(config, errors)
        validateMilestones(config, errors)
        validateAssets(config, assetLocator, policy, errors, placeholders)

        return ValidationResult(errors.isEmpty(), errors, placeholders)
    }

    private fun validateBasics(config: SceneConfig, errors: MutableList<String>) {
        if (config.requiredDistanceMeters <= 0) {
            errors.add("requiredDistanceMeters 必须为正，实际为 ${config.requiredDistanceMeters}")
        }
        if (config.id.isBlank()) errors.add("场景 id 不能为空")
        if (config.name.isBlank()) errors.add("场景 name 不能为空")
    }

    private fun validatePhases(config: SceneConfig, errors: MutableList<String>) {
        val phases = config.phases
        if (phases.isEmpty()) {
            errors.add("phases 不能为空")
            return
        }

        // ID 唯一
        phases.groupBy { it.id }.filterValues { it.size > 1 }.forEach { (id, dup) ->
            errors.add("相位 id 重复: '$id' 出现 ${dup.size} 次（atMeters=${dup.map { it.atMeters }}）")
        }

        // 非递减排序（允许不同通道在同一距离触发）
        phases.zipWithNext().forEach { (a, b) ->
            if (b.atMeters < a.atMeters) {
                errors.add("phases 必须按 atMeters 非递减排序: '${a.id}'(${a.atMeters}) 之后出现 '${b.id}'(${b.atMeters})")
            }
        }

        val required = config.requiredDistanceMeters
        phases.forEach { p ->
            if (p.atMeters < 0) errors.add("相位 '${p.id}' atMeters=${p.atMeters} 不能为负")
            if (p.atMeters > required) {
                errors.add("相位 '${p.id}' atMeters=${p.atMeters} 超过终点 $required")
            }
            when (p.channel) {
                PhaseChannel.AUDIO -> {
                    if (p.layer == null) errors.add("audio 相位 '${p.id}' 缺少 layer 引用")
                    else if (!config.layers.containsKey(p.layer)) {
                        errors.add("audio 相位 '${p.id}' 引用的层 '${p.layer}' 未在 layers 中定义")
                    }
                    val v = p.toVolume
                    when {
                        v == null -> errors.add("audio 相位 '${p.id}' 缺少 toVolume")
                        !v.isFinite() -> errors.add("audio 相位 '${p.id}' toVolume=$v 非有限数值")
                        v < 0f || v > 1f -> errors.add("audio 相位 '${p.id}' toVolume=$v 超出 [0,1]")
                    }
                    if (p.fadeMs != null && p.fadeMs < 0) errors.add("audio 相位 '${p.id}' fadeMs=${p.fadeMs} 不能为负")
                }
                PhaseChannel.VISUAL -> {
                    if (p.layer == null) errors.add("visual 相位 '${p.id}' 缺少 layer 引用")
                    else if (!config.visualLayers.containsKey(p.layer)) {
                        errors.add("visual 相位 '${p.id}' 引用的层 '${p.layer}' 未在 visualLayers 中定义")
                    }
                    val o = p.toOpacity
                    when {
                        o == null -> errors.add("visual 相位 '${p.id}' 缺少 toOpacity")
                        !o.isFinite() -> errors.add("visual 相位 '${p.id}' toOpacity=$o 非有限数值")
                        o < 0f || o > 1f -> errors.add("visual 相位 '${p.id}' toOpacity=$o 超出 [0,1]")
                    }
                    val fade = p.fadeMeters ?: 0
                    if (fade < 0) errors.add("visual 相位 '${p.id}' fadeMeters=$fade 不能为负")
                    if (p.atMeters + fade > required) {
                        errors.add("visual 相位 '${p.id}' 的淡入越过终点: ${p.atMeters}+${fade} > $required")
                    }
                }
                PhaseChannel.HAPTIC -> {
                    if (p.pattern.isNullOrBlank()) errors.add("haptic 相位 '${p.id}' 缺少 pattern")
                    val n = p.everyNSteps
                    if (n == null) errors.add("haptic 相位 '${p.id}' 缺少 everyNSteps")
                    else if (n < 1) errors.add("haptic 相位 '${p.id}' everyNSteps=$n 必须 ≥ 1")
                }
            }
        }

        // 起点黑幕（§12.4）：必须有 atMeters=0、引用 solid 类型 void 层的视觉相位，
        // 不能用任意 atMeters=0 的视觉相位替代
        val hasVoid = phases.any { p ->
            p.channel == PhaseChannel.VISUAL &&
                p.atMeters == 0 &&
                p.layer == "void" &&
                config.visualLayers["void"] is VisualLayerDef.Solid
        }
        if (!hasVoid) {
            errors.add("缺少 atMeters=0 的 void 黑幕视觉相位（须引用 visualLayers 中 solid 类型的 void 层）")
        }
    }

    private fun validatePathProfile(config: SceneConfig, errors: MutableList<String>) {
        val segments = config.pathProfile.segments
        val required = config.requiredDistanceMeters
        if (segments.isEmpty()) {
            errors.add("pathProfile.segments 不能为空")
            return
        }
        if (segments.first().from != 0) {
            errors.add("pathProfile 必须从 0 开始，实际从 ${segments.first().from} 开始")
        }
        segments.zipWithNext().forEach { (a, b) ->
            if (a.to != b.from) {
                errors.add("pathProfile 段不连续: [${a.from},${a.to}] 之后是 [${b.from},${b.to}]（存在空缺或重叠）")
            }
        }
        segments.forEach { s ->
            if (s.from >= s.to) errors.add("pathProfile 段 [${s.from},${s.to}] 长度必须为正")
            val g = s.grade
            if (g != null && (!g.isFinite() || g <= 0f || g > 0.2f)) {
                errors.add("pathProfile 段 [${s.from},${s.to}] grade=$g 非有限或超出 (0, 0.2]")
            }
        }
        if (segments.last().to != required) {
            errors.add("pathProfile 终点 ${segments.last().to} 与 requiredDistanceMeters=$required 不一致（未覆盖全程）")
        }
        // 前 10% 是黑幕阶段，看不清地形，禁止 gap_hop
        val darknessLimit = required * 0.10
        segments.filter { it.kind == TerrainKind.GAP_HOP }.forEach { s ->
            if (s.from < darknessLimit) {
                errors.add("gap_hop 出现在前 10% 路程（黑幕阶段不可见地形）: 段 [${s.from},${s.to}] 早于 $darknessLimit m")
            }
        }
    }

    private fun validateMilestones(config: SceneConfig, errors: MutableList<String>) {
        val required = config.requiredDistanceMeters.toDouble()
        fun covered(channel: PhaseChannel, ratio: Double): Boolean =
            config.phases.any { p ->
                p.channel == channel && kotlin.math.abs(p.atMeters - ratio * required) <= MILESTONE_TOLERANCE * required
            }

        fun check(channel: PhaseChannel, ratios: List<Double>, channelName: String) {
            ratios.forEach { ratio ->
                if (!covered(channel, ratio)) {
                    val percent = (ratio * 100).toInt()
                    errors.add("$channelName 通道缺少 ~$percent% 里程碑相位（±5% 内无覆盖，见 §8.1 叙事弧）")
                }
            }
        }
        check(PhaseChannel.AUDIO, AUDIO_MILESTONES, "audio")
        check(PhaseChannel.HAPTIC, HAPTIC_MILESTONES, "haptic")
        check(PhaseChannel.VISUAL, VISUAL_MILESTONES, "visual")
    }

    private fun validateAssets(
        config: SceneConfig,
        locator: AssetLocator,
        policy: AssetsPolicy,
        errors: MutableList<String>,
        placeholders: MutableList<String>,
    ) {
        config.layers.forEach { (name, def) ->
            when (def) {
                is AudioLayerDef.StepOneShot -> {
                    def.files.forEach { file ->
                        if (!locator.exists(file)) errors.add("音频层 '$name' 引用的素材不存在: $file")
                    }
                    def.placeholder?.let { placeholders.add("layers.$name → $it") }
                }
                is AudioLayerDef.Loop -> {
                    def.file?.let { file ->
                        if (!locator.exists(file)) errors.add("音频层 '$name' 引用的素材不存在: $file")
                    }
                    def.placeholder?.let { placeholders.add("layers.$name → $it") }
                }
            }
        }
        config.visualLayers.forEach { (name, def) ->
            when (def) {
                is VisualLayerDef.Parallax -> {
                    def.asset?.let { asset ->
                        if (!locator.exists(asset)) errors.add("视觉层 '$name' 引用的素材不存在: $asset")
                    }
                    if (!def.parallax.isFinite() || def.parallax < 0f || def.parallax > 1f) {
                        errors.add("视觉层 '$name' parallax=${def.parallax} 非有限或超出 [0,1]")
                    }
                    def.placeholder?.let { placeholders.add("visualLayers.$name → $it") }
                }
                is VisualLayerDef.Overlay -> {
                    def.asset?.let { asset ->
                        if (!locator.exists(asset)) errors.add("视觉层 '$name' 引用的素材不存在: $asset")
                    }
                    def.placeholder?.let { placeholders.add("visualLayers.$name → $it") }
                }
                is VisualLayerDef.Solid -> Unit
            }
        }
        if (policy == AssetsPolicy.REQUIRE_REAL_ASSETS && placeholders.isNotEmpty()) {
            errors.add("发布配置不允许开发占位（共 ${placeholders.size} 处）: ${placeholders.joinToString("; ")}")
        }
    }
}
