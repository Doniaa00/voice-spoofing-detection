"""Score-level evaluation metrics shared by the baseline, the CNN and the external run (FR-12, D4).

Conventions (Protocol v1.0 §5, D4):
- labels: 1 = spoof (positive class), 0 = bonafide.
- scores: higher score = more likely spoof.
- decision rule: predict spoof if score >= threshold.
- three-way decisions (FR-05): authentic / synthetic / uncertain, with a symmetric uncertain band
  around the threshold (Protocol v1.0 §6, D12).

All functions validate their input and raise ValueError on anything ambiguous (AGENTS.md code
rules: fail loudly).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve

# The band rule and the input checks live in the shared core (src/risk, SDD Fig. 1); they are
# re-exported here so existing imports keep working.
from src.risk.decisions import (  # noqa: F401  (re-exported)
    AUTHENTIC,
    DECISIONS,
    SYNTHETIC,
    UNCERTAIN,
    _require_finite_number,
    _validate,
    _validate_labels,
    _validate_scores,
    three_way_decisions,
)


def roc_auc(labels, scores) -> float:
    """Area under the ROC curve (spoof = positive class)."""
    y, s = _validate(labels, scores)
    return float(roc_auc_score(y, s))


def eer(labels, scores) -> tuple[float, float]:
    """Equal error rate and its threshold, as (eer, threshold).

    The ROC comes from sklearn.metrics.roc_curve(drop_intermediate=False), with FNR = 1 - TPR.
    At the first ROC index where FPR >= FNR: if FPR == FNR, that value is the EER and that ROC
    threshold is the threshold. Otherwise the EER is where the straight lines FPR and FNR cross
    between this point and the previous one, and the threshold is interpolated between the two ROC
    thresholds with the same weight. sklearn's first threshold is +inf; it is replaced by the
    highest score so the returned threshold is always finite.
    """
    y, s = _validate(labels, scores)
    fpr, tpr, thresholds = roc_curve(y, s, drop_intermediate=False)
    fnr = 1.0 - tpr
    thresholds = np.where(np.isfinite(thresholds), thresholds, s.max())

    # fpr[0] = 0 and fnr[0] = 1, and the last point has fpr = 1, fnr = 0, so i >= 1 always exists.
    i = int(np.argmax(fpr >= fnr))
    if fpr[i] == fnr[i]:
        return float(fpr[i]), float(thresholds[i])

    gap_before = fnr[i - 1] - fpr[i - 1]  # > 0
    gap_after = fpr[i] - fnr[i]           # > 0
    w = gap_before / (gap_before + gap_after)
    rate = fpr[i - 1] + w * (fpr[i] - fpr[i - 1])
    threshold = thresholds[i - 1] + w * (thresholds[i] - thresholds[i - 1])
    return float(rate), float(threshold)


@dataclass(frozen=True)
class BinaryMetrics:
    """Confusion counts and rates at one threshold. Rates are fractions in [0, 1], NaN if undefined."""

    tp: int
    fp: int
    tn: int
    fn: int
    n_spoof: int
    n_bonafide: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    fpr: float
    fnr: float


def _rate(numerator: int, denominator: int) -> float:
    """numerator / denominator, or NaN (never 0) when the denominator is 0."""
    return numerator / denominator if denominator else float("nan")


def _metrics_from_counts(tp: int, fp: int, tn: int, fn: int) -> BinaryMetrics:
    """Rates from confusion counts: the one rate formula behind the forced-binary and 3-way views."""
    return BinaryMetrics(
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        n_spoof=tp + fn,
        n_bonafide=fp + tn,
        accuracy=_rate(tp + tn, tp + fp + tn + fn),
        precision=_rate(tp, tp + fp),
        recall=_rate(tp, tp + fn),
        f1=_rate(2 * tp, 2 * tp + fp + fn),
        fpr=_rate(fp, fp + tn),
        fnr=_rate(fn, fn + tp),
    )


def binary_metrics(labels, scores, threshold) -> BinaryMetrics:
    """Forced binary decision metrics at a threshold: predict spoof if score >= threshold.

    Same rule as eer(). Single-class input is allowed; any rate whose denominator is 0 is NaN.
    F1 is computed from counts as 2TP / (2TP + FP + FN).
    """
    y, s = _validate(labels, scores, require_both_classes=False)
    _require_finite_number("threshold", threshold)

    predicted_spoof = s >= threshold
    is_spoof = y == 1
    return _metrics_from_counts(
        tp=int(np.sum(predicted_spoof & is_spoof)),
        fp=int(np.sum(predicted_spoof & ~is_spoof)),
        tn=int(np.sum(~predicted_spoof & ~is_spoof)),
        fn=int(np.sum(~predicted_spoof & is_spoof)),
    )


@dataclass(frozen=True)
class ThreeWayMetrics:
    """Three-way confusion matrix, coverage / deferral and non-deferred metrics (D4, Protocol §5).

    confusion: rows (bonafide, spoof), columns (authentic, synthetic, uncertain).
    Rates are fractions in [0, 1], NaN if undefined. non_deferred: forced-binary metrics over the
    non-deferred cases only, with synthetic = predicted spoof.
    """

    confusion: tuple[tuple[int, int, int], tuple[int, int, int]]
    n: int
    n_deferred: int
    coverage: float
    deferral_rate: float
    deferral_rate_bonafide: float
    deferral_rate_spoof: float
    non_deferred: BinaryMetrics


def three_way_metrics(labels, predictions) -> ThreeWayMetrics:
    """Metrics of three-way predictions (AUTHENTIC / SYNTHETIC / UNCERTAIN) against 0/1 labels.

    Takes predictions, not scores, so stored predictions can be evaluated without re-running the
    model. Single-class input is allowed. If every case is deferred, non_deferred has zero counts
    and NaN rates.
    """
    y = _validate_labels(labels, require_both_classes=False)
    p = np.asarray(predictions, dtype=object)
    if p.ndim != 1:
        raise ValueError(f"predictions must be 1-D, got shape {p.shape}")
    if len(p) != len(y):
        raise ValueError(f"labels and predictions differ in length: {len(y)} != {len(p)}")
    for value in p.tolist():
        if not isinstance(value, str) or value not in DECISIONS:
            raise ValueError(f"predictions must be one of {DECISIONS}, found {value!r}")

    is_spoof = y == 1
    confusion = tuple(
        tuple(int(np.sum((p == d) & (is_spoof == row_is_spoof))) for d in DECISIONS)
        for row_is_spoof in (False, True)
    )
    kept = p != UNCERTAIN
    predicted_spoof = p == SYNTHETIC
    n = len(y)
    n_deferred = n - int(kept.sum())
    return ThreeWayMetrics(
        confusion=confusion,
        n=n,
        n_deferred=n_deferred,
        coverage=_rate(n - n_deferred, n),
        deferral_rate=_rate(n_deferred, n),
        deferral_rate_bonafide=_rate(confusion[0][2], sum(confusion[0])),
        deferral_rate_spoof=_rate(confusion[1][2], sum(confusion[1])),
        non_deferred=_metrics_from_counts(
            tp=int(np.sum(kept & predicted_spoof & is_spoof)),
            fp=int(np.sum(kept & predicted_spoof & ~is_spoof)),
            tn=int(np.sum(kept & ~predicted_spoof & ~is_spoof)),
            fn=int(np.sum(kept & ~predicted_spoof & is_spoof)),
        ),
    )
