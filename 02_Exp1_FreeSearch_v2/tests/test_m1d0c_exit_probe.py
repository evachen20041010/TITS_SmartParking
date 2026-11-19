#!/usr/bin/env python3
"""Static unit tests for M1D-0C route/exiting semantics (no SUMO required)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_m1d0c_exit_probe import (  # noqa: E402
    EARLY_EXPECTED,
    FULL_ROUTE,
    LATE_EXPECTED,
    allow_completed_after,
    exit_route_from,
    should_request_parking,
    validate_inputs,
)
from scripts.vehicle_state import VehicleState  # noqa: E402


class RecirculationExitProbeTests(unittest.TestCase):
    def test_candidate_manifest_and_capacity(self):
        manifest = validate_inputs()
        self.assertEqual(manifest["candidate_id"], "recirculation_v1")
        self.assertFalse(manifest["stage_b_approved"])

    def test_two_pass_route_preserves_first_pass(self):
        self.assertEqual(FULL_ROUTE[:3], ("E1", "E2", "E3"))
        self.assertEqual(FULL_ROUTE[-3:], ("E1", "E2", "E3"))
        self.assertEqual(FULL_ROUTE[3:6], ("E_RU", "E_RW", "E_RD"))
        self.assertEqual(EARLY_EXPECTED, ("E1", "E2", "E3"))
        self.assertEqual(LATE_EXPECTED, FULL_ROUTE)

    def test_exit_route_uses_current_edge(self):
        self.assertEqual(exit_route_from("E2"), ("E2", "E3"))
        self.assertEqual(exit_route_from("E3"), ("E3",))
        for edge in ("E1", "E_RU", ":J2_0_0"):
            with self.assertRaises(ValueError):
                exit_route_from(edge)

    def test_parking_commands_only_on_intended_pass(self):
        self.assertTrue(should_request_parking("early_park", "E1", 0))
        self.assertFalse(should_request_parking("early_park", "E1", 6))
        self.assertFalse(should_request_parking("late_park", "E1", 0))
        self.assertTrue(should_request_parking("late_park", "E1", 6))
        self.assertFalse(should_request_parking("late_park", "E2", 7))

    def test_only_post_parking_departure_is_completed(self):
        for state in VehicleState:
            self.assertEqual(
                allow_completed_after(state),
                state == VehicleState.DEPARTING,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
