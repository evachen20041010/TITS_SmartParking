# Milestone 1B-2 — SUMO Lifecycle Smoke Test / SUMO 車輛生命週期煙霧測試

This smoke test connects the validated `VehicleLedger` to real SUMO vehicle events. It is intentionally small and deterministic.

本測試將已通過單元測試的 `VehicleLedger` 第一次接上真實 SUMO 車輛事件。測試刻意保持小型且具決定性，以隔離生命週期整合問題。

## Purpose / 目的

The test verifies the following real-SUMO lifecycle（驗證下列真實 SUMO 生命週期）:

```text
outside
→ entry_queue
→ cruising
→ parked
→ departing
→ completed
```

Three vehicles are released at fixed times and are assigned a fixed legal
parking area. This is **not** a free-search experiment.

三台車會在固定時間進入系統，並被指定至固定且合法的停車區。
本測試**不是**自由搜尋實驗。

## Pass Criteria / 通過條件

- All 3 vehicles reach `completed`.（三台車全部到達）
- `removed_error = 0`.
- `mass_balance_error = 0` at every recorded step.（每一個記錄步驟皆須滿足）
- Every vehicle follows the exact expected lifecycle sequence.（每台車都必須依照完整預期生命週期順序轉移）

## Output / 輸出

The script writes:

```text
validation/lifecycle_smoke/system_log.csv
validation/lifecycle_smoke/vehicle_events.csv
validation/lifecycle_smoke/summary.json
```
