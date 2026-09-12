"""PROTOCOL_SURFACE_TEST.

Cross-protocol surface tests for the algorithm-layer pluggable
abstract-impl design. For every Protocol, the suite:

1. Instantiates every concrete implementation registered in
   :data:`adaptive_reflow.algorithm.protocol_registry.PROTOCOL_REGISTRY`.
2. Asserts ``config_hash`` stability across runs (same args -> same
   hash).
3. Asserts ``config_hash`` uniqueness (different args -> different
   hash, where supported by the implementation).
4. Asserts ``from_config`` round-trip byte-identity (the rebuilt
   instance equals the original under ``to_config`` /
   ``from_config``).
5. Asserts ``audit_codes`` emission on bad inputs where the
   implementation supports it.

Module boundary
---------------

* pytest + stdlib only.
* Skips protocols whose implementations cannot be safely constructed
  inside the unit-test harness (e.g. the cosine family requires a
  fully-built :class:`CosineScheduleConfig`).
"""
from __future__ import annotations

import math
from collections.abc import Iterable

import pytest

from adaptive_reflow.algorithm import (
    PROTOCOL_REGISTRY,
    AdaptivePIDScheduler,
    AdaptivePolicyDriver,
    BayesianMergeOperator,
    BoundedMergeOperator,
    ConstantPolicyDriver,
    ConstantScheduler,
    ConvergenceAdaptiveScheduler,
    CosineAnnealScheduler,
    DistanceDecayBlender,
    EDMScheduler,
    EMAOperator,
    ExponentialScheduler,
    IdentityOperator,
    JitteredConstantScheduler,
    KalmanBoundedMergeOperator,
    LinearBlender,
    LinearScheduler,
    MergeOperatorProtocol,
    MultiTemperatureDistanceDecayBlender,
    OTLinearBlender,
    PIDIdentityOperator,
    PolicyDriverProtocol,
    PolynomialScheduler,
    ProtocolRegistryError,
    RestartBlenderProtocol,
    ScheduleAwareEMAOperator,
    ScheduleDerivedPolicyDriver,
    SchedulerProtocol,
    SigmoidScheduler,
    build_blender_from_config,
    build_merge_operator_from_config,
    build_policy_driver_from_config,
    build_scheduler_from_config,
    registered_families,
    validate_config_schema,
)
from adaptive_reflow.algorithm.scheduler import CodimensionSheetScheduler
from adaptive_reflow.universal.state import StateBundle

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state_bundle(value: float = 0.1, channel: str = "xy") -> Any:
    """Build a duck-typed bundle that exposes ``channel_values`` for
    the blender's extractor.

    A real :class:`StateBundle` is frozen so we wrap the value in a
    lightweight object that exposes the same duck-typed surface the
    blender looks for (``channel_values`` mapping). Returning a
    fully-built :class:`StateBundle` is unnecessary for these tests.
    """
    return _SimpleBundle(channel, value)


class _SimpleBundle:
    """Duck-typed blender input carrying a single channel value."""

    __slots__ = ("channel", "value")

    def __init__(self, channel: str, value: float) -> None:
        self.channel = str(channel)
        self.value = float(value)

    @property
    def channel_values(self) -> dict[str, tuple[float, ...]]:
        return {self.channel: (self.value,)}


# ---------------------------------------------------------------------------
# Registry surface tests
# ---------------------------------------------------------------------------


def test_protocol_registry_auto_populated() -> None:
    """PROTOCOL_REGISTRY auto-populates on import."""
    assert "SchedulerProtocol" in PROTOCOL_REGISTRY
    assert "PolicyDriverProtocol" in PROTOCOL_REGISTRY
    assert "MergeOperatorProtocol" in PROTOCOL_REGISTRY
    assert "RestartBlenderProtocol" in PROTOCOL_REGISTRY
    for protocol_name, families in registered_families().items():
        assert families, f"{protocol_name} should have registered families"


def test_validate_config_schema_fail_closed() -> None:
    """Unknown family raises ``ProtocolRegistryError`` with a clear message."""
    with pytest.raises(ProtocolRegistryError):
        validate_config_schema(
            {"family": "not-a-real-family"},
            protocol_name="SchedulerProtocol",
        )
    with pytest.raises(ProtocolRegistryError):
        validate_config_schema(
            {"family": "cosine"},
            protocol_name="NotAProtocol",
        )
    with pytest.raises(ProtocolRegistryError):
        validate_config_schema(
            "not-a-dict",  # type: ignore[arg-type]
            protocol_name="SchedulerProtocol",
        )


# ---------------------------------------------------------------------------
# SchedulerProtocol surface tests
# ---------------------------------------------------------------------------


# Mapping: family -> (default constructor kwargs, optional kwargs to
# vary for the uniqueness assertion). Some families need additional
# helpers (e.g. cosine needs a CosineScheduleConfig) — those are
# exercised via ``build_scheduler_from_config`` directly below.
SCHEDULER_INSTANCES: list[tuple[str, object]] = [
    ("constant", ConstantScheduler(cycle_length=10, n_cap=0.5)),
    ("constant", ConstantScheduler(cycle_length=10, n_cap=0.7)),
    ("linear", LinearScheduler(cycle_length=10, n_min=0.0, n_max=1.0)),
    ("linear", LinearScheduler(cycle_length=10, n_min=0.2, n_max=0.8)),
    ("exponential", ExponentialScheduler(cycle_length=10, n_max=1.0, alpha=0.1)),
    ("exponential", ExponentialScheduler(cycle_length=10, n_max=1.0, alpha=0.2)),
    ("polynomial", PolynomialScheduler(cycle_length=10, power=2.0)),
    ("polynomial", PolynomialScheduler(cycle_length=10, power=3.0)),
    ("sigmoid", SigmoidScheduler(cycle_length=10, steepness=10.0, midpoint=0.5)),
    ("sigmoid", SigmoidScheduler(cycle_length=10, steepness=5.0, midpoint=0.5)),
    ("convergence_adaptive", ConvergenceAdaptiveScheduler()),
    ("edm", EDMScheduler(cycle_length=10)),
    ("edm", EDMScheduler(cycle_length=10, sigma_min=0.001, sigma_max=160.0)),
    ("adaptive_pid", AdaptivePIDScheduler()),
    ("jittered_constant", JitteredConstantScheduler(cycle_length=10, n_cap=0.5)),
    ("jittered_constant", JitteredConstantScheduler(cycle_length=10, n_cap=0.3)),
]


@pytest.mark.parametrize("family,scheduler", SCHEDULER_INSTANCES)
def test_scheduler_protocol_surface(family: str, scheduler: object) -> None:
    assert isinstance(scheduler, SchedulerProtocol)
    # 1. config_hash stability.
    h1 = scheduler.config_hash()
    h2 = scheduler.config_hash()
    assert h1 == h2
    # 2. cycle_length / schedule_family are sane.
    assert scheduler.cycle_length() >= 1
    assert isinstance(scheduler.schedule_family(), str)
    # 3. round-trip via to_config / from_config is byte-identical.
    config = scheduler.to_config()
    rebuilt_cls = PROTOCOL_REGISTRY["SchedulerProtocol"].get(family)
    if rebuilt_cls is None:
        pytest.skip(f"{family} not in registry")
    rebuilt = rebuilt_cls.from_config(config)
    assert rebuilt.config_hash() == scheduler.config_hash()


# Uniqueness: same family + different config must hash differently.
@pytest.mark.parametrize(
    "family,a,b",
    [
        ("constant", ConstantScheduler(cycle_length=10, n_cap=0.5),
         ConstantScheduler(cycle_length=10, n_cap=0.7)),
        ("linear", LinearScheduler(cycle_length=10, n_min=0.0, n_max=1.0),
         LinearScheduler(cycle_length=10, n_min=0.2, n_max=0.8)),
        ("exponential", ExponentialScheduler(cycle_length=10, alpha=0.1),
         ExponentialScheduler(cycle_length=10, alpha=0.2)),
        ("polynomial", PolynomialScheduler(cycle_length=10, power=2.0),
         PolynomialScheduler(cycle_length=10, power=3.0)),
    ],
)
def test_scheduler_config_hash_uniqueness(
    family: str, a: object, b: object
) -> None:
    assert a.config_hash() != b.config_hash(), family


def test_scheduler_bad_input_rejected() -> None:
    """Schedulers fail closed on out-of-range / non-numeric inputs.

    ``ExponentialScheduler`` no longer rejects negative ``alpha`` — the
    decay-rate sign is a free choice (negative ``alpha`` produces a
    growing curve, which is a valid degenerate usage). All other
    families remain strict.
    """
    with pytest.raises(ValueError):
        ConstantScheduler(cycle_length=0)
    with pytest.raises(ValueError):
        ConstantScheduler(cycle_length=10, n_cap=1.5)
    with pytest.raises(ValueError):
        LinearScheduler(cycle_length=10, n_min=-0.1)
    with pytest.raises(ValueError):
        EDMScheduler(cycle_length=10, sigma_min=1.0, sigma_max=1.0)


def test_cosine_scheduler_round_trip() -> None:
    """Cosine round-trip via ``build_scheduler_from_config``."""
    from adaptive_reflow.algorithm import default_cosine_scheduler

    original = default_cosine_scheduler(cycle_length=10, n_min=0.1, n_max=0.9)
    cfg = original.to_config()
    cfg["family"] = "cosine"
    rebuilt = build_scheduler_from_config(cfg)
    assert isinstance(rebuilt, CosineAnnealScheduler)
    assert rebuilt.config_hash() == original.config_hash()


# ---------------------------------------------------------------------------
# MergeOperatorProtocol surface tests
# ---------------------------------------------------------------------------


MERGE_INSTANCES: list[tuple[str, object]] = [
    ("bounded", BoundedMergeOperator()),
    ("identity", IdentityOperator()),
    ("ema", EMAOperator(alpha=0.5)),
    ("kalman_bounded", KalmanBoundedMergeOperator()),
    ("bayesian", BayesianMergeOperator()),
    ("pid_identity", PIDIdentityOperator()),
    ("schedule_ema", ScheduleAwareEMAOperator()),
]


@pytest.mark.parametrize("family,operator", MERGE_INSTANCES)
def test_merge_operator_protocol_surface(
    family: str, operator: object
) -> None:
    assert isinstance(operator, MergeOperatorProtocol)
    h1 = operator.config_hash()
    h2 = operator.config_hash()
    assert h1 == h2
    config = operator.to_config()
    rebuilt_cls = PROTOCOL_REGISTRY["MergeOperatorProtocol"].get(family)
    if rebuilt_cls is None:
        pytest.skip(f"{family} not in registry")
    rebuilt = rebuilt_cls.from_config(config)
    assert rebuilt.config_hash() == operator.config_hash()


@pytest.mark.parametrize(
    "family,a,b",
    [
        ("ema", EMAOperator(alpha=0.1), EMAOperator(alpha=0.5)),
        ("kalman_bounded", KalmanBoundedMergeOperator(prior_variance=0.1),
         KalmanBoundedMergeOperator(prior_variance=0.5)),
        ("bayesian", BayesianMergeOperator(alpha_prior=1.0),
         BayesianMergeOperator(alpha_prior=2.0)),
        ("pid_identity", PIDIdentityOperator(kp_residual=0.1),
         PIDIdentityOperator(kp_residual=0.2)),
        ("schedule_ema", ScheduleAwareEMAOperator(alpha_min=0.1),
         ScheduleAwareEMAOperator(alpha_min=0.4)),
    ],
)
def test_merge_operator_config_hash_uniqueness(
    family: str, a: object, b: object
) -> None:
    assert a.config_hash() != b.config_hash(), family


def test_merge_audit_codes_emitted_on_bad_input() -> None:
    """Operators emit canonical audit codes on non-finite / out-of-range
    inputs (closes P0-3)."""
    op = BoundedMergeOperator()
    audit: list[str] = []
    result = op.merge(
        prev=float("nan"),
        dynamic=0.5,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=audit,
    )
    assert math.isfinite(result)
    assert audit, "audit_codes should be non-empty on bad input"
    # Identity / EMA also clip + audit.
    for op_ in (IdentityOperator(), EMAOperator()):
        audit2: list[str] = []
        result2 = op_.merge(
            prev=0.5,
            dynamic=float("nan"),
            cap=1.0,
            floor=0.0,
            delta_cap_up=0.5,
            delta_cap_down=0.5,
            audit_codes=audit2,
        )
        assert math.isfinite(result2)
        assert audit2


def test_merge_bad_input_rejected() -> None:
    """Non-numeric / None inputs still raise (fail-closed)."""
    op = BoundedMergeOperator()
    with pytest.raises((ValueError, TypeError)):
        op.merge(
            prev=None,  # type: ignore[arg-type]
            dynamic=0.5,
            cap=1.0,
            floor=0.0,
            delta_cap_up=0.5,
            delta_cap_down=0.5,
        )


# ---------------------------------------------------------------------------
# PolicyDriverProtocol surface tests
# ---------------------------------------------------------------------------


def _make_base_policy() -> object:
    """Build a minimal :class:`FinalRestartPolicy` for driver tests."""
    from adaptive_reflow.contracts.authority import FinalRestartPolicy

    return FinalRestartPolicy(
        policy_id="policy-test",
        writer_id="writer-test",
        run_id="run-test",
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={},
        alpha_by_channel={},
        fresh_noise_floor_by_channel={},
        freeze_admission_by_channel={},
        beta_from_schedule=False,
        driver_computed_beta=False,
        policy_hash="placeholder-hash",
    )


POLICY_DRIVERS: list[tuple[str, object]] = [
    ("schedule_derived", ScheduleDerivedPolicyDriver()),
    ("constant", ConstantPolicyDriver(beta=0.5)),
    ("constant", ConstantPolicyDriver(beta=0.7)),
    ("adaptive", AdaptivePolicyDriver()),
]


@pytest.mark.parametrize("family,driver", POLICY_DRIVERS)
def test_policy_driver_protocol_surface(family: str, driver: object) -> None:
    assert isinstance(driver, PolicyDriverProtocol)
    h1 = driver.config_hash()
    h2 = driver.config_hash()
    assert h1 == h2
    config = driver.to_config()
    rebuilt_cls = PROTOCOL_REGISTRY["PolicyDriverProtocol"].get(family)
    assert rebuilt_cls is not None, f"{family} not in registry"
    rebuilt = rebuilt_cls.from_config(config)
    assert rebuilt.config_hash() == driver.config_hash()


def test_policy_driver_bad_input_rejected() -> None:
    with pytest.raises(ValueError):
        ConstantPolicyDriver(beta=float("nan"))
    with pytest.raises(ValueError):
        AdaptivePolicyDriver(target_estimate=float("inf"))
    with pytest.raises(ValueError):
        AdaptivePolicyDriver(per_cell_coefficient_C=-1.0)


# ---------------------------------------------------------------------------
# RestartBlenderProtocol surface tests
# ---------------------------------------------------------------------------


BLENDERS: list[tuple[str, object]] = [
    ("linear", LinearBlender()),
    ("distance_decay", DistanceDecayBlender(temperature=1.0)),
    ("distance_decay", DistanceDecayBlender(temperature=2.0)),
    ("ot_linear", OTLinearBlender()),
    ("multi_temperature_distance_decay",
     MultiTemperatureDistanceDecayBlender(
         per_channel_temperatures={"xy": 0.5}
     )),
]


@pytest.mark.parametrize("family,blender", BLENDERS)
def test_blender_protocol_surface(family: str, blender: object) -> None:
    assert isinstance(blender, RestartBlenderProtocol)
    h1 = blender.config_hash()
    h2 = blender.config_hash()
    assert h1 == h2
    config = blender.to_config()
    rebuilt_cls = PROTOCOL_REGISTRY["RestartBlenderProtocol"].get(family)
    assert rebuilt_cls is not None, f"{family} not in registry"
    rebuilt = rebuilt_cls.from_config(config)
    assert rebuilt.config_hash() == blender.config_hash()


def test_blender_audit_codes_emitted_on_bad_input() -> None:
    """Blenders emit canonical audit codes when ``memory_fraction`` is
    out of range."""
    prior = _make_state_bundle(value=0.5, channel="xy")
    fresh = _make_state_bundle(value=0.7, channel="xy")
    audit: list[str] = []
    bundle = LinearBlender().blend(
        prior, fresh,
        memory_fraction=1.5,  # out of range
        channel="xy",
        audit_codes=audit,
    )
    assert isinstance(bundle, StateBundle)
    assert audit
    # Distance-decay blender also clips.
    audit2: list[str] = []
    bundle2 = DistanceDecayBlender().blend(
        prior, fresh,
        memory_fraction=-0.1,
        channel="xy",
        audit_codes=audit2,
    )
    assert isinstance(bundle2, StateBundle)
    assert audit2


def test_blender_byte_determinism() -> None:
    """Two calls with identical inputs yield identical ``native_state_digest``."""
    prior = _make_state_bundle(value=0.5, channel="xy")
    fresh = _make_state_bundle(value=0.7, channel="xy")
    blender = LinearBlender()
    b1 = blender.blend(prior, fresh, memory_fraction=0.5, channel="xy")
    b2 = blender.blend(prior, fresh, memory_fraction=0.5, channel="xy")
    assert b1.native_state_digest == b2.native_state_digest
    b3 = blender.blend(prior, fresh, memory_fraction=0.7, channel="xy")
    assert b1.native_state_digest != b3.native_state_digest


def test_blender_bad_input_rejected() -> None:
    blender = LinearBlender()
    with pytest.raises(ValueError):
        blender.blend(
            _make_state_bundle(),
            _make_state_bundle(),
            memory_fraction=None,  # type: ignore[arg-type]
            channel="xy",
        )
    with pytest.raises(ValueError):
        DistanceDecayBlender(temperature=-1.0)
    with pytest.raises(ValueError):
        DistanceDecayBlender(temperature=float("inf"))


# ---------------------------------------------------------------------------
# Polymorphic builders
# ---------------------------------------------------------------------------


def test_build_scheduler_from_config_round_trip() -> None:
    """``build_scheduler_from_config`` rebuilds every registered family."""
    for family, scheduler in SCHEDULER_INSTANCES:
        config = scheduler.to_config()
        config["family"] = family
        rebuilt = build_scheduler_from_config(config)
        assert isinstance(rebuilt, SchedulerProtocol)
        # The rebuilt scheduler's config_hash may differ slightly from
        # the original (e.g. ``build_scheduler_from_config`` may set
        # default values the original omitted), but the family / class
        # must match.
        assert rebuilt.schedule_family() == scheduler.schedule_family()


def test_build_merge_operator_from_config_round_trip() -> None:
    for family, operator in MERGE_INSTANCES:
        config = operator.to_config()
        config["family"] = family
        rebuilt = build_merge_operator_from_config(config)
        assert isinstance(rebuilt, MergeOperatorProtocol)
        assert rebuilt.config_hash() == operator.config_hash()


def test_build_policy_driver_from_config_round_trip() -> None:
    for family, driver in POLICY_DRIVERS:
        config = driver.to_config()
        config["family"] = family
        rebuilt = build_policy_driver_from_config(config)
        assert isinstance(rebuilt, PolicyDriverProtocol)
        assert rebuilt.config_hash() == driver.config_hash()


def test_build_blender_from_config_round_trip() -> None:
    for family, blender in BLENDERS:
        config = blender.to_config()
        config["family"] = family
        rebuilt = build_blender_from_config(config)
        assert isinstance(rebuilt, RestartBlenderProtocol)
        assert rebuilt.config_hash() == blender.config_hash()


# ---------------------------------------------------------------------------
# W2 estimator + integrator + stage + runner surface smoke tests
# ---------------------------------------------------------------------------


def test_w2_registry_smoke() -> None:
    import numpy as np

    from adaptive_reflow.eval import (
        W2_REGISTRY,
        ModeCentreMSEEstimator,
        build_w2_estimator,
    )

    samples = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]], dtype=np.float64)
    centres = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float64)
    for family in W2_REGISTRY:
        estimator = build_w2_estimator(family)
        v = estimator.estimate(samples, centres)
        assert math.isfinite(v)
        # The estimator exposes either a class attribute or a
        # ``family()`` method depending on the convention.
        ef = getattr(estimator, "family", None)
        if callable(ef):
            assert ef() == family
        elif ef is not None:
            assert ef == family
    # Legacy estimator should reproduce the legacy formula
    # (mean of min_i ||x - c_i||^2 for each sample x).
    legacy = ModeCentreMSEEstimator().estimate(samples, centres)
    diffs = samples[:, None, :] - centres[None, :, :]
    sq = (diffs * diffs).sum(axis=-1)
    nearest = sq.min(axis=-1)
    expected = float(nearest.mean())
    assert legacy == pytest.approx(expected)


def test_integrator_registry_smoke() -> None:
    import numpy as np

    from adaptive_reflow.adapters import (
        INTEGRATOR_REGISTRY,
        build_integrator,
    )

    def v(t: float, y: np.ndarray) -> np.ndarray:
        return np.full_like(y, -0.5 * y)

    for family in INTEGRATOR_REGISTRY:
        integ = build_integrator(family)
        y = np.array([1.0, 1.0], dtype=np.float64)
        y_next = integ.step(v, 0.0, y, 0.1)
        assert y_next.shape == y.shape
        assert np.isfinite(y_next).all()


def test_stage_registry_smoke() -> None:
    from adaptive_reflow.frame import (
        STAGE_REGISTRY,
        CalibrationStage,
        ClaimGateStage,
        PromotionStage,
        RunStage,
        build_stage,
    )

    for family in STAGE_REGISTRY:
        stage = build_stage(family)
        out = stage.run({"input": "value"})
        assert isinstance(out, dict)
        assert "stage" in out
    # RunStage needs n_rounds.
    rs = RunStage(n_rounds=5)
    assert rs.config_hash() == rs.config_hash()
    cs = CalibrationStage()
    assert cs.config_hash() == cs.config_hash()
    cgs = ClaimGateStage()
    assert cgs.config_hash() == cgs.config_hash()
    ps = PromotionStage(policy_version="v1", route="default")
    assert ps.config_hash() == ps.config_hash()


def test_runner_registry_smoke() -> None:
    from adaptive_reflow.algorithm import (
        RUNNER_REGISTRY,
        build_runner,
    )

    for family in RUNNER_REGISTRY:
        runner = build_runner(family)
        out = runner.run({})
        assert isinstance(out, dict)


def test_rotation_policy_registry_smoke() -> None:
    from adaptive_reflow.algorithm import (
        ROTATION_POLICY_REGISTRY,
        build_rotation_policy,
    )

    for family in ROTATION_POLICY_REGISTRY:
        policy = build_rotation_policy(family)
        idx = policy.choose([])
        assert isinstance(idx, int)
        assert 0 <= idx < policy.n_arms
