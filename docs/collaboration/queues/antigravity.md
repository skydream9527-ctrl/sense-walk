# Antigravity 常驻验收队列

本轮2026-10-15，main更新至集成SW-010/SW-012/SW-015/SW-005；观察来源 [P-20261015-02](../evidence/P-20261015-02/README.md) 及最新审核。

| 顺序 | 交付定位 | 动作/退出条件 |
| --- | --- | --- |
| 已收口 SW010 | PR #3，merge `2b47f01aa64262433b52c1a071ddfec2ba4ee249`；accepted | 归档门禁已修，全CI绿；素材hash与delta复核无误，已合入main并标记accepted |
| 已审并集成 SW012 | PR #15，merge `bb05b035f1109d974790a9e576a77a539c2e43ed`；accepted | 53文件hash全匹配、验图/裁切通过；已发 R-SW-012-R1 与 D-009 冻结五层参数及spec哈希；PR #19 intake notes已合并 |
| 已审并集成 SW015 | PR #18，merge `a235f7376f6103c6c02bef3f4c4306dd6f0cc3d5`；accepted | 真实SW-011/SW-012 spec解析完全一致；8组fixture/6类负例拦截测试100%符合预期；消耗0 API；已发 R-SW-015-R1 获批 |
| 已审并集成 SW005 | PR #14，merge `70ebfc7587cf4e8e07dc4979ee0c18deb1616436`；accepted | R2已闭环UI提示（「慢一点，站稳再跳。」3s消失）、步态消费（ForestShell HOP/TENSE）、同局恢复持久化快照（stabilizeHintShown）与死区（d=0.01/0.079/0.08）单测；全CI与303单测全绿；已发 R-SW-005-R2 获批 |
| 门禁激活 SW006 | ready，前置SW-012+SW-015全部accepted | 门禁正式激活！MiniMax可动用8次独立API预算启动雨林正式候选素材生成流水线 |
| 下游排队 SW007 | queued，依赖SW-005(已完成)+SW-006(等待制作) | 等待SW-006交付并集成后激活 |

SW011 correction PR13已完成。既有SW001/SW004/SW010/SW011/SW012/SW014/SW015/SW005批准全部有效。各作者state本人更新，QA维护registry/BOARD/review/顺序集成。
已有build109含恢复/可靠性；真实JUnit、作者local XML、作者模拟器证据读取、本人模拟器、实体/真人结果分开；缺设备Pending不阻塞独立代码阶段，不宣称最终MVP。
