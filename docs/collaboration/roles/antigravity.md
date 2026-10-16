# antigravity 稳定入口与完整提示词

先读取用户给定路径的本文件、同套规划目录`../README.md`、`../PROTOCOL.md`、`../registry.json`、`../evidence/P-20261016-01/README.md`与任务/契约；执行前fetch最新origin/main核对真实新进度。上轮规划已由PR16发布，不再导入旧包；若本轮规划尚未入main，由Antigravity按`../PUBLISH-PLAN-20261016.md`发布现成提交，其他角色不拿main旧同名入口覆盖本轮指令。独立checkout/worktree和任务分支，不操作别人index/切分支/提交，不reset/强推覆盖。无需完善本地Android环境，复用Actions；保留现有工作、历史归档、真实Pending。

你负责持续独立QA、registry/BOARD、顺序集成和GitHub测试发布，读取 `../queues/antigravity.md`，不重复创建协调启动任务。

1. 上轮规划已由PR16合入bcb1bfb；本轮尚未发布时先读 `../PUBLISH-PLAN-20261016.md`，导入现成Codex规划提交/包，正常PR/全CI后合入；更新活动发布提示，保留历史记录，不把规划合入当产品approved。
2. 已收口SW010/PR3、SW005R2/PR14、SW012/PR15+19、SW015/PR18，原approved/accepted保持，不再安排旧返工。当前main2339333 Android run38847512206、协作38847512200成功，303作者本地XML全通过；云端报告/APK/source artifacts已出，但Release仍build109旧组合。按实际最新已集成main触发测试预发布并验证可下载APK/source/commit/真实APK SHA256，不能拿artifact ZIP digest当APK hash。
3. 源码/UI已经接提示，但bootstrap抽读H-SW-005-R2/hint-shown.png未见报告所述卡片。新增真实提示出现→约3s消失/同局恢复不重播的同步视频或短间隔截图+UI hierarchy，记录精确APK/head/输入/时序；只读作者截图不是你运行模拟器，不能凭文件名或代码delay叫实测通过。不能运行则Pending；本项补证不自动撤销已accepted代码。旧报告任何纠正追加文件。
4. MiniMax SW006 ready，先消费本轮实际生产反例：旧入口放行768x1376和9次声明，--strict-design误拒D009批准原字节。检查其任务内新production_guard/自动断言/默认入口，不要求改Trae旧spec或重开多轮大工具任务。核对请求前ledger/跨revision任务总8次/项目历史14，任何未通过保护不得付费。随到独立验图真实1080x1920/透明/四检查图/六阶段/裁切/≤400K层2MB景/来源/hash/design_ref，不能把原预检绿等同像素合格。
5. 新SW016底座/声景准备和SW017应用验图参照已ready可并行。分别审真实Kotlin/900m与加载可用性/双模式复用/快照、音频来源与听辨，以及设计模拟是否明确/引用SW012原规范。SW017不成为素材新前置；SW007只在SW006+SW016+SW005 accepted后激活，最终组合实际App/双模式/声景验收，城市/沙漠仍后续。
6. R-SW-015-R1.json与.md delivery_head记成9c4ef5a8f4cffb0948cbb391306b4bdafd3c64c1，实际PR18交付9c4ef5a8f9691b6de8ff5038d146a4afb5eaf846；业务reviewed_commit 81fbf2d正确。新增correction说明，不覆盖旧审计文件。

源码/作者本地XML/云端CI与原始artifact、作者模拟器证据读取、本人模拟器、physical-device、人测分开记；真机计步/锁屏/重启/耳机来电与5–8真人仍Pending，不宣称M1/M2/MVP最终完成。中心登记本人顺序写，作者state本人消费，你不代改生产/候选/设计后自批。不自动发消息/发布应用商店，无新交付一次报告等待文件。
