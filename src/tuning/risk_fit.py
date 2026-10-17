"""Fit the risk policy on val-B (Protocol v1.0 §6; D2, D9, D12): Training & Tuning, research tier.

Uses eer() from the evaluation harness, so it lives in the research tier (SDD Fig. 1); the core
(src/risk) only applies and loads the fitted policy and never imports this module.
"""
from __future__ import annotations

import numpy as np

from src.evaluation.metrics import eer
from src.risk.calibration import fit_platt
from src.risk.decisions import UNCERTAIN, _require_finite_number, three_way_decisions
from src.risk.policy import RiskPolicy

BISECTION_ITERATIONS = 60


def _deferral(p: np.ndarray, threshold: float, half_width: float) -> float:
    """Fraction of p that the core band rule defers (uncertain)."""
    return float(np.mean(three_way_decisions(p, threshold, half_width) == UNCERTAIN))


def fit_risk_policy(labels, scores, *, version: str, target_deferral: float = 0.10) -> RiskPolicy:
    """Fit calibration, threshold and uncertain band. Fitted on val-B only (D2, D9).

    1. calibration = fit_platt(labels, scores); p = calibration.transform(scores).
    2. threshold = eer(labels, p)[1], the val-B EER point on calibrated p (D12); ValueError if it is
       not strictly inside (0, 1).
    3. half_width = the largest value in [0, 1] with deferral on the fit data <= target_deferral
       (Protocol v1.0 §6: 10% is the maximum), found by bisection (60 iterations) with the core band
       rule; deferral_on_fit is the rate achieved there.

    Deferral is a step function of half_width (it jumps each time the band reaches another p), and
    tied or close p values can jump past the target together, so the achieved rate can stay below
    the target. target_deferral = 0 gives half_width = 0 exactly (no band).
    """
    _require_finite_number("target_deferral", target_deferral)
    if not 0 <= target_deferral < 1:
        raise ValueError(f"target_deferral must be in [0, 1), got {target_deferral!r}")

    calibration = fit_platt(labels, scores)
    p = calibration.transform(scores)
    threshold = eer(labels, p)[1]
    if not 0 < threshold < 1:
        raise ValueError(f"val-B EER threshold on p must be strictly inside (0, 1), got {threshold!r}")

    # Deferral is non-decreasing in half_width. lo is always feasible (half_width 0 defers nothing);
    # half_width 1 defers every p in [threshold - 1, threshold + 1), i.e. all p < 1.
    # target_deferral 0 means no band: bisection could return a band of a few ulps that floating point
    # rounding hides (threshold +/- h == threshold), which is not a meaningful width.
    lo, hi = 0.0, 1.0
    if target_deferral > 0 and _deferral(p, threshold, hi) <= target_deferral:
        lo = hi
    elif target_deferral > 0:
        for _ in range(BISECTION_ITERATIONS):
            mid = (lo + hi) / 2
            if _deferral(p, threshold, mid) <= target_deferral:
                lo = mid
            else:
                hi = mid

    return RiskPolicy(
        version=version,
        calibration=calibration,
        threshold=threshold,
        half_width=lo,
        target_deferral=target_deferral,
        n_spoof_fit=calibration.n_spoof,
        n_bonafide_fit=calibration.n_bonafide,
        deferral_on_fit=_deferral(p, threshold, lo),
    )
