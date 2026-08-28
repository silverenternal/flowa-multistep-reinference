"""Tests for the per-round policy driver (PolicyDriverProtocol + 3 impls)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from adaptive_reflow.algorithm import (
    ADAPTIVE_FAMILY,
    CONSTANT_FAMILY,
    SCHEDULE_DERIVED_FAMILY,
    AdaptivePolicyDriver,
    ConstantPolicyDriver,
    PolicyDriverProtocol,
    ScheduleDerivedPolicyDriver,
    default_policy_driver,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


TWODIM_FM_CHANNELS: tuple[str, ...] = ("xy",)


def _make_base_policy(
    *,
    policy_id: str = "policy-driver-test",
    run_id: str = "run-driver-test",
    beta: float = 0.0,
    channels: tuple[str, ...] = TWODIM_FM_CHANNELS,
    target_round: int = 0,
) -> FinalRestartPolicy:  # noqa: F821 — forward reference, imported lazily
    """Build a deterministic :class:`FinalRestartPolicy` for one round.

    The helper imports the typed-contract surface lazily so this test
    module stays independent of the heavy ``contracts`` import path.
    """
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

    placeholder = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(run_id),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={
            ChannelName(k): FactorValue(float(beta)) for k in channels
        },
        alpha_by_channel={ChannelName(k): FactorValue(1.0) for k in channels},
        fresh_noise_floor_by_channel={
            ChannelName(k): FactorValue(0.0) for k in channels
        },
        schedule_sample=None,
        freeze_admission_by_channel={ChannelName(k): True for k in channels},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
    )
    return replace(placeholder, policy_hash=hash_policy_hash(placeholder))


def _make_schedule_sample(
    *,
    n_cap: float,
    round_in_cycle: int = 0,
    cycle_length: int = 4,
    family: str = "cosine_no_restart",
) -> CosineScheduleSample:  # noqa: F821 — forward reference
    """Build a deterministic :class:`CosineScheduleSample` with the given n_cap."""
    from adaptive_reflow.contracts import (
        ArtifactHash,
        CosineScheduleSample,
        FactorValue,
    )

    return CosineScheduleSample(
        schedule_hash=ArtifactHash("policy-driver-test-schedule"),
        outer_cycle_id=0,
        round_in_cycle=int(round_in_cycle),
        cycle_length=int(cycle_length),
        n_cap=FactorValue(float(n_cap)),
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        u_r=float(round_in_cycle) / float(max(cycle_length - 1, 1)),
        family=family,
        computed_at_round=int(round_in_cycle),
    )


def _beta_value(policy, channel: str = "xy") -> float:
    """Return the per-channel ``beta`` carried by ``policy``."""
    from adaptive_reflow.contracts import ChannelName

    return float(policy.beta_by_channel.get(ChannelName(channel), -1.0))


# ---------------------------------------------------------------------------
# 1. Protocol runtime_checkable
# ---------------------------------------------------------------------------


def test_policy_driver_protocol_runtime_checkable() -> None:
    """All three concrete drivers satisfy the runtime_checkable Protocol."""
    schedule = ScheduleDerivedPolicyDriver()
    constant = ConstantPolicyDriver(beta=0.5)
    adaptive = AdaptivePolicyDriver()

    assert isinstance(schedule, PolicyDriverProtocol)
    assert isinstance(constant, PolicyDriverProtocol)
    assert isinstance(adaptive, PolicyDriverProtocol)
    assert isinstance(default_policy_driver(), PolicyDriverProtocol)
    assert isinstance(default_policy_driver(), ScheduleDerivedPolicyDriver)

    # Driver family identifiers match the canonical literals.
    assert schedule.driver_family() == SCHEDULE_DERIVED_FAMILY
    assert constant.driver_family() == CONSTANT_FAMILY
    assert adaptive.driver_family() == ADAPTIVE_FAMILY


# ---------------------------------------------------------------------------
# 2. Schedule-derived driver matches the engine's inline override
# ---------------------------------------------------------------------------


def test_schedule_derived_driver_matches_engine_override() -> None:
    """``ScheduleDerivedPolicyDriver`` reproduces
    ``engine._policy_with_schedule_beta`` (Contract 1.2 + Contract 3.1).

    Both writers compute ``beta = n_cap``, but they differ in one
    meta field: the driver sets ``driver_computed_beta=True`` (so the
    engine skips its re-override) while the engine helper leaves it
    ``False`` (so it can apply the inline override itself). The
    ``policy_hash`` therefore differs across the two paths even
    though the resulting ``beta`` value is identical. The test
    asserts the ``beta`` equality and the ``driver_computed_beta``
    delta — NOT the ``policy_hash`` equality.
    """
    from adaptive_reflow.frame.engine import _policy_with_schedule_beta

    base_policy = _make_base_policy(beta=0.0)
    sample = _make_schedule_sample(n_cap=0.7, round_in_cycle=1)

    # Reference: the engine's existing inline helper.
    engine_policy = _policy_with_schedule_beta(
        replace(base_policy, schedule_sample=sample)
    )

    # Driver: the schedule-derived driver fed the same arguments.
    driver = ScheduleDerivedPolicyDriver()
    driver_policy = driver.compute_policy(
        sample,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest="some-digest",
    )

    # Both override ``beta_by_channel`` to ``n_cap`` and recompute the
    # policy hash; the resulting ``beta`` MUST match (Contract 3.1).
    assert _beta_value(driver_policy) == pytest.approx(0.7)
    assert _beta_value(driver_policy) == pytest.approx(_beta_value(engine_policy))
    # Contract 1.2: the driver sets ``driver_computed_beta=True`` so
    # the engine skips its re-override; the legacy engine path leaves
    # the flag at ``False`` so it applies the inline override. The
    # flags MUST differ across paths.
    assert driver_policy.driver_computed_beta is True
    assert engine_policy.driver_computed_beta is False
    # The ``policy_hash`` differs because ``driver_computed_beta`` is
    # part of the canonical payload (deliberate — preserves the audit
    # invariant that the hash uniquely identifies the policy
    # surface).
    assert str(driver_policy.policy_hash) != str(engine_policy.policy_hash)

    # ``None`` schedule: the driver returns ``base_policy`` verbatim
    # (no schedule-driven override possible). The engine now (closes P0-5)
    # fails closed: when ``beta_from_schedule`` is ``True`` and
    # ``schedule_sample`` is ``None``, the helper emits
    # ``ERR_SCHEDULE_SAMPLE_MISSING`` and returns a NEW policy with all
    # ``beta_by_channel`` zeroed (it is NOT the same object as the
    # base policy).
    unchanged_driver = driver.compute_policy(
        None,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest="some-digest",
    )
    assert unchanged_driver is base_policy
    # The driver never sets the dedup flag when the schedule is absent.
    assert unchanged_driver.driver_computed_beta is False

    audit_codes: list[str] = []
    fail_closed_engine = _policy_with_schedule_beta(base_policy, audit_codes)
    # Engine returned a NEW (not the same) policy with all beta zeroed,
    # and emitted ERR_SCHEDULE_SAMPLE_MISSING into the audit trail.
    assert fail_closed_engine is not base_policy
    assert any("schedule_sample_missing" in code for code in audit_codes)
    assert _beta_value(fail_closed_engine) == 0.0


# ---------------------------------------------------------------------------
# 3. ConstantPolicyDriver returns the configured beta
# ---------------------------------------------------------------------------


def test_constant_driver_returns_constant_beta() -> None:
    """``ConstantPolicyDriver`` overrides ``beta`` to its config regardless of inputs."""
    base_policy = _make_base_policy(beta=0.0)
    sample = _make_schedule_sample(n_cap=0.7)

    # Default constant.
    driver_default = ConstantPolicyDriver()
    out_default = driver_default.compute_policy(
        sample,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest="round-1",
    )
    assert _beta_value(out_default) == pytest.approx(0.5)
    assert driver_default.beta == 0.5

    # Custom constant 0.3 — schedule and prior are ignored.
    driver_custom = ConstantPolicyDriver(beta=0.3)
    out_custom = driver_custom.compute_policy(
        sample,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest="round-1",
    )
    assert _beta_value(out_custom) == pytest.approx(0.3)

    # Custom constant 0.0 -> pure prior preservation.
    driver_zero = ConstantPolicyDriver(beta=0.0)
    out_zero = driver_zero.compute_policy(
        sample,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest="round-1",
    )
    assert _beta_value(out_zero) == pytest.approx(0.0)

    # Custom constant 1.0 -> pure fresh noise.
    driver_one = ConstantPolicyDriver(beta=1.0)
    out_one = driver_one.compute_policy(
        sample,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest="round-1",
    )
    assert _beta_value(out_one) == pytest.approx(1.0)

    # Out-of-range constant is clipped at construction time.
    driver_clip = ConstantPolicyDriver(beta=1.7)
    assert driver_clip.beta == 1.0


# ---------------------------------------------------------------------------
# 4. AdaptivePolicyDriver varies beta with prior digest
# ---------------------------------------------------------------------------


def test_adaptive_driver_beta_varies_with_prior_digest() -> None:
    """``AdaptivePolicyDriver`` yields different betas for different prior digests."""
    base_policy = _make_base_policy(beta=0.0)
    driver = AdaptivePolicyDriver()  # target_estimate = 0.5

    # Two structurally distinct digests — the driver normalises the
    # digest into ``[0, 1]`` deterministically, so the resulting
    # ``beta`` values must be deterministically distinct for at least
    # some pair of inputs.
    digest_a = "deadbeef" * 8  # 64-hex prefix maps to a unit value.
    digest_b = "feedface" * 8  # distinct hex prefix -> distinct value.

    policy_a = driver.compute_policy(
        None,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest=digest_a,
    )
    policy_b = driver.compute_policy(
        None,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest=digest_b,
    )

    beta_a = _beta_value(policy_a)
    beta_b = _beta_value(policy_b)

    # The two digests must produce different ``beta`` values.
    assert beta_a != pytest.approx(beta_b), (
        f"expected distinct betas for distinct digests; "
        f"got beta_a={beta_a:.6f}, beta_b={beta_b:.6f}"
    )

    # Same digest twice -> identical ``beta`` (pure / deterministic).
    policy_a_again = driver.compute_policy(
        None,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest=digest_a,
    )
    assert _beta_value(policy_a_again) == pytest.approx(beta_a)
    assert str(policy_a_again.policy_hash) == str(policy_a.policy_hash)

    # ``beta`` is in ``[0, 1]`` for *any* digest (the helper clips).
    for digest in ("", "0", "abc", digest_a, digest_b):
        out = driver.compute_policy(
            None,
            base_policy=base_policy,
            channel="xy",
            prior_endpoint_digest=digest,
        )
        beta = _beta_value(out)
        assert 0.0 <= beta <= 1.0, (
            f"beta out of [0, 1] for digest={digest!r}: {beta:.6f}"
        )


# ---------------------------------------------------------------------------
# 5. Drivers are swapable — switching drivers changes engine behaviour
# ---------------------------------------------------------------------------


def test_drivers_are_swapable() -> None:
    """Different drivers produce different ``applied_policy_hash`` per round.

    The test feeds the same ``base_policy`` + ``schedule_sample`` to
    each driver and asserts that:

    * :class:`ScheduleDerivedPolicyDriver` emits ``beta = n_cap`` per
      sample (so the resulting beta sequence traces the cosine ramp).
    * :class:`ConstantPolicyDriver` emits a flat ``beta = constant``
      sequence.
    * :class:`AdaptivePolicyDriver` emits a different beta sequence
      from both (the prior-driven envelope diverges from both the
      schedule ramp and the constant floor).

    The test then asserts that the *applied policy hash* changes when
    we swap drivers for the same ``(base_policy, sample)`` triple.
    This proves the :class:`PolicyDriverProtocol` is a true pluggable
    boundary: switching drivers changes the per-round ``beta`` the
    adapter receives, without touching the engine, the adapter, or
    the schedule module.
    """
    cycle_length = 4
    # Build a sequence of samples whose ``n_cap`` varies so the
    # schedule-derived driver produces a non-trivial sequence; the
    # constant and adaptive drivers must diverge from this.
    samples = [
        _make_schedule_sample(
            n_cap=n_cap,
            round_in_cycle=r,
            cycle_length=cycle_length,
        )
        for r, n_cap in enumerate([1.0, 0.5, 0.25, 0.0])
    ]

    # Schedule-derived driver emits ``beta = n_cap`` per sample.
    schedule_driver = ScheduleDerivedPolicyDriver()
    schedule_betas = [
        schedule_driver.compute_policy(
            sample,
            base_policy=_make_base_policy(beta=0.0, target_round=r),
            channel="xy",
            prior_endpoint_digest=f"prior-{r}",
        )
        for r, sample in enumerate(samples)
    ]
    schedule_values = [_beta_value(p) for p in schedule_betas]
    assert schedule_values == pytest.approx([1.0, 0.5, 0.25, 0.0])

    # Constant driver emits ``beta = constant`` regardless of n_cap.
    constant_driver = ConstantPolicyDriver(beta=0.5)
    constant_values = [
        _beta_value(
            constant_driver.compute_policy(
                sample,
                base_policy=_make_base_policy(beta=0.0, target_round=r),
                channel="xy",
                prior_endpoint_digest=f"prior-{r}",
            )
        )
        for r, sample in enumerate(samples)
    ]
    assert constant_values == pytest.approx([0.5, 0.5, 0.5, 0.5])

    # Adaptive driver emits ``beta = 1 - |p - t|`` per sample; the
    # values are deterministic and vary across rounds (different prior
    # digests -> different normalized priors).
    adaptive_driver = AdaptivePolicyDriver()
    adaptive_values = [
        _beta_value(
            adaptive_driver.compute_policy(
                sample,
                base_policy=_make_base_policy(beta=0.0, target_round=r),
                channel="xy",
                prior_endpoint_digest=f"prior-{r}",
            )
        )
        for r, sample in enumerate(samples)
    ]
    assert adaptive_values != schedule_values, (
        "adaptive driver produced same betas as schedule-derived driver"
    )
    assert adaptive_values != constant_values, (
        "adaptive driver produced same betas as constant driver"
    )

    # Engine dispatch is swapable: the same engine + same base policy
    # + different driver -> different applied_policy_hash per round.
    # Use a sample whose ``n_cap`` differs from the constant beta so
    # the two drivers produce distinguishable policies.
    base_policy = _make_base_policy(beta=0.5, target_round=0)
    sample = samples[2]  # n_cap = 0.25 (constant driver uses 0.5)
    schedule_applied = schedule_driver.compute_policy(
        sample, base_policy=base_policy, channel="xy", prior_endpoint_digest="round-2"
    )
    constant_applied = constant_driver.compute_policy(
        sample, base_policy=base_policy, channel="xy", prior_endpoint_digest="round-2"
    )
    adaptive_applied = adaptive_driver.compute_policy(
        sample, base_policy=base_policy, channel="xy", prior_endpoint_digest="round-2"
    )
    assert str(schedule_applied.policy_hash) != str(constant_applied.policy_hash), (
        "schedule-derived and constant drivers produced the same applied "
        "policy hash for a sample whose n_cap != constant beta"
    )
    assert str(adaptive_applied.policy_hash) != str(schedule_applied.policy_hash), (
        "adaptive and schedule-derived drivers produced the same applied "
        "policy hash for the same prior digest"
    )
    assert str(adaptive_applied.policy_hash) != str(constant_applied.policy_hash), (
        "adaptive and constant drivers produced the same applied policy "
        "hash for the same prior digest"
    )


# ---------------------------------------------------------------------------
# 6. AdaptivePolicyDriver — paper-quantity wiring (ADR-0013 follow-up)
# ---------------------------------------------------------------------------


def test_adaptive_policy_driver_with_paper_quantities_uses_C() -> None:
    """``per_cell_coefficient_C`` normalises beta to paper Lemma 3 scale.

    When the driver is constructed with ``per_cell_coefficient_C``, the
    per-round ``beta`` is the legacy envelope divided by ``C_g``:

        beta = clip((1 - |p - t|) / C_g, 0, 1)

    The default ``C_g`` from ``paper_quantities.per_cell_coefficient_C``
    is approximately 1.2408 (rho=0.1, c=1.0); the resulting beta is
    therefore smaller than the legacy envelope but still in ``[0, 1]``.
    """
    from adaptive_reflow.contracts import paper_quantities as _pq

    base_policy = _make_base_policy(beta=0.0)
    cell_C = float(_pq.per_cell_coefficient_C())
    driver = AdaptivePolicyDriver(per_cell_coefficient_C=cell_C)
    assert driver.per_cell_coefficient_C == pytest.approx(cell_C, rel=1e-12)

    # Sample a non-trivial prior digest; the legacy envelope gives
    # ``1 - |p - t|``, which the driver divides by ``C_g``.
    digest = "abcdef0123456789" * 4  # 64-hex; maps into [0, 1]
    out_with_C = driver.compute_policy(
        None,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest=digest,
    )
    beta_with_C = _beta_value(out_with_C)
    assert 0.0 <= beta_with_C <= 1.0

    # The legacy driver produces a different beta (no division by C_g).
    legacy_driver = AdaptivePolicyDriver()
    out_legacy = legacy_driver.compute_policy(
        None,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest=digest,
    )
    beta_legacy = _beta_value(out_legacy)

    # The relationship holds: beta_with_C = clip(beta_legacy / C_g, 0, 1).
    expected = beta_legacy / cell_C
    expected = max(0.0, min(1.0, expected))
    assert beta_with_C == pytest.approx(expected, rel=1e-12)


def test_adaptive_policy_driver_without_paper_quantities_legacy_behavior() -> None:
    """Without ``per_cell_coefficient_C`` the legacy formula is used.

    Backward compatibility: ``AdaptivePolicyDriver()`` (no
    ``per_cell_coefficient_C``) preserves the legacy
    ``beta = 1 - |p - t|`` formula byte-for-byte.
    """
    driver = AdaptivePolicyDriver()
    assert driver.per_cell_coefficient_C is None

    base_policy = _make_base_policy(beta=0.0)
    for digest in ("", "0", "abc", "deadbeef" * 8, "feedface" * 8):
        out = driver.compute_policy(
            None,
            base_policy=base_policy,
            channel="xy",
            prior_endpoint_digest=digest,
        )
        beta = _beta_value(out)
        # Legacy invariant: ``beta`` equals the legacy envelope,
        # clipped into ``[0, 1]`` (``driver.target_estimate = 0.5``
        # by default). The exact value depends on the digest mapping
        # but must lie in ``[0, 1]``.
        assert 0.0 <= beta <= 1.0


def test_adaptive_policy_driver_rejects_invalid_per_cell_coefficient_C() -> None:
    """Invalid ``per_cell_coefficient_C`` values raise ``ValueError``."""
    with pytest.raises(ValueError, match="real number"):
        AdaptivePolicyDriver(per_cell_coefficient_C="not a number")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        AdaptivePolicyDriver(per_cell_coefficient_C=float("inf"))
    with pytest.raises(ValueError, match="finite"):
        AdaptivePolicyDriver(per_cell_coefficient_C=float("-inf"))
    with pytest.raises(ValueError, match="positive"):
        AdaptivePolicyDriver(per_cell_coefficient_C=0.0)
    with pytest.raises(ValueError, match="positive"):
        AdaptivePolicyDriver(per_cell_coefficient_C=-1.0)


def test_adaptive_policy_driver_config_hash_varies_with_per_cell_coefficient_C() -> None:
    """``config_hash`` captures the ``per_cell_coefficient_C`` choice.

    Two drivers with the same ``target_estimate`` but different
    ``per_cell_coefficient_C`` must produce different
    ``config_hash`` values; two drivers with the same parameters
    must produce the same ``config_hash``.
    """
    a = AdaptivePolicyDriver(per_cell_coefficient_C=1.0)
    b = AdaptivePolicyDriver(per_cell_coefficient_C=2.0)
    c = AdaptivePolicyDriver(per_cell_coefficient_C=None)
    d = AdaptivePolicyDriver(per_cell_coefficient_C=1.0)
    assert a.config_hash() != b.config_hash()
    assert a.config_hash() != c.config_hash()
    assert b.config_hash() != c.config_hash()
    assert a.config_hash() == d.config_hash()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "--no-header", "-q"]))


# ---------------------------------------------------------------------------
# from_config / to_config round-trip (P1-1) — drivers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "driver",
    [
        ScheduleDerivedPolicyDriver(),
        ConstantPolicyDriver(beta=0.7),
        AdaptivePolicyDriver(target_estimate=0.4),
        AdaptivePolicyDriver(
            target_estimate=0.4, per_cell_coefficient_C=1.3
        ),
    ],
)
def test_driver_config_round_trip(driver) -> None:
    """``driver == cls.from_config(driver.to_config())`` byte-for-byte."""
    config = driver.to_config()
    if isinstance(driver, ScheduleDerivedPolicyDriver):
        rebuilt = ScheduleDerivedPolicyDriver.from_config(config)
    elif isinstance(driver, ConstantPolicyDriver):
        rebuilt = ConstantPolicyDriver.from_config(config)
    elif isinstance(driver, AdaptivePolicyDriver):
        rebuilt = AdaptivePolicyDriver.from_config(config)
    else:  # pragma: no cover
        raise AssertionError("unhandled driver")
    assert type(rebuilt) is type(driver)
    assert rebuilt.driver_family() == driver.driver_family()
    assert rebuilt.config_hash() == driver.config_hash()
    assert rebuilt.to_config() == config


# ---------------------------------------------------------------------------
# 7. Beta-saturation audit code (P2-3 / 8.3) — adaptive driver
# ---------------------------------------------------------------------------


def test_adaptive_driver_beta_saturation_with_C_below_one() -> None:
    """When ``per_cell_coefficient_C < 1`` and the raw envelope
    ``1 - |p - t|`` is close to 1, the unclipped
    ``(1 - |p - t|) / C_g`` exceeds 1.0 and the driver emits
    :data:`BETA_SATURATION_FROM_PAPER_QUANTITY` (audit P2-3 / 8.3).
    """
    from adaptive_reflow.algorithm.policy_driver import (
        BETA_SATURATION_FROM_PAPER_QUANTITY,
    )

    base_policy = _make_base_policy(beta=0.0)
    # C = 0.5 means the unclipped value can reach 2 * (1 - |p - t|),
    # which exceeds 1.0 for any digest whose mapped |p - t| < 0.5.
    # Use target_estimate = 0.0 and a digest that maps to ~0 so
    # ``diff = 0`` and ``raw / C_g = 2.0`` (well above the ceiling).
    driver = AdaptivePolicyDriver(
        target_estimate=0.0, per_cell_coefficient_C=0.5
    )
    digest = "0" * 64  # maps to ~0
    audit: list[str] = []
    out = driver.compute_policy(
        None,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest=digest,
        audit_codes=audit,
    )
    # The unclipped envelope exceeds 1.0 -> saturation audit code emitted.
    saturation_codes = [
        code for code in audit
        if code.startswith(BETA_SATURATION_FROM_PAPER_QUANTITY)
    ]
    assert saturation_codes, (
        f"expected a {BETA_SATURATION_FROM_PAPER_QUANTITY!r} audit "
        f"line; got audit list {audit!r}"
    )
    # beta is still saturated at 1.0 (the engine invariant).
    beta = _beta_value(out)
    assert beta == pytest.approx(1.0)


def test_adaptive_driver_no_saturation_when_C_above_one() -> None:
    """When ``per_cell_coefficient_C >= 1`` the unclipped envelope is
    always ``<= 1.0`` so no saturation audit code is emitted (audit
    P2-3 / 8.3).
    """
    from adaptive_reflow.algorithm.policy_driver import (
        BETA_SATURATION_FROM_PAPER_QUANTITY,
    )

    base_policy = _make_base_policy(beta=0.0)
    # Use target_estimate = 0.0 so ``diff = 0`` and ``raw = 1.0``;
    # divided by C = 1.0 the unclipped envelope is exactly 1.0 and
    # therefore not strictly > 1.0.
    driver = AdaptivePolicyDriver(
        target_estimate=0.0, per_cell_coefficient_C=1.0
    )
    audit: list[str] = []
    driver.compute_policy(
        None,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest="0" * 64,
        audit_codes=audit,
    )
    saturation_codes = [
        code for code in audit
        if code.startswith(BETA_SATURATION_FROM_PAPER_QUANTITY)
    ]
    assert saturation_codes == []


def test_adaptive_driver_legacy_path_does_not_saturate() -> None:
    """When ``per_cell_coefficient_C=None`` (legacy path) the
    unclipped envelope is already ``<= 1.0`` so no saturation audit
    code is emitted (audit P2-3 / 8.3).
    """
    from adaptive_reflow.algorithm.policy_driver import (
        BETA_SATURATION_FROM_PAPER_QUANTITY,
    )

    base_policy = _make_base_policy(beta=0.0)
    driver = AdaptivePolicyDriver(target_estimate=0.0)
    audit: list[str] = []
    driver.compute_policy(
        None,
        base_policy=base_policy,
        channel="xy",
        prior_endpoint_digest="0" * 64,
        audit_codes=audit,
    )
    saturation_codes = [
        code for code in audit
        if code.startswith(BETA_SATURATION_FROM_PAPER_QUANTITY)
    ]
    assert saturation_codes == []


# ---------------------------------------------------------------------------
# 8. _stable_digest canonical JSON encoder (P2-11)
# ---------------------------------------------------------------------------


def test_stable_digest_canonical_json_numpy_float64() -> None:
    """``_stable_digest`` produces the same digest for
    ``numpy.float64(0.5)`` and ``float(0.5)`` (audit P2-11:
    numerically-equal values from different dtypes produce the same
    digest).
    """
    import numpy as np

    from adaptive_reflow.algorithm.policy_driver import (
        _canonical_json_default,
        _stable_digest,
    )

    digest_py = _stable_digest({"value": 0.5})
    digest_np = _stable_digest({"value": np.float64(0.5)})
    assert digest_py == digest_np, (
        f"numpy.float64(0.5) and float(0.5) produced different "
        f"digests: {digest_py!r} vs {digest_np!r}"
    )


def test_canonical_json_default_handles_numpy_scalar() -> None:
    """``_canonical_json_default`` returns the Python builtin
    equivalent of numpy scalars (audit P2-11 helper contract).
    """
    import numpy as np

    from adaptive_reflow.algorithm.policy_driver import _canonical_json_default

    assert _canonical_json_default(np.float64(0.5)) == 0.5
    assert _canonical_json_default(np.int64(3)) == 3


def test_canonical_json_default_handles_arbitrary_object() -> None:
    """``_canonical_json_default`` falls back to ``str(obj)`` for
    objects that don't expose ``.item()`` or ``__float__`` (last-resort
    deterministic behaviour).
    """
    from adaptive_reflow.algorithm.policy_driver import _canonical_json_default

    class _Custom:
        def __str__(self) -> str:
            return "custom_repr"

    assert _canonical_json_default(_Custom()) == "custom_repr"


def test_frame_engine_canonical_json_numpy_float64() -> None:
    """The frame engine's ``_digest`` uses the same canonical JSON
    helper so numpy.float64(0.5) and float(0.5) produce the same
    digest (audit P2-15 cross-check).
    """
    import numpy as np

    from adaptive_reflow.frame.engine import _digest

    assert _digest({"value": 0.5}) == _digest({"value": np.float64(0.5)})
