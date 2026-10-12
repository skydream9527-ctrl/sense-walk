package com.sensewalk.app.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import com.sensewalk.app.domain.scene.SceneLoadState
import com.sensewalk.app.ui.theme.AccentSoft
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface
import com.sensewalk.app.ui.theme.sceneTint

/** T04 已开放的虚走场景（其余场景如实标注暂未开放，不进入假会话） */
private val OPEN_VIRTUAL_SCENES = setOf("forest")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    state: SceneLoadState,
    lastSceneId: String?,
    onRetry: () -> Unit,
    onSelectScene: (sceneId: String) -> Unit,
    onOpenSettings: () -> Unit,
) {
    var selectedId by remember { mutableStateOf<String?>(null) }
    val scenes = (state as? SceneLoadState.Ready)?.scenes.orEmpty()
    LaunchedEffect(scenes, lastSceneId) {
        if (selectedId == null || scenes.none { it.id == selectedId }) {
            // 恢复上次可用选择；失效时回退到第一个可用场景
            selectedId = scenes.firstOrNull { it.id == lastSceneId }?.id ?: scenes.firstOrNull()?.id
        }
    }

    Scaffold(
        containerColor = SenseBlack,
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = "慢行",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Medium,
                            color = SenseOnSurface,
                        )
                        Text(
                            text = "SenseWalk",
                            style = MaterialTheme.typography.labelMedium,
                            color = SenseMuted,
                        )
                    }
                },
                actions = {
                    IconButton(onClick = onOpenSettings) {
                        Icon(
                            imageVector = Icons.Outlined.Settings,
                            contentDescription = "设置",
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
        when (state) {
            is SceneLoadState.Loading -> Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentAlignment = Alignment.Center,
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator(color = AccentSoft)
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "正在加载场景…",
                        style = MaterialTheme.typography.bodyMedium,
                        color = SenseMuted,
                    )
                }
            }

            is SceneLoadState.Error -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = 28.dp)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.Center,
            ) {
                Text(
                    text = "场景配置加载失败",
                    style = MaterialTheme.typography.titleLarge,
                    color = SenseOnSurface,
                    fontWeight = FontWeight.Medium,
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "配置有问题的场景不会被静默隐藏。修复配置或重试。",
                    style = MaterialTheme.typography.bodySmall,
                    color = SenseMuted,
                )
                Spacer(modifier = Modifier.height(16.dp))
                state.diagnostics.forEach { line ->
                    Text(
                        text = line,
                        style = MaterialTheme.typography.bodySmall,
                        color = SenseOnSurface.copy(alpha = 0.75f),
                        modifier = Modifier.padding(vertical = 2.dp),
                    )
                }
                Spacer(modifier = Modifier.height(24.dp))
                OutlinedButton(
                    onClick = onRetry,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp),
                    shape = RoundedCornerShape(14.dp),
                ) {
                    Text("重试", color = SenseOnSurface)
                }
            }

            is SceneLoadState.Ready -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = 20.dp),
            ) {
                Text(
                    text = "选一个场景，安静地走一会儿",
                    style = MaterialTheme.typography.bodyMedium,
                    color = SenseMuted,
                    modifier = Modifier.padding(bottom = 16.dp),
                )

                LazyColumn(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    contentPadding = PaddingValues(bottom = 16.dp),
                ) {
                    items(scenes, key = { it.id }) { scene ->
                        val open = scene.id in OPEN_VIRTUAL_SCENES
                        SceneCard(
                            scene = scene,
                            open = open,
                            selected = scene.id == selectedId,
                            onClick = { selectedId = scene.id },
                        )
                    }
                }

                Button(
                    onClick = { selectedId?.let(onSelectScene) },
                    enabled = selectedId != null,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 24.dp)
                        .height(52.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = AccentSoft,
                        contentColor = SenseBlack,
                        disabledContainerColor = SenseMuted.copy(alpha = 0.3f),
                    ),
                    shape = RoundedCornerShape(14.dp),
                ) {
                    Text(
                        text = "下一步 · 怎么走",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }
        }
    }
}

@Composable
private fun SceneCard(
    scene: SceneConfig,
    open: Boolean,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val tint = sceneTint(scene.id)
    val shape = RoundedCornerShape(16.dp)
    val minutes = SceneDurationEstimator.estimatedVirtualMinutes(scene)
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(110.dp)
            .clip(shape)
            .background(if (open) tint.copy(alpha = 0.55f) else tint.copy(alpha = 0.25f))
            .then(
                if (selected) {
                    Modifier.border(2.dp, AccentSoft, shape)
                } else {
                    Modifier.border(1.dp, SenseMuted.copy(alpha = 0.25f), shape)
                }
            )
            .clickable(onClick = onClick)
            .semantics {
                contentDescription = "${scene.name}，${scene.requiredDistanceMeters} 米，约 $minutes 分钟" +
                    if (open) "，可以走" else "，暂未开放"
            }
            .padding(20.dp),
        contentAlignment = Alignment.BottomStart,
    ) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = scene.name,
                    style = MaterialTheme.typography.titleLarge,
                    color = if (open) SenseOnSurface else SenseMuted,
                    fontWeight = FontWeight.Medium,
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    text = if (open) "可虚走" else "暂未开放",
                    style = MaterialTheme.typography.labelSmall,
                    color = if (open) AccentSoft else SenseMuted,
                    modifier = Modifier
                        .background(
                            if (open) AccentSoft.copy(alpha = 0.15f) else SenseMuted.copy(alpha = 0.12f),
                            RoundedCornerShape(6.dp),
                        )
                        .padding(horizontal = 6.dp, vertical = 2.dp),
                )
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "${scene.requiredDistanceMeters} m · 约 $minutes 分钟",
                style = MaterialTheme.typography.bodySmall,
                color = if (open) SenseOnSurface.copy(alpha = 0.7f) else SenseMuted.copy(alpha = 0.7f),
            )
        }
    }
}
