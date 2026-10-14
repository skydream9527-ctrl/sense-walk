#!/usr/bin/env python3
"""Protocol boundary tests in disposable repos; these are not Android tests."""
import importlib.util
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

    def handoff(self):
        relative = 'docs/collaboration/handoffs/zcode/H-SW-001-R1.json'
        report = relative.replace('.json', '.md')
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        (self.root / report).write_text('Fixture delivery, not actual project QA')
        h = dict(schema_version=1, id='H-SW-001-R1', task_id='SW-001', revision=1,
                 producer='zcode', recipient='antigravity', base_commit='1'*40,
                 head_commit='2'*40, report=report, changed_files=['app/src/main/Example.kt'],
                 checks=[dict(name='fixture source check', type='source', status='passed', evidence=[report])], artifacts=[], pending=[])
        path.write_text(json.dumps(h))
        return relative, h

    def review(self, handoff):
        relative = 'docs/collaboration/reviews/R-SW-001-R1.json'
        report = relative.replace('.json', '.md')
        (self.root / report).write_text('Fixture independent review, not actual project QA')
        r = dict(schema_version=1, task_id='SW-001', reviewer='antigravity', producer='zcode',
                 handoff=handoff, reviewed_commit='2'*40, verdict='approved', report=report,
                 checks=[dict(name='fixture review', type='source', status='passed', evidence=[report])], artifact_hashes={})
        (self.root / relative).write_text(json.dumps(r))
        return relative, r

    def test_initial_baseline_is_valid(self):
        self.assertEqual([], module.validate())

    def test_unknown_dependency_is_rejected(self):
        self.change_registry(lambda r: r['tasks'][0]['depends_on'].append('SW-MISSING'))
        self.error_contains('unknown dependency')

    def test_dependency_cycle_is_rejected(self):
        self.change_registry(lambda r: r['tasks'][0]['depends_on'].append('SW-004'))
        self.error_contains('dependency cycle')

    def test_queued_dependency_cannot_be_skipped(self):
        self.change_registry(lambda r: r['tasks'][3].update(status='ready'))
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
        new.parent.mkdir(parents=True); new.with_suffix('.md').write_text('fixture')
        new.write_text(json.dumps(h))
        self.error_contains('outside producer scope')

    def test_accepted_without_review_is_rejected(self):
        self.change_registry(lambda r: r['tasks'][0].update(status='accepted'))
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
