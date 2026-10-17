"""Risk policy fit tests (Stage 10, step R2) on a synthetic val-B (no dataset access).

Convention: label 1 = spoof (positive), 0 = bonafide; higher score = more spoof; p = P(spoof).
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from src.evaluation.metrics import binary_metrics, eer
from src.risk.decisions import SYNTHETIC, UNCERTAIN, three_way_decisions
from src.tuning.risk_fit import fit_risk_policy

N_PER_CLASS = 665


def _val_b():
    # 665 spoof ~ N(+1, 1) and 665 bonafide ~ N(-1, 1), seed 2026.
    rng = np.random.default_rng(2026)
    labels = np.r_[np.ones(N_PER_CLASS, dtype=int), np.zeros(N_PER_CLASS, dtype=int)]
    scores = np.r_[rng.normal(1.0, 1.0, N_PER_CLASS), rng.normal(-1.0, 1.0, N_PER_CLASS)]
    return labels, scores


def _deferral(p, threshold, half_width) -> float:
    return float(np.mean(three_way_decisions(p, threshold, half_width) == UNCERTAIN))


def test_fit_end_to_end_and_deterministic():
    # 1,330 scores, continuous, so each band step adds about one case (1/1330 ~ 0.00075):
    # the largest band with deferral <= 10% should defer between 9% and 10%.
    labels, scores = _val_b()
    policy = fit_risk_policy(labels, scores, version="test-v1")
    assert 0.09 <= policy.deferral_on_fit <= 0.10
    assert 0 < policy.threshold < 1
    assert (policy.n_spoof_fit, policy.n_bonafide_fit) == (N_PER_CLASS, N_PER_CLASS)
    # Platt fit, eer and bisection are all deterministic: refitting gives the same policy exactly.
    assert fit_risk_policy(labels, scores, version="test-v1") == policy


def test_band_is_maximal():
    # Any band just wider than the fitted one defers more than the target: the bisection interval
    # after 60 halvings (2^-60) is far below 0.1% of half_width + 1e-12.
    labels, scores = _val_b()
    policy = fit_risk_policy(labels, scores, version="test-v1")
    p = policy.calibration.transform(scores)
    wider = policy.half_width * 1.001 + 1e-12
    assert _deferral(p, policy.threshold, wider) > policy.target_deferral


def test_threshold_is_eer_point_and_zero_band_is_forced_binary():
    # The threshold is the val-B EER point on calibrated p (D12), bit for bit.
    labels, scores = _val_b()
    policy = fit_risk_policy(labels, scores, version="test-v1")
    p = policy.calibration.transform(scores)
    assert policy.threshold == eer(labels, p)[1]

    # With no band, the policy decides "synthetic" exactly when p >= threshold, which is the
    # forced-binary rule of binary_metrics: same confusion counts.
    decisions = dataclasses.replace(policy, half_width=0.0).decide(scores)
    synthetic = np.array([d.prediction == SYNTHETIC for d in decisions])
    assert np.array_equal(synthetic, p >= policy.threshold)
    m = binary_metrics(labels, p, policy.threshold)
    assert m.tp == int(np.sum(synthetic & (labels == 1)))
    assert m.fp == int(np.sum(synthetic & (labels == 0)))
    assert m.tn == int(np.sum(~synthetic & (labels == 0)))
    assert m.fn == int(np.sum(~synthetic & (labels == 1)))


def test_zero_target_gives_no_band():
    # Target 0 means no uncertain band: half_width exactly 0, nothing deferred.
    labels, scores = _val_b()
    policy = fit_risk_policy(labels, scores, version="test-v1", target_deferral=0.0)
    assert policy.half_width == 0.0
    assert policy.deferral_on_fit == 0.0


@pytest.mark.parametrize("target", [-0.01, 1.0, 1.5, float("nan")])
def test_target_outside_range_raises(target):
    labels, scores = _val_b()
    with pytest.raises(ValueError):
        fit_risk_policy(labels, scores, version="test-v1", target_deferral=target)
