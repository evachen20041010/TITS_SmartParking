#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping


class LifecycleError(RuntimeError):
    pass


class VehicleState(str, Enum):
    OUTSIDE = "outside"
    ENTRY_QUEUE = "entry_queue"
    CRUISING = "cruising"
    PARKED = "parked"
    DEPARTING = "departing"
    COMPLETED = "completed"
    REMOVED_ERROR = "removed_error"


NORMAL_TRANSITIONS = {
    VehicleState.OUTSIDE: {VehicleState.ENTRY_QUEUE},
    VehicleState.ENTRY_QUEUE: {VehicleState.CRUISING},
    VehicleState.CRUISING: {VehicleState.PARKED},
    VehicleState.PARKED: {VehicleState.DEPARTING},
    VehicleState.DEPARTING: {VehicleState.COMPLETED},
    VehicleState.COMPLETED: set(),
    VehicleState.REMOVED_ERROR: set(),
}


@dataclass(frozen=True)
class TransitionEvent:
    vehicle_id: str
    sim_time: float
    from_state: VehicleState | None
    to_state: VehicleState
    reason: str = ""


@dataclass
class VehicleRecord:
    vehicle_id: str
    arrival_time: float
    state: VehicleState = VehicleState.OUTSIDE
    state_enter_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[TransitionEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.arrival_time = float(self.arrival_time)
        self.state_enter_time = float(self.arrival_time)
        if not self.history:
            self.history.append(
                TransitionEvent(
                    vehicle_id=self.vehicle_id,
                    sim_time=self.arrival_time,
                    from_state=None,
                    to_state=VehicleState.OUTSIDE,
                    reason="demand_arrival_released",
                )
            )


class VehicleLedger:
    def __init__(self) -> None:
        self._vehicles: Dict[str, VehicleRecord] = {}

    def __len__(self) -> int:
        return len(self._vehicles)

    def __contains__(self, vehicle_id: str) -> bool:
        return vehicle_id in self._vehicles

    def ids(self) -> Iterable[str]:
        return self._vehicles.keys()

    def get(self, vehicle_id: str) -> VehicleRecord:
        try:
            return self._vehicles[vehicle_id]
        except KeyError as exc:
            raise LifecycleError(f"Unknown vehicle_id: {vehicle_id}") from exc

    def register_arrival(self, vehicle_id: str, arrival_time: float,
                         metadata: Mapping[str, Any] | None = None) -> VehicleRecord:
        if vehicle_id in self._vehicles:
            raise LifecycleError(f"Duplicate vehicle_id: {vehicle_id}")
        if float(arrival_time) < 0:
            raise LifecycleError(f"{vehicle_id}: arrival_time must be >= 0")

        rec = VehicleRecord(
            vehicle_id=vehicle_id,
            arrival_time=float(arrival_time),
            metadata=dict(metadata or {}),
        )
        self._vehicles[vehicle_id] = rec
        self.assert_mass_balance()
        return rec

    def transition(self, vehicle_id: str, new_state: VehicleState | str,
                   sim_time: float, reason: str = "") -> VehicleRecord:
        rec = self.get(vehicle_id)
        new_state = VehicleState(new_state)
        sim_time = float(sim_time)

        if sim_time < rec.state_enter_time:
            raise LifecycleError(
                f"{vehicle_id}: non-monotonic transition time "
                f"{sim_time} < {rec.state_enter_time}"
            )

        if new_state not in NORMAL_TRANSITIONS[rec.state]:
            raise LifecycleError(
                f"{vehicle_id}: illegal transition "
                f"{rec.state.value} -> {new_state.value}"
            )

        old_state = rec.state
        rec.state = new_state
        rec.state_enter_time = sim_time
        rec.history.append(
            TransitionEvent(vehicle_id, sim_time, old_state, new_state, reason)
        )
        self.assert_mass_balance()
        return rec

    def mark_removed_error(self, vehicle_id: str, sim_time: float,
                           reason: str) -> VehicleRecord:
        rec = self.get(vehicle_id)
        sim_time = float(sim_time)

        if rec.state in {VehicleState.COMPLETED, VehicleState.REMOVED_ERROR}:
            raise LifecycleError(
                f"{vehicle_id}: cannot mark terminal state "
                f"{rec.state.value} as removed_error"
            )
        if sim_time < rec.state_enter_time:
            raise LifecycleError(
                f"{vehicle_id}: non-monotonic removal time "
                f"{sim_time} < {rec.state_enter_time}"
            )
        if not reason.strip():
            raise LifecycleError(
                f"{vehicle_id}: removed_error requires a non-empty reason"
            )

        old_state = rec.state
        rec.state = VehicleState.REMOVED_ERROR
        rec.state_enter_time = sim_time
        rec.history.append(
            TransitionEvent(
                vehicle_id, sim_time, old_state,
                VehicleState.REMOVED_ERROR, reason
            )
        )
        self.assert_mass_balance()
        return rec

    def counts(self) -> Dict[str, int]:
        out = {state.value: 0 for state in VehicleState}
        for rec in self._vehicles.values():
            out[rec.state.value] += 1
        return out

    def generated_to_date(self) -> int:
        return len(self._vehicles)

    def active_in_system(self) -> int:
        c = self.counts()
        return (
            c[VehicleState.ENTRY_QUEUE.value]
            + c[VehicleState.CRUISING.value]
            + c[VehicleState.PARKED.value]
            + c[VehicleState.DEPARTING.value]
        )

    def assert_mass_balance(self) -> None:
        c = self.counts()
        lhs = self.generated_to_date()
        rhs = sum(c.values())
        if lhs != rhs:
            raise LifecycleError(
                f"Mass balance failed: generated={lhs}, "
                f"accounted={rhs}, counts={c}"
            )

    def assert_formal_run_health(self) -> None:
        self.assert_mass_balance()
        c = self.counts()
        if c[VehicleState.REMOVED_ERROR.value] != 0:
            raise LifecycleError(
                "Formal-run QC failed: "
                f"removed_error={c[VehicleState.REMOVED_ERROR.value]}"
            )

    def snapshot(self, sim_time: float) -> Dict[str, int | float]:
        self.assert_mass_balance()
        c = self.counts()
        accounted = sum(c.values())
        return {
            "time": float(sim_time),
            "generated_to_date": self.generated_to_date(),
            **{f"n_{k}": v for k, v in c.items()},
            "n_active_in_system": self.active_in_system(),
            "mass_balance_accounted": accounted,
            "mass_balance_error": self.generated_to_date() - accounted,
        }
