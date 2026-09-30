#!/usr/bin/env python3
"""
Milestone 1A - Canonical-network inventory and capacity validation.

This script reads the T-ITS Experiment 1 canonical SUMO network and parking
definitions, validates parking-area references/geometry, and writes a
machine-readable inventory.

No pandas or third-party package is required.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

TYPE_MAP = {
    "G": "general",
    "F": "family",
    "D": "disabled",
}

# Experiment 1 core assumption: general vehicles may legally use G spaces only.
LEGAL_SPACE_TYPES = {
    "general": {"general"},
    "family": {"family", "general"},
    "disabled": {"disabled", "general"},
}

PA_ID_RE = re.compile(r"^PA_Z(?P<zone>\d+)_(?P<type>[GFD])$")


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve()
    project_root = here.parent.parent
    default_network_dir = project_root / "network" / "canonical"
    default_validation_dir = project_root / "validation"

    p = argparse.ArgumentParser(
        description="Inspect canonical SUMO parking network and compute effective capacity."
    )
    p.add_argument(
        "--network-dir",
        type=Path,
        default=default_network_dir,
        help="Directory containing parking_lot.net.xml and parking_areas.add.xml",
    )
    p.add_argument(
        "--validation-dir",
        type=Path,
        default=default_validation_dir,
        help="Output directory for inventory and summary files",
    )
    p.add_argument(
        "--vehicle-class",
        choices=sorted(LEGAL_SPACE_TYPES),
        default="general",
        help="Vehicle class used to compute C_eff (default: general)",
    )
    return p.parse_args()


def load_lane_info(net_file: Path) -> dict[str, dict[str, float | str]]:
    root = ET.parse(net_file).getroot()
    lanes: dict[str, dict[str, float | str]] = {}

    for edge in root.findall("edge"):
        if edge.get("function") == "internal":
            continue
        edge_id = edge.get("id", "")
        for lane in edge.findall("lane"):
            lane_id = lane.get("id", "")
            if not lane_id:
                continue
            lanes[lane_id] = {
                "edge_id": edge_id,
                "length": float(lane.get("length", "nan")),
                "speed": float(lane.get("speed", "nan")),
            }
    return lanes


def load_parking_areas(parking_file: Path) -> list[dict]:
    root = ET.parse(parking_file).getroot()
    rows = []

    for pa in root.findall("parkingArea"):
        pa_id = pa.get("id", "")
        m = PA_ID_RE.match(pa_id)

        zone = int(m.group("zone")) if m else None
        type_code = m.group("type") if m else None
        space_type = TYPE_MAP.get(type_code, "unknown")

        rows.append(
            {
                "parking_area_id": pa_id,
                "zone": zone,
                "type_code": type_code,
                "space_type": space_type,
                "lane": pa.get("lane", ""),
                "start_pos": float(pa.get("startPos", "nan")),
                "end_pos": float(pa.get("endPos", "nan")),
                "capacity": int(pa.get("roadsideCapacity", "0")),
                "on_road": pa.get("onRoad", ""),
            }
        )
    return rows


def validate(rows: list[dict], lanes: dict[str, dict]) -> list[str]:
    errors: list[str] = []

    ids = [r["parking_area_id"] for r in rows]
    duplicates = [k for k, v in Counter(ids).items() if v > 1]
    if duplicates:
        errors.append(f"Duplicate parkingArea IDs: {duplicates}")

    if not rows:
        errors.append("No parkingArea elements were found.")

    for r in rows:
        pid = r["parking_area_id"]

        if r["zone"] is None or r["space_type"] == "unknown":
            errors.append(
                f"{pid}: ID does not match expected naming convention PA_Z<zone>_[G|F|D]."
            )

        if r["lane"] not in lanes:
            errors.append(f"{pid}: lane '{r['lane']}' does not exist in net file.")
            continue

        lane_len = float(lanes[r["lane"]]["length"])
        start = float(r["start_pos"])
        end = float(r["end_pos"])

        if r["capacity"] <= 0:
            errors.append(f"{pid}: capacity must be > 0.")

        if start < 0 or end < 0 or start >= end:
            errors.append(f"{pid}: invalid start/end positions ({start}, {end}).")

        if end > lane_len + 1e-9:
            errors.append(
                f"{pid}: endPos={end} exceeds lane length={lane_len} on {r['lane']}."
            )

    return errors


def write_inventory(rows: list[dict], lanes: dict[str, dict], out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "parking_area_id",
        "zone",
        "type_code",
        "space_type",
        "lane",
        "edge",
        "lane_length_m",
        "lane_speed_mps",
        "start_pos",
        "end_pos",
        "capacity",
        "on_road",
    ]

    with out_file.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            lane_info = lanes.get(r["lane"], {})
            w.writerow(
                {
                    **r,
                    "edge": lane_info.get("edge_id", ""),
                    "lane_length_m": lane_info.get("length", ""),
                    "lane_speed_mps": lane_info.get("speed", ""),
                }
            )


def main() -> int:
    args = parse_args()
    network_dir = args.network_dir.resolve()
    validation_dir = args.validation_dir.resolve()

    net_file = network_dir / "parking_lot.net.xml"
    parking_file = network_dir / "parking_areas.add.xml"

    missing = [p for p in (net_file, parking_file) if not p.exists()]
    if missing:
        print("ERROR: required file(s) missing:")
        for p in missing:
            print(f"  - {p}")
        return 2

    lanes = load_lane_info(net_file)
    rows = load_parking_areas(parking_file)
    errors = validate(rows, lanes)

    by_type = defaultdict(int)
    by_zone = defaultdict(int)
    by_zone_type = defaultdict(int)

    for r in rows:
        by_type[r["space_type"]] += r["capacity"]
        by_zone[r["zone"]] += r["capacity"]
        by_zone_type[(r["zone"], r["space_type"])] += r["capacity"]

    c_total = sum(r["capacity"] for r in rows)
    legal_types = LEGAL_SPACE_TYPES[args.vehicle_class]
    c_eff = sum(
        r["capacity"] for r in rows if r["space_type"] in legal_types
    )

    inventory_csv = validation_dir / "network_inventory.csv"
    summary_json = validation_dir / "network_summary.json"
    write_inventory(rows, lanes, inventory_csv)

    summary = {
        "network_dir": str(network_dir),
        "net_file": str(net_file),
        "parking_file": str(parking_file),
        "edge_count_non_internal": len({v["edge_id"] for v in lanes.values()}),
        "lane_count_non_internal": len(lanes),
        "parking_area_count": len(rows),
        "capacity_total": c_total,
        "capacity_by_type": dict(sorted(by_type.items())),
        "capacity_by_zone": {
            str(k): v for k, v in sorted(by_zone.items())
        },
        "capacity_by_zone_and_type": {
            f"Z{z}_{t}": cap
            for (z, t), cap in sorted(by_zone_type.items())
        },
        "vehicle_class": args.vehicle_class,
        "legal_space_types": sorted(legal_types),
        "effective_capacity": c_eff,
        "validation_errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }

    validation_dir.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("=" * 72)
    print("T-ITS EXPERIMENT 1 - MILESTONE 1A NETWORK INSPECTION")
    print("=" * 72)
    print(f"Network directory : {network_dir}")
    print(f"Parking areas     : {len(rows)}")
    print(f"Non-internal edges: {summary['edge_count_non_internal']}")
    print(f"Non-internal lanes: {summary['lane_count_non_internal']}")
    print()
    print("Capacity by parking-space type:")
    for t in ("general", "family", "disabled"):
        print(f"  {t:10s}: {by_type.get(t, 0)}")
    print(f"  {'TOTAL':10s}: {c_total}")
    print()
    print("Capacity by zone:")
    for z, cap in sorted(by_zone.items()):
        print(f"  Zone {z}: {cap}")
    print()
    print(f"Studied vehicle class : {args.vehicle_class}")
    print(f"Legal space types     : {', '.join(sorted(legal_types))}")
    print(f"C_eff                 : {c_eff}")
    print()

    print("Parking-area inventory:")
    for r in rows:
        li = lanes.get(r["lane"], {})
        print(
            f"  {r['parking_area_id']:8s} "
            f"zone={r['zone']} type={r['space_type']:8s} "
            f"capacity={r['capacity']:3d} "
            f"lane={r['lane']} edge={li.get('edge_id', '?')}"
        )

    print()
    if errors:
        print("Validation: FAIL")
        for e in errors:
            print(f"  ERROR: {e}")
    else:
        print("Validation: PASS")

    print(f"Inventory CSV : {inventory_csv}")
    print(f"Summary JSON  : {summary_json}")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
