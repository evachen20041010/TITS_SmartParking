# Milestone 1D-0B — Versioned Recirculation Candidate / 版本化回程路網候選方案

**Status:** `DESIGN_CANDIDATE_ONLY` — not authorized for formal Experiment 1 load sweeps.（**僅為設計候選**，不得用於正式負載掃描）

## Why this milestone exists / 目的

The frozen canonical graph has `E1 -> E2 -> E3` and no directed cycle. Continuous free search requiring a second physical visit to Z1–Z3 cannot be implemented on this graph without changing the road topology.

The SOP requires the ICCE geometry to remain fixed for Experiment 1-Core. This candidate is therefore explicitly a **proposed amendment** and **not automatically the approved Experiment 1-Core network**.

已凍結 canonical 路網只有 `E1 -> E2 -> E3`，不存在有向迴路。若持續式自由搜尋要求車輛實際再次經過 Z1–Z3，則必須修改道路拓撲。

原 SOP 要求 Experiment 1-Core 沿用並固定 ICCE 幾何。因此本候選方案屬於**待審核的設計變更**，**不能自動視為已核准的正式 Experiment 1-Core 路網**。

## Proposed topology / 候選道路拓撲

```text
J0 --E1--> J1 --E2--> J2 --E3--> J3
 ^                              |
 |                              E_RU
E_RD                            |
 |                              v
J5 <-----------E_RW------------ J4
```

- Original nodes（原有節點）：`J0=(0,0)`, `J1=(200,0)`, `J2=(400,0)`, `J3=(600,0)`.
- Added nodes（新增節點）：`J4=(600,60)`, `J5=(0,60)`.
- Return edges（回程路段）：`E_RU`, `E_RW`, `E_RD`.
- Existing parking lanes（原停車車道）：`E1_0`, `E2_0`, `E3_0`, unchanged IDs.
- Parking-area XML（停車區 XML）：byte-identical copy, **7 areas; 200 total; `C_eff=170` general spaces**.
- `J0` and `J3` junction types change from `dead_end` to `priority` only in the candidate.（`J0` 與 `J3` 在候選路網改為 `priority`，canonical 原始檔完全不動）

**The 60 m return offset is a non-formal design fixture, not a measured/calibrated distance.** The nominal road length of one complete loop is `600 + 60 + 600 + 60 = 1320 m`, compared with the original `600 m` one-pass route. This can change travel time, merging, queuing, and any inferred instability mechanism.

**回程偏移 60 公尺僅是非正式候選幾何參數，不是經校準的實際距離。** 一圈名目長度約 `1320 m`，原本單程為 `600 m`，因此會影響行駛時間、匯流、排隊與失穩機制，不能忽略此研究混雜因素。

## Files added by this patch / 本次修補檔案

```text
02_Exp1_FreeSearch_v2/
├─ scripts/
│  ├─ build_m1d0b_candidate.py
│  └─ run_m1d0b_route_probe.py
├─ tests/
│  └─ test_m1d0b_candidate.py
└─ validation/
   ├─ Milestone_1D0B_README.md
   └─ Milestone_1D0B_Decision_Record.md
```

The builder writes only to（生成器只會寫入）：

```text
02_Exp1_FreeSearch_v2/network/candidates/recirculation_v1/
├─ parking.nod.xml
├─ parking.edg.xml
├─ parking_areas.add.xml
├─ base.sumocfg
├─ route_probe.rou.xml
├─ parking_lot.net.xml          # created by netconvert（由 netconvert 生成）
└─ candidate_manifest.json
```

The builder refuses to silently overwrite an already modified candidate source. The original `network/canonical/` and historical `01_ICCE_2026_Frozen/` are never modified.

生成器不會靜默覆寫曾被修改的候選來源檔；原始 `network/canonical/` 與歷史 `01_ICCE_2026_Frozen/` 完全不動。

## Execution / 執行

Run all unit tests from `02_Exp1_FreeSearch_v2/`（執行所有單元測試）:

```cmd
python -m unittest discover -s tests -p "test_*.py"
```

The new M1D-0B module adds **9 static unit tests** (tested independently). If you already have the 29 M1D-0 tests installed, the expected total is **38**.　Build the new candidate in an isolated directory:

本次新增 **9 個靜態單元測試**（已獨立驗證）。若本機已具有原先的 M1D-0 共 29 個測試，總數預期為 **38**。將候選路網建在獨立目錄：

```cmd
where netconvert
python scripts\build_m1d0b_candidate.py
```

If `netconvert` is absent from `PATH`, supply its actual installed path using `--netconvert` or run `--static-only` to generate source files without a compiled `.net.xml`. **`--static-only` is not the SUMO network PASS criterion.**

Once `Compiled SUMO network: PASS` is printed, run the one-vehicle, two-pass route probe:

若 `PATH` 找不到 `netconvert`，請以 `--netconvert` 指定實際安裝位置，或先用 `--static-only` 產生來源 XML。**`--static-only` 不代表 SUMO 路網編譯驗證已通過。**

確定輸出 `Compiled SUMO network: PASS` 後，執行單車兩輪實際路線測試：

```cmd
python scripts\run_m1d0b_route_probe.py
```

Expected roadway sequence (not a parking/search test)（預期實際道路序列（此測試**不測停車或搜尋**））:

```text
E1 E2 E3 E_RU E_RW E_RD E1 E2 E3
```

Output（輸出）：`validation/m1d0b/route_probe/route_probe_summary.json`.

## Acceptance boundary / 驗收邊界

- `M1D0B static candidate`: PASS only if source checks and all 9 tests pass.（靜態檢查與 9 個測試通過才算候選來源 PASS）
- `M1D0B compiled graph`: PASS only if `netconvert` succeeds and all nine route edges connect.（netconvert 編譯成功且連線完整才算路網 PASS）
- `M1D0B physical revisitation`: PASS only when SUMO actually observes the expected repeated edge sequence.（SUMO 真正觀察到完整兩次經過停車道路，才算實體回訪 PASS）
- `Formal Experiment 1`: **HOLD** until documented SOP amendment, geometry validation, and method sign-off.（正式 Experiment 1 **仍暫停**，需先完成 SOP 變更紀錄、幾何重新驗證與方法簽核）

Passing the route probe does **not** demonstrate a free-search algorithm, traffic stability, or search-induced gridlock.

路線測試通過**不代表**自由搜尋演算法、交通穩定性或搜尋誘發失穩已獲得驗證。
