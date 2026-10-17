"""Bootstrap CI tests on small synthetic arrays (no dataset access).

Step 4: bootstrap_ci, percentile intervals with row or cluster resampling (Protocol v1.0 §5, D11).
The statistic receives row indices into the test's own arrays.
"""
from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pytest

from src.evaluation.bootstrap import BootstrapCI, bootstrap_ci
from src.evaluation.metrics import eer, roc_auc


def _mean_of(values):
    return lambda idx: float(np.mean(values[idx]))


def test_deterministic_for_a_seed():
    # Same seed -> same generator stream -> same resamples -> identical (frozen, comparable)
    # dataclass. Another seed draws other resamples, so the percentile bounds move.
    x = np.random.default_rng(2026).normal(size=100)
    first = bootstrap_ci(_mean_of(x), len(x), seed=2026)
    again = bootstrap_ci(_mean_of(x), len(x), seed=2026)
    other = bootstrap_ci(_mean_of(x), len(x), seed=7)
    assert isinstance(first, BootstrapCI)
    assert first == again
    assert (other.low, other.high) != (first.low, first.high)


def test_estimate_is_statistic_on_full_data():
    # x = [1, 2, 3, 4, 10]: mean on np.arange(5) = 20 / 5 = 4.0, the reported estimate
    # (not the mean of the resampled means).
    x = np.array([1.0, 2.0, 3.0, 4.0, 10.0])
    ci = bootstrap_ci(_mean_of(x), len(x), n_resamples=200)
    assert ci.estimate == 4.0
    assert (ci.confidence, ci.n_resamples, ci.n_invalid) == (0.95, 200, 0)


def test_mean_ci_matches_normal_theory():
    # For the mean of n i.i.d. values the 95% interval width is about 2 * 1.96 * sd / sqrt(n).
    # n = 400 N(0, 1) values: theory ~ 0.196. The percentile bootstrap should be within +-20%.
    x = np.random.default_rng(2026).normal(size=400)
    ci = bootstrap_ci(_mean_of(x), len(x))
    theory = 2 * 1.96 * x.std(ddof=1) / math.sqrt(len(x))
    width = ci.high - ci.low
    print(f"bootstrap width {width:.4f}, theory {theory:.4f}, ratio {width / theory:.3f}")
    assert ci.low <= x.mean() <= ci.high
    assert 0.8 * theory <= width <= 1.2 * theory


def test_cluster_resampling_keeps_clusters_whole_and_widens_ci():
    # 20 clusters of 10 identical values: the rows of a cluster carry no independent information.
    # A cluster resample is a union of whole clusters, so every index set has a multiple of 10
    # rows and contains each drawn cluster completely. The effective sample size is 20, not 200,
    # so the cluster CI is about sqrt(200 / 20) ~ 3.2x wider than the row CI; require >= 2x.
    cluster_values = np.random.default_rng(2026).normal(size=20)
    x = np.repeat(cluster_values, 10)
    clusters = [f"c{i}" for i in range(20) for _ in range(10)]
    sizes, whole = [], []

    def recording_mean(idx):
        sizes.append(len(idx))
        rows_per_cluster = Counter(clusters[i] for i in idx)
        whole.append(all(count % 10 == 0 for count in rows_per_cluster.values()))
        return float(np.mean(x[idx]))

    cluster_ci = bootstrap_ci(recording_mean, len(x), clusters=clusters, n_resamples=300)
    row_ci = bootstrap_ci(_mean_of(x), len(x), n_resamples=300)
    assert all(size % 10 == 0 for size in sizes)
    assert all(whole)
    assert (cluster_ci.high - cluster_ci.low) >= 2 * (row_ci.high - row_ci.low)


def test_paired_difference_on_same_resample_is_zero():
    # The statistic sees one index set per resample, so mean(a[idx]) - mean(a[idx]) is exactly 0
    # every time: a paired difference (H1, H5, H6) uses the same rows for both terms.
    a = np.random.default_rng(2026).normal(size=50)
    ci = bootstrap_ci(lambda idx: float(np.mean(a[idx]) - np.mean(a[idx])), len(a))
    assert ci.low == ci.high == ci.estimate == 0.0


def test_works_with_harness_eer():
    # 200 random labels and scores (seed 2026): eer() is the Step 1 harness metric. Resamples of
    # 200 rows almost surely keep both classes; the interval must bracket the full-data EER.
    rng = np.random.default_rng(2026)
    labels = np.array([0] * 100 + [1] * 100)
    scores = rng.random(200)
    ci = bootstrap_ci(lambda idx: eer(labels[idx], scores[idx])[0], len(labels))
    assert ci.estimate == eer(labels, scores)[0]
    assert ci.low <= ci.estimate <= ci.high


def test_invalid_resamples_are_excluded_and_counted():
    # labels [0, 1], scores [0.2, 0.8]: a resample of 2 rows has one class with probability 1/2
    # (indices (0, 0) or (1, 1)), and roc_auc raises ValueError there -> invalid. Every valid
    # resample has both rows -> AUC 1.0, so the CI from valid ones is [1.0, 1.0].
    labels = np.array([0, 1])
    scores = np.array([0.2, 0.8])
    ci = bootstrap_ci(lambda idx: roc_auc(labels[idx], scores[idx]), 2)
    print(f"n_invalid {ci.n_invalid} of {ci.n_resamples}")
    assert 0 < ci.n_invalid < ci.n_resamples
    assert ci.estimate == ci.low == ci.high == 1.0


def test_all_resamples_invalid_raises():
    # The full-data call succeeds, every resample raises ValueError -> no valid statistic -> raise.
    calls = []

    def fails_on_resamples(idx):
        calls.append(1)
        if len(calls) > 1:
            raise ValueError("undefined")
        return 0.5

    with pytest.raises(ValueError, match="all 50 resamples are invalid"):
        bootstrap_ci(fails_on_resamples, 10, n_resamples=50)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"n_resamples": 0}, "n_resamples must be >= 1"),
        ({"n_resamples": 10.0}, "n_resamples must be an int"),
        ({"n_resamples": True}, "n_resamples must be an int"),
        ({"confidence": 0}, "confidence must be a number in"),
        ({"confidence": 1}, "confidence must be a number in"),
        ({"clusters": [0, 1, 2]}, "clusters must have length"),
        ({"seed": 1.5}, "seed must be an int"),
        ({"n": 0}, "n must be >= 1"),
        ({"n": True}, "n must be an int"),
    ],
)
def test_invalid_parameters_raise(kwargs, message):
    # Each parameter outside its domain (counts as non-bool ints >= 1, 0 < confidence < 1,
    # clusters of length n) is rejected before any resampling.
    x = np.arange(5, dtype=float)
    args = {"n": 5, **kwargs}
    n = args.pop("n")
    with pytest.raises(ValueError, match=message):
        bootstrap_ci(_mean_of(x), n, **args)


def test_nan_estimate_raises():
    # A statistic that is NaN on the full data has no estimate to report -> ValueError.
    with pytest.raises(ValueError, match="NaN on the full data"):
        bootstrap_ci(lambda idx: float("nan"), 5)
