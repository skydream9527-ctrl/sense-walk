package com.sensewalk.app.ui.session

import android.app.Application
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.Companion.APPLICATION_KEY
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.stick.ComfortStickMapper
import com.sensewalk.app.session.SessionViewModel
import com.sensewalk.app.ui.navigation.NavRoutes
import com.sensewalk.app.ui.theme.AccentSoft
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface
import kotlinx.coroutines.delay

/**
 * 虚走会话页（T04）：
 * - 会话状态唯一来源是 SessionViewModel 持有的 VirtualWalkController；
 * - 本页只提交输入、渲染快照；一个 LaunchedEffect 帧循环驱动 controller.frame；
 * - 上半区轻触查看米数、右上角长按 1.5s 放弃、系统返回出继续/放弃确认；
 * - 下半区 45% 为浮动摇杆；按住前进（无障碍）开启时显示按住按钮；
 * - 视觉由 ForestShell 按 SensoryState 绘制，从黑幕起，米数不变揭示不变。
 */
@Composable
fun SessionScreen(
    sceneId: String,
    mode: String,
    onFinished: (outcome: String, meters: Int, elapsedMs: Long) -> Unit,
    onBack: () -> Unit,
) {
    val vm: SessionViewModel = viewModel(
        key = "session-$sceneId-$mode",
        factory = viewModelFactory {
            initializer {
                SessionViewModel(
                    this[APPLICATION_KEY] as Application,
                    sceneId,
                    com.sensewalk.app.ui.navigation.PendingRestore.consumeVirtual(),
                )
            }
        },
    )
    val uiState by vm.uiState.collectAsStateWithLifecycle()
    val walk by vm.walk.collectAsStateWithLifecycle()
    val settings by vm.settings.collectAsStateWithLifecycle()

    when (val state = uiState) {
        is SessionViewModel.UiState.Loading -> Box(
            Modifier
                .fillMaxSize()
                .background(SenseBlack),
            contentAlignment = Alignment.Center,
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                CircularProgressIndicator(color = AccentSoft)
                Text("正在准备场景…", color = SenseMuted, modifier = Modifier.padding(top = 16.dp))
            }
        }

        is SessionViewModel.UiState.Error -> Column(
            Modifier
                .fillMaxSize()
                .background(SenseBlack)
                .padding(28.dp),
            verticalArrangement = Arrangement.Center,
        ) {
            Text("暂时走不了", style = MaterialTheme.typography.titleLarge, color = SenseOnSurface)
            Text(
                text = state.message,
                style = MaterialTheme.typography.bodySmall,
                color = SenseMuted,
                modifier = Modifier.padding(vertical = 12.dp),
            )
            Button(onClick = onBack) { Text("返回") }
        }

        is SessionViewModel.UiState.Ready -> {
            val session = walk?.session ?: SessionState.READY
            if (mode != NavRoutes.Mode.VIRTUAL) {
                // 双保险：导航参数异常时不进入会话
                Column(
                    Modifier
                        .fillMaxSize()
                        .background(SenseBlack)
                        .padding(28.dp),
                    verticalArrangement = Arrangement.Center,
                ) {
                    Text("这个模式还没有开放", style = MaterialTheme.typography.titleLarge, color = SenseOnSurface)
                    Text(
                        "实走（计步）在后续版本开放。可以回首页选择虚走。",
                        color = SenseMuted,
                        modifier = Modifier.padding(vertical = 12.dp),
                    )
                    Button(onClick = onBack) { Text("返回") }
                }
                return
            }
            SessionContent(
                vm = vm,
                config = state.controller.config,
                walk = walk,
                reduceMotion = settings.reduceMotion,
                rhythmHint = settings.rhythmHint,
                holdToWalk = settings.holdToWalk,
                onFinished = onFinished,
            )
        }
    }
}

@Composable
private fun SessionContent(
    vm: SessionViewModel,
    config: com.sensewalk.app.domain.scene.SceneConfig,
    walk: com.sensewalk.app.domain.walk.VirtualWalkController.Snapshot?,
    reduceMotion: Boolean,
    rhythmHint: Boolean,
    holdToWalk: Boolean,
    onFinished: (outcome: String, meters: Int, elapsedMs: Long) -> Unit,
) {
    val session = walk?.session ?: SessionState.READY
    val sessionActive = session == SessionState.READY || session == SessionState.WALKING || session == SessionState.PAUSED
    val stabilizeHint by vm.stabilizeHint.collectAsStateWithLifecycle()

    // 单帧循环：全页唯一的帧驱动，重组不会新增循环
    LaunchedEffect(vm) {
        while (true) {
            withFrameNanos { vm.onFrame() }
        }
    }

    // 生命周期：后台清输入+暂停；回前台重置基线等待新输入
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner, vm) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_STOP -> vm.onAppBackground()
                Lifecycle.Event.ON_START -> vm.onAppForeground()
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    // 系统返回：暂停 + 继续/放弃确认（确认期间不累计）
    var showConfirm by remember { mutableStateOf(false) }
    BackHandler(enabled = sessionActive && !showConfirm) {
        vm.pauseForDialog()
        showConfirm = true
    }

    if (showConfirm && sessionActive) {
        AlertDialog(
            onDismissRequest = {
                vm.resumeFromDialog()
                showConfirm = false
            },
            title = { Text("要放弃这段路吗？") },
            text = { Text("现在停下来，这一局就到这里了。想走的时候随时再来。") },
            confirmButton = {
                TextButton(onClick = {
                    vm.resumeFromDialog()
                    showConfirm = false
                }) { Text("继续走") }
            },
            dismissButton = {
                TextButton(onClick = {
                    vm.abandon()
                    showConfirm = false
                }) { Text("放弃这段路") }
            },
        )
    }

    // 终态只导航一次
    var navigated by remember { mutableStateOf(false) }
    LaunchedEffect(session) {
        if (!navigated && (session == SessionState.COMPLETED || session == SessionState.ABANDONED)) {
            navigated = true
            val snapshot = walk ?: return@LaunchedEffect
            onFinished(
                if (session == SessionState.COMPLETED) NavRoutes.Outcome.COMPLETED else NavRoutes.Outcome.ABANDONED,
                snapshot.meters.toInt(),
                snapshot.elapsedActiveMs,
            )
        }
    }

    // 首局说明（I02）：短暂可关闭，首次输入后消失
    var showIntro by remember { mutableStateOf(true) }
    LaunchedEffect(Unit) {
        delay(8_000)
        showIntro = false
    }
    LaunchedEffect(walk?.deflection) {
        if ((walk?.deflection ?: 0f) > 0.05f) showIntro = false
    }

    // 轻触查看米数（可信米数 = 领域累计值）
    var showMeters by remember { mutableStateOf(false) }

    Box(
        Modifier
            .fillMaxSize()
            .background(SenseBlack),
    ) {
        // 森林视觉：黑幕起，按 SensoryState 揭示；带 asset 的层渲染真实图片，其余程序降级
        val imageLayers = remember(config) {
            buildMap {
                config.visualLayers.forEach { (id, def) ->
                    val asset = when (def) {
                        is com.sensewalk.app.domain.scene.VisualLayerDef.Parallax -> def.asset
                        is com.sensewalk.app.domain.scene.VisualLayerDef.Overlay -> def.asset
                        is com.sensewalk.app.domain.scene.VisualLayerDef.Solid -> null
                    }
                    if (asset != null) {
                        val parallax = (def as? com.sensewalk.app.domain.scene.VisualLayerDef.Parallax)?.parallax ?: 0f
                        put(id, ForestImageLayer(asset, parallax))
                    }
                }
            }
        }
        ForestShell(
            sensory = walk?.sensory ?: com.sensewalk.app.domain.phase.SensoryState(emptyMap(), emptyMap(), emptyList()),
            sPos = walk?.sPos ?: 0f,
            velocity = walk?.velocity ?: 0f,
            terrain = walk?.terrain ?: com.sensewalk.app.domain.scene.TerrainKind.FLAT,
            reduceMotion = reduceMotion,
            imageLayers = imageLayers,
            gait = walk?.gait ?: com.sensewalk.app.domain.walk.TerrainMotor.Gait.IDLE,
        )

        // 上半区：轻触查看米数 + 放弃/暂停控件
        Box(
            Modifier
                .fillMaxWidth()
                .fillMaxHeight(0.55f)
                .pointerInput(Unit) {
                    detectTapGestures { showMeters = !showMeters }
                },
        ) {
            Column(
                Modifier
                    .align(Alignment.TopCenter)
                    .padding(top = 64.dp)
                    .semantics { contentDescription = if (showMeters) "已走 ${walk?.meters?.toInt() ?: 0} 米" else "轻触查看已走米数" },
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
                verticalArrangement = Arrangement.spacedBy(8.dp),
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

        // 下半区 45%：浮动摇杆（实体区域限定，不拦截上方控件）
        JoystickZone(
            rhythmHint = rhythmHint,
            onDeflection = vm::onStick,
            onReleased = vm::onStickReleased,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .fillMaxHeight(0.45f),
        )

        // 按住前进（无障碍，开放决策 #12）：持续按住才走，同一曲线与门禁
        if (holdToWalk) {
            Box(
                Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 48.dp),
            ) {
                HoldToWalkButton(
                    enabled = sessionActive,
                    onHold = { vm.onStick(ComfortStickMapper.SWEET_SPOT_DEFLECTION) },
                    onRelease = { vm.onStickReleased() },
                )
            }
        }

        // T07B 首坎站稳提示（一次性，非 QTE）：3 秒自动消失
        if (stabilizeHint && sessionActive && !showIntro) {
            LaunchedEffect(stabilizeHint) {
                delay(3000)
                vm.consumeStabilizeHintDone()
            }
            Column(
                Modifier
                    .align(Alignment.Center)
                    .padding(horizontal = 36.dp)
                    .background(Color.White.copy(alpha = 0.10f), RoundedCornerShape(16.dp))
                    .padding(horizontal = 24.dp, vertical = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    text = "慢一点，站稳再跳。",
                    style = MaterialTheme.typography.bodyLarge,
                    color = SenseOnSurface,
                    textAlign = TextAlign.Center,
                )
            }
        }

        // 说明卡片
        if (showIntro && sessionActive) {
            Column(
                Modifier
                    .align(Alignment.Center)
                    .padding(horizontal = 36.dp)
                    .background(Color.White.copy(alpha = 0.06f), RoundedCornerShape(16.dp))
                    .clickable { showIntro = false }
                    .padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    text = "推满不会更快。\n松一点，找舒服的节奏。",
                    style = MaterialTheme.typography.bodyLarge,
                    color = SenseOnSurface,
                    textAlign = TextAlign.Center,
                )
                Text(
                    text = "走着走着，声音和风景会慢慢出现。\n（轻点此处关闭）",
                    style = MaterialTheme.typography.bodySmall,
                    color = SenseMuted,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
        }

        // 暂停（外部中断/后台返回/手动）：明确的「继续」操作回到 Ready 等待新输入。
        // 焦点恢复/耳机重连不会自动行走——必须点按继续并重新给摇杆输入。
        if (session == SessionState.PAUSED && !showConfirm) {
            Column(
                modifier = Modifier
                    .align(Alignment.Center)
                    .padding(horizontal = 48.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    text = "已暂停",
                    style = MaterialTheme.typography.titleMedium,
                    color = SenseOnSurface,
                )
                Text(
                    text = "点「继续走」后，摇杆重新给输入才会前进",
                    style = MaterialTheme.typography.bodySmall,
                    color = SenseMuted,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 6.dp, bottom = 16.dp),
                )
                Button(
                    onClick = vm::resumeAfterInterruption,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = AccentSoft,
                        contentColor = SenseBlack,
                    ),
                    shape = RoundedCornerShape(14.dp),
                ) {
                    Text("继续走", style = MaterialTheme.typography.titleMedium)
                }
            }
        }
    }
}

@Composable
internal fun PauseButton(enabled: Boolean, onClick: () -> Unit) {
    Box(
        Modifier
            .semantics { contentDescription = "暂停：打开继续或放弃确认" }
            .background(Color.White.copy(alpha = 0.06f), RoundedCornerShape(20.dp))
            .clickable(enabled = enabled, onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 10.dp),
    ) {
        Text("暂停", style = MaterialTheme.typography.labelMedium, color = SenseMuted)
    }
}

/** 按住前进：只在按住期间以甜点偏转前进，松开即停；不做自动行走 */
@Composable
private fun HoldToWalkButton(
    enabled: Boolean,
    onHold: () -> Unit,
    onRelease: () -> Unit,
) {
    val currentOnHold by rememberUpdatedState(onHold)
    val currentOnRelease by rememberUpdatedState(onRelease)

    // 离开页面时释放前进输入
    DisposableEffect(Unit) {
        onDispose { currentOnRelease() }
    }

    Box(
        Modifier
            .semantics {
                contentDescription = "按住前进：按住期间以舒适区速度前进，松开即停"
            }
            .pointerInput(enabled) {
                awaitEachGesture {
                    val down = awaitFirstDown(requireUnconsumed = false)
                    if (!enabled) return@awaitEachGesture
                    down.consume()
                    try {
                        currentOnHold()
                        while (true) {
                            val event = awaitPointerEvent()
                            val change = event.changes.firstOrNull { it.id == down.id } ?: break
                            if (!change.pressed) break // 松手或系统取消
                            change.consume()
                        }
                    } finally {
                        // 松手、取消、禁用切换重启协程或离开组合都保证释放
                        currentOnRelease()
                    }
                }
            }
            .background(Color.White.copy(alpha = 0.10f), RoundedCornerShape(24.dp))
            .padding(horizontal = 28.dp, vertical = 16.dp),
    ) {
        Text("按住前进", style = MaterialTheme.typography.titleMedium, color = SenseOnSurface)
    }
}
