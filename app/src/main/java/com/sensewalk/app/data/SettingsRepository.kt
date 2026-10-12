package com.sensewalk.app.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "sensewalk_settings")

/**
 * 用户设置（§12.4 设置项重做）。
 * silenceSeconds（时间驱动遗留）已删除；新增节奏提示、减少动效、按住前进与上次选择。
 */
data class UserSettings(
    val vibrationEnabled: Boolean = true,
    val rhythmHint: Boolean = true,
    val reduceMotion: Boolean = false,
    val holdToWalk: Boolean = false,
    val lastSceneId: String? = null,
    val lastMode: String? = null,
)

class SettingsRepository(private val context: Context) {

    private object Keys {
        val VIBRATION_ENABLED = booleanPreferencesKey("vibration_enabled")
        val RHYTHM_HINT = booleanPreferencesKey("rhythm_hint")
        val REDUCE_MOTION = booleanPreferencesKey("reduce_motion")
        val HOLD_TO_WALK = booleanPreferencesKey("hold_to_walk")
        val LAST_SCENE_ID = stringPreferencesKey("last_scene_id")
        val LAST_MODE = stringPreferencesKey("last_mode")
    }

    val settings: Flow<UserSettings> = context.dataStore.data.map { prefs ->
        UserSettings(
            vibrationEnabled = prefs[Keys.VIBRATION_ENABLED] ?: true,
            rhythmHint = prefs[Keys.RHYTHM_HINT] ?: true,
            reduceMotion = prefs[Keys.REDUCE_MOTION] ?: false,
            holdToWalk = prefs[Keys.HOLD_TO_WALK] ?: false,
            lastSceneId = prefs[Keys.LAST_SCENE_ID],
            lastMode = prefs[Keys.LAST_MODE],
        )
    }

    suspend fun setVibrationEnabled(enabled: Boolean) {
        context.dataStore.edit { it[Keys.VIBRATION_ENABLED] = enabled }
    }

    suspend fun setRhythmHint(enabled: Boolean) {
        context.dataStore.edit { it[Keys.RHYTHM_HINT] = enabled }
    }

    suspend fun setReduceMotion(enabled: Boolean) {
        context.dataStore.edit { it[Keys.REDUCE_MOTION] = enabled }
    }

    suspend fun setHoldToWalk(enabled: Boolean) {
        context.dataStore.edit { it[Keys.HOLD_TO_WALK] = enabled }
    }

    /** 保存上次可用的场景/模式选择；Home 与模式页默认选中 */
    suspend fun setLastSelection(sceneId: String, mode: String) {
        context.dataStore.edit {
            it[Keys.LAST_SCENE_ID] = sceneId
            it[Keys.LAST_MODE] = mode
        }
    }
}
