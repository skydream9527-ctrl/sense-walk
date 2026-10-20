# H-SW-006-R2-supplement · CI 两处失败的成因定位与转交

- 任务/角色/接收者：SW-006 / minimax / antigravity
- 业务 head（不变）：`511adf5bc7cd0a80be23b431fbe6a4c3b72efa52`
- 交付 PR：https://github.com/skydream9527-ctrl/sense-walk/pull/35
- 主交接：[H-SW-006-R2.json](./H-SW-006-R2.json) / [H-SW-006-R2.md](./H-SW-006-R2.md)
- 依据：[PROTOCOL.md](../../PROTOCOL.md) 第 29–37、69 行；`tools/collaboration.py`；`tools/qa/test_collaboration.py`

> 本 supplement **不新增业务改动**，不改动已推送的 `H-SW-006-R2.json/.md`。
> 素材、门禁、manifest 与主交接内容均不变。

---

## 摘要

PR #35 的 `Collaboration handoff checks` 出现两处失败，成因完全不同，需分别处理：

| # | 失败 run | 报错 | 归属 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | `39441667048`（push 事件） | `history: existing record changed/deleted H-SW-006-R2.json/.md` | **minimax（我方流程）** | 我在首次推送后又原地修改了已推送的 handoff 文件，违反协议"已入库 handoff 的修正走新增 correction 文件" |
| 2 | `39441674753`（pull_request 事件） | `test_asset_cannot_substitute_other_approved_design` 与 `test_retired_asset_can_remain_visible_during_rework` 失败 | **antigravity（`tools/**` 写入范围）** | QA fixture 自身隔离缺陷：把真实 `docs/collaboration` 整树复制进沙箱，新增真实交付后与 fixture 自造交付冲突 |

**第 2 项不是本轮交付的缺陷，也与素材/门禁逻辑无关**；minimax 未代改 QA 源文件（`tools/**` 属 antigravity 写入范围），已给出本地实测通过的最小修法。

---

## 1. push 事件失败（我方流程问题）

### 现象

```
history: existing record changed/deleted docs/collaboration/handoffs/minimax/H-SW-006-R2.json; add a new revision/correction instead
history: existing record changed/deleted docs/collaboration/handoffs/minimax/H-SW-006-R2.md; add a new revision/correction instead
```

### 成因

`immutable_history_errors(base_ref)` 比较 `base_ref..HEAD`，凡 `docs/collaboration/{handoffs,reviews,evidence,decisions}/` 下**非 A（新增）**的变更即判失败。push 事件取 `TASK_CHECK_BASE = github.event.before`：

```
TASK_CHECK_BASE: b6d39f498c96b209d8184b57ec2dbe1a92d1c4c5   # 我首次推送的业务+交接提交
HEAD:             09307b7165a1047bbd1b531f5a39d788b256ce5f   # 我为补 pr_url 又提交的一次
```

我先推送 `b6d39f4`（含 `H-SW-006-R2.json/.md`），随后又提交 `09307b7` **原地修改**这两个文件以补 PR 链接。于是相对 `b6d39f4`，两个 protected 路径是 `M` 而非 `A`：

```
$ git diff --name-status b6d39f4 HEAD -- docs/collaboration/
M       docs/collaboration/handoffs/minimax/H-SW-006-R2.json
M       docs/collaboration/handoffs/minimax/H-SW-006-R2.md
```

对照 `pull_request` 事件（base = main）则是干净的 `A`：

```
$ git diff --name-status a2d727f HEAD -- docs/collaboration/
A       docs/collaboration/handoffs/minimax/H-SW-006-R2.json
A       docs/collaboration/handoffs/minimax/H-SW-006-R2.md
M       docs/collaboration/state/minimax.json
```

### 处置

按 [PROTOCOL.md](../../PROTOCOL.md) 第 69 条「已入库 handoff 的修正采用新增 revision/correction 文件」：

- 本次**不再原地修改** `H-SW-006-R2.json/.md`；PR 链接与后续说明统一写在本 supplement。
- 后续对本分支 handoff 只做新增，不做原地改写。

---

## 2. pull_request 事件失败（QA fixture 隔离缺陷，需 antigravity 修）

### 现象

```
FAIL: test_asset_cannot_substitute_other_approved_design
  AssertionError: False is not true : []
FAIL: test_retired_asset_can_remain_visible_during_rework
  AssertionError: Lists differ: [] != ['H-SW-006-R2.json: design_ref does not ma[89 chars]ion']
+ 'H-SW-006-R2.json: design_ref does not match required design task',
+ 'H-SW-006-R2.json: design_ref is not the accepted design revision'
Ran 31 tests in 44.327s
FAILED (failures=2)
```

注意报错里的文件名是 **`H-SW-006-R2.json`** —— 那是**我本轮的真实交付**，不是 fixture 自造的记录。

### 成因

`tools/qa/test_collaboration.py` 的 `setUp` 把**真实** `docs/collaboration` 整树复制进一次性沙箱：

```python
shutil.copytree(REPO / 'docs/collaboration', self.base)
```

而 fixture 自己也用 `SW-006` 作为素材任务的样例，且**自造的是 revision 1**：

```python
def handoff(self, task_id='SW-001', producer='zcode', revision=1):
    relative = f'docs/collaboration/handoffs/{producer}/H-{task_id}-R{revision}.json'
```

于是校验器计算「最新 revision」时：

```
latest_revision[SW-006] = max(1 (fixture 自造 R1), 2 (我的真实 R2)) = 2
```

我的真实 `H-SW-006-R2.json` 因此被当作**当前交付**参与 `design_ref` 校验；而该测试随后又把沙箱 registry 的 SW-006 依赖临时改成 `SW-011`：

```python
self.change_registry(lambda data: next(t for t in data['tasks'] if t['id'] == 'SW-006').update(
    status='rework', depends_on=['SW-011'], latest_handoff='.../H-SW-006-R1.json'))
```

我的 R2 声明 `design_ref.task_id = SW-012`，与临时的 `depends_on=['SW-011']` 不匹配 → 触发那两条 `design_ref` 报错。

**根因是 fixture 没有隔离真实交付记录**，而不是我的 `design_ref` 有问题：同一份 `H-SW-006-R2.json` 在真实仓库里 `python3 tools/collaboration.py check` 是 **OK** 的。

### 因果复现（本地四组对照，均在临时副本上做，未改工作区）

| 组 | 条件 | 结果 |
| --- | --- | --- |
| a | 真实工作区当前状态 | 2 failures |
| b | 副本中删除真实 `H-SW-006-R2.json` | 目标 2 个测试 **OK** |
| c | 副本 `setUp` 追加「复制后删除 fixture 将自造任务的真实交付记录」（约 4 行） | **31/31 OK** |
| d | 另一等价变体「复制后删除全部 `handoffs/`+`reviews/` 的 `*.json`」 | **31/31 OK** |
| e | 干净 `origin/main` worktree 跑 `tools/qa` 全量 | **31/31 OK**（main 本身是绿的） |

组 (e) 说明：该缺陷由**新增真实交付**触发，main 上因为还没有任何 SW-006 交付而不暴露。

### 建议修法（属 `tools/**`，请 antigravity 落地）

在 `tools/qa/test_collaboration.py` 的 `setUp` 里，复制真实目录后把 fixture 将要自造的**任务**的真实交付记录剔除即可（c、d 两种都已实测通过）：

```python
shutil.copytree(REPO / 'docs/collaboration', self.base)
# 沙箱只应继承 registry/契约, 不应继承真实交付记录:
# fixture 会自造 SW-001/SW-006/SW-012 的 handoff, 真实同名记录会让
# latest_revision 取到真实 revision, 造成 fixture 断言被真实交付污染.
for _d in ('handoffs', 'reviews'):
    for _p in list((self.base / _d).rglob('*.json')):
        _p.unlink()
```

（若担心 `test_existing_audit_history_cannot_be_rewritten` 等用例依赖真实记录，可用变体 (c) 只删 SW-006 相关记录；两种均实测 31/31 OK。）

minimax **未**提交该修改（`tools/**` 属 antigravity 写入范围，且任务文件明确「作者不要禁用严格检查或代改QA」）。

---

## 3. 本轮交付自身的门禁状态（与上述失败无因果关系）

以下四项在本分支本地复跑**全部通过**：

| 检查 | 结果 |
| --- | --- |
| `production_guard.py --selftest` | 14/14 passed，exit 0 |
| `production_guard.py <r2 manifest>` | 122/122 passed，exit 0 |
| SW-015 R1 批准预检（默认严格入口） | 80/80 passed，exit 0 |
| `python3 tools/collaboration.py check` | Coordination check: OK |

素材内容、五层候选、账本与主交接均不受本次两处 CI 失败影响；两处失败分别是**流程**问题与**fixture 隔离**问题。

---

## 给接收者的下一步

1. 修复 `tools/qa/test_collaboration.py` 的 fixture 隔离（§2 建议修法，本地已实测 31/31 OK），重跑 PR #35 的 Collaboration handoff checks 确认绿。
2. 独立审核 [H-SW-006-R2.json](./H-SW-006-R2.json) / [H-SW-006-R2.md](./H-SW-006-R2.md)，绑定业务 head `511adf5bc7cd0a80be23b431fbe6a4c3b72efa52` 与 manifest 内五层 sha256。
3. 审核通过后登记 `registry.json` SW-006 = accepted 并同步 `BOARD.md`；入包由 ZCode 按 SW-007 单独执行。
4. SW-006 8 次付费预算已用尽（`sw006_attempts=8` / `cumulative_attempts=22`）；如需新增尝试请另行授权，不要换 revision 重置账本。
5. SW-022 仍等待 SW-021 获批（registry SW-021 = `ready`，归 trae-design），本轮未领取。

---

## 本轮复验关系

- 主交接 `H-SW-006-R2`（业务 head `511adf5`）内容未变；本 supplement 只追加 CI 成因定位与转交。
- R1 评审 [R-SW-006-R1.md](../../reviews/R-SW-006-R1.md) 的 F-01/F-02/F-03 三项在 R2 均已对应修复（见主交接 §本轮复验关系）。
- 业务 head、素材哈希、账本与 registry 状态均未因本 supplement 改变。
