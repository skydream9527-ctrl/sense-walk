# 森林800m双模式 · 渲染加载改进测试版

[下载app-debug.apk（约20.3MB）](https://github.com/skydream9527-ctrl/sense-walk/releases/download/build-224-2e6f266/app-debug.apk) · [GitHub Release](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-224-2e6f266) · [测试步骤](TESTING.md) · [已知项](KNOWN-ISSUES.md) · [反馈模板](FEEDBACK.md)

- Release：`build-224-2e6f266`，GitHub测试预发布，Android8.0+。
- 冻结源码：`2e6f266aaf8f0e3aed3e47b4388cc84bf82ff68d`。
- 发布run：[39561811899](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/39561811899)，云端329项JVM/0失败、lint/debug构建及release manifest guard成功。
- APK SHA256：`eca9a854a1908643ff00123edd3a4a0e6fed97f2df43288ae6fd8d937f9e675a`；大小20,294,186B。
- 源码ZIP SHA256：`fc42d1c08d1ea36c2dae000380575d764dbd4a9149c07ca95125a2fd69e1f1d0`；大小261,844,977B。安装只需要APK。

本次新增SW019异步图层解码/缓存、场景缓存和绘制状态读取优化；森林虚走/实走、正式五层、越坎和被动恢复继续沿用。真机帧率/耗电改善还没有可分辨测量，不承诺提帧百分比。

没有SW020步长/触感/安全区、SW025App可见构建身份、SW022/023平铺与UI精修，雨林保持未开放。Trae批准设计不是已经入包的素材。源ZIP是冻结commit的真实归档；本轮新增收口/三份提示词/测试文档在后续文档提交，Release文档附件另外保存，不能混称该ZIP源码已包含。

本次签名证书与build176**实际不同**；装过176时覆盖安装会发生证书冲突。先保存需要的记录，卸载旧包后再装；卸载清除本地进度/设置。App内版本仍0.1.0-week1/versionCode1，反馈用Release tag识别，不以版本文字判断新旧。

实际下载与证据见[本轮核查](../../collaboration/evidence/P-20261021-01/README.md)、[发布元数据](release-manifest.json)。后续三方任务与提示词见[收口规划](../../collaboration/plans/2026-10-21/README.md)。旧build176仍保留，新修复另发新tag。
