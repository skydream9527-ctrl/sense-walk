# R-SW-015-R1 更正 · 交付分支 SHA 校准

对已登记独立评审报告 [R-SW-015-R1.md](R-SW-015-R1.md) 及 [R-SW-015-R1.json](R-SW-015-R1.json) 的勘误说明（追加新文件，不改动已归档历史文件原文）。

## 勘误内容

在原评审报告及 JSON 中：
- `reviewed_commit`: **`81fbf2d21e7cdc3131618f9ba6450109a3420f58`**（准确，与业务实现及交接 head 一致）
- `delivery_head` 原记录为：`9c4ef5a8f4cffb0948cbb391306b4bdafd3c64c1`
- 实际 PR #18 交付分支 tip 为：**`9c4ef5a8f9691b6de8ff5038d146a4afb5eaf846`**

## 说明

本次更正仅对评审报告与 JSON 元数据中分支 tip 的笔误进行归档说明。被审核的业务代码 `reviewed_commit`（`81fbf2d`）、7 项交付 artifacts SHA-256、8 组 fixture 及 0 API 账本审查结论均保持有效，SW-015 的 `accepted` 结论与已激活的 SW-006 门禁不受影响。
