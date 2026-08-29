"""Round-2 coverage / metric / change-point tests.

Tests for:
* KDE-support coverage metric (P1 #11)
* Top-k entropy coverage (P1 #12)
* W2-barycenter coverage (P1 #13)
* Kernel Lipschitz density diagnostic (P2 #30)
* Soft-mode LayeredMetricPanel (P1 #27)
* CUSUM / Bayesian change-point detector (P1 #28)
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.eval.coverage_r2 import (
    COVERAGE_REGISTRY,
    KDE_SUPPORT_DEFAULT_BANDWIDTH,
    CoverageFamily,
    W2BarycenterCoverage,
    support_coverage_score,
    top_k_coverage_with_entropy,
)
from adaptive_reflow.eval.lipschitz_diagnostic import kernel_lipschitz_constant
from adaptive_reflow.eval.metric_panel import (
    SoftLayeredMetricPanel,
    build_soft_layered_metric_panel,
    enforce_separation,
)
from adaptive_reflow.eval.protocol import (
    BayesianChangePointDetector,
    CUSUMOscillationDetector,
)

# ---------------------------------------------------------------------------
# KDE-support coverage
# ---------------------------------------------------------------------------


def test_kde_support_default_bandwidth() -> None:
    assert KDE_SUPPORT_DEFAULT_BANDWIDTH > 0.0


def test_support_coverage_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        support_coverage_score(np.zeros((2, 2)), np.zeros((0, 2)))


def test_support_coverage_constant_bandwidth() -> None:
    rng = np.random.default_rng(42)
    samples = rng.standard_normal((100, 2))
    ref = rng.standard_normal((100, 2))
    score = support_coverage_score(samples, ref, bandwidth=0.5)
    assert 0.0 <= score <= 1.0


def test_support_coverage_separation() -> None:
    rng = np.random.default_rng(42)
    ref = rng.standard_normal((100, 2))
    near = rng.standard_normal((100, 2))
    far = 10.0 + 0.01 * rng.standard_normal((100, 2))
    assert support_coverage_score(near, ref) > support_coverage_score(far, ref)


# ---------------------------------------------------------------------------
# Top-k entropy coverage
# ---------------------------------------------------------------------------


def test_top_k_entropy_returns_finite() -> None:
    rng = np.random.default_rng(7)
    samples = rng.standard_normal((128, 2))
    ref = rng.standard_normal((8, 2))
    est = top_k_coverage_with_entropy(samples, ref, radius=2.0)
    assert math.isfinite(est.entropy_nats)


def test_top_k_entropy_bad_bandwidth_raises() -> None:
    rng = np.random.default_rng(0)
    samples = rng.standard_normal((64, 2))
    ref = rng.standard_normal((8, 2))
    with pytest.raises(ValueError):
        top_k_coverage_with_entropy(samples, ref, radius=-1.0)


# ---------------------------------------------------------------------------
# W2-barycenter coverage
# ---------------------------------------------------------------------------


def test_w2_barycenter_registry() -> None:
    assert CoverageFamily.W2_BARYCENTER in COVERAGE_REGISTRY


def test_w2barycenter_class_round_trip() -> None:
    cov = W2BarycenterCoverage(n_projections=32, seed=0)
    cfg = cov.to_config()
    cov2 = W2BarycenterCoverage.from_config(cfg)
    assert cov.config_hash() == cov2.config_hash()


def test_w2barycenter_estimator_empty() -> None:
    cov = W2BarycenterCoverage(n_projections=8)
    assert cov.estimate(np.zeros((1, 2))) == 0.0


# ---------------------------------------------------------------------------
# Kernel Lipschitz
# ---------------------------------------------------------------------------


def test_kernel_lipschitz_constant_converged() -> None:
    rng = np.random.default_rng(0)
    samples = rng.standard_normal((128, 4))
    report = kernel_lipschitz_constant(samples)
    assert report.n_samples == 128
    assert report.constant > 0.0
    # On converged data, L_k * sqrt(N) is finite (the bounded-Lipschitz
    # target is asymptotic; we only assert finiteness).
    assert math.isfinite(report.ratio_to_sqrt_n)


def test_kernel_lipschitz_constant_1d() -> None:
    rng = np.random.default_rng(0)
    samples = rng.standard_normal((64, 1))
    report = kernel_lipschitz_constant(samples)
    assert report.n_samples == 64


# ---------------------------------------------------------------------------
# Soft-mode LayeredMetricPanel
# ---------------------------------------------------------------------------


def test_soft_panel_records_overlap() -> None:
    raw = {"a": 1.0, "b": 2.0}
    ar = {"b": 3.0, "c": 4.0}  # overlap on "b".
    post = {"c": 5.0, "d": 6.0}
    panel = build_soft_layered_metric_panel(
        raw_generation_metrics=raw,
        adaptive_reflow_metrics=ar,
        postprocess_assisted_metrics=post,
        strict=False,
    )
    assert isinstance(panel, SoftLayeredMetricPanel)
    assert "b" in panel.overlapping_keys


def test_soft_panel_strict_raises() -> None:
    raw = {"a": 1.0, "b": 2.0}
    ar = {"b": 3.0}  # overlap on "b".
    post = {}
    with pytest.raises(ValueError):
        build_soft_layered_metric_panel(
            raw_generation_metrics=raw,
            adaptive_reflow_metrics=ar,
            postprocess_assisted_metrics=post,
            strict=True,
        )


def test_soft_panel_no_overlap() -> None:
    raw = {"a": 1.0}
    ar = {"b": 2.0}
    post = {"c": 3.0}
    panel = build_soft_layered_metric_panel(
        raw_generation_metrics=raw,
        adaptive_reflow_metrics=ar,
        postprocess_assisted_metrics=post,
        strict=False,
    )
    assert panel.overlapping_keys == ()


def test_soft_panel_enforce_separation() -> None:
    panel = build_soft_layered_metric_panel(
        raw_generation_metrics={"a": 1.0},
        adaptive_reflow_metrics={"b": 2.0},
        postprocess_assisted_metrics={"c": 3.0},
        strict=False,
    )
    ok, overlap = enforce_separation(panel)
    assert ok
    assert overlap == ()


# ---------------------------------------------------------------------------
# CUSUM / Bayesian change-point detectors
# ---------------------------------------------------------------------------


def test_cusum_no_detection_when_stable() -> None:
    det = CUSUMOscillationDetector(mu_0=0.0, sigma=1.0, threshold=20.0)
    rng = np.random.default_rng(0)
    fired_count = 0
    for _ in range(50):
        v = rng.standard_normal()
        if det.update(float(v)):
            fired_count += 1
    assert fired_count == 0


def test_cusum_detects_mean_shift() -> None:
    det = CUSUMOscillationDetector(mu_0=0.0, sigma=1.0, threshold=3.0, drift_k=0.0)
    # 10 observations of 5.0 (a clear mean shift).
    for _ in range(10):
        det.update(5.0)
    assert det.detection_count >= 1


def test_cusum_reset() -> None:
    det = CUSUMOscillationDetector(mu_0=0.0, sigma=1.0, threshold=3.0)
    det.update(5.0)
    det.reset()
    assert det.cumulative_pos == 0.0
    assert det.cumulative_neg == 0.0
    assert det.detection_count == 0


def test_bayesian_change_point_detector() -> None:
    det = BayesianChangePointDetector(hazard_rate=0.05, alarm_threshold=0.5)
    # Feed a stable series; detection probability should be low.
    rng = np.random.default_rng(0)
    det.update(float(rng.standard_normal()))
    det.update(float(rng.standard_normal()))
    det.update(float(rng.standard_normal()))
    assert isinstance(det.snapshot(), dict)


# ---------------------------------------------------------------------------
# Coverage registry sanity
# ---------------------------------------------------------------------------


def test_coverage_registry_keys() -> None:
    assert set(COVERAGE_REGISTRY) == {
        CoverageFamily.KDE_SUPPORT,
        CoverageFamily.TOP_K_ENTROPY,
        CoverageFamily.W2_BARYCENTER,
    }
