"""Risk policy tests (Stage 10, step R2): apply, save and load, on synthetic scores (no dataset access).

Convention: label 1 = spoof (positive), 0 = bonafide; higher score = more spoof; p = P(spoof).
"""
from __future__ import annotations

import dataclasses
import json

import numpy as np
import pytest

from src.risk.calibration import PlattCalibration
from src.risk.decisions import UNCERTAIN
from src.risk.policy import RISK_LEVELS, SCHEMA_VERSION, Decision, RiskPolicy


def _policy(**overrides) -> RiskPolicy:
    fields = dict(
        version="test-v1",
        calibration=PlattCalibration(a=1.0, b=0.0, n_spoof=10, n_bonafide=12),
        threshold=0.5,
        half_width=0.1,
        target_deferral=0.10,
        n_spoof_fit=10,
        n_bonafide_fit=12,
        deferral_on_fit=0.0909090909090909,
    )
    fields.update(overrides)
    return RiskPolicy(**fields)


def test_risk_levels():
    # FR-07, Protocol v1.0 §6: authentic -> LOW, uncertain -> MEDIUM, synthetic -> HIGH.
    assert RISK_LEVELS == {"authentic": "LOW", "uncertain": "MEDIUM", "synthetic": "HIGH"}


def test_decide_hand_case():
    # a = 1, b = 0: p = sigmoid(s). Band [0.4, 0.6) around threshold 0.5.
    # s = 0  -> p = 0.5, inside the band -> uncertain, MEDIUM, confidence max(0.5, 0.5) = 0.5.
    # s = 3  -> p = 1 / (1 + e^-3) ~ 0.9526 >= 0.6 -> synthetic, HIGH, round(0.9526, 2) = 0.95.
    # s = -3 -> p ~ 0.0474 < 0.4 -> authentic, LOW, max(p, 1 - p) ~ 0.9526 -> 0.95.
    d0, d3, dm3 = _policy().decide([0.0, 3.0, -3.0])
    assert d0 == Decision(p=0.5, prediction="uncertain", confidence=0.5, risk_level="MEDIUM")
    assert d3.p == pytest.approx(0.9526, abs=1e-4)
    assert (d3.prediction, d3.risk_level, d3.confidence) == ("synthetic", "HIGH", 0.95)
    assert dm3.p == pytest.approx(0.0474, abs=1e-4)
    assert (dm3.prediction, dm3.risk_level, dm3.confidence) == ("authentic", "LOW", 0.95)


def test_zero_half_width_never_defers():
    # Band [t, t) is empty: every p is either >= t (synthetic) or < t (authentic).
    scores = np.random.default_rng(2026).normal(size=200)
    decisions = _policy(half_width=0.0).decide(scores)
    assert len(decisions) == 200
    assert all(d.prediction != UNCERTAIN for d in decisions)


def test_json_round_trip_is_exact():
    # json writes floats with repr(), which round-trips every finite float exactly, so the loaded
    # policy compares equal field by field (dataclass ==, exact float comparison).
    policy = _policy(threshold=0.4964645456388069, half_width=0.0998582077382769)
    text = policy.to_json()
    assert json.loads(text)["schema_version"] == SCHEMA_VERSION
    assert RiskPolicy.from_json(text) == policy


def _mutated(mutate) -> str:
    data = json.loads(_policy().to_json())
    mutate(data)
    return json.dumps(data)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(schema_version=2),             # wrong schema version
        lambda d: d.pop("half_width"),                    # missing key
        lambda d: d.update(extra=1),                      # unknown key
        lambda d: d["calibration"].update(c=0.0),         # unknown calibration key
        lambda d: d.update(threshold=float("nan")),       # NaN threshold (json writes NaN)
        lambda d: d.update(threshold=0.0),                # threshold on the boundary
        lambda d: d.update(threshold=1.0),
        lambda d: d.update(half_width=-0.01),             # negative band
    ],
)
def test_from_json_rejects_invalid(mutate):
    with pytest.raises(ValueError):
        RiskPolicy.from_json(_mutated(mutate))


@pytest.mark.parametrize(
    "overrides",
    [
        {"version": ""},
        {"threshold": float("inf")},
        {"target_deferral": 1.0},
        {"n_spoof_fit": 0},
        {"deferral_on_fit": 1.5},
    ],
)
def test_constructor_rejects_invalid(overrides):
    with pytest.raises(ValueError):
        _policy(**overrides)


_INCONSISTENT = [
    {"n_spoof_fit": 11},                              # calibration.n_spoof is 10
    {"n_bonafide_fit": 13},                           # calibration.n_bonafide is 12
    {"deferral_on_fit": 0.15},                        # above target_deferral 0.10
]


@pytest.mark.parametrize("overrides", _INCONSISTENT)
def test_constructor_rejects_inconsistent(overrides):
    with pytest.raises(ValueError):
        _policy(**overrides)


@pytest.mark.parametrize("overrides", _INCONSISTENT)
def test_from_json_rejects_inconsistent(overrides):
    # Same contradictions written into an otherwise valid file.
    with pytest.raises(ValueError):
        RiskPolicy.from_json(_mutated(lambda d: d.update(overrides)))


def test_deferral_equal_to_target_is_accepted():
    # The fit's bound is <=, so deferral_on_fit == target_deferral is consistent.
    assert _policy(deferral_on_fit=0.10).deferral_on_fit == 0.10


def test_policy_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _policy().threshold = 0.3
