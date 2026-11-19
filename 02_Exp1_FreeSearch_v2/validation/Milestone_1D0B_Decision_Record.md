# M1D-0B Research Design Decision Record / 研究設計決策紀錄

**Decision status（決策狀態）:** `OPEN — CANDIDATE ONLY（待決策，僅候選路網）`

## Confirmed evidence / 已確認證據

- M1D-0 tests passed `29/29`, with static audit `PASS` and `HOLD_NO_REVISIT_LOOP`.（M1D-0 已通過 `29/29`，靜態稽核 `PASS`，但因無回訪迴路而為 `HOLD_NO_REVISIT_LOOP`）
- Canonical directed edges: `E1 -> E2 -> E3`, no directed cycle.（原始路網僅有 `E1 -> E2 -> E3`，不存在有向迴路）
- Original parking inventory: seven parking areas, 200 physical spaces, general-vehicle effective capacity 170.（原始容量為 7 個停車區、200 格實體車位、170 格一般車輛合法容量）
- ICCE historical free-search reads live zone parking counts and uses top-two candidates with acceptance draws.（ICCE 歷史自由搜尋使用即時跨區停車量、前兩名候選分區與接受機率抽樣）

## SOP alignment / 與 SOP 的相容性

The v2.0 SOP §4.1 fixes the ICCE geometry in Experiment 1-Core, while §4.2 requires the perceived-scarcity information regime to be documented. Changing the road into a loop necessarily departs from the literal same-geometry condition.

v2.0 SOP §4.1 要求 Experiment 1-Core 固定 ICCE 幾何，§4.2 則要求資訊來源清楚記錄。新增實體回程路段必然偏離「完全相同路網幾何」的原規定。

**Research options（研究選項）：**

A. **Canonical one-pass baseline（原始單程基準）** — retains source geometry; cars can try multiple parking areas along the road but cannot revisit earlier zones. Not equivalent to multi-lap continuous free-search.（忠實維持原路網，可嘗試沿途不同區域，但無法重新經過較早分區；不能稱為多圈持續式自由搜尋）

B. **Versioned recirculation geometry（版本化巡迴路網）** — allows real revisitation but changes physical topology, total road length, junctions, merging, and possible spillback mechanisms; requires explicit SOP amendment and renewed validation.（允許實體再次搜尋，但同時改變道路拓撲、總里程、路口匯流與可能的回堵機制；必須修訂 SOP 並重新驗證）

## Current recommendation / 目前建議

Build **Option B as a non-formal feasibility candidate only**, not as a silent replacement of the canonical network. Preserve Option A for historical geometry and as a potential one-pass reference.

A validated loop alone is not sufficient to freeze the new network. Before the proposed geometry becomes an Experiment 1 condition, document its influence on speed, per-lap distance, entrance/return merge, queue storage, parking accessibility, and the C1/C2 detector. Record a separately approved SOP change and re-run relevant M1A–M1C checks using the new network.

先把**方案 B 當成非正式可行性候選**，絕不悄悄取代 canonical；方案 A 仍保留作原始幾何與單程參考。

即使路網可繞行，也不能直接凍結為正式研究場域。需先檢查速度、單圈距離、入口 / 回程匯流、入口儲車空間、停車位可達性與 C1/C2 偵測規則，再經 SOP 變更簽核，並在新路網上重跑受影響的 M1A～M1C 驗證。

**No high-load runs, critical-load claims, or controller comparisons are authorized at M1D-0B.**
**M1D-0B 不得執行正式高負載掃描、宣稱臨界負載，或進行控制器比較。**

## Next sign-off questions / 後續簽核議題

- Can the extra perimeter travel and merge geometry be justified as a physically meaningful parking-site circulation system?（新增回程里程與匯流是否能代表合理的停車場巡迴道路？）
- Which topology is the primary Experiment 1-Core layout after SOP amendment?（SOP 修訂後哪一套路網才是正式主實驗路網？）
- How will non-searching background traffic and geometry-only congestion be distinguished from search-induced congestion?（如何透過對照實驗區分幾何本身壅塞與搜尋行為誘發壅塞？）
- Will the ICCE live-zone information regime be retained, or will a separately labeled local-information sensitivity study be added?（是否保留 ICCE 跨區即時資訊，或另外設置明確標示的局部資訊敏感度研究？）

## Sign-off

- Candidate topology and route probe（候選拓撲與路線測試）
- Revised geometry and mechanism validation（修改後幾何與機制驗證）
- SOP amendment approval（SOP 變更核准）
- Authorization for M1D-1 behavior implementation（M1D-1 行為模型實作核可）
