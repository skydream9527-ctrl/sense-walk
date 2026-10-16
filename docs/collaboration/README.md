# SenseWalk 多 agent 协作

状态以registry为准，产品规则以DEVELOPMENT为准，源码/提交/实际证据高于完成声明。无需额外调度服务或完整本地Android环境。四角色独立worktree；用户转发入口，不自动发消息。

## 当前进展 · 2026-10-16

main **2339333**：森林正式光效SW010、地形SW005 R2、雨林设计SW012及规格预检SW015均已独立验收合入；上轮规划也已由PR16发布，不再导入旧包。main云端构建/协作检查成功，作者已有28份XML共303项通过。雨林尚无正式候选与运行配置，测试Release仍旧build109。详见 [本轮核查](evidence/P-20261016-01/README.md)。

本轮规划如尚未入main，Antigravity先按 [本轮发布交接](PUBLISH-PLAN-20261016.md) 导入现成提交/交付包；其余角色可直接读用户提供的本机入口。发布后沿用下面相同入口。

## 四条稳定入口提示词

- ZCode：`请先 fetch 最新 origin/main，读取并执行 docs/collaboration/roles/zcode.md，保留现有工作。`
- MiniMax Code：`请先 fetch 最新 origin/main，读取并执行 docs/collaboration/roles/minimax.md，保留现有工作。`
- Trae Design：`请使用 Design 模式，先 fetch 最新 origin/main，读取并执行 docs/collaboration/roles/trae-design.md，保留已有设计稿。`
- Antigravity：`请先 fetch 最新 origin/main，读取并执行 docs/collaboration/roles/antigravity.md，保留现有工作。`

| 角色 | 本轮可执行任务 | 交付去向 |
| --- | --- | --- |
| ZCode | ready [SW016雨林运行时底座与真实声景准备](tasks/SW-016.md) | 900m接口/渲染/双模式复用/合法声音准备→QA；最终SW007另等候选 |
| MiniMax | ready [SW006雨林候选](tasks/SW-006.md) | 先本任务内0API生产尺寸/冻结批准/总预算guard，再按原总8次制作→独立验图 |
| Trae Design | ready [SW017应用验图参照](tasks/SW-017.md) | 两模式/阶段/尺寸/状态参考与验图清单→QA/ZCode；不重画生产五层 |
| Antigravity | [常驻验收队列](queues/antigravity.md) | 当前main组合测试Release、提示时序补证、随到审三路交付；通过后启用SW007 |

既有批准保留；旧预检的768尺寸/9次声明误放行与strict-design误拒见真实0API反例，不能让工具绿替代实际契约。SW017不改SW012生产设计/素材前置；缺真机/真人仍Pending。

## 文件导航

- [registry.json](registry.json) → [生成看板](BOARD.md)；[整体路线](ROADMAP.md)。
- [协议](PROTOCOL.md)；[验收队列](queues/antigravity.md)；[本轮核查](evidence/P-20261016-01/README.md)。
- [前轮核查](evidence/P-20261015-02/README.md)与其历史发布限制保留；后由PR16实际发布，不改旧事实。
- [快照契约](contracts/session-snapshot.md)、[设计契约](contracts/visual-design.md)、[素材契约](contracts/visual-assets.md)、[雨林冻结D009](decisions/D-009-freeze-rainforest-design-spec.md)。
- [交接模板](templates/HANDOFF.md)、[审核模板](templates/REVIEW.md)、[设计规格模板](templates/design-spec.json.example)。
- [校验工具](../../tools/collaboration.py)：render生成BOARD，check只检结构/哈希/依赖/历史，不证明运行QA。

## 文件系统与单写

roles为稳定入口；tasks为每项完整要求；registry为协调单写事实；BOARD自动生成；state/handoffs由生产者本人写；reviews/evidence/decisions保存精确head/hash/检查与限制，旧归档不覆盖；contracts为跨角色接口。Trae拥有设计源/规范/prompts，MiniMax拥有候选/美术工具，ZCode拥有app/生产素材，Antigravity拥有独立QA/中心登记/集成发布。设计→候选→入包→App验收分开。
