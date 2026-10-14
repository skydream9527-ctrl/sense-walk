# Antigravity 常驻验收队列

更新依据：[P-20261014-02](../evidence/P-20261014-02/README.md)。本队列保存已观察的远端交付/待收稿；它不是 review，不改变作者文件，也不授予 approved。先 fetch 最新 main/角色分支，再读取实际最新 handoff；若以下 head 已更新，比较差异并记录新的完整 head，不能沿用此快照批准。

| 顺序/任务 | 发布位置与当时业务/交付head | 验收动作 |
| --- | --- | --- |
| 1 / SW-001 R2 | [PR #1](https://github.com/skydream9527-ctrl/sense-walk/pull/1)，`codex/zcode/SW-001-t06-reliability`；业务 `7b17424886ba4b0c7608bd451f0ee244f3b88390`，交付 `c026c641a98bd9b9c86ac31a88da31f18857ecc8`；分支文件 `docs/collaboration/handoffs/zcode/H-SW-001-R2.json` | 实际 Kotlin 低步数同刻合并、counter-only cue 到 SensoryCoordinator、detector成功无双cue、下降/暂停/重启、服务/调试release边界；同步main后全head及CI；记录 R-SW-001-R2 |
| 2 / SW-010 R1 | [PR #3](https://github.com/skydream9527-ctrl/sense-walk/pull/3)，`codex/zcode/SW-010-forest-lightshows`；业务 `a1df0e295b7c95d6212b8c65d597087a9458d906`，交付 `dfcc19edd7a73a02cfa1261d6223496b4d0f3fa8`；分支 `H-SW-010-R1.json` | 两层批准hash→正式文件→JSON接线；实际app六阶段、中央/边缘/cover/不同屏比/停走；终景柔光意图判断；冲突解决后PR合并版本CI；记录独立review |
| 3 / SW-014 R1→R2 | `codex/minimax/SW-014-rainforest-preflight`；业务 `7d047a22ddde21664983db5ee298c18d805b5326`，交付 `13d6c0d51261a467feb2c3a57705ae7820198e49`；分支 `H-SW-014-R1.json`，当前未观察到PR | 正式核对 PF-01～04；若R2已提交审最新版本，否则记录R1具体退回；批准/哈希/路径/真实解码/隔离fixture/累计账本验收。Android CI绿不算脚本行为验证 |
| 4 / SW-011 | 本机草稿，尚无共享head/handoff；等待Trae推送 | 不复制草稿替作者交付；收到后验证43份或实际最新manifest、源/预览/spec/逐层提示词与裁切；approved后激活SW-012 |

前两 PR 的已观察冲突仅在 `state/zcode.json`。让 ZCode 在自己的工作分支顺序合并最新 main、保留双方交付信息，禁止跨角色改 private state 或用 reset/全选一方。同步造成业务/配置变化需新业务 head/revision；只文档/state变化也须逐项核对并记录实际 PR head。

审核与集成顺序：优先可靠性 R2→独立review/集成→激活SW-004；SW-010依赖已经满足，可独立review，但最后测试包须验证二者组合。SW-014不依赖尚未批准的雨林实图，测试正例必须是显式隔离fixture；不得在真实registry伪造SW-012批准。Trae稿可随到随审，SW-006仅在SW-012/SW-014 accepted后启用。

SW-003、SW-013的coordination accepted不等于所有产品完成，也不停止本队列。执行角色为antigravity的独立review/登记/集成属于协议中的持续职责，不要求每次核查新增协调任务。维护本文件时更新来源/状态，不改历史handoff/review；没有新交付就报告需等的文件，不无限轮询。

批准后按分支保护合入，记录精确merge SHA与实际Actions，再登记accepted并render BOARD。两个工作PR与规划PR依次同步，避免中心文件并发冲突。测试预发布只在获准集成版本上使用现有workflow；归档最小XML/必要截图，APK Release记SHA256。真机/真人仍Pending，不能拿作者模拟器截图当亲自复验或真机证据。
