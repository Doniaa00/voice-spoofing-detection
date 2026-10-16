"""Score-level evaluation metrics shared by the baseline, the CNN and the external run (FR-12, D4).

Conventions (Protocol v1.0 §5, D4):
- labels: 1 = spoof (positive class), 0 = bonafide.
- scores: higher score = more likely spoof.
- decision rule: predict spoof if score >= threshold.

All functions validate their input and raise ValueError on anything ambiguous (AGENTS.md code
rules: fail loudly).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


def _validate(labels, scores, require_both_classes: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Return labels (int) and scores (float) as 1-D arrays, or raise ValueError.

    require_both_classes=False allows single-class input (e.g. spoof-only subsets for recall).
    """
    y = np.asarray(labels)
    s = np.asarray(scores, dtype=float)
    if y.ndim != 1 or s.ndim != 1:
        raise ValueError(f"labels and scores must be 1-D, got shapes {y.shape} and {s.shape}")
    if len(y) != len(s):
        raise ValueError(f"labels and scores differ in length: {len(y)} != {len(s)}")
    if len(y) == 0:
        raise ValueError("labels and scores are empty")
    if not np.isin(y, [0, 1]).all():
        bad = sorted({repr(v) for v in y[~np.isin(y, [0, 1])].tolist()})[:5]
        raise ValueError(f"labels must be 0 (bonafide) or 1 (spoof), found {', '.join(bad)}")
    y = y.astype(int)
    if require_both_classes and len(np.unique(y)) < 2:
        raise ValueError(f"labels contain only one class ({int(y[0])}); both 0 and 1 are needed")
    if not np.isfinite(s).all():
        raise ValueError(f"scores contain {int((~np.isfinite(s)).sum())} NaN or infinite values")
    return y, s


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


def binary_metrics(labels, scores, threshold) -> BinaryMetrics:
    """Forced binary decision metrics at a threshold: predict spoof if score >= threshold.

    Same rule as eer(). Single-class input is allowed; any rate whose denominator is 0 is NaN.
    F1 is computed from counts as 2TP / (2TP + FP + FN).
    """
    y, s = _validate(labels, scores, require_both_classes=False)
    if isinstance(threshold, bool) or not isinstance(threshold, Real) or not math.isfinite(threshold):
        raise ValueError(f"threshold must be a finite number, got {threshold!r}")

    predicted_spoof = s >= threshold
    is_spoof = y == 1
    tp = int(np.sum(predicted_spoof & is_spoof))
    fp = int(np.sum(predicted_spoof & ~is_spoof))
    tn = int(np.sum(~predicted_spoof & ~is_spoof))
    fn = int(np.sum(~predicted_spoof & is_spoof))
    return BinaryMetrics(
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        n_spoof=tp + fn,
        n_bonafide=fp + tn,
        accuracy=_rate(tp + tn, len(y)),
        precision=_rate(tp, tp + fp),
        recall=_rate(tp, tp + fn),
        f1=_rate(2 * tp, 2 * tp + fp + fn),
        fpr=_rate(fp, fp + tn),
        fnr=_rate(fn, fn + tp),
    )
