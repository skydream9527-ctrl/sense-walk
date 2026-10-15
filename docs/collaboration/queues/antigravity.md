# Antigravity 常驻验收队列

本轮依据：[P-20261014-03](../evidence/P-20261014-03/README.md) 及第四轮独立验收执行。下表保存当前队列状态与各任务验收动作：

| 优先级 / 任务 | 交付入口与版本 | 当前状态与验收动作 |
| --- | --- | --- |
| 1 / SW-001 R2 | [PR #1](https://github.com/skydream9527-ctrl/sense-walk/pull/1)，head `d11873f3d5553fda872dd18f4483ca1e1b11223a`，业务 head `7b17424886ba4b0c7608bd451f0ee244f3b88390` | **已验收并集成 (accepted)**：出具 [R-SW-001-R2](../reviews/R-SW-001-R2.md)（approved），PR #1 已合入 main（merge `1e238812c62c97486e96fa68c2eecbf450e160a0`）；下游任务 `SW-004` 激活为 `ready` |
| 2 / SW-010 R1 | [PR #3](https://github.com/skydream9527-ctrl/sense-walk/pull/3)，head `393f22570a541118d80e7a50c6860c3b57f2fd49`，业务 head `a1df0e295b7c95d6212b8c65d597087a9458d906` | **已完成独立审核 (approved)**：出具 [R-SW-010-R1](../reviews/R-SW-010-R1.md)；终景柔光意图裁定通过；待 ZCode 同步最新 main 解决 state 冲突后合并 PR #3 |
| 3 / SW-014 R2→R3 | `codex/minimax/SW-014-r2`，head `bda0b74d53791c09a4c9b7a2858b9c32321bc862`，业务 head `6e683e2087574df51efd43d8dea73270d321f5aa` | **已完成独立审核 (changes_requested)**：出具 [R-SW-014-R2](../reviews/R-SW-014-R2.md)；记录 R2-01～R2-05 等 5 项缺陷，登记 rework，等待 MiniMax 在 R3 修订 |
| 4 / SW-011 | 本机草稿，尚无共享 head/handoff | **等待交付**：等待 Trae 提交推送已有 43 份设计包；收到真实 PR 后按规范独立审核 |

## 协作与集成说明

1. **SW-001 成功集成入 main**：云端 249 项全量单测通过，Kotlin 低步数合并带回、detector 注册失败距离脚步音回退与 SessionArbiter 状态机经独立 QA 套件验证无误。PR #1 已合并（`1e23881`）。下游依赖解除，`SW-004`（会话快照与中断恢复）正式就绪（`ready`）。
2. **SW-010 审核通过**：候选素材 SHA256 100% 吻合 SW-002 批准结果，`forest.json` 接线无损保留产品参数；长屏/小屏六阶段铺展无畸变，停走冻结画面主体 0 像素差；终景微光裁定符合设计意图。PR #3 因 main 刚刚并入 PR #1 产生 `state/zcode.json` 冲突，由 ZCode 同步 main 后合入。
3. **SW-014 退回 R3**：工具脚本根路径已修，但存在测试标记绕过生产门禁、透明度计算反转、检查图清单缺失放行、API 账本无负数校验及假超预算 fixture 等问题，已详尽记录于 `R-SW-014-R2` 并指引 R3 修复。雨林生图任务 `SW-006` 保持锁定，API 预算零消耗。
4. **测试预发布准备**：待 PR #3 合入后，针对包含可靠性补强与森林光效接线的组合 main 执行 CI，并按 GitHub Actions 触发打包发布新测试版本，彻底替换旧 build-41。
