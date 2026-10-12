package com.sensewalk.app.session

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.sensewalk.app.data.SceneRepository
import com.sensewalk.app.data.SettingsRepository
import com.sensewalk.app.data.UserSettings
import com.sensewalk.app.domain.scene.SceneLoadState
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.walk.VirtualWalkController
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * 会话 ViewModel（T04）：持有 [VirtualWalkController] 作为唯一状态来源。
 *
 * - 作用域为会话导航条目：离开会话/再走一次时销毁，天然全新会话；
 * - Compose 只调用 [onFrame]/输入方法并渲染 [walk] 快照，不持有任何行走逻辑；
 * - 场景配置缺失或加载失败给出可解释错误页，不进入会话。
 */
class SessionViewModel(
    application: Application,
    private val sceneId: String,
) : AndroidViewModel(application) {

    sealed interface UiState {
        data object Loading : UiState
        data class Ready(val controller: VirtualWalkController) : UiState
        data class Error(val message: String) : UiState
    }

    private val sceneRepository = SceneRepository(application)
    private val settingsRepository = SettingsRepository(application)

    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    /** 每帧/每次输入后的会话快照；null = 会话未就绪 */
    private val _walk = MutableStateFlow<VirtualWalkController.Snapshot?>(null)
    val walk: StateFlow<VirtualWalkController.Snapshot?> = _walk.asStateFlow()

    val settings: StateFlow<UserSettings> = settingsRepository.settings
        .stateIn(viewModelScope, SharingStarted.Eagerly, UserSettings())

    private val systemClock = MonotonicClock { System.nanoTime() / 1_000_000 }

    init {
        viewModelScope.launch {
            when (val state = sceneRepository.loadAll()) {
                is SceneLoadState.Error -> _uiState.value = UiState.Error(
                    "场景配置加载失败：\n" + state.diagnostics.joinToString("\n"),
                )
                is SceneLoadState.Ready -> {
                    val config = state.scenes.firstOrNull { it.id == sceneId }
                    if (config == null) {
                        _uiState.value = UiState.Error("场景不可用：'$sceneId' 不在已加载的场景中")
                    } else {
                        val controller = VirtualWalkController(config, systemClock)
                        _uiState.value = UiState.Ready(controller)
                        _walk.value = controller.snapshot()
                    }
                }
                SceneLoadState.Loading -> Unit
            }
        }
    }

    private fun withController(block: (VirtualWalkController) -> Unit) {
        (uiState.value as? UiState.Ready)?.let { block(it.controller) }
    }

    /** 唯一帧驱动入口（由 SessionScreen 的单个 LaunchedEffect 帧循环调用） */
    fun onFrame() = withController { controller ->
        _walk.value = controller.frame()
    }

    fun onStick(deflection: Float) = withController {
        it.onStick(deflection)
        _walk.value = it.snapshot()
    }

    fun onStickReleased() = withController {
        it.onStickReleased()
        _walk.value = it.snapshot()
    }

    fun onAppBackground() = withController {
        it.onAppBackground()
        _walk.value = it.snapshot()
    }

    fun onAppForeground() = withController {
        it.onAppForeground()
        _walk.value = it.snapshot()
    }

    fun pauseForDialog() = withController {
        it.pause()
        _walk.value = it.snapshot()
    }

    fun resumeFromDialog() = withController {
        it.resume()
        _walk.value = it.snapshot()
    }

    fun abandon() = withController {
        it.abandon()
        _walk.value = it.snapshot()
    }
}
