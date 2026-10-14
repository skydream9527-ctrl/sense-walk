package com.sensewalk.app.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo

/**
 * 实走冒烟注入接收器（**只在 debug 构建的 manifest 注册**，见 src/debug/AndroidManifest.xml；
 * release 构建不存在此组件）。adb 广播 counter 读数给服务做生命周期/渲染冒烟：
 *
 * `adb shell am broadcast -a com.sensewalk.action.DEBUG_STEP_BROADCAST \
 *    -n com.sensewalk.app/.service.DebugStepReceiver --el debugCount 1050`
 *
 * 双重守卫：仅可调试构建 + DebugWalkSmoke 开关打开时才转发；
 * **不构成真实计步验证**（计距规则由 RealWalkEngine 的 JVM 测试锁定，真机待验证）。
 */
class DebugStepReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val debuggable =
            (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
        if (!debuggable || !DebugWalkSmoke.enabled(context)) return
        if (intent.action != ACTION) return
        val count = intent.getLongExtra(EXTRA_COUNT, -1L)
        if (count < 0L) return
        context.startService(
            Intent(context, WalkForegroundService::class.java)
                .setAction(WalkForegroundService.ACTION_DEBUG_STEP)
                .putExtra(WalkForegroundService.EXTRA_DEBUG_COUNT, count),
        )
    }

    companion object {
        const val ACTION = "com.sensewalk.action.DEBUG_STEP_BROADCAST"
        const val EXTRA_COUNT = "debugCount"
    }
}
