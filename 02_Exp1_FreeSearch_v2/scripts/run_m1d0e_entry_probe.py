#!/usr/bin/env python3
"""M1D-0E: tiny SUMO probe of new-entry and return approaches at J0.

NON-FORMAL: deliberately programmed 3-car fixture, NOT bounded-rational
free-search and NOT Event-A calibration.  Stops are fixed and diagnostic.
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

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.vehicle_state import VehicleLedger, VehicleState  # noqa: E402
from scripts.build_m1d0e_entry_candidate import (  # noqa: E402
    CANONICAL, PARENT, TARGET, ONE_PASS, TWO_PASS, ID,
    check_parent, verify_compiled, sha256_file, VERSION,
)

OUTPUT = ROOT / "validation" / "m1d0e"
AREA = "PA_Z2_G"
STEP = 1.0
DURATION_S = 12.0
HORIZON_S = 450.0
# Staggered low-demand movement probe; NOT merge conflict or spillback calibration.
RELEASE_S = {"early_park": 0.0, "late_park": 8.0, "fresh_at_merge": 100.0}
EXPECTED = {"early_park": ONE_PASS, "late_park": TWO_PASS, "fresh_at_merge": ONE_PASS}
PARK_E1_INDEX = {"early_park": 1, "late_park": 7, "fresh_at_merge": 1}
PARK_E2_INDEX = {"early_park": 2, "late_park": 8, "fresh_at_merge": 2}


def numeric(v: object, label: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f"{label} must be a numeric scalar")
    result = float(v)
    if not math.isfinite(result):
        raise ValueError(f"{label} is not finite")
    return result


def ids(v: object, label: str) -> set[str]:
    if not isinstance(v, (list, tuple, set)) or not all(isinstance(x, str) for x in v):
        raise TypeError(f"{label} must be a list/tuple/set of vehicle IDs")
    return set(v)


def checked_runtime_entry_length(actual_m: float, compiled_m: float) -> float:
    """Require TraCI lane length to match the compiled net, not nominal node spacing."""
    actual = numeric(actual_m, "TraCI E_IN lane length")
    compiled = numeric(compiled_m, "compiled E_IN lane length")
    if not math.isclose(actual, compiled, rel_tol=0.0, abs_tol=0.05):
        raise ValueError(
            f"TraCI E_IN length {actual} does not match compiled network {compiled}"
        )
    return actual


def should_park(vid: str, road: str, route_index: int) -> bool:
    return vid in PARK_E1_INDEX and road == "E1" and route_index == PARK_E1_INDEX[vid]


def exit_route(road: str) -> tuple[str, ...]:
    if road == "E2":
        return ("E2", "E3")
    if road == "E3":
        return ("E3",)
    raise ValueError(f"Parking-exit route cannot be set from road {road}")


def is_service_completion(state: VehicleState) -> bool:
    return state == VehicleState.DEPARTING


def entrance_and_return_observed(edges: dict[str, list[str]]) -> bool:
    """Both geometric approaches traversed in the same SUMO run.

    Does NOT assert any conflicting simultaneous arrival or queue spillback.
    """
    return (
        all(tuple(edges[v]) == EXPECTED[v] for v in EXPECTED)
        and any(a == "E_IN" and b == "E1" for v in ("early_park", "fresh_at_merge")
                for a, b in zip(edges[v], edges[v][1:]))
        and any(a == "E_RD" and b == "E1" for a, b in
                zip(edges["late_park"], edges["late_park"][1:]))
    )


def validate_inputs() -> dict[str, Any]:
    check_parent(PARENT, CANONICAL)
    manifest_path = TARGET / "candidate_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Build the v2 candidate first: {manifest_path}")
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("candidate_id") != ID or manifest.get("stage_b_approved") is not False:
        raise ValueError("Not the expected unapproved recirculation_v2_entry candidate")
    if manifest.get("formal_experiment_approved") is not False or manifest.get("physical_event_A_validated") is not False:
        raise ValueError("Diagnostic candidate must not claim formal approval or Event A validation")
    for name, value in manifest["candidate_sha256"].items():
        if sha256_file(TARGET / name) != value:
            raise ValueError(f"Candidate hash mismatch: {name}")
    if not manifest.get("candidate_net_sha256") or sha256_file(TARGET / "parking_lot.net.xml") != manifest["candidate_net_sha256"]:
        raise ValueError("Missing or mismatched compiled SUMO network")
    stats = verify_compiled(TARGET)
    if manifest.get("generator_version") != VERSION:
        raise ValueError("Candidate builder version does not match this probe; rebuild candidate")
    recorded = manifest.get("compiled_stats")
    if not isinstance(recorded, dict) or not math.isclose(
        float(recorded.get("E_IN_length_compiled_m", -1.0)),
        stats["E_IN_length_compiled_m"], rel_tol=0.0, abs_tol=0.01
    ):
        raise ValueError("Compiled E_IN length differs from candidate manifest")
    if tuple(manifest.get("new_arrival_route", ())) != ONE_PASS or tuple(manifest.get("one_return_route", ())) != TWO_PASS:
        raise ValueError("Expected routes differ from candidate manifest")
    areas = ET.parse(TARGET / "parking_areas.add.xml").getroot().findall("parkingArea")
    if sum(int(a.get("roadsideCapacity", 0)) for a in areas) != 200:
        raise ValueError("Parking capacity changed")
    return manifest


def write_csv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def run(verbose: bool = False) -> int:
    import traci  # type: ignore[import-not-found]

    exe = shutil.which("sumo")
    if not exe:
        raise FileNotFoundError("SUMO not in PATH; activate sumo_py310")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    ledger = VehicleLedger()
    released: set[str] = set()
    departures: set[str] = set()
    stopped: set[str] = set()
    shortened: set[str] = set()
    parked_indices: dict[str, int] = {}
    edges: dict[str, list[str]] = {v: [] for v in RELEASE_S}
    previous: dict[str, str] = {v: "" for v in RELEASE_S}
    system_log: list[dict[str, Any]] = [ledger.snapshot(0.0)]
    lane_rows: list[dict[str, Any]] = []
    lane_timeseries: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    collisions: set[str] = set()
    teleports: set[str] = set()
    emergency_stops: set[str] = set()
    run_error: str | None = None
    connected = False
    lane_length: float | None = None
    cmd = [exe, "-c", str(TARGET / "base.sumocfg"),
           "--time-to-teleport", "-1", "--step-length", str(STEP),
           "--no-step-log", "true"]
    try:
        traci.start(cmd)
        connected = True
        traci.route.add("m1d0e_short", list(ONE_PASS))
        traci.route.add("m1d0e_return", list(TWO_PASS))
        compiled_length = verify_compiled(TARGET)["E_IN_length_compiled_m"]
        lane_length = checked_runtime_entry_length(
            numeric(traci.lane.getLength("E_IN_0"), "E_IN lane length"),
            compiled_length,
        )
        while numeric(traci.simulation.getTime(), "time") < HORIZON_S:
            now = numeric(traci.simulation.getTime(), "time")
            for vid, when in RELEASE_S.items():
                if vid in released or now < when:
                    continue
                ledger.register_arrival(vid, now, metadata={"probe": True, "stop_on_index": PARK_E1_INDEX[vid]})
                traci.vehicle.add(
                    vehID=vid,
                    routeID="m1d0e_return" if vid in ("early_park", "late_park") else "m1d0e_short",
                    typeID="DEFAULT_VEHTYPE", depart="now", departLane="first",
                    departPos="base", departSpeed="0",
                )
                released.add(vid)

            traci.simulationStep()
            now = numeric(traci.simulation.getTime(), "time")
            departed = ids(traci.simulation.getDepartedIDList(), "departed IDs")
            arrived = ids(traci.simulation.getArrivedIDList(), "arrived IDs")
            active = ids(traci.vehicle.getIDList(), "active IDs")
            departures.update(departed)
            collisions.update(ids(traci.simulation.getCollidingVehiclesIDList(), "collision IDs"))
            teleports.update(ids(traci.simulation.getStartingTeleportIDList(), "teleport IDs"))
            emergency_stops.update(ids(traci.simulation.getEmergencyStoppingVehiclesIDList(), "emergency-stop IDs"))

            for vid in departed:
                if vid not in ledger:
                    raise ValueError(f"SUMO inserted unexpected vehicle {vid}")
                if ledger.get(vid).state == VehicleState.OUTSIDE:
                    ledger.transition(vid, VehicleState.ENTRY_QUEUE, now, "sumo_inserted_on_E_IN")

            for vid in sorted(active):
                if vid not in ledger:
                    raise ValueError(f"SUMO active vehicle missing in ledger: {vid}")
                road = traci.vehicle.getRoadID(vid)
                if not isinstance(road, str):
                    raise TypeError("Non-string vehicle road ID")
                route_index = traci.vehicle.getRouteIndex(vid)
                if not isinstance(route_index, int) or isinstance(route_index, bool):
                    raise TypeError("Non-integer route index")
                if road and not road.startswith(":") and road != previous[vid]:
                    edges[vid].append(road)
                    previous[vid] = road
                    audit.append({"time_s": now, "vehicle_id": vid, "event": "enter_edge", "value": road})
                if ledger.get(vid).state == VehicleState.ENTRY_QUEUE:
                    if now - ledger.get(vid).state_enter_time >= STEP - 1e-9:
                        ledger.transition(vid, VehicleState.CRUISING, now, "physical_entry_road_traversal")

                state = ledger.get(vid).state
                if state == VehicleState.CRUISING and vid not in stopped and should_park(vid, road, route_index):
                    traci.vehicle.setParkingAreaStop(vid, AREA, duration=DURATION_S)
                    stopped.add(vid)
                    audit.append({"time_s": now, "vehicle_id": vid, "event": "park_command", "value": str(route_index)})
                if state == VehicleState.CRUISING and traci.vehicle.isStoppedParking(vid):
                    parked_indices[vid] = route_index
                    ledger.transition(vid, VehicleState.PARKED, now, "physical_parking_started")
                    audit.append({"time_s": now, "vehicle_id": vid, "event": "parked", "value": str(route_index)})
                if ledger.get(vid).state == VehicleState.PARKED and not traci.vehicle.isStoppedParking(vid):
                    if vid == "early_park":
                        new_route = exit_route(road)
                        traci.vehicle.setRoute(vid, list(new_route))
                        shortened.add(vid)
                        audit.append({"time_s": now, "vehicle_id": vid, "event": "exit_route_updated", "value": " ".join(new_route)})
                    ledger.transition(vid, VehicleState.DEPARTING, now, "parking_stop_ended")

            lane_vehicles = ids(traci.lane.getLastStepVehicleIDs("E_IN_0"), "E_IN vehicle IDs")
            lane_timeseries.append({
                "time_s": now, "lane_id": "E_IN_0",
                "n_vehicles": len(lane_vehicles),
                "n_halting": int(traci.lane.getLastStepHaltingNumber("E_IN_0")),
                "lane_length_m": lane_length,
                "event_A_status": "NOT_CALIBRATED",
            })
            for vid in sorted(lane_vehicles):
                if vid not in active or traci.vehicle.getLaneID(vid) != "E_IN_0":
                    continue  # last-step IDs can have already crossed the junction
                lane_rows.append({
                    "time_s": now, "vehicle_id": vid,
                    "front_pos_m": numeric(traci.vehicle.getLanePosition(vid), "getLanePosition"),
                    "length_m": numeric(traci.vehicle.getLength(vid), "getLength"),
                    "speed_mps": numeric(traci.vehicle.getSpeed(vid), "getSpeed"),
                    "lane_length_m": lane_length,
                    "measurement_validity": "RAW_ONLY_NOT_CALIBRATED",
                })

            for vid in arrived:
                if vid not in ledger:
                    raise ValueError(f"Unregistered SUMO route completion: {vid}")
                if is_service_completion(ledger.get(vid).state):
                    ledger.transition(vid, VehicleState.COMPLETED, now, "normal_exit_after_parking")
                else:
                    ledger.mark_removed_error(vid, now, "route_ended_without_parking")

            for vid in ledger.ids():
                if (ledger.get(vid).state in (
                        VehicleState.ENTRY_QUEUE, VehicleState.CRUISING,
                        VehicleState.PARKED, VehicleState.DEPARTING)
                        and vid not in active and vid not in arrived):
                    ledger.mark_removed_error(vid, now, "unexpected_sumo_disappearance")

            snap = ledger.snapshot(now)
            system_log.append(snap)
            if verbose or int(round(now)) % 30 == 0:
                print(f"t={now:5.0f} | generated={snap['generated_to_date']} "
                      f"parked={snap['n_parked']} completed={snap['n_completed']} "
                      f"MB={snap['mass_balance_error']}")
            if ledger.counts()[VehicleState.COMPLETED.value] == len(RELEASE_S):
                break
    except Exception as exc:
        run_error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        if connected:
            traci.close()

    events: list[dict[str, Any]] = []
    for vid in RELEASE_S:
        if vid in ledger:
            for ev in ledger.get(vid).history:
                events.append({
                    "vehicle_id": vid, "time_s": ev.sim_time,
                    "from_state": "" if ev.from_state is None else ev.from_state.value,
                    "to_state": ev.to_state.value, "reason": ev.reason,
                })
    max_mb = max(abs(int(row["mass_balance_error"])) for row in system_log)
    counts = ledger.counts()
    routes_ok = entrance_and_return_observed(edges)
    parked_ok = parked_indices == PARK_E2_INDEX
    completion_ok = counts[VehicleState.COMPLETED.value] == 3
    no_errors = counts[VehicleState.REMOVED_ERROR.value] == 0 and not collisions and not teleports and run_error is None
    # Emergency braking is reported and is a diagnostic warning, not hidden.
    passed = all((routes_ok, parked_ok, completion_ok, no_errors,
                  max_mb == 0, shortened == {"early_park"},
                  departures == set(RELEASE_S)))
    summary = {
        "milestone": "1D-0E", "candidate_id": ID,
        "technical_verdict": "PASS" if passed else "FAIL",
        "source_type": "NON_FORMAL_FIXED_DECISION_PROBE",
        "formal_experiment_approved": False,
        "physical_event_A_calibrated": False,
        "physical_entry_link": "E_IN_0",
        "E_IN_length_compiled_m": lane_length,
        "E_IN_length_nominal_m": 150.0,
        "usable_entry_storage_length_m": None,
        "both_approaches_observed": routes_ok,
        "simultaneous_merge_conflict_validated": False,
        "parked_route_indices": parked_indices,
        "early_route_shortened": "early_park" in shortened,
        "completed": counts[VehicleState.COMPLETED.value],
        "removed_error": counts[VehicleState.REMOVED_ERROR.value],
        "max_abs_mass_balance_error": max_mb,
        "colliding_vehicle_ids": sorted(collisions),
        "teleport_vehicle_ids": sorted(teleports),
        "emergency_stop_vehicle_ids": sorted(emergency_stops),
        "observed_edges": edges,
        "raw_entrance_samples": len(lane_rows),
        "driver_search_policy": "NOT IMPLEMENTED",
        "runtime_error": run_error,
        "formal_study_status": "HOLD_SOP_AMENDMENT_REQUIRED",
    }
    write_csv(OUTPUT / "entry_lane_raw.csv", lane_rows,
              ["time_s", "vehicle_id", "front_pos_m", "length_m", "speed_mps", "lane_length_m", "measurement_validity"])
    write_csv(OUTPUT / "entry_lane_timeseries.csv", lane_timeseries,
              ["time_s", "lane_id", "n_vehicles", "n_halting", "lane_length_m", "event_A_status"])
    write_csv(OUTPUT / "vehicle_events.csv", events,
              ["vehicle_id", "time_s", "from_state", "to_state", "reason"])
    write_csv(OUTPUT / "system_log.csv", system_log, list(system_log[0]))
    write_csv(OUTPUT / "route_audit.csv", audit, ["time_s", "vehicle_id", "event", "value"])
    out = OUTPUT / "entry_probe_summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n" + "=" * 74)
    print("MILESTONE 1D-0E - ENTRY AND RECIRCULATION PROBE")
    print("=" * 74)
    for vid in RELEASE_S:
        print(f"{vid:<17}: {' -> '.join(edges[vid])}")
    print(f"Parking route indices     : {parked_indices}")
    print(f"Both J0 approaches        : {'PASS' if routes_ok else 'FAIL'}")
    print(f"Service completed          : {summary['completed']}/3")
    print(f"Removed error              : {summary['removed_error']}")
    print(f"Max mass balance err       : {max_mb}")
    print(f"Collisions / teleports     : {len(collisions)} / {len(teleports)}")
    print(f"Entry raw samples          : {len(lane_rows)} (NO Event A QC)")
    print(f"Technical verdict          : {summary['technical_verdict']}")
    print("Formal geometry gate       : HOLD_SOP_AMENDMENT_REQUIRED")
    print(f"Summary                    : {out}")
    return 0 if passed else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--precheck", action="store_true")
    p.add_argument("--verbose", action="store_true")
    opts = p.parse_args()
    try:
        validate_inputs()
        print("=" * 74)
        print("MILESTONE 1D-0E - ENTRANCE / RETURN PRECHECK")
        print("=" * 74)
        print("Source and network hashes  : PASS")
        print("J0 incoming roads          : E_IN, E_RD")
        print("Parking capacity           : 200 total / 170 general")
        print("Physical Event A QC        : NOT YET VALIDATED")
        print("Formal geometry gate       : HOLD_SOP_AMENDMENT_REQUIRED")
        if opts.precheck:
            print("PRECHECK PASS - no SUMO simulation performed")
            return 0
        return run(opts.verbose)
    except Exception as exc:
        print(f"PRECHECK ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
