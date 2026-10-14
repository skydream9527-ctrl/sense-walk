# SW-014 · 雨林素材交付预检准备 (零 API)

**任务 ID**: SW-014  
**owner**: minimax  
**type**: code（素材工具脚本，不是 Android 代码）  
**status**: ready → 准备中 → handoff_ready → 等 Antigravity 审核  
**前置**: SW-002/SW-003 accepted（已满足）  
**API 预算**: 0（本任务零调用；SW-006 沿原 8 次预算不重置）  
**等待**: SW-012 approved 后才能领 SW-006

## 范围

- 提供雨林候选交付的预检脚本（fixture-based, 零 API 调用）
- 提供 fixture 自制小样本（不调用生图 API, 用 PIL 程序化生成）
- 提供 `manifest.json` schema 验证 + SHA256 / 字节 / 尺寸 / 预算检查
- 提供 4 底色检查图路径完整性
- 提供 design_ref 验证（缺设计/未批准/PENDING 视为阻断）
- 提供 API 账本模板（`fixtures/api_log_template.json`）
- 提供 dry-run 入口（模拟 SW-006 未来实际启动检查）
- **不替 Trae 决定雨林构图/色板/光效**
- **不伪造已批准设计**
- **不调用生图 API**

## 目录

```
design/assets/rainforest/preflight/SW-014/r1/
├── README.md                    本文件
├── scripts/
│   ├── gen_fixtures.py          生成 6 个 fixture (零 API, PIL 程序化)
│   ├── preflight.py             主预检脚本 (--json 输出报告)
│   ├── dry_run.py               dry-run 模拟 SW-006 启动检查
│   └── api_log_template.py      SW-006 调用账本模板
├── fixtures/                    6 个 fixture
│   ├── manifest_ok/             合法: 5 层 + 透明 + 预算内 + 4 底色检查齐 (但 design_ref PENDING)
│   ├── manifest_oversize/       1 层 manifest bytes 字段虚报 (500KB)
│   ├── manifest_wrong_hash/     1 层 manifest sha256 字段虚报 (0...0)
│   ├── manifest_missing/        1 层 webp 文件实际不存在
│   ├── manifest_not_tileable/   1 层 tileable=true 但缺 tileable checks
│   ├── manifest_no_design/      manifest 缺 design_ref
│   ├── design_ref_pending.json  design_ref fixture (PENDING_SW012_APPROVAL)
│   └── api_log_template.json    SW-006 账本模板 (0 attempts)
└── records/                     实际预检结果 JSON
    ├── preflight_manifest_ok.json
    ├── preflight_manifest_oversize.json
    ├── preflight_manifest_wrong_hash.json
    ├── preflight_manifest_missing.json
    ├── preflight_manifest_not_tileable.json
    ├── preflight_manifest_no_design.json
    └── dry_run_pending.json
```

## 实际预检结果（6 fixture）

| fixture | 主要失败 | 用途 |
| --- | --- | --- |
| manifest_ok | design_ref handoff 不存在 + spec_sha256 PENDING | 验证"全部正确但设计未批"也阻断 |
| manifest_oversize | layer_mist_bytes 500000 != actual 10346 | 验证字节字段不实报 |
| manifest_wrong_hash | layer_vines_light_sha256 0...0 != actual 0c5b... | 验证 SHA 字段不实报 |
| manifest_missing | webp/rainforest_far_glow.webp 文件不存在 | 验证文件路径检查 |
| manifest_not_tileable | tileable=true 但缺 seamless/stages 检查图 | 验证 tileable=true 限制 |
| manifest_no_design | design_ref 字段缺失 | 验证新场景必须有 design_ref |

每个 fixture 报告保存在 `records/preflight_<name>.json`。

## 实际执行命令与结果

```bash
$ python3 scripts/gen_fixtures.py
=== SW-014 fixture 生成 ===
  manifest_ok: 5 层, total bytes=94778
  manifest_oversize: 5 层, total bytes=561318
  manifest_wrong_hash: 5 层, total bytes=94778
  manifest_missing: 5 层, total bytes=94778
  manifest_not_tileable: 5 层, total bytes=94778
  manifest_no_design: 5 层, total bytes=94778

$ python3 scripts/dry_run.py --design-ref-json fixtures/design_ref_pending.json --out records/dry_run_pending.json
# design_ref_check.ok = false, design_ref.handoff 不存在
# exit code 1
```

## 设计 + 协议

- 依赖: `Pillow`, `numpy` (项目已有)
- 协议: `docs/collaboration/PROTOCOL.md` + `contracts/visual-assets.md` + `contracts/visual-design.md`
- fixture 拒绝: `PENDING_*` 视为 spec 未批准, handoff 不存在视为 Trae 未发布
- 尺寸: 接受 768x1376 (历史 raw) 与 1080x1920 (项目最终画布 cover 缩放); 其他视为异常
- 预算: 400 KB/层, 2 MB/景 (5 外部视觉层)
- 账本: API 账本字段必须存在 (api_attempts_this_revision / api_attempts_total / cost)

## 拒绝 AI 输出 CC0

`origin` 字段含 "CC0" 视为不合规, 预检失败 (在 contracts/visual-assets.md 规则下).

## 凭据

零硬编码, host-managed / 环境变量 (本任务不调用 API, 无凭据需求).

## 失败/超时

零调用, 无账本条目.

## 调用账本 (本任务)

```json
{
  "task_id": "SW-014",
  "api_attempts_this_revision": 0,
  "api_attempts_total": 0,
  "cost": "n/a (零 API)"
}
```

## 依赖与下一步

- 本任务完成不依赖 SW-012 (但预检脚本可以读 SW-012 approved 后的 design_ref)
- SW-006 启动时: minimax 实例化 `fixtures/api_log_template.json`, 按真实顺序生图, 每次写 attempt
- SW-006 真实生成前: minimax 必须先 dry-run 一次, design_ref_check.ok 必须为 true
- 预检脚本可被 SW-006 集成测试复用 (单测边界值)

## 维护者

minimax (代码 + 文档)  
Antigravity (独立审核)
