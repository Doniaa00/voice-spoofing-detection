"""Step 1 evaluation harness tests: EER and ROC-AUC on small synthetic arrays (no dataset access).

Convention: label 1 = spoof (positive), 0 = bonafide; higher score = more spoof; spoof if
score >= threshold. In the hand calculations, ROC rows are (threshold, FPR, TPR, FNR) as returned by
roc_curve(drop_intermediate=False), with sklearn's +inf first threshold.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from src.evaluation.metrics import eer, roc_auc

LABELS = [0, 0, 1, 1]


def test_perfect_separation():
    # scores [0.1, 0.2, 0.8, 0.9]: every spoof outranks every bonafide -> AUC = 4/4 pairs = 1.0.
    # ROC: (inf,0,0,1) (0.9,0,.5,.5) (0.8,0,1,0) (0.2,.5,1,0) (0.1,1,1,0).
    # First FPR >= FNR at threshold 0.8: FPR = FNR = 0 -> EER 0.0, threshold 0.8.
    scores = [0.1, 0.2, 0.8, 0.9]
    assert roc_auc(LABELS, scores) == 1.0
    rate, threshold = eer(LABELS, scores)
    assert rate == 0.0
    assert threshold == pytest.approx(0.8)


def test_reversed_scores():
    # scores [0.9, 0.8, 0.2, 0.1]: every bonafide outranks every spoof -> AUC = 0/4 = 0.0.
    # ROC: (inf,0,0,1) (0.9,.5,0,1) (0.8,1,0,1) (0.2,1,.5,.5) (0.1,1,1,0).
    # First FPR >= FNR at threshold 0.8: FPR = FNR = 1 -> EER 1.0, threshold 0.8.
    scores = [0.9, 0.8, 0.2, 0.1]
    assert roc_auc(LABELS, scores) == 0.0
    rate, threshold = eer(LABELS, scores)
    assert rate == 1.0
    assert threshold == pytest.approx(0.8)


def test_all_scores_equal():
    # All 4 pairs tie, each counts 1/2 -> AUC 0.5.
    # ROC: (inf,0,0,1) (0.5,1,1,0). First FPR >= FNR at index 1 with FPR 1 > FNR 0, so interpolate:
    # gap before = 1 - 0 = 1, gap after = 1 - 0 = 1, w = 1/2 -> EER = 0 + 1/2 * (1 - 0) = 0.5.
    # Threshold: inf is replaced by the highest score 0.5 -> 0.5 + 1/2 * (0.5 - 0.5) = 0.5 (finite).
    scores = [0.5, 0.5, 0.5, 0.5]
    assert roc_auc(LABELS, scores) == 0.5
    rate, threshold = eer(LABELS, scores)
    assert rate == pytest.approx(0.5)
    assert threshold == pytest.approx(0.5)
    assert math.isfinite(threshold)


def test_hand_calculated_case():
    # scores [0.1, 0.6, 0.4, 0.9]. Pairs (spoof, bonafide): 0.4>0.1 yes, 0.4>0.6 no, 0.9>0.1 yes,
    # 0.9>0.6 yes -> AUC = 3/4 = 0.75.
    # ROC: (inf,0,0,1) (0.9,0,.5,.5) (0.6,.5,.5,.5) (0.4,.5,1,0) (0.1,1,1,0).
    # First FPR >= FNR at threshold 0.6: FPR = FNR = 0.5 -> EER 0.5, threshold 0.6.
    scores = [0.1, 0.6, 0.4, 0.9]
    assert roc_auc(LABELS, scores) == pytest.approx(0.75)
    rate, threshold = eer(LABELS, scores)
    assert rate == pytest.approx(0.5)
    assert threshold == pytest.approx(0.6)


def test_interpolated_threshold_between_roc_points():
    # labels [0,1,1], scores [0.5,0.4,0.9].
    # ROC: (inf,0,0,1) (0.9,0,.5,.5) (0.5,1,.5,.5) (0.4,1,1,0).
    # First FPR >= FNR at threshold 0.5 (FPR 1 > FNR .5). Previous point threshold 0.9 (FPR 0, FNR .5).
    # gap before = .5 - 0 = .5, gap after = 1 - .5 = .5, w = 1/2:
    # EER = 0 + 1/2 * (1 - 0) = 0.5; threshold = 0.9 + 1/2 * (0.5 - 0.9) = 0.7.
    rate, threshold = eer([0, 1, 1], [0.5, 0.4, 0.9])
    assert rate == pytest.approx(0.5)
    assert threshold == pytest.approx(0.7)


def test_realised_rates_at_interpolated_threshold():
    # Same data. At threshold 0.7 (spoof if score >= 0.7) only 0.9 is predicted spoof:
    # bonafide 0.5 < 0.7 -> no false positive -> FPR 0/1 = 0.0;
    # spoofs 0.4 (missed) and 0.9 (caught) -> FNR 1/2 = 0.5.
    # The realised rates belong to a neighbouring ROC point, not to the interpolated EER 0.5.
    labels = np.array([0, 1, 1])
    scores = np.array([0.5, 0.4, 0.9])
    _, threshold = eer(labels, scores)
    predicted_spoof = scores >= threshold
    fpr = predicted_spoof[labels == 0].mean()
    fnr = (~predicted_spoof[labels == 1]).mean()
    assert fpr == 0.0
    assert fnr == 0.5


def _random_case(n: int = 200):
    rng = np.random.default_rng(2026)
    labels = rng.integers(0, 2, size=n)
    scores = rng.normal(size=n) + labels  # spoof scores shifted up, so AUC is well above 0.5
    return labels, scores


def test_roc_auc_matches_sklearn_on_random_scores():
    # 200 random scores, seed 2026; must agree with sklearn to 1e-12.
    labels, scores = _random_case()
    assert abs(roc_auc(labels, scores) - roc_auc_score(labels, scores)) <= 1e-12


def test_metrics_invariant_under_monotonic_transform():
    # A strictly increasing transform keeps the ranking, so the ROC (FPR, TPR) points are identical
    # and EER and AUC must not change. Reason: calibration (Platt, Stage 10) is monotonic and must
    # not change score-level metrics. Logistic function used as the transform.
    labels, scores = _random_case()
    transformed = 1.0 / (1.0 + np.exp(-scores))
    assert roc_auc(labels, transformed) == pytest.approx(roc_auc(labels, scores), abs=1e-12)
    assert eer(labels, transformed)[0] == pytest.approx(eer(labels, scores)[0], abs=1e-12)


def test_auc_of_negated_scores_is_complement():
    # Negating the scores reverses every pair (ties stay ties) -> AUC(s) + AUC(-s) == 1.
    labels, scores = _random_case()
    assert roc_auc(labels, scores) + roc_auc(labels, -scores) == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize("metric", [roc_auc, eer])
@pytest.mark.parametrize(
    ("labels", "scores", "message"),
    [
        ([0, 1, 1], [0.1, 0.9], "differ in length"),
        ([], [], "empty"),
        ([1, 1, 1], [0.1, 0.5, 0.9], "only one class"),
        ([0, 1, 2], [0.1, 0.5, 0.9], "must be 0"),
        ([0, 1, -1], [0.1, 0.5, 0.9], "must be 0"),
        (["bonafide", "spoof"], [0.1, 0.9], "must be 0"),
        ([0, 1, 1], [0.1, float("nan"), 0.9], "NaN or infinite"),
        ([0, 1, 1], [0.1, float("inf"), 0.9], "NaN or infinite"),
        ([0, 1, 1], [0.1, float("-inf"), 0.9], "NaN or infinite"),
    ],
)
def test_invalid_input_raises(metric, labels, scores, message):
    with pytest.raises(ValueError, match=message):
        metric(labels, scores)
