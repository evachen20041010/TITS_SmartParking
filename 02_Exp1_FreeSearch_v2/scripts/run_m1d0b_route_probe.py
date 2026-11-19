#!/usr/bin/env python3
"""M1D-0B: one-vehicle, two-pass SUMO topology probe (NOT a free-search test)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_m1d0b_candidate import (  # noqa: E402
    CANDIDATE,
    PROBE_EDGES,
    CandidateError,
    verify_net,
)

OUTPUT_DIR = PROJECT_ROOT / "validation" / "m1d0b" / "route_probe"
PROBE_ID = "probe_two_passes"
MAX_SIM_TIME_S = 350.0


def sumo_number(value: object, label: str) -> float:
    if type(value) not in (float, int):
        raise TypeError(f"{label} must return a numerical scalar; got {type(value).__name__}.")
    return float(value)


def main() -> int:
    try:
        verify_net(CANDIDATE)
    except CandidateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Build the candidate first: python scripts\\build_m1d0b_candidate.py")
        return 2

    sumo = shutil.which("sumo")
    if sumo is None:
        print("ERROR: sumo not on PATH. Activate sumo_py310.", file=sys.stderr)
        return 2

    try:
        import traci  # type: ignore[import-not-found]
    except ImportError as exc:
        print(f"ERROR: TraCI could not be imported: {exc}", file=sys.stderr)
        return 2

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trace: list[str] = []
    started = False
    arrived = False
    time_end = 0.0
    error: str | None = None
    cmd = [
        sumo,
        "-c", str(CANDIDATE / "base.sumocfg"),
        "--route-files", str(CANDIDATE / "route_probe.rou.xml"),
        "--time-to-teleport", "-1",
        "--step-length", "1.0",
        "--no-step-log", "true",
    ]

    try:
        traci.start(cmd)
        started = True
        while True:
            traci.simulationStep()
            now = sumo_number(traci.simulation.getTime(), "simulation.getTime")
            time_end = now
            if PROBE_ID in traci.simulation.getArrivedIDList():
                arrived = True
                break
            if PROBE_ID in traci.vehicle.getIDList():
                road: object = traci.vehicle.getRoadID(PROBE_ID)
                if not isinstance(road, str):
                    raise TypeError("vehicle.getRoadID must return a string")
                if road and not road.startswith(":") and (not trace or road != trace[-1]):
                    trace.append(road)
            if now >= MAX_SIM_TIME_S:
                break
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if started:
            try:
                traci.close()
            except Exception as exc:
                error = error or f"TraCI close failed: {type(exc).__name__}: {exc}"

    passed = error is None and arrived and trace == PROBE_EDGES
    summary: dict[str, Any] = {
        "status": "PASS" if passed else "FAIL",
        "formal_experiment": False,
        "scope": "route connectivity and physical revisitation only",
        "probe_vehicle": PROBE_ID,
        "arrived": arrived,
        "observed_edges": trace,
        "expected_edges": PROBE_EDGES,
        "same_three_parking_edges_visited_twice": trace == PROBE_EDGES,
        "final_time_s": time_end,
        "error": error,
        "sop_amendment_required_before_formal_experiment": True,
    }
    (OUTPUT_DIR / "route_probe_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("=" * 72)
    print("MILESTONE 1D-0B - SUMO TWO-PASS ROUTE PROBE")
    print("=" * 72)
    print(f"Vehicle arrived          : {arrived}")
    print(f"Observed edge sequence   : {' -> '.join(trace)}")
    print(f"Two-pass route           : {'PASS' if trace == PROBE_EDGES else 'FAIL'}")
    print(f"Route probe              : {summary['status']}")
    print("Formal study approval    : HOLD_SOP_AMENDMENT_REQUIRED")
    print(f"Summary                  : {OUTPUT_DIR / 'route_probe_summary.json'}")
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
    return 0 if passed else (2 if error else 1)


if __name__ == "__main__":
    sys.exit(main())
