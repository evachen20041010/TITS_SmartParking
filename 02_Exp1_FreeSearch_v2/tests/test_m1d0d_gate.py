#!/usr/bin/env python3
"""Synthetic regression tests for M1D-0D geometry and entrance-metric contract."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_m1d0d_gate import (  # noqa: E402
    check_hashes,
    formal_gate_reasons,
    sha256,
)
from scripts.entrance_queue_contract import (  # noqa: E402
    LaneVehicle,
    QueueContractError,
    SustainedSpillbackWindow,
    measure_contiguous_entry_queue,
)


KW = dict(
    lane_length_m=200.0,
    usable_storage_m=190.0,
    lead_distance_tolerance_m=5.0,
    max_intervehicle_gap_m=3.0,
)


class M1D0DQueueContractTests(unittest.TestCase):
    def test_empty_link_has_no_spillback(self):
        result = measure_contiguous_entry_queue([], **KW)
        self.assertEqual(result.contiguous_queued_vehicles, 0)
        self.assertEqual(result.storage_coverage, 0.0)
        self.assertFalse(result.at_90_percent)

    def test_24_contiguous_halted_vehicles_can_cover_90_percent(self):
        vehicles = [LaneVehicle(f"v{i}", 198.0 - 7.5 * i, 5.0, 0.0) for i in range(24)]
        result = measure_contiguous_entry_queue(vehicles, **KW)
        self.assertEqual(result.contiguous_queued_vehicles, 24)
        self.assertGreaterEqual(result.storage_coverage, 0.90)
        self.assertTrue(result.at_90_percent)

    def test_upstream_halt_without_downstream_queue_is_not_spillback(self):
        vehicles = [LaneVehicle("u1", 30.0, 5.0, 0.0)]
        result = measure_contiguous_entry_queue(vehicles, **KW)
        self.assertEqual(result.physical_queue_length_m, 0)
        self.assertFalse(result.at_90_percent)

    def test_queue_cannot_jump_large_gap(self):
        vehicles = [
            LaneVehicle("lead", 198.0, 5.0, 0.0),
            LaneVehicle("isolated", 80.0, 5.0, 0.0),
        ]
        result = measure_contiguous_entry_queue(vehicles, **KW)
        self.assertEqual(result.contiguous_queued_vehicles, 1)
        self.assertFalse(result.at_90_percent)

    def test_moving_front_vehicle_breaks_stopped_queue(self):
        vehicles = [
            LaneVehicle("lead", 198.0, 5.0, 0.1),
            LaneVehicle("follow", 190.0, 5.0, 0.0),
        ]
        result = measure_contiguous_entry_queue(vehicles, **KW)
        self.assertEqual(result.contiguous_queued_vehicles, 0)

    def test_reject_duplicate_ids_and_invalid_inputs(self):
        with self.assertRaises(QueueContractError):
            measure_contiguous_entry_queue(
                [LaneVehicle("a", 198, 5, 0), LaneVehicle("a", 190, 5, 0)],
                **KW,
            )
        with self.assertRaises(QueueContractError):
            measure_contiguous_entry_queue([], lane_length_m=0, usable_storage_m=0,
                                          lead_distance_tolerance_m=5, max_intervehicle_gap_m=3)
        with self.assertRaises(QueueContractError):
            measure_contiguous_entry_queue(
                [LaneVehicle("a", 201, 5, 0)], **KW,
            )

    def test_sustained_event_a_requires_60_continuous_seconds(self):
        tracker = SustainedSpillbackWindow()
        for sec in range(60):
            self.assertFalse(tracker.observe(float(sec), 0.95))
        self.assertTrue(tracker.observe(60.0, 0.95))
        self.assertFalse(tracker.observe(61.0, 0.4))
        self.assertFalse(tracker.observe(62.0, 0.95))

    def test_missing_epoch_breaks_sustained_evidence(self):
        tracker = SustainedSpillbackWindow()
        self.assertFalse(tracker.observe(0.0, 0.99))
        self.assertFalse(tracker.observe(61.0, 0.99))
        with self.assertRaises(QueueContractError):
            tracker.observe(61.0, 0.99)


class M1D0DGeometryGateTests(unittest.TestCase):
    def test_missing_entry_and_approval_stays_on_hold(self):
        reasons = formal_gate_reasons(
            dedicated_entrance=False,
            approved_amendment=False,
            entrance_qc=False,
            behavior_frozen=False,
            detector_verified=False,
        )
        self.assertIn("dedicated_physical_entrance_link", reasons)
        self.assertIn("signed_geometry_sop_amendment", reasons)
        self.assertEqual(len(reasons), 5)

    def test_hash_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "toy.xml"
            p.write_text("version1", encoding="utf-8")
            reference = {"toy.xml": sha256(p)}
            self.assertEqual(check_hashes(Path(d), reference), [])
            p.write_text("version2", encoding="utf-8")
            self.assertEqual(len(check_hashes(Path(d), reference)), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
