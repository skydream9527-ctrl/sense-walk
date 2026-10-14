# 会话快照契约草案 v1（SW-004 冻结后生效）

这是 T07A 的输入要求，**尚未实现或验收**。DEVELOPMENT §12.3/20.3 的产品语义仍优先。ZCode 在 SW-004 开始时把具体字段/兼容策略交给 Antigravity 形成决策，再实施消费者；不要求另一个 agent同时写领域模型。

必须包含：sessionId、快照版本、sceneId/scene schema版本或配置标识、mode、state、savedAt、meters、s_pos、s_best、firedPhaseIds、elapsedActive。实走补 counter最后读数、sensor事件时间、启动/boot时间基准；感官恢复补当前已揭示目标和可重建环境状态，不恢复旧 SoundPool stream。

快照版本与 scene schemaVersion=2 区分，不直接复用错误的同一个字段含义。保存 wall time 用于30min候选时限，事件/速度用统一 monotonic/boot 基准；跨重启不能直接减旧 sensor timestamp。字段名与值类型在实现前冻结为具体模型并附样例。

虚走 progress 必须保留 s_best≥s_pos，合法回退恢复不重复计距；NaN/Infinity/负数、超终点、不认识的场景/相位/版本属于损坏/不兼容，不盲目钳制成有效存档。

每5s、越相位、重要状态变更保存；主动放弃/完成清快照；进程死亡不依赖 onDestroy。只有被动中断且30min内可选择恢复；恢复后虚走 Ready 等新输入，实走重新建基线不补缺口。后台仍在合法运行的实走 Service 为当前会话，Activity 重建重绑定，不能把它当作另一份恢复会话。

验收反例：回退快照往返、快照过期/未知版本、恢复跨 boot、暂停期步数、终态迟到回调、应用冷启动与已有服务竞争恢复、恢复时同一相位提示不得重播。最终模型与序列化样例记录到契约 revision与handoff，不仅写“支持恢复”。
