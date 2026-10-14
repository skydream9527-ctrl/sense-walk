package com.sensewalk.app.engine.sensor

import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.Looper

/**
 * 实走传感器源（T06）：
 * - [TYPE_STEP_COUNTER][Sensor.TYPE_STEP_COUNTER] 为**唯一计距源**（硬件累计步数）；
 * - [TYPE_STEP_DETECTOR][Sensor.TYPE_STEP_DETECTOR] 只产出步伐 cue（已解锁脚步音/振同步），
 *   由上层（RealWalkController.onDetectorStep）节流，不参与计距；
 * - counter 缺失时 [canCountDistance]=false——上层提供虚走回退，不伪造计步；
 * - 回调统一投递到主线程（注册时传主线程 Handler），上层无需再切线程。
 */
class StepSensorSource(
    private val sensorManager: SensorManager?,
    private val onCounter: (stepCount: Long, eventTimeMs: Long) -> Unit,
    private val onDetectorStep: (eventTimeMs: Long) -> Unit,
) : SensorEventListener {

    private val mainHandler = Handler(Looper.getMainLooper())

    /** 计步硬件存在性（缺 counter 的设备诚实降级，见 §3.3） */
    val hasCounter: Boolean get() = sensorManager?.getDefaultSensor(Sensor.TYPE_STEP_COUNTER) != null
    val hasDetector: Boolean get() = sensorManager?.getDefaultSensor(Sensor.TYPE_STEP_DETECTOR) != null

    /** counter 可用才可实走计距；detector 只影响音/振同步精细度 */
    val canCountDistance: Boolean get() = hasCounter

    private var registered = false

    /** 注册监听（幂等）；返回是否成功（无硬件/无管理器返回 false） */
    fun start(): Boolean {
        if (registered || sensorManager == null) return registered
        val counter = sensorManager.getDefaultSensor(Sensor.TYPE_STEP_COUNTER)
        if (counter != null) {
            sensorManager.registerListener(this, counter, SensorManager.SENSOR_DELAY_UI, mainHandler)
        }
        val detector = sensorManager.getDefaultSensor(Sensor.TYPE_STEP_DETECTOR)
        if (detector != null) {
            sensorManager.registerListener(this, detector, SensorManager.SENSOR_DELAY_UI, mainHandler)
        }
        registered = counter != null
        return registered
    }

    /** 注销（终态/销毁）；重注册时上层应调用引擎 restartBaseline */
    fun stop() {
        if (sensorManager != null && registered) {
            sensorManager.unregisterListener(this)
        }
        registered = false
    }

    override fun onSensorChanged(event: SensorEvent?) {
        when (event?.sensor?.type) {
            Sensor.TYPE_STEP_COUNTER -> {
                // 硬件累计步数（float 精度足够日常步数）；时间戳为传感器单调时钟
                val count = event.values.firstOrNull()?.toLong() ?: return
                onCounter(count, event.timestamp / 1_000_000L)
            }
            Sensor.TYPE_STEP_DETECTOR -> onDetectorStep(event.timestamp / 1_000_000L)
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
}
