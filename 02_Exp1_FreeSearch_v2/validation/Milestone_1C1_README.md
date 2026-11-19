# Milestone 1C-1 - Poisson Arrival Generator / Poisson 車輛到達生成器

## Scope / 本階段範圍

This module generates **continuous-time** arrival schedules for a homogeneous Poisson process. It was unit-tested independently of SUMO; discrete release and vehicle insertion are verified later in M1C-3.

本模組為 homogeneous Poisson process 產生**連續時間**到達排程。它先獨立於 SUMO 通過單元測試；離散釋放與車輛插入則在 M1C-3 驗證。

## Mathematical model / 數學模型

Inter-arrival times follow an exponential distribution with rate `lambda` (vehicles per second). Offered parking load follows the Experiment 1 SOP:

到達間隔時間服從參數為 `lambda`（輛 / 秒）的 exponential distribution。停車需求負載依 Experiment 1 SOP 定義：

```text
Delta_t ~ Exponential(lambda)
rho     = lambda * E[T_park] / C_eff
lambda  = rho * C_eff / E[T_park]
C_eff   = 170  # general-only core
```

`rho` is not actual occupancy. The formal `E[T_park]` must be supported by an approved parameter freeze; it is not automatically determined by passing these unit tests.

`rho` 不是實際占用率。正式的 `E[T_park]` 必須有核准的參數凍結依據，不能因本單元測試通過就視為已確定。

## Time semantics / 到達時間語意

Arrival times are strictly increasing real-valued seconds and remain unrounded inside the generator. M1C-3 releases each scheduled event at the first SUMO control epoch at or after its scheduled time.

This separation prevents numerical step length from silently redefining the stochastic arrival model.

生成器輸出的到達時間為嚴格遞增的連續秒數，不在生成階段取整。M1C-3 於第一個不早於預定到達時間的 SUMO 控制時刻釋放事件。

這項分離可避免離散模擬步長在沒有紀錄的情況下改變隨機到達模型。

## Reproducibility / 可重現性

The schedule depends on the arrival rate, time window, seed, algorithm version, and vehicle-ID prefix. The generator saves a SHA-256 schedule fingerprint.

M1C-3 derives separate arrival and duration seeds from a common master seed. This avoids accidental coupling from consuming a single mutable RNG stream.

排程由到達率、時間區間、亂數種子、演算法版本與車輛 ID 前綴共同決定。生成器另保存 SHA-256 排程指紋。

M1C-3 由共同 master seed 分別產生 arrival 與 duration seed，可避免共用同一亂數流造成的意外耦合。

## CLI examples (Windows CMD) / 命令列範例（Windows CMD）

**Debug-only direct arrival rate（僅供除錯的直接到達率模式）:**

```cmd
python scripts\demand_generator.py --rate-per-s 0.05 --duration-s 600 --seed 10
```

**Offered-load calculation, only after parking parameters have been frozen（依 offered load 計算到達率（須先凍結正式停車時間參數））:**

```cmd
python scripts\demand_generator.py --rho 0.90 --mean-parking-s 1800 --duration-s 7200 --seed 10
```

The `1800` value in the second command is an **illustrative placeholder**, not an approved parking-duration mean. Do **not** treat output from this example as a formal experiment.

**Manifest caveat:** the generator may label a `--rho` invocation as `formal_parameterization=true` to identify its calculation mode. That field alone does **not** certify that the scenario's mean, distribution, warm-up, or other parameters have been formally approved.

第二個指令中的 `1800` **僅是示意數值**，不是已核准的平均停車時間。由此範例產生的結果**不得**當成正式實驗。

**Manifest 注意事項：** 生成器可能以 `formal_parameterization=true` 標記 `--rho` 的計算模式，但此欄位**不代表**平均停車時間、分布、warm-up 或其他情境參數已完成正式核准。

## Outputs / 輸出

A CLI invocation produces a schedule and a manifest（執行 CLI 後會產生到達排程與 manifest）:

```text
validation/demand_generator/
├─ arrivals_seed<seed>.csv
└─ arrival_manifest_seed<seed>.json
```

The manifest stores input rate/load settings, window, seed, expected/observed counts, and SHA-256. It is reproducibility metadata, not evidence that real SUMO insertion succeeded.

Manifest 記錄到達率 / 負載、時間區間、seed、預期 / 實際到達數與 SHA-256。這是可重現性資訊，不代表實際 SUMO 插入已成功。

## Verified unit tests / 已驗證單元測試

Eight tests verify: `rho -> lambda` conversion; same-seed reproducibility; different-seed schedules; increasing bounded arrival times; unique IDs; zero-rate behavior; long-run statistical sanity; and invalid-parameter rejection.

八項測試檢查：`rho -> lambda` 轉換、同 seed 重現、不同 seed 產生不同排程、到達時間嚴格遞增且符合範圍、車輛 ID 唯一、零到達率行為、長期統計合理性，以及不合法參數拒絕。

```cmd
python tests\test_demand_generator.py
```

Archived result: **8/8 PASS**. This does not replace M1C-3's separate live SUMO integration test.

封存結果：**8/8 PASS**。此結果不能取代 M1C-3 的獨立真實 SUMO 整合測試。
