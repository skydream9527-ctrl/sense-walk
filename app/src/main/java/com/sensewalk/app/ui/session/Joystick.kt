package com.sensewalk.app.ui.session

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import kotlin.math.sqrt

/**
 * 浮动摇杆（§4.3.3）：手指在激活区内任意位置按下，摇杆出现在那里。
 *
 * - 本组件只占据屏幕下方 45% 的实体区域（由调用方用 Modifier 约束），
 *   不拦截上方米数/暂停/放弃控件的触摸；
 * - 底座半径 56dp、拇指圆点 22dp，半透明，无刻度数值；
 * - 前进 = 向右：d = (len/底座半径) × max(0, cosθ)，左推为 0；
 * - 只跟踪首个按下的指针（多指不叠加）；松手/手势取消/禁用/离开页面
 *   都通过 try/finally 与 DisposableEffect 释放输入，不会卡住；
 * - 甜点区（0.45–0.65）拇指圆点变暖色（rhythmHint 关闭时不变色）。
 */
@Composable
fun JoystickZone(
    rhythmHint: Boolean,
    onDeflection: (Float) -> Unit,
    onReleased: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var basePos by remember { mutableStateOf(Offset.Zero) }
    var thumbPos by remember { mutableStateOf(Offset.Zero) }
    var active by remember { mutableStateOf(false) }
    var deflection by remember { mutableStateOf(0f) }

    val currentOnDeflection by rememberUpdatedState(onDeflection)
    val currentOnReleased by rememberUpdatedState(onReleased)

    // 离开页面/重组销毁时释放输入
    DisposableEffect(Unit) {
        onDispose { currentOnReleased() }
    }

    val density = LocalDensity.current
    val baseRadius = with(density) { 56.dp.toPx() }
    val thumbRadius = with(density) { 22.dp.toPx() }

    Box(
        modifier = modifier
            .semantics {
                contentDescription = "虚拟摇杆：按住并向右推动控制前进。推满不会更快，中间偏右的舒适区最快"
            }
            .pointerInput(rhythmHint) {
                awaitEachGesture {
                    // 只接手未被其他控件（按住前进等）消费的按下
                    val down = awaitFirstDown(requireUnconsumed = true, pass = PointerEventPass.Main)
                    active = true
                    basePos = down.position
                    thumbPos = down.position
                    deflection = 0f
                    down.consume()
                    try {
                        while (true) {
                            val event = awaitPointerEvent(PointerEventPass.Main)
                            val change = event.changes.firstOrNull { it.id == down.id } ?: break
                            val dx = change.position.x - basePos.x
                            val dy = change.position.y - basePos.y
                            val len = sqrt(dx * dx + dy * dy)
                            val lenNormalized = (len / baseRadius).coerceAtMost(1f)
                            val cosTheta = if (len > 0.001f) dx / len else 0f
                            deflection = (lenNormalized * cosTheta.coerceAtLeast(0f)).coerceIn(0f, 1f)
                            // 移出底座范围：拇指钳制在底座内，输入保持有界
                            thumbPos = basePos + Offset(
                                dx.coerceIn(-baseRadius, baseRadius),
                                dy.coerceIn(-baseRadius, baseRadius),
                            )
                            currentOnDeflection(deflection)
                            if (!change.pressed) break // 松手或系统手势取消
                            change.consume()
                        }
                    } finally {
                        active = false
                        deflection = 0f
                        currentOnReleased()
                    }
                }
            },
    ) {
        if (active) {
            Canvas(Modifier.fillMaxSize()) {
                drawCircle(
                    color = Color.White.copy(alpha = 0.10f),
                    radius = baseRadius,
                    center = basePos,
                )
                drawCircle(
                    color = Color.White.copy(alpha = 0.16f),
                    radius = baseRadius,
                    center = basePos,
                    style = Stroke(width = 2f),
                )
                val inSweetSpot = deflection in 0.45f..0.65f
                val thumbColor = when {
                    inSweetSpot && rhythmHint -> Color(0xFFA8C5A0).copy(alpha = 0.85f)
                    else -> Color.White.copy(alpha = 0.45f)
                }
                drawCircle(color = thumbColor, radius = thumbRadius, center = thumbPos)
            }
        }
    }
}
