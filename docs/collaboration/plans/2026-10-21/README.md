# 2026-10-21 阶段收口与三方分工

用户本轮要求：检查进展、先收尾并在GitHub交安装包，后续交ZCode、MiniMax Code、Antigravity继续开发。本轮不新增设计任务，消费Trae已经获批的SW021；不转移或改写设计所有权。此文件安排不表示外部agent已被自动通知。

## 本次包的范围

冻结源码`2e6f266aaf8f0e3aed3e47b4388cc84bf82ff68d`，即SW019/021独立审核已入主干的时点。实际APK/源码/哈希/测试结果见[发布档案](../../../releases/2026-10-21-forest-render-beta/README.md)，检查证据见[本轮实核](../../evidence/P-20261021-01/README.md)。

本次是**森林800m双模式渲染加载改进测试包**：增加异步图层读取/解码、32MiB有界LRU与并发请求去重、场景配置共享缓存、移除实走UI阻塞等待、高频绘制状态读取下沉。仍使用既有五层正式图、现有地形与恢复。云端329项JVM测试，设备帧率/耗电改善没有实测结论。

SW020安全区/步长/每局触感、SW025版本追溯、SW022平铺候选、SW023视觉接线尚未交付，不在包内。SW021设计accepted不等于素材或UI已入包；雨林R2仍rework，不能进入本包或开放雨林。0m黑幕、800m门禁、comfort_v1、计距与恢复语义保持。

2026-10-20计划的第一批原本等SW019/020/025；**本轮按用户直接要求先缩小为已验收SW019范围，立即交可安装基准**，不把后两项写成完成，也不因它们未完成继续拖延现有改进包。后续代码通过后再出新tag，旧包不覆盖。

## 三方下一步

| 角色 | 先做 | 后续与边界 |
| --- | --- | --- |
| ZCode | 消费SW019 accepted，领取ready SW020；收到本次安装反馈时先复现、修阻断 | SW020获批后SW025；SW023等SW020与SW022获批。各任务独立PR/handoff，不重做SW019，不强开雨林 |
| MiniMax Code | 优先ready SW022，按SW021精确批准spec制作森林三层平铺候选，0新增付费 | SW006另分支做R3零API返工，8/8账本不重置；两批候选分开，不让雨林阻断森林，不改Trae源稿或生产assets |
| Antigravity | 核对本次包与安装反馈；独立审核后续SW020/022/025 | 消费SW024 accepted，不重复造基准任务；追加修正本轮指出的评审路径/SHA/字段事实，提示同步画面与真机保持Pending |

每个角色使用独立checkout/worktree；不要为了同步文件在共享checkout reset/切分支。本人state本人维护，中心registry/BOARD由QA顺序维护。作者不能自判accepted，功能/素材head变化重新审核。

## MiniMax的准确消费要求

森林SW022引用SW021 spec `86f8a19f39a481dfa21f74e543c10ecd96f05f2747d563a3da4936caf0b08d90`，只制作tree_outline/tree_trunks/leaf_path；原light_shows与clearing复用。0新付费，真实源尺寸/alpha/hash、三底/三次拼接/多偏移/六阶段/三比例与五层总预算交齐。每层≤400000B，不用409600B冒十进制上限。设计里的运行时代码建议只作需求：SW022不写app，重复绘制由ZCode在SW023实现。

雨林SW006 R2当前`asset_manifest`字段**已经存在**、`artifacts`没有列旧哈希数组；不要照旧评审重复“补缺失字段/四个artifact mismatch”。真实问题是handoff业务head及文字/尺寸摘要未随33dd824后处理同步，vines_light 406320B超限，薄雾/空地视觉须依据原图重验。新交H-SW006-R3 + **r3/manifest.json且revision=3**，引用最终业务SHA和真实哈希。不能把R3 handoff直接指向revision=2的R2 manifest，不能原地覆盖旧交付。重编码/透明处理只用封存原图；账本8次、项目累计22保留，不再调用生图。

## QA收口条件

- 本轮源/云端/安装包验证与真实设备验证分开记；329测试不等于UI instrumentation或真机通过，代码改造不等于已证明提帧。
- 提示缺证按SW024已交方法补237m首次站稳可读画面→约3s消失及同局不重复，缺设备继续Pending。不要以旧H2文件名当闭环。
- SW021业务head/spec/34文件哈希匹配已复核，历史approved保留；其review的delivery_head写错，应追加correction，实际Trae交付head是`cf2f9aa15fc7955ac8754b356dfccb3b5fd0f961`。
- SW006旧review的生产guard路径不存在，正确路径在`design/assets/rainforest/candidates/SW-006/r2/scripts/production_guard.py`，实际运行结果见本轮证据；修正不能覆盖旧review。
- 后续发布绑定独立批准的实际head、运行号、APK/source SHA、证书指纹与测试范围。版本/签名仍旧机制，本次反馈用Release tag；覆盖安装冲突与卸载清数据必须说明，不生成或替换密钥。

收到反馈先记build/手机/系统/步骤/发生米数/预期与实际、截图/录像，分配owner并复测。严重问题先修，非阻断视觉与雨林继续原队列。三份可转发文本见[PROMPTS](PROMPTS.md)，稳定入口仍在roles目录。
