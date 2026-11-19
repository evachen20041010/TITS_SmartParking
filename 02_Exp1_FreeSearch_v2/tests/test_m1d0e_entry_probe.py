"""M1D-0E pure-logic tests; no SUMO needed for these five tests."""

import unittest

from scripts.run_m1d0e_entry_probe import (
    EXPECTED, PARK_E1_INDEX, PARK_E2_INDEX,
    entrance_and_return_observed, exit_route, should_park,
    is_service_completion, checked_runtime_entry_length,
)
from scripts.vehicle_state import VehicleState


class TestEntryProbeLogic(unittest.TestCase):
    def test_11_early_first_lap(self) -> None:
        self.assertTrue(should_park("early_park", "E1", 1))
        self.assertFalse(should_park("early_park", "E1", 7))
        self.assertEqual(PARK_E2_INDEX["early_park"], 2)

    def test_12_late_second_lap_only(self) -> None:
        self.assertFalse(should_park("late_park", "E1", 1))
        self.assertTrue(should_park("late_park", "E1", 7))
        self.assertFalse(should_park("late_park", "E2", 7))
        self.assertEqual(PARK_E2_INDEX["late_park"], 8)

    def test_13_both_approaches_observed(self) -> None:
        self.assertTrue(entrance_and_return_observed({v: list(r) for v, r in EXPECTED.items()}))

    def test_14_missing_return_approach_rejected(self) -> None:
        edges = {v: list(r) for v, r in EXPECTED.items()}
        edges["late_park"].remove("E_RD")
        self.assertFalse(entrance_and_return_observed(edges))

    def test_15_normal_service_requires_departing(self) -> None:
        self.assertTrue(is_service_completion(VehicleState.DEPARTING))
        self.assertFalse(is_service_completion(VehicleState.CRUISING))
        self.assertFalse(is_service_completion(VehicleState.PARKED))
        self.assertEqual(exit_route("E2"), ("E2", "E3"))
        with self.assertRaises(ValueError):
            exit_route("E_IN")

    def test_16_runtime_uses_actual_compiled_length(self) -> None:
        self.assertAlmostEqual(checked_runtime_entry_length(142.8, 142.8), 142.8)
        self.assertAlmostEqual(checked_runtime_entry_length(142.82, 142.8), 142.82)

    def test_17_runtime_rejects_nominal_length_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not match compiled"):
            checked_runtime_entry_length(150.0, 142.8)


if __name__ == "__main__":
    unittest.main()
