"""End-to-end bench runner — 200 ``evaluate_bundle`` rounds.

This is a hand-rolled, stdlib-only harness built around
:func:`time.perf_counter_ns`. It wires the v2
:class:`SyntheticMechanismAdapter` (see
:mod:`tests.perf.synthetic_driver`) to the
:class:`AdaptiveReflowPolicyOrchestrator` and times exactly ``N=200``
consecutive ``evaluate_bundle`` calls. The harness is intentionally
simple:

* no threading, no async, no warm-up tricks beyond the round-1 call
  (which is included in the timing so the budget check sees the
  cold-cache cost);
* no pytest, no pytest-benchmark — this script is meant to be invoked
  by CI from a plain shell command;
* results are emitted as JSON to ``docs/benchmarks.json`` (overwriting
  any previous snapshot) and the same JSON is printed to stdout.

JSON schema
-----------

The emitted JSON has the shape::

    {
      "schema": "flowa.benchmarks/v1",
      "captured_at": "2026-08-27T00:00:00Z",     # ISO 8601 UTC
      "rounds": 200,
      "metrics": {
        "engine_round_loop_us_p95": 1234,        # p95 per-call cost in microseconds
        "engine_round_loop_us_median": 1100,
        "engine_round_loop_us_max": 2500,
        "engine_round_loop_us_total": 220000
      },
      "raw_samples_ns": [1100000, 1110000, ...]  # N integers; for CI tools that want to recompute
    }

Command-line
------------

::

    PYTHONPATH=. ./.venv/Scripts/python.exe tools/bench/runner.py

Optional arguments
------------------

* ``--rounds N`` — override the default ``N=200``.
* ``--output PATH`` — override the default ``docs/benchmarks.json`` path.
* ``--warmup N`` — discard the first ``N`` samples from the reported
  statistics (default ``0``).

Exit status is ``0`` on success and non-zero only on internal errors;
regression detection is the job of :mod:`tools.bench.check_budgets`.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import statistics
import sys
import time
from pathlib import Path

# Repo root must be on sys.path so ``adaptive_reflow`` resolves when the
# script is invoked directly from the repo root. The script lives at
# ``tools/bench/runner.py`` so ``parents[2]`` is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adaptive_reflow.contracts import (  # noqa: E402  (after sys.path tweak)
    ArtifactHash,
    BundleId,
    ChannelName,
    ChannelRuleInputs,
    ChannelTransferEvidence,
    CosineScheduleConfig,
    EnvelopeLayer,
    FactorValue,
    FrozenEnvelopeManifest,
    ProvenanceChain,
    RoundResultBundle,
    RunId,
    SampleId,
    TraceDigest,
    hash_artifact,
    hash_trace_digest,
    make_default_phase_state,
)
from adaptive_reflow.eval import (  # noqa: E402
    build_default_claim_gate_config,
    evaluate_claim_gate,
)
from adaptive_reflow.frame import (  # noqa: E402
    AdaptiveReflowPolicyOrchestrator,
    bounded_merge,
)
from adaptive_reflow.frame.channel_rule import (  # noqa: E402
    compute_channel_decision,
)
from adaptive_reflow.schedule import CosineScheduleSampler  # noqa: E402
from tests.perf.synthetic_driver import (  # noqa: E402
    SUPPORTED_CHANNELS,
    SYNTHETIC_CHANNEL,
    SyntheticMechanismAdapter,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

SCHEMA_NAME: str = "flowa.benchmarks/v1"
DEFAULT_ROUNDS: int = 200
DEFAULT_OUTPUT: Path = _REPO_ROOT / "docs" / "benchmarks.json"
DEFAULT_WARMUP: int = 0

# The metric keys we emit. Centralised so the budget checker and the
# runner never drift on naming.
METRIC_KEYS: tuple[str, ...] = (
    "engine_round_loop_us_p95",
    "engine_round_loop_us_median",
    "engine_round_loop_us_max",
    "engine_round_loop_us_total",
)


# ---------------------------------------------------------------------------
# Helpers — fixtures
# ---------------------------------------------------------------------------


def _make_kernel_evidence(bundle: RoundResultBundle) -> ChannelTransferEvidence:
    """Build a deterministic evidence row that opens the channel gate."""
    return ChannelTransferEvidence(
        bundle_id=bundle.bundle_id,
        channel=ChannelName(SYNTHETIC_CHANNEL),
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
        provenance=ProvenanceChain(("bench.runner.evidence",)),
        validation_errors=(),
    )


def _make_kernel_channel_rule_inputs() -> ChannelRuleInputs:
    """Build a fully-valid, gate-opening :class:`ChannelRuleInputs`."""
    bundle = _make_bundle(source_round=0, sample_id="bench-kernel")
    evidence = _make_kernel_evidence(bundle)
    phase_state = make_default_phase_state(
        operation_order_version="v1",
        horizon_coverage_proven=True,
    )
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


def _make_kernel_claim_gate_config():
    """Build a deterministic :class:`ClaimGateConfig` for the kernel bench."""
    return build_default_claim_gate_config(
        required_contracts_passing=("DTB-NC1", "DTB-NC2"),
        required_calibration_artifact_hash=ArtifactHash("calibration-artifact-stub"),
        required_paired_evidence_count=2,
        gate_enabled=True,
        evaluation_window_rounds=1,
        minimum_confidence_interval_coverage=0.5,
    )


def _make_kernel_claim_gate_evidence() -> dict:
    """Build a fully-passing evidence mapping for the gate bench."""
    return {
        "DTB-NC1": {"passed": True, "summary": "nc1-pass"},
        "DTB-NC2": {"passed": True, "summary": "nc2-pass"},
        "calibration_artifact": {"hash": "calibration-artifact-stub"},
        "paired_evidence_count": 4,
        "confidence_interval_coverage": 0.95,
        "evaluation_window_rounds": 2,
    }


def _make_envelope_manifest() -> FrozenEnvelopeManifest:
    """Build a one-layer, very-loose envelope so classification passes."""
    layer = EnvelopeLayer(
        layer_index=0,
        label="synthetic-loose",
        coordinate_extent_rms_max=1.0e9,
        coordinate_extent_rms_source_stats_hash=ArtifactHash(""),
        pocket_distance_max=1.0e9,
        pocket_contact_support_min=0.0,
        atom_count_min=0,
        atom_count_max=1_000_000,
        graph_complexity_max=1_000_000,
        sanitization_required=False,
        valence_rules_hash=ArtifactHash(""),
        pair_entropy_min=0.0,
        pair_entropy_source_stats_hash=ArtifactHash(""),
        projection_loss_max=1.0,
        internal_geometry_pass_required=False,
        evaluator_provenance_required=False,
        source_stats_hash=ArtifactHash(""),
        threshold_digest=ArtifactHash(""),
        layer_hash=ArtifactHash(""),
    )
    payload = {
        "manifest_id": "manifest-synthetic",
        "layers": [
            {f.name: getattr(layer_, f.name) for f in layer.__dataclass_fields__.values()}
            for layer_ in (layer,)
        ],
        "finite_prefix_only": True,
        "empirical_only": True,
        "tail_selection_certified": False,
    }
    digest = hash_artifact(payload)
    return FrozenEnvelopeManifest(
        manifest_id="manifest-synthetic",
        run_id=RunId("run-synthetic"),
        sample_id=SampleId("sample-synthetic"),
        target_pocket_hash=ArtifactHash(""),
        config_hash=ArtifactHash(""),
        created_at_round=0,
        layers=(layer,),
        empirical_only=True,
        finite_prefix_only=True,
        tail_selection_certified=False,
        manifest_hash=digest,
    )


def _make_schedule_config() -> CosineScheduleConfig:
    """Build a constant, deterministic schedule config."""
    return CosineScheduleConfig(
        schedule_family="cosine_no_restart",
        cycle_length=4,
        n_min=FactorValue(0.0),
        n_max=FactorValue(0.5),
        per_channel_caps={
            ChannelName(SYNTHETIC_CHANNEL): FactorValue(1.0),
        },
        fresh_noise_floor_by_channel={
            ChannelName(SYNTHETIC_CHANNEL): FactorValue(0.0),
        },
        symmetric_delta_caps_by_channel={
            ChannelName(SYNTHETIC_CHANNEL): FactorValue(0.5),
        },
        restart_triggers_allowed=(),
        config_hash=ArtifactHash(""),
        frozen_before_evaluation=True,
    )


def _make_bundle(*, source_round: int, sample_id: str) -> RoundResultBundle:
    """Build a minimal, validating :class:`RoundResultBundle`."""
    bundle_id = f"bundle-{sample_id}-{source_round}"
    trace = TraceDigest(
        hash_trace_digest(
            BundleId(bundle_id),
            source_round,
            1,
            RunId("run-synthetic"),
            SampleId(sample_id),
        )
    )
    return RoundResultBundle(
        bundle_id=BundleId(bundle_id),
        source_round=source_round,
        round_count=1,
        run_id=RunId("run-synthetic"),
        sample_id=SampleId(sample_id),
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
        provenance=ProvenanceChain(("synthetic.v2",)),
        created_at_round=source_round,
        revoked=False,
    )


def _make_evidence(bundle: RoundResultBundle) -> ChannelTransferEvidence:
    """Build a deterministic :class:`ChannelTransferEvidence` row."""
    return ChannelTransferEvidence(
        bundle_id=bundle.bundle_id,
        channel=ChannelName(SYNTHETIC_CHANNEL),
        materialization_pass=True,
        geometry_pass=True,
        perturbation_stability_lower_bound=FactorValue(0.5),
        condition_sensitivity_observable_pass=True,
        external_metric_uncertainty=FactorValue(0.1),
        proxy_only_evidence=False,
        ambiguity=FactorValue(0.1),
        degeneracy_penalty=FactorValue(0.1),
        support_coverage=FactorValue(0.5),
        recency_decay=FactorValue(0.8),
        calibration_lower_bound=FactorValue(0.5),
        raw_score=0.5,
        bounded_score=0.5,
        provenance=ProvenanceChain(("synthetic.v2.evidence",)),
        validation_errors=(),
    )


def _build_orchestrator() -> AdaptiveReflowPolicyOrchestrator:
    """Build a fresh orchestrator wired with the synthetic fixtures."""
    envelope = _make_envelope_manifest()
    schedule = _make_schedule_config()
    return AdaptiveReflowPolicyOrchestrator(
        envelope_manifest=envelope,
        schedule_config=schedule,
        schedule_sampler=CosineScheduleSampler(schedule),
    )


# ---------------------------------------------------------------------------
# Helpers — statistics
# ---------------------------------------------------------------------------


def _percentile(samples: list[int], *, pct: float) -> int:
    """Return the ``pct``-th percentile of ``samples`` as a plain int.

    Uses the standard nearest-rank convention. ``pct`` is in ``[0, 100]``.
    """
    if not samples:
        return 0
    if pct <= 0:
        return int(min(samples))
    if pct >= 100:
        return int(max(samples))
    ordered = sorted(samples)
    rank = max(0, min(len(ordered) - 1, int(round(pct / 100.0 * (len(ordered) - 1)))))
    return int(ordered[rank])


def _ns_to_us(ns: int) -> int:
    """Convert nanoseconds to whole-microseconds (floor)."""
    return int(ns) // 1000


def _time_callable(callable_obj, *, iterations: int) -> list[int]:
    """Run ``callable_obj()`` ``iterations`` times and return the per-call ns samples.

    The callable is invoked once outside the timed loop to amortise any
    lazy-import / one-time cost, then ``iterations`` timed invocations
    are recorded. The benchmark uses :func:`time.perf_counter_ns`
    directly because the goal is sub-microsecond precision.
    """
    if int(iterations) <= 0:
        raise ValueError(f"iterations must be > 0, got {iterations}")
    # Warm-up call so JIT / cache effects are uniform.
    callable_obj()
    samples_ns: list[int] = []
    for _ in range(int(iterations)):
        t0 = time.perf_counter_ns()
        callable_obj()
        t1 = time.perf_counter_ns()
        samples_ns.append(int(t1 - t0))
    return samples_ns


# ---------------------------------------------------------------------------
# Main bench loop
# ---------------------------------------------------------------------------


KERNEL_ITERATIONS: int = 5_000


def _kernel_callables() -> dict[str, object]:
    """Return a fresh mapping of kernel name -> zero-arg callable."""
    channel_rule_inputs = _make_kernel_channel_rule_inputs()
    claim_gate_config = _make_kernel_claim_gate_config()
    claim_gate_evidence = _make_kernel_claim_gate_evidence()
    return {
        "bounded_merge": lambda: bounded_merge(
            prev=0.5,
            dynamic=0.4,
            cap=1.0,
            floor=0.0,
            delta_cap_up=0.5,
            delta_cap_down=0.5,
        ),
        "compute_channel_decision": lambda: compute_channel_decision(
            channel_rule_inputs
        ),
        "evaluate_claim_gate": lambda: evaluate_claim_gate(
            claim_gate_config,
            claim_gate_evidence,
            evaluated_at_round=0,
        ),
    }


def run_benchmark_round(
    *,
    rounds: int = DEFAULT_ROUNDS,
    kernel_iterations: int = KERNEL_ITERATIONS,
) -> tuple[dict[str, list[int]], dict[str, int]]:
    """Time ``rounds`` ``evaluate_bundle`` calls and the three kernels.

    Returns ``(samples_by_metric, metrics)`` where ``samples_by_metric``
    maps a metric name to its raw nanosecond samples and ``metrics``
    maps the same metric name to its p95 in whole-microseconds (plus
    median / max / total helpers for ``engine_round_loop``).
    """
    if int(rounds) <= 0:
        raise ValueError(f"rounds must be > 0, got {rounds}")
    if int(kernel_iterations) <= 0:
        raise ValueError(
            f"kernel_iterations must be > 0, got {kernel_iterations}"
        )

    # ---- engine round loop ---------------------------------------------
    orchestrator = _build_orchestrator()
    evidence_by_channel = {
        ChannelName(SYNTHETIC_CHANNEL): _make_evidence(
            _make_bundle(source_round=0, sample_id="bench-0")
        )
    }
    bundles = [
        _make_bundle(source_round=i, sample_id=f"bench-{i}")
        for i in range(int(rounds))
    ]
    round_samples_ns: list[int] = []
    for bundle in bundles:
        t0 = time.perf_counter_ns()
        orchestrator.evaluate_bundle(bundle, evidence_by_channel)
        t1 = time.perf_counter_ns()
        round_samples_ns.append(int(t1 - t0))

    # ---- kernel benchmarks ---------------------------------------------
    kernel_callables = _kernel_callables()
    kernel_samples_ns: dict[str, list[int]] = {
        name: _time_callable(callable_obj, iterations=int(kernel_iterations))
        for name, callable_obj in kernel_callables.items()
    }

    samples_by_metric: dict[str, list[int]] = {
        "engine_round_loop_us_p95": round_samples_ns,
    }
    for name, samples in kernel_samples_ns.items():
        samples_by_metric[f"{name}_us_p95"] = samples

    metrics: dict[str, int] = {
        "engine_round_loop_us_p95": _ns_to_us(
            _percentile(round_samples_ns, pct=95)
        ),
        "engine_round_loop_us_median": _ns_to_us(
            _percentile(round_samples_ns, pct=50)
        ),
        "engine_round_loop_us_max": _ns_to_us(max(round_samples_ns)),
        "engine_round_loop_us_total": _ns_to_us(sum(round_samples_ns)),
        "bounded_merge_us_p95": _ns_to_us(
            _percentile(kernel_samples_ns["bounded_merge"], pct=95)
        ),
        "compute_channel_decision_us_p95": _ns_to_us(
            _percentile(kernel_samples_ns["compute_channel_decision"], pct=95)
        ),
        "evaluate_claim_gate_us_p95": _ns_to_us(
            _percentile(kernel_samples_ns["evaluate_claim_gate"], pct=95)
        ),
    }
    return samples_by_metric, metrics


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="flowa.bench.runner",
        description="End-to-end benchmark runner (200 evaluate_bundle rounds).",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=DEFAULT_ROUNDS,
        help=f"number of evaluate_bundle calls to time (default: {DEFAULT_ROUNDS})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"output JSON path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=DEFAULT_WARMUP,
        help=f"discard the first N samples (default: {DEFAULT_WARMUP})",
    )
    parser.add_argument(
        "--kernel-iterations",
        type=int,
        default=KERNEL_ITERATIONS,
        help=(
            "iterations for each kernel benchmark "
            f"(default: {KERNEL_ITERATIONS})"
        ),
    )
    return parser.parse_args(argv)


def _utc_now_iso() -> str:
    """Return the current UTC time in ISO 8601 with ``Z`` suffix."""
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    # Pre-flight: sanity-check the synthetic adapter once so a missing
    # import or broken fixture fails loudly *before* we start the
    # clock.
    _ = SUPPORTED_CHANNELS
    _ = SyntheticMechanismAdapter()

    samples_by_metric, metrics = run_benchmark_round(
        rounds=int(args.rounds),
        kernel_iterations=int(getattr(args, "kernel_iterations", KERNEL_ITERATIONS)),
    )
    warmup = max(0, int(args.warmup))
    if warmup:
        for name in list(samples_by_metric.keys()):
            samples_by_metric[name] = samples_by_metric[name][warmup:]

    payload = {
        "schema": SCHEMA_NAME,
        "captured_at": _utc_now_iso(),
        "rounds": int(args.rounds),
        "warmup": warmup,
        "metrics": dict(metrics),
        "raw_samples_ns_by_metric": {
            name: [int(s) for s in samples]
            for name, samples in samples_by_metric.items()
        },
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    # Also print to stdout so CI can grep the JSON without re-reading
    # the file.
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
    sys.stdout.write("\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
