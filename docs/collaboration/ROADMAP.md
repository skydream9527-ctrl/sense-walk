# 后续协同路线

2026-10-15核查基准main=6104e3d。可靠性/快照、森林设计、素材预检R3已accepted；SW-005/SW-012已ready，新增SW-015真实规格联调ready。SW-010已approved但尚未集成，build-109不含两层正式接图。详见 [本轮报告](evidence/P-20261015-01/README.md)。不按任务数或CI绿推算M1/M2/MVP验收百分比。

| 阶段 | 任务与负责者 | 当前状态/前置 | 退出条件 |
| --- | --- | --- | --- |
| 已完成代码阶段 | SW-001可靠性、SW-004快照 / ZCode+QA | accepted/已合入 | 保留真机计步/锁屏/跨boot恢复Pending；不重复初版 |
| 已完成参考/工具阶段 | SW-011森林设计 / Trae，SW-014 R3 / MiniMax | accepted/已合入 | 设计53文件共享、工具原18fixture/6探针通过；参考不自动入包 |
| 当前收口 | SW-010森林正式接图 / ZCode+Antigravity | approved，PR #3作者state冲突 | 同步/复核新head/CI后集成并交含恢复+接图的组合包 |
| 当前开发主线 | SW-005站稳/自动轻跳 / ZCode+QA | ready，SW-004 accepted | .72阈值、3m接近、1.2s站稳不刷距，恢复/reduceMotion/800m回归 |
| 当前视觉主线 | SW-012雨林设计 / Trae+QA | ready，SW-011 accepted | 900m湿绿阔叶/雾/藤蔓、canonical字段、阶段/比例/局部/逐层prompt，冻结供下游消费 |
| 当前素材工具主线 | SW-015真实规格预检联调 / MiniMax+QA | ready，SW-011/SW-014 accepted | 真实id/type五层解析、空/冲突规格和空候选拒绝，0 API，独立批准 |
| 下一批素材 | SW-006雨林候选 / MiniMax+QA | queued，另等SW-012/SW-015 accepted | 精确design_ref/新批准预检入口、实际候选/hash/验图，原总8次尝试 |
| 下一批应用 | SW-007雨林双模式 / ZCode+QA | queued，等SW-005/SW-006 | 900m配置/专属真实声景/素材、复用门禁/恢复/服务，双模式回归 |
| 后续扩景 | SW-008城市/沙漠 / 四角色 | queued，等SW-007/SW-010 | 激活前拆各景设计→候选→接入子任务，逐景独立审核 |
| 持续与最终 | SW-009实体/真人内测 / Antigravity组织 | 可提前核查设备项，最终依赖SW-008 | 计步/锁屏/耳机来电/物理重启/真机视觉，5–8人内测与严重问题关闭 |

SW-003/SW-013协调任务已accepted，Antigravity持续维护 [验收队列](queues/antigravity.md)，不重复创建启动任务。三个可并行交付是SW-005、SW-012、SW-015；SW-010先顺序处理作者分支同步和QA集成。各角色state滞后由本人更新，中心登记和正式review由协调者维护。

当前测试包 [build-109-6104e3d](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-109-6104e3d) 绑定274项JVM/lint/debug build；原始XML与APK hash已核查。接图合入后再发布新的组合main版本，后续每次功能集成按必要回归出包。设备/真人缺失保留Pending，不阻塞独立开发，也不宣称最终验收完成。无需在本地完善Android环境。
