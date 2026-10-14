# H-<TASK>-R<REVISION> 交付报告

配套复制 [handoff.json.example](handoff.json.example)，元数据路径与本文一致。

- 任务/角色/接收者：
- 基线 SHA / 本轮 head SHA / PR：
- 交付范围与明确未做：

## 最终行为

写具体触发前后，不只列文件名。

## 变更与契约

列文件、消费者、接口 revision 与需要下游执行的动作。

- 设计任务：JSON附 `design_manifest`，列可编辑源、规范、逐层提示词、实际预览的全部哈希与限制，见 [设计清单模板](design-manifest.json.example) 和 [设计规格模板](design-spec.json.example)。
- 素材任务：JSON附 `asset_manifest`，列真实哈希、检查图与拒绝稿；新场景manifest的 `design_ref` 记录已批准设计任务/handoff/spec文件及SHA256。
- 代码任务：引用实际批准候选与接线差异，另交应用验证。设计预览不能充当Android截图或功能通过证据。

## 检查记录

| 检查 | 类型 | passed/failed/pending/not_applicable | 实际数量/设备 | 精确证据 |
| --- | --- | --- | --- | --- |

## 风险与待验证

真实 Pending 不藏在“全部完成”之后。超时/失败 API 请求计入账本。

## 给接收者的下一步

精确到文件/任务/候选，不自动替对方确认。请求 shared doc/status 更新也写在这里。

## 本轮复验关系

若为 R2：引用上轮 handoff/review，逐条列已修/未修。不能覆盖 R1。
