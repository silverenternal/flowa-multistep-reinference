"""Smoke test for ``FlowMatchingODEAdapter.observe_token_indices`` (Wave 44).

Wave 44 addition: closes the Tier-3 metric-axis gap (Wave 43 finding)
by exposing the per-channel decoded token indices on the adapter
Protocol so the metric layer can consume framework-side samples
without re-running forward. The protocol method is exercised on the
two adapters that ship discrete-domain channels
(:class:`adaptive_reflow.adapters.kanzi.KanziAdapter` and
:class:`adaptive_reflow.adapters.lineageflow.LineageFlowAdapter`).

All tests are CPU-only, run against the synthetic adapter mode, and
are deterministic for fixed ``batch_id``/``sample_id``/``seed``.
"""
from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.adapters.kanzi import (
    DISCRETE_TOKEN_INDEX,
    KANZI_AR_SEQ_LENGTH,
    KANZI_INTEGRATOR_EULER,
    KANZI_VOCAB_SIZE,
    KanziAdapter,
)
from adaptive_reflow.adapters.lineageflow import (
    AMINO_ACID_CATEGORICAL,
    LINEAGEFLOW_INTEGRATOR_EULER,
    LINEAGEFLOW_MAX_LENGTH,
    LINEAGEFLOW_VOCAB_SIZE,
    LineageFlowAdapter,
)
from adaptive_reflow.universal.state import ODEConditionDelta

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kanzi_bundle(adapter: KanziAdapter) -> tuple:
    """Build a Kanzi initial state + composed condition (synthetic mode)."""
    bundle = adapter.build_initial_state(batch_id="wb1", sample_id="ws1")
    delta = ODEConditionDelta(
        delta_spec={  # type: ignore[arg-type]
            "num_steps": 4,
            "sampler_id": KANZI_INTEGRATOR_EULER,
            "guidance_scale": 1.0,
            "family_id": "PF00001.21",
        },
        source="wave44_test",
        target_round=1,
        calibration_artifact_hash=adapter.capabilities().native_config_hash,
    )
    delta = adapter.compose_condition(bundle, delta)
    return bundle, delta


def _lineageflow_bundle(adapter: LineageFlowAdapter) -> tuple:
    """Build a LineageFlow initial state + composed condition."""
    bundle = adapter.build_initial_state(batch_id="wb2", sample_id="ws2")
    delta = ODEConditionDelta(
        delta_spec={  # type: ignore[arg-type]
            "num_steps": 4,
            "sampler_id": LINEAGEFLOW_INTEGRATOR_EULER,
            "guidance_scale": 1.0,
            "family_id": "PF00001.21",
        },
        source="wave44_test",
        target_round=1,
        calibration_artifact_hash=adapter.capabilities().native_config_hash,
    )
    delta = adapter.compose_condition(bundle, delta)
    return bundle, delta


# ---------------------------------------------------------------------------
# Kanzi
# ---------------------------------------------------------------------------


def test_kanzi_observe_token_indices_returns_dict() -> None:
    """Kanzi.observe_token_indices returns a non-empty dict."""
    adapter = KanziAdapter(force_mode="synthetic")
    bundle, delta = _kanzi_bundle(adapter)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    result = adapter.observe_token_indices(trace, paper_quantities=None)

    assert isinstance(result, dict)
    assert result, "kanzi observe_token_indices must return non-empty dict"


def test_kanzi_observe_token_indices_has_correct_channel_and_shape() -> None:
    """Kanzi dict maps ``discrete_token_index`` to a ``(L_z,)`` array."""
    adapter = KanziAdapter(force_mode="synthetic")
    bundle, delta = _kanzi_bundle(adapter)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    result = adapter.observe_token_indices(trace, paper_quantities=None)

    assert str(DISCRETE_TOKEN_INDEX) in result
    arr = np.asarray(result[str(DISCRETE_TOKEN_INDEX)], dtype=np.float64)
    assert arr.shape == (int(KANZI_AR_SEQ_LENGTH),)
    # Values must lie inside the AR codebook range.
    arr_int = arr.astype(np.int64)
    assert arr_int.min() >= 0
    assert arr_int.max() < int(KANZI_VOCAB_SIZE)


def test_kanzi_observe_token_indices_deterministic_for_fixed_seed() -> None:
    """Repeated calls with identical inputs produce identical arrays."""
    adapter_a = KanziAdapter(force_mode="synthetic", seed_offset=0)
    adapter_b = KanziAdapter(force_mode="synthetic", seed_offset=0)
    bundle_a, delta_a = _kanzi_bundle(adapter_a)
    bundle_b, delta_b = _kanzi_bundle(adapter_b)
    trace_a = adapter_a.solve_ode(bundle_a, delta_a, seed=42)
    trace_b = adapter_b.solve_ode(bundle_b, delta_b, seed=42)

    result_a = adapter_a.observe_token_indices(trace_a, paper_quantities=None)
    result_b = adapter_b.observe_token_indices(trace_b, paper_quantities=None)

    np.testing.assert_array_equal(
        np.asarray(result_a[str(DISCRETE_TOKEN_INDEX)], dtype=np.float64),
        np.asarray(result_b[str(DISCRETE_TOKEN_INDEX)], dtype=np.float64),
    )


def test_kanzi_observe_token_indices_satisfies_protocol_surface() -> None:
    """The adapter satisfies the augmented ``FlowMatchingODEAdapter`` protocol."""
    from adaptive_reflow.universal import FlowMatchingODEAdapter

    adapter = KanziAdapter(force_mode="synthetic")
    assert isinstance(adapter, FlowMatchingODEAdapter)
    assert hasattr(adapter, "observe_token_indices")
    assert callable(adapter.observe_token_indices)


# ---------------------------------------------------------------------------
# LineageFlow
# ---------------------------------------------------------------------------


def test_lineageflow_observe_token_indices_returns_dict() -> None:
    """LineageFlow.observe_token_indices returns a non-empty dict."""
    adapter = LineageFlowAdapter(force_mode="synthetic")
    bundle, delta = _lineageflow_bundle(adapter)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    result = adapter.observe_token_indices(trace, paper_quantities=None)

    assert isinstance(result, dict)
    assert result, "lineageflow observe_token_indices must return non-empty dict"


def test_lineageflow_observe_token_indices_has_correct_channel_and_shape() -> None:
    """LineageFlow dict maps ``amino_acid_categorical`` to a ``(L,)`` array."""
    adapter = LineageFlowAdapter(force_mode="synthetic")
    bundle, delta = _lineageflow_bundle(adapter)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    result = adapter.observe_token_indices(trace, paper_quantities=None)

    assert str(AMINO_ACID_CATEGORICAL) in result
    arr = np.asarray(result[str(AMINO_ACID_CATEGORICAL)], dtype=np.float64)
    assert arr.shape == (int(LINEAGEFLOW_MAX_LENGTH),)
    # Values must lie inside the Pfam 33-token alphabet.
    arr_int = arr.astype(np.int64)
    assert arr_int.min() >= 0
    assert arr_int.max() < int(LINEAGEFLOW_VOCAB_SIZE)


def test_lineageflow_observe_token_indices_argmax_matches_trajectory() -> None:
    """The decoded indices equal ``argmax(theta_final, axis=-1)``."""
    adapter = LineageFlowAdapter(force_mode="synthetic")
    bundle, delta = _lineageflow_bundle(adapter)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    result = adapter.observe_token_indices(trace, paper_quantities=None)

    # Cross-check against the export_trajectory surface.
    trajectory = adapter.export_trajectory(trace)
    assert trajectory is not None
    expected = np.argmax(trajectory[-1], axis=-1).astype(np.float64)
    np.testing.assert_array_equal(
        np.asarray(result[str(AMINO_ACID_CATEGORICAL)], dtype=np.float64),
        expected,
    )


def test_lineageflow_observe_token_indices_satisfies_protocol_surface() -> None:
    """The adapter satisfies the augmented ``FlowMatchingODEAdapter`` protocol."""
    from adaptive_reflow.universal import FlowMatchingODEAdapter

    adapter = LineageFlowAdapter(force_mode="synthetic")
    assert isinstance(adapter, FlowMatchingODEAdapter)
    assert hasattr(adapter, "observe_token_indices")
    assert callable(adapter.observe_token_indices)


# ---------------------------------------------------------------------------
# Cache-miss fallback (Kanzi)
# ---------------------------------------------------------------------------


def test_kanzi_observe_token_indices_fallback_for_unknown_digest() -> None:
    """Unknown ``native_state_digest`` falls back to a uniform sample (no crash)."""
    adapter = KanziAdapter(force_mode="synthetic")
    fake_trace = _FakeTrace("does_not_exist_in_cache")

    # The Kanzi implementation walks the chain; an unknown digest
    # yields a deterministic uniform-random ``(L_z,)`` fallback.
    result = adapter.observe_token_indices(fake_trace, paper_quantities=None)

    assert str(DISCRETE_TOKEN_INDEX) in result
    arr = np.asarray(result[str(DISCRETE_TOKEN_INDEX)], dtype=np.float64)
    assert arr.shape == (int(KANZI_AR_SEQ_LENGTH),)
    arr_int = arr.astype(np.int64)
    assert arr_int.min() >= 0
    assert arr_int.max() < int(KANZI_VOCAB_SIZE)


# ---------------------------------------------------------------------------
# Helpers (test-local)
# ---------------------------------------------------------------------------


class _FakeTrace:
    """Minimal duck-typed ``ODEIntegratorTrace`` for cache-miss testing."""

    def __init__(self, native_state_digest: str) -> None:
        self.native_state_digest = str(native_state_digest)
        self.steps = 0
        self.accept_rate = 0.0
        self.integrator_config_hash = "fake"
