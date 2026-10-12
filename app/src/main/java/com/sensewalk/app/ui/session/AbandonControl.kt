package com.sensewalk.app.ui.session

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface
import kotlinx.coroutines.android.awaitFrame

/**
 * 放弃控件（§11.1）：长按 1.5 s 确认放弃，带进度反馈；提前松手取消。
 * 轻点打开与系统返回相同的「继续/放弃」确认对话框（无障碍等价操作）。
 *
 * 注意：进度条是纯 UI 时间反馈，与距离/门禁无关。
 */
@Composable
fun AbandonControl(
    enabled: Boolean,
    holdMillis: Long = 1_500L,
    onAbandon: () -> Unit,
    onOpenConfirmDialog: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var holding by remember { mutableStateOf(false) }
    var progress by remember { mutableFloatStateOf(0f) }
    var downTimeMs by remember { mutableLongStateOf(0L) }

    LaunchedEffect(holding, enabled) {
        if (holding && enabled) {
            var last = awaitFrame()
            while (progress < 1f) {
                val now = awaitFrame()
                progress += ((now - last) / holdMillis / 1_000_000f).coerceAtLeast(0f)
                last = now
            }
            holding = false
            progress = 0f
            onAbandon()
        } else {
            progress = 0f
        }
    }

    val progressAnimated by animateFloatAsState(targetValue = progress, label = "abandonProgress")

    Box(
        modifier = modifier
            .semantics {
                contentDescription = "放弃本局：长按 1.5 秒确认放弃；轻点可打开继续或放弃的确认对话框"
            }
            .pointerInput(enabled) {
                awaitEachGesture {
                    val down = awaitFirstDown(requireUnconsumed = false)
                    downTimeMs = System.currentTimeMillis()
                    holding = true
                    down.consume()
                    while (true) {
                        val event = awaitPointerEvent()
                        val change = event.changes.firstOrNull { it.id == down.id } ?: break
                        if (!change.pressed) break
                        change.consume()
                    }
                    val held = System.currentTimeMillis() - downTimeMs
                    holding = false
                    // 短按（未到 300ms 且未完成长按）= 无障碍等价：打开确认对话框
                    if (enabled && held < 300L && progress < 1f) {
                        onOpenConfirmDialog()
                    }
                }
            }
            .background(
                color = Color.White.copy(alpha = 0.06f),
                shape = RoundedCornerShape(20.dp),
            )
            .padding(horizontal = 16.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = "长按放弃",
                style = MaterialTheme.typography.labelMedium,
                color = SenseMuted,
            )
            LinearProgressIndicator(
                progress = { progressAnimated },
                modifier = Modifier
                    .padding(top = 6.dp)
                    .width(72.dp)
                    .height(3.dp),
                color = SenseOnSurface.copy(alpha = 0.8f),
                trackColor = Color.White.copy(alpha = 0.12f),
            )
        }
    }
}
