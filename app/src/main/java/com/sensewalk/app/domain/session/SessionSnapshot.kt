package com.sensewalk.app.domain.session

import kotlinx.serialization.json.put

/**
 * 会话快照（T07A / SW-004，契约 `contracts/session-snapshot.md`）。
 *
 * 只在**被动中断**后作为恢复候选：主动放弃/通关由保存方清除，
 * 恢复候选仅接受 WALKING/PAUSED 状态、且 30 分钟内的快照。
 *
 * 时间基准（契约）：
 * - [savedAtWallMs] 用 wall time（System.currentTimeMillis），仅用于 30min 时限判断；
 * - [lastCounterEventMs] 是 monotonic（elapsedRealtime 基准）的 sensor 事件时间，
 *   **跨 boot 不可减算**（[bootCount] 变化即作废，实走恢复只重建基线不补缺口）；
 * - [elapsedActiveMs] 为累计活跃时长，无基准依赖。
 *
 * 快照版本 [SNAPSHOT_VERSION] 与场景 schemaVersion（=2）语义独立，互不复用。
 */
data class SessionSnapshot(
    val snapshotVersion: Int,
    val sessionId: String,
    /** "virtual" / "real"（与 NavRoutes.Mode 字符串一致） */
    val mode: String,
    val sceneId: String,
    val sceneSchemaVersion: Int,
    /** 被动中断时的会话状态；恢复候选只接受 WALKING/PAUSED */
    val state: String,
    val savedAtWallMs: Long,
    /** 保存时的 Settings.Global.BOOT_COUNT；不同即跨 boot，sensor 事件基准作废 */
    val bootCount: Int,
    val meters: Float,
    val sPos: Float,
    val sBest: Float,
    val firedPhaseIds: List<String>,
    val elapsedActiveMs: Long,
    /** 实走：counter 最后累计读数（恢复不据此补距，仅诊断） */
    val lastCounterReading: Long? = null,
    /** 实走：最后 counter 事件的 monotonic 时间（跨 boot 作废） */
    val lastCounterEventMs: Long? = null,
) {
    companion object {
        const val SNAPSHOT_VERSION = 1

        /** 恢复候选时限：被动中断后 30 分钟内可选择恢复 */
        const val RECOVERY_WINDOW_MS = 30L * 60 * 1000

        val ACCEPTED_STATES = setOf(SessionState.WALKING.name, SessionState.PAUSED.name)

        /** 手动 JSON 编解码（项目未启用 serialization 编译插件；沿用 SceneJsonParser 的 JsonObject 模式） */
        fun toJson(s: SessionSnapshot): String {
            val obj = kotlinx.serialization.json.buildJsonObject {
                put("snapshotVersion", s.snapshotVersion)
                put("sessionId", s.sessionId)
                put("mode", s.mode)
                put("sceneId", s.sceneId)
                put("sceneSchemaVersion", s.sceneSchemaVersion)
                put("state", s.state)
                put("savedAtWallMs", s.savedAtWallMs)
                put("bootCount", s.bootCount)
                put("meters", s.meters.toDouble())
                put("sPos", s.sPos.toDouble())
                put("sBest", s.sBest.toDouble())
                put("firedPhaseIds", kotlinx.serialization.json.buildJsonArray { s.firedPhaseIds.forEach { add(kotlinx.serialization.json.JsonPrimitive(it)) } })
                put("elapsedActiveMs", s.elapsedActiveMs)
                s.lastCounterReading?.let { put("lastCounterReading", it) }
                s.lastCounterEventMs?.let { put("lastCounterEventMs", it) }
            }
            return obj.toString()
        }

        /** 解析失败/字段缺失返回 null（损坏存档不抛异常）；忽略未知字段 */
        fun fromJson(json: String): SessionSnapshot? = runCatching {
            val obj = kotlinx.serialization.json.Json.parseToJsonElement(json).let { it as? kotlinx.serialization.json.JsonObject ?: return@runCatching null }
            fun str(k: String) = (obj[k] as? kotlinx.serialization.json.JsonPrimitive)?.content
            fun int(k: String) = (obj[k] as? kotlinx.serialization.json.JsonPrimitive)?.content?.toIntOrNull()
            fun long(k: String) = (obj[k] as? kotlinx.serialization.json.JsonPrimitive)?.content?.toLongOrNull()
            fun dbl(k: String) = (obj[k] as? kotlinx.serialization.json.JsonPrimitive)?.content?.toDoubleOrNull()
            val fired = (obj["firedPhaseIds"] as? kotlinx.serialization.json.JsonArray)
                ?.mapNotNull { (it as? kotlinx.serialization.json.JsonPrimitive)?.content } ?: return@runCatching null
            SessionSnapshot(
                snapshotVersion = int("snapshotVersion") ?: return@runCatching null,
                sessionId = str("sessionId") ?: return@runCatching null,
                mode = str("mode") ?: return@runCatching null,
                sceneId = str("sceneId") ?: return@runCatching null,
                sceneSchemaVersion = int("sceneSchemaVersion") ?: return@runCatching null,
                state = str("state") ?: return@runCatching null,
                savedAtWallMs = long("savedAtWallMs") ?: return@runCatching null,
                bootCount = int("bootCount") ?: -1,
                meters = dbl("meters")?.toFloat() ?: return@runCatching null,
                sPos = dbl("sPos")?.toFloat() ?: return@runCatching null,
                sBest = dbl("sBest")?.toFloat() ?: return@runCatching null,
                firedPhaseIds = fired,
                elapsedActiveMs = long("elapsedActiveMs") ?: 0L,
                lastCounterReading = long("lastCounterReading"),
                lastCounterEventMs = long("lastCounterEventMs"),
            )
        }.getOrNull()
    }
}

/** 快照评估结果：只有 [Valid] 可恢复，其余均给出可解释原因（契约：不盲目钳制） */
sealed interface SnapshotCandidate {
    data class Valid(val snapshot: SessionSnapshot, val acrossBoot: Boolean) : SnapshotCandidate
    data class Expired(val savedAtWallMs: Long, val ageMs: Long) : SnapshotCandidate
    data class Incompatible(val reason: String) : SnapshotCandidate
    data class Corrupted(val reason: String) : SnapshotCandidate
}

/** 校验所需的场景元信息（由调用方从 SceneRepository 解析后注入） */
data class SceneInfo(val sceneId: String, val schemaVersion: Int, val requiredMeters: Float, val phaseIds: Set<String>)

/**
 * 快照校验器（纯 Kotlin）：损坏/不兼容/过期分别可解释，不做静默修复。
 * 跨 boot 不是拒绝条件——虚走照常恢复；实走恢复时由引擎重建 counter 基线。
 */
object SessionSnapshotValidator {

    fun evaluate(
        snapshot: SessionSnapshot?,
        nowWallMs: Long,
        sceneOf: (String) -> SceneInfo?,
        currentBootCount: Int,
    ): SnapshotCandidate {
        if (snapshot == null) return SnapshotCandidate.Incompatible("无快照")
        if (snapshot.snapshotVersion != SessionSnapshot.SNAPSHOT_VERSION) {
            return SnapshotCandidate.Incompatible("快照版本 ${snapshot.snapshotVersion} 不受支持（当前 ${SessionSnapshot.SNAPSHOT_VERSION}）")
        }
        if (snapshot.sessionId.isBlank()) return SnapshotCandidate.Corrupted("sessionId 为空")
        if (snapshot.mode !in setOf("virtual", "real")) {
            return SnapshotCandidate.Corrupted("未知模式 '${snapshot.mode}'")
        }
        if (snapshot.state !in SessionSnapshot.ACCEPTED_STATES) {
            return SnapshotCandidate.Incompatible("状态 ${snapshot.state} 不是可恢复的被动中断态")
        }
        val scene = sceneOf(snapshot.sceneId)
            ?: return SnapshotCandidate.Incompatible("场景 '${snapshot.sceneId}' 不存在")
        if (scene.schemaVersion != snapshot.sceneSchemaVersion) {
            return SnapshotCandidate.Incompatible(
                "场景 schemaVersion 已变化（快照 ${snapshot.sceneSchemaVersion}，当前 ${scene.schemaVersion}）",
            )
        }
        // 数值健全性：非有限/负数/超终点属于损坏，不钳制成有效存档（契约）
        if (!snapshot.meters.isFinite() || !snapshot.sPos.isFinite() || !snapshot.sBest.isFinite()) {
            return SnapshotCandidate.Corrupted("进度含非有限值")
        }
        if (snapshot.meters < 0f || snapshot.sPos < 0f || snapshot.sBest < 0f) {
            return SnapshotCandidate.Corrupted("进度含负值")
        }
        if (snapshot.meters > scene.requiredMeters) {
            return SnapshotCandidate.Corrupted("米数 ${snapshot.meters} 超过终点 ${scene.requiredMeters}")
        }
        if (snapshot.sBest < snapshot.sPos) {
            // 不变量 s_best ≥ s_pos 破坏：宁可拒绝也不抬 best 计距（与 ProgressAccumulator 的宽容策略不同，
            // 持久层入口从严——损坏即整份作废，避免半修复状态继续传播）
            return SnapshotCandidate.Corrupted("s_best(${snapshot.sBest}) < s_pos(${snapshot.sPos})")
        }
        if (snapshot.elapsedActiveMs < 0L) return SnapshotCandidate.Corrupted("elapsedActiveMs 为负")
        val unknownPhases = snapshot.firedPhaseIds.filter { it !in scene.phaseIds }
        if (unknownPhases.isNotEmpty()) {
            return SnapshotCandidate.Corrupted("含未知相位 ${unknownPhases.joinToString(",")}")
        }
        val age = nowWallMs - snapshot.savedAtWallMs
        if (age > SessionSnapshot.RECOVERY_WINDOW_MS) {
            return SnapshotCandidate.Expired(snapshot.savedAtWallMs, age)
        }
        return SnapshotCandidate.Valid(snapshot, acrossBoot = snapshot.bootCount != currentBootCount)
    }
}
