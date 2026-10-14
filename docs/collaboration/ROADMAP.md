# 后续协同路线

2026-10-14核查：main为da9bd24，仍是T06应用基线；SW-002候选与SW-003初审已合入。ZCode PR #1云端238项通过但未合入；Trae有43文件本机草稿，未共享提交。细节、源码反例与原始证据见 [最新核查](evidence/P-20261014-01/README.md)。M1/M2仍有真机与真人Pending，不按代码阶段数推算完成百分比。

| 顺序 | 任务 | 角色与边界 | 前置 | 退出条件 |
| --- | --- | --- | --- | --- |
| 当前收口 | SW-001 T06补强R2 | ZCode；Antigravity回归 | 现有PR #1 | detector失败cue回退、低步数同刻合并、完整head审核 |
| 已获批准 | SW-002 森林光效候选 | MiniMax；Antigravity验图 | 已accepted | 保留原候选/hash；不重复生成，不等于入包 |
| 已完成启动 | SW-003 独立基线与协作集成 | Antigravity | 已accepted | 保留历史，转SW-013持续审核 |
| 当前并行 | SW-011 森林设计包收口 | Trae Design；Antigravity审稿 | 本机草稿 | 提交可编辑源、局部/阶段/比例预览、提示词和handoff |
| 当前并行 | SW-014 素材预检准备 | MiniMax；Antigravity审脚本 | SW-002/003 | 零API真实预检/fixture，未来design_ref输入和账本 |
| 当前并行 | SW-013 第二轮复验/集成 | Antigravity | SW-003 | 消费具体新交付、独立review、顺序集成/激活 |
| ZCode下一项 | SW-010 森林光效正式接入 | ZCode；Antigravity复验 | SW-002/003 | 候选逐字节→生产配置→真实Android渲染 |
| 第二批 | SW-004 快照恢复（T07A） | ZCode | SW-001/003 | 被动中断 30min 恢复；主动结束不恢复；S7/S9 |
| 设计第二批 | SW-012 雨林图片设计包 | Trae Design；Antigravity 审稿 | SW-011 | 雨林设计明确分层/透明/比例/色板与逐层素材提示词 |
| 第二批 | SW-006 雨林候选（T07C 美术） | MiniMax | SW-002/003/012/014 | 引用批准设计的候选与manifest；原8次预算 |
| 第三批 | SW-005 自动越坎（T07B） | ZCode | SW-004 | 站稳/跳跃不刷距，reduceMotion 可用 |
| 第三批 | SW-007 雨林双模式接入 | ZCode；Antigravity 审核 | SW-005/006 | 900m 雨林配置、声景、素材与双模式 |
| 第四批 | SW-008 城市/沙漠与一致性（T08） | ZCode 接线；MiniMax 分景候选 | SW-007/010 | 四主场景同规则，各景素材可追溯 |
| 持续+最终 | SW-009 实体验证与发布候选（T09） | Antigravity 组织；用户提供真实设备/参与者 | SW-008 | 真机矩阵、5–8 人真实内测、严重问题关闭 |

SW-003已启动，SW-013作为当前QA队列入口。ZCode优先修订SW-001，再推进SW-010；两项分别验收，SW-004仍等待可靠性批准。真机已有时可提前验证森林，最终SW-009汇总证据，不把真机验证拖到最后。旧Release build-41不含新补强；测试包需记录实际SHA。

任务文件已经保存完整下一步要求。后续只需要协调者把满足前置的任务激活为 ready，四个角色继续读取自己的入口即可。森林既有修图SW-002继续原范围；新场景按“Trae设计→Antigravity批准→MiniMax制作→Antigravity验图→ZCode入包→Antigravity应用复验”推进。若 SW-008 范围过大，激活前拆子任务并为城市/沙漠分别登记Trae设计、MiniMax候选与ZCode接入的前置链，保留旧 ID 的 superseded 决策，不能一次性混合多景修改。
