package com.sensewalk.app.ui.session

import androidx.compose.ui.graphics.Color

/**
 * 场景色板（SW-016）：ForestShell 泛化后的场景专用颜色。
 * forest 六色与既有值逐字节一致（批准表现不变）；rainforest 为湿绿程序色板
 * （D-009 冻结的画布规格/层参数之外的程序绘制颜色，候选图到位后仅作降级）。
 */
data class ScenePalette(
    val voidColor: Color,
    val silhouetteFar: Color,
    val silhouetteMid: Color,
    val groundDetail: Color,
    val glow: Color,
    val traveler: Color,
) {
    companion object {
        /** 森林既有色板（design/01-scenes-terrain/forest.md；与原 ForestShell 常量一致） */
        val FOREST = ScenePalette(
            voidColor = Color(0xFF060806),
            silhouetteFar = Color(0xFF1A2820),
            silhouetteMid = Color(0xFF2D4A3E),
            groundDetail = Color(0xFF6B8F71),
            glow = Color(0xFFA8C5A0),
            traveler = Color(0xFF7A857C),
        )

        /** 雨林程序色板（湿绿/深青系；未冻结，仅程序降级用） */
        val RAINFOREST = ScenePalette(
            voidColor = Color(0xFF0A1410),
            silhouetteFar = Color(0xFF14231C),
            silhouetteMid = Color(0xFF1E3A2C),
            groundDetail = Color(0xFF3E6B4F),
            glow = Color(0xFF9FD8B4),
            traveler = Color(0xFF6E8A7C),
        )

        fun of(sceneId: String): ScenePalette = when (sceneId) {
            "rainforest" -> RAINFOREST
            else -> FOREST
        }
    }
}
