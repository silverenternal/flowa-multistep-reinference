"""CLM-003: Framework `selection_ratio` metric is invariant to scheduler.

Asserted by docs/CLAIMS.md:55-72.
The shipped `selection_ratio = sheet_evidence / (sheet_evidence + cell_evidence)`
emitted by EvidenceScaleGapMetric is schedule-independent by construction
on the legacy replay path; both schedulers report bit-identical per-round
values on each target because the evaluator scores the adapter's own
posterior geometry at a fixed noise scale.

We pin: two metric instances configured with DIFFERENT `eps_schedule`s
but the same `(target, seed)` produce identical `selection_ratio` via
the legacy `oracle` path (the replay-based metric that ignores
`eps_round` and `eps_schedule`).
"""
from __future__ import annotations

from tests.test_claims._claim_template import (
    AdapterCapabilities,
    ChannelName,
    StateBundle,
    TensorRef,
)

_XY = ChannelName("xy")

def _bundle(digest: str = "claim-003-schedule-invariant") -> StateBundle:
    return StateBundle(
        channels={_XY: TensorRef("claim-003-xy-ref")},
        masks={},
        batch_id="batch-claim-003",
        sample_id="sample-claim-003",
        reference_frame="world",
        normalization="none",
        source_round=0,
        detach_proof=True,
        native_state_digest=digest,
        provenance=("test.claim_003",),
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
            supported_channels=(_XY,),
            channel_domains={_XY: "continuous"},
        ),
    )

def _metric(target: str, *, eps_schedule):
    """Construct an EvidenceScaleGapMetric at fixed noise replay."""
    # Lazy import keeps the module-level import graph stable across
    # test ordering (EvidenceScaleGapMetric builds an internal TwoDimFMAdapter).
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        EvidenceScaleGapMetric,
    )
    return EvidenceScaleGapMetric(
        target=target,  # type: ignore[arg-type]
        n_gen=200, n_ref=200, seed=42,
        eps_implicit=0.05,
        eps_schedule=eps_schedule,
    )

def test_claim_003_selection_ratio_invariant_under_schedule_swap() -> None:
    """Two metrics with different schedules -> identical oracle ratio."""
    bundle = _bundle()
    m_a = _metric("two_moons", eps_schedule=lambda r: 0.05 * (1.0 - r / 20.0))
    m_b = _metric("two_moons", eps_schedule=lambda r: 0.05 * (1.0 + r / 20.0))
    ratio_a = m_a.oracle(bundle, channel=_XY, seed=42)["selection_ratio"]
    ratio_b = m_b.oracle(bundle, channel=_XY, seed=42)["selection_ratio"]
    assert ratio_a == ratio_b, (
        f"schedule changed oracle ratio: {ratio_a!r} vs {ratio_b!r}"
    )
