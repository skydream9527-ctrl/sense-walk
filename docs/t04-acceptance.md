# T04 验收清单（对照 design/ 与 PRD）

核查日期：2026-10-12 · 对照 commit `808d872` · CI [run 38249797779](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38249797779) 成功。  
基线：`design/README.md` 硬约束 + `design/03-product-prd/prd.md` P0 + `docs/zcode-handoff.md` T04 退出条件。

## 源码/CI 已满足（无需真机也可记为通过）

| 项 | 证据 | 结论 |
| --- | --- | --- |
| Home → 模式 → 会话 → 通关/放弃 | `HomeScreen` / `ModeScreen` / `SessionScreen` / `ResultScreen` | 通过 |
| 仅森林虚走开放；实走诚实关闭 | `ModeScreen`：`virtualWalkOpen = scene.id == "forest"`；实走 `enabled = false` 文案「暂未开放」 | 通过 |
| 距离门禁；未满只能放弃 | `CompletionGate` + 结果页 Completed/Abandoned 分流 | 通过（JVM 单测覆盖） |
| 舒适摇杆接入领域层 | `JoystickZone` → `ComfortStickMapper` / `VirtualWalkController`；设置含按住前进 | 通过 |
| 黑幕起笔、米数揭示 | `ForestShell` 按 `SensoryState` opacity；轻触才看可信米数 | 通过（视觉为程序剪影） |
| 放弃 1.5 s 长按；系统返回确认 | `AbandonControl`；`BackHandler` 继续/放弃对话框 | 通过 |
| 后台不偷跑 | 生命周期暂停清零速度/输入（SessionScreen + controller） | 通过（单测/代码路径；真机再确认） |
| 音频未冒充完成 | `AudioMixer`/`HapticEngine` 仍 stub；占位显式 | 正确：T05 范围 |

## 待真机/人工（标「待验证」，不据此宣称 M1 完成）

1. 安装 T04 debug APK，森林虚走满 800 m 一次通关（勿用 release 调试注入代替唯一手测）。
2. 未满距长按放弃，结果页为放弃且米数诚实。
3. 会话中切后台再回前台：进度不自动前进，需重新给摇杆输入。
4. 大字号 / TalkBack 能否开始、查看进度、放弃（T04 有语义标签；完整无障碍矩阵仍属后续）。
5. 拉满摇杆体感是否慢于中段（曲线单测已有；体感以真机为准）。

## 明确不在 T04

- 真实森林音效与振动生命周期 → **T05**
- 计步实走与前台服务 → **T06**
- 快照恢复、自动越坎、雨林 → **T07**

## APK

Actions artifact（需登录 GitHub）：`sensewalk-apk-808d872…`（约 16.4 MB），见成功 run 的 Artifacts。稳定下载链路由 main 手动 `workflow_dispatch` 并勾选 `publish_release` 生成 Pre-release。
