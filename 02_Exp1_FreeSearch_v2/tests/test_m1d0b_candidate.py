#!/usr/bin/env python3
"""M1D-0B static candidate tests; no SUMO or netconvert required."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_m1d0b_candidate import (  # noqa: E402
    CANONICAL,
    CANDIDATE,
    PROBE_EDGES,
    CandidateError,
    build_candidate,
    canonical_hashes,
    check_canonical,
    render_source_files,
)


class RecirculationCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "canonical"
        self.target = self.root / "candidates" / "recirculation_v1"
        self.source.mkdir()
        for name in (
            "parking.nod.xml", "parking.edg.xml", "parking_areas.add.xml",
            "base.sumocfg", "parking_lot.net.xml",
        ):
            shutil.copyfile(CANONICAL / name, self.source / name)

    def test_canonical_assumptions_match_inspected_geometry(self):
        check_canonical(self.source)

    def test_static_build_produces_all_candidate_sources(self):
        result = build_candidate(self.source, self.target, static_only=True)
        self.assertTrue(result["static_source_valid"])
        self.assertFalse(result["compiled_net_valid"])
        for name in (
            "parking.nod.xml", "parking.edg.xml", "parking_areas.add.xml",
            "base.sumocfg", "route_probe.rou.xml", "candidate_manifest.json",
        ):
            self.assertTrue((self.target / name).is_file(), name)

    def test_return_topology_is_directed_cycle(self):
        files = render_source_files(self.source)
        root = ET.fromstring(files["parking.edg.xml"])
        edges = {e.attrib["id"]: (e.attrib["from"], e.attrib["to"]) for e in root.findall("edge")}
        for a, b in zip(PROBE_EDGES, PROBE_EDGES[1:]):
            self.assertEqual(edges[a][1], edges[b][0])
        self.assertEqual(PROBE_EDGES.count("E1"), 2)
        self.assertEqual(PROBE_EDGES.count("E2"), 2)
        self.assertEqual(PROBE_EDGES.count("E3"), 2)

    def test_original_parking_inventory_is_byte_identical(self):
        files = render_source_files(self.source)
        self.assertEqual(files["parking_areas.add.xml"], (self.source / "parking_areas.add.xml").read_bytes())
        root = ET.fromstring(files["parking_areas.add.xml"])
        areas = root.findall("parkingArea")
        self.assertEqual(len(areas), 7)
        self.assertEqual(sum(int(a.attrib["roadsideCapacity"]) for a in areas), 200)
        self.assertEqual(sum(int(a.attrib["roadsideCapacity"]) for a in areas if a.attrib["id"].endswith("_G")), 170)

    def test_existing_geometry_and_source_file_hashes_unchanged(self):
        before = canonical_hashes(self.source)
        build_candidate(self.source, self.target, static_only=True)
        self.assertEqual(before, canonical_hashes(self.source))

    def test_rejects_silent_overwrite_of_existing_candidate(self):
        build_candidate(self.source, self.target, static_only=True)
        with (self.target / "parking.nod.xml").open("a", encoding="utf-8") as f:
            f.write("<!-- untracked modification -->\n")
        with self.assertRaises(CandidateError):
            build_candidate(self.source, self.target, static_only=True)

    def test_rejects_unexpected_canonical_node_position(self):
        node_file = self.source / "parking.nod.xml"
        data = node_file.read_text(encoding="utf-8").replace('id="J3" x="600.0"', 'id="J3" x="610.0"')
        node_file.write_text(data, encoding="utf-8")
        with self.assertRaises(CandidateError):
            check_canonical(self.source)

    def test_manifest_explicitly_prohibits_formal_stage_b(self):
        manifest = build_candidate(self.source, self.target, static_only=True)
        self.assertFalse(manifest["stage_b_approved"])
        self.assertTrue(manifest["sop_amendment_required"])
        self.assertEqual(manifest["capacity_eligible_general"], 170)
        self.assertEqual(manifest["candidate_classification"], "NON_FORMAL_GEOMETRY_AMENDMENT_PROPOSAL")
        self.assertEqual(
            json.loads((self.target / "candidate_manifest.json").read_text(encoding="utf-8"))["canonical_sha256"],
            canonical_hashes(self.source),
        )

    def test_never_write_candidate_into_canonical_directory(self):
        with self.assertRaises(CandidateError):
            build_candidate(self.source, self.source, static_only=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
