package com.sensewalk.app.ui.session

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.sensewalk.app.ui.navigation.NavRoutes
import com.sensewalk.app.ui.theme.AccentSoft
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface

/**
 * 结果页（§11.2）：明确 Completed / Abandoned，显示实际米数；
 * 用时默认折叠（开放决策 #14）；不评判、不显示还差多少米。
 */
@Composable
fun ResultScreen(
    sceneName: String,
    requiredDistanceMeters: Int,
    outcome: String,
    meters: Int,
    elapsedMs: Long,
    onWalkAgain: () -> Unit,
    onHome: () -> Unit,
) {
    val completed = outcome == NavRoutes.Outcome.COMPLETED
    var elapsedExpanded by remember { mutableStateOf(false) }
    val elapsedMinutes = (elapsedMs / 60_000).toInt()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(SenseBlack)
            .padding(horizontal = 28.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = sceneName,
            style = MaterialTheme.typography.labelLarge,
            color = SenseMuted,
        )
        Spacer(Modifier.height(16.dp))
        Text(
            text = if (completed) "走到了" else "这次先到这里",
            style = MaterialTheme.typography.headlineMedium,
            color = SenseOnSurface,
            fontWeight = FontWeight.Medium,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(10.dp))
        Text(
            text = if (completed) {
                "走完 $requiredDistanceMeters m"
            } else {
                "这次走了 $meters m"
            },
            style = MaterialTheme.typography.bodyLarge,
            color = SenseOnSurface.copy(alpha = 0.85f),
            textAlign = TextAlign.Center,
            modifier = Modifier.semantics {
                contentDescription = if (completed) "通关：走完 $requiredDistanceMeters 米" else "本局走了 $meters 米，下次想走的时候再来"
            },
        )
        if (!completed) {
            Text(
                text = "想走的时候再来。",
                style = MaterialTheme.typography.bodySmall,
                color = SenseMuted,
                modifier = Modifier.padding(top = 4.dp),
            )
        }

        Spacer(Modifier.height(20.dp))
        // 用时折叠（开放决策 #14）：点一下才展开，避免变成速度成绩
        Row(
            modifier = Modifier
                .clickable { elapsedExpanded = !elapsedExpanded }
                .semantics {
                    contentDescription = if (elapsedExpanded) "用时已展开：约 $elapsedMinutes 分钟，点按折叠" else "查看用时（默认折叠）"
                }
                .padding(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = if (elapsedExpanded) "用时 · 约 $elapsedMinutes 分钟 ▴" else "用时 ▾",
                style = MaterialTheme.typography.labelMedium,
                color = SenseMuted,
            )
        }

        Spacer(Modifier.height(40.dp))
        Button(
            onClick = onWalkAgain,
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = AccentSoft,
                contentColor = SenseBlack,
            ),
            shape = RoundedCornerShape(14.dp),
        ) {
            Text("再走一次", style = MaterialTheme.typography.titleMedium)
        }
        Spacer(Modifier.height(12.dp))
        OutlinedButton(
            onClick = onHome,
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            shape = RoundedCornerShape(14.dp),
        ) {
            Text("回到首页", style = MaterialTheme.typography.titleMedium, color = SenseOnSurface)
        }
    }
}
