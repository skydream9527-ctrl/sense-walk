package com.sensewalk.app.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.sensewalk.app.domain.scene.SessionClock
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "sensewalk_settings")

data class UserSettings(
    val silenceSeconds: Int = SessionClock.DEFAULT_SILENCE_SECONDS,
    val vibrationEnabled: Boolean = true,
)

class SettingsRepository(private val context: Context) {

    private object Keys {
        val SILENCE_SECONDS = intPreferencesKey("silence_seconds")
        val VIBRATION_ENABLED = booleanPreferencesKey("vibration_enabled")
    }

    val settings: Flow<UserSettings> = context.dataStore.data.map { prefs ->
        UserSettings(
            silenceSeconds = prefs[Keys.SILENCE_SECONDS] ?: SessionClock.DEFAULT_SILENCE_SECONDS,
            vibrationEnabled = prefs[Keys.VIBRATION_ENABLED] ?: true,
        )
    }

    suspend fun setSilenceSeconds(seconds: Int) {
        context.dataStore.edit { it[Keys.SILENCE_SECONDS] = seconds.coerceIn(0, 300) }
    }

    suspend fun setVibrationEnabled(enabled: Boolean) {
        context.dataStore.edit { it[Keys.VIBRATION_ENABLED] = enabled }
    }
}
