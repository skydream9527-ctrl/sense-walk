SW-010 R1 补充证据（2026-10-14 第四轮，响应对长屏/小屏/阶段/停走/光效意图的验收要求）

设备：emulator-5554（api36_test），wm size 覆盖两种比例；冒烟注入驱动真实渲染链。
APK：合并 main(e7ab092) 后的分支构建；git diff a1df0e2..HEAD -- app/ 为空，
即与首个交付 head 的 APK 内容等价（Gradle up-to-date 未重打包，字节级同源）。

[长屏 1080x2880（2.67:1 覆盖）]
- 1080x2880-100m.png / -630m.png / -785m.png：三阶段
- cover 裁切正确、无棋盘格/接缝；更多纵向内容正常渲染
- -freeze-a/b：8 秒间隔，画面主体逐像素一致（差异仅状态栏 266px，y<80）

[小屏 720x1280（16:9）]
- 720x1280-100m.png / -630m.png / -785m.png：三阶段
- 缩放正常、无裁切异常
- -freeze-a/b：8 秒间隔，画面主体逐像素一致（差异仅状态栏 87px，y<47）

[光效意图裁切（供独立判断「安静空地」意图是否达成）]
- intent-lightshows-2x.png：785m 上部斜光带 2 倍放大
- intent-clearing-2x.png：785m clearing 主光斑（图内 cx0.68W,cy0.42H 经 cover 映射）2 倍放大
- intent-maxdiff-window-3x.png：630m vs 785m 差异最大 300x300 窗口 3 倍放大，
  窗口位于 (720,1060)，与 clearing 光斑推算中心 (828,1209) 吻合——
  揭示增量位置正确、集中于 clearing 层，幅度弱（与前轮 alpha 分析一致）
