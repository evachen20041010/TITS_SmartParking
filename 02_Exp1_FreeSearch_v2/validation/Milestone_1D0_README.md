# Milestone 1D-0 - Free-Search Feasibility Audit / 自由搜尋可行性審查

## Purpose / 目的

This milestone validates whether the **existing, frozen canonical network** can physically support repeated visits to parking areas, and documents the information regime of the reproduced ICCE free-search baseline. It does **not** implement a search algorithm, run SUMO, or modify the network.

本階段確認**既有且已凍結的標準路網**是否能讓車輛重訪停車區，並紀錄已重現之 ICCE 自由搜尋基準模型使用的資訊來源。此階段**不會**實作搜尋演算法、執行 SUMO 或修改路網。

## Sources / 依據

- `network/canonical/parking_lot.net.xml`: actual SUMO connections / 實際 SUMO 連接關係。
- `network/canonical/parking_areas.add.xml`: parking IDs, legal capacities / 停車區與合法容量。
- `validation/network_summary.json`: previously validated capacity / 已通過驗證的容量。
- `01_ICCE_2026_Frozen/snapshot/sumo_parking/run_simulation.py` (repository-relative): frozen free-search behavior / 凍結的 ICCE 自由搜尋行為。
- `03_docs/20260920_IEEE_Trans_ITS_Experiment1_v2_SOP.pdf`, Sections 4.1, 4.2, Appendix A: geometry and information-freeze constraints / 路網與資訊假設的凍結要求。

## How to run / 執行方式

From `C:\TITS_SmartParking\02_Exp1_FreeSearch_v2`:

```cmd
python tests\test_m1d0_topology.py
python scripts\audit_m1d0_feasibility.py
```

The script uses only Python's standard library. SUMO and TraCI are not launched.

程式只使用 Python 標準函式庫，不啟動 SUMO 或 TraCI。

## Expected assessment for the uploaded canonical model / 既有路網的預期判定

```text
Canonical edges              : E1, E2, E3
Connections                  : E1->E2, E2->E3
Any directed cycle           : False
Revisitable parking areas    : []
Legal general spaces         : 170
Network capacity cross-check : PASS
ICCE live zone counts        : True
ICCE top-two candidates      : True
ICCE acceptance draw         : True
Static audit                 : PASS
1D search implementation    : HOLD_NO_REVISIT_LOOP
```

`Static audit: PASS` means the audit executed correctly and matched the canonical source. **It does not mean the continuous free-search simulator is ready.** The physical ability to revisit parking areas is currently absent.

The original ICCE baseline calls `traci.parkingarea.getVehicleCount()` while ranking all three zones. This is **cross-zone live occupancy information**. It must not silently be reinterpreted as uninformed/local-only search.

`Static audit: PASS` 表示審查程式正常執行、結果與來源一致，**不代表持續式自由搜尋模擬器已準備完成**。現有路網無法重訪已經經過的停車區。

ICCE 原始程式評分三個分區時會呼叫 `traci.parkingarea.getVehicleCount()`，因此使用了**跨區即時占用資訊**。不得在未經說明的情況下，將它重新描述成無資訊／僅局部觀察的搜尋模型。

## Decision gate / 研究決策關卡

| Design option / 方案 | Scientific status / 研究效力 | Decision / 建議 |
| --- | --- | --- |
| A. Preserve one-way geometry; forward-only searches / 保留單向路網，只能向前搜尋 | Keeps SOP physical geometry but cannot revisit passed zones / 符合原幾何，但無法回訪 | Valid as a *finite-pass benchmark*, not as repeated-loop continuous search / 可作單次通行比較組，不應宣稱多輪巡航 |
| B. Create a **versioned** network with explicit return connections / 建立具回程道路的新版本路網 | Enables recirculation, **changes original ICCE geometry** / 可巡迴，但改變 ICCE 原始幾何 | Recommended only after a documented SOP addendum and fresh validation / 建議經 SOP 變更審核並重驗後採用 |
| C. Remove/reinsert vehicles to simulate returning / 移除再插入車輛模擬回程 | Hides time, space and congestion costs / 隱藏回程時間、距離與交通互動 | Not recommended as the formal baseline / 不建議用於正式基準 |

**Recommended research treatment:** preserve the existing canonical network and ICCE freeze unchanged. Prepare a versioned, physically explicit network alternative for a later controlled feasibility test, not an immediate replacement. A revised primary geometry needs a documented SOP departure, capacity/topology checks, run-manifest changes, and re-validation of integration tests.

**建議處理方式：** 保留既有 canonical network 與 ICCE 凍結檔案；另以版本化方式提出「具有實際回程道路」的候選路網，待方法學審核後再進行小型可行性測試，不直接覆蓋原始檔案。若更動正式研究使用的幾何，必須留下 SOP 變更說明、容量與拓撲檢查、manifest 修訂，以及受影響的整合測試重驗證。

## Research boundaries / 研究界線

**Do not proceed to formal load sweeps or `rho_50` estimates at this stage.** Continuous-search behavior, the information/perception rule `O_hat_iz`, route-failure accounting, parking rejection, occupancy checks, and C1-versus-C2 detector have not yet been verified.

Per SOP v2.0, retain the distinction between `rho` (offered load) and observed occupancy, and between C1 search-induced gridlock with eligible vacancies and C2 capacity-induced blockage.

**此階段不得開始正式負載掃描或估計 `rho_50`。** 持續搜尋行為、資訊感知規則 `O_hat_iz`、路線失敗記帳、停車拒絕、空位檢查，以及 C1/C2 失穩判定均尚待驗證。

依 SOP v2.0，`rho`（外生需求負載）不得視為實測占用率；C1 需與仍有合法空位的搜尋失穩相關，C2 則為合法容量耗盡下的阻塞，兩者不可混用。

## Outputs / 輸出

```text
validation/m1d0/
├─ feasibility_audit.json
└─ network_adjacency.csv
```

These artifacts record source SHA-256 values and the geometry/information checks. They are evidence for the *decision gate*, not simulation outcomes.

以上檔案保留來源 SHA-256 與路網／資訊檢查紀錄；它們是**研究決策依據**，不是 SUMO 模擬結果。
