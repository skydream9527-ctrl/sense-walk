# 文件交接协议 v1

## 角色与单写范围

| 文件/动作 | 负责者 | 其他角色的方式 |
| --- | --- | --- |
| `app/src/main/**`、`app/src/test/**`、Gradle、生产 Manifest、正式 assets、业务 CI | ZCode | 提交需求/发现，ZCode 接线 |
| `design/05-visual-design/**`、design-spec/manifest、素材级提示词与设计源 | Trae Design | MiniMax只读批准设计；不得自动入包 |
| `design/assets/**/candidates/**`、美术脚本、候选 manifest/检查图 | MiniMax | 只读验收；候选不得自动入包 |
| `app/src/androidTest/**`、`tools/qa/**`、独立证据/审核 | Antigravity | ZCode 可提出测试需求；测试依赖改动由 ZCode 处理 |
| `registry.json`、BOARD、任务启用、集成/发布清单、当前状态摘要 | Antigravity | 作者在自己的 handoff 提出更新请求 |
| 各角色 `state/<role>.json`、`handoffs/<role>/**` | 对应角色 | 其他角色只读 |
| `ASSETS.md` 正式素材状态 | ZCode（入包变更）、Antigravity（审核纠正） | 两者通过顺序 PR 更新；MiniMax 在候选报告提出映射 |
| 产品规则、任务描述、共享契约 | Antigravity 管协调；执行者提交具体修改建议 | 新 revision + 决策记录；不暗改既定米数/门禁 |

所有权是协作约定，校验工具不能替代文件权限或证明真实测试。当前登记全由 Antigravity 在集成分支顺序维护，其他人不同时改中心文件。

## 并行与 Git 隔离

每个 agent 使用独立克隆或 worktree，分支为 `codex/<role>/<task-id>-<slug>`。从最近已验收 main 开始。不得共享同一 checkout 的 Git index；已有 checkout 正在被另一角色修改时，只读后转到自己的 checkout。工作目录隔离只隔离文件，不能替代任务范围与依赖检查。

不要自动安装完整 Android SDK/JDK/模拟器；云端 Actions 是打包入口。已有可用本地工具可用于验证，但不作为其他 agent 的前置。

PR 提交前同步 main；有冲突在自己的分支解决，保留双方工作。禁止强推 main、清理其他 agent 的目录、全量 add 不相关文件。候选未审核前不能从旁路直接复制进正式 assets。

## 一次完整 handoff

1. 读取角色入口 → registry → 可执行任务文件 → 契约 → 最新相关 handoff/review。
2. 仅领取归属本角色、状态 ready/rework/in_progress 且前置均 accepted 的任务。更新自己的 state；state 只是进度通知，不能自授权跨角色任务。
3. 修改自己的范围，按任务执行验证。没有条件的设备项写 pending，失败写 failed，不能用空测试、截图文件存在或日志 stub 代替完成证据。
4. 写 `handoffs/<role>/H-<task>-R<revision>.json` 与同名 `.md`。填写真实 base/head SHA、变更文件、检查、证据、候选哈希、剩余项和接收者；运行 `python3 tools/collaboration.py check`。
5. 提交/推送交付 PR，自己的 state 改为 handoff_ready。可以填写零次 API、无新增源码等事实，但不能编造另一个 agent 已收到或确认。
6. Antigravity 审查对应 head，写独立 `reviews/R-<task>-R<revision>.json/.md`。只覆盖在 SHA/哈希上确实验证过的内容。
7. 不满足条件 → changes_requested，登记 rework，生产者写 R2；不得覆盖 R1。通过 → approved，按分支保护集成，合入后的 SHA/Actions 记录到 registry，登记 accepted。
8. 新改动使审核失效：任何 head 或候选哈希变化都需复验。交付作者不能把 own task 改 accepted；同一 agent 写的代码不能当作独立审核。

SHA 记录方式：先提交业务代码/候选得到 `head_commit`，再提交引用这个 SHA 的交接文档，避免“文件记录自身提交 SHA”的循环。审核绑定业务/候选 head；之后仅增加本角色交付/state记录的提交不改变该业务 head。协调者必须比较业务 head 与实际 PR head 的差异；如果业务、配置、契约或候选发生变化，就产生新的业务 head 与新 revision，不能借“文档提交”保留旧批准。

GitHub 账号可能相同；这里保证的是执行角色独立，不能宣称 GitHub 账户身份也独立。

## 状态与证据

`queued → ready → in_progress → handoff_ready → in_review → accepted`；退回为 rework；缺不可替代输入才 blocked。queued 的未来任务不能跳前置开工。生产者 state 是辅助进度，registry 是经过协调更新的任务状态；BOARD 是 registry 的生成视图，允许尚未同步时明确显示生产者已报交付。

coordination 启动/验收组织任务可由协调者依据实际产出登记完成；这不是批准自己的产品代码或素材，代码/素材仍必须独立 review。

Antigravity 的独立审稿/登记/集成是持续职责；coordination任务accepted后仍读取 `queues/antigravity.md`，不要求每轮新增启动ID。队列只定位待验交付，不授权作者跨任务开工，也不代替review。

registry可保存 `observed_delivery`（branch、branch_head、business_head、handoff_path、pr_url、source_report）定位已发布但尚未导入main的交付；该字段为bootstrap/协调核查观察，不是正式latest_handoff，也不满足accepted条件。latest_handoff/latest_review仍须是本仓库实际文件。已有R1 changes_requested不能否定后来R2的存在，也不能自动将R2批准；中心状态handoff_ready注明正在等哪个revision复审。用户要求的bootstrap计划维护可依据实测问题安排rework，但必须标明来源，由Antigravity另写正式review。

accepted 的语义取决于任务：素材任务=候选获验收；入包任务=应用接线获验收；开发任务=指定源码/CI 范围通过。真机 Pending 仍写在 registry 和报告中，不能自动将 M1/M2/MVP 判为完成。

design任务accepted仅表示设计包获独立审核，不是素材入包。Trae交design_manifest与源/预览/spec/提示词哈希；批准后MiniMax新场景素材需引用具体design_ref。设计文件变化使原引用失效。森林SW-002机械修复沿原设计继续；SW-006雨林必须先有SW-012批准设计。规范见 [visual-design](contracts/visual-design.md)。

新设计revision被批准后，协调者将受影响素材任务登记rework、同步接入依赖；历史记录保持原head/哈希及当时独立批准，不覆盖。归档或明确退回的旧交付可以查看；最新新交付及仍accepted的当前交付必须匹配当前批准设计。归档语义不能成为继续入包旧稿的授权。

检查类型至少区分 source / unit / cloud-build / emulator / physical-device / human / visual。同一轮截图检查不等于自动化 UI 测试；debug 注入不等于真实传感器。仪器测试未运行必须直说。

## 证据永久性

Actions Artifacts 有保留期；每个交付在 repo 保留最小证据：测试摘要与必要原始 XML、截图/合成预览、设备/版本/步骤、真实文件哈希、API 调用账本与审核结论。截图可以压缩，不存个人数据或密钥。大型 APK 放测试 Release 并记录 SHA256；本机 `.local-verify` 只能补充，不能作为唯一共享证据。

引用精确 SHA 与相对 repo 路径，不把 main 的可变内容当历史证据。历史原稿/失败稿可保留但标 rejected，候选状态不得继承旧批准。

## 依赖等待与变更

没有收到 handoff 时做独立核查/可并行工作，不能虚构文件或通过状态。不得反复无限轮询；当前运行完成后报告需等待的文件。此次方案没有自动调度、自动消息或自动唤醒。

合理实现细节自主完成。产品米数、门禁、隐私/服务范围改变先形成具体决策；不能仅因工具方便更改产品。新付费 API 请求必须在任务预算内；按总尝试数记账，超时/失败也计入，不能通过重命名轮次重置账本。无新预算的素材收尾使用已有图/程序素材。

Antigravity 在工作 PR 绿跑且审核完成后按现有授权集成；遇保护规则走受支持的 PR 流程，不绕过保护。正式商店发布与签名密钥不在授权范围。

工具可用 `python3 tools/collaboration.py check --base-ref <精确旧SHA>` 拒绝改写已入库 handoff/review/evidence/decision；修正错误采用新增 revision/correction 文件。中心登记和生成看板允许协调者更新。`.github/workflows/collaboration.yml` 在相关 push/PR 运行结构、哈希、依赖和历史检查，不等于运行实际业务验收。

看板任务行只从 registry 生成；生产者状态列链接到各自实时 JSON，不把这些自报值固化为验收状态。这样生产者更新自己的 state 不必抢写中心看板。

协调者已accepted/blocked但生产者尚未消费结果时，private state允许短暂滞后；以registry为准，不要求协调者越权替对方清state。执行者下一轮读取登记后将已结束任务清空/领取下一ready任务。

同一角色存在多个待验PR时，只有本人可在private state追加 `deliveries` 对象（task ID→分支/业务head/交付head/handoff路径/PR）以保留定位；它不改变中心状态，现有校验器不验证扩展字段。current_task仍指本人当前动作。本人顺序同步各分支、人工合并state冲突并保留两项信息，不能全选一方抹掉另一个交付，不把未审业务合进别的任务以规避冲突。bootstrap不替作者写该文件。详见 [D-005](decisions/D-005-persistent-review-queue.md)。
