package com.sensewalk.app.domain.progress

/**
 * 距离门禁（§6 / S3）：通关 ⟺ 本局有效距离 ≥ requiredDistanceMeters。
 *
 * 只在首次满足时触发一次；之后的任何事件（重复上报、迟到的更高米数、
 * 终态后的迟到回调）都不会再次通关。未满距的主动结束由状态机判为
 * Abandoned，与本门禁无关。
 */
class CompletionGate(
    private val requiredDistanceMeters: Float,
) {

    init {
        require(requiredDistanceMeters.isFinite() && requiredDistanceMeters > 0f)
    }

    var isCompleted: Boolean = false
        private set

    /**
     * 每次距离更新后调用。返回 true 当且仅当本次调用首次满足门禁
     * （meters ≥ required 且此前未通关）。
     */
    fun onMeters(meters: Float): Boolean {
        if (isCompleted) return false
        if (meters.isFinite() && meters >= requiredDistanceMeters) {
            isCompleted = true
            return true
        }
        return false
    }
}
