# SW-017 R1 · 森林 800m 双模式应用验图参照

应用验图参照包（kind=integration_reference）。用途：把「当前 main 已入包的森林生产五层 + 当前 App 真实几何」放进虚走/实走双模式的应用上下文，给 ZCode（SW-018 安装测试与缺陷收尾）和 Antigravity/QA 一套可对拍的参照图、逐项验图清单与有依据的问题标注。

**不是**：新生产美术、新设计 spec、素材候选、Android 截图、真机证据。所有生成图带「设计模拟 · 非 App 截图」角标；`previews/real_captures/` 是作者既有证据的逐字节副本，不是本轮取证。

- 任务：`docs/collaboration/tasks/SW-017.md`（依赖 SW-011/SW-012/SW-005/SW-010 accepted）
- 基线：`422451e25ba3dfa9b44c9421d00188f81944e2bc`（origin/main，PR #27 合入后）
- 集成引用与全部输入 hash：[`integration-reference.json`](./integration-reference.json)
- 逐项验图清单：[`checklist.md`](./checklist.md)（[素材] 候选核对 vs [设备] 真机取证）
- 本轮范围：registry pending 指定「优先森林双模式阶段包」；雨林 900m 双模式参照保留后续轮次。

## 目录地图

| 路径 | 内容 | 消费方 |
| --- | --- | --- |
| `previews/matrix/forest_{virtual,real}_six_stages.png` | 两模式六阶段 0/100/265/425/630/785m 缩略矩阵（1080×2400 构图） | QA 对拍 |
| `previews/zones/{virtual,real}_zones_1080x1920.png` | 上 55%/下 45% 分区、控件、旅人 x=.34/y=.865、右缘 Void 带标注 | ZCode/QA |
| `previews/crops/` | 三比例（390×844 / 1080×1920 / 1080×2400）×两模式×关键阶段共 12 张 | QA 裁切走查 |
| `previews/states/` | 暂停、首局说明、站稳提示、放弃确认、大字号 ×1.5、reduceMotion 代表图（6 张，均无真机证据） | QA 补证对照 |
| `previews/parallax/parallax_clamp_pair_1080x2400.png` | offset=0 vs 钳制溢出端对拍 | ZCode 视差核对 |
| `previews/findings/evidence_findings_sheet.png` | F1–F7 作者截图走查标注板 | Antigravity 裁定 |
| `previews/findings/edge-audit.json` | F7 可复跑像素审计（all_pass=true） | Antigravity/ZCode |
| `previews/real_captures/capture_real_*.png` | H-SW-010-R1（10 张）+ H-SW-005-R2（2 张）作者证据副本 | 所有人 |
| `source/sw017_context_sim.py` | 参照图生成器（只读入包 webp 与源码语义，PIL+numpy 本地渲染） | 复现/审阅 |
| `source/sw017_edge_audit.py` | F7 右缘透明列/作者截图像素审计脚本 | 复跑取证 |
| `prompts.md` | 状态模拟级提示词补充（约束性文档；本轮零调用，不触发生图） | 后续轮次 |

## 给 ZCode（SW-018）的检查步骤

1. 先读 `checklist.md` B 节，每项在真实 App（模拟器或真机）取证后回填结果；参照图只回答「正确时长什么样」。
2. 运行时映射以 `integration-reference.json` 的 `proposed_runtime_notes_for_zcode`（P1–P3）为准：视差钳满米数（长屏 outline/trunks≈144m、leaf_path≈72m）、1080×1920 cover 宽不足导致视差失效与静态暗带、390×844 固定 px 几何须 @3x 物理渲染——均标 proposed，需设备数据证实或修正。
3. 复跑 F7 审计：`python3 design/05-visual-design/SW-017/r1/source/sw017_edge_audit.py`（只读，不改任何文件；输出 `previews/findings/edge-audit.json`）。设备新截图可按同一 ROI（y∈[.25h,.62h)，逐通道容差 2）扩展扫描。
4. 修复边界若涉及素材 webp 或 forest.json 参数：属于生产设计变更，不允许在 SW-018 直接改；走变更请求与新轮次（森林素材返工不改动 SW-012/D-009）。

## 给 Antigravity / QA 的走查步骤

1. 先看 `previews/findings/evidence_findings_sheet.png`：F1（265m 层缘硬分界）、F3（785m 文案叠印）、F4（冠线意图差异）是待裁定项；F2/F5/F6 是证据缺口；F7 是已量化的素材问题。
2. F7 判定材料：`edge-audit.json` 记录五层右/左全透明列（outline/trunks/leaf_path 各 30 列硬切、light_shows 右 133 列、clearing 右 4 列）、三档 cover 几何、作者 265m 截图右缘 52px 纯 Void（占比 1.0000，几何估计 52.3px）以及六阶段黑带演变（265/425m=52px → 630m=12px → 785m=0px）。是否返工、何时返工由审核方裁定，设计不自判修法。
3. 设备取证包每张图需附 head SHA、分辨率/density、米数、模式；F2 站稳提示需短视频或 ≤1s 连拍 + UI hierarchy。
4. 参照图与设备截图对拍时允许的差异：字体渲染（系统中文字体 vs Android）、状态栏/手势条精确外观（图中仅避让示意）、抗锯齿细节；不允许的差异：分区比例、锚点、相位有无、摇杆有无、黑带位置与宽度量级。

## 复现

```sh
# 生成全部 36 张参照图（确定性，固定种子/固定字体候选）
python3 design/05-visual-design/SW-017/r1/source/sw017_context_sim.py
# F7 像素审计
python3 design/05-visual-design/SW-017/r1/source/sw017_edge_audit.py
```

依赖：Python 3 + Pillow + numpy（本地已有）；零网络、零付费/生图 API。输入全部来自当前 main 入包素材与 `forest.json`，路径与 sha256 见 `integration-reference.json`。

## 边界

- 未修改 `app/`、候选目录、他人 state 与 registry；未运行 Android 构建，未冒称真机/真人计步。
- 未改动 SW-011/SW-012 已发布交付与 D-009 冻结参数；本包不是 SW-006 的 design_ref。
- 素材层若必须返工，另写变更请求走新轮次；本包只交参照、标准与证据标注。
