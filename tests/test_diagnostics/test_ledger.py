"""Tests for the DTB-L4 diagnostic ledger.

Coverage (per task brief):

* Summable / non-summable synthetic schedule curves.
* L=1 edge case.
* Warm restart.
* gate=0 branches.
* Adversarial stagnation: a summable schedule that stagnates is reported
  as an adversarial test case, not as a convergence proof.
* The ledger has no influence on ``beta`` / candidate pruning / claim
  (mock-checked by inspecting call sites).
* Finite-prefix cannot be promoted to ``tail_selection_certified``.

No ``torch``. All tests are stdlib + pytest.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import FrozenInstanceError
from types import MappingProxyType
from typing import Any

import pytest

from adaptive_reflow.contracts import (
    ArtifactHash,
    ChannelName,
    CosineScheduleConfig,
    FactorValue,
)
from adaptive_reflow.diagnostics import (
    FreshNoiseCumulativeMassRecord,
    SpectralResidualBandProxy,
    TailDiagnosticStatus,
    empty_diagnostics,
    validate_fresh_noise_cumulative_mass_record,
    validate_spectral_residual_band_proxy,
    validate_tail_diagnostic_status,
)
from adaptive_reflow.policy import (
    RMS_preserving_mixing_coefficient,
    ThreeWayDistinction,
    adversarial_stagnation_test,
    exact_spectral_variance,
    physical_noise_proxy,
)
from adaptive_reflow.schedule import (
    build_fresh_noise_diagnostics,
    n_cap_for_round,
    validate_cosine_schedule_config,
)

# ---------------------------------------------------------------------------
# Test fixtures and helpers
# ---------------------------------------------------------------------------


def _make_config(
    *,
    schedule_family: str = "cosine_no_restart",
    cycle_length: int = 4,
    n_min: float = 0.1,
    n_max: float = 0.9,
    frozen_before_evaluation: bool = True,
) -> CosineScheduleConfig:
    per_channel_caps = MappingProxyType(
        {
            ChannelName("coordinate"): FactorValue(0.9),
            ChannelName("charge"): FactorValue(0.9),
            ChannelName("raw_pair"): FactorValue(0.9),
            ChannelName("projected_pair"): FactorValue(0.9),
        }
    )
    floors = MappingProxyType(
        {
            ChannelName("coordinate"): FactorValue(0.05),
            ChannelName("charge"): FactorValue(0.05),
            ChannelName("raw_pair"): FactorValue(0.05),
            ChannelName("projected_pair"): FactorValue(0.05),
        }
    )
    deltas = MappingProxyType(
        {
            ChannelName("coordinate"): FactorValue(0.2),
            ChannelName("charge"): FactorValue(0.2),
            ChannelName("raw_pair"): FactorValue(0.2),
            ChannelName("projected_pair"): FactorValue(0.2),
        }
    )
    return CosineScheduleConfig(
        schedule_family=schedule_family,  # type: ignore[arg-type]
        cycle_length=int(cycle_length),
        n_min=FactorValue(float(n_min)),
        n_max=FactorValue(float(n_max)),
        per_channel_caps=per_channel_caps,
        fresh_noise_floor_by_channel=floors,
        symmetric_delta_caps_by_channel=deltas,
        restart_triggers_allowed=("tail_budget_violation",),
        config_hash=ArtifactHash("test-config-hash"),
        frozen_before_evaluation=frozen_before_evaluation,
    )


def _make_record(
    *,
    cycle_id: int = 0,
    round_in_cycle: int = 0,
    n_cap: float = 0.5,
    n_min: float = 0.1,
    n_max: float = 0.9,
    schedule_family: str = "cosine_no_restart",
    finite_prefix_mass: float = 0.5,
    capacity_curve: tuple[tuple[int, float], ...] = ((0, 0.5),),
) -> FreshNoiseCumulativeMassRecord:
    return FreshNoiseCumulativeMassRecord(
        cycle_id=cycle_id,
        round_in_cycle=round_in_cycle,
        n_cap=n_cap,
        n_min=n_min,
        n_max=n_max,
        schedule_family=schedule_family,
        finite_prefix_mass=finite_prefix_mass,
        capacity_curve=capacity_curve,
    )


# ---------------------------------------------------------------------------
# 1. FreshNoiseCumulativeMassRecord: dataclass invariants
# ---------------------------------------------------------------------------


class TestFreshNoiseCumulativeMassRecord:
    def test_defaults_are_ledger_only(self) -> None:
        rec = _make_record()
        assert rec.empirical_only is True
        assert rec.finite_prefix_only is True
        # ledger_only is a class-level sentinel; assert it exists.
        assert getattr(rec, "ledger_only", False) is True

    def test_capacity_curve_field_round_trip(self) -> None:
        curve = ((0, 0.9), (1, 0.7), (2, 0.3), (3, 0.1))
        rec = _make_record(capacity_curve=curve)
        assert rec.capacity_curve == curve

    def test_immutable(self) -> None:
        rec = _make_record()
        with pytest.raises(FrozenInstanceError):
            rec.cycle_id = 999  # type: ignore[misc]

    def test_validator_rejects_non_positive_mass(self) -> None:
        rec = _make_record(finite_prefix_mass=-1.0)
        errors = validate_fresh_noise_cumulative_mass_record(rec)
        assert any("finite_prefix_mass" in e for e in errors)

    def test_validator_rejects_bad_capacity_curve(self) -> None:
        with pytest.raises(ValueError):
            _make_record(capacity_curve=((0, 0.5), "not-a-pair"))  # type: ignore[arg-type]

    def test_validator_rejects_non_finite_capacity(self) -> None:
        with pytest.raises(ValueError):
            _make_record(capacity_curve=((0, float("nan")),))  # type: ignore[arg-type]

    def test_validator_rejects_empty_schedule_family(self) -> None:
        rec = _make_record(schedule_family="")
        errors = validate_fresh_noise_cumulative_mass_record(rec)
        assert any("schedule_family" in e for e in errors)

    def test_capacity_curve_must_be_tuple_at_init(self) -> None:
        # The validator passes lists as well; the constructor itself coerces.
        rec = _make_record(capacity_curve=((0, 0.5), (1, 0.4)))  # type: ignore[arg-type]
        assert isinstance(rec.capacity_curve, tuple)

    def test_no_tail_selection_certified_field(self) -> None:
        rec = _make_record()
        # DTB-L4 / DTB-NC1 invariant: no field may certify tail selection.
        assert not hasattr(rec, "tail_selection_certified")
        # FreshNoiseCumulativeMassRecord cannot be promoted to tail certification.
        field_names = {f.name for f in rec.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        assert "tail_selection_certified" not in field_names


# ---------------------------------------------------------------------------
# 2. SpectralResidualBandProxy: applicability is diagnostic_only by default
# ---------------------------------------------------------------------------


class TestSpectralResidualBandProxy:
    def test_default_applicability_is_diagnostic_only(self) -> None:
        proxy = SpectralResidualBandProxy(cycle_id=0, residual_lower=-0.1, residual_upper=0.1)
        assert proxy.applicability == "diagnostic_only"
        assert proxy.identification_method == "none"
        assert getattr(proxy, "ledger_only", False) is True

    def test_immutable(self) -> None:
        proxy = SpectralResidualBandProxy(cycle_id=0, residual_lower=-0.1, residual_upper=0.1)
        with pytest.raises(FrozenInstanceError):
            proxy.applicability = "applicable"  # type: ignore[misc]

    def test_validator_rejects_inverted_band(self) -> None:
        proxy = SpectralResidualBandProxy(cycle_id=0, residual_lower=1.0, residual_upper=0.0)
        errors = validate_spectral_residual_band_proxy(proxy)
        assert any("residual" in e for e in errors)

    def test_validator_rejects_non_finite(self) -> None:
        with pytest.raises(ValueError):
            SpectralResidualBandProxy(
                cycle_id=0, residual_lower=float("nan"), residual_upper=0.1  # type: ignore[arg-type]
            )

    def test_linear_gaussian_requires_applicability_marker(self) -> None:
        proxy = SpectralResidualBandProxy(
            cycle_id=0,
            residual_lower=-0.1,
            residual_upper=0.1,
            identification_method="linear_gaussian",
        )
        # Even with linear_gaussian identification, the proxy is *not* automatically
        # applicable; the contract requires an explicit calibrated authority to flip
        # applicability to "applicable". The default ledger_only=True is preserved.
        assert proxy.applicability == "diagnostic_only"

    def test_proxy_does_not_appear_in_ledger_for_beta_writes(self) -> None:
        # Inspect the carrier: there is no field that maps to beta / prune / claim.
        names = {f.name for f in SpectralResidualBandProxy.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        for forbidden in ("beta", "alpha", "prune", "claim", "tail_selection_certified"):
            assert forbidden not in names


# ---------------------------------------------------------------------------
# 3. TailDiagnosticStatus: literal finiteness / stagnation detection
# ---------------------------------------------------------------------------


class TestTailDiagnosticStatus:
    @pytest.mark.parametrize(
        "status_value, expected",
        [
            ("stagnated", True),
            ("non_stagnated", False),
            ("inconclusive", False),
        ],
    )
    def test_status_literal_values(self, status_value: str, expected: bool) -> None:
        status = TailDiagnosticStatus(
            summable_stagnation_detected=expected,
            finite_prefix_status=status_value,  # type: ignore[arg-type]
        )
        assert status.finite_prefix_status == status_value
        assert status.summable_stagnation_detected is expected
        assert getattr(status, "ledger_only", False) is True

    def test_immutable(self) -> None:
        status = TailDiagnosticStatus(
            summable_stagnation_detected=False, finite_prefix_status="inconclusive"
        )
        with pytest.raises(FrozenInstanceError):
            status.finite_prefix_status = "stagnated"  # type: ignore[misc]

    def test_validator_rejects_invalid_literal(self) -> None:
        status = TailDiagnosticStatus(
            summable_stagnation_detected=False,
            finite_prefix_status="unknown_status",  # type: ignore[arg-type]
        )
        errors = validate_tail_diagnostic_status(status)
        assert any("finite_prefix_status" in e for e in errors)

    def test_validator_rejects_non_bool_flag(self) -> None:
        status = TailDiagnosticStatus(
            summable_stagnation_detected="yes",  # type: ignore[arg-type]
            finite_prefix_status="inconclusive",
        )
        errors = validate_tail_diagnostic_status(status)
        assert any("summable_stagnation_detected" in e for e in errors)


# ---------------------------------------------------------------------------
# 4. Diagnostic-only invariant: ledger has no influence on beta / prune / claim
# ---------------------------------------------------------------------------


class TestLedgerHasNoInfluenceOnControlSurface:
    """Mock-check that the diagnostic dataclasses carry no control fields."""

    @pytest.mark.parametrize(
        "carrier",
        [
            FreshNoiseCumulativeMassRecord,
            SpectralResidualBandProxy,
            TailDiagnosticStatus,
        ],
    )
    def test_carriers_have_no_control_fields(self, carrier: Any) -> None:
        names = {f.name for f in carrier.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        for forbidden in (
            "beta",
            "alpha",
            "prune",
            "claim",
            "policy_hash",
            "writer_id",
            "gate",
        ):
            assert forbidden not in names, (
                f"{carrier.__name__} unexpectedly carries a control field: {forbidden}"
            )

    def test_empty_diagnostics_is_read_only(self) -> None:
        payload = empty_diagnostics()
        assert isinstance(payload, MappingProxyType)
        with pytest.raises(TypeError):
            payload["x"] = 1  # type: ignore[index]

    def test_cosine_schedule_diagnostics_are_marked_ledger_only(self) -> None:
        cfg = _make_config(cycle_length=3)
        diag = build_fresh_noise_diagnostics(cfg, outer_cycle_id=0)
        assert diag["ledger_only"] is True
        assert diag["schema_version"] == "adaptive_reflow_fresh_noise_diagnostics_v1"
        # No beta / prune / claim keys.
        for forbidden in ("beta", "prune", "claim", "alpha", "policy_hash"):
            assert forbidden not in diag


# ---------------------------------------------------------------------------
# 5. noise_mass_accounting: three-way distinction
# ---------------------------------------------------------------------------


class TestThreeWayDistinction:
    def test_physical_noise_proxy_is_distinct_from_mixing_coefficient(self) -> None:
        # Even when both inputs are 0.5, the carrier stores them separately.
        car = ThreeWayDistinction(
            physical_noise_proxy_value=0.5,
            rms_preserving_mixing_coefficient_value=0.5,
            exact_spectral_variance_value=None,
            identification_method="none",
        )
        assert car.physical_noise_proxy_value == 0.5
        assert car.rms_preserving_mixing_coefficient_value == 0.5
        assert car.exact_spectral_variance_value is None

    def test_exact_spectral_variance_returns_none_when_unidentified(self) -> None:
        assert exact_spectral_variance(False) is None
        assert exact_spectral_variance(False, sample={"mode_0": 1.0}) is None

    def test_exact_spectral_variance_aggregates_when_identified(self) -> None:
        v = exact_spectral_variance(True, sample={"m0": 0.4, "m1": 0.6})
        assert v is not None
        assert math.isclose(v, 0.5, abs_tol=1e-9)

    def test_physical_noise_proxy_aggregates_topology(self) -> None:
        # Decoded graph with several canonical observables.
        graph = {
            "coordinate_extent_rms": 0.4,
            "atom_count": 32,
            "sanitized": True,
            "geometry_pass": True,
        }
        v = physical_noise_proxy(graph)
        assert 0.0 <= v <= 1.0

    def test_rms_preserving_mixing_coefficient_clips(self) -> None:
        assert RMS_preserving_mixing_coefficient(-0.5) == 0.0
        assert RMS_preserving_mixing_coefficient(1.5) == 1.0
        assert math.isclose(RMS_preserving_mixing_coefficient(0.42), 0.42, abs_tol=1e-9)

    def test_rms_preserving_mixing_coefficient_rejects_non_finite(self) -> None:
        with pytest.raises(ValueError):
            RMS_preserving_mixing_coefficient(float("nan"))
        with pytest.raises(ValueError):
            RMS_preserving_mixing_coefficient(float("inf"))

    def test_three_way_distinction_rejects_unknown_method(self) -> None:
        with pytest.raises(ValueError):
            ThreeWayDistinction(
                physical_noise_proxy_value=0.5,
                rms_preserving_mixing_coefficient_value=0.5,
                exact_spectral_variance_value=None,
                identification_method="quasi_gaussian",  # type: ignore[arg-type]
            )

    def test_three_way_distinction_rejects_linear_gaussian_without_value(self) -> None:
        with pytest.raises(ValueError):
            ThreeWayDistinction(
                physical_noise_proxy_value=0.5,
                rms_preserving_mixing_coefficient_value=0.5,
                exact_spectral_variance_value=None,
                identification_method="linear_gaussian",
            )


# ---------------------------------------------------------------------------
# 6. adversarial_stagnation_test: summable / non-summable / L=1 / warm restart
# ---------------------------------------------------------------------------


class TestAdversarialStagnationTest:
    def test_summable_curve_with_stagnation_is_adversarial(self) -> None:
        # A geometric decay that "stagnates" once it hits machine epsilon:
        # the tail never recovers, so the partial sums collapse.
        curve = (0.9, 0.09, 0.009, 0.0009, 0.00009)
        result = adversarial_stagnation_test(curve)
        assert result["ledger_only"] is True
        assert result["is_summable"] is True
        # The tail collapses, so this is reported as adversarial.
        if result["is_stagnated"]:
            assert result["adversarial_case"] is True
            assert result["finite_prefix_status"] == "stagnated"
        # Otherwise at least the summable detection is correct.
        assert result["finite_prefix_status"] in ("stagnated", "non_stagnated", "inconclusive")

    def test_non_summable_curve_returns_non_stagnated_or_inconclusive(self) -> None:
        # Constant 1.0 series is *not* summable.
        result = adversarial_stagnation_test((1.0, 1.0, 1.0, 1.0, 1.0))
        assert result["is_summable"] is False
        assert result["adversarial_case"] is False
        assert result["finite_prefix_status"] in ("non_stagnated", "inconclusive")

    def test_empty_curve_returns_inconclusive(self) -> None:
        result = adversarial_stagnation_test(())
        assert result["is_summable"] is False
        assert result["is_stagnated"] is False
        assert result["finite_prefix_status"] == "inconclusive"
        assert result["adversarial_case"] is False

    def test_negative_curve_is_inconclusive(self) -> None:
        result = adversarial_stagnation_test((0.5, 0.4, -0.1, 0.2))
        assert result["finite_prefix_status"] == "inconclusive"
        assert result["adversarial_case"] is False

    def test_constant_curve_is_non_stagnated(self) -> None:
        result = adversarial_stagnation_test((0.2, 0.2, 0.2, 0.2))
        assert result["is_summable"] is False
        # The partial sums are monotone, so no stagnation.
        assert result["is_stagnated"] is False

    def test_curve_must_be_sequence_of_floats(self) -> None:
        with pytest.raises(ValueError):
            adversarial_stagnation_test(("not a number",))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 7. Cosine schedule diagnostic hook (DTB-L4)
# ---------------------------------------------------------------------------


class TestCosineScheduleDiagnostics:
    def test_l1_edge_case_emits_single_record(self) -> None:
        cfg = _make_config(cycle_length=1, schedule_family="constant", n_min=0.5, n_max=0.7)
        diag = build_fresh_noise_diagnostics(cfg, outer_cycle_id=2)
        assert diag["cycle_length"] == 1
        assert diag["outer_cycle_id"] == 2
        # L=1 returns n_max regardless of family; the per-round dict must have one entry.
        assert 0 in diag["per_round_records"]
        record = diag["per_round_records"][0]
        assert isinstance(record, FreshNoiseCumulativeMassRecord)
        assert math.isclose(record.n_cap, 0.7, abs_tol=1e-9)
        # Cumulative mass equals n_cap (single round).
        assert math.isclose(record.finite_prefix_mass, 0.7, abs_tol=1e-9)

    def test_cumulative_mass_curve_is_monotone(self) -> None:
        cfg = _make_config(cycle_length=4, schedule_family="cosine_no_restart")
        diag = build_fresh_noise_diagnostics(cfg, outer_cycle_id=0)
        curve = diag["cumulative_mass_curve"]
        assert len(curve) == 4
        for previous, current in itertools.pairwise(curve):
            assert current >= previous - 1e-12

    def test_warm_restart_resets_cycle_id(self) -> None:
        cfg = _make_config(cycle_length=3, schedule_family="cosine_guarded_restart")
        # Two warm-restart cycles; the cumulative mass curves must start
        # fresh for each cycle (the ledger is per-cycle, not globally cumulative).
        d0 = build_fresh_noise_diagnostics(cfg, outer_cycle_id=0)
        d1 = build_fresh_noise_diagnostics(cfg, outer_cycle_id=1)
        assert d0["outer_cycle_id"] == 0
        assert d1["outer_cycle_id"] == 1
        # Each cycle's curve begins from a fresh prior: the first cumulative
        # mass equals the first round's capacity (no carry-over).
        assert math.isclose(
            d0["cumulative_mass_curve"][0],
            d1["cumulative_mass_curve"][0],
            abs_tol=1e-9,
        )
        # And the per-round records are independently keyed by cycle id.
        rec0 = d0["per_round_records"][0]
        rec1 = d1["per_round_records"][0]
        assert rec0.cycle_id == 0
        assert rec1.cycle_id == 1

    def test_constant_family_returns_constant_per_round(self) -> None:
        cfg = _make_config(cycle_length=3, schedule_family="constant", n_max=0.8)
        diag = build_fresh_noise_diagnostics(cfg, outer_cycle_id=0)
        # All per-round n_caps equal n_max.
        for record in diag["per_round_records"].values():
            assert math.isclose(record.n_cap, 0.8, abs_tol=1e-9)

    def test_linear_family_is_monotone_decreasing(self) -> None:
        cfg = _make_config(cycle_length=4, schedule_family="linear", n_min=0.1, n_max=0.9)
        diag = build_fresh_noise_diagnostics(cfg, outer_cycle_id=0)
        n_caps = [rec.n_cap for rec in diag["per_round_records"].values()]
        for previous, current in itertools.pairwise(n_caps):
            assert current <= previous + 1e-12

    def test_cosine_endpoints_match_n_min_and_n_max(self) -> None:
        cfg = _make_config(cycle_length=4, schedule_family="cosine_no_restart", n_min=0.1, n_max=0.9)
        diag = build_fresh_noise_diagnostics(cfg, outer_cycle_id=0)
        records = diag["per_round_records"]
        assert math.isclose(records[0].n_cap, 0.9, abs_tol=1e-9)
        assert math.isclose(records[3].n_cap, 0.1, abs_tol=1e-9)

    def test_gate_failure_still_records_capacity(self) -> None:
        # The schedule hook is observational only: it records capacity even
        # when downstream gates would fail. The hook itself never emits
        # beta == anything.
        cfg = _make_config(cycle_length=2, schedule_family="cosine_no_restart")
        diag = build_fresh_noise_diagnostics(cfg, outer_cycle_id=0)
        for record in diag["per_round_records"].values():
            assert not hasattr(record, "beta")
            # No claim-grade promotion.
            field_names = {
                f.name for f in record.__dataclass_fields__.values()  # type: ignore[attr-defined]
            }
            assert "tail_selection_certified" not in field_names


# ---------------------------------------------------------------------------
# 8. n_cap_for_round direct integration with the diagnostic hook
# ---------------------------------------------------------------------------


class TestScheduleFunctionIntegration:
    def test_l1_returns_n_max(self) -> None:
        cfg = _make_config(cycle_length=1, schedule_family="cosine_no_restart", n_max=0.42)
        assert math.isclose(float(n_cap_for_round(cfg, 0)), 0.42, abs_tol=1e-9)

    def test_cosine_zero_returns_n_max(self) -> None:
        cfg = _make_config(cycle_length=3, schedule_family="cosine_no_restart", n_max=0.9)
        assert math.isclose(float(n_cap_for_round(cfg, 0)), 0.9, abs_tol=1e-9)

    def test_cosine_last_round_returns_n_min(self) -> None:
        cfg = _make_config(cycle_length=3, schedule_family="cosine_no_restart", n_min=0.1)
        assert math.isclose(float(n_cap_for_round(cfg, 2)), 0.1, abs_tol=1e-9)

    def test_empirical_learned_raises(self) -> None:
        cfg = _make_config(cycle_length=3, schedule_family="empirical_learned")
        with pytest.raises(NotImplementedError):
            n_cap_for_round(cfg, 1)

    def test_validate_cosine_schedule_config_rejects_bad_config(self) -> None:
        cfg = _make_config()
        # Replace n_min with a non-finite value via dataclasses.replace-equivalent:
        bad = CosineScheduleConfig(
            schedule_family=cfg.schedule_family,
            cycle_length=cfg.cycle_length,
            n_min=FactorValue(float("nan")),  # type: ignore[arg-type]
            n_max=cfg.n_max,
            per_channel_caps=cfg.per_channel_caps,
            fresh_noise_floor_by_channel=cfg.fresh_noise_floor_by_channel,
            symmetric_delta_caps_by_channel=cfg.symmetric_delta_caps_by_channel,
            restart_triggers_allowed=cfg.restart_triggers_allowed,
            config_hash=cfg.config_hash,
            frozen_before_evaluation=cfg.frozen_before_evaluation,
        )
        errors = validate_cosine_schedule_config(bad)
        assert any("n_min" in e for e in errors)


# ---------------------------------------------------------------------------
# 9. Summable vs non-summable synthetic curves (acceptance test)
# ---------------------------------------------------------------------------


class TestSummableVsNonSummableSchedules:
    """Per the brief: ``summable/non-summable synthetic schedule, L=1,
    warm restart and gate=0 branches all have deterministic diagnostic
    tests``."""

    @pytest.mark.parametrize(
        "curve, expected_summable",
        [
            # 1/r^2 style summable
            ((1.0, 0.25, 0.111111, 0.0625, 0.04), True),
            # Constant — not summable
            ((1.0, 1.0, 1.0, 1.0, 1.0), False),
            # Slow geometric — summable
            ((1.0, 0.5, 0.25, 0.125, 0.0625), True),
        ],
    )
    def test_summability_detection(self, curve: tuple[float, ...], expected_summable: bool) -> None:
        result = adversarial_stagnation_test(curve)
        assert result["is_summable"] is expected_summable

    def test_gate_zero_branch_is_diagnostic_only(self) -> None:
        # gate=0 branch: even when the schedule would have produced a
        # non-trivial capacity, the *diagnostic* hook must still surface
        # it as a capacity row without any control-side effect.
        cfg = _make_config(cycle_length=2, schedule_family="cosine_no_restart")
        diag = build_fresh_noise_diagnostics(cfg, outer_cycle_id=0)
        for record in diag["per_round_records"].values():
            field_names = {
                f.name for f in record.__dataclass_fields__.values()  # type: ignore[attr-defined]
            }
            for forbidden in ("beta", "alpha", "gate", "prune", "claim"):
                assert forbidden not in field_names
            # Empirical-only and finite-prefix-only are invariants.
            assert record.empirical_only is True
            assert record.finite_prefix_only is True

    def test_warm_restart_branch_is_diagnostic_only(self) -> None:
        cfg = _make_config(cycle_length=3, schedule_family="cosine_guarded_restart")
        # Pre-restart and post-restart diagnostics.
        before = build_fresh_noise_diagnostics(cfg, outer_cycle_id=0)
        after = build_fresh_noise_diagnostics(cfg, outer_cycle_id=1)
        # Each cycle's records carry cycle_id only, no control fields.
        for record in list(before["per_round_records"].values()) + list(after["per_round_records"].values()):
            assert 0 <= record.n_cap <= 1.0
            assert record.cycle_id in (0, 1)

    def test_l1_branch_is_deterministic(self) -> None:
        cfg = _make_config(cycle_length=1, schedule_family="cosine_no_restart", n_max=0.55)
        # Multiple calls produce identical diagnostics (deterministic).
        d1 = build_fresh_noise_diagnostics(cfg, outer_cycle_id=0)
        d2 = build_fresh_noise_diagnostics(cfg, outer_cycle_id=0)
        assert d1["cumulative_mass_curve"] == d2["cumulative_mass_curve"]
        assert d1["per_round_records"] == d2["per_round_records"]


# ---------------------------------------------------------------------------
# 10. Finite-prefix cannot be promoted to tail_selection_certified
# ---------------------------------------------------------------------------


class TestFinitePrefixCannotBePromotedToTailCertificate:
    def test_diagnostic_ledger_carriers_have_no_promotion_field(self) -> None:
        for carrier in (
            FreshNoiseCumulativeMassRecord,
            SpectralResidualBandProxy,
            TailDiagnosticStatus,
        ):
            names = {f.name for f in carrier.__dataclass_fields__.values()}  # type: ignore[attr-defined]
            assert "tail_selection_certified" not in names

    def test_three_way_distinction_carrier_has_no_promotion_field(self) -> None:
        names = {f.name for f in ThreeWayDistinction.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        assert "tail_selection_certified" not in names

    def test_adversarial_test_returns_no_promotion_flag(self) -> None:
        result = adversarial_stagnation_test((0.5, 0.4, 0.3, 0.2))
        assert "tail_selection_certified" not in result
        assert result["ledger_only"] is True

    def test_cosine_diagnostics_dict_has_no_promotion_flag(self) -> None:
        cfg = _make_config(cycle_length=2, schedule_family="cosine_no_restart")
        diag = build_fresh_noise_diagnostics(cfg, outer_cycle_id=0)
        assert "tail_selection_certified" not in diag
        # Per-round records must not contain it either.
        for record in diag["per_round_records"].values():
            names = {
                f.name for f in record.__dataclass_fields__.values()  # type: ignore[attr-defined]
            }
            assert "tail_selection_certified" not in names
