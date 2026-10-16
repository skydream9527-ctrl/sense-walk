# D-009 · 冻结雨林设计规格与五层参数

日期：2026-10-15；决策角色：antigravity；依据：`docs/collaboration/reviews/R-SW-012-R1.md`、`design/01-scenes-terrain/rainforest.md`、`DEVELOPMENT.md` §7.1/§7.7。

## 背景与事实

Trae Design 在 SW-012 R1（PR #15，merge `bb05b035f1109d974790a9e576a77a539c2e43ed`）中交付了完整雨林 900m 视觉设计包，其中 `design-spec.json` 的五层 layer ID 与 parallax 标记为 `proposed`，等待 Antigravity 审稿冻结。
经独立审查（`R-SW-012-R1`），该设计包 53 文件哈希吻合、无棋盘/硬边、六阶段时间轴对齐、运行时逐像素裁切通过且冷湿绿雨林身份与森林明确可分。

为了避免改动 Trae 原交付手稿及 `design-spec.json` 字节而导致 SHA-256 校验循环失效，依据《文件交接协议》第 53 条与 D-008 约定：**由 Antigravity 通过独立评审报告与本决策记录冻结 canonical 规格，绑定精确 spec 哈希**。

## 冻结决策

### 1. 规范哈希绑定
- 雨林设计规格文件：`design/05-visual-design/SW-012/r1/design-spec.json`
- 精确 SHA-256：`643e77b1ba7574c9b013dce485fde2797816096181feda91c2fa7920d042c320`
- 清单文件：`design/05-visual-design/SW-012/r1/design-manifest.json`
- 精确 SHA-256：`8cbbdd8d374ace50e71756a410482596592d0e8c61d595207521c841399872ac`

### 2. 五层 Canonical 参数冻结
以下五层 ID、图层类型、视差比例、解锁与淡入参数确立为雨林场景正式规范，不再处于 `proposed` 状态：

| 层 ID | 类型 | 视差比 | 解锁 (atMeters) | 目标透明度 | 淡入 (fadeMeters) | 达成米数 | 画布规格 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mist` | overlay | 0.0 | 90m | 0.55 | 20m | 110m | 1080×1920 RGBA |
| `trunks_canopy` | parallax | 0.30 | 270m | 0.85 | 25m | 295m | 1080×1920 RGBA |
| `vines_light` | parallax | 0.60 | 450m | 1.00 | 25m | 475m | 1080×1920 RGBA |
| `distant_glow` | overlay | 0.0 | 675m | 0.85 | 25m | 700m | 1080×1920 RGBA |
| `glade` | overlay | 0.0 | 855m | 0.90 | 20m | 875m | 1080×1920 RGBA |

- 总目标路程：`900m`（875m 完成全显，900m 保持景色完整，不切屏）。
- 旅人锚点：$x=0.34$, $y=0.865$（沿用森林归一化坐标系，程序绘制，素材不画人）。
- 触控保护区：下方 45%（$y \ge 0.55$）低对比湿雾留白。
- 视差两层（`trunks_canopy`, `vines_light`）当前 `tileable=false`，按高度铺满左对齐，在右侧溢出宽内横移。

### 3. 下游约束与门禁生效
1. **SW-015 消费约束**：MiniMax 在 SW-015 联调解析时，必须严格支持上述 5 层 canonical ID、overlay/parallax 类型判定，并拒绝不匹配上述规范的脏数据。
2. **SW-006 激活门禁**：SW-012 获 `accepted` 不可单独解锁 SW-006。必须在 SW-015 亦通过验收集成后，SW-006 始得激活为 `ready`。
3. **制作引用绑定**：SW-006 候选素材清单中的 `design_ref` 必须指向本决策与 `design-spec.json` 的确切哈希 `643e77b1...`。若未来 Trae 提交 R2 发生实质参数变更，须重新经过独立审稿并生成新决策记录。
