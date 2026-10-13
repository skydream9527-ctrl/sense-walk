# T05 验收清单（对照 design/ 与 PRD）

核查日期：2026-10-13 · 对照 commit `4974b23` · CI [run 38406951754](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38406951754) 成功（196 JVM 测试全绿）。  
基线：`design/README.md` 硬约束 + `design/03-product-prd/prd.md` P0（F03–F06）+ `docs/zcode-handoff.md` T05 退出条件 + DEVELOPMENT.md §0 / §20.8–§20.10。  
核查方式：源码与配置静态对照 + CI 结论；**不把模拟器走查当真人验收**。

## 源码/CI 已满足（无需真机也可记为通过）

| 项 | 证据 | 结论 |
| --- | --- | --- |
| 距离门禁 800 m；未满只能放弃 | `forest.json` `requiredDistanceMeters=800`；`CompletionGate` + 结果页分流；单测 | 通过 |
| 舒适摇杆 comfort_v1；拉满 ≠ 最快；硬顶 ≤ 1.4 | `ComfortStickMapper` + `ComfortStickMapperTest`（甜点峰值与硬顶） | 通过 |
| 黑幕起笔；音/振/视按 atMeters 同程 | 相位：void@0 → steps/outline@80 → ambience/trunks@240 → haptic/leaf@400 → birds/light@600 → clearing@760 | 通过（配置） |
| 真实森林音频入库 | `layers.footsteps`×6 + `ambience`/`deep_birds` loop；`app/src/main/assets/audio/*.ogg` | 通过 |
| 感官引擎与停走边界 | `SensoryCoordinator` + `AndroidSensoryBackend`；播放边界单测（焦点被拒、暂停停脚步流、终态吸收迟到回调等） | 通过 |
| 音频焦点门控全部出声入口 | `AudioFocusGate` + SessionViewModel；获准不补播、不重复建层；调用链测试 | 通过 |
| 视觉三层真实图 + 两层程序降级 | `visualLayers`：outline/trunks/leaf_path 有 webp；light_shows/clearing 为 overlay（无 asset，程序渲染，不冒充真实素材） | 通过（诚实降级） |
| 仅森林虚走开放 | `ModeScreen`：`virtualWalkOpen = scene.id == "forest"`；实走「暂未开放」 | 通过 |
| 模拟器 800 m 全程 | DEVELOPMENT.md §20.9 记录检查点与来电「已暂停 + 继续走」 | 通过（模拟器证据；非真人） |

## 待真机/人工（标「待验证」，不据此宣称 M1 完成）

1. 安装本轮 debug APK，森林虚走标准 800 m **真人手动**通关一次（勿用调试注入代替）。
2. 拉满摇杆体感是否慢于中段甜点区（曲线单测已有；体感以真机为准）。
3. 实体耳机断连 / 来电抢焦点：应暂停且不自动恢复行走；回前台需用户再给输入。
4. 脚步振动（`haptic_steps`@400 m）：模拟器无 HAL，必须真机确认。
5. 切后台再回前台：进度不偷跑；需重新给摇杆。
6. 视觉真人走查：outline/trunks/leaf_path 观感；light_shows/clearing 程序层是否可接受，或等 MiniMax 重制后再验。

## 已知诚实缺口（不阻塞开 T06，但阻塞宣布 M1）

- light_shows / clearing：曾入包 webp 因 32px 对角棋盘被撤回「五层合格」结论，现为程序 overlay；磁盘上仍留有旧 webp，配置未引用为真实层。
- 旅人：程序绘制为正式方案（非贴图角色）。
- t04-acceptance.md 中「音频仍 stub」已过时；以本清单与 DEVELOPMENT.md §0 为准。

## 明确不在 T05 / 下一阶段

- 计步实走、权限、前台服务 → **T06**
- 快照恢复、自动越坎、雨林 → **T07**
- 城市/沙漠四景 → **T08**
- 真机矩阵与内测报告 → **T09**

## APK

- **稳定 Pre-release（推荐真机安装）**：[`build-34-9c0ccc4`](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-34-9c0ccc4) · 直接下载 [`app-debug.apk`](https://github.com/skydream9527-ctrl/sense-walk/releases/download/build-34-9c0ccc4/app-debug.apk)（约 19.2 MB，含 `4974b23` 程序渲染层修复 + 本清单）。
- Actions artifact（需登录）：[run 38406951754](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38406951754)（`4974b23`）；Pre-release 构建记录见 [run 38421621801](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38421621801)。
- 旧包 `build-26-3062ed5` **早于**本轮修复，真机请勿再用。

## 结论

T05 机制与素材在源码/CI/模拟器维度可记「完成」。**M1 退出条件未齐**（标准 800 m 真人手测 + 真机耳机/来电/振动）。建议：装 `build-34-9c0ccc4` APK 跑待验证 1–5，或先开 T06 并行推进实走，M1 勾选留到有真机证据再做。
