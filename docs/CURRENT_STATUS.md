# SenseWalk 当前进展与接手说明

更新日期 2026-11-21。开发以 GitHub `main` 为基线，后续由一个 Agent 独立推进。原开发工作树的提交归入主线历史。产品规则以 [DEVELOPMENT.md](../DEVELOPMENT.md) 为准。

## 当前可以体验什么

最新 Android 测试版为 [build-232-51a2b33](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-232-51a2b33)，源码基线为 `51a2b339ba50c2200d3cd41efab6afd7f952cb4c`。[APK 直接下载](https://github.com/skydream9527-ctrl/sense-walk/releases/download/build-232-51a2b33/app-debug.apk) · [构建记录](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/39774253141)。

| 范围 | 已有实现 | 待完成或待验证 |
| --- | --- | --- |
| Android 角色玩法 | 森林 800 米已开放。选景、模式、触屏摇杆、舒适节奏曲线、有效距离、地形自动越坎、按距揭示、暂停恢复、放弃和结果齐备 | 提升「操控角色」入口和角色动作可读性，完成安全区、操作手感与真实界面回归 |
| Android 户外实走 | 计步传感器、健康前台服务、暂停恢复和无传感器时的提示已实现 | SW-020 步长设置、保持同局步长、旧存档兼容与一次性触感。真机计步、锁屏 15 分钟及权限流待实测 |
| 森林画面与声音 | 已入包的森林音视素材、分层揭示、渲染缓存与异步加载可用 | 森林平铺候选和 UI 精修依次走 SW-022、SW-023。同条件真机性能对比待验证 |
| 雨林与其他场景 | 雨林设计和部分运行时、声景底座已交付。SW-006 R2 有真实出图候选 | 雨林仍未开放。候选需解决文件预算、交接与视觉问题才进入 SW-007。其余场景与四景整体验收仍在路线中 |
| iPadOS | 已确定与 Android 共享森林玩法规则 | 从独立原生工程、模拟器运行与森林触屏闭环开始。后续按设备与系统能力验证户外实走 |

森林规则为 `comfort_v1`，摇杆中段快于推满，瞬时上限 1.4 m/s，每局按有效距离累计并在 800 米达标后通关。触控取消、暂停、后台切换和恢复行为继续按产品规则验证。

## 验证证据

- build-232 的 Android JVM 单测任务、Lint、debug APK 构建和 Release Manifest 检查通过。329 项测试的原始 XML 对应较早的森林渲染基线，见 [2026-10-21 证据](collaboration/evidence/P-20261021-01/README.md)。
- 现有模拟器和截图记录覆盖一些森林流程。标准 800 米真人手动通关、真实计步与锁屏、实体耳机/来电、触感、真机视觉与性能，以及最终 5–8 人内测仍待验证。
- 已有 Android 界面回归草案。SW-026 交付时要运行实操测试并留原始记录。

## 单 Agent 的下一步

1. **先完善 Android 森林**。复现最新安装包，完成 SW-020 的安全区、步长和触感，完善「操控角色」入口、操作反馈与可访问替代。跑 SW-026 的真实操作回归，补 SW-025 构建身份追溯。
2. **再完成 iPadOS 森林可玩版**。独立维护原生工程和构建。在模拟器完成选景、触屏操控、地形反馈、按距声景、暂停恢复和 800 米通关。覆盖横竖屏、安全区及切后台。iPad 实走作为后续阶段，依据目标设备和系统能力实现与验收。
3. **继续素材和场景**。先完成并验证 SW-022 森林连续平铺候选，再做 SW-023 入包。雨林使用获批设计和 R2 候选继续返工，沿用已有 API 尝试账本，复核预算、图层及声景证据后启动 SW-007。再推进 SW-008 四景和 SW-009 真机内测。

每批交付记录准确 SHA、实际运行命令与结果、构建下载、相关素材哈希和待验证项。历史任务编号可从 [档案看板](collaboration/BOARD.md) 查找。单 Agent 的执行入口在 [AGENTS.md](../AGENTS.md)。

## 旧工作树和大样本的取回位置

已合入的代码和审核继续沿用主线。下表是这次纳入主线提交历史的五个原工作树尖端。主线检出保留已验收的工程与素材版本。

| 提交 | 保存内容 |
| --- | --- |
| [e3d45ed](https://github.com/skydream9527-ctrl/sense-walk/commit/e3d45ed59ce3dd1dc53bfe6b2e9b045ab889f42d) | SW-002 已完成交付的作者状态记录 |
| [8e73b13](https://github.com/skydream9527-ctrl/sense-walk/commit/8e73b13c432fb8b003c960d1706bc09b22814533) | SW-006 R1 零 API 占位草案 |
| [9bcfbab](https://github.com/skydream9527-ctrl/sense-walk/commit/9bcfbaba356269ed43b6944d44c7fc1c531788d4) | SW-006 R2 候选、交接和补充修订 |
| [13d6c0d](https://github.com/skydream9527-ctrl/sense-walk/commit/13d6c0d51261a467feb2c3a57705ae7820198e49) | SW-014 R1 预检旧版 |
| [bda0b74](https://github.com/skydream9527-ctrl/sense-walk/commit/bda0b74d53791c09a4c9b7a2858b9c32321bc862) | SW-014 R2 预检旧版，已由合入主线的 R3 继承其工作目标 |

雨林下一轮可从 `9bcfbab` 获取 `design/assets/rainforest/candidates/SW-006/r2/` 下的候选，以 [R2 更正审核](collaboration/reviews/R-SW-006-R2-correction.md) 核对。R2 仍待返工，现有尝试预算已用完。

三套程序生成的雨林超预算反例移出日常检出。历史报告、复验脚本和原始样本仍能按提交取回。需要重跑旧版探针时，在仓库根目录恢复这些路径，运行对应修订的脚本。恢复的样本在 Git 忽略范围内。

```sh
git archive 51a2b339ba50c2200d3cd41efab6afd7f952cb4c -- \
  design/assets/rainforest/preflight/SW-014/r2/fixtures/negative_real_oversize \
  design/assets/rainforest/preflight/SW-014/r3/fixtures/negative_real_oversize_layer \
  design/assets/rainforest/preflight/SW-014/r3/fixtures/negative_real_oversize_scene | tar -xf -
```
