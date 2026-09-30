# T-ITS Experiment 1 — Free-Search Instability and Critical-Load Characterization / 自由搜尋失穩與臨界負載特性分析

This directory contains the simulation framework for Experiment 1 of the IEEE Transactions on Intelligent Transportation Systems (T-ITS) research project.

The purpose of Experiment 1 is to determine whether decentralized bounded-rational parking search exhibits a reproducible transition from stable operation to congestion and gridlock as offered parking load increases.

本目錄包含 IEEE Transactions on Intelligent Transportation Systems（T-ITS）研究計畫之 Experiment 1 模擬框架。

Experiment 1 的目的，是確認在沒有中央控制器介入的情況下，去中心化且具有限理性的停車搜尋行為，是否會隨 offered parking load 增加，出現可重現的穩定、轉換與失穩／壅塞狀態。

---

## Research Questions / 研究問題

Experiment 1 addresses three primary questions:

1. Does decentralized bounded-rational free search exhibit a reproducible instability transition as offered parking load increases?（去中心化的 bounded-rational free search 是否會隨 offered parking load 增加而出現可重現的失穩轉換）

2. At what offered load does the probability of persistent congestion or gridlock become substantial?(offered load 增加到什麼程度時，持續性壅塞或 gridlock 的發生機率會明顯增加？)

3. Which microscopic variables precede the transition, such as circulating vehicles, entrance queue, cruising-time tail, speed degradation, or zone imbalance?(哪些 microscopic variables 會在失穩之前出現明顯變化，例如巡航空車數、入口排隊、cruising-time tail、速度下降或區域不平衡？)

The simulator must reproduce the phenomenon faithfully rather than being tuned to create an artificial phase transition.

模擬器的目的在於忠實觀察系統現象，而不是為了產生理想化的 phase transition 而調整模型。

---

## Relationship to the ICCE-TW Baseline / 與 ICCE-TW 基準實驗的關係

The historical ICCE-TW 2026 simulator and outputs are preserved separately under（模擬器與輸出已獨立封存於）:

```text
01_ICCE_2026_Frozen/
```

The ICCE baseline was reproduced before development of this Experiment 1 simulator.

The complete historical experiment contains four scenarios and ten seeds per scenario, for a total of 40 runs. The archived core results were reproduced exactly.

The T-ITS Experiment 1 simulator does not extend the old ICCE controller directly. It inherits the canonical parking-lot geometry but rebuilds demand generation, vehicle lifecycle accounting, free-search behavior, logging, and instability detection independently.

在建立 Experiment 1 simulator 之前，已完成 ICCE baseline 重現。

完整歷史實驗包含四個情境，每個情境使用十個 random seeds，共 40 runs；核心 archived results 已可精確重現。

T-ITS Experiment 1 不直接修改或延伸舊 ICCE controller。僅沿用 canonical parking-lot geometry；需求生成、車輛生命週期、自由搜尋行為、logging 與失穩偵測均重新獨立建構。

---

## Canonical Network / 標準道路網路

The canonical network is located at:

```text
network/canonical/
```

The initial network（初始網路） contains:

```text
3 parking zones
3 non-internal road edges
200 total parking spaces
```

Parking-space capacities are（停車位）:

```text
General (G)   : 170
Family (F)    : 20
Disabled (D)  : 10
Total         : 200
```

Experiment 1-Core studies general vehicles only under strict legal parking constraints.

Therefore, the effective parking capacity is:

Experiment 1-Core 第一階段僅研究一般車輛，並採嚴格合法車位限制。

因此有效停車容量定義為：

```text
C_eff = 170
```

The total capacity of 200 must not be used as the denominator for the general-vehicle-only core experiment.

在 general-vehicle-only 核心實驗中，不得直接使用總容量 200 作為 offered-load denominator。

---

## Offered Parking Load / 停車需求負載

Experiment 1 uses offered parking load rather than fixed occupancy as the experimental control variable. The load is defined as:

Experiment 1 使用 offered parking load，而不是固定 occupancy，作為主要實驗控制變數。負載定義為：

```text
rho = lambda * E[T_park] / C_eff
```

where:

```text
rho        = offered parking load
lambda     = vehicle arrival rate
E[T_park]  = expected parking duration
C_eff      = effective legal parking capacity
```

For the initial general-only core experiment:

```text
C_eff = 170
```

Actual occupancy is generated endogenously by the simulator and is not forced to equal `rho`.

The intended causal chain is:

實際 occupancy 由 simulator 內生產生，不會被強制設定成與 `rho` 相同。

預期的因果鏈為：

```text
demand
→ occupancy
→ parking search
→ circulation
→ congestion
→ spillback / gridlock
```

---

## Vehicle Lifecycle / 車輛生命週期

Every released vehicle must belong to exactly one lifecycle state:

每一台已產生需求事件的車輛，在任何時間只能屬於一個生命週期狀態：

```text
outside
→ entry_queue
→ cruising
→ parked
→ departing
→ completed
```

An additional terminal state is used for abnormal accounting:

另外定義一個異常終止狀態：

```text
removed_error
```

`removed_error` preserves mass balance when a vehicle unexpectedly disappears, but any formal experiment containing such a vehicle is invalid.

At every simulation step:

`removed_error` 用來在車輛非預期消失時維持質量平衡；但任何包含此狀態的正式實驗都必須判定為無效。

每一個 simulation step 都必須滿足：

```text
N_generated_to_date
=
N_outside
+ N_entry_queue
+ N_cruising
+ N_parked
+ N_departing
+ N_completed
+ N_removed_error
```

Therefore:

```text
mass_balance_error = 0
```

must hold throughout the run（必須在整個 simulation run 中始終成立）.

---

## Current Milestone Status / 目前里程碑進度

### Milestone 0 — Historical ICCE Recovery / ICCE 歷史基準復原

```text
[PASS] Original ICCE archive recovered
[PASS] Python/SUMO environment reproduced
[PASS] Single-seed reproduction
[PASS] Free_95 ten-seed reproduction
[PASS] Complete 40-run reproduction
[PASS] Archived Table-I reconstruction
```

### Milestone 1A — Canonical Network / 標準網路

```text
[PASS] Canonical network created
[PASS] Parking-area inventory validated
[PASS] C_total = 200
[PASS] C_eff = 170 for general vehicles
[PASS] SUMO base configuration loads successfully
```

### Milestone 1B — Vehicle Lifecycle and Mass Balance / 車輛生命週期與質量平衡

```text
[PASS] Vehicle lifecycle ledger implemented
[PASS] 7/7 lifecycle unit tests
[PASS] SUMO lifecycle integration
[PASS] 3/3 smoke-test vehicles completed
[PASS] removed_error = 0
[PASS] mass_balance_error = 0 for all recorded steps
```

### Milestone 1C — Dynamic Demand / 動態需求

```text
[ ] Poisson arrival generator
[ ] Arrival reproducibility tests
[ ] Parking-duration generator
[ ] Dynamic-demand SUMO smoke test
```

### Milestone 1D — Continuous Free Search / 持續式自由搜尋

```text
[ ] Driver preference generation
[ ] Zone-choice model
[ ] Acceptance / rejection behavior
[ ] Continued search after unsuccessful parking attempt
```

### Milestone 1E — Instability Detection / 失穩偵測

```text
[ ] Entrance spillback detector
[ ] Severe internal congestion detector
[ ] Gridlock detector
[ ] Threshold sensitivity tests
```

---

## Repository Structure / 專案結構

```text
02_Exp1_FreeSearch_v2/
│
├─ README.md
│
├─ config/
│
├─ network/
│  └─ canonical/
│     ├─ parking_lot.net.xml
│     ├─ parking_areas.add.xml
│     ├─ parking.edg.xml
│     ├─ parking.nod.xml
│     ├─ base.sumocfg
│     └─ README.md
│
├─ demand/
│
├─ scripts/
│  ├─ inspect_network.py
│  ├─ vehicle_state.py
│  └─ run_lifecycle_smoke.py
│
├─ tests/
│  └─ test_vehicle_state.py
│
├─ validation/
│  ├─ network_inventory.csv
│  ├─ network_summary.json
│  ├─ Milestone_1B_README.md
│  ├─ Milestone_1B2_README.md
│  └─ lifecycle_smoke/
│     ├─ system_log.csv
│     ├─ vehicle_events.csv
│     └─ summary.json
│
├─ raw/
├─ processed/
├─ figures/
└─ logs/
```

---

## Basic Validation Commands / 基本驗證指令

Activate the validated environment（啟用已驗證環境）:

```bash
conda activate sumo_py310
```

Inspect the canonical network（檢查）:

```bash
python scripts/inspect_network.py
```

Expected result（預期結果）:

```text
C_total = 200
C_eff   = 170
Validation: PASS
```

Run lifecycle unit tests（執行生命週期單元測試）:

```bash
python tests/test_vehicle_state.py
```

Expected result（預期結果）:

```text
Ran 7 tests
OK
```

Run the SUMO lifecycle smoke test:

```bash
python scripts/run_lifecycle_smoke.py
```

Expected result（預期結果）:

```text
Completed vehicles        : 3/3
removed_error             : 0
max |mass_balance_error|  : 0
Milestone 1B-2 verdict    : PASS
```

---

## Reproducibility Rules / 可重現性規則

Formal simulation runs must satisfy the following requirements（正式 simulation runs 必須遵守以下規則）:

* Automatic SUMO teleport must remain disabled.（SUMO automatic teleport 必須關閉）

* Random seeds and scenario parameters must be recorded.（Random seeds 與 scenario parameters 必須完整記錄）

* Silent vehicle removal is prohibited.（禁止未留下紀錄的車輛移除）

* Vehicle-state mass balance must remain exact.（Vehicle-state mass balance 必須完全成立）

* Raw logs, processed summaries, configuration files, and Git commit identifiers must be preserved.（Raw logs、processed summaries、configuration files 與 Git commit identifier 必須保存）

* Formal runs must satisfy `removed_error = 0`.（正式實驗必須滿足 `removed_error = 0`）

---

## Development Principle / 開發原則

Each new mechanism is validated independently before it is included in formal experiments.

The development sequence is:

每一項新機制都必須先獨立驗證，通過後才能納入正式實驗。

開發順序為：

```text
historical reproduction
→ canonical network
→ lifecycle accounting
→ dynamic arrivals/departures
→ continuous free search
→ logging
→ instability detection
→ load sweep
→ critical-load estimation
```

Formal load-sweep experiments must not begin until the simulator foundation and quality-control checks are complete.

在 simulator foundation 與品質控制機制完成之前，不得開始正式 load-sweep 實驗。
