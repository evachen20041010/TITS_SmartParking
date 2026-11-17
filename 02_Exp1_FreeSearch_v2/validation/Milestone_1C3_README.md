# Milestone 1C-3 - Dynamic-Demand SUMO Integration Smoke Test / 動態需求 SUMO 整合煙霧測試

## Objective and limits / 目的與限制

This milestone connects the independently unit-tested homogeneous Poisson arrivals, lognormal parking durations, `VehicleLedger`, and real SUMO/TraCI events.

**It is non-formal engineering validation.** The vehicles use fixed legal parking area `PA_Z2_G`. This test **does not implement or establish** bounded-rational continuous free search, C1 search-induced gridlock, C2 capacity-induced blockage, or critical offered load.

本階段串接已通過單元測試的 homogeneous Poisson 到達、lognormal 停車時間、`VehicleLedger` 與真實 SUMO/TraCI 事件。

**這是非正式工程驗證。** 車輛使用固定合法停車區 `PA_Z2_G`。本測試**尚未實作，也不能證明**有限理性持續式自由搜尋、C1 搜尋誘發失穩、C2 容量不足阻塞或臨界需求負載。

## Smoke-only settings / 僅供煙霧測試的設定

These values are fixtures for integration testing and must **not** be reused as formal research parameters:

下列數值只用於整合測試，**不得**直接當作正式研究參數：

```text
master_seed        = 10
arrival_rate       = 0.04 vehicles/s
demand_window      = [0, 120) s
parking_mean       = 20 s
parking_CV         = 0.25
control_step       = 1.0 s
fixed_parking_area = PA_Z2_G
```

The generator derives distinct arrival and parking-duration RNG seeds from the common master seed and records SHA-256 fingerprints for both realizations.

生成器由相同 master seed 衍生不同的 arrival 與 parking-duration RNG seeds，並為兩份抽樣結果記錄 SHA-256 指紋。

## Running the precheck / 執行前置檢查

In Windows CMD with the validated environment:

```cmd
conda activate sumo_py310
cd /d C:\TITS_SmartParking\02_Exp1_FreeSearch_v2
python scripts\run_dynamic_demand_smoke.py --precheck
```

Precheck validates input files, `C_eff=170`, the legal parking target, and the exogenous schedules. It does **not** launch SUMO, so a successful precheck is not an integration PASS.

Precheck 檢查輸入檔案、`C_eff=170`、合法停車目標及外生抽樣排程；它**不會**啟動 SUMO，因此通過 precheck 不等於已完成整合驗證。

## Running SUMO / 執行 SUMO

After a successful precheck:

```cmd
python scripts\run_dynamic_demand_smoke.py
```

For per-step console output, add `--verbose`.

如需在終端顯示每個 simulation step 的資訊，可加入 `--verbose`。

## Arrival and state timing / 到達與狀態時間定義

For a scheduled continuous-time arrival `a_i`, the simulator releases the demand event at the first control epoch `r_i >= a_i`. At a one-second control step, `0 <= r_i-a_i <= 1 s`; the released vehicle is visible as `outside` in that epoch's snapshot.

A successfully inserted vehicle enters `entry_queue`, stays observable for at least one control epoch, and later becomes `cruising` after the entrance-region rule is satisfied. The full expected sequence is:

對預定連續時間到達事件 `a_i`，模擬器在第一個滿足 `r_i >= a_i` 的控制時刻 `r_i` 釋放需求。採一秒控制步長時，`0 <= r_i-a_i <= 1 秒`；當下的系統快照即須將該車計入 `outside`。

成功插入的車輛進入 `entry_queue`，至少在一個控制時刻可觀察，符合入口空間規則後才進入 `cruising`。完整預期狀態順序為：

```text
outside -> entry_queue -> cruising -> parked -> departing -> completed
```

## Pass criteria / 通過條件

All generated events must be released; every vehicle must complete the full lifecycle; no vehicle may enter `removed_error`; mass balance must remain exact; release delays must respect the control step; both `outside` and `entry_queue` must be observable.

所有生成的事件都必須釋放；每台車都須完成完整生命週期；不得出現 `removed_error`；質量平衡須始終成立；釋放延遲須符合控制步長；`outside` 與 `entry_queue` 必須可觀察。

## Archived result / 已封存結果

The project-provided `validation/dynamic_demand_smoke/summary.json` reports **PASS** for the master-seed-10 smoke test:

專案中的 `validation/dynamic_demand_smoke/summary.json` 記錄 master-seed-10 煙霧測試 **PASS**：

| Metric / 指標 | Recorded value / 記錄值 |
| --- | ---: |
| Generated arrivals / 生成到達事件 | **7** |
| Released arrivals / 釋放事件 | **7/7** |
| Completed vehicles / 正常完成車輛 | **7/7** |
| `removed_error` | **0** |
| Maximum absolute mass-balance error / 最大帳務絕對誤差 | **0** |
| Maximum release delay / 最大到達釋放延遲 | **0.9312152104140328 s** |
| Release-delay rule / 釋放延遲規則 | **PASS** |
| `outside` and `entry_queue` visibility / 狀態可觀測性 | **PASS** |
| Lifecycle sequences / 生命週期順序 | **7/7 PASS** |
| Final simulated time / 結束模擬時間 | **162 s** |

The arrival schedule and parking-duration fingerprints are stored with the run so subsequent verification can identify the same exogenous realizations. This is **one smoke-test seed**, not a stochastic load-sweep result.

本次使用的 arrival schedule 與 parking-duration 指紋已隨 run 保存，可供後續確認相同外生抽樣結果。這只是**單一煙霧測試 seed**，不是隨機負載掃描結果。

## Validation artifacts / 驗證輸出檔案

```text
validation/dynamic_demand_smoke/
├─ arrival_schedule.csv
├─ parking_durations.csv
├─ demand_release_audit.csv
├─ vehicle_events.csv
├─ system_log.csv
└─ summary.json
```

`demand_release_audit.csv` records continuous scheduled arrival times and their discrete release epochs; `system_log.csv` records per-epoch state counts and mass balance; `vehicle_events.csv` records lifecycle transitions.

`demand_release_audit.csv` 記錄連續預定到達時間與離散釋放控制時刻；`system_log.csv` 記錄各時刻狀態數與質量平衡；`vehicle_events.csv` 記錄生命週期轉移事件。

## Relationship to next milestones / 與後續里程碑的關係

M1C is complete within its engineering validation scope. M1D must implement and separately validate bounded-rational continuous free-search behavior; M1E must implement the SOP-defined C1/C2 detectors, eligible-vacancy checks, and related instrumentation before formal load sweeps.

M1C 的工程整合驗證範圍已完成。M1D 必須另外實作並驗證有限理性持續式自由搜尋；M1E 必須依 SOP 實作 C1/C2 偵測器、合法空位檢查與相關資料紀錄，才能開始正式負載掃描。
