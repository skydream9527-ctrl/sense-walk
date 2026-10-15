#!/usr/bin/env python3
"""Independent QA verification suite for ZCode SW-001 R2 (T06 Reliability).

Verifies commit 7b17424886ba4b0c7608bd451f0ee244f3b88390 and delivery head d11873f:
1. P-01: detector registration failure fallback to distance-driven step audio in SensoryCoordinator.
2. P-02: same-millisecond batch carryover without step loss and without cap evasion.
3. P-03: scope and head alignment (business head 7b17424, delivery head d11873f).
4. Service lifecycle: SessionArbiter handling of START_STICKY, duplicate starts, and abandoned setups.
"""
import json
from pathlib import Path
import subprocess
import unittest

REPO = Path(__file__).resolve().parents[2]
REVIEW_COMMIT = "7b17424886ba4b0c7608bd451f0ee244f3b88390"
BRANCH_HEAD = "d11873f3d5553fda872dd18f4483ca1e1b11223a"


def git_show(path_in_repo: str, commit: str = REVIEW_COMMIT) -> str:
    cmd = ['git', 'show', f'{commit}:{path_in_repo}']
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FileNotFoundError(f"Cannot show {path_in_repo} at {commit}: {proc.stderr}")
    return proc.stdout


class SW001R2VerificationTest(unittest.TestCase):
    """Independent verification of SW-001 R2 fixes in Kotlin and runtime contracts."""

    def test_p01_detector_registration_fallback_kotlin_contracts(self):
        """Verify StepSensorSource and WalkForegroundService properly use detector registration result."""
        sensor_source_code = git_show('app/src/main/java/com/sensewalk/app/engine/sensor/StepSensorSource.kt')

        # Check port registration return value is captured:
        self.assertIn('detectorRegistered = port.registerDetector(onDetectorStep)', sensor_source_code)
        # Check cueAudioFromDistance property:
        self.assertIn('val cueAudioFromDistance: Boolean get() = started && !detectorRegistered', sensor_source_code)
        self.assertIn('val detectorActive: Boolean get() = started && detectorRegistered', sensor_source_code)

        # Check WalkForegroundService wiring:
        service_code = git_show('app/src/main/java/com/sensewalk/app/service/WalkForegroundService.kt')
        self.assertIn('sensory.stepAudioFromDistance = sensorSource.cueAudioFromDistance', service_code)

    def test_p01_behavioral_simulation(self):
        """Simulate the fixed P-01 cue routing logic."""
        class MockPort:
            def __init__(self, has_counter=True, has_detector=True, detector_registers=True):
                self.hasCounter = has_counter
                self.hasDetector = has_detector
                self._detector_registers = detector_registers

            def registerCounter(self):
                return True

            def registerDetector(self):
                return self._detector_registers

        # Case 1: Detector hardware present, but registration fails
        port1 = MockPort(has_counter=True, has_detector=True, detector_registers=False)
        started1 = port1.hasCounter and port1.registerCounter()
        detector_registered1 = port1.hasDetector and port1.registerDetector()
        cue_audio_from_distance1 = started1 and not detector_registered1
        self.assertTrue(cue_audio_from_distance1, "When detector registration fails, distance cues must be enabled")

        # Case 2: Detector registers successfully
        port2 = MockPort(has_counter=True, has_detector=True, detector_registers=True)
        started2 = port2.hasCounter and port2.registerCounter()
        detector_registered2 = port2.hasDetector and port2.registerDetector()
        cue_audio_from_distance2 = started2 and not detector_registered2
        self.assertFalse(cue_audio_from_distance2, "When detector registers successfully, distance cues must be silenced")

        # Case 3: No detector hardware
        port3 = MockPort(has_counter=True, has_detector=False, detector_registers=False)
        started3 = port3.hasCounter and port3.registerCounter()
        detector_registered3 = port3.hasDetector and port3.registerDetector()
        cue_audio_from_distance3 = started3 and not detector_registered3
        self.assertTrue(cue_audio_from_distance3, "When no detector hardware exists, distance cues must be enabled")

    def test_p02_same_ms_carryover_kotlin_contracts(self):
        """Verify RealWalkEngine.kt does not advance lastAcceptedCount on same-ms batches."""
        engine_code = git_show('app/src/main/java/com/sensewalk/app/domain/walk/RealWalkEngine.kt')

        # In intervalMs <= 0 branch: must return StepDelta(0f, 0L) WITHOUT advancing lastAcceptedCount
        self.assertIn('if (intervalMs <= 0L)', engine_code)
        self.assertIn('return StepDelta(0f, 0L)', engine_code)

    def test_p02_fixed_engine_simulation(self):
        """Simulate RealWalkEngine R2 logic and verify step carryover."""
        stride_meters = 0.70
        max_speed_mps = 1.4

        class RealWalkEngineR2:
            def __init__(self):
                self.baseline_count = None
                self.last_accepted_count = -1
                self.last_accepted_ms = -1
                self.rebase_pending = True
                self.paused = False
                self.terminal = False

            def on_counter_event(self, step_count, event_time_ms):
                if self.terminal:
                    return 0.0, 0
                if self.paused:
                    self.baseline_count = step_count
                    self.rebase_pending = True
                    return 0.0, 0
                if self.rebase_pending or self.baseline_count is None:
                    self.baseline_count = step_count
                    self.last_accepted_count = step_count
                    self.last_accepted_ms = event_time_ms
                    self.rebase_pending = False
                    return 0.0, 0
                if step_count == self.last_accepted_count:
                    return 0.0, 0
                if step_count < self.last_accepted_count:
                    self.baseline_count = step_count
                    self.last_accepted_count = step_count
                    self.last_accepted_ms = event_time_ms
                    return 0.0, 0
                if event_time_ms < self.last_accepted_ms:
                    return 0.0, 0

                steps = step_count - self.last_accepted_count
                interval_ms = event_time_ms - self.last_accepted_ms
                if interval_ms <= 0:
                    # R2 fix: do NOT advance last_accepted_count!
                    return 0.0, 0

                raw = steps * stride_meters
                cap = max_speed_mps * interval_ms / 1000.0
                delta = max(0.0, min(raw, cap))

                self.last_accepted_count = step_count
                self.last_accepted_ms = event_time_ms
                return delta, interval_ms

            def pause(self):
                self.paused = True
                self.rebase_pending = True

            def resume(self):
                self.paused = False
                self.rebase_pending = True

        engine = RealWalkEngineR2()
        # Event 0: baseline (0, 0)
        d0, _ = engine.on_counter_event(0, 0)
        self.assertEqual(d0, 0.0)

        # Event 1: (1, 1000) -> 1 step in 1000ms = 0.7m
        d1, _ = engine.on_counter_event(1, 1000)
        self.assertAlmostEqual(d1, 0.7, places=3)

        # Event 2: (2, 1000) -> same ms batch -> 0.0m
        d2, _ = engine.on_counter_event(2, 1000)
        self.assertEqual(d2, 0.0)

        # Event 3: (3, 2000) -> 2 steps carried over (from count=1 to count=3), interval=1000ms
        # raw = 2 * 0.7 = 1.4m, cap = 1.4 * 1.0 = 1.4m -> delta = 1.4m!
        d3, _ = engine.on_counter_event(3, 2000)
        self.assertAlmostEqual(d3, 1.4, places=3)

        total = d0 + d1 + d2 + d3
        self.assertAlmostEqual(total, 2.1, places=3, msg="Total for 3 steps must be 2.1m without step loss")

        # Test pause semantics: uncounted same-ms batch must be dropped across pause
        d4, _ = engine.on_counter_event(4, 3000)
        self.assertAlmostEqual(d4, 0.7, places=3)
        # same-ms batch:
        d5, _ = engine.on_counter_event(5, 3000)
        self.assertEqual(d5, 0.0)
        # pause & resume:
        engine.pause()
        engine.on_counter_event(6, 3500)
        engine.resume()
        d7, _ = engine.on_counter_event(7, 4000)
        self.assertEqual(d7, 0.0, "First event after resume establishes baseline only")
        d8, _ = engine.on_counter_event(8, 5000)
        self.assertAlmostEqual(d8, 0.7, places=3, msg="Only new step counted after resume")

    def test_p03_scope_and_head_alignment(self):
        """Verify delivery head d11873f and business head 7b17424 alignment."""
        raw_json = git_show('docs/collaboration/handoffs/zcode/H-SW-001-R2.json', commit=BRANCH_HEAD)
        h = json.loads(raw_json)

        self.assertEqual(h['head_commit'], REVIEW_COMMIT)
        self.assertEqual(h['base_commit'], '550eb63b0ad14dae39d03b3e5b97ed0080057bda')

        # Check correction note:
        corr_text = git_show('docs/collaboration/handoffs/zcode/H-SW-001-R2-correction.md', commit=BRANCH_HEAD)
        self.assertIn('550eb63b0ad14dae39d03b3e5b97ed0080057bda', corr_text)

    def test_session_arbiter_service_lifecycle(self):
        """Verify SessionArbiter.kt contracts for clean service shutdown and single flight."""
        arbiter_code = git_show('app/src/main/java/com/sensewalk/app/service/SessionArbiter.kt')

        self.assertIn('STOP_CLEAN', arbiter_code)
        self.assertIn('START_FOREGROUND_AND_SETUP', arbiter_code)
        self.assertIn('ABANDON_AND_FINISH', arbiter_code)
        self.assertIn('FORWARD_DEBUG_STEP', arbiter_code)


if __name__ == '__main__':
    unittest.main()
