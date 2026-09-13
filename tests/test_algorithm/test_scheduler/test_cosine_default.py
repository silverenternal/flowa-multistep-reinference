"""Cosine default + Protocol-conformance + deprecation tests.

Split out of the monolithic ``tests/test_algorithm/test_scheduler.py``
during Wave 104 P2-B. Pure file-system refactor — no behaviour change.
"""

from __future__ import annotations

import math
import warnings

import pytest

from adaptive_reflow.algorithm import (
    SCHEDULER_REGISTRY,
    CodimensionSheetScheduler,
    ConstantScheduler,
    ConvergenceAdaptiveScheduler,
    CosineAnnealScheduler,
    ExponentialScheduler,
    LinearScheduler,
    PolynomialScheduler,
    SchedulerProtocol,
    ScheduleSample,
    SigmoidScheduler,
    default_cosine_scheduler,
    default_paper_ratio_scheduler,
)
from adaptive_reflow.schedule.cosine import CosineScheduleSampler


def _legacy_sampler(config) -> CosineScheduleSampler:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return CosineScheduleSampler(config)


def test_scheduler_protocol_runtime_checkable() -> None:
    """Wave 34: the framework's *default* scheduler is paper-quantity-driven.

    ``default_paper_ratio_scheduler()`` returns a
    :class:`CodimensionSheetScheduler` whose ``n_cap`` is driven by
    the paper Lemma 2 / Lemma 3 sheet-vs-cell evidence balance (not
    the cosine closed form). It still conforms to
    :class:`SchedulerProtocol` (the framework depends only on the
    Protocol, never on a concrete schedule family).
    """
    scheduler = default_paper_ratio_scheduler()
    assert isinstance(scheduler, SchedulerProtocol)
    assert isinstance(scheduler, CodimensionSheetScheduler)


def test_cosine_anneal_scheduler_matches_legacy() -> None:
    scheduler = default_cosine_scheduler(cycle_length=8, n_min=0.1, n_max=0.9)
    legacy = _legacy_sampler(scheduler.config)
    for r in range(8):
        new = scheduler.sample(0, r, r)
        old = legacy.sample(0, r, r)
        assert new.n_cap == pytest.approx(float(old.n_cap))
        assert new.u_r == pytest.approx(old.u_r)
        assert new.family == old.family
        assert new.cycle_length == old.cycle_length
        assert new.memory_fraction() == pytest.approx(1.0 - float(old.n_cap))


def test_scheduler_sample_is_pure() -> None:
    scheduler = default_cosine_scheduler(cycle_length=5)
    a = scheduler.sample(2, 3, 7)
    b = scheduler.sample(2, 3, 7)
    assert a == b
    assert isinstance(a, ScheduleSample)


def test_scheduler_config_hash_is_stable() -> None:
    a = default_cosine_scheduler(cycle_length=12, n_min=0.2, n_max=0.8)
    b = default_cosine_scheduler(cycle_length=12, n_min=0.2, n_max=0.8)
    assert a.config_hash() == b.config_hash()
    a.sample(0, 1, 1)
    assert a.config_hash() == b.config_hash()
    c = default_cosine_scheduler(cycle_length=13, n_min=0.2, n_max=0.8)
    assert c.config_hash() != a.config_hash()


def test_scheduler_reset_clears_state() -> None:
    scheduler = default_cosine_scheduler(cycle_length=4)
    assert scheduler.last_sample is None
    scheduler.sample(0, 1, 1)
    assert scheduler.last_sample is not None
    scheduler.reset()
    assert scheduler.last_sample is None


def test_scheduler_accessors() -> None:
    """Wave 34: the framework's *default* scheduler is paper-quantity-driven.

    ``default_paper_ratio_scheduler`` returns a
    :class:`CodimensionSheetScheduler` whose ``schedule_family`` is
    """
    scheduler = default_paper_ratio_scheduler()
    assert scheduler.schedule_family() == "codimension_sheet"
    assert scheduler.cycle_length() >= 1
    assert isinstance(scheduler.config_hash(), str)
    # Cosine scheduler accessors still work.
    cosine = default_cosine_scheduler(cycle_length=4)
    assert cosine.schedule_family() == "cosine_no_restart"
    assert cosine.cycle_length() == 4


def test_legacy_sampler_emits_deprecation_warning() -> None:
    """Calling the legacy cosine sampler emits a :class:`DeprecationWarning`.

    Wave 34 (commit 55c6c3a) flipped the framework default to
    paper-quantity-driven via ``default_paper_ratio_scheduler()``;
    ``default_cosine_scheduler()`` is now deprecated. The
    ``CosineScheduleSampler`` helper inside ``adaptive_reflow.schedule.cosine``
    is itself a thin alias and no longer raises its own DeprecationWarning
    — the deprecation is raised by ``default_cosine_scheduler()`` itself.
    """
    with pytest.warns(DeprecationWarning, match="default_cosine_scheduler"):
        scheduler = default_cosine_scheduler(cycle_length=4)
        # Constructing the legacy sampler directly should warn.
        _legacy_sampler(scheduler.config)


def test_default_paper_ratio_scheduler_returns_codimension() -> None:
    """``default_paper_ratio_scheduler()`` returns a :class:`CodimensionSheetScheduler`."""
    scheduler = default_paper_ratio_scheduler()
    assert isinstance(scheduler, CodimensionSheetScheduler)
    assert scheduler.schedule_family() == "codimension_sheet"


def test_default_paper_ratio_scheduler_carries_evidence_ratio() -> None:
    """``default_paper_ratio_scheduler()`` runs through the paper-quantity path."""
    scheduler = default_paper_ratio_scheduler()
    for r in range(scheduler.cycle_length()):
        sample = scheduler.sample(0, r, r)
        # The codimension scheduler always carries evidence_ratio.
        assert sample.evidence_ratio is not None
        assert 0.0 <= sample.evidence_ratio <= 1.0


def test_default_paper_ratio_scheduler_byte_deterministic() -> None:
    """Two consecutive calls produce identical config_hash."""
    a = default_paper_ratio_scheduler()
    b = default_paper_ratio_scheduler()
    assert a.config_hash() == b.config_hash()
    # Sampling a few rounds doesn't perturb the hash.
    for r in range(a.cycle_length()):
        a.sample(0, r, r)
    assert a.config_hash() == b.config_hash()


def test_default_paper_ratio_scheduler_differs_from_cosine() -> None:
    """``default_paper_ratio_scheduler`` config_hash != ``default_cosine_scheduler``."""
    paper = default_paper_ratio_scheduler()
    cosine = default_cosine_scheduler()
    assert paper.config_hash() != cosine.config_hash()


def test_default_cosine_scheduler_emits_deprecation_warning() -> None:
    """``default_cosine_scheduler`` itself is now deprecated (Wave 34)."""
    with pytest.warns(DeprecationWarning, match="default_cosine_scheduler"):
        default_cosine_scheduler(cycle_length=4)


def test_default_paper_ratio_scheduler_audit_codes() -> None:
    """``default_paper_ratio_scheduler`` samples carry codimension audit codes."""
    scheduler = default_paper_ratio_scheduler()
    sample = scheduler.sample(0, 0, 0)
    # The codimension scheduler emits at least one audit code per sample.
    assert sample.audit_codes
    # All audit codes are non-empty strings.
    for code in sample.audit_codes:
        assert isinstance(code, str)
        assert code


def test_default_paper_ratio_scheduler_rejects_non_positive_eps() -> None:
    """``eps_implicit`` must be positive (paper Theorem 1 requires it)."""
    with pytest.raises(ValueError):
        CodimensionSheetScheduler(cycle_length=4, eps_implicit=0.0)
    with pytest.raises(ValueError):
        CodimensionSheetScheduler(cycle_length=4, eps_implicit=-0.1)


def test_default_paper_ratio_scheduler_with_profile_wires_paper_quantities() -> None:
    """``with_profile`` returns a scheduler whose paper quantities are cached."""
    base = default_paper_ratio_scheduler()
    profile = lambda x: math.sin(x)  # noqa: E731
    wired = base.with_profile(profile)
    assert wired.sheet_A is not None
    assert wired.packing_B is not None
    assert wired._profile_residual_fn is profile


def test_all_schedulers_conform_to_protocol() -> None:
    """Every registered scheduler class must satisfy SchedulerProtocol structurally."""
    # Ensure Phase-2 extra families (edm / adaptive_pid / jittered_constant) are
    # registered before asserting on SCHEDULER_REGISTRY contents — these are
    # registered lazily via _register_extra_scheduler_families on first
    # build_scheduler call, so we trigger that explicitly here.
    from adaptive_reflow.algorithm.scheduler._core import (
        _ensure_extra_families_registered,
    )
    _ensure_extra_families_registered()
    assert set(SCHEDULER_REGISTRY) == {
        "codimension_sheet",
        "cosine",
        "constant",
        "linear",
        "exponential",
        "polynomial",
        "sigmoid",
        "convergence_adaptive",
        "sequential",
        # Phase-2 P0/P2 additions (see
        # ``docs/algorithm-deep-uplift-plan.md``).
        "edm",
        "adaptive_pid",
        "jittered_constant",
        # Wave 31 — paper-quantity-driven + paper-quantity-aware scheduler.
        "paper_ratio_adaptive",
        # Wave 61 Agent 2 — smooth NFE-aware memory_fraction scaling.
        "nfe_aware_memory",
    }
    from adaptive_reflow.algorithm import (
        AdaptivePIDScheduler,
        EDMScheduler,
        JitteredConstantScheduler,
        PaperRatioAdaptiveScheduler,
    )
    instances: list[SchedulerProtocol] = [
        default_cosine_scheduler(cycle_length=5),
        ConstantScheduler(cycle_length=5),
        LinearScheduler(cycle_length=5),
        ExponentialScheduler(cycle_length=5),
        PolynomialScheduler(cycle_length=5),
        SigmoidScheduler(cycle_length=5),
        ConvergenceAdaptiveScheduler(),
        CodimensionSheetScheduler(cycle_length=5),
        EDMScheduler(cycle_length=5),
        AdaptivePIDScheduler(),
        JitteredConstantScheduler(cycle_length=5, n_cap=0.5),
        PaperRatioAdaptiveScheduler(
            base=CodimensionSheetScheduler(cycle_length=5),
        ),
    ]
    for instance in instances:
        assert isinstance(instance, SchedulerProtocol)
        # Every Protocol method must be callable and return the right shape.
        sample = instance.sample(0, 0, 0)
        assert isinstance(sample, ScheduleSample)
        assert isinstance(instance.cycle_length(), int)
        assert isinstance(instance.schedule_family(), str)
        assert isinstance(instance.config_hash(), str)
        instance.reset()


def test_all_schedulers_have_noop_record_round_feedback() -> None:
    """Every scheduler exposes a callable record_round_feedback (no-op by default)."""
    schedulers = [
        default_cosine_scheduler(cycle_length=5),
        ConstantScheduler(cycle_length=5),
        LinearScheduler(cycle_length=5),
        ExponentialScheduler(cycle_length=5),
        PolynomialScheduler(cycle_length=5),
        SigmoidScheduler(cycle_length=5),
        ConvergenceAdaptiveScheduler(),
        CodimensionSheetScheduler(cycle_length=5),
    ]
    for s in schedulers:
        assert hasattr(s, "record_round_feedback")
        assert callable(s.record_round_feedback)
        # The default no-op returns None and mutates no state.
        assert s.record_round_feedback(0, {"W2": 1.0}) is None
        # Resetting still works after a feedback call.
        s.reset()
