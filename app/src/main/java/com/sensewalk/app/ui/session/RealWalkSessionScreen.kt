package com.sensewalk.app.ui.session

import android.Manifest
import android.app.Application
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.content.pm.PackageManager
import android.hardware.SensorManager
import android.os.IBinder
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.viewModelFactory
import androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.Companion.APPLICATION_KEY
import com.sensewalk.app.data.SettingsRepository
import com.sensewalk.app.data.UserSettings
import com.sensewalk.app.domain.scene.SceneLoadState
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.walk.VirtualWalkController
import com.sensewalk.app.service.WalkForegroundService
import com.sensewalk.app.ui.theme.AccentSoft
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * 实走会话 UI 桥（T06）：
 * - 会话真实状态都在 [WalkForegroundService]（唯一引擎）；本 VM 只负责
 *   绑定服务、转发命令、镜像快照——Activity 重建不产生第二套计距；
 * - 权限（ACTIVITY_RECOGNITION）与硬件（TYPE_STEP_COUNTER）先检查后启动，
 *   缺失/拒绝时给出可解释页面与虚走回退，不进假会话。
 */
class RealWalkViewModel(
    application: Application,
    private val sceneId: String,
) : AndroidViewModel(application) {

    sealed interface UiState {
        data object Loading : UiState
        data object NeedPermission : UiState
        data object NoSensor : UiState
        data class Error(val message: String) : UiState
        data class Ready(val sceneName: String) : UiState
    }

    private val app = application
    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    /** 服务快照镜像（会话状态唯一来源在服务里） */
    private val _walk = MutableStateFlow<VirtualWalkController.Snapshot?>(null)
    val walk: StateFlow<VirtualWalkController.Snapshot?> = _walk.asStateFlow()

    val settings: StateFlow<UserSettings> = SettingsRepository(app).settings
        .stateIn(viewModelScope, SharingStarted.Eagerly, UserSettings())

    private var binder: WalkForegroundService.LocalBinder? = null
    private var bound = false

    private val connection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, service: IBinder?) {
            val b = service as? WalkForegroundService.LocalBinder ?: return
            binder = b
            bound = true
            mirrorFlows(b)
        }

        override fun onServiceDisconnected(name: ComponentName?) {
            binder = null
            bound = false
        }
    }

    init {
        when {
            // 冒烟开关仅 debug 构建生效（DebugWalkSmoke），不构成真实计步验证
            !hasCounterSensor() && !com.sensewalk.app.service.DebugWalkSmoke.enabled(app) ->
                _uiState.value = UiState.NoSensor
            !hasPermission() && !com.sensewalk.app.service.DebugWalkSmoke.enabled(app) ->
                _uiState.value = UiState.NeedPermission
            else -> startService()
        }
    }

    /** 权限授予后从 UI 调用（rememberLauncherForActivityResult 的回调） */
    fun onPermissionResult(granted: Boolean) {
        _uiState.value = when {
            !granted -> UiState.NeedPermission
            !hasCounterSensor() -> UiState.NoSensor
            else -> {
                startService()
                UiState.Loading
            }
        }
    }

    private fun startService() {
        _uiState.value = UiState.Loading
        WalkForegroundService.start(app, sceneId)
        val ok = app.bindService(
            Intent(app, WalkForegroundService::class.java),
            connection,
            Context.BIND_AUTO_CREATE,
        )
        if (!ok) {
            _uiState.value = UiState.Error("无法启动实走服务，请回到首页改用虚走")
        }
    }

    private fun mirrorFlows(b: WalkForegroundService.LocalBinder) {
        viewModelScope.launch {
            b.uiState.collect { state ->
                _uiState.value = when (state) {
                    is WalkForegroundService.UiState.Loading -> UiState.Loading
                    is WalkForegroundService.UiState.Ready -> UiState.Ready(state.sceneName)
                    is WalkForegroundService.UiState.Error -> UiState.Error(state.message)
                }
            }
        }
        viewModelScope.launch { b.walk.collect { _walk.value = it } }
        viewModelScope.launch {
            settings.collect { b.setVibrationEnabled(it.vibrationEnabled) }
        }
    }

    fun pauseForDialog() = binder?.pauseForDialog()
    fun resumeFromDialog() = binder?.resumeFromDialog()
    fun abandon() = binder?.abandon()

    private fun hasPermission(): Boolean =
        ContextCompat.checkSelfPermission(app, Manifest.permission.ACTIVITY_RECOGNITION) ==
            PackageManager.PERMISSION_GRANTED

    private fun hasCounterSensor(): Boolean =
        app.getSystemService(SensorManager::class.java)
            ?.getDefaultSensor(android.hardware.Sensor.TYPE_STEP_COUNTER) != null

    override fun onCleared() {
        if (bound) runCatching { app.unbindService(connection) }
        super.onCleared()
    }
}

/**
 * 实走会话页：视觉/米数/放弃/暂停复用虚走组件；下半区不是摇杆，
 * 而是「收进口袋走吧」的状态区（无输入控件，计步由服务驱动）。
 */
@Composable
fun RealWalkSessionScreen(
    vm: RealWalkViewModel,
    sceneId: String,
    onFinished: (outcome: String, meters: Int, elapsedMs: Long) -> Unit,
    onBack: () -> Unit,
) {
    val uiState by vm.uiState.collectAsState()
    val walk by vm.walk.collectAsState()
    val settings by vm.settings.collectAsState()

    when (val state = uiState) {
        is RealWalkViewModel.UiState.Loading -> Box(
            Modifier
                .fillMaxSize()
                .background(SenseBlack),
            contentAlignment = Alignment.Center,
        ) {
            Text("正在准备实走…", color = SenseMuted)
        }

        is RealWalkViewModel.UiState.NeedPermission -> Column(
            Modifier
                .fillMaxSize()
                .background(SenseBlack)
                .padding(28.dp),
            verticalArrangement = Arrangement.Center,
        ) {
            Text("需要活动识别权限", style = MaterialTheme.typography.titleLarge, color = SenseOnSurface)
            Text(
                "计步只在设备上完成，不上传、不定位。拒绝也可以用虚走。",
                style = MaterialTheme.typography.bodySmall,
                color = SenseMuted,
                modifier = Modifier.padding(vertical = 12.dp),
            )
            val context = LocalContext.current
            PermissionRequestButton(context, vm)
            Spacer(Modifier.height(8.dp))
            Button(onClick = onBack) { Text("回首页改用虚走") }
        }

        is RealWalkViewModel.UiState.NoSensor -> Column(
            Modifier
                .fillMaxSize()
                .background(SenseBlack)
                .padding(28.dp),
            verticalArrangement = Arrangement.Center,
        ) {
            Text("这台设备没有计步传感器", style = MaterialTheme.typography.titleLarge, color = SenseOnSurface)
            Text(
                "TYPE_STEP_COUNTER 不可用，无法诚实计距。虚走不受影响。",
                style = MaterialTheme.typography.bodySmall,
                color = SenseMuted,
                modifier = Modifier.padding(vertical = 12.dp),
            )
            Button(onClick = onBack) { Text("回首页改用虚走") }
        }

        is RealWalkViewModel.UiState.Error -> Column(
            Modifier
                .fillMaxSize()
                .background(SenseBlack)
                .padding(28.dp),
            verticalArrangement = Arrangement.Center,
        ) {
            Text("暂时走不了", style = MaterialTheme.typography.titleLarge, color = SenseOnSurface)
            Text(state.message, style = MaterialTheme.typography.bodySmall, color = SenseMuted,
                modifier = Modifier.padding(vertical = 12.dp))
            Button(onClick = onBack) { Text("返回") }
        }

        is RealWalkViewModel.UiState.Ready -> {
            // 终态导航（与虚走同型）
            var navigated by remember { mutableStateOf(false) }
            LaunchedEffect(walk?.session) {
                val session = walk?.session ?: return@LaunchedEffect
                if (!navigated && (session == SessionState.COMPLETED || session == SessionState.ABANDONED)) {
                    navigated = true
                    val snap = walk ?: return@LaunchedEffect
                    onFinished(
                        if (session == SessionState.COMPLETED) {
                            com.sensewalk.app.ui.navigation.NavRoutes.Outcome.COMPLETED
                        } else {
                            com.sensewalk.app.ui.navigation.NavRoutes.Outcome.ABANDONED
                        },
                        snap.meters.toInt(),
                        snap.elapsedActiveMs,
                    )
                }
            }

            // 页面离开（回首页/系统返回）时若仍在走，暂停会话（交由通知栏恢复/停止）
            DisposableEffect(Unit) {
                onDispose {
                    if (walk?.session == SessionState.WALKING) vm.pauseForDialog()
                }
            }

            RealWalkContent(
                vm = vm,
                sceneId = sceneId,
                sceneName = state.sceneName,
                walk = walk,
                reduceMotion = settings.reduceMotion,
            )
        }
    }
}

@Composable
private fun PermissionRequestButton(context: Context, vm: RealWalkViewModel) {
    val launcher = androidx.activity.compose.rememberLauncherForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.RequestPermission(),
    ) { granted -> vm.onPermissionResult(granted) }
    Button(
        onClick = { launcher.launch(Manifest.permission.ACTIVITY_RECOGNITION) },
        modifier = Modifier
            .fillMaxWidth()
            .height(52.dp),
        colors = ButtonDefaults.buttonColors(containerColor = AccentSoft, contentColor = SenseBlack),
    ) {
        Text("授予权限并开始")
    }
}

/** 导航入口：按 sceneId 建 VM（重建不重复建服务会话——引擎在服务里） */
@Composable
fun RealWalkSession(
    sceneId: String,
    onFinished: (outcome: String, meters: Int, elapsedMs: Long) -> Unit,
    onBack: () -> Unit,
) {
    val vm: RealWalkViewModel = viewModel(
        key = "real-walk-$sceneId",
        factory = viewModelFactory {
            initializer {
                RealWalkViewModel(this[APPLICATION_KEY] as Application, sceneId)
            }
        },
    )
    RealWalkSessionScreen(
        vm = vm,
        sceneId = sceneId,
        onFinished = onFinished,
        onBack = onBack,
    )
}
