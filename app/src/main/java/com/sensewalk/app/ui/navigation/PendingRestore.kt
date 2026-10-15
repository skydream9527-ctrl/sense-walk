package com.sensewalk.app.ui.navigation

import com.sensewalk.app.domain.session.SessionSnapshot

/**
 * T07A 恢复载荷的进程内传递（MODE 页确认后写入，会话入口消费即清）。
 * 仅用于同进程导航传参——避免把快照 JSON 塞进 nav 路由参数。
 * 无持久化语义：进程死亡即空，恢复候选仍以 DataStore 快照为准。
 */
object PendingRestore {
    /** 实走：恢复快照 JSON（服务 start extra 消费） */
    var realJson: String? = null

    /** 虚走：恢复快照对象（SessionViewModel factory 消费） */
    var virtual: SessionSnapshot? = null

    fun consumeRealJson(): String? = realJson.also { realJson = null }

    fun consumeVirtual(): SessionSnapshot? = virtual.also { virtual = null }
}
