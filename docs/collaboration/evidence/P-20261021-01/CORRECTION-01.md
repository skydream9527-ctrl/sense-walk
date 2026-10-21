# CORRECTION-01 · 空数组/缺字段及UI测试范围澄清

2026-10-21，追加到本轮P20261021实核，不覆盖其已归档README/source-audit或任何历史review。适用PR35 tip9bcfbaba356269ed43b6944d44c7fc1c531788d4、产品源码2e6f266aaf8f0e3aed3e47b4388cc84bf82ff68d。

## artifacts为空，不是字段不存在

本轮README曾写“artifacts字段不存在”；实际H-SW006-R2.json含`"artifacts": []`，`asset_manifest`也存在。source-audit.json当时已经正确记录`artifacts_field_present: true`，因此错误在协调Markdown解释，不在原始JSON，也不归因MiniMax。

准确结论：artifacts数组为空，没有旧哈希条目，旧QA所谓“四项artifact mismatch”不适用于当前tip。最终业务head/摘要失步、406320B超限与mist/glade视觉问题仍独立成立，继续R3零API返工。当前计划/角色提示统一采用“数组为空”。

## UI检查尚不是可发现、实际操作App的测试

SW024的Python用例主要断言源码字符串、JSON和已存审计值；AndroidTest文件是object/runAll(context)领域检查集合，没有可发现的@Test/Runner调用入口。verifyTapToRevealMetersContract未操作UI，displayedInt由m1.toInt赋值后再比较同式，不证明点击显距。既有“7项UI入口”应限于草案/领域检查，实际UI覆盖与设备执行保持Pending。

后续由Antigravity在本人QA范围实现有价值、可执行的UI测试，依赖/业务Gradle由ZCode支持；原SW024协调accepted不改，不将新发现假称已修复。

## 设计内容与审核叙述的范围

SW02134文件hash与批准业务head匹配，accepted保留；夜径模拟800m与正式700m不一致、长屏表dp/px混用、误把App绘制派给SW022，后续消费必须按正式配置和所有权校核，不暗改批准spec。

SW019独立review中的scenes/index.json、脉冲圆/旅人徽章等叙述与实际源码不符；这不否定已实际存在的异步缓存和329云端结果，但QA需要追加更正，不再把相似项目叙述当本项目证据。

详尽能力与任务匹配见[AGENT-ASSESSMENT](../../plans/2026-10-21/AGENT-ASSESSMENT.md)。冻结build224/APK/源码及首版文档包不替换，本追加随新的评估附件保存。
