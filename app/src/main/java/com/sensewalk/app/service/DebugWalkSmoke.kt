package com.sensewalk.app.service

import android.content.Context
import android.content.pm.ApplicationInfo
import android.provider.Settings

/**
 * 实走冒烟开关（仅可调试构建生效）：
 * `adb shell settings put global sensewalk_debug_stub 1` 后，
 * 实走入口跳过硬件检查、服务可经 debug 注入 counter 读数。
 * **只用于服务生命周期/渲染冒烟——不构成真实计步或锁屏验证**；
 * release 构建 isDebuggable=false，此开关永远无效。
 */
object DebugWalkSmoke {
    private const val KEY = "sensewalk_debug_stub"

    fun enabled(context: Context): Boolean {
        val debuggable = (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
        if (!debuggable) return false
        return runCatching {
            Settings.Global.getInt(context.contentResolver, KEY, 0) == 1
        }.getOrDefault(false)
    }
}
