"""CLM-032: C4 Loop 2 closure verified — `selection_ratio` moves toward 1.

Asserted by docs/CLAIMS.md:819-907.
The C4 fix wires `ScheduleSample.eps_implicit` through the runner into
`EvidenceScaleGapMetric.oracle_at_round(eps_round=...)` so the cell-
evidence term is multiplied by `eps_round` (`c_ev *= eps_round`). When
`eps_round -> 0`, the ratio rises toward 1 — exactly paper Lemma 2 +
Lemma 3's prediction.

We pin:
    1. With `eps_round=0.0`, the oracle_at_round cell-evidence term
       collapses to 0 (cell mass vanishes in the `eps -> 0` limit).
    2. With `eps_round=0.0`, the oracle_at_round `selection_ratio`
       rises toward 1 (the sheet-dominated regime).
    3. With `eps_round=large`, the oracle_at_round `selection_ratio`
       stays low (cells still dominate).
"""
from __future__ import annotations

from adaptive_reflow.universal.state import (
    ChannelName,
    StateBundle,
    TensorRef,
)
from adaptive_reflow.universal.adapter import AdapterCapabilities


_XY = ChannelName("xy")


def _bundle(digest: str = "claim-032-c4-closure") -> StateBundle:
    return StateBundle(
        channels={_XY: TensorRef("claim-032-xy-ref")},
        masks={},
        batch_id="batch-claim-032",
        sample_id="sample-claim-032",
        reference_frame="world",
        normalization="none",
        source_round=0,
        detach_proof=True,
        native_state_digest=digest,
        provenance=("test.claim_032",),
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


def test_claim_032_eps_round_zero_collapses_cell_evidence() -> None:
    """eps_round=0 collapses c_ev to 0 (sheet-dominated regime)."""
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        EvidenceScaleGapMetric,
    )
    bundle = _bundle()
    metric = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42, eps_implicit=0.05,
    )
    out = metric.oracle_at_round(
        bundle, channel=_XY, seed=42, round_index=0, eps_round=0.0,
    )
    assert out["cell_evidence"] == 0.0, (
        f"c_ev = {out['cell_evidence']!r} did not collapse at eps_round=0"
    )


def test_claim_032_eps_round_zero_drives_ratio_toward_one() -> None:
    """eps_round=0 drives selection_ratio to 1.0 (sheet dominance)."""
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        EvidenceScaleGapMetric,
    )
    bundle = _bundle()
    metric = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42, eps_implicit=0.05,
    )
    out = metric.oracle_at_round(
        bundle, channel=_XY, seed=42, round_index=0, eps_round=0.0,
    )
    assert out["selection_ratio"] >= 0.99, (
        f"ratio at eps_round=0 = {out['selection_ratio']!r}; expected ~1.0"
    )


def test_claim_032_large_eps_round_keeps_cells_dominant() -> None:
    """eps_round=1 keeps cells dominant (ratio stays low)."""
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        EvidenceScaleGapMetric,
    )
    bundle = _bundle()
    metric = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42, eps_implicit=0.05,
    )
    out = metric.oracle_at_round(
        bundle, channel=_XY, seed=42, round_index=0, eps_round=1.0,
    )
    assert out["selection_ratio"] < 1.0, (
        f"ratio at eps_round=1 = {out['selection_ratio']!r}; "
        "should remain cell-dominated"
    )
