# 协作任务看板

> 自动生成：仅编辑 registry.json，再执行 python3 tools/collaboration.py render。状态是交付登记，不是产品最终验收。

基线：`8056e11` · 更新日期：2026-10-13 · 协调者：antigravity

| ID | 任务 | 负责者 | 状态 | 前置 | 最新交付 / 审核 |
| --- | --- | --- | --- | --- | --- |
| SW-001 | [T06 可靠性补强](tasks/SW-001.md) | zcode | ready | — | — / — |
| SW-002 | [森林光效候选验收收尾](tasks/SW-002.md) | minimax | ready | — | — / — |
| SW-003 | [独立基线验收与协作集成启动](tasks/SW-003.md) | antigravity | ready | — | — / — |
| SW-010 | [森林光效批准候选入包](tasks/SW-010.md) | zcode | queued | SW-001, SW-002, SW-003 | — / — |
| SW-004 | [T07A 会话快照与中断恢复](tasks/SW-004.md) | zcode | queued | SW-001, SW-003 | — / — |
| SW-006 | [T07C 雨林候选素材批次](tasks/SW-006.md) | minimax | queued | SW-002, SW-003 | — / — |
| SW-005 | [T07B 自动越坎与站稳规则](tasks/SW-005.md) | zcode | queued | SW-004 | — / — |
| SW-007 | [T07C 雨林双模式与素材接入](tasks/SW-007.md) | zcode | queued | SW-005, SW-006 | — / — |
| SW-008 | [T08 四景内容与一致性](tasks/SW-008.md) | zcode | queued | SW-007, SW-010 | — / — |
| SW-009 | [T09 真机内测与发布候选验收](tasks/SW-009.md) | antigravity | queued | SW-008 | — / — |

## 生产者状态（辅助，不能替代审核）

| 角色 | 当前任务 | 自报状态 | 最近交付 |
| --- | --- | --- | --- |
| antigravity | [查看本角色实时状态](state/antigravity.json) | 生产者单写 | [查看交付目录](handoffs/README.md) |
| minimax | [查看本角色实时状态](state/minimax.json) | 生产者单写 | [查看交付目录](handoffs/README.md) |
| zcode | [查看本角色实时状态](state/zcode.json) | 生产者单写 | [查看交付目录](handoffs/README.md) |

## 实体验证仍待完成

- 标准距离真人手动行走
- 真实计步与锁屏15分钟
- 实体耳机/来电与振动
- 真机视觉走查
- 最终5–8人内测
