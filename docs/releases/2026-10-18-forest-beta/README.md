# 森林双模式阶段测试版 · build-176-aaa789b

已发布：[GitHub Release](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-176-aaa789b) · [直接下载APK](https://github.com/skydream9527-ctrl/sense-walk/releases/download/build-176-aaa789b/app-debug.apk)。Android8.0及以上，Debug测试包；无需本地开发环境。

冻结源码 `aaa789b3afd789d121eb6f0c96189fe9835d3e3c`；云端run39189446098实际312项JUnit通过（0失败/错误/跳过），lint/debug构建/release manifest guard及预发布均成功。本轮实际下载APK与源码ZIP，两者完整性及SHA256匹配GitHub digest，源码ZIP内commit与关键源码匹配冻结Git；没有进行本轮真机安装或模拟器走查，设备项目仍Pending。

| 文件 | 字节数 | SHA256 |
| --- | --- | --- |
| app-debug.apk | 20277802 | cbe827bfff555939871e94e0b785bd89ac2780275d8a1c5fe81320fdc3c40a67 |
| sensewalk-source-aaa789b.zip | 215887996 | 1082b4355085fb2283990c64ef54d0c05817e5a2d9143ec717120579a7a66dd0 |

开放森林800m虚走/实走、正式光效、地形与恢复；雨林底座仅内部，不开放未完成正式图/声景。不是四景MVP验收完成。App内版本仍0.1.0-week1，反馈用Release tag辨认。

先按 [TESTING](TESTING.md) 安装/快速检查，再做完整800m/实走锁屏等；[已知问题](KNOWN-ISSUES.md)、[反馈模板](FEEDBACK.md)、[机器清单](release-manifest.json)。本轮APK与上轮build153实际证书指纹不同，覆盖安装可能被系统拒绝；若需卸载重装，会清本地设置/会话，先记录数据。源码完整ZIP约216MB，APK约20.3MB，安装只需APK。

APK/源码ZIP固定于上方commit；本轮后续文档PR更新提示词/收口说明，另附stage-closeout-docs.zip与Markdown，不重新打包假称源码ZIP含这些新文档。后续确认缺陷由独立复验后出新tag，不覆盖本包二进制。
