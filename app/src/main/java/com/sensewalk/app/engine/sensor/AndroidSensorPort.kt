package com.sensewalk.app.engine.sensor

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.Looper
import android.os.SystemClock

/**
 * [SensorPort] 的 Android 实现（SW-001 F-003）。
 *
 * - 注册结果取 `SensorManager.registerListener` 的真实布尔返回值，不再把
 *   「硬件存在」当作「注册成功」；
 * - 只注销自己注册过的监听（sensor 实例逐个 unregister），重复注销安全；
 * - 回调统一投递到主线程；事件时间戳使用 `event.timestamp/1_000_000`
 *   （elapsedRealtimeNanos 基准，休眠不停表）——调用方传入引擎的注入时间
 *   也必须同基准（服务侧使用 SystemClock.elapsedRealtime）。设备重启双方
 *   一同归零且 counter 读数重置，由引擎的「读数下降重建基线」兜住。
 */
class AndroidSensorPort(context: Context) : SensorPort {

    private val sensorManager = context.getSystemService(SensorManager::class.java)
    private val mainHandler = Handler(Looper.getMainLooper())

    private val counterSensor: Sensor? =
        sensorManager?.getDefaultSensor(Sensor.TYPE_STEP_COUNTER)
    private val detectorSensor: Sensor? =
        sensorManager?.getDefaultSensor(Sensor.TYPE_STEP_DETECTOR)

    private var registeredSensors = mutableSetOf<Sensor>()

    private val listener = object : SensorEventListener {
        override fun onSensorChanged(event: SensorEvent?) {
            when (event?.sensor?.type) {
                Sensor.TYPE_STEP_COUNTER -> {
                    val count = event.values.firstOrNull()?.toLong() ?: return
                    onCounterEvent?.invoke(count, event.timestamp / 1_000_000L)
                }
                Sensor.TYPE_STEP_DETECTOR ->
                    onDetectorEvent?.invoke(event.timestamp / 1_000_000L)
            }
        }

        override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
    }

    private var onCounterEvent: ((Long, Long) -> Unit)? = null
    private var onDetectorEvent: ((Long) -> Unit)? = null

    override val hasCounter: Boolean get() = counterSensor != null
    override val hasDetector: Boolean get() = detectorSensor != null

    override fun registerCounter(onEvent: (stepCount: Long, eventTimeMs: Long) -> Unit): Boolean {
        val sensor = counterSensor ?: return false
        onCounterEvent = onEvent
        val ok = sensorManager?.registerListener(listener, sensor, SensorManager.SENSOR_DELAY_UI, mainHandler) == true
        if (ok) registeredSensors.add(sensor) else onCounterEvent = null
        return ok
    }

    override fun registerDetector(onEvent: (eventTimeMs: Long) -> Unit): Boolean {
        val sensor = detectorSensor ?: return false
        onDetectorEvent = onEvent
        val ok = sensorManager?.registerListener(listener, sensor, SensorManager.SENSOR_DELAY_UI, mainHandler) == true
        if (ok) registeredSensors.add(sensor) else onDetectorEvent = null
        return ok
    }

    override fun unregisterAll() {
        val sm = sensorManager
        if (sm != null) {
            registeredSensors.forEach { runCatching { sm.unregisterListener(listener, it) } }
        }
        registeredSensors.clear()
        onCounterEvent = null
        onDetectorEvent = null
    }

    /** 与事件时间戳同基准的注入时钟（debug 冒烟用；亦可供测试对照） */
    fun injectedNowMs(): Long = SystemClock.elapsedRealtime()
}
