# Milestone 1C-1 — Poisson Arrival Generator / Poisson 車輛到達生成器

This milestone implements the dynamic vehicle-arrival process used by
Experiment 1.

本階段建立 Experiment 1 所使用的動態車輛到達機制。

## Model / 模型

Vehicle arrivals follow a homogeneous Poisson process.
The inter-arrival time is exponentially distributed:

車輛到達採用 homogeneous Poisson process。
車輛到達間隔時間服從 exponential distribution：

```text
Delta t_i ~ Exponential(lambda)
```

Experiment 1 defines offered parking load as:

```text
rho = lambda * E[T_park] / C_eff
```

Therefore:

```text
lambda = rho * C_eff / E[T_park]
```

For the initial general-vehicle-only experiment:

```text
C_eff = 170
```

## Time Semantics / 時間語意

The generator produces continuous-valued scheduled arrival times.
Arrival times must not be rounded to the SUMO step length inside the demand generator.
The policy for releasing a scheduled arrival at a discrete SUMO control epoch belongs to Milestone 1C-3.


生成器輸出連續時間的預定到達時刻。
不得在 demand generator 中將 arrival time 四捨五入至 SUMO step。
預定到達事件如何映射至離散 SUMO control epoch，將由 Milestone 1C-3 統一規範。

## Reproducibility / 可重現性

A schedule is determined by（由下列條件決定）:

```text
arrival model
lambda
start time
end time
random seed
generator version
```

Every generated schedule also receives a SHA-256 fingerprint.

每份生成的 schedule 另外產生 SHA-256 fingerprint，用於確認不同電腦或不同實驗階段所使用的 arrival schedule 是否完全一致。

## Direct-Rate Mode / 直接到達率模式

`--rate-per-s` is provided only for smoke tests and debugging.（僅供 smoke test 與除錯使用）

Example:

```bash
python scripts/demand_generator.py \
  --rate-per-s 0.05 \
  --duration-s 600 \
  --seed 10
```

Outputs produced in this mode must not be used as formal Experiment 1 results unless the rate itself has been formally frozen.

若 arrival rate 尚未正式凍結，direct-rate mode 產生的資料不得用於正式 Experiment 1 結果。

## Offered-Load Mode / Offered-load 模式

After the parking-duration model is frozen（停車時間模型正式凍結後）, use:

```bash
python scripts/demand_generator.py \
  --rho 0.90 \
  --mean-parking-s <FROZEN_VALUE> \
  --duration-s 7200 \
  --seed 10
```

`C_eff` is read from（會自動讀取）:

```text
validation/network_summary.json
```

This prevents the general-only experiment from accidentally using
`C_total = 200` instead of `C_eff = 170`.

如此可避免 general-only 實驗誤將 `C_total = 200` 當成
`C_eff = 170` 使用。

## Outputs / 輸出

The generator writes（生成器輸出）:

```text
validation/demand_generator/
├─ arrivals_seed<seed>.csv
└─ arrival_manifest_seed<seed>.json
```

The manifest records the arrival rate, seed, time window, expected number of arrivals, actual number of arrivals, and schedule SHA-256.

Manifest 會記錄 arrival rate、random seed、時間範圍、理論預期到達數、實際生成到達數與 schedule SHA-256。

## Unit-Test Pass Criteria / 單元測試通過條件

The unit tests verify（單元測試驗證）:

- Correct conversion from `rho` to `lambda`.（`rho` 至 `lambda` 的轉換公式正確）
- Exact reproduction under the same seed.（相同 seed 必須產生完全相同的 schedule）
- Different seeds produce different schedules.（不同 seed 應產生不同 schedule）
- Arrival times are strictly increasing and inside the requested horizon.（Arrival time 必須嚴格遞增且位於指定時間範圍內）
- Vehicle IDs are unique.（Vehicle ID 不得重複）
- Zero arrival rate generates no vehicles.（Arrival rate 為 0 時不得產生車輛）
- Long-run arrival count is statistically reasonable.（Arrival rate 為 0 時不得產生車輛）
- Invalid parameters are rejected.（不合法參數必須被拒絕）

Run:


```bash
python tests/test_demand_generator.py
```

Expected result:

```text
Ran 8 tests

OK
```
