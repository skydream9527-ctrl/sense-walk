package com.sensewalk.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val SenseBlack = Color(0xFF0A0A0A)
val SenseSurface = Color(0xFF141414)
val SenseOnSurface = Color(0xFFE8E4D9)
val SenseMuted = Color(0xFF8A8680)
val ForestTint = Color(0xFF2D4A3E)
val DesertTint = Color(0xFF8B7355)
val NightTint = Color(0xFF1A1F3A)
val AccentSoft = Color(0xFFA8C5A0)

private val SenseWalkDarkColors = darkColorScheme(
    primary = AccentSoft,
    onPrimary = SenseBlack,
    secondary = SenseMuted,
    background = SenseBlack,
    onBackground = SenseOnSurface,
    surface = SenseSurface,
    onSurface = SenseOnSurface,
    surfaceVariant = Color(0xFF1E1E1E),
    onSurfaceVariant = SenseMuted,
)

@Composable
fun SenseWalkTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = SenseWalkDarkColors,
        content = content,
    )
}

fun sceneTint(sceneId: String): Color = when (sceneId) {
    "forest" -> ForestTint
    "desert" -> DesertTint
    "night_path" -> NightTint
    else -> SenseSurface
}
