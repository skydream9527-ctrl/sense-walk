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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Settings
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.sensewalk.app.domain.scene.Scene
import com.sensewalk.app.ui.theme.AccentSoft
import com.sensewalk.app.ui.theme.SenseBlack
import com.sensewalk.app.ui.theme.SenseMuted
import com.sensewalk.app.ui.theme.SenseOnSurface
import com.sensewalk.app.ui.theme.sceneTint

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    scenes: List<Scene>,
    onStart: (Scene) -> Unit,
    onOpenSettings: () -> Unit,
) {
    var selectedId by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(scenes) {
        if (selectedId == null && scenes.isNotEmpty()) {
            selectedId = scenes.first().id
        }
    }
    val selected = scenes.find { it.id == selectedId }

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
        Column(
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
                    SceneCard(
                        scene = scene,
                        selected = scene.id == selectedId,
                        onClick = { selectedId = scene.id },
                    )
                }
            }

            Button(
                onClick = { selected?.let(onStart) },
                enabled = selected != null,
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
                    text = "开始",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }
    }
}

@Composable
private fun SceneCard(
    scene: Scene,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val tint = sceneTint(scene.id)
    val shape = RoundedCornerShape(16.dp)
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(110.dp)
            .clip(shape)
            .background(tint.copy(alpha = 0.55f))
            .then(
                if (selected) {
                    Modifier.border(2.dp, AccentSoft, shape)
                } else {
                    Modifier.border(1.dp, SenseMuted.copy(alpha = 0.25f), shape)
                }
            )
            .clickable(onClick = onClick)
            .padding(20.dp),
        contentAlignment = Alignment.BottomStart,
    ) {
        Column {
            Text(
                text = scene.name,
                style = MaterialTheme.typography.titleLarge,
                color = SenseOnSurface,
                fontWeight = FontWeight.Medium,
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "建议 ${scene.suggestedMinutes} 分钟",
                style = MaterialTheme.typography.bodySmall,
                color = SenseOnSurface.copy(alpha = 0.7f),
            )
        }
    }
}
