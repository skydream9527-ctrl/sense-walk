package com.sensewalk.app.domain.progress

/**
 * 有效前进会计（§5.4 / §12.2 / S2 / S9）。
 *
 * - [sPos]：角色在路径上的位置，可因重试/回退下降（不越过起点 0）；
 * - [sBest]：历史最远位置，单调不减；
 * - [meters]：对外唯一有效米数 = 只累计超过 sBest 的增量，钳制到 [0, required]。
 *
 * 回退后走回旧位置不重复累计；非有限增量被忽略，不污染状态。
 * UI 动画、计时、相位都无入口写入本类——只有 [advance] 增加距离。
 * [snapshot]/[fromSnapshot] 为 T07 会话恢复预留（本阶段不做持久化）。
 */
class ProgressAccumulator(val requiredDistanceMeters: Float) {

    init {
        require(requiredDistanceMeters.isFinite() && requiredDistanceMeters > 0f) {
            "requiredDistanceMeters 必须为正有限值"
        }
    }

    var sPos: Float = 0f
        private set
    var sBest: Float = 0f
        private set
    var meters: Float = 0f
        private set

    /** 沿路径的位移增量：正=前进，负=回退；只有超越历史最远位置的部分计入 meters */
    fun advance(delta: Float) {
        if (!delta.isFinite()) return
        sPos = (sPos + delta).coerceAtLeast(0f)
        if (sPos > sBest) {
            meters = (meters + (sPos - sBest)).coerceIn(0f, requiredDistanceMeters)
            sBest = sPos
        }
    }

    val remaining: Float get() = (requiredDistanceMeters - meters).coerceAtLeast(0f)

    fun snapshot(): ProgressSnapshot = ProgressSnapshot(sPos, sBest, meters, requiredDistanceMeters)

    companion object {
        /** 从快照恢复：s_best 与 s_pos 分开还原，回退后恢复不重复计距（S9） */
        fun fromSnapshot(snapshot: ProgressSnapshot): ProgressAccumulator {
            val acc = ProgressAccumulator(snapshot.requiredDistanceMeters)
            acc.sPos = snapshot.sPos.coerceAtLeast(0f)
            acc.sBest = snapshot.sBest.coerceIn(0f, acc.sPos)
            acc.meters = snapshot.meters.coerceIn(0f, acc.requiredDistanceMeters)
            return acc
        }
    }
}

/** T07 会话快照的进度部分 */
data class ProgressSnapshot(
    val sPos: Float,
    val sBest: Float,
    val meters: Float,
    val requiredDistanceMeters: Float,
)
