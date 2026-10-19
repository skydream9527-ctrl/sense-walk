# Antigravity 常驻验收队列

2026-10-18；main当前推进至 `30780af`。最新规划 [P-20261016-01](../evidence/P-20261016-01/README.md)（PR #21）、预发布（build-153-15e000b）及审计补证（PR #22）均已合入，旧已接受任务（SW-001/SW-004/SW-005/SW-010/SW-011/SW-012/SW-014/SW-015）保持 accepted。

| 优先级 | 当前状态 | 退出条件 |
| --- | --- | --- |
| 最新组合包 | 已发布 [build-153-15e000b](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-153-15e000b)；真实APK SHA-256 (`6600f554...`) 与源码包已本地独立下载验证通过 | 产物与commit一致，真机计步/锁屏/重启与5-8人内测依协议仍保持Pending |
| 审计与时序说明 | PR #22已合入；[R-SW-015-R1-correction.md](../reviews/R-SW-015-R1-correction.md) 校准交付SHA；[R-SW-005-R2-correction.md](../reviews/R-SW-005-R2-correction.md) 记录提示时序实测Pending | 归档说明已入库，不覆盖历史评审原文，不影响代码已accepted结论 |
| SW-016 / ZCode | ready；作者本地工作区已有底座实现 `c87366d`（312项单测0失败/D-009参数精确核对/双模式/声景清单），等待作者完成交付与PR | 实际Kotlin/配置/渲染/两模式复用/快照；来源许可/声音听辨；底座≠雨林完成 |
| SW-006 / MiniMax | ready；作者本地已有雨林候选生成草稿，正在进行0API生产guard与预检自测，等待作者完成交付与PR | 先核任务内0API生产guard：真实D009批准、实际1080x1920、跨revision总8次/API前ledger；到稿后独立像素/alpha/四检查/阶段/裁切/预算/来源/hash |
| SW-017 / Trae | ready，应用上下文参照 | 两模式/阶段/比例/状态、清单/可编辑源/hash；design模拟明确，不改D009/不替App，不成素材新前置 |
| SW-007激活 | queued，依赖SW-005(已完成)+SW-006(等待制作)+SW-016(等待交付) | 后两项均accepted再ready，批准图正式入包+900m双模式/真实声景/组合App独立回归 |

中心状态由QA维护，各作者state本人消费。源码/已有XML/云端artifact与真正运行模拟器/实体/真人分开；无设备/人Pending，不宣称最终MVP。城市/沙漠继续queued，先雨林闭环再拆任务/预算。无新交付一次报告等待项，不无限轮询/自动发消息/商店发布。
