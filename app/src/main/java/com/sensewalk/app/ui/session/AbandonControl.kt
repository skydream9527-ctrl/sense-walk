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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.onClick
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface
import kotlinx.coroutines.android.awaitFrame

/**
 * 放弃控件（§11.1）：长按 1.5 s 确认放弃，带进度反馈；提前松手或取消则不放弃。
 * 轻点（含无障碍点击动作）打开与系统返回相同的「继续/放弃」确认对话框。
 *
 * 稳健性约定：
 * - 长按进度用单调帧时间累计：进后台无帧即冻结，回来不补满；
 * - 松手/手势取消/禁用/离开页面都经 try/finally 复位；
 * - 长按完成后松手不再打开确认框；
 * - 进度条是纯 UI 时间反馈，与距离/门禁无关。
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
    var heldNanos by remember { mutableStateOf(0f) }
    var holdCompleted by remember { mutableStateOf(false) }

    val currentOnAbandon by rememberUpdatedState(onAbandon)
    val currentOnOpenDialog by rememberUpdatedState(onOpenConfirmDialog)
    val currentEnabled by rememberUpdatedState(enabled)

    LaunchedEffect(holding, enabled) {
        if (holding && enabled) {
            try {
                var last = awaitFrame()
                while (progress < 1f) {
                    // 单调帧时间：后台/无帧时挂起，进度冻结不补算
                    val now = awaitFrame()
                    val dtNanos = (now - last).coerceAtLeast(0L)
                    heldNanos += dtNanos
                    progress = (progress + dtNanos / 1_000_000f / holdMillis).coerceAtMost(1f)
                    last = now
                }
                holdCompleted = true
                currentOnAbandon()
            } finally {
                holding = false
                progress = 0f
            }
        } else {
            progress = 0f
        }
    }

    val progressAnimated by animateFloatAsState(targetValue = progress, label = "abandonProgress")

    Box(
        modifier = modifier
            .semantics {
                contentDescription = "放弃本局：长按 1.5 秒确认放弃；轻点打开继续或放弃的确认对话框"
                onClick(label = "打开放弃确认对话框") {
                    if (currentEnabled) currentOnOpenDialog()
                    true
                }
            }
            .pointerInput(enabled) {
                awaitEachGesture {
                    val down = awaitFirstDown(requireUnconsumed = false)
                    holdCompleted = false
                    heldNanos = 0f
                    holding = true
                    down.consume()
                    try {
                        while (true) {
                            val event = awaitPointerEvent()
                            val change = event.changes.firstOrNull { it.id == down.id } ?: break
                            if (!change.pressed) break // 松手或系统取消
                            change.consume()
                        }
                    } finally {
                        holding = false
                        // 只有「未完成长按」的短按（<300ms）才当轻点；长按完成后松手不弹框
                        if (currentEnabled && !holdCompleted && heldNanos < 300_000_000f) {
                            currentOnOpenDialog()
                        }
                        holdCompleted = false
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
