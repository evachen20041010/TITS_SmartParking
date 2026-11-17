# Milestone 1B-2 - SUMO Lifecycle Smoke Test / SUMO 車輛生命週期煙霧測試

## Objective / 目的

This deterministic smoke test connects the previously validated `VehicleLedger` to real SUMO/TraCI vehicle events. It checks event ordering and end-to-end state transitions on a small network.

**This is not a continuous free-search experiment.** Three vehicles are inserted at fixed demand epochs, assigned to the legal general parking area `PA_Z2_G`, and stopped for 15 seconds each.

本測試將已驗證的 `VehicleLedger` 接上真實 SUMO/TraCI 車輛事件，以小型情境檢查事件順序與完整狀態轉換。

**這不是持續式自由搜尋實驗。** 三台車依固定需求時刻進入系統，指定至合法一般停車區 `PA_Z2_G`，每台停放 15 秒。

## Expected lifecycle / 預期生命週期

Each vehicle follows（每台車依序經過）:

```text
outside -> entry_queue -> cruising -> parked -> departing -> completed
```

`cruising` in this smoke test is a lifecycle state, not proof of bounded-rational search-choice implementation.

本測試中的 `cruising` 是生命週期狀態，不代表已實作有限理性搜尋決策。

## Run command / 執行指令

From `02_Exp1_FreeSearch_v2/` with `sumo_py310` activated:

```cmd
python scripts\run_lifecycle_smoke.py
```

## Pass criteria / 通過條件

All conditions must hold（必須同時滿足）:

- All three vehicles reach `completed`.（三台車全部進入 `completed`）
- No vehicle enters `removed_error`.（不得有車輛進入 `removed_error`）
- Every recorded epoch has zero mass-balance error.（每個記錄時刻的質量平衡誤差必須為零）
- Each vehicle follows the complete expected state sequence.（每台車的狀態順序必須完全正確）

## Archived results / 封存結果

The archived `summary.json` records **PASS**, `completed=3/3`, `removed_error=0`, `max_abs_mass_balance_error=0`, and final simulation time `90 s`.

已封存的 `summary.json` 記錄 **PASS**、`completed=3/3`、`removed_error=0`、`max_abs_mass_balance_error=0`，模擬結束時間為 `90 秒`。

```text
validation/lifecycle_smoke/
├─ system_log.csv
├─ vehicle_events.csv
└─ summary.json
```

The entry state can be transitory within one SUMO step in this early smoke test. Milestone 1C-3 subsequently adds explicit release-epoch and entrance-state visibility checks.

在此早期 smoke test 中，入口狀態可能於同一個 SUMO step 內短暫出現。後續 M1C-3 已加入明確的釋放控制時刻與入口狀態可觀測性驗證。
