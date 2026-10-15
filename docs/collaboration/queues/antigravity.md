# Antigravity 常驻验收队列

本轮依据：[P-20261014-03](../evidence/P-20261014-03/README.md)。先fetch最新main/角色分支，再读取最新实际handoff；下面是观察快照而非批准，head变化须比较全diff并复验。旧正式R1记录保留，不据此忽略新R2。

| 优先级 | 当前交付入口 | 退出条件 |
| --- | --- | --- |
| 1 / SW-001 R2 | [PR #1](https://github.com/skydream9527-ctrl/sense-walk/pull/1)，分支`codex/zcode/SW-001-t06-reliability`，当前head `d11873f3d5553fda872dd18f4483ca1e1b11223a`；业务head `7b17424886ba4b0c7608bd451f0ee244f3b88390`；分支内`docs/collaboration/handoffs/zcode/H-SW-001-R2.json`及新增correction | 独立复验实际Kotlin低步数同刻合并、实际注册→cue/无双cue、暂停/下降/重启/服务边界、完整head。写R-SW-001-R2；通过则集成/记merge与CI，激活SW-004；未过则具体退回 |
| 2 / SW-010 R1+附录 | [PR #3](https://github.com/skydream9527-ctrl/sense-walk/pull/3)，分支`codex/zcode/SW-010-forest-lightshows`，当前head `393f22570a541118d80e7a50c6860c3b57f2fd49`；业务head `a1df0e295b7c95d6212b8c65d597087a9458d906`；H-SW-010-R1.json及appendix-sizes/correction | 批准hash→正式图→配置→实际app六阶段/屏比/停走，终景意图有明确裁定。写独立review后集成，必要修图退回所属角色 |
| 3 / SW-014 R2→R3 | `codex/minimax/SW-014-r2`，当前head `bda0b74d53791c09a4c9b7a2858b9c32321bc862`；业务head `6e683e2087574df51efd43d8dea73270d321f5aa`；H-SW-014-R2.json，尚无PR | 独立核对R2-01～05及无效oversize样本，记录正式发现。R3到达时审最新head：默认入口/测试隔离、alpha/三底图、精确批准链/spec读取、真实预算/累计账本；不可仅凭13旧样本或Android CI批准 |
| 随到随审 / SW-011 | 43文件本机草稿，仍无共享head/handoff | 收到Trae真实PR后审源/spec/全部manifest hash/逐层prompt/局部与裁切预览；批准集成后激活SW-012，不代作者复制草稿作交付 |

两个ZCode PR的旧冲突/描述/纠正已处理，当前均MERGEABLE/CLEAN，最新PR合并checkout分别249/217项通过；不要继续要求重复修旧冲突或声称PR #3只有push CI。新计划合入后正常同步main，发现新冲突再让作者处理自己的state，保留双任务索引，不代写private state。旧bug Python模型不能替代对修复后Kotlin/真实调用链的回归。

新增屏比/冻结/意图证据已在PR #3。本轮Codex读取作者图，确认两个尺寸状态栏以下停走对照零像素差；这是作者证据检查，不是重新运行app。独立app复验与终景意图由本角色完成；必要时请Trae在设计范围补判断，不按单一平均差异阈值拒绝，也不改既定opacity。需改候选则MiniMax新hash→独立验图→ZCode新接线head。

SW-001可靠性复审可以先完成，不等待雨林工具/Trae稿或真机最终验收。代码验收范围通过时记录physical-device/human Pending并按授权集成；不能冒称M1/M2/MVP完成。两个工作PR集成后对组合main再跑必要CI，触发现有publish_release交新测试包，记录commit/APK SHA256/源码下载；当前build-41不含这些PR。

SW-003/SW-013 coordination accepted不结束本队列，也不需要另建启动任务。审稿/登记/集成为持续职责；没有新交付时一次报告待哪个文件，不无限轮询。只有依赖accepted才激活SW-004/SW-012/SW-006。真实SW-012未批准时，预检工具可用临时fixture验证，不能让manifest测试标记放行正式制作。

维护registry正式指针时消费真实作者文件和最小证据，先独立review、再集成/CI、最后accepted及render BOARD。observed_delivery仅远端定位；主线、工作PR与规划PR顺序同步，不改旧审计记录、不覆写别人工作。本轮不自动向外部工具发消息。
