"""Three-way decision rule (FR-05) and the input checks it shares with the evaluation harness.

This module is part of the shared core (SDD Fig. 1): the API's Risk & Confidence service and the
research Evaluation service both use it, so it must not import src.evaluation.
src.evaluation.metrics re-exports everything public here.

Conventions (Protocol v1.0 §5-6, D4, D12):
- labels: 1 = spoof (positive class), 0 = bonafide.
- scores: higher score = more likely spoof.
- three-way decisions: authentic / synthetic / uncertain, with a symmetric uncertain band around
  the threshold.

All functions validate their input and raise ValueError on anything ambiguous (AGENTS.md code
rules: fail loudly).
"""
from __future__ import annotations

import math
from numbers import Real

import numpy as np


AUTHENTIC = "authentic"
SYNTHETIC = "synthetic"
UNCERTAIN = "uncertain"
DECISIONS = (AUTHENTIC, SYNTHETIC, UNCERTAIN)  # FR-05 labels, in confusion-matrix column order


def _validate_labels(labels, require_both_classes: bool = True) -> np.ndarray:
    """Return labels as a 1-D int array of 0/1, or raise ValueError."""
    y = np.asarray(labels)
    if y.ndim != 1:
        raise ValueError(f"labels must be 1-D, got shape {y.shape}")
    if len(y) == 0:
        raise ValueError("labels are empty")
    if not np.isin(y, [0, 1]).all():
        bad = sorted({repr(v) for v in y[~np.isin(y, [0, 1])].tolist()})[:5]
        raise ValueError(f"labels must be 0 (bonafide) or 1 (spoof), found {', '.join(bad)}")
    y = y.astype(int)
    if require_both_classes and len(np.unique(y)) < 2:
        raise ValueError(f"labels contain only one class ({int(y[0])}); both 0 and 1 are needed")
    return y


def _validate_scores(scores) -> np.ndarray:
    """Return scores as a 1-D float array of finite values, or raise ValueError."""
    s = np.asarray(scores, dtype=float)
    if s.ndim != 1:
        raise ValueError(f"scores must be 1-D, got shape {s.shape}")
    if len(s) == 0:
        raise ValueError("scores are empty")
    if not np.isfinite(s).all():
        raise ValueError(f"scores contain {int((~np.isfinite(s)).sum())} NaN or infinite values")
    return s


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
    y = _validate_labels(y, require_both_classes)
    if not np.isfinite(s).all():
        raise ValueError(f"scores contain {int((~np.isfinite(s)).sum())} NaN or infinite values")
    return y, s


def _require_finite_number(name: str, value) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number, got {value!r}")


def three_way_decisions(scores, threshold, half_width) -> np.ndarray:
    """Three-way decisions (FR-05) with a symmetric uncertain band around the threshold (D12).

    - synthetic if score >= threshold + half_width
    - uncertain if threshold - half_width <= score < threshold + half_width
    - authentic if score < threshold - half_width

    This is the single definition of the band rule. The Stage 10 risk policy must import it, not
    re-implement it, so evaluation and deployment apply the same rule. half_width = 0 gives the
    forced binary rule of binary_metrics (no case is uncertain). The bounds threshold +/- half_width
    are computed in floating point.
    """
    s = _validate_scores(scores)
    _require_finite_number("threshold", threshold)
    _require_finite_number("half_width", half_width)
    if half_width < 0:
        raise ValueError(f"half_width must be >= 0, got {half_width!r}")

    upper = threshold + half_width
    lower = threshold - half_width
    return np.where(s >= upper, SYNTHETIC, np.where(s < lower, AUTHENTIC, UNCERTAIN))
