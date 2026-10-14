# R-<TASK>-R<REVISION> 独立审核

配套 [review.json.example](review.json.example)。记录审核角色、producer、精确 head 和 handoff 路径。

## 结论

approved / changes_requested / blocked；批准仅覆盖本轮 SHA/哈希与指定验收范围。

## 实际执行

命令/CI/设备、真实测试统计、截图/素材哈希。历史证据与本轮亲自检查分开。

## 发现

每项有ID、严重度、触发、实际/预期、影响、文件行号（绑定SHA）、证据类型、建议修复和回归。不能把猜测写成实测。

## 待验证与集成

未执行设备项保留 pending；说明能否接受代码阶段、是否允许集成、产品里程碑仍缺什么。

## 后续

退回生产者→下一 revision；通过→集成 SHA、合入后 CI 与下游 ready 条件。
