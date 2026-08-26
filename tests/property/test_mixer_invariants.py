"""Property-based invariants for the per-channel mixer (DTB-R2 / DTB-R3).

Five hypothesis-driven templates covering the universal mixer output of
:func:`adaptive_reflow.frame.channel_rule.compute_channel_decision`:

14. ``bounded_target_fraction`` lies in ``[0, 1]``.
15. When the gate is open, ``alpha + beta == 1.0`` (label-only identity).
16. Gate-open monotonicity in the four canonical families
    (``stability_up`` / ``uncertainty_up`` / ``support_down`` / ``age_up``).
17. Closed-gate collapse: any blocker -> ``beta=0``, ``alpha=1``,
    ``evidence_score=0``.
18. ``audit_reason`` is deterministic across repeated calls.

Stdlib-only.
"""
from __future__ import annotations

import dataclasses

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from adaptive_reflow.frame.channel_rule import (
    check_monotonicity_property,
    compute_channel_decision,
)
from tests._utils.asserters import (
    assert_idempotent,
    assert_unit_interval,
)

from . import unit_floats

# ---------------------------------------------------------------------------
# Local helpers — build a controlled ChannelRuleInputs.
# ---------------------------------------------------------------------------
#
# We avoid the heavier ``st_channel_inputs`` strategy from conftest.py
# here because that strategy samples ``tail_admissibility`` /
# ``horizon_coverage_proven`` / etc. from ``st.booleans()`` independently,
# so 50% of inputs would carry a closed gate even when no adversarial
# perturbation was requested. The mixer tests need finer control over
# whether the gate is open or closed.


def _build_channel_inputs(
    *,
    perturbation_stability_lower_bound: float = 0.5,
    ambiguity: float = 0.1,
    degeneracy_penalty: float = 0.1,
    support_coverage: float = 0.5,
    recency_decay: float = 0.8,
    calibration_lower_bound: float = 0.5,
    mixing_cap: float = 1.0,
    scheduled_cap: float = 0.5,
    fresh_noise_floor: float = 0.0,
    delta_cap_up: float = 0.5,
    delta_cap_down: float = 0.5,
    tail_admissibility: bool = True,
    complement_excluded: bool = False,
    horizon_coverage_proven: bool = True,
    finite_prefix_only: bool = True,
    proxy_only_evidence: bool = False,
    envelope_hash_present: bool = True,
):
    """Build a :class:`ChannelRuleInputs` whose every field is in-domain.

    Defaults correspond to the "gate-open" happy path; the optional
    keyword arguments expose the failure-mode toggles so the test
    bodies can build closed-gate inputs without going through the
    molecule bundle / evidence constructors.
    """
    # Lazy imports: the contracts / molecule import cycle is broken
    # by importing channels first, then bundles.
    from adaptive_reflow.contracts import (
        ArtifactHash,
        BundleId,
        ChannelName,
        ChannelRuleInputs,
        ChannelTransferEvidence,
        FactorValue,
        ProvenanceChain,
        RoundResultBundle,
        RunId,
        SampleId,
        TraceDigest,
        hash_artifact,
        hash_trace_digest,
        make_default_phase_state,
    )
    from adaptive_reflow.molecular.channels import MOLECULE_CHANNELS

    channel = ChannelName(MOLECULE_CHANNELS[0])
    bundle_id = "bundle-prop"
    trace = TraceDigest(
        hash_trace_digest(
            BundleId(bundle_id), 0, 1, RunId("run-prop"), SampleId("sample-prop")
        )
    )
    bundle = RoundResultBundle(
        bundle_id=BundleId(bundle_id),
        source_round=0,
        round_count=1,
        run_id=RunId("run-prop"),
        sample_id=SampleId("sample-prop"),
        trace_digest=trace,
        condition_digest=TraceDigest(""),
        feedback_mode="inference_external_diagnostic",
        calibration_artifact_hash=ArtifactHash("calibration-prop"),
        state_lock_is_detached=True,
        update_scope="ode_restart_distribution_only",
        coordinate_channel={"source_round": 0, "channel": "coordinate"},
        charge_channel={"source_round": 0, "channel": "charge"},
        raw_pair_channel={"source_round": 0, "channel": "raw_pair"},
        projected_pair_channel={"source_round": 0, "channel": "projected_pair"},
        materialization_evidence=None,
        evaluator_provenance=None,
        feedback_evidence=None,
        shape_spec={},
        frame_spec={},
        provenance=ProvenanceChain(("test_provenance",)),
        created_at_round=0,
        revoked=False,
    )
    evidence = ChannelTransferEvidence(
        bundle_id=bundle.bundle_id,
        channel=channel,
        materialization_pass=True,
        geometry_pass=True,
        perturbation_stability_lower_bound=perturbation_stability_lower_bound,
        condition_sensitivity_observable_pass=True,
        external_metric_uncertainty=0.1,
        proxy_only_evidence=proxy_only_evidence,
        ambiguity=ambiguity,
        degeneracy_penalty=degeneracy_penalty,
        support_coverage=support_coverage,
        recency_decay=recency_decay,
        calibration_lower_bound=calibration_lower_bound,
        raw_score=0.5,
        bounded_score=0.5,
        provenance=ProvenanceChain(("test_evidence",)),
        validation_errors=(),
    )
    phase = make_default_phase_state(
        outer_cycle_id=0,
        round_in_cycle=0,
        horizon_coverage_proven=bool(horizon_coverage_proven),
    )
    envelope_hash = (
        ArtifactHash(hash_artifact({"envelope": "prop"})) if envelope_hash_present else None
    )
    return ChannelRuleInputs(
        bundle=bundle,
        evidence=evidence,
        phase_state=phase,
        scheduled_cap=scheduled_cap,
        mixing_cap=mixing_cap,
        fresh_noise_floor=fresh_noise_floor,
        delta_cap_up=delta_cap_up,
        delta_cap_down=delta_cap_down,
        tail_admissibility=bool(tail_admissibility),
        complement_excluded=bool(complement_excluded),
        frozen_envelope_manifest_hash=envelope_hash,
        finite_prefix_only=bool(finite_prefix_only),
        calibration_lower_bound=calibration_lower_bound,
        perturbation_stability_lower_bound=perturbation_stability_lower_bound,
        support_coverage=support_coverage,
        ambiguity=ambiguity,
        degeneracy_penalty=degeneracy_penalty,
        recency_decay=recency_decay,
        horizon_coverage_proven=bool(horizon_coverage_proven),
        selected_bundle_id=bundle.bundle_id,
    )


# ---------------------------------------------------------------------------
# 14. bounded_target_fraction in [0, 1]
# ---------------------------------------------------------------------------


@given(
    mixing_cap=unit_floats,
    scheduled_cap=unit_floats,
    fresh_noise_floor=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    delta_cap_up=unit_floats,
    delta_cap_down=unit_floats,
    calibration_lower_bound=unit_floats,
    perturbation_stability_lower_bound=unit_floats,
    support_coverage=unit_floats,
    ambiguity=unit_floats,
    degeneracy_penalty=unit_floats,
    recency_decay=unit_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_mixer_bounded_target_fraction_in_unit_interval(
    mixing_cap: float,
    scheduled_cap: float,
    fresh_noise_floor: float,
    delta_cap_up: float,
    delta_cap_down: float,
    calibration_lower_bound: float,
    perturbation_stability_lower_bound: float,
    support_coverage: float,
    ambiguity: float,
    degeneracy_penalty: float,
    recency_decay: float,
) -> None:
    """The mixer's ``bounded_target_fraction`` is always in ``[0, 1]``."""
    inputs = _build_channel_inputs(
        mixing_cap=mixing_cap,
        scheduled_cap=scheduled_cap,
        fresh_noise_floor=fresh_noise_floor,
        delta_cap_up=delta_cap_up,
        delta_cap_down=delta_cap_down,
        calibration_lower_bound=calibration_lower_bound,
        perturbation_stability_lower_bound=perturbation_stability_lower_bound,
        support_coverage=support_coverage,
        ambiguity=ambiguity,
        degeneracy_penalty=degeneracy_penalty,
        recency_decay=recency_decay,
    )
    outputs = compute_channel_decision(inputs)
    bounded = float(outputs.decision.bounded_target_fraction)
    assert_unit_interval(bounded, name="bounded_target_fraction")


# ---------------------------------------------------------------------------
# 15. alpha + beta == 1.0 when the gate is open
# ---------------------------------------------------------------------------


@given(
    mixing_cap=unit_floats,
    scheduled_cap=unit_floats,
    delta_cap_up=unit_floats,
    delta_cap_down=unit_floats,
    calibration_lower_bound=unit_floats,
    perturbation_stability_lower_bound=unit_floats,
    support_coverage=unit_floats,
    ambiguity=unit_floats,
    degeneracy_penalty=unit_floats,
    recency_decay=unit_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_mixer_alpha_beta_sum_is_one_when_gate_open(
    mixing_cap: float,
    scheduled_cap: float,
    delta_cap_up: float,
    delta_cap_down: float,
    calibration_lower_bound: float,
    perturbation_stability_lower_bound: float,
    support_coverage: float,
    ambiguity: float,
    degeneracy_penalty: float,
    recency_decay: float,
) -> None:
    """In the gate-open path the mixer enforces ``alpha + beta == 1.0``.

    This is a label-only identity (the mixer does not assume any
    variance equality). The test pins it as a structural invariant.
    """
    inputs = _build_channel_inputs(
        mixing_cap=mixing_cap,
        scheduled_cap=scheduled_cap,
        delta_cap_up=delta_cap_up,
        delta_cap_down=delta_cap_down,
        calibration_lower_bound=calibration_lower_bound,
        perturbation_stability_lower_bound=perturbation_stability_lower_bound,
        support_coverage=support_coverage,
        ambiguity=ambiguity,
        degeneracy_penalty=degeneracy_penalty,
        recency_decay=recency_decay,
        # Default: gate-open values for the structural toggles.
        tail_admissibility=True,
        complement_excluded=False,
        horizon_coverage_proven=True,
        finite_prefix_only=True,
        envelope_hash_present=True,
    )
    outputs = compute_channel_decision(inputs)
    decision = outputs.decision
    # Gate must actually be open — the inputs are constructed in the
    # happy path. If the gate happens to be closed the sample is
    # discarded (the structural alpha+beta=1 identity only applies on
    # the open gate).
    assume(decision.gate is True)
    alpha = float(decision.alpha)
    beta = float(decision.beta)
    assert alpha + beta == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 16. Gate-open monotonicity in four families
# ---------------------------------------------------------------------------


FAMILIES = ("stability_up", "uncertainty_up", "support_down", "age_up")


@given(
    family=st.sampled_from(FAMILIES),
    calibration_lower_bound=unit_floats,
    perturbation_stability_lower_bound=unit_floats,
    support_coverage=unit_floats,
    ambiguity=unit_floats,
    degeneracy_penalty=unit_floats,
    recency_decay=unit_floats,
    delta_cap_up=unit_floats,
    delta_cap_down=unit_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_mixer_open_gate_monotone_in_family(
    family: str,
    calibration_lower_bound: float,
    perturbation_stability_lower_bound: float,
    support_coverage: float,
    ambiguity: float,
    degeneracy_penalty: float,
    recency_decay: float,
    delta_cap_up: float,
    delta_cap_down: float,
) -> None:
    """Gate-open monotonicity must hold for all four canonical families."""
    baseline = _build_channel_inputs(
        calibration_lower_bound=calibration_lower_bound,
        perturbation_stability_lower_bound=perturbation_stability_lower_bound,
        support_coverage=support_coverage,
        ambiguity=ambiguity,
        degeneracy_penalty=degeneracy_penalty,
        recency_decay=recency_decay,
        delta_cap_up=delta_cap_up,
        delta_cap_down=delta_cap_down,
    )
    if family == "stability_up":
        perturbed = _build_channel_inputs(
            calibration_lower_bound=min(1.0, calibration_lower_bound + 0.1),
            perturbation_stability_lower_bound=perturbation_stability_lower_bound,
            support_coverage=support_coverage,
            ambiguity=ambiguity,
            degeneracy_penalty=degeneracy_penalty,
            recency_decay=recency_decay,
            delta_cap_up=delta_cap_up,
            delta_cap_down=delta_cap_down,
        )
    elif family == "uncertainty_up":
        perturbed = _build_channel_inputs(
            calibration_lower_bound=calibration_lower_bound,
            perturbation_stability_lower_bound=perturbation_stability_lower_bound,
            support_coverage=support_coverage,
            ambiguity=min(1.0, ambiguity + 0.1),
            degeneracy_penalty=degeneracy_penalty,
            recency_decay=recency_decay,
            delta_cap_up=delta_cap_up,
            delta_cap_down=delta_cap_down,
        )
    elif family == "support_down":
        perturbed = _build_channel_inputs(
            calibration_lower_bound=calibration_lower_bound,
            perturbation_stability_lower_bound=perturbation_stability_lower_bound,
            support_coverage=max(0.0, support_coverage - 0.1),
            ambiguity=ambiguity,
            degeneracy_penalty=degeneracy_penalty,
            recency_decay=recency_decay,
            delta_cap_up=delta_cap_up,
            delta_cap_down=delta_cap_down,
        )
    elif family == "age_up":
        perturbed = _build_channel_inputs(
            calibration_lower_bound=calibration_lower_bound,
            perturbation_stability_lower_bound=perturbation_stability_lower_bound,
            support_coverage=support_coverage,
            ambiguity=ambiguity,
            degeneracy_penalty=degeneracy_penalty,
            recency_decay=max(0.0, recency_decay - 0.1),
            delta_cap_up=delta_cap_up,
            delta_cap_down=delta_cap_down,
        )
    else:  # pragma: no cover - guarded by sampled_from
        raise AssertionError(f"unknown family: {family!r}")

    base_dec = compute_channel_decision(baseline).decision
    pert_dec = compute_channel_decision(perturbed).decision
    # Only assert monotonicity when both gates are open; otherwise the
    # closed-gate collapse (alpha=1, beta=0) trivially satisfies the
    # direction but does not exercise the open-gate monotonicity.
    assume(base_dec.gate is True)
    assume(pert_dec.gate is True)
    assert check_monotonicity_property(family, baseline, perturbed) is True, (
        f"monotonicity violated for family={family!r}"
    )


# ---------------------------------------------------------------------------
# 17. Closed-gate collapse: any blocker -> beta=0, alpha=1, evidence_score=0
# ---------------------------------------------------------------------------


@given(
    closed_kind=st.sampled_from(
        [
            "tail_inadmissible",
            "complement_excluded",
            "horizon_unproven",
            "not_finite_prefix",
        ]
    ),
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_mixer_closed_gate_collapses_to_zero(closed_kind: str) -> None:
    """When the gate is closed the mixer emits the canonical collapse."""
    kwargs = dict(
        tail_admissibility=True,
        complement_excluded=False,
        horizon_coverage_proven=True,
        finite_prefix_only=True,
        envelope_hash_present=True,
    )
    if closed_kind == "tail_inadmissible":
        kwargs["tail_admissibility"] = False
    elif closed_kind == "complement_excluded":
        kwargs["complement_excluded"] = True
    elif closed_kind == "horizon_unproven":
        kwargs["horizon_coverage_proven"] = False
    elif closed_kind == "not_finite_prefix":
        kwargs["finite_prefix_only"] = False
    inputs = _build_channel_inputs(**kwargs)
    outputs = compute_channel_decision(inputs)
    decision = outputs.decision
    assert decision.gate is False, (
        f"expected closed gate for {closed_kind!r} but got open; "
        f"blocker_codes={decision.blocker_codes!r}"
    )
    # Canonical closed-gate collapse per DTB-R2.
    assert float(decision.beta) == 0.0
    assert float(decision.alpha) == 1.0
    assert float(decision.evidence_score) == 0.0
    assert float(decision.bounded_target_fraction) == 0.0
    # The audit reason encodes the blockers, separated by ';'.
    assert decision.audit_reason != "ok"
    assert decision.blocker_codes
    for code in decision.blocker_codes:
        assert isinstance(code, str)
        assert code != ""


# ---------------------------------------------------------------------------
# 18. audit_reason deterministic across repeated calls
# ---------------------------------------------------------------------------


@given(
    mixing_cap=unit_floats,
    scheduled_cap=unit_floats,
    delta_cap_up=unit_floats,
    delta_cap_down=unit_floats,
    calibration_lower_bound=unit_floats,
    perturbation_stability_lower_bound=unit_floats,
    support_coverage=unit_floats,
    ambiguity=unit_floats,
    degeneracy_penalty=unit_floats,
    recency_decay=unit_floats,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_mixer_audit_reason_deterministic(
    mixing_cap: float,
    scheduled_cap: float,
    delta_cap_up: float,
    delta_cap_down: float,
    calibration_lower_bound: float,
    perturbation_stability_lower_bound: float,
    support_coverage: float,
    ambiguity: float,
    degeneracy_penalty: float,
    recency_decay: float,
) -> None:
    """Calling ``compute_channel_decision`` twice yields identical outputs."""
    inputs = _build_channel_inputs(
        mixing_cap=mixing_cap,
        scheduled_cap=scheduled_cap,
        delta_cap_up=delta_cap_up,
        delta_cap_down=delta_cap_down,
        calibration_lower_bound=calibration_lower_bound,
        perturbation_stability_lower_bound=perturbation_stability_lower_bound,
        support_coverage=support_coverage,
        ambiguity=ambiguity,
        degeneracy_penalty=degeneracy_penalty,
        recency_decay=recency_decay,
    )
    outputs_a = compute_channel_decision(inputs)
    outputs_b = compute_channel_decision(inputs)
    reason_a = outputs_a.decision.audit_reason
    reason_b = outputs_b.decision.audit_reason
    assert reason_a == reason_b
    # Full decision tuple is byte-identical.
    assert outputs_a.decision == outputs_b.decision
    assert_idempotent(compute_channel_decision, inputs)
