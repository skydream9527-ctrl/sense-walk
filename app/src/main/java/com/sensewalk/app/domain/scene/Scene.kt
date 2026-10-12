package com.sensewalk.app.domain.scene

/**
 * Scene loaded from assets/scenes/*.json (see DEVELOPMENT.md schema).
 */
data class Scene(
    val id: String,
    val name: String,
    val suggestedMinutes: Int,
    val phases: List<Phase>,
    val layers: Map<String, Layer>,
)

data class Phase(
    val atSec: Int,
    val action: String,
    val layer: String? = null,
    val toVolume: Float? = null,
    val fadeMs: Int? = null,
    val pattern: String? = null,
    val intervalMs: Int? = null,
)

data class Layer(
    val file: String,
    val loop: Boolean = true,
)
