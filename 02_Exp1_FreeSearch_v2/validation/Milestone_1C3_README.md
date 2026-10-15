# Milestone 1C-3 — Dynamic-Demand SUMO Smoke Test / 動態需求 SUMO 煙霧測試

This milestone connects the independently validated Poisson arrival generator, lognormal parking-duration generator, `VehicleLedger`, and real SUMO traffic simulation.

本階段將已獨立驗證的 Poisson 車輛到達生成器、對數常態停車時間生成器、`VehicleLedger` 及真實 SUMO 交通模擬整合在一起。

## Scope / 範圍

**This is a smoke test, not a formal Experiment 1 result.** It uses a fixed legal parking target (`PA_Z2_G`) solely to isolate integration issues. It does **not** implement continuous free search.
Smoke-only parameters: Poisson arrival rate 0.04 vehicles/s, demand window 0–120 s, lognormal parking duration mean 20 s and CV 0.25, and master seed 10.
These numeric values are **NOT** frozen research parameters and must not be used for the `rho` sweep.

**這是煙霧測試，不是 Experiment 1 正式實驗結果。** 此處固定指定合法停車區 `PA_Z2_G`，僅用來檢查模組整合，**尚未實作持續式自由搜尋**。
僅供 smoke test 的參數：Poisson 到達率 0.04 輛/秒、到達時間 0–120 秒、停車時間對數常態分布平均 20 秒及 CV 0.25、master seed 10。
上述數值**不是**正式研究凍結參數，不得直接用於 `rho` sweep。

## Installation / 安裝位置

Place the script and documentation into the current repository:

```text
TITS_SmartParking/
└─ 02_Exp1_FreeSearch_v2/
   ├─ scripts/
   │  └─ run_dynamic_demand_smoke.py
   └─ validation/
      └─ Milestone_1C3_README.md
```

## Precheck / 執行前檢查

From `sumo_py310` and the Experiment 1 folder:

```cmd
conda activate sumo_py310
cd /d C:\TITS_SmartParking\02_Exp1_FreeSearch_v2
python scripts\run_dynamic_demand_smoke.py --precheck
```

This checks that network inputs are present, `C_eff=170` is validated, `PA_Z2_G` is a legal general parking area, and both RNG streams produce reproducible schedules. It does not start SUMO or write result logs.

此步驟檢查網路檔案、已驗證的 `C_eff=170`、`PA_Z2_G` 一般合法車位，以及兩組獨立亂數流。這一步不啟動 SUMO，也不輸出正式執行紀錄。

## Smoke simulation / 煙霧模擬

After precheck passes, run:

```cmd
python scripts\run_dynamic_demand_smoke.py
```

For per-step console output, add `--verbose`.

## Time and lifecycle semantics / 時間與生命週期語意

For each continuous scheduled arrival time `a_i`, the simulator registers the vehicle at the first control epoch `r_i >= a_i`, then attempts SUMO insertion on a subsequent simulation step. The system snapshot at `r_i` already counts the vehicle as `outside`.
At 1 s step length, the release delay must satisfy `0 <= r_i - a_i <= 1 s`. Every vehicle must remain in `outside` and `entry_queue` for at least one logged control epoch before transitioning onward.
Normal states:

對每筆連續時間到達事件 `a_i`，模擬器在第一個滿足 `r_i >= a_i` 的控制時刻註冊車輛，後續 simulation step 才嘗試插入 SUMO。在 `r_i` 的系統快照中，車輛已被計入 `outside`。
當 step length 為 1 秒，釋放延遲需滿足 `0 <= r_i - a_i <= 1 s`。每台車的 `outside` 與 `entry_queue` 都必須至少在一個記錄的控制時刻中可觀察到。
正常狀態依序為：

```text
outside -> entry_queue -> cruising -> parked -> departing -> completed
```

## Pass criteria / 通過條件

All scheduled arrivals must be released, all released vehicles must reach `completed`, there must be no unexplained removals, and mass balance must hold at every recorded epoch.
The following must all be true:

所有預定到達事件都必須釋放，所有車輛必須到達 `completed`，不得發生非預期移除，且每個記錄時刻的質量平衡必須成立。
以下條件必須全部成立：

- Released / Generated = N/N.（釋放數量與生成數量相等）
- Completed / Generated = N/N.（所有車輛正常完成）
- `removed_error = 0`.（沒有非預期移除）
- `max |mass_balance_error| = 0`.（每個時刻的帳務差異為零）
- Release-delay rule = PASS.（到達事件離散化符合規範）
- `outside` and `entry_queue` visibility = PASS.（兩個狀態都至少可觀察一個控制時刻）
- Every lifecycle sequence = PASS.（每台車的狀態順序正確）

## Outputs / 輸出檔案

The script writes the following files under `validation/dynamic_demand_smoke/`:

```text
arrival_schedule.csv
parking_durations.csv
demand_release_audit.csv
vehicle_events.csv
system_log.csv
summary.json
```

The two SHA-256 values in `summary.json` identify the exact arrival schedule and parking-duration draws. These output files may be committed as **non-formal validation evidence**.

`summary.json` 中的兩組 SHA-256 分別對應精確的到達排程與停車時間抽樣。這些輸出可以作為**非正式的驗證證據**提交至 Git。

## Important limitation / 重要限制

Passing this smoke test confirms integration only. It does not establish the validity of the parking search behavioral model, entry spillback definition, critical load, or gridlock detector.

通過本 smoke test 僅代表模組整合運作正常，**不等於**已驗證停車搜尋行為模型、入口回堵定義、臨界負載或 gridlock detector。
