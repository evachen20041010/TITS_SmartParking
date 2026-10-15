#!/usr/bin/env python3
"""Milestone 1C-3: non-formal dynamic demand / SUMO lifecycle smoke test.

Run from the Experiment 1 project root:
    python scripts/run_dynamic_demand_smoke.py --precheck
    python scripts/run_dynamic_demand_smoke.py

Tests independently seeded Poisson arrivals and lognormal parking durations,
continuous-time event -> control-epoch mapping, SUMO insertion and parking,
vehicle lifecycle transitions, and per-epoch mass balance.

All numbers in this script are SMOKE-TEST FIXTURES, not research parameters.
There is no free-search algorithm in this test: vehicles use PA_Z2_G.
"""

from __future__ import annotations

import argparse
import csv
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

from scripts.demand_generator import (  # noqa: E402
    ArrivalEvent,
    generate_poisson_arrivals,
    schedule_fingerprint,
)
from scripts.parking_duration import (  # noqa: E402
    ParkingDurationEvent,
    derive_stream_seed,
    duration_fingerprint,
    generate_lognormal_durations,
)
from scripts.vehicle_state import (  # noqa: E402
    LifecycleError,
    VehicleLedger,
    VehicleState,
)

# This is NOT a formal rho experiment: parameters are for smoke testing only.
MASTER_SEED = 10
ARRIVAL_RATE_PER_S = 0.04
DEMAND_START_S = 0.0
DEMAND_END_S = 120.0
PARKING_MEAN_S = 20.0
PARKING_CV = 0.25
CONTROL_STEP_S = 1.0
MAX_SIM_TIME_S = 300.0

ROUTE_ID = "smoke_dynamic_route"
ROUTE_EDGES = ["E1", "E2", "E3"]
TARGET_PARKING_AREA = "PA_Z2_G"
ENTRY_SEARCH_BOUNDARY_M = 25.0

CONFIG_FILE = PROJECT_ROOT / "network" / "canonical" / "base.sumocfg"
PARKING_FILE = PROJECT_ROOT / "network" / "canonical" / "parking_areas.add.xml"
NETWORK_SUMMARY = PROJECT_ROOT / "validation" / "network_summary.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "validation" / "dynamic_demand_smoke"

EXPECTED_STATES = [
    VehicleState.OUTSIDE.value,
    VehicleState.ENTRY_QUEUE.value,
    VehicleState.CRUISING.value,
    VehicleState.PARKED.value,
    VehicleState.DEPARTING.value,
    VehicleState.COMPLETED.value,
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--precheck", action="store_true", help="No SUMO run; validate inputs and RNG schedule.")
    p.add_argument("--verbose", action="store_true", help="Print every simulation step.")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return p.parse_args()


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def require_sumo_float(value: object, source: str) -> float:
    """Validate and normalize a numeric TraCI result.

    SUMO's TraCI implementation exposes broad/dynamic return annotations to
    static analyzers. Treat the boundary as unknown, validate at runtime,
    and expose a narrow ``float`` type to the rest of the simulator.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(
            f"{source} must return a numeric scalar, "
            f"got {type(value).__name__}: {value!r}"
        )
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{source} returned non-finite value: {result!r}")
    return result


def require_vehicle_id_set(value: object, source: str) -> set[str]:
    """Validate and normalize a list/tuple of SUMO vehicle IDs to set[str]."""
    if not isinstance(value, (list, tuple)):
        raise TypeError(
            f"{source} must return a list/tuple of vehicle IDs, "
            f"got {type(value).__name__}"
        )

    vehicle_ids: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise TypeError(
                f"{source} contained a non-string vehicle ID: {item!r}"
            )
        vehicle_ids.add(item)
    return vehicle_ids


def append_event(
    events: list[dict[str, Any]],
    vehicle_id: str,
    time_s: float,
    previous: VehicleState | None,
    new: VehicleState,
    reason: str,
) -> None:
    events.append(
        {
            "vehicle_id": vehicle_id,
            "time_s": time_s,
            "from_state": "" if previous is None else previous.value,
            "to_state": new.value,
            "reason": reason,
        }
    )


def move(
    ledger: VehicleLedger,
    events: list[dict[str, Any]],
    vehicle_id: str,
    new: VehicleState,
    now: float,
    reason: str,
) -> None:
    previous = ledger.get(vehicle_id).state
    ledger.transition(vehicle_id, new, now, reason)
    append_event(events, vehicle_id, now, previous, new, reason)


def report_error(
    ledger: VehicleLedger,
    events: list[dict[str, Any]],
    vehicle_id: str,
    now: float,
    reason: str,
) -> None:
    previous = ledger.get(vehicle_id).state
    ledger.mark_removed_error(vehicle_id, now, reason)
    append_event(events, vehicle_id, now, previous, VehicleState.REMOVED_ERROR, reason)


def validate_network_inputs() -> dict[str, Any]:
    if not CONFIG_FILE.is_file():
        raise FileNotFoundError(f"Missing base.sumocfg: {CONFIG_FILE}")
    if not PARKING_FILE.is_file():
        raise FileNotFoundError(f"Missing parking_areas.add.xml: {PARKING_FILE}")
    if not NETWORK_SUMMARY.is_file():
        raise FileNotFoundError(f"Missing validated network_summary.json: {NETWORK_SUMMARY}")

    capacity = json.loads(NETWORK_SUMMARY.read_text(encoding="utf-8"))
    if capacity.get("status") != "PASS" or capacity.get("effective_capacity") != 170:
        raise ValueError("Expected a validated general-only C_eff=170 network summary.")

    root = ET.parse(PARKING_FILE).getroot()
    matched = [
        el for el in root.findall("parkingArea")
        if el.get("id") == TARGET_PARKING_AREA
    ]
    if len(matched) != 1 or matched[0].get("lane") != "E2_0":
        raise ValueError(f"Parking area {TARGET_PARKING_AREA} is missing or on wrong lane.")
    if int(matched[0].get("roadsideCapacity", "0")) < 1:
        raise ValueError("Smoke parking area has zero capacity.")
    return capacity


def generate_exogenous_inputs() -> tuple[list[ArrivalEvent], list[ParkingDurationEvent], int, int]:
    arrival_seed = derive_stream_seed(MASTER_SEED, "arrival")
    parking_seed = derive_stream_seed(MASTER_SEED, "parking_duration")
    if arrival_seed == parking_seed:
        raise AssertionError("Arrival/parking streams must have different seeds.")

    arrivals = generate_poisson_arrivals(
        rate_per_s=ARRIVAL_RATE_PER_S,
        start_time_s=DEMAND_START_S,
        end_time_s=DEMAND_END_S,
        seed=arrival_seed,
        id_prefix="dyn",
    )
    durations = generate_lognormal_durations(
        vehicle_ids=[event.vehicle_id for event in arrivals],
        mean_s=PARKING_MEAN_S,
        cv=PARKING_CV,
        seed=parking_seed,
    )
    if not arrivals:
        raise ValueError("Empty smoke demand; choose a seed with at least one arrival.")
    if [a.vehicle_id for a in arrivals] != [d.vehicle_id for d in durations]:
        raise AssertionError("Arrival and duration ID order does not match.")
    return arrivals, durations, arrival_seed, parking_seed


def print_precheck(
    arrivals: list[ArrivalEvent],
    durations: list[ParkingDurationEvent],
    arrival_seed: int,
    parking_seed: int,
) -> None:
    print("=" * 76)
    print("T-ITS EXPERIMENT 1 - MILESTONE 1C-3 DYNAMIC-DEMAND SMOKE TEST")
    print("=" * 76)
    print("Mode                : NON-FORMAL SMOKE TEST")
    print(f"SUMO config         : {CONFIG_FILE}")
    print(f"Route               : {' -> '.join(ROUTE_EDGES)}")
    print(f"Parking area        : {TARGET_PARKING_AREA} (general legal)")
    print(f"Master seed         : {MASTER_SEED}")
    print(f"Arrival stream seed : {arrival_seed}")
    print(f"Parking stream seed : {parking_seed}")
    print(f"Poisson lambda      : {ARRIVAL_RATE_PER_S} veh/s")
    print(f"Demand window       : [{DEMAND_START_S}, {DEMAND_END_S}) s")
    print(f"Parking mean/CV     : {PARKING_MEAN_S} s / {PARKING_CV}")
    print(f"Control step        : {CONTROL_STEP_S} s")
    print(f"Generated vehicles  : {len(arrivals)}")
    print(f"Arrival SHA-256     : {schedule_fingerprint(arrivals)}")
    print(f"Duration SHA-256    : {duration_fingerprint(durations)}")
    print("NOT FOR FORMAL EXPERIMENT RESULTS")


def run(
    arrivals: list[ArrivalEvent],
    durations: list[ParkingDurationEvent],
    output_dir: Path,
    verbose: bool,
    arrival_seed: int,
    parking_seed: int,
) -> int:
    # Lazy import lets --precheck run without TraCI and SUMO installed.
    import traci  # type: ignore[import-not-found]

    sumo_binary = shutil.which("sumo")
    if sumo_binary is None:
        raise FileNotFoundError("SUMO binary was not found on PATH; activate sumo_py310.")

    output_dir.mkdir(parents=True, exist_ok=True)
    duration_for = {event.vehicle_id: event.parking_duration_s for event in durations}

    write_csv(
        output_dir / "arrival_schedule.csv",
        [
            {"vehicle_id": event.vehicle_id, "scheduled_arrival_s": f"{event.arrival_time_s:.12f}"}
            for event in arrivals
        ],
        ["vehicle_id", "scheduled_arrival_s"],
    )
    write_csv(
        output_dir / "parking_durations.csv",
        [
            {"vehicle_id": event.vehicle_id, "parking_duration_s": f"{event.parking_duration_s:.12f}"}
            for event in durations
        ],
        ["vehicle_id", "parking_duration_s"],
    )

    ledger = VehicleLedger()
    events: list[dict[str, Any]] = []
    system_rows: list[dict[str, Any]] = [ledger.snapshot(0.0)]
    release_rows: list[dict[str, Any]] = []
    released: set[str] = set()
    commanded_parking: set[str] = set()
    release_epoch_for: dict[str, float] = {}
    next_arrival_idx = 0

    cmd = [
        sumo_binary,
        "-c", str(CONFIG_FILE),
        "--step-length", str(CONTROL_STEP_S),
        "--time-to-teleport", "-1",
        "--no-step-log", "true",
    ]
    connected = False
    try:
        traci.start(cmd)
        connected = True
        traci.route.add(ROUTE_ID, ROUTE_EDGES)

        while require_sumo_float(traci.simulation.getTime(), "simulation.getTime") < MAX_SIM_TIME_S:
            # Advance first. The observations/event lists are labeled with the
            # *end* time of the just-finished SUMO step.
            traci.simulationStep()
            now: float = require_sumo_float(
                traci.simulation.getTime(), "simulation.getTime"
            )
            departed_ids: set[str] = require_vehicle_id_set(
                traci.simulation.getDepartedIDList(), "simulation.getDepartedIDList"
            )
            arrived_ids: set[str] = require_vehicle_id_set(
                traci.simulation.getArrivedIDList(), "simulation.getArrivedIDList"
            )
            active_ids: set[str] = require_vehicle_id_set(
                traci.vehicle.getIDList(), "vehicle.getIDList"
            )

            # Handle departures (SUMO road insertion) before checking active state.
            for vid in departed_ids:
                if vid in ledger and ledger.get(vid).state == VehicleState.OUTSIDE:
                    move(ledger, events, vid, VehicleState.ENTRY_QUEUE, now, "sumo_inserted")

            # Normal end-of-route arrivals are not in active_ids any longer.
            for vid in arrived_ids:
                if vid not in ledger:
                    continue
                old = ledger.get(vid).state
                if old == VehicleState.DEPARTING:
                    move(ledger, events, vid, VehicleState.COMPLETED, now, "sumo_normal_exit")
                elif old not in {VehicleState.COMPLETED, VehicleState.REMOVED_ERROR}:
                    report_error(ledger, events, vid, now, f"early_route_exit_from:{old.value}")

            for vid in sorted(active_ids):
                if vid not in ledger:
                    raise LifecycleError(f"Unexpected SUMO vehicle not in ledger: {vid}")
                state = ledger.get(vid).state

                # Do not collapse insertion and search activation into one epoch.
                if state == VehicleState.ENTRY_QUEUE:
                    road_id = traci.vehicle.getRoadID(vid)
                    lane_pos: float = require_sumo_float(
                        traci.vehicle.getLanePosition(vid), "vehicle.getLanePosition"
                    )
                    duration_in_entry = now - ledger.get(vid).state_enter_time
                    if (
                        road_id == "E1"
                        and lane_pos >= ENTRY_SEARCH_BOUNDARY_M
                        and duration_in_entry >= CONTROL_STEP_S - 1e-9
                    ):
                        move(
                            ledger, events, vid, VehicleState.CRUISING, now,
                            f"passed_entry_boundary_{ENTRY_SEARCH_BOUNDARY_M:g}m",
                        )

                state = ledger.get(vid).state
                if state == VehicleState.CRUISING and vid not in commanded_parking:
                    traci.vehicle.setParkingAreaStop(
                        vid, TARGET_PARKING_AREA, duration=duration_for[vid]
                    )
                    commanded_parking.add(vid)

                # Vehicle may have been parked by SUMO during this step.
                state = ledger.get(vid).state
                if state == VehicleState.CRUISING and traci.vehicle.isStoppedParking(vid):
                    move(ledger, events, vid, VehicleState.PARKED, now, "sumo_parking_stop_started")

                state = ledger.get(vid).state
                if state == VehicleState.PARKED and not traci.vehicle.isStoppedParking(vid):
                    move(ledger, events, vid, VehicleState.DEPARTING, now, "sumo_parking_stop_ended")

            # An inserted (active) vehicle disappearing unexpectedly is an error.
            for vid in tuple(ledger.ids()):
                state = ledger.get(vid).state
                if state in {
                    VehicleState.ENTRY_QUEUE, VehicleState.CRUISING,
                    VehicleState.PARKED, VehicleState.DEPARTING,
                } and vid not in active_ids and vid not in arrived_ids:
                    report_error(ledger, events, vid, now, "unexpected_sumo_disappearance")

            # Release continuous scheduled arrivals at the FIRST control epoch
            # at or after their scheduled time. Release+snapshot share timestamp.
            while (
                next_arrival_idx < len(arrivals)
                and arrivals[next_arrival_idx].arrival_time_s <= now + 1e-12
            ):
                event = arrivals[next_arrival_idx]
                vid = event.vehicle_id
                ledger.register_arrival(
                    vehicle_id=vid,
                    arrival_time=event.arrival_time_s,
                    metadata={
                        "target_parking_area": TARGET_PARKING_AREA,
                        "parking_duration_s": duration_for[vid],
                        "scheduled_arrival_s": event.arrival_time_s,
                    },
                )
                released.add(vid)
                release_epoch_for[vid] = now
                append_event(
                    events, vid, event.arrival_time_s, None,
                    VehicleState.OUTSIDE, "scheduled_demand_arrival",
                )

                # SUMO attempts insertion at a following simulationStep().
                traci.vehicle.add(
                    vehID=vid,
                    routeID=ROUTE_ID,
                    typeID="DEFAULT_VEHTYPE",
                    depart="now",
                    departLane="first",
                    departPos="base",
                    departSpeed="0",
                )
                release_rows.append(
                    {
                        "vehicle_id": vid,
                        "scheduled_arrival_s": event.arrival_time_s,
                        "release_epoch_s": now,
                        "release_delay_s": now - event.arrival_time_s,
                        "parking_duration_s": duration_for[vid],
                    }
                )
                next_arrival_idx += 1

            snap = ledger.snapshot(now)
            system_rows.append(snap)

            if verbose or int(round(now)) % 10 == 0:
                print(
                    f"t={now:5.0f} | gen={snap['generated_to_date']:2d} "
                    f"outside={snap['n_outside']:2d} "
                    f"entry={snap['n_entry_queue']:2d} "
                    f"cruise={snap['n_cruising']:2d} "
                    f"parked={snap['n_parked']:2d} "
                    f"depart={snap['n_departing']:2d} "
                    f"done={snap['n_completed']:2d} "
                    f"error={snap['n_removed_error']:2d} "
                    f"MB={snap['mass_balance_error']}"
                )

            if (
                len(released) == len(arrivals)
                and ledger.counts()[VehicleState.COMPLETED.value] == len(arrivals)
            ):
                break

    finally:
        if connected:
            traci.close()

    # Persist artifacts and compute PASS/FAIL. A failed smoke test is recorded
    # as FAIL; no test parameters are retuned to make it pass.
    write_csv(
        output_dir / "demand_release_audit.csv", release_rows,
        ["vehicle_id", "scheduled_arrival_s", "release_epoch_s", "release_delay_s", "parking_duration_s"],
    )
    write_csv(
        output_dir / "vehicle_events.csv", events,
        ["vehicle_id", "time_s", "from_state", "to_state", "reason"],
    )
    write_csv(
        output_dir / "system_log.csv", system_rows,
        list(system_rows[0].keys()),
    )

    counts = ledger.counts()
    max_abs_mb = max(abs(int(r["mass_balance_error"])) for r in system_rows)
    delays = [float(row["release_delay_s"]) for row in release_rows]
    release_delay_pass = (
        len(release_rows) == len(arrivals)
        and all(-1e-9 <= delay <= CONTROL_STEP_S + 1e-9 for delay in delays)
    )

    lifecycle_results: dict[str, dict[str, Any]] = {}
    for vid in [a.vehicle_id for a in arrivals]:
        record = ledger.get(vid)
        actual = [event.to_state.value for event in record.history]
        transition_times = {event.to_state.value: event.sim_time for event in record.history}
        entry_t = transition_times.get(VehicleState.ENTRY_QUEUE.value)
        cruise_t = transition_times.get(VehicleState.CRUISING.value)
        release_t = release_epoch_for.get(vid)
        visible_outside = (
            release_t is not None and entry_t is not None
            and entry_t - release_t >= CONTROL_STEP_S - 1e-9
        )
        visible_entry = (
            entry_t is not None and cruise_t is not None
            and cruise_t - entry_t >= CONTROL_STEP_S - 1e-9
        )
        lifecycle_results[vid] = {
            "actual": actual,
            "expected": EXPECTED_STATES,
            "sequence_pass": actual == EXPECTED_STATES,
            "outside_visible_for_one_epoch": visible_outside,
            "entry_queue_visible_for_one_epoch": visible_entry,
        }

    completed = counts[VehicleState.COMPLETED.value]
    all_sequences = all(row["sequence_pass"] for row in lifecycle_results.values())
    outside_pass = all(row["outside_visible_for_one_epoch"] for row in lifecycle_results.values())
    entry_pass = all(row["entry_queue_visible_for_one_epoch"] for row in lifecycle_results.values())
    passed = (
        len(released) == len(arrivals)
        and completed == len(arrivals)
        and counts[VehicleState.REMOVED_ERROR.value] == 0
        and max_abs_mb == 0
        and release_delay_pass
        and outside_pass and entry_pass and all_sequences
    )

    summary = {
        "status": "PASS" if passed else "FAIL",
        "formal_experiment": False,
        "purpose": "Milestone 1C-3 integration smoke test only",
        "master_seed": MASTER_SEED,
        "arrival_stream_seed": arrival_seed,
        "parking_stream_seed": parking_seed,
        "arrival_rate_per_s": ARRIVAL_RATE_PER_S,
        "demand_start_s": DEMAND_START_S,
        "demand_end_s": DEMAND_END_S,
        "parking_mean_s": PARKING_MEAN_S,
        "parking_cv": PARKING_CV,
        "control_step_s": CONTROL_STEP_S,
        "generated_arrivals": len(arrivals),
        "released_arrivals": len(released),
        "completed": completed,
        "removed_error": counts[VehicleState.REMOVED_ERROR.value],
        "max_abs_mass_balance_error": max_abs_mb,
        "max_release_delay_s": max(delays) if delays else None,
        "release_delay_rule_pass": release_delay_pass,
        "outside_visible_for_one_epoch": outside_pass,
        "entry_queue_visible_for_one_epoch": entry_pass,
        "arrival_schedule_sha256": schedule_fingerprint(arrivals),
        "parking_duration_sha256": duration_fingerprint(durations),
        "final_sim_time_s": system_rows[-1]["time"],
        "lifecycle_results": lifecycle_results,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n" + "=" * 76)
    print("MILESTONE 1C-3 SUMMARY")
    print("=" * 76)
    print(f"Generated arrivals         : {len(arrivals)}")
    print(f"Released arrivals          : {len(released)}/{len(arrivals)}")
    print(f"Completed vehicles         : {completed}/{len(arrivals)}")
    print(f"removed_error              : {summary['removed_error']}")
    print(f"max |mass_balance_error|   : {max_abs_mb}")
    print(f"max release delay          : {summary['max_release_delay_s']} s")
    print(f"release-delay rule         : {'PASS' if release_delay_pass else 'FAIL'}")
    print(f"outside visible >= 1 step  : {'PASS' if outside_pass else 'FAIL'}")
    print(f"entry visible >= 1 step    : {'PASS' if entry_pass else 'FAIL'}")
    for vid, row in lifecycle_results.items():
        print(f"{vid} lifecycle         : {'PASS' if row['sequence_pass'] else 'FAIL'}")
        if not row["sequence_pass"]:
            print(f"  actual = {row['actual']}")
    print("\n--- Milestone 1C-3 verdict ---")
    print(summary["status"])
    print(f"Validation files: {output_dir}")
    if passed:
        ledger.assert_formal_run_health()
    return 0 if passed else 1


def main() -> int:
    args = parse_args()
    try:
        validate_network_inputs()
        arrivals, durations, arrival_seed, parking_seed = generate_exogenous_inputs()
        print_precheck(arrivals, durations, arrival_seed, parking_seed)
        if args.precheck:
            print("\nPRECHECK PASS - no SUMO simulation was run.")
            return 0
        return run(
            arrivals, durations, args.output_dir.resolve(), args.verbose,
            arrival_seed, parking_seed,
        )
    except Exception as exc:
        print(f"\nERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
