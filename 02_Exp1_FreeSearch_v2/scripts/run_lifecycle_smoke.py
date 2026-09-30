#!/usr/bin/env python3
"""
Milestone 1B-2 - SUMO Lifecycle Smoke Test

Purpose:
- Connect VehicleLedger to real SUMO vehicle events.
- Verify outside -> entry_queue -> cruising -> parked -> departing -> completed.
- Require mass_balance_error == 0 at every recorded step.
- Require removed_error == 0.
- This is NOT a free-search experiment. Parking targets are fixed only to
  validate lifecycle integration.

Run from:
    C:\TITS_SmartParking\02_Exp1_FreeSearch_v2

Command:
    python scripts\run_lifecycle_smoke.py
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import traci

from vehicle_state import LifecycleError, VehicleLedger, VehicleState


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "network" / "canonical" / "base.sumocfg"
OUTPUT_DIR = PROJECT_ROOT / "validation" / "lifecycle_smoke"

ROUTE_ID = "lifecycle_smoke_route"
ROUTE_EDGES = ["E1", "E2", "E3"]

# Fixed parking target: this is a lifecycle test, not a search-strategy test.
TARGET_PARKING_AREA = "PA_Z2_G"

# Three released demand arrivals.
ARRIVALS = {
    "smoke_000": 0.0,
    "smoke_001": 10.0,
    "smoke_002": 20.0,
}

PARKING_DURATION_S = 15.0
SEARCH_START_POS_M = 5.0
MAX_SIM_TIME_S = 180.0


def append_event(event_rows, vehicle_id, sim_time, from_state, to_state, reason):
    event_rows.append(
        {
            "vehicle_id": vehicle_id,
            "time": float(sim_time),
            "from_state": "" if from_state is None else from_state.value,
            "to_state": to_state.value,
            "reason": reason,
        }
    )


def transition_and_log(
    ledger: VehicleLedger,
    event_rows: list[dict],
    vehicle_id: str,
    new_state: VehicleState,
    sim_time: float,
    reason: str,
) -> None:
    old_state = ledger.get(vehicle_id).state
    ledger.transition(vehicle_id, new_state, sim_time, reason)
    append_event(event_rows, vehicle_id, sim_time, old_state, new_state, reason)


def mark_error_and_log(
    ledger: VehicleLedger,
    event_rows: list[dict],
    vehicle_id: str,
    sim_time: float,
    reason: str,
) -> None:
    old_state = ledger.get(vehicle_id).state
    ledger.mark_removed_error(vehicle_id, sim_time, reason)
    append_event(
        event_rows,
        vehicle_id,
        sim_time,
        old_state,
        VehicleState.REMOVED_ERROR,
        reason,
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if not CONFIG_FILE.exists():
        print(f"ERROR: missing SUMO config: {CONFIG_FILE}")
        return 2

    sumo_binary = shutil.which("sumo")
    if not sumo_binary:
        print("ERROR: 'sumo' was not found on PATH.")
        return 2

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ledger = VehicleLedger()
    released = set()
    stop_commanded = set()
    event_rows: list[dict] = []
    system_rows: list[dict] = []

    print("=" * 76)
    print("T-ITS EXPERIMENT 1 - MILESTONE 1B-2 SUMO LIFECYCLE SMOKE TEST")
    print("=" * 76)
    print(f"SUMO       : {sumo_binary}")
    print(f"Config     : {CONFIG_FILE}")
    print(f"Route      : {' -> '.join(ROUTE_EDGES)}")
    print(f"Parking    : {TARGET_PARKING_AREA}")
    print(f"Vehicles   : {len(ARRIVALS)}")
    print(f"Park time  : {PARKING_DURATION_S:.0f} s")
    print()

    cmd = [
        sumo_binary,
        "-c",
        str(CONFIG_FILE),
        "--no-step-log",
        "true",
        "--time-to-teleport",
        "-1",
    ]

    try:
        traci.start(cmd)
        traci.route.add(ROUTE_ID, ROUTE_EDGES)

        while traci.simulation.getTime() <= MAX_SIM_TIME_S:
            now = float(traci.simulation.getTime())

            # Release demand arrivals whose scheduled arrival time is due.
            for vehicle_id, arrival_time in ARRIVALS.items():
                if vehicle_id in released or arrival_time > now:
                    continue

                ledger.register_arrival(
                    vehicle_id,
                    arrival_time=arrival_time,
                    metadata={"target_parking_area": TARGET_PARKING_AREA},
                )
                append_event(
                    event_rows,
                    vehicle_id,
                    now,
                    None,
                    VehicleState.OUTSIDE,
                    "demand_arrival_released",
                )

                traci.vehicle.add(
                    vehID=vehicle_id,
                    routeID=ROUTE_ID,
                    typeID="DEFAULT_VEHTYPE",
                    depart="now",
                    departLane="first",
                    departPos="base",
                    departSpeed="0",
                )
                released.add(vehicle_id)

            # Advance SUMO one step.
            traci.simulationStep()
            now = float(traci.simulation.getTime())

            departed_ids = set(traci.simulation.getDepartedIDList())
            arrived_ids = set(traci.simulation.getArrivedIDList())
            active_ids = set(traci.vehicle.getIDList())

            # A SUMO departure means insertion into the modeled road system.
            for vehicle_id in departed_ids:
                if vehicle_id in ledger:
                    rec = ledger.get(vehicle_id)
                    if rec.state == VehicleState.OUTSIDE:
                        transition_and_log(
                            ledger,
                            event_rows,
                            vehicle_id,
                            VehicleState.ENTRY_QUEUE,
                            now,
                            "sumo_departed_inserted",
                        )

            # Start active parking search after a small entrance-distance threshold.
            for vehicle_id in list(active_ids):
                if vehicle_id not in ledger:
                    continue

                rec = ledger.get(vehicle_id)

                if rec.state == VehicleState.ENTRY_QUEUE:
                    road_id = traci.vehicle.getRoadID(vehicle_id)
                    lane_pos = float(traci.vehicle.getLanePosition(vehicle_id))

                    if road_id == "E1" and lane_pos >= SEARCH_START_POS_M:
                        transition_and_log(
                            ledger,
                            event_rows,
                            vehicle_id,
                            VehicleState.CRUISING,
                            now,
                            f"search_activation_position>={SEARCH_START_POS_M:.1f}m",
                        )

                rec = ledger.get(vehicle_id)

                # Fixed parking command only for lifecycle validation.
                if (
                    rec.state == VehicleState.CRUISING
                    and vehicle_id not in stop_commanded
                ):
                    traci.vehicle.setParkingAreaStop(
                        vehicle_id,
                        TARGET_PARKING_AREA,
                        duration=PARKING_DURATION_S,
                    )
                    stop_commanded.add(vehicle_id)

                rec = ledger.get(vehicle_id)

                if (
                    rec.state == VehicleState.CRUISING
                    and traci.vehicle.isStoppedParking(vehicle_id)
                ):
                    transition_and_log(
                        ledger,
                        event_rows,
                        vehicle_id,
                        VehicleState.PARKED,
                        now,
                        "sumo_isStoppedParking_true",
                    )

                rec = ledger.get(vehicle_id)

                if (
                    rec.state == VehicleState.PARKED
                    and not traci.vehicle.isStoppedParking(vehicle_id)
                ):
                    transition_and_log(
                        ledger,
                        event_rows,
                        vehicle_id,
                        VehicleState.DEPARTING,
                        now,
                        "parking_stop_ended",
                    )

            # Process normal SUMO arrivals at the end of the route.
            for vehicle_id in arrived_ids:
                if vehicle_id not in ledger:
                    continue

                rec = ledger.get(vehicle_id)
                if rec.state == VehicleState.DEPARTING:
                    transition_and_log(
                        ledger,
                        event_rows,
                        vehicle_id,
                        VehicleState.COMPLETED,
                        now,
                        "sumo_arrived_normal_exit",
                    )
                elif rec.state not in {
                    VehicleState.COMPLETED,
                    VehicleState.REMOVED_ERROR,
                }:
                    mark_error_and_log(
                        ledger,
                        event_rows,
                        vehicle_id,
                        now,
                        f"sumo_arrived_from_unexpected_state:{rec.state.value}",
                    )

            # Detect unexplained disappearance of vehicles that should be in SUMO.
            for vehicle_id in list(ledger.ids()):
                rec = ledger.get(vehicle_id)
                if rec.state not in {
                    VehicleState.ENTRY_QUEUE,
                    VehicleState.CRUISING,
                    VehicleState.PARKED,
                    VehicleState.DEPARTING,
                }:
                    continue

                if vehicle_id not in active_ids and vehicle_id not in arrived_ids:
                    mark_error_and_log(
                        ledger,
                        event_rows,
                        vehicle_id,
                        now,
                        "unexpected_disappearance_from_sumo",
                    )

            snap = ledger.snapshot(now)
            system_rows.append(snap)

            print(
                f"t={now:6.1f} | generated={snap['generated_to_date']} "
                f"outside={snap['n_outside']} "
                f"entry={snap['n_entry_queue']} "
                f"cruise={snap['n_cruising']} "
                f"parked={snap['n_parked']} "
                f"depart={snap['n_departing']} "
                f"done={snap['n_completed']} "
                f"error={snap['n_removed_error']} "
                f"MB={snap['mass_balance_error']}"
            )

            if (
                len(released) == len(ARRIVALS)
                and ledger.counts()[VehicleState.COMPLETED.value] == len(ARRIVALS)
            ):
                break

        ledger.assert_mass_balance()

        counts = ledger.counts()
        max_abs_mass_balance_error = max(
            abs(int(row["mass_balance_error"])) for row in system_rows
        )

        expected_sequence = [
            VehicleState.OUTSIDE.value,
            VehicleState.ENTRY_QUEUE.value,
            VehicleState.CRUISING.value,
            VehicleState.PARKED.value,
            VehicleState.DEPARTING.value,
            VehicleState.COMPLETED.value,
        ]

        sequence_results = {}
        for vehicle_id in ARRIVALS:
            actual = [
                e.to_state.value for e in ledger.get(vehicle_id).history
            ]
            sequence_results[vehicle_id] = {
                "actual": actual,
                "expected": expected_sequence,
                "pass": actual == expected_sequence,
            }

        passed = (
            counts[VehicleState.COMPLETED.value] == len(ARRIVALS)
            and counts[VehicleState.REMOVED_ERROR.value] == 0
            and max_abs_mass_balance_error == 0
            and all(v["pass"] for v in sequence_results.values())
        )

        summary = {
            "status": "PASS" if passed else "FAIL",
            "vehicle_count": len(ARRIVALS),
            "completed": counts[VehicleState.COMPLETED.value],
            "removed_error": counts[VehicleState.REMOVED_ERROR.value],
            "max_abs_mass_balance_error": max_abs_mass_balance_error,
            "parking_area": TARGET_PARKING_AREA,
            "parking_duration_s": PARKING_DURATION_S,
            "search_start_pos_m": SEARCH_START_POS_M,
            "final_sim_time_s": system_rows[-1]["time"] if system_rows else None,
            "sequence_results": sequence_results,
        }

        write_csv(OUTPUT_DIR / "system_log.csv", system_rows)
        write_csv(OUTPUT_DIR / "vehicle_events.csv", event_rows)
        (OUTPUT_DIR / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print()
        print("=" * 76)
        print("MILESTONE 1B-2 SUMMARY")
        print("=" * 76)
        print(f"Completed vehicles         : {summary['completed']}/{len(ARRIVALS)}")
        print(f"removed_error              : {summary['removed_error']}")
        print(
            "max |mass_balance_error|  : "
            f"{summary['max_abs_mass_balance_error']}"
        )
        for vehicle_id, result in sequence_results.items():
            print(
                f"{vehicle_id} lifecycle        : "
                f"{'PASS' if result['pass'] else 'FAIL'}"
            )
            if not result["pass"]:
                print(f"  actual   = {result['actual']}")
                print(f"  expected = {result['expected']}")

        print()
        print(f"--- Milestone 1B-2 verdict ---")
        print(summary["status"])
        print(f"Validation files: {OUTPUT_DIR}")

        if passed:
            ledger.assert_formal_run_health()
            return 0
        return 1

    except (traci.TraCIException, LifecycleError, RuntimeError) as exc:
        print()
        print(f"ERROR: {type(exc).__name__}: {exc}")
        return 2

    finally:
        try:
            traci.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
