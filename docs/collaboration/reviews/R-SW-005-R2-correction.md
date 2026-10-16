# R-SW-005-R2 补证与视觉时序说明

对已登记独立评审报告 [R-SW-005-R2.md](R-SW-005-R2.md) 及 [H-SW-005-R2](../handoffs/zcode/H-SW-005-R2.md) 证据范围的补证记录（追加新文件，不改动已归档历史文件原文）。

## 1. 证据复核情况

在本次 P-20261016-01 规划抽读核查中：
1. **源码与单测闭环**:
   - `SessionViewModel.stabilizeHint`、`SessionScreen` 提示卡片 Composable 与 `ForestShell` gait 步态在主干已有完整代码接入；
   - 303 项 JVM 单测（含死区、同局快照恢复不重播）已 100% 通过；
   - 代码层逻辑已在 main（merge commit `70ebfc7`）正式集成。
2. **作者模拟器截图抽读**:
   - 作者提交的 `docs/collaboration/evidence/H-SW-005-R2/hint-shown.png` 在视觉抽读中未能直接辨识到「慢一点，站稳再跳。」文字卡片（可能因截屏帧时机或渲染透明度覆盖所致）；
   - 当前执行环境无本地 Android SDK/adb 模拟器设备，无法直接运行抓取运行时短间隔视频与 UI hierarchy。

## 2. 结论与 Pending 登记

- **诚实归档**: 依据协作协议，QA 不得凭作者截图文件名或代码 `delay` 声明运行时实测已通过；
- **Pending 项**: 将“真实提示出现→约 3s 消失/同局恢复不重播的同步视频或短间隔截图 + UI hierarchy”明确列为 **`Pending`**，留待后续具备真机/模拟器环境时补证；
- **状态影响**: 本项实测证据补证不撤销已 `accepted` 的领域代码与交互逻辑，保持 SW-005 `accepted` 状态。
