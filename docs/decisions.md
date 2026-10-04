# Decision Log

Approved decisions from the Project Readiness Audit (Sept 2026). These override the Proposal and the
Execution Plan where they differ. Any change needs a new entry with a reason and team approval.

| ID | Decision | Status |
|---|---|---|
| D1 | Write Experimental Protocol v1.0 after the dataset audit; freeze it before training | Approved |
| D2 | Fit the risk policy (thresholds, uncertain band) and calibration on FoR validation **before** the ModelBundle freeze. The DEEP-VOICE run comes after. Supersedes the Exec Plan order (Phase 5 before Phases 6/9). | Approved |
| D3 | No robustness evaluation on DEEP-VOICE. Robustness runs on the FoR test split only (FR-17). Supersedes Exec Plan Phase 9 "optionally DEEP-VOICE". | Approved |
| D4 | Metrics: score-level (EER, ROC-AUC) on the continuous score; decision-level (accuracy, precision, recall, F1) at the frozen threshold, both forced-binary and on the non-deferred subset; 3-way confusion matrix; coverage/deferral rate; class counts; FPR/FNR; 95% CIs. Positive class = spoof. | Approved |
| D5 | Evaluation unit: 2 s windows (primary), file-level mean score (secondary) | **Provisional — pending dataset audit** |
| D6 | DEEP-VOICE audit is metadata-only (counts, headers, hashes, filenames, CSV schema). No listening, spectrograms, or feature stats. Supersedes Exec Plan Phase 2 "explore both datasets". | Approved |
| D7 | Baseline = RBF-SVM on MFCC mean + std | Approved |
| D8 | Research question narrowed to cross-dataset FoR (TTS) → DEEP-VOICE (RVC) generalization. Attribution to "generation method" is a hypothesis only. | Approved |
| D9 | Split FoR validation into val-A (training decisions) and val-B (threshold, calibration) if the size permits | Approved, conditional |
| D10 | No degradation augmentation in ModelBundle v1 | Approved |
| D11 | 3 seeds on the final CNN config; bootstrap 95% CIs, clustered by source speaker for DEEP-VOICE | Approved |
| D12 | Operating threshold at the FoR-val EER point, plus a fixed deferral policy (exact criterion in Protocol v1.0) | Approved |
| D13 | Official FoR split vs re-split: decided by the pre-registered rule in `docs/dataset_audit.md` §0 | **Deferred to audit** |
| D14 | Grouping fallback = duplicate hashing + near-duplicate components, if no speaker metadata | Approved as fallback, pending audit |
| D15 | Official Python version = 3.13 (Colab runtime 3.13.15; results come from Colab). Local development on Python 3.14 is allowed for editing and quick tests. `requirements.txt` must install on both 3.13 and 3.14; CI tests on 3.13. | Approved |
