"""Platt calibration tests (Stage 10, step R1) on small synthetic arrays (no dataset access).

Convention: label 1 = spoof (positive), 0 = bonafide; higher score = more spoof;
p = 1 / (1 + exp(-(a*s + b))) = calibrated P(spoof).
"""
from __future__ import annotations

import numpy as np
import pytest

from src.evaluation.metrics import eer, roc_auc
from src.risk.calibration import PlattCalibration, _platt_targets, _sigmoid, fit_platt


def test_smoothed_targets():
    # N_spoof = N_bonafide = 2: t_spoof = (2 + 1) / (2 + 2) = 3/4, t_bonafide = 1 / (2 + 2) = 1/4.
    assert _platt_targets(2, 2) == (0.75, 0.25)


def test_parameter_recovery():
    # Labels drawn from the model itself, P(spoof | s) = sigmoid(2s - 1), so the fit should recover
    # a = 2, b = -1. With 5,000 points the standard errors are about 0.05, so +/- 0.15 is ~3 SE;
    # the smoothed targets shift the optimum by O(1/N), far below the tolerance.
    rng = np.random.default_rng(2026)
    s = rng.normal(size=5000)
    y = (rng.random(5000) < _sigmoid(2.0 * s - 1.0)).astype(int)
    cal = fit_platt(y, s)
    assert cal.a == pytest.approx(2.0, abs=0.15)
    assert cal.b == pytest.approx(-1.0, abs=0.15)
    assert cal.n_spoof + cal.n_bonafide == 5000
    assert cal.n_spoof == int(y.sum())


def test_separable_data_gives_finite_parameters():
    # Plain logistic regression has no finite solution here: any a > 0 with threshold -b/a in
    # (0.3, 0.7) separates the classes, and the likelihood keeps increasing as a -> inf.
    # Targets 4/5 and 1/5 (N = 3 per class) cap the optimum, so a and b stay finite and every p
    # stays strictly inside (0, 1).
    labels = [0, 0, 0, 1, 1, 1]
    scores = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
    cal = fit_platt(labels, scores)
    assert np.isfinite(cal.a) and cal.a > 0
    assert np.isfinite(cal.b)
    p = cal.transform(scores)
    assert np.all((p > 0) & (p < 1))
    # Symmetric data around 0.5 -> p(0.5) = 0.5, i.e. b = -a/2.
    assert cal.b == pytest.approx(-cal.a / 2, abs=1e-9)


def test_calibration_is_monotonic_and_keeps_score_metrics():
    # a > 0, so p is strictly increasing in s; ROC-AUC and EER depend only on the ranking, so they
    # are identical for p and for s (the EER threshold moves, the EER rate does not).
    rng = np.random.default_rng(2026)
    s = rng.normal(size=200)
    y = (rng.random(200) < _sigmoid(2.0 * s)).astype(int)
    cal = fit_platt(y, s)
    order = np.argsort(s)
    p = cal.transform(s)
    assert np.all(np.diff(p[order]) > 0)
    assert roc_auc(y, p) == pytest.approx(roc_auc(y, s), abs=1e-12)
    assert eer(y, p)[0] == pytest.approx(eer(y, s)[0], abs=1e-12)


def test_reversed_scores_raise():
    # Scores decrease with spoof: the fit gives a < 0, which would invert the ranking.
    with pytest.raises(ValueError, match="a = .* <= 0"):
        fit_platt([0, 0, 0, 1, 1, 1], [0.9, 0.8, 0.7, 0.3, 0.2, 0.1])


@pytest.mark.filterwarnings("error")
def test_transform_extreme_scores_without_warnings():
    # a*s + b = -1e6, 0, 1e6: a naive exp(-z) would overflow at z = -1e6. The stable sigmoid only
    # takes exp of non-positive numbers, so the results are 0 (underflow), 0.5 and 1.
    cal = PlattCalibration(a=1.0, b=0.0, n_spoof=1, n_bonafide=1)
    p = cal.transform([-1e6, 0.0, 1e6])
    assert np.all((p >= 0) & (p <= 1))
    assert p.tolist() == [0.0, 0.5, 1.0]


@pytest.mark.parametrize(
    ("labels", "scores"),
    [
        ([1, 1, 1], [0.1, 0.2, 0.3]),          # one class
        ([0, 1, 1], [0.1, float("nan"), 0.3]),  # NaN score
        ([0, 1, 1], [0.1, 0.2]),                # length mismatch
        ([], []),                               # empty
    ],
)
def test_invalid_input_raises(labels, scores):
    with pytest.raises(ValueError):
        fit_platt(labels, scores)
