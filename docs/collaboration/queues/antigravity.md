# Antigravity 常驻验收队列

本轮2026-10-15，main更新至集成SW-010/SW-012；观察来源 [P-20261015-02](../evidence/P-20261015-02/README.md) 及最新审核。快照不是独立批准，先fetch核对精确新head。

| 顺序 | 交付定位 | 动作/退出条件 |
| --- | --- | --- |
| 已收口 SW010 | PR #3，merge `2b47f01aa64262433b52c1a071ddfec2ba4ee249`；accepted | 归档门禁已修，全CI绿；素材hash与delta复核无误，已合入main并标记accepted |
| 已审并集成 SW012 | PR #15，merge `bb05b035f1109d974790a9e576a77a539c2e43ed`；accepted | 53文件hash全匹配、验图/裁切通过；已发 R-SW-012-R1 与 D-009 冻结五层参数及spec哈希；SW-006仍等SW-015 |
| 正式审稿完成/待R2 SW005 | PR #14，业务 `9a791b55`，交付 `9541f62e`；changes_requested (rework) | 核心296作者local XML/云端CI已核，但UI缺少提示与步态消费者；已发正式审稿 R-SW-005-R1，待作者R2接UI并补同局恢复/死区边缘用例 |
| 随到审 SW015 | MiniMax ready，未见远端新交付 | 真实SW011/PR15 schema，空/冲突/重复spec/空候选拒绝；原严格入口/预算/累计/alpha/四检查保护、自动断言；0 API |
| 激活 SW006 | queued，等待SW-015 accepted | SW-012已accepted冻结，仍需SW-015真实预检联调accepted后激活正式候选制作，原总8次尝试 |

SW011 correction PR13已完成，不重复。既有SW001/SW004/SW011/SW014批准保留。各作者state本人更新，QA维护registry/BOARD/review/顺序集成，旧记录新增correction而非覆盖。SW007仍依SW005+SW006，城市/沙漠先拆任务再启用。

已有build109含恢复/可靠性；待接图/地形实际集成后出对应main组合包，准确APK/source/hash/测试范围。真实JUnit、作者local XML、作者模拟器证据读取、本人模拟器、实体/真人结果分开；缺设备Pending不阻塞独立代码阶段，不宣称最终MVP。没有新交付一次报告等待文件，不无限轮询/自动发消息。
