package com.sensewalk.app.domain.stick

import kotlin.math.exp

/**
 * 速度惯性（§4.3.2）：v ← v + (v_tgt − v) × (1 − e^(−dt/τ))。
 *
 * τ 选择：加速 0.60 s / 减速 0.35 s / 松手（目标为 0）0.25 s。
 *
 * dt 约束：
 * - 负数 / NaN / Infinity 视为无效步进，速度不变；
 * - 单次有效步进上限 [MAX_STEP_SECONDS]（0.05 s）：一帧卡顿或后台回来传入的
 *   大 dt 不会追补成前进——调用方（帧循环）本身也应先钳制 dt（§12.2），
 *   这里是领域层的第二道防线，时间由调用方注入。
 */
class VelocityInertia(initialVelocity: Float = 0f) {

    var velocity: Float = if (initialVelocity.isFinite() && initialVelocity >= 0f) initialVelocity else 0f
        private set

    fun step(dt: Float, targetSpeed: Float): Float {
        val effectiveDt = when {
            !dt.isFinite() || dt <= 0f -> return velocity
            dt > MAX_STEP_SECONDS -> MAX_STEP_SECONDS
            else -> dt
        }
        val target = if (targetSpeed.isFinite() && targetSpeed > 0f) targetSpeed else 0f
        if (target == velocity) return velocity

        val tau = when {
            target > velocity -> TAU_ACCELERATE_SECONDS
            target == 0f -> TAU_RELEASE_SECONDS
            else -> TAU_DECELERATE_SECONDS
        }
        velocity += (target - velocity) * (1f - exp(-effectiveDt.toDouble() / tau.toDouble()).toFloat())
        return velocity
    }

    /** 暂停/终态清零速度（§12.3：暂停清零输入与速度） */
    fun reset() {
        velocity = 0f
    }

    companion object {
        const val TAU_ACCELERATE_SECONDS = 0.60f
        const val TAU_DECELERATE_SECONDS = 0.35f
        const val TAU_RELEASE_SECONDS = 0.25f
        const val MAX_STEP_SECONDS = 0.05f
    }
}
