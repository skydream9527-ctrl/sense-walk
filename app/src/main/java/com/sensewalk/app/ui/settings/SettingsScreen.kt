package com.sensewalk.app.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.sensewalk.app.data.UserSettings
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface

/**
 * 设置页（§12.4 设置项重做）：静默秒数（时间驱动遗留）已移除。
 * 音频/振动引擎仍是日志 stub（T05 接真实引擎），振动开关此刻只保存偏好。
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    settings: UserSettings,
    onVibrationChange: (Boolean) -> Unit,
    onRhythmHintChange: (Boolean) -> Unit,
    onReduceMotionChange: (Boolean) -> Unit,
    onHoldToWalkChange: (Boolean) -> Unit,
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
                .padding(horizontal = 20.dp)
                .verticalScroll(rememberScrollState()),
        ) {
            SettingSwitch(
                title = "振动",
                subtitle = "跟脚步的轻微振动（真实振动引擎将在下一版接入）",
                checked = settings.vibrationEnabled,
                onChange = onVibrationChange,
            )
            SettingSwitch(
                title = "节奏提示",
                subtitle = "进入舒适区时，摇杆圆点变暖色",
                checked = settings.rhythmHint,
                onChange = onRhythmHintChange,
            )
            SettingSwitch(
                title = "减少动效",
                subtitle = "关闭视差滚动与角色起伏；不影响距离与景色解锁",
                checked = settings.reduceMotion,
                onChange = onReduceMotionChange,
            )
            SettingSwitch(
                title = "按住前进",
                subtitle = "无障碍替代操作：按住按钮以舒适速度前进，松开即停（不会自动行走）",
                checked = settings.holdToWalk,
                onChange = onHoldToWalkChange,
            )
            Spacer(Modifier.height(24.dp))
        }
    }
}

@Composable
private fun SettingSwitch(
    title: String,
    subtitle: String,
    checked: Boolean,
    onChange: (Boolean) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 12.dp)
            .semantics(mergeDescendants = true) {
                contentDescription = "$title：${if (checked) "已开启" else "已关闭"}。$subtitle"
            },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge, color = SenseOnSurface)
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = SenseMuted,
                modifier = Modifier.padding(top = 2.dp),
            )
        }
        Switch(checked = checked, onCheckedChange = onChange)
    }
}
