#!/usr/bin/env python3
"""Validate file handoffs and render the coordination board. Standard library only.
This checks structure/hashes/dependencies; it does not run agents or certify QA.
"""
from __future__ import annotations
import argparse, fnmatch, hashlib, json, re, subprocess, sys, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/collaboration'
ROLES = {'zcode', 'minimax', 'antigravity', 'trae-design'}
STATES = {'queued', 'ready', 'in_progress', 'handoff_ready', 'in_review', 'rework', 'accepted', 'blocked'}
CHECK_STATES = {'passed', 'failed', 'pending', 'not_applicable'}
SHA = re.compile(r'^[a-f0-9]{40}$')
HASH = re.compile(r'^[a-f0-9]{64}$')
WRITE_SCOPES = {
    'zcode': ['app/**', 'gradle/**', 'gradlew*', '*gradle*', 'settings.gradle.kts', '.github/workflows/android.yml', 'ASSETS.md', 'docs/collaboration/handoffs/zcode/**', 'docs/collaboration/state/zcode.json'],
    'minimax': ['design/assets/**', 'docs/collaboration/handoffs/minimax/**', 'docs/collaboration/state/minimax.json'],
    'trae-design': ['design/05-visual-design/**', 'docs/collaboration/handoffs/trae-design/**', 'docs/collaboration/state/trae-design.json'],
    'antigravity': ['docs/**', 'README.md', 'DEVELOPMENT.md', 'ASSETS.md', 'AGENTS.md', 'app/src/androidTest/**', 'tools/**', '.github/workflows/collaboration.yml'],
}


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def repo_path(value: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError(f'invalid repo-relative path: {value!r}')
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f'path escapes repository: {value}')
    return path


def checks(items: list, context: str, errors: list):
    for check in items:
        if check.get('status') not in CHECK_STATES:
            errors.append(f'{context}: invalid check status')
        if check.get('status') == 'passed' and not check.get('evidence'):
            errors.append(f'{context}: passed check without evidence')
        for evidence in check.get('evidence', []):
            if evidence.startswith(('https://', 'http://')):
                continue
            clean_evidence = re.sub(r'\s*\([^)]*\)$', '', evidence).strip()
            path = None
            try:
                p_cand = repo_path(evidence)
                if p_cand.is_file():
                    path = p_cand
                else:
                    p_clean = repo_path(clean_evidence)
                    if p_clean.is_file():
                        path = p_clean
            except ValueError:
                try:
                    p_clean = repo_path(clean_evidence)
                    if p_clean.is_file():
                        path = p_clean
                except ValueError:
                    pass
            if path is None or not path.is_file():
                errors.append(f'{context}: missing evidence {evidence}')


def validate() -> list[str]:
    errors = []
    registry = read(BASE / 'registry.json')
    if registry.get('schema_version') != 1 or registry.get('coordinator') != 'antigravity':
        errors.append('registry: wrong schema/coordinator')
    tasks = registry['tasks']
    by_id = {t['id']: t for t in tasks}
    if len(by_id) != len(tasks):
        errors.append('registry: duplicate task IDs')
    for role, entry in registry['role_entries'].items():
        if role not in ROLES or not repo_path(entry).is_file():
            errors.append(f'missing/invalid role entry {role}')
    for task in tasks:
        id = task['id']
        if task['owner'] not in ROLES or task['status'] not in STATES:
            errors.append(f'{id}: invalid owner/status')
        if not repo_path(task['task_file']).is_file():
            errors.append(f'{id}: missing task document')
        for dep in task['depends_on']:
            if dep not in by_id:
                errors.append(f'{id}: unknown dependency {dep}')
            elif task['status'] in {'ready', 'in_progress', 'handoff_ready', 'in_review', 'accepted'} and by_id[dep]['status'] != 'accepted':
                errors.append(f'{id}: active before dependency {dep} accepted')
        for key in ('latest_handoff', 'latest_review'):
            if task.get(key) and not repo_path(task[key]).is_file():
                errors.append(f'{id}: missing {key}')
        if task.get('integrated_commit') and not SHA.fullmatch(task['integrated_commit']):
            errors.append(f'{id}: invalid integrated SHA')
        if task['status'] == 'accepted' and task['kind'] != 'coordination':
            if not task.get('latest_handoff') or not task.get('latest_review') or not task.get('integrated_commit'):
                errors.append(f'{id}: accepted without delivery/review/integration evidence')
            else:
                review = read(repo_path(task['latest_review']))
                handoff = read(repo_path(task['latest_handoff']))
                if review.get('verdict') != 'approved' or review.get('reviewed_commit') != handoff.get('head_commit'):
                    errors.append(f'{id}: approval does not match delivery head')
                if review.get('task_id') != id or handoff.get('task_id') != id:
                    errors.append(f'{id}: cross-task approval')
    visiting, visited = set(), set()
    def visit(id):
        if id in visiting:
            errors.append(f'dependency cycle at {id}'); return
        if id in visited: return
        visiting.add(id)
        for dep in by_id[id]['depends_on']:
            if dep in by_id: visit(dep)
        visiting.remove(id); visited.add(id)
    for id in by_id: visit(id)
    for role in ROLES:
        state = read(BASE / 'state' / f'{role}.json')
        if state.get('schema_version') != 1 or state.get('agent') != role or state.get('status') not in {'idle', 'in_progress', 'handoff_ready', 'waiting', 'blocked'}:
            errors.append(f'state/{role}: invalid identity/status')
        id = state.get('current_task')
        if id and (id not in by_id or by_id[id]['owner'] != role):
            errors.append(f'state/{role}: task not owned')
        elif id and state.get('status') in {'in_progress', 'handoff_ready'}:
            # A producer may not yet have consumed the coordinator's acceptance/block notice.
            # Stale private state must not force the coordinator to overwrite another role's file.
            if by_id[id]['status'] == 'queued' or (by_id[id]['status'] not in {'accepted', 'blocked'} and any(d not in by_id or by_id[d]['status'] != 'accepted' for d in by_id[id]['depends_on'])):
                errors.append(f'state/{role}: task not executable')
        if state.get('latest_handoff') and not repo_path(state['latest_handoff']).is_file():
            errors.append(f'state/{role}: missing handoff')
    deliveries = [(path, read(path)) for path in (BASE / 'handoffs').rglob('*.json')]
    latest_revision = {}
    for _, h in deliveries:
        if h.get('kind') != 'supplement':
            latest_revision[h.get('task_id')] = max(latest_revision.get(h.get('task_id'), 0), h.get('revision', 0))
    reviews = [(path, read(path)) for path in (BASE / 'reviews').rglob('*.json')]
    for path, h in deliveries:
        context = path.name
        task = by_id.get(h.get('task_id'))
        if not task or h.get('producer') != task['owner']:
            errors.append(f'{context}: producer/task mismatch')
        if task and task['kind'] == 'asset' and h.get('kind') != 'supplement' and not h.get('asset_manifest'):
            errors.append(f'{context}: asset delivery requires a manifest')
        if task and task['kind'] == 'design' and h.get('kind') != 'supplement' and not h.get('design_manifest'):
            errors.append(f'{context}: design delivery requires a manifest')
        if h.get('schema_version') != 1 or h.get('revision', 0) < 1:
            errors.append(f'{context}: invalid version/revision')
        if not SHA.fullmatch(h.get('head_commit', '')) or not SHA.fullmatch(h.get('base_commit', '')):
            errors.append(f'{context}: invalid base/head SHA')
        if h.get('producer') not in path.parts or not repo_path(h.get('report', '')).is_file():
            errors.append(f'{context}: misplaced handoff/missing report')
        for changed in h.get('changed_files', []):
            canonical = repo_path(changed).relative_to(ROOT).as_posix()
            if canonical != changed:
                errors.append(f'{context}: changed file path must be canonical {changed}')
            if not any(fnmatch.fnmatchcase(canonical, pattern) for pattern in WRITE_SCOPES.get(h.get('producer'), [])):
                errors.append(f'{context}: file outside producer scope {changed}')
            for role in ROLES - {h.get('producer')}:
                if changed.startswith(f'docs/collaboration/handoffs/{role}/') or changed == f'docs/collaboration/state/{role}.json':
                    errors.append(f'{context}: writes another producer private file {changed}')
        checks(h.get('checks', []), context, errors)
        for artifact in h.get('artifacts', []):
            p = repo_path(artifact['path'])
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != artifact.get('sha256'):
                errors.append(f'{context}: artifact hash mismatch {artifact["path"]}')
        if h.get('asset_manifest'):
            m = read(repo_path(h['asset_manifest']))
            if m.get('schema_version') != 1 or m.get('task_id') != h.get('task_id') or m.get('producer') != h.get('producer') or m.get('revision') != h.get('revision'):
                errors.append(f'{context}: manifest task mismatch')
            for layer in m['layers']:
                p = repo_path(layer['file'])
                if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != layer.get('sha256'):
                    errors.append(f'{context}: candidate hash mismatch {layer["file"]}')
                if p.is_file() and p.stat().st_size != layer.get('bytes'):
                    errors.append(f'{context}: candidate byte count mismatch {layer["file"]}')
                if layer.get('width', 0) <= 0 or layer.get('height', 0) <= 0 or not layer.get('checks'):
                    errors.append(f'{context}: missing dimensions/visual evidence {layer["file"]}')
                for evidence in layer.get('checks', []):
                    if not repo_path(evidence).is_file(): errors.append(f'{context}: missing visual check {evidence}')
            design_dependencies = [d for d in task['depends_on'] if by_id[d]['kind'] == 'design'] if task else []
            ref = m.get('design_ref')
            if design_dependencies and not ref:
                errors.append(f'{context}: new asset batch requires approved design_ref')
            if ref:
                handoff_path = path.relative_to(ROOT).as_posix()
                is_current = h.get('revision') == latest_revision[h.get('task_id')]
                # An explicitly retired delivery remains readable during rework.
                if task and task['status'] in {'rework', 'blocked'} and task.get('latest_handoff') == handoff_path:
                    is_current = False
                if task and task['status'] == 'accepted' and task.get('latest_handoff') == handoff_path:
                    is_current = True
                design_task = by_id.get(ref.get('task_id'))
                if is_current and design_dependencies and ref.get('task_id') not in design_dependencies:
                    errors.append(f'{context}: design_ref does not match required design task')
                if not design_task or design_task['kind'] != 'design':
                    errors.append(f'{context}: design_ref does not cite a design task')
                else:
                    if is_current and (design_task['status'] != 'accepted' or design_task.get('latest_handoff') != ref.get('handoff')):
                        errors.append(f'{context}: design_ref is not the accepted design revision')
                    design_h = read(repo_path(ref['handoff']))
                    if design_h.get('task_id') != ref.get('task_id') or design_h.get('producer') != 'trae-design':
                        errors.append(f'{context}: design_ref handoff task mismatch')
                    if not any(r.get('handoff') == ref['handoff'] and r.get('verdict') == 'approved'
                               and r.get('reviewer') == 'antigravity' and r.get('producer') == 'trae-design'
                               and r.get('task_id') == ref['task_id'] and r.get('reviewed_commit') == design_h.get('head_commit')
                               for _, r in reviews):
                        errors.append(f'{context}: design_ref has no approval for cited revision')
                    if not design_h.get('design_manifest') or not repo_path(design_h['design_manifest']).is_file():
                        errors.append(f'{context}: design_ref cited design delivery missing manifest')
                    else:
                        design_m = read(repo_path(design_h['design_manifest']))
                        spec = repo_path(ref.get('spec_file', ''))
                        if ref.get('spec_file') != design_m.get('spec_file') or not spec.is_file() or hashlib.sha256(spec.read_bytes()).hexdigest() != ref.get('spec_sha256'):
                            errors.append(f'{context}: design_ref spec hash mismatch')
        if h.get('design_manifest'):
            manifest_path = repo_path(h['design_manifest'])
            design_prefix = f'design/05-visual-design/{h["task_id"]}/r{h["revision"]}/'
            if not manifest_path.relative_to(ROOT).as_posix().startswith(design_prefix):
                errors.append(f'{context}: design manifest outside task revision directory')
            m = read(manifest_path)
            if m.get('schema_version') != 1 or m.get('task_id') != h.get('task_id') or m.get('producer') != 'trae-design' or m.get('producer') != h.get('producer') or m.get('revision') != h.get('revision'):
                errors.append(f'{context}: design manifest identity mismatch')
            files = m.get('files', [])
            roles = {f.get('role') for f in files}
            if not {'spec', 'source', 'prompt', 'preview'}.issubset(roles):
                errors.append(f'{context}: design package missing source/spec/prompt/preview')
            if m.get('spec_file') not in {f.get('path') for f in files if f.get('role') == 'spec'}:
                errors.append(f'{context}: design spec not present in manifest')
            for artifact in files:
                p = repo_path(artifact['path'])
                canonical = p.relative_to(ROOT).as_posix()
                if canonical != artifact['path'] or not canonical.startswith(design_prefix):
                    errors.append(f'{context}: design output outside task revision directory or noncanonical path')
                if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != artifact.get('sha256'):
                    errors.append(f'{context}: design artifact hash mismatch {artifact["path"]}')
                if p.is_file() and p.stat().st_size != artifact.get('bytes'):
                    errors.append(f'{context}: design artifact byte count mismatch {artifact["path"]}')
    for path, r in reviews:
        context = path.name
        if not r.get('handoff') or not repo_path(r['handoff']).is_file():
            errors.append(f'{context}: missing handoff {r.get("handoff")}')
            continue
        h = read(repo_path(r['handoff']))
        if r.get('reviewer') != 'antigravity' or r.get('reviewer') == h.get('producer'):
            errors.append(f'{context}: not an independent review')
        if r.get('verdict') not in {'approved', 'changes_requested', 'blocked'}:
            errors.append(f'{context}: invalid verdict')
        if r.get('reviewed_commit') != h.get('head_commit') or r.get('task_id') != h.get('task_id') or r.get('producer') != h.get('producer'):
            errors.append(f'{context}: stale/mismatched approval')
        if not repo_path(r.get('report', '')).is_file(): errors.append(f'{context}: missing review report')
        checks(r.get('checks', []), context, errors)
        if r.get('verdict') == 'approved':
            if not any(c.get('status') == 'passed' for c in r.get('checks', [])):
                errors.append(f'{context}: approved without any evidenced passed check')
            if any(c.get('status') == 'failed' for c in r.get('checks', [])):
                errors.append(f'{context}: approved with a failed current check')
        if r.get('verdict') == 'approved' and h.get('asset_manifest'):
            m = read(repo_path(h['asset_manifest']))
            expected = {l['file']: l['sha256'] for l in m['layers']}
            if r.get('artifact_hashes') != expected: errors.append(f'{context}: approval missing exact candidate hashes')
        if r.get('verdict') == 'approved' and h.get('design_manifest'):
            m = read(repo_path(h['design_manifest']))
            expected = {f['path']: f['sha256'] for f in m['files']}
            if r.get('artifact_hashes') != expected:
                errors.append(f'{context}: approval missing exact design hashes')
    # Preserve the historical CI proof: counters and hashes must remain consistent.
    for path in (BASE / 'evidence').glob('*/test-summary.json'):
        s = read(path); total = dict(tests=0, failures=0, errors=0, skipped=0)
        for suite in s['suites']:
            p = repo_path(suite['file'])
            if hashlib.sha256(p.read_bytes()).hexdigest() != suite['sha256']:
                errors.append(f'{path.name}: archived XML hash mismatch')
            attrs = ET.parse(p).getroot().attrib
            values = {k: int(attrs.get(k, 0)) for k in total}
            if values != suite['counts']: errors.append(f'{path.name}: suite counts mismatch')
            for k, v in values.items(): total[k] += v
        if total != s['counts']: errors.append(f'{path.name}: total counts mismatch')
    # Local Markdown navigation only; fragments/external URLs are not QA evidence.
    for path in BASE.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if target.startswith(('http://', 'https://', '#')): continue
            target = target.split('#', 1)[0]
            if target and not (path.parent / target).resolve().exists():
                errors.append(f'{path.relative_to(ROOT)}: broken link {target}')
    return errors


def board_text() -> str:
    r = read(BASE / 'registry.json')
    lines = ['# 协作任务看板', '', '> 自动生成：仅编辑 registry.json，再执行 python3 tools/collaboration.py render。状态是交付登记，不是产品最终验收。', '',
             f'基线：`{r["baseline_commit"][:7]}` · 更新日期：{r["updated_on"]} · 协调者：{r["coordinator"]}', '',
             '| ID | 任务 | 负责者 | 状态 | 前置 | 已入库交付 / 审核 |', '| --- | --- | --- | --- | --- | --- |']
    def link(p):
        return f'[{Path(p).stem}]({Path(p).relative_to(Path("docs/collaboration")).as_posix()})' if p else '—'
    for t in r['tasks']:
        lines.append(f'| {t["id"]} | [{t["title"]}]({Path(t["task_file"]).relative_to(Path("docs/collaboration"))}) | {t["owner"]} | {t["status"]} | {", ".join(t["depends_on"]) or "—"} | {link(t.get("latest_handoff"))} / {link(t.get("latest_review"))} |')
    observed = [t for t in r['tasks'] if t.get('observed_delivery')]
    if observed:
        lines += ['', '## 远端交付观察（尚非独立批准）', '',
                  '上表交付/审核指已入库记录；下面的新轮次由协调者消费后再更新正式指针。远端head变化须重新核对，不能从观察直接accepted。', '',
                  '| 任务/轮次 | PR或分支 | 观察交付head | 来源 |', '| --- | --- | --- | --- |']
        for t in observed:
            d = t['observed_delivery']
            location = f'[PR]({d["pr_url"]})' if d.get('pr_url') else f'`{d["branch"]}`'
            lines.append(f'| {t["id"]} R{d["revision"]} | {location} | `{d["branch_head"][:7]}` | {link(d["source_report"])} |')
    if r.get('review_queue'):
        lines += ['', f'持续审稿与下一步：{link(r["review_queue"])}。协调轮完成不等于产品验收完成。']
    lines += ['', '## 生产者状态（辅助，不能替代审核）', '', '| 角色 | 当前任务 | 自报状态 | 最近交付 |', '| --- | --- | --- | --- |']
    for role in sorted(ROLES):
        lines.append(f'| {role} | [查看本角色实时状态](state/{role}.json) | 生产者单写 | [查看交付目录](handoffs/README.md) |')
    lines += ['', '## 实体验证仍待完成', ''] + [f'- {p}' for p in r['physical_validation_pending']] + ['']
    return '\n'.join(lines)


def immutable_history_errors(base_ref: str | None) -> list[str]:
    if not base_ref or base_ref == '0' * 40:
        return []
    if not SHA.fullmatch(base_ref):
        return ['history: base-ref must be an exact 40-character commit SHA']
    diff = subprocess.run(['git', 'diff', '--name-status', '--no-renames', base_ref, 'HEAD', '--', 'docs/collaboration/'], cwd=ROOT, capture_output=True, text=True)
    if diff.returncode:
        return ['history: base commit unavailable; fetch it before checking']
    errors = []
    protected = ('docs/collaboration/handoffs/', 'docs/collaboration/reviews/', 'docs/collaboration/evidence/', 'docs/collaboration/decisions/')
    for line in diff.stdout.splitlines():
        status, path = line.split('\t', 1)
        if status != 'A' and path.startswith(protected) and path != 'docs/collaboration/handoffs/README.md':
            errors.append(f'history: existing record changed/deleted {path}; add a new revision/correction instead')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'render'])
    parser.add_argument('--base-ref', help='Exact prior commit SHA; reject rewriting existing audit records')
    args = parser.parse_args()
    try:
        errors = validate()
        errors += immutable_history_errors(args.base_ref)
        if args.command == 'render' and not errors:
            (BASE / 'BOARD.md').write_text(board_text(), encoding='utf-8')
        if args.command == 'check' and (BASE / 'BOARD.md').read_text(encoding='utf-8') != board_text():
            errors.append('BOARD.md stale: run render')
    except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as e:
        errors = [f'Invalid coordination input: {e}']
    if errors:
        print('\n'.join(errors), file=sys.stderr); return 1
    print(f'Coordination {args.command}: OK (structure/dependencies/hashes; not runtime QA)')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
