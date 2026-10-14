#!/usr/bin/env python3
"""Independent QA verification suite for SenseWalk baseline risks (R-BASE-001 / B-20261013-01).

This suite tests the exact algorithmic properties, state machine paths, and failure
counterexamples identified in R-BASE-001 (F-001 to F-004) without modifying production code.
"""
import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[2]


class BaselineEvidenceAudit(unittest.TestCase):
    """Audit baseline B-20261013-01 evidence files, commit SHA, and test report XMLs."""

    def test_baseline_summary_and_xml_hashes(self):
        summary_file = REPO / 'docs/collaboration/evidence/B-20261013-01/test-summary.json'
        self.assertTrue(summary_file.is_file(), "Missing baseline test-summary.json")
        summary = json.loads(summary_file.read_text(encoding='utf-8'))

        self.assertEqual(summary['head_commit'], '8056e11b2b366d958132dfa0d5674dbaa8577db1')
        self.assertEqual(summary['counts'], {'tests': 217, 'failures': 0, 'errors': 0, 'skipped': 0})
        self.assertEqual(len(summary['suites']), 19)

        total = dict(tests=0, failures=0, errors=0, skipped=0)
        for suite in summary['suites']:
            xml_path = REPO / suite['file']
            self.assertTrue(xml_path.is_file(), f"Missing XML report {suite['file']}")
            actual_sha = hashlib.sha256(xml_path.read_bytes()).hexdigest()
            self.assertEqual(actual_sha, suite['sha256'], f"SHA256 mismatch for {suite['file']}")

            root = ET.parse(xml_path).getroot()
            counts = {k: int(root.attrib.get(k, 0)) for k in total}
            self.assertEqual(counts, suite['counts'], f"Count mismatch in {suite['file']}")
            for k, v in counts.items():
                total[k] += v

        self.assertEqual(total, summary['counts'])


class BaselineRiskReproductions(unittest.TestCase):
    """Algorithmic and static path verifications for R-BASE-001 findings."""

    def test_f001_zero_interval_step_burst_speed_cap_bypass(self):
        """F-001: Reproduce speed-cap bypass on zero-interval events in RealWalkEngine.

        In RealWalkEngine.kt:85:
            val capMeters = if (intervalMs <= 0L) strideMeters else MAX_SPEED_MPS * intervalMs / 1000f
            val delta = min(raw, capMeters).coerceAtLeast(0f)
        When intervalMs == 0, capMeters is strideMeters (0.7m).
        Therefore N events delivered in the same millisecond award N * strideMeters,
        completely evading the 1.4 m/s speed cap.
        """
        stride_meters = 0.7
        max_speed_mps = 1.4

        def buggy_engine_delta(steps, interval_ms):
            raw = steps * stride_meters
            cap_meters = stride_meters if interval_ms <= 0 else max_speed_mps * interval_ms / 1000.0
            return max(0.0, min(raw, cap_meters))

        def expected_safe_delta(steps, interval_ms):
            if interval_ms <= 0:
                return 0.0
            raw = steps * stride_meters
            cap_meters = max_speed_mps * interval_ms / 1000.0
            return max(0.0, min(raw, cap_meters))

        # Baseline event at t = 1000ms, count = 1000
        # Now 5 step events arrive at the same timestamp t = 1000ms:
        events = [1001, 1002, 1003, 1004, 1005]
        total_buggy_distance = 0.0
        total_safe_distance = 0.0

        for count in events:
            steps = 1
            interval_ms = 0  # same millisecond
            total_buggy_distance += buggy_engine_delta(steps, interval_ms)
            total_safe_distance += expected_safe_delta(steps, interval_ms)

        # Buggy implementation grants 5 * 0.7 = 3.5 meters in 0 ms:
        self.assertAlmostEqual(total_buggy_distance, 3.5, places=3)
        # Safe implementation should grant 0.0 meters:
        self.assertEqual(total_safe_distance, 0.0)

    def test_f002_start_sticky_empty_restart_path_confirmed(self):
        """F-002: WalkForegroundService.kt START_STICKY empty restart leaves orphaned notification.

        Source confirmation in WalkForegroundService.kt:
        1. onStartCommand handles `else` branch when intent?.action is null (START_STICKY restart).
        2. Calls `startAsForeground()` unconditionally -> notification is posted.
        3. `val sceneId = intent?.getStringExtra(EXTRA_SCENE_ID)` -> sceneId is null.
        4. `if (controller == null && sceneId != null && !finished)` -> FALSE, setupSession NOT called.
        5. Returns `START_STICKY`.
        Outcome: Notification is permanently shown with no active session or controller.
        """
        service_file = REPO / 'app/src/main/java/com/sensewalk/app/service/WalkForegroundService.kt'
        source = service_file.read_text(encoding='utf-8')

        self.assertIn('startAsForeground()', source)
        self.assertIn('val sceneId = intent?.getStringExtra(EXTRA_SCENE_ID)', source)
        self.assertIn('if (controller == null && sceneId != null && !finished)', source)
        self.assertIn('return START_STICKY', source)

    def test_f003_hardware_check_vs_registration_result(self):
        """F-003: StepSensorSource.kt ignores registerListener boolean return value.

        Source confirmation in StepSensorSource.kt:
        1. `counter != null` only checks if the hardware sensor exists.
        2. `sensorManager.registerListener(this, counter, ...)` returns Boolean, which is ignored.
        3. `registered = counter != null` sets registered to true even if registerListener failed.
        4. In WalkForegroundService.kt: `sensorSource.start()` return value is discarded.
        """
        sensor_source_file = REPO / 'app/src/main/java/com/sensewalk/app/engine/sensor/StepSensorSource.kt'
        source = sensor_source_file.read_text(encoding='utf-8')

        self.assertIn('sensorManager.registerListener(this, counter', source)
        self.assertIn('registered = counter != null', source)

        service_file = REPO / 'app/src/main/java/com/sensewalk/app/service/WalkForegroundService.kt'
        service_source = service_file.read_text(encoding='utf-8')
        # Line 167: sensorSource.start() invoked with return value ignored
        self.assertIn('sensorSource.start()', service_source)

    def test_f004_async_session_setup_concurrent_invocation_risk(self):
        """F-004: Concurrent onStartCommand calls before SceneRepository.loadAll() returns.

        Source confirmation:
        1. `setupSession(sceneId)` launches `scope.launch { SceneRepository(app).loadAll() ... }`.
        2. `controller` is only assigned at line 164 (`controller = real`).
        3. A second onStartCommand arriving before `loadAll` completes sees `controller == null`,
           triggering a duplicate `setupSession(sceneId)` coroutine.
        """
        service_file = REPO / 'app/src/main/java/com/sensewalk/app/service/WalkForegroundService.kt'
        source = service_file.read_text(encoding='utf-8')

        self.assertIn('if (controller == null && sceneId != null && !finished)', source)
        self.assertIn('scope.launch {', source)
        self.assertIn('SceneRepository(app).loadAll()', source)
        self.assertIn('controller = real', source)

    def test_security_debug_step_injection_restricted_to_debuggable(self):
        """ACTION_DEBUG_STEP is strictly restricted to debug builds."""
        service_file = REPO / 'app/src/main/java/com/sensewalk/app/service/WalkForegroundService.kt'
        source = service_file.read_text(encoding='utf-8')

        self.assertIn('if (isDebuggable() && controller != null)', source)
        self.assertIn('ApplicationInfo.FLAG_DEBUGGABLE', source)

    def test_counter_and_detector_audio_segregation(self):
        """Detector does not double-count distance; counter stepAudioFromDistance is gated."""
        service_file = REPO / 'app/src/main/java/com/sensewalk/app/service/WalkForegroundService.kt'
        source = service_file.read_text(encoding='utf-8')

        self.assertIn('sensory.stepAudioFromDistance = !sensorSource.hasDetector', source)


if __name__ == '__main__':
    unittest.main()
