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

CASE = {"name": "Free_95", "occupancy": 95, "strategy": "free"}
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


def load_archived_ground_truth(archive: Path) -> dict[int, dict[str, object]]:
    truth: dict[int, dict[str, object]] = {}

    with zipfile.ZipFile(archive, "r") as zf:
        summary_member = find_zip_member(zf, "sumo_results_summary.csv")
        summary_text = zf.read(summary_member).decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(summary_text))
        truncated_by_seed: dict[int, bool] = {}
        for row in reader:
            if row["Strategy"].strip().lower() != "free":
                continue
            if int(float(row["Occupancy"])) != 95:
                continue
            seed = int(row["Seed"])
            truncated_by_seed[seed] = bool_value(row["Is_Truncated"])

        for seed in SEEDS:
            trip_member = find_zip_member(zf, f"tripinfo_Free_95_{seed}.xml")
            trip_text = zf.read(trip_member).decode("utf-8", errors="replace")
            kpi = parse_tripinfo_text(trip_text)
            if seed not in truncated_by_seed:
                raise RuntimeError(f"Missing archived truncation flag for seed {seed}")
            truth[seed] = {
                "Is_Truncated": truncated_by_seed[seed],
                **kpi,
            }

    return truth


def copy_workspace(snapshot: Path, work_dir: Path) -> None:
    work_dir.mkdir(parents=True, exist_ok=False)
    for name in REQUIRED_FILES:
        shutil.copy2(snapshot / name, work_dir / name)


def load_run_module(work_dir: Path, seed: int):
    module_path = work_dir / "run_simulation.py"
    spec = importlib.util.spec_from_file_location(
        f"icce_run_simulation_seed_{seed}", module_path
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


def compare_seed(
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


def aggregate(rows: list[dict[str, object]], prefix: str) -> dict[str, float]:
    n = len(rows)
    if n == 0:
        raise ValueError("No rows to aggregate")

    return {
        "Mean_N_Trips": sum(float(r[f"{prefix}_N_Trips"]) for r in rows) / n,
        "Mean_Avg_Cruising_Time_s": sum(
            float(r[f"{prefix}_Avg_Cruising_Time_s"]) for r in rows
        )
        / n,
        "Mean_Total_CO2_kg": sum(float(r[f"{prefix}_Total_CO2_kg"]) for r in rows)
        / n,
        "N_Truncated": sum(bool(r[f"{prefix}_Is_Truncated"]) for r in rows),
        "P_Truncated": sum(bool(r[f"{prefix}_Is_Truncated"]) for r in rows) / n,
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce ICCE-TW Free_95 for all 10 archived seeds."
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

    print("=" * 78)
    print("ICCE-TW 2026 MILESTONE 0B - FREE_95 / ALL 10 SEEDS")
    print(f"Python:  {sys.executable}")
    print(f"SUMO:    {sumo_exe}")
    print(f"SUMO ver:{first_line(sumo_version.stdout)}")
    print(f"TraCI:   {traci.__file__}")
    print(f"Archive: {archive}")
    print(f"Snapshot:{snapshot}")
    print("Seeds:   " + ", ".join(str(x) for x in SEEDS))
    print("=" * 78)

    archived_rows_for_agg = [
        {
            "Archived_Is_Truncated": archived[s]["Is_Truncated"],
            "Archived_N_Trips": archived[s]["N_Trips"],
            "Archived_Avg_Cruising_Time_s": archived[s]["Avg_Cruising_Time_s"],
            "Archived_Total_CO2_kg": archived[s]["Total_CO2_kg"],
        }
        for s in SEEDS
    ]
    archived_agg = aggregate(archived_rows_for_agg, "Archived")

    print("\nArchived aggregate target:")
    print(f"  Mean N_Trips              = {archived_agg['Mean_N_Trips']:.6f}")
    print(
        "  Mean Avg cruising time   = "
        f"{archived_agg['Mean_Avg_Cruising_Time_s']:.12f} s"
    )
    print(f"  Mean Total CO2            = {archived_agg['Mean_Total_CO2_kg']:.6f} kg")
    print(
        f"  Truncated runs            = {int(archived_agg['N_Truncated'])}/10 "
        f"({100 * archived_agg['P_Truncated']:.1f}%)"
    )

    if args.precheck:
        print("\nPRECHECK PASS - no simulation was run.")
        return 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = frozen_root / "validation" / "runs" / f"Free_95_all_seeds_{timestamp}"
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
        "case=Free_95",
        "seeds=" + ",".join(str(x) for x in SEEDS),
    ]
    (batch_dir / "environment_runtime.txt").write_text(
        "\n".join(env_lines) + "\n", encoding="utf-8"
    )

    validation_rows: list[dict[str, object]] = []

    for i, seed in enumerate(SEEDS, start=1):
        print("\n" + "-" * 78)
        print(f"[{i}/10] Reproducing Free_95 | Seed {seed}")
        print("-" * 78)

        seed_dir = batch_dir / f"seed_{seed}"
        work_dir = seed_dir / "workspace"
        seed_dir.mkdir(parents=True, exist_ok=False)
        copy_workspace(snapshot, work_dir)

        old_cwd = Path.cwd()
        try:
            os.chdir(work_dir)
            module = load_run_module(work_dir, seed)
            module.SCENARIOS = [CASE.copy()]
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

        tripinfo_path = work_dir / "outputs" / f"tripinfo_Free_95_{seed}.xml"
        if not tripinfo_path.exists():
            print(f"ERROR: Missing output {tripinfo_path}")
            return 7

        observed_kpi = parse_tripinfo_path(tripinfo_path)
        observed = {
            "Is_Truncated": read_observed_summary(work_dir),
            **observed_kpi,
        }

        comparison = compare_seed(seed, archived[seed], observed)
        validation_rows.append(comparison)

        detail_lines = [
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
            f"truncated={archived[seed]['Is_Truncated']}, "
            f"trips={archived[seed]['N_Trips']}, "
            f"cruise={float(archived[seed]['Avg_Cruising_Time_s']):.6f}s, "
            f"CO2={float(archived[seed]['Total_CO2_kg']):.6f}kg"
        )
        print(
            "Observed -> "
            f"truncated={observed['Is_Truncated']}, "
            f"trips={observed['N_Trips']}, "
            f"cruise={float(observed['Avg_Cruising_Time_s']):.6f}s, "
            f"CO2={float(observed['Total_CO2_kg']):.6f}kg"
        )
        print(
            "Seed verdict: " + ("PASS" if bool(comparison["Pass_5pct"]) else "FAIL")
            + (" (exact core match)" if bool(comparison["Exact_Flag"]) and bool(comparison["Exact_Core_Numeric"]) else "")
        )

    validation_csv = batch_dir / "free95_seed_validation.csv"
    write_csv(validation_csv, validation_rows)

    archived_agg = aggregate(validation_rows, "Archived")
    observed_agg = aggregate(validation_rows, "Observed")

    aggregate_rows: list[dict[str, object]] = []
    for metric in [
        "Mean_N_Trips",
        "Mean_Avg_Cruising_Time_s",
        "Mean_Total_CO2_kg",
        "N_Truncated",
        "P_Truncated",
    ]:
        expected = float(archived_agg[metric])
        observed = float(observed_agg[metric])
        err = rel_error(observed, expected)
        aggregate_rows.append(
            {
                "Metric": metric,
                "Archived": expected,
                "Observed": observed,
                "Relative_Error": err,
                "Pass_5pct": err <= PASS_REL_ERROR,
            }
        )

    write_csv(batch_dir / "aggregate_validation.csv", aggregate_rows)

    exact_seed_count = sum(
        bool(r["Exact_Flag"]) and bool(r["Exact_Core_Numeric"])
        for r in validation_rows
    )
    pass_seed_count = sum(bool(r["Pass_5pct"]) for r in validation_rows)
    all_seed_pass = pass_seed_count == len(SEEDS)
    aggregate_pass = all(bool(r["Pass_5pct"]) for r in aggregate_rows)
    milestone_pass = all_seed_pass and aggregate_pass

    report_lines = [
        "ICCE-TW 2026 Milestone 0B - Free_95 all seeds",
        "",
        f"Exact core matches: {exact_seed_count}/10",
        f"Seeds passing 5% criterion: {pass_seed_count}/10",
        "",
        "Archived aggregate:",
        f"Mean_N_Trips={archived_agg['Mean_N_Trips']:.12f}",
        f"Mean_Avg_Cruising_Time_s={archived_agg['Mean_Avg_Cruising_Time_s']:.12f}",
        f"Mean_Total_CO2_kg={archived_agg['Mean_Total_CO2_kg']:.12f}",
        f"N_Truncated={int(archived_agg['N_Truncated'])}",
        f"P_Truncated={archived_agg['P_Truncated']:.12f}",
        "",
        "Observed aggregate:",
        f"Mean_N_Trips={observed_agg['Mean_N_Trips']:.12f}",
        f"Mean_Avg_Cruising_Time_s={observed_agg['Mean_Avg_Cruising_Time_s']:.12f}",
        f"Mean_Total_CO2_kg={observed_agg['Mean_Total_CO2_kg']:.12f}",
        f"N_Truncated={int(observed_agg['N_Truncated'])}",
        f"P_Truncated={observed_agg['P_Truncated']:.12f}",
        "",
        "Milestone 0B verdict: " + ("PASS" if milestone_pass else "FAIL / INVESTIGATE"),
    ]
    (batch_dir / "milestone_0B_report.txt").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )

    print("\n" + "=" * 78)
    print("MILESTONE 0B SUMMARY")
    print("=" * 78)
    print(f"Exact core matches:       {exact_seed_count}/10")
    print(f"Seeds passing 5%:         {pass_seed_count}/10")
    print("\nArchived aggregate:")
    print(f"  Mean N_Trips            = {archived_agg['Mean_N_Trips']:.6f}")
    print(
        "  Mean Avg cruising      = "
        f"{archived_agg['Mean_Avg_Cruising_Time_s']:.12f} s"
    )
    print(f"  Mean Total CO2          = {archived_agg['Mean_Total_CO2_kg']:.6f} kg")
    print(
        f"  Truncated               = {int(archived_agg['N_Truncated'])}/10 "
        f"({100 * archived_agg['P_Truncated']:.1f}%)"
    )
    print("\nObserved aggregate:")
    print(f"  Mean N_Trips            = {observed_agg['Mean_N_Trips']:.6f}")
    print(
        "  Mean Avg cruising      = "
        f"{observed_agg['Mean_Avg_Cruising_Time_s']:.12f} s"
    )
    print(f"  Mean Total CO2          = {observed_agg['Mean_Total_CO2_kg']:.6f} kg")
    print(
        f"  Truncated               = {int(observed_agg['N_Truncated'])}/10 "
        f"({100 * observed_agg['P_Truncated']:.1f}%)"
    )
    print("\n--- Milestone 0B verdict ---")
    print("PASS" if milestone_pass else "FAIL / INVESTIGATE")
    print(f"Validation files: {batch_dir}")

    return 0 if milestone_pass else 10


if __name__ == "__main__":
    raise SystemExit(main())
