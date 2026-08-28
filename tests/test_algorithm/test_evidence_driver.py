"""Evidence-driven scheduling + heuristic-mode asymptotic diagnostics."""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from typing import Any

import numpy as np
import pytest

from adaptive_reflow.algorithm.evidence_driver import (
    EVIDENCE_DRIVEN_AUDIT_CODE,
    EVIDENCE_DRIVEN_FAMILY_SUFFIX,
    EvidenceDrivenScheduler,
    EvidenceModeReport,
    check_evidence_mode,
    warn_if_heuristic_evidence_mode,
)
from adaptive_reflow.algorithm.scheduler import (
    CodimensionSheetScheduler,
    ConstantScheduler,
    ScheduleSample,
)
from adaptive_reflow.contracts import CosineScheduleSample

CYCLE = 20


class _StubScheduler:
    """Minimal scheduler with a scripted evidence trajectory.

    Emits a fixed terminal capacity of ``0.15`` (memory fraction
    ``0.85`` — the cosine baseline's documented plateau) and an
    evidence ratio that anneals toward the sheet-dominant regime, so the
    driver's effect can be read off exactly rather than inferred.
    """

    def __init__(self, *, ratios: tuple[float, ...], n_cap: float = 0.15) -> None:
        self._ratios = ratios
        self._n_cap = float(n_cap)
        self.feedback: list[tuple[int, Mapping[str, float]]] = []
        self.reset_calls = 0

    def sample(
        self, outer_cycle_id: int, round_in_cycle: int, target_round: int
    ) -> ScheduleSample:
        return ScheduleSample(
            outer_cycle_id=int(outer_cycle_id),
            round_in_cycle=int(round_in_cycle),
            cycle_length=len(self._ratios),
            n_cap=self._n_cap,
            n_min=0.0,
            n_max=1.0,
            u_r=float(round_in_cycle) / float(max(1, len(self._ratios) - 1)),
            family="stub",
            computed_at_round=int(target_round),
            schedule_hash="stub-hash",
            audit_codes=("stub_baseline",),
            evidence_ratio=self._ratios[int(round_in_cycle)],
        )

    def cycle_length(self) -> int:
        return len(self._ratios)

    def schedule_family(self) -> str:
        return "stub"

    def config_hash(self) -> str:
        return "stub-config-hash"

    def reset(self) -> None:
        self.reset_calls += 1

    def record_round_feedback(
        self, round_in_cycle: int, metrics: Mapping[str, float]
    ) -> None:
        self.feedback.append((int(round_in_cycle), dict(metrics)))

    def inject_noise(
        self,
        state: np.ndarray,
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> np.ndarray:
        return np.asarray(state, dtype=np.float64) + 1.0

    def to_config(self) -> dict[str, Any]:
        return {"family": "stub", "ratios": list(self._ratios)}


# ---------------------------------------------------------------------------
# Construction / validation
# ---------------------------------------------------------------------------


def test_rejects_a_non_scheduler_inner() -> None:
    with pytest.raises(ValueError):
        EvidenceDrivenScheduler(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        EvidenceDrivenScheduler(object())  # type: ignore[arg-type]


@pytest.mark.parametrize("strength", [-0.1, 1.5, float("nan"), True])
def test_rejects_out_of_range_strength(strength: Any) -> None:
    with pytest.raises(ValueError):
        EvidenceDrivenScheduler(ConstantScheduler(), strength=strength)


# ---------------------------------------------------------------------------
# Pluggability: opting out changes nothing
# ---------------------------------------------------------------------------


def test_strength_zero_is_the_identity() -> None:
    inner = _StubScheduler(ratios=(0.5,) * CYCLE)
    wrapped = EvidenceDrivenScheduler(inner, strength=0.0)
    for r in range(CYCLE):
        assert wrapped.sample(0, r, r) == inner.sample(0, r, r)


def test_families_without_an_evidence_ratio_pass_through_untouched() -> None:
    """Wrapping a non-codimension scheduler must be a no-op, not an error."""
    inner = ConstantScheduler(cycle_length=CYCLE)
    wrapped = EvidenceDrivenScheduler(inner, strength=1.0)
    for r in range(CYCLE):
        base = inner.sample(0, r, r)
        driven = wrapped.sample(0, r, r)
        assert driven == base
        assert EVIDENCE_DRIVEN_AUDIT_CODE not in driven.audit_codes


def test_delegation_reaches_the_inner_scheduler() -> None:
    inner = _StubScheduler(ratios=(0.9,) * CYCLE)
    wrapped = EvidenceDrivenScheduler(inner)
    assert wrapped.cycle_length() == CYCLE
    assert wrapped.schedule_family() == "stub" + EVIDENCE_DRIVEN_FAMILY_SUFFIX
    wrapped.reset()
    assert inner.reset_calls == 1
    wrapped.record_round_feedback(3, {"W2": 0.5})
    assert inner.feedback == [(3, {"W2": 0.5})]


def test_config_hash_separates_strengths_and_inner_configs() -> None:
    inner = _StubScheduler(ratios=(0.9,) * CYCLE)
    weak = EvidenceDrivenScheduler(inner, strength=0.25)
    strong = EvidenceDrivenScheduler(inner, strength=1.0)
    assert weak.config_hash() != strong.config_hash()
    assert weak.config_hash() != inner.config_hash()
    assert weak.config_hash() == EvidenceDrivenScheduler(inner,
                                                          strength=0.25).config_hash()


def test_to_config_round_trips_through_from_config() -> None:
    inner = _StubScheduler(ratios=(0.9,) * CYCLE)
    original = EvidenceDrivenScheduler(inner, strength=0.6)
    config = original.to_config()
    assert config["family"] == "stub" + EVIDENCE_DRIVEN_FAMILY_SUFFIX
    assert config["inner"] == inner.to_config()
    rebuilt = EvidenceDrivenScheduler.from_config(config, inner=inner)
    assert rebuilt.config_hash() == original.config_hash()


def test_from_config_requires_an_explicit_inner() -> None:
    with pytest.raises(ValueError):
        EvidenceDrivenScheduler.from_config({"strength": 1.0})


def test_inject_noise_is_not_double_modulated() -> None:
    inner = _StubScheduler(ratios=(0.5,) * CYCLE)
    wrapped = EvidenceDrivenScheduler(inner, strength=1.0)
    sample = wrapped.sample(0, 0, 0).as_cosine_schedule_sample()
    state = np.zeros(3, dtype=np.float64)
    generator = np.random.default_rng(0)
    assert np.allclose(
        wrapped.inject_noise(state, sample, generator=generator),
        inner.inject_noise(state, sample, generator=generator),
    )


# ---------------------------------------------------------------------------
# Quantitative target: terminal memory fraction 0.85 -> >= 0.99
# ---------------------------------------------------------------------------


def test_evidence_driver_lifts_the_terminal_memory_fraction() -> None:
    """P0 #9 target: terminal memory fraction 0.85 (baseline) -> >= 0.99.

    The stub anneals the evidence ratio to ``0.06`` at the terminal
    round — the sheet-dominant regime paper Theorem 1 predicts — so the
    driver cuts the residual fresh-noise capacity to ``0.15 * 0.06``.
    """
    ratios = tuple(
        1.0 - 0.94 * (r / (CYCLE - 1)) ** 2 for r in range(CYCLE)
    )
    inner = _StubScheduler(ratios=ratios, n_cap=0.15)
    wrapped = EvidenceDrivenScheduler(inner, strength=1.0)

    baseline_memory = inner.sample(0, CYCLE - 1, CYCLE - 1).memory_fraction()
    driven_memory = wrapped.sample(0, CYCLE - 1, CYCLE - 1).memory_fraction()

    assert baseline_memory == pytest.approx(0.85)
    assert driven_memory >= 0.99, (
        f"driven terminal memory fraction {driven_memory:.4f} missed the "
        f">= 0.99 target (baseline {baseline_memory:.4f})"
    )


def test_driven_capacity_never_exceeds_the_baseline() -> None:
    ratios = tuple(1.0 - 0.5 * (r / (CYCLE - 1)) for r in range(CYCLE))
    inner = _StubScheduler(ratios=ratios)
    wrapped = EvidenceDrivenScheduler(inner, strength=1.0)
    for r in range(CYCLE):
        assert wrapped.sample(0, r, r).n_cap <= inner.sample(0, r, r).n_cap + 1e-15


def test_driven_capacity_stays_inside_the_inner_envelope() -> None:
    inner = _StubScheduler(ratios=(0.0,) * CYCLE, n_cap=0.5)
    wrapped = EvidenceDrivenScheduler(inner, strength=1.0)
    for r in range(CYCLE):
        base = inner.sample(0, r, r)
        driven = wrapped.sample(0, r, r)
        assert base.n_min <= driven.n_cap <= base.n_max


def test_strength_interpolates_monotonically() -> None:
    inner = _StubScheduler(ratios=(0.2,) * CYCLE)
    caps = [
        EvidenceDrivenScheduler(inner, strength=s).sample(0, 0, 0).n_cap
        for s in (0.0, 0.25, 0.5, 0.75, 1.0)
    ]
    assert caps == sorted(caps, reverse=True)


def test_driven_samples_carry_the_audit_code() -> None:
    inner = _StubScheduler(ratios=(0.5,) * CYCLE)
    driven = EvidenceDrivenScheduler(inner, strength=1.0).sample(0, 0, 0)
    assert driven.audit_codes[-1] == EVIDENCE_DRIVEN_AUDIT_CODE
    assert "stub_baseline" in driven.audit_codes
    assert driven.family.endswith(EVIDENCE_DRIVEN_FAMILY_SUFFIX)


def test_wraps_the_real_codimension_scheduler() -> None:
    inner = CodimensionSheetScheduler(cycle_length=10, eps_implicit=0.05)
    wrapped = EvidenceDrivenScheduler(inner, strength=1.0)
    for r in range(10):
        base = inner.sample(0, r, r)
        driven = wrapped.sample(0, r, r)
        assert driven.n_cap <= base.n_cap + 1e-15
        assert driven.memory_fraction() >= base.memory_fraction() - 1e-15


# ---------------------------------------------------------------------------
# Heuristic-mode asymptotic diagnostic
# ---------------------------------------------------------------------------


def test_paper_grounded_scheduler_is_not_flagged() -> None:
    scheduler = CodimensionSheetScheduler(
        cycle_length=20, eps_implicit=1e-6, profile_residual_fn=lambda x: x * x
    )
    report = check_evidence_mode(scheduler)
    assert isinstance(report, EvidenceModeReport)
    assert report.paper_grounded
    assert not report.asymptotic_risk
    assert report.message == ""


@pytest.mark.parametrize("eps", [1e-4, 1e-6, 1e-9])
def test_heuristic_mode_at_small_eps_is_flagged(eps: float) -> None:
    """Detection coverage: every unsound configuration is caught."""
    scheduler = CodimensionSheetScheduler(cycle_length=20, eps_implicit=eps)
    report = check_evidence_mode(scheduler)
    assert report.asymptotic_risk
    assert not report.paper_grounded
    assert "profile_residual_fn" in report.message


@pytest.mark.parametrize("eps", [1e-3, 0.01, 0.05, 0.5])
def test_heuristic_mode_at_safe_eps_is_not_flagged(eps: float) -> None:
    """No false positives on correctly-configured schedulers."""
    scheduler = CodimensionSheetScheduler(cycle_length=20, eps_implicit=eps)
    assert not check_evidence_mode(scheduler).asymptotic_risk


def test_non_codimension_schedulers_are_out_of_scope() -> None:
    report = check_evidence_mode(ConstantScheduler())
    assert not report.asymptotic_risk
    assert report.eps_implicit is None


def test_warn_helper_emits_exactly_once_for_a_risky_scheduler() -> None:
    risky = CodimensionSheetScheduler(cycle_length=20, eps_implicit=1e-8)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        report = warn_if_heuristic_evidence_mode(risky)
    assert report.asymptotic_risk
    assert len(caught) == 1
    assert issubclass(caught[0].category, UserWarning)


def test_warn_helper_is_silent_for_a_safe_scheduler() -> None:
    safe = CodimensionSheetScheduler(
        cycle_length=20, eps_implicit=1e-8, profile_residual_fn=lambda x: x
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warn_if_heuristic_evidence_mode(safe)
    assert [w for w in caught if issubclass(w.category, UserWarning)] == []


def test_check_rejects_a_bad_threshold() -> None:
    with pytest.raises(ValueError):
        check_evidence_mode(ConstantScheduler(), eps_threshold=0.0)
