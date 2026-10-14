# 后续协同路线

2026-10-14第三轮核查：main为6d33d94，应用仍是T06基线；SW-002候选及SW-003/SW-013协调已accepted。PR #1 R2云端249项、PR #3正式接图push云端217项通过，均待独立验收/解决state冲突/合入；SW-014已发布但实测有误判，Trae43份草稿仍未共享。细节与原始证据见 [最新核查](evidence/P-20261014-02/README.md)。M1/M2仍有真机与真人Pending，不按代码阶段数推算完成百分比。

| 顺序 | 任务 | 角色与边界 | 前置 | 退出条件 |
| --- | --- | --- | --- | --- |
| 当前收口 | SW-001 T06补强R2已交 | ZCode同步/纠正；Antigravity回归 | 现有PR #1 | 实际调用链/低步数回归、完整head/新CI审核与集成 |
| 已获批准 | SW-002 森林光效候选 | MiniMax；Antigravity验图 | 已accepted | 保留原候选/hash；不重复生成，不等于入包 |
| 已完成启动 | SW-003 独立基线与协作集成 | Antigravity | 已accepted | 保留历史，转常驻验收queue |
| 当前并行 | SW-011 森林设计包收口 | Trae Design；Antigravity审稿 | 本机草稿 | 提交可编辑源、局部/阶段/比例预览、提示词和handoff |
| 当前并行 | SW-014 预检R2修订 | MiniMax；Antigravity审脚本 | SW-002/003 | 修PF-01～04、真实解码/批准hash/路径与隔离fixture，0 API |
| 持续职责 | 常驻验收队列（SW-013协调已完成） | Antigravity | 已发布交付 | 消费精确head、独立review、顺序集成/激活与组合测试包 |
| 当前收口 | SW-010 正式接图PR #3已交 | ZCode同步/补证据；Antigravity复验 | SW-002/003 | 批准hash→配置→六阶段/裁切/冻结/终景意图，组合CI |
| 第二批 | SW-004 快照恢复（T07A） | ZCode | SW-001/003 | 被动中断 30min 恢复；主动结束不恢复；S7/S9 |
| 设计第二批 | SW-012 雨林图片设计包 | Trae Design；Antigravity 审稿 | SW-011 | 雨林设计明确分层/透明/比例/色板与逐层素材提示词 |
| 第二批 | SW-006 雨林候选（T07C 美术） | MiniMax | SW-002/003/012/014 | 引用批准设计的候选与manifest；原8次预算 |
| 第三批 | SW-005 自动越坎（T07B） | ZCode | SW-004 | 站稳/跳跃不刷距，reduceMotion 可用 |
| 第三批 | SW-007 雨林双模式接入 | ZCode；Antigravity 审核 | SW-005/006 | 900m 雨林配置、声景、素材与双模式 |
| 第四批 | SW-008 城市/沙漠与一致性（T08） | ZCode 接线；MiniMax 分景候选 | SW-007/010 | 四主场景同规则，各景素材可追溯 |
| 持续+最终 | SW-009 实体验证与发布候选（T09） | Antigravity 组织；用户提供真实设备/参与者 | SW-008 | 真机矩阵、5–8 人真实内测、严重问题关闭 |

SW-003/SW-013协调已经accepted，Antigravity继续消费 [常驻验收队列](queues/antigravity.md)。ZCode收口已交的SW-001 R2与SW-010，两项分别验收，SW-004仍等待可靠性批准；MiniMax先修预检，不启动付费雨林；Trae先发布已有稿，再做获准后的雨林设计。真机已有时可提前验证森林，最终SW-009汇总证据，不把真机验证拖到最后。旧Release build-41不含新补强；测试包需记录实际SHA。

任务文件已经保存完整下一步要求。后续只需要协调者把满足前置的任务激活为 ready，四个角色继续读取自己的入口即可。森林既有修图SW-002继续原范围；新场景按“Trae设计→Antigravity批准→MiniMax制作→Antigravity验图→ZCode入包→Antigravity应用复验”推进。若 SW-008 范围过大，激活前拆子任务并为城市/沙漠分别登记Trae设计、MiniMax候选与ZCode接入的前置链，保留旧 ID 的 superseded 决策，不能一次性混合多景修改。
