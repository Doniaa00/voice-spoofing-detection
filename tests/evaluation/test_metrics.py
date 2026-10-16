"""Evaluation harness tests on small synthetic arrays (no dataset access).

Step 1: EER and ROC-AUC. Step 2: decision-level metrics at a threshold (binary_metrics).
Step 3: three-way decisions and metrics with an uncertain band (three_way_decisions,
three_way_metrics).

Convention: label 1 = spoof (positive), 0 = bonafide; higher score = more spoof; spoof if
score >= threshold. In the hand calculations, ROC rows are (threshold, FPR, TPR, FNR) as returned by
roc_curve(drop_intermediate=False), with sklearn's +inf first threshold.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, roc_auc_score

from src.evaluation.metrics import (
    AUTHENTIC,
    SYNTHETIC,
    UNCERTAIN,
    binary_metrics,
    eer,
    roc_auc,
    three_way_decisions,
    three_way_metrics,
)

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


# --- Step 2: decision-level metrics at a threshold -------------------------------------------

HAND_SCORES = [0.1, 0.6, 0.4, 0.9]  # with LABELS = [0, 0, 1, 1]


def test_binary_metrics_hand_case():
    # threshold 0.5: predicted spoof = [F, T, F, T].
    # bonafide 0.1 -> TN, bonafide 0.6 -> FP, spoof 0.4 -> FN, spoof 0.9 -> TP.
    # precision 1/2, recall 1/2, fpr 1/2, fnr 1/2, accuracy 2/4, f1 2/(2+1+1) = 0.5.
    m = binary_metrics(LABELS, HAND_SCORES, 0.5)
    assert (m.tp, m.fp, m.tn, m.fn) == (1, 1, 1, 1)
    assert (m.n_spoof, m.n_bonafide) == (2, 2)
    for rate in (m.accuracy, m.precision, m.recall, m.f1, m.fpr, m.fnr):
        assert rate == 0.5


@pytest.mark.filterwarnings("error")
def test_binary_metrics_nothing_predicted_spoof():
    # threshold 0.95: no score >= 0.95 -> TP 0, FP 0, TN 2, FN 2.
    # precision 0/0 -> NaN; recall 0/2 = 0; f1 0/(0+0+2) = 0; fpr 0/2 = 0; fnr 2/2 = 1;
    # accuracy 2/4 = 0.5.
    m = binary_metrics(LABELS, HAND_SCORES, 0.95)
    assert (m.tp, m.fp, m.tn, m.fn) == (0, 0, 2, 2)
    assert math.isnan(m.precision)
    assert m.recall == 0.0
    assert m.f1 == 0.0
    assert m.fpr == 0.0
    assert m.fnr == 1.0
    assert m.accuracy == 0.5


def test_binary_metrics_tie_counts_as_spoof():
    # threshold 0.4: spoof 0.4 >= 0.4 -> predicted spoof (TP); 0.6 and 0.9 are also >= 0.4.
    # TP 2 (0.4, 0.9), FP 1 (0.6), TN 1 (0.1), FN 0.
    m = binary_metrics(LABELS, HAND_SCORES, 0.4)
    assert (m.tp, m.fp, m.tn, m.fn) == (2, 1, 1, 0)


@pytest.mark.filterwarnings("error")
def test_binary_metrics_single_class():
    # labels [1,1,1], scores [0.2,0.6,0.9], threshold 0.5: TP 2 (0.6, 0.9), FN 1 (0.2), FP 0, TN 0.
    # recall 2/3, fnr 1/3, fpr 0/0 -> NaN, precision 2/2 = 1.0, f1 4/(4+0+1) = 0.8, accuracy 2/3.
    m = binary_metrics([1, 1, 1], [0.2, 0.6, 0.9], 0.5)
    assert (m.tp, m.fp, m.tn, m.fn) == (2, 0, 0, 1)
    assert m.n_bonafide == 0
    assert m.recall == pytest.approx(2 / 3)
    assert m.fnr == pytest.approx(1 / 3)
    assert math.isnan(m.fpr)
    assert m.precision == 1.0
    assert m.f1 == pytest.approx(0.8)
    assert m.accuracy == pytest.approx(2 / 3)


def test_binary_metrics_consistent_with_sklearn():
    # 200 random scores, seed 2026, threshold 0.5. Counts must sum to N, fnr == 1 - recall, and
    # counts / precision / recall / f1 must equal scikit-learn's on the same predictions.
    labels, scores = _random_case()
    m = binary_metrics(labels, scores, 0.5)
    predicted = (scores >= 0.5).astype(int)
    assert m.tp + m.fp + m.tn + m.fn == len(labels)
    assert m.fnr == pytest.approx(1.0 - m.recall, abs=1e-12)
    tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
    assert (m.tp, m.fp, m.tn, m.fn) == (tp, fp, tn, fn)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predicted, average="binary", pos_label=1
    )
    assert m.precision == pytest.approx(precision, abs=1e-12)
    assert m.recall == pytest.approx(recall, abs=1e-12)
    assert m.f1 == pytest.approx(f1, abs=1e-12)


def test_binary_metrics_at_eer_threshold():
    # Hand case: eer() gives EER 0.5 at threshold 0.6 (exact ROC point, see test_hand_calculated_case).
    # At 0.6: 0.6 -> FP, 0.9 -> TP, 0.1 -> TN, 0.4 -> FN -> FPR 1/2 = FNR 1/2 = 0.5.
    _, threshold = eer(LABELS, HAND_SCORES)
    m = binary_metrics(LABELS, HAND_SCORES, threshold)
    assert m.fpr == 0.5
    assert m.fnr == 0.5


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), float("-inf"), "0.5", None])
def test_binary_metrics_invalid_threshold_raises(threshold):
    with pytest.raises(ValueError, match="threshold must be a finite number"):
        binary_metrics(LABELS, HAND_SCORES, threshold)


@pytest.mark.parametrize(
    ("labels", "scores", "message"),
    [
        ([0, 1, 1], [0.1, 0.9], "differ in length"),
        ([], [], "empty"),
        ([0, 1, 2], [0.1, 0.5, 0.9], "must be 0"),
        (["bonafide", "spoof"], [0.1, 0.9], "must be 0"),
        ([0, 1, 1], [0.1, float("nan"), 0.9], "NaN or infinite"),
    ],
)
def test_binary_metrics_invalid_input_raises(labels, scores, message):
    with pytest.raises(ValueError, match=message):
        binary_metrics(labels, scores, 0.5)


@pytest.mark.parametrize("metric", [roc_auc, eer])
def test_score_metrics_still_require_both_classes(metric):
    # Regression check after adding require_both_classes: the default stays True.
    with pytest.raises(ValueError, match="only one class"):
        metric([1, 1, 1], [0.2, 0.6, 0.9])


# --- Step 3: three-way decisions and metrics (uncertain band) --------------------------------


def test_three_way_decisions_boundaries():
    # threshold 0.5, half_width 0.1 -> lower 0.4, upper 0.6 (both exact in float: 0.5 -/+ 0.1).
    # 0.39 < 0.4 -> authentic; 0.4 = lower -> uncertain (lower bound included);
    # 0.5, 0.59 in [0.4, 0.6) -> uncertain; 0.6 = upper -> synthetic (>= rule); 0.7 -> synthetic.
    decisions = three_way_decisions([0.39, 0.4, 0.5, 0.59, 0.6, 0.7], 0.5, 0.1)
    assert decisions.tolist() == [AUTHENTIC, UNCERTAIN, UNCERTAIN, UNCERTAIN, SYNTHETIC, SYNTHETIC]


def test_three_way_metrics_hand_case():
    # labels [0,0,1,1,0,1], scores [0.1,0.45,0.55,0.9,0.7,0.3], threshold 0.5, half_width 0.1:
    #   bonafide 0.1 -> authentic, bonafide 0.45 -> uncertain, spoof 0.55 -> uncertain,
    #   spoof 0.9 -> synthetic, bonafide 0.7 -> synthetic, spoof 0.3 -> authentic.
    # Confusion (authentic, synthetic, uncertain): bonafide (1, 1, 1), spoof (1, 1, 1).
    # n 6, deferred 2 -> coverage 4/6 = 2/3, deferral 2/6 = 1/3; bonafide 1/3, spoof 1/3.
    # Non-deferred (4 cases): TP 1 (0.9), FP 1 (0.7), TN 1 (0.1), FN 1 (0.3) -> every rate 0.5.
    labels = [0, 0, 1, 1, 0, 1]
    decisions = three_way_decisions([0.1, 0.45, 0.55, 0.9, 0.7, 0.3], 0.5, 0.1)
    m = three_way_metrics(labels, decisions)
    assert m.confusion == ((1, 1, 1), (1, 1, 1))
    assert (m.n, m.n_deferred) == (6, 2)
    assert m.coverage == pytest.approx(2 / 3)
    assert m.deferral_rate == pytest.approx(1 / 3)
    assert m.deferral_rate_bonafide == pytest.approx(1 / 3)
    assert m.deferral_rate_spoof == pytest.approx(1 / 3)
    nd = m.non_deferred
    assert (nd.tp, nd.fp, nd.tn, nd.fn) == (1, 1, 1, 1)
    assert (nd.n_spoof, nd.n_bonafide) == (2, 2)
    for rate in (nd.accuracy, nd.precision, nd.recall, nd.f1, nd.fpr, nd.fnr):
        assert rate == 0.5


def test_zero_half_width_equals_forced_binary():
    # half_width 0: lower = upper = threshold, so [threshold, threshold) is empty -> no uncertain;
    # synthetic iff score >= threshold, the binary_metrics rule. 200 random scores, seed 2026.
    labels, scores = _random_case()
    decisions = three_way_decisions(scores, 0.5, 0.0)
    assert UNCERTAIN not in decisions.tolist()
    m = three_way_metrics(labels, decisions)
    assert (m.n_deferred, m.coverage, m.deferral_rate) == (0, 1.0, 0.0)
    assert m.non_deferred == binary_metrics(labels, scores, 0.5)


@pytest.mark.filterwarnings("error")
def test_three_way_metrics_all_deferred():
    # half_width 100 around 0.5: every score of HAND_SCORES lies in [-99.5, 100.5) -> all uncertain.
    # coverage 0/4 = 0, deferral 4/4 = 1 (both classes 2/2 = 1); non-deferred: no case left, so all
    # counts 0 and every rate 0/0 -> NaN.
    m = three_way_metrics(LABELS, three_way_decisions(HAND_SCORES, 0.5, 100.0))
    assert m.confusion == ((0, 0, 2), (0, 0, 2))
    assert (m.n_deferred, m.coverage, m.deferral_rate) == (4, 0.0, 1.0)
    assert (m.deferral_rate_bonafide, m.deferral_rate_spoof) == (1.0, 1.0)
    nd = m.non_deferred
    assert (nd.tp, nd.fp, nd.tn, nd.fn, nd.n_spoof, nd.n_bonafide) == (0, 0, 0, 0, 0, 0)
    for rate in (nd.accuracy, nd.precision, nd.recall, nd.f1, nd.fpr, nd.fnr):
        assert math.isnan(rate)


@pytest.mark.filterwarnings("error")
def test_three_way_metrics_single_class_deferral_nan():
    # labels [1,1], decisions [uncertain, synthetic]: spoof deferral 1/2; no bonafide -> 0/0 -> NaN.
    m = three_way_metrics([1, 1], [UNCERTAIN, SYNTHETIC])
    assert m.deferral_rate_spoof == 0.5
    assert math.isnan(m.deferral_rate_bonafide)


def test_three_way_metrics_consistency_on_random_scores():
    # 200 random scores, seed 2026, threshold 0.5, half_width 0.3. Each case falls in exactly one
    # cell: cells sum to n; the uncertain column sums to n_deferred; coverage + deferral = 1;
    # non-deferred counts sum to n - n_deferred; row sums are the class counts.
    labels, scores = _random_case()
    m = three_way_metrics(labels, three_way_decisions(scores, 0.5, 0.3))
    assert sum(sum(row) for row in m.confusion) == m.n == len(labels)
    assert m.n_deferred == m.confusion[0][2] + m.confusion[1][2]
    assert m.n_deferred > 0
    assert m.coverage + m.deferral_rate == pytest.approx(1.0, abs=1e-12)
    nd = m.non_deferred
    assert nd.tp + nd.fp + nd.tn + nd.fn == m.n - m.n_deferred
    assert sum(m.confusion[0]) == int(np.sum(labels == 0))
    assert sum(m.confusion[1]) == int(np.sum(labels == 1))


@pytest.mark.parametrize("half_width", [-0.1, float("nan"), float("inf"), float("-inf"), "0.1", None])
def test_three_way_decisions_invalid_half_width_raises(half_width):
    with pytest.raises(ValueError, match="half_width must be"):
        three_way_decisions(HAND_SCORES, 0.5, half_width)


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), "0.5", None, True])
def test_three_way_decisions_invalid_threshold_raises(threshold):
    with pytest.raises(ValueError, match="threshold must be a finite number"):
        three_way_decisions(HAND_SCORES, threshold, 0.1)


@pytest.mark.parametrize(
    ("scores", "message"),
    [([], "empty"), ([0.1, float("nan")], "NaN or infinite"), ([[0.1, 0.2]], "1-D")],
)
def test_three_way_decisions_invalid_scores_raises(scores, message):
    with pytest.raises(ValueError, match=message):
        three_way_decisions(scores, 0.5, 0.1)


@pytest.mark.parametrize(
    ("labels", "predictions", "message"),
    [
        ([0, 1], [AUTHENTIC, "spoof"], "found 'spoof'"),
        ([0, 1], [AUTHENTIC, "Synthetic"], "found 'Synthetic'"),
        ([0, 1], [AUTHENTIC, 1], "found 1"),
        ([0, 1], [AUTHENTIC, None], "found None"),
        ([0, 1, 1], [AUTHENTIC, SYNTHETIC], "differ in length"),
        ([], [], "empty"),
        ([0, 2], [AUTHENTIC, SYNTHETIC], "must be 0"),
    ],
)
def test_three_way_metrics_invalid_input_raises(labels, predictions, message):
    with pytest.raises(ValueError, match=message):
        three_way_metrics(labels, predictions)
