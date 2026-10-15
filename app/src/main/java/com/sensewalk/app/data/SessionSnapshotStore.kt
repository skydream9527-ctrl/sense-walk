package com.sensewalk.app.data

import android.content.Context
import android.provider.Settings
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.sensewalk.app.domain.session.SessionSnapshot
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext

private val Context.sessionStore: DataStore<Preferences> by preferencesDataStore(name = "sensewalk_session")

/**
 * 会话快照存储（T07A / SW-004）：DataStore 单键 JSON。
 *
 * 保存方负责在「每 5s / 越相位 / 状态转换」写入、主动放弃与通关时 [clear]；
 * 进程死亡不依赖 onDestroy——周期性保存已覆盖（契约）。
 * 损坏 JSON 读出为 null（可解释为无快照，不抛异常）。
 */
class SessionSnapshotStore(private val context: Context) {

    private object Keys {
        val SNAPSHOT_JSON = stringPreferencesKey("snapshot_json")
    }

    suspend fun save(snapshot: SessionSnapshot) = withContext(Dispatchers.IO) {
        context.sessionStore.edit { it[Keys.SNAPSHOT_JSON] = SessionSnapshot.toJson(snapshot) }
    }

    /** 读取原始快照（未校验）；无/损坏返回 null。校验由 [com.sensewalk.app.domain.session.SessionSnapshotValidator] 做 */
    suspend fun load(): SessionSnapshot? = withContext(Dispatchers.IO) {
        val raw = context.sessionStore.data.first()[Keys.SNAPSHOT_JSON] ?: return@withContext null
        SessionSnapshot.fromJson(raw)
    }

    /** 主动放弃 / 通关：清除恢复候选 */
    suspend fun clear() = withContext(Dispatchers.IO) {
        context.sessionStore.edit { it.remove(Keys.SNAPSHOT_JSON) }
    }

    companion object {
        /** 跨 boot 检测基准（API 24+；读不到时退化为 -1，视为「未知」不作废虚走恢复） */
        fun bootCount(context: Context): Int =
            runCatching { Settings.Global.getInt(context.contentResolver, Settings.Global.BOOT_COUNT) }
                .getOrDefault(-1)
    }
}
