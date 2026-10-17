# Risk policy

The risk policy turns a raw detector score into the output the system reports: one of
authentic / synthetic / uncertain (FR-05), a confidence (FR-06) and a LOW/MEDIUM/HIGH risk level
(FR-07). It is part of the ModelBundle (D2, AGENTS.md hard rule 2): fitted on FoR val-B only, for
the bundle seed, and frozen in F4 before the external run (Protocol v1.0 §6; D9, D12). It lives in
`src/risk/`, the Risk & Confidence service of the shared core (SDD Fig. 1), so the API and the
research notebooks apply the same rule. It is built in two steps, one section each below; Step R2
(threshold, band width, confidence and risk level) follows.

Step R1 is tested on synthetic scores only; no dataset is read.

## Step R1: band rule in the core, and Platt calibration

### Conventions
- Labels: `1` = spoof (positive class), `0` = bonafide (D4, Protocol v1.0 §5).
- Scores: higher score = more likely spoof. Calibrated output `p` = P(spoof).
- Band rule: unchanged from the evaluation harness (Step 3 of
  [evaluation_harness.md](evaluation_harness.md)); it now lives in `src/risk/decisions.py`.
- Calibration: Platt scaling, 2 parameters, fitted on val-B (Protocol v1.0 §6, FR-18).

`src/risk/decisions.py` holds `AUTHENTIC`, `SYNTHETIC`, `UNCERTAIN`, `DECISIONS`,
`three_way_decisions` and the input checks they share with the harness. `src/evaluation/metrics.py`
imports and re-exports them, so existing imports keep working and both names refer to the same
objects.

`src/risk/calibration.py` holds:
- `PlattCalibration(a, b, n_spoof, n_bonafide)`, a frozen dataclass. `transform(scores)` returns
  `p = 1 / (1 + exp(-(a*s + b)))`, computed so that `exp` is only taken of non-positive numbers
  (no overflow for large `|a*s + b|`). The constructor raises `ValueError` if `a` or `b` is not
  finite, if `a <= 0`, or if a count is not an int ≥ 1.
- `fit_platt(labels, scores) -> PlattCalibration`.

### Method
1. Validate the input with the harness rules: labels 0/1, both classes present, finite scores,
   equal lengths, non-empty; otherwise `ValueError`.
2. Smoothed targets (Platt 1999): `t_spoof = (N_spoof + 1) / (N_spoof + 2)` for spoof rows,
   `t_bonafide = 1 / (N_bonafide + 2)` for bonafide rows.
3. Minimise the cross-entropy `Σ log(1 + exp(z)) − t·z`, with `z = a*s + b`, by Newton's method:
   gradient `Σ (p − t)·(s, 1)`, Hessian `Σ p(1 − p)·(s, 1)(s, 1)ᵀ` plus `1e-12` on the diagonal
   (Lin, Lin and Weng 2007).
4. Start from `a = 0`, `b = log((N_spoof + 1) / (N_bonafide + 1))`, so the starting `p` is the
   (smoothed) class prior.
5. Each Newton step is shortened by a backtracking line search (halving, sufficient decrease
   constant 1e-4) until the loss decreases.
6. Stop when the gradient norm is < 1e-10. After 100 iterations without that, or if the line search
   fails, `ValueError`.
7. If the fitted `a <= 0`, `ValueError`.

### Why (team reasoning)
- **(a) Core / research layering (SDD Fig. 1).** The API container has the Risk & Confidence service
  but not the Evaluation service, so the band rule cannot live in `src/evaluation`. It moves to
  `src/risk`, `src/risk` never imports `src/evaluation`, and the harness re-exports it. There is
  still one definition of the band rule, and the deployed system does not depend on research code.
- **(b) Smoothed targets.** FoR in-domain may be separable on val-B. Plain logistic regression then
  has no finite solution: `a` grows without limit, every `p` becomes 0 or 1, the confidence is 1.00
  everywhere and the uncertain band collapses. The smoothed targets keep `a` and `b` finite and `p`
  strictly inside (0, 1).
- **(c) Newton in NumPy.** The problem has 2 parameters, so a 2 × 2 Newton solve is exact and fast.
  It needs no new dependency, and the fit is fully specified by this note.
- **(d) `a > 0` enforced.** The calibration is then strictly increasing, so it never changes the
  ranking of scores: ROC-AUC and EER are identical on `s` and on `p`, and score-level results stay
  comparable with the uncalibrated ones. A fit with `a <= 0` would mean the scores rank spoof
  below bonafide on val-B; that is an error to investigate, not something to calibrate away.

### Tests (`tests/risk/`)
Each case has its hand reasoning as a comment.

| Point | Test |
|---|---|
| (a) one band rule | `test_metrics_reexports_the_core_band_rule` (`metrics.three_way_decisions is decisions.three_way_decisions`) |
| (a) layering | `test_risk_does_not_import_evaluation` (parses every `src/risk/*.py`; no import of `src.evaluation`) |
| (b) targets | `test_smoothed_targets` (N_spoof = N_bonafide = 2 → 3/4 and 1/4) |
| Method, (c) Newton | `test_parameter_recovery` (5,000 scores ~ N(0, 1), labels ~ Bernoulli(sigmoid(2s − 1)), seed 2026: a = 2 ± 0.15, b = −1 ± 0.15) |
| (b) separable data | `test_separable_data_gives_finite_parameters` (labels [0,0,0,1,1,1], scores [0.1 … 0.9]: finite a > 0, finite b, every p in (0, 1)) |
| (d) ranking kept | `test_calibration_is_monotonic_and_keeps_score_metrics` (200 scores, seed 2026: p strictly increasing; `eer` and `roc_auc` of p equal those of s, tolerance 1e-12) |
| (d) `a > 0` | `test_reversed_scores_raise` |
| Numerical stability | `test_transform_extreme_scores_without_warnings` (scores −1e6, 0, 1e6 with warnings as errors → 0, 0.5, 1) |
| Fail loudly | `test_invalid_input_raises` (one class, NaN score, length mismatch, empty) |

## References
- [doc] Platt, J. (1999). Probabilistic outputs for support vector machines and comparisons to
  regularized likelihood methods.
- [doc] Lin, H.-T., Lin, C.-J. and Weng, R. C. (2007). A note on Platt's probabilistic outputs for
  support vector machines.
