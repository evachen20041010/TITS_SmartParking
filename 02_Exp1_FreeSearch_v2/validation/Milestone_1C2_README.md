# Milestone 1C-2 - Parking Duration Generator / 停車時間生成器

## Scope / 本階段範圍

This module creates reproducible, positive parking dwell times for vehicle IDs produced by the demand generator. Milestone 1C-2 validates the sampler independently; SUMO integration is covered by M1C-3.

本模組依需求生成器提供的車輛 ID，產生可重現且為正值的停車時間。M1C-2 獨立驗證抽樣器；與 SUMO 的整合則由 M1C-3 驗證。

## Distribution / 分布模型

The implementation uses an untruncated lognormal distribution parameterized by its arithmetic mean `m` (seconds) and coefficient of variation `CV`.

目前實作使用**未截尾**的 lognormal distribution，以算術平均停車時間 `m`（秒）與變異係數 `CV` 作為輸入。

```text
sigma_log^2 = ln(1 + CV^2)
mu_log      = ln(m) - sigma_log^2 / 2
T_park      ~ Lognormal(mu_log, sigma_log)
```

A value of `CV=0` produces a constant dwell time. Generated durations must be positive and finite.

**Formal parameter status:** the research mean, CV, source dataset, and any future truncation policy have **not been frozen**. Unit-test values such as `m=1800 s` and `CV=0.5` are numerical fixtures only.

當 `CV=0` 時，生成器會產生固定停車時間。所有抽樣結果都必須是有限正值。

**正式參數狀態：** 研究使用的平均值、CV、來源資料與未來可能採用的截尾政策**都尚未凍結**。單元測試中的 `m=1800 秒` 與 `CV=0.5` 僅為數值測試條件。

## Truncation rule / 截尾規則

Version `1C2-v1` does not clip or truncate generated dwell times. Introducing a minimum or maximum stay changes the effective distribution and its mean, so it requires an explicit, independently validated new configuration/version.

Because offered load uses `E[T_park]`, duration-distribution changes also affect the arrival rate required for any given `rho`.

`1C2-v1` 不裁切或截尾生成的停車時間。加入停車時間上下限會改變實際分布與平均值，因此必須建立明確且獨立驗證的新設定或版本。

由於 offered load 使用 `E[T_park]`，改變停車時間分布也會影響各個 `rho` 所對應的車輛到達率。

## Independent random streams / 獨立亂數流

A deterministic SHA-256 seed derivation maps `(master_seed, stream_name)` to a reproducible stream seed. Arrival and parking draws use different stream names.

This supports future paired scenario comparisons while keeping stochastic realizations independent of function-call order.

程式使用確定性的 SHA-256 seed derivation，將 `(master_seed, stream_name)` 映射到可重現的 stream seed。到達事件與停車時間使用不同的 stream name。

如此可支援未來的配對情境比較，並避免抽樣結果受到函式呼叫先後順序影響。

## CLI usage (Windows CMD) / 命令列使用方式（Windows CMD）

The CLI reads vehicle IDs from an already generated arrival schedule.（CLI 從既有到達排程讀取車輛 ID） Example:

```cmd
python scripts\demand_generator.py --rate-per-s 0.05 --duration-s 600 --seed 10
python scripts\parking_duration.py --arrival-csv validation\demand_generator\arrivals_seed10.csv --mean-s 1800 --cv 0.5 --master-seed 10
```

**Both commands above are for development and demonstration only.** Their numeric parameters have not been approved for a formal experiment.

**以上兩個指令僅供開發與示範。** 其中數值參數尚未獲得正式實驗核准。

## Outputs / 輸出

The generator writes one duration per vehicle and a manifest containing mean/CV, log-space parameters, stream seed, sample count, sample mean, and SHA-256 fingerprint.

生成器為每台車輸出一筆停車時間，並在 manifest 中記錄平均值 / CV、log-space 參數、亂數流 seed、樣本數、樣本平均值及 SHA-256 指紋。

```text
validation/parking_duration_generator/
├─ parking_durations_seed<master_seed>.csv
└─ parking_duration_manifest_seed<master_seed>.json
```

The current manifest explicitly records `formal_parameterization=false`; it must not be interpreted as evidence of a frozen model.

目前 manifest 明確記錄 `formal_parameterization=false`，不可將其視為正式分布模型已凍結的證據。

## Verified unit tests / 已驗證單元測試

Eight tests verify parameter conversion, same-seed reproduction, different-seed results, positive/finite samples, `CV=0`, long-run mean/CV sanity, deterministic separated stream seeds, and invalid-input rejection.

八項測試檢查參數轉換、同 seed 重現、不同 seed 差異、樣本有限正值、`CV=0`、長期平均值與 CV 的合理性、獨立且可重現的亂數流 seed，以及不合法輸入拒絕。

```cmd
python tests\test_parking_duration.py
```

Archived result: **8/8 PASS**. The subsequent M1C-3 smoke test confirmed integration of sampled durations into the SUMO lifecycle, not formal calibration of the duration distribution.

封存結果：**8/8 PASS**。後續 M1C-3 煙霧測試已確認抽樣停車時間能接入 SUMO 生命週期，但**不代表**停車時間分布已完成正式校準。
