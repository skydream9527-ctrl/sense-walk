# 可直接转发的四份提示词

本轮总体安排见[执行计划](README.md)。以下文本指向稳定角色入口，完整范围/依赖/验收在仓库文件中。先将本轮规划PR合入main，再让各工具fetch；不要在共享checkout切分支。文件存在不表示工具已收到消息。

## ZCode

```text
先fetch最新origin/main，保留现有工作，在你自己的独立checkout/worktree中读取并执行docs/collaboration/roles/zcode.md。本轮按docs/collaboration/plans/2026-10-20/README.md与registry领取SW-019，独立交付后依次做已启用的SW-020、SW-025；SW-023等设计和候选批准后再做。每项独立PR和准确handoff，不重做已accepted的恢复/越坎/光效，不改黑幕、距离门禁或冻结测试包。无需补齐本地Android环境，复用GitHub Actions。
```

## MiniMax Code

```text
先fetch最新origin/main，保留已有SW-006/PR25及未提交素材，在你自己的独立checkout/worktree中读取并执行docs/collaboration/roles/minimax.md。本轮先收SW-006的零API生产guard和R2交接；SW-021独立批准且SW-022启用后，按其精确design_ref制作森林平铺候选。当前森林候选为零付费范围，雨林既有总8次预算不借用、不重置。只交候选、实际预览和哈希，不复制到生产assets，不自判approved。
```

## Trae Design

```text
请使用Design模式。先fetch最新origin/main，保留已有设计，在你自己的独立checkout/worktree中读取并执行docs/collaboration/roles/trae-design.md，领取SW-021。按docs/collaboration/plans/2026-10-20/README.md产出森林连续视差与界面精修设计，给MiniMax和ZCode分别提供可消费规范。0m保持近黑，沿用五层距离门禁，设计模拟与App截图分开，保留SW-011/012/017和雨林D-009原字节，0付费API，不直接改app或候选。
```

## Antigravity

```text
先fetch最新origin/main，保留现有工作，在你自己的独立checkout/worktree中读取并执行docs/collaboration/roles/antigravity.md，先做SW-024，再按队列持续独立审查与顺序集成。重点读取docs/collaboration/plans/2026-10-20/SOURCE-REVIEW.md中的提示截图缺证，追加correction，不照抄文件名宣称闭环。保持registry单写与真实head/hash，SW-019/020/025通过即可交第一批测试包，无需等平铺素材；设计→候选→SW-023另交第二批。真机/真人项如实Pending，不重复发布同源码APK，不覆盖build176。
```
