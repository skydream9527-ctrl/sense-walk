package com.sensewalk.app.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.sensewalk.app.data.UserSettings
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    settings: UserSettings,
    onSilenceSecondsChange: (Int) -> Unit,
    onVibrationChange: (Boolean) -> Unit,
    onBack: () -> Unit,
) {
    Scaffold(
        containerColor = SenseBlack,
        topBar = {
            TopAppBar(
                title = { Text("设置") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "返回",
                            tint = SenseOnSurface,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = SenseBlack,
                    titleContentColor = SenseOnSurface,
                ),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 20.dp),
        ) {
            Text(
                text = "静默秒数",
                style = MaterialTheme.typography.titleMedium,
                color = SenseOnSurface,
            )
            Text(
                text = "开始后前 ${settings.silenceSeconds} 秒保持完全安静（默认 60）",
                style = MaterialTheme.typography.bodySmall,
                color = SenseMuted,
                modifier = Modifier.padding(top = 4.dp, bottom = 8.dp),
            )
            Slider(
                value = settings.silenceSeconds.toFloat(),
                onValueChange = { onSilenceSecondsChange(it.roundToInt()) },
                valueRange = 0f..180f,
                steps = 35, // 5-second increments roughly
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(modifier = Modifier.height(28.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "振动",
                        style = MaterialTheme.typography.titleMedium,
                        color = SenseOnSurface,
                    )
                    Text(
                        text = "总开关（Week 3 起生效）",
                        style = MaterialTheme.typography.bodySmall,
                        color = SenseMuted,
                    )
                }
                Switch(
                    checked = settings.vibrationEnabled,
                    onCheckedChange = onVibrationChange,
                )
            }
        }
    }
}
