# M1D-0B — Proposed SOP Geometry Amendment / SOP 路網幾何修正提案

**Status: DRAFT — NOT APPROVED（草案）**

## 1. Original SOP constraint / 原始 SOP 限制

Experiment 1 v2.0, §4.1, specifies one fixed canonical layout inherited from the ICCE-TW geometry and states that layout, lane geometry and other design factors should not be changed within the Experiment 1-Core load comparison.

Experiment 1 v2.0 SOP 第 4.1 節要求固定並沿用 ICCE-TW 的 canonical layout，正式 Core 不得在負載比較過程中任意改變路網與車道幾何。

## 2. Engineering observation / 工程發現

The original route is `E1 → E2 → E3` (600 m, no directed revisit cycle). This permits parking followed by normal route completion but cannot support a second pass to a previously visited zone.

The versioned `recirculation_v1` candidate adds `E_RU (60 m)`, `E_RW (600 m)` and `E_RD (60 m)`. A complete circuit is 1,320 m. It preserves seven parking areas, `C_total=200`, and `C_eff=170`. The user's 2026-11-17 Windows SUMO probe confirmed two visits to E1/E2/E3.

原始路線長 600 公尺，能停車後正常離場，但沒有回訪先前分區的有向迴路，無法實現多圈搜尋。

候選路網新增三段共 720 公尺回程道路，單圈長 1,320 公尺；七個停車區、總容量 200 與一般合法容量 170 均維持不變。2026-11-17 的 Windows SUMO 測試已確認車輛可以回訪原始三條停車道路。

## 3. Research threats / 研究有效性風險

1. **Network confounding / 幾何混雜：** added distance and junctions alter travel time, circulating density and possible spillback independently of behavioral search.（增加道路與路口可能獨立影響巡航密度、旅行時間與回堵）
2. **Entrance spillback / 入口回堵：** J0 is used for recirculation via `E_RD → E1`, but new demand is inserted directly on E1. This does not yet define a separate physical upstream entrance link/queue required for a defensible Event A detector.（目前缺乏獨立、具有可核對容量的入口等待連結，尚不能直接據此測量正式 Event A）
3. **Exit semantics / 離場機制：** ending a route at E3 removes a car from SUMO even though E3 also connects to the return loop. Whether this abstract sink is an acceptable modeled exit must be declared, or a separate exit edge should be versioned and assessed.（E3 可當作模擬邊界出口；是否接受此抽象邊界，或增設實體出口道路，需先做設計決策）
4. **No-parking route end / 未停車直接離場：** a route completion without a parked event must never count as parking success; unresolved searches should be tracked or right-censored at the defined horizon.（未停妥的車輛不得因抵達路線終點而被列為成功停車）
5. **Information regime / 駕駛資訊：** frozen ICCE `get_zone_score` uses live cross-zone parking counts. The new continuous-search information assumption must be documented explicitly and cannot silently become perfect or zero information.（ICCE 使用即時跨分區車位數；M1D-1 必須明確記錄資訊來源與更新規則）

## 4. Recommended conditional design / 建議條件式設計

- Preserve `network/canonical/` and the ICCE frozen archive unchanged.（原始路網及 ICCE 凍結檔案不動）
- Keep `recirculation_v1` as a separate versioned candidate for **engineering** probes.（候選路網僅供工程驗證）
- Complete M1D-0C: verify first-pass parking → exit and first-pass miss → second-pass parking → exit on the same candidate.（完成雙分支車輛路線驗證）
- Before formal load sweeps, choose and document an entrance-queue measurement definition and exit boundary model, then freeze an amended network revision.（正式負載掃描前決定入口排隊與出口邊界定義，凍結修正版路網）
- Keep one fixed topology and behavior distribution across all offered loads; do not mix the original and amended network results in a single critical-load fit.（不同負載使用同一凍結幾何，不得混合不同幾何結果估計單一臨界負載）
- Preserve an original-geometry baseline as a separately labeled comparison or sensitivity experiment, if needed.（原始幾何若保留，僅作明確標示的對照或敏感度分析）

## 5. Sign-off gate / 核准門檻

This proposal **does not authorize Stage A/B formal runs**. Formal use requires a documented amended SOP/version, validated entry and exit semantics, completed parking-search behavior tests, detector QC, parameter freeze and supervisor approval.

本提案**不授權正式 Stage A/B 批次實驗**。正式採用前必須具備修訂版 SOP、經驗證的出入口機制、搜尋行為測試、detector QC、參數凍結及研究指導者簽核。

- Accept a versioned recirculation geometry for Experiment 1-Core（核准正式 Core 使用新版巡迴路網）
- Freeze geometry and hash（凍結路網與雜湊）
- Define entry storage, exit boundary and queue metrics（定義入口容量、離場邊界與排隊量測）
- Verify no silent departure of unparked vehicles（驗證未停妥車輛不會被錯列完成）
- Approve M1D search behavior and information source（核准搜尋行為與資訊來源）
- Approve formal-batch readiness separately（另行核准正式實驗批次）
