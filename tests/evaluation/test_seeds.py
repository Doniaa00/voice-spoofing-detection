"""Seed summary and bundle-seed rule tests on synthetic numbers (no dataset access).

Step 5: seed_summary (mean ± sample SD across seeds) and select_bundle_seed (median val-A EER,
tie -> lower seed) (Protocol v1.0 §4–5, D11).
"""
from __future__ import annotations

import math

import pytest

from src.evaluation.seeds import SeedSummary, seed_summary, select_bundle_seed


def test_seed_summary_hand_case():
    # values 0.10, 0.12, 0.14: mean = 0.36 / 3 = 0.12.
    # deviations -0.02, 0, +0.02 -> squares 0.0004, 0, 0.0004, sum 0.0008.
    # sample SD (ddof = 1): sqrt(0.0008 / 2) = sqrt(0.0004) = 0.02.
    summary = seed_summary({0: 0.10, 1: 0.12, 2: 0.14})
    assert isinstance(summary, SeedSummary)
    assert summary.mean == pytest.approx(0.12)
    assert summary.sd == pytest.approx(0.02)
    assert summary.n_seeds == 3
    assert summary.values == ((0, 0.10), (1, 0.12), (2, 0.14))


def test_select_bundle_seed_median():
    # sorted values 0.10 (seed 1), 0.20 (seed 2), 0.30 (seed 0): median 0.20 -> seed 2.
    assert select_bundle_seed({0: 0.30, 1: 0.10, 2: 0.20}) == 2


def test_select_bundle_seed_tie_at_median():
    # sorted values 0.1 (seed 1), 0.2, 0.2: median 0.2, shared by seeds 0 and 2 -> lower seed 0.
    assert select_bundle_seed({0: 0.2, 1: 0.1, 2: 0.2}) == 0


def test_select_bundle_seed_all_equal():
    # all values 0.1: median 0.1, shared by seeds 0, 1, 2 -> lowest seed 0.
    assert select_bundle_seed({0: 0.1, 1: 0.1, 2: 0.1}) == 0


def test_order_independence():
    # Same mapping, reversed insertion order: values are sorted by seed before use, so the seed
    # choice and the summary (including its values tuple) are identical.
    forward = {0: 0.30, 1: 0.10, 2: 0.20}
    backward = {2: 0.20, 1: 0.10, 0: 0.30}
    assert select_bundle_seed(forward) == select_bundle_seed(backward) == 2
    assert seed_summary(forward) == seed_summary(backward)


@pytest.mark.parametrize("values", [{0: 0.1, 1: 0.2}, {0: 0.1, 1: 0.2, 2: 0.3, 3: 0.4}])
def test_select_bundle_seed_even_count_raises(values):
    # Even count: the median is the mean of the two middle values, which need not belong to a seed.
    with pytest.raises(ValueError, match="odd number of seeds"):
        select_bundle_seed(values)


def test_seed_summary_one_seed_raises():
    # One seed has no sample SD (division by n - 1 = 0).
    with pytest.raises(ValueError, match=">= 2 seeds"):
        seed_summary({0: 0.1})


@pytest.mark.parametrize(
    "values",
    [
        {},
        {0: math.nan, 1: 0.1, 2: 0.2},
        {0: math.inf, 1: 0.1, 2: 0.2},
        {0: -math.inf, 1: 0.1, 2: 0.2},
        {0: "0.1", 1: 0.1, 2: 0.2},
        {0: True, 1: 0.1, 2: 0.2},
        {True: 0.1, 1: 0.2, 2: 0.3},
        {0.0: 0.1, 1: 0.2, 2: 0.3},
        [0.1, 0.2, 0.3],
    ],
)
@pytest.mark.parametrize("function", [seed_summary, select_bundle_seed])
def test_invalid_input_raises(function, values):
    with pytest.raises(ValueError):
        function(values)
