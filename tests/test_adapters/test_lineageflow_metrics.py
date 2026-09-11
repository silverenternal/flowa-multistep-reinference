"""Smoke test suite for the LineageFlow protein flow-matching adapter (Wave 10).

Mirrors :mod:`tests.test_adapters.test_self_flow`'s structure for the
LineageFlow ESM-2 + flow-head adapter. Tests exercise the load-bearing
:class:`FlowMatchingODEAdapter` Protocol contract, the
``build_initial_state`` / ``solve_ode`` / ``observe_endpoint`` loop,
the per-position categorical restart blending, and the
synthetic-mode determinism invariant.

22 tests; all CPU-runnable.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from adaptive_reflow.adapters.lineageflow import (
    AMINO_ACID_CATEGORICAL,
    AUDIT_FORWARD_NOISE_APPLIED,
    AUDIT_LINEAGEFLOW_OBSERVED,
    AUDIT_LINEAGEFLOW_PERTURBATION_POLICY,
    AUDIT_LINEAGEFLOW_RESTART_BLEND,
    ERR_LINEAGEFLOW_FAMILY_ID_INVALID,
    ERR_LINEAGEFLOW_INTEGRATOR_UNKNOWN,
    ERR_LINEAGEFLOW_L_OUT_OF_RANGE,
    ERR_LINEAGEFLOW_NUM_STEPS,
    ERR_LINEAGEFLOW_VOCAB_OUT_OF_RANGE,
    LINEAGEFLOW_CFG_SCALE_DEFAULT,
    LINEAGEFLOW_CHANNELS,
    LINEAGEFLOW_CLAMP,
    LINEAGEFLOW_CONFIG_HASH,
    LINEAGEFLOW_FAMILY_ID_DEFAULT,
    LINEAGEFLOW_INTEGRATORS,
    LINEAGEFLOW_INTEGRATOR_EULER,
    LINEAGEFLOW_INTEGRATOR_HEUN,
    LINEAGEFLOW_MECHANISM_ID,
    LINEAGEFLOW_MAX_LENGTH,
    LINEAGEFLOW_NUM_STEPS_DEFAULT,
    LINEAGEFLOW_STATE_SHAPE,
    LINEAGEFLOW_T_END,
    LINEAGEFLOW_VOCAB_SIZE,
    LineageFlowAdapter,
    LineageFlowCapabilities,
    PER_POSITION_ENTROPY_REDUCTION,
    PFAM_FAMILY_COND,
    default_lineageflow_adapter,
    lineageflow_resolve_weights_path,
    torch_is_available,
)
from adaptive_reflow.algorithm.perturbation import (
    PaperQuantityAttractorInversion,
    UniformFreshPerturbation,
)
from adaptive_reflow.universal.adapter import CapabilityMissingError
from adaptive_reflow.universal import FlowMatchingODEAdapter
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    StateBundle,
    validate_state_bundle,
)
from adaptive_reflow.contracts import (
    ArtifactHash,
    FactorValue,
    FinalRestartPolicy,
    LedgerRowId,
    PolicyId,
    RunId,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(*, force_mode: str = "synthetic", **kwargs) -> LineageFlowAdapter:
    """Build a synthetic-mode adapter for protocol-surface tests."""
    return LineageFlowAdapter(force_mode=force_mode, **kwargs)


def _make_delta(
    *,
    source: str = "test",
    target_round: int = 1,
    calibration_artifact_hash: str = LINEAGEFLOW_CONFIG_HASH,
    **spec: object,
) -> ODEConditionDelta:
    """Build an :class:`ODEConditionDelta` with sensible defaults."""
    base: dict[str, object] = {
        "num_steps": 4,
        "sampler_id": LINEAGEFLOW_INTEGRATOR_EULER,
        "guidance_scale": LINEAGEFLOW_CFG_SCALE_DEFAULT,
        "family_id": "PF00001.21",
    }
    base.update(spec)
    return ODEConditionDelta(
        delta_spec=base,  # type: ignore[arg-type]
        source=source,
        target_round=target_round,
        calibration_artifact_hash=calibration_artifact_hash,
    )


# ---------------------------------------------------------------------------
# Capability / construction
# ---------------------------------------------------------------------------


# ---
# (Header + imports shared with test_lineageflow_smoke.py; see that file.)
# ---


# ---------------------------------------------------------------------------
# per_position_entropy_reduction (Wave 45 — P2-W33-C metric promotion)
# ---------------------------------------------------------------------------


def _solved_trace(adapter: LineageFlowAdapter, *, tag: str = "e0"):
    """Run one synthetic solve and return its trace."""
    bundle = adapter.build_initial_state(batch_id=tag, sample_id=tag)
    delta = adapter.compose_condition(bundle, _make_delta(target_round=1))
    return adapter.solve_ode(bundle, delta, seed=42)


def _overwrite_trajectory(
    adapter: LineageFlowAdapter, trace, theta0: np.ndarray, theta1: np.ndarray,
) -> None:
    """Pin the cached trajectory to a controlled ``(2, L, K)`` pair.

    Lets the entropy tests assert exact analytic values instead of
    whatever the synthetic velocity field happens to produce.
    """
    traj = np.empty((2, *LINEAGEFLOW_STATE_SHAPE), dtype=np.float64)
    traj[0] = theta0
    traj[1] = theta1
    adapter._native_states[trace.native_state_digest]["trajectory"] = traj


def _uniform_theta() -> np.ndarray:
    return np.full(LINEAGEFLOW_STATE_SHAPE, 1.0 / LINEAGEFLOW_VOCAB_SIZE)


def _spike_theta() -> np.ndarray:
    theta = np.zeros(LINEAGEFLOW_STATE_SHAPE, dtype=np.float64)
    theta[:, 0] = 1.0
    return theta


def test_entropy_reduction_uniform_to_spike_equals_log_k() -> None:
    """Uniform prior collapsing to a one-hot endpoint reduces entropy by log K.

    This is the calibration anchor for the P2-W33-C metric
    (``docs/theory/operating-regime.md`` §11): the maximum achievable
    reduction is exactly ``log K``.

    It is also the **regression test for the double-normalisation bug**.
    LineageFlow's trajectory is already row-normalised, while the shared
    helper softmaxes its inputs as logits, so the adapter must convert
    via ``_theta_to_logits`` first. Dropping that conversion feeds
    probabilities into a softmax and collapses this assertion from
    3.4965 to 0.0275 — a 127x understatement that would leave the
    metric near-degenerate.
    """
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)
    _overwrite_trajectory(adapter, trace, _uniform_theta(), _spike_theta())

    out = adapter.observe_entropy_reduction(trace, None)
    assert out[PER_POSITION_ENTROPY_REDUCTION] == pytest.approx(
        float(np.log(LINEAGEFLOW_VOCAB_SIZE)), abs=1e-6,
    )


def test_entropy_reduction_spike_to_uniform_is_negative_log_k() -> None:
    """The metric is signed: widening the posterior scores -log K."""
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)
    _overwrite_trajectory(adapter, trace, _spike_theta(), _uniform_theta())

    out = adapter.observe_entropy_reduction(trace, None)
    assert out[PER_POSITION_ENTROPY_REDUCTION] == pytest.approx(
        -float(np.log(LINEAGEFLOW_VOCAB_SIZE)), abs=1e-6,
    )


def test_entropy_reduction_identical_endpoints_is_zero() -> None:
    """No change in the categorical means no entropy reduction."""
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)
    _overwrite_trajectory(adapter, trace, _uniform_theta(), _uniform_theta())

    out = adapter.observe_entropy_reduction(trace, None)
    assert out[PER_POSITION_ENTROPY_REDUCTION] == pytest.approx(0.0, abs=1e-12)


def test_entropy_reduction_on_real_trajectory_is_bounded_and_nondegenerate() -> None:
    """The synthetic field produces a finite, in-bounds, non-saturated value."""
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)

    out = adapter.observe_entropy_reduction(trace, None)
    assert set(out) == {PER_POSITION_ENTROPY_REDUCTION}
    value = out[PER_POSITION_ENTROPY_REDUCTION]

    log_k = float(np.log(LINEAGEFLOW_VOCAB_SIZE))
    assert np.isfinite(value)
    assert -log_k - 1e-9 <= value <= log_k + 1e-9
    # P2-W33-C requires a *discriminating* metric: a value pinned at 0
    # or saturated at the log K bound carries no framework-vs-baseline
    # signal. The synthetic field must land strictly inside.
    assert abs(value) > 1e-6
    assert abs(value) < log_k - 1e-6


def test_entropy_reduction_reference_theta_mode() -> None:
    """An explicit reference replaces ``trajectory[0]`` as the baseline."""
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)
    _overwrite_trajectory(adapter, trace, _spike_theta(), _spike_theta())

    # Within-trajectory: spike -> spike is a zero reduction.
    within = adapter.observe_entropy_reduction(trace, None)
    assert within[PER_POSITION_ENTROPY_REDUCTION] == pytest.approx(0.0, abs=1e-12)

    # Against a uniform baseline the same endpoint scores the full log K.
    against = adapter.observe_entropy_reduction(
        trace, None, reference_theta=_uniform_theta(),
    )
    assert against[PER_POSITION_ENTROPY_REDUCTION] == pytest.approx(
        float(np.log(LINEAGEFLOW_VOCAB_SIZE)), abs=1e-6,
    )


def test_entropy_reduction_is_deterministic() -> None:
    """Repeated calls on one trace are byte-identical (no RNG in the path)."""
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)

    first = adapter.observe_entropy_reduction(trace, None)
    second = adapter.observe_entropy_reduction(trace, None)
    assert first == second

    # And a second adapter solving the same inputs agrees exactly.
    other = _make_adapter(num_steps=4)
    other_trace = _solved_trace(other)
    assert (
        other.observe_entropy_reduction(other_trace, None)
        == first
    )


def test_entropy_reduction_ignores_paper_quantities() -> None:
    """``paper_quantities`` is signature-parity only; it must not change the value."""
    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)

    baseline = adapter.observe_entropy_reduction(trace, None)
    assert adapter.observe_entropy_reduction(trace, object()) == baseline


def test_entropy_reduction_missing_native_state_raises() -> None:
    """A digest outside the LRU cache raises rather than returning a bogus number."""
    from adaptive_reflow.universal.state import ODEIntegratorTrace

    adapter = _make_adapter(num_steps=4)
    bogus = ODEIntegratorTrace(
        steps=1, accept_rate=1.0,
        native_state_digest="bogus", integrator_config_hash="bogus",
    )
    with pytest.raises(CapabilityMissingError):
        adapter.observe_entropy_reduction(bogus, None)


def test_entropy_reduction_matches_shared_helper() -> None:
    """The adapter re-derives nothing: it delegates to ``_adapter_common``."""
    from adaptive_reflow.adapters._adapter_common import (
        per_position_entropy_reduction,
    )
    from adaptive_reflow.adapters.lineageflow import _theta_to_logits

    adapter = _make_adapter(num_steps=4)
    trace = _solved_trace(adapter)
    traj = adapter.export_trajectory(trace)
    assert traj is not None

    expected = per_position_entropy_reduction(
        _theta_to_logits(traj[0]), _theta_to_logits(traj[-1]),
    )
    out = adapter.observe_entropy_reduction(trace, None)
    assert out[PER_POSITION_ENTROPY_REDUCTION] == expected


def test_per_position_entropy_reduction_constant_is_exported() -> None:
    """The metric key is a stable public name a duck-typed caller can import."""
    import adaptive_reflow.adapters.lineageflow as lf

    assert PER_POSITION_ENTROPY_REDUCTION == "per_position_entropy_reduction"
    assert "PER_POSITION_ENTROPY_REDUCTION" in lf.__all__
