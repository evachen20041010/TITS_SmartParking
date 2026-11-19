# Canonical Network - Experiment 1 / Experiment 1 標準路網

## Provenance and boundary / 來源與研究邊界

The canonical network geometry and parking-area definitions originate from the reproduced ICCE-TW 2026 layout under `01_ICCE_2026_Frozen/snapshot/sumo_parking/`. This physical baseline is preserved while Experiment 1 develops new demand, lifecycle, search, logging, and instability logic separately.

標準路網的幾何與停車區設定源自 `01_ICCE_2026_Frozen/snapshot/sumo_parking/` 中已完成重現的 ICCE-TW 2026 場域。本研究保留相同物理基準，並在 Experiment 1 中另外開發需求、生命週期、搜尋、紀錄及失穩邏輯。

**Implementation status:** demand generation and lifecycle integration are validated through M1C. The continuous free-search model and instability detector are **not** yet implemented or validated.（需求生成與生命週期整合已通過 M1C；持續式自由搜尋與失穩偵測器目前**尚未**實作或驗證）

## Geometry and capacity / 幾何與容量

The network has three non-internal road edges (`E1`, `E2`, `E3`), three parking zones, and seven SUMO parking areas. The archived inventory is:

路網有三條非內部道路邊（`E1`、`E2`、`E3`）、三個停車分區及七個 SUMO 停車區域。封存的容量清冊如下：

| Zone / 分區 | General / 一般 | Family / 親子 | Disabled / 身障 | Total / 總數 |
| --- | ---: | ---: | ---: | ---: |
| Z1 | 40 | 10 | 5 | **55** |
| Z2 | 50 | 10 | 5 | **65** |
| Z3 | 80 | 0 | 0 | **80** |
| **Total / 合計** | **170** | **20** | **10** | **200** |

The seven parking-area IDs and capacities are（七個停車區域的 ID 與容量）:

```text
PA_Z1_G = 40       PA_Z1_F = 10       PA_Z1_D = 5
PA_Z2_G = 50       PA_Z2_F = 10       PA_Z2_D = 5
PA_Z3_G = 80
```

The general-only Experiment 1-Core population is legally eligible for **general spaces only**. Thus, `C_eff=170` and `C_total=200` are different and must not be interchanged.

只研究一般車輛的 Experiment 1-Core，依法**僅能使用一般車位**；因此 `C_eff=170` 與 `C_total=200` 不同，不能互相替代。

## Offered-load definition / 停車需求負載定義

Offered load uses the legally eligible capacity as its denominator（需求負載以**合法可使用容量**為分母）:

```text
rho    = lambda * E[T_park] / C_eff
lambda = rho * C_eff / E[T_park]
C_eff  = 170
```

This `rho` is an exogenous demand parameter, **not** instantaneous measured occupancy. Occupancy arises from arrivals, parking admissions, dwell times, and departures.

此 `rho` 為外生需求參數，**不是**實測瞬間 occupancy。實際占用率由到達、入位、停放時間與離場過程自然形成。

## Canonical files and SUMO settings / 標準檔案與 SUMO 設定

The files below define the geometry, parking areas, and SUMO base configuration（下列檔案定義路網幾何、停車區與 SUMO 基礎設定）:

```text
network/canonical/
├─ parking_lot.net.xml
├─ parking_areas.add.xml
├─ parking.edg.xml
├─ parking.nod.xml
├─ base.sumocfg
└─ README.md
```

`base.sumocfg` loads `parking_lot.net.xml` and `parking_areas.add.xml` with a default `1.0 s` simulation step and disables SUMO automatic teleport (`time-to-teleport=-1`).

Automatic teleport must stay disabled so prolonged congestion is not silently erased. A future formal step-length convergence study must still compare different step lengths according to the SOP.

`base.sumocfg` 載入 `parking_lot.net.xml` 與 `parking_areas.add.xml`，預設模擬步長為 `1.0 秒`，並關閉 SUMO 自動 teleport（`time-to-teleport=-1`）。

停用 teleport 可避免持續壅塞被模擬器無聲移除；但未來正式實驗仍須依 SOP 比較不同步長，完成 step-length convergence study。

## Inventory validation / 清冊驗證

From `02_Exp1_FreeSearch_v2/` in the validated Python environment, run:

```cmd
python scripts\inspect_network.py
```

The script checks parking IDs, linked lanes, segment positions, zone/type capacities, and legal effective capacity. The archived result is PASS with 3 non-internal edges, 3 non-internal lanes, 7 parking areas, 200 total spaces, and 170 legally eligible general spaces. The evidence files are:

程式檢查停車區 ID、對應車道、起迄位置、分區 / 類型容量與合法有效容量。封存驗證結果為 PASS：3 條非內部道路邊、3 條非內部車道、7 個停車區、200 個實體車位，以及一般車輛可合法使用的 170 個車位。驗證證據保存於：

```text
validation/network_inventory.csv
validation/network_summary.json
```

## Fixed-layout rule / 路網固定規則

Experiment 1-Core isolates offered-load changes. Do not simultaneously modify lane geometry, parking distribution, vehicle class, walking destination, legal access rules, speed, or car-following parameters during the same load sweep.

If any physical assumptions must change in a new research version, update and revalidate the network files, inventory, capacities, hashes, and experiment manifests, with a new Git commit.

Experiment 1-Core 只隔離 offered load 的效果。執行同一組負載掃描時，不得同時更動車道幾何、車位分布、研究車種、步行目的地、合法性限制、速度或 car-following 參數。

若新版本確實需要變更物理假設，必須同步更新並重新驗證路網檔案、容量清冊、校驗碼與實驗 manifest，且建立新的 Git commit。

## Historical test boundary / 歷史測試範圍提醒

M1B-2 and M1C-3 used `PA_Z2_G` as a **fixed** legal parking target to test integration. This does not imply that parking search is already modeled or that vehicles know global vacancy information.

M1B-2 與 M1C-3 皆以 `PA_Z2_G` 作為**固定**合法停車目標來檢查整合流程。這不代表已建立真正的停車搜尋模型，更不代表駕駛可取得全域空位資訊。
