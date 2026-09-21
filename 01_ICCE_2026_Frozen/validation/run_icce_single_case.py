from __future__ import annotations

import csv
import importlib.util
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import pandas as pd
import traci

CASE = {"name": "Free_95", "occupancy": 95, "strategy": "free"}
SEED = 10
EXPECTED = {
    "Is_Truncated": True,
    "N_Trips": 152,
    "Avg_Cruising_Time_s": 79.55263157894737,
    "Total_CO2_kg": 37.4852,
}
FACTOR_KG_PER_S = 0.0031


def first_line(text: str) -> str:
    return text.splitlines()[0] if text else ""


def bool_value(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def rel_error(new: float, old: float) -> float:
    if old == 0:
        return 0.0 if new == 0 else float("inf")
    return abs(new - old) / abs(old)


def parse_tripinfo(path: Path) -> dict[str, float | int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    idx = text.find("<tripinfos")
    if idx < 0:
        raise RuntimeError(f"Cannot find <tripinfos> in {path}")
    root = ET.fromstring(text[idx:])

    cruising = []
    stop_times = []
    vaporized_traci = 0
    route_length_zero = 0

    for trip in root.findall("tripinfo"):
        if trip.get("vaporized") == "traci":
            vaporized_traci += 1
            continue
        if float(trip.get("routeLength", "0")) <= 0:
            route_length_zero += 1
            continue

        duration = float(trip.get("duration", "0"))
        stop_time = float(trip.get("stopTime", "0"))
        cruising.append(max(0.0, duration - stop_time))
        stop_times.append(stop_time)

    n = len(cruising)
    avg = sum(cruising) / n if n else 0.0
    total_co2 = sum(cruising) * FACTOR_KG_PER_S

    return {
        "N_Trips": n,
        "Avg_Cruising_Time_s": avg,
        "Total_CO2_kg": total_co2,
        "Trips_with_stopTime_gt_1s": sum(x > 1.0 for x in stop_times),
        "Trips_with_stopTime_le_1s": sum(x <= 1.0 for x in stop_times),
        "Vaporized_traci": vaporized_traci,
        "RouteLength_zero": route_length_zero,
    }


def main() -> int:
    frozen_root = Path(__file__).resolve().parents[1]
    snapshot = frozen_root / "snapshot" / "sumo_parking"

    required = [
        "run_simulation.py",
        "extract_kpi.py",
        "parking_areas.add.xml",
        "parking_lot.net.xml",
        "traffic.rou.xml",
        "your_config.sumocfg",
        "parking.edg.xml",
        "parking.nod.xml",
    ]

    missing = [name for name in required if not (snapshot / name).exists()]
    if missing:
        print("ERROR: Frozen snapshot is not in the expected location:")
        print(f"  {snapshot}")
        print("Missing files:")
        for name in missing:
            print(f"  - {name}")
        return 2

    if not os.environ.get("SUMO_HOME"):
        print("ERROR: SUMO_HOME is not defined. Activate the ICCE environment first.")
        return 3

    sumo_exe = shutil.which("sumo")
    if not sumo_exe:
        print("ERROR: sumo is not available on PATH.")
        return 4

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = frozen_root / "validation" / "runs" / f"Free_95_seed10_{timestamp}"
    work_dir = run_dir / "workspace"
    work_dir.mkdir(parents=True, exist_ok=False)

    for name in required:
        shutil.copy2(snapshot / name, work_dir / name)

    sumo_version = subprocess.run(
        [sumo_exe, "--version"], capture_output=True, text=True, check=False
    )

    env_lines = [
        f"timestamp={timestamp}",
        f"python_version={sys.version.replace(chr(10), ' ')}",
        f"python_executable={sys.executable}",
        f"sumo_executable={sumo_exe}",
        f"sumo_version={first_line(sumo_version.stdout)}",
        f"SUMO_HOME={os.environ.get('SUMO_HOME')}",
        f"traci_file={traci.__file__}",
        f"case={CASE['name']}",
        f"seed={SEED}",
    ]
    (run_dir / "environment_runtime.txt").write_text(
        "\n".join(env_lines) + "\n", encoding="utf-8"
    )

    print("=" * 72)
    print("ICCE-TW 2026 SINGLE-CASE REPRODUCTION")
    print("Case: Free_95 | Seed: 10")
    print(f"Python: {sys.executable}")
    print(f"SUMO:   {sumo_exe}")
    print(f"TraCI:  {traci.__file__}")
    print(f"Work:   {work_dir}")
    print("=" * 72)

    old_cwd = Path.cwd()
    try:
        os.chdir(work_dir)

        spec = importlib.util.spec_from_file_location(
            "icce_run_simulation", work_dir / "run_simulation.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Cannot load run_simulation.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        module.SCENARIOS = [CASE.copy()]
        module.SEEDS = [SEED]
        module.run()

        # Run the original KPI extractor and preserve its console output.
        kpi_proc = subprocess.run(
            [sys.executable, "extract_kpi.py"],
            capture_output=True,
            text=True,
            check=False,
        )
        (run_dir / "original_extract_kpi_stdout.txt").write_text(
            kpi_proc.stdout + ("\nSTDERR:\n" + kpi_proc.stderr if kpi_proc.stderr else ""),
            encoding="utf-8",
        )

    finally:
        os.chdir(old_cwd)

    summary_path = work_dir / "sumo_results_summary.csv"
    tripinfo_path = work_dir / "outputs" / "tripinfo_Free_95_10.xml"

    if not summary_path.exists() or not tripinfo_path.exists():
        print("ERROR: Expected output files were not produced.")
        return 5

    summary = pd.read_csv(summary_path)
    if len(summary) != 1:
        raise RuntimeError(f"Expected one summary row, got {len(summary)}")
    row = summary.iloc[0]
    truncated = bool_value(row["Is_Truncated"])

    kpi = parse_tripinfo(tripinfo_path)

    checks = []
    checks.append(
        {
            "Metric": "Is_Truncated",
            "Expected": str(EXPECTED["Is_Truncated"]),
            "Observed": str(truncated),
            "Relative_Error": "",
            "Pass_5pct": truncated == EXPECTED["Is_Truncated"],
        }
    )

    for metric in ["N_Trips", "Avg_Cruising_Time_s", "Total_CO2_kg"]:
        observed = float(kpi[metric])
        expected = float(EXPECTED[metric])
        err = rel_error(observed, expected)
        checks.append(
            {
                "Metric": metric,
                "Expected": expected,
                "Observed": observed,
                "Relative_Error": err,
                "Pass_5pct": err <= 0.05,
            }
        )

    result_csv = run_dir / "validation_result.csv"
    with result_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Metric", "Expected", "Observed", "Relative_Error", "Pass_5pct"],
        )
        writer.writeheader()
        writer.writerows(checks)

    detail_lines = [
        f"N_Trips={kpi['N_Trips']}",
        f"Avg_Cruising_Time_s={kpi['Avg_Cruising_Time_s']:.12f}",
        f"Total_CO2_kg={kpi['Total_CO2_kg']:.12f}",
        f"Trips_with_stopTime_gt_1s={kpi['Trips_with_stopTime_gt_1s']}",
        f"Trips_with_stopTime_le_1s={kpi['Trips_with_stopTime_le_1s']}",
        f"Vaporized_traci={kpi['Vaporized_traci']}",
        f"RouteLength_zero={kpi['RouteLength_zero']}",
    ]
    (run_dir / "observed_kpi.txt").write_text(
        "\n".join(detail_lines) + "\n", encoding="utf-8"
    )

    print("\n--- Expected archived ICCE result ---")
    print("Is_Truncated: True")
    print("N_Trips: 152")
    print("Avg cruising: 79.55263157894737 s")
    print("Total CO2: 37.4852 kg")

    print("\n--- Reproduced result ---")
    print(f"Is_Truncated: {truncated}")
    for line in detail_lines:
        print(line)

    all_pass = all(bool(x["Pass_5pct"]) for x in checks)
    print("\n--- Milestone 0A verdict ---")
    print("PASS" if all_pass else "FAIL / INVESTIGATE")
    print(f"Validation files: {run_dir}")

    return 0 if all_pass else 10


if __name__ == "__main__":
    raise SystemExit(main())
