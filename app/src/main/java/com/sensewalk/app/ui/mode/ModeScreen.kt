package com.sensewalk.app.ui.mode

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.SceneDurationEstimator
import com.sensewalk.app.ui.navigation.NavRoutes
import com.sensewalk.app.ui.theme.AccentSoft
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface
import com.sensewalk.app.ui.theme.sceneTint

/**
 * 模式选择页（§2 流程 ②）：先选场景后选模式，会话中途不可换。
 * T04 仅开放森林虚走；实走与其他场景如实标注「暂未开放」，不进入假会话。
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ModeScreen(
    scene: SceneConfig?,
    sceneLoadError: Boolean,
    lastMode: String?,
    onBack: () -> Unit,
    onStart: (sceneId: String, mode: String) -> Unit,
) {
    // 场景缺失 / 加载失败：可解释页面，不空白
    if (scene == null) {
        Scaffold(containerColor = SenseBlack) { padding ->
            Column(
                Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(28.dp),
                verticalArrangement = Arrangement.Center,
            ) {
                Text(
                    text = if (sceneLoadError) "场景配置加载失败" else "找不到这个场景",
                    style = MaterialTheme.typography.titleLarge,
                    color = SenseOnSurface,
                )
                Text(
                    text = if (sceneLoadError) "配置有问题的场景不会静默隐藏。可以回首页重试。" else "它可能已下线或链接已过期。",
                    style = MaterialTheme.typography.bodySmall,
                    color = SenseMuted,
                    modifier = Modifier.padding(top = 8.dp, bottom = 20.dp),
                )
                Button(onClick = onBack) { Text("回首页") }
            }
        }
        return
    }

    val virtualWalkOpen = scene.id == "forest"
    val realWalkOpen = scene.id == "forest" // T06：森林实走开放（counter 计步 + 前台服务）
    var selectedMode by remember { mutableStateOf(if (virtualWalkOpen) NavRoutes.Mode.VIRTUAL else null) }

    // 恢复上次选择（仅当仍可用）
    LaunchedEffect(lastMode) {
        if (virtualWalkOpen && lastMode == NavRoutes.Mode.VIRTUAL) selectedMode = NavRoutes.Mode.VIRTUAL
        if (realWalkOpen && lastMode == NavRoutes.Mode.REAL) selectedMode = NavRoutes.Mode.REAL
    }

    Scaffold(
        containerColor = SenseBlack,
        topBar = {
            TopAppBar(
                title = { Text("怎么走") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回", tint = SenseOnSurface)
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
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 20.dp)
                .verticalScroll(rememberScrollState()),
        ) {
            Text(
                text = "${scene.name} · ${scene.requiredDistanceMeters} m · 约 ${SceneDurationEstimator.estimatedVirtualMinutes(scene)} 分钟",
                style = MaterialTheme.typography.bodyMedium,
                color = SenseMuted,
                modifier = Modifier.padding(bottom = 16.dp),
            )

            ModeCard(
                title = "虚走 · 手机上走",
                subtitle = if (virtualWalkOpen) {
                    "摇杆控制角色，找舒服的节奏"
                } else {
                    "暂未开放 · 本景正在准备中"
                },
                enabled = virtualWalkOpen,
                selected = selectedMode == NavRoutes.Mode.VIRTUAL,
                onClick = { selectedMode = NavRoutes.Mode.VIRTUAL },
            )
            Spacer(Modifier.height(12.dp))
            ModeCard(
                title = "实走 · 出门走",
                subtitle = if (realWalkOpen) {
                    "计步算距离，锁屏也能走（需活动识别权限）"
                } else {
                    "暂未开放 · 本景正在准备中"
                },
                enabled = realWalkOpen,
                selected = selectedMode == NavRoutes.Mode.REAL,
                onClick = { selectedMode = NavRoutes.Mode.REAL },
            )

            Spacer(Modifier.height(24.dp))
            Button(
                onClick = { selectedMode?.let { onStart(scene.id, it) } },
                enabled = selectedMode != null,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = AccentSoft,
                    contentColor = SenseBlack,
                    disabledContainerColor = SenseMuted.copy(alpha = 0.3f),
                ),
                shape = RoundedCornerShape(14.dp),
            ) {
                Text("开始", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}

@Composable
private fun ModeCard(
    title: String,
    subtitle: String,
    enabled: Boolean,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val shape = RoundedCornerShape(16.dp)
    Box(
        Modifier
            .fillMaxWidth()
            .height(92.dp)
            .clip(shape)
            .background(
                if (enabled) sceneTint("forest").copy(alpha = 0.35f)
                else SenseBlack,
            )
            .then(
                if (selected) Modifier.border(2.dp, AccentSoft, shape)
                else Modifier.border(1.dp, SenseMuted.copy(alpha = if (enabled) 0.25f else 0.12f), shape)
            )
            .clickable(enabled = enabled, onClick = onClick)
            .semantics {
                contentDescription = "$title，$subtitle" + if (selected) "，已选中" else ""
            }
            .padding(20.dp),
        contentAlignment = Alignment.BottomStart,
    ) {
        Column {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                color = if (enabled) SenseOnSurface else SenseMuted,
                fontWeight = FontWeight.Medium,
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = if (enabled) SenseOnSurface.copy(alpha = 0.7f) else SenseMuted.copy(alpha = 0.8f),
                modifier = Modifier.padding(top = 4.dp),
            )
        }
    }
}
