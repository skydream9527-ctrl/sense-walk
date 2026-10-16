# 会话快照契约 v1（含已批准SW-005 R2可选字段）

2026-10-15状态：SW-004已实现、独立approved并accepted，生产集成`814fc78f72017c643ce43cbf4b3ced6d89c1f5bd`；依据 [R-SW-004-R1](../reviews/R-SW-004-R1.md) 和domain/session/SessionSnapshot.kt。以下语义已生效，真机跨boot/真实计步恢复仍Pending。DEVELOPMENT §12.3/20.3产品语义优先；后续地形持久中间态扩展须追加兼容决策，不暗改v1。

必须包含：sessionId、快照版本、sceneId/scene schema版本或配置标识、mode、state、savedAt、meters、s_pos、s_best、firedPhaseIds、elapsedActive。实走补 counter最后读数、sensor事件时间、启动/boot时间基准；感官恢复补当前已揭示目标和可重建环境状态，不恢复旧 SoundPool stream。

快照版本与 scene schemaVersion=2 区分，不直接复用错误的同一个字段含义。保存 wall time 用于30min候选时限，事件/速度用统一 monotonic/boot 基准；跨重启不能直接减旧 sensor timestamp。具体字段/类型已在下表冻结；变更需新revision与兼容决策。

虚走 progress 必须保留 s_best≥s_pos，合法回退恢复不重复计距；NaN/Infinity/负数、超终点、不认识的场景/相位/版本属于损坏/不兼容，不盲目钳制成有效存档。

每5s、越相位、重要状态变更保存；主动放弃/完成清快照；进程死亡不依赖 onDestroy。只有被动中断且30min内可选择恢复；恢复后虚走 Ready 等新输入，实走重新建基线不补缺口。后台仍在合法运行的实走 Service 为当前会话，Activity 重建重绑定，不能把它当作另一份恢复会话。

验收反例：回退快照往返、快照过期/未知版本、恢复跨 boot、暂停期步数、终态迟到回调、应用冷启动与已有服务竞争恢复、恢复时同一相位提示不得重播。最终模型与序列化样例记录到契约 revision与handoff，不仅写“支持恢复”。


## 已冻结的具体字段

| 字段 | Kotlin类型 | 持久/恢复语义 |
| --- | --- | --- |
| snapshotVersion | Int | 当前1，与scene schemaVersion=2独立 |
| sessionId | String | 生成UUID，validator拒绝空白；恢复沿用原ID |
| mode | String | virtual或real，未知拒绝 |
| sceneId / sceneSchemaVersion | String / Int | 场景存在且schema兼容，否则Incompatible |
| state | String | 只接受WALKING/PAUSED；终态不提供恢复 |
| savedAtWallMs | Long | 墙上时间用于30min候选时限；边界30min允许，超过Expired |
| bootCount | Int | 对比Settings.Global.BOOT_COUNT；变化标acrossBoot，不能沿旧sensor时间补距 |
| meters / sPos / sBest | Float | 非有限/负数/超终点或sBest<sPos拒绝，不钳成有效档 |
| firedPhaseIds | List<String> | 只接受已知相位；恢复不重播一次性cue |
| elapsedActiveMs | Long | 累计活跃时长，非负 |
| stabilizeHintShown | Boolean | SW005 R2新增可选字段，缺省false；同sessionId恢复保持首局站稳提示已发，不重复提示；snapshotVersion仍1 |
| lastCounterReading / lastCounterEventMs | Long? / Long? | 可选诊断字段；恢复重新建counter基线，不补缺口 |

JSON手动编码，忽略未知扩展字段，损坏输入返回null。字段使用camelCase实际名称；文档s_pos/s_best是概念别名，不创建第二套JSON字段。示例仅说明结构，不是真实运行证据：

```json
{"snapshotVersion":1,"sessionId":"00000000-0000-4000-8000-000000000001","mode":"virtual","sceneId":"forest","sceneSchemaVersion":2,"state":"PAUSED","savedAtWallMs":1000,"bootCount":7,"meters":0.0,"sPos":0.0,"sBest":0.0,"firedPhaseIds":[],"elapsedActiveMs":0}
```

存储在SessionSnapshotStore，按周期/越相位/重要状态持久化，主动放弃/完成清除；恢复入口与已有实走Service仲裁避免双会话。静态感官重建不复用旧stream、不补播旧脚步。地形任务新增状态时必须回归现有validator/虚走回退/实走基线/感官恢复用例。

2026-10-16摘要同步：可选stabilizeHintShown依据已approved的H-SW-005-R2/R-SW-005-R2，业务b92144e07f9318f1e14f7f18e0a1a28b0115f0d7，集成70ebfc7587cf4e8e07dc4979ee0c18deb1616436。旧R1“零新增字段”提案由R2修订；原hand-off保持历史。此处记录现有实现，不新批字段或改变快照版本。
