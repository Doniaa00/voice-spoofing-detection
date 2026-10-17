"""Risk policy: apply the frozen policy to detector scores, and save / load it (Protocol v1.0 §6).

A RiskPolicy turns raw scores into the reported output: calibrated p = P(spoof), one of
authentic / synthetic / uncertain (FR-05), a confidence (FR-06) and a risk level (FR-07). It is
fitted on val-B only (D2, D9) by src.tuning.risk_fit and frozen in F4 as part of the ModelBundle.

Part of the shared core (SDD Fig. 1): the API applies the policy, so this module must not import
src.evaluation or src.tuning (research code).
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass

from src.risk.calibration import PlattCalibration
from src.risk.decisions import AUTHENTIC, SYNTHETIC, UNCERTAIN, _require_finite_number, three_way_decisions

RISK_LEVELS = {AUTHENTIC: "LOW", UNCERTAIN: "MEDIUM", SYNTHETIC: "HIGH"}  # FR-07, Protocol v1.0 §6
SCHEMA_VERSION = 1

_CALIBRATION_KEYS = ("a", "b", "n_spoof", "n_bonafide")


@dataclass(frozen=True)
class Decision:
    """The output for one score: calibrated P(spoof), prediction, confidence and risk level."""

    p: float
    prediction: str
    confidence: float
    risk_level: str


def _require_int_at_least_one(name: str, value) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be an int >= 1, got {value!r}")


@dataclass(frozen=True)
class RiskPolicy:
    """Frozen risk policy: Platt calibration, threshold and uncertain band on p, and fit metadata.

    threshold and half_width are on the calibrated probability p. target_deferral is the maximum
    deferral rate asked for at fit time; deferral_on_fit is the rate achieved on the fit data (val-B).
    """

    version: str
    calibration: PlattCalibration
    threshold: float
    half_width: float
    target_deferral: float
    n_spoof_fit: int
    n_bonafide_fit: int
    deferral_on_fit: float

    def __post_init__(self) -> None:
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError(f"version must be a non-empty string, got {self.version!r}")
        if not isinstance(self.calibration, PlattCalibration):
            raise ValueError(f"calibration must be a PlattCalibration, got {type(self.calibration).__name__}")
        _require_finite_number("threshold", self.threshold)
        if not 0 < self.threshold < 1:
            raise ValueError(f"threshold must be strictly inside (0, 1), got {self.threshold!r}")
        _require_finite_number("half_width", self.half_width)
        if self.half_width < 0:
            raise ValueError(f"half_width must be >= 0, got {self.half_width!r}")
        _require_finite_number("target_deferral", self.target_deferral)
        if not 0 <= self.target_deferral < 1:
            raise ValueError(f"target_deferral must be in [0, 1), got {self.target_deferral!r}")
        _require_int_at_least_one("n_spoof_fit", self.n_spoof_fit)
        _require_int_at_least_one("n_bonafide_fit", self.n_bonafide_fit)
        _require_finite_number("deferral_on_fit", self.deferral_on_fit)
        if not 0 <= self.deferral_on_fit <= 1:
            raise ValueError(f"deferral_on_fit must be in [0, 1], got {self.deferral_on_fit!r}")

    def decide(self, scores) -> tuple[Decision, ...]:
        """Apply the policy: p = calibration(s), the core band rule on p, confidence and risk level.

        confidence = max(p, 1 - p) rounded to 2 decimals with Python round() (FR-06).
        """
        p = self.calibration.transform(scores)
        predictions = three_way_decisions(p, self.threshold, self.half_width)
        return tuple(
            Decision(
                p=float(pi),
                prediction=str(pred),
                confidence=round(max(float(pi), 1.0 - float(pi)), 2),
                risk_level=RISK_LEVELS[str(pred)],
            )
            for pi, pred in zip(p, predictions)
        )

    def to_json(self) -> str:
        """One JSON object with schema_version and every field; floats round-trip exactly."""
        payload = {"schema_version": SCHEMA_VERSION, **dataclasses.asdict(self)}
        return json.dumps(payload, indent=2, allow_nan=False)

    @classmethod
    def from_json(cls, text: str) -> RiskPolicy:
        """Load a policy written by to_json; ValueError on any schema or value problem."""
        data = json.loads(text)  # json.JSONDecodeError is a ValueError
        if not isinstance(data, dict):
            raise ValueError(f"policy JSON must be an object, got {type(data).__name__}")
        schema = data.get("schema_version")
        if isinstance(schema, bool) or not isinstance(schema, int) or schema != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}, got {schema!r}")

        expected = {"schema_version"} | {f.name for f in dataclasses.fields(cls)}
        _check_keys("policy", data, expected)
        calibration = data["calibration"]
        if not isinstance(calibration, dict):
            raise ValueError(f"calibration must be an object, got {type(calibration).__name__}")
        _check_keys("calibration", calibration, set(_CALIBRATION_KEYS))

        fields = {k: v for k, v in data.items() if k != "schema_version"}
        fields["calibration"] = PlattCalibration(**calibration)
        return cls(**fields)


def _check_keys(where: str, data: dict, expected: set[str]) -> None:
    missing = sorted(expected - data.keys())
    unknown = sorted(data.keys() - expected)
    if missing or unknown:
        raise ValueError(f"{where} JSON: missing keys {missing}, unknown keys {unknown}")
