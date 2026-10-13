# SenseWalk · 森林视觉素材交接

> 任务范围：森林场景视觉素材生成。
> 目标读者：ZCode（Android 端实现），本文档是**配置映射 + 验收证据**，不是 Android 接入完成证明。
> 本轮说明：本任务在与 ZCode 的 T05 commit（`0d7651c` / `dfa0db7`）并行进行；T05 已用我前两批（v1 + v2）的 5 张图作为参考并接入了 3 张（`tree_trunks` / `light_shows` / `clearing`）。`ASSETS.md` 给出 ZCode 自己的视觉验收反馈，本轮根据该反馈出 v3 重做 3 张被拒的层（`tree_outline` / `leaf_path` / `traveler_idle`）。
> 生成日期：2026-10-12（v1/v2）+ 2026-10-13（v3）
> 对齐文档：[DEVELOPMENT.md v0.8 §14](../DEVELOPMENT.md)、[design/01-scenes-terrain/forest.md](../design/01-scenes-terrain/forest.md)、[design/02-characters/traveler.md](../design/02-characters/traveler.md)、[ASSETS.md](../ASSETS.md)

## 0. TL;DR

| 项 | 状态 |
| --- | --- |
| 生成 API | mcode-tools `connector__matrix__generate_image`（text-to-image，1K，9:16） |
| 调用次数 | 1（连通性） + 7（v1） + 3（v2 修复） + 3（v3 按 ZCode 反馈重做） = **14 次** |
| 修复预算 | 任务内"修复最多 3 次"已用尽；v3 是 ZCode 在 T05 commit 后给的**新一轮**反馈，不计入原任务预算 |
| 凭据处理 | 通过 host-managed auth（`mcode-tools auth status` = authenticated），脚本/代码不读不写任何 API Key / token |
| ZCode 接入状态 | 3 张已接入（`tree_trunks` / `light_shows` / `clearing`），3 张 v3 待 ZCode 重做 `forest.json` 引用后接入 |
| 音频占位 | **仍未解决**（forest.json 中 `footsteps` / `ambience` / `deep_birds` 仍指向 dev_tone 占位；本任务不做） |
| 已知偏差 | §7。**不宣称森林 800 m 整体素材已满足发布验收。** |

## 1. 美术方向（来自本任务约定 + design/01-scenes-terrain/forest.md §2）

- 风格：克制的二维手绘插画、干净剪影、轻微纸感、低饱和、柔和边缘、侧视 / 轻微 3/4 侧视、横向行走场景
- 与雨林区分：少雾、透气、干爽落叶、少量温暖褐色点缀
- 色板：`#060806` 黑幕 / `#1A2820` 远树轮廓 / `#2D4A3E` 树干 / `#8FA87A` 林间光 / `#6B8F71` 落叶 / `#A89060` 暖褐
- 禁止：文字 / 标志 / 水印 / UI / 边框 / 血条 / 数字 / 高饱和霓虹 / 恐怖元素 / 强光爆点 / 复杂写实纹理 / 第一人称透视道路
- 角色主色：`#6A7A6E`，暗部 `#2A322C`，极弱灰绿边缘光，头身比约 1:3.2–1:3.5

## 2. ZCode 接入与本轮 v3 重做背景

ZCode 在 T05 commit `0d7651c` 中：
- 接入了 3 张 v2 修复图（`tree_trunks` / `light_shows` / `clearing`），通过 `forest.json` 改为 `asset` 字段并在 `ForestShell` 真实渲染；
- 拒绝了 3 张（`tree_outline` / `leaf_path` / `traveler_idle`），原因是"未通过验收"（详见 `ASSETS.md` 一、森林视觉素材表）。

`dfa0db7` 把这 3 张从 `app/src/main/assets/visual/` 移除（标记 0 bytes），**未删盘**，仅做包内清理。

`ASSETS.md` 写明的具体不合格原因（与本轮 v3 提示词直接对应）：

| 层 | ASSETS.md 结论 | 本轮 v3 调整 |
| --- | --- | --- |
| `tree_outline` | 顶部透明合格，但**可见内容仅 ~2%**（远山树线过稀） | 改为"中段 35% 高度密集远山树线" |
| `leaf_path` | 覆盖 85%，**顶部 92% 可见**（近景地面层不应占满画面上部） | 改为"上 70% 完全空 + 下 30% 地面" |
| `traveler_idle` | 覆盖 80%——**角色应只占画布小部分，非全幅** | 改为"角色占画布下半中段约 30% 高度 + 四周大幅留白" |

## 3. 交付清单

> **当前状态**：v3 修复稿已落盘到 `app/src/main/assets/visual/`，但 `forest.json` 仍引用旧 placeholder（v2 被 ZCode 在 `dfa0db7` 中清出包后未替换）。ZCode 在 T06+ 重做 `asset` 字段后即可接入；本任务**不**直接改 forest.json。

### 3.1 Android assets（与 ZCode 同步状态）

```
app/src/main/assets/visual/forest_tree_trunks.webp     ~136 KB   ✓ ZCode 接入
app/src/main/assets/visual/forest_light_shows.webp     ~20 KB    ✓ ZCode 接入
app/src/main/assets/visual/forest_clearing.webp        ~43 KB    ✓ ZCode 接入
app/src/main/assets/visual/forest_tree_outline.webp    ~80 KB    ⚠ v3 已落盘；待 ZCode 重做 forest.json `asset` 引用
app/src/main/assets/visual/forest_leaf_path.webp      ~95 KB    ⚠ v3 已落盘；待 ZCode 重做 forest.json `asset` 引用
app/src/main/assets/visual/traveler_idle.webp         ~86 KB    ⚠ v3 已落盘；待 ZCode 重做 forest.json `asset` 引用
app/src/main/assets/visual/forest_style_ref.webp      —         不入包（参考用，留档在 design/assets/forest/raw/）
```

5 森林层 + 1 角色 = 6 槽位；本轮 v3 修复 3 张后，建议 ZCode 重新把这些 webp 放回 `app/src/main/assets/visual/`，**并修改 `forest.json` 的 `asset` 字段引用**（如 `tree_outline` / `leaf_path` 的 `placeholder: "dev_silhouette:..."` 替换为 `asset: "visual/forest_xxx.webp"`）。

### 3.2 美术目录（仅供设计追溯，不入包）

```
design/assets/forest/
├── artwork/                # 高质量 PNG（带 alpha），原始编辑底
├── raw/                    # 当前 raw（v3 = 当前；v2 = raw_v2；v1 = raw_v1）
├── raw_v1/                 # 3 张 v1 失败稿留档
├── raw_v2/                 # 3 张 v2 修复稿留档（被 ZCode 拒绝）
├── previews/               # 透明检查 / 拼接 / 6 阶段合成预览
├── records/                # 任务清单 + 后处理汇总 + 阶段合成记录
└── scripts/                # 可重复执行脚本
    ├── forest_asset_gen.py
    ├── forest_asset_postprocess.py
    ├── forest_asset_postprocess_subset.py
    └── forest_stage_compose.py
```

## 4. 各层技术规格（v3 修订版）

> 共同画布：API 实际 1K 9:16 = **768×1376** px。比例与用户约定的 1080×1920 一致（9:16），但像素低——见 §7 #1。
> 透明状态：所有层均为 RGBA / WebP alpha 通道；alpha=0 表示完全透明。
> 边带：所有层四周 4% 边带强制 alpha=0，角色 6% / 5% / 5% 边带。

| Layer ID | 文件 | unlock (m) | 目标 opacity | fade (m) | role | v3 内容约束 | 拼接 | 透明 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `tree_outline` | `forest_tree_outline.webp` | 80 | 0.60 | 20 | 远景 parallax 0.3 | 中段 35% 高度**密集**远山树线（v3 修订）；上/下全 #060806 | 左右 | ✓ |
| `tree_trunks` | `forest_tree_trunks.webp` | 240 | 0.70 | 25 | 中景 parallax 0.3 | 中段垂直树干 + 林间光；上 10% / 下 18% 透明 | 左右 | ✓ |
| `leaf_path` | `forest_leaf_path.webp` | 400 | 0.80 | 25 | 近景 parallax 0.6 | **下 30% 落叶地面**；上 70% 完全空（v3 修订） | 左右 | ✓ |
| `light_shows` | `forest_light_shows.webp` | 600 | 0.65 | 30 | overlay | 3 道斜光柱 + 3 只飞鸟剪影 | 不要求 | ✓ |
| `clearing` | `forest_clearing.webp` | 760 | 0.90 | 25 | overlay | 中央椭圆微光 + 远景薄雾 | 不要求 | ✓ |
| `traveler_idle` | `traveler_idle.webp` | （角色，非 layer） | — | — | character | 角色**只占画布下半中段 ~30% 高度**；四周大幅留白（v3 修订） | 不要求 | ✓ |

### 4.1 基线 / 裁切建议

- `traveler_idle.webp` 推荐与 `ForestShell.kt` 现有 `cx = size.width * 0.34f`、`groundY = size.height * 0.865f` 一致放置；脚底与 `leaf_path` 上沿对齐。
- `leaf_path` v3 的水平地面只占画布下 30%（按 `groundY = size.height * 0.865f` 估算，正好在 groundY 附近）。
- 摇杆交互区位于画布下约 45%（按 ForestShell 现状）；素材在该区域细节较疏，不会干扰操作。

## 5. 生成记录（14 次 API 调用）

| # | job_id | 阶段 | 状态 | 主要差异 |
| - | --- | --- | --- | --- |
| 1 | connectivity_test | 连通性 | OK | 弃用，仅留档 |
| 2 | style_ref | v1 | OK | 风格参考，作色彩参照；不入包 |
| 3 | forest_tree_outline | v1 | REJECTED | 3 段堆叠 |
| 4 | forest_tree_trunks | v1 | OK（v2 也通过） | 树干层 |
| 5 | forest_leaf_path | v1 | OK（v2 也通过） | 上半有远景雾，v2 后处理收紧 |
| 6 | forest_light_shows | v1 | REJECTED | 只 1 根光柱 |
| 7 | forest_clearing | v1 | OK（v2 也通过） | 微光椭圆 + 雾 |
| 8 | traveler_idle | v1 | REJECTED | 正面 + 头身比 1:6 |
| 9 | forest_tree_outline | v2 | **ZCode 拒绝**（内容过稀 2%） | 单条树线在画布下 50% |
| 10 | forest_light_shows | v2 | OK | 3 光柱 + 3 飞鸟（ZCode 接受） |
| 11 | traveler_idle | v2 | **ZCode 拒绝**（角色占 80%） | 3/4 侧视朝右、头身比 1:3.3 |
| 12 | forest_tree_outline | **v3（本轮）** | 待 ZCode 重做引用 | 中段 35% 密集远山树线 |
| 13 | forest_leaf_path | **v3（本轮）** | 待 ZCode 重做引用 | 上 70% 空 + 下 30% 地面 |
| 14 | traveler_idle | **v3（本轮）** | 待 ZCode 重做引用 | 角色占画布下半中段 30% |

完整提示词与参数见 [`design/assets/forest/records/jobs.json`](../design/assets/forest/records/jobs.json)。

### 5.1 失败/修复策略

v1 → v2 修复原因（任务内 3 次修复预算）：
- **tree_outline v1 → v2**：原提示词"horizontal seamless tile"被模型理解为"垂直堆叠三段"；v2 改为单条树线。
- **light_shows v1 → v2**：原提示词"two or three"被模型保守到 1；v2 改为"EXACTLY THREE"。
- **traveler_idle v1 → v2**：原提示词"side 3/4 view"被模型画成正面；v2 改为"STRICT side view facing RIGHT"。

v2 → v3 修复原因（ZCode 在 `ASSETS.md` 反馈）：
- **tree_outline v2 → v3**：v2 单条树线过于稀疏（覆盖率 2%），改为"中段 35% 密集"。
- **leaf_path v2 → v3**：v2 顶部 92% 可见（被模型画了远景雾），改为"上 70% 完全空 + 下 30% 地面"。
- **traveler_idle v2 → v3**：v2 角色覆盖 80% 画布，改为"角色占画布下半中段 30%"。

### 5.2 用量与费用

- 单价信息：API 文档未返回 unit price；本环境也未返回 token / credit 用量。
- 用户可见成本：仅"调用 14 次"的事实；具体金额不可知。
- 凭据安全：脚本与所有提交文件中**不**含 API Key / token / 签名 URL。

## 6. 配置映射（建议，**不**直接修改 forest.json / Kotlin）

`app/src/main/assets/scenes/forest.json` 当前 `visualLayers` 段（推测，ZCode 已在 T05 中修改过）：

```json
"visualLayers": {
  "void":         { "type": "solid", "color": "#060806" },
  "tree_outline": { "type": "parallax", "asset": "visual/forest_tree_outline.webp", "parallax": 0.3 },
  "tree_trunks":  { "type": "parallax", "asset": "visual/forest_tree_trunks.webp", "parallax": 0.3 },
  "leaf_path":    { "type": "parallax", "asset": "visual/forest_leaf_path.webp", "parallax": 0.6 },
  "light_shows":  { "type": "overlay", "asset": "visual/forest_light_shows.webp" },
  "clearing":     { "type": "overlay", "asset": "visual/forest_clearing.webp" }
}
```

**建议**（ZCode 自行评估后决定）：

- v3 修复后，把 `app/src/main/assets/visual/forest_tree_outline.webp` / `forest_leaf_path.webp` / `traveler_idle.webp` 重新放回包内；
- 这些层当前 v3 视觉上更符合 ZCode 验收要求（密集远山 / 上下 70% 空 / 小角色）。

**本任务不直接修改 forest.json**——按用户原始要求"仅提供映射建议，不直接修改"。

### 6.1 渲染层（ForestShell.kt）影响

- `ForestShell.kt` 当前已经在 T05 中支持 `asset` 字段的视觉层；ZCode 负责接入。
- 透明度仍由 `SensoryState.visualOpacities`（米数纯函数）驱动；`parallax` 因子 0.3 / 0.3 / 0.6 保持兼容。
- **不在本任务范围**。

## 7. 已知偏差

1. **画布尺寸**：API 实际输出 768×1376（1K 9:16），不是用户约定的 1080×1920。  
   - 影响：1080×1920 屏上会插值放大；锐度略降。
   - 修法：API 改 2K（成本上升）或本地 Lanczos 上采样。

2. **后处理不是"真 alpha"**：模型只输出 JPG，`alpha` 是后期基于 #060806 颜色距离模拟的。  
   - 影响：少数边界像素与真透明 RGBA 输出有差异；在 #060806 黑底上无可见差异。

3. **JPEG 无原生透明**：ASSETS.md 已记录；左右 4% 边带被裁成全透明，水平拼接会有周期性空隙。  
   - 影响：parallax 滑动时若滑出图片宽度则保持静态（已记录）。

4. **clearing 椭圆位置偏高**：模型把"林间空地"画在画面正中（~45% y），不是"远处"（上 1/3）。  
   - 影响：785m 阶段微光位置偏中央。
   - 修法：可重出（用完 v3 修复）；或保留并接受。

5. **forest_tree_outline v2 已知过稀**（ASSETS.md）；v3 已修复（中段 35% 密集远山），但本轮 v3 还没有 ZCode 验收。

6. **leaf_path v2 已知溢出**（ASSETS.md）；v3 已修复（上 70% 完全空 + 下 30% 地面），但本轮 v3 还没有 ZCode 验收。

7. **traveler_idle v2 已知占满**（ASSETS.md）；v3 已修复（角色占画布下半中段 30%），但本轮 v3 还没有 ZCode 验收。

8. **生成服务条款**：本批 AI 生成素材按生成服务条款记录，**不**声明 CC0。详见 §10。

## 8. 不在本任务范围

- **不**修改 `app/` 业务代码；
- **不**修改 `forest.json`（仅提供 §6 映射建议）；
- **不**解决音频占位（`footsteps` / `ambience` / `deep_birds` 仍指向 `dev_tone:...`）；
- **不**生成动画 sprite sheet（用户明确"本轮只交付静态角色及比例参考"）；
- **不**自动扩展到雨林 / 沙漠 / 城市等其他场景；
- **不**把"文件已生成"描述为"Android 已完成接入"。

## 9. 复现步骤（给后续维护者）

```bash
# 1. 验证 API 凭据
mcode-tools auth status

# 2. 生成（7 张 + 修复 3 张 + ZCode 反馈 3 张）
python3 design/assets/forest/scripts/forest_asset_gen.py --limit 10

# 3. 后处理（抠图 + 边带 + alpha 二值化 → WebP）
python3 design/assets/forest/scripts/forest_asset_postprocess.py

# 4. 6 阶段合成预览
python3 design/assets/forest/scripts/forest_stage_compose.py

# 5. 验证：app/src/main/assets/visual/ 下应有 6 个 webp
ls -la app/src/main/assets/visual/
```

> 脚本使用 host-managed auth；不读不写任何 API Key / token。

## 10. 生成服务的使用条款依据

本任务调用 `connector__matrix__generate_image`（mcode-tools 通过阿里云 OSS 上传并返回短时下载链接）。生成内容**仅作为本项目自有视觉素材使用**：

- **不**对外发布到公共 URL（assets/visual/ 在 Android APK 内，不联网）；
- **不**声明为 CC0 / 公有领域（`ASSETS.md` / `docs/visual-assets-handoff.md` / `assets/` 注释中**明确**AI 生成，**不**移除 AI 来源标注）；
- 生成模型的实际条款由 mcode-tools / 平台侧约束；本仓库侧承担"自有项目内使用、不转授"的责任。

**不建议**把本批素材直接发布到 CC0 仓库或转售。如需明确授权链，请联系 mcode-tools 提供方获取书面许可。
