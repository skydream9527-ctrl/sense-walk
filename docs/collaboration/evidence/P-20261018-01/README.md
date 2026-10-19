# P-20261018-01 · 森林阶段收口与可安装包

客户端日期2026-10-18。用户明确要求先阶段收尾、GitHub打包并安装测试。本轮源码冻结 **aaa789b3afd789d121eb6f0c96189fe9835d3e3c**；在已附独立规划worktree/分支维护文档，未改共享作者checkout/index、生产源码、正式美术、旧审计或他人state。

## 交付范围与真实进展

| 项目 | 当前事实 | 阶段处理 |
| --- | --- | --- |
| 森林虚走/实走800m | 可靠性/地形R2/正式光效/快照恢复均独立accepted并集成 | 本次开放安装测试，真机结果仍待用户/QA |
| 雨林运行时SW016 | PR23合入b4d4000、PR26独立approved/accepted；新增9项领域测试，主线312项 | 底座已完成，不重复开发；生产rainforest.json仍仅test/resources，不开放 |
| 雨林素材SW006 | PR25 head d71d6278860c3551b545bd3b476e38c77096622a，business声明6ba654c；0API程序占位，未合入/未批准 | 不进森林包；草案交接/guard收尾后下一阶段正式制作 |
| 雨林声景 | 实际未获取/处理/听辨，test配置仍引用显式森林音频占位 | 阻塞雨林最终SW007，不能以底座accepted宣称声景完成 |
| Trae SW017 | main未见新交付，原state仍等待SW012旧结果 | 本轮优先森林App视觉收口，保留已有雨林稿，不推测外部工具本机是否开工 |
| 之前规划与纠错 | PR21已发布上轮规划；PR22追加delivery SHA与视觉Pending说明 | 已完成，无需再次离线导入或重复勘误 |

## 实际GitHub发布

已执行现有 `android.yml` workflow_dispatch，publish_release=true；run **39189446098**、build **176**、源码为上述精确main。Source、Test/lint/debug、release-manifest guard与GitHub prerelease全部success。Release：

[build-176-aaa789b](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-176-aaa789b)

APK/source文件与SHA、下载实核范围、安装测试/已知项/反馈模板见 [发布档案](../../../releases/2026-10-18-forest-beta/README.md)。本次不安装完整Android环境、不运行付费生图、不发布应用商店、不自己启动模拟器或冒称真机安装。后续文档main前进不改变APK绑定源码；源码ZIP保持冻结commit，新收口文件另作附页交付，不覆盖二进制。

## 实际测试与包核验

- 主线push run39188818031与本次发布run39189446098都已下载原始JUnit XML，各29份、**312项/0失败/0错误/0跳过**。前者见 [test-summary.json](test-summary.json)/[junit](junit)，后者见 [release-test-summary.json](release-test-summary.json)/[release-junit](release-junit)。不是作者local XML，也不是模型推演。
- APK已实际下载，大小20277802 bytes，实算SHA256 `cbe827bfff555939871e94e0b785bd89ac2780275d8a1c5fe81320fdc3c40a67` 匹配GitHub digest；ZIP完整、AndroidManifest.xml/classes.dex存在。证书指纹仅用于升级比较，不宣称执行了完整apksigner密码学校验。
- 源码ZIP实际完整下载，215887996 bytes，实算SHA256匹配GitHub digest、ZIP完整、git archive comment为冻结commit，关键源码字节匹配Git对象；结果归档发布清单。
- 本轮计划31项协议测试通过（30.887s）；具体命令与最终history/diff/HTML检查见 [planning-checks.json](planning-checks.json)。产品云端312与文档协议31分开，不能相加当设备覆盖。

## PR25更新：已经修过的问题不要重复派

本轮只读导出d71d627到本机临时目录，未改作者分支。当前manifest的file/checks已是仓库根完整相对路径；handoff evidence无通配符；所有列入artifacts的真实hash匹配。旧R-SW006R1远端观察针对更早eac92e4，不能继续把旧路径问题当当前红灯。

当前run **39188385684** 的结构/哈希/历史检查已通过，失败在 `tools/qa/test_collaboration.py` 的隔离用例：

- `test_design_accepted_with_exact_independent_hashes_is_valid`：fixture替换SW012设计，与新真实SW006引用的spec hash冲突。
- `test_design_without_manifest_is_rejected`：真实SW006关系指向测试替换handoff的缺字段，抛 `KeyError: design_manifest`，应成为正常拒绝而非crash。
- 31用例结果 **1failure/1error**。准确失败摘录见 [pr25-current-ci.txt](pr25-current-ci.txt)，查询时PR状态/完整rollup见 [pr25.json](pr25.json)。

由Antigravity隔离测试关系并保留缺manifest/严格批准/hash拒绝，不skip或禁检查，不让MiniMax改QA。素材仍是0API占位，CI修复不自动意味着可生产入包；R2需新business head/准确范围。registry改rework并保存observed_delivery，未导入的handoff/review JSON不伪造成本地latest指针，原Markdown观察保留并后续追加纠正。

## 本轮收尾分工

- ZCode：新ready SW018具体安装/森林双模式缺陷收尾；无已复现问题可交0源码核查，不重复SW016或造重构/空测试。
- MiniMax：SW006草案/guard/交接收尾，不将占位混入森林阶段包；本阶段不新增付费调用，原后续总8次授权不重置/不重复索要。
- Trae：SW017先当前森林实际图/清单/必要参照和具体问题；设计模拟不冒充App/设备，保留已有雨林草稿。
- Antigravity：常驻独立QA/现成包核验/用户反馈分级、提示出现→约3s消失/恢复不重复补证、PR25测试隔离、必要patch新包。

完整执行提示词在roles四文件；范围/退出条件见 [STAGE-CLOSEOUT](../../STAGE-CLOSEOUT.md) 和 [D011](../../decisions/D-011-stage-closeout-forest-beta.md)。没有自动发消息、调度器或重复协调启动任务。源commit可打包/下载和用户真机体验通过分开，阶段状态released_for_installation_test，未宣称M1/M2或四景MVP最终验收。
