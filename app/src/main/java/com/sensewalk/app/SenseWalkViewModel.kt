package com.sensewalk.app

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.sensewalk.app.data.SceneRepository
import com.sensewalk.app.data.SettingsRepository
import com.sensewalk.app.data.UserSettings
import com.sensewalk.app.domain.scene.Scene
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class SenseWalkViewModel(application: Application) : AndroidViewModel(application) {

    private val sceneRepository = SceneRepository(application)
    private val settingsRepository = SettingsRepository(application)

    val scenes: StateFlow<List<Scene>> = kotlinx.coroutines.flow.flow {
        emit(sceneRepository.loadAll())
    }.stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())

    val settings: StateFlow<UserSettings> = settingsRepository.settings
        .stateIn(viewModelScope, SharingStarted.Eagerly, UserSettings())

    fun setSilenceSeconds(seconds: Int) {
        viewModelScope.launch { settingsRepository.setSilenceSeconds(seconds) }
    }

    fun setVibrationEnabled(enabled: Boolean) {
        viewModelScope.launch { settingsRepository.setVibrationEnabled(enabled) }
    }
}
