# 视觉交付契约 v1（生效）

正式 layer ID/atMeters/opacity/fadeMeters 从当前已验收 SceneConfig 获取，不在素材中烘焙距离透明度。角色与黑幕为程序绘制，不属于本轮候选验收。

候选根目录：`design/assets/<scene>/candidates/<task-id>/r<revision>/`。至少包括 `png/`、`webp/`、`checks/black/`、`checks/white/`、`checks/magenta/`、`checks/stages/` 与 `manifest.json`。manifest 字段结构见 [示例](../templates/asset-manifest.json.example)。

每层记录 layer_id、file、sha256、width/height、bytes、alpha_channel、render_role、tileable、origin、process、quality_status、checks、limitations。manifest 内 file/checks 路径相对 repo 根。origin 指明 AI/service、原稿、原有程序算法或其他来源及条款依据；API 账本记录实际累计尝试数、成功/失败与已知费用，未知费用写 unknown。不得把 AI 输出标为 CC0。

验收要求：
- 每层仅画该层内容；overlay 不能附带完整背景或第二套树林。实际纯色底合成无烘焙棋盘、白边和矩形底；正确 alpha 不等于像素内容合格。
- 重点看实际入包等比例裁切后的中央与边缘；至少黑/白/洋红底及实际 opacity 六阶段预览。指标只能辅助，不能把“浅色像素为零”当通过规则。
- 森林本轮阶段为 0/100/265/425/630/785m；雨林按 900m 配置和各 fadeMeters 推导展示检查点。0m 无提前风景。
- 目标宽1080、每层≤400KB、每景五个外部视觉层≤2MB。现森林历史768×1376为已记录偏差，收尾不通过单纯放大冒称原生1080；新景按规格出最终文件并记录原始尺寸。
- tileable 必须提供三次拼接与多个偏移预览；仅边缘透明或复制同一边带不能证明连续。只有交付实际通过才写 true；当前渲染只有限滑动，不能宣称候选平铺已经接入。

状态：candidate → approved_candidate/rejected → integrated（需单独 ZCode 入包任务）→ app_verified。MiniMax 最多声明 candidate；approved_candidate 来自独立 review；integrated 来自配置/代码提交；app_verified 来自 Android 证据。每个批准必须匹配 file sha256。

发生尺寸、ID、定位基线或渲染角色变化，先写 handoff 给 ZCode/Antigravity，不直接改 app。候选是契约数据，不是产品规则授权。

新场景制作前先消费Trae批准设计，按 [图片设计契约](visual-design.md) 给manifest增加design_ref：task_id、已批准handoff路径、spec_file、spec_sha256。雨林SW-006以SW-012 accepted为前置；森林SW-002机械修复保持原任务输入，design_ref可为null，不能用这条例外跳过新场景设计。设计稿、候选素材、正式入包各自独立验收。
