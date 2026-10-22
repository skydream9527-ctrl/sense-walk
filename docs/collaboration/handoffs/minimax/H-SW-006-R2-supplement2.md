# H-SW-006-R2-supplement2 · 候选字节刷新（硬边羽化）→ 审核改绑新业务 head

- 任务/角色/接收者：SW-006 / minimax / antigravity
- **新业务 head（羽化后候选字节）**：`33dd824566e65cc68cbfeeeed42f416e1092793c`
- **旧业务 head（羽化前字节，H-SW-006-R2.json 所引）**：`511adf5bc7cd0a80be23b431fbe6a4c3b72efa52`
- 交付 PR：https://github.com/skydream9527-ctrl/sense-walk/pull/35
- 主交接：[H-SW-006-R2.json](./H-SW-006-R2.json) / [H-SW-006-R2.md](./H-SW-006-R2.md)
- 前一 supplement：[H-SW-006-R2-supplement.json](./H-SW-006-R2-supplement.json)（CI 两处失败成因定位）
- 依据：[PROTOCOL.md](../../PROTOCOL.md) 第 37 行（审核绑定业务 head；候选哈希变化即需复验）、第 69 行（已入库记录只增不改）；[visual-assets.md](../../contracts/visual-assets.md)

> 本 supplement **不改写** 已推送的 `H-SW-006-R2.json/.md` 与 `H-SW-006-R2-supplement.json/.md`。
> 素材形态、账本、门禁逻辑均未变；变的是**候选像素字节**（一次确定性零 API 修正）。

---

## 1. 为什么刷新字节

自审时逐层对照 SW-012 批准 export 的边缘口径，发现 `glade` 存在真实缺陷：

| 口径（逐行最大水平 alpha 梯度） | 批准 design export | 刷新前我的候选 | 刷新后 |
| --- | --- | --- | --- |
| `glade` max\|dA/dx\| | 0.024 | **0.431** | 0.031 |
| `glade` 硬边行占比 | 0.0% | **5.5%** | 0.0% |

生图把湿径画成了**硬边锥形**，与两项已批准要求冲突：

- SW-012 批准 `design-spec.json` 的 `glade` 层：`湿径上下缘都用纵向 mask 淡出，屏底 alpha=0`、`无同心环、无重复纹理`；
- [visual-assets.md](../../contracts/visual-assets.md)：`无…硬边抠图`，且 `实际纯色底合成` 目检要求无矩形/硬边。

刷新前该层在白底三底图上呈明显硬边三角形（见下方"证据"）。

## 2. 修正方式（确定性、零 API）

`postprocess_r2.py` 新增 `soften_hard_edges()`：

- 以**批准 export 的 `max|dA/dx|`** 为上限口径（不写死数值，按层取参考）；
- 二分出**最小** sigma 做高斯羽化（保留形态，避免过度模糊）；
- 羽化后**重新标定 alpha 密度**，保证最大 alpha 与半透明占比不因羽化漂移；
- 只作用于确实超批准口径的层；结构层不动。

| 层 | 是否羽化 | sigma | 刷新前 max\|dA/dx\| | 刷新后 | 批准参考 |
| --- | --- | --- | --- | --- | --- |
| `mist` | 是 | 16 | 0.397 | 0.023 | 0.012 |
| `distant_glow` | 是 | 2 | 0.238 | 0.004 | 0.004 |
| `glade` | 是 | 8 | 0.365 | 0.028 | 0.024 |
| `trunks_canopy` | **否** | — | 0.524 | 0.600 | 0.937（硬边行 72.0%） |
| `vines_light` | **否** | — | 0.587 | 0.788 | 0.906（硬边行 52.3%） |

**结构层不羽化的理由**：树廓与叶缘的硬边就是形态本身，批准稿同样有 72.0% / 52.3% 的硬边行；羽化会把树干和叶片轮廓糊掉，反而偏离批准设计。

刷新后五层的 `has_hard_edge` 均为 `false`、`background_residual_fraction` 均为 `0.0000`；边缘像素实测 **whiteish 0.00% / magentaish 0.00%**（无白边、无洋红溢色）。

## 3. 哈希对照（审核请绑新值）

| 层 | 刷新前 sha256 | **刷新后 sha256（请用此值）** | 刷新前/后 bytes |
| --- | --- | --- | --- |
| `mist` | `ab2e0b8d836724ecd22f275972382175f48a4c1c86a5127c17f65428ad3071c7` | **`d78c1850cee39bbb2a10186b7787f03ebe5d487a46979ac9868cdbbbff33b9e7`** | 145032 → 75804 |
| `trunks_canopy` | `20940b39b150d2f320aae7faba76ee9dcff64414ec27c545c752b9c8a5edcacb` | **未变** | 245458 → 245458 |
| `vines_light` | `d1031bc1d97c1eabd94978275df9d7f63568abd39a5f449dffaf242ced0fd19a` | **未变** | 406320 → 406320 |
| `distant_glow` | `63e09c78f337b31ea9853634db4e190c73aaaac7284b879010fde9017674da74` | **`9dddeb743010826931ff4382ed2bad84906c8b146ee2e45d8f2712145e04cd35`** | 254702 → 193552 |
| `glade` | `428e75759f4b986d425bdf05eb0149fb5c0428ef0bb38ee246228a97a697dc13` | **`6c3330d4837128ea7fa9faef50be233514f70153fdf0ee15d5f12694e7279b75`** | 252440 → 99402 |

WebP 合计由 1303952 B 降至 **1020536 B**（< 2 MB），单层仍 ≤ 400 KB。

## 4. 预算与门禁（未变）

- **尝试账本不变**：SW-006 仍为 **8/8 用尽**（6 成功 / 2 被拒），`state` 仍 `sw006_attempts=8` / `cumulative_attempts=22`。本次刷新是**纯本地确定性处理，零新增 API 尝试**，未借任何预算。
- `production_guard.py --selftest` → **14/14**；
- r2 manifest 过自有门禁 → **122/122**；
- SW-015 R1 批准预检（默认严格） → **80/80**；
- `python3 tools/collaboration.py check` → **OK**。

## 5. 证据

- 逐层边缘与羽化诊断：`design/assets/rainforest/candidates/SW-006/r2/records/postprocess-report.json`（`edge_soften` 段）
- `glade` 三底实际合成：`design/assets/rainforest/candidates/SW-006/r2/checks/{black,white,magenta}/rainforest_glade.jpg`
- 刷新后 875m 终景：`design/assets/rainforest/candidates/SW-006/r2/checks/stages/stage_875m.png`
- 新 manifest（含新哈希与 `edge_soften` 记录）：`design/assets/rainforest/candidates/SW-006/r2/manifest.json`

## 6. 给接收者的下一步

1. **审核 SW-006 R2 时请绑定业务 head `33dd824566e65cc68cbfeeeed42f416e1092793c`**，并以上表"刷新后" sha256 作为 `artifact_hashes`；`H-SW-006-R2.json` 中的 `head_commit=511adf5…` 指向羽化前字节，已过时。
2. 重点复核 `glade` 湿径的淡出是否已符合"上下缘纵向 mask 淡出"；`mist` 因 σ=16 羽化较明显，请一并目检是否仍读作贴地湿雾。
3. `tools/qa/test_collaboration.py` 的 fixture 隔离缺陷仍待 antigravity 修复（见 [H-SW-006-R2-supplement](./H-SW-006-R2-supplement.md)），修复后重跑 PR #35 检查。
4. 审核通过后登记 `registry.json` SW-006 = accepted 并同步 `BOARD.md`；入包由 ZCode 按 SW-007 单独执行。
5. SW-006 8 次预算已用尽且本轮零新增；如需重做请另行授权，不要换 revision 重置账本。
6. SW-022 仍等待 SW-021 获批（PR #34 已交付、尚无独立审核，registry 仍 `ready`），本轮未领取。

---

## 本轮复验关系

- 业务 head 由 `511adf5` 变为 `33dd824`（同一分支的追加提交）；素材形态、账本、门禁脚本与批准设计引用均未变。
- 依据 [PROTOCOL.md](../../PROTOCOL.md) 第 37 行「任何 head 或候选哈希变化都需复验」：候选字节已变，故本 supplement 给出新 head 与新哈希供重新绑定，**不覆盖** R2 原记录。
- SW-022 依赖未满足，本轮未领取。
