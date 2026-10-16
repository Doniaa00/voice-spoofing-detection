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

### Tests (`tests/evaluation/test_metrics.py`)
Each case has its hand calculation as a comment.

| Point | Test |
|---|---|
| Conventions, exact-match rule | `test_perfect_separation` (AUC 1, EER 0, threshold 0.8), `test_reversed_scores` (AUC 0, EER 1), `test_hand_calculated_case` (AUC 0.75, EER 0.5, threshold 0.6) |
| (a) agreement with scikit-learn | `test_roc_auc_matches_sklearn_on_random_scores` (200 scores, seed 2026, tolerance 1e-12) |
| (b) interpolation | `test_all_scores_equal` (EER 0.5 between the two only ROC points), `test_interpolated_threshold_between_roc_points` (EER 0.5, threshold 0.7 between 0.9 and 0.5) |
| (c) finite threshold | `test_all_scores_equal` (the +∞ threshold is replaced; result 0.5, asserted finite) |
| (d) fail loudly | `test_invalid_input_raises` (each invalid input, for both functions) |
| Ranking properties | `test_metrics_invariant_under_monotonic_transform` (logistic transform: calibration such as Platt scaling in Stage 10 is monotonic and must not change score-level metrics), `test_auc_of_negated_scores_is_complement` (AUC(s) + AUC(−s) = 1) |
