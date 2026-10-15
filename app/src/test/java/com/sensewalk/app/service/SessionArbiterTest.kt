package com.sensewalk.app.service

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 会话仲裁（SW-001 F-002/F-004）：空重启退出、单飞装配、迟到协程丢弃、终态吸收。
 */
class SessionArbiterTest {

    @Test
    fun `F002 空重启 - null Intent 无会话时干净退出而非空前台`() {
        val a = SessionArbiter()
        // 首个无 sceneId 的默认启动（START_STICKY 空重启等价）：无恢复候选（T07 前）
        assertEquals(SessionArbiter.Decision.STOP_CLEAN, a.onCommand(null, hasSceneId = false))
        assertEquals(SessionArbiter.Phase.IDLE, a.phase)
    }

    @Test
    fun `正常启动 - 进前台装配并最终 active`() {
        val a = SessionArbiter()
        assertEquals(
            SessionArbiter.Decision.START_FOREGROUND_AND_SETUP,
            a.onCommand(null, hasSceneId = true),
        )
        assertEquals(SessionArbiter.Phase.STARTING, a.phase)
        assertTrue(a.onSetupCompleted(active = true))
        assertEquals(SessionArbiter.Phase.ACTIVE, a.phase)
        assertTrue(a.hasLiveSession)
    }

    @Test
    fun `F004 单飞 - 装配期间重复 start 一律 NONE`() {
        val a = SessionArbiter()
        a.onCommand(null, hasSceneId = true) // → STARTING
        assertEquals(SessionArbiter.Decision.NONE, a.onCommand(null, hasSceneId = true))
        assertEquals(SessionArbiter.Decision.NONE, a.onCommand("com.sensewalk.other", hasSceneId = true))
        a.onSetupCompleted(active = true) // → ACTIVE
        assertEquals("活动后重复 start 同样单飞", SessionArbiter.Decision.NONE, a.onCommand(null, hasSceneId = true))
    }

    @Test
    fun `F004 迟到协程 - 装配期间已停止则丢弃结果`() {
        val a = SessionArbiter()
        a.onCommand(null, hasSceneId = true) // STARTING
        a.onFinish() // 用户在 IO 期间经通知「停止」
        assertFalse("迟到装配必须丢弃（调用方释放临时资源）", a.onSetupCompleted(active = true))
        assertEquals(SessionArbiter.Phase.FINISHED, a.phase)
    }

    @Test
    fun `F002 终态吸收 - 粘性重启与后续命令不再复活会话`() {
        val a = SessionArbiter()
        a.onCommand(null, hasSceneId = true)
        a.onSetupCompleted(active = true)
        assertEquals(SessionArbiter.Decision.ABANDON_AND_FINISH, a.onCommand(WalkForegroundService.ACTION_STOP, false))
        a.onFinish()
        assertEquals("终态后默认命令 → 干净退出", SessionArbiter.Decision.STOP_CLEAN, a.onCommand(null, hasSceneId = true))
        assertEquals("终态后 STOP → 干净退出", SessionArbiter.Decision.STOP_CLEAN, a.onCommand(WalkForegroundService.ACTION_STOP, false))
        assertEquals("终态后 debug 注入 → 忽略", SessionArbiter.Decision.NONE, a.onCommand(WalkForegroundService.ACTION_DEBUG_STEP, false))
        assertFalse("终态后迟到装配丢弃", a.onSetupCompleted(active = true))
    }

    @Test
    fun `F002 装配中 STOP - 未发布控制器也可放弃并使迟到装配丢弃`() {
        val a = SessionArbiter()
        a.onCommand(null, hasSceneId = true) // STARTING，controller 尚未发布
        assertEquals(SessionArbiter.Decision.ABANDON_AND_FINISH, a.onCommand(WalkForegroundService.ACTION_STOP, false))
        a.onFinish() // 服务 abandonSession → finishSession 的等价调用
        assertFalse(a.onSetupCompleted(active = true))
    }

    @Test
    fun `装配失败上报 - 记终态不发布会话`() {
        val a = SessionArbiter()
        a.onCommand(null, hasSceneId = true)
        assertFalse(a.onSetupCompleted(active = false))
        assertEquals(SessionArbiter.Phase.FINISHED, a.phase)
        assertEquals(SessionArbiter.Decision.STOP_CLEAN, a.onCommand(null, hasSceneId = false))
    }

    @Test
    fun `debug 注入只在活动会话转发`() {
        val a = SessionArbiter()
        assertEquals(SessionArbiter.Decision.NONE, a.onCommand(WalkForegroundService.ACTION_DEBUG_STEP, false))
        a.onCommand(null, hasSceneId = true)
        assertEquals("装配中也忽略（controller 未就绪）", SessionArbiter.Decision.NONE, a.onCommand(WalkForegroundService.ACTION_DEBUG_STEP, false))
        a.onSetupCompleted(active = true)
        assertEquals(SessionArbiter.Decision.FORWARD_DEBUG_STEP, a.onCommand(WalkForegroundService.ACTION_DEBUG_STEP, false))
    }
}
