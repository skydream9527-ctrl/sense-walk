# SW-015 R1 · 真实设计规格与素材预检联调（零 API）

负责人 minimax。前置 SW-011（accepted）+ SW-014 R3（accepted），依据 P-20261015-02 与 [SW-015.md](../../../../../collaboration/tasks/SW-015.md)。

本目录在已批准 SW-014 R3 之上扩展，验证对真实 Trae 设计规格（SW-011 已批 + PR #15 SW-012 只读样本）的解析与兼容性。不重写 R3、不直接生雨林图；SW-012 尚未 approved 时只能作解析样本。

## 运行依赖

- Python 3.9+
- Pillow（`PIL`）
- numpy

无网络调用；无 host-managed token。

## 默认严格入口（生产）

```bash
# 单个 manifest
python3 design/assets/rainforest/preflight/SW-015/r1/scripts/preflight.py \
  design/assets/rainforest/preflight/SW-015/r1/fixtures/sw015_positive_rainforest_canonical/manifest.json
# 退出码: 0=ok, 1=failed, 2=usage

# 严格模式: spec.id_status=proposed 也算未批准 (用于真实已批 design)
python3 .../preflight.py --strict-design <manifest>

# 启用 fixture 模式 (允许 manifest 含 _fixture_mode 字段, 仅供测试 harness)
python3 .../preflight.py --fixture-mode <manifest>
```

## Dry-run（严格批准链 + spec 校验）

```bash
python3 design/assets/rainforest/preflight/SW-015/r1/scripts/dry_run.py \
  --design-ref-json <manifest.json>  # 自动提取 design_ref 字段
# 也可显式传 design_ref JSON
python3 .../dry_run.py --design-ref-json path/to/design_ref.json
```

## 字段映射

设计 spec（Trae schema）→ 素材 manifest 字段：

| spec 字段 | manifest 字段 | 说明 |
| --- | --- | --- |
| `layers[].id` | `layers[].layer_id` | legacy alias 归一化（forest SW-011 + rainforest SW-012） |
| `layers[].type` (`parallax`/`overlay`) | `layers[].render_role` | 同 enum |
| `layers[].at_meters` | (运行时配置，不进 manifest) | 设计阶段 |
| `layers[].to_opacity` | (运行时配置) | 设计阶段 |
| `layers[].fade_meters` | (运行时配置) | 设计阶段 |
| `layers[].id_status` (`proposed`/`approved`) | (设计冻结时由 QA 改 approved) | 当前允许 proposed 作样本 |
| `canvas.width` / `canvas.height` | (合同要求一致) | 1080×1920 |

不修改 spec；要求 manifest.layer_id/render_role 与 spec 一致；legacy 别名在 spec_reader 内归一化。

## 测试 harness

```bash
# 复现/验证全部 8 fixture + 6 回归探针（合成 tmp registry/handoff/review）
python3 design/assets/rainforest/preflight/SW-015/r1/scripts/probe_r1_reproduction.py . \
  --out design/assets/rainforest/preflight/SW-015/r1/records/probe-results.json
# 退出码: 0=ok（默认）/1=有负例未按预期 fail
```

输出：

- `fixture_mode_results`: CLI `--fixture-mode` 旗标下结果
- `strict_results`: 默认严格入口结果
- `dry_run_results`: dry-run 结果
- `scripts`: 本轮 4 脚本 SHA256

预期：

| fixture | fixture_mode | strict | dry_run |
| --- | --- | --- | --- |
| sw015_positive_rainforest_canonical | ok | ok | ok |
| sw015_positive_forest_legacy_alias | ok | ok | ok |
| sw015_negative_empty_spec | failed | failed | failed |
| sw015_negative_duplicate_layer_id | failed | failed | failed |
| sw015_negative_unknown_type | failed | failed | failed |
| sw015_negative_wrong_canvas | failed | failed | failed |
| sw015_negative_layer_id_mismatch | failed | failed | ok (dry_run 不校验 manifest) |
| sw015_negative_legacy_alias_mismatch | failed | failed | ok (dry_run 不校验 manifest) |

> 注：`negative_layer_id_mismatch` 与 `negative_legacy_alias_mismatch` 的 spec 本身合法，但 manifest 与 spec 不一致。这类失败只能在 `preflight` 层捕获；`dry_run` 只校验 spec + 批准链，因此 dry_run 报 ok 是预期行为。

## 退出码

| 入口 | 退出码 | 含义 |
| --- | --- | --- |
| `preflight.py` | 0 | ok |
| | 1 | failed（含具体非 PENDING 错） |
| | 2 | usage error（参数缺失） |
| `dry_run.py` | 0 | ok（批准链 + spec 全部通过） |
| | 1 | failed（批准链或 spec 不通过） |
| | 2 | usage error |
| `probe_r1_reproduction.py` | 0 | 全部 fixture 通过/失败符合预期 |
| | 1 | 有负例未按预期失败 |

## 已知边界

- PR #15 SW-012 雨林 spec 是 `id_status="proposed"`，默认 `--strict-design` 关闭，允许作为解析样本。Antigravity 审核通过后会改为 `approved`。
- SW-011 forest 5 层（tree_outline/tree_trunks/leaf_path/light_shows/clearing）已批；本工具将其归入 `KNOWN_LAYERS_FALLBACK`。
- 不修改 R3 preflight 的 18 fixture/6 探针历史（隔离在 `preflight/SW-014/r3/`）。
- 不修改真实 registry/中心登记/状态文件；probe_r1 用 tmp 隔离。
- API 累计：project lifetime baseline 14（SW-002 R1 历史），SW-015 R1 0 API，SW-006 单任务 8 次单独预算（不动）。