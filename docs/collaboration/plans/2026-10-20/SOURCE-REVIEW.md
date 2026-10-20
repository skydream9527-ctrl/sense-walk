# 三份输入的采纳与修正

审阅日期2026-10-20。主干源码基线`321060e945b512f3f6b8b038543eb3b9d16a58bc`。原件来自用户共享checkout的三个未跟踪Markdown文件，逐字复制进[inputs](inputs/index.json)，共享checkout及原件未改动。快照以.txt保存原字节，原文相对链接按仓库根目录解释。原文为建议来源，不是当前任务状态或产品规则。

## 三份计划各自的价值

| 输入 | 采用部分 | 需要修正 |
| --- | --- | --- |
| [OPTIMIZATION_PLAN](inputs/OPTIMIZATION_PLAN.txt) | 高频状态延后读取、异步图层、轻量复用、触觉与结果落幕、四角色划分 | 基线8056e11已旧；217测试过期；恢复/越坎/光效/可靠性已accepted；Edge-to-Edge已开；不立即引入Media3或R8 |
| [优化计划](inputs/优化计划.txt) | 先单景质量、保持黑幕/距离/温柔文案、真机与注入分开、视觉/代码独立交接、无障碍与关于页 | “快照没落地”“结尾光效仍程序降级”已过期；阶段A/B/E实现部分不重做；不把缺真机当成设计/代码独立开发的阻断 |
| [技术优化建议](inputs/技术优化建议-20261020.txt) | 精确定位主线程解码/阻塞、视差钳制、insets、步长设置、触感、颜色与构图问题 | “0m增加基础风景”冲突；“后656m完全静止”忽略其他层继续按距揭示；8–12%旅人高度不是已定产品标准；恢复入口已存在；雨林不能直接改为tileable |

## 源码复核与决策

| 项目 | 核查依据（以上精确基线的仓库路径） | 结论/去向 |
| --- | --- | --- |
| 已有恢复 | `domain/session/SessionSnapshot.kt`、`data/SessionSnapshotStore.kt`、`SenseWalkApp.kt`中的PendingRestore、SW004批准记录 | 不是重做任务；回归恢复/损坏/终态，新增设置字段必须兼容旧快照 |
| 已有地形/光效 | `domain/walk/TerrainMotor.kt`、`assets/scenes/forest.json`五层asset、SW005R2/SW010记录 | 不重复生产或撤销原批准；视觉更新用新的任务链 |
| Edge-to-Edge | `MainActivity.kt`已调用enableEdgeToEdge与setDecorFitsSystemWindows(false) | 不再“开启”；需要保护裸Box页面上的控件与触摸区，SW020 |
| 图层解码 | `ui/session/ForestShell.kt` remember中decodeStream | 确认组合期同步解码；SW019后台加载。约20MiB是五张768×1376×4字节的估算，不是设备峰值实测 |
| 实走阻塞 | `ui/session/RealWalkContent.kt`的RealWalkVisualCache.runBlocking；`data/SceneRepository.kt`已有withContext(IO) | IO工作本身已经后台执行，但调用UI线程同步等待仍存在；SW019移除等待，不能说所有JSON在UI线程解析 |
| 高频状态 | `ui/session/SessionScreen.kt`顶层读取walk；VM逐帧发布Snapshot | 有较大重组作用域风险；实际哪些子节点重组需计数，不能源码推断“整树每秒60次”已实测 |
| 视差 | `ForestShell.kt`的drawImageLayer/PX_PER_METER，`forest.json` parallax .3/.3/.6 | 在1080×2400下横向溢出约259px，远/中层约144m、叶层约72m时钳满；叶层400m才解锁。图层移动受限不等于之后全画面静止，揭示透明度及角色仍变化。SW021→022→023解决 |
| cover几何 | drawImageLayer只按高度缩放 | 宽高比不匹配时可能铺不满；SW023明确cover=max(宽比,高比)，tile另设策略，不一律对现有图取模 |
| 步长 | SettingsRepository无stride；WalkForegroundService创建RealWalkController未传stride；RealWalkEngine已支持范围 | SW020打通持久化→服务→引擎，默认0.70、0.45–0.95；区分cm/m与会话冻结/恢复语义 |
| 触感 | Joystick只有颜色变化；实际haptic backend已存在 | SW020补每局两种一次性反馈，服从设置与生命周期；不绕开振动开关 |
| 场景颜色 | Theme.sceneTint硬编码；ModeCard使用forest；ScenePalette已存在森林/雨林 | SW021给UI规范，SW023消费themeColor修UI色源；themeColor是强调色，不足以替代完整六色板，不盲删现有palette |
| DataStore | SettingsRepository使用Context.preferencesDataStore委托 | 多个repository包装不等于多个DataStore实例；本轮不为这个论据强上DI框架 |
| 逐帧drawImage缩放 | Canvas drawImage dstSize | 不等于CPU每帧重新采样位图；不能盲目预放大到大屏导致内存增加。SW019按测量与实际缓存预算做 |
| 领域分配 | PhaseScheduler/snapshot/drainPhaseEvents | 有分配代码但“600次/秒GC”“8–12次每帧”非剖析结果。不得clear已经交给消费者的事件列表；先测再改 |
| 退暗时长 | DEVELOPMENT §11.2规定≥3s | 采用3s；不是另一计划提出的1–2s。先终态冻结输入/释放引擎再呈现，reduceMotion按静态替代，不延长计距 |
| GPS与留存 | DEVELOPMENT §13将GPS/本地累计置P2；无排行/焦虑 | 后置；“增加回来理由”不足以授权本轮定位、轨迹、健康同步或打卡 |
| 文件所有权 | PROTOCOL | `design/assets/**`归MiniMax，不是第三份文档所说的Trae；用户共享checkout未跟踪雨林稿保持原样 |

## 提示截图仍待复核

SW018的作者核查与独立review已approved/accepted，这一历史事实保留。但bootstrap于上轮直接查看、并在本轮读取同一基线的`docs/collaboration/evidence/H-SW-018-R1/screens/H2-hint-appear.png`与`H2-hint-gone.png`：前者能看到微蹲旅人，**未看到“慢一点，站稳再跳。”卡片文字**。这不足以证明提示出现及随后消失；文件名和日志不代替画面。800m通关截图确实有“走完800m”。

该发现是证据范围修正，不据此断言UI必坏，也不推翻整个SW018或要求重做越坎。SW024由QA追加correction及真实同步截图/短录像/UI层级与单调时间；若复现代码缺陷再给ZCode具体步骤。计步/锁屏/耳机/物理重启仍无新增真机结果。当前测试包继续可用于收集这些反馈。

## 未采用的建议

- 0m加天空/雾/地面、提前显示完整终景：冲突于DEVELOPMENT §9与视觉契约，拒绝。
- 直接将当前非无缝素材循环，或把森林平铺要求塞进冻结的雨林SW012/D009：拒绝。森林单建SW021→022→023，雨林维持tileable=false。
- 同时重构全部控制器、拆domain模块、加Hilt/Koin、换引擎/播放器/依赖大版本：暂缓，不能拿架构改造代替实际体验问题。
- 将传感器处理一律移后台：暂缓；必须先证明热点并维护服务事件串行性，否则可能引入计距竞态。
- 单凭alpha统计、截图存在、模糊阈值或未经测量的“必然掉帧/ANR”结论放行：拒绝。
- 8–12%旅人屏高、强行双列、不解释的禁用卡片、所有页强制同一安全区padding：仅作设计比较，按实际小屏/大字号结果选方案，不直接升级为产品硬规范。

## 官方实现参考

执行时兼容本仓库现有Compose版本，不照搬最新示例顺带升级依赖。高频读取下沉/derivedStateOf参见[Compose性能实践](https://developer.android.com/develop/ui/compose/performance/bestpractices)；系统栏保护参见[Window insets](https://developer.android.com/develop/ui/compose/system/insets)；递增versionCode与可见versionName参见[Android版本管理](https://developer.android.com/studio/publish/versioning)。这些是实现依据，不证明本项目已测得收益。
