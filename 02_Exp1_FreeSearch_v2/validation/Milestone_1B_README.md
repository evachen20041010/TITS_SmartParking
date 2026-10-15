# Milestone 1B — Vehicle Lifecycle and Mass Balance / 車輛生命週期與質量平衡

This milestone establishes the vehicle lifecycle model and mass-balance rules used in T-ITS Experiment 1. The lifecycle logic is validated independently before it is connected to dynamic SUMO demand generation.

本階段建立 T-ITS Experiment 1 所使用的車輛生命週期模型與質量平衡規則。在與 SUMO 動態需求產生機制整合之前，先獨立驗證生命週期邏輯是否正確。

---

## Vehicle Lifecycle / 車輛生命週期

The normal vehicle lifecycle is:

```text
outside
  ↓
entry_queue
  ↓
cruising
  ↓
parked
  ↓
departing
  ↓
completed
```

An additional terminal state, `removed_error`, is used only when a vehicle unexpectedly disappears or is removed from the simulation.
A formal experiment run is invalid if:

另外定義一個終止狀態 `removed_error`，僅用於記錄車輛在模擬中非預期消失或被移除的情況。
若正式實驗中出現下列情況，該次實驗應判定為無效：

```text
removed_error > 0
```

---

## State Definitions / 狀態定義

### `outside`

The demand-arrival event has occurred, but the vehicle has not yet been successfully inserted into the SUMO network.
Future scheduled vehicles are not counted as `outside` before their arrival time.

車輛的需求到達事件已經發生，但尚未成功插入 SUMO 路網。
尚未到達預定時間的未來車輛，不計入 `outside`。

### `entry_queue`

The vehicle has entered the modeled system and is waiting or moving through the entrance region before active parking search begins.

車輛已進入模擬系統，正在入口區域等待或前進，但尚未正式開始搜尋停車位。

### `cruising`

The vehicle is actively searching for a legally accessible parking space.

車輛正在主動搜尋其依法可使用的停車位。

### `parked`

The vehicle is currently occupying a parking space.

車輛目前正在停車位內停放。

### `departing`

The parking duration has ended and the vehicle is driving toward the system exit.

停車時間已結束，車輛正在駛向系統出口。

### `completed`

The vehicle has normally exited the modeled system.

車輛已正常離開模擬系統。

### `removed_error`

The vehicle disappeared or was unexpectedly removed before normal completion.
This state preserves accounting consistency but causes formal-run quality control to fail.

車輛在正常完成生命週期之前，非預期地消失或被移除。
此狀態的目的在於維持帳目一致性，但正式實驗的品質檢查必須判定為失敗。

---

## Allowed Transitions / 合法狀態轉移

The normal lifecycle permits only the following transitions:

```text
outside
→ entry_queue
→ cruising
→ parked
→ departing
→ completed
```

Illegal transitions（不合法狀態轉移） such as:

```text
outside → parked
cruising → completed
completed → cruising
```

must raise a `LifecycleError`（必須觸發，不得由程式自動修正或忽略）.

---

## Mass Balance / 質量平衡

At every simulation step, the following identity must hold（必須滿足下列質量平衡）:

```text
N_generated_to_date
=
N_outside
+ N_entry_queue
+ N_cruising
+ N_parked
+ N_departing
+ N_completed
+ N_removed_error
```

Therefore:

```text
mass_balance_error = 0
```

must hold throughout the entire simulation.

必須在整段模擬期間始終成立。

For formal experiment runs（正式實驗另外要求）, an additional quality-control condition is required:

```text
N_removed_error = 0
```

---

## Definition of Generated Demand / 已產生需求的定義

`N_generated_to_date` counts only vehicles whose demand-arrival event has already occurred（僅計算「需求到達事件已經發生」的車輛）.

For example, if a vehicle is scheduled to arrive at:

```text
t = 100 s
```

then at:

```text
t = 50 s
```

the vehicle is not yet included in the lifecycle ledger（該車輛尚未納入生命週期帳本）.

At（當時間到達）:

```text
t = 100 s
```

the vehicle is registered as:

```text
outside
```

If insertion into SUMO succeeds, it may then transition to:

```text
entry_queue
```

---

## Quality-Control Principle / 品質控制原則

The simulator must never silently lose a vehicle. If a vehicle unexpectedly disappears from SUMO, it must be explicitly recorded as:

模擬器不得在沒有紀錄的情況下讓車輛憑空消失。若 SUMO 中的車輛非預期消失，必須明確記錄為：

```text
removed_error
```

The mass balance may still remain mathematically valid, but the corresponding formal simulation run must be rejected.

即使此時質量平衡在數學上仍然成立，該次正式實驗仍必須被判定為無效。

---

## Unit Tests / 單元測試

The current unit tests verify:

1. Normal complete vehicle lifecycle.（正常完整生命週期）

2. Rejection of illegal state transitions.（拒絕非法狀態轉移）

3. Rejection of duplicate vehicle IDs.（拒絕重複的車輛 ID）

4. Rejection of non-monotonic transition times.（拒絕時間倒退的狀態轉移）

5. Confirmation that `completed` is a terminal state.（確認 `completed` 為終止狀態）

6. Confirmation that `removed_error` preserves mass balance but fails formal-run quality control.（確認 `removed_error` 可維持質量平衡，但正式實驗品質檢查必須失敗）

7. Mass-balance verification for multiple vehicles in different states.（驗證多車處於不同狀態時的質量平衡）

Run the tests using:

```bash
python tests/test_vehicle_state.py
```

The expected result is:

```text
Ran 7 tests

OK
```

---

## Current Scope / 本階段範圍

Milestone 1B validates the vehicle lifecycle and accounting logic independently of SUMO demand generation.
The following components are introduced only after this milestone passes:

Milestone 1B 目前只驗證車輛生命週期與帳務邏輯，不處理 SUMO 動態需求生成。
以下功能將在本階段通過後才加入：

```text
dynamic arrivals 動態車輛到達
parking-duration sampling 停車時間抽樣
SUMO vehicle insertion SUMO 車輛插入
continuous free search 持續式自由搜尋
gridlock detection 壅塞／失穩偵測
```

---

## Milestone 1B Pass Criteria / Milestone 1B 通過條件

Milestone 1B passes only when（僅在以下條件全部成立時通過）:

```text
All lifecycle unit tests pass. 所有生命週期單元測試皆通過。
Mass balance is always preserved. 質量平衡始終成立。
Illegal state transitions are rejected. 非法狀態轉移會被拒絕。
Duplicate vehicle IDs are rejected. 重複 vehicle ID 會被拒絕。
Transition timestamps are monotonic. 狀態轉移時間不可倒退。
Formal-run QC rejects removed_error > 0. removed_error > 0 時正式實驗 QC 必須失敗。
```
