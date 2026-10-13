package com.sensewalk.app.domain.sensory

/**
 * 感官后端：真实实现为 Android 音频/振动引擎（engine/sensory），测试注入 Fake。
 * 协调器只通过本接口发声/振动，不直接持有任何 Android 组件。
 */
interface SensoryBackend {

    /** 开始循环播放环境层（协调器保证每层只调用一次） */
    fun startLoop(layerId: String)

    /** 设置环境层绝对增益 0..1（淡入由协调器按 fadeMs 推进） */
    fun setLoopGain(layerId: String, gain: Float)

    /** 播放一次脚步（变体、音量与音高随机由协调器决定） */
    fun playStep(layerId: String, variant: Int, volume: Float, pitchFactor: Float)

    fun pauseAll()

    fun resumeAll()

    /** 终态/销毁：停止并释放全部音频与振动资源 */
    fun releaseAll()

    fun vibrate(patternId: String)

    fun stopVibrate()
}
