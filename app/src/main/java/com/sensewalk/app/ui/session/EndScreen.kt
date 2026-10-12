package com.sensewalk.app.ui.session

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.sensewalk.app.ui.theme.AccentSoft
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface

@Composable
fun EndScreen(
    sceneName: String,
    elapsedSeconds: Long,
    onWalkAgain: () -> Unit,
    onHome: () -> Unit,
) {
    val minutes = (elapsedSeconds / 60).toInt()
    val line = when {
        elapsedSeconds < 60 -> "你安静地走了不到一分钟"
        minutes == 1 -> "你安静地走了 1 分钟"
        else -> "你安静地走了 $minutes 分钟"
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 28.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = sceneName,
            style = MaterialTheme.typography.labelLarge,
            color = SenseMuted,
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = line,
            style = MaterialTheme.typography.headlineSmall,
            color = SenseOnSurface,
            fontWeight = FontWeight.Medium,
            textAlign = TextAlign.Center,
        )
        Spacer(modifier = Modifier.height(48.dp))
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
        Spacer(modifier = Modifier.height(12.dp))
        OutlinedButton(
            onClick = onHome,
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            shape = RoundedCornerShape(14.dp),
        ) {
            Text("回首页", style = MaterialTheme.typography.titleMedium, color = SenseOnSurface)
        }
    }
}
