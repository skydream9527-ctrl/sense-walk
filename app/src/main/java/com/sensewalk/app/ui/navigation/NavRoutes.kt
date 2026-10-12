package com.sensewalk.app.ui.navigation

object NavRoutes {
    const val HOME = "home"
    const val SETTINGS = "settings"
    const val MODE = "mode/{sceneId}"
    const val SESSION = "session/{sceneId}/{mode}"
    const val RESULT = "result/{sceneId}/{outcome}/{meters}/{elapsedMs}"

    fun mode(sceneId: String) = "mode/$sceneId"
    fun session(sceneId: String, mode: String) = "session/$sceneId/$mode"
    fun result(sceneId: String, outcome: String, meters: Int, elapsedMs: Long) =
        "result/$sceneId/$outcome/$meters/$elapsedMs"

    /** 会话结果（终态由领域层决定，米数来自 ProgressAccumulator） */
    object Outcome {
        const val COMPLETED = "completed"
        const val ABANDONED = "abandoned"
    }

    /** 行走模式；T04 仅开放 virtual */
    object Mode {
        const val VIRTUAL = "virtual"
        const val REAL = "real"
    }
}
