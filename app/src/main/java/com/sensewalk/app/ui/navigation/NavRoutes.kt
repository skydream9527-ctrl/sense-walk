package com.sensewalk.app.ui.navigation

object NavRoutes {
    const val HOME = "home"
    const val SETTINGS = "settings"
    const val SESSION = "session/{sceneId}"
    const val END = "end/{sceneId}/{elapsedSeconds}"

    fun session(sceneId: String) = "session/$sceneId"
    fun end(sceneId: String, elapsedSeconds: Long) = "end/$sceneId/$elapsedSeconds"
}
