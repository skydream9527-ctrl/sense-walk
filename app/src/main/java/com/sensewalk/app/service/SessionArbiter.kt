package com.sensewalk.app.service

/**
 * 实走服务会话仲裁（SW-001 F-002/F-004，纯 Kotlin 可 JVM 单测）。
 *
 * 管理服务生命周期的三个易错决策，服务本体只执行决策结果：
 * 1. **空重启**：START_STICKY 系统重启带来 null Intent 且无活会话/恢复候选
 *    （快照恢复属 T07）→ 不进前台、不产生空通知，直接干净退出；
 * 2. **单飞装配**：场景异步装配（IO 读配置）期间重复 start 只允许一次
 *    setup，不创建第二套控制器/音频/监听器；
 * 3. **迟到协程**：装配完成时若服务已停止/终态（或已被新会话取代），
 *    决策为丢弃，调用方负责释放其临时创建的资源。
 *
 * 状态只在此处流转：idle → starting → active → finished（终态吸收一切）。
 */
class SessionArbiter {

    enum class Phase { IDLE, STARTING, ACTIVE, FINISHED }

    enum class Decision {
        /** 首次有效启动：进前台并开始异步装配（带 sceneId） */
        START_FOREGROUND_AND_SETUP,

        /** 已在装配/活动：无事可做（单飞；前台已在） */
        NONE,

        /** 无有效会话（空重启/无 sceneId/已终态）：清残留通知并干净退出 */
        STOP_CLEAN,

        /** 活动会话收到停止动作：按放弃收尾 */
        ABANDON_AND_FINISH,

        /** 活动会话收到 debug 注入：转发（仅 debug 构建可达的调用方使用） */
        FORWARD_DEBUG_STEP,
    }

    var phase: Phase = Phase.IDLE
        private set

    /** onStartCommand 决策（主线程串行调用） */
    fun onCommand(action: String?, hasSceneId: Boolean): Decision = when {
        action == WalkForegroundService.ACTION_STOP ->
            // 装配中收到停止＝放弃进行中的开始（controller 可能尚未发布），
            // 终态由服务统一收尾，迟到的装配协程按 FINISHED 丢弃
            if (phase == Phase.ACTIVE || phase == Phase.STARTING) Decision.ABANDON_AND_FINISH
            else Decision.STOP_CLEAN

        action == WalkForegroundService.ACTION_DEBUG_STEP ->
            if (phase == Phase.ACTIVE) Decision.FORWARD_DEBUG_STEP else Decision.NONE

        // 默认分支：正常启动或 START_STICKY 空重启
        phase == Phase.FINISHED -> Decision.STOP_CLEAN // 终态后系统粘性重启：不复活会话
        phase == Phase.IDLE && hasSceneId -> {
            phase = Phase.STARTING
            Decision.START_FOREGROUND_AND_SETUP
        }
        phase == Phase.STARTING || phase == Phase.ACTIVE -> Decision.NONE // 单飞
        else -> Decision.STOP_CLEAN // IDLE 且无 sceneId：空重启，无恢复候选（T07 前不假装可恢复）
    }

    /**
     * 异步装配结果上报。返回 true = 接受（starting → active，可发布会话）；
     * false = 丢弃（期间已 STOP/终态），调用方必须释放其临时创建的
     * 控制器/音频/监听器，不得发布第二套会话。
     */
    fun onSetupCompleted(active: Boolean): Boolean = when (phase) {
        Phase.STARTING ->
            if (active) {
                phase = Phase.ACTIVE
                true
            } else {
                phase = Phase.FINISHED // 装配失败（无传感器/注册失败/配置错误）
                false
            }
        else -> false // 已停止/终态/异常路径：迟到协程一律丢弃
    }

    /** 会话终态（通关/放弃/销毁）：吸收后续一切 */
    fun onFinish() {
        phase = Phase.FINISHED
    }

    val hasLiveSession: Boolean get() = phase == Phase.STARTING || phase == Phase.ACTIVE
}
