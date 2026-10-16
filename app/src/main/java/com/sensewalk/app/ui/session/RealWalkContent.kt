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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.walk.VirtualWalkController
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface
import androidx.compose.foundation.gestures.detectTapGestures

/** 实走页视觉配置只读缓存（服务持有会话；UI 只需要 ForestShell 的层定义） */
private object RealWalkVisualCache {
    private val cache = mutableMapOf<String, com.sensewalk.app.domain.scene.SceneConfig?>()

    fun load(context: android.content.Context, sceneId: String): com.sensewalk.app.domain.scene.SceneConfig? =
        synchronized(cache) {
            cache.getOrPut(sceneId) {
                // loadAll 是挂起函数；服务已就绪说明仓库此刻可读——用阻塞读取（一次性，IO 线程池）
                kotlinx.coroutines.runBlocking {
                    (com.sensewalk.app.data.SceneRepository(context).loadAll()
                        as? com.sensewalk.app.domain.scene.SceneLoadState.Ready)
                        ?.scenes
                        ?.firstOrNull { it.id == sceneId }
                }
            }
        }
}

/**
 * 实走会话主体（T06）：视觉层/米数/放弃/暂停复用虚走组件；
 * 下半区为「收进口袋走吧」状态区（实走无摇杆，计步由服务驱动）。
 */
@Composable
fun RealWalkContent(
    vm: RealWalkViewModel,
    sceneId: String,
    sceneName: String,
    walk: VirtualWalkController.Snapshot?,
    reduceMotion: Boolean,
) {
    val session = walk?.session ?: SessionState.READY
    val sessionActive =
        session == SessionState.READY || session == SessionState.WALKING || session == SessionState.PAUSED

    // 场景配置只为视觉层（ForestShell）取一次；计距/相位全在服务里
    val context = androidx.compose.ui.platform.LocalContext.current
    val visualConfig = remember(sceneId) { RealWalkVisualCache.load(context, sceneId) }

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
        visualConfig?.let { cfg ->
            ForestShell(
                sensory = walk?.sensory ?: com.sensewalk.app.domain.phase.SensoryState(emptyMap(), emptyMap(), emptyList()),
                sPos = walk?.sPos ?: 0f,
                velocity = walk?.velocity ?: 0f,
                terrain = walk?.terrain ?: com.sensewalk.app.domain.scene.TerrainKind.FLAT,
                reduceMotion = reduceMotion,
                sceneId = cfg.id,
                imageLayers = remember(cfg) {
                    buildMap {
                        cfg.visualLayers.forEach { (id, def) ->
                            val asset = when (def) {
                                is com.sensewalk.app.domain.scene.VisualLayerDef.Parallax -> def.asset
                                is com.sensewalk.app.domain.scene.VisualLayerDef.Overlay -> def.asset
                                is com.sensewalk.app.domain.scene.VisualLayerDef.Solid -> null
                            }
                            if (asset != null) {
                                val parallax =
                                    (def as? com.sensewalk.app.domain.scene.VisualLayerDef.Parallax)?.parallax ?: 0f
                                put(id, ForestImageLayer(asset, parallax))
                            }
                        }
                    }
                },
            )
        }

        // 上半区：轻触米数 + 放弃/暂停（复用虚走控件）
        Box(
            Modifier
                .fillMaxWidth()
                .fillMaxHeight(0.55f)
                .pointerInput(Unit) { detectTapGestures { showMeters = !showMeters } },
        ) {
            Column(
                Modifier
                    .align(Alignment.TopCenter)
                    .padding(top = 64.dp)
                    .semantics {
                        contentDescription =
                            if (showMeters) "已走 ${walk?.meters?.toInt() ?: 0} 米" else "轻触查看已走米数"
                    },
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                if (showMeters && walk != null) {
                    Text(
                        text = "${walk.meters.toInt()} m",
                        style = MaterialTheme.typography.displayMedium,
                        fontWeight = FontWeight.Light,
                        color = SenseOnSurface.copy(alpha = 0.9f),
                    )
                    Text(
                        text = "已走",
                        style = MaterialTheme.typography.labelSmall,
                        color = SenseMuted,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                } else {
                    Text(
                        text = "轻触查看米数",
                        style = MaterialTheme.typography.labelSmall,
                        color = SenseMuted.copy(alpha = 0.5f),
                    )
                }
            }

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
            Text(
                text = when {
                    session == SessionState.PAUSED -> "已暂停 · 走动时点「继续走」"
                    session == SessionState.WALKING && (walk?.velocity ?: 0f) > 0.05f ->
                        "走得刚刚好 · 就这样"
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
