# Milestone 1D-0C — Recirculation vs Exit / 巡迴與離場路線驗證

**Status：NON-FORMAL TECHNICAL PROBE（非正式技術驗證）**

This is a route/parking lifecycle probe on the versioned candidate `recirculation_v1`. It does not implement bounded-rational free search, estimate gridlock, or authorize formal experiments.

本測試使用版本化候選路網 `recirculation_v1`，只驗證路線分支與停車生命週期。不代表已實作有限理性自由搜尋，也不能用於 gridlock 判定或正式實驗。

## Question / 核心問題

Can a vehicle that successfully parks leave directly after its stop, while a vehicle that does not park on the first pass makes a second pass, parks, and then leaves?

成功停車者能否在停車時間結束後直接離場，而首次未停車者可繼續第二圈、停妥後再離場？

## Diagnostic Cases / 測試情境

| Vehicle / 車輛 | Action / 動作 | Expected observed edges / 預期道路順序 |
|---|---|---|
| `early_park` | Park on pass 1, shorten the remaining route on departure / 第一圈停車，離場時縮短路線 | `E1 E2 E3` |
| `late_park` | Skip pass 1, park on pass 2, then exit / 第一圈不停車，第二圈停車並離場 | `E1 E2 E3 E_RU E_RW E_RD E1 E2 E3` |

Both initially have the same two-pass route. The parking target is `PA_Z2_G` with a fixed diagnostic stop duration of 12 seconds.

兩台車起初具有相同的雙圈路線；固定停車區為 `PA_Z2_G`，固定停車時間 12 秒僅供技術測試。

## Design Boundaries / 設計界線

- The existing canonical files and the candidate network files are never modified.（不修改 canonical 或候選路網檔案）
- Normal completion requires the full `parked → departing → completed` chain.（正常完成必須經過停車、離場及完成的完整狀態轉移）
- A SUMO route end without prior parking must not be counted as a successful parking service.（沒有成功停車就走到路線終點，不得計入停車服務完成）
- SUMO `setRoute` is called only on the current road edge, after parking ends.（停車結束後，且目前車輛仍位於道路上，才以當前道路為起點更新路線）
- `HOLD_SOP_AMENDMENT_REQUIRED` remains in force even if the probe passes.（測試通過仍不等於幾何變更已取得正式 SOP 核准）

## Execution / 執行

Run from `C:\TITS_SmartParking\02_Exp1_FreeSearch_v2` in the `sumo_py310` environment.

```cmd
python -m unittest discover -s tests -p "test_*.py"
python scripts\run_m1d0c_exit_probe.py --precheck
python scripts\run_m1d0c_exit_probe.py
```

Expected unit-test total after installing these five tests: `43` (previous `38` + new `5`).

加入本次五個測試後，預期為 `43` 個單元測試（原先 `38` + 本次 `5`）。

## PASS Criteria / 通過條件

- Two vehicles parked and normally exited（兩台車都停車後正常離場）
- First-pass vehicle did not use return edges（第一圈停車者不走回程道路）
- Second-pass vehicle visited the return loop and re-entered `E1`（第二圈停車者實際繞行並回訪 `E1`）
- `parked_route_indices = {"early_park": 1, "late_park": 7}`（停車時的路線索引符合預期）
- `removed_error = 0` and `max_abs_mass_balance_error = 0`（異常移除與車輛質量平衡誤差皆為零）
- No route-end-without-parking is accepted as a normal completion（不將未停車的路線結束誤計成正常完成）

## Outputs / 輸出

```text
validation/m1d0c/
├─ route_audit.csv
├─ vehicle_events.csv
├─ system_log.csv
└─ summary.json
```

Only after this probe is successful should the project decide whether a separately amended recirculating geometry is methodologically appropriate for Experiment 1-Core.

只有本項驗證成功後，才進一步決定是否將經過正式 SOP 變更的巡迴路網納入 Experiment 1-Core。

## Validation Status / 驗證狀態

Technical validation: PASS / 技術驗證通過

Validation environment: Windows, sumo_py310
Validation date: 2026-11-17

Unit tests: 43/43 PASS
SUMO route probe: PASS
Completed vehicles: 2/2
Removed error: 0
Maximum mass-balance error: 0

Evidence:
validation/m1d0c/summary.json

Formal Experiment 1 approval:
HOLD_SOP_AMENDMENT_REQUIRED

The technical validation is complete, but formal use of the modified geometry requires an approved SOP amendment.

技術驗證已完成，但修改後的路網仍須經 SOP 研究方法修訂核准，才能納入正式 Experiment 1。
