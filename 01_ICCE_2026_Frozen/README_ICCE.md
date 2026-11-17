# ICCE-TW 2026 Frozen Baseline / ICCE-TW 2026 凍結基準

## Historical research / 歷史研究

This directory preserves the simulator and reproduction records for *Stabilizing High-Occupancy Parking Systems via Legally Constrained Dynamic Assignment* (ICCE-TW 2026).

The frozen baseline is a historical reference. It is **not** the current T-ITS Experiment 1 implementation, and new control, demand, or instability models must not be added to its frozen snapshot.

本目錄保存 ICCE-TW 2026 研究 *Stabilizing High-Occupancy Parking Systems via Legally Constrained Dynamic Assignment* 的模擬器與重現紀錄。

此凍結基準只作為歷史參考，**不是**目前的 T-ITS Experiment 1 實作。新的控制、需求或失穩模型不得加入凍結快照。

## Important paths / 重要路徑

| Path | Role / 用途 |
| --- | --- |
| `../00_archive/sumo_parking_ICCE_2026_original.zip` | Original source archive / 原始程式封存檔 |
| `snapshot/sumo_parking/` | Frozen recovered simulator / 凍結的復原模擬器 |
| `validation/` | Independent reproduction scripts/results / 獨立重現腳本與結果 |
| `reproduction_notes.md` | Human-readable verified reproduction record / 已驗證重現紀錄 |

Keep `snapshot/sumo_parking/` unchanged. Verification scripts may be updated **outside** the snapshot, with changes documented separately.

`snapshot/sumo_parking/` 必須維持不變。驗證腳本可在快照**以外**的目錄更新，但變更應另行記錄。

## Reproduction design / 重現設計

The four historical scenario identifiers are preserved exactly（四個歷史情境識別碼必須保持原樣）:

```text
Free_85
Free_95
Assigned_85
Assigned_95
```

Each scenario uses ten original random seeds: `10, 20, 30, ..., 100`. In total, the archived experiment has **40 runs**; the reproduced core outputs matched **40/40** historical runs.

The `85` and `95` suffixes are names of the historical nominal vehicle-demand scenarios. They must **not** be equated to continuously measured parking occupancy or the newer Experiment 1 offered load `rho`.

每個情境使用十個原始 random seeds：`10, 20, 30, ..., 100`。歷史實驗總共 **40 runs**，重現後的核心輸出與歷史紀錄 **40/40 完全一致**。

`85` 與 `95` 是早期**名目車輛需求情境**的名稱，**不可**直接視為連續時間量測的停車占用率，也不可與新版 Experiment 1 的 offered load `rho` 混用。

## Reproduced aggregate results / 重現彙總結果

The following numbers are archived-core reproduction statistics (ten seeds per scenario), not new T-ITS stability findings.

下表為每個情境十個 seeds 的歷史核心指標重現統計，**不是**新的 T-ITS 穩定性實驗結果。

| Scenario / 情境 | Mean `N_Trips` | Mean cruising time (s) / 平均巡航時間 | Mean total CO2 (kg) / 平均 CO2 | Truncated / 截斷次數 |
| --- | ---: | ---: | ---: | ---: |
| `Free_85` | 166.8 | 78.872922 | 40.778020 | 3/10 |
| `Free_95` | 174.9 | 78.988812 | 42.807280 | **8/10** |
| `Assigned_85` | 170.0 | 73.945294 | 38.969170 | 0/10 |
| `Assigned_95` | 190.0 | 74.555263 | 43.913050 | 0/10 |

**Historical discrepancy:** the archived `Free_95` output contains **8/10 truncated runs (80%)**, whereas the ICCE-TW manuscript reports 70% in its instability description. The archived outputs were reproduced faithfully; they were not edited to force agreement with the manuscript.

**Interpretation boundary:** a time-limit truncation is **not**, by itself, proof of traffic gridlock. Likewise, the historical `N_Trips` measure must not automatically be interpreted as confirmed successful parking for every recorded trip.

**歷史差異：** 封存的 `Free_95` 結果為 **8/10 次截斷（80%）**，而 ICCE-TW 稿件關於失穩的文字提及 70%。本專案忠實重現封存結果，並未為了與稿件一致而修改歷史輸出。

**判讀界線：** 模擬因時間上限而截斷，**本身不足以證明**交通 gridlock；歷史 `N_Trips` 也不能直接解讀為每一筆皆已成功完成停車。

## Reproduction tools / 重現工具

The independent validation scripts are stored under `validation/`（獨立驗證腳本保存）:

```text
run_icce_single_case.py
run_icce_free95_all_seeds.py
run_icce_table1_all_40.py
run_single_validation.py
```

The validated environment records Python 3.10.18, SUMO 1.24.0, and pandas 2.2.3 for reproduction. The original historical pandas version is unknown; check `reproduction_notes.md` and the environment files before rerunning the archive.

重現時記錄的環境為 Python 3.10.18、SUMO 1.24.0 與 pandas 2.2.3；原始歷史 pandas 版本未知。重新執行前應先閱讀 `reproduction_notes.md` 及環境紀錄。

## Boundary to T-ITS Experiment 1 / 與 T-ITS Experiment 1 的邊界

The new simulator under `../02_Exp1_FreeSearch_v2/` inherits the canonical physical geometry but independently implements its demand, lifecycle, parking-search behavior, logging, and instability definitions as development proceeds.

The newer SOP explicitly distinguishes search-induced gridlock (C1) from capacity-induced blockage (C2). Do not retrospectively apply these labels to historical ICCE truncated runs without the required event evidence.

新的 `../02_Exp1_FreeSearch_v2/` 沿用 canonical 物理路網，但需求生成、車輛生命週期、搜尋行為、紀錄及失穩定義，須依開發階段獨立實作。**目前已完成動態流程整合，持續式自由搜尋與失穩偵測仍待實作。**

新版 SOP 明確區分搜尋誘發失穩（C1）與容量不足阻塞（C2）。若沒有所需事件證據，不得事後將這些標籤直接套用到早期 ICCE 的截斷 runs。

## Archive tag / 封存標籤

The historical reproduction milestone is tagged `milestone0-icce-reproduction`. Changes to documentation must not silently modify the archived simulator or reinterpret the original observations.

歷史重現里程碑標籤為 `milestone0-icce-reproduction`。後續文件更新不得默默修改原始模擬器，或重新定義歷史觀測結果。
