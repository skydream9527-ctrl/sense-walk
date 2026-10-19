# 本阶段收口：森林双模式安装测试版

阶段ID S-20261018-forest-beta；客户端日期2026-10-18；冻结源码 `aaa789b3afd789d121eb6f0c96189fe9835d3e3c`。目标：先将现有已批准森林功能交给用户安装测试，收回真实问题；后续再推进雨林完整接入。不是四景MVP/真机验收完成声明。

## 安装包与范围

本轮Actions run39189446098（build176），Release [build-176-aaa789b](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-176-aaa789b)；构建/校验与文件摘要见 [阶段发布档案](../releases/2026-10-18-forest-beta/README.md)。发布状态以档案与实际Release为准，文档PR后的新main不改变此包绑定commit。

开放森林800m虚走/实走、正式光效、地形/站稳/轻跳、暂停/放弃/完成与被动中断恢复；保留真实计步与锁屏的待设备验证项。SW016已集成的雨林底座不开放，SW006仍占位待返工、真实雨林声景缺失；SW007/城市/沙漠不为凑包强行启用。

## 当前四方动作

| 角色 | 本阶段收尾 | 交付/退出 |
| --- | --- | --- |
| ZCode | ready SW018：安装/启动/森林双模式与具体阻断缺陷核查 | 无缺陷交0源码改动与Pending；有复现才最小patch/测试/新包，不重做accepted SW016 |
| MiniMax | rework SW006：消费最新PR25、草案/guard/交接收尾 | 路径/通配符最新已修；当前QA fixture红灯交Antigravity。保留R1/交R2，不把占位入森林包，不新增本轮API调用 |
| Trae Design | ready SW017：先森林阶段App视觉走查/参照与问题标注 | 实际截图/设计模拟分开，先交必要清单，不重绘生产美术；保留已有雨林工作 |
| Antigravity | 持续独立QA/发布档案、用户反馈分级与必要补丁复验 | 补提示时序/设备矩阵，修PR25测试隔离，按准确新head复审；不重复发布同包/重复启动任务 |

## 收口条件与后续

当前可交付条件：主线云端test/lint/debug/release-manifest guard成功、APK/source可下载且哈希/源commit准确、范围/已知项/安装测试/反馈模板齐。用户安装与真机结果未到时保留Pending，阶段状态released_for_installation_test。

收到P0/P1可复现问题后由ZCode最小修复→QA独立复验→新tag包，既有包二进制不替换。阶段问题有结论后继续SW006正式雨林候选/生产保护和真实声景→SW007双模式组合→逐景城市/沙漠。原总8次素材尝试授权不重置，不重复请求已给授权；当前收尾不增加付费生成。无需完善本地Android环境，所有角色独立worktree/精确handoff，用户转发文件提示词不等于已自动派发。
