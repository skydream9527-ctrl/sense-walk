# 本轮三份可转发提示词

先fetch合入本轮文档后的main；先阅读[能力评估](AGENT-ASSESSMENT.md)，再按已匹配职责工作。完整要求见[阶段收口](README.md)、角色入口和registry。外部工具由用户转发启动，文件不代表消息已送达。

## ZCode

```text
先fetch最新origin/main，保留已有工作，在独立checkout/worktree读取并执行docs/collaboration/roles/zcode.md，并读docs/collaboration/plans/2026-10-21/README.md。SW-019已accepted且已出森林渲染测试包，不重复实现。先领取ready SW-020，按安全区、步长/快照兼容、触感三段给出可观察现象和原始证据；关键内容未拍到写Pending。安装反馈有阻断时优先复现最小修；审核后再做SW-025，SW-023等批准平铺候选。每项独立PR与准确JSON/Markdown handoff，旧包不覆盖，不改距离门禁，不强开雨林，无需完善本地Android环境。
```

## MiniMax Code

```text
先fetch最新origin/main，保留PR25/PR35和已有原图，在独立checkout/worktree读取并执行docs/collaboration/roles/minimax.md，并读docs/collaboration/plans/2026-10-21/README.md。优先执行ready SW-022，按已批准SW-021精确design_ref先交一层接缝/offset预览校准，再制作森林三层平铺候选，脚本统一生成manifest和handoff摘要，0新增付费。雨林SW-006另分支做R3零API收尾，按本轮实核纠正旧评审不符项，修复实际head/摘要失步、406320B超限和视觉问题。R3使用revision=3新manifest；8/8预算与累计22不重置，不再调用生图。候选不复制入app，不自批准。
```

## Antigravity

```text
先fetch最新origin/main，保留已有工作，在独立checkout/worktree读取并执行docs/collaboration/roles/antigravity.md，并读docs/collaboration/plans/2026-10-21/README.md和docs/collaboration/evidence/P-20261021-01/README.md。核对本轮森林渲染测试包/真实哈希/329云端测试，收用户安装反馈；SW-019/021/024已accepted不重做。追加修正SW021 review交付SHA和SW006旧评审的错误字段/命令路径，领取ready SW-026，把现有AndroidTest草案接成可发现、实际操作UI的测试，不能把源码字符串/自等断言当UI通过；每条结论附命令、原始输出与精确head，关键发布/视觉证据另交非作者复核。再按新head独立审SW020/022/025与雨林R3，维护依赖/BOARD并顺序集成。缺真机与提示同步画面如实Pending，后续修复新tag发布，不覆盖本轮包，不用文档前进重复打包。
```
