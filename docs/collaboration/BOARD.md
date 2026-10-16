# 协作任务看板

> 自动生成：仅编辑 registry.json，再执行 python3 tools/collaboration.py render。状态是交付登记，不是产品最终验收。

基线：`8056e11` · 更新日期：2026-10-16 · 协调者：antigravity

| ID | 任务 | 负责者 | 状态 | 前置 | 已入库交付 / 审核 |
| --- | --- | --- | --- | --- | --- |
| SW-001 | [T06 可靠性补强](tasks/SW-001.md) | zcode | accepted | — | [H-SW-001-R2](handoffs/zcode/H-SW-001-R2.json) / [R-SW-001-R2](reviews/R-SW-001-R2.json) |
| SW-002 | [森林光效候选验收收尾](tasks/SW-002.md) | minimax | accepted | — | [H-SW-002-R1](handoffs/minimax/H-SW-002-R1.json) / [R-SW-002-R1](reviews/R-SW-002-R1.json) |
| SW-003 | [独立基线验收与协作集成启动](tasks/SW-003.md) | antigravity | accepted | — | [H-SW-003-R1](handoffs/antigravity/H-SW-003-R1.json) / — |
| SW-011 | [森林图片设计与通用视觉规范](tasks/SW-011.md) | trae-design | accepted | — | [H-SW-011-R1](handoffs/trae-design/H-SW-011-R1.json) / [R-SW-011-R1](reviews/R-SW-011-R1.json) |
| SW-010 | [森林光效批准候选入包](tasks/SW-010.md) | zcode | accepted | SW-002, SW-003 | [H-SW-010-R1](handoffs/zcode/H-SW-010-R1.json) / [R-SW-010-R1](reviews/R-SW-010-R1.json) |
| SW-004 | [T07A 会话快照与中断恢复](tasks/SW-004.md) | zcode | accepted | SW-001, SW-003 | [H-SW-004-R1](handoffs/zcode/H-SW-004-R1.json) / [R-SW-004-R1](reviews/R-SW-004-R1.json) |
| SW-012 | [雨林图片设计包](tasks/SW-012.md) | trae-design | accepted | SW-011 | [H-SW-012-R1](handoffs/trae-design/H-SW-012-R1.json) / [R-SW-012-R1](reviews/R-SW-012-R1.json) |
| SW-006 | [T07C 雨林候选素材批次](tasks/SW-006.md) | minimax | ready | SW-002, SW-003, SW-012, SW-014, SW-015 | — / — |
| SW-005 | [T07B 自动越坎与站稳规则](tasks/SW-005.md) | zcode | accepted | SW-004 | [H-SW-005-R2](handoffs/zcode/H-SW-005-R2.json) / [R-SW-005-R2](reviews/R-SW-005-R2.json) |
| SW-007 | [T07C 雨林双模式与素材接入](tasks/SW-007.md) | zcode | queued | SW-005, SW-006, SW-016 | — / — |
| SW-008 | [T08 四景内容与一致性](tasks/SW-008.md) | zcode | queued | SW-007, SW-010 | — / — |
| SW-009 | [T09 真机内测与发布候选验收](tasks/SW-009.md) | antigravity | queued | SW-008 | — / — |
| SW-013 | [第二轮独立复验与交接收口](tasks/SW-013.md) | antigravity | accepted | SW-003 | [H-SW-013-R1](handoffs/antigravity/H-SW-013-R1.json) / — |
| SW-014 | [雨林素材交付预检准备（零API）](tasks/SW-014.md) | minimax | accepted | SW-002, SW-003 | [H-SW-014-R3](handoffs/minimax/H-SW-014-R3.json) / [R-SW-014-R3](reviews/R-SW-014-R3.json) |
| SW-015 | [真实设计规格与素材预检联调（零API）](tasks/SW-015.md) | minimax | accepted | SW-011, SW-014 | [H-SW-015-R1](handoffs/minimax/H-SW-015-R1.json) / [R-SW-015-R1](reviews/R-SW-015-R1.json) |
| SW-016 | [雨林运行时底座与真实声景准备](tasks/SW-016.md) | zcode | ready | SW-005, SW-012 | — / — |
| SW-017 | [雨林双模式应用验图参照与交接标准](tasks/SW-017.md) | trae-design | ready | SW-012 | — / — |

持续审稿与下一步：[antigravity](queues/antigravity.md)。协调轮完成不等于产品验收完成。

## 生产者状态（辅助，不能替代审核）

| 角色 | 当前任务 | 自报状态 | 最近交付 |
| --- | --- | --- | --- |
| antigravity | [查看本角色实时状态](state/antigravity.json) | 生产者单写 | [查看交付目录](handoffs/README.md) |
| minimax | [查看本角色实时状态](state/minimax.json) | 生产者单写 | [查看交付目录](handoffs/README.md) |
| trae-design | [查看本角色实时状态](state/trae-design.json) | 生产者单写 | [查看交付目录](handoffs/README.md) |
| zcode | [查看本角色实时状态](state/zcode.json) | 生产者单写 | [查看交付目录](handoffs/README.md) |

## 实体验证仍待完成

- 标准距离真人手动行走
- 真实计步与锁屏15分钟
- 实体耳机/来电与振动
- 真机视觉走查
- 最终5–8人内测
