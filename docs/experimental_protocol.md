# Experimental Protocol — Voice-Spoofing Detection for Fraud Prevention

**Version:** 0.1 (draft, skeleton only)
**Freezes at v1.0 = F1 (D1); after F1, changes need a decision.**
**Authors:** Donia Mabrouk (lead), Malak Ben Salem, Khalil Dridi, Iheb Zemzemi (D26).

This draft lists, per section, what Protocol v1.0 must decide. It decides nothing yet. Each owner
fills in their section on their own branch (one PR per author); Donia integrates; all four sign off
(§13). Sources: decision register `docs/decisions/README.md` (D-IDs, H5, H6), Execution Plan v2.1
(`docs/reference/Execution_Plan_v2.1.pdf`, "v2.1" below), SRS v3.0, `docs/threat_model.md`,
`docs/project_log.md` Open items. "Proposed in v2.1" values are proposals, not decisions.

---

## 0. Purpose, scope, deployment scenario

- **Owner:** Donia Mabrouk
- **Reviewer:** all four
- **Must decide:**
  - [ ] Purpose of the protocol: fix every rule before any model exists (D1; v2.1 Stage 3 goal).
  - [ ] Scope statement: FoR-2sec (TTS) → DEEP-VOICE (RVC) generalization; attribution to the
        generation method stays a hypothesis (D8).
  - [ ] Deployment scenario: confirm primary (bank call-center triage) and secondary (executive voice
        message) scenarios (threat model §13 Q1).
  - [ ] Language scope: confirm both datasets are English-only before stating it (threat model §13 Q3).
- **Status:** TODO

## 1. Research questions and hypotheses

- **Owner:** Donia Mabrouk
- **Reviewer:** all four
- **Must decide:**
  - [ ] RQ1 FoR → DEEP-VOICE generalization (proposed in v2.1: RQ1; to confirm).
  - [ ] RQ2 CNN vs baseline, in-domain and externally (proposed in v2.1: RQ2; to confirm).
  - [ ] RQ3 robustness under degradation (proposed in v2.1: RQ3; to confirm).
  - [ ] RQ4 calibration under shift (proposed in v2.1: RQ4; to confirm).
  - [ ] H1 (proposed in v2.1: CNN beats baseline in-domain; to confirm), with its test and stage.
  - [ ] H2 (proposed in v2.1: external EER higher than in-domain; to confirm), with its test and stage.
  - [ ] H3 (proposed in v2.1: calibration worsens externally; to confirm), with its test and stage.
  - [ ] H4 (proposed in v2.1: EER rises with degradation; to confirm), with its test and stage.
  - [ ] Copy H5 and H6 unchanged from the register (below); they are already pre-registered.

  | ID | Hypothesis | Test | Stage |
  |---|---|---|---|
  | H5 | If the CNN relies on MP3 traces, its recall on FAKE_other is clearly lower than on FAKE_mp3. | Subgroup recall on the FoR test split | 11 / 16 |
  | H6 | If the CNN relies on bandwidth, band-limiting REAL clips to ~3.4 kHz raises false FAKE calls. | Robustness test on FoR test REAL clips | 14 |
- **Status:** TODO

## 2. Data and split

- **Owner:** Malak Ben Salem
- **Reviewer:** Donia Mabrouk
- **Must decide:**
  - [ ] Re-split of FoR-2sec (D13).
  - [ ] Grouping: near-duplicate components at 0.95; no group crosses splits (D14).
  - [ ] Stratification by REAL / FAKE_mp3 / FAKE_other (D16).
  - [ ] Ratios (proposed in v2.1: 70/15/15, group-aware; to confirm).
  - [ ] Validation split into val-A (training decisions) and val-B (threshold, calibration) (D9;
        proposed in v2.1: validation halved; to confirm).
  - [ ] Split seed (seed policy, log Open item 0.10).
  - [ ] Automated split checks (proposed in v2.1 Stage 4: no group in two splits, class and subgroup
        proportions, split sizes; to confirm).
  - [ ] DEEP-VOICE file manifest: metadata only (D20; v2.1 Stage 5).
  - [ ] What freeze F2 contains (proposed in v2.1: manifests (path, label, subgroup, group, split,
        hash) for FoR + DEEP-VOICE file manifest, with their hashes; to confirm) (D26 B→C).
- **Status:** TODO

## 3. Preprocessing profile

- **Owner:** Malak Ben Salem
- **Reviewer:** Donia Mabrouk, Iheb Zemzemi
- **Must decide:**
  - [ ] Mono averaging and resampling to 16 kHz, identical everywhere (D18).
  - [ ] What is fixed now (Protocol v1.0) vs in Stage 6 (D18: resampler, settings and tolerance are
        fixed in Stage 6).
  - [ ] Silence detector choice and when it is fixed (proposed in v2.1 Stage 6: energy-based vs a small
        VAD such as silero-vad, recorded as a decision; to confirm); the D17 filter uses the same
        detector (D17).
  - [ ] Pipeline-invariance test: 40 / 44.1 / 48 kHz stereo FoR clips; tolerance (D18).
  - [ ] Silence re-screen after trimming (D16; D5 note on length variation).
  - [ ] What freeze F3 contains (proposed in v2.1 Stage 6: versioned profile config, fixed 2-s input,
        MFCC and log-Mel features; to confirm).
- **Status:** TODO

## 4. Models and training plan

- **Owner:** Donia Mabrouk
- **Reviewer:** Khalil Dridi
- **Must decide:**
  - [ ] Baseline: RBF-SVM on MFCC mean + std, evaluation only (D7); tuning on val-A (proposed in v2.1
        Stage 7; to confirm).
  - [ ] Deployed model: one CNN on log-Mel spectrograms; scope lock (AGENTS.md hard rule 3).
  - [ ] No degradation augmentation in model v1 (D10).
  - [ ] Model selection on val-A only; test split and DEEP-VOICE untouched (D9; v2.1 Stage 9).
  - [ ] 3 seeds on the final CNN configuration (D11).
  - [ ] Seed policy (log Open item 0.10).
  - [ ] W&B logging of every run, with its config (AGENTS.md code rules; v2.1 §4.5).
  - [ ] Compute benchmark before Stage 8 (v2.1 Stage 6; log Open items, Phase 2).
- **Status:** TODO

## 5. Metrics and statistics

- **Owner:** Donia Mabrouk
- **Reviewer:** Khalil Dridi
- **Must decide:**
  - [ ] Positive class = spoof (D4; AGENTS.md hard rule 5).
  - [ ] Score-level metrics: EER, ROC-AUC on the continuous score (D4).
  - [ ] Decision-level metrics at the frozen threshold, forced-binary and on the non-deferred subset
        (D4).
  - [ ] 3-way confusion matrix, coverage / deferral rate, class counts, FPR / FNR (D4; FR-13, FR-14).
  - [ ] 95% bootstrap CIs, clustered by source speaker for DEEP-VOICE (D11).
  - [ ] How the 3 seeds are reported (D11).
- **Status:** TODO

## 6. Risk policy and calibration fit

- **Owner:** Donia Mabrouk
- **Reviewer:** Khalil Dridi, Iheb Zemzemi
- **Must decide:**
  - [ ] Fitted on FoR only, before the ModelBundle freeze (D2).
  - [ ] Fitted on val-B (D9).
  - [ ] Operating threshold at the FoR-val EER point (D12; proposed in v2.1: val-B EER point; to
        confirm).
  - [ ] Exact deferral criterion: uncertain band (D12) and maximum deferral rate (proposed in v2.1
        Stage 3; value to set).
  - [ ] LOW / MEDIUM / HIGH mapping (FR-07; v2.1 Stage 10).
  - [ ] Calibration method (proposed in v2.1: temperature or Platt scaling; to confirm) (FR-18).
  - [ ] Confidence definition in [0.00, 1.00] (FR-06).
  - [ ] What freeze F4 contains (proposed in v2.1 Stage 12: checkpoint + preprocessing profile + risk
        policy as one versioned bundle with hashes; to confirm) (D2; AGENTS.md hard rule 2).
- **Status:** TODO

## 7. FoR internal test (Stage 11)

- **Owner:** Donia Mabrouk
- **Reviewer:** Khalil Dridi
- **Must decide:**
  - [ ] Run once, baseline and CNN on the same FoR test split (v2.1 Stage 11; FR-12).
  - [ ] All D4 metrics, with class counts (D4; FR-14).
  - [ ] H5: subgroup recall FAKE_mp3 vs FAKE_other, and what counts as "clearly lower" (H5).
- **Status:** TODO

## 8. External run (Stage 13)

- **Owner:** Khalil Dridi
- **Reviewer:** all four
- **Must decide:**
  - [ ] Evaluation unit: 2-s windows (primary), file-level mean score (secondary) (D5).
  - [ ] Speech-window filter with the frozen silence detector, and its threshold (D17).
  - [ ] Filtered (primary) and unfiltered (sensitivity) views from the same run; drop counts per class
        and per speaker (D17).
  - [ ] Per-speaker table (8 rows) and speaker average (D19).
  - [ ] What is stored: per-sample scores (v2.1 Stage 13); file format per §11 (D26 C→D).
  - [ ] Single-run rule: exactly one run of the frozen bundle, reported once (AGENTS.md hard rule 1;
        FR-15).
  - [ ] Reporting next to the in-domain result, with the gap, RVC-only scope and 87.5% FAKE imbalance
        stated (FR-16; D8).
  - [ ] Governance: decision on how the external-run code joins the allowlist of
        `tests/governance/test_deepvoice_access.py`, before Stage 13 (log Open items).
- **Status:** TODO

## 9. Robustness (Stage 14)

- **Owner:** Malak Ben Salem
- **Reviewer:** Khalil Dridi
- **Must decide:**
  - [ ] FoR test split only; no DEEP-VOICE (D3).
  - [ ] Conditions: noise, compression, bandwidth reduction (FR-17).
  - [ ] Levels per condition (FR-17 acceptance: clean → mild → moderate → severe).
  - [ ] H6: band-limiting REAL clips to ~3.4 kHz (H6; proposed in v2.1 Stage 3: telephone band; to
        confirm).
  - [ ] Applied through the same preprocessing profile (D26 B→Stage 14).
- **Status:** TODO

## 10. Calibration and error analysis plans (Stages 15–16)

- **Owner:** Khalil Dridi
- **Reviewer:** Donia Mabrouk
- **Must decide:**
  - [ ] Reliability diagram and ECE, before and after calibration (FR-18).
  - [ ] Run on the FoR test split and on the stored DEEP-VOICE scores; no re-run (v2.1 Stage 15).
  - [ ] Whether the uncertain band still means something under shift (v2.1 Stage 15; RQ4).
  - [ ] Error analysis by subgroup, speaker, confidence level and deferral, linked to threats T1–T7
        (v2.1 Stage 16).
- **Status:** TODO

## 11. Interfaces

- **Owner:** Iheb Zemzemi
- **Reviewer:** Donia Mabrouk, Malak Ben Salem, Khalil Dridi
- **Must decide:**
  - [ ] B→C: manifest columns (path, label, subgroup, group, split, hash) and the preprocessing
        function's input / output (sample rate, length, feature shapes) (D26).
  - [ ] C→D: ModelBundle format and `score(audio) → score`, plus the per-sample stored-score file
        format (D26).
  - [ ] C→E: API response `{prediction, confidence, risk_level}` plus model / profile / policy
        versions, and how the bundle is loaded and its hash verified (D26).
  - [ ] B→Stage 14: degradation conditions and levels, applied through the same preprocessing profile
        (D26).
- **Status:** TODO

## 12. Freeze points F1–F4

- **Owner:** Donia Mabrouk
- **Reviewer:** all four
- **Must decide:**
  - [ ] F1 = this protocol at v1.0, Stage 3 (D1; v2.1 §6).
  - [ ] F2 = dataset split + manifests, Stage 5 (v2.1 §6).
  - [ ] F3 = preprocessing profile, Stage 6 (v2.1 §6).
  - [ ] F4 = ModelBundle, Stage 12 (D2; v2.1 §6).
  - [ ] After a freeze, the frozen item changes only through a new decision (v2.1 §6; AGENTS.md hard
        rule 6).
- **Status:** TODO

## 13. Sign-off

| Member | Role | Date | PR |
|---|---|---|---|
| Donia Mabrouk | Lead; §0, 1, 4–7, 12 | | |
| Malak Ben Salem | §2, 3, 9 | | |
| Khalil Dridi | §8, 10 | | |
| Iheb Zemzemi | §11 | | |

## 14. Change log

| Version | Date | Change | PR |
|---|---|---|---|
| 0.1 | 2026-10-12 | Skeleton: sections, owners, reviewers, "Must decide" items. No content. | |
