"""Tests for the bias-corrected FID bootstrap interval (GAP-57 §7)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gap56_r5c_paired_bootstrap import _bias_corrected_ci  # noqa: E402


def test_interval_contains_the_point_estimate_under_a_large_bias() -> None:
    # A bootstrap distribution centred 1.3 below the point estimate, which is
    # the pattern actually observed (e.g. w16e1_5k_s42 cosine: point -3.575,
    # bootstrap mean -4.844).
    rng = np.random.default_rng(0)
    point = -3.575
    deltas = rng.normal(loc=point - 1.268, scale=0.35, size=2000)
    lo, hi, bias = _bias_corrected_ci(point, deltas)
    assert lo < point < hi
    assert bias == pytest.approx(float(deltas.mean()) - point)


def test_interval_is_the_percentile_interval_when_unbiased() -> None:
    rng = np.random.default_rng(1)
    point = 0.5
    deltas = rng.normal(loc=point, scale=0.1, size=4000)
    lo, hi, bias = _bias_corrected_ci(point, deltas)
    raw_lo, raw_hi = np.percentile(deltas, [2.5, 97.5])
    assert abs(bias) < 0.01
    assert lo == pytest.approx(float(raw_lo), abs=0.02)
    assert hi == pytest.approx(float(raw_hi), abs=0.02)


def test_correction_preserves_width() -> None:
    rng = np.random.default_rng(2)
    point = -2.0
    deltas = rng.normal(loc=-3.0, scale=0.4, size=3000)
    lo, hi, _ = _bias_corrected_ci(point, deltas)
    raw_lo, raw_hi = np.percentile(deltas, [2.5, 97.5])
    assert (hi - lo) == pytest.approx(float(raw_hi - raw_lo))


def test_negative_bias_shifts_the_interval_up() -> None:
    # If the bootstrap mean sits *above* the point estimate, the correction
    # must move the interval down.
    rng = np.random.default_rng(3)
    point = 1.0
    deltas = rng.normal(loc=2.0, scale=0.2, size=3000)
    lo, hi, bias = _bias_corrected_ci(point, deltas)
    raw_lo, raw_hi = np.percentile(deltas, [2.5, 97.5])
    assert bias > 0
    assert lo < float(raw_lo)
    assert hi < float(raw_hi)
    assert lo < point < hi
