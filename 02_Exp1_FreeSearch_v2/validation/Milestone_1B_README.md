# Milestone 1B - Vehicle Lifecycle and Mass Balance / 車輛生命週期與質量平衡

## Objective / 目的

Milestone 1B validates the vehicle state machine and conservation ledger before dynamic demand and search behavior are added. Its Python unit-test milestone has been completed, and real-SUMO lifecycle integration was separately validated in Milestone 1B-2.

Milestone 1B 先驗證車輛狀態機與帳務守恆，再逐步加入動態需求與搜尋行為。本階段已通過 Python 單元測試，並在 Milestone 1B-2 另行完成真實 SUMO 生命週期整合驗證。

## Normal lifecycle / 正常生命週期

The only normal state sequence is（唯一正常狀態順序如下）:

```text
outside -> entry_queue -> cruising -> parked -> departing -> completed
```

Unexpectedly lost or removed vehicles enter the terminal state `removed_error` and fail formal-run quality control.

車輛若發生非預期消失或移除，必須進入異常終止狀態 `removed_error`，並使正式 run 的品質檢查失敗。

## State definitions / 狀態定義

**`outside`:** the scheduled demand-arrival event has occurred, but SUMO has not yet inserted the vehicle. Future events are not counted.（車輛的預定需求到達事件已發生，但 SUMO 尚未插入車輛；未來尚未到達的事件不計入）

**`entry_queue`:** the vehicle is in the modeled entrance region but has not started active parking search.（車輛已位於模擬入口區，但尚未開始主動搜尋車位）

**`cruising`:** the vehicle is in the active parking-search state. In M1B/M1C smoke tests, this state was used for lifecycle integration with a fixed parking target, **not** a completed free-search model.（車輛處於主動搜尋的狀態；但 M1B/M1C 的 smoke test 使用固定停車目標驗證狀態轉換，**不是**已完成的自由搜尋模型）

**`parked`:** the vehicle is occupying a parking space.（車輛正在占用停車位）

**`departing`:** the parking stay has ended and the vehicle is heading toward the system exit.（停車時間結束，車輛正駛往系統出口）

**`completed`:** the vehicle exited normally and its lifecycle ended.（車輛正常離開系統，生命週期結束）

**`removed_error`:** an abnormal terminal state that preserves accounting but invalidates a formal run.（用於維持帳務一致性的異常終止狀態；正式 run 出現此狀態即為無效）

## Allowed transitions and validation / 合法轉移與驗證

Only consecutive transitions in the normal sequence are allowed. Illegal jumps (for example `outside -> parked`, `cruising -> completed`) and transitions out of terminal states must raise `LifecycleError`.

Vehicle IDs must be unique; transition timestamps must never go backwards.

僅允許按照正常順序逐步轉移。非法跳躍（例如 `outside -> parked`、`cruising -> completed`）或從終止狀態離開，都必須觸發 `LifecycleError`。

每台車的 ID 必須唯一，狀態轉換的時間戳記不得倒退。

## Mass balance / 質量平衡

At every recorded simulation epoch（每個記錄的模擬控制時刻均須滿足）:

```text
N_generated_to_date = N_outside + N_entry_queue + N_cruising
                    + N_parked + N_departing + N_completed + N_removed_error
mass_balance_error = 0
```

`N_generated_to_date` includes only events that have actually arrived according to the demand model, not all vehicles scheduled for the future.

A correct accounting identity can coexist with `removed_error>0`; therefore formal quality control must enforce `N_removed_error=0` separately.

`N_generated_to_date` 僅包含依需求模型已經到達的事件，不包含未來才預定出現的車輛。

質量平衡數學式即使正確，也可能仍有 `removed_error>0`；因此正式品質檢查必須**另外**要求 `N_removed_error=0`。

## Unit-test coverage / 單元測試範圍

The seven tests cover:

1. Complete normal lifecycle.（正常完整生命週期）
2. Rejection of illegal state transitions.（拒絕非法狀態轉移）
3. Rejection of duplicate vehicle IDs.（拒絕重複車輛 ID）
4. Rejection of non-monotonic timestamps.（拒絕時間倒退）
5. Terminal `completed` state.（`completed` 為不可再次轉移的終止狀態）
6. Accounting and formal QC for `removed_error`.（`removed_error` 的帳務處理與正式品質檢查）
7. Multi-vehicle mixed-state mass balance.（多車輛混合狀態下的質量平衡）

Run from the Experiment 1 directory（從 Experiment 1 目錄執行）:

```cmd
python tests\test_vehicle_state.py
```

The recorded outcome is **7/7 PASS**.

已記錄結果為 **7/7 PASS**。

## Boundaries and follow-up / 範圍與後續階段

M1B validates accounting rules, not stochastic demand or behavior. M1B-2 later proved a three-vehicle SUMO lifecycle, and M1C later connected the demand and parking-duration samplers. Continuous free search and instability detection remain future milestones.

See [`Milestone_1B2_README.md`](Milestone_1B2_README.md) and [`Milestone_1C3_README.md`](Milestone_1C3_README.md) for the integration checks.

M1B 驗證帳務規則，不驗證隨機需求或駕駛行為。後續 M1B-2 已完成三車 SUMO 生命週期；M1C 已串接需求與停車時間生成器。持續式自由搜尋與失穩偵測仍屬後續里程碑。

整合驗證請參考 [`Milestone_1B2_README.md`](Milestone_1B2_README.md) 與 [`Milestone_1C3_README.md`](Milestone_1C3_README.md)。
