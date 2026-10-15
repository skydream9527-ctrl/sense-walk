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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import com.sensewalk.app.data.SessionSnapshotStore
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.SceneLoadState
import com.sensewalk.app.domain.session.SessionSnapshot
import com.sensewalk.app.domain.session.SessionSnapshotValidator
import com.sensewalk.app.domain.session.SnapshotCandidate
import com.sensewalk.app.service.WalkForegroundService
import com.sensewalk.app.ui.navigation.PendingRestore
import com.sensewalk.app.ui.home.HomeScreen
import com.sensewalk.app.ui.mode.ModeScreen
import com.sensewalk.app.ui.navigation.NavRoutes
import com.sensewalk.app.ui.session.RealWalkSession
import com.sensewalk.app.ui.session.ResultScreen
import com.sensewalk.app.ui.session.SessionScreen
import com.sensewalk.app.ui.settings.SettingsScreen
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseWalkTheme
import kotlinx.coroutines.launch

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
                val context = LocalContext.current
                val scope = rememberCoroutineScope()
                val store = remember { SessionSnapshotStore(context) }
                // T07A（SW-004）：进入 MODE 页预载快照；点开始时按校验结果决定
                // 恢复确认 / 直接新会话；实走活服务优先重绑（不起第二套恢复引擎）
                var pendingSnapshot by remember { mutableStateOf<SessionSnapshot?>(null) }
                var restoreCandidate by remember { mutableStateOf<SessionSnapshot?>(null) }
                var pendingNewStart by remember { mutableStateOf<Pair<String, String>?>(null) }
                LaunchedEffect(Unit) { pendingSnapshot = store.load() }

                val sceneInfo: (String) -> com.sensewalk.app.domain.session.SceneInfo? = { id ->
                    findScene(id)?.let { cfg ->
                        com.sensewalk.app.domain.session.SceneInfo(
                            sceneId = cfg.id,
                            schemaVersion = cfg.schemaVersion,
                            requiredMeters = cfg.requiredDistanceMeters.toFloat(),
                            phaseIds = cfg.phases.map { it.id }.toSet(),
                        )
                    }
                }

                fun startSession(sid: String, mode: String, restore: SessionSnapshot?) {
                    viewModel.setLastSelection(sid, mode)
                    if (restore != null) {
                        if (mode == NavRoutes.Mode.REAL) {
                            PendingRestore.realJson = SessionSnapshot.toJson(restore)
                        } else {
                            PendingRestore.virtual = restore
                        }
                    }
                    navController.navigate(NavRoutes.session(sid, mode))
                }

                if (restoreCandidate != null) {
                    val snap = restoreCandidate!!
                    AlertDialog(
                        onDismissRequest = { restoreCandidate = null },
                        title = { Text("继续上次的路段？") },
                        text = {
                            val minutesAgo = (System.currentTimeMillis() - snap.savedAtWallMs) / 60_000
                            Text(
                                "上次在${if (snap.mode == "real") "实走" else "虚走"}${findScene(snap.sceneId)?.name ?: snap.sceneId}" +
                                    "走到约 ${snap.meters.toInt()} m 时中断了（约 ${minutesAgo} 分钟前）。\n" +
                                    "继续就从这里接着走；重新开始则丢弃这段进度。",
                            )
                        },
                        confirmButton = {
                            TextButton(onClick = {
                                restoreCandidate = null
                                startSession(snap.sceneId, snap.mode, snap)
                            }) { Text("继续") }
                        },
                        dismissButton = {
                            TextButton(onClick = {
                                restoreCandidate = null
                                val start = pendingNewStart
                                scope.launch {
                                    store.clear() // 用户显式放弃恢复：清候选
                                    if (start != null) startSession(start.first, start.second, null)
                                }
                            }) { Text("重新开始") }
                        },
                    )
                }

                ModeScreen(
                    scene = findScene(sceneId),
                    sceneLoadError = sceneState is SceneLoadState.Error,
                    lastMode = settings.lastMode,
                    onBack = { navController.popBackStack() },
                    onStart = { sid, mode ->
                        viewModel.setLastSelection(sid, mode)
                        // 实走活服务：直接进会话重绑（服务在跑，恢复候选不适用）
                        if (mode == NavRoutes.Mode.REAL && WalkForegroundService.hasActiveSession) {
                            navController.navigate(NavRoutes.session(sid, mode))
                            return@ModeScreen
                        }
                        val candidate = SessionSnapshotValidator.evaluate(
                            snapshot = pendingSnapshot,
                            nowWallMs = System.currentTimeMillis(),
                            sceneOf = sceneInfo,
                            currentBootCount = SessionSnapshotStore.bootCount(context),
                        )
                        when (candidate) {
                            is SnapshotCandidate.Valid ->
                                if (candidate.snapshot.mode == mode && candidate.snapshot.sceneId == sid) {
                                    pendingNewStart = sid to mode
                                    restoreCandidate = candidate.snapshot
                                } else {
                                    // 候选属于另一模式/场景：用户已显式选择新会话，候选交给新会话保存覆盖
                                    navController.navigate(NavRoutes.session(sid, mode))
                                }
                            else -> {
                                // 无快照/过期/损坏/不兼容：清掉不可恢复的残留，直接新会话
                                if (pendingSnapshot != null) scope.launch { store.clear() }
                                navController.navigate(NavRoutes.session(sid, mode))
                            }
                        }
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
