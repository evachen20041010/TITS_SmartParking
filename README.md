# T-ITS Smart Parking Research / T-ITS 智慧停車研究專案

## Research objective / 研究目標

This repository supports a staged research program on near-saturation parking systems. Experiment 1 asks whether decentralized, bounded-rational parking search develops reproducible instability as **offered parking load** increases. A subsequent controller-comparison study is conditional on the Experiment 1 go/no-go findings.

本專案以分階段方式研究接近飽和的停車系統。Experiment 1 要回答的是：隨著 **停車需求負載（offered parking load）** 增加，去中心化、有限理性的駕駛搜尋行為是否會產生可重現的失穩現象。後續控制策略比較研究，應依 Experiment 1 的 go/no-go 結果決定研究定位。

## Source of methodological authority / 正式研究方法依據

The current Experiment 1 execution specification is:

目前 Experiment 1 的正式執行規格為：

[`03_docs/20260920_IEEE_Trans_ITS_Experiment1_v2_SOP.pdf`](03_docs/20260920_IEEE_Trans_ITS_Experiment1_v2_SOP.pdf)

Its key requirements include a frozen canonical layout, legal effective capacity, bounded-rational information assumptions, distinct C1/C2 event definitions, run-level traceability, right-censoring-aware analyses, and a formal sign-off before coarse-load sweeps.

其核心要求包含：固定標準路網、合法有效容量、有限理性資訊假設、區分 C1/C2 事件、完整 run 追溯資訊、處理右設限（right censoring）的分析，以及 coarse-load sweep 開始前的正式簽核。

## Repository layout / 專案目錄

| Path | Purpose / 用途 |
| --- | --- |
| [`00_archive/`](00_archive/README.md) | Original historical packages / 歷史原始封存檔 |
| [`01_ICCE_2026_Frozen/`](01_ICCE_2026_Frozen/README_ICCE.md) | Reproducible ICCE-TW baseline; frozen simulator / 可重現的 ICCE-TW 凍結基準 |
| [`02_Exp1_FreeSearch_v2/`](02_Exp1_FreeSearch_v2/README.md) | Experiment 1 implementation and validation / Experiment 1 實作與驗證 |
| `03_docs/` | Research SOP and supporting documentation / 研究 SOP 與文件 |
| `04_paper/` | Manuscript workspace / 論文工作目錄 |

Never modify the historical simulator under `01_ICCE_2026_Frozen/snapshot/` to match newer interpretations. Implement new Experiment 1 behavior only in `02_Exp1_FreeSearch_v2/`.

不得為了符合新的研究解釋而修改 `01_ICCE_2026_Frozen/snapshot/` 中的歷史模擬器。新的 Experiment 1 行為應僅於 `02_Exp1_FreeSearch_v2/` 開發。

## Verified progress / 已驗證研究進度

The status below reflects the archived validations included with the project, **as of 2026-10-15**.

下列狀態以本專案保存的驗證結果為準，**截至 2026-10-15**。

| Milestone | Status | Evidence / 驗證依據 |
| --- | --- | --- |
| M0 - ICCE reproduction / ICCE 重現 | **PASS** | 40/40 historical runs matched / 40/40 歷史實驗重現 |
| M1A - Canonical network / 標準路網 | **PASS** | `validation/network_summary.json`; `C_total=200`, `C_eff=170` |
| M1B - Lifecycle / 車輛生命週期 | **PASS** | 7 unit tests; 3/3 SUMO smoke vehicles / 7 項測試、3/3 台模擬車 |
| M1C-1 - Poisson arrivals / 動態到達 | **PASS** | 8 unit tests / 8 項單元測試 |
| M1C-2 - Parking durations / 停車時間 | **PASS** | 8 unit tests / 8 項單元測試 |
| M1C-3 - Dynamic SUMO integration / 動態整合 | **PASS** | 7/7 completed; mass-balance error 0 / 7/7 完成、帳務誤差 0 |
| M1D - Continuous free search / 持續式自由搜尋 | **NOT STARTED** | Behavior and information rules must be specified / 待凍結行為與資訊規則 |
| M1E - Instability detector / 失穩偵測 | **NOT STARTED** | C1/C2 and sensitivity checks pending / C1/C2 與敏感度檢查待完成 |
| Formal load sweeps / 正式負載掃描 | **NOT STARTED** | Requires parameter freeze and sign-off / 須先完成參數凍結與簽核 |

**Scope warning:** M1C-3 uses a fixed legal parking target (`PA_Z2_G`) and smoke-only input parameters. Its PASS result proves end-to-end integration, **not** a validated free-search strategy, system instability, or a critical offered load.

**範圍警示：** M1C-3 使用固定合法停車區 `PA_Z2_G` 與僅供煙霧測試的參數。其 PASS 只證明動態流程整合成功，**不代表**自由搜尋策略、系統失穩或臨界負載已通過正式驗證。

## Core experiment definitions / 核心實驗定義

The general-vehicle-only core experiment has 170 legally usable spaces out of 200 physically defined spaces. Offered load is defined by:

僅研究一般車輛的核心實驗，在總共 200 個實體車位中，有 170 個可合法使用的車位。需求負載定義為：

```text
C_total = 200
C_eff   = 170
rho     = lambda * E[T_park] / C_eff
lambda  = rho * C_eff / E[T_park]
```

`rho` is **not** instantaneous occupancy. The SOP treats search-induced gridlock (C1) and capacity-induced blockage (C2) as different events; capacity saturation alone is not proof of gridlock.

`rho` **不是**瞬間實際占用率。SOP 將搜尋誘發失穩（C1）與容量不足造成的阻塞（C2）視為不同事件；停車位滿位本身不是 gridlock 的證據。

## Environment and quick validation / 環境與快速驗證

The historically validated working environment uses Python 3.10.18, SUMO 1.24.0, and TraCI. Select the `sumo_py310` interpreter before running these commands in Windows CMD:

先前已驗證的工作環境使用 Python 3.10.18、SUMO 1.24.0 與 TraCI。請在 Windows CMD 選用 `sumo_py310` 環境後執行：

```cmd
conda activate sumo_py310
cd /d C:\TITS_SmartParking\02_Exp1_FreeSearch_v2
python -m unittest discover -s tests -p "test_*.py"
python scripts\run_dynamic_demand_smoke.py --precheck
python scripts\run_dynamic_demand_smoke.py
```

The present repository contains **23** discovered unit tests, not 27. The complete SUMO smoke test requires a working SUMO/TraCI installation; `--precheck` does not start SUMO.

See the [Experiment 1 README](02_Exp1_FreeSearch_v2/README.md) for milestone-specific commands, data locations, and method limitations.

目前 repository 內可由 discovery 找到的單元測試為 **23 項**，不是 27 項。完整 SUMO 煙霧測試需要可用的 SUMO/TraCI 環境；`--precheck` 不會啟動 SUMO。

各里程碑指令、資料位置與方法限制，請參考 [Experiment 1 README](02_Exp1_FreeSearch_v2/README.md)。

## Reproducibility and Git / 可重現性與版本控制

Commit source code, validation reports, manifests, and small verification logs. Git LFS is configured for selected historical archives and large experiment outputs; do not assume every future generated file is automatically covered.

Use `local_paths.example.yaml` as a machine-specific template, and keep the actual `local_paths.yaml` private and out of Git. Formal research parameters belong in reviewed experiment configurations, **not** local path settings.

Milestone tags in the repository include `milestone0-icce-reproduction`, `milestone1b-lifecycle`, and `milestone1c-dynamic-demand`. A documentation-only change after a milestone tag does not retroactively alter its frozen validation evidence.

程式碼、驗證報告、manifest 及小型驗證紀錄應納入版本控制。指定的歷史封存檔與大型實驗輸出已設定 Git LFS，但不可假設所有未來生成的檔案都會自動被 LFS 管理。

`local_paths.example.yaml` 僅作為電腦專屬路徑範例；實際 `local_paths.yaml` 應保留於本機且不得提交 Git。正式研究參數應存於經審查的實驗設定檔，**不能**放在本機路徑設定中。

Repository 已包含 `milestone0-icce-reproduction`、`milestone1b-lifecycle` 與 `milestone1c-dynamic-demand` 等里程碑標籤。後續僅修改文件，不會追溯變更先前 tag 所封存的驗證依據。

## Historical-data caution / 歷史資料判讀提醒

The reproduced ICCE `Free_95` archive has **8/10 truncated runs (80%)**, whereas the earlier manuscript reports 70%. Truncation must not be silently reclassified as search-induced gridlock. Consult [`01_ICCE_2026_Frozen/README_ICCE.md`](01_ICCE_2026_Frozen/README_ICCE.md) and its reproduction notes.

重現後的 ICCE `Free_95` 歷史輸出有 **8/10 次截斷（80%）**，但早期論文文字記載 70%。不得在沒有證據的情況下，直接將截斷重新分類為搜尋誘發 gridlock。詳見 [`01_ICCE_2026_Frozen/README_ICCE.md`](01_ICCE_2026_Frozen/README_ICCE.md) 與重現紀錄。

