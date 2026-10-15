#!/usr/bin/env python3
"""Milestone 1C-2 parking-duration generator."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

GENERATOR_VERSION = "1C2-v1"


class ParkingDurationError(ValueError):
    pass


@dataclass(frozen=True)
class ParkingDurationEvent:
    vehicle_id: str
    parking_duration_s: float


def derive_stream_seed(master_seed: int, stream_name: str) -> int:
    if not isinstance(master_seed, int):
        raise ParkingDurationError("master_seed must be an integer.")
    if not stream_name:
        raise ParkingDurationError("stream_name must be non-empty.")
    payload = f"{master_seed}:{stream_name}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def lognormal_parameters_from_mean_cv(
    mean_s: float,
    cv: float,
) -> tuple[float, float]:
    mean_s = float(mean_s)
    cv = float(cv)

    if mean_s <= 0:
        raise ParkingDurationError("mean_s must be > 0.")
    if cv < 0:
        raise ParkingDurationError("cv must be >= 0.")

    sigma2 = math.log1p(cv * cv)
    sigma = math.sqrt(sigma2)
    mu = math.log(mean_s) - 0.5 * sigma2
    return mu, sigma


def generate_lognormal_durations(
    vehicle_ids: Sequence[str],
    mean_s: float,
    cv: float,
    seed: int,
) -> list[ParkingDurationEvent]:
    mu, sigma = lognormal_parameters_from_mean_cv(mean_s, cv)

    if not isinstance(seed, int):
        raise ParkingDurationError("seed must be an integer.")

    ids = list(vehicle_ids)
    if len(ids) != len(set(ids)):
        raise ParkingDurationError("vehicle_ids must be unique.")
    if any(not v for v in ids):
        raise ParkingDurationError("vehicle_ids must be non-empty strings.")

    rng = random.Random(seed)
    events: list[ParkingDurationEvent] = []

    for vehicle_id in ids:
        duration = float(mean_s) if sigma == 0 else rng.lognormvariate(mu, sigma)
        if not math.isfinite(duration) or duration <= 0:
            raise ParkingDurationError(
                f"Generated invalid duration for {vehicle_id}: {duration}"
            )
        events.append(ParkingDurationEvent(vehicle_id, duration))

    return events


def duration_fingerprint(events: Iterable[ParkingDurationEvent]) -> str:
    h = hashlib.sha256()
    for event in events:
        h.update(
            f"{event.vehicle_id},{event.parking_duration_s:.12f}\n".encode("utf-8")
        )
    return h.hexdigest()


def load_vehicle_ids_from_arrival_csv(path: Path) -> list[str]:
    if not path.exists():
        raise ParkingDurationError(f"arrival CSV does not exist: {path}")

    ids: list[str] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "vehicle_id" not in (reader.fieldnames or []):
            raise ParkingDurationError(
                "arrival CSV must contain a vehicle_id column."
            )
        for row in reader:
            vehicle_id = (row.get("vehicle_id") or "").strip()
            if not vehicle_id:
                raise ParkingDurationError(
                    "arrival CSV contains an empty vehicle_id."
                )
            ids.append(vehicle_id)

    if len(ids) != len(set(ids)):
        raise ParkingDurationError(
            "arrival CSV contains duplicate vehicle IDs."
        )
    return ids


def write_duration_csv(
    path: Path,
    events: list[ParkingDurationEvent],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["vehicle_id", "parking_duration_s"],
        )
        writer.writeheader()
        for e in events:
            writer.writerow(
                {
                    "vehicle_id": e.vehicle_id,
                    "parking_duration_s": f"{e.parking_duration_s:.12f}",
                }
            )


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parent.parent
    default_output = (
        project_root / "validation" / "parking_duration_generator"
    )

    p = argparse.ArgumentParser(
        description="Generate reproducible lognormal parking durations."
    )
    p.add_argument("--arrival-csv", type=Path, required=True)
    p.add_argument("--mean-s", type=float, required=True)
    p.add_argument("--cv", type=float, required=True)
    p.add_argument("--master-seed", type=int, required=True)
    p.add_argument("--stream-name", default="parking_duration")
    p.add_argument("--output-dir", type=Path, default=default_output)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    vehicle_ids = load_vehicle_ids_from_arrival_csv(
        args.arrival_csv.resolve()
    )
    stream_seed = derive_stream_seed(
        args.master_seed,
        args.stream_name,
    )

    events = generate_lognormal_durations(
        vehicle_ids,
        args.mean_s,
        args.cv,
        stream_seed,
    )

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / (
        f"parking_durations_seed{args.master_seed}.csv"
    )
    manifest_path = output_dir / (
        f"parking_duration_manifest_seed{args.master_seed}.json"
    )

    write_duration_csv(csv_path, events)
    mu, sigma = lognormal_parameters_from_mean_cv(
        args.mean_s,
        args.cv,
    )
    values = [e.parking_duration_s for e in events]

    manifest = {
        "generator_version": GENERATOR_VERSION,
        "distribution": "lognormal",
        "parameterization": "arithmetic_mean_and_cv",
        "mean_s": float(args.mean_s),
        "cv": float(args.cv),
        "mu_log": mu,
        "sigma_log": sigma,
        "master_seed": args.master_seed,
        "stream_name": args.stream_name,
        "derived_stream_seed": stream_seed,
        "vehicle_count": len(events),
        "sample_mean_s": (sum(values) / len(values)) if values else None,
        "duration_sha256": duration_fingerprint(events),
        "source_arrival_csv": str(args.arrival_csv.resolve()),
        "truncation": None,
        "formal_parameterization": False,
        "note": (
            "Formal mean/CV values are not frozen yet. "
            "Do not use this as a formal Experiment 1 parameter set."
        ),
    }

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("=" * 76)
    print("T-ITS EXPERIMENT 1 - MILESTONE 1C-2 PARKING DURATION GENERATOR")
    print("=" * 76)
    print("Distribution       : lognormal")
    print(f"Mean parameter     : {args.mean_s:.6f} s")
    print(f"CV                 : {args.cv:.6f}")
    print(f"mu_log             : {mu:.12f}")
    print(f"sigma_log          : {sigma:.12f}")
    print(f"Master seed        : {args.master_seed}")
    print(f"Stream name        : {args.stream_name}")
    print(f"Derived seed       : {stream_seed}")
    print(f"Vehicles           : {len(events)}")
    if values:
        print(f"Sample mean        : {sum(values)/len(values):.6f} s")
    print(f"SHA-256            : {manifest['duration_sha256']}")
    print(f"CSV                : {csv_path}")
    print(f"Manifest           : {manifest_path}")
    print()
    print("NOTICE: mean/CV are not yet formal frozen parameters.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ParkingDurationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
