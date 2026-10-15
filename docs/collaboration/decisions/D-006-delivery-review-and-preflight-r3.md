# D-006 第四轮以验收集成为近期里程碑

日期：2026-10-14；状态adopted。用户要求继续核查并给四角色分别的执行入口。Codex作bootstrap计划维护，不授予产品批准。

依据 [P-20261014-03](../evidence/P-20261014-03/README.md)：ZCode已解决冲突/补纠正/屏比证据，两个PR最新合并checkout云端通过；MiniMax已发布R2但实测仍有五类误放行；Antigravity无新共享review，Trae仍只有本机草稿。

- 不增加启动任务或调度系统；Antigravity持续队列优先SW-001 R2→SW-010→预检最新revision/收到的设计，符合明确条件就顺序集成并激活依赖，不以协调任务accepted结束工作。
- 更新registry远端观察到d11873f/393f225/bda0b74，保留正式R1 review和所有历史记录。SW-001/SW-010仍handoff_ready；SW-014仍rework但目标改R3，原因是本轮实测，不冒充独立changes_requested。生产者private state不代写。
- SW-014 R3必须移除manifest控制的默认门禁旁路，隔离fixture与生产入口；修alpha/检查图/批准链/账本，读取批准spec而非硬编码。测试模式的成功不表示SW-012真实accepted，也不授予付费调用权限。
- ZCode不重复已经完成的冲突/元数据处理；等待明确QA结果，只有依赖accepted才开发SW-004。Trae优先共享现有稿，不因未共享重复生成。
- 当前退出目标是独立review/集成SHA/组合CI/新测试包，以及可消费的设计与预检工具；产品米数/相位/opacity、API总预算和物理/真人Pending保持。城市/沙漠在SW-008启用前再拆分，不提前混做。

计划与入口发布不表示外部工具已收到消息；由用户分别发送稳定roles入口提示词。
