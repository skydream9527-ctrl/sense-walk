# SW-006 R1 独立评审纠正与状态追加报告

- **任务 ID**: SW-006（雨林候选素材批次）
- **评审人**: Antigravity (QA)
- **提交人**: MiniMax Code
- **交付 PR**: [PR #25](https://github.com/skydream9527-ctrl/sense-walk/pull/25)
- **最新交付分支状态**: `codex/minimax/SW-006-r1`（tip `8e73b13c432fb8b003c960d1706bc09b22814533`，路径修复 commit `d71d6278860c3551b545bd3b476e38c77096622a`，业务 commit `6ba654c5ba761ab25d94d121e985c5298d2d3d8a`）
- **相关 Handoff**: 
  - `docs/collaboration/handoffs/minimax/H-SW-006-R1.json`（原始 R1 handoff）
  - `docs/collaboration/handoffs/minimax/H-SW-006-R1-supplement.json`（最新追加通知与 CI fixture 转交）
- **前置评审报告**: [R-SW-006-R1.md](./R-SW-006-R1.md)
- **本次评审结论**: **`changes_requested`**（门禁规范项 F-01/F-02 已确认修复；CI 协议测试 fixture 隔离已由 QA 修复闭环；F-03 占位草案性质在当前阶段收口期保持，待下一阶段 R2 真实生图交付）

---

## 1. 历史 Finding 复查与核验

对 MiniMax 在 PR #25 提交的最新提交（`d71d627` 与 `8e73b13`）进行重新独立核验：

| Finding | 原始问题 | 最新核验结果（d71d627 / 8e73b13） | 状态 |
| :--- | :--- | :--- | :--- |
| **F-01** | Manifest 路径缺失仓库根前缀 | `design/assets/rainforest/candidates/SW-006/r1/manifest.json` 中 5 个图层的 `file` 与 `checks` 路径已全部补全仓库根相对路径前缀（如 `design/assets/rainforest/candidates/SW-006/r1/webp/rainforest_mist.webp`）。 | **已修复 (Fixed)** |
| **F-02** | Handoff Evidence 包含通配符 | `H-SW-006-R1.json` 中的 9 项 checks evidence 已全部展开为具体存在的文件路径，无通配符 `*` 且无目录结尾 `/`。 | **已修复 (Fixed)** |
| **F-03** | 0 API 占位草案性质 | R1 明确声明为 0 API 程序化 PIL 占位（~125KB 全景），非正式生产级像素美术素材。按 `STAGE-CLOSEOUT.md` 与当前阶段收口规定，当前阶段不新增付费 API 调用，不把雨林占位放入当前森林阶段包（`build-176-aaa789b`）；既有 8 次单任务尝试预算保留至下一阶段 R2 正式雨林生图使用。 | **保持观察 (Observed)** |

### 独立执行验证
- **SW-015 生产预检**: `python3 design/assets/rainforest/preflight/SW-015/r1/scripts/preflight.py design/assets/rainforest/candidates/SW-006/r1/manifest.json` → **80/80 passed** (0 failed)。
- **SW-015 批准链严格 Dry Run**: `python3 design/assets/rainforest/preflight/SW-015/r1/scripts/dry_run.py --design-ref-json design/assets/rainforest/candidates/SW-006/r1/manifest.json` → **11/11 passed**。
- **文件哈希比对**: 5 层 WebP、1 候选 manifest、1 生成脚本与 20 张检查图 SHA-256 均与 manifest 及 handoff 记录完全吻合。

---

## 2. 协作 CI 红灯转交与 QA 隔离修复闭环

MiniMax 在 `H-SW-006-R1-supplement.json` 中转交了 `tools/qa/test_collaboration.py` 在 GitHub Actions 上的 1 failure / 1 error 阻断。QA 独立定位并完成修复：

1. **测试替换关系污染 (Cross-Test Fixture Pollution)**:
   - 根因：`test_collaboration.py` 中的 `test_design_accepted_with_exact_independent_hashes_is_valid` 调用 `design_delivery(accepted=True)` 生成了一套新的虚拟 SW-012 设计交付，重写了 `design-spec.json`。由于下游真实 `SW-006` 候选 manifest 引用了 SW-012，导致 `SW-006` 的 `spec_sha256` 与新生成的虚拟 spec 产生 hash mismatch。
   - 修复：在 `test_collaboration.py` 的 `design_delivery()` 中增加测试隔离同步逻辑，在创建虚拟设计交付时，将测试沙箱根目录下的下游候选 manifest 与 handoff artifacts sha256 保持联动，避免跨用例测试污染。
2. **缺失 Manifest 防御性校验 (Defensive Manifest Check)**:
   - 根因：`test_design_without_manifest_is_rejected` 删除了虚拟设计 handoff 的 `design_manifest` 字段，导致 `tools/collaboration.py` 在验证下游引用时抛出 `KeyError: 'design_manifest'`。
   - 修复：在 `tools/collaboration.py` 中增加对 `design_manifest` 字段存在性与物理文件存在性的防御性检查，缺失时作为验证错误安全报告，杜绝 Python 未捕获异常。
3. **Supplement 补丁与检查证据兼容**:
   - `tools/collaboration.py` 补充支持 `kind == "supplement"` 类型 handoff（无需 asset/design manifest），并在解析 evidence 路径时防御性剥离说明性括号后缀。
4. **验证结果**:
   - `python3 tools/qa/test_collaboration.py` **31 项单测全部通过 (OK)**，未 skip 任何测试，严格批准链、真实哈希比对与依赖校验 100% 保留；同时未修改 MiniMax 任何生产与候选素材。

---

## 3. 阶段收口与后续指引

- **当前阶段结论**:
  - 本阶段聚焦于冻结并回收森林双模式安装测试包（`build-176-aaa789b`）的真实反馈。
  - SW-006 在 `registry.json` 保持 **`rework`** 状态；R1 零 API 草案已完成门禁与路径规范收尾，不合入当前阶段包。
  - 下一阶段启动雨林正式制作时，MiniMax 直接沿用已授权的总 8 次模型尝试预算，产出 1080×1920 真实像素、真透明无黑底、四检查图齐备的正式素材 R2 交付。
