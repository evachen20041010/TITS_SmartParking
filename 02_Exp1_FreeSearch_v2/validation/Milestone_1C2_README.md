# Milestone 1C-2 — Parking Duration Generator / 停車時間生成器

This milestone implements a reproducible positive parking-duration model.

本階段建立可重現且保證為正值的停車時間生成模型。

## Distribution / 分布

The implementation uses a lognormal distribution parameterized by its arithmetic mean and coefficient of variation (CV).

目前實作採用 lognormal distribution，並以算術平均值與變異係數 (coefficient of variation, CV) 參數化。

```text
sigma_log^2 = ln(1 + CV^2)
mu_log      = ln(mean) - sigma_log^2 / 2
```

The formal Experiment 1 mean and CV are intentionally not hard-coded.
Values such as `1800 s` and `CV = 0.5` appearing in unit tests are only numerical test fixtures. They are not formal research parameters.

正式 Experiment 1 的平均停車時間與 CV 目前刻意不寫死在程式中。
單元測試中出現的 `1800 s` 與 `CV = 0.5` 僅為數值測試用參數，不是正式研究參數。

## No Truncation Yet / 目前不進行截尾

Version 1C2-v1 does not clip or truncate parking durations.
If truncation is later required, it must be treated as a separate frozen model because truncation changes the effective distribution mean.

1C2-v1 不對停車時間進行 clipping 或 truncation。
若後續需要設定上下限，必須視為另一個需要正式凍結的模型，因為截尾會改變實際分布的平均值。

## Independent Random Streams / 獨立亂數流

Arrival generation and parking-duration generation must not consume the same mutable random-number stream.
A master seed is converted into independent deterministic stream seeds.

車輛到達與停車時間不得共用同一個會持續消耗的亂數流。
同一個 master seed 會依用途產生獨立且可重現的 stream seed。

## Unit Tests / 單元測試

Run:

```bash
python tests/test_parking_duration.py
```

Expected:

```text
Ran 8 tests

OK
```
