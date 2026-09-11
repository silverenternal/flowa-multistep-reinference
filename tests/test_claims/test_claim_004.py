"""CLM-004: Framework `selection_ratio` plateaus, does NOT converge to 1.

Asserted by docs/CLAIMS.md:74-90.
The shipped `selection_ratio` is a fixed-noise replay estimator; it
plateaus at the value dictated by the adapter's training noise rather
than converging to 1 as rounds progress. Convergence to 1 would require
an endpoint-conditioned metric operating in the `eps -> 0` limit, which
is the open follow-up.

We pin: across `round_index` values, the legacy `oracle` replay returns
the SAME selection_ratio (no progression toward 1). The plateau is
strictly below 1 on canonical 2D targets (paper predicts 1 in the
asymptotic limit; framework's fixed-noise replay never reaches it).
"""
from __future__ import annotations
from tests.test_claims._claim_template import (AdapterCapabilities, ChannelName, StateBundle, TensorRef)

_XY = ChannelName("xy")

def _bundle(digest: str = "claim-004-plateau") -> StateBundle:
    return StateBundle(
        channels={_XY: TensorRef("claim-004-xy-ref")},
        masks={},
        batch_id="batch-claim-004",
        sample_id="sample-claim-004",
        reference_frame="world",
        normalization="none",
        source_round=0,
        detach_proof=True,
        native_state_digest=digest,
        provenance=("test.claim_004",),
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

def test_claim_004_selection_ratio_plateau_below_one_on_two_moons() -> None:
    """On two_moons, the oracle replay ratio is strictly below 1.0."""
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        EvidenceScaleGapMetric,
    )
    bundle = _bundle()
    metric = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42, eps_implicit=0.05,
    )
    ratio = metric.oracle(bundle, channel=_XY, seed=42)["selection_ratio"]
    assert ratio < 1.0, f"oracle ratio = {ratio!r} reached 1 (no plateau)"
    assert ratio > 0.0, f"oracle ratio = {ratio!r} non-positive"

def test_claim_004_selection_ratio_independent_of_round_index() -> None:
    """Without eps_round, oracle_at_round returns the plateau ratio."""
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        EvidenceScaleGapMetric,
    )
    bundle = _bundle()
    metric = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42, eps_implicit=0.05,
    )
    r0 = metric.oracle_at_round(bundle, channel=_XY, seed=42, round_index=0)
    r5 = metric.oracle_at_round(bundle, channel=_XY, seed=42, round_index=5)
    assert r0["selection_ratio"] == r5["selection_ratio"], (
        f"oracle_at_round ratio moved: {r0['selection_ratio']!r} vs "
        f"{r5['selection_ratio']!r}"
    )
