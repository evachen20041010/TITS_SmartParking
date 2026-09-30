#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from vehicle_state import LifecycleError, VehicleLedger, VehicleState


class VehicleLifecycleTests(unittest.TestCase):
    def test_happy_path_and_mass_balance(self):
        ledger = VehicleLedger()
        ledger.register_arrival("veh0", 10.0)

        for state, t in [
            (VehicleState.ENTRY_QUEUE, 11.0),
            (VehicleState.CRUISING, 12.0),
            (VehicleState.PARKED, 20.0),
            (VehicleState.DEPARTING, 620.0),
            (VehicleState.COMPLETED, 640.0),
        ]:
            ledger.transition("veh0", state, t)
            ledger.assert_mass_balance()

        snap = ledger.snapshot(640.0)
        self.assertEqual(snap["generated_to_date"], 1)
        self.assertEqual(snap["n_completed"], 1)
        self.assertEqual(snap["mass_balance_error"], 0)
        ledger.assert_formal_run_health()

    def test_illegal_transition_is_rejected(self):
        ledger = VehicleLedger()
        ledger.register_arrival("veh0", 0.0)
        with self.assertRaises(LifecycleError):
            ledger.transition("veh0", VehicleState.PARKED, 1.0)

    def test_duplicate_vehicle_id_is_rejected(self):
        ledger = VehicleLedger()
        ledger.register_arrival("veh0", 0.0)
        with self.assertRaises(LifecycleError):
            ledger.register_arrival("veh0", 1.0)

    def test_non_monotonic_time_is_rejected(self):
        ledger = VehicleLedger()
        ledger.register_arrival("veh0", 10.0)
        ledger.transition("veh0", VehicleState.ENTRY_QUEUE, 12.0)
        with self.assertRaises(LifecycleError):
            ledger.transition("veh0", VehicleState.CRUISING, 11.0)

    def test_completed_is_terminal(self):
        ledger = VehicleLedger()
        ledger.register_arrival("veh0", 0.0)
        ledger.transition("veh0", VehicleState.ENTRY_QUEUE, 1.0)
        ledger.transition("veh0", VehicleState.CRUISING, 2.0)
        ledger.transition("veh0", VehicleState.PARKED, 3.0)
        ledger.transition("veh0", VehicleState.DEPARTING, 10.0)
        ledger.transition("veh0", VehicleState.COMPLETED, 11.0)
        with self.assertRaises(LifecycleError):
            ledger.transition("veh0", VehicleState.CRUISING, 12.0)

    def test_removed_error_preserves_balance_but_fails_formal_qc(self):
        ledger = VehicleLedger()
        ledger.register_arrival("veh0", 0.0)
        ledger.transition("veh0", VehicleState.ENTRY_QUEUE, 1.0)
        ledger.transition("veh0", VehicleState.CRUISING, 2.0)
        ledger.mark_removed_error("veh0", 3.0, "unexpected SUMO disappearance")
        ledger.assert_mass_balance()
        self.assertEqual(ledger.counts()["removed_error"], 1)
        with self.assertRaises(LifecycleError):
            ledger.assert_formal_run_health()

    def test_multiple_vehicles_mixed_states(self):
        ledger = VehicleLedger()
        for i in range(4):
            ledger.register_arrival(f"veh{i}", float(i))

        ledger.transition("veh0", VehicleState.ENTRY_QUEUE, 5.0)
        ledger.transition("veh0", VehicleState.CRUISING, 6.0)
        ledger.transition("veh1", VehicleState.ENTRY_QUEUE, 5.0)
        ledger.transition("veh2", VehicleState.ENTRY_QUEUE, 5.0)
        ledger.transition("veh2", VehicleState.CRUISING, 6.0)
        ledger.transition("veh2", VehicleState.PARKED, 7.0)

        c = ledger.counts()
        self.assertEqual(c["outside"], 1)
        self.assertEqual(c["entry_queue"], 1)
        self.assertEqual(c["cruising"], 1)
        self.assertEqual(c["parked"], 1)
        self.assertEqual(c["removed_error"], 0)

        snap = ledger.snapshot(7.0)
        self.assertEqual(snap["generated_to_date"], 4)
        self.assertEqual(snap["mass_balance_accounted"], 4)
        self.assertEqual(snap["mass_balance_error"], 0)
        self.assertEqual(snap["n_active_in_system"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
