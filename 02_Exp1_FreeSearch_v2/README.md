# Experiment 1 v2 - Free-Search Instability and Critical-Load Characterization / 自由搜尋失穩與臨界負載特性分析

## Purpose and scope / 目的與範圍

Experiment 1 is the go/no-go study for the T-ITS research program. It tests whether decentralized, bounded-rational parking search exhibits a reproducible transition from stable operation to a search-induced unstable regime as offered parking load increases. **No proposed controller is part of Experiment 1.**

The authoritative specification is [`../03_docs/20260920_IEEE_Trans_ITS_Experiment1_v2_SOP.pdf`](../03_docs/20260920_IEEE_Trans_ITS_Experiment1_v2_SOP.pdf). This README describes what has actually been built and validated, alongside the work that remains.

Experiment 1 是 T-ITS 研究計畫的 go/no-go 實驗，目標是檢驗去中心化、有限理性的停車搜尋行為，是否會隨 offered parking load 增加，從穩定運作轉變為可重現的搜尋誘發失穩狀態。**Experiment 1 不包含 proposed controller。**

正式方法依據為 [`../03_docs/20260920_IEEE_Trans_ITS_Experiment1_v2_SOP.pdf`](../03_docs/20260920_IEEE_Trans_ITS_Experiment1_v2_SOP.pdf)。本 README 同時說明目前**實際完成的程式與驗證**，以及尚待執行的研究工作。

## Scientific questions / 研究問題

The study asks whether instability is reproducible, at what offered load search-induced gridlock becomes probable within a fixed measurement horizon, which microscopic precursors appear first, and whether these observations can be distinguished from capacity exhaustion or exogenous overload.

The primary event is **C1: search-induced gridlock**. **C2: capacity-induced blockage** is analyzed separately. The primary critical-load quantity is `rho_50(T_m)`, with `T_m = 120 min` in the main analysis and `60/240 min` horizon sensitivity.

A simulator run that stops at a time limit or runs out of eligible spaces is **not** automatically a C1 event. The C1 detector, threshold sensitivity, and censored-search analysis have **not yet been implemented**.

本研究關注：失穩是否可重現、固定觀測時間內搜尋誘發 gridlock 在何種需求負載下變得顯著、哪些微觀前兆最先出現，以及如何區分真正的搜尋失穩、合法車位耗盡與外生需求過載。

主要事件為 **C1：search-induced gridlock（搜尋誘發失穩）**；**C2：capacity-induced blockage（容量不足造成的阻塞）** 必須另行分析。主要臨界負載指標為 `rho_50(T_m)`；主分析使用 `T_m = 120 min`，另做 `60/240 min` 觀測時間敏感度分析。

模擬因時間上限結束，或合法空位已耗盡，**不能**自動視為 C1。C1 偵測器、門檻敏感度及搜尋時間設限分析**目前尚未實作**。

## Historical baseline boundary / 歷史基準與開發邊界

The original ICCE-TW 2026 experiment was reproduced exactly for **40/40 runs** and remains frozen under [`../01_ICCE_2026_Frozen/`](../01_ICCE_2026_Frozen/README_ICCE.md). Experiment 1 retains the canonical physical geometry but does **not** modify or directly inherit the old controller.

The historical `Free_95` archive has **8/10 truncated runs**, not 7/10. This observed truncation is not sufficient evidence of search-induced gridlock; the discrepancy with the earlier manuscript wording is documented in the frozen baseline README.

原始 ICCE-TW 2026 實驗已完成 **40/40 runs 精確重現**，並凍結於 [`../01_ICCE_2026_Frozen/`](../01_ICCE_2026_Frozen/README_ICCE.md)。Experiment 1 保留 canonical 物理路網，但**不修改、不直接沿用**早期控制器。

歷史 `Free_95` 封存輸出有 **8/10 次截斷**，不是 7/10。這種截斷不足以單獨證明搜尋誘發 gridlock；與早期稿件文字的差異已記錄在凍結基準 README 中。

## Canonical network and legal capacity / 標準路網與合法容量

The canonical network is under [`network/canonical/`](network/canonical/README.md), with three non-internal edges, three parking zones, and seven SUMO parking areas.

標準路網位於 [`network/canonical/`](network/canonical/README.md)，包含三條非內部道路邊、三個停車分區與七個 SUMO 停車區域。

| Space type / 車位類別 | Capacity / 車位數 |
| --- | ---: |
| General / 一般 | 170 |
| Family / 親子 | 20 |
| Disabled / 身障 | 10 |
| **Total / 總計** | **200** |

Experiment 1-Core studies **general vehicles only** under strict legal access. General drivers may use general spaces only, giving `C_eff=170` rather than the physical total `C_total=200`.

Experiment 1-Core **僅研究一般車輛**，並遵守嚴格合法車位限制。一般駕駛只能使用一般車位，因此有效容量為 `C_eff=170`，不是物理總容量 `C_total=200`。

## Demand and duration models / 到達需求與停車時間模型

The homogeneous Poisson arrival process and the positive lognormal parking-duration sampler have both passed standalone unit tests. The offered-load definition is:

Homogeneous Poisson 到達過程與正值 lognormal 停車時間生成器都已通過獨立單元測試。需求負載定義為：

```text
rho    = lambda * E[T_park] / C_eff
lambda = rho * C_eff / E[T_park]
C_eff  = 170 (general-only Experiment 1-Core)
```

`rho` is **offered parking load**, not measured instantaneous occupancy. The demand generator preserves continuous-valued arrival times; the 1C-3 integration maps each scheduled arrival to the first subsequent discrete control epoch.

The formal parking-duration mean, coefficient of variation, data source, truncation policy, and driver-behavior distributions are **not frozen**. Unit-test values such as `1800 s / CV=0.5` and smoke values `20 s / CV=0.25` must not be used as unreviewed paper parameters.

`rho` 是**停車需求負載**，不是實測瞬間占用率。需求生成器保留連續到達時間；1C-3 整合測試再把每筆預定到達映射到第一個符合條件的離散控制時刻。

正式停車時間平均值、變異係數、資料來源、截尾政策與駕駛行為分布都**尚未凍結**。單元測試中的 `1800 s / CV=0.5`，以及煙霧測試中的 `20 s / CV=0.25`，不得在未審查下直接當成論文實驗參數。

## Vehicle lifecycle / 車輛生命週期

Every released demand event is tracked by `VehicleLedger`, with exactly one primary state per vehicle and a separate terminal error state:

每筆已釋放的需求事件由 `VehicleLedger` 追蹤，每台車任何時刻只有一個主要狀態，並有獨立的異常終止狀態：

```text
outside -> entry_queue -> cruising -> parked -> departing -> completed
removed_error (unexpected termination / 非預期終止)
```

Mass balance must hold at every recorded simulation epoch（每個記錄的模擬控制時刻都必須滿足）:

```text
N_generated_to_date = N_outside + N_entry_queue + N_cruising
                    + N_parked + N_departing + N_completed + N_removed_error
mass_balance_error = 0
```

An unexpected disappearance is recorded as `removed_error` to preserve accounting, but **any formal run with `removed_error > 0` is invalid**.

車輛非預期消失時必須記錄為 `removed_error` 以維持帳務一致，但**任何正式 run 只要 `removed_error > 0` 即屬無效**。

## Validated milestones as of 2026-10-15 / 截至 2026-10-15 的驗證進度

The status below comes from the source tree, unit tests, and archived validation summaries. A PASS applies only to the stated test scope.

下列結果以原始程式、單元測試與封存的驗證摘要為依據；PASS 只適用於其明確測試範圍。

| Milestone / 里程碑 | Status / 狀態 | Evidence / 依據 |
| --- | --- | --- |
| M0 historical reproduction / 歷史重現 | **PASS** | 40/40 archived runs |
| M1A canonical network / 標準路網 | **PASS** | 7 parking areas, `C_eff=170`, network validation |
| M1B lifecycle / 生命週期 | **PASS** | 7/7 unit tests; 3/3 SUMO lifecycle smoke |
| M1C-1 Poisson arrivals / 動態到達 | **PASS** | 8/8 unit tests |
| M1C-2 Parking durations / 停車時間 | **PASS** | 8/8 unit tests |
| M1C-3 dynamic integration / 動態整合 | **PASS** | 7/7 completed; zero mass-balance error |
| M1D continuous free search / 持續自由搜尋 | **PENDING** | Not yet implemented / 尚未實作 |
| M1E instability detector / 失穩偵測 | **PENDING** | C1/C2 not yet implemented / C1/C2 尚未實作 |
| Formal Stage A/B/C sweeps / 正式負載掃描 | **PENDING** | Requires model validation and parameter freeze / 待完成模型驗證與參數凍結 |

The 1C-3 smoke run released and completed **7/7 vehicles**, with `removed_error=0`, maximum absolute mass-balance error `0`, and maximum scheduled-release delay `0.9312152104140328 s`. The `outside` and `entry_queue` visibility checks also passed.

**Important:** M1C-3 uses the **fixed** legal parking area `PA_Z2_G`. It does **not** validate free-search choice, refusal/retry behavior, C1/C2 gridlock, or any critical load.

1C-3 的 smoke run 共釋放並完成 **7/7 台車**，`removed_error=0`、最大質量平衡絕對誤差為 `0`、最大預定到達至釋放延遲為 `0.9312152104140328 秒`。`outside` 與 `entry_queue` 狀態可觀測性檢查也已通過。

**重要：** M1C-3 指定**固定**合法停車區 `PA_Z2_G`，**尚未**驗證自由搜尋選擇、拒絕／重試行為、C1/C2 gridlock 或任何臨界負載。

## Source structure / 程式與資料結構

```text
02_Exp1_FreeSearch_v2/
├─ README.md
├─ config/                         # formal configs to be frozen later
├─ demand/                         # future demand scenario assets
├─ network/canonical/              # fixed network + network README
├─ scripts/
│  ├─ inspect_network.py
│  ├─ vehicle_state.py
│  ├─ run_lifecycle_smoke.py
│  ├─ demand_generator.py
│  ├─ parking_duration.py
│  └─ run_dynamic_demand_smoke.py
├─ tests/
│  ├─ test_vehicle_state.py
│  ├─ test_demand_generator.py
│  └─ test_parking_duration.py
├─ validation/
│  ├─ network_summary.json
│  ├─ network_inventory.csv
│  ├─ Milestone_1B_README.md
│  ├─ Milestone_1B2_README.md
│  ├─ Milestone_1C1_README.md
│  ├─ Milestone_1C2_README.md
│  ├─ Milestone_1C3_README.md
│  ├─ lifecycle_smoke/
│  └─ dynamic_demand_smoke/
├─ raw/
├─ processed/
├─ figures/
└─ logs/
```

The `config/`, `demand/`, and data-output directories are reserved for future research stages; their presence does not imply that corresponding formal scenarios or paper-ready data already exist.

`config/`、`demand/` 與資料輸出目錄是預留給後續研究階段使用；目錄存在不代表對應的正式情境或論文級資料已完成。

## Validation commands (Windows CMD) / 驗證指令（Windows CMD）

From the Experiment 1 directory in the validated `sumo_py310` environment, run:

於已驗證的 `sumo_py310` 環境中，切換至 Experiment 1 目錄後執行：

```cmd
conda activate sumo_py310
cd /d C:\TITS_SmartParking\02_Exp1_FreeSearch_v2
python scripts\inspect_network.py
python -m unittest discover -s tests -p "test_*.py"
python scripts\run_lifecycle_smoke.py
python scripts\run_dynamic_demand_smoke.py --precheck
python scripts\run_dynamic_demand_smoke.py
```

The repository currently discovers **23 tests** (7 lifecycle + 8 Poisson + 8 duration). Passing these tests is separate from a live SUMO smoke test, and neither substitutes for the future formal Experiment 1 batch.

The M1C-3 smoke records are under [`validation/dynamic_demand_smoke/`](validation/dynamic_demand_smoke/), including `summary.json`, arrival schedule, parking durations, release audit, vehicle events, and system log.

本 repository 目前可找到 **23 項測試**（生命週期 7、Poisson 到達 8、停車時間 8）。通過單元測試不等於已通過真實 SUMO 煙霧測試；兩者也都不能取代未來正式 Experiment 1 批次實驗。

M1C-3 的煙霧測試證據位於 [`validation/dynamic_demand_smoke/`](validation/dynamic_demand_smoke/)，包含 `summary.json`、到達排程、停車時間、釋放時間稽核、車輛事件與系統紀錄。

## Next milestone: M1D / 下一里程碑：M1D

Before implementation, define the bounded-rational driver information regime and the source/update rate of perceived zone scarcity `O_hat_iz`. Specify frozen distributions for driving-time, walking-distance, perceived-scarcity weights, and parking acceptance probability. Do **not** substitute global instantaneous vacancy knowledge without documenting that information assumption.

Then implement legal candidate-zone filtering, driver zone choice, local observation and parking acceptance, rejection/continued search, explicit loops, and deterministic RNG streams. Validate each mechanism with unit tests before integrating with SUMO.

The M1E detector and the SOP's formal load sweeps must wait until these behavior, instrumentation, and freeze conditions pass independent quality control.

實作前必須明確定義有限理性駕駛的資訊範圍，以及感知區域稀缺度 `O_hat_iz` 的來源與更新頻率；同時訂定行車時間、步行距離、感知稀缺度權重，以及停車接受機率的固定分布。**不得**在未說明資訊假設的情況下，直接讓駕駛使用即時全域空位資訊。

再依序實作合法候選區域過濾、駕駛分區選擇、局部觀測及停車接受／拒絕、持續搜尋、迴圈紀錄與獨立可重現亂數流。各機制須先通過單元測試，再整合到 SUMO。

M1E 偵測器以及 SOP 規定的正式負載掃描，必須等候行為模型、資料紀錄與參數凍結完成獨立品質驗證後才能進行。

## Formal-run safeguards / 正式實驗保護規則

Formal runs must preserve SUMO teleport disabling, collision/route-failure logs, consistent geometry and behavior distributions, complete seeds and configuration manifests, legal eligible-space accounting, right-censoring information, and Git/SUMO/Python version identifiers. The SOP requires warm-up and step-length checks plus a Stage B sign-off before coarse sweeps.

Do not tune the simulator or detector after seeing preliminary results merely to create a desirable instability transition. The SOP explicitly allows a negative or capacity-only result and a corresponding change of paper framing.

正式 run 須維持 SUMO teleport 關閉、碰撞與路線失敗記錄、固定路網與行為分布、完整種子與情境 manifest、合法空位帳務、右設限資訊，以及 Git/SUMO/Python 版本紀錄。SOP 要求在 coarse sweep 前完成 warm-up 與 step-length 檢查，以及 Stage B 正式簽核。

不得為了產生理想的失穩轉換，而在看到初步結果後任意調整模擬器或偵測門檻。SOP 明確允許觀察到無失穩或僅容量不足的結果，並依此調整論文研究定位。
