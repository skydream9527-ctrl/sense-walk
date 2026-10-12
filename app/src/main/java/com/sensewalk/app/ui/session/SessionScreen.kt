package com.sensewalk.app.ui.session

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.sensewalk.app.domain.audio.AudioMixer
import com.sensewalk.app.domain.haptics.HapticEngine
import com.sensewalk.app.domain.scene.Scene
import com.sensewalk.app.domain.scene.SessionClock
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface
import com.sensewalk.app.ui.theme.sceneTint
import kotlinx.coroutines.withTimeoutOrNull

@Composable
fun SessionScreen(
    scene: Scene,
    silenceSeconds: Int,
    vibrationEnabled: Boolean,
    onEnd: (elapsedSeconds: Long) -> Unit,
) {
    val scope = rememberCoroutineScope()
    val clock = remember(silenceSeconds) {
        SessionClock(scope = scope, silenceSeconds = silenceSeconds)
    }
    val audioMixer = remember { AudioMixer() }
    val hapticEngine = remember(vibrationEnabled) { HapticEngine(enabled = vibrationEnabled) }
    val currentOnEnd by rememberUpdatedState(onEnd)

    val elapsed by clock.elapsedSeconds.collectAsStateWithLifecycle()
    val clockVisible by clock.clockVisible.collectAsStateWithLifecycle()

    LaunchedEffect(clock) {
        scene.layers.forEach { (id, layer) ->
            audioMixer.prepare(id, layer.file, layer.loop)
        }
        clock.start()
    }

    DisposableEffect(Unit) {
        onDispose {
            clock.stop()
            audioMixer.release()
            hapticEngine.stop()
        }
    }

    fun endSession() {
        val secs = clock.elapsedSeconds.value
        clock.stop()
        audioMixer.release()
        hapticEngine.stop()
        currentOnEnd(secs)
    }

    val bg = blend(SenseBlack.copy(alpha = 0.95f), sceneTint(scene.id).copy(alpha = 0.15f))

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(bg)
            .pointerInput(Unit) {
                awaitEachGesture {
                    awaitFirstDown(requireUnconsumed = false)
                    val upBeforeTimeout = withTimeoutOrNull(1_000L) {
                        waitForUpOrCancellation()
                    }
                    if (upBeforeTimeout == null) {
                        // Held ≥ 1s → end session, then wait for finger up
                        endSession()
                        waitForUpOrCancellation()
                    } else {
                        clock.toggleClockVisibility()
                    }
                }
            },
        contentAlignment = Alignment.Center,
    ) {
        if (clockVisible) {
            Text(
                text = formatElapsed(elapsed),
                style = MaterialTheme.typography.displayMedium,
                color = SenseOnSurface.copy(alpha = 0.85f),
                fontWeight = FontWeight.Light,
            )
        }

        Text(
            text = if (clockVisible) "长按结束" else "轻触显示时间 · 长按结束",
            style = MaterialTheme.typography.labelMedium,
            color = SenseMuted.copy(alpha = 0.55f),
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 48.dp),
        )
    }
}

private fun formatElapsed(totalSeconds: Long): String {
    val m = totalSeconds / 60
    val s = totalSeconds % 60
    return "%d:%02d".format(m, s)
}

private fun blend(over: Color, under: Color): Color {
    val a = over.alpha
    return Color(
        red = over.red * a + under.red * (1 - a),
        green = over.green * a + under.green * (1 - a),
        blue = over.blue * a + under.blue * (1 - a),
        alpha = 1f,
    )
}
