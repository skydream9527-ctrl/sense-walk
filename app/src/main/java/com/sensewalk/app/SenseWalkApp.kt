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
import com.sensewalk.app.ui.home.HomeScreen
import com.sensewalk.app.ui.navigation.NavRoutes
import com.sensewalk.app.ui.session.EndScreen
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
        val scenes by viewModel.scenes.collectAsStateWithLifecycle()
        val settings by viewModel.settings.collectAsStateWithLifecycle()

        NavHost(
            navController = navController,
            startDestination = NavRoutes.HOME,
            modifier = Modifier
                .fillMaxSize()
                .background(SenseBlack),
        ) {
            composable(NavRoutes.HOME) {
                HomeScreen(
                    scenes = scenes,
                    onStart = { scene ->
                        navController.navigate(NavRoutes.session(scene.id))
                    },
                    onOpenSettings = {
                        navController.navigate(NavRoutes.SETTINGS)
                    },
                )
            }

            composable(NavRoutes.SETTINGS) {
                SettingsScreen(
                    settings = settings,
                    onSilenceSecondsChange = viewModel::setSilenceSeconds,
                    onVibrationChange = viewModel::setVibrationEnabled,
                    onBack = { navController.popBackStack() },
                )
            }

            composable(
                route = NavRoutes.SESSION,
                arguments = listOf(navArgument("sceneId") { type = NavType.StringType }),
            ) { entry ->
                val sceneId = entry.arguments?.getString("sceneId") ?: return@composable
                val scene = scenes.find { it.id == sceneId } ?: return@composable
                SessionScreen(
                    scene = scene,
                    silenceSeconds = settings.silenceSeconds,
                    vibrationEnabled = settings.vibrationEnabled,
                    onEnd = { elapsed ->
                        navController.navigate(NavRoutes.end(sceneId, elapsed)) {
                            popUpTo(NavRoutes.session(sceneId)) { inclusive = true }
                        }
                    },
                )
            }

            composable(
                route = NavRoutes.END,
                arguments = listOf(
                    navArgument("sceneId") { type = NavType.StringType },
                    navArgument("elapsedSeconds") { type = NavType.LongType },
                ),
            ) { entry ->
                val sceneId = entry.arguments?.getString("sceneId") ?: return@composable
                val elapsed = entry.arguments?.getLong("elapsedSeconds") ?: 0L
                val scene = scenes.find { it.id == sceneId }
                EndScreen(
                    sceneName = scene?.name ?: "",
                    elapsedSeconds = elapsed,
                    onWalkAgain = {
                        navController.navigate(NavRoutes.session(sceneId)) {
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
