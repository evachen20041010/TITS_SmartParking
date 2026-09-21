from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path

import traci

SCENARIOS = [
    {"name": "Free_85", "occupancy": 85, "strategy": "free"},
    {"name": "Free_95", "occupancy": 95, "strategy": "free"},
    {"name": "Assigned_85", "occupancy": 85, "strategy": "assigned"},
    {"name": "Assigned_95", "occupancy": 95, "strategy": "assigned"},
]
SEEDS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
FACTOR_KG_PER_S = 0.0031
NUMERIC_TOL = 1e-9
PASS_REL_ERROR = 0.05

REQUIRED_FILES = [
    "run_simulation.py",
    "extract_kpi.py",
    "parking_areas.add.xml",
    "parking_lot.net.xml",
    "traffic.rou.xml",
    "your_config.sumocfg",
    "parking.edg.xml",
    "parking.nod.xml",
]


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


def parse_tripinfo_text(text: str) -> dict[str, float | int]:
    idx = text.find("<tripinfos")
    if idx < 0:
        raise RuntimeError("Cannot find <tripinfos> in tripinfo XML")
    root = ET.fromstring(text[idx:])

    cruising: list[float] = []
    stop_times: list[float] = []
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


def parse_tripinfo_path(path: Path) -> dict[str, float | int]:
    return parse_tripinfo_text(path.read_text(encoding="utf-8", errors="replace"))


def find_original_archive(repo_root: Path) -> Path:
    candidates = [
        repo_root / "00_archive" / "sumo_parking_ICCE_2026_original.zip",
        repo_root / "00_archive" / "sumo_parking.zip",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "Cannot find the original ICCE archive. Expected one of:\n  "
        + "\n  ".join(str(x) for x in candidates)
    )


def find_zip_member(zf: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in zf.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one archive member ending with {suffix!r}, got {matches}"
        )
    return matches[0]


def scenario_key(strategy: str, occupancy: int) -> str:
    return f"{strategy.lower()}_{occupancy}"


def load_archived_ground_truth(
    archive: Path,
) -> dict[tuple[str, int], dict[str, object]]:
    truth: dict[tuple[str, int], dict[str, object]] = {}

    with zipfile.ZipFile(archive, "r") as zf:
        summary_member = find_zip_member(zf, "sumo_results_summary.csv")
        summary_text = zf.read(summary_member).decode("utf-8-sig", errors="replace")
        summary_rows = list(csv.DictReader(io.StringIO(summary_text)))

        truncation: dict[tuple[str, int, int], bool] = {}
        for row in summary_rows:
            key = (
                row["Strategy"].strip().lower(),
                int(float(row["Occupancy"])),
                int(row["Seed"]),
            )
            truncation[key] = bool_value(row["Is_Truncated"])

        for scenario in SCENARIOS:
            name = scenario["name"]
            strategy = scenario["strategy"]
            occupancy = int(scenario["occupancy"])
            for seed in SEEDS:
                trip_member = find_zip_member(zf, f"tripinfo_{name}_{seed}.xml")
                trip_text = zf.read(trip_member).decode("utf-8", errors="replace")
                kpi = parse_tripinfo_text(trip_text)
                trunc_key = (strategy, occupancy, seed)
                if trunc_key not in truncation:
                    raise RuntimeError(
                        f"Missing archived truncation flag for {name}, seed {seed}"
                    )
                truth[(name, seed)] = {
                    "Scenario": name,
                    "Strategy": strategy,
                    "Occupancy": occupancy,
                    "Seed": seed,
                    "Is_Truncated": truncation[trunc_key],
                    **kpi,
                }

    return truth


def copy_workspace(snapshot: Path, work_dir: Path) -> None:
    work_dir.mkdir(parents=True, exist_ok=False)
    for name in REQUIRED_FILES:
        shutil.copy2(snapshot / name, work_dir / name)


def load_run_module(work_dir: Path, scenario_name: str, seed: int):
    module_path = work_dir / "run_simulation.py"
    safe_name = scenario_name.replace("-", "_")
    spec = importlib.util.spec_from_file_location(
        f"icce_run_{safe_name}_{seed}", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_observed_summary(work_dir: Path) -> bool:
    summary_path = work_dir / "sumo_results_summary.csv"
    if not summary_path.exists():
        raise RuntimeError(f"Missing observed summary: {summary_path}")
    with summary_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 1:
        raise RuntimeError(f"Expected one summary row, got {len(rows)}")
    return bool_value(rows[0]["Is_Truncated"])


def compare_run(
    scenario: dict[str, object],
    seed: int,
    expected: dict[str, object],
    observed: dict[str, object],
) -> dict[str, object]:
    fields = ["N_Trips", "Avg_Cruising_Time_s", "Total_CO2_kg"]
    errors = {
        name: rel_error(float(observed[name]), float(expected[name])) for name in fields
    }
    exact_numeric = all(
        abs(float(observed[name]) - float(expected[name])) <= NUMERIC_TOL
        for name in fields
    )
    exact_flag = bool(observed["Is_Truncated"]) == bool(expected["Is_Truncated"])
    pass_5pct = exact_flag and all(errors[name] <= PASS_REL_ERROR for name in fields)

    return {
        "Scenario": scenario["name"],
        "Strategy": scenario["strategy"],
        "Occupancy": int(scenario["occupancy"]),
        "Seed": seed,
        "Archived_Is_Truncated": bool(expected["Is_Truncated"]),
        "Observed_Is_Truncated": bool(observed["Is_Truncated"]),
        "Archived_N_Trips": int(expected["N_Trips"]),
        "Observed_N_Trips": int(observed["N_Trips"]),
        "N_Trips_RelError": errors["N_Trips"],
        "Archived_Avg_Cruising_Time_s": float(expected["Avg_Cruising_Time_s"]),
        "Observed_Avg_Cruising_Time_s": float(observed["Avg_Cruising_Time_s"]),
        "Cruising_RelError": errors["Avg_Cruising_Time_s"],
        "Archived_Total_CO2_kg": float(expected["Total_CO2_kg"]),
        "Observed_Total_CO2_kg": float(observed["Total_CO2_kg"]),
        "CO2_RelError": errors["Total_CO2_kg"],
        "Archived_Stop_gt_1s": int(expected["Trips_with_stopTime_gt_1s"]),
        "Observed_Stop_gt_1s": int(observed["Trips_with_stopTime_gt_1s"]),
        "Archived_Stop_le_1s": int(expected["Trips_with_stopTime_le_1s"]),
        "Observed_Stop_le_1s": int(observed["Trips_with_stopTime_le_1s"]),
        "Archived_Vaporized_traci": int(expected["Vaporized_traci"]),
        "Observed_Vaporized_traci": int(observed["Vaporized_traci"]),
        "Exact_Flag": exact_flag,
        "Exact_Core_Numeric": exact_numeric,
        "Pass_5pct": pass_5pct,
    }


def aggregate_scenario(
    rows: list[dict[str, object]], prefix: str
) -> dict[str, float]:
    n = len(rows)
    if n == 0:
        raise ValueError("No rows to aggregate")
    return {
        "Mean_N_Trips": sum(float(r[f"{prefix}_N_Trips"]) for r in rows) / n,
        "Mean_Avg_Cruising_Time_s": sum(
            float(r[f"{prefix}_Avg_Cruising_Time_s"]) for r in rows
        )
        / n,
        "Mean_Total_CO2_kg": sum(
            float(r[f"{prefix}_Total_CO2_kg"]) for r in rows
        )
        / n,
        "N_Truncated": sum(bool(r[f"{prefix}_Is_Truncated"]) for r in rows),
        "P_Truncated": sum(bool(r[f"{prefix}_Is_Truncated"]) for r in rows) / n,
    }


def archive_aggregate(
    archived: dict[tuple[str, int], dict[str, object]], scenario_name: str
) -> dict[str, float]:
    rows = []
    for seed in SEEDS:
        d = archived[(scenario_name, seed)]
        rows.append(
            {
                "Archived_Is_Truncated": d["Is_Truncated"],
                "Archived_N_Trips": d["N_Trips"],
                "Archived_Avg_Cruising_Time_s": d["Avg_Cruising_Time_s"],
                "Archived_Total_CO2_kg": d["Total_CO2_kg"],
            }
        )
    return aggregate_scenario(rows, "Archived")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_archived_targets(
    archived: dict[tuple[str, int], dict[str, object]],
) -> None:
    print("\nArchived Table-I targets reconstructed from original ZIP:")
    print("  Scenario      Trips       Cruising(s)      CO2(kg)     Truncated")
    for scenario in SCENARIOS:
        agg = archive_aggregate(archived, scenario["name"])
        print(
            f"  {scenario['name']:<12} "
            f"{agg['Mean_N_Trips']:>7.3f}   "
            f"{agg['Mean_Avg_Cruising_Time_s']:>13.6f}   "
            f"{agg['Mean_Total_CO2_kg']:>10.6f}   "
            f"{int(agg['N_Truncated'])}/10"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce all 40 ICCE-TW runs and reconstruct Table I."
    )
    parser.add_argument(
        "--precheck",
        action="store_true",
        help="Validate project paths/archive/environment without running SUMO.",
    )
    args = parser.parse_args()

    frozen_root = Path(__file__).resolve().parents[1]
    repo_root = frozen_root.parent
    snapshot = frozen_root / "snapshot" / "sumo_parking"

    missing = [name for name in REQUIRED_FILES if not (snapshot / name).exists()]
    if missing:
        print("ERROR: Frozen snapshot is not in the expected location:")
        print(f"  {snapshot}")
        print("Missing files:")
        for name in missing:
            print(f"  - {name}")
        return 2

    try:
        archive = find_original_archive(repo_root)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 3

    if not os.environ.get("SUMO_HOME"):
        print("ERROR: SUMO_HOME is not defined. Activate the ICCE environment first.")
        return 4

    sumo_exe = shutil.which("sumo")
    if not sumo_exe:
        print("ERROR: sumo is not available on PATH.")
        return 5

    try:
        archived = load_archived_ground_truth(archive)
    except Exception as exc:
        print(f"ERROR: Could not load archived ground truth: {exc}")
        return 6

    sumo_version = subprocess.run(
        [sumo_exe, "--version"], capture_output=True, text=True, check=False
    )

    print("=" * 86)
    print("ICCE-TW 2026 MILESTONE 0C - COMPLETE 40-RUN TABLE-I REPRODUCTION")
    print(f"Python:  {sys.executable}")
    print(f"SUMO:    {sumo_exe}")
    print(f"SUMO ver:{first_line(sumo_version.stdout)}")
    print(f"TraCI:   {traci.__file__}")
    print(f"Archive: {archive}")
    print(f"Snapshot:{snapshot}")
    print("Scenarios: " + ", ".join(s["name"] for s in SCENARIOS))
    print("Seeds:     " + ", ".join(str(x) for x in SEEDS))
    print("=" * 86)

    print_archived_targets(archived)

    if args.precheck:
        print("\nPRECHECK PASS - no simulation was run.")
        return 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = (
        frozen_root
        / "validation"
        / "runs"
        / f"ICCE_Table1_all_40_{timestamp}"
    )
    batch_dir.mkdir(parents=True, exist_ok=False)

    env_lines = [
        f"timestamp={timestamp}",
        f"python_version={sys.version.replace(chr(10), ' ')}",
        f"python_executable={sys.executable}",
        f"sumo_executable={sumo_exe}",
        f"sumo_version={first_line(sumo_version.stdout)}",
        f"SUMO_HOME={os.environ.get('SUMO_HOME')}",
        f"traci_file={traci.__file__}",
        f"archive={archive}",
        f"snapshot={snapshot}",
        "scenarios=" + ",".join(s["name"] for s in SCENARIOS),
        "seeds=" + ",".join(str(x) for x in SEEDS),
    ]
    (batch_dir / "environment_runtime.txt").write_text(
        "\n".join(env_lines) + "\n", encoding="utf-8"
    )

    validation_rows: list[dict[str, object]] = []
    total_runs = len(SCENARIOS) * len(SEEDS)
    run_idx = 0

    for scenario in SCENARIOS:
        scenario_name = scenario["name"]
        scenario_dir = batch_dir / scenario_name
        scenario_dir.mkdir(parents=True, exist_ok=False)

        for seed in SEEDS:
            run_idx += 1
            print("\n" + "-" * 86)
            print(
                f"[{run_idx}/{total_runs}] Reproducing {scenario_name} | Seed {seed}"
            )
            print("-" * 86)

            seed_dir = scenario_dir / f"seed_{seed}"
            work_dir = seed_dir / "workspace"
            seed_dir.mkdir(parents=True, exist_ok=False)
            copy_workspace(snapshot, work_dir)

            old_cwd = Path.cwd()
            try:
                os.chdir(work_dir)
                module = load_run_module(work_dir, scenario_name, seed)
                module.SCENARIOS = [dict(scenario)]
                module.SEEDS = [seed]
                module.run()

                kpi_proc = subprocess.run(
                    [sys.executable, "extract_kpi.py"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                (seed_dir / "original_extract_kpi_stdout.txt").write_text(
                    kpi_proc.stdout
                    + ("\nSTDERR:\n" + kpi_proc.stderr if kpi_proc.stderr else ""),
                    encoding="utf-8",
                )
            finally:
                os.chdir(old_cwd)

            tripinfo_path = (
                work_dir / "outputs" / f"tripinfo_{scenario_name}_{seed}.xml"
            )
            if not tripinfo_path.exists():
                print(f"ERROR: Missing output {tripinfo_path}")
                return 7

            observed_kpi = parse_tripinfo_path(tripinfo_path)
            observed = {
                "Is_Truncated": read_observed_summary(work_dir),
                **observed_kpi,
            }
            expected = archived[(scenario_name, seed)]
            comparison = compare_run(scenario, seed, expected, observed)
            validation_rows.append(comparison)

            detail_lines = [
                f"Scenario={scenario_name}",
                f"Strategy={scenario['strategy']}",
                f"Occupancy={scenario['occupancy']}",
                f"Seed={seed}",
                f"Is_Truncated={observed['Is_Truncated']}",
                f"N_Trips={observed['N_Trips']}",
                f"Avg_Cruising_Time_s={float(observed['Avg_Cruising_Time_s']):.12f}",
                f"Total_CO2_kg={float(observed['Total_CO2_kg']):.12f}",
                f"Trips_with_stopTime_gt_1s={observed['Trips_with_stopTime_gt_1s']}",
                f"Trips_with_stopTime_le_1s={observed['Trips_with_stopTime_le_1s']}",
                f"Vaporized_traci={observed['Vaporized_traci']}",
                f"RouteLength_zero={observed['RouteLength_zero']}",
            ]
            (seed_dir / "observed_kpi.txt").write_text(
                "\n".join(detail_lines) + "\n", encoding="utf-8"
            )

            print(
                "Archived -> "
                f"truncated={expected['Is_Truncated']}, "
                f"trips={expected['N_Trips']}, "
                f"cruise={float(expected['Avg_Cruising_Time_s']):.6f}s, "
                f"CO2={float(expected['Total_CO2_kg']):.6f}kg"
            )
            print(
                "Observed -> "
                f"truncated={observed['Is_Truncated']}, "
                f"trips={observed['N_Trips']}, "
                f"cruise={float(observed['Avg_Cruising_Time_s']):.6f}s, "
                f"CO2={float(observed['Total_CO2_kg']):.6f}kg"
            )
            exact_core = bool(comparison["Exact_Flag"]) and bool(
                comparison["Exact_Core_Numeric"]
            )
            print(
                "Run verdict: "
                + ("PASS" if bool(comparison["Pass_5pct"]) else "FAIL")
                + (" (exact core match)" if exact_core else "")
            )

    write_csv(batch_dir / "icce_40run_seed_validation.csv", validation_rows)

    table_rows: list[dict[str, object]] = []
    aggregate_check_rows: list[dict[str, object]] = []

    for scenario in SCENARIOS:
        name = scenario["name"]
        rows = [r for r in validation_rows if r["Scenario"] == name]
        archived_agg = aggregate_scenario(rows, "Archived")
        observed_agg = aggregate_scenario(rows, "Observed")

        row = {
            "Scenario": name,
            "Strategy": scenario["strategy"],
            "Occupancy_pct": int(scenario["occupancy"]),
            "Archived_Mean_N_Trips": archived_agg["Mean_N_Trips"],
            "Observed_Mean_N_Trips": observed_agg["Mean_N_Trips"],
            "Archived_Mean_Cruising_s": archived_agg["Mean_Avg_Cruising_Time_s"],
            "Observed_Mean_Cruising_s": observed_agg["Mean_Avg_Cruising_Time_s"],
            "Archived_Mean_Total_CO2_kg": archived_agg["Mean_Total_CO2_kg"],
            "Observed_Mean_Total_CO2_kg": observed_agg["Mean_Total_CO2_kg"],
            "Archived_Truncated_Runs": int(archived_agg["N_Truncated"]),
            "Observed_Truncated_Runs": int(observed_agg["N_Truncated"]),
            "Archived_P_Truncated": archived_agg["P_Truncated"],
            "Observed_P_Truncated": observed_agg["P_Truncated"],
        }
        table_rows.append(row)

        for metric in [
            "Mean_N_Trips",
            "Mean_Avg_Cruising_Time_s",
            "Mean_Total_CO2_kg",
            "N_Truncated",
            "P_Truncated",
        ]:
            expected = float(archived_agg[metric])
            actual = float(observed_agg[metric])
            err = rel_error(actual, expected)
            aggregate_check_rows.append(
                {
                    "Scenario": name,
                    "Metric": metric,
                    "Archived": expected,
                    "Observed": actual,
                    "Relative_Error": err,
                    "Exact": abs(actual - expected) <= NUMERIC_TOL,
                    "Pass_5pct": err <= PASS_REL_ERROR,
                }
            )

    write_csv(batch_dir / "icce_table1_reproduction.csv", table_rows)
    write_csv(batch_dir / "icce_aggregate_validation.csv", aggregate_check_rows)

    exact_run_count = sum(
        bool(r["Exact_Flag"]) and bool(r["Exact_Core_Numeric"])
        for r in validation_rows
    )
    pass_run_count = sum(bool(r["Pass_5pct"]) for r in validation_rows)
    all_run_pass = pass_run_count == total_runs
    all_aggregate_pass = all(bool(r["Pass_5pct"]) for r in aggregate_check_rows)
    milestone_pass = all_run_pass and all_aggregate_pass

    report_lines = [
        "ICCE-TW 2026 Milestone 0C - Complete 40-run Table-I reproduction",
        "",
        f"Exact core matches: {exact_run_count}/{total_runs}",
        f"Runs passing 5% criterion: {pass_run_count}/{total_runs}",
        "",
        "Scenario aggregates:",
    ]
    for row in table_rows:
        report_lines += [
            (
                f"{row['Scenario']}: "
                f"Archived trips={float(row['Archived_Mean_N_Trips']):.6f}, "
                f"Observed trips={float(row['Observed_Mean_N_Trips']):.6f}; "
                f"Archived cruise={float(row['Archived_Mean_Cruising_s']):.12f}, "
                f"Observed cruise={float(row['Observed_Mean_Cruising_s']):.12f}; "
                f"Archived CO2={float(row['Archived_Mean_Total_CO2_kg']):.6f}, "
                f"Observed CO2={float(row['Observed_Mean_Total_CO2_kg']):.6f}; "
                f"Archived trunc={int(row['Archived_Truncated_Runs'])}/10, "
                f"Observed trunc={int(row['Observed_Truncated_Runs'])}/10"
            )
        ]
    report_lines += [
        "",
        "Historical note:",
        "The archived Free_95 outputs contain 8/10 truncated runs (80%),",
        "although the ICCE-TW manuscript states 70%. This validation preserves",
        "the archived simulation as ground truth and does not alter it.",
        "",
        "Milestone 0C verdict: " + ("PASS" if milestone_pass else "FAIL / INVESTIGATE"),
    ]
    (batch_dir / "milestone_0C_report.txt").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )

    print("\n" + "=" * 86)
    print("MILESTONE 0C SUMMARY")
    print("=" * 86)
    print(f"Exact core matches:       {exact_run_count}/{total_runs}")
    print(f"Runs passing 5%:          {pass_run_count}/{total_runs}")
    print("\nICCE Table-I reproduction:")
    print(
        "  Scenario      Archived -> Observed "
        "[Trips | Cruising(s) | CO2(kg) | Truncated]"
    )
    for row in table_rows:
        print(
            f"  {row['Scenario']:<12} "
            f"{float(row['Archived_Mean_N_Trips']):.3f} -> {float(row['Observed_Mean_N_Trips']):.3f} | "
            f"{float(row['Archived_Mean_Cruising_s']):.6f} -> {float(row['Observed_Mean_Cruising_s']):.6f} | "
            f"{float(row['Archived_Mean_Total_CO2_kg']):.6f} -> {float(row['Observed_Mean_Total_CO2_kg']):.6f} | "
            f"{int(row['Archived_Truncated_Runs'])}/10 -> {int(row['Observed_Truncated_Runs'])}/10"
        )

    print("\n--- Milestone 0C verdict ---")
    print("PASS" if milestone_pass else "FAIL / INVESTIGATE")
    print(f"Validation files: {batch_dir}")

    return 0 if milestone_pass else 10


if __name__ == "__main__":
    raise SystemExit(main())
