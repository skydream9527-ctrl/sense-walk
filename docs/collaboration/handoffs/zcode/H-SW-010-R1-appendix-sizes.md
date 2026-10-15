# H-SW-010-R1 附录 · 长屏/小屏/停走/光效意图补充证据

对已推送 [H-SW-010-R1.md](H-SW-010-R1.md) 的**追加证据**（不改原文；按 D-005，
handoff_ready 阶段可追加审核要求的证据）。

## 本轮补充（第四轮，响应 P-20261014-02 的验收要求）

模拟器 `wm size` 覆盖两种屏幕比例，冒烟注入驱动真实渲染链走完整程：

| 证据 | 内容 |
| --- | --- |
| `sizes/1080x2880-{100m,630m,785m}.png` | 长屏（2.67:1）三阶段，cover 裁切正确、无瑕疵 |
| `sizes/1080x2880-freeze-{a,b}.png` | 长屏停走冻结：8s 间隔画面主体逐像素一致（仅状态栏 266px，y<80） |
| `sizes/720x1280-{100m,630m,785m}.png` | 小屏（16:9）三阶段，缩放正常 |
| `sizes/720x1280-freeze-{a,b}.png` | 小屏停走冻结：8s 间隔画面主体逐像素一致（仅状态栏 87px，y<47） |
| `sizes/intent-lightshows-2x.png` | 785m 上部斜光带 2 倍放大（光效意图判断材料） |
| `sizes/intent-clearing-2x.png` | 785m clearing 主光斑 2 倍放大 |
| `sizes/intent-maxdiff-window-3x.png` | 630m→785m 差异最大窗口 3 倍放大：位于 (720,1060)，与 clearing 光斑推算中心 (828,1209) 吻合——揭示增量位置正确、集中于目标层，幅度弱与 R1 alpha 分析一致 |

默认尺寸（1080x2400）的六阶段与停走证据见 R1 原文（`stages/`），仍有效：
分支同步 main（e7ab092）未触及 `app/`（`git diff a1df0e2..HEAD -- app/` 为空），
APK 内容等价。

## 结论不变

接线/裁切/冻结/相位触发在各比例下均按预期；光效强度弱的问题仍待独立裁定，
本附录不改变 R1 的请求与 Pending。

---

## 同步说明（2026-10-15，收口轮）

按 P-20261015-01/R-SW-010-R1 approved 后的集成要求，分支已 merge 最新 main
（`7c2a3b7`），merge head `586e6ad`：

- 冲突仅 `state/zcode.json`：以 main（SW-004 交付后）为基础人工合并，
  current_task 指回 SW-010 收口，deliveries 索引保留 SW-001（accepted）、
  SW-004（accepted，集成 814fc78）、SW-010（approved）全部记录；
- `app/` 业务内容与获准集成一致：两 webp sha256 仍为
  `1dcda4f7…` / `1973a1f5…`（R-SW-010-R1 核对的值），forest.json 参数未动；
- 无业务变化，不新开 revision；本 head 的 CI 供 QA 复核后集成。
