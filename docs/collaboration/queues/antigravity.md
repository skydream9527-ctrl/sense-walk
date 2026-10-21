# Antigravity 当前独立验收队列

2026-10-20；先读[合并计划](../plans/2026-10-20/README.md)、[采纳审阅](../plans/2026-10-20/SOURCE-REVIEW.md)和registry。本轮不覆盖历史评审，不代写作者state。

| 顺序 | 对象 | 退出条件 |
| --- | --- | --- |
| 1 | SW024：提示证据与基准（已完成） | 已亲自目检并像素审计H2两图，追加`R-SW-018-R1-correction.md`与`h2-pixel-audit.json`；已固定同环境性能比较协议与7项UI回归入口 |
| 2 | SW019（已批准入main `b59da1b`）→ SW020（已激活ready）→ SW025 | SW019独立审核通过（`R-SW-019-R1`）并激活SW020；待ZCode提交`H-SW-020-R1`审核安全区/步长/触感/快照兼容，通过后激活SW025 |
| 3 | 第一批测试发布（待SW020+SW025完成） | SW019+SW020+SW025全部独立通过并合入main后，触发`publish_release`产出新tag、APK/source/hash/版本/证书及真实限制声明；不等新平铺素材 |
| 4 | SW021设计（已批准入main `7d77ff1`） | 34文件SHA-256与三比例无缝repeat-x/UI规范已独立审核通过（`R-SW-021-R1`），已启用SW022为ready |
| 5 | SW022候选（已ready，待`H-SW-022-R1`） | 核验`design_ref`（`SW-021` spec `86f8a19f...`）、0新增付费API、三层源尺寸、三底/接缝/offset/阶段与五层预算（单层≤400,000B）；未合格继续rework |
| 6 | SW023生产入包与第二批测试包 | 待SW020与SW022均accepted后激活；核验cover/tile区分、旧配置兼容、候选hash=入包、800m末段位移/停稳冻结、UI与结果、实际Android证据 |
| 7 | SW006 R2（`changes_requested`，待`H-SW-006-R3`） | PR35已独立审核并出具`R-SW-006-R2-correction.md`（QA已修`test_collaboration.py` R2沙箱隔离）；待MiniMax以0 API提交`H-SW-006-R3`闭环hash/manifest同步、`vines_light.webp`≤400KB及`mist`/`glade`后处理 |
| 8 | 后续雨林 | 原SW012/D009和8次预算冻结，真实候选（SW006 accepted）与真实声景未齐前SW007继续queued，不用森林平铺要求改雨林设计 |

SW017/018已accepted且保留；H2提示截图的可见范围疑点见新SOURCE-REVIEW，不能继续把原closed文案当复核结论。真实counter/锁屏15min/实体耳机来电/重启/触觉与5–8真人继续各自Pending，收到用户反馈先记录build/设备/步骤/严重度/owner并回归。无新交付一次报告待文件，无无限轮询、自动外发或商店发布。
