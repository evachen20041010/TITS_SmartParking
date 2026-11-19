# Milestone 1D-0 - Research Decision Memo / 自由搜尋模型研究決策備忘錄

**Status：STATIC AUDIT PASS；CONTINUOUS-SEARCH MODEL DESIGN ON HOLD（靜態審查完成；持續式搜尋模型設計待決策）**

## 1. Primary question / 核心問題

Can an agent reject or fail a parking attempt and then legally reach a previously passed eligible parking zone again, while the road and parking states remain part of the microscopic SUMO traffic simulation?

當車輛拒絕停車位或搜尋失敗時，能否在 SUMO 路網中，透過實際合法的道路移動重新抵達已經過的停車分區，同時保留完整交通與車位占用狀態？

## 2. Evidence from source / 來源證據

`parking.edg.xml` defines three directed edges: `E1: J0->J1`, `E2: J1->J2`, and `E3: J2->J3`. The net file contains only `E1->E2` and `E2->E3` non-internal connections. `J3` is a `dead_end`.

`parking_areas.add.xml` defines general capacities `40 + 50 + 80 = 170`, family `20`, disabled `10`; total `200`. A geometry change must not silently change these counts.

The frozen `run_simulation.py` uses `get_zone_score()` with current parking-area vehicle counts, computes `occ_proxy=1/(max(available_spots,0)+1)`, ranks zones, uses two leading candidates and per-driver acceptance probability, and sets one parking-area stop when the selection is eligible. A periodic decision loop or a route for returning to an earlier zone is not implemented in the reviewed code.

`parking.edg.xml` 僅有三條有向道路；`parking_lot.net.xml` 僅有兩項非內部道路連接，`J3` 為 `dead_end`。因此不存在回訪任何已經經過的停車區的有向迴路。

`parking_areas.add.xml` 中一般車位共 `170`、親子車位 `20`、身障車位 `10`，總計 `200`；任何幾何調整皆不可未經確認就改變車位容量。

凍結的 `run_simulation.py` 透過 `get_zone_score()` 使用即時停車數量計算占用代理值 `occ_proxy`，依評分排序，並採前兩名候選及個別駕駛接受機率；合法且判定有位時設定一次停車命令。審查的程式中並未實作「搜尋失敗後週期性重新決策並回訪前面分區」的機制。

## 3. SOP constraint and conflict / SOP 限制與衝突

SOP v2.0 Section 4.1 requires one canonical layout based on ICCE geometry, while Section 4.2 requires the perceived-scarcity source to be identified and prohibits secretly weakening information to create a transition. The current physical geometry and a repeated-loop free-search model cannot both be assumed valid without explicitly resolving this conflict.

SOP v2.0 第 4.1 節要求沿用 ICCE 標準幾何，第 4.2 節要求說明感知稀缺度資訊的來源，且不可為了製造失穩而暗中弱化資訊。**目前這個單向幾何，與多輪回訪式自由搜尋的需求存在設計衝突，必須明確決策。**

## 4. Proposed next engineering gate / 建議下一個工程關卡

Before implementing `free_search.py`, create a **versioned topology proposal** separate from `network/canonical`. Specify possible return-edge connections; re-check edge adjacency and legal capacity; model actual return travel and road-queue interactions; and record changes to the SOP and simulation manifest.

Do **not** immediately overwrite the frozen network, insert artificial TraCI remove/reinsert loops, or claim instability based on results from a dead-end geometry.

在實作 `free_search.py` 前，應於 `network/canonical` 之外建立**版本化的拓撲候選方案**，明列回程道路、實際回程時間及交通交互作用，再核對道路連接與合法容量，並記錄對 SOP 與實驗 manifest 的變更。

**目前不要**覆蓋已凍結路網、用 TraCI 移除再插入車輛模擬巡迴，或把死路結構下的阻塞直接解釋成搜尋引發的失穩。

## 5. Required sign-off before M1D-1 implementation / 開始 M1D-1 前的核准項目

- Geometry decision / 幾何決策：有限單次通行模型，或經 SOP 升版後的具回程拓撲。
- Information decision / 資訊決策：維持 ICCE 的跨區即時占用資訊，或另列已核准、清楚命名的替代感知情境。
- Rejection and retry semantics / 搜尋失敗語意：何種事件代表拒絕、何時重新抽樣、何時重新選區。
- Terminal/censoring rule / 終止與設限：未停車就抵達路線終點不得誤算為成功搜尋。
- Logging and QA / 記錄與品管：停車資格、空位、佇列、重新搜尋次數、質量平衡、route failures、C1/C2 分類。

The static audit **does not** approve these design choices and does not change the experimental hypotheses.

靜態審查**不代表已核准以上設計選項**，也不變更原研究假設。
