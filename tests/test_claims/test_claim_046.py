"""CLM-046: EvidenceScaleGapMetric honours paper-math `eps` scaling flags.

Asserted by docs/CLAIMS.md:1657-1703.
The evaluator exposes two opt-in flags:
    - `use_quadratic_eps_scaling` (A-02.M2) — scales cell-evidence by
      `eps ** 2` instead of the legacy `eps`.
    - `apply_lemma4_exponential_suppression` (A-02.G1) — multiplies the
      cell-evidence term by `exp(-e_rho / (2 * eps ** 2))`.
Additionally, NaN/inf `eps_round` is rejected with a ValueError.

We pin:
    1. Both opt-in flags are constructor parameters.
    2. The default is `False` for both (backward compatibility).
    3. NaN/inf `eps_schedule` raises ValueError on the first call.
"""
from __future__ import annotations

import inspect
import math

import pytest

from adaptive_reflow.eval.posterior_selection_evaluator import (
    EvidenceScaleGapMetric,
)
from tests.test_claims._claim_template import (
    AdapterCapabilities,
    ChannelName,
    StateBundle,
    TensorRef,
)


def test_claim_046_constructor_accepts_paper_math_flags() -> None:
    sig = inspect.signature(EvidenceScaleGapMetric.__init__)
    assert "use_quadratic_eps_scaling" in sig.parameters
    assert "apply_lemma4_exponential_suppression" in sig.parameters

def test_claim_046_paper_math_flags_default_false() -> None:
    """Both flags default to False (backward-compatible)."""
    sig = inspect.signature(EvidenceScaleGapMetric.__init__)
    assert sig.parameters["use_quadratic_eps_scaling"].default is False
    assert sig.parameters["apply_lemma4_exponential_suppression"].default is False

def test_claim_046_nan_eps_round_raises_value_error() -> None:
    """A NaN `eps_round` to oracle_at_round raises ValueError (A-02.M3)."""
    from adaptive_reflow.universal.adapter import AdapterCapabilities  # noqa: F401
    xy = ChannelName("xy")
    bundle = StateBundle(
        channels={xy: TensorRef("claim-046-xy")},
        masks={},
        batch_id="batch-claim-046",
        sample_id="sample-claim-046",
        reference_frame="world",
        normalization="none",
        source_round=0,
        detach_proof=True,
        native_state_digest="claim-046-nan",
        provenance=("test.claim_046",),
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
            supported_channels=(xy,),
            channel_domains={xy: "continuous"},
        ),
    )
    metric = EvidenceScaleGapMetric(
        target="two_moons", n_gen=20, n_ref=20, seed=42, eps_implicit=0.05,
    )
    with pytest.raises(ValueError, match="finite"):
        metric.oracle_at_round(
            bundle, channel=xy, seed=42, round_index=0,
            eps_round=float("nan"),
        )

def test_claim_046_inf_eps_round_raises_value_error() -> None:
    """An inf `eps_round` to oracle_at_round raises ValueError (A-02.M3)."""
    from adaptive_reflow.universal.adapter import AdapterCapabilities  # noqa: F401
    xy = ChannelName("xy")
    bundle = StateBundle(
        channels={xy: TensorRef("claim-046-xy")},
        masks={},
        batch_id="batch-claim-046",
        sample_id="sample-claim-046",
        reference_frame="world",
        normalization="none",
        source_round=0,
        detach_proof=True,
        native_state_digest="claim-046-inf",
        provenance=("test.claim_046",),
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
            supported_channels=(xy,),
            channel_domains={xy: "continuous"},
        ),
    )
    metric = EvidenceScaleGapMetric(
        target="two_moons", n_gen=20, n_ref=20, seed=42, eps_implicit=0.05,
    )
    with pytest.raises(ValueError, match="finite"):
        metric.oracle_at_round(
            bundle, channel=xy, seed=42, round_index=0,
            eps_round=math.inf,
        )
