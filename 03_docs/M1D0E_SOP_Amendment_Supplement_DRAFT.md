# M1D-0E — SOP Geometry Amendment Supplement / SOP 幾何修正補充草案

**Status: DRAFT, UNSIGNED, NOT FROZEN（草案、未簽核、尚未凍結）**

## A. Link to the original SOP / 與原始 SOP 的關係

The 2026-09-20 Experiment 1 v2.0 SOP §4.1 requires a fixed ICCE-compatible canonical layout within Experiment 1-Core. Its §7 defines Event A as upstream entrance storage queue length at least 90% for at least 60 seconds, and Event C1 requires A together with specified service/mobility collapse and eligible vacancy evidence.

The original canonical `E1 → E2 → E3` has no return path. A separately versioned `recirculation_v1` achieved returning traffic but lacked a dedicated physical entrance. In M1D-0E, `recirculation_v2_entry` is proposed for engineering tests only; its Stage A/B use remains on HOLD.

2026-09-20 版 Experiment 1 v2.0 SOP 第 4.1 節要求在 Core 中固定沿用 ICCE 路網；第 7 節規定 Event A 必須是入口可用儲車長度的 90% 以上、持續至少 60 秒，C1 則須結合 A、服務 / 移動崩落及合法空位證據，不能將滿位當成 gridlock。

原始 canonical `E1 → E2 → E3` 無回訪道路；`recirculation_v1` 已驗證巡迴行駛，但沒有獨立實體入口。本關提出 `recirculation_v2_entry` 僅供工程驗證，尚未核准進入正式 Stage A/B。

## B. Proposed network revision / 幾何變更提案

- Parent（基礎版本）：`recirculation_v1`; retain `E1 E2 E3 E_RU E_RW E_RD` and all existing lane/parking source attributes（保留既有道路與停車區來源設定）
- Added（新增）：`E_IN`, one 150 m access lane from `J_IN=(-150,0)` to `J0=(0,0)` with nominal 13.89 m/s speed（150 公尺單車道入口，名目速度 13.89 m/s）
- New arrivals（新到達車）：always enter via `E_IN`, not directly on E1（只能由 `E_IN` 進場）
- Returning vehicles（回流車）：continue via `E_RD → E1`（仍從 E_RD 回到 E1）
- J0（匯流點）：two incoming roads, one outgoing road; priority/conflict relationships MUST be verified in the compiled SUMO network and dynamic probe（兩入一出，編譯後交通優先權與實際匯流必須另外驗證）
- Exit boundary（出口）：route end on E3 only after successful parking (virtual sink under review)（成功停車後由 E3 模擬邊界離場，尚待正式批准）

The 150 m value is provisional and is not derived from site survey or ICCE geometry. It is a research-design change that must not be presented as observed physical entrance length.

150 公尺僅為測試值，尚未由實地測量或 ICCE 幾何推導；不得對外宣稱為真實停車場入口長度。

## C. Queue measurement contract / 排隊量測規範

1. `outside / entry_queue` lifecycle counts and SUMO delayed insertions are **not** physical spillback（生命週期狀態數及插入延遲**不等於**實體回堵）
2. On `E_IN_0`, record the vehicle front position, length and speed per step, plus lane vehicle/halting count even when empty（對 `E_IN_0` 記錄車頭位置、車長、車速及每步車道統計（含空車道））
3. Later calibrate the physical `L_usable`, connected-stopped-queue definition, head/gap tolerances and observation interval（後續必須校準可用儲車長度、連續靜止隊列與間隙、量測間隔）
4. Only after calibration test the SOP Event A condition `L_queue / L_usable >= 0.90` continuously for >=60 s（完成校準後才可正式測試 90% / 60 秒條件）
5. Event A is a prerequisite for C1, **not** sufficient on its own; eligible vacancy and mobility/service criteria must separately pass（Event A 是 C1 的必要條件之一，仍須其他合法空位與服務 / 移動崩落條件）

## D. Confounding and controls / 混雜來源與控制

J0 now combines new arrivals and search returns, creating a merge bottleneck that did not exist in the original canonical network. Queue amplification arising from this merge must be distinguished from behavioral free-search amplification. Add geometry-only/no-search controls, and preserve identical revised geometry for all load levels before estimating any P_C1 or rho50.

J0 新增了原始 canonical 不存在的新車 / 回流匯流，可能形成由路口本身誘發的瓶頸。未來必須用不含自由搜尋行為的幾何控制組，分辨單純匯流壅塞與搜尋誘發壅塞；不同負載必須使用同一凍結路網，才可估計 P_C1 與 rho50。

## E. Pending sign-off gates

- Validate actual SUMO v2 build, entry/return route, parking, normal exit, collision-free/teleport-free behavior（驗證 v2 路網、進場 / 回流、停車與正常離場）
- Specify and calibrate physical usable entrance storage and Event A algorithm（校準可用入口儲車長度與 Event A）
- Validate controlled merge interactions and low-load geometry-only control（驗證匯流衝突及低載幾何控制組）
- Choose and document exit-boundary semantics（確認出口模型）
- Approve a revised canonical-for-Experiment-1 geometry and its hashes（核准新版正式幾何與雜湊）
- Freeze behavioral information, driver distributions, duration parameters and C1/C2 detector（凍結行為資訊、駕駛分布、停車時間及 C1/C2）
- Execute parameter freeze, step-length/warm-up pilot and supervisor sign-off before Stage B（完成參數凍結、時間步長 / 暖機驗證與指導者簽核）

**Approval to generate a technical candidate is not approval to conduct a formal Experiment 1 batch.（允許產生工程候選路網，不代表核准正式 Experiment 1 批次）**
