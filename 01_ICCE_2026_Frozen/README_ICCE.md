# ICCE-TW 2026 Frozen Baseline / ICCE-TW 2026 凍結基準版本

This directory preserves the simulation used for:
Stabilizing High-Occupancy Parking Systems via Legally Constrained Dynamic Assignment.

本目錄保存用於重現 ICCE-TW 2026 研究之模擬環境、原始檔案與驗證資料：

> **Stabilizing High-Occupancy Parking Systems via Legally Constrained Dynamic Assignment**

## Purpose / 目的
This directory is maintained exclusively for historical reproduction and baseline validation.
No T-ITS Experiment 1 development is performed inside this directory.
The T-ITS Experiment 1 simulator is developed separately under:

本目錄僅用於歷史實驗重現與基準驗證。
任何 T-ITS Experiment 1 的新功能開發，都不得在本目錄中進行。
T-ITS Experiment 1 simulator 於下列目錄中獨立開發：

```text
02_Exp1_FreeSearch_v2/
```

This separation prevents later research development from modifying or contaminating the historical ICCE baseline.

此種分離方式可避免後續研究開發修改或污染 ICCE 歷史基準版本。

---

## Frozen-Snapshot Rule / 凍結快照規則

The frozen snapshot directory must not be modified. The preserved snapshot is located at:

凍結後的 snapshot 目錄不得修改。保存的 snapshot 位於：

```text
01_ICCE_2026_Frozen/snapshot/sumo_parking/
```

Files inside the snapshot must remain unchanged so that the historical experiment can always be reproduced from the preserved implementation.
Any new validation, analysis, or reproduction script must be placed outside the frozen snapshot.

Snapshot 內的檔案必須維持原始狀態，以確保未來仍可使用保存的歷史實作重現原始實驗。
任何新增的驗證、分析或重現程式，都必須放在 frozen snapshot 之外。

For example:

```text
01_ICCE_2026_Frozen/validation/
```

---

## Original Archive / 原始封存檔

The original ICCE-TW simulation archive is stored at:

原始 ICCE-TW 模擬封存檔保存於：

```text
00_archive/sumo_parking_ICCE_2026_original.zip
```

This archive is the historical source of truth for reproduction checks.
The frozen snapshot should remain consistent with the contents recovered from this archive.

此封存檔為歷史重現驗證的原始依據。
Frozen snapshot 應維持與此 archive 中復原之內容一致。

---

## Original Scenarios / 原始實驗情境

The historical ICCE-TW experiment contains four scenarios:

```text
Free_85
Free_95
Assigned_85
Assigned_95
```

Their conceptual meanings are（概念意義）:

* `Free_85` — Free-search scenario at the historical 85% setting.（歷史實驗中 85% 設定下的自由搜尋情境）

* `Free_95` — Free-search scenario at the historical 95% setting.（歷史實驗中 95% 設定下的自由搜尋情境）

* `Assigned_85` — Assigned-parking scenario at the historical 85% setting.（`Assigned_85` — 歷史實驗中 85% 設定下的指派停車情境）

* `Assigned_95` — Assigned-parking scenario at the historical 95% setting.（`Assigned_95` — 歷史實驗中 95% 設定下的指派停車情境）

These names are preserved exactly for historical reproducibility.

上述 scenario 名稱應完整保留，以維持歷史實驗的可重現性。

---

## Random Seeds / 隨機種子

The historical experiment uses the following ten random seeds:

歷史實驗使用以下十個 random seeds：

```text
10
20
30
40
50
60
70
80
90
100
```

The same seed set must be used when reproducing the original ICCE-TW results.

重現原始 ICCE-TW 結果時，必須使用相同的 seed 集合。

---

## Reproduction Scope / 重現範圍

The purpose of this frozen baseline is to verify that the preserved simulator can reproduce the historical experimental outputs. The reproduction workflow may include:

本 frozen baseline 的目的，是驗證保存的 simulator 能否重現歷史實驗輸出。重現流程可包含：

```text
single-case validation（單一案例驗證）
single-scenario multi-seed validation（單一情境多 seed 驗證）
complete four-scenario / forty-run validation（四情境共 40 runs 完整驗證）
aggregate KPI comparison（彙總 KPI 比較）
archived-output comparison（歷史 archived output 比較）
```

Reproduction scripts and newly generated validation results may be stored under:

重現程式與新產生的驗證結果可保存於：

```text
01_ICCE_2026_Frozen/validation/
```

They must not overwrite or alter the frozen historical simulator itself.

這些驗證資料不得覆寫或修改 frozen historical simulator 本身。

---

## Development Boundary / 開發邊界

The ICCE frozen baseline and the T-ITS Experiment 1 simulator serve different purposes.

ICCE frozen baseline 與 T-ITS Experiment 1 simulator 具有不同用途。

```text
01_ICCE_2026_Frozen/
    Historical reproduction only（僅供歷史實驗重現）

02_Exp1_FreeSearch_v2/
    New T-ITS Experiment 1 development（T-ITS Experiment 1 新研究開發）
```

New mechanisms such as dynamic arrivals, lifecycle accounting, continuous free search, instability detection, and critical-load analysis must be implemented only in the Experiment 1 directory.

新的動態到達、生命週期帳務、持續式自由搜尋、失穩偵測與臨界負載分析等機制，只能在 Experiment 1 目錄中開發。

---

## Reproducibility Principle / 可重現性原則

The frozen ICCE baseline must remain a stable historical reference.
Do not modify the frozen simulator in order to make it agree with later interpretations, revised metrics, or new T-ITS experimental definitions.
Historical behavior should be documented as observed.
Any new correction, interpretation, or experimental redesign belongs in the T-ITS development branch rather than in the frozen baseline.


ICCE frozen baseline 必須維持為穩定的歷史參考版本。
不得為了配合後續研究詮釋、新版 metrics 或 T-ITS Experiment 1 的新實驗定義，而修改 frozen simulator。
歷史行為應依實際觀察結果如實記錄。
任何新的修正、研究詮釋或實驗重新設計，都應放在 T-ITS 開發版本中，而不是修改 frozen baseline。
