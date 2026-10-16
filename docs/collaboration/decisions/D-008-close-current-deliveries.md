# D-008 · 已交付内容先验收收口

日期2026-10-15；类型bootstrap计划维护；依据 [P-20261015-02](../evidence/P-20261015-02/README.md)。不改变产品米数/门禁，不替产品作者作独立批准。

1. SW010旧state冲突已经解决，当前实际门禁是历史交接文件改写造成协作CI失败。作者用新文件记录同步、恢复旧文件字节，不放宽immutable检查。原批准业务/素材不变时复核新head/delta/CI再集成。
2. SW005 R1核心已交但没有UI消费者，提示/站稳/轻跳属于当前DEVELOPMENT要求。bootstrap登记rework，由ZCode R2补齐，不将必需功能挪到queued SW007；正式review由Antigravity另写。
3. SW012 R1已发布，登记handoff_ready；冻结可以由新QA review/decision引用当前spec SHA256完成，不需要编辑Trae拥有的design_candidate/proposed原字节。实质修改由Trae新revision/manifest/hash重审。未批准样本可以用来测试解析，不能绕过SW015/SW006门禁。
4. SW015保持ready，未见远端交付；不据此判断外部工具是否正在执行。SW006仍等SW012和SW015都accepted；当前工具任务0 API，原素材总8次尝试不重置。
5. 保留常驻队列与四角色稳定入口，不建重复协调任务、不自动发消息。main/未合PR/作者本地XML/云端CI/物理设备证据分别标注。
