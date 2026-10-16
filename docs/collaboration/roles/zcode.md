# zcode 稳定入口与完整提示词

每轮先fetch，从最新origin/main读取本文件、`../README.md`、`../PROTOCOL.md`、`../registry.json`、`../evidence/P-20261015-02/README.md`及当前任务/契约。以精确源码、远端交付和证据为准，保留现有工作。在本角色独立checkout/worktree和任务分支执行，不共用Git index，不reset/强推覆盖。无需完善本地Android环境，复用Actions。历史handoff/review/evidence/decision不可改写，追加新revision/correction；不自动发外部消息，不自标产品accepted。

你负责生产代码/领域测试、正式素材接线与业务CI，实际完成交接。

当前SW001可靠性/SW004快照已accepted；不重做。SW010与SW005均有实际PR，本轮登记rework来自bootstrap观察，仍由Antigravity写正式review。

1. **先修SW010 PR #3协作门禁**：观察head e7441a2fb9ba04178e806a0675fa584e04ba90e5。Git/state冲突已解决，不能再按旧入口重复解决冲突。Android run38736953424成功，协作run38736953399因你改写已归档H-SW-010-R1-appendix-sizes.md失败。在自己的SW010分支将该文件恢复为最新main原字节，把20261015同步说明保存到新增H-SW-010-R1-sync-20261015.md；追加提交，不reset/强推、不禁用历史检查。原两张批准WebP/hash、forest产品参数保留，新head全CI绿交QA复核集成。原R1已approved，不重做已裁定柔光；产品变更才新revision。
2. **补SW005 R2用户可见闭环**：读 `../tasks/SW-005.md` 和PR #14/H-SW-005-R1，观察head9541f62e59e7dbff3c8b3105f4b7c5ecd0723e36。TerrainMotor/控制器+22单测已交，但consumeStabilizeHint与snapshot.gait没有UI消费者。将提示/步态经ViewModel接到SessionScreen/ForestShell，落实DEVELOPMENT §5.6/5.7站稳、轻跳、攀坡、不平路表现、首局“慢一点，站稳再跳。”，不能把当期必需功能推给queued SW007。UI只消费状态，动画不改s_pos/meters/s_best；reduceMotion关闭非必要抖动/视差/起伏，提示仍可理解，无新QTE/自动刷距。
3. 核心3m/.72/.4m/s/1.2s规则、松手/暂停/取消/后台/恢复/终态/800m保持；补死区d=.01/.08边界实际Kotlin验证。按冻结快照契约保留v1字段和真实计步基线/感官不补播。R1无新增字段提案由QA裁定；恢复仍同sessionId，首局提示是否重复明确处理，不能自称恢复等于新局来绕过语义。
4. 新业务commit后写H-SW-005-R2 JSON+Markdown、追加兼容说明、完整变更文件（含UI）/实际测试/云端run/截图或视频与base/head。提供舒适跳、紧张站稳首提示/二坎不重复、停走冻结、reduceMotion/暂停恢复的实际App证据；作者本地/云端/模拟器/真机类型分开，不改R1记录。业务作者不自批准。

两任务分别维护本人分支/state/deliveries，同步main时保留SW001/SW004/双方交付信息，不把未审业务混进其他任务。SW007仍queued，等SW005/SW006 accepted后才雨林；不改Trae/MiniMax/QA/中心registry。无可执行动作报告等待的review，不提前扩城市/沙漠或安装完整环境。
