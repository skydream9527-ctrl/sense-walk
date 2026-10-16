package com.sensewalk.app.domain.session

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 会话快照校验/序列化（T07A / SW-004，契约 session-snapshot.md）：
 * 过期/损坏/不兼容分别可解释，不盲目钳制；JSON 往返无损。
 */
class SessionSnapshotValidatorTest {

    private val scene = SceneInfo("forest", schemaVersion = 2, requiredMeters = 800f, phaseIds = setOf("void", "steps", "tree_outline", "ambience", "tree_trunks", "haptic_steps", "leaf_path", "deep_birds", "light_shows", "clearing"))

    private val scenes = mapOf("forest" to scene)

    private fun snapshot(
        state: String = SessionState.WALKING.name,
        meters: Float = 300f,
        sPos: Float = 300f,
        sBest: Float = 300f,
        savedAt: Long = 0L,
        version: Int = SessionSnapshot.SNAPSHOT_VERSION,
        sceneId: String = "forest",
        schema: Int = 2,
        fired: List<String> = listOf("void", "steps", "tree_outline", "ambience"),
        elapsed: Long = 100_000L,
        mode: String = "virtual",
    ) = SessionSnapshot(
        snapshotVersion = version,
        sessionId = "s-1",
        mode = mode,
        sceneId = sceneId,
        sceneSchemaVersion = schema,
        state = state,
        savedAtWallMs = savedAt,
        bootCount = 7,
        meters = meters,
        sPos = sPos,
        sBest = sBest,
        firedPhaseIds = fired,
        elapsedActiveMs = elapsed,
        lastCounterReading = if (mode == "real") 500L else null,
        lastCounterEventMs = if (mode == "real") 123_456L else null,
    )

    private fun evaluate(snap: SessionSnapshot?, now: Long = 10 * 60 * 1000L, boot: Int = 7) =
        SessionSnapshotValidator.evaluate(snap, now, { scenes[it] }, boot)

    @Test
    fun `有效快照 - Valid 且同 boot 不标跨启动`() {
        val r = evaluate(snapshot())
        assertTrue("应判定 Valid，实际 $r", r is SnapshotCandidate.Valid)
        assertEquals(false, (r as SnapshotCandidate.Valid).acrossBoot)
    }

    @Test
    fun `跨 boot - 仍 Valid 但 acrossBoot 为真（虚走照常恢复，实走重建基线）`() {
        val r = evaluate(snapshot(), boot = 8)
        assertTrue(r is SnapshotCandidate.Valid)
        assertEquals(true, (r as SnapshotCandidate.Valid).acrossBoot)
    }

    @Test
    fun `30 分钟整点内有效 - 超过 1ms 过期`() {
        assertTrue(evaluate(snapshot(savedAt = 0L), now = SessionSnapshot.RECOVERY_WINDOW_MS) is SnapshotCandidate.Valid)
        val r = evaluate(snapshot(savedAt = 0L), now = SessionSnapshot.RECOVERY_WINDOW_MS + 1)
        assertTrue("应过期，实际 $r", r is SnapshotCandidate.Expired)
    }

    @Test
    fun `快照版本不符 - Incompatible 可解释`() {
        val r = evaluate(snapshot(version = 99))
        assertTrue(r is SnapshotCandidate.Incompatible)
        assertTrue((r as SnapshotCandidate.Incompatible).reason.contains("99"))
    }

    @Test
    fun `场景不存在 - Incompatible`() {
        assertTrue(evaluate(snapshot(sceneId = "gone")) is SnapshotCandidate.Incompatible)
    }

    @Test
    fun `场景 schemaVersion 变化 - Incompatible 不盲目迁移`() {
        val r = evaluate(snapshot(schema = 3))
        assertTrue(r is SnapshotCandidate.Incompatible)
    }

    @Test
    fun `终态快照不是恢复候选 - Incompatible`() {
        assertTrue(evaluate(snapshot(state = SessionState.COMPLETED.name)) is SnapshotCandidate.Incompatible)
        assertTrue(evaluate(snapshot(state = SessionState.ABANDONED.name)) is SnapshotCandidate.Incompatible)
    }

    @Test
    fun `NaN 与 Infinity - Corrupted 不钳制`() {
        assertTrue(evaluate(snapshot(meters = Float.NaN)) is SnapshotCandidate.Corrupted)
        assertTrue(evaluate(snapshot(sPos = Float.POSITIVE_INFINITY)) is SnapshotCandidate.Corrupted)
        assertTrue(evaluate(snapshot(sBest = Float.NEGATIVE_INFINITY)) is SnapshotCandidate.Corrupted)
    }

    @Test
    fun `负进度与超终点 - Corrupted`() {
        assertTrue(evaluate(snapshot(meters = -1f)) is SnapshotCandidate.Corrupted)
        assertTrue(evaluate(snapshot(meters = 800.5f)) is SnapshotCandidate.Corrupted)
        assertTrue(evaluate(snapshot(sPos = -0.1f)) is SnapshotCandidate.Corrupted)
    }

    @Test
    fun `s_best 小于 s_pos - Corrupted 不半修复`() {
        assertTrue(evaluate(snapshot(sPos = 300f, sBest = 200f)) is SnapshotCandidate.Corrupted)
    }

    @Test
    fun `未知相位 - Corrupted`() {
        val r = evaluate(snapshot(fired = listOf("void", "nonexistent_phase")))
        assertTrue(r is SnapshotCandidate.Corrupted)
        assertTrue((r as SnapshotCandidate.Corrupted).reason.contains("nonexistent_phase"))
    }

    @Test
    fun `未知模式与负时长 - Corrupted`() {
        assertTrue(evaluate(snapshot(mode = "teleport")) is SnapshotCandidate.Corrupted)
        assertTrue(evaluate(snapshot(elapsed = -5L)) is SnapshotCandidate.Corrupted)
    }

    @Test
    fun `JSON 序列化往返无损 - 兼容未知字段与损坏输入`() {
        val snap = snapshot(mode = "real").copy(stabilizeHintShown = true)
        // P-02：hintShown 持久往返
        assertEquals(true, SessionSnapshot.fromJson(SessionSnapshot.toJson(snap))?.stabilizeHintShown)
        val encoded = SessionSnapshot.toJson(snap)
        // 模拟未来版本新增字段：老读取忽略
        val withExtra = encoded.dropLast(1) + ",\"futureField\":1}"
        assertEquals(snap, SessionSnapshot.fromJson(withExtra))
        // 损坏输入：null 而非异常
        assertEquals(null, SessionSnapshot.fromJson("not-json"))
        assertEquals(null, SessionSnapshot.fromJson("{\"snapshotVersion\":1}"))
    }

    @Test
    fun `无快照 - Incompatible 而非崩溃`() {
        assertTrue(evaluate(null) is SnapshotCandidate.Incompatible)
    }
}
