"""Smoke test suite for the Kanzi protein flow-autoencoder adapter (Wave 21).

Mirrors :mod:`tests.test_adapters.test_self_flow` and
:mod:`tests.test_adapters.test_lineageflow` structure for the Kanzi
protein-flow-AE adapter. Tests exercise the load-bearing
:class:`FlowMatchingODEAdapter` Protocol contract, the
``build_initial_state`` / ``solve_ode`` / ``observe_endpoint`` loop,
the Pfam-family conditioning, the latent restart blending, and the
synthetic-mode determinism invariant.

22 tests; all CPU-runnable.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from adaptive_reflow.adapters.kanzi import (
    AUDIT_FORWARD_NOISE_APPLIED,
    AUDIT_KANZI_GPT_PRIOR_RESTART,
    AUDIT_KANZI_OBSERVED,
    AUDIT_KANZI_PERTURBATION_POLICY,
    AUDIT_KANZI_RESTART_BLEND,
    DISCRETE_TOKEN_INDEX,
    ERR_KANZI_FAMILY_ID_INVALID,
    ERR_KANZI_INTEGRATOR_UNKNOWN,
    ERR_KANZI_NUM_STEPS,
    KANZI_AR_SEQ_LENGTH,
    KANZI_CHANNEL_DOMAINS,
    KANZI_CHANNELS,
    KANZI_CFG_SCALE_DEFAULT,
    KANZI_CONFIG_HASH,
    KANZI_FAMILY_ID_DEFAULT,
    KANZI_FLAT_LATENT_DIM,
    KANZI_INTEGRATORS,
    KANZI_INTEGRATOR_EULER,
    KANZI_INTEGRATOR_HEUN,
    KANZI_LATENT_CLAMP,
    KANZI_LATENT_DIM,
    KANZI_MECHANISM_ID,
    KANZI_NATIVE_STATES_MAXSIZE,
    KANZI_NUM_STEPS_DEFAULT,
    KANZI_STATE_SHAPE,
    KANZI_T_END,
    KANZI_VOCAB_SIZE,
    KanziAdapter,
    KanziCapabilities,
    KanziGPTPriorRestartPolicy,
    PFAM_FAMILY_COND,
    PROTEIN_LATENT,
    default_kanzi_adapter,
    kanzi_resolve_weights_path,
    torch_is_available,
)
from adaptive_reflow.algorithm.perturbation import (
    PaperQuantityAttractorInversion,
    UniformFreshPerturbation,
)
from adaptive_reflow.framework._compliance import implements
from adaptive_reflow.universal import FlowMatchingODEAdapter
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
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


def _make_adapter(*, force_mode: str = "synthetic", **kwargs) -> KanziAdapter:
    """Build a synthetic-mode adapter for protocol-surface tests."""
    return KanziAdapter(force_mode=force_mode, **kwargs)


def _make_delta(
    *,
    source: str = "test",
    target_round: int = 1,
    calibration_artifact_hash: str = KANZI_CONFIG_HASH,
    **spec: object,
) -> ODEConditionDelta:
    """Build an :class:`ODEConditionDelta` with sensible defaults."""
    base: dict[str, object] = {
        "num_steps": 4,
        "sampler_id": KANZI_INTEGRATOR_EULER,
        "guidance_scale": KANZI_CFG_SCALE_DEFAULT,
        "family_id": KANZI_FAMILY_ID_DEFAULT,
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
# (Header + imports shared with test_kanzi_smoke.py; see that file.)
# ---


def test_observe_entropy_reduction_via_mahalanobis() -> None:
    """Wave 95 Phase 2.C: Kanzi exposes per-position Mahalanobis reduction.

    Regression for A.3: the Kanzi adapter's continuous-latent trajectory
    surfaces a per-position restart signal via
    :meth:`KanziAdapter.observe_entropy_reduction` keyed by
    :data:`adaptive_reflow.adapters.kanzi.PER_POSITION_ENTROPY_REDUCTION`
    (the same channel name LineageFlow uses). Unlike LineageFlow's
    Shannon-entropy reduction, Kanzi computes a per-position
    Mahalanobis distance to the trajectory's empirical mean/covariance
    manifold, with a small ridge (``eps * I``) to keep the solve
    numerically stable when ``T+1 < d`` (synthetic-mode default).

    Sanity: a 4-step Euler solve on a 64-position × 64-d latent
    trajectory returns a finite, real-valued scalar under both modes
    (within-trajectory default and the ``reference_theta`` framework-
    vs-baseline override). Also verifies the ``observe()`` typed
    surface emits a POSITION_ENTROPY_REDUCTION ObservationResult with
    ``units="mahalanobis_sq_per_position"`` and the
    :data:`PER_POSITION_ENTROPY_REDUCTION` channel name.
    """
    from adaptive_reflow.adapters.kanzi import (
        PER_POSITION_ENTROPY_REDUCTION,
    )
    from adaptive_reflow.framework.interfaces import ObservationKind

    adapter = _make_adapter(num_steps=4)
    bundle = adapter.build_initial_state(
        batch_id="w95c_mahalanobis", sample_id="s"
    )
    delta = _make_delta(target_round=1)
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)

    # (1) Within-trajectory mode (default). Within-trajectory:
    # x_before = trajectory[0]; distance to self is 0; distance to
    # trajectory[-1] is finite → reduction is finite (and sign reflects
    # whether the endpoint moved closer to / farther from the
    # trajectory's empirical manifold centre than the start).
    within = adapter.observe_entropy_reduction(trace)
    assert isinstance(within, dict)
    assert PER_POSITION_ENTROPY_REDUCTION in within
    scalar_within = within[PER_POSITION_ENTROPY_REDUCTION]
    assert isinstance(scalar_within, float)
    assert np.isfinite(scalar_within), (
        f"within-trajectory Mahalanobis reduction must be finite, "
        f"got {scalar_within!r}"
    )

    # (2) Framework-vs-baseline mode: pass reference_theta. Same
    # continuity contract; result is finite; key is the same.
    traj = adapter.export_trajectory(trace)
    assert traj is not None
    reference_theta = traj[0]  # shape (L_z, d)
    baseline = adapter.observe_entropy_reduction(
        trace, reference_theta=reference_theta
    )
    assert isinstance(baseline, dict)
    assert PER_POSITION_ENTROPY_REDUCTION in baseline
    scalar_baseline = baseline[PER_POSITION_ENTROPY_REDUCTION]
    assert isinstance(scalar_baseline, float)
    assert np.isfinite(scalar_baseline)

    # (3) Typed observe() surface emits a POSITION_ENTROPY_REDUCTION
    # ObservationResult with the right channel + units.
    results = adapter.observe(
        trace,
        bundle,
        paper_quantities=None,
        strategies=(ObservationKind.POSITION_ENTROPY_REDUCTION,),
    )
    assert len(results) == 1
    obs = results[0]
    assert obs.kind == ObservationKind.POSITION_ENTROPY_REDUCTION
    assert obs.channel == PER_POSITION_ENTROPY_REDUCTION
    assert obs.units == "mahalanobis_sq_per_position"
    assert np.isfinite(float(obs.payload))

    # (4) Reference override via the typed observe(theta_before=...) is
    # plumbed through to observe_entropy_reduction(reference_theta=...).
    theta_before_value = traj[0]  # any (L_z, d) reference works
    results_with_ref = adapter.observe(
        trace,
        bundle,
        strategies=(ObservationKind.POSITION_ENTROPY_REDUCTION,),
        theta_before=theta_before_value,
    )
    assert len(results_with_ref) == 1
    assert np.isfinite(float(results_with_ref[0].payload))
