#!/usr/bin/env python3
"""Unit tests for Milestone 1C-1 Poisson arrival generation."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.demand_generator import (  # noqa: E402
    DemandError,
    arrival_rate_from_load,
    generate_poisson_arrivals,
    schedule_fingerprint,
)


class DemandGeneratorTests(unittest.TestCase):
    def test_load_to_rate_formula(self):
        rate = arrival_rate_from_load(
            rho=0.90,
            c_eff=170,
            mean_parking_s=1800.0,
        )
        self.assertAlmostEqual(rate, 0.085, places=12)
        self.assertAlmostEqual(rate * 3600.0, 306.0, places=9)

    def test_same_seed_reproduces_exact_schedule(self):
        a = generate_poisson_arrivals(0.02, 0.0, 1000.0, seed=12345)
        b = generate_poisson_arrivals(0.02, 0.0, 1000.0, seed=12345)
        self.assertEqual(a, b)
        self.assertEqual(schedule_fingerprint(a), schedule_fingerprint(b))

    def test_different_seed_changes_schedule(self):
        a = generate_poisson_arrivals(0.02, 0.0, 1000.0, seed=1)
        b = generate_poisson_arrivals(0.02, 0.0, 1000.0, seed=2)
        self.assertNotEqual(a, b)
        self.assertNotEqual(schedule_fingerprint(a), schedule_fingerprint(b))

    def test_arrival_times_are_strictly_increasing_and_bounded(self):
        events = generate_poisson_arrivals(
            rate_per_s=0.10,
            start_time_s=50.0,
            end_time_s=500.0,
            seed=10,
        )
        times = [e.arrival_time_s for e in events]
        self.assertTrue(all(50.0 < t < 500.0 for t in times))
        self.assertTrue(all(t2 > t1 for t1, t2 in zip(times, times[1:])))

    def test_vehicle_ids_are_unique_and_ordered(self):
        events = generate_poisson_arrivals(
            0.05, 0.0, 1000.0, seed=99, id_prefix="arr"
        )
        ids = [e.vehicle_id for e in events]
        self.assertEqual(len(ids), len(set(ids)))
        if ids:
            self.assertEqual(ids[0], "arr_000000")
            self.assertEqual(ids[-1], f"arr_{len(ids)-1:06d}")

    def test_zero_rate_generates_no_arrivals(self):
        events = generate_poisson_arrivals(0.0, 0.0, 3600.0, seed=123)
        self.assertEqual(events, [])

    def test_long_run_count_is_statistically_reasonable(self):
        rate = 0.02
        horizon = 100000.0
        events = generate_poisson_arrivals(
            rate, 0.0, horizon, seed=20260923
        )
        expected = rate * horizon
        sigma = math.sqrt(expected)
        self.assertLessEqual(abs(len(events) - expected), 6.0 * sigma)

    def test_invalid_parameters_are_rejected(self):
        with self.assertRaises(DemandError):
            arrival_rate_from_load(-0.1, 170, 1800.0)
        with self.assertRaises(DemandError):
            arrival_rate_from_load(0.9, 0, 1800.0)
        with self.assertRaises(DemandError):
            arrival_rate_from_load(0.9, 170, 0.0)
        with self.assertRaises(DemandError):
            generate_poisson_arrivals(-0.1, 0.0, 100.0, seed=1)
        with self.assertRaises(DemandError):
            generate_poisson_arrivals(0.1, 100.0, 100.0, seed=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
