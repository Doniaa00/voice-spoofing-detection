"""Seed summary and bundle-seed rule for the 3 CNN seeds (Protocol v1.0 §4–5, D11).

Conventions (Protocol v1.0 §4–5, D11):
- CNN seeds 0, 1, 2 on the final configuration.
- Seed reporting: mean ± SD of EER and ROC-AUC across the seeds (seed_summary). The SD is the
  sample SD (ddof = 1).
- Bundle seed: the seed with the median val-A EER; tie -> lower seed number (select_bundle_seed).

These functions encode protocol §5 before any result exists, so the bundle choice cannot be
adjusted after the numbers are seen (Protocol §12, change control).

Limitation: with 3 seeds the SD is a rough spread of training randomness, not a precise estimate;
it is reported as such, as a separate row next to the bootstrap CIs (Protocol §5).

All functions validate their input and raise ValueError on anything ambiguous (AGENTS.md code
rules: fail loudly).
"""
from __future__ import annotations

import math
import statistics
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Integral, Real


@dataclass(frozen=True)
class SeedSummary:
    """Mean and sample SD of one metric across seeds; values are (seed, value) sorted by seed."""

    mean: float
    sd: float
    n_seeds: int
    values: tuple[tuple[int, float], ...]


def _validate(values: Mapping[int, float]) -> tuple[tuple[int, float], ...]:
    """(seed, value) pairs sorted by seed, after checking seeds are ints and values finite numbers."""
    if not isinstance(values, Mapping):
        raise ValueError(f"values must be a mapping of seed -> value, got {type(values).__name__}")
    if not values:
        raise ValueError("values is empty")
    pairs = []
    for seed, value in values.items():
        if isinstance(seed, bool) or not isinstance(seed, Integral):
            raise ValueError(f"seed must be an int, got {seed!r}")
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
            raise ValueError(f"value for seed {seed} must be a finite number, got {value!r}")
        pairs.append((int(seed), float(value)))
    return tuple(sorted(pairs))


def seed_summary(values: Mapping[int, float]) -> SeedSummary:
    """Mean and sample SD (ddof = 1) of a metric across seeds. Requires >= 2 seeds."""
    pairs = _validate(values)
    if len(pairs) < 2:
        raise ValueError(f"seed_summary needs >= 2 seeds for a sample SD, got {len(pairs)}")
    numbers = [v for _, v in pairs]
    return SeedSummary(
        mean=statistics.fmean(numbers),
        sd=statistics.stdev(numbers),
        n_seeds=len(pairs),
        values=pairs,
    )


def select_bundle_seed(val_a_eer: Mapping[int, float]) -> int:
    """The seed with the median val-A EER; among seeds tied at the median, the lowest seed.

    Requires an odd number of seeds, so the median is one of the values (a member). With an even
    count the median is the mean of the two middle values, which may belong to no seed.
    """
    pairs = _validate(val_a_eer)
    if len(pairs) % 2 == 0:
        raise ValueError(
            f"select_bundle_seed needs an odd number of seeds, got {len(pairs)}: with an even count "
            "the median is the mean of the two middle values and need not belong to any seed"
        )
    m = statistics.median(v for _, v in pairs)
    return min(seed for seed, v in pairs if v == m)
