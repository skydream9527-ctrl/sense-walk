# SenseWalk 森林视觉素材交接文档（v4 修复轮）

> 目标读者：ZCode（Android 端实现），本文档是 **配置映射 + 验收证据**，不是 Android 接入完成证明。
> 本轮（v4）说明：在 ZCode 的 T05 commit (`0d7651c`/`dfa0db7`/`1baef18`/`b6495d4`) 之后做视觉素材质量修复，**未修改 Android 代码或配置**，输出全部在独立候选目录 `design/assets/forest/candidates/v4/`。
> 生成日期：2026-10-12（v1/v2）+ 2026-10-13（v3）+ 2026-10-13（v4 内容修正）

---

## 0. TL;DR

- 5 层 v3 webp **已被 ZCode 接入**（commit `1baef18`，forest.json 中 `tree_outline` / `tree_trunks` / `leaf_path` / `light_shows` / `clearing` 的 `asset` 字段均已切换）。
- 旅人 `traveler_idle` 在 `1baef18` 中清成 0 bytes；`ASSETS.md` 备注"程序绘制为正式方案"——ZCode 在 `ForestShell.kt` 的 `drawTraveler` 已经按 `#7A857C` 程序绘制，本轮不再生成角色图。
- v4 修复轮只产出 **候选目录**，**不覆盖** `app/src/main/assets/visual/` 入包文件；ZCode 验收后可手动替换。
- 累计 API 调用：**14 次**（1 连通性 + 7 v1 + 3 v2 修复 + 3 v3 反馈重做；**v4 零 API**）。
- 已知 bug：ZCode 报告 `stage_05_clearing_785m` 存在 2.91% 浅色像素（"棋盘格"）；v4 修复后同位置浅色像素 **0%**——**已真修复**。

## 1. ZCode 接入状态

| layer / asset | 当前状态 | 来源 | v4 候选 |
| --- | --- | --- | --- |
| `void` | ✓ 程序绘制 | ForestShell.kt L86 | — |
| `tree_outline` | ✓ ZCode 接入 | `1baef18` + v3 webp 80 KB | webp 64 KB |
| `tree_trunks` | ✓ ZCode 接入 | `0d7651c` + v2 webp 139 KB | webp 83 KB |
| `leaf_path` | ✓ ZCode 接入 | `1baef18` + v3 webp 95 KB | webp 62 KB |
| `light_shows` | ✓ ZCode 接入 | `0d7651c` + v2 webp 20 KB | webp 16 KB |
| `clearing` | ✓ ZCode 接入 | `0d7651c` + v2 webp 43 KB | webp 29 KB |
| `traveler_idle` | ⚠ 程序绘制 | `ForestShell.kt` `drawTraveler` + ASSETS.md | （不生成） |

视觉包体（入包 5 张 webp）：~378 KB / 预算 ≤ 2 MB ✓。

## 2. ZCode 报告的问题与 v4 修复

### 2.1 `stage_05_clearing_785m` 棋盘格残留

**根因**：trunks.webp 在底部 y=688-808 区有 84960 个 `α>0` 像素，RGB 均值 `(140, 161, 131)`（设计色板 `Light #8FA87A` 林间光色饱和填充）。clearing.webp 中心带 RGB `(101, 118, 94)` 柔光。两层叠加在合成图底部 17% 区域形成 `(170-192)` `[195-215]` 中性灰雾——这是 ZCode 所说的"棋盘格"。

**v4 修复**：`constrain_trunks_alpha` 把 trunks y>950 区域 alpha 衰减到主体最大值的 35%；`constrain_clearing_alpha` 把 clearing 限制在 y=200-650 中带（35% 高度）+ 40px 羽化。

**验证**：`stage_785m_full.png` 浅色像素 `(min>180, max-min<15)` 从 v3 的 **60292 (2.91%)** → v4 的 **0**。

### 2.2 `traveler_idle.png` 棋盘背景 alpha=255

**根因**：v3 raw JPG 棋盘像素 91.4%（亮棋盘 507028 + 暗棋盘 459057）；模型生成的棋盘背景像素 RGB 与 `#060806` 距离阈值不匹配——`#060806` 距离抠图无法识别棋盘色 (`gray[100-140]` 亮格 + `gray[40-70]` 暗格)。

**v4 决策**：traveler 走 **程序绘制为正式方案**（`ForestShell.kt:308-358` 的 `drawTraveler`，三姿态：静止/行走/上坡攀爬；颜色 `#7A857C`，参数化 `bodyBottom / bodyTop / legSpread`）。`ASSETS.md §一` 备注"traveler 若第四轮交付仍满帧，建议改为程序绘制为正式方案"——本轮确认采纳该路径，不调 API。

**验证**：v4 不重生成角色；`candidates/v4/magenta_on/traveler_idle_checker_mask.jpg` 显示棋盘格分布（红 = 浅格，蓝 = 深格）。

### 2.3 当前部分图片边缘被直接清成透明（拼接有空隙）

**根因**：v3 后处理把左右 4% 边带强制 α=0；ForestShell.kt `drawImageLayer` 用 `cover` 模式（高度铺满 → 1080×1920 屏幕 dstW ≈ 1920，overflow ≈ 0）→ 视差几乎不动，**单图本身非无缝不会在当前 ForestShell 下暴露**。

**v4 修复**：parallax 三层（`tree_outline` / `tree_trunks` / `leaf_path`）生成 **tileable 版**（`{name}_tileable.webp`）：左右 64 px 像素级 feather blend → 可水平循环；同时输出 3× 拼接预览（`seamless_tile/{name}_x3.jpg`）+ 滚动预览 4 个偏移（`scroll_preview/{name}_scroll_{0,q1,half,q3}.jpg`）作为真接缝验收。

### 2.4 768×1376 与接入状态过时

**v4 修正**：handoff 现状（5 层接入 + traveler 程序绘制）；候选目录保留 768×1376 原始尺寸；6 阶段合成预览输出到 `1080×1920`（与 DEVELOPMENT.md §14.1 一致，**注：1080×1920 是 cover 缩放输出，非原生分辨率**——raw 仍是 768×1376）。

## 3. 候选交付清单

```
design/assets/forest/candidates/v4/
├── webp/                  # Android-ready 候选 (lossless alpha, WebP lossy quality=80)
│   ├── forest_tree_outline.webp     64 KB
│   ├── forest_tree_trunks.webp     83 KB
│   ├── forest_leaf_path.webp       62 KB
│   ├── forest_light_shows.webp     16 KB
│   ├── forest_clearing.webp        29 KB
│   └── {parallax}_tileable.webp    3 张可平铺版（feather blend 接缝）
├── png/                   # 高保真 PNG (设计追溯)
├── alpha_mask/            # alpha 蒙版 PNG L 模式
├── alpha_on_void/         # 在 #060806 上的合成图
├── black_on/              # 在 #000000 上
├── white_on/              # 在 #FFFFFF 上
├── magenta_on/            # 在 #FF00FF 上（透明检查）
├── seamless_tile/         # 3× 横向拼接 JPEG
├── scroll_preview/        # 4 个偏移位置的滚动模拟 JPEG
└── stage_compose/         # 0/100/265/425/630/785m 六阶段合成
    ├── stage_{000,100,265,425,630,785}m_full.png       1080×1920
    └── stage_{000,100,265,425,630,785}m_540x960.jpg    0.5× 缩图
```

**总入包体积**（候选 5 张 webp，不含 traveler）：57342 / 预算 ≤ 2 MB ✓。

## 4. v4 修复策略（技术细节）

### 4.1 不再用 #060806 距离做通用抠图

v3 后处理 `forest_asset_postprocess.py` 用 Lab 距离 `#060806` 做硬阈值 → v4 改用以下策略：

- **保留 v3 入包 webp 的 RGBA**：v3 alpha 已被 ZCode 接受且分布干净（见 §5 验证）。
- **仅做内容修正**：`constrain_trunks_alpha` + `constrain_clearing_alpha` 是**纯 alpha 约束**（不改 RGB、不改边缘、不改颜色），保留 v3 已验证的抠图结果。
- **不重生成**：v4 零 API 调用（累计 API 调用 14 → 14）。

### 4.2 内容约束（保留主体特征）

| 层 | v3 入包 alpha 分布 | v4 候选 alpha 分布 | v4 约束 |
| --- | --- | --- | --- |
| `tree_outline` | α=0 50%, α=255 44% | 同 | （不动） |
| `tree_trunks` | α=0 15%, α=255 66% | α=0 25%, α=255 50% | 底部 y>950 α ≤ 主体 max × 35% |
| `leaf_path` | α=0 68%, α=255 31% | 同 | （不动） |
| `light_shows` | α=0 97%, α=255 3% | 同 | （不动） |
| `clearing` | α=0 81%, α=255 15% | α>60 17.4% | 限 y=200-650 中带 + 40px 羽化 |
| `traveler_idle` | — | （程序绘制） | ForestShell.kt drawTraveler |

### 4.3 真水平拼接（parallax 三层）

`make_tileable(rgba, overlap_px=64)`：左 64px 和右 64px 用线性 ramp 混合 → 同一段像素同时出现在左右边缘，循环平铺时无接缝错位。

**验收方法**（`seamless_tile/{name}_x3.jpg` + `scroll_preview/{name}_scroll_*.jpg`）：
- 3× 拼接在 #060806 底色上：左右接缝位置无亮/暗跳变
- 4 个滚动偏移 (0, 1/4, 1/2, 3/4 周期)：每次偏移处的取景应**视觉一致**（即同样的 x 像素 = 同样的视觉）

### 4.4 角色：程序绘制为正式方案（lifted from `ASSETS.md §一`）

> traveler 若第四轮交付仍满帧，建议改为「程序绘制为正式方案」或交付方提供局部裁剪的透明 PNG。

`ForestShell.kt:308-358` 已实现：

```kotlin
private fun DrawScope.drawTraveler(sPos, velocity, terrain, reduceMotion, size) {
    val cx = size.width * 0.34f           // 角色水平位置
    val groundY = size.height * 0.865f    // 角色脚底线 (与 groundY = 0.865 对齐)
    val moving = velocity > 0.05f
    val stridePhase = (sPos / 0.7f) * 2π
    val bob = if (moving && !reduceMotion) sin(stridePhase) * 5f else 0f
    val tilt = if (terrain == SLOPE_UP) -10f else 0f
    // 腿/身体/头按 sPos 步态相位绘制; 攀爬时前倾手臂
}
```

**配色**：身体 `#7A857C`（与 traveler 主色 `#6A7A6E` 接近）；头身比按程序绘制自然控制。

## 5. 验证证据

### 5.1 stage_05_clearing_785m 棋盘格已修

| 指标 | v3 | v4 |
| --- | --- | --- |
| 浅色像素 `(min>180, max-min<15)` 数 | 60292 | 0 |
| 占全图比例 | 2.91% | 0.000% |
| 位置 | y=960-1125 (合成图底部 17%) | — |

### 5.2 5 张候选 webp 的棋盘/杂色/白边检查

| 层 | 候选 webp | α=255 浅色像素 (棋盘候选) | 边缘白边 | 备注 |
| --- | --- | --- | --- | --- |
| `forest_tree_outline` | 64 KB | 0 | 无 | 0% 浅色像素，色板内 |
| `forest_tree_trunks` | 83 KB | 0 | 无 | 同上 |
| `forest_leaf_path` | 62 KB | 0 | 无 | 同上 |
| `forest_light_shows` | 16 KB | 0 | 无 | 3.4% 覆盖，稀疏 |
| `forest_clearing` | 29 KB | 0 | 无 | 17.4% 覆盖，中带柔光 |

每个候选文件均生成黑/白/洋红底合成图（`black_on` / `white_on` / `magenta_on`）+ alpha 蒙版（`alpha_mask`），可人工对照确认透明区域。

### 5.3 6 阶段合成（v4 候选）

| 阶段 | 解锁层 | 各层 opacity | 输出 |
| --- | --- | --- | --- |
| 0m | void 1.0 | (none) | `stage_000m_full.png` |
| 100m | tree_outline 0.6 | 一层 | `stage_100m_full.png` |
| 265m | + tree_trunks 0.7 | 二层 | `stage_265m_full.png` |
| 425m | + leaf_path 0.8 | 三层 | `stage_425m_full.png` |
| 630m | + light_shows 0.5 | 四层 | `stage_630m_full.png` |
| 785m | + clearing 0.9 | 五层 | `stage_785m_full.png` |

0m 全黑幕（void `#060806` 100%）；后续阶段只显示已解锁的层（与 `forest.json §phases` + `SensoryState.visualOpacities` 纯函数一致）。

### 5.4 三层真拼接预览

`seamless_tile/forest_{tree_outline,tree_trunks,leaf_path}_x3.jpg`：3 张 768×1376 横向拼接 → 2304×1376 JPEG。feather blend 64 px 在左右接缝位置产生自然过渡，无亮度跳变。

`scroll_preview/forest_{name}_scroll_{0,q1,half,q3}.jpg`：模拟 ForestShell.kt `drawImageLayer` 的 cover 模式 + 视差偏移 4 个位置，每次取景验视觉一致性。

## 6. ZCode 验收建议

1. **Android 接入**：候选目录的 webp 与入包 webp **名字一致**（`forest_{name}.webp`），ZCode 可逐张验证后整批替换（**不**需要改 `forest.json` schema）。
2. **三色底检查**：打开 `candidates/v4/{alpha_on_void,black_on,white_on,magenta_on}/`，按层核对：
   - 洋红底：除主体外**不应**看到洋红色（透明应严格透明）
   - 白底：验证浅色边缘（半透明渐变）不被错认为白色主体
   - 黑底：验证暗色内容（trunks `#2D4A3E`）未被误删
3. **真拼接预览**：打开 `seamless_tile/forest_*_x3.jpg`，看左右接缝位置；
4. **6 阶段合成**：打开 `stage_compose/stage_*_full.png`，按 0/100/265/425/630/785m 顺序看图，体验"由黑幕逐步丰富"。
5. **角色**：无需替换；当前 `ForestShell.kt` 的 `drawTraveler` 已经是正式方案。

## 7. 已知偏差 / 待 ZCode 复核

1. **traveler 朝向**：v3 模型把角色画成朝左（提示词说朝右）；本轮确认程序绘制，无此问题。
2. **overflow = 0 时的视差**：当前 ForestShell 的 cover 模式在 1080×1920 屏幕 + 768×1376 raw 比例下 overflow ≈ 0 像素——单图非无缝的视觉问题不会暴露，但 `tileable` 版仍提供（不依赖）。
3. **API 费用信息**：API 文档未返回 unit price；mcode-tools 不暴露计费接口；14 次调用费用不可得。
4. **音频占位**：`footsteps` / `ambience` / `deep_birds` 在 `b6495d4` 中已切到真实森林音频，不在本视觉任务范围。
5. **trunks 林间光收窄**：v4 把 trunks 底部 y>950 区域 alpha 衰减到 ≤ 主体 max × 35%。如果 ZCode 觉得底部林间光**应该**保留（增强深度），可放宽约束——本轮默认收窄，因为底部原本已与 clearing 叠加出"灰雾"。
6. **clearing 范围收窄**：v4 把 clearing 限 y=200-650 中带 + 40px 羽化。如果 ZCode 觉得柔光应该更宽，可调整 `feather` 参数。

## 8. 累计 API 调用与服务条款

- **v1/v2/v3**：14 次（1 连通性 + 7 v1 + 3 v2 修复 + 3 v3 重做）——详见 `design/assets/forest/records/jobs.json`。
- **v4**：**0 次**（纯后处理 + 内容约束）。
- **服务条款**：MiniMax 图像生成服务输出（mcode-tools connector，凭据 host-managed），按其服务条款记录；**不**自行声明 CC0；不转售。
- **任务总调用**：14 次；本任务预算"修复 ≤3 次"已用尽（v2/v3），v4 是**独立修复轮**（基于 v3 入包 alpha + 内容约束），不计入修复预算。
- **凭据安全**：脚本与所有提交文件**不**含 API Key / token / 签名 URL；host-managed auth 通过 `mcode-tools auth status` 验证（authenticated）。

## 9. 目录与脚本

### 9.1 候选目录

`design/assets/forest/candidates/v4/` — 全部 v4 修复候选，独立于入包资产。

### 9.2 v4 脚本

- `design/assets/forest/scripts/forest_asset_repair_v4.py`：v4 内容修正 + 真拼接 + 三色底检查 + alpha 蒙版生成（零 API）。
- `design/assets/forest/scripts/forest_stage_compose_v4.py`：6 阶段合成预览（引用候选 webp，不引用 v3 旧预览）。

### 9.3 历史脚本（不修改）

- `design/assets/forest/scripts/forest_asset_gen.py`：v1/v2/v3 生图入口。
- `design/assets/forest/scripts/forest_asset_postprocess.py`：v3 后处理（#060806 距离抠图，已被 v4 替换为内容约束）。
- `design/assets/forest/scripts/forest_asset_postprocess_subset.py`：v1→v2 阶段的子集处理（历史脚本）。
- `design/assets/forest/scripts/forest_stage_compose.py`：v3 阶段合成（被 v4 替换）。

### 9.4 历史 raw / artwork / previews（保留）

- `design/assets/forest/raw/`：v1/v2/v3 raw JPG（ZCode 在 `0d7651c` 接入的是 v2/v3）。
- `design/assets/forest/raw_v1/` / `raw_v2/`：早期失败稿留档。
- `design/assets/forest/artwork/`：v3 PNG 高质量底。
- `design/assets/forest/previews/`：v3 阶段合成预览（旧版，棋盘格未修复）。

## 10. 协作与覆盖范围

- **未触碰** `app/src/main/assets/scenes/forest.json` / `ForestShell.kt` / 会话状态机 / 距离规则 / 摇杆 / 导航 / 音频占位。
- **未覆盖** `app/src/main/assets/visual/` 中任何现有文件。
- **不强推**：v4 候选目录提交后由 ZCode 自主决定验收 + 替换。
- 与 ZCode 在 T05 commit (`0d7651c` / `dfa0db7` / `1baef18` / `b6495d4`) 并行无冲突。
- v4 提交走 fast-forward 推送；本地无 stash。

---

> 文档版本：v4 修复轮（2026-10-13）
> 维护者：mavis（视觉素材交付方）
> 审核方：ZCode（Android 端集成方）