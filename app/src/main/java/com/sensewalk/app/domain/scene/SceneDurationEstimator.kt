package com.sensewalk.app.domain.scene

/**
 * 展示层时长推导（DEVELOPMENT.md §6.1）。
 *
 * suggestedMinutes 不再写入配置；卡片上的「约 N 分钟」由标准距离与地形
 * 平均速度系数运行时推导。实走不套用虚拟地形减速，另行估算。
 */
object SceneDurationEstimator {

    /** 虚走典型巡航速度（甜点区实际平均值，m/s），见 §6.1 */
    private const val VIRTUAL_TYPICAL_SPEED = 1.10

    /** 地形速度系数（§5.7）；gap_hop 采用「站稳再跳」的保守近似，待 T07 实装后校准 */
    fun terrainSpeedFactor(kind: TerrainKind, grade: Float?): Double = when (kind) {
        TerrainKind.FLAT -> 1.00
        TerrainKind.SLOPE_UP -> (1.0 - 1.5 * (grade?.toDouble() ?: 0.08)).coerceAtLeast(0.80)
        TerrainKind.SLOPE_DOWN -> 0.95
        TerrainKind.GAP_HOP -> 0.90
        TerrainKind.UNEVEN -> 0.95
    }

    /** 按 pathProfile 加权的平均地形系数 */
    fun averageTerrainFactor(config: SceneConfig): Double {
        val total = config.pathProfile.segments.sumOf { (it.to - it.from).toDouble() }
        if (total <= 0.0) return 1.0
        val weighted = config.pathProfile.segments.sumOf { seg ->
            (seg.to - seg.from).toDouble() * terrainSpeedFactor(seg.kind, seg.grade)
        }
        return weighted / total
    }

    /** 虚走典型时长（分钟，四舍五入到整数） */
    fun estimatedVirtualMinutes(config: SceneConfig): Int {
        val typicalSpeed = VIRTUAL_TYPICAL_SPEED * averageTerrainFactor(config)
        if (typicalSpeed <= 0.0) return 0
        return Math.round(config.requiredDistanceMeters / typicalSpeed / 60.0).toInt()
    }
}
