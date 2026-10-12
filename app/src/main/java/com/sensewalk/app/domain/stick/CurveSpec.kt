package com.sensewalk.app.domain.stick

/**
 * 摇杆→速度曲线规格（DEVELOPMENT.md §4.3.1）。
 *
 * 控制点经 Fritsch–Carlson 保形三次 Hermite 插值求值：
 * - 每个单调段内曲线单调，不会冲过端点值 → 峰值严格等于控制点峰值（1.18 m/s），
 *   远低于 1.4 m/s 硬顶；
 * - 局部极值点切线置 0 → 甜点中心 d=0.55 处曲线平稳达到峰值；
 * - 端点用 FC 单侧公式并限幅 3δ，保证首末段同样保形。
 *
 * 曲线数据可替换（stickCurveId），不改代码。
 */
class CurveSpec(
    val id: String,
    private val xs: FloatArray,
    private val ys: FloatArray,
) {

    init {
        require(xs.size == ys.size && xs.size >= 2) { "$id: 控制点数量不匹配" }
        require(xs[0] == 0f && xs.last() == 1f) { "$id: 曲线必须覆盖 [0,1]" }
        for (i in xs.indices) {
            require(ys[i].isFinite() && ys[i] >= 0f) { "$id: v[$i]=${ys[i]} 必须为有限非负值" }
            if (i > 0) require(xs[i] > xs[i - 1]) { "$id: d[$i] 必须严格递增" }
        }
    }

    private val tangents = computeTangents()

    /** 求值：d 会被钳制到 [0,1]；返回目标速度 m/s（非负、≤ 控制点峰值） */
    fun eval(deflection: Float): Float {
        val d = if (deflection.isNaN()) 0f else deflection.coerceIn(0f, 1f)
        var i = 0
        while (i < xs.size - 2 && d > xs[i + 1]) i++
        val h = xs[i + 1] - xs[i]
        val t = if (h <= 0f) 0f else (d - xs[i]) / h
        val t2 = t * t
        val t3 = t2 * t
        val h00 = 2f * t3 - 3f * t2 + 1f
        val h10 = t3 - 2f * t2 + t
        val h01 = -2f * t3 + 3f * t2
        val h11 = t3 - t2
        return h00 * ys[i] + h10 * h * tangents[i] + h01 * ys[i + 1] + h11 * h * tangents[i + 1]
    }

    /** Fritsch–Carlson 切线：极值点切线为 0，其余取相邻斜率的加权调和平均 */
    private fun computeTangents(): FloatArray {
        val n = xs.size - 1
        val m = FloatArray(xs.size)
        if (n == 1) {
            m[0] = (ys[1] - ys[0]) / (xs[1] - xs[0])
            m[1] = m[0]
            return m
        }
        val h = FloatArray(n) { xs[it + 1] - xs[it] }
        val delta = FloatArray(n) { (ys[it + 1] - ys[it]) / h[it] }

        for (i in 1 until n) {
            m[i] = if (delta[i - 1] * delta[i] <= 0f) {
                0f
            } else {
                val w1 = 2f * h[i] + h[i - 1]
                val w2 = h[i] + 2f * h[i - 1]
                (w1 + w2) / (w1 / delta[i - 1] + w2 / delta[i])
            }
        }
        // 端点：FC 单侧公式；与相邻斜率反号或超 3δ 时退化/限幅，保证段内保形
        m[0] = if (delta[0] * delta[1] <= 0f) {
            0f
        } else {
            val raw = ((2f * h[0] + h[1]) * delta[0] - h[0] * delta[1]) / (h[0] + h[1])
            val cap = 3f * kotlin.math.abs(delta[0])
            raw.coerceIn(-cap, cap)
        }
        m[n] = if (delta[n - 2] * delta[n - 1] <= 0f) {
            0f
        } else {
            val raw = ((2f * h[n - 1] + h[n - 2]) * delta[n - 1] - h[n - 1] * delta[n - 2]) / (h[n - 1] + h[n - 2])
            val cap = 3f * kotlin.math.abs(delta[n - 1])
            raw.coerceIn(-cap, cap)
        }
        return m
    }

    companion object {
        /**
         * comfort_v1（§4.3.1 定稿）：死区 0–0.08；甜点中心 0.55 峰值 1.18 m/s；
         * 拉满 1.0 → 0.65 m/s，明显慢于甜点（v(1)/v(0.55) ≈ 0.55）。
         */
        val COMFORT_V1 = CurveSpec(
            id = "comfort_v1",
            xs = floatArrayOf(0.00f, 0.08f, 0.15f, 0.35f, 0.45f, 0.55f, 0.65f, 0.75f, 0.90f, 1.00f),
            ys = floatArrayOf(0.00f, 0.00f, 0.45f, 0.90f, 1.08f, 1.18f, 1.10f, 1.00f, 0.85f, 0.65f),
        )
    }
}
