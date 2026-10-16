# 后续协同路线

2026-10-15核查main=904ab01。详见 [P-20261015-02](evidence/P-20261015-02/README.md)；不按任务数量或CI绿推算MVP百分比。

| 阶段 | 任务/负责者 | 当前事实与退出条件 |
| --- | --- | --- |
| 已验收 | SW001可靠性/SW004快照，SW011森林设计/SW014 R3 | accepted/入main；真机项Pending，设计不是正式素材 |
| 收口接图 | SW010 / ZCode→Antigravity | PR3原approved、冲突已解；修旧交接改写导致的协作红，QA复验新head/hash/CI后合入 |
| 补齐地形 | SW005 / ZCode→Antigravity | PR14核心+22测试已交、CI绿；rework R2接UI提示/步态/减少动效/恢复，不能等SW007才做 |
| 雨林审稿 | SW012 / Trae→Antigravity | PR15/53文件hash匹配、CI绿；补消费说明，QA用精确spec hash冻结参数，实质改动Trae R2 |
| 当前关键接口 | SW015 / MiniMax→Antigravity | ready、未见远端交付；0API真实id/type与严格非空/批准链/账本自动测试 |
| 雨林素材 | SW006 / MiniMax→Antigravity | queued；SW012+SW015都accepted/集成后启用原总8次尝试预算，候选/验图独立 |
| 雨林应用 | SW007 / ZCode→Antigravity | queued，等SW005+SW006；900m双模式、真实专属声景、批准素材、门禁/恢复/实际App |
| 四景 | SW008 / 四角色 | queued；雨林稳定后，激活前拆城市/沙漠设计→候选→接入子任务及预算 |
| 持续设备/最终 | SW009 / Antigravity组织 | 可提前执行设备矩阵；最后5–8人体验与严重问题关闭，不伪造真人/物理结果 |

沿用现有四角色独立worktree、registry、handoff/review/evidence和 [常驻验收队列](queues/antigravity.md)。当前并行的是ZCode收口、MiniMax接口、Trae待审说明、Antigravity审稿/集成；任务accepted由独立review和实际merge决定。共享checkout只读，private state由本人维护，不新增调度器/自动消息/重复协调ID。

只从实际合入main出GitHub测试Release。已确认 [build109](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-109-6104e3d) 含可靠性/快照，未含接图/地形；下一组合包绑定实际commit/APK/source/hash。无需完善本地Android环境。
