package com.sensewalk.app.domain.audio

import android.util.Log

/**
 * Week-1 stub. Real multi-track fade-in arrives in Week 2.
 * Silence-only sessions must work without this doing anything.
 */
class AudioMixer {
    fun prepare(layerId: String, assetPath: String, loop: Boolean) {
        Log.d(TAG, "prepare layer=$layerId path=$assetPath loop=$loop (stub)")
    }

    fun fadeIn(layerId: String, toVolume: Float, fadeMs: Int) {
        Log.d(TAG, "fadeIn layer=$layerId to=$toVolume fadeMs=$fadeMs (stub)")
    }

    fun fadeOut(layerId: String, fadeMs: Int) {
        Log.d(TAG, "fadeOut layer=$layerId fadeMs=$fadeMs (stub)")
    }

    fun setMasterVolume(volume: Float) {
        Log.d(TAG, "setMasterVolume=$volume (stub)")
    }

    fun release() {
        Log.d(TAG, "release (stub)")
    }

    companion object {
        private const val TAG = "AudioMixer"
    }
}
