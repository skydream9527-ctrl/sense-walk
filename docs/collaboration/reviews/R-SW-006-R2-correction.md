# SW-006 R2 独立评审与返工指引报告

- **任务 ID**: `SW-006`（雨林候选素材批次 R2）
- **评审人**: Antigravity (QA)
- **提交人**: MiniMax Code
- **交付 PR**: [PR #35](https://github.com/skydream9527-ctrl/sense-walk/pull/35)
- **交付分支状态**: `codex/minimax/SW-006-r2`（分支 tip `9bcfbaba356269ed43b6944d44c7fc1c531788d4`，最新业务提交 `33dd824566e65cc68cbfeeeed42f416e1092793c`，原始 R2 handoff 记录的业务提交 `511adf5bc7cd0a80be23b431fbe6a4c3b72efa52`）
- **相关 Handoff**:
  - `docs/collaboration/handoffs/minimax/H-SW-006-R2.json` / `.md`
  - `docs/collaboration/handoffs/minimax/H-SW-006-R2-supplement.md`
  - `docs/collaboration/handoffs/minimax/H-SW-006-R2-supplement2.md`
- **本次评审结论**: **`changes_requested`**（`SW-006` 在 `registry.json` 保持 **`rework`**；不合并 PR #35；严禁新增付费生图 API 调用，请以 **0 API 本地确定性重编码与新修订号 `H-SW-006-R3`** 闭环以下阻断项）

---

## 1. 独立核验已确认通过项

在独立 worktree 对 `codex/minimax/SW-006-r2` (`9bcfbab` / `33dd824`) 执行验证：
1. **生产门禁脚本自检与候选检查**:
   - `python3 design/assets/rainforest/preflight/SW-014/r3/scripts/production_guard.py --selftest` → **14/14 passed**。
   - `python3 design/assets/rainforest/preflight/SW-014/r3/scripts/production_guard.py design/assets/rainforest/candidates/SW-006/r2/manifest.json` → **122/122 passed**。
2. **API 账本与真实生成溯源**:
   - `api_ledger.json` 完整记录 8 次 MiniMax `image-01` 真实调用（`api_calls_used: 8 / 8`），`source/sw006_r2_*.png` 原始生成图已封存留档。
3. **测试沙箱隔离转交项（已由 QA 修复闭环）**:
   - 针对 `H-SW-006-R2-supplement.md` 报告的 `tools/qa/test_collaboration.py` 在存在 `H-SW-006-R2+` 时 `asset_delivery(revision=1)` 最新修订号被推高至 R2 导致 2 项测试失败的问题，QA 已在 `tools/qa/test_collaboration.py` 的 `asset_delivery()` 中完成 `revision == 1` 沙箱清理隔离，31/31 项协议单测全绿。

---

## 2. 阻断通过的 3 项 Finding（需在 R3 零 API 闭环）

### Finding R2-01（协议门禁阻断）：`H-SW-006-R2.json` 元数据失步且缺失 `asset_manifest`

- **事实证据**:
  1. 在提交 `33dd824566e65cc68cbfeeeed42f416e1092793c` 中，MiniMax 重新运行了 `postprocess_r2.py`（`soften_hard_edges`），更新了 `rainforest_mist.webp`、`rainforest_distant_glow.webp`、`rainforest_glade.webp` 以及 `design/assets/rainforest/candidates/SW-006/r2/manifest.json`（最新哈希 `b3045bc4a82a45c3cf6c4a406ceeb5ca538e296db12e85ff2e6d1d0bc9f9cf74`）。
  2. 但 `docs/collaboration/handoffs/minimax/H-SW-006-R2.json` 仍停留在旧提交：
     - `"head_commit": "511adf5bc7cd0a80be23b431fbe6a4c3b72efa52"`（非最新业务提交 `33dd824...`）；
     - `"asset_manifest"` 字段缺失（ waardoor `tools/collaboration.py` 在将 `SW-006` 标为 `accepted` 时直接报错 `SW-006: asset task accepted without asset_manifest`）；
     - `"artifacts"` 数组中记录的仍是 `511adf5` 时的旧 SHA-256（例如 `manifest.json` 记录为 `d4fc3883...`、`rainforest_mist.webp` 记录为 `ab2e0b8d...`），一旦在 `registry.json` 将 `latest_handoff` 指向 `H-SW-006-R2.json`，`tools/collaboration.py` 立即触发 4 处 `artifact hash mismatch`！
- **修复要求**:
  - 遵守不可变审计历史规则，不要原地篡改已提交的旧版记录；请新增 **`docs/collaboration/handoffs/minimax/H-SW-006-R3.json`** 与 **`H-SW-006-R3.md`**（`"revision": 3`）。
  - 在 `H-SW-006-R3.json` 中显式设置 `"asset_manifest": "design/assets/rainforest/candidates/SW-006/r2/manifest.json"`（或 `r3/manifest.json`），确保 `"head_commit"` 为包含全部候选素材与 manifest 变更的最终业务 commit SHA，且 `"artifacts"` 列表中每个文件的 `sha256` 与磁盘实际文件 100% 一致。

### Finding R2-02（字节预算超限）：`rainforest_vines_light.webp` 超过 400KB 契约上限

- **事实证据**:
  - `design/assets/rainforest/candidates/SW-006/r2/webp/rainforest_vines_light.webp` 当前大小为 **`406,320` bytes**（`406.32 KB`）。
  - 根据 `docs/collaboration/tasks/SW-006.md` 与 `docs/collaboration/contracts/visual-assets.md`（单层 WebP `≤ 400KB`），`406,320` bytes 超出十进制 `400,000` bytes 上限（`preflight.py` 使用 `400 * 1024 = 409,600` KiB 才未报错）。
- **修复要求（0 API）**:
  - 在本地脚本中基于已封存的 `source/sw006_r2_vines_light.png` 调整 WebP 编码质量参数（例如 `quality=76..78, method=6`），使 `rainforest_vines_light.webp` 严格满足 `bytes <= 400000`（同时 `<= 409600`）。

### Finding R2-03（视觉质量问题）：`110m (mist)` 近乎全黑不可见、`875m (glade)` 呈对称灰斑

- **事实证据（独立目检 `checks/*_white_check.png` 与 `checks/stage_*.png`）**:
  1. `stage_110m.png`（对应 `rainforest_mist.webp` 按 `to_opacity=0.55` 合成）：由于 `33dd824` 对 `mist` 叠加了 `sigma=16` 羽化与高阈值抠图，合成到 `#050C08` 底色后在 `110m` 阶段几乎全黑，肉眼无法辨识任何林间薄雾层次。
  2. `stage_875m.png`（叠加 `rainforest_glade.webp`）：`rainforest_glade_white_check.png` 显示 `glade` 图层仅在画面中下部残留两团左右对称的灰绿暗斑，合成到 `875m` 终局画面时在气根上产生突兀的灰雾斑块，缺乏雨林幽谷豁然开朗的通透感。
- **修复要求（0 API，严禁新增生图调用）**:
  - **严禁调用任何付费生图 API**（`8/8` 预算已冻结）。
  - 仅在本地 `postprocess_r2.py` 中针对已封存的 `source/sw006_r2_mist.png` 与 `source/sw006_r2_glade.png` 优化 alpha 提取与柔和垂直渐变映射：
    - 让 `rainforest_mist.webp` 在 `110m`（`opacity=0.55`）下具备柔和可辨的近地薄雾体积感；
    - 让 `rainforest_glade.webp` 在 `875m`（`opacity=0.90`）下呈现自然连贯的林间空地微光，消除突兀的对称双灰斑。
  - 重新生成对应的 4 张单层检查图、6 张阶段合成图与 `manifest.json`，确认 `production_guard.py` 全绿后通过 `H-SW-006-R3.json/.md` 提交。
