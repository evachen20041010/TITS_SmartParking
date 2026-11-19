#!/usr/bin/env python3
"""M1D-0E: non-formal entry-link extension of recirculation_v1.

Creates only network/candidates/recirculation_v2_entry. Does not alter either
canonical or recirculation_v1. An existing source file is never silently
replaced. The output is NOT authorized for formal Experiment 1 load sweeps.
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

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "network" / "canonical"
PARENT = ROOT / "network" / "candidates" / "recirculation_v1"
TARGET = ROOT / "network" / "candidates" / "recirculation_v2_entry"
ID = "recirculation_v2_entry"
VERSION = "m1d0e-1.1-length-qc"
ENTRY_NODE = "J_IN"
ENTRY_EDGE = "E_IN"
ENTRY_LENGTH_M = 150.0  # PROVISIONAL node-to-node geometry, NOT usable storage
MIN_ENTRY_COMPILED_RATIO = 0.90  # engineering plausibility guard, NOT SOP Event A
MAX_ENTRY_COMPILED_EXCESS_M = 1.0  # tolerate minor coordinate/rounding effects
SPEED_MPS = 13.89
ORIGINAL_EDGES = ("E1", "E2", "E3", "E_RU", "E_RW", "E_RD")
ONE_PASS = ("E_IN", "E1", "E2", "E3")
TWO_PASS = ("E_IN", "E1", "E2", "E3", "E_RU", "E_RW", "E_RD", "E1", "E2", "E3")
REQUIRED_LINKS = set(zip(TWO_PASS, TWO_PASS[1:])) | {("E_RD", "E1")}
BASE_NAMES = ("parking.nod.xml", "parking.edg.xml", "parking_areas.add.xml", "base.sumocfg")


class CandidateError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(p: Path) -> str:
    if not p.is_file():
        raise CandidateError(f"Required source file missing: {p}")
    return digest(p.read_bytes())


def xml_bytes(root: ET.Element) -> bytes:
    ET.indent(root, space="    ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def check_parent(parent: Path, canonical: Path) -> dict[str, Any]:
    """Validate exactly the immutable input snapshot, not merely filenames."""
    manifest = json.loads((parent / "candidate_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("candidate_id") != "recirculation_v1":
        raise CandidateError("Expected validated recirculation_v1 parent")
    if manifest.get("stage_b_approved") is not False:
        raise CandidateError("Parent manifest unexpectedly claims formal approval")
    for name, expected in manifest["canonical_sha256"].items():
        if sha256_file(canonical / name) != expected:
            raise CandidateError(f"Canonical hash mismatch: {name}")
    for name, expected in manifest["candidate_sha256"].items():
        if sha256_file(parent / name) != expected:
            raise CandidateError(f"Parent candidate hash mismatch: {name}")
    net_hash = manifest.get("candidate_net_sha256")
    if not net_hash or sha256_file(parent / "parking_lot.net.xml") != net_hash:
        raise CandidateError("Parent compiled SUMO network hash mismatch")

    nodes = {a.get("id"): a for a in ET.parse(parent / "parking.nod.xml").getroot().findall("node")}
    edges = {a.get("id"): a for a in ET.parse(parent / "parking.edg.xml").getroot().findall("edge")}
    if ENTRY_NODE in nodes or ENTRY_EDGE in edges or set(edges) != set(ORIGINAL_EDGES):
        raise CandidateError("Unexpected parent topology; refuse automatic geometry editing")
    if (nodes["J0"].get("x"), nodes["J0"].get("y")) not in (("0.0", "0.0"), ("0", "0")):
        raise CandidateError("Unexpected J0 geometry")
    if edges["E_RD"].get("to") != "J0" or edges["E1"].get("from") != "J0":
        raise CandidateError("Expected E_RD -> J0 -> E1 junction topology")
    for name in ORIGINAL_EDGES:
        if edges[name].get("numLanes") != "1" or not math.isclose(float(edges[name].get("speed", "0")), SPEED_MPS, abs_tol=1e-8):
            raise CandidateError(f"Unexpected lane or speed settings for {name}")

    areas = ET.parse(parent / "parking_areas.add.xml").getroot().findall("parkingArea")
    general = sum(int(a.get("roadsideCapacity", "0")) for a in areas if a.get("id", "").endswith("_G"))
    total = sum(int(a.get("roadsideCapacity", "0")) for a in areas)
    if len(areas) != 7 or general != 170 or total != 200:
        raise CandidateError(f"Parking inventory mismatch: {len(areas)} areas, {total} total, {general} general")
    if sha256_file(parent / "parking_areas.add.xml") != sha256_file(canonical / "parking_areas.add.xml"):
        raise CandidateError("Parent parking area XML differs from canonical")
    return manifest


def source_files(parent: Path, canonical: Path) -> dict[str, bytes]:
    check_parent(parent, canonical)
    nod = ET.fromstring((parent / "parking.nod.xml").read_bytes())
    ET.SubElement(nod, "node", {"id": ENTRY_NODE, "x": str(-ENTRY_LENGTH_M), "y": "0.0", "type": "dead_end"})
    edg = ET.fromstring((parent / "parking.edg.xml").read_bytes())
    ET.SubElement(edg, "edge", {
        "id": ENTRY_EDGE, "from": ENTRY_NODE, "to": "J0",
        "numLanes": "1", "speed": str(SPEED_MPS),
    })
    route = ET.Element("routes")
    ET.SubElement(route, "vType", {"id": "m1d0e_car", "vClass": "passenger", "length": "5.0"})
    ET.SubElement(route, "route", {"id": "new_arrival", "edges": " ".join(ONE_PASS)})
    ET.SubElement(route, "route", {"id": "return_once", "edges": " ".join(TWO_PASS)})
    return {
        "parking.nod.xml": xml_bytes(nod),
        "parking.edg.xml": xml_bytes(edg),
        "parking_areas.add.xml": (parent / "parking_areas.add.xml").read_bytes(),
        "base.sumocfg": (parent / "base.sumocfg").read_bytes(),
        "route_probe.rou.xml": xml_bytes(route),
    }


def check_compiled_entry_length(length_m: float) -> float:
    """Validate plausibility without conflating node spacing and SUMO lane length.

    SUMO netconvert may trim a lane at its junction. This engineering-only
    tolerance is NOT an estimate of physical usable entrance queue storage.
    """
    length = float(length_m)
    lower = ENTRY_LENGTH_M * MIN_ENTRY_COMPILED_RATIO
    upper = ENTRY_LENGTH_M + MAX_ENTRY_COMPILED_EXCESS_M
    if not math.isfinite(length) or not (lower <= length <= upper):
        raise CandidateError(
            f"Compiled E_IN lane length outside engineering range "
            f"[{lower:.1f}, {upper:.1f}] m: {length!r}"
        )
    return length


def verify_compiled(candidate: Path) -> dict[str, Any]:
    path = candidate / "parking_lot.net.xml"
    if not path.is_file():
        raise CandidateError("No compiled .net.xml; build using netconvert in sumo_py310")
    net = ET.parse(path).getroot()
    roads = {a.get("id"): a for a in net.findall("edge") if a.get("function") != "internal"}
    expected_roads = set(ORIGINAL_EDGES) | {ENTRY_EDGE}
    if set(roads) != expected_roads:
        raise CandidateError(f"Compiled roads mismatch: {sorted(roads)}")
    links = {(a.get("from"), a.get("to")) for a in net.findall("connection")}
    if not REQUIRED_LINKS.issubset(links):
        raise CandidateError(f"Missing required connections: {sorted(REQUIRED_LINKS - links)}")
    junctions = {j.get("id"): j for j in net.findall("junction")}
    j0 = junctions.get("J0")
    inc = set((j0.get("incLanes", "") if j0 is not None else "").split())
    if not {"E_IN_0", "E_RD_0"}.issubset(inc):
        raise CandidateError("J0 must have both new-arrival and return approaches")
    lanes = {lane.get("id"): float(lane.get("length", "0"))
             for edge in roads.values() for lane in edge.findall("lane")}
    entry_length = check_compiled_entry_length(lanes.get("E_IN_0", 0.0))
    for pa in ET.parse(candidate / "parking_areas.add.xml").getroot().findall("parkingArea"):
        lane = pa.get("lane", "")
        if lane not in lanes or float(pa.get("endPos", "0")) > lanes[lane] + 1e-6:
            raise CandidateError(f"Parking area out of bounds: {pa.get('id')}")
    return {
        "E_IN_length_compiled_m": entry_length,
        "E_IN_length_nominal_m": ENTRY_LENGTH_M,
        "E_IN_length_ratio_to_nominal": round(entry_length / ENTRY_LENGTH_M, 8),
        "E_IN_nominal_minus_compiled_m": round(ENTRY_LENGTH_M - entry_length, 8),
        "E_IN_length_qc": "ENGINEERING_PLAUSIBILITY_ONLY",
        "usable_entry_storage_length_m": None,
        "j0_incoming_lanes": sorted(inc),
        "required_links_verified": True,
    }


def ensure_immutable_files(target: Path, files: dict[str, bytes]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name, desired in files.items():
        path = target / name
        if path.exists():
            if path.read_bytes() != desired:
                raise CandidateError(f"Candidate file differs: {path}. Make a NEW candidate version; never overwrite silently")
        else:
            path.write_bytes(desired)


def build(parent: Path, canonical: Path, target: Path, *, static_only: bool = False, netconvert: str | None = None) -> dict[str, Any]:
    parent, canonical, target = parent.resolve(), canonical.resolve(), target.resolve()
    if len({parent, canonical, target}) != 3 or parent in target.parents or canonical in target.parents or target in parent.parents:
        raise CandidateError("Source and output directories must be separate")
    before = {n: sha256_file(parent / n) for n in BASE_NAMES}
    files = source_files(parent, canonical)
    ensure_immutable_files(target, files)
    compiled = (target / "parking_lot.net.xml").exists()
    if not static_only and not compiled:
        exe = netconvert or shutil.which("netconvert")
        if not exe:
            raise CandidateError("netconvert not available. Activate sumo_py310 or use --static-only for source audit")
        result = subprocess.run([
            exe, "--node-files", str(target / "parking.nod.xml"),
            "--edge-files", str(target / "parking.edg.xml"),
            "--output-file", str(target / "parking_lot.net.xml"),
            "--no-turnarounds", "true",
        ], text=True, capture_output=True, check=False)
        if result.returncode:
            raise CandidateError(f"netconvert exit={result.returncode}\n{result.stdout}\n{result.stderr}")
        compiled = True
    stats = verify_compiled(target) if compiled else None
    if {n: sha256_file(parent / n) for n in BASE_NAMES} != before:
        raise CandidateError("Parent source modified during build")
    reference = check_parent(parent, canonical)
    manifest: dict[str, Any] = {
        "candidate_id": ID, "generator_version": VERSION,
        "classification": "NON_FORMAL_ENGINEERING_CANDIDATE",
        "derived_from": "recirculation_v1",
        "sop_amendment_required": True, "stage_b_approved": False,
        "formal_experiment_approved": False, "physical_event_A_validated": False,
        "parent_candidate_net_sha256": reference["candidate_net_sha256"],
        "canonical_sha256": reference["canonical_sha256"],
        "parent_source_sha256": {n: sha256_file(parent / n) for n in BASE_NAMES},
        "candidate_sha256": {n: digest(data) for n, data in files.items()},
        "candidate_net_sha256": sha256_file(target / "parking_lot.net.xml") if compiled else None,
        "compiled_net_valid": compiled,
        "compiled_stats": stats,
        "added_entry_edge": ENTRY_EDGE, "entry_length_m_nominal": ENTRY_LENGTH_M,
        "junction_merge": {"incoming": ["E_IN", "E_RD"], "outgoing": "E1", "junction": "J0"},
        "parking_areas": 7, "capacity_total": 200, "capacity_eligible_general": 170,
        "new_arrival_route": list(ONE_PASS), "one_return_route": list(TWO_PASS),
        "usable_entry_storage_length_m": None,
        "geometry_notice": "E_IN creates a new external approach and changes J0 junction priority/merge. Physical queue length, conflict behavior and Event A remain uncalibrated. Formal use is prohibited.",
    }
    manifest_file = target / "candidate_manifest.json"
    new_manifest = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    # An existing verified candidate cannot be silently 'upgraded' to approved.
    if manifest_file.exists() and manifest_file.read_text(encoding="utf-8") != new_manifest:
        old = json.loads(manifest_file.read_text(encoding="utf-8"))
        # A previously source-only snapshot may be upgraded once after the
        # first legitimate netconvert build; no source hashes or approval flags
        # are allowed to change.
        eligible = (
            old.get("compiled_net_valid") is False and compiled is True
            and old.get("candidate_net_sha256") is None
            and old.get("candidate_id") == ID
        )
        for field in ("compiled_net_valid", "candidate_net_sha256", "compiled_stats"):
            old.pop(field, None)
        before_fields = dict(manifest)
        for field in ("compiled_net_valid", "candidate_net_sha256", "compiled_stats"):
            before_fields.pop(field, None)
        if not eligible or old != before_fields:
            raise CandidateError("Existing candidate manifest differs; create a new version instead of overwriting")
        manifest_file.write_text(new_manifest, encoding="utf-8")
    elif not manifest_file.exists():
        manifest_file.write_text(new_manifest, encoding="utf-8")
    return manifest


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--static-only", action="store_true", help="Write/check sources without SUMO compilation")
    p.add_argument("--netconvert", default=None, help="Optional full path to netconvert.exe")
    opts = p.parse_args()
    try:
        result = build(PARENT, CANONICAL, TARGET, static_only=opts.static_only, netconvert=opts.netconvert)
    except (CandidateError, OSError, ValueError, KeyError, ET.ParseError) as exc:
        print(f"BUILD ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print("=" * 74)
    print("MILESTONE 1D-0E - DEDICATED ENTRANCE LINK CANDIDATE")
    print("=" * 74)
    print("Source geometry immutable : PASS")
    print("New approach              : E_IN -> E1")
    print("Return approach           : E_RD -> E1")
    print("Parking capacity          : 200 total / 170 general")
    print(f"Compiled network          : {'PASS' if result['compiled_net_valid'] else 'NOT BUILT (SOURCE ONLY)'}")
    if result["compiled_stats"] is not None:
        print(f"Entrance nominal/compiled : {ENTRY_LENGTH_M:.1f} / "
              f"{result['compiled_stats']['E_IN_length_compiled_m']:.2f} m")
    print("Physical Event A QC       : NOT VALIDATED")
    print("Formal Experiment 1       : HOLD_SOP_AMENDMENT_REQUIRED")
    print(f"Candidate                 : {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
