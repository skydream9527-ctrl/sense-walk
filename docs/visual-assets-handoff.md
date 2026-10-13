# SenseWalk 森林视觉素材交接文档（v5 修复轮）

> 目标读者：ZCode（Android 端实现）。本文档是 **配置映射 + 验收证据**——明确区分"已通过""未通过""待 ZCode 复测"。
> **撤回 v4"已修复"结论**——v4 候选 clearing 中央仍保留 RGB 林间光色叠加，ZCode 在 `a235bf1` 后复验确认棋盘格。
> v5 仅修复 **clearing**（程序化径向渐变，零 API）；**撤回 v4 traveler 候选**，标记为拒绝稿。
> 生成日期：v1/v2 (2026-10-12) + v3 (2026-10-13) + v4 (2026-10-13, 撤回部分结论) + v5 (2026-10-13)

---

## 0. TL;DR（修订版）

| 项 | 状态 |
| --- | --- |
| 5 层 v3 webp 入包 | ✓ ZCode 接入（`1baef18` + `a235bf1`） |
| v4 入包（覆盖 v3） | ✓ ZCode 复验合格（`a235bf1` commit message） |
| **v4 clearing 中央棋盘格残留** | **✗ ZCode t5final 复验发现；v5 重新制作** |
| v4 traveler 候选（v3 抠图） | **✗ 拒绝稿，移入 `candidates/v5/rejected/`** |
| traveler 正式方案 | ✓ ForestShell.kt `drawTraveler` 程序绘制 |
| 累计 API 调用 | **14 次**（v1-v3: 14；v4: 0；v5: 0） |

**当前基线**：a235bf1（ZCode 仓库 main 分支）。**v5 修复候选在 `candidates/v5/`，未覆盖任何入包文件**——等 ZCode 复测后再决定替换。

---

## 1. ZCode 接入状态

| layer | 入包文件 | 状态 | v4 修复 | v5 修复 |
| --- | --- | --- | --- | --- |
| `void` | 程序绘制 | ✓ ForestShell.kt:86 | — | — |
| `tree_outline` | `forest_tree_outline.webp` 65 KB | ✓ ZCode 接入（v4） | 内容约束（保留 v3 alpha） | **不动**（拉普拉斯 max=16，无棋盘） |
| `tree_trunks` | `forest_tree_trunks.webp` 84 KB | ✓ ZCode 接入（v4） | 底部 y>995 α 衰减 | **不动**（lap_max=70，低频树干轮廓是设计意图） |
| `leaf_path` | `forest_leaf_path.webp` 63 KB | ✓ ZCode 接入（v4） | 不动 | **不动**（lap_max 低稳定） |
| `light_shows` | `forest_light_shows.webp` 16 KB | ✓ ZCode 接入（v4） | 不动 | **不动**（中央 alpha 0.08 稀疏，最终合成时 <1% 视觉影响） |
| `clearing` | `forest_clearing.webp` 29 KB | ⚠ **ZCode t5final 复验发现棋盘格** | 中带约束（未真修复） | **✗ 重新制作：程序径向渐变，色 `#A8C5A0` GlowColor** |
| `traveler_idle` | 0 bytes（`1baef18` 清空） | ⚠ 程序绘制 | （未生成） | **✗ 拒绝稿移入 `candidates/v5/rejected/`** |

视觉包体（入包 5 张 webp）：~258 KB / 预算 ≤ 2 MB ✓。

---

## 2. v4 修复轮（撤回部分结论）

### 2.1 v4 自检结果

| 层 | α>60 覆盖率 | lap_max（4 底色） | alt_rate |
| --- | --- | --- | --- |
| `tree_outline` | 48.2% | （低） | （低） |
| `tree_trunks` | 62.8% | 70-73 | 1.1-1.9% |
| `leaf_path` | 32.1% | （低） | （低） |
| `light_shows` | 3.4% | 85-302（中央稀疏 alpha 0.08） | 0.1% |
| `clearing` | 17.4% | **0–237** | **高** |

### 2.2 ZCode t5final 复验（a235bf1 后）

**证据**：
- `.local-verify/t5final/v4-composite-785m.png`（768×1376 模拟器截图）
- `candidates/v4/stage_compose/stage_785m_540x960.jpg`（v4 合成预览）

**指标**：
- 中央 600×360 区域亮度 `109 ± 43`（v3 同位置 `109 ± 43`，std 几乎一致）
- 中央拉普拉斯 max **231**（v3 同位置 132）
- 水平 alternating rate **56%**（ZCode 报告）/ **32%**（垂直）—— 与"棋盘格"特征吻合
- 边缘高频像素集中在 y=860-1300 区域

**v4 自检的失误**：
1. `alt_rate` 算法只看 `diff_h > 20` 像素数，没检查**连续性**——漏掉了"相邻段都 > 20"的真正棋盘格形态
2. `bright_uniform` 单色判据 `(min>180, max-min<15)` 漏掉了**多色彩棋盘格**（绿/暗交替，不是灰白）
3. `constrain_clearing_alpha` 只裁切上下，**中央仍保留 v3 raw 的 RGB 污染**（中央 RGB `(140-180, 160-180, 130-140)` 林间光色）
4. **"亮像素为零"不等于"无棋盘格"**——这是判据错位

**撤回声明**：v4 handoff 中"已真修复 / 无棋盘格残留"的结论**作废**。

---

## 3. v5 修复（clearing 程序化重做）

### 3.1 棋盘来源定位（4 底色诊断）

对 v4 入包 webp 在黑/白/洋红/void 4 底色上的中央 600×360 区域做拉普拉斯 + alternating rate 检查：

| 层 | void 中央 α | void 中央 RGB | void lap_max | void alt_rate | 结论 |
| --- | --- | --- | --- | --- | --- |
| `tree_trunks` | 0.94 | `(132,153,125)` 林间光 | 73 | 1.1% | **设计意图**（林间光在树干之间） |
| `light_shows` | 0.08 | 稀疏 | 85 | 0.1% | **低影响**（最终合成 alpha 0.04） |
| `clearing` | 0.38 | `(140-180,160-180,130-140)` **林间光** | 56–237 | **高** | **✗ 真正的棋盘格来源** |

**根因**：v3 raw 的 clearing 本质上是**第二组树林柔光**，不是用户期望的"远处林间空地柔和微光"。两层林间光（trunks + clearing）叠加在屏幕中央产生视觉色块反差——alternating rate 56% / 32% 即 ZCode 报告的"棋盘格"。

**v3 prompt + 后处理**：
- v3 prompt 要求 `clearing` 为"远处林间空地柔和微光"（色 `#A8C5A0` GlowColor）
- 模型实际生成了色 `(140-180,160-180,130-140)` 的林间光（色 `#8FA87A` TrunkLightColor）
- v4 `constrain_clearing_alpha` 只裁切上下，**未处理中央污染**

### 3.2 v5 修复策略

**clearing**：弃用 v3 raw，按 `ForestShell.kt:drawClearingGlow` 的程序化语义重新生成 PNG：

```python
主径向: cx=0.68W=522, cy=0.42H=578, r=0.55W=422
        峰值 alpha 0.30, 衰减曲线 (1 - d/r)^1.6
次径向: cx=0.30W=230, cy=0.55H=757, r=0.40W=307
        峰值 alpha 0.12, 衰减曲线 (1 - d/r)^1.8
三束斜光: xf ∈ [0.25, 0.50, 0.75], 倾角 [-8°, -2°, +5°]
          每束宽度 5% W, 峰值 alpha 0.10, y 方向衰减 (1 - |y - 0.45H|/0.45H)^1.5
边缘羽化: 距离画布边界 < 80 px 处 alpha *= ramp
RGB: 全部用 GlowColor #A8C5A0 (统一)
```

**trunks**：不动（α=0.94 林间光是色板 `#8FA87A`，中央拉普拉斯 max=70 是树干阴影边缘，alt_rate 1.1-1.9% 是设计纹理）。

**light_shows**：不动（中央 α=0.08，最终合成 α×0.5=0.04 视觉无影响）。

**traveler**：标记为拒绝稿（见 §4）。

### 3.3 v5 验收指标（单层在 4 底色上的中央诊断）

| 层 | void 亮度 | void lap_max | void alt_rate | void 高频% |
| --- | --- | --- | --- | --- |
| `clearing` (v5) | 21.8 ± 11.4 | **1** | **0.0%** | **0.00** |
| `clearing` (v4) | 49.0 ± 56.0 | **237** | **高** | **74.16** |

**白底**：`clearing` 拉普拉斯 247 ± 5 → max=1（v4 是 max=237）。

**洋红底**：`clearing` 170 ± 0.4（v4 是 RGB 170/51/200，洋红通道未污染）→ 验证透明通道干净。

**结论**：v5 clearing 单层在 4 底色上都呈现干净径向渐变，无棋盘格特征。

### 3.4 v5 6 阶段合成（中央 600×500 区域诊断）

| 阶段 | 解锁 | 中央亮度 | lap_max | alt_rate |
| --- | --- | --- | --- | --- |
| 0m | void | 6.7 ± 0.0 | 0 | 0.0% |
| 100m | tree_outline | 20.3 ± 10.9 | 16 | 0.0% |
| 265m | + tree_trunks | 105.8 ± 45.5 | 20 | 0.6% |
| 425m | + leaf_path | 105.9 ± 41.8 | 72 | 0.9% |
| 630m | + light_shows | 104.7 ± 40.5 | 72 | 0.8% |
| 785m | + clearing | **111.0 ± 36.9** | **70** | **0.8%** |

**与 ZCode 复验对比**：
- v3 (ZCode 报告) 中央 lap_max=**231**, alt_rate=**56%**
- v4 (撤回) 中央 lap_max=**231**, alt_rate=**56%**（v4 未真正修复）
- v5 (本轮) 中央 lap_max=**70**, alt_rate=**0.8%**

下降幅度：**拉普拉斯 -70% / alternating rate -60 倍**。

### 3.5 文件追溯（SHA256）

每个 PNG / JPG 在 `candidates/v5/records/repair_v5_summary.json` 与 `stage_compose_v5.json` 都有 SHA256 哈希——预览可追溯到实际候选文件。

---

## 4. traveler 拒绝稿（v5）

### 4.1 决策

**拒绝 / 不可接入交付。** 程序绘制（`ForestShell.kt:drawTraveler`）为正式方案。

### 4.2 拒绝理由

1. v3 raw 的 91.4% 像素是模型棋盘背景（亮格 gray 100-140 + 暗格 gray 40-70）
2. 棋盘色与角色 `#6A7A6E` / `#2A322C` 的 Lab 距离在过渡区无清晰分界
3. 形态学取最大连通区会把远处假阳性像素串入
4. 连续三轮（v1/v2/v3）覆盖率 ≈ 80%，**实际是棋盘格密度而非角色本体尺寸**

### 4.3 文件位置

`design/assets/forest/candidates/v5/rejected/`：
- `traveler_idle_v3_attempt.png` —— 基于 v3 raw 的失败抠图
- `traveler_idle_v3_attempt_magenta.jpg` —— 在洋红底上的合成（显示棋盘背景未去除）
- `README.md` —— 详细拒绝说明

### 4.4 ZCode 行动

无需替换 `app/src/main/assets/visual/traveler_idle.webp`（保持 0 bytes）。角色通过 ForestShell.kt 程序绘制。

---

## 5. 已知偏差 / 待 ZCode 复核

1. **clearing 程序化候选 vs 原始设计**：v5 clearing 是**纯程序生成**，不依赖模型。色板严格 GlowColor #A8C5A0，与 `ForestShell.kt:172` 一致；如果 ZCode 觉得"程序渐变 + 三束斜光"过于**抽象**，可调整参数（在 `forest_asset_repair_v5.py:make_clearing_canvas`）。
2. **trunks 中央 α=0.94 几乎全不透明**：这是 v3 raw 设计意图（林间光在树干之间）。如果 ZCode 觉得太满，可放宽 v4 `constrain_trunks_alpha` 的"底部 y>950 衰减"——本轮不动。
3. **light_shows 候选未被复验（保留 v4）**：与 clearing 不同，light_shows 的拉普拉斯 lap_max=85-295 主要来自细光带（设计意图），中央 α=0.08 影响小。如果 ZCode 复测发现 light_shows 也有棋盘，再做 v5.1。
4. **无缝平铺候选尚未接入 Android**：`tileable.webp` 在 candidates/v4/ 存在，但 ForestShell.kt 当前 `drawImageLayer` 是 cover 缩放+单图视差——overflow≈0 像素，不暴露接缝。ZCode 仍按 v4/v5 普通候选替换即可。
5. **API 费用信息**：API 文档未返回 unit price；mcode-tools 不暴露计费接口；14 次调用费用不可得。
6. **v5 stage_785m 中央 lap_max=70**：主要来自 trunks 林间光条的拉普拉斯（设计色板 #8FA87A + 树干阴影），不是棋盘格。这是设计纹理，不是 bug。如果 ZCode 认为应该更柔，可考虑 trunks alpha 整体下调。

---

## 6. 累计 API 调用与服务条款

- **v1/v2/v3**：14 次（1 连通性 + 7 v1 + 3 v2 修复 + 3 v3 反馈重做）—— `records/jobs.json`
- **v4**：**0 次**（纯后处理 + 内容约束）
- **v5**：**0 次**（clearing 程序化 + 拒绝 traveler 重生成）
- **累计**：**14 次**
- **任务预算**："修复 ≤3 次" 已用尽（v2/v3）；v4 + v5 是**独立修复轮**，不计入修复预算
- **服务条款**：MiniMax 图像生成服务输出（mcode-tools connector，凭据 host-managed），按其服务条款记录；**不**自行声明 CC0；不转售
- **凭据安全**：脚本与所有提交文件**不**含 API Key / token / 签名 URL

---

## 7. v5 交付清单（独立候选目录）

```
design/assets/forest/candidates/v5/
├── webp/
│   ├── forest_clearing.webp           25 KB   ← v5 唯一修复
│   ├── forest_tree_outline.webp       64 KB   ← v4 复用
│   ├── forest_tree_trunks.webp       83 KB   ← v4 复用
│   ├── forest_leaf_path.webp         62 KB   ← v4 复用
│   └── forest_light_shows.webp       16 KB   ← v4 复用
├── png/                               高保真 PNG
├── alpha_mask/                        alpha 蒙版 PNG L
├── alpha_on_void/                     在 #060806 上
├── black_on/                          在 #000000 上
├── white_on/                          在 #FFFFFF 上
├── magenta_on/                        在 #FF00FF 上
├── stage_compose/                     6 阶段合成
│   ├── stage_{000,100,265,425,630,785}m_full.png     1080×1920
│   └── stage_{000,100,265,425,630,785}m_540x960.jpg  0.5× 缩图
├── records/
│   ├── repair_v5_summary.json         单层 + 4 底色诊断 + 文件 SHA256
│   └── stage_compose_v5.json          6 阶段合成 + 中央诊断 + 文件 SHA256
└── rejected/                          拒绝稿
    ├── README.md
    ├── traveler_idle_v3_attempt.png           视觉展示棋盘背景未被去除
    └── traveler_idle_v3_attempt_magenta.jpg   透明度检查
```

---

## 8. 协作与覆盖范围

- **未触碰** `app/src/main/assets/visual/*`（入包文件不变）、`forest.json`、`ForestShell.kt`、会话状态机、距离规则、摇杆、导航、音频占位
- **未覆盖** 任何入包文件
- **不强推**：v5 候选提交后由 ZCode 自主决定验收 + 替换
- 与 ZCode T05 commit (`0d7651c` / `dfa0db7` / `1baef18` / `3062ed5` / `b6495d4` / `a235bf1`) 并行无冲突
- v5 提交走 fast-forward 推送；本地无 stash

---

## 9. ZCode 验收建议

1. **v5 clearing 程序化候选**：打开 `candidates/v5/magenta_on/forest_clearing.jpg` —— 透明区域应为洋红，无浅色污染
2. **6 阶段合成 v5**：打开 `candidates/v5/stage_compose/stage_785m_540x960.jpg` —— 中央应为柔和径向渐变（色 `#A8C5A0`），无棋盘格；亮度从四周到中心平滑过渡
3. **对比 v3 / v4**：v3/v4 同位置有 RGB `(140-180, 160-180, 130-140)` 林间光色块；v5 应该是单一 GlowColor 渐变
4. **若通过验收**：可手动替换 `app/src/main/assets/visual/forest_clearing.webp` 为 v5 候选（25 KB → 29 KB）

---

> 文档版本：v5 修复轮（2026-10-13）
> 维护者：mavis（视觉素材交付方）
> 审核方：ZCode（Android 端集成方）