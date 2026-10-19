#!/usr/bin/env python3
"""Protocol boundary tests in disposable repos; these are not Android tests."""
import importlib.util
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('collaboration', REPO / 'tools/collaboration.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CoordinationChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.base = self.root / 'docs/collaboration'
        shutil.copytree(REPO / 'docs/collaboration', self.base)
        if (REPO / 'design').exists():
            shutil.copytree(REPO / 'design', self.root / 'design')
        if (REPO / 'tools').exists():
            shutil.copytree(REPO / 'tools', self.root / 'tools')
        self.old_root, self.old_base = module.ROOT, module.BASE
        module.ROOT, module.BASE = self.root, self.base
        # Non-protocol files are link targets only, not simulated runtime evidence.
        for p in self.base.rglob('*.md'):
            for url in re.findall(r'\]\(([^)]+)\)', p.read_text()):
                if url.startswith(('http://', 'https://', '#')): continue
                target = (p.parent / url.split('#', 1)[0]).resolve()
                if target.is_relative_to(self.root) and not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text('fixture link target')
        self.registry = self.base / 'registry.json'

    def tearDown(self):
        module.ROOT, module.BASE = self.old_root, self.old_base
        self.temp.cleanup()

    def change_registry(self, callback):
        data = module.read(self.registry)
        callback(data)
        self.registry.write_text(json.dumps(data))

    def error_contains(self, text):
        self.assertTrue(any(text in e for e in module.validate()), module.validate())

    def handoff(self, task_id='SW-001', producer='zcode', revision=1):
        relative = f'docs/collaboration/handoffs/{producer}/H-{task_id}-R{revision}.json'
        report = relative.replace('.json', '.md')
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        (self.root / report).write_text('Fixture delivery, not actual project QA')
        h = dict(schema_version=1, id=f'H-{task_id}-R{revision}', task_id=task_id, revision=revision,
                 producer=producer, recipient='antigravity', base_commit='1'*40,
                 head_commit=('2' if revision == 1 else '4')*40, report=report, changed_files=['app/src/main/Example.kt'],
                 checks=[dict(name='fixture source check', type='source', status='passed', evidence=[report])], artifacts=[], pending=[])
        path.write_text(json.dumps(h))
        return relative, h

    def review(self, handoff):
        h = module.read(self.root / handoff)
        relative = f'docs/collaboration/reviews/R-{h["task_id"]}-R{h["revision"]}.json'
        report = relative.replace('.json', '.md')
        (self.root / report).write_text('Fixture independent review, not actual project QA')
        r = dict(schema_version=1, task_id=h['task_id'], reviewer='antigravity', producer=h['producer'],
                 handoff=handoff, reviewed_commit=h['head_commit'], verdict='approved', report=report,
                 checks=[dict(name='fixture review', type='source', status='passed', evidence=[report])], artifact_hashes={})
        (self.root / relative).write_text(json.dumps(r))
        return relative, r

    def design_delivery(self, accepted=False, revision=1):
        relative, h = self.handoff('SW-012', 'trae-design', revision)
        folder = self.root / f'design/05-visual-design/SW-012/r{revision}'
        folder.mkdir(parents=True, exist_ok=True)
        files = []
        # Plain bytes model protocol inputs only, never pretend to be image QA.
        for role, filename in [('spec', 'design-spec.json'), ('source', 'source.svg'),
                               ('prompt', 'prompts.md'), ('preview', 'preview.txt')]:
            path = folder / filename
            path.write_text(json.dumps({'fixture': role, 'revision': revision}))
            files.append(dict(path=str(path.relative_to(self.root)), role=role,
                              sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size))
        manifest = dict(schema_version=1, task_id='SW-012', revision=revision, producer='trae-design',
                        spec_file=files[0]['path'], files=files, limitations=['protocol fixture'])
        manifest_path = folder / 'design-manifest.json'
        manifest_path.write_text(json.dumps(manifest))
        h.update(changed_files=[f['path'] for f in files], design_manifest=str(manifest_path.relative_to(self.root)))
        (self.root / relative).write_text(json.dumps(h))
        if accepted:
            review_path, review = self.review(relative)
            review['artifact_hashes'] = {f['path']: f['sha256'] for f in files}
            (self.root / review_path).write_text(json.dumps(review))
            self.change_registry(lambda data: next(t for t in data['tasks'] if t['id'] == 'SW-012').update(
                status='accepted', latest_handoff=relative, latest_review=review_path, integrated_commit='3'*40))
        else:
            review_path = f'docs/collaboration/reviews/R-SW-012-R{revision}.json'
            (self.root / review_path).unlink(missing_ok=True)
            (self.root / review_path.replace('.json', '.md')).unlink(missing_ok=True)
            self.change_registry(lambda data: next(t for t in data['tasks'] if t['id'] == 'SW-012').update(
                status='handoff_ready', latest_handoff=None, latest_review=None, integrated_commit=None))
        ref = dict(task_id='SW-012', handoff=relative, spec_file=manifest['spec_file'], spec_sha256=files[0]['sha256'])
        for m_path in self.root.glob('design/assets/**/manifest*.json'):
            if not m_path.is_file(): continue
            try:
                m_data = json.loads(m_path.read_text())
                d_ref = m_data.get('design_ref')
                if d_ref and d_ref.get('task_id') == 'SW-012' and d_ref.get('handoff') == relative:
                    d_ref['spec_file'] = manifest['spec_file']
                    d_ref['spec_sha256'] = files[0]['sha256']
                    m_path.write_text(json.dumps(m_data, indent=2))
                    new_m_hash = hashlib.sha256(m_path.read_bytes()).hexdigest()
                    rel_m_path = str(m_path.relative_to(self.root))
                    for h_path in (self.base / 'handoffs').rglob('*.json'):
                        try:
                            h_data = json.loads(h_path.read_text())
                            updated = False
                            for art in h_data.get('artifacts', []):
                                if art.get('path') == rel_m_path:
                                    art['sha256'] = new_m_hash
                                    updated = True
                            if updated:
                                h_path.write_text(json.dumps(h_data, indent=2))
                        except Exception:
                            pass
            except Exception:
                pass
        return relative, h, manifest_path, manifest, ref

    def asset_delivery(self, design_ref=None, revision=1):
        relative, h = self.handoff('SW-006', 'minimax', revision)
        folder = self.root / f'design/assets/rainforest/candidates/fixture/r{revision}'
        folder.mkdir(parents=True, exist_ok=True)
        candidate = folder / 'layer.txt'
        candidate.write_text('protocol fixture, not a generated image')
        manifest = dict(schema_version=1, task_id='SW-006', revision=revision, producer='minimax', design_ref=design_ref,
                        layers=[dict(file=str(candidate.relative_to(self.root)), sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
                                     bytes=candidate.stat().st_size, width=1080, height=1920, checks=[h['report']])])
        manifest_path = folder / 'asset-manifest.json'
        manifest_path.write_text(json.dumps(manifest))
        h.update(changed_files=[str(candidate.relative_to(self.root))], asset_manifest=str(manifest_path.relative_to(self.root)))
        (self.root / relative).write_text(json.dumps(h))
        return manifest_path, manifest

    def test_initial_baseline_is_valid(self):
        self.assertEqual([], module.validate())

    def test_unknown_dependency_is_rejected(self):
        self.change_registry(lambda r: r['tasks'][0]['depends_on'].append('SW-MISSING'))
        self.error_contains('unknown dependency')

    def test_dependency_cycle_is_rejected(self):
        self.change_registry(lambda r: r['tasks'][0]['depends_on'].append('SW-004'))
        self.error_contains('dependency cycle')

    def test_queued_dependency_cannot_be_skipped(self):
        self.change_registry(lambda r: next(t for t in r['tasks'] if t['id'] == 'SW-007').update(status='ready'))
        self.error_contains('active before dependency')

    def test_author_cannot_claim_another_role_task(self):
        path = self.base / 'state/minimax.json'
        state = module.read(path); state.update(current_task='SW-001', status='in_progress')
        path.write_text(json.dumps(state))
        self.error_contains('task not owned')

    def test_state_update_does_not_require_central_board_write(self):
        original = module.board_text()
        path = self.base / 'state/zcode.json'
        state = module.read(path); state.update(current_task='SW-001', status='in_progress')
        path.write_text(json.dumps(state))
        self.assertEqual([], module.validate())
        self.assertEqual(original, module.board_text())

    def test_coordinator_can_accept_before_producer_consumes_notice(self):
        h, _ = self.handoff(); r, _ = self.review(h)
        self.change_registry(lambda data: data['tasks'][0].update(status='accepted', latest_handoff=h, latest_review=r, integrated_commit='3'*40))
        path = self.base / 'state/zcode.json'
        state = module.read(path); state.update(current_task='SW-001', status='handoff_ready', latest_handoff=h)
        path.write_text(json.dumps(state))
        self.assertEqual([], module.validate())

    def test_file_scope_cannot_be_bypassed_with_dotdot(self):
        relative, h = self.handoff()
        h['changed_files'] = ['app/../README.md']
        (self.root / relative).write_text(json.dumps(h))
        self.error_contains('outside producer scope')

    def test_minimax_cannot_report_production_code_changes(self):
        relative, h = self.handoff()
        path = self.root / relative; path.unlink()
        h.update(producer='minimax', task_id='SW-002', report='docs/collaboration/handoffs/minimax/H-SW-002-R1.md')
        new = self.base / 'handoffs/minimax/H-SW-002-R1.json'
        new.parent.mkdir(parents=True, exist_ok=True); new.with_suffix('.md').write_text('fixture')
        new.write_text(json.dumps(h))
        self.error_contains('outside producer scope')

    def test_accepted_without_review_is_rejected(self):
        self.change_registry(lambda r: next(t for t in r['tasks'] if t['id'] == 'SW-007').update(status='accepted'))
        self.error_contains('accepted without delivery')

    def test_matching_independent_approval_is_structurally_valid(self):
        h, _ = self.handoff(); r, _ = self.review(h)
        self.change_registry(lambda data: data['tasks'][0].update(status='accepted', latest_handoff=h, latest_review=r, integrated_commit='3'*40))
        self.assertEqual([], module.validate())

    def test_approval_for_old_head_is_rejected(self):
        h, _ = self.handoff(); relative, review = self.review(h)
        review['reviewed_commit'] = '4'*40
        (self.root / relative).write_text(json.dumps(review))
        self.error_contains('stale/mismatched')

    def test_self_approval_is_rejected(self):
        h, _ = self.handoff(); relative, review = self.review(h)
        review['reviewer'] = 'zcode'
        (self.root / relative).write_text(json.dumps(review))
        self.error_contains('not an independent')

    def test_changed_artifact_hash_is_rejected(self):
        relative, h = self.handoff()
        artifact = self.root / 'docs/collaboration/evidence/artifact.txt'
        artifact.write_text('actual fixture content')
        h['artifacts'] = [dict(path=str(artifact.relative_to(self.root)), sha256='0'*64)]
        (self.root / relative).write_text(json.dumps(h))
        self.error_contains('artifact hash mismatch')

    def test_archived_junit_corruption_is_rejected(self):
        p = next((self.base / 'evidence').rglob('TEST-*.xml'))
        p.write_bytes(p.read_bytes() + b'\n')
        self.error_contains('XML hash mismatch')

    def test_design_accepted_with_exact_independent_hashes_is_valid(self):
        self.design_delivery(accepted=True)
        self.assertEqual([], module.validate())

    def test_trae_cannot_report_production_code_changes(self):
        relative, h, _, _, _ = self.design_delivery()
        h['changed_files'].append('app/src/main/Example.kt')
        (self.root / relative).write_text(json.dumps(h))
        self.error_contains('outside producer scope')

    def test_design_without_manifest_is_rejected(self):
        relative, h, _, _, _ = self.design_delivery()
        del h['design_manifest']
        (self.root / relative).write_text(json.dumps(h))
        self.error_contains('design delivery requires a manifest')

    def test_design_source_changed_after_manifest_is_rejected(self):
        _, _, _, manifest, _ = self.design_delivery()
        source = next(f for f in manifest['files'] if f['role'] == 'source')
        (self.root / source['path']).write_text('changed editable source')
        self.error_contains('design artifact hash mismatch')

    def test_design_approval_without_exact_hashes_is_rejected(self):
        relative, _, _, _, _ = self.design_delivery()
        self.review(relative)
        self.error_contains('approval missing exact design hashes')

    def test_design_manifest_cannot_escape_owned_revision_with_dotdot(self):
        _, _, path, manifest, _ = self.design_delivery()
        source = next(f for f in manifest['files'] if f['role'] == 'source')
        # The resolved file is real, but the apparent owned prefix is misleading.
        escaped = self.root / 'app/fixture.txt'
        escaped.parent.mkdir(parents=True, exist_ok=True)
        escaped.write_text('outside Trae output directory')
        source.update(path='design/05-visual-design/SW-011/r1/../../../../app/fixture.txt',
                      sha256=hashlib.sha256(escaped.read_bytes()).hexdigest(), bytes=escaped.stat().st_size)
        path.write_text(json.dumps(manifest))
        self.error_contains('design output outside task revision directory')

    def test_new_asset_without_design_ref_is_rejected(self):
        self.asset_delivery()
        self.error_contains('requires approved design_ref')

    def test_asset_cannot_consume_unapproved_design(self):
        _, _, _, _, ref = self.design_delivery()
        self.asset_delivery(ref)
        self.error_contains('not the accepted design revision')

    def test_asset_cannot_substitute_other_approved_design(self):
        ref = dict(task_id='SW-011', handoff='docs/collaboration/handoffs/trae-design/H-SW-011-R1.json',
                   spec_file='design/05-visual-design/SW-011/r1/design-spec.json',
                   spec_sha256='f1dc9f2a73cba5a8c9e9363e419cfd851e4a643f598bd999d2d674c758cb5414')
        self.asset_delivery(ref)  # SW-006 requires SW-012, not approved SW-011.
        self.error_contains('does not match required design task')

    def test_asset_old_spec_hash_is_rejected(self):
        _, _, _, _, ref = self.design_delivery(accepted=True)
        ref['spec_sha256'] = '0'*64
        self.asset_delivery(ref)
        self.error_contains('design_ref spec hash mismatch')

    def test_asset_exact_accepted_design_reference_is_valid(self):
        _, _, _, _, ref = self.design_delivery(accepted=True)
        self.asset_delivery(ref)
        self.assertEqual([], module.validate())

    def test_archived_asset_reference_survives_new_approved_design_revision(self):
        _, _, _, _, old_ref = self.design_delivery(accepted=True)
        self.asset_delivery(old_ref)
        _, _, _, _, new_ref = self.design_delivery(accepted=True, revision=2)
        self.asset_delivery(new_ref, revision=2)
        self.assertEqual([], module.validate())

    def test_current_asset_cannot_use_superseded_design_revision(self):
        _, _, _, _, old_ref = self.design_delivery(accepted=True)
        self.asset_delivery(old_ref)
        self.design_delivery(accepted=True, revision=2)
        self.asset_delivery(old_ref, revision=2)
        self.error_contains('not the accepted design revision')

    def test_archived_asset_reference_still_requires_historical_approval(self):
        self.change_registry(lambda data: next(t for t in data['tasks'] if t['id'] == 'SW-006').update(depends_on=['SW-011']))
        _, _, _, _, unapproved_ref = self.design_delivery()
        self.asset_delivery(unapproved_ref)
        _, _, _, _, new_ref = self.design_delivery(accepted=True, revision=2)
        self.asset_delivery(new_ref, revision=2)
        self.error_contains('no approval for cited revision')

    def test_retired_asset_can_remain_visible_during_rework(self):
        _, _, _, _, old_ref = self.design_delivery(accepted=True)
        self.asset_delivery(old_ref)
        self.design_delivery(accepted=True, revision=2)
        self.change_registry(lambda data: next(t for t in data['tasks'] if t['id'] == 'SW-006').update(
            status='rework', depends_on=['SW-011'], latest_handoff='docs/collaboration/handoffs/minimax/H-SW-006-R1.json'))
        self.assertEqual([], module.validate())

    def test_existing_audit_history_cannot_be_rewritten(self):
        def git(*args):
            return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=self.root, stderr=subprocess.DEVNULL, text=True).strip()
        git('init', '-q'); git('config', 'user.name', 'Protocol fixture'); git('config', 'user.email', 'fixture@example.invalid')
        git('add', '.'); git('commit', '-qm', 'fixture baseline'); base = git('rev-parse', 'HEAD')
        p = self.base / 'reviews/R-BASE-001.md'; p.write_text('rewritten history')
        git('add', '.'); git('commit', '-qm', 'fixture overwrite')
        self.assertTrue(any('existing record changed' in e for e in module.immutable_history_errors(base)))


if __name__ == '__main__':
    unittest.main()
