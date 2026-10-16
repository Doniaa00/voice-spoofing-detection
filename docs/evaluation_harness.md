# Evaluation harness

The evaluation harness is one shared metrics module, `src/evaluation/metrics.py`, used by the
MFCC/SVM baseline (Stage 7), the CNN (Stages 8–11) and the single DEEP-VOICE external run
(Stage 13). Because every result comes from the same code, numbers are comparable across models
and datasets (FR-12), and the positive class is the same everywhere: spoof (D4, Protocol v1.0 §5).
The harness is built in five steps; this document grows with each one.

## Step 1: EER and ROC-AUC

### Conventions
- Labels: `1` = spoof (positive class), `0` = bonafide.
- Scores: higher score = more likely spoof.
- Decision rule: predict spoof if `score >= threshold`.

`roc_auc(labels, scores) -> float` returns the area under the ROC curve, computed by
`sklearn.metrics.roc_auc_score`.

`eer(labels, scores) -> tuple[float, float]` returns `(eer, threshold)`.

### EER method and threshold rule
1. Build the ROC with `sklearn.metrics.roc_curve(..., drop_intermediate=False)` and set
   FNR = 1 − TPR.
2. Find the first ROC index where FPR ≥ FNR. The previous index always exists, because the ROC
   starts at FPR = 0, FNR = 1.
3. If FPR = FNR at that index, that value is the EER and that ROC threshold is the threshold.
4. Otherwise, treat FPR and FNR as straight lines between the previous point and this one. The EER
   is where they cross, at weight `w = gap_before / (gap_before + gap_after)`, where
   `gap_before = FNR − FPR` at the previous point and `gap_after = FPR − FNR` at this point. The
   threshold is interpolated between the two ROC thresholds with the same weight `w`.
5. scikit-learn's first ROC threshold is +∞. It is replaced by the highest score, so the returned
   threshold is always finite.

### Why (team reasoning)
- **(a) scikit-learn for the ROC.** It is widely used and tested, so we do not maintain our own
  ROC code.
- **(b) Interpolation.** On small sets, such as the recordings of one DEEP-VOICE speaker, the ROC has
  few points. Without interpolation, the EER would jump between them.
- **(c) A finite threshold.** Stage 10 stores the threshold in the risk-policy file of the
  ModelBundle, and +∞ cannot be stored or applied meaningfully there.
- **(d) Fail loudly** (AGENTS.md code rules). Both functions raise `ValueError` with a clear
  message on any of these inputs: labels and scores of different lengths, empty input, only one
  class, labels other than 0/1, or NaN/infinite scores.

### Limitation
The EER is an interpolated rate. Applying the returned threshold to the same data gives the error
rates of a neighbouring ROC point, not exactly the EER. For example, in the 0.7 test, a threshold
of 0.7 gives FPR 0 and FNR 0.5, while the EER is 0.5. On large sets (val-B ≈ 1,330 clips) the
gap is small; on small sets (one DEEP-VOICE speaker) it can be large. Stage 11 therefore reports
the realised FPR/FNR at the frozen threshold, and never reports the EER as the error rate at that
threshold.

### Tests (`tests/evaluation/test_metrics.py`)
Each case has its hand calculation as a comment.

| Point | Test |
|---|---|
| Conventions, exact-match rule | `test_perfect_separation` (AUC 1, EER 0, threshold 0.8), `test_reversed_scores` (AUC 0, EER 1), `test_hand_calculated_case` (AUC 0.75, EER 0.5, threshold 0.6) |
| (a) agreement with scikit-learn | `test_roc_auc_matches_sklearn_on_random_scores` (200 scores, seed 2026, tolerance 1e-12) |
| (b) interpolation | `test_all_scores_equal` (EER 0.5 between the two only ROC points), `test_interpolated_threshold_between_roc_points` (EER 0.5, threshold 0.7 between 0.9 and 0.5) |
| Limitation: realised rates | `test_realised_rates_at_interpolated_threshold` (threshold 0.7 gives FPR 0.0, FNR 0.5) |
| (c) finite threshold | `test_all_scores_equal` (the +∞ threshold is replaced; result 0.5, asserted finite) |
| (d) fail loudly | `test_invalid_input_raises` (each invalid input, for both functions) |
| Ranking properties | `test_metrics_invariant_under_monotonic_transform` (logistic transform: calibration such as Platt scaling in Stage 10 is monotonic and must not change score-level metrics), `test_auc_of_negated_scores_is_complement` (AUC(s) + AUC(−s) = 1) |

## Step 2: decision-level metrics at a threshold

### Conventions
- Same labels and scores as Step 1; positive class = spoof (D4, Protocol v1.0 §5).
- Forced binary decision: predict spoof if `score >= threshold` (no uncertain band at this step).

`binary_metrics(labels, scores, threshold) -> BinaryMetrics` returns a frozen dataclass with the
counts `tp, fp, tn, fn, n_spoof, n_bonafide` (int) and the rates `accuracy, precision, recall, f1,
fpr, fnr` (float, fractions in [0, 1]).

### Formulas
| Rate | Formula |
|---|---|
| accuracy | (TP + TN) / N |
| precision | TP / (TP + FP) |
| recall | TP / (TP + FN) |
| F1 | 2TP / (2TP + FP + FN) |
| FPR | FP / (FP + TN) |
| FNR | FN / (FN + TP) |

Any rate whose denominator is 0 is `NaN`, never 0, and no warning is emitted. The threshold must
be a finite number, otherwise `ValueError` is raised. All Step 1 input checks still apply, except
that a single class is allowed.

### Why (team reasoning)
- **(a) Same `>=` rule as the EER threshold.** A threshold returned by `eer()` (and later the
  frozen risk-policy threshold) means the same thing when it is applied here.
- **(b) NaN, not 0, for undefined rates.** A 0 looks like a real result (for example "precision 0"
  when nothing is predicted spoof), and scikit-learn's default silently returns 0 in that case.
  NaN keeps the undefined case visible.
- **(c) One class allowed.** H5 subgroup recall is computed on spoof-only subsets, so
  `binary_metrics` must accept them; rates that need the missing class come out as NaN. EER and
  AUC still need both classes, so `roc_auc` and `eer` keep raising on a single class.
- **(d) F1 from counts.** 2TP / (2TP + FP + FN) is defined in more cases than 2PR / (P + R): for
  example it gives 0 when nothing is predicted spoof but spoofs exist, where precision is NaN.
- **(e) Counts always returned.** Every rate can be recomputed and checked from the counts
  (FR-14).

### Tests (`tests/evaluation/test_metrics.py`)
Each case has its hand calculation as a comment.

| Point | Test |
|---|---|
| Formulas, hand case | `test_binary_metrics_hand_case` (TP = FP = TN = FN = 1; all six rates 0.5) |
| (a) `>=` rule | `test_binary_metrics_tie_counts_as_spoof` (a score equal to the threshold is spoof), `test_binary_metrics_at_eer_threshold` (FPR = FNR = 0.5 at the `eer()` threshold) |
| (b) NaN, (d) F1 from counts | `test_binary_metrics_nothing_predicted_spoof` (precision NaN, F1 0, recall 0, FNR 1) |
| (c) one class | `test_binary_metrics_single_class` (recall 2/3, FPR NaN, `n_bonafide` 0), `test_score_metrics_still_require_both_classes` (`roc_auc`, `eer` still raise) |
| Agreement with scikit-learn, (e) counts | `test_binary_metrics_consistent_with_sklearn` (200 scores, seed 2026: counts sum to N, FNR = 1 − recall, counts match `confusion_matrix`, precision/recall/F1 match `precision_recall_fscore_support`) |
| Fail loudly | `test_binary_metrics_invalid_threshold_raises` (NaN, ±∞, string, None), `test_binary_metrics_invalid_input_raises` (lengths, empty, bad labels, NaN scores) |
