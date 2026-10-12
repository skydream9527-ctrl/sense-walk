package com.sensewalk.app.domain.stick

/**
 * 舒适摇杆映射（§4.3）：摇杆前进偏转 d ∈ [0,1] → 目标速度。
 *
 * - 左推（d < 0）为 0：不倒走、不计距（§3.1/§5.4）；
 * - NaN 等非法输入返回 0，不污染任何状态；
 * - 超出 [0,1] 的偏转按端点钳制；
 * - 由 [CurveSpec] 提供具体曲线（默认 comfort_v1），拉满慢于甜点区。
 */
class ComfortStickMapper(
    private val curve: CurveSpec = CurveSpec.COMFORT_V1,
) {

    fun targetSpeed(deflection: Float): Float = when {
        deflection.isNaN() -> 0f
        else -> curve.eval(deflection)
    }

    /** 曲线标识（配置 stickCurveId 的运行时对应物） */
    val curveId: String get() = curve.id

    companion object {
        /** comfort_v1 甜点中心 */
        const val SWEET_SPOT_DEFLECTION = 0.55f

        /** 任意输入下的速度硬顶（§4.3 硬规则 2） */
        const val SPEED_HARD_CAP = 1.4f
    }
}
