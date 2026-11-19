#!/usr/bin/env python3
"""M1D-0D proposed *physical* entrance queue measurement contract.

This is a pure-Python, synthetic-data-tested measurement prototype, not a
TraCI logger and not a validated Event A detector. A dedicated E_IN lane and
calibration/approval are required before formal use.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


class QueueContractError(ValueError):
    """Invalid physical queue measurement input."""


@dataclass(frozen=True)
class LaneVehicle:
    vehicle_id: str
    front_position_m: float  # SUMO lane-position convention: downstream front
    length_m: float
    speed_mps: float


@dataclass(frozen=True)
class QueueObservation:
    contiguous_queued_vehicles: int
    physical_queue_length_m: float
    storage_coverage: float
    at_90_percent: bool


def measure_contiguous_entry_queue(
    vehicles: list[LaneVehicle],
    *,
    lane_length_m: float,
    usable_storage_m: float,
    lead_distance_tolerance_m: float,
    max_intervehicle_gap_m: float,
    halt_speed_mps: float = 0.1,
    coverage_threshold: float = 0.90,
) -> QueueObservation:
    """Measure a stopped queue connected to the lane's downstream boundary.

    A halted vehicle far upstream is not an entrance-spillback queue by itself.
    This distinguishes connected queue length from raw lane halt count.

    The geometric / gap parameters MUST be calibrated and frozen before any
    official Event A data collection. Ratios are clamped to [0, 1].
    """
    vals = (
        lane_length_m, usable_storage_m, lead_distance_tolerance_m,
        max_intervehicle_gap_m, halt_speed_mps, coverage_threshold,
    )
    if not all(math.isfinite(float(v)) for v in vals):
        raise QueueContractError("All measurement parameters must be finite.")
    if lane_length_m <= 0 or not 0 < usable_storage_m <= lane_length_m:
        raise QueueContractError("Invalid lane length or usable storage.")
    if lead_distance_tolerance_m < 0 or max_intervehicle_gap_m < 0:
        raise QueueContractError("Distance tolerances must be nonnegative.")
    if halt_speed_mps <= 0 or not 0 < coverage_threshold <= 1:
        raise QueueContractError("Invalid speed or coverage threshold.")

    ids: set[str] = set()
    for v in vehicles:
        if not v.vehicle_id or v.vehicle_id in ids:
            raise QueueContractError("Vehicle IDs must be unique and nonempty.")
        ids.add(v.vehicle_id)
        if not all(math.isfinite(float(x)) for x in (v.front_position_m, v.length_m, v.speed_mps)):
            raise QueueContractError("Vehicle fields must be finite.")
        if not (0 <= v.front_position_m <= lane_length_m) or v.length_m <= 0 or v.speed_mps < 0:
            raise QueueContractError("Invalid vehicle position, length or speed.")
        if v.front_position_m - v.length_m < -1e-6:
            raise QueueContractError("Vehicle rear extends beyond lane start.")

    ordered = sorted(vehicles, key=lambda v: v.front_position_m, reverse=True)
    if not ordered:
        return QueueObservation(0, 0.0, 0.0, False)
    lead = ordered[0]
    if (
        lead.speed_mps >= halt_speed_mps
        or lane_length_m - lead.front_position_m > lead_distance_tolerance_m
    ):
        return QueueObservation(0, 0.0, 0.0, False)

    queue = [lead]
    previous = lead
    for current in ordered[1:]:
        if current.speed_mps >= halt_speed_mps:
            break
        gap_m = (previous.front_position_m - previous.length_m) - current.front_position_m
        if gap_m < -1e-6:
            raise QueueContractError("Overlapping vehicle geometry in a lane.")
        if gap_m > max_intervehicle_gap_m:
            break
        queue.append(current)
        previous = current

    upstream_rear_m = max(0.0, previous.front_position_m - previous.length_m)
    queue_m = lane_length_m - upstream_rear_m
    fraction = min(1.0, max(0.0, queue_m / usable_storage_m))
    return QueueObservation(
        contiguous_queued_vehicles=len(queue),
        physical_queue_length_m=queue_m,
        storage_coverage=fraction,
        at_90_percent=fraction >= coverage_threshold,
    )


class SustainedSpillbackWindow:
    """Track the SOP's 90%-for-60s condition at regular control epochs.

    This is NOT a complete C1/C2 detector. Missing observation steps reset
    the continuous-time claim rather than silently interpolating a queue.
    """

    def __init__(
        self,
        *,
        coverage_threshold: float = 0.90,
        duration_s: float = 60.0,
        max_sample_gap_s: float = 1.01,
    ) -> None:
        if not (0 < coverage_threshold <= 1):
            raise QueueContractError("Invalid coverage threshold.")
        if duration_s <= 0 or max_sample_gap_s <= 0:
            raise QueueContractError("Invalid window duration or sample gap.")
        self.coverage_threshold = coverage_threshold
        self.duration_s = duration_s
        self.max_sample_gap_s = max_sample_gap_s
        self.last_time_s: float | None = None
        self.sustained_since_s: float | None = None

    def observe(self, time_s: float, coverage: float) -> bool:
        if not math.isfinite(time_s) or not math.isfinite(coverage):
            raise QueueContractError("Samples must be finite.")
        if time_s < 0 or not 0 <= coverage <= 1:
            raise QueueContractError("Invalid sample time or coverage.")
        if self.last_time_s is not None and time_s <= self.last_time_s:
            raise QueueContractError("Observation timestamps must increase.")
        gap_is_missing = (
            self.last_time_s is not None
            and time_s - self.last_time_s > self.max_sample_gap_s
        )
        self.last_time_s = time_s
        if coverage < self.coverage_threshold:
            self.sustained_since_s = None
            return False
        if gap_is_missing or self.sustained_since_s is None:
            self.sustained_since_s = time_s
        return time_s - self.sustained_since_s >= self.duration_s - 1e-9
