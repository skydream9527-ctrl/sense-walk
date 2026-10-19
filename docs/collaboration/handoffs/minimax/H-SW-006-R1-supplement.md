# H-SW-006-R1-supplement · 雨林 R1 修复状态追加 + 协作 CI fixture 转交

- 任务/角色/接收者：SW-006 / minimax / antigravity
- 业务 head：仍为 `6ba654c5ba761ab25d94d121e985c5298d2d3d8a`（无新业务改动）
- 元数据 commit chain：`b1a775a` → `eac92e4` → `624dab8` → `d71d627`
- PR：https://github.com/skydream9527-ctrl/sense-walk/pull/25
- 依据：[R-SW-006-R1.md](../../reviews/R-SW-006-R1.md) + [H-SW-006-R1.json](./H-SW-006-R1.json) + minimax.md（origin/main 当前阶段收口版）

---

## 摘要

针对 Antigravity 在 R-SW-006-R1 提出的 3 项 finding（F-01/F-02/F-03），本 supplement 追加观察：

- **F-01**（manifest 路径缺失仓库根前缀）— **已修**，d71d627 后所有 `file` / `checks` 路径为完整仓库根相对路径
- **F-02**（handoff evidence 通配符）— **已修**，所有 evidence 为具体文件，无通配符/无目录
- **F-03**（0 API 占位）— **按 minimax.md 当前阶段收口规定保持 0 API**，下一阶段 R2 真实生图继续沿既有总 8 次尝试授权

旧 R-SW-006-R1 review 引用的 tip `eac92e4`（**已过时**），请按 **d71d627** 重新独立审核。

---

## 修复证据

### F-01 manifest file/checks 路径（d71d627）

manifest.json 中每层 `file` 与 `checks` 已改为完整仓库根相对：

```json
"file": "design/assets/rainforest/candidates/SW-006/r1/webp/rainforest_mist.webp"
"checks": [
  "design/assets/rainforest/candidates/SW-006/r1/checks/alpha_mask/rainforest_mist.png",
  "design/assets/rainforest/candidates/SW-006/r1/checks/black/rainforest_mist.jpg",
  ...
]
```

### F-02 handoff evidence 展开（d71d627）

handoff.json 的 9 个 check 全部 evidence 为具体文件，无通配符/无目录路径。验证：grep evidence `*` 与 `/` 结尾 = 0 命中。

### 协议校验结果（d71d627, base 30780af）

`python3 tools/collaboration.py check --base-ref 30780af2d4dbe7daa9323ae27ff76fb973d596a6` → **`Coordination check: OK (structure/dependencies/hashes; not runtime QA)`**

### SW-015 预检（默认严格入口）

`python3 design/assets/rainforest/preflight/SW-015/r1/scripts/preflight.py design/assets/rainforest/candidates/SW-006/r1/manifest.json` → **80/80 passed (0 failed)**

### SW-015 dry_run（严格批准链）

`python3 design/assets/rainforest/preflight/SW-015/r1/scripts/dry_run.py --design-ref-json design/assets/rainforest/candidates/SW-006/r1/manifest.json` → **11/11 passed**

---

## F-03 处理

按 minimax.md 入口（本轮阶段收口版）：

> "当前阶段不新增付费调用；下一阶段正式雨林制作继续沿既有总 8 次尝试授权（失败/超时/重试均计入、项目历史 14 分开、不重置），不用再向用户索要已给的授权。"

R1 保持 0 API（PIL 程序化占位），R2 真实生图待下一阶段 minimax.md 释放阶段收口后启动。**不**当前阶段调用 mcode-tools 付费 API。

---

## 协作 CI fixture 红灯转交

`tools/qa/test_collaboration.py` 跑 1 failure/1 error，根因（按 minimax.md 入口描述）：隔离 fixture 替换 SW012（伪造 reference）与真实 SW006 引用 SW012 关系冲突，且缺 design_manifest 应正常拒绝。

按 minimax.md 入口明确：

> "通过新增 handoff 告知 Antigravity 处理，自己不改 QA、不禁严格设计 hash 检查。"

**minimax 不动**：
- `tools/qa/test_collaboration.py`（QA 工具，不属 minimax 范围）
- 不 skip 失败 fixture
- 不禁严格设计 hash 检查
- 不代改作者候选

转交 Antigravity 处理。

---

## minimax.md 流程合规自检

- ✅ 未修改 `app/`、ForestShell.kt、forest.json、registry.json、BOARD.md
- ✅ 未重画已批准森林
- ✅ 未把雨林占位放进当前森林阶段包（按 minimax.md "不往当前森林阶段包放雨林占位"）
- ✅ 候选目录走 `design/assets/rainforest/candidates/SW-006/r1/` 独立路径
- ✅ 复用 SW-014 R3 + SW-015 R1 已合并 main 工具
- ✅ API 累计 baseline 14 + 0 增量
- ✅ 凭据仅 host-managed，未进 Git
- ✅ 保留 R1 与已有脚本/图（不删除）
- ✅ 协作 CI fixture 失败未自处理，**通过本 supplement handoff 转交 Antigravity**

---

## 给接收者的下一步

- 读本 supplement + 原 H-SW-006-R1.json/.md，**按 d71d627 最新 tip** 重新独立审核
- 实际跑 d71d627 上：
  - `python3 design/assets/rainforest/preflight/SW-015/r1/scripts/preflight.py <manifest>` 验证 80/80 通过
  - `python3 design/assets/rainforest/preflight/SW-015/r1/scripts/dry_run.py --design-ref-json <manifest>` 验证 11/11 通过
  - `python3 tools/collaboration.py check --base-ref 30780af...` 验证 OK
- 通过 → 改 registry SW-006 = accepted；R2 真实生图待下一阶段 minimax.md 释放阶段收口
- 退回 → 写新 changes_requested + R2 不覆盖 R1（草案与脚本/图保留）
- 协作 CI 红灯 `tools/qa/test_collaboration.py` 修复由 Antigravity 处理，minimax 不改

---

## 累计 API 预算

- SW-006 R1 = **0 API**（PIL 程序化占位）
- project lifetime baseline = 14（SW-002 R1 历史）
- SW-006 单任务 8 次预算待 R2 启动（按 minimax.md 阶段收口规定：当前阶段不调用）