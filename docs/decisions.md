# Decision Log

Approved decisions from the Project Readiness Audit (Sept 2026). These override the Proposal and the
Execution Plan where they differ. Any change needs a new entry with a reason and team approval.

| ID | Decision | Status |
|---|---|---|
| D1 | Write Experimental Protocol v1.0 after the dataset audit; freeze it before training | Approved |
| D2 | Fit the risk policy (thresholds, uncertain band) and calibration on FoR validation **before** the ModelBundle freeze. The DEEP-VOICE run comes after. Supersedes the Exec Plan order (Phase 5 before Phases 6/9). | Approved |
| D3 | No robustness evaluation on DEEP-VOICE. Robustness runs on the FoR test split only (FR-17). Supersedes Exec Plan Phase 9 "optionally DEEP-VOICE". | Approved |
| D4 | Metrics: score-level (EER, ROC-AUC) on the continuous score; decision-level (accuracy, precision, recall, F1) at the frozen threshold, both forced-binary and on the non-deferred subset; 3-way confusion matrix; coverage/deferral rate; class counts; FPR/FNR; 95% CIs. Positive class = spoof. | Approved |
| D5 | Evaluation unit: 2 s windows (primary), file-level mean score (secondary) | **Confirmed** by the Stage 1 audit (DEEP-VOICE files 79–600 s; `docs/dataset_audit.md` §7). Raw FoR clips need no pad/crop (all 2.0 s); whether silence trimming introduces length variation is decided in Stage 6. |
| D6 | DEEP-VOICE audit is metadata-only (counts, headers, hashes, filenames, CSV schema). No listening, spectrograms, or feature stats. Supersedes Exec Plan Phase 2 "explore both datasets". | Approved |
| D7 | Baseline = RBF-SVM on MFCC mean + std | Approved |
| D8 | Research question narrowed to cross-dataset FoR (TTS) → DEEP-VOICE (RVC) generalization. Attribution to "generation method" is a hypothesis only. | Approved |
| D9 | Split FoR validation into val-A (training decisions) and val-B (threshold, calibration) if the size permits | **Applies** (val-B ≈ 665 clips per class ≥ 500; `docs/dataset_audit.md` §7) |
| D10 | No degradation augmentation in ModelBundle v1 | Approved |
| D11 | 3 seeds on the final CNN config; bootstrap 95% CIs, clustered by source speaker for DEEP-VOICE | Approved |
| D12 | Operating threshold at the FoR-val EER point, plus a fixed deferral policy (exact criterion in Protocol v1.0) | Approved |
| D13 | Official FoR split vs re-split: decided by the pre-registered rule in `docs/dataset_audit.md` §0 | **Re-split** (no packaged split; `docs/dataset_audit.md` §7) |
| D14 | Grouping fallback = duplicate hashing + near-duplicate components, if no speaker metadata | **Groups at 0.95** (no speaker metadata; largest group 6 clips = 0.03%; sanity check passed, 0 PCM pairs; `docs/dataset_audit.md` §7) |
| D15 | Official Python version = 3.13 (Colab runtime 3.13.15; results come from Colab). Local development on Python 3.14 is allowed for editing and quick tests. `requirements.txt` must install on both 3.13 and 3.14; CI tests on 3.13. | Approved |
| D16 | FoR codec-history imbalance (85% of FAKE vs 0% of REAL clips have an MP3 step): no data changes; re-split stratified by REAL / FAKE_mp3 / FAKE_other; the imbalance is recorded as a limitation; silence is re-screened after trimming (Stage 6). | Approved (Stage 1 audit, 2026-10-04) |
| D17 | DEEP-VOICE speech-window filter using the frozen silence detector. Its threshold is fixed in Protocol v1.0, before the external run. Filtered (primary) and unfiltered (sensitivity) views are computed in the same single run. Drop counts are reported per class and per speaker. | Approved (2026-10-04) |
| D18 | Preprocessing averages channels to mono and resamples to 16 kHz, identically everywhere. Stage 6 adds a pipeline-invariance test on FoR clips converted to 40, 44.1 and 48 kHz stereo. Resampler, settings and tolerance are fixed in Stage 6. | Approved (2026-10-04) |
| D19 | External (DEEP-VOICE) results include a per-speaker table (8 rows) and a speaker average as a secondary summary. | Approved (2026-10-04) |
| D20 | Permitted DEEP-VOICE accesses before the external run are **only**: download, zip hash, unzip, listing paths / extensions / sizes / byte hashes, and `src/audit/deepvoice_metadata_audit.py`. Nothing reads audio content. Extends D6 to cover the download steps; `CLAUDE.md` hard rule 1 matches. | Approved (2026-10-04) |
| D21 | Datasets are pinned: FoR-2sec HF revision `ff8c82c79e7bbefef811941bac9775c9328e9055` and DEEP-VOICE zip SHA-256 `8cb258530daa2bb678121f3b276313a4d56fc638280bfd276a610dd8f732bdcf` in `configs/audit.yaml`. The notebook refuses unpinned or mismatched data. Changing a pin requires a new decision entry. | Approved (2026-10-04) |

## Pre-registered hypotheses

Written before any model exists. Each is tested once, at the stage named, and reported whatever the outcome.

| ID | Hypothesis | Test | Stage |
|---|---|---|---|
| H5 | If the CNN relies on MP3 traces, its recall on FAKE_other is clearly lower than on FAKE_mp3. | Subgroup recall on the FoR test split | 11 / 16 |
| H6 | If the CNN relies on bandwidth, band-limiting REAL clips to ~3.4 kHz raises false FAKE calls. | Robustness test on FoR test REAL clips | 14 |
