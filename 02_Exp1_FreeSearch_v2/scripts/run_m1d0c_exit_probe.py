#!/usr/bin/env python3
"""Milestone 1D-0C: two-vehicle recirculation vs post-parking exit probe.

NON-FORMAL diagnostic. Does not change canonical or candidate road files.

  python scripts/run_m1d0c_exit_probe.py --precheck
  python scripts/run_m1d0c_exit_probe.py

Two vehicles start with the same two-pass route:
  early_park: park on pass 1; shorten remaining route on departure; exit E3.
  late_park : skip first pass; park on pass 2; exit E3.

Both must park before being counted as completed. An unparked normal route
arrival is a test failure, never a completed parking service.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.vehicle_state import VehicleLedger, VehicleState  # noqa: E402

CANDIDATE = PROJECT_ROOT / "network" / "candidates" / "recirculation_v1"
CONFIG_FILE = CANDIDATE / "base.sumocfg"
OUTPUT = PROJECT_ROOT / "validation" / "m1d0c"

FULL_ROUTE = ("E1", "E2", "E3", "E_RU", "E_RW", "E_RD", "E1", "E2", "E3")
EARLY_EXPECTED = ("E1", "E2", "E3")
LATE_EXPECTED = FULL_ROUTE
PARKING_AREA = "PA_Z2_G"
STOP_SECONDS = 12.0
STEP_S = 1.0
HORIZON_S = 360.0
DEPART_EPOCH = {"early_park": 0.0, "late_park": 8.0}
PARK_ON_PASS = {"early_park": 1, "late_park": 2}


def require_float(value: object, source: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise TypeError(f"{source}: expected numeric scalar, got {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{source}: value is not finite")
    return result


def require_int(value: object, source: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{source}: expected int, got {type(value).__name__}")
    return value


def require_ids(value: object, source: str) -> set[str]:
    if not isinstance(value, (tuple, list, set)):
        raise TypeError(f"{source}: expected list/tuple/set")
    if any(not isinstance(v, str) for v in value):
        raise TypeError(f"{source}: vehicle IDs must be strings")
    return set(value)


def exit_route_from(current_edge: str) -> tuple[str, ...]:
    """Route replacement MUST begin on the vehicle's present edge."""
    if current_edge == "E2":
        return ("E2", "E3")
    if current_edge == "E3":
        return ("E3",)
    raise ValueError(f"Cannot issue normal-exit route from {current_edge!r}")


def should_request_parking(vehicle_id: str, road: str, route_index: int) -> bool:
    """Deterministic control fixture, NOT a free-search behavior rule."""
    if vehicle_id not in PARK_ON_PASS or road != "E1":
        return False
    return route_index == (0 if PARK_ON_PASS[vehicle_id] == 1 else 6)


def allow_completed_after(state: VehicleState) -> bool:
    """Never count a route end as successful service unless parking ended."""
    return state == VehicleState.DEPARTING


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_inputs() -> dict[str, Any]:
    path = CANDIDATE / "candidate_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing candidate manifest: {path}")
    manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("candidate_id") != "recirculation_v1":
        raise ValueError("Unexpected candidate ID")
    if manifest.get("stage_b_approved") is not False:
        raise ValueError("Formal approval must remain FALSE in diagnostic candidate")
    if manifest.get("sop_amendment_required") is not True:
        raise ValueError("SOP amendment flag is missing")

    net = CANDIDATE / "parking_lot.net.xml"
    if sha256(net) != manifest.get("candidate_net_sha256"):
        raise ValueError("Compiled candidate network hash mismatch")
    for filename, digest in manifest["candidate_sha256"].items():
        if sha256(CANDIDATE / filename) != digest:
            raise ValueError(f"Candidate source hash mismatch: {filename}")
    xml = ET.parse(CANDIDATE / "parking_areas.add.xml").getroot()
    spaces = {
        item.get("id"): int(item.get("roadsideCapacity", "0"))
        for item in xml.findall("parkingArea")
    }
    if sum(spaces.values()) != 200 or sum(
        v for k, v in spaces.items() if k is not None and k.endswith("_G")
    ) != 170:
        raise ValueError("Parking capacity mismatch: expected total=200, general=170")
    if spaces.get(PARKING_AREA) != 50:
        raise ValueError("Expected PA_Z2_G with 50 spaces")
    if tuple(manifest.get("probe_route_edges", [])) != FULL_ROUTE:
        raise ValueError("Two-pass candidate route differs from recorded manifest")
    if not CONFIG_FILE.is_file():
        raise FileNotFoundError(CONFIG_FILE)
    return manifest


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(verbose: bool = False) -> int:
    # Lazy import means --precheck is possible without SUMO/TraCI.
    import traci  # type: ignore[import-not-found]

    sumo = shutil.which("sumo")
    if sumo is None:
        raise FileNotFoundError("Activate sumo_py310: SUMO binary not on PATH")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    ledger = VehicleLedger()
    released: set[str] = set()
    stop_requested: set[str] = set()
    shortened: set[str] = set()
    parked_index: dict[str, int] = {}
    seen_edges: dict[str, list[str]] = {v: [] for v in DEPART_EPOCH}
    previous_edge: dict[str, str] = {v: "" for v in DEPART_EPOCH}
    system_log: list[dict[str, Any]] = [ledger.snapshot(0.0)]
    audit: list[dict[str, Any]] = []
    runtime_error: str | None = None

    cmd = [sumo, "-c", str(CONFIG_FILE), "--step-length", str(STEP_S),
           "--time-to-teleport", "-1", "--no-step-log", "true"]
    connected = False
    try:
        traci.start(cmd)
        connected = True
        traci.route.add("m1d0c_two_pass", list(FULL_ROUTE))

        while True:
            now = require_float(traci.simulation.getTime(), "simulation.getTime")
            if now >= HORIZON_S:
                break

            for vid, epoch in DEPART_EPOCH.items():
                if vid in released or now < epoch:
                    continue
                ledger.register_arrival(vid, now, metadata={"diagnostic_parking_pass": PARK_ON_PASS[vid]})
                traci.vehicle.add(
                    vehID=vid, routeID="m1d0c_two_pass", typeID="DEFAULT_VEHTYPE",
                    depart="now", departLane="first", departPos="base", departSpeed="0",
                )
                released.add(vid)

            traci.simulationStep()
            now = require_float(traci.simulation.getTime(), "simulation.getTime")
            departed = require_ids(traci.simulation.getDepartedIDList(), "getDepartedIDList")
            arrived = require_ids(traci.simulation.getArrivedIDList(), "getArrivedIDList")
            active = require_ids(traci.vehicle.getIDList(), "vehicle.getIDList")

            for vid in departed:
                if vid in ledger and ledger.get(vid).state == VehicleState.OUTSIDE:
                    ledger.transition(vid, VehicleState.ENTRY_QUEUE, now, "sumo_inserted")

            for vid in sorted(active):
                if vid not in ledger:
                    raise ValueError(f"SUMO vehicle not registered in ledger: {vid}")
                state = ledger.get(vid).state
                road = traci.vehicle.getRoadID(vid)
                if not isinstance(road, str):
                    raise TypeError(f"getRoadID returned non-string for {vid}")
                route_index = require_int(traci.vehicle.getRouteIndex(vid), "getRouteIndex")

                if road and not road.startswith(":") and road != previous_edge[vid]:
                    seen_edges[vid].append(road)
                    previous_edge[vid] = road
                    audit.append({"time_s": now, "vehicle_id": vid,
                                  "event": "enter_edge", "value": road})

                if state == VehicleState.ENTRY_QUEUE:
                    if now - ledger.get(vid).state_enter_time >= STEP_S - 1e-9:
                        ledger.transition(vid, VehicleState.CRUISING, now, "search_started")

                state = ledger.get(vid).state
                if (state == VehicleState.CRUISING and vid not in stop_requested
                        and should_request_parking(vid, road, route_index)):
                    traci.vehicle.setParkingAreaStop(vid, PARKING_AREA, duration=STOP_SECONDS)
                    stop_requested.add(vid)
                    audit.append({"time_s": now, "vehicle_id": vid,
                                  "event": "parking_command", "value": str(route_index)})

                if state == VehicleState.CRUISING and traci.vehicle.isStoppedParking(vid):
                    parked_index[vid] = route_index
                    ledger.transition(vid, VehicleState.PARKED, now, "physically_parked")
                    audit.append({"time_s": now, "vehicle_id": vid,
                                  "event": "parking_started", "value": str(route_index)})

                state = ledger.get(vid).state
                if state == VehicleState.PARKED and not traci.vehicle.isStoppedParking(vid):
                    # SHORTEN only after actual departure from parking. No teleport.
                    # A vehicle that parks on pass 1 must not traverse the return loop.
                    if vid == "early_park":
                        new_route = exit_route_from(road)
                        traci.vehicle.setRoute(vid, list(new_route))
                        shortened.add(vid)
                        audit.append({"time_s": now, "vehicle_id": vid,
                                      "event": "exit_route_changed", "value": " ".join(new_route)})
                    ledger.transition(vid, VehicleState.DEPARTING, now, "parking_stop_ended")

            for vid in arrived:
                if vid not in ledger:
                    raise ValueError(f"Unexpected arrival not in ledger: {vid}")
                state = ledger.get(vid).state
                if not allow_completed_after(state):
                    ledger.mark_removed_error(vid, now, "route_ended_without_completed_parking")
                else:
                    ledger.transition(vid, VehicleState.COMPLETED, now, "normal_exit_after_parking")

            for vid in list(ledger.ids()):
                state = ledger.get(vid).state
                if (state in {VehicleState.ENTRY_QUEUE, VehicleState.CRUISING,
                              VehicleState.PARKED, VehicleState.DEPARTING}
                        and vid not in active and vid not in arrived):
                    ledger.mark_removed_error(vid, now, "unexpected_sumo_disappearance")

            snap = ledger.snapshot(now)
            system_log.append(snap)
            if verbose or int(round(now)) % 20 == 0:
                print(f"t={now:5.0f} | gen={snap['generated_to_date']} "
                      f"parked={snap['n_parked']} done={snap['n_completed']} "
                      f"error={snap['n_removed_error']} MB={snap['mass_balance_error']}")
            if ledger.counts()[VehicleState.COMPLETED.value] == len(DEPART_EPOCH):
                break
    except Exception as exc:
        runtime_error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        if connected:
            traci.close()

    events: list[dict[str, Any]] = []
    for vid in DEPART_EPOCH:
        if vid in ledger:
            for e in ledger.get(vid).history:
                events.append({"vehicle_id": vid, "time_s": e.sim_time,
                               "from_state": "" if e.from_state is None else e.from_state.value,
                               "to_state": e.to_state.value, "reason": e.reason})

    max_mb = max(abs(int(row["mass_balance_error"])) for row in system_log)
    counts = ledger.counts()
    observed_a = tuple(seen_edges["early_park"])
    observed_b = tuple(seen_edges["late_park"])
    parked_pass_ok = parked_index == {"early_park": 1, "late_park": 7}
    routes_ok = observed_a == EARLY_EXPECTED and observed_b == LATE_EXPECTED
    completed_ok = counts[VehicleState.COMPLETED.value] == 2
    shortened_ok = shortened == {"early_park"}
    errors_ok = counts[VehicleState.REMOVED_ERROR.value] == 0 and runtime_error is None
    passed = all((parked_pass_ok, routes_ok, completed_ok, shortened_ok, errors_ok, max_mb == 0))
    result = {
        "status": "PASS" if passed else "FAIL",
        "formal_experiment": False,
        "candidate_id": "recirculation_v1",
        "stage_b_approved": False,
        "sop_amendment_required": True,
        "completed": counts[VehicleState.COMPLETED.value],
        "removed_error": counts[VehicleState.REMOVED_ERROR.value],
        "max_abs_mass_balance_error": max_mb,
        "parking_area": PARKING_AREA,
        "parked_route_indices": parked_index,
        "early_route_shortened": "early_park" in shortened,
        "early_observed_edges": list(observed_a),
        "late_observed_edges": list(observed_b),
        "expected_early_edges": list(EARLY_EXPECTED),
        "expected_late_edges": list(LATE_EXPECTED),
        "park_pass_check": parked_pass_ok,
        "route_branch_check": routes_ok,
        "runtime_error": runtime_error,
        "final_sim_time_s": system_log[-1]["time"],
    }
    write_csv(OUTPUT / "system_log.csv", system_log, list(system_log[0].keys()))
    write_csv(OUTPUT / "vehicle_events.csv", events,
              ["vehicle_id", "time_s", "from_state", "to_state", "reason"])
    write_csv(OUTPUT / "route_audit.csv", audit,
              ["time_s", "vehicle_id", "event", "value"])
    (OUTPUT / "summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("\n" + "=" * 74)
    print("MILESTONE 1D-0C - EXIT / RECIRCULATION ROUTE PROBE")
    print("=" * 74)
    print(f"Early edges         : {' -> '.join(observed_a)}")
    print(f"Late edges          : {' -> '.join(observed_b)}")
    print(f"Parking route index : {parked_index}")
    print(f"Early route shortened: {shortened_ok}")
    print(f"Completed           : {result['completed']}/2")
    print(f"Removed error       : {result['removed_error']}")
    print(f"Max mass balance err: {max_mb}")
    print(f"Route branch check  : {'PASS' if routes_ok else 'FAIL'}")
    print(f"Parking pass check  : {'PASS' if parked_pass_ok else 'FAIL'}")
    print(f"Technical verdict   : {result['status']}")
    print("Formal study status : HOLD_SOP_AMENDMENT_REQUIRED")
    print(f"Summary             : {OUTPUT / 'summary.json'}")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--precheck", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    try:
        manifest = validate_inputs()
        print("=" * 74)
        print("MILESTONE 1D-0C - EXIT / RECIRCULATION PRECHECK")
        print("=" * 74)
        print(f"Candidate           : {manifest['candidate_id']}")
        print("Candidate hashes    : PASS")
        print("Parking capacity    : 200 total / 170 general")
        print("Route semantics     : early park+exit / late recirculate+park+exit")
        print("Formal approval     : HOLD_SOP_AMENDMENT_REQUIRED")
        if args.precheck:
            print("PRECHECK PASS - no SUMO simulation was run.")
            return 0
        return run(args.verbose)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
