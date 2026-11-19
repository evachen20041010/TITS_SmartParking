#!/usr/bin/env python3
"""M1D-0B: build a versioned, non-formal recirculation-network candidate.

Never modifies canonical network, frozen ICCE files, or past validations.
Only the candidate source files are created; netconvert is needed to compile
its SUMO network. Formal use is prohibited pending SOP amendment/sign-off.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = PROJECT_ROOT / "network" / "canonical"
CANDIDATE = PROJECT_ROOT / "network" / "candidates" / "recirculation_v1"
VERSION = "m1d0b-1.0"
RETURN_OFFSET_M = 60.0  # NON-FORMAL geometry fixture; not an approved parameter
EDGE_SPEED_MPS = 13.89  # Match existing edge setting for topology-only trial

ORIGINAL_NODES = {
    "J0": (0.0, 0.0), "J1": (200.0, 0.0),
    "J2": (400.0, 0.0), "J3": (600.0, 0.0),
}
ORIGINAL_EDGES = {
    "E1": ("J0", "J1"), "E2": ("J1", "J2"),
    "E3": ("J2", "J3"),
}
RETURN_EDGES = {
    "E_RU": ("J3", "J4"),
    "E_RW": ("J4", "J5"),
    "E_RD": ("J5", "J0"),
}
LAP_EDGES = ["E1", "E2", "E3", "E_RU", "E_RW", "E_RD"]
PROBE_EDGES = LAP_EDGES + ["E1", "E2", "E3"]
SOURCE_FILES = [
    "parking.nod.xml", "parking.edg.xml", "parking_areas.add.xml",
    "base.sumocfg", "parking_lot.net.xml",
]


class CandidateError(ValueError):
    """Unexpected source geometry or candidate mismatch."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hashes(source: Path) -> dict[str, str]:
    return {name: file_sha256(source / name) for name in SOURCE_FILES}


def check_canonical(source: Path) -> None:
    for name in SOURCE_FILES:
        if not (source / name).is_file():
            raise CandidateError(f"Missing canonical source file: {source / name}")

    root = ET.parse(source / "parking.nod.xml").getroot()
    nodes = {n.get("id"): n for n in root.findall("node")}
    if set(nodes) != set(ORIGINAL_NODES):
        raise CandidateError("Unexpected canonical node IDs; do not auto-modify this network.")
    for nid, (x, y) in ORIGINAL_NODES.items():
        n = nodes[nid]
        if not math.isclose(float(n.attrib["x"]), x, abs_tol=1e-8) or not math.isclose(float(n.attrib["y"]), y, abs_tol=1e-8):
            raise CandidateError(f"Unexpected geometry for {nid}.")

    edge_root = ET.parse(source / "parking.edg.xml").getroot()
    edges = {e.get("id"): e for e in edge_root.findall("edge")}
    if set(edges) != set(ORIGINAL_EDGES):
        raise CandidateError("Unexpected canonical edge IDs; manual review required.")
    for eid, (start, end) in ORIGINAL_EDGES.items():
        e = edges[eid]
        if (e.get("from"), e.get("to")) != (start, end):
            raise CandidateError(f"Unexpected direction for {eid}.")
        if e.get("numLanes") != "1" or not math.isclose(float(e.attrib["speed"]), EDGE_SPEED_MPS, abs_tol=1e-8):
            raise CandidateError(f"Unexpected number of lanes or speed for {eid}.")

    park_root = ET.parse(source / "parking_areas.add.xml").getroot()
    areas = list(park_root.findall("parkingArea"))
    if len(areas) != 7:
        raise CandidateError("Expected 7 canonical parking areas.")
    if sum(int(p.attrib["roadsideCapacity"]) for p in areas) != 200:
        raise CandidateError("Expected 200 physical parking spaces.")
    if sum(int(p.attrib["roadsideCapacity"]) for p in areas if p.attrib["id"].endswith("_G")) != 170:
        raise CandidateError("Expected C_eff=170 general spaces.")
    if not all(p.attrib["lane"] in {"E1_0", "E2_0", "E3_0"} for p in areas):
        raise CandidateError("Parking areas must remain on existing original lanes.")


def xml_bytes(root: ET.Element) -> bytes:
    ET.indent(root, space="    ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def render_source_files(source: Path) -> dict[str, bytes]:
    """Pure function: return candidate XML bytes without touching filesystem."""
    check_canonical(source)
    node_root = ET.fromstring((source / "parking.nod.xml").read_bytes())
    nodes = {n.get("id"): n for n in node_root.findall("node")}
    for nid in ("J0", "J3"):
        nodes[nid].set("type", "priority")
    ET.SubElement(node_root, "node", id="J4", x="600.0", y=str(RETURN_OFFSET_M), type="priority")
    ET.SubElement(node_root, "node", id="J5", x="0.0", y=str(RETURN_OFFSET_M), type="priority")

    edge_root = ET.fromstring((source / "parking.edg.xml").read_bytes())
    for eid, (start, end) in RETURN_EDGES.items():
        ET.SubElement(
            edge_root, "edge",
            {"id": eid, "from": start, "to": end, "numLanes": "1", "speed": str(EDGE_SPEED_MPS)},
        )

    probe_root = ET.Element("routes")
    ET.SubElement(probe_root, "vType", {"id": "probe_car", "vClass": "passenger", "length": "5.0"})
    ET.SubElement(probe_root, "route", {"id": "two_pass", "edges": " ".join(PROBE_EDGES)})
    ET.SubElement(
        probe_root, "vehicle",
        {"id": "probe_two_passes", "type": "probe_car", "route": "two_pass", "depart": "0", "departSpeed": "0"},
    )
    return {
        "parking.nod.xml": xml_bytes(node_root),
        "parking.edg.xml": xml_bytes(edge_root),
        "parking_areas.add.xml": (source / "parking_areas.add.xml").read_bytes(),
        "base.sumocfg": (source / "base.sumocfg").read_bytes(),
        "route_probe.rou.xml": xml_bytes(probe_root),
    }


def ensure_exact_sources(target: Path, sources: dict[str, bytes]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name, expected in sources.items():
        dest = target / name
        if dest.exists():
            if dest.read_bytes() != expected:
                raise CandidateError(
                    f"Existing candidate differs: {dest}. Create a NEW candidate version; do not silently overwrite."
                )
        else:
            dest.write_bytes(expected)


def direct_connections(net: Path) -> set[tuple[str, str]]:
    root = ET.parse(net).getroot()
    return {
        (c.attrib["from"], c.attrib["to"])
        for c in root.findall("connection")
        if not c.attrib["from"].startswith(":") and not c.attrib["to"].startswith(":")
    }


def verify_net(target: Path) -> None:
    net = target / "parking_lot.net.xml"
    if not net.is_file():
        raise CandidateError("Compiled network missing; run netconvert to create candidate .net.xml.")
    root = ET.parse(net).getroot()
    observed = {
        e.attrib["id"]
        for e in root.findall("edge")
        if e.attrib.get("function") != "internal"
    }
    expected = set(ORIGINAL_EDGES) | set(RETURN_EDGES)
    if observed != expected:
        raise CandidateError(f"Compiled edge IDs {observed} != expected {expected}")

    connections = direct_connections(net)
    for a, b in zip(PROBE_EDGES, PROBE_EDGES[1:]):
        if (a, b) not in connections:
            raise CandidateError(f"Compiled network lacks required drivable connection {a}->{b}.")

    lanes = {lane.attrib["id"]: float(lane.attrib["length"])
             for edge in root.findall("edge") for lane in edge.findall("lane")}
    for pa in ET.parse(target / "parking_areas.add.xml").getroot().findall("parkingArea"):
        lane = pa.attrib["lane"]
        if lane not in lanes or float(pa.attrib["endPos"]) > lanes[lane] + 1e-6:
            raise CandidateError(f"Parking area {pa.attrib['id']} is outside lane {lane}.")


def build_candidate(
    source: Path,
    target: Path,
    *,
    static_only: bool = False,
    netconvert_path: str | None = None,
) -> dict[str, Any]:
    source = source.resolve()
    target = target.resolve()
    if source == target or source in target.parents or target in source.parents:
        raise CandidateError("Source/target directories must be separate; do not write inside canonical.")

    before = canonical_hashes(source)
    files = render_source_files(source)
    ensure_exact_sources(target, files)

    compiled = (target / "parking_lot.net.xml").exists()
    if not static_only and not compiled:
        exe = netconvert_path or shutil.which("netconvert")
        if not exe:
            raise CandidateError("netconvert is not on PATH. Activate sumo_py310 or use --static-only.")
        cmd = [
            exe,
            "--node-files", str(target / "parking.nod.xml"),
            "--edge-files", str(target / "parking.edg.xml"),
            "--output-file", str(target / "parking_lot.net.xml"),
            "--no-turnarounds", "true",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode:
            raise CandidateError(f"netconvert failed (exit={result.returncode}):\n{result.stdout}\n{result.stderr}")
        compiled = True

    if compiled:
        verify_net(target)
    after = canonical_hashes(source)
    if before != after:
        raise CandidateError("Canonical network CHANGED; stop and investigate.")

    manifest: dict[str, Any] = {
        "candidate_id": "recirculation_v1",
        "generator_version": VERSION,
        "candidate_classification": "NON_FORMAL_GEOMETRY_AMENDMENT_PROPOSAL",
        "sop_amendment_required": True,
        "stage_b_approved": False,
        "static_source_valid": True,
        "compiled_net_valid": compiled,
        "canonical_sha256": before,
        "candidate_sha256": {n: sha256_bytes(b) for n, b in files.items()},
        "candidate_net_sha256": file_sha256(target / "parking_lot.net.xml") if compiled else None,
        "original_edges_preserved": ["E1", "E2", "E3"],
        "added_edges": list(RETURN_EDGES),
        "return_geometry_offset_m": RETURN_OFFSET_M,
        "return_road_length_m_nominal": 600.0 + 2 * RETURN_OFFSET_M,
        "loop_length_m_nominal": 1200.0 + 2 * RETURN_OFFSET_M,
        "parking_areas": 7,
        "capacity_total": 200,
        "capacity_eligible_general": 170,
        "probe_route_edges": PROBE_EDGES,
        "design_warning": (
            "This candidate changes physical topology, junction types, total road length, "
            "route travel times, and potential queue/spillback mechanisms. "
            "No stability inference and no formal load sweep are authorized."
        ),
    }
    (target / "candidate_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--static-only", action="store_true", help="Write source XML but do not invoke netconvert.")
    ap.add_argument("--netconvert", default=None, help="Explicit path to netconvert binary, if absent from PATH.")
    args = ap.parse_args()
    try:
        manifest = build_candidate(
            CANONICAL,
            CANDIDATE,
            static_only=args.static_only,
            netconvert_path=args.netconvert,
        )
    except (CandidateError, OSError, ET.ParseError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print("=" * 72)
    print("MILESTONE 1D-0B - VERSIONED RECIRCULATION CANDIDATE")
    print("=" * 72)
    print("Canonical files unchanged   : PASS")
    print("Candidate source structure  : PASS")
    print(f"Compiled SUMO network       : {'PASS' if manifest['compiled_net_valid'] else 'NOT_BUILT'}")
    print("Existing parking capacity   : 200 total / 170 general")
    print("Revisitable route           : " + " -> ".join(PROBE_EDGES))
    print("Formal Experiment 1 use     : HOLD_SOP_AMENDMENT_REQUIRED")
    print(f"Candidate directory         : {CANDIDATE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
