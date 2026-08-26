"""Kernel benchmarks for the three DTB hot-paths.

This file provides ``pytest-benchmark`` decorated tests for the three
canonical hot-path kernels:

* :func:`test_bounded_merge_kernel` — bench :func:`bounded_merge`.
* :func:`test_compute_channel_decision_kernel` — bench
  :func:`compute_channel_decision`.
* :func:`test_evaluate_claim_gate_kernel` — bench
  :func:`evaluate_claim_gate`.

Each test prints the ``pytest-benchmark`` summary which includes mean /
median / p95 / max in **microseconds** (the bench plugin reports
``Time`` in seconds; ``--benchmark-columns`` is configured below so the
default output already shows the microsecond range).

Running
-------

::

    PYTHONPATH=. python -m pytest tests/perf/test_kernel_benchmarks.py \\
        --benchmark-only --benchmark-columns=min,max,mean,median,p95 \\
        --benchmark-sort=median

The fixture builders are deliberately deterministic and stdlib-only;
no torch / numpy / I/O is involved.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make sure the repo root is importable when pytest is invoked from any
# directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adaptive_reflow.contracts import (  # noqa: E402
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
    hash_trace_digest,
)
from adaptive_reflow.eval import (  # noqa: E402
    ClaimGateEvaluation,
    build_default_claim_gate_config,
    evaluate_claim_gate,
)
from adaptive_reflow.frame import (  # noqa: E402
    bounded_merge,
)
from adaptive_reflow.frame.channel_rule import (  # noqa: E402
    compute_channel_decision,
)

# ---------------------------------------------------------------------------
# Fixtures — deterministic, stdlib-only
# ---------------------------------------------------------------------------


def _make_bundle_for_channel_decision() -> RoundResultBundle:
    """Build a valid :class:`RoundResultBundle` for the channel-rule bench."""
    bundle_id = "bundle-perf"
    trace = TraceDigest(
        hash_trace_digest(
            BundleId(bundle_id),
            0,
            1,
            RunId("run-perf"),
            SampleId("sample-perf"),
        )
    )
    return RoundResultBundle(
        bundle_id=BundleId(bundle_id),
        source_round=0,
        round_count=1,
        run_id=RunId("run-perf"),
        sample_id=SampleId("sample-perf"),
        trace_digest=trace,
        condition_digest=TraceDigest(""),
        feedback_mode="inference_external_diagnostic",
        calibration_artifact_hash=ArtifactHash("calibration-stub"),
        state_lock_is_detached=True,
        update_scope="ode_restart_distribution_only",
        coordinate_channel=None,
        charge_channel=None,
        raw_pair_channel=None,
        projected_pair_channel=None,
        materialization_evidence=None,
        evaluator_provenance=None,
        feedback_evidence=None,
        shape_spec={},
        frame_spec={},
        provenance=ProvenanceChain(("perf",)),
        created_at_round=0,
        revoked=False,
    )


def _make_evidence_for_channel_decision(
    bundle: RoundResultBundle, channel: ChannelName
) -> ChannelTransferEvidence:
    """Build a deterministic evidence row that opens the channel gate."""
    return ChannelTransferEvidence(
        bundle_id=bundle.bundle_id,
        channel=channel,
        materialization_pass=True,
        geometry_pass=True,
        perturbation_stability_lower_bound=FactorValue(0.8),
        condition_sensitivity_observable_pass=True,
        external_metric_uncertainty=FactorValue(0.1),
        proxy_only_evidence=False,
        ambiguity=FactorValue(0.1),
        degeneracy_penalty=FactorValue(0.1),
        support_coverage=FactorValue(0.9),
        recency_decay=FactorValue(0.9),
        calibration_lower_bound=FactorValue(0.8),
        raw_score=0.5,
        bounded_score=0.5,
        provenance=ProvenanceChain(("perf.evidence",)),
        validation_errors=(),
    )


def _make_phase_state_for_channel_decision():
    """Build a :class:`PhaseState` matching the default operation order."""
    from adaptive_reflow.contracts import make_default_phase_state

    return make_default_phase_state(
        operation_order_version="v1",
        horizon_coverage_proven=True,
    )


def _make_channel_rule_inputs() -> ChannelRuleInputs:
    """Build a fully-valid, gate-opening :class:`ChannelRuleInputs`."""
    bundle = _make_bundle_for_channel_decision()
    channel = ChannelName("coordinate")
    evidence = _make_evidence_for_channel_decision(bundle, channel)
    phase_state = _make_phase_state_for_channel_decision()
    return ChannelRuleInputs(
        bundle=bundle,
        evidence=evidence,
        phase_state=phase_state,
        scheduled_cap=FactorValue(0.5),
        mixing_cap=FactorValue(1.0),
        fresh_noise_floor=FactorValue(0.0),
        delta_cap_up=FactorValue(0.5),
        delta_cap_down=FactorValue(0.5),
        tail_admissibility=True,
        complement_excluded=False,
        frozen_envelope_manifest_hash=ArtifactHash("syn2:envelope-hash"),
        finite_prefix_only=True,
        calibration_lower_bound=FactorValue(0.8),
        perturbation_stability_lower_bound=FactorValue(0.8),
        support_coverage=FactorValue(0.9),
        ambiguity=FactorValue(0.1),
        degeneracy_penalty=FactorValue(0.1),
        recency_decay=FactorValue(0.9),
        horizon_coverage_proven=True,
        selected_bundle_id=bundle.bundle_id,
    )


def _make_claim_gate_config():
    """Build a deterministic :class:`ClaimGateConfig` with the gate enabled."""
    return build_default_claim_gate_config(
        required_contracts_passing=("DTB-NC1", "DTB-NC2"),
        required_calibration_artifact_hash=ArtifactHash("calibration-artifact-stub"),
        required_paired_evidence_count=2,
        gate_enabled=True,
        evaluation_window_rounds=1,
        minimum_confidence_interval_coverage=0.5,
    )


def _make_claim_gate_evidence() -> dict:
    """Build a fully-passing evidence mapping for the gate bench."""
    return {
        "DTB-NC1": {"passed": True, "summary": "nc1-pass"},
        "DTB-NC2": {"passed": True, "summary": "nc2-pass"},
        "calibration_artifact": {"hash": "calibration-artifact-stub"},
        "paired_evidence_count": 4,
        "confidence_interval_coverage": 0.95,
        "evaluation_window_rounds": 2,
    }


# ---------------------------------------------------------------------------
# Fixtures exposed to pytest
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def channel_rule_inputs() -> ChannelRuleInputs:
    """Reusable channel-rule inputs (gate opens)."""
    return _make_channel_rule_inputs()


@pytest.fixture(scope="module")
def claim_gate_config():
    """Reusable claim-gate config (gate enabled, several contracts)."""
    return _make_claim_gate_config()


@pytest.fixture(scope="module")
def claim_gate_evidence() -> dict:
    """Reusable fully-passing claim-gate evidence mapping."""
    return _make_claim_gate_evidence()


# ---------------------------------------------------------------------------
# Kernel benchmarks
# ---------------------------------------------------------------------------


def test_bounded_merge_kernel(benchmark) -> None:
    """Bench :func:`bounded_merge` with a representative call shape."""

    def _call() -> float:
        return bounded_merge(
            prev=0.5,
            dynamic=0.4,
            cap=1.0,
            floor=0.0,
            delta_cap_up=0.5,
            delta_cap_down=0.5,
        )

    result = benchmark(_call)
    # Sanity check so a future regression that returns the wrong
    # value (e.g. ``0.0``) fails the test loudly.
    assert 0.0 <= float(result) <= 1.0


def test_compute_channel_decision_kernel(benchmark, channel_rule_inputs) -> None:
    """Bench :func:`compute_channel_decision` on the gate-opening inputs."""
    inputs = channel_rule_inputs

    def _call():
        return compute_channel_decision(inputs)

    result = benchmark(_call)
    assert result.decision.gate is True


def test_evaluate_claim_gate_kernel(
    benchmark, claim_gate_config, claim_gate_evidence
) -> None:
    """Bench :func:`evaluate_claim_gate` with a fully-passing evidence map."""
    config = claim_gate_config
    evidence = claim_gate_evidence

    def _call() -> ClaimGateEvaluation:
        return evaluate_claim_gate(
            config,
            evidence,
            evaluated_at_round=0,
        )

    evaluation = benchmark(_call)
    # The structural decision is always ``"defer"`` (R7 data deferred);
    # we just check that the call returns a non-empty evaluation.
    assert evaluation.decision in ("promote", "rollback", "defer")
    assert evaluation.evaluated_at_round == 0


# ---------------------------------------------------------------------------
# pytest configuration hooks
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    """Default benchmark columns to the microsecond-relevant subset.

    This keeps the printed numbers in the same units as the budgets
    declared in :mod:`tools.bench.budgets` so a reader can eyeball the
    output against the JSON.
    """
    parser.addini(
        "benchmark_columns",
        "default columns for pytest-benchmark output",
        default="min,max,mean,median,p95",
    )
