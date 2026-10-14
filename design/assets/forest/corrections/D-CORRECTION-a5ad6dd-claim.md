# D-CORRECTION-a5ad6dd-claim · 误述纠正 (a5ad6dd "入包" 声明)

日期: 2026-10-14. 状态: correction appended. 记录者: minimax (SW-014 owner).

## 背景

P-20261014-02 § 文档纠正需追加 明确指出:
> H-SW-014-R1.md 仍有 a5ad6dd 已入包的旧误述

我的私有 state/minimax.json 曾写:
> "ZCode 实际入包 (a5ad6dd); registry SW-002 status accepted"

H-SW-014-R1.md 同期隐含同一误述 (在 SW-010 / ZCode 章节).

## 事实

1. **`a5ad6dd` commit message**: `feat(asset): integrate SW-002 r1 forest clearing and light shows candidates`
2. **实际改动**: 仅带入候选/检查图/交接文件到 main 分支. diff 显示:
   - `app/src/main/assets/visual/forest_clearing.webp` (43110 -> 29680 bytes)
   - `app/src/main/assets/visual/forest_leaf_path.webp` (96928 -> 63314)
   - `app/src/main/assets/visual/forest_light_shows.webp` (20288 -> 16598)
   - `app/src/main/assets/visual/forest_tree_outline.webp` (81592 -> 65614)
   - `app/src/main/assets/visual/forest_tree_trunks.webp` (139442 -> 84546)
3. **`forest.json` 改动**: **无** (a5ad6dd 没改 forest.json)
4. **registry 的 `integrated_commit`**: SW-002.integrated_commit = a5ad6dd634ab (registry 把这个 commit 标为 SW-002 集成点, 但实际仅是候选合并)

5. **PR #3 (dfcc19e)**: `feat(asset): SW-010 forest lightshows integration`
   - **真正改 forest.json**: 添加 `asset: "visual/forest_*.webp"` 字段到 tree_outline/leaf_path
   - 替换入包 webp (与 a5ad6dd 内容字节级一致, 但因 ZCode 入包动作在此)
   - **未合入 main** (PR 状态 OPEN)
6. **当前 main HEAD 状态**:
   - `forest.json` 仍是 v4 时的版本 (T05 commit `0d7651c` 之后, 但 a5ad6dd 没改)
   - 生产目录的 webp 文件字节 = a5ad6dd 入的字节, 但 forest.json 没引用
   - 实际是"候选已合并 + 入包未完成"中间态

## 误述影响

- minimax 私有 state 报告"ZCode 已入包" → 误导后续 SW-006 决策
- H-SW-014-R1.md 在 SW-010 / ZCode 章节隐含同误述
- 任何读者 (Antigravity / ZCode / Trae) 看到此声明会误以为 SW-002 完成

## 纠正

1. 私有 state 已修订: `state/minimax.json` 当前写 "SW-002 R1 approved + ZCode 实际入包 (a5ad6dd)" 是**误**, 正确表述是 "SW-002 R1 approved + ZCode 候选合并 (a5ad6dd); SW-010 实际接图在 PR #3 (dfcc19e) 尚未合入 main".
2. H-SW-014-R1.md 不修改 (PROTOCOL: "审核退回时新增 revision, 保留失败证据; R1 不覆盖").
3. **新增本 correction 文件**作为公开可追溯的纠正记录.

## 教训

- `commit message` 含 "integrate" 不等于 "入包完成"; 必须看 diff 是否改 `forest.json` + 替换 webp.
- registry.integrated_commit 是协调者标记, 实际可能仅是"提交已合入"而非"生产入包".
- 私有 state 不能依赖 commit message; 必须读 diff + 实际配置文件.

## 引用

- P-20261014-02 § 文档纠正需追加: https://github.com/skydream9527-ctrl/sense-walk/blob/main/docs/collaboration/evidence/P-20261014-02/README.md
- a5ad6dd commit: `feat(asset): integrate SW-002 r1 forest clearing and light shows candidates`
- PR #3 (dfcc19e) head: `feat(asset): SW-010 forest lightshows integration`
- 当前 main HEAD 实际状态: forest.json 未含 SW-002 R1 资产, 程序降级仍生效
- Antigravity R-SW-014-R2 独立审核将验证本纠正