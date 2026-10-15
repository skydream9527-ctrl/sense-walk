# SW-014 · 雨林素材交付预检准备 (R2 修订)

**任务 ID**: SW-014  
**owner**: minimax  
**type**: code (素材工具脚本)  
**status**: R1 已推, R2 修订中  
**前置**: SW-002/SW-003 accepted (满足)  
**API 预算**: 0 (R1 + R2 累计 0; SW-006 沿原 8 次预算不重置)  
**等**: SW-012 approved → SW-006 ready

## R1 → R2 变更

R1 在 [P-20261014-02](../evidence/P-20261014-02/README.md) 报告有 4 个反例:

| PF | 描述 | R1 actual | R2 修正 |
| --- | --- | --- | --- |
| PF-01 | 文本伪装 WebP, 0×0, 未知 layer, 缺检查图, 缺 design_ref | **ok** | 拒绝 (真实解码 + alpha 像素 + 路径解析) |
| PF-02 | 空 layers + 缺 design_ref | **ok** | 拒绝 (缺必需层 + 真实 registry_status) |
| PF-03 | dummy handoff JSON + 缺 spec + 错 hash | **ok=True** | 拒绝 (路径不存在 + spec_sha_stale + registry_status) |
| PF-04 | 真实 SW-002 manifest 用仓库根相对路径 | **failed** (路径被错位为 manifest 目录相对) | OK (find_repo_root 探测 + 越界检查 + repo 根强制) |

**根本问题**:
- ROOT 解析用 `parents[5]` 实际落在 `design/assets`, 不是 repo 根
- 没真实解码, 文本伪装/0x0 都被接受
- 没拒绝越界/绝对路径
- 缺必需 layer 集合校验
- dry_run 接受 dummy 文件 + 缺 spec + 错 hash

**R2 修正**:
1. `find_repo_root` 向上查找 `docs/collaboration` + `design/assets` 双重确认 + git toplevel 交叉验证
2. `real_decode_image` 用 PIL `Image.open` + `verify` + `load` + alpha 像素比例
3. `safe_repo_path` 拒绝 `..` 越界 + 绝对路径 + 不存在
4. `KNOWN_LAYERS` 按 `(task_id, scene_id)` 定义必需层集合
5. dry_run 严格验证: task_id / handoff producer (trae-design/antigravity) / handoff head_commit / spec_file 存在 / spec_sha256 实际匹配 / registry task 状态

## 13 个 fixture 实际结果 (R2)

| fixture | preflight status | 核心失败 |
| --- | --- | --- |
| `positive_ok` | **ok** (48/48) | — |
| `negative_not_image` | failed (43/44) | `layer_mist_decode` 非图/坏图 (文本伪装) |
| `negative_zero_size` | failed (46/49) | `size_manifest: 1x1 != manifest 0x0` + `size_unsupported` + `opaque` |
| `negative_opaque_layer` | failed (47/48) | `layer_mist_opaque: 透明 0%` |
| `negative_empty_layers` | failed (12/13) | `missing_required_layers: 缺 5 层` |
| `negative_unknown_layer` | failed (19/21) | `layer_foo_bar_unknown + 缺必需层` |
| `negative_duplicate_layer` | failed (26/28) | `layer_mist_duplicate + 缺必需层` |
| `negative_missing_file` | failed (37/42) | `layer_mist_file_missing + 4 个 bytes 不符` |
| `negative_wrong_hash` | failed (47/48) | `layer_mist_sha256: 0...0 != 实际` |
| `negative_missing_check` | failed (48/49) | `layer_mist_check_alpha_mask 缺` |
| `negative_real_oversize` | failed (47/48) | `layer_trunks_canopy_opaque (alpha=0)` |
| `negative_wrong_design_ref` | failed (45/48) | `design_ref_handoff_path + spec_file_path 越界` |
| `negative_stale_spec_sha` | failed (47/48) | `design_ref_spec_sha_mismatch: stale != 实际 c8eb...` |

> 12 个 negative 全部有**具体非 PENDING 错**; `registry_status: queued != accepted` 是 fixture 模式副作用 (临时标记 `_fixture_mode=true` 接受 queued), 不算"全因 PENDING 失败".

## 目录

```
design/assets/rainforest/preflight/SW-014/r2/
├── README.md                          本文件
├── scripts/
│   ├── build_fixtures.py              13 fixture 构建 (零 API, PIL)
│   ├── preflight.py                   预检 (find_repo_root + 真实解码 + 越界拒绝)
│   ├── dry_run.py                     dry-run (严格 design_ref 验证)
│   └── probe_r1_reproduction.py       R1 复现脚本 (从 origin/main 复制)
├── fixtures/                          13 fixture
│   ├── positive_ok/                    5 层 + 临时 fixture_mode approved design_ref
│   ├── negative_*/                    12 个隔离反例 (每例只改一个目标条件)
│   └── _design/                       临时 handoff/spec 副本 (R1 未批准)
├── records/                           实际预检结果
│   ├── preflight_*.json                13 份 preflight 报告
│   ├── dry_run_*.json                  13 份 dry_run 报告
│   └── r1_probe_reproduction.json      R1 probe 复现 (证明 R1 bug 存在)
└── (README.md)
```

## 实际执行命令

```bash
# 1. 构建 13 fixture
python3 scripts/build_fixtures.py

# 2. 跑 preflight + dry_run 每个 fixture
for f in fixtures/*/manifest.json; do
    python3 scripts/preflight.py "$f" --json --out records/preflight_$(basename $(dirname $f)).json
    python3 scripts/dry_run.py --design-ref-json "$f" --out records/dry_run_$(basename $(dirname $f)).json
done

# 3. 复现 R1 bug (在 R1 发布 head 13d6c0d 上跑)
python3 scripts/probe_r1_reproduction.py <R1 worktree> --out records/r1_probe_reproduction.json
```

## 关键设计决策

1. **fixture_mode 模式**: SW-012 真实状态 queued (R2 期间仍如此), fixture 通过 `_fixture_mode=true` + `_expected_registry_status=queued` 接受. 真实模式 (未标 fixture_mode) 严格校验 registry accepted.
2. **真实路径解析**: `find_repo_root` 向上查找 `docs/collaboration` + `design/assets` + git toplevel 三重确认, 不依赖 `parents[N]` 错位.
3. **真实解码**: `Image.open` + `verify` + `load` + alpha 像素比例, 拒绝文本伪装 / 0x0 / 不透明层.
4. **隔离反例**: 每个 negative fixture 只改一个目标条件, 验证具体错误, 避免全因 PENDING 失败.
5. **真实文件**: 不用只改 manifest 声明的"虚报字节", 真实写大文件 (negative_real_oversize trunks_canopy 96 KB) 验证.
6. **不重置账本**: R1/R2 失败/超时累计; SW-006 沿原 8 次总尝试预算.
7. **AI 不标 CC0**: preflight 检查每层 origin 字段, 含 CC0 字符串直接拒绝.

## 调用账本

```json
{
  "task_id": "SW-014",
  "api_attempts_r1": 0,
  "api_attempts_r2": 0,
  "api_attempts_total": 0,
  "cost_usd": "n/a",
  "note": "R1 + R2 零 API. SW-006 沿原 8 次总尝试预算不重置."
}
```

## 与 SW-002 批准的兼容

- SW-002 = forest, 2 层 (clearing + light_shows), 已 accepted, R-SW-002-R1 approved at f512d20
- SW-002 manifest 在 `design/assets/forest/candidates/SW-002/r1/manifest.json`
- 预检 SW-002 manifest 用 `KNOWN_LAYERS[("SW-002", "forest")] = {clearing, light_shows}` 校验必需层
- 不替 SW-002 强制 5 层 (森林历史 2 层修图, 不是 5 层雨林)
- SW-006 = rainforest, 5 层 (mist + trunks_canopy + vines_light + far_glow + clearing_glow), 等 SW-012 approved

## a5ad6dd 误述纠正

P-20261014-02 § 文档纠正需追加 明确指出:
- H-SW-014-R1.md 写"a5ad6dd 入包" 是误述; a5ad6dd 仅是候选合并, 没改 forest.json 或替换入包 webp
- SW-010 接图在 PR #3 (dfcc19e), 尚未合入 main
- 私有 state 也曾误写"观察到 ZCode 入包" → 已更新追加纠正记录 (不重写历史 handoff/review)
- R2 在 `docs/collaboration/decisions/D-CORRECTION-a5ad6dd-claim.md` 追加 correction 记录

## 维护者

minimax (代码 + 文档)  
Antigravity (独立审核 R-SW-014-R2)
