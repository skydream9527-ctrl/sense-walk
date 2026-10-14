package com.sensewalk.app

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.SceneLoadState
import com.sensewalk.app.ui.home.HomeScreen
import com.sensewalk.app.ui.mode.ModeScreen
import com.sensewalk.app.ui.navigation.NavRoutes
import com.sensewalk.app.ui.session.RealWalkSession
import com.sensewalk.app.ui.session.ResultScreen
import com.sensewalk.app.ui.session.SessionScreen
import com.sensewalk.app.ui.settings.SettingsScreen
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseWalkTheme

@Composable
fun SenseWalkApp(
    viewModel: SenseWalkViewModel = viewModel(),
) {
    SenseWalkTheme {
        val navController = rememberNavController()
        val sceneState by viewModel.sceneState.collectAsStateWithLifecycle()
        val settings by viewModel.settings.collectAsStateWithLifecycle()

        fun findScene(sceneId: String): SceneConfig? =
            (sceneState as? SceneLoadState.Ready)?.scenes?.find { it.id == sceneId }

        NavHost(
            navController = navController,
            startDestination = NavRoutes.HOME,
            modifier = Modifier
                .fillMaxSize()
                .background(SenseBlack),
        ) {
            composable(NavRoutes.HOME) {
                HomeScreen(
                    state = sceneState,
                    lastSceneId = settings.lastSceneId,
                    onRetry = viewModel::retrySceneLoad,
                    onSelectScene = { sceneId ->
                        navController.navigate(NavRoutes.mode(sceneId))
                    },
                    onOpenSettings = {
                        navController.navigate(NavRoutes.SETTINGS)
                    },
                )
            }

            composable(NavRoutes.SETTINGS) {
                SettingsScreen(
                    settings = settings,
                    onVibrationChange = viewModel::setVibrationEnabled,
                    onRhythmHintChange = viewModel::setRhythmHint,
                    onReduceMotionChange = viewModel::setReduceMotion,
                    onHoldToWalkChange = viewModel::setHoldToWalk,
                    onBack = { navController.popBackStack() },
                )
            }

            composable(
                route = NavRoutes.MODE,
                arguments = listOf(navArgument("sceneId") { type = NavType.StringType }),
            ) { entry ->
                val sceneId = entry.arguments?.getString("sceneId") ?: ""
                ModeScreen(
                    scene = findScene(sceneId),
                    sceneLoadError = sceneState is SceneLoadState.Error,
                    lastMode = settings.lastMode,
                    onBack = { navController.popBackStack() },
                    onStart = { sid, mode ->
                        viewModel.setLastSelection(sid, mode)
                        navController.navigate(NavRoutes.session(sid, mode))
                    },
                )
            }

            composable(
                route = NavRoutes.SESSION,
                arguments = listOf(
                    navArgument("sceneId") { type = NavType.StringType },
                    navArgument("mode") { type = NavType.StringType },
                ),
            ) { entry ->
                val sceneId = entry.arguments?.getString("sceneId") ?: return@composable
                val mode = entry.arguments?.getString("mode") ?: return@composable
                if (mode == NavRoutes.Mode.REAL) {
                    RealWalkSession(
                        sceneId = sceneId,
                        onFinished = { outcome, meters, elapsedMs ->
                            navController.navigate(
                                NavRoutes.result(sceneId, outcome, meters, elapsedMs),
                            ) {
                                popUpTo(NavRoutes.session(sceneId, mode)) { inclusive = true }
                            }
                        },
                        onBack = { navController.popBackStack() },
                    )
                } else {
                    SessionScreen(
                        sceneId = sceneId,
                        mode = mode,
                        onFinished = { outcome, meters, elapsedMs ->
                            navController.navigate(
                                NavRoutes.result(sceneId, outcome, meters, elapsedMs),
                            ) {
                                popUpTo(NavRoutes.session(sceneId, mode)) { inclusive = true }
                            }
                        },
                        onBack = { navController.popBackStack() },
                    )
                }
            }

            composable(
                route = NavRoutes.RESULT,
                arguments = listOf(
                    navArgument("sceneId") { type = NavType.StringType },
                    navArgument("outcome") { type = NavType.StringType },
                    navArgument("meters") { type = NavType.IntType },
                    navArgument("elapsedMs") { type = NavType.LongType },
                ),
            ) { entry ->
                val sceneId = entry.arguments?.getString("sceneId") ?: ""
                val outcome = entry.arguments?.getString("outcome") ?: NavRoutes.Outcome.ABANDONED
                val meters = entry.arguments?.getInt("meters") ?: 0
                val elapsedMs = entry.arguments?.getLong("elapsedMs") ?: 0L
                val scene = findScene(sceneId)
                ResultScreen(
                    sceneName = scene?.name ?: "",
                    requiredDistanceMeters = scene?.requiredDistanceMeters ?: 0,
                    outcome = outcome,
                    meters = meters,
                    elapsedMs = elapsedMs,
                    onWalkAgain = {
                        navController.navigate(NavRoutes.mode(sceneId)) {
                            popUpTo(NavRoutes.HOME)
                        }
                    },
                    onHome = {
                        navController.navigate(NavRoutes.HOME) {
                            popUpTo(NavRoutes.HOME) { inclusive = true }
                        }
                    },
                )
            }
        }
    }
}
