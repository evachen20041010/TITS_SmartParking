# Experiment 1 — M1D-0D Geometry Amendment and Entrance-Queue Measurement Proposal / 路網幾何修訂暨入口排隊量測提案

**Document class（文件性質）:** Research-methods amendment *draft*（研究方法修訂草案）
**Decision（決策）:** `PROPOSED_NOT_APPROVED`（尚未核准）
**Original authority（原始依據）:** `20260920_IEEE_Trans_ITS_Experiment1_v2_SOP.pdf` (§4.1, §4.2, §6, §7, Appendix A/B)  
**Candidate under review（候選路網）:** `recirculation_v1`  
**Date（日期）:** 2026-11-18

## 1. Purpose / 目的

The initial SOP fixes a single ICCE-derived geometry. We now have engineering evidence that the canonical one-pass route cannot physically revisit parking zones, whereas a versioned return-loop candidate can. This document records the proposed deviation before selecting a geometry for the actual continuous-search and C1/C2 experiments. It does not alter the signed original SOP.

初版 SOP 要求固定並沿用 ICCE 的單一路網。目前工程驗證證明，原始單程道路無法實體回訪較早的停車分區，版本化回程候選則可以。本文件在正式選定持續搜尋及 C1/C2 實驗路網前，先記錄可能偏離原 SOP 的變更理由；**不直接改寫原始 SOP**。

## 2. Evidence and unchanged research boundaries / 已有證據與不變的研究界線

| Evidence / 證據 | Verified result / 已驗證結果 | Implication / 意涵 |
|---|---|---|
| Canonical geometry / 原始幾何 | `E1 → E2 → E3`, 600 m, no directed cycle | One-pass reference only / 僅可作單次搜尋基準 |
| M1D-0B technical route probe / 技術路線測試 | `E1 E2 E3 E_RU E_RW E_RD E1 E2 E3` | Physically revisitable / 可實體回訪 |
| Candidate perimeter / 回程通道 | `E_RU=60 m`, `E_RW=600 m`, `E_RD=60 m` | +720 m and additional junctions / 幾何變更不可忽略 |
| Parking inventory / 車位清冊 | 7 areas, 200 total, 170 general-eligible | Legal capacity preserved / 合法容量不變 |
| M1D-0C two-branch live SUMO probe / 雙分支模擬 | 2/2 parked and normally exited; zero removal and mass-balance errors | Route mechanics work, but behavior not yet modeled / 路線機制成立，尚非行為模型 |

The historical ICCE baseline remains frozen. No official offered-load runs have been conducted on the new candidate, and no critical-load or search-induced gridlock claim follows from these probes.

ICCE 歷史基準仍維持凍結。新候選路網尚未做正式 offered-load 實驗，這些技術測試不能用來宣稱臨界負載或搜尋誘發失穩。

## 3. Proposed geometry lineage / 建議路網版本關係

| ID | Role / 角色 | Status / 狀態 |
|---|---|---|
| `canonical` | Original ICCE-compatible one-pass geometry / 原始單程幾何 | PRESERVED; never overwrite / 永久保留 |
| `recirculation_v1` | Validated physical return-loop feasibility candidate / 已驗證回程技術候選 | ENGINEERING PASS; not formal / 工程通過，非正式 |
| `recirculation_v2_entry` | *Proposed only*: add a dedicated measurable access approach / 擬議加上可量測入口道路 | NOT BUILT; requires engineering checks / 尚未建立 |

For the proposed `recirculation_v2_entry`, introduce an upstream access edge `E_IN` from a new upstream boundary node to `J0`, while retaining `E_RD → J0 → E1` for recirculating traffic. All new external arrivals enter via `E_IN`; recirculating vehicles must never be routed through `E_IN`. Keep `E1/E2/E3` parking locations and the reserved-space configuration unchanged. This approach makes the source of external arrivals spatially distinguishable from recirculation.

Exact `E_IN` length, lane geometry, vehicle type, clearances, and merge priority are **not chosen here**. These are research parameters which affect queue storage and gridlock, and must be justified and frozen before experiments. Any new candidate must have a new manifest and hashes; never edit `recirculation_v1` in place.

建議 `recirculation_v2_entry` 從新設上游邊界節點增加 `E_IN → J0 → E1`，原有 `E_RD → J0 → E1` 則保留給巡迴回流。所有新到達車輛由 `E_IN` 進入，巡迴車輛不得改走 `E_IN`。原本 `E1/E2/E3` 上的停車區及保留車位配置不變，讓外生需求與再次巡迴能在道路空間上區分。

`E_IN` 長度、車道幾何、車種、保留距離及匯流優先權**此處均未決定**。這些參數會直接影響入口容量與回堵判定，必須先說明依據再凍結。新版本必須建立新的 manifest 與雜湊，不得直接覆蓋 `recirculation_v1`。

## 4. Entrance queue and Event A measurement / 入口佇列與 Event A 量測

The SOP's Event A is: **entrance access-link queue length ≥90% of usable storage for ≥60 consecutive seconds**. This is a *physical road-queue* event, not a ledger label or a count of vehicles awaiting SUMO insertion.

原 SOP 的 Event A 規定：**入口道路隊列長度達可用儲車長度 90% 以上，且連續至少 60 秒**。這是*道路上的實體排隊*事件，不是帳本狀態名稱，也不是等待 SUMO 插入的車輛數。

| Variable / 變數 | Operational meaning / 操作性定義 | Stage / 階段 |
|---|---|---|
| `N_outside` | Demand events already released but not yet inserted / 已到達但尚未插入 SUMO | Lifecycle accounting / 生命週期帳本 |
| `N_entry_queue` | Entered the model but not yet actively searching / 已進路網但尚未開始搜尋 | Lifecycle accounting / 生命週期帳本 |
| `Q_entry_physical` | Number of downstream-connected halted vehicles on `E_IN_0` / `E_IN_0` 上連續停等車數 | Requires v2 / 需新路網 |
| `L_queue_m` | Physical length from downstream lane boundary to connected queue tail / 從下游端到連續隊列尾端的實際長度 | Requires v2 + calibration / 需新路網與校準 |
| `L_usable_m` | Actual entrance-road usable storage length / 實際可用入口儲車長度 | Needs justification / 需具體依據 |
| `Q_outside_pending` | Separate nonspatial backlog, including delayed insertion / 非空間性外部待插入車輛 | **Not** Event A / **不是** Event A |

For a dedicated `E_IN_0` lane, proposed measurement is `coverage(t) = clamp(L_queue_m(t)/L_usable_m, 0, 1)`. To avoid counting unrelated stopped cars as a queue, vehicles must form a downstream-connected halted platoon, with a documented leading-vehicle boundary tolerance and maximum vehicle-to-vehicle gap. The sample-level stop threshold of `v < 0.1 m/s` matches SUMO's halting convention. Gap and leader tolerances require calibration and are **not frozen**.

Event A should be triggered only after *uninterrupted* threshold satisfaction over 60 seconds. Any missing observation epoch breaks that claim unless a specific missing-data treatment has been preapproved. Raw halting-number and lane occupancy may be logged as auxiliary checks; they do not replace contiguous queue-length measurement.

`entrance_queue_contract.py` and its unit tests implement this *proposed* measurement on synthetic observations. They do not yet establish physical calibration or an operational TraCI detector in `recirculation_v1`.

在獨立 `E_IN_0` 車道上，擬議使用 `coverage(t)=clamp(L_queue_m(t)/L_usable_m,0,1)`。不能把零散停住的車直接加總為回堵；應確認車輛形成從下游端連續向上游延伸的停等隊列，並記錄前車距邊界容許值及車間最大間隙。`v<0.1 m/s` 採 SUMO 的 halting 慣例，但空間間隙及前車容許值尚待校準，**未凍結**。

Event A 必須連續滿足門檻 60 秒才觸發。除非預先核准缺值處理方式，否則中斷的觀測點不能被默默視為持續回堵。TraCI 的 halting-number 和 lane occupancy 可作輔助核對，但不能替代連續隊列的空間長度。

`entrance_queue_contract.py` 及單元測試只在人工觀測樣本上實作此**擬議**規則，尚未在 `recirculation_v1` 上完成實體校準，也不是已驗證的正式 TraCI 偵測器。

## 5. Exit boundary and parking success / 離場邊界與停車成功

The live M1D-0C probe supports an *abstract route-end exit at `E3`*. This can remain a declared candidate boundary, rather than introducing a new exit road unnecessarily. **A successful parking service requires** `parked → departing → completed`; route-end removal without a parked event is **not** successful parking and must not enter parking-admission statistics. Unfinished searches are subject to the SOP's censoring rules.

實際 M1D-0C 測試支援把 `E3` 路線終點視為**抽象離場邊界**，可先作為候選，不必為了形式而立刻新增出口道路。**成功停車服務必須經過** `parked → departing → completed`；未停妥而走到路線終點的車輛**不是**停車成功，不得計入 parking admissions。尚未停妥者須遵循 SOP 的右設限規則。

## 6. Research validity controls / 研究有效性控制

A new entrance link changes merge delay, storage and traffic capacity. A new return loop changes travel distances and may itself create congestion. Therefore one versioned geometry, one car-following/speed configuration, one parking inventory and one behavioral-information distribution must be held fixed **across all values of ρ**. The original one-pass network and revised loop should not be pooled into a single `ρ50(T_m)` fit.

Perform a separate low-demand geometry-control diagnostic to determine whether queueing or stopping occurs even without stochastic parking-search rejection. This diagnostic is *not the proposed controller* for Experiment 2 and is not evidence of C1 by itself. Compare information regimes only as separately labeled sensitivity studies; the frozen ICCE source used live cross-zone parking counts.

C1 is only established under the SOP's compound conditions, including a genuine observable Event A and evidence of eligible vacancies. C2 must be separately reported. No detector threshold may be chosen after seeing desirable transition results.

新入口道路會改變匯流延遲、儲車空間與車流容量；回程道路也會改變行駛距離，並可能獨立產生壅塞。因此所有 ρ 值都必須使用**同一版本路網**，固定跟車 / 速度參數、車位清冊與行為資訊分布。原始單程路網與新版巡迴路網不得混在同一組 `ρ50(T_m)` 擬合。

建議安排獨立低負載的幾何診斷，檢查即使沒有隨機拒絕停車，路網是否也會自然形成排隊 / 停滯。這不是 Experiment 2 的 proposed controller，也不能單獨證明 C1。不同駕駛資訊機制只能作另外標示的敏感度分析；ICCE 原始版本曾使用即時跨分區停車數量。

C1 必須符合 SOP 的複合條件，包括可實際觀察的 Event A 以及檢測期間仍有合法空位的證據；C2 必須另行報告。不得在看過負載轉換結果後再調整偵測門檻。

## 7. Required gates and signatures / 必要門檻與簽核

| Gate / 門檻 | Status / 狀態 |
|---|---|
| Original network untouched, candidate hashes verified / 原始路網未更動、候選雜湊核對 | To be checked by M1D-0D audit / 由本階段檢查 |
| M1D-0C route branching 2/2, zero mass-balance errors / 雙分支測試通過 | **PASS** (user's 2026-11-17 Windows result) |
| Explicit signed geometry amendment / 路網 SOP 修訂簽核 | **PENDING** |
| Versioned `E_IN` approach and merge validation / 獨立入口與匯流驗證 | **PENDING** |
| Verified physical queue measurement against SUMO traces / 實體排隊量測核對 | **PENDING** |
| Candidate geometry and entrance storage formally frozen / 路網與入口儲車容量凍結 | **PENDING** |
| Driver information/behavior frozen and tested / 駕駛資訊與行為分布凍結 | **PENDING** |
| C1/C2 detector QC, step-length and warm-up pilot / 偵測器及數值敏感度檢查 | **PENDING** |
| Formal Stage B supervisor sign-off / 正式 Stage B 指導者簽核 | **PENDING** |

**Proposed M1D-0D outcome（本階段預期結果）:** Static documentation and integrity audit can **PASS**, while the formal geometry/use gate must remain **HOLD** until the missing prerequisites are completed.（靜態完整性通過；正式幾何採用與負載掃描仍須維持 HOLD，直至上述前提全部成立）

### Decision register / 研究決策欄位

- **Proposed primary Experiment 1-Core geometry（擬議主實驗路網）:** `recirculation_v2_entry` (NOT BUILT)
- **Original reference（原始參考）:** `canonical` (unchanged)
- **Entrance storage length & basis（入口儲車長度與依據）:** *to be documented*
- **Entrance link and merge tests（入口與匯流測試）:** *to be run*
- **Exit boundary decision（出口邊界決策）:** `E3 route-end virtual sink` (proposed)
- **Document version（文件版次）:** `M1D-0D-draft-1`

**This document does not certify the experiment, grant formal Stage A/B/C authorization, or override the original SOP.（本文件不構成實驗簽核，不授權正式 Stage A/B/C，也不凌駕原始 SOP）**
