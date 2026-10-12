package com.sensewalk.app.domain.scene

import org.junit.Assert.assertEquals
import org.junit.Test

/** §6.1 时长推导：地形系数与四舍五入规则 */
class SceneDurationEstimatorTest {

    @Test
    fun `平地 800m 约 12 分钟`() {
        val config = TestScenes.validConfig(required = 800)
        // 800 / 1.10 / 60 = 12.12 → 12
        assertEquals(12, SceneDurationEstimator.estimatedVirtualMinutes(config))
    }

    @Test
    fun `地形系数符合 §5_7`() {
        assertEquals(1.00, SceneDurationEstimator.terrainSpeedFactor(TerrainKind.FLAT, null), 1e-6)
        assertEquals(0.88, SceneDurationEstimator.terrainSpeedFactor(TerrainKind.SLOPE_UP, 0.08f), 1e-6)
        assertEquals(0.95, SceneDurationEstimator.terrainSpeedFactor(TerrainKind.SLOPE_DOWN, null), 1e-6)
        assertEquals(0.95, SceneDurationEstimator.terrainSpeedFactor(TerrainKind.UNEVEN, null), 1e-6)
        // 缺省坡度 0.08
        assertEquals(0.88, SceneDurationEstimator.terrainSpeedFactor(TerrainKind.SLOPE_UP, null), 1e-6)
        // 极陡坡不低于 0.80 下限
        assertEquals(0.80, SceneDurationEstimator.terrainSpeedFactor(TerrainKind.SLOPE_UP, 0.5f), 1e-6)
    }

    @Test
    fun `上坡降低平均速度从而拉长时长`() {
        val flat = TestScenes.validConfig(
            required = 1000,
            segments = listOf(PathSegment(0, 1000, TerrainKind.FLAT)),
        )
        val hilly = TestScenes.validConfig(
            required = 1000,
            segments = listOf(
                PathSegment(0, 500, TerrainKind.FLAT),
                PathSegment(500, 1000, TerrainKind.SLOPE_UP, 0.10f),
            ),
        )
        assertEquals(1.0, SceneDurationEstimator.averageTerrainFactor(flat), 1e-6)
        assertEquals(0.925, SceneDurationEstimator.averageTerrainFactor(hilly), 1e-6)
        assertEquals(15, SceneDurationEstimator.estimatedVirtualMinutes(flat))
        assertEquals(16, SceneDurationEstimator.estimatedVirtualMinutes(hilly))
    }
}
