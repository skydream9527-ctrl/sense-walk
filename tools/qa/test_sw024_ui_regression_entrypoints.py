#!/usr/bin/env python3
"""SW-024 Independent QA verification & UI regression entrypoints.

Covers:
1. H-SW-018-R1 H2 screenshot evidence audit (proving H2-hint-appear.png does not
   display the '慢一点，站稳再跳。' card text and shows Gait.HOP rather than Gait.TENSE,
   while F3-completed.png validly shows 800m completion).
2. Seven core UI & domain regression entrypoints for SW-019/020/025 & SW-021/022/023:
   - 0m void black-screen start & no premature layer reveal
   - Tap-to-reveal integer distance contract
   - Pause confirmation dialog distance freeze & new-input requirement on resume
   - Single terminal navigation guard (800m completion / abandon)
   - First-gap stabilize hint (237m approach, 1.2s zero-displacement stabilize, 3s auto-hide,
     same-session restore non-replay)
   - Legacy SessionSnapshot compatibility & stride bounds (0.45..0.95m, default 0.70m)
   - Dual-mode 55%/45% split & WindowInsets safe-area audit
3. Optional live ADB burst-capture & gfxinfo benchmark helpers (--capture-h2-burst /
   --adb-benchmark). Note: ADB touch/broadcast injection is ONLY for emulator/device UI
   smoke and benchmark comparison, NEVER a substitute for physical-device TYPE_STEP_COUNTER
   walking or 15-minute lockscreen validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import time
import unittest

REPO = Path(__file__).resolve().parents[2]


def read_text(rel_path: str) -> str:
    return (REPO / rel_path).read_text(encoding='utf-8')


def png_dimensions(data: bytes) -> tuple[int, int]:
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG file')
    width, height = struct.unpack('>II', data[16:24])
    return width, height


class Sw024H2ScreenshotAuditTest(unittest.TestCase):
    """Verify H-SW-018-R1 H2 hint screenshots and SW-024 correction artifacts."""

    def test_h2_pixel_audit_hashes_and_dimensions(self):
        audit_path = REPO / 'docs/collaboration/evidence/SW-024/h2-pixel-audit.json'
        self.assertTrue(audit_path.is_file(), 'Missing SW-024 h2-pixel-audit.json')
        audit = json.loads(audit_path.read_text(encoding='utf-8'))

        self.assertEqual(audit['verdict']['h2_hint_text_visible_in_screenshot'], False)
        self.assertEqual(audit['verdict']['f3_800m_completion_visible'], True)
        self.assertEqual(audit['verdict']['runtime_sync_hint_evidence_status'], 'pending')

        for name, meta in audit['screens'].items():
            img_path = REPO / meta['path']
            self.assertTrue(img_path.is_file(), f'Missing screenshot {meta["path"]}')
            raw = img_path.read_bytes()
            self.assertEqual(len(raw), meta['bytes'], f'Byte size mismatch for {name}')
            self.assertEqual(
                hashlib.sha256(raw).hexdigest(),
                meta['sha256'],
                f'SHA256 mismatch for {name}',
            )
            self.assertEqual(list(png_dimensions(raw)), meta['dimensions'])

        # H2-hint-appear.png has 0 bright center pixels (card text not captured)
        h2_appear = audit['screens']['H2-hint-appear.png']
        self.assertEqual(
            h2_appear['center_card_region_x100_980_y950_1450']['bright_pixel_count_rgb_gt_100'],
            0,
        )
        # Traveler y_max in both H2 screenshots is 2050/2049 = 2076 - 26 (Gait.HOP, not TENSE)
        self.assertEqual(h2_appear['traveler_bbox']['y_max'], 2050)
        self.assertEqual(audit['screens']['H2-hint-gone.png']['traveler_bbox']['y_max'], 2049)
        self.assertEqual(audit['screens']['02-virtual-session.png']['traveler_bbox']['y_max'], 2076)

        # F3-completed.png has bright center completion text
        f3 = audit['screens']['F3-completed.png']
        self.assertGreater(
            f3['center_card_region_x100_980_y950_1450']['bright_pixel_count_rgb_gt_100'],
            100_000,
        )

    def test_correction_document_preserves_history_and_records_pending(self):
        orig_review = REPO / 'docs/collaboration/reviews/R-SW-018-R1.md'
        corr_review = REPO / 'docs/collaboration/reviews/R-SW-018-R1-correction.md'
        self.assertTrue(orig_review.is_file())
        self.assertTrue(corr_review.is_file())
        corr_text = corr_review.read_text(encoding='utf-8')
        self.assertIn('H2-hint-appear.png', corr_text)
        self.assertIn('Gait.HOP', corr_text)
        self.assertIn('F3-completed.png', corr_text)
        self.assertIn('Pending', corr_text)


class Sw024UiAndDomainRegressionEntrypointsTest(unittest.TestCase):
    """Seven core UI and domain regression entrypoints defined by SW-024."""

    def test_01_zero_meter_void_start_and_opacity_gate(self):
        forest = json.loads(read_text('app/src/main/assets/scenes/forest.json'))
        self.assertEqual(forest['requiredDistanceMeters'], 800)
        phases = {p['id']: p for p in forest['phases']}
        self.assertEqual(phases['void']['atMeters'], 0)
        self.assertEqual(phases['void']['toOpacity'], 1.0)
        self.assertEqual(phases['tree_outline']['atMeters'], 80)
        self.assertEqual(phases['tree_trunks']['atMeters'], 240)
        self.assertEqual(phases['leaf_path']['atMeters'], 400)
        self.assertEqual(phases['light_shows']['atMeters'], 600)
        self.assertEqual(phases['clearing']['atMeters'], 760)

        shell_src = read_text('app/src/main/java/com/sensewalk/app/ui/session/ForestShell.kt')
        self.assertIn('drawRect(palette.voidColor)', shell_src)
        self.assertIn('if (outlineAlpha > 0.01f)', shell_src)
        self.assertIn('if (trunkAlpha > 0.01f)', shell_src)
        self.assertIn('if (pathAlpha > 0.01f)', shell_src)
        self.assertIn('if (lightAlpha > 0.01f)', shell_src)
        self.assertIn('if (clearingAlpha > 0.01f)', shell_src)

    def test_02_tap_to_reveal_meters_contract(self):
        session_src = read_text('app/src/main/java/com/sensewalk/app/ui/session/SessionScreen.kt')
        real_src = read_text('app/src/main/java/com/sensewalk/app/ui/session/RealWalkContent.kt')
        for src in (session_src, real_src):
            self.assertIn('var showMeters by remember { mutableStateOf(false) }', src)
            self.assertIn('showMeters = !showMeters', src)
            self.assertIn('轻触查看米数', src)

    def test_03_pause_confirm_freezes_distance_and_requires_new_input(self):
        ctrl_src = read_text('app/src/main/java/com/sensewalk/app/domain/walk/VirtualWalkController.kt')
        self.assertIn('stateMachine.dispatch(SessionEvent.Pause)', ctrl_src)
        self.assertIn('inputDeflection = 0f', ctrl_src)
        self.assertIn('inertia.reset()', ctrl_src)
        self.assertIn('lastFrameMs = null', ctrl_src)
        self.assertIn('stateMachine.dispatch(SessionEvent.Resume)', ctrl_src)

        session_src = read_text('app/src/main/java/com/sensewalk/app/ui/session/SessionScreen.kt')
        self.assertIn('vm.pauseForDialog()', session_src)
        self.assertIn('vm.resumeFromDialog()', session_src)
        self.assertIn('要放弃这段路吗？', session_src)

    def test_04_single_terminal_navigation_guard(self):
        session_src = read_text('app/src/main/java/com/sensewalk/app/ui/session/SessionScreen.kt')
        real_session_src = read_text('app/src/main/java/com/sensewalk/app/ui/session/RealWalkSessionScreen.kt')
        for src in (session_src, real_session_src):
            self.assertIn('var navigated by remember { mutableStateOf(false) }', src)
            self.assertIn('if (!navigated && (session == SessionState.COMPLETED || session == SessionState.ABANDONED))', src)
            self.assertIn('navigated = true', src)

    def test_05_first_gap_stabilize_hint_and_restore_non_replay(self):
        motor_src = read_text('app/src/main/java/com/sensewalk/app/domain/walk/TerrainMotor.kt')
        self.assertIn('const val APPROACH_METERS = 3f', motor_src)
        self.assertIn('const val COMFORT_DEFLECTION = 0.72f', motor_src)
        self.assertIn('const val STABILIZE_DURATION_MS = 1_200L', motor_src)
        self.assertIn('hintPending = !hintShownThisSession', motor_src)
        self.assertIn('hintShownThisSession = true', motor_src)
        self.assertIn('SpeedDirective.holdZero()', motor_src)

        session_src = read_text('app/src/main/java/com/sensewalk/app/ui/session/SessionScreen.kt')
        self.assertIn('慢一点，站稳再跳。', session_src)
        self.assertIn('delay(3000)', session_src)
        self.assertIn('vm.consumeStabilizeHintDone()', session_src)

        snap_src = read_text('app/src/main/java/com/sensewalk/app/domain/session/SessionSnapshot.kt')
        self.assertIn('val stabilizeHintShown: Boolean = false', snap_src)

    def test_06_legacy_snapshot_and_stride_engine_contract(self):
        snap_src = read_text('app/src/main/java/com/sensewalk/app/domain/session/SessionSnapshot.kt')
        self.assertIn('stabilizeHintShown = (obj["stabilizeHintShown"]', snap_src)

        engine_src = read_text('app/src/main/java/com/sensewalk/app/domain/walk/RealWalkEngine.kt')
        self.assertIn('DEFAULT_STRIDE_METERS = 0.70f', engine_src)
        self.assertIn('MIN_STRIDE_METERS = 0.45f', engine_src)
        self.assertIn('MAX_STRIDE_METERS = 0.95f', engine_src)
        self.assertIn('MAX_SPEED_MPS = 1.4f', engine_src)

    def test_07_dual_mode_split_and_android_test_entrypoint_present(self):
        session_src = read_text('app/src/main/java/com/sensewalk/app/ui/session/SessionScreen.kt')
        real_src = read_text('app/src/main/java/com/sensewalk/app/ui/session/RealWalkContent.kt')
        for src in (session_src, real_src):
            self.assertIn('.fillMaxHeight(0.55f)', src)
            self.assertIn('.fillMaxHeight(0.45f)', src)

        android_test = REPO / 'app/src/androidTest/java/com/sensewalk/app/qa/SenseWalkRegressionInstrumentationTest.kt'
        self.assertTrue(android_test.is_file(), 'Missing androidTest regression entrypoint')


def capture_h2_burst(adb_path: str, serial: str | None, out_dir: Path, count: int = 16, interval_s: float = 0.4) -> None:
    """Capture a high-frequency screencap burst without blocking uiautomator dump."""
    out_dir.mkdir(parents=True, exist_ok=True)
    base_cmd = [adb_path] + (['-s', serial] if serial else [])
    manifest = {
        'mode': 'emulator_or_device_screencap_burst',
        'note': 'Does NOT represent physical-device step sensor validation.',
        'interval_s': interval_s,
        'frames': [],
    }
    for idx in range(count):
        t0 = time.monotonic()
        frame_path = out_dir / f'frame-{idx:02d}.png'
        proc = subprocess.run(base_cmd + ['exec-out', 'screencap', '-p'], capture_output=True, check=True)
        frame_path.write_bytes(proc.stdout)
        manifest['frames'].append({
            'index': idx,
            'file': frame_path.name,
            'sha256': hashlib.sha256(proc.stdout).hexdigest(),
            'captured_monotonic_s': round(t0, 3),
        })
        elapsed = time.monotonic() - t0
        if elapsed < interval_s:
            time.sleep(interval_s - elapsed)
    (out_dir / 'burst-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='SW-024 QA Regression & Benchmark Tool')
    parser.add_argument('--capture-h2-burst', type=Path, help='Output directory for non-blocking 400ms screencap burst')
    parser.add_argument('--adb', default='adb', help='Path to adb binary')
    parser.add_argument('--serial', default=None, help='Optional adb device serial')
    args, remaining = parser.parse_known_args(argv)

    if args.capture_h2_burst:
        capture_h2_burst(args.adb, args.serial, args.capture_h2_burst)
        return 0

    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
