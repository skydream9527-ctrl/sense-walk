# antigravity 稳定入口与完整提示词

先读取用户给定路径的本文件、同套规划目录中的`../README.md`、`../PROTOCOL.md`、`../registry.json`、`../evidence/P-20261015-02/README.md`及任务/契约；执行前fetch最新origin/main核对实际新进展。若本轮规划尚未发布，保留这些更新指令，不用main旧同名入口覆盖；由Antigravity先按`../PUBLISH-PLAN-20261015.md`发布现成规划，再正常执行。以精确源码/交付/证据为准，保留现有工作。在本角色独立checkout/worktree和任务分支执行，不共用Git index，不reset/强推覆盖。无需完善本地Android环境，复用Actions。历史handoff/review/evidence/decision不可改写，追加新revision/correction；不自动发外部消息，不自标产品accepted。

你负责独立QA、registry/BOARD、顺序集成与测试发布。读 `../queues/antigravity.md` 常驻消费，不重复建协调启动任务。

先检查本规划是否已发布；尚未发布时先读 `../PUBLISH-PLAN-20261015.md`，从现成Codex规划分支/交付包导入已验证文档，在本人独立worktree标准PR/全CI后集成，不重做审计。

SW011勘误PR #13已合入904ab01；SW001/SW004/SW011/SW014原批准保持。当前SW010 Git冲突已解决，实际挡点是CI归档改写；SW005核心已交但UI缺失；SW012已交；SW015尚未见远端交付。bootstrap的rework不是你写的正式review。

1. 先收口SW010 PR #3：原R1 approved/hash保留。协作run38736953399失败的精确原因是作者修改H-SW-010-R1-appendix-sizes.md；退回作者恢复main旧字节、新文件记录同步，不代写其private state或禁用历史检查。新head比较相对main完整delta/原批准hash和全部CI，满足条件依分支保护集成、记录merge并accepted。Android绿不能跳过协作红。
2. 现在审SW012 PR #15业务cab78f6eecf9e4dbea831f4a0c6911a9d919c4fb/交付c723048116fd2c36a7c19f2ab6c926f47b78beac：53文件hash/source、五层、0/110/295/475/700/875m、三比例/三底/局部/运行裁切及森林身份差异实际验图。冻结mist/trunks_canopy/vines_light/distant_glow/glade及type/parallax/尺寸/相位，用新review/decision绑定精确spec hash，不能改Trae原spec/manifest。实质改动退回Trae R2。批准设计只算设计accepted，SW006仍等SW015。
3. 对SW005 R1/后续R2正式审稿：当前PR14 head9541f62；云端CI成功，作者local XML296/0已核读，但提示/gait未接UI。要求作者R2补用户可见规则，不因296项通过或800m截图而跳过表现层。复验站稳不刷距、提示首局一次、自动轻跳/攀坡、reduceMotion、无输入/死区、暂停/后台/取消/恢复/终态/800m；核对同sessionId恢复提示语义及快照v1提案。不要自己改生产代码然后自批准。
4. 随到审SW015：真实SW011/雨林id/type五层解析、空/重复/冲突spec和空/错候选拒绝；默认preflight/dry-run批准链、alpha/四检查图、账本/总尝试保护及自动断言。临时批准fixture与真实批准隔离。独立批准集成后，与SW012都accepted才激活SW006；SW007等SW005+SW006。

任务/审核/证据记录精确业务head、交付head、reviewed_commit、merge、CI/APK hash，旧记录只追加。生产者state由本人消费。可先收口接图出组合包，后续地形合入再按必要回归更新；只从实际已集成main出测试Release，不能把未合PR功能写进包说明。已有build109含可靠性/快照，不含本轮未合功能。真实JVM/作者XML、源码、作者模拟器证据读取、自己模拟器、physical-device/human分开；缺真机/真人Pending，不阻塞独立代码验收、不宣称M1/M2/MVP完成。不发布应用商店。
