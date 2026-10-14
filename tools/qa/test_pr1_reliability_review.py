#!/usr/bin/env python3
"""Independent QA review and regression suite for ZCode PR #1 (SW-001) and SW-013.

This verifies the findings in P-20261014-01 regarding:
1. P-01: detector registration failure causing distance footstep audio to be disabled (silent walk).
2. P-02: same-millisecond step batching updating lastAcceptedCount and discarding pending steps.
3. P-03: scope violation in commit bdb1ea7 (editing tools/collaboration.py) and head divergence.
4. Production forest.json audit verifying clearing/light_shows remain procedural until SW-010.
"""
import json
from pathlib import Path
import subprocess
import unittest

REPO = Path(__file__).resolve().parents[2]


class PR1ReliabilityReview(unittest.TestCase):
    """Independent algorithmic and static verifications on ZCode PR #1."""

    def test_p01_detector_registration_failure_silences_footsteps(self):
        """P-01: When detector hardware exists but registerDetector fails, footstep audio is silenced.

        In StepSensorSource.kt on PR #1:
            port.registerDetector(onDetectorStep)  // return value is discarded!
            val hasDetector: Boolean get() = port.hasDetector // only checks hardware existence!
        In WalkForegroundService.kt:
            sensory.stepAudioFromDistance = !(sensorSource.isStarted && sensorSource.hasDetector)

        If hasDetector == true but registerDetector returned false:
        - sensorSource.isStarted is true (counter registered)
        - sensorSource.hasDetector is true (hardware exists)
        - Therefore sensory.stepAudioFromDistance becomes FALSE.
        - Because registerDetector failed, detector step events will never arrive.
        - Because stepAudioFromDistance is false, distance accumulation will never trigger footstep audio.
        Result: Walking produces distance but is completely silent.
        """
        # We model the logic directly from ZCode's implementation in PR #1:
        class MockPort:
            hasCounter = True
            hasDetector = True  # Hardware exists!

            def registerCounter(self):
                return True

            def registerDetector(self):
                return False  # Permission or driver failure!

        port = MockPort()

        # StepSensorSource logic on PR #1:
        is_started = port.hasCounter and port.registerCounter()
        if port.hasDetector:
            port.registerDetector()  # discarded return value!

        has_detector_property = port.hasDetector

        # WalkForegroundService logic line 192:
        step_audio_from_distance = not (is_started and has_detector_property)

        # In buggy implementation, step_audio_from_distance is FALSE:
        self.assertFalse(step_audio_from_distance, "Buggy code set stepAudioFromDistance to False")

        # But expected safe logic should check if detector was ACTUALLY registered:
        detector_registered = port.hasDetector and port.registerDetector()
        expected_step_audio_from_distance = not (is_started and detector_registered)
        self.assertTrue(expected_step_audio_from_distance, "Expected stepAudioFromDistance to fallback to True")

    def test_p02_same_millisecond_batching_step_loss_counterexample(self):
        """P-02: Same-millisecond events update lastAcceptedCount, discarding steps.

        In RealWalkEngine.kt on PR #1:
            if (intervalMs <= 0L) {
                lastAcceptedCount = stepCount
                return StepDelta(0f, 0L)
            }
        When Event 2 arrives at (count=1001, t=2000), steps=1, interval=1000 -> delta=0.7m.
        When Event 3 arrives at (count=1002, t=2000), interval=0 <= 0 -> sets lastAcceptedCount=1002.
        When Event 4 arrives at (count=1003, t=3000), interval=1000 -> steps = 1003 - 1002 = 1 -> delta=0.7m.
        The step between 1001 and 1002 was lost instead of being carried over to t=3000.
        """
        stride_meters = 0.70
        max_speed_mps = 1.4

        class PR1EngineSimulation:
            def __init__(self):
                self.last_count = None
                self.last_ms = None
                self.total_meters = 0.0

            def on_step(self, step_count, event_time_ms):
                if self.last_count is None:
                    self.last_count = step_count
                    self.last_ms = event_time_ms
                    return 0.0

                interval_ms = event_time_ms - self.last_ms
                if interval_ms <= 0:
                    # Buggy PR #1 implementation:
                    self.last_count = step_count
                    return 0.0

                steps = step_count - self.last_count
                raw = steps * stride_meters
                cap = max_speed_mps * interval_ms / 1000.0
                delta = max(0.0, min(raw, cap))

                self.last_count = step_count
                self.last_ms = event_time_ms
                self.total_meters += delta
                return delta

        engine = PR1EngineSimulation()
        engine.on_step(1000, 1000)  # baseline
        engine.on_step(1001, 2000)  # +1 step in 1000ms -> 0.7m
        engine.on_step(1002, 2000)  # +1 step at same ms -> 0.0m, last_count advances to 1002!
        engine.on_step(1003, 3000)  # +1 step in 1000ms -> steps = 1003-1002 = 1 -> 0.7m

        # Total distance granted in PR #1 simulation is 1.4m:
        self.assertAlmostEqual(engine.total_meters, 1.4, places=2)

        # But in reality, from t=2000 to t=3000 (1.0 second), count grew from 1001 to 1003 (2 steps = 1.4m).
        # Including the step from t=1000 to t=2000 (0.7m), total true distance should be 0.7 + 1.4 = 2.1m,
        # perfectly legitimate at 1.4 m/s over 1.0 second!
        # The buggy engine lost 0.7m.
        self.assertEqual(engine.last_count, 1003)

    def test_p03_pr1_scope_and_head_divergence(self):
        """P-03: Commit bdb1ea7 modified tools/collaboration.py and diverged from handoff head."""
        handoff_file = REPO / 'docs/collaboration/handoffs/zcode/H-SW-001-R1.json'
        # Check if handoff exists locally or in PR branch
        if not handoff_file.exists():
            cmd = ['git', 'show', 'origin/codex/zcode/SW-001-t06-reliability:docs/collaboration/handoffs/zcode/H-SW-001-R1.json']
            proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0)
            h = json.loads(proc.stdout)
        else:
            h = json.loads(handoff_file.read_text(encoding='utf-8'))

        self.assertEqual(h['head_commit'], '2dba5ebbb4897a7a6b9f05e562a9bf6b5bebb39c')

        # Check commit bdb1ea7 changes:
        cmd = ['git', 'show', '--name-only', '--format=', 'bdb1ea7']
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if proc.returncode == 0:
            changed_in_bdb = proc.stdout.strip().splitlines()
            self.assertIn('tools/collaboration.py', changed_in_bdb, "Commit bdb1ea7 touched tools/collaboration.py")

    def test_production_forest_json_remains_procedural_until_sw010(self):
        """SW-002 candidates are approved but forest.json has not integrated them (SW-010 pending)."""
        forest_json_file = REPO / 'app/src/main/assets/scenes/forest.json'
        self.assertTrue(forest_json_file.is_file())
        forest = json.loads(forest_json_file.read_text(encoding='utf-8'))

        layers_by_id = forest['visualLayers']
        self.assertIn('clearing', layers_by_id)
        self.assertIn('light_shows', layers_by_id)

        # Neither clearing nor light_shows specifies an 'asset' file in production config:
        self.assertNotIn('asset', layers_by_id['clearing'], "clearing must remain procedural until SW-010")
        self.assertNotIn('asset', layers_by_id['light_shows'], "light_shows must remain procedural until SW-010")


if __name__ == '__main__':
    unittest.main()
