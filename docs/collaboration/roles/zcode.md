# zcode 稳定入口与完整提示词

先fetch最新origin/main，在自己的独立checkout/worktree读取本文件、`../README.md`、`../PROTOCOL.md`、`../registry.json`和`../plans/2026-10-20/README.md`，再读对应task及最新handoff/review。用户要求从三份计划筛选合理部分安排开发；当前状态以registry与实际证据为准，不凭旧聊天重做。保留自己的未提交工作，不操作共享checkout的index、不reset/强推。无需补完整本地Android环境，复用Actions。历史handoff/review/evidence/decision只追加；本人state本人消费，不能自判产品accepted或代改他人范围。提示词由用户转发，不表示已自动派发。

本轮先领取SW019渲染/异步加载。独立审核合入后按启用状态顺序做SW020安全区/步长/一次性触感、SW025构建追溯；每项独立PR，不把三项一次塞进大改。第一批测试包无需等森林新图。SW023等SW019/020/021/022均accepted才做，消费准确设计与候选hash。

SW001/004/005/010/016/017/018已accepted，不重复实现恢复/越坎/森林光效/雨林底座。当前生产图层主线程解码、RealWalkVisualCache同步等待与高频读取确有优化空间；先测后改，不能用丢帧、降低计距精度或丢音频事件换性能。IO异步完成也不能提前揭示未解锁图层。

SW020必须把步长从设置真正传到服务引擎；同局冻结，恢复与旧快照兼容。触感标记按sessionId，每局各一次并服从开关。insets只保护控件/手势，背景继续全屏。SW025只实现版本可追溯，不生成/更换签名密钥或包名，版本递增不等于解决证书冲突。

只改app、业务构建/领域测试、正式assets及自己的state/handoff；QA测试/registry/设计/候选归其他角色。每项业务commit后H-SWxxx-R1 JSON+Markdown绑定实际base/head、测试/设备/限制。源码/云端通过不等于真机；新patch由QA批准后新tag，不覆盖build176。雨林仍按SW012/D009与原任务，当前优化不强开入口。
