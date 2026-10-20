# R-SW-018-R1 独立证据范围修正（H2 站稳提示截图复核）

本文件为对已归档独立评审报告 [R-SW-018-R1.md](R-SW-018-R1.md) 及生产者交付报告 [H-SW-018-R1.md](../handoffs/zcode/H-SW-018-R1.md)、[verification-report.md](../evidence/H-SW-018-R1/verification-report.md) 的追加勘误与证据范围复核记录（依据 [SW-024](../tasks/SW-024.md) 与 [SOURCE-REVIEW](../plans/2026-10-20/SOURCE-REVIEW.md) 执行，不覆盖任何历史 handoff/review/evidence 原文，亦不撤销 `SW-018` 整体 `accepted` 状态）。

---

## 1. 作者原报告与初审声明 vs 独立实看与像素量化事实

| 维度 | 作者原报告（`H-SW-018-R1`）与初审报告（`R-SW-018-R1`）原表述 | SW-024 独立实看画面与像素级核查事实 | 复核结论 |
| --- | --- | --- | --- |
| **`H2-hint-appear.png` 中央提示卡片** | 声称「角色微蹲姿态可见，『慢一点，站稳再跳』卡片正常弹出显示」 | 直接目视 [H2-hint-appear.png](../evidence/H-SW-018-R1/screens/H2-hint-appear.png)（SHA256 `96faa8faa8261c8a210c404a0077327440723be01786be990920eee3bcf4f3d6`）：画面中央**未见**「慢一点，站稳再跳。」文字卡片。对中央卡片区域（`x ∈ [100, 980], y ∈ [950, 1450]`）做像素统计：对照含说明卡的 [02-virtual-session.png](../evidence/H-SW-018-R1/screens/02-virtual-session.png) 有 `14,056` 个高亮文字像素（`max RGB = [232, 228, 217]`），而 `H2-hint-appear.png` 与 [H2-hint-gone.png](../evidence/H-SW-018-R1/screens/H2-hint-gone.png) 均为 **`0` 个高亮像素**（`max RGB = [33, 46, 40]` / `[36, 49, 42]`，纯森林暗背景）。 | **原图未拍到提示卡片文字**；不能凭文件名或轮询日志宣布画面已闭环。 |
| **`H2-hint-appear.png` 与 `H2-hint-gone.png` 的旅人姿态** | 声称 `H2-hint-appear.png` 为站稳微蹲姿态（`Gait.TENSE`） | 对比 `ForestShell.drawTraveler` 源码（`groundY = 2400 × 0.865 = 2076`）：平地静止/行走（[02-virtual-session.png](../evidence/H-SW-018-R1/screens/02-virtual-session.png)、[03-walking.png](../evidence/H-SW-018-R1/screens/03-walking.png)）旅人色块 `#7A857C` 纵向范围为 `y = 1981..2076`；若处于 `Gait.TENSE`（`tenseDuck = +6px, hopLift = 0px`），纵向应为 `y = 1987..2076`。实测 `H2-hint-appear.png` 旅人纵向为 `y = 1957..2050`（脚底 `2050 = 2076 - 26`），`H2-hint-gone.png` 为 `y = 1955..2049`（脚底 `2049`），**两张图均处于离地抬升 26px 的跳跃态 `Gait.HOP`**。前图后仰 `-10°` 且带前伸手臂，是因为当时 `sPos ∈ [237, 240)` 仍处于 `140..240m` 的 `slope_up` 段（叠加了攀爬旋转与手臂，且 `240m` 的 `tree_trunks` 尚未解锁）；后图已进入 `240..270m` 的 `gap_hop` 段（`tilt = 0°`、无攀爬手臂、`tree_trunks` 微弱显现）。 | **两图实际均为 `Gait.HOP` 腾空帧**，初审将 `SLOPE_UP + HOP` 误判为 `Gait.TENSE` 微蹲。 |
| **800m 虚走通关截图（`F3-completed.png`）** | 声称真实摇杆完整局走完 800m 进入完成页 | 直接目视并核验 [F3-completed.png](../evidence/H-SW-018-R1/screens/F3-completed.png)（SHA256 `2a5550b3936e276ef96253d0af3a7a03b752e55674387128c85d7d1089dfb6eb`）：画面清晰可见「森林 / 走到了 / 走完 800 m / 用时 ▾ / 再走一次 / 回到首页」（中央高亮像素 `119,926`）。 | **800m 通关截图真实有效，原结论单独保留。** |

量化像素审计原始数据存档于：[h2-pixel-audit.json](../evidence/SW-024/h2-pixel-audit.json)。

---

## 2. 截屏未命中提示卡片的时序根因与源码核查

1. **源码链路核查（非代码逻辑损坏）**:
   - `forest.json` 中首坎为 `{ "from": 240, "to": 270, "kind": "gap_hop" }`；`TerrainMotor.APPROACH_METERS = 3f`，当 `sPos` 到达 `237.0m` 且摇杆处于紧张区（`deflection > 0.72`）时，第 1 帧进入 `Phase.APPROACH`，第 2 帧进入 `Phase.STABILIZE`（持续 `STABILIZE_DURATION_MS = 1_200L`）并置 `hintPending = true`、`hintShownThisSession = true`。
   - `SessionViewModel.onFrame()` 消费 `consumeStabilizeHint()` 将 `_stabilizeHint.value = true`；`SessionScreen.kt` 在 `stabilizeHint && sessionActive && !showIntro` 下渲染「慢一点，站稳再跳。」卡片，并通过 `LaunchedEffect(stabilizeHint) { delay(3000); vm.consumeStabilizeHintDone() }` 在 **3.0 秒**后关闭卡片。
2. **外部脚本抓拍滞后根因**:
   - 作者脚本通过循环执行 `adb shell uiautomator dump` 检测文字出现后再调 `adb exec-out screencap -p`。由于 `SessionScreen` 存在 60fps `withFrameNanos` 帧循环，Accessibility `uiautomator dump` 等待空闲超时需耗费约 `1.5–2.5s`：当 XML 在 `t ∈ [0, 3.0s]` 内捕获到文字并写回宿主机打印 `[20:56:21] H2-提示出现(#41)`（见 [emulator-checklist.txt](../evidence/H-SW-018-R1/emulator-checklist.txt)）后，紧随其后的 `screencap` 实际执行时刻已超过 `t = 3.0s`（此时 `1.2s` 站稳已结束并以 `1.0 m/s` 轻跳推进至 `sPos ≈ 238.8m < 240m`，`3.0s` 提示定时器也已触发 `consumeStabilizeHintDone()`）。
   - 因此，该问题是**截屏采样落后于 3 秒提示窗口导致的证据缺失**，不据此断言产品代码损坏，也不推翻 `SW-018` 整体 `accepted`。
3. **关联代码观察（供后续评估，不改变本轮门禁）**:
   - `forest.json` 中 `gap_hop` 段跨度为 `240..270m`（共 `30m`），导致 `Phase.HOP`（`hopLift = 26px` 双脚腾空）持续整段 `30m`（按 `1.0 m/s` 约 30 秒）；同时在接近区 `sPos ∈ [237, 240)` 内，`terrainAt(sPos)` 仍返回上一段 `SLOPE_UP`，使 `ForestShell.drawTraveler` 将上坡前倾旋转/手臂与 `TENSE`/`HOP` 姿态叠加。

---

## 3. 未验证状态保留（Pending）与准确复核步骤

- **当前状态**: 「首次站稳提示在 `sPos ∈ [237, 240)` 出现（含可读『慢一点，站稳再跳。』画面 + `Gait.TENSE` 姿态）→ 约 3s 自动消失 → 同 `sessionId` 恢复后再次越坎不重播」的同步 App 画面与时间线保持 **`Pending`**。
- **不阻塞范围**: 不撤回 `SW-005` / `SW-018` 已 `accepted` 结论，不阻塞第一批功能与性能测试包推进。
- **标准复核取证步骤（供具备模拟器/真机连接时执行）**:
  1. 禁止先跑阻塞式 `uiautomator dump` 再截屏；应使用 [tools/qa/test_sw024_ui_regression_entrypoints.py](../../../tools/qa/test_sw024_ui_regression_entrypoints.py) 的 `--capture-h2-burst` 模式或 `adb shell screenrecord`。
  2. 在森林虚走会话开启「轻触查看米数」显示实时米数，舒适区推进至 `235m` 后切换为紧张输入（`deflection = 0.90 > 0.72`）。
  3. 从 `235m` 起以 `≤ 400ms` 间隔连续抓取 `screencap` 帧序列（持续 `6.0s`），并在序列结束后单独导出 `session_snapshot`（含 `sessionId` 与 `stabilizeHintShown = true`）。
  4. 对帧序列逐帧执行 `h2-pixel-audit` 断言：必须至少存在 1 帧同时满足中央高亮像素 `> 3000`（可读「慢一点，站稳再跳。」）且旅人 `y_max == 2076`（站稳不腾空），且在该帧之后 `3.0–3.8s` 的帧中央高亮像素归 `0`。
