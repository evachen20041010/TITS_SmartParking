# Milestone 1D-0E — Dedicated Entry and Return Merge / 獨立入口與巡迴匯流驗證

**Status：NON-FORMAL CANDIDATE — WINDOWS SUMO PROBE PENDING（非正式候選，待 Windows SUMO 實測）**

## 1. Research purpose / 研究目的

Create a **separately versioned** access approach `E_IN` for new arrivals without modifying the canonical or `recirculation_v1` networks. Establish that the SUMO junction J0 accepts both `E_IN → E1` and `E_RD → E1`, and gather raw entry-lane observations for the next queue-calibration milestone.

建立**獨立版本**的入口道路 `E_IN`，供新到達車輛使用，且不更動 canonical 或 `recirculation_v1`。核對 SUMO 的 J0 路口同時接受 `E_IN → E1` 與 `E_RD → E1`，並保留入口車道原始資料，以便後續校準實體排隊指標。

**This milestone does not validate entrance spillback Event A, bounded-rational search, or gridlock C1/C2.（本關不代表 Event A 入口回堵、有限理性搜尋或 C1/C2 壅塞判定已獲驗證）**

## 2. Network geometry / 候選路網幾何

| Element / 項目 | Engineering candidate / 工程候選 |
|---|---|
| Version / 版本 | `network/candidates/recirculation_v2_entry/` |
| New node / 新節點 | `J_IN=(-150, 0) m` (provisional / 暫定) |
| New edge / 新道路 | `E_IN: J_IN → J0`, nominal 150 m, 1 lane, 13.89 m/s / 名目 150 公尺，單車道 |
| External arrivals / 外部新到達 | `E_IN → E1 → E2 → E3` |
| Returning searches / 巡迴車 | `E3 → E_RU → E_RW → E_RD → E1` |
| Virtual exit / 抽象出口 | End of route on E3 **after successful parking**, unchanged from 1D-0C / 成功停車後於 E3 路線終點離場 |
| Parking / 停車區 | 7 areas, total 200; legally eligible general 170 / 7 區、總計 200、一般車合法 170 |

`E_IN=150 m` is a **diagnostic candidate value** and is **not** a signed or calibrated storage length. The effective usable entrance storage (`L_usable`), queue-gap tolerance, and physical Event A detection are **not yet frozen**.

`E_IN=150 m` 僅為**工程測試用暫定長度**，不是已簽核或校準的儲車空間。有效入口儲車長度 `L_usable`、車距容許值與 Event A 的實體量測方式**尚未凍結**。

## 3. Installation / 安裝

Extract the M1D-0E patch ZIP into `C:\TITS_SmartParking\` using relative paths as packaged. It adds only two scripts, two tests, and research documentation; it does **not** replace any previously validated network or program.

將 M1D-0E 修補包依既有相對目錄解壓至 `C:\TITS_SmartParking\`。本次僅新增兩個程式、兩個測試檔及研究文件；**不覆蓋**原有已驗證的程式或路網。

## 4. Windows execution / Windows 執行順序

```cmd
conda activate sumo_py310
cd /d C:\TITS_SmartParking\02_Exp1_FreeSearch_v2

python -m unittest discover -s tests -p "test_*.py"
where netconvert
python scripts\build_m1d0e_entry_candidate.py
python scripts\run_m1d0e_entry_probe.py --precheck
python scripts\run_m1d0e_entry_probe.py
```

Expected unit tests after correct patch installation: **69** (53 existing + 16 new). The new scripts can perform a source-only geometry build with `--static-only`, but that option does **not** compile a drivable SUMO network.

修補包正確安裝後，預期單元測試數為 **69**（原有 53 + 新增 16）。路網產生程式亦支援 `--static-only` 進行純來源檢查，但此選項**不會**建立可行駛的 SUMO 編譯路網。

## 5. Technical probe / 技術驗證情境

| Vehicle / 車輛 | Behavior / 固定診斷行為 | Expected observed route / 預期行駛路徑 |
|---|---|---|
| `early_park` | Entry; park on first pass, shorten to E3 on exit / 入口進場、第一圈停車後直接離場 | `E_IN E1 E2 E3` |
| `late_park` | Entry; skip first pass; return via E_RD; park second pass / 入口進場、第一圈不停、經回程道路、第二圈停車 | `E_IN E1 E2 E3 E_RU E_RW E_RD E1 E2 E3` |
| `fresh_at_merge` | Another external arrival near the expected return window; park first pass / 於巡迴回流附近時段增加新車，第一圈停車 | `E_IN E1 E2 E3` |

All three stop at general-use `PA_Z2_G` with a **12-second diagnostic duration only**. The expected **route indices at the parked edge E2** are `{"early_park": 2, "late_park": 8, "fresh_at_merge": 2}`. They differ from M1D-0C because the new entry edge adds one route index.

**Important：** The timing of `fresh_at_merge` is an attempted overlap, **not a proof of simultaneous conflicting arrivals**. A PASS only verifies both J0 approaches in one SUMO run, without collision or teleportation. Controlled merge-conflict and sustained physical queue tests remain pending.

三輛車均於一般合法停車區 `PA_Z2_G` 停車，**固定 12 秒僅為工程測試**。預期 E2 停車路線索引為 `early=2, late=8, fresh=2`；相較 1D-0C，多了一段 `E_IN`，因此索引各加一。

`fresh_at_merge` 的加入時間只是嘗試使新車與回流車接近，**並不保證兩車同時發生衝突式匯流**。PASS 僅證明兩種 J0 進場路徑能在同一次 SUMO 模擬中通過且沒有碰撞 / 傳送；控制式匯流衝突與持續實體排隊測試仍待後續執行。

## 6. Acceptance gates / 驗收門檻

- **Static builder（靜態生成）：** Original XML and hashes unchanged; `netconvert` succeeds; compiled `E_IN → E1` and `E_RD → E1` exist; J0 has both incoming lanes（原始來源雜湊未變、編譯成功、兩條進場連接均存在）
- **Actual SUMO（實際模擬）：** Three vehicles physically park and exit; the return vehicle truly revisits E1; only first-pass vehicle with full two-pass route is shortened on exit（三車停妥離場、回流車真正回訪 E1、早停車輛縮短路線）
- **Data integrity（資料完整性）：** `completed=3/3`, `removed_error=0`, `max_abs_mass_balance_error=0`, `collisions=0`, `teleports=0`（完成率、質量平衡、碰撞與傳送皆須符合標準）
- **Raw physical observations（原始入口觀測）：** Emit `entry_lane_raw.csv` and `entry_lane_timeseries.csv`, including empty-lane timesteps（須輸出車輛原始位置與每秒車道統計（含無車時間點））
- **Research authorization（正式核准）：** Always `HOLD_SOP_AMENDMENT_REQUIRED` pending revised SOP, approved geometry, physical queue calibration and driver-behavior freeze（SOP 修訂、正式幾何、入口儲車量測及駕駛模型尚未完成前一律維持 HOLD）

If the vehicle has not parked, arriving at the E3 route end **must not** count as a successful parking service. A collision, teleport, or abnormal removal fails this diagnostic, even if some vehicles arrived.

若車輛未停妥便抵達 E3 路線終點，**不得**計入停車服務完成。即使部分車輛正常抵達，只要有碰撞、傳送或異常移除，本關仍判 FAIL。

## 7. Evidence / 驗證檔案

The candidate is generated in `network/candidates/recirculation_v2_entry/`, with `candidate_manifest.json`, source hashes and compiled network hash. The test writes:

候選路網建立於 `network/candidates/recirculation_v2_entry/`，包含 `candidate_manifest.json`、來源雜湊及編譯網路雜湊；實測輸出位置為：

```text
validation/m1d0e/
  entry_probe_summary.json
  route_audit.csv
  vehicle_events.csv
  system_log.csv
  entry_lane_raw.csv
  entry_lane_timeseries.csv
```

`entry_lane_raw.csv` contains TraCI front positions, speeds and lengths. `entry_lane_timeseries.csv` records lane counts and halted vehicle numbers at every step. **Neither is a validated Event A detector**, and a high raw lane occupancy is not automatically a 90%-for-60-second spillback event.

`entry_lane_raw.csv` 紀錄 TraCI 車頭位置、車速與車長；`entry_lane_timeseries.csv` 每步保存車道車數與停車車數。**兩者目前都不是已驗證的 Event A 偵測器**，車道高占用也不自動等於符合 90% / 60 秒的實體回堵事件。

## 8. Research boundaries / 研究限制

This proposal is a physical-geometry amendment to SOP v2.0 §4.1, not a reproduction of unchanged ICCE geometry. Merge-priority effects, added entrance travel time, entrance storage, and possible geometry-only congestion require additional validation. Do not mix canonical and revised-geometry runs in one critical-load curve.

本方案新增入口路段，屬 SOP v2.0 第 4.1 節的實體幾何變更，不能視為完全未變更的 ICCE 幾何重現。匯流優先權、入口額外行駛時間、儲車容量及單純由幾何誘發的壅塞，都需另行驗證；不得混合不同幾何的數據來擬合同一條臨界負載曲線。

**Technical success is not formal-study approval.（工程測試成功不代表正式研究已核准）**
