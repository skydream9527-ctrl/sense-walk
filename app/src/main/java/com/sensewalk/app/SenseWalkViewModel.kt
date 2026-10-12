package com.sensewalk.app

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.sensewalk.app.data.SceneRepository
import com.sensewalk.app.data.SettingsRepository
import com.sensewalk.app.data.UserSettings
import com.sensewalk.app.domain.scene.SceneLoadState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class SenseWalkViewModel(application: Application) : AndroidViewModel(application) {

    private val sceneRepository = SceneRepository(application)
    private val settingsRepository = SettingsRepository(application)

    private val _sceneState = MutableStateFlow<SceneLoadState>(SceneLoadState.Loading)
    val sceneState: StateFlow<SceneLoadState> = _sceneState.asStateFlow()

    val settings: StateFlow<UserSettings> = settingsRepository.settings
        .stateIn(viewModelScope, SharingStarted.Eagerly, UserSettings())

    init {
        loadScenes()
    }

    /** 首页错误态的重试入口：重新走一遍 读取→解析→校验 */
    fun retrySceneLoad() {
        loadScenes()
    }

    private fun loadScenes() {
        viewModelScope.launch {
            _sceneState.value = SceneLoadState.Loading
            _sceneState.value = sceneRepository.loadAll()
        }
    }

    fun setVibrationEnabled(enabled: Boolean) {
        viewModelScope.launch { settingsRepository.setVibrationEnabled(enabled) }
    }

    fun setRhythmHint(enabled: Boolean) {
        viewModelScope.launch { settingsRepository.setRhythmHint(enabled) }
    }

    fun setReduceMotion(enabled: Boolean) {
        viewModelScope.launch { settingsRepository.setReduceMotion(enabled) }
    }

    fun setHoldToWalk(enabled: Boolean) {
        viewModelScope.launch { settingsRepository.setHoldToWalk(enabled) }
    }

    fun setLastSelection(sceneId: String, mode: String) {
        viewModelScope.launch { settingsRepository.setLastSelection(sceneId, mode) }
    }
}
