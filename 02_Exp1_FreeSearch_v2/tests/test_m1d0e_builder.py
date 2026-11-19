"""Static M1D-0E tests: source provenance, entrance geometry, connections."""

from __future__ import annotations

import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.build_m1d0e_entry_candidate import (
    CANONICAL, PARENT, ORIGINAL_EDGES, REQUIRED_LINKS,
    ENTRY_LENGTH_M, ONE_PASS, TWO_PASS,
    CandidateError, build, check_parent, ensure_immutable_files, source_files,
    verify_compiled, check_compiled_entry_length,
)


class TestEntryCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not PARENT.is_dir():
            raise RuntimeError(f"Missing recirculation_v1 candidate: {PARENT}")
        cls.files = source_files(PARENT, CANONICAL)

    def test_01_parent_provenance(self) -> None:
        manifest = check_parent(PARENT, CANONICAL)
        self.assertEqual(manifest["candidate_id"], "recirculation_v1")
        self.assertFalse(manifest["stage_b_approved"])

    def test_02_dedicated_entry_node(self) -> None:
        root = ET.fromstring(self.files["parking.nod.xml"])
        nodes = {n.attrib["id"]: n for n in root.findall("node")}
        self.assertEqual(set(nodes) - {"J0", "J1", "J2", "J3", "J4", "J5"}, {"J_IN"})
        self.assertEqual((float(nodes["J_IN"].attrib["x"]), float(nodes["J_IN"].attrib["y"])),
                         (-ENTRY_LENGTH_M, 0.0))

    def test_03_entry_edge(self) -> None:
        root = ET.fromstring(self.files["parking.edg.xml"])
        edges = {e.attrib["id"]: e for e in root.findall("edge")}
        self.assertEqual(set(edges) - set(ORIGINAL_EDGES), {"E_IN"})
        self.assertEqual((edges["E_IN"].attrib["from"], edges["E_IN"].attrib["to"]), ("J_IN", "J0"))
        self.assertEqual(edges["E_IN"].attrib["numLanes"], "1")

    def test_04_original_edges_exactly_preserved(self) -> None:
        orig = {e.attrib["id"]: e.attrib for e in ET.parse(PARENT / "parking.edg.xml").getroot().findall("edge")}
        new = {e.attrib["id"]: e.attrib for e in ET.fromstring(self.files["parking.edg.xml"]).findall("edge")}
        for name in ORIGINAL_EDGES:
            self.assertEqual(orig[name], new[name])

    def test_05_parking_areas_exactly_preserved(self) -> None:
        self.assertEqual(self.files["parking_areas.add.xml"], (PARENT / "parking_areas.add.xml").read_bytes())
        a = ET.fromstring(self.files["parking_areas.add.xml"]).findall("parkingArea")
        self.assertEqual(sum(int(x.attrib["roadsideCapacity"]) for x in a), 200)
        self.assertEqual(sum(int(x.attrib["roadsideCapacity"]) for x in a if x.attrib["id"].endswith("_G")), 170)

    def test_06_routes_from_entry(self) -> None:
        root = ET.fromstring(self.files["route_probe.rou.xml"])
        routes = {a.attrib["id"]: tuple(a.attrib["edges"].split()) for a in root.findall("route")}
        self.assertEqual(routes["new_arrival"], ONE_PASS)
        self.assertEqual(routes["return_once"], TWO_PASS)
        self.assertEqual(TWO_PASS.count("E1"), 2)

    def test_07_parent_tamper_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "parent"
            shutil.copytree(PARENT, p)
            (p / "parking.edg.xml").write_bytes((p / "parking.edg.xml").read_bytes() + b"\n")
            with self.assertRaisesRegex(CandidateError, "hash mismatch"):
                check_parent(p, CANONICAL)

    def test_08_refuse_silent_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "candidate"
            ensure_immutable_files(target, self.files)
            (target / "parking.edg.xml").write_text("malformed or altered", encoding="utf-8")
            with self.assertRaisesRegex(CandidateError, "differs"):
                ensure_immutable_files(target, self.files)

    def create_compiled_fixture(self, directory: Path, *, remove_link: bool = False,
                                entry_length: float = ENTRY_LENGTH_M) -> None:
        ensure_immutable_files(directory, self.files)
        root = ET.Element("net")
        for name in (*ORIGINAL_EDGES, "E_IN"):
            edge = ET.SubElement(root, "edge", id=name)
            ET.SubElement(edge, "lane", id=name + "_0", length=str(entry_length if name == "E_IN" else (60 if name in ("E_RU", "E_RD") else (600 if name == "E_RW" else 200))))
        ET.SubElement(root, "junction", id="J0", incLanes="E_IN_0 E_RD_0")
        for start, end in REQUIRED_LINKS:
            if remove_link and (start, end) == ("E_IN", "E1"):
                continue
            ET.SubElement(root, "connection", {"from": start, "to": end})
        ET.ElementTree(root).write(directory / "parking_lot.net.xml", encoding="utf-8", xml_declaration=True)

    def test_09_compiled_link_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            self.create_compiled_fixture(target)
            result = verify_compiled(target)
            self.assertTrue(result["required_links_verified"])
            self.assertEqual(result["j0_incoming_lanes"], ["E_IN_0", "E_RD_0"])

    def test_10_compiled_missing_approach_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            self.create_compiled_fixture(target, remove_link=True)
            with self.assertRaisesRegex(CandidateError, "Missing required connections"):
                verify_compiled(target)

    def test_11_source_only_can_be_compiled_later(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            first = build(PARENT, CANONICAL, target, static_only=True)
            self.assertFalse(first["compiled_net_valid"])
            self.create_compiled_fixture(target)
            second = build(PARENT, CANONICAL, target, static_only=False)
            self.assertTrue(second["compiled_net_valid"])
            self.assertFalse(second["stage_b_approved"])


    def test_12_junction_trimmed_entry_length_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            self.create_compiled_fixture(target, entry_length=142.8)
            stats = verify_compiled(target)
            self.assertAlmostEqual(stats["E_IN_length_compiled_m"], 142.8)
            self.assertAlmostEqual(stats["E_IN_nominal_minus_compiled_m"], 7.2)
            self.assertIsNone(stats["usable_entry_storage_length_m"])

    def test_13_excessively_short_entry_length_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            self.create_compiled_fixture(target, entry_length=120.0)
            with self.assertRaisesRegex(CandidateError, "engineering range"):
                verify_compiled(target)

    def test_14_excessively_long_entry_length_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            self.create_compiled_fixture(target, entry_length=160.0)
            with self.assertRaisesRegex(CandidateError, "engineering range"):
                verify_compiled(target)

    def test_15_nonfinite_or_missing_length_rejected(self) -> None:
        for invalid in (float("nan"), float("inf"), -1.0, 0.0):
            with self.subTest(invalid=invalid):
                with self.assertRaises(CandidateError):
                    check_compiled_entry_length(invalid)

if __name__ == "__main__":
    unittest.main()
