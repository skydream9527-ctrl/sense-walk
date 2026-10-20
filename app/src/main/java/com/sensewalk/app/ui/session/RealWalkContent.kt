package com.sensewalk.app.ui.session

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.State
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.sensewalk.app.data.SceneCatalog
import com.sensewalk.app.domain.scene.SceneLoadState
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.walk.VirtualWalkController
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface
import androidx.compose.foundation.gestures.detectTapGestures

/**
 * 实走会话主体（T06）：视觉层/米数/放弃/暂停复用虚走组件；
 * 下半区为「收进口袋走吧」状态区（实走无摇杆，计步由服务驱动）。
 *
 * SW-019：场景配置来自进程级 [SceneCatalog]（服务装配时已加载，组合期同步命中；
 * 未命中则异步加载），不再 runBlocking 阻塞 UI 线程；高频快照只在绘制期/派生态读取。
 */
@Composable
fun RealWalkContent(
    vm: RealWalkViewModel,
    sceneId: String,
    sceneName: String,
    walkState: State<VirtualWalkController.Snapshot?>,
    reduceMotion: Boolean,
) {
    val session by remember(walkState) { derivedStateOf { walkState.value?.session ?: SessionState.READY } }
    val sessionActive =
        session == SessionState.READY || session == SessionState.WALKING || session == SessionState.PAUSED

    // 场景配置只为视觉层（ForestShell）；计距/相位全在服务里。
    // remember 以 sceneId 为键：先同步命中进程缓存（服务装配时已加载），未命中才异步兜底，不阻塞 UI 线程
    val context = androidx.compose.ui.platform.LocalContext.current
    val visualConfig = remember(sceneId) { mutableStateOf(SceneCatalog.peekScene(context, sceneId)) }
    LaunchedEffect(sceneId) {
        if (visualConfig.value == null) {
            visualConfig.value = (SceneCatalog.load(context) as? SceneLoadState.Ready)
                ?.scenes
                ?.firstOrNull { it.id == sceneId }
        }
    }

    var showMeters by remember { mutableStateOf(false) }
    var showConfirm by remember { mutableStateOf(false) }

    androidx.activity.compose.BackHandler(enabled = sessionActive && !showConfirm) {
        vm.pauseForDialog()
        showConfirm = true
    }

    if (showConfirm && sessionActive) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = {
                vm.resumeFromDialog()
                showConfirm = false
            },
            title = { Text("要放弃这段路吗？") },
            text = { Text("现在停下来，这一局就到这里了。想走的时候随时再来。") },
            confirmButton = {
                androidx.compose.material3.TextButton(onClick = {
                    vm.resumeFromDialog()
                    showConfirm = false
                }) { Text("继续走") }
            },
            dismissButton = {
                androidx.compose.material3.TextButton(onClick = {
                    vm.abandon()
                    showConfirm = false
                }) { Text("放弃这段路") }
            },
        )
    }

    Box(
        Modifier
            .fillMaxSize()
            .background(SenseBlack),
    ) {
        visualConfig.value?.let { cfg ->
            ForestShell(
                walk = { walkState.value },
                reduceMotion = reduceMotion,
                imageLayers = remember(cfg) { ForestImageLayer.fromConfig(cfg) },
                sceneId = cfg.id,
            )
        }

        // 上半区：轻触米数 + 放弃/暂停（复用虚走控件）
        Box(
            Modifier
                .fillMaxWidth()
                .fillMaxHeight(0.55f)
                .pointerInput(Unit) { detectTapGestures { showMeters = !showMeters } },
        ) {
            MetersReadout(
                showMeters = showMeters,
                walkState = walkState,
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .padding(top = 64.dp),
            )

            Column(
                Modifier
                    .align(Alignment.TopEnd)
                    .padding(top = 48.dp, end = 16.dp),
                verticalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(8.dp),
            ) {
                AbandonControl(
                    enabled = sessionActive,
                    onAbandon = { vm.abandon() },
                    onOpenConfirmDialog = {
                        vm.pauseForDialog()
                        showConfirm = true
                    },
                )
                PauseButton(enabled = session == SessionState.WALKING) {
                    vm.pauseForDialog()
                    showConfirm = true
                }
            }
        }

        // 下半区：实走状态区（无摇杆；诚实提示当前节奏）
        Column(
            Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .fillMaxHeight(0.45f)
                .padding(bottom = 96.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = androidx.compose.foundation.layout.Arrangement.Center,
        ) {
            // 速度只派生成"是否在动"的布尔，文案不随每帧速度浮动失效
            val moving by remember(walkState) { derivedStateOf { (walkState.value?.velocity ?: 0f) > 0.05f } }
            Text(
                text = when {
                    session == SessionState.PAUSED -> "已暂停 · 走动时点「继续走」"
                    session == SessionState.WALKING && moving -> "走得刚刚好 · 就这样"
                    session == SessionState.WALKING -> "在走了 · 手机收好"
                    else -> "收进口袋，走吧"
                },
                style = MaterialTheme.typography.titleMedium,
                color = SenseOnSurface.copy(alpha = 0.85f),
            )
            Text(
                text = sceneName,
                style = MaterialTheme.typography.labelSmall,
                color = SenseMuted.copy(alpha = 0.7f),
                modifier = Modifier.padding(top = 8.dp),
            )
        }
    }
}
