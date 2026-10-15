# Antigravity 常驻验收队列

本轮依据：[P-20261014-03](../evidence/P-20261014-03/README.md) 及第四轮独立验收执行。下表保存当前队列状态与各任务验收动作：

| 优先级 / 任务 | 交付入口与版本 | 当前状态与验收动作 |
| --- | --- | --- |
| 1 / SW-011 R1 | [PR #7](https://github.com/skydream9527-ctrl/sense-walk/pull/7)，head `9a68b99081158f38223efa7aa3dbd1580bedbb44`，业务 head `52779607f4205d4281e1200a25a78ed24d59bf74` | **已验收并集成 (accepted)**：出具 [R-SW-011-R1](../reviews/R-SW-011-R1.md)（approved），PR #7 已合入 main（merge `256d7e3b3fb426a03401c19e8495eacbd93048b2`）；下游任务 `SW-012` 激活为 `ready` |
| 2 / SW-014 R3 | [PR #8](https://github.com/skydream9527-ctrl/sense-walk/pull/8)，head `a50afebe892c6243c37dc3805a9ad3e2cf5330cd`，业务 head `f8aad383db465592bf1bd749db42bdef3e3901e2` | **已验收并集成 (accepted)**：出具 [R-SW-014-R3](../reviews/R-SW-014-R3.md)（approved），PR #8 已合入 main（merge `3ea89c16815ff93677cda00ed6e04d41728b998a`）；18 组 fixture 与回归测试实测通过；SW-006 保持锁定 |
| 3 / SW-010 R1 | [PR #3](https://github.com/skydream9527-ctrl/sense-walk/pull/3)，head `393f22570a541118d80e7a50c6860c3b57f2fd49`，业务 head `a1df0e295b7c95d6212b8c65d597087a9458d906` | **已完成独立审核 (approved)**：出具 [R-SW-010-R1](../reviews/R-SW-010-R1.md)；终景柔光意图裁定通过；待 ZCode 同步最新 main 解决 state 冲突后合并 PR #3 |
| 4 / SW-004 R1 | [PR #9](https://github.com/skydream9527-ctrl/sense-walk/pull/9)，head `db1ec81e5bc4aad5bbc23ab74a1c29c1d3ce0651`，业务 head `dac64311092f18dc1fabe49977cf845d2fa5da89` | **已验收并集成 (accepted)**：出具 [R-SW-004-R1](../reviews/R-SW-004-R1.md)（approved），PR #9 已合入 main（merge `814fc78f72017c643ce43cbf4b3ced6d89c1f5bd`）；下游任务 `SW-005` 激活为 `ready` |
| 5 / SW-012 | 状态 `ready` | **等待交付**：前置 SW-011 已 accepted，等待 Trae Design 领取开展雨林场景分层设计 |
| 6 / SW-005 | 状态 `ready` | **等待交付**：前置 SW-004 已 accepted，等待 ZCode 领取实现 T07B 越坎与姿态防作弊 |

## 协作与集成说明

1. **SW-011 成功集成入 main**：Trae Design 交付的 53 文件设计包与图元模型通过独立验收。彻底消除了历史光效/空地候选的棋盘格/硬边缺陷，逐像素裁切复核验证了恒可见带与旅人安全区，SVG/PIL 双后端模型及 manifest SHA256 零差异。PR #7 已合入 main（`256d7e3`）。下游 `SW-012`（雨林图片设计包）激活为 `ready`。
2. **SW-014 R3 成功集成入 main**：MiniMax 彻底修复了 R2-01～R2-05 等 5 项漏洞，新增动态 spec 读取（R3-06）与 5.56MB/27.44MB 真实超预算反例（R3-07）。经 Antigravity 本地实测 18 组 fixture 与 6 组回归探针，门禁与审批链无懈可击，全流程 0 API 消耗。PR #8 已合入 main（`3ea89c1`）。雨林生图 `SW-006` 仍需等待 `SW-012` 验收，保持锁定。
3. **SW-004 R1 成功集成入 main**：ZCode 交付的 T07A 会话快照与中断恢复机制通过独立验收。快照模型字段（snapshotVersion=1, UUID, 30min wall-time, acrossBoot 等）完成契约冻结；独立 QA 验证套件（12 项测试）与 274 项 JVM 单测全部通过；实走杀进程重新建基线防作弊与静态感官重建无破音/不重播验证通过。PR #9 已合入 main（`814fc78`）。下游 `SW-005`（T07B 越坎与姿态防作弊）激活为 `ready`。
4. **SW-010 待合并**：PR #3 经独立审核已通过（`approved`），待 ZCode 同步 main 后由 Antigravity 完成 GitHub 合并。
5. **测试预发布版本**：当前 main 分支已集齐 SW-001 可靠性补强、SW-011 森林视觉规范与图元模型、SW-014 R3 预检工具链以及 SW-004 会话快照持久化恢复机制，将触发发布新一版集成测试包。
