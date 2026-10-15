# Antigravity 常驻验收队列

2026-10-15依据 [P-20261015-01](../evidence/P-20261015-01/README.md)。先fetch最新main/实际交付分支；以下是定位快照，head变化需比较差异。已accepted的SW-001/SW-004/SW-011/SW-014不再按旧入口重做。

| 顺序 | 当前入口 | 实际动作/退出条件 |
| --- | --- | --- |
| 1 / SW-010接图集成 | [PR #3](https://github.com/skydream9527-ctrl/sense-walk/pull/3)，head `2a7121677ee7579da1955dd0352631ec0525a566`；R-SW-010-R1已approved，业务head `a1df0e295b7c95d6212b8c65d597087a9458d906` | 让ZCode在本人分支合main并保留SW-004等state信息，当前冲突仅该文件。复核新head相对main的实际delta/原批准hash/CI后集成，记merge与accepted；业务差异需新revision/复验，不代写作者state |
| 随到审 / SW-015 | MiniMax ready的新零API真实规格联调，前置SW-011/SW-014均accepted | 真实Trae id/type规格提取五层；空/重复/冲突spec和空/缺层候选拒绝，严格批准/账本/预算保护回归，测试自动断言；写独立review并集成 |
| 随到审 / SW-012 | Trae ready的雨林900m设计 | 全manifest/source/spec/prompt/hash、解锁与fade完成点、三比例/三底局部、真实输出/透明/拼接；冻结canonical id/type及下游映射，设计批准不当作素材/Android完成 |
| 随到审 / SW-005 | ZCode ready的地形/站稳/轻跳 | 实际Kotlin/调用链和app证据，站稳不刷距、反复同坎、暂停/后台/取消/恢复/迟到、reduceMotion、800m；回归SW-004快照 |
| 激活门禁 / SW-006 | queued，仍等SW-012与SW-015 | 两者accepted后才ready，候选使用具体批准design_ref和新批准预检入口、原总8次尝试；不能凭临时fixture批准或SW-014原通过跳过联调 |

已完成：SW-001集成1e23881；SW-004集成814fc78；SW-011集成256d7e3；SW-014集成3ea89c1。build-109-6104e3d已发布，274项JVM/lint/build成功，APK SHA256见本轮报告；不是“准备发布”，也不含未合入SW-010。接图集成后再交组合CI/Release，记录准确commit/APK hash及Pending。

本轮bootstrap只做观察/派工，不新批产品；SW-015发现见可复现输入输出。SW-014原18fixture严格模式1正/17负与6回归探针重跑吻合，不能推导为所有真实设计schema已经兼容。不要在队列使用“无懈可击”等无范围结论。旧SW-011 review Markdown的merge SHA笔误用新correction追加，registry/真实PR merge为准，不改历史。

Python规格模型、真实JVM测试、作者模拟器证据读取、本人模拟器/physical-device/真人分别记录；模型不能代表执行Kotlin/Service/Android。真机/真人可提前执行，缺设备保留Pending，不阻塞独立代码阶段集成、不宣称M1/M2/MVP完成。各角色本人消费批准后更新state，协调者不代写。

顺序写review→依保护集成→CI/准确merge登记→accepted/render BOARD；没有新交付一次报告待哪个文件，不无限轮询。保持SW-003/SW-013历史协调结论，不重复建启动任务、不自动向外部工具发消息。
