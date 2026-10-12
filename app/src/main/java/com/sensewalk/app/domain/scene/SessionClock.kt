package com.sensewalk.app.domain.scene

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Session clock for Week 1 silence-only sessions.
 *
 * Starts in pure silence. [elapsedSeconds] always advances from start.
 * UI may hide the clock until the user taps once ([clockVisible]).
 * Long-press end is handled by the UI; call [stop] when ending.
 */
class SessionClock(
    private val scope: CoroutineScope,
    val silenceSeconds: Int = DEFAULT_SILENCE_SECONDS,
) {
    private val _elapsedSeconds = MutableStateFlow(0L)
    val elapsedSeconds: StateFlow<Long> = _elapsedSeconds.asStateFlow()

    private val _isRunning = MutableStateFlow(false)
    val isRunning: StateFlow<Boolean> = _isRunning.asStateFlow()

    private val _clockVisible = MutableStateFlow(false)
    val clockVisible: StateFlow<Boolean> = _clockVisible.asStateFlow()

    /** True while still in the configured silence window (no audio/haptics yet). */
    val isInSilence: Boolean
        get() = _elapsedSeconds.value < silenceSeconds

    private var tickerJob: Job? = null

    fun start() {
        if (_isRunning.value) return
        _elapsedSeconds.value = 0L
        _clockVisible.value = false
        _isRunning.value = true
        tickerJob = scope.launch {
            while (isActive && _isRunning.value) {
                delay(1000L)
                if (_isRunning.value) {
                    _elapsedSeconds.value = _elapsedSeconds.value + 1
                }
            }
        }
    }

    fun revealClock() {
        _clockVisible.value = true
    }

    fun toggleClockVisibility() {
        _clockVisible.value = !_clockVisible.value
    }

    fun stop() {
        _isRunning.value = false
        tickerJob?.cancel()
        tickerJob = null
    }

    companion object {
        const val DEFAULT_SILENCE_SECONDS = 60
    }
}
