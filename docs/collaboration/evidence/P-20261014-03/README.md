# 第四轮进展核查与分工

日期：2026-10-14（America/Los_Angeles）；基准 main `e7ab092ad9967d9e6d97e212d777ac3546e4525e`。Codex负责bootstrap核查/计划维护，本记录不授予产品/素材/设计approved，也不代表外部工具正在运行。精确观察见 [source-snapshot.json](source-snapshot.json)。

## 这轮实际新增

| 角色 | 已核实变化 | 当前缺口 |
| --- | --- | --- |
| ZCode SW-001 | PR #1同步main并解决state冲突，保留两项deliveries；标题/描述已更新R2，base SHA笔误用新correction追加。最新PR合并checkout249项通过 | Antigravity尚未发布R-SW-001-R2；未合入，SW-004仍queued |
| ZCode SW-010 | PR #3同步main、解决state冲突、补PR URL纠正；新增1080×2880/720×1280三阶段、停走与光效意图截图。最新PR合并checkout217项通过 | 独立应用/视觉review及集成；与SW-001组合版本未测 |
| MiniMax SW-014 | R2已推送 `codex/minimax/SW-014-r2`，业务 `6e683e2087574df51efd43d8dea73270d321f5aa`，交付 `bda0b74d53791c09a4c9b7a2858b9c32321bc862`；根定位/真实解码已修，1正例+12负例按声明通过/拒绝 | 无PR、无独立review；新实测R2-01～05仍误放行，下一轮R3 |
| Antigravity | 新本机队列worktree存在，HEAD仍为e7ab092，未观察到新增tracked改动/提交 | 没有新的R2/接图/预检正式review。不能据worktree存在宣称已开始或已完成审核 |
| Trae SW-011 | 原43份草稿本轮hash/bytes仍全部匹配 | HEAD仍5a129d4，草稿未提交/未推送/无handoff；SW-012仍queued |

两个工作PR当前均 **MERGEABLE/CLEAN**；上一轮“冲突待解决”已不适用。精确PR head：[#1](https://github.com/skydream9527-ctrl/sense-walk/pull/1) `d11873f3d5553fda872dd18f4483ca1e1b11223a`；[#3](https://github.com/skydream9527-ctrl/sense-walk/pull/3) `393f22570a541118d80e7a50c6860c3b57f2fd49`。与原业务head相比`app/`均无新增差异；docs/state/维护差异仍要纳入完整审核。

main应用功能没有因这些未合入分支而更新，两层光效仍程序降级。最新测试Release仍是[build-41-8ef1446](https://github.com/skydream9527-ctrl/sense-walk/releases/tag/build-41-8ef1446)，不含两工作PR；真机计步、锁屏、耳机/来电与真人内测仍Pending。

## 本轮实测

下载并重新计数了最新PR合并checkout原始JUnit：SW-001 [run 38554272476](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38554272476)，[22份XML/249项](../P-20261014-03-SW-001/test-summary.json)；SW-010 [run 38558587815](https://github.com/skydream9527-ctrl/sense-walk/actions/runs/38558587815)，[19份XML/217项](../P-20261014-03-SW-010/test-summary.json)。失败/错误/跳过均0，相应lint/build成功。现在SW-010也已有PR合并checkout CI，不能再只称push分支绿；但两个PR尚未组合，不能合计测试数或据此自标accepted。

读取作者长屏/小屏785m截图并检查停走对照：长屏变化266像素全位于顶部80行内，小屏87像素全位于顶部47行内，状态栏以下均0像素差。文件hash/尺寸见 [作者证据检查](sw010-author-evidence-inspection.json)。这是读取作者产物，未重新运行模拟器，不等于独立Android走查。终景柔光强度由Antigravity看实际app/阶段与设计意图裁定；必要时Trae补意见，不用平均差异单独判定、不擅改既定opacity。

### SW-014 R2仍需修订

对实际发布R2脚本只读执行，根定位正确；13个原样本确实得到1个ok/12个failed。但原样本通过不足以证明门禁正确。[probe_sw014_r2.py](probe_sw014_r2.py)在临时测试目录追加反例，结果见 [原始输出](sw014-r2-probe-results.json)：

| 编号 | 触发与应有结果 | 实际结果 |
| --- | --- | --- |
| R2-01 | 默认预检/dry-run面对真实registry中的SW-012 queued，应拒绝正式制作入口 | manifest内`_fixture_mode=true`/`_expected_registry_status=queued`即可使两入口通过；没有显式隔离测试边界 |
| R2-02 | 全不透明RGBA（alpha=255）应失败 | 通过，并称100%透明；实际算的是`alpha>0`像素，即非全透明覆盖率 |
| R2-03 | 必需黑/白/洋红底检查图清单为空应失败 | `checks=[]`通过，只检查已提供路径，不检查缺项 |
| R2-04 | API累计次数为负应失败，轮次不能重置已发生尝试 | `api_attempts_total=-1`通过；仅字段存在检查，没有累计账本校验 |
| R2-05 | 隔离测试registry批准A，但输入引用错任务/非SHA的B，应因当前批准review/交付不匹配而失败 | 去掉fixture标记后两入口仍通过；只看status、producer/非空head、spec哈希，未核对批准链 |

R2-05只修改了临时测试registry，未改真实SW-012状态。正例中的FAKE设计和review不是批准。默认入口不能让输入文件决定是否跳过门禁；测试应注入独立fixture registry/review/spec或显式测试入口，与生产模式分开。

另外，发布的`negative_real_oversize`实际目标图仅4414 bytes、全景96894 bytes，失败项是alpha而非budget；不能称真实超400KB/2MB覆盖。雨林layer集合仍硬编码，不读取批准design-spec；handoff承认留待R3，但这是原任务要求，不应留到付费制作后再补。API跨revision累计也须以实际账本验证，不能只保留文字承诺。

复现：`python3 docs/collaboration/evidence/P-20261014-03/probe_sw014_r2.py <SW-014-R2发布head的独立checkout> --out <本地结果.json>`；使用已有Pillow/numpy，0 API。生产者源码/素材和真实registry均未修改。本轮bootstrap据实安排R3，Antigravity另出正式review。

## 下一轮分工与退出条件

1. **Antigravity优先交可追溯结论。** 先复审SW-001 R2实际Kotlin/服务cue调用链及完整head，写R-SW-001-R2；符合条件即按分支保护集成，记录merge/CI并激活SW-004。再审SW-010含新增屏比/冻结/意图证据，写独立review；有明确视觉问题才退回对应作者。SW-014审最新revision，Trae共享稿随到随审。全部写入常驻队列，不新增重复启动任务。
2. **ZCode收口待验交付。** 旧冲突/描述/纠正已完成，不重做；响应具体QA发现，纯证据追加correction/appendix，业务修改则新head/revision。SW-001 accepted后才领取SW-004，之后SW-005；缺真机不阻塞不依赖设备的代码审核。不要因QA尚未完成提前做恢复/雨林。
3. **MiniMax交SW-014 R3与真实PR。** 只修上述五类漏洞、从批准spec读取层/尺寸、有效正负fixture/真实预算及跨revision账本；复用R2已修的根定位/解码，保留R1/R2。0新增API；修完交新业务head/H-SW-014-R3与检查输出，作者state改handoff_ready。SW-006仍等SW-012/SW-014 accepted、原总8次尝试预算。
4. **Trae把已有成果共享出来。** 优先提交推送原43文件设计包及handoff/PR；保留本机草稿，必要局部/crop补齐后更新manifest。与设计无关的.gitignore改动不混入。审稿获批后再SW-012雨林900m；若Antigravity要求终景意见，在自己拥有的设计范围追加判断依据，不代改正式图/代码。

近期里程碑是“可靠性与森林接图获独立验收并合入 + 新组合CI/可下载测试包”，以及“SW-011共享批准 + SW-014工具获批”。之后SW-004快照→SW-005地形；SW-012雨林设计→SW-006候选→SW-007双模式接入；SW-008启用前拆城市/沙漠设计/候选/接入；SW-009汇总真实设备与5–8人内测。不要按文档任务数估算产品完成百分比。

完整执行提示词已更新到四个roles入口。用户仍只需让对应工具读取一个文件；本轮不向外部工具发消息、不安装Android环境、不调用生图API、不代做产品批准。
