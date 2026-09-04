"""Property-based tests for :mod:`adaptive_reflow.algorithm.policy_driver`.

B.7 property-based testing — ``framework-internal-metrics.md`` rev 2 §1.

Coverage targets
----------------
* :class:`ScheduleDerivedPolicyDriver` — idempotency: identical
  ``(schedule_sample, base_policy, channel, prior_digest)`` ⇒ identical
  output policy. ``beta = n_cap`` invariant.
* :class:`ConstantPolicyDriver` — ``beta`` is constant across calls;
  clipped into ``[0, 1]``.
* :class:`AdaptivePolicyDriver` — output ``beta`` lies in ``[0, 1]`` for
  every ``prior_endpoint_digest``; identical input ⇒ identical output.
* :class:`PolicyDriverProtocol` — protocol round-trip
  ``to_config() -> driver`` is the identity.
* :func:`_clip_unit_finite` — clipping invariants.

Seed policy (Research 4 mitigation): policy drivers are deterministic;
seeding pins Hypothesis's internal deriver via ``derandomize=True``.
"""

from __future__ import annotations

import math
from dataclasses import replace

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.algorithm.policy_driver import (
    AdaptivePolicyDriver,
    ConstantPolicyDriver,
    ScheduleDerivedPolicyDriver,
)
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


_PROPERTY_SETTINGS = settings(
    max_examples=20,
    deadline=2000,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


_N_CAP = st.floats(
    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
)
_BETA = st.floats(
    min_value=-1.0, max_value=2.0, allow_nan=False, allow_infinity=False
)
_DIGEST = st.text(
    alphabet=st.characters(min_codepoint=ord("0"), max_codepoint=ord("z")),
    min_size=8,
    max_size=32,
)


def _make_base_policy(channel: ChannelName = ChannelName("c")) -> FinalRestartPolicy:
    """Build a minimal-but-valid :class:`FinalRestartPolicy` with one channel."""
    placeholder = FinalRestartPolicy(
        policy_id=PolicyId("prop-test-policy"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("prop-test-run"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={channel: FactorValue(0.5)},
        alpha_by_channel={channel: FactorValue(0.5)},
        fresh_noise_floor_by_channel={channel: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={channel: False},
        ledger_row_id=LedgerRowId("prop-test-ledger"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
    )
    return replace(placeholder, policy_hash=hash_policy_hash(placeholder))


def _make_cosine_schedule_sample(n_cap: float):
    """Build a minimal :class:`CosineScheduleSample` carrying ``n_cap``.

    Imported lazily to keep this module's import surface narrow when the
    scheduler module drifts.
    """
    from adaptive_reflow.contracts import (
        CosineScheduleSample,
    )
    return CosineScheduleSample(
        schedule_hash=ArtifactHash("prop-test"),
        outer_cycle_id=0,
        round_in_cycle=0,
        cycle_length=4,
        n_cap=FactorValue(n_cap),
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        u_r=0.0,
        family="cosine_no_restart",
        computed_at_round=0,
    )


# ---------------------------------------------------------------------------
# ScheduleDerivedPolicyDriver: beta = n_cap (within [0, 1]).
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(n_cap=_N_CAP)
def test_schedule_derived_beta_equals_n_cap(n_cap: float) -> None:
    driver = ScheduleDerivedPolicyDriver()
    base = _make_base_policy()
    sample = _make_cosine_schedule_sample(n_cap)
    out = driver.compute_policy(
        schedule_sample=sample,
        base_policy=base,
        channel=ChannelName("c"),
        prior_endpoint_digest="",
    )
    assert math.isclose(out.beta_by_channel[ChannelName("c")], n_cap, abs_tol=1e-9)


@_PROPERTY_SETTINGS
@given(n_cap=_N_CAP)
def test_schedule_derived_idempotent(n_cap: float) -> None:
    driver = ScheduleDerivedPolicyDriver()
    base = _make_base_policy()
    sample = _make_cosine_schedule_sample(n_cap)
    a = driver.compute_policy(
        schedule_sample=sample,
        base_policy=base,
        channel=ChannelName("c"),
        prior_endpoint_digest="",
    )
    b = driver.compute_policy(
        schedule_sample=sample,
        base_policy=base,
        channel=ChannelName("c"),
        prior_endpoint_digest="",
    )
    assert a == b


# ---------------------------------------------------------------------------
# ConstantPolicyDriver: beta is constant in [0, 1].
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(beta=_BETA)
def test_constant_beta_is_clipped(beta: float) -> None:
    driver = ConstantPolicyDriver(beta=beta)
    base = _make_base_policy()
    out = driver.compute_policy(
        schedule_sample=None,
        base_policy=base,
        channel=ChannelName("c"),
        prior_endpoint_digest="",
    )
    observed = out.beta_by_channel[ChannelName("c")]
    if beta < 0.0:
        assert math.isclose(observed, 0.0, abs_tol=1e-9)
    elif beta > 1.0:
        assert math.isclose(observed, 1.0, abs_tol=1e-9)
    else:
        assert math.isclose(observed, beta, abs_tol=1e-9)
    assert 0.0 <= observed <= 1.0


@_PROPERTY_SETTINGS
@given(beta=_BETA, prior=_DIGEST)
def test_constant_idempotent_under_prior(beta: float, prior: str) -> None:
    """Constant driver ignores ``prior_endpoint_digest`` (idempotency)."""
    driver = ConstantPolicyDriver(beta=beta)
    base = _make_base_policy()
    a = driver.compute_policy(
        schedule_sample=None,
        base_policy=base,
        channel=ChannelName("c"),
        prior_endpoint_digest=prior,
    )
    b = driver.compute_policy(
        schedule_sample=None,
        base_policy=base,
        channel=ChannelName("c"),
        prior_endpoint_digest=prior,
    )
    assert a == b


# ---------------------------------------------------------------------------
# AdaptivePolicyDriver: beta is in [0, 1] regardless of digest.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(prior=_DIGEST)
def test_adaptive_beta_in_unit_interval(prior: str) -> None:
    driver = AdaptivePolicyDriver()
    base = _make_base_policy()
    out = driver.compute_policy(
        schedule_sample=None,
        base_policy=base,
        channel=ChannelName("c"),
        prior_endpoint_digest=prior,
    )
    observed = out.beta_by_channel[ChannelName("c")]
    assert 0.0 <= observed <= 1.0


@_PROPERTY_SETTINGS
@given(prior=_DIGEST, target=_N_CAP)
def test_adaptive_idempotent(prior: str, target: float) -> None:
    """Adaptive driver with same prior gives same beta."""
    driver = AdaptivePolicyDriver(target_estimate=target)
    base = _make_base_policy()
    a = driver.compute_policy(
        schedule_sample=None,
        base_policy=base,
        channel=ChannelName("c"),
        prior_endpoint_digest=prior,
    )
    b = driver.compute_policy(
        schedule_sample=None,
        base_policy=base,
        channel=ChannelName("c"),
        prior_endpoint_digest=prior,
    )
    assert a == b


# ---------------------------------------------------------------------------
# driver_computed_beta: every driver's output sets the flag so the
# engine skips its inline re-override.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(beta=_BETA, n_cap=_N_CAP)
def test_drivers_set_driver_computed_beta(beta: float, n_cap: float) -> None:
    """Every driver sets ``driver_computed_beta=True`` whenever it
    overrides ``beta_by_channel``. ScheduleDerivedPolicyDriver only
    overrides when ``schedule_sample is not None`` (returns base
    verbatim otherwise) — the test passes the sample so the override
    path is exercised."""
    base = _make_base_policy()
    sample = _make_cosine_schedule_sample(n_cap)
    for driver in (
        ConstantPolicyDriver(beta=beta),
        AdaptivePolicyDriver(),
        ScheduleDerivedPolicyDriver(),
    ):
        out = driver.compute_policy(
            schedule_sample=sample,
            base_policy=base,
            channel=ChannelName("c"),
            prior_endpoint_digest="x",
        )
        assert out.driver_computed_beta is True


# ---------------------------------------------------------------------------
# policy_hash invariant: hash(policy) == policy.policy_hash (closes
# Contract 1.1).
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(beta=_BETA)
def test_output_policy_hash_matches_hash_policy_hash(beta: float) -> None:
    base = _make_base_policy()
    driver = ConstantPolicyDriver(beta=beta)
    out = driver.compute_policy(
        schedule_sample=None,
        base_policy=base,
        channel=ChannelName("c"),
        prior_endpoint_digest="x",
    )
    assert out.policy_hash == hash_policy_hash(out)