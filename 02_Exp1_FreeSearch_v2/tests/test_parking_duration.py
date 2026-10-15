#!/usr/bin/env python3
"""Unit tests for Milestone 1C-2 parking-duration generation."""

from __future__ import annotations

import math
import statistics
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.parking_duration import (  # noqa: E402
    ParkingDurationError,
    derive_stream_seed,
    duration_fingerprint,
    generate_lognormal_durations,
    lognormal_parameters_from_mean_cv,
)


class ParkingDurationTests(unittest.TestCase):
    def test_mean_cv_conversion(self):
        mean_s = 1800.0
        cv = 0.5
        mu, sigma = lognormal_parameters_from_mean_cv(mean_s, cv)

        reconstructed_mean = math.exp(mu + 0.5 * sigma * sigma)
        reconstructed_cv = math.sqrt(math.exp(sigma * sigma) - 1.0)

        self.assertAlmostEqual(reconstructed_mean, mean_s, places=9)
        self.assertAlmostEqual(reconstructed_cv, cv, places=12)

    def test_same_seed_reproduces_exact_durations(self):
        ids = [f"veh_{i}" for i in range(100)]
        a = generate_lognormal_durations(ids, 1800.0, 0.5, seed=123)
        b = generate_lognormal_durations(ids, 1800.0, 0.5, seed=123)
        self.assertEqual(a, b)
        self.assertEqual(duration_fingerprint(a), duration_fingerprint(b))

    def test_different_seed_changes_durations(self):
        ids = [f"veh_{i}" for i in range(50)]
        a = generate_lognormal_durations(ids, 1800.0, 0.5, seed=1)
        b = generate_lognormal_durations(ids, 1800.0, 0.5, seed=2)
        self.assertNotEqual(a, b)
        self.assertNotEqual(duration_fingerprint(a), duration_fingerprint(b))

    def test_all_durations_are_positive_and_finite(self):
        ids = [f"veh_{i}" for i in range(1000)]
        events = generate_lognormal_durations(
            ids, 1800.0, 0.8, seed=10
        )
        self.assertTrue(
            all(
                math.isfinite(e.parking_duration_s)
                and e.parking_duration_s > 0
                for e in events
            )
        )

    def test_zero_cv_returns_constant_duration(self):
        ids = ["a", "b", "c"]
        events = generate_lognormal_durations(
            ids, 900.0, 0.0, seed=10
        )
        self.assertEqual(
            [e.parking_duration_s for e in events],
            [900.0, 900.0, 900.0],
        )

    def test_long_run_mean_and_cv_are_reasonable(self):
        mean_s = 1800.0
        cv = 0.5
        ids = [f"veh_{i}" for i in range(50000)]
        events = generate_lognormal_durations(
            ids, mean_s, cv, seed=20261001
        )
        values = [e.parking_duration_s for e in events]

        sample_mean = statistics.fmean(values)
        sample_cv = statistics.stdev(values) / sample_mean

        self.assertLess(abs(sample_mean / mean_s - 1.0), 0.03)
        self.assertLess(abs(sample_cv - cv), 0.03)

    def test_stream_seed_derivation_is_stable_and_separated(self):
        master = 10
        a1 = derive_stream_seed(master, "arrival")
        a2 = derive_stream_seed(master, "arrival")
        p = derive_stream_seed(master, "parking_duration")

        self.assertEqual(a1, a2)
        self.assertNotEqual(a1, p)

    def test_invalid_parameters_are_rejected(self):
        with self.assertRaises(ParkingDurationError):
            lognormal_parameters_from_mean_cv(0.0, 0.5)
        with self.assertRaises(ParkingDurationError):
            lognormal_parameters_from_mean_cv(1800.0, -0.1)
        with self.assertRaises(ParkingDurationError):
            derive_stream_seed(10, "")
        with self.assertRaises(ParkingDurationError):
            generate_lognormal_durations(
                ["veh0", "veh0"], 1800.0, 0.5, seed=10
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
