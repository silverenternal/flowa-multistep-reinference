"""CLM-009: `eight_gaussians` plateau is lower than `two_moons`.

Asserted by docs/CLAIMS.md:160-175.
The framework's heuristic `selection_ratio` is target-sensitive in the
direction paper Lemma 3 predicts: more competing cell roots means a
lower plateau value. Empirically `eight_gaussians` (7 cells) plateaus
materially below `two_moons` (1 cell).

We pin: with the canonical fixture (n_gen=200, n_ref=200, seed=42,
eps_implicit=0.05), the two_moons replay ratio strictly exceeds the
eight_gaussians replay ratio.
"""
from __future__ import annotations

from adaptive_reflow.universal.state import (
    ChannelName,
    StateBundle,
    TensorRef,
)
from adaptive_reflow.universal.adapter import AdapterCapabilities


_XY = ChannelName("xy")


def _bundle(digest: str) -> StateBundle:
    return StateBundle(
        channels={_XY: TensorRef("claim-009-xy-ref")},
        masks={},
        batch_id="batch-claim-009",
        sample_id="sample-claim-009",
        reference_frame="world",
        normalization="none",
        source_round=0,
        detach_proof=True,
        native_state_digest=digest,
        provenance=("test.claim_009",),
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


def test_claim_009_two_moons_ratio_strictly_exceeds_eight_gaussians() -> None:
    """two_moons > eight_gaussians plateau, paper Lemma 3 direction."""
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        EvidenceScaleGapMetric,
    )
    b_2m = _bundle("claim-009-two-moons")
    b_8g = _bundle("claim-009-eight-gaussians")
    m_2m = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42, eps_implicit=0.05,
    )
    m_8g = EvidenceScaleGapMetric(
        target="eight_gaussians", n_gen=200, n_ref=200, seed=42, eps_implicit=0.05,
    )
    r_2m = m_2m.oracle(b_2m, channel=_XY, seed=42)["selection_ratio"]
    r_8g = m_8g.oracle(b_8g, channel=_XY, seed=42)["selection_ratio"]
    assert r_2m > r_8g, (
        f"two_moons ratio {r_2m!r} not strictly greater than "
        f"eight_gaussians {r_8g!r}"
    )
