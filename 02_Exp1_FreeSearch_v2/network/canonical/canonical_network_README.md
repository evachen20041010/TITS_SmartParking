# Canonical Network / 標準路網 — T-ITS Experiment 1

## Provenance / 來源與沿革

Source network:

```text
01_ICCE_2026_Frozen/snapshot/sumo_parking
```

The network geometry and parking-area definitions originate from the reproduced ICCE-TW 2026 experiment.

The T-ITS Experiment 1 demand process, vehicle lifecycle, free-search behavior, logging, and gridlock detection are rebuilt independently.

The purpose of inheriting the ICCE geometry is to preserve a common physical baseline while separating the new T-ITS experimental logic from the historical implementation.

本路網的幾何結構與停車區定義源自已完成重現驗證的 ICCE-TW 2026 實驗。

T-ITS Experiment 1 的需求生成、車輛生命週期、自由搜尋行為、資料記錄與 gridlock detection 均重新獨立建構，不直接沿用 ICCE simulator 的控制邏輯。

沿用 ICCE geometry 的目的，是保留一致的物理場域基準，同時將新的 T-ITS 實驗邏輯與歷史實作明確分離。

---

## Initial Network Facts / 初始路網資訊

The canonical network contains:

```text
Non-internal edges : 3
Edge IDs           : E1, E2, E3
Edge length        : 200 m each
Parking zones      : 3
Total capacity     : 200 spaces
```

Parking-space capacity encoded in `parking_areas.add.xml` is（定義的停車容量）:

```text
General (G)   : 170
Family (F)    : 20
Disabled (D)  : 10
Total         : 200
```

The parking-area inventory is（停車區容量）:

```text
Zone 1
  PA_Z1_G : 40
  PA_Z1_F : 10
  PA_Z1_D : 5
  Total   : 55

Zone 2
  PA_Z2_G : 50
  PA_Z2_F : 10
  PA_Z2_D : 5
  Total   : 65

Zone 3
  PA_Z3_G : 80
  Total   : 80
```

Therefore:

```text
Zone 1 = 55
Zone 2 = 65
Zone 3 = 80
Total  = 200
```

---

## Effective Capacity / 有效容量

For Experiment 1-Core, the studied population is **general vehicles only** under strict legal parking access. General vehicles may use general parking spaces only. Therefore:

Experiment 1-Core 第一階段的研究對象為**一般車輛**，並採用嚴格合法停車限制。一般車輛僅允許使用一般停車位。因此：

```text
C_eff = C_general = 170
```

The total physical capacity（總物理容量）:

```text
C_total = 200
```

must not be used as the denominator of offered load for the general-vehicle-only core experiment. The distinction is:

不得直接作為 general-vehicle-only 核心實驗的 offered-load denominator。兩者差異為：

```text
C_total = all physically defined parking spaces（路網中所有物理停車位）
C_eff   = parking spaces legally accessible to the studied vehicle class（研究車種依法可以使用的停車位）
```

---

## Experiment-1 Load Definition / Experiment 1 負載定義

Experiment 1 uses offered parking load:

```text
rho = lambda * E[T_park] / C_eff
```

where:

```text
rho        = offered parking load
lambda     = arrival rate
E[T_park]  = expected parking duration
C_eff      = effective legal parking capacity
```

For the initial general-only core experiment（對初始 general-only 核心實驗）:

```text
C_eff = 170
```

Therefore:

```text
rho = lambda * E[T_park] / 170
```

`rho` is not the same as instantaneous occupancy.

Actual occupancy must emerge endogenously from arrivals, parking durations, parking search, and departures.

`rho` 不等同於任一時間點的實際 occupancy。

實際 occupancy 必須由車輛到達、停車時間、搜尋行為與離場過程自然形成。

---

## Canonical Configuration / 標準設定

The base SUMO configuration is（SUMO 基礎設定檔）:

```text
base.sumocfg
```

It loads（載入）:

```text
parking_lot.net.xml
parking_areas.add.xml
```

Automatic teleport is disabled for Experiment 1 because long-duration congestion must remain observable instead of being artificially cleared by SUMO. The relevant setting is:

Experiment 1 關閉 automatic teleport，因為長時間壅塞必須被保留並觀察，不能由 SUMO 自動移除車輛造成假性恢復。相關設定為：

```text
--time-to-teleport -1
```

---

## Network Validation / 路網驗證

The canonical network must be inspected using:

Canonical network 必須使用下列程式進行檢查：

```bash
python scripts/inspect_network.py
```

The validation script checks:

* Parking-area IDs.（停車區 ID）

* Parking-area lane references.（停車區所引用的 lane）

* Start and end positions.（停車區起點與終點位置）

* Positive parking capacities.（停車容量是否為正值）

* Capacity by zone.（各 zone 容量）

* Capacity by parking-space type.（各類型停車位容量）

* Effective capacity for the studied vehicle class.（研究車種的有效容量）

Expected result（預期結果）:

```text
Parking areas      : 7
Non-internal edges : 3
Non-internal lanes : 3

general            : 170
family             : 20
disabled           : 10
TOTAL              : 200

C_eff              : 170

Validation: PASS
```

The validation outputs are stored in（驗證輸出保存）:

```text
validation/network_inventory.csv
validation/network_summary.json
```

These files form part of the network provenance and should be committed with the canonical network.

這些檔案屬於 network provenance 的一部分，應與 canonical network 一起納入版本控制。

---

## Modification Rule / 修改規則

The canonical geometry must remain fixed during Experiment 1-Core unless a deliberate new experimental phase is introduced. Do not simultaneously modify:

在 Experiment 1-Core 中，除非正式開啟新的實驗階段，否則 canonical geometry 必須保持固定。不得在核心 load experiment 中同時修改：

```text
layout
lane geometry
number of zones
parking-space distribution
parking-space legality
speed configuration
car-following configuration
walking destination
```

while studying the effect of offered load.

Any future geometry or parking-capacity modification must be committed together with:

在研究 offered load 的影響時，上述條件應維持固定。

未來如修改路網 geometry 或停車容量，必須同步保存：

```text
updated network files
updated network_inventory.csv
updated network_summary.json
validation result
Git commit identifier
```

This prevents silent changes to the physical experiment baseline.

如此可避免物理實驗基準在沒有紀錄的情況下被修改。

---

## Current Validation Status / 目前驗證狀態

The initial canonical network has passed Milestone 1A validation.Validated values:

初始 canonical network 已通過 Milestone 1A 驗證。已驗證數值：

```text
C_total    = 200
C_general  = 170
C_family   = 20
C_disabled = 10
C_eff      = 170

Network XML validation = PASS
SUMO base config load  = PASS
```

This configuration is the physical baseline for subsequent T-ITS Experiment 1 development.

此設定為後續 T-ITS Experiment 1 開發與正式實驗的物理基準。
