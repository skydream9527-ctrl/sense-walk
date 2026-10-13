# 拒绝稿说明 — traveler_idle v3 尝试

## 状态

**拒绝 / 不可接入交付。** 本目录文件保留仅作"为何拒绝"的证据，**不**作为 ZCode 可替换的交付物。

## 拒绝理由（来自用户原话 + ASSETS.md §一）

> "角色已确定采用程序绘制。当前候选抠图还破坏人物并保留棋盘背景，标记为拒绝稿，不再作为可接入交付物。"

具体：

1. **棋盘背景**：v3 raw JPG 的 91.4% 像素是模型生成的棋盘背景（亮格 gray 100-140 + 暗格 gray 40-70），无法通过颜色距离 / 局部方差 / 形态学可靠区分。
2. **抠图破坏人物**：棋盘像素与角色 `#6A7A6E` / `#2A322C` 色板的 Lab 距离在过渡区无清晰分界；形态学取最大连通区会把远处假阳性像素串入。
3. **81% 满帧 = 棋盘而非角色**：连续三轮（v1/v2/v3）覆盖率都 ≈ 80%，实际是棋盘格密度，不是角色本体尺寸。

## 正式方案

`app/src/main/java/com/sensewalk/app/ui/session/ForestShell.kt:308-358` 的 `drawTraveler`（静止/行走/上坡攀爬三姿态）已被 ZCode 在 T05 commit (`0d7651c`) 及之后 commit 中接受为正式方案。

`app/src/main/assets/visual/traveler_idle.webp` 在 `1baef18` 中清为 0 bytes，与 ASSETS.md §一备注"程序绘制为正式方案"一致。

## 本目录文件用途

| 文件 | 用途 |
| --- | --- |
| `traveler_idle_v3_attempt.png` | v4 候选 PNG（基于 v3 raw 抠图失败稿）—— 视觉展示棋盘背景未被去除 |
| `traveler_idle_v3_attempt_magenta.jpg` | 在洋红底上的合成（透明度检查）—— 显示棋盘背景仍可见 |

## ZCode 行动

无需替换 `app/src/main/assets/visual/traveler_idle.webp`（保持 0 bytes）。角色通过 ForestShell.kt 程序绘制。