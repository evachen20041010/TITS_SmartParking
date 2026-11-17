# Historical Source Archives / 歷史研究原始封存檔

## Purpose / 目的

This directory stores original historical source packages. These files are evidence of earlier implementations, not the source directory for current T-ITS Experiment 1 development.

本目錄保存早期研究的原始程式封存檔，屬於歷史實作證據，不是目前 T-ITS Experiment 1 的開發目錄。

## Archive inventory / 封存檔清單

### `sumo_parking_ICCE_2026_original.zip`

Original source package for the ICCE-TW 2026 parking simulation. The reproducible working snapshot and reproduction scripts are maintained separately in `01_ICCE_2026_Frozen/`.

ICCE-TW 2026 停車模擬的原始程式封存檔。可重現的工作快照與重現腳本另存於 `01_ICCE_2026_Frozen/`。

### `SUMO_Guided_Parking_2025_prototype.zip`

Earlier guided-parking prototype retained for historical comparison. It is **not** the validated Experiment 1 simulator and must not be treated as a formal T-ITS baseline.

早期導引停車原型，保留作為研究歷程比較。它**不是**目前已驗證的 Experiment 1 模擬器，也不得當成正式 T-ITS 基準。

### `archive_manifest.csv`

This file exists but is **currently empty** in the supplied project snapshot. Do not present it as a completed archive inventory. A future provenance review may fill in names, versions, origins, and checksums without changing the original archives.

目前提供的專案快照中確實存在此檔，但其內容**仍為空白**，因此不能稱為已完成的封存清冊。未來可在不修改原始封存檔的前提下，補上檔名、版本、來源與校驗碼等資訊。

## Preservation rule / 保存規則

Do not edit or overwrite original ZIP contents to make them match newer analyses, KPI definitions, or publications. Put all recovered files, scripts, and comparison logs in separate directories.

The original archive ZIP files are subject to the repository's Git LFS rules. Verify LFS availability when cloning the repository on another machine.

不得為了符合新的分析結果、KPI 定義或論文描述，而修改或覆蓋原始 ZIP。復原後的檔案、腳本及比對紀錄應放在獨立目錄。

原始 ZIP 受 repository 的 Git LFS 規則管理；在其他電腦複製專案時，請確認 LFS 檔案已正確取得。

## Related documentation / 相關文件

- [ICCE-TW frozen baseline and reproduction](../01_ICCE_2026_Frozen/README_ICCE.md)

  [ICCE-TW 凍結基準與重現說明](../01_ICCE_2026_Frozen/README_ICCE.md)
- [Experiment 1 implementation](../02_Exp1_FreeSearch_v2/README.md)

  [Experiment 1 實作說明](../02_Exp1_FreeSearch_v2/README.md)
