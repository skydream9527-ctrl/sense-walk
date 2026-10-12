package com.sensewalk.app.domain.haptics

import android.util.Log

/**
 * Week-1 stub. Vibration patterns arrive in Week 3.
 */
class HapticEngine(
    private val enabled: Boolean = true,
) {
    fun playPattern(pattern: String, intervalMs: Int) {
        if (!enabled) {
            Log.d(TAG, "haptics disabled; skip $pattern")
            return
        }
        Log.d(TAG, "playPattern=$pattern intervalMs=$intervalMs (stub)")
    }

    fun stop() {
        Log.d(TAG, "stop (stub)")
    }

    companion object {
        private const val TAG = "HapticEngine"
    }
}
