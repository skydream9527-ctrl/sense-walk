# SW-024 证据档案 · 独立基准、提示证据复核与回归入口

- **任务**: [SW-024](../../tasks/SW-024.md)（独立基准、提示证据复核与回归入口）
- **负责角色**: `antigravity`（QA / 协调集成）
- **主干基线**: `4f57659e00e0267be03a0a7b966cacba8387c5ee`（源码同 `321060e945b512f3f6b8b038543eb3b9d16a58bc`；冻结安装基准 `build-176-aaa789b` / `aaa789b3afd789d121eb6f0c96189fe9835d3e3c`）

## 档案索引

1. **[R-SW-018-R1 独立证据范围修正](../../reviews/R-SW-018-R1-correction.md)**：亲自审看并像素量化复核 `H-SW-018-R1` 的 `H2-hint-appear.png`、`H2-hint-gone.png` 与 `F3-completed.png`，区分作者原报告、QA 实看事实与待验证项，定位 `uiautomator dump` 阻塞导致错失 `3.0s` 提示窗口的时序根因，保留 `SW-018` 整体 `accepted` 与 `800m` 通关结论，将同步提示截图/时间线如实列为 `Pending` 并给出 400ms 连续抓拍复核步骤。
2. **[H2 截图量化像素审计数据](h2-pixel-audit.json)**：5 张关键截图的字节数、SHA256、旅人 `#7A857C` 像素包围盒（证明两张 H2 图均为 `y_max = 2050/2049` 的 `Gait.HOP` 腾空帧而非 `Gait.TENSE` 微蹲）及中央卡片区域高亮像素统计（`H2-hint-appear.png` 为 `0`）。
3. **[同环境性能基准与前后比较协议](performance-benchmark-protocol.md)**：固定硬件/AVD、分辨率、刷新率、构建类型、冷热启动及 S0–S6 行走阶段点，记录 `321060e` 静态源码基线数据，并将帧时间/解码耗时/内存/重组计数等运行时对拍指标列为 `Pending`。
4. **[基线缺陷分级表与两批发布验收清单](defect-and-release-checklist.md)**：汇总 `D-SW024-01` 至 `D-SW024-09`（含 owner、严重度、复现 build、证据路径）、向 ZCode 转交的 `androidTestImplementation` 依赖缺口说明，以及第一批（`SW-019` + `SW-020` + `SW-025`，不等平铺素材）和第二批（`SW-021` → `SW-022` → `SW-023`）测试包发布门禁。
5. **UI 与领域回归入口**：
   - Python 独立回归与 ADB 取证入口：[tools/qa/test_sw024_ui_regression_entrypoints.py](../../../../tools/qa/test_sw024_ui_regression_entrypoints.py)
   - AndroidTest 源码回归入口（未在设备运行，状态记 `pending`）：[SenseWalkRegressionInstrumentationTest.kt](../../../../app/src/androidTest/java/com/sensewalk/app/qa/SenseWalkRegressionInstrumentationTest.kt)
