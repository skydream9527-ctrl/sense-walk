package com.sensewalk.app.engine.sensor

/**
 * 传感器端口（SW-001 F-003）：把「注册是否真的成功」从硬件探测中分离出来。
 * 纯 Kotlin 接口——JVM 用假端口覆盖注册失败/部分注册/重复停止边界；
 * Android 实现见 [AndroidSensorPort]。
 */
interface SensorPort {

    /** 计步硬件存在性（存在 ≠ 注册成功） */
    val hasCounter: Boolean

    /** detector 硬件存在性（只影响音/振同步精细度，不阻塞实走） */
    val hasDetector: Boolean

    /**
     * 注册 counter 监听。返回**实际注册结果**（Android 侧为
     * SensorManager.registerListener 的布尔返回值；失败可能来自权限变化或
     * 传感器暂时不可用）。回调时间戳为事件时间的毫秒值
     * （elapsedRealtimeNanos/1e6 基准，见 [AndroidSensorPort]）。
     */
    fun registerCounter(onEvent: (stepCount: Long, eventTimeMs: Long) -> Unit): Boolean

    /** 注册 detector 监听；返回实际注册结果 */
    fun registerDetector(onEvent: (eventTimeMs: Long) -> Unit): Boolean

    /** 注销本次端口注册的全部监听（幂等） */
    fun unregisterAll()
}

/**
 * 传感器源（T06 / F-003 修订）：counter 为唯一计距源，detector 只作步伐 cue。
 * 注册以端口**实际返回值**为准：counter 注册失败即视为不可实走，
 * 已注册的部分监听会被清理，不留半开状态。
 */
class StepSensorSource(
    private val port: SensorPort,
    private val onCounter: (stepCount: Long, eventTimeMs: Long) -> Unit,
    private val onDetectorStep: (eventTimeMs: Long) -> Unit,
) {

    val hasCounter: Boolean get() = port.hasCounter
    val hasDetector: Boolean get() = port.hasDetector

    /** counter 硬件可用才可实走计距；detector 只影响音/振同步精细度 */
    val canCountDistance: Boolean get() = port.hasCounter

    private var started = false

    /**
     * 注册监听（一次）。返回是否**真的注册成功**（硬件存在且端口注册返回
     * true）；未整体成功时已注册的部分会被注销。
     */
    fun start(): Boolean {
        if (started) return true
        if (!port.hasCounter) return false
        var success = false
        try {
            if (!port.registerCounter(onCounter)) return false
            if (port.hasDetector) {
                // detector 注册失败不阻塞实走（counter-only 可走），音/振按距离步幅驱动
                port.registerDetector(onDetectorStep)
            }
            started = true
            success = true
            return true
        } finally {
            if (!success) port.unregisterAll()
        }
    }

    /** 注销（终态/销毁；幂等）。重注册前调用方应让引擎 restartBaseline */
    fun stop() {
        if (!started) return
        started = false
        port.unregisterAll()
    }

    val isStarted: Boolean get() = started
}
