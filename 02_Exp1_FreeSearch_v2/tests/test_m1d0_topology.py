#!/usr/bin/env python3
"""Milestone 1D-0 static-audit unit tests (no SUMO / no TraCI)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_m1d0_feasibility import (  # noqa: E402
    build_report, inspect_icce_behavior, inspect_topology,
)


def write_fixture(root: Path, connections: list[tuple[str, str]],
                  parking_edge: str = 'E2') -> tuple[Path, Path]:
    edges = ('E1', 'E2', 'E3', 'E4')
    cxml = '\n'.join(
        f'<connection from="{source}" to="{target}"/>'
        for source, target in connections
    )
    net = root / 'net.xml'
    net.write_text(
        '<net>' + ''.join(f'<edge id="{e}"/>' for e in edges)
        + cxml + '</net>', encoding='utf-8'
    )
    park = root / 'parking.xml'
    park.write_text(
        f'<additional><parkingArea id="PA_Z2_G" lane="{parking_edge}_0" '
        f'roadsideCapacity="50"/></additional>', encoding='utf-8'
    )
    return net, park


class M1D0TopologyTests(unittest.TestCase):
    def test_one_way_chain_has_no_revisit(self):
        with tempfile.TemporaryDirectory() as td:
            net, park = write_fixture(Path(td), [('E1', 'E2'), ('E2', 'E3')])
            result = inspect_topology(net, park)
            self.assertFalse(result['directed_cycle_exists'])
            self.assertEqual(result['revisitable_parking_areas_from_E1'], [])

    def test_return_cycle_through_parking_allows_revisit(self):
        with tempfile.TemporaryDirectory() as td:
            net, park = write_fixture(
                Path(td), [('E1', 'E2'), ('E2', 'E3'), ('E3', 'E2')]
            )
            result = inspect_topology(net, park)
            self.assertTrue(result['directed_cycle_exists'])
            self.assertEqual(
                result['revisitable_parking_areas_from_E1'], ['PA_Z2_G']
            )

    def test_loop_elsewhere_does_not_make_parking_revisitable(self):
        with tempfile.TemporaryDirectory() as td:
            net, park = write_fixture(
                Path(td), [('E1', 'E2'), ('E2', 'E3'),
                           ('E3', 'E4'), ('E4', 'E3')]
            )
            result = inspect_topology(net, park)
            self.assertTrue(result['directed_cycle_exists'])
            self.assertEqual(result['revisitable_parking_areas_from_E1'], [])

    def test_missing_parking_edge_raises(self):
        with tempfile.TemporaryDirectory() as td:
            net, park = write_fixture(
                Path(td), [('E1', 'E2')], parking_edge='MISSING'
            )
            with self.assertRaisesRegex(ValueError, 'missing edge'):
                inspect_topology(net, park)

    def test_icce_source_includes_live_parking_counts(self):
        icce = (
            PROJECT_ROOT.parent / '01_ICCE_2026_Frozen' / 'snapshot'
            / 'sumo_parking' / 'run_simulation.py'
        )
        if not icce.exists():
            self.skipTest('ICCE frozen snapshot was not supplied in test directory')
        result = inspect_icce_behavior(icce)
        self.assertTrue(result['zone_score_queries_live_parking_counts'])
        self.assertTrue(result['top_two_zone_candidates'])
        self.assertTrue(result['uses_acceptance_probability_draw'])

    def test_project_audit_does_not_declare_free_search_ready(self):
        baseline = (
            PROJECT_ROOT.parent / '01_ICCE_2026_Frozen' / 'snapshot'
            / 'sumo_parking' / 'run_simulation.py'
        )
        if not baseline.exists():
            self.skipTest('ICCE frozen snapshot was not supplied in test directory')
        report = build_report(PROJECT_ROOT)
        self.assertEqual(report['static_audit_status'], 'PASS')
        self.assertEqual(
            report['m1d_continuous_search_readiness'], 'HOLD_NO_REVISIT_LOOP'
        )
        self.assertEqual(report['network']['general_capacity_from_XML'], 170)
        self.assertEqual(report['network']['total_capacity_from_XML'], 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)
