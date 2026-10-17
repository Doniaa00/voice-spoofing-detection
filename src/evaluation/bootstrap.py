"""Bootstrap confidence intervals for evaluation metrics (Protocol v1.0 §5, D11).

Conventions (Protocol v1.0 §5, D11):
- 95% percentile intervals from 2,000 resamples with seed 2026 (the defaults below).
- The statistic is a callable of row indices into the caller's arrays, so one resample can feed a
  single metric or a paired difference of two systems on the same rows (H1, H5, H6).
- The estimate is the statistic on the full data, not the mean of the resamples.

Cluster rule: rows inside one cluster are not independent (FoR near-duplicate groups, DEEP-VOICE
source speakers), so with clusters given, the unique cluster ids are resampled with replacement (as
many draws as there are clusters) and every row of each drawn cluster is included. Without
clusters, the n rows are resampled with replacement.

A resample on which the statistic raises ValueError or returns NaN (for example a resample with one
class, where EER and AUC are undefined) is invalid: it is excluded from the percentiles and counted
in n_invalid, never hidden.

Limitation: with few clusters the percentile interval is approximate and wide. DEEP-VOICE has only
8 source speakers (dataset_audit §8, limitation 4), so its intervals must be reported as such.

All functions validate their input and raise ValueError on anything ambiguous (AGENTS.md code
rules: fail loudly).
"""
from __future__ import annotations

import math
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np


@dataclass(frozen=True)
class BootstrapCI:
    """A bootstrap percentile interval. low/high come from the valid resamples only."""

    estimate: float
    low: float
    high: float
    confidence: float
    n_resamples: int
    n_invalid: int


def _require_int(name: str, value, minimum: int | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an int, got {value!r}")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value!r}")


def _cluster_rows(clusters: Sequence[Hashable], n: int) -> list[np.ndarray]:
    """Row indices of each unique cluster id, in order of first appearance."""
    ids = list(clusters)
    if len(ids) != n:
        raise ValueError(f"clusters must have length n = {n}, got {len(ids)}")
    rows: dict[Hashable, list[int]] = {}
    for i, cluster_id in enumerate(ids):
        rows.setdefault(cluster_id, []).append(i)
    return [np.asarray(r, dtype=int) for r in rows.values()]


def bootstrap_ci(
    statistic: Callable[[np.ndarray], float],
    n: int,
    *,
    clusters: Sequence[Hashable] | None = None,
    n_resamples: int = 2000,
    seed: int = 2026,
    confidence: float = 0.95,
) -> BootstrapCI:
    """Percentile bootstrap CI of statistic(indices), resampling rows or whole clusters (D11).

    - statistic(indices) receives row indices into the caller's arrays and returns a float.
    - estimate = statistic(np.arange(n)); ValueError if it raises or returns NaN.
    - clusters None: each resample draws n row indices with replacement. clusters given (length n,
      any hashable ids): each resample draws the unique cluster ids with replacement, as many as
      there are clusters, and concatenates all rows of each drawn cluster.
    - Random generator: np.random.default_rng(seed), so the result is deterministic.
    - A resample is invalid if statistic raises ValueError or returns NaN; it is excluded and
      counted in n_invalid. ValueError if every resample is invalid.
    - low/high = np.percentile(valid, [100 * (1 - confidence) / 2, 100 * (1 + confidence) / 2],
      method="linear").
    """
    _require_int("n", n, minimum=1)
    _require_int("n_resamples", n_resamples, minimum=1)
    _require_int("seed", seed)
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, Real)
        or not math.isfinite(confidence)
        or not 0 < confidence < 1
    ):
        raise ValueError(f"confidence must be a number in (0, 1), got {confidence!r}")
    groups = None if clusters is None else _cluster_rows(clusters, n)

    try:
        estimate = float(statistic(np.arange(n)))
    except Exception as exc:
        raise ValueError(f"statistic failed on the full data: {exc}") from exc
    if math.isnan(estimate):
        raise ValueError("statistic is NaN on the full data")

    rng = np.random.default_rng(seed)
    values = []
    n_invalid = 0
    for _ in range(n_resamples):
        if groups is None:
            indices = rng.integers(0, n, size=n)
        else:
            drawn = rng.integers(0, len(groups), size=len(groups))
            indices = np.concatenate([groups[j] for j in drawn])
        try:
            value = float(statistic(indices))
        except ValueError:
            n_invalid += 1
            continue
        if math.isnan(value):
            n_invalid += 1
            continue
        values.append(value)

    if not values:
        raise ValueError(f"all {n_resamples} resamples are invalid (statistic raised or was NaN)")
    alpha = 1.0 - confidence
    low, high = np.percentile(values, [100 * alpha / 2, 100 * (1 - alpha / 2)], method="linear")
    return BootstrapCI(
        estimate=estimate,
        low=float(low),
        high=float(high),
        confidence=float(confidence),
        n_resamples=int(n_resamples),
        n_invalid=n_invalid,
    )
