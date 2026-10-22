"""GAP-71 — image spectral restart blend and the matched-NFE guard.

Pre-registration: ``docs/audit/gap71-image-spectral.md`` §0. This file tests the
two code artefacts that gap landed, both default-off:

* ``_spectral_restart_blend`` / ``RectifiedFlowCIFARAdapter(spectral_band_fraction=...)``
  — radial-frequency selective restart, ``cut = memory_fraction``;
* ``tools.run_sota_cifar_experiment._check_matched_nfe`` — the GAP-66 constraint
  on the CIFAR side, where ``--match-nfe budget`` does not bound the total.

No GPU, no torch: every adapter here is built with ``force_mode="synthetic"``.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from adaptive_reflow.adapters.rectified_flow_cifar import (
    RF_CIFAR_CLAMP,
    RF_CIFAR_STATE_SHAPE,
    RectifiedFlowCIFARAdapter,
    _spectral_restart_blend,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _adapter(*, spectral: float | None = None) -> RectifiedFlowCIFARAdapter:
    return RectifiedFlowCIFARAdapter(
        weights_path=None,
        force_mode="synthetic",
        num_steps=2,
        synthetic_seed=42,
        spectral_band_fraction=spectral,
    )


def _make_final_policy(*, policy_id: str, beta: float) -> object:
    from adaptive_reflow.contracts import (
        ArtifactHash,
        ChannelName,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )

    channel = ChannelName("image")
    policy = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("run-gap71"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={channel: FactorValue(float(beta))},
        alpha_by_channel={channel: FactorValue(1.0)},
        fresh_noise_floor_by_channel={channel: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={channel: True},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _x0(adapter: RectifiedFlowCIFARAdapter, digest: str) -> np.ndarray:
    return np.asarray(adapter._native_states.get(digest)["x0"], dtype=np.float64)


def _restarted(
    adapter: RectifiedFlowCIFARAdapter, beta: float
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(prior_x0, restarted_x0)`` for one restart."""
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    prior = _x0(adapter, bundle.native_state_digest)
    policy = _make_final_policy(policy_id=f"p-{beta}-{id(adapter)}", beta=beta)
    out = adapter.apply_restart_distribution(bundle, policy)
    return prior, _x0(adapter, out.native_state_digest)


def _radial_energy(x: np.ndarray, *, low: bool) -> float:
    """Mean |FFT|^2 in the lower / upper half of the radial frequency axis."""
    height, width = x.shape[-2], x.shape[-1]
    fy = np.fft.fftfreq(height)
    fx = np.fft.fftfreq(width)
    radius = np.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2) / np.sqrt(0.5)
    mask = radius <= 0.5 if low else radius > 0.5
    power = np.abs(np.fft.fft2(x, axes=(-2, -1))) ** 2
    return float(power[..., mask].mean())


# ---------------------------------------------------------------------------
# 1. the operator
# ---------------------------------------------------------------------------


def test_spectral_blend_endpoints_are_the_per_pixel_endpoints() -> None:
    """``cut = 0`` is pure fresh and ``cut = 1`` is pure prior, exactly.

    This is the property that makes the operator hyperparameter-free: the two
    ends of the ``m`` sweep are unchanged, so a difference at ``0 < m < 1`` is
    attributable to the band structure and nothing else.
    """
    rng = np.random.default_rng(0)
    prior = rng.standard_normal(RF_CIFAR_STATE_SHAPE)
    fresh = rng.standard_normal(RF_CIFAR_STATE_SHAPE)

    np.testing.assert_array_equal(_spectral_restart_blend(prior, fresh, 0.0), fresh)
    np.testing.assert_array_equal(_spectral_restart_blend(prior, fresh, 1.0), prior)


def test_spectral_blend_is_frequency_selective() -> None:
    """Low bands come from the prior, high bands from the fresh draw.

    The prior is a smooth low-frequency ramp and the fresh draw is white noise,
    so a correct operator keeps the ramp's low-band power and replaces its
    high-band power with the noise's.
    """
    grid = np.linspace(-1.0, 1.0, RF_CIFAR_STATE_SHAPE[-1])
    ramp = (grid[None, None, :] + grid[None, :, None]) * np.ones(
        (RF_CIFAR_STATE_SHAPE[0], 1, 1)
    )
    rng = np.random.default_rng(7)
    fresh = rng.standard_normal(RF_CIFAR_STATE_SHAPE)

    out = _spectral_restart_blend(ramp, fresh, 0.5)

    assert out.shape == RF_CIFAR_STATE_SHAPE
    # Low band: much closer to the prior than to the fresh draw.
    assert _radial_energy(out - ramp, low=True) < 0.25 * _radial_energy(
        fresh - ramp, low=True
    )
    # High band: the prior's high-frequency content is gone, replaced by fresh.
    assert _radial_energy(out - fresh, low=False) < 0.25 * _radial_energy(
        ramp - fresh, low=False
    )


def test_spectral_blend_is_deterministic_and_finite() -> None:
    rng = np.random.default_rng(3)
    prior = rng.standard_normal(RF_CIFAR_STATE_SHAPE)
    fresh = rng.standard_normal(RF_CIFAR_STATE_SHAPE)
    a = _spectral_restart_blend(prior, fresh, 0.3)
    b = _spectral_restart_blend(prior, fresh, 0.3)
    np.testing.assert_array_equal(a, b)
    assert np.all(np.isfinite(a))
    assert a.dtype == np.float64


# ---------------------------------------------------------------------------
# 2. the adapter wiring
# ---------------------------------------------------------------------------


def test_default_adapter_keeps_the_per_pixel_blend() -> None:
    """``spectral_band_fraction=None`` must not change the blend arithmetic."""
    adapter = _adapter()
    assert adapter._spectral_band_fraction is None
    prior, out = _restarted(adapter, beta=0.5)
    # m = 1 - beta = 0.5; the fresh draw is seed-derived and not reachable from
    # outside, so the sound check is that the result is a convex combination
    # that the clamp did not have to touch.
    assert out.shape == RF_CIFAR_STATE_SHAPE
    assert np.all(np.isfinite(out))
    assert np.max(np.abs(out)) <= RF_CIFAR_CLAMP + 1e-9
    assert not np.array_equal(out, prior)


def test_spectral_adapter_agrees_with_default_at_beta_zero() -> None:
    """``beta = 1`` ⇒ ``m = 0`` ⇒ both operators return the same fresh draw."""
    default_prior, default_out = _restarted(_adapter(), beta=1.0)
    spectral_prior, spectral_out = _restarted(_adapter(spectral=0.5), beta=1.0)
    np.testing.assert_array_equal(default_prior, spectral_prior)
    # The fresh draw is keyed on policy_hash + round; the two adapters share a
    # synthetic seed, so the draws are the same and the operators coincide.
    np.testing.assert_allclose(default_out, spectral_out, atol=1e-12)


def test_spectral_adapter_differs_from_default_in_the_interior() -> None:
    """At ``beta = 0.5`` the two operators must not produce the same field."""
    _, default_out = _restarted(_adapter(), beta=0.5)
    _, spectral_out = _restarted(_adapter(spectral=0.5), beta=0.5)
    assert not np.allclose(default_out, spectral_out)


def test_spectral_fraction_out_of_range_is_rejected() -> None:
    for bad in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError, match="spectral_band_fraction_must_be"):
            _adapter(spectral=bad)


# ---------------------------------------------------------------------------
# 3. the matched-NFE guard (GAP-66 constraint, CIFAR side)
# ---------------------------------------------------------------------------


def test_matched_nfe_guard_reports_mismatch() -> None:
    """Wave 280's own configuration: framework NFE=3 against baseline NFE=2."""
    from tools.run_sota_cifar_experiment import _check_matched_nfe

    rows = [
        {"name": "baseline", "framework_total_nfe": 0},
        {"name": "CosineAnnealScheduler", "framework_total_nfe": 3},
    ]
    matched, mismatch = _check_matched_nfe(2, rows, require=False)
    assert matched is False
    assert mismatch == {"CosineAnnealScheduler": {"baseline": 2, "framework": 3}}


def test_matched_nfe_guard_fails_closed_when_required() -> None:
    from tools.run_sota_cifar_experiment import _check_matched_nfe

    rows = [{"name": "CosineAnnealScheduler", "framework_total_nfe": 3}]
    with pytest.raises(SystemExit) as exc:
        _check_matched_nfe(2, rows, require=True)
    assert "--require-matched-nfe" in str(exc.value)


def test_matched_nfe_guard_accepts_an_exact_match() -> None:
    from tools.run_sota_cifar_experiment import _check_matched_nfe

    rows = [
        {"name": "baseline", "framework_total_nfe": 0},
        {"name": "CosineAnnealScheduler", "framework_total_nfe": 2},
        {"name": "FreeTrajScheduler", "framework_total_nfe": 2},
    ]
    matched, mismatch = _check_matched_nfe(2, rows, require=True)
    assert matched is True
    assert mismatch == {}
