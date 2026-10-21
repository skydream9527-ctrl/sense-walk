# 2026-10-21 阶段收口实核

本报告是bootstrap/发布核查，不代替各任务作者或独立QA交付。代码基线main `2e6f266aaf8f0e3aed3e47b4388cc84bf82ff68d`，本次文档维护不改生产代码/素材/业务CI，不代写作者state。用户要求立即收尾并交安装包，后续只向ZCode、MiniMax Code、Antigravity转发提示词。

## 核准的进展

- PR36的SW019（业务a666b76793a77039df9e435d7877bb6fd55a4aec，交付5611ac7801d6f143bd02b3311d2ee0d3263440c0）已独立批准并集成；源码确认组合期同步解码与实走runBlocking已移除，新增32MiB位图LRU和single-flight、场景缓存与绘制阶段读取。没有设备前后可分辨性能收益，不能写成实测提帧。
- PR34的SW021设计accepted：业务28ef82c7f1e28eb4c48c98843d9bdc6a09959341、spec SHA256 86f8a19f39a481dfa21f74e543c10ecd96f05f2747d563a3da4936caf0b08d90；34项文件哈希实际复算一致。平铺设计没有入app，SW022 ready、SW023 queued。
- PR33的SW024协调交付accepted：已有H2缺证修正与回归入口；提示同步可读画面、instrumentation运行和设备性能仍Pending。不能把该任务accepted说成未来UI代码已验收。
- SW020 ready、SW025 queued，尚无实际交付；不把步长设置/操作安全区/新触感/可见构建身份写进本包。
- PR35仍OPEN，SW006 R2保持rework，未入main/未入生产；本轮不合并候选或开放雨林。

## 云端与二进制

主干run [39558848666](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/39558848666)与实际发布run [39561811899](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/39561811899)均成功。分别下载原JUnit XML，各31份、329 tests、0 failure/error/skipped，见[main-tests](main-tests.json)/[release-tests](release-tests.json)与两组原XML。源码/发布guard通过不等于本机或实体安装测试。

新包[build-224-2e6f266](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-224-2e6f266)。真实APK已下载核验：20,294,186B，SHA256 `eca9a854a1908643ff00123edd3a4a0e6fed97f2df43288ae6fd8d937f9e675a`，ZIP CRC通过，AndroidManifest/classes存在，五层正式森林WebP逐字匹配冻结源码。详见[apk-verification](apk-verification.json)。APK签名块证书指纹与build176不同，覆盖安装冲突为已确认工程限制；仅解析证书指纹，不冒充完整apksigner密码学验证。

源码ZIP以准确2e6f266命名；用同一commit与CI的TZ=UTC条件重建归档，其全文件SHA256/bytes与GitHub上传摘要完全相等，CRC及关键入口比对通过（未使用完整网络下载）。结果见[source-verification](source-verification.json)。新增本轮提示词/测试文档在之后的文档提交，不伪称已包含在冻结源码ZIP；Release另附本轮文档包并绑定文档业务SHA。

## PR35复核：不能照搬旧评审描述

只读观察PR35 tip `9bcfbaba356269ed43b6944d44c7fc1c531788d4`，实际最近业务`33dd824566e65cc68cbfeeeed42f416e1092793c`，在本机隔离导出中检查，原分支/作者文件未改。详见[source-audit](source-audit.json)。

1. H-SW006-R2的asset_manifest字段**存在**，artifacts字段**不存在**，并不是旧评审说的“缺asset_manifest且4个artifacts旧哈希”。handoff业务head仍511adf5，文字摘要还列后处理之前的旧大小/统计，与33dd824后的文件失步；这个真实问题保留，旧评审不符部分交QA追加修正。
2. manifest五层实际文件hash与bytes均匹配；vines_light为406320B，确实超过本轮明确400000B上限。旧预检按409600B容忍，所以预检成功不能作为十进制预算合格证据。
3. 直接查看110m与875m阶段图：前者薄雾几乎不可辨，后者空地呈左右对称亮斑。需要基于封存原图的0API处理和重新目检，不能凭统计通过自动approved。
4. 真实账本8 entries，任务8/8、项目总22；没有新增调用。隔离运行实际`SW006/r2/scripts/production_guard.py`：自检14/14、当前manifest 122/122，原始输出见[guard-selftest](guard-selftest.json)/[guard-manifest](guard-manifest.json)。第一次隔离导出因工具要求git根而退出；在该隔离副本初始化测试repo后重跑成功，不属于候选业务修复。
5. 旧评审写的`preflight/SW014/r3/scripts/production_guard.py`在该head不存在，实际脚本在SW006/r2。下一版handoff必须R3、manifest revision3、完整base/head/hash/实际检查；不能照旧建议让R3直接引用revision2 manifest，也不能覆盖R2记录。

## 设计审核SHA的追加纠正需求

SW021 review JSON/Markdown的delivery_head记录为`cf2f9aa893ca5ae57a939e4095c7fa326dfeb106`；Git对象/PR34实际交付为`cf2f9aa15fc7955ac8754b356dfccb3b5fd0f961`。业务head和批准spec/34文件哈希匹配，所以保留accepted，不因此要求重画设计；交QA追加correction，后续消费准确business/spec与真实交付头。

## 留待安装或后续开发

本轮没有真机、模拟器安装/声景听辨或计步/锁屏结果；只复用既有作者/QA的已注明设备证据，并实际核云端和下载产物。此前SW019的0m截图可见近黑与实走状态文案，但不是本轮新安装证据。低内存机、触觉、来电/耳机、真实步数、提示时序与800m真人体验保持Pending。

三方执行入口见[本轮计划](../../plans/2026-10-21/README.md)，最新安装测试说明见[发布目录](../../../releases/2026-10-21-forest-render-beta/README.md)。
