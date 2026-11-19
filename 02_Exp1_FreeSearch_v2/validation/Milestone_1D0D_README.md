# M1D-0D - Geometry Amendment & Entrance-Spillback Contract / 路網修訂與入口回堵量測規格

**Status:** `STATIC AUDIT ONLY; FORMAL STUDY HOLD`（僅靜態審查，正式實驗仍暫緩）

## Evidence already obtained / 已取得的工程證據

- M1D-0A original one-pass network has no revisit loop（原始單程路網沒有回訪迴路）
- M1D-0B `recirculation_v1` compiles, and the two-pass route probe passed（候選巡迴路網能編譯，兩圈行駛驗證通過）
- M1D-0C 2/2 vehicles parked and exited; `removed_error=0`, mass-balance error 0（兩車皆停妥離場，異常移除及帳務誤差皆為零）

The passed probes do **not** demonstrate search-induced gridlock and are not formal load experiments.

上述測試不構成搜尋誘發失穩證據，也不是正式負載實驗。

## Current limitation / 當前限制

`recirculation_v1` contains `E1/E2/E3` and the return loop `E_RU/E_RW/E_RD` but **no physically separate upstream entry edge**.

`N_entry_queue` (lifecycle), `N_outside` (pending demand/insertion), and a physically observed entrance queue are **different variables**.

A raw count of halted vehicles on `E1` is not sufficient to establish the SOP Event A, because `E1` also carries parking search traffic and traffic returning via `E_RD`.

`recirculation_v1` 具有原始停車道路與回程迴路，但**沒有獨立的上游入口道路**。

生命週期的 `N_entry_queue`、外部等待的 `N_outside`，以及實體入口道路上可觀察的隊列，是**不同變數**。

不能僅用 `E1` 上停住的車數證明 SOP Event A，因為 `E1` 同時承載搜尋車流與從 `E_RD` 回流的車流。

## Proposed Event A definition / 建議的 Event A 定義

The SOP specifies an entrance queue occupying at least **90% of usable access-link storage for at least 60 seconds**. The proposed operational implementation requires a **dedicated `E_IN` access link**.

SOP 指定入口道路排隊長度須達**可用儲車長度的 90%，且連續至少 60 秒**；建議使用**獨立 `E_IN` 入口道路**量測。

- `Q_entry_physical(t)`: number of stopped cars belonging to a **downstream-connected** queue on `E_IN_0`（實體入口連續停等車數）
- `L_queue(t)`: from downstream end to rear of the last car in that connected queue（從入口道路下游端至連續隊列尾車車尾的長度）
- `L_storage_usable`: actual access-lane length minus a justified upstream clearance（真正可用儲車長度，需扣除經合理說明的保留空間）
- `queue_coverage = min(1, L_queue/L_storage_usable)`（儲車空間占用比例）
- `Event_A = queue_coverage >= 0.90` sustained for `>=60 s`（連續至少 60 秒達到 90% 才屬 Event A）

`traci.lane.getLastStepHaltingNumber()` counts vehicles moving at less than 0.1 m/s, but **cannot by itself establish a spatially connected queue**. A future TraCI logger must combine per-vehicle lane positions, vehicle lengths and speeds, and then validate against SUMO GUI/trace observations.

The pure functions in `scripts/entrance_queue_contract.py` are a **proposal tested with synthetic lane data**, not validated measurements from the current candidate.

TraCI 的 halting number 使用車速小於 0.1 m/s 的標準，但**不能單靠停車數量證明隊列在空間上連續**。後續 logger 必須結合位置、車長與車速，並與 SUMO GUI / 軌跡人工核對。

`entrance_queue_contract.py` 僅為使用人工樣本驗證的**擬議量測函式**，不是當前路網已驗證的正式指標。

## Exit boundary / 離場邊界

`E3` route-end removal may remain a **proposed virtual exit sink** for cars whose parked → departing → completed events are verified. The 1D-0C probe supports this route mechanism, but the formal SOP must explicitly identify the virtual sink; unparked route-end events are not service completions.

`E3` 路線終點可暫作**虛擬出口邊界**候選，且只在經過 parked → departing → completed 時記為服務完成。1D-0C 已驗證路線機制，但正式 SOP 必須明示虛擬出口；未停車走到路線終點不可列為成功服務。

## Commands / 執行命令

From `C:\TITS_SmartParking\02_Exp1_FreeSearch_v2`:

```cmd
conda activate sumo_py310
cd /d C:\TITS_SmartParking\02_Exp1_FreeSearch_v2
python -m unittest discover -s tests -p "test_*.py"
python scripts\audit_m1d0d_gate.py
```

The audit only writes `validation/m1d0d/geometry_gate_summary.json` and `geometry_gate_checks.csv`. It does not change XML or re-run SUMO.

審查程式只輸出上述兩個驗證檔，不修改 XML，也不啟動 SUMO。

## Gate / 驗收門檻

- `Static integrity verdict: PASS` is expected if the candidate and canonical hashes match（雜湊與路網資料一致則靜態完整性通過）
- `Dedicated entry edge: NONE` is **expected for v1**, and is a documented deficiency（v1 沒有入口連結是已知缺口）
- `Formal geometry gate: HOLD` is the **correct** decision until entry instrumentation and SOP approval（未完成入口量測與 SOP 簽核前，正式路網仍應 HOLD）

A static-audit PASS **must not** be reported as approval to run formal load sweeps.

See `03_docs/M1D0D_SOP_Amendment_DRAFT.md` and `config/M1D0D_geometry_freeze_DRAFT.yaml` for proposed decisions. The latter is explicitly **not** a signed parameter freeze.

靜態審查 PASS **不等於**可以執行正式負載掃描。

詳見上述 SOP 修訂草案與 YAML 規格草案；YAML **不代表**已簽核的參數凍結。
