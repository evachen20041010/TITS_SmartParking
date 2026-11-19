#!/usr/bin/env python3
"""M1D-0D: read-only geometry/instrumentation freeze-gate audit.

The only outputs are written under validation/m1d0d; canonical/candidate XML
and all prior validation evidence are never modified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = PROJECT_ROOT / "network" / "canonical"
CANDIDATE = PROJECT_ROOT / "network" / "candidates" / "recirculation_v1"
OUTPUT = PROJECT_ROOT / "validation" / "m1d0d"

CYCLE = (
    ("E1", "E2"),
    ("E2", "E3"),
    ("E3", "E_RU"),
    ("E_RU", "E_RW"),
    ("E_RW", "E_RD"),
    ("E_RD", "E1"),
)


class GateAuditError(ValueError):
    pass


def sha256(path: Path) -> str:
    if not path.is_file():
        raise GateAuditError(f"Missing source file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_hashes(directory: Path, hashes: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for filename, expected in sorted(hashes.items()):
        p = directory / filename
        if not p.is_file() or sha256(p) != expected:
            errors.append(f"SHA-256 mismatch or missing: {p}")
    return errors


def edge_attributes(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise GateAuditError(f"Missing edges file: {path}")
    root = ET.parse(path).getroot()
    return {e.attrib["id"]: dict(e.attrib) for e in root.findall("edge")}


def net_edges_and_connections(path: Path) -> tuple[set[str], set[tuple[str, str]]]:
    if not path.is_file():
        raise GateAuditError(f"Missing compiled network: {path}")
    root = ET.parse(path).getroot()
    edges = {
        e.attrib["id"] for e in root.findall("edge")
        if e.get("function") != "internal"
    }
    connections = {
        (c.get("from", ""), c.get("to", ""))
        for c in root.findall("connection")
        if c.get("from") in edges and c.get("to") in edges
    }
    return edges, connections


def capacity_by_type(path: Path) -> dict[str, int]:
    if not path.is_file():
        raise GateAuditError(f"Missing parking areas file: {path}")
    root = ET.parse(path).getroot()
    capacity = {"general": 0, "family": 0, "disabled": 0}
    suffix_map = {"G": "general", "F": "family", "D": "disabled"}
    areas = root.findall("parkingArea")
    if len(areas) != 7 or len({e.get("id") for e in areas}) != 7:
        raise GateAuditError("Expected 7 uniquely identified parking areas.")
    for a in areas:
        parking_id = a.get("id", "")
        subtype = parking_id.rsplit("_", 1)[-1]
        if subtype not in suffix_map:
            raise GateAuditError(f"Unrecognized parking type: {parking_id}")
        capacity[suffix_map[subtype]] += int(a.get("roadsideCapacity", "0"))
    return capacity


def formal_gate_reasons(
    *,
    dedicated_entrance: bool,
    approved_amendment: bool,
    entrance_qc: bool,
    behavior_frozen: bool,
    detector_verified: bool,
) -> list[str]:
    flags = {
        "dedicated_physical_entrance_link": dedicated_entrance,
        "signed_geometry_sop_amendment": approved_amendment,
        "entrance_measurement_qc": entrance_qc,
        "free_search_behavior_frozen": behavior_frozen,
        "c1_c2_detector_verified": detector_verified,
    }
    return [name for name, passed in flags.items() if not passed]


def audit_geometry(canonical: Path, candidate: Path) -> dict[str, Any]:
    manifest_path = candidate / "candidate_manifest.json"
    if not manifest_path.is_file():
        raise GateAuditError(f"Missing candidate manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    errors.extend(check_hashes(canonical, manifest["canonical_sha256"]))
    errors.extend(check_hashes(candidate, manifest["candidate_sha256"]))
    if sha256(candidate / "parking_lot.net.xml") != manifest["candidate_net_sha256"]:
        errors.append("Compiled candidate network hash mismatch.")

    source_old = edge_attributes(canonical / "parking.edg.xml")
    source_new = edge_attributes(candidate / "parking.edg.xml")
    for e in ("E1", "E2", "E3"):
        if source_old.get(e) != source_new.get(e):
            errors.append(f"Original edge {e} changed.")

    compiled, links = net_edges_and_connections(candidate / "parking_lot.net.xml")
    for a, b in CYCLE:
        if (a, b) not in links:
            errors.append(f"Missing directed SUMO connection: {a}->{b}")

    inventory = capacity_by_type(candidate / "parking_areas.add.xml")
    if inventory != {"general": 170, "family": 20, "disabled": 10}:
        errors.append(f"Legal capacity mismatch: {inventory}")
    if sha256(candidate / "parking_areas.add.xml") != sha256(canonical / "parking_areas.add.xml"):
        errors.append("Parking area file differs from canonical.")

    # The return merge E_RD->E1 is not a separate upstream entry approach.
    # Only an actual E_IN approach that joins E1 can implement physical Event A.
    entry_edge = "E_IN" if "E_IN" in compiled and ("E_IN", "E1") in links else None
    extra_edges = sorted(compiled - {"E1", "E2", "E3", "E_RU", "E_RW", "E_RD"})
    if extra_edges and entry_edge is None:
        errors.append(f"Unreviewed candidate extra edges: {extra_edges}")

    integrity_pass = not errors
    reasons = formal_gate_reasons(
        dedicated_entrance=entry_edge is not None,
        approved_amendment=False,
        entrance_qc=False,
        behavior_frozen=False,
        detector_verified=False,
    )
    return {
        "milestone": "1D-0D",
        "candidate_id": manifest.get("candidate_id", "UNKNOWN"),
        "static_integrity": "PASS" if integrity_pass else "FAIL",
        "static_integrity_errors": errors,
        "original_edges_preserved": all(source_old.get(e) == source_new.get(e) for e in ("E1", "E2", "E3")),
        "revisit_connections_present": all(k in links for k in CYCLE),
        "parking_capacity": inventory,
        "candidate_entrance_access_edge": entry_edge,
        "physical_event_a_measurable": False,  # calibration/QC not performed
        "separate_entrance_from_return_merge": entry_edge is not None,
        "exit_boundary_model": "E3 route-end virtual sink (1D-0C probe)",
        "entry_state_is_not_spillback_metric": True,
        "formal_study_gate": "HOLD" if integrity_pass else "FAIL_SOURCE_INTEGRITY",
        "unmet_formal_requirements": reasons,
        "recommended_next_candidate": "recirculation_v2_entry (proposed, not created)",
        "network_files_modified": False,
        "formal_batch_authorized": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Read-only M1D-0D geometry gate audit.")
    p.add_argument("--canonical-dir", type=Path, default=CANONICAL)
    p.add_argument("--candidate-dir", type=Path, default=CANDIDATE)
    p.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = p.parse_args()

    try:
        result = audit_geometry(args.canonical_dir, args.candidate_dir)
    except (GateAuditError, OSError, ET.ParseError, ValueError, KeyError) as exc:
        print(f"AUDIT ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "geometry_gate_summary.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with (args.output_dir / "geometry_gate_checks.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["check", "value"])
        for field in (
            "static_integrity", "original_edges_preserved", "revisit_connections_present",
            "candidate_entrance_access_edge", "physical_event_a_measurable",
            "entry_state_is_not_spillback_metric", "formal_study_gate",
            "formal_batch_authorized",
        ):
            writer.writerow([field, result[field]])

    print("=" * 76)
    print("MILESTONE 1D-0D - RESEARCH GEOMETRY / ENTRY-QUEUE GATE")
    print("=" * 76)
    print(f"Candidate                : {result['candidate_id']}")
    print(f"Source + network hashes  : {result['static_integrity']}")
    print(f"Original roads preserved : {result['original_edges_preserved']}")
    print(f"Revisitable route        : {result['revisit_connections_present']}")
    print(f"Legal general spaces     : {result['parking_capacity']['general']}")
    print(f"Dedicated entry edge     : {result['candidate_entrance_access_edge'] or 'NONE'}")
    print(f"Physical Event A QC      : {'PASS' if result['physical_event_a_measurable'] else 'NOT YET VALIDATED'}")
    print(f"Static integrity verdict : {result['static_integrity']}")
    print(f"Formal geometry gate     : {result['formal_study_gate']}")
    print(f"Formal batch authorized  : {result['formal_batch_authorized']}")
    print(f"Evidence                 : {path}")
    return 0 if result["static_integrity"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
