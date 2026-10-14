# R-BASE-001 · 协作初始化源码审阅

基线：8056e11b2b366d958132dfa0d5674dbaa8577db1。作者：本轮 Codex 核查。证据类型：source + historical cloud unit reports + candidate visual inspection。结论：安排 SW-001 补强、SW-002 素材收尾、SW-003 独立复验，不篡改已经合入的历史状态。

## F-001 · P1 · 零间隔事件可刷距离（源码确认）

`app/src/main/java/com/sensewalk/app/domain/walk/RealWalkEngine.kt:85` 在intervalMs<=0时把上限改成strideMeters，而规则要求Δd<=1.4×Δt。基线(0,1000)后(100,1000)/(200,1000)各可增加0.7m；持续同刻事件可绕过速度帽。当前测试“同刻批量按单步封顶”恰好锁定错误行为；这说明全绿测试也可能只镜像实现。

预期：零或负有效间隔不涨距，定义合法基线策略并测试后续正常事件。此处是按源码可构造反例，**本轮未新增执行JUnit复现**；Antigravity需要独立失败用例，ZCode修复旧断言。

## F-002 · P1 · START_STICKY空重启会留下空前台会话（源码路径确认）

`WalkForegroundService.kt:120`默认分支先startAsForeground，再只在sceneId非空时setupSession；返回START_STICKY。在进程死亡后null Intent重启且无恢复快照时，有前台通知但无控制器。T07未实现，不能暗示已经可自动恢复。

预期：无有效会话参数/恢复候选时明确退出并清通知，或采用无空重启的策略。测试null Intent、setup中停止/失败及重复start。**真实系统重启路径本轮未跑**。

## F-003 · P1 · 硬件存在被当作注册成功（源码确认）

`StepSensorSource.kt:40/46`忽略registerListener返回布尔，只以counter!=null设置registered；`WalkForegroundService.setupSession`又忽略start()结果。设备有counter但注册失败时可能显示实走已开始却无事件，部分监听还未清理。

预期：检查实际注册结果，失败清理counter/detector部分状态，给可理解回退，服务/音频/通知不残留。Android服务与注册假适配的边界均需覆盖；不能仅引擎测试代替注册。

## F-004 · P2 · 装配期间重复start可能启动两套协程（待独立复现）

onStartCommand只检查controller==null；controller在异步loadAll返回后才设置。等待IO期间重复start可再次setupSession，需调查single-flight保护。**这是源码风险推导，不是本轮已复现实测缺陷**。SW-001调查并在handoff标明是否复现及如何排除。

## 视觉结论与待验证

v5 clearing 单层目视未见明显棋盘；它尚未入包。v5 light_shows未重做，不能继承其他层批准。人物拒绝稿不再接入，程序旅人不阻塞当前任务。某个频率/覆盖率阈值不构成通用视觉验收规则；需要实际多底色图与应用合成。

所有行号绑定本基线，后续以新head准确路径更新。M1真人、真机耳机/计步/振动/锁屏仍Pending。这个初始化审阅不冒充Antigravity已经执行的独立review。
