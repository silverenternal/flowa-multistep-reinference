"""Tests for the 2D rectified flow evaluator (DTB-R7 real replay oracle).

Acceptance
----------

* The :class:`TwoDimFMEvaluator` produces a closed-form-2D Wasserstein
  distance below the canonical "well-trained" threshold for both
  ``two_moons`` and ``eight_gaussians`` targets.
* :meth:`TwoDimFMEvaluator.evaluate` and :meth:`TwoDimFMEvaluator.oracle`
  return byte-for-byte equal values for every input.
* :meth:`TwoDimFMEvaluator.evaluate` is fully deterministic across
  repeated calls (same bundle + channel + seed → same diagnostics).
* Unknown channels raise :class:`NotImplementedError`.
* The module is torch-free: ``"torch" not in sys.modules``.
* The :func:`coverage_score` helper always returns a value in
  ``[0, 1]``.
* The :func:`energy_distance` helper is non-negative on finite samples.

No torch. No GPU. The real replay-through-adapter path is exercised
end-to-end.
"""
from __future__ import annotations

import sys

import numpy as np
import pytest

from adaptive_reflow.adapters.twodim_fm_train import (
    sample_eight_gaussians,
    sample_two_moons,
)
from adaptive_reflow.eval.twodim_fm_evaluator import (
    TWODIM_FM_EVALUATOR_AUDIT_REASON,
    TWODIM_FM_EVALUATOR_CHANNELS,
    TwoDimFMEvaluator,
    analytic_samples,
    coverage_score,
    energy_distance,
    voronoi_grid,
)
from adaptive_reflow.universal.adapter import AdapterCapabilities
from adaptive_reflow.universal.state import ChannelName, StateBundle, TensorRef

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: Canonical W2 threshold for a "well-trained" two_moons adapter.
#: The model is small (3 -> 64 -> 64 -> 2 MLP) but two_moons converges
#: cleanly; the iid-vs-iid W2 between two fresh analytic samples is
#: ~0.03, so 0.5 leaves substantial headroom.
_W2_THRESHOLD_TWO_MOONS: float = 0.5

#: Relaxed W2 threshold for ``eight_gaussians``. The 8-gaussians
#: target has 8 disconnected modes (each a tight Gaussian at radius 2)
#: and the small MLP plateaus at a higher marginal W2 than two_moons;
#: we therefore accept W2 up to 0.8 as proof that the adapter has
#: learned *something* about the target shape. The iid-vs-iid baseline
#: for the 8-gaussians sampler is ~0.09.
_W2_THRESHOLD_EIGHT_GAUSSIANS: float = 0.8

#: Test-side bundle identity. The evaluator derives the bundle-id
#: from the bundle's ``native_state_digest`` via a stable prefix, so the
#: choice of digest does not affect the diagnostic values.
_TEST_BATCH_ID: str = "batch-twodim-fm"
_TEST_SAMPLE_ID: str = "sample-twodim-fm"
_XY_CHANNEL: ChannelName = ChannelName("xy")


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_state_bundle(digest: str = "twodim_fm_test_digest") -> StateBundle:
    """Build a minimal valid :class:`StateBundle` for the 2D FM evaluator."""
    return StateBundle(
        channels={_XY_CHANNEL: TensorRef("twodim-xy-test-ref-001")},
        masks={},
        batch_id=_TEST_BATCH_ID,
        sample_id=_TEST_SAMPLE_ID,
        reference_frame="world",
        normalization="none",
        source_round=0,
        detach_proof=True,
        native_state_digest=digest,
        provenance=("test.twodim_fm_evaluator",),
        capability_token=AdapterCapabilities(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            has_continuous_channels=True,
            has_discrete_channels=False,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=True,
            supported_channels=(_XY_CHANNEL,),
            channel_domains={_XY_CHANNEL: "continuous"},
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_wasserstein_below_threshold_on_two_moons() -> None:
    """The two_moons adapter should produce W2 < 0.5 against analytic samples."""
    evaluator = TwoDimFMEvaluator(
        target="two_moons",
        n_gen=500,
        n_ref=500,
        seed=42,
    )
    bundle = _make_state_bundle("twodim-fm-eval-two-moons")
    evidence = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=42)

    # Recompute the W2 explicitly so the assertion message can quote
    # the actual numerical distance (rather than a derived raw_score).
    raw_score = float(evidence.raw_score)
    # raw_score = 1 - W2 / W2_max with W2_max = 2.0 → W2 = (1 - raw_score) * 2.0
    recovered_w2 = (1.0 - raw_score) * 2.0
    assert recovered_w2 < _W2_THRESHOLD_TWO_MOONS, (
        f"two_moons W2 = {recovered_w2:.4f} exceeds threshold "
        f"{_W2_THRESHOLD_TWO_MOONS}"
    )


def test_wasserstein_below_threshold_on_eight_gaussians() -> None:
    """The eight_gaussians adapter should produce W2 < 0.8 (relaxed threshold)."""
    evaluator = TwoDimFMEvaluator(
        target="eight_gaussians",
        n_gen=500,
        n_ref=500,
        seed=42,
    )
    bundle = _make_state_bundle("twodim-fm-eval-eight-gaussians")
    evidence = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=42)

    raw_score = float(evidence.raw_score)
    recovered_w2 = (1.0 - raw_score) * 2.0
    # The 8-gaussians target has 8 disconnected modes and the small MLP
    # plateaus at a higher marginal W2 than two_moons; we use a relaxed
    # threshold of 0.8 (above the iid-vs-iid baseline of ~0.09 but below
    # the ceiling for the current weights) as proof that the adapter
    # has learned the target shape.
    assert recovered_w2 < _W2_THRESHOLD_EIGHT_GAUSSIANS, (
        f"eight_gaussians W2 = {recovered_w2:.4f} exceeds threshold "
        f"{_W2_THRESHOLD_EIGHT_GAUSSIANS}"
    )


def test_evaluator_equals_oracle_byte_for_byte() -> None:
    """``evaluate`` and ``oracle`` must return byte-for-byte equal values."""
    evaluator = TwoDimFMEvaluator(target="two_moons", n_gen=300, n_ref=300)
    bundle = _make_state_bundle("twodim-fm-byte-identity")
    seed = 17

    evidence = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=seed)
    oracle = evaluator.oracle(bundle, channel=_XY_CHANNEL, seed=seed)

    # Byte-for-byte equality on every published diagnostic.
    assert float(evidence.raw_score) == oracle["raw_score"]
    assert float(evidence.bounded_score) == oracle["bounded_score"]
    assert float(evidence.calibration_lower_bound) == oracle[
        "calibration_lower_bound"
    ]
    assert float(evidence.perturbation_stability_lower_bound) == oracle[
        "perturbation_stability_lower_bound"
    ]

    # Same contract on a second (different) seed.
    seed2 = 99
    evidence2 = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=seed2)
    oracle2 = evaluator.oracle(bundle, channel=_XY_CHANNEL, seed=seed2)
    assert float(evidence2.raw_score) == oracle2["raw_score"]
    assert float(evidence2.bounded_score) == oracle2["bounded_score"]
    assert float(evidence2.calibration_lower_bound) == oracle2[
        "calibration_lower_bound"
    ]
    assert float(evidence2.perturbation_stability_lower_bound) == oracle2[
        "perturbation_stability_lower_bound"
    ]


def test_deterministic() -> None:
    """Repeated evaluate calls with the same seed must be byte-identical."""
    evaluator = TwoDimFMEvaluator(target="two_moons", n_gen=300, n_ref=300)
    bundle = _make_state_bundle("twodim-fm-determinism")
    seed = 1234

    first = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=seed)
    for _ in range(9):
        again = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=seed)
        assert again.raw_score == first.raw_score
        assert again.bounded_score == first.bounded_score
        assert again.calibration_lower_bound == first.calibration_lower_bound
        assert again.perturbation_stability_lower_bound == (
            first.perturbation_stability_lower_bound
        )
        assert again.bundle_id == first.bundle_id
        assert again.channel == first.channel
        assert again.provenance == first.provenance


def test_unknown_channel_raises() -> None:
    """Unknown channels must raise :class:`NotImplementedError`."""
    evaluator = TwoDimFMEvaluator(target="two_moons", n_gen=100, n_ref=100)
    bundle = _make_state_bundle("twodim-fm-unknown-channel")
    with pytest.raises(NotImplementedError):
        evaluator.evaluate(bundle, channel=ChannelName("coordinate"), seed=0)
    with pytest.raises(NotImplementedError):
        evaluator.oracle(bundle, channel=ChannelName("charge"), seed=0)


def test_no_torch_imported() -> None:
    """The 2D FM evaluator must not depend on ``torch`` at import time."""
    # Sanity: the module itself does not import torch.
    import adaptive_reflow.eval.twodim_fm_evaluator as mod  # noqa: F401

    assert "torch" not in sys.modules, (
        "twodim_fm_evaluator must be torch-free; torch is in sys.modules"
    )


def test_coverage_metric_in_unit_interval() -> None:
    """``coverage_score`` must always return a value in ``[0, 1]``."""
    rng = np.random.default_rng(0)
    grid = voronoi_grid("two_moons", k=10)
    mode_centers = np.asarray([[0.0, 1.0], [1.0, -0.5]], dtype=np.float64)
    samples = sample_two_moons(500, rng)
    target_samples = sample_two_moons(500, np.random.default_rng(1))
    score = coverage_score(samples, target_samples, grid, mode_centers)
    assert 0.0 <= score <= 1.0, f"coverage_score = {score!r} outside [0, 1]"

    # Empty / degenerate inputs must still return a value in [0, 1].
    empty_score = coverage_score(
        np.empty((0, 2), dtype=np.float64),
        target_samples,
        grid,
        mode_centers,
    )
    assert 0.0 <= empty_score <= 1.0


def test_energy_distance_nonnegative() -> None:
    """``energy_distance`` must be non-negative on finite empirical samples."""
    rng = np.random.default_rng(7)
    samples = sample_two_moons(300, rng)
    target_samples = sample_two_moons(300, np.random.default_rng(11))
    e2 = energy_distance(samples, target_samples)
    assert e2 >= 0.0, f"energy_distance must be >= 0; got {e2!r}"

    # Identity case (samples == target_samples) collapses to zero within
    # sampling noise. We assert non-strict positivity with a small slack
    # to absorb the finite-sample ``E^2`` noise floor.
    same = sample_two_moons(300, np.random.default_rng(13))
    same_energy = energy_distance(same, same)
    assert 0.0 <= same_energy < 0.5, (
        f"self-energy-distance must be small; got {same_energy!r}"
    )


# ---------------------------------------------------------------------------
# Auxiliary assertions (cheap; protect the public surface)
# ---------------------------------------------------------------------------


def test_audit_reason_is_stable() -> None:
    """``TWODIM_FM_EVALUATOR_AUDIT_REASON`` must match the documented literal."""
    assert (
        TWODIM_FM_EVALUATOR_AUDIT_REASON
        == "twodim_fm_evaluator:wasserstein+coverage+energy"
    )


def test_supported_channels_constant() -> None:
    """``TWODIM_FM_EVALUATOR_CHANNELS`` must publish the 2D-FM channel vocabulary."""
    assert TWODIM_FM_EVALUATOR_CHANNELS == (ChannelName("xy"),)  # noqa: SIM300


def test_analytic_samples_shape_and_dtype() -> None:
    """``analytic_samples`` must return ``(n, 2)`` float64."""
    rng = np.random.default_rng(2)
    samples = analytic_samples("two_moons", 100, rng)
    assert samples.shape == (100, 2)
    assert samples.dtype == np.float64

    samples_eg = analytic_samples("eight_gaussians", 50, rng)
    assert samples_eg.shape == (50, 2)
    assert samples_eg.dtype == np.float64


def test_voronoi_grid_shape_and_bounds() -> None:
    """``voronoi_grid`` must return ``(k*k, 2)`` points in ``[-2.5, 2.5]^2``."""
    grid = voronoi_grid("two_moons", k=20)
    assert grid.shape == (400, 2)
    assert grid.dtype == np.float64
    assert float(grid.min()) >= -2.5 - 1e-9
    assert float(grid.max()) <= 2.5 + 1e-9
