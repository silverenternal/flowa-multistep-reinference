"""Tests for DTB-R5 per-round provenance and condition-trace evidence.

No torch. No IO. Stdlib + dataclasses only.

Acceptance contract:

* v3 traces round-trip deterministically.
* v2 payloads still parse via ``read_round_trace_v2``.
* Missing fields are rejected at runtime.
* Hash mismatch is rejected at runtime.
* Non-finite values are rejected at runtime.
* Condition unchanged is respected (zero-bet row needs a blocker).
* ``final_policy_writer=adaptive_reflow`` is recorded for adopted rows.
"""

from __future__ import annotations

import importlib.util
import math
import sys
import types
from pathlib import Path


# Stub ``pocket_modules.mechanisms.inference.channel_freeze.schedule`` so
# that ``reinference_plan`` (which does a top-level relative import) loads
# without requiring the upstream private package. We register an empty
# stub module that returns a benign runtime plan dict on call. The trace
# tests do not exercise the channel-freeze runtime plan; they only need
# ``build_reinference_round_plan`` to return a typed plan.
def _stub_channel_freeze_runtime_plan(**_kwargs):  # pragma: no cover - trivial
    return {"ready": True, "blockers": ()}


_pocket = types.ModuleType("pocket_modules")
_mech = types.ModuleType("pocket_modules.mechanisms")
_inference = types.ModuleType("pocket_modules.mechanisms.inference")
_channel_freeze = types.ModuleType("pocket_modules.mechanisms.inference.channel_freeze")
_schedule = types.ModuleType("pocket_modules.mechanisms.inference.channel_freeze.schedule")
_schedule.channel_freeze_runtime_plan = _stub_channel_freeze_runtime_plan
sys.modules.setdefault("pocket_modules", _pocket)
sys.modules.setdefault("pocket_modules.mechanisms", _mech)
sys.modules.setdefault("pocket_modules.mechanisms.inference", _inference)
sys.modules.setdefault(
    "pocket_modules.mechanisms.inference.channel_freeze", _channel_freeze
)
sys.modules.setdefault(
    "pocket_modules.mechanisms.inference.channel_freeze.schedule", _schedule
)

# Mirror the existing test convention: load the conftest first so the
# synthetic ``adaptive_reflow`` package context is in place before we
# import any sibling modules. Pytest auto-runs conftest, but this guard
# is cheap and keeps the imports explicit.
import conftest  # noqa: F401  -- side-effect import
import pytest

# Load ``adaptive_reflow.legacy.plan`` (the renamed ``reinference_plan``)
# via the package so its ``from adaptive_reflow.contracts import ...``
# absolute import resolves.
try:
    from adaptive_reflow.legacy import plan as _rp_module
except Exception:
    _REPO_ROOT = Path(__file__).resolve().parent.parent
    _spec = importlib.util.spec_from_file_location(
        "adaptive_reflow.legacy.plan",
        str(_REPO_ROOT / "adaptive_reflow" / "legacy" / "plan.py"),
    )
    _rp_module = importlib.util.module_from_spec(_spec)
    sys.modules["adaptive_reflow.legacy.plan"] = _rp_module
    _spec.loader.exec_module(_rp_module)

REINFERENCE_ROUND_PLAN_SCHEMA_VERSION = _rp_module.REINFERENCE_ROUND_PLAN_SCHEMA_VERSION
REINFERENCE_ROUND_PLAN_SCHEMA_VERSION_LEGACY_V1 = (
    _rp_module.REINFERENCE_ROUND_PLAN_SCHEMA_VERSION_LEGACY_V1
)
build_reinference_round_plan = _rp_module.build_reinference_round_plan
read_round_plan_v1 = _rp_module.read_round_plan_v1

import adaptive_reflow.contracts as rmt
import adaptive_reflow.frame.trace as ts

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _valid_trace_kwargs(**overrides):
    base = {
        "round_index": 2,
        "source_bundle_id": "bundle-A",
        "source_round": 1,
        "selected_bundle_id": "bundle-A",
        "rejected_bundle_ids": ("bundle-B", "bundle-C"),
        "per_factor_raw": {"score": 0.91, "uncertainty": 0.13},
        "per_factor_bounded": {"score": 0.80, "uncertainty": 0.10},
        "alpha_by_channel": {"charge": 0.5, "pair": 0.5},
        "beta_by_channel": {"charge": 0.18, "pair": 0.22},
        "fresh_noise_floor_by_channel": {"charge": 0.05, "pair": 0.05},
        "calibration_artifact_hash": "cal-hash-001",
        "feedback_mode": "proxy_only",
        "producer_id": "inference.adaptive_reflow",
        "producer_mode": "adaptive_reflow_executable",
        "was_adopted": True,
        "final_policy_writer": ts.FINAL_POLICY_WRITER_ADAPTIVE_REFLOW,
        "blockers": (),
        "acceptance_reason": "adopted after envelope classifier passed",
        "operation_order_version": "v6",
        "created_at_round": 2,
    }
    base.update(overrides)
    return base


def _valid_v2_payload(**overrides):
    base = {
        "schema_name": ts.ROUND_TRACE_V2_SCHEMA_NAME,
        "round_index": 2,
        "source_round": 1,
        "selected_bundle_id": "bundle-A",
        "rejected_bundle_ids": ["bundle-B"],
        "alpha_by_channel": {"charge": 0.5, "pair": 0.5},
        "beta_by_channel": {"charge": 0.18, "pair": 0.22},
        "fresh_noise_floor_by_channel": {"charge": 0.05, "pair": 0.05},
        "calibration_artifact_hash": "cal-hash-001",
        "feedback_mode": "proxy_only",
        "operation_order_version": "v6",
        "created_at_round": 2,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Round-trip / hash
# ---------------------------------------------------------------------------


def test_round_trip_round_trace_v3_is_stable():
    kwargs = _valid_trace_kwargs()
    frozen = ts.freeze_round_trace_v3(ts.RoundTraceV3(**kwargs))
    round_tripped = ts.round_trip_round_trace_v3(frozen)
    assert round_tripped == frozen
    again = ts.round_trip_round_trace_v3(round_tripped)
    assert again == frozen
    digest_one = ts.compute_round_trace_v3_content_hash(frozen)
    digest_two = ts.compute_round_trace_v3_content_hash(again)
    assert digest_one == digest_two
    assert dict(frozen.hashes)["content_hash"] == digest_one


def test_round_trip_rejects_hash_mismatch():
    import dataclasses
    kwargs = _valid_trace_kwargs()
    frozen = ts.freeze_round_trace_v3(ts.RoundTraceV3(**kwargs))
    tampered = ts.RoundTraceV3(
        **{**kwargs, "beta_by_channel": {"charge": 0.99, "pair": 0.22}, "hashes": {}}
    )
    assert tampered != frozen
    # First confirm an unfrozen tampered row round-trips cleanly (it has
    # no embedded content_hash so the refreeze is a no-op).
    ts.round_trip_round_trace_v3(tampered)
    # Now take the *frozen* reference trace and tamper with the
    # beta_by_channel but keep the original content_hash. The embedded
    # hash no longer matches the recomputed digest; round-trip must reject.
    poison = dataclasses.replace(frozen, beta_by_channel={"charge": 0.99, "pair": 0.22})
    with pytest.raises(ValueError, match="content_hash mismatch"):
        ts.round_trip_round_trace_v3(poison)


def test_round_trip_rejects_frozen_with_wrong_content_hash():
    kwargs = _valid_trace_kwargs()
    good = ts.freeze_round_trace_v3(ts.RoundTraceV3(**kwargs))
    poisoned_hash = "0" * 64
    poisoned = good.__class__(
        **{
            **{f.name: getattr(good, f.name) for f in __import__("dataclasses").fields(good)},
            "hashes": {"content_hash": poisoned_hash},
        }
    )
    with pytest.raises(ValueError, match="content_hash mismatch"):
        ts.round_trip_round_trace_v3(poisoned)


# ---------------------------------------------------------------------------
# v2 reader
# ---------------------------------------------------------------------------


def test_read_round_trace_v2_still_works():
    payload = _valid_v2_payload()
    round_tripped = ts.read_round_trace_v2(payload)
    assert round_tripped["schema_name"] == ts.ROUND_TRACE_V2_SCHEMA_NAME
    assert round_tripped["round_index"] == 2
    assert round_tripped["beta_by_channel"] == {"charge": 0.18, "pair": 0.22}


def test_read_round_trace_v2_rejects_wrong_schema_name():
    payload = _valid_v2_payload(schema_name="something_else")
    with pytest.raises(ValueError, match="v2 reader requires"):
        ts.read_round_trace_v2(payload)


def test_read_round_trace_v2_rejects_missing_field():
    payload = _valid_v2_payload()
    payload.pop("beta_by_channel")
    with pytest.raises(ValueError, match="v2 trace missing fields"):
        ts.read_round_trace_v2(payload)


# ---------------------------------------------------------------------------
# Missing / non-finite / condition unchanged
# ---------------------------------------------------------------------------


def test_missing_field_rejected_at_round_trip():
    kwargs = _valid_trace_kwargs()
    kwargs.pop("calibration_artifact_hash")
    with pytest.raises(TypeError):
        ts.RoundTraceV3(**kwargs)


def test_round_trip_rejects_non_finite_values():
    kwargs = _valid_trace_kwargs(beta_by_channel={"charge": math.inf, "pair": 0.22})
    trace = ts.RoundTraceV3(**kwargs)
    with pytest.raises(ValueError, match="non_finite"):
        ts.round_trip_round_trace_v3(trace)


def test_round_trip_rejects_nan_values():
    kwargs = _valid_trace_kwargs(per_factor_raw={"score": math.nan})
    trace = ts.RoundTraceV3(**kwargs)
    with pytest.raises(ValueError, match="non_finite"):
        ts.round_trip_round_trace_v3(trace)


def test_condition_unchanged_zero_bet_without_blocker_rejected():
    kwargs = _valid_trace_kwargs(beta_by_channel={}, alpha_by_channel={}, blockers=())
    trace = ts.RoundTraceV3(**kwargs)
    with pytest.raises(ValueError, match="zero_beta_no_blocker"):
        ts.round_trip_round_trace_v3(trace)


def test_condition_unchanged_zero_bet_with_blocker_accepted():
    kwargs = _valid_trace_kwargs(
        beta_by_channel={},
        alpha_by_channel={},
        blockers=("envelope_classifier_out_of_envelope",),
        was_adopted=False,
    )
    trace = ts.RoundTraceV3(**kwargs)
    frozen = ts.round_trip_round_trace_v3(trace)
    assert "envelope_classifier_out_of_envelope" in frozen.blockers


# ---------------------------------------------------------------------------
# Writer arbitration
# ---------------------------------------------------------------------------


def test_adopted_row_records_adaptive_reflow_writer():
    kwargs = _valid_trace_kwargs(
        was_adopted=True,
        final_policy_writer=ts.FINAL_POLICY_WRITER_ADAPTIVE_REFLOW,
    )
    trace = ts.freeze_round_trace_v3(ts.RoundTraceV3(**kwargs))
    assert trace.final_policy_writer == "adaptive_reflow"
    assert trace.was_adopted is True
    ts.round_trip_round_trace_v3(trace)


def test_legacy_only_run_explicitly_legacy_writer():
    kwargs = _valid_trace_kwargs(
        was_adopted=False,
        final_policy_writer=ts.FINAL_POLICY_WRITER_LEGACY_NOISE_BIAS,
        producer_mode="legacy_standalone",
        producer_id="inference.noise_bias",
        selected_bundle_id=None,
        blockers=("legacy_standalone_window_only",),
    )
    trace = ts.freeze_round_trace_v3(ts.RoundTraceV3(**kwargs))
    assert trace.final_policy_writer == "noise_bias"
    assert trace.was_adopted is False
    ts.round_trip_round_trace_v3(trace)


def test_two_executable_writers_cannot_coexist():
    kwargs = _valid_trace_kwargs(
        final_policy_writer=ts.FINAL_POLICY_WRITER_ADAPTIVE_REFLOW,
        producer_mode="adaptive_reflow_executable",
    )
    ts.RoundTraceV3(**kwargs)
    # Mutating ``final_policy_writer`` is impossible post-construction
    # because the dataclass is frozen; the only way two writers could
    # "coexist" is via the producer_mode declaring executable while the
    # final writer is something else. Reject that combination explicitly.
    with pytest.raises(ValueError, match="round_trace_v3_rejected"):
        ts.round_trip_round_trace_v3(
            ts.RoundTraceV3(
                **{
                    **kwargs,
                    "final_policy_writer": "noise_bias",
                    "was_adopted": True,
                }
            )
        )


# ---------------------------------------------------------------------------
# Ledger-row embedding (DTB-R5 reproducibility)
# ---------------------------------------------------------------------------


def test_round_plan_embeds_ledger_row_for_reproducibility():
    ledger = {
        "ledger_row_id": "row-1",
        "run_id": "run-1",
        "sample_id": "sample-1",
        "trace_digest": "deadbeef",
        "source_round": 1,
        "target_round": 2,
        "outer_cycle_id": 0,
        "selected_bundle_id": "bundle-A",
        "rejected_bundle_ids": ["bundle-B"],
        "alpha_by_channel": {"charge": 0.5, "pair": 0.5},
        "beta_by_channel": {"charge": 0.18, "pair": 0.22},
        "calibration_artifact_hash": "cal-hash-001",
        "feedback_mode": "proxy_only",
        "writer_id": "inference.adaptive_reflow",
        "validation_errors": (),
        "created_at_round": 2,
    }
    plan = build_reinference_round_plan(
        round_index=1,
        rounds=3,
        controls={"memory_fraction": 0.3},
        ledger_row=ledger,
    )
    payload = plan.as_dict()
    assert payload["schema_version"] == REINFERENCE_ROUND_PLAN_SCHEMA_VERSION
    assert payload["condition_delta"]["ledger_row"]["ledger_row_id"] == "row-1"
    assert (
        payload["condition_delta"]["ledger_row"]["beta_by_channel"]["charge"] == 0.18
    )


def test_round_plan_v1_reader_still_parses():
    payload = {
        "schema_version": REINFERENCE_ROUND_PLAN_SCHEMA_VERSION_LEGACY_V1,
        "round_index": 0,
        "target_metric_family": "bootstrap",
        "observed_deficit": 0.0,
        "difficulty_rank": 0,
        "condition_delta": {"source": "applied_sampler_controls"},
        "restart_bias_scale": 0.0,
        "frozen_channels": [],
        "active_experts": ["flowa.mainline_ode"],
        "rationale": "bootstrap",
        "feedback_mode": "proxy_only",
        "uses_true_metric_feedback": False,
        "difficulty_strategy": "adaptive_deficit_first",
    }
    parsed = read_round_plan_v1(payload)
    assert parsed["schema_version"] == REINFERENCE_ROUND_PLAN_SCHEMA_VERSION_LEGACY_V1


# ---------------------------------------------------------------------------
# Ledger / NoiseBiasInputRow carriers
# ---------------------------------------------------------------------------


def test_dynamic_restart_transfer_ledger_has_v3_version_default():
    ledger = rmt.DynamicRestartTransferLedger(
        ledger_row_id=rmt.LedgerRowId("row-1"),
        run_id=rmt.RunId("run-1"),
        sample_id=rmt.SampleId("sample-1"),
        trace_digest=rmt.TraceDigest("deadbeef"),
        source_round=1,
        target_round=2,
        outer_cycle_id=0,
        selected_bundle_id=rmt.BundleId("bundle-A"),
        rejected_bundle_ids=(rmt.BundleId("bundle-B"),),
        per_channel_evidence=(),
        per_channel_decision=(),
        alpha_by_channel={"charge": rmt.FactorValue(0.5)},
        beta_by_channel={"charge": rmt.FactorValue(0.18)},
        raw_fraction_by_channel={"charge": rmt.FactorValue(0.30)},
        bounded_fraction_by_channel={"charge": rmt.FactorValue(0.18)},
        fresh_noise_floor_by_channel={"charge": rmt.FactorValue(0.05)},
        calibration_artifact_hash=rmt.ArtifactHash("cal-hash-001"),
        frozen_envelope_manifest_hash=None,
        tail_budget_row_ref=None,
        finite_prefix_only=True,
        empirical_only=True,
        feedback_mode=rmt.FeedbackMode("proxy_only"),
        writer_id=rmt.MechanismId("inference.adaptive_reflow"),
        provenance=rmt.ProvenanceChain(()),
        validation_errors=(),
        created_at_round=2,
    )
    assert ledger.ledger_version == "v3"


def test_noise_bias_input_row_carries_provenance():
    row = rmt.NoiseBiasInputRow(
        producer_id=rmt.MechanismId("inference.noise_bias"),
        producer_mode="legacy_standalone",
        was_adopted=False,
        calibration_artifact_hash=rmt.ArtifactHash("cal-hash-001"),
        feedback_mode=rmt.FeedbackMode("proxy_only"),
        round_in_cycle=1,
        score=0.42,
        uncertainty=0.10,
        audit_reason="legacy diagnostic; not adopted",
    )
    assert row.producer_mode == "legacy_standalone"
    assert row.was_adopted is False
    assert row.score == 0.42


# ---------------------------------------------------------------------------
# Hash determinism (the explicit acceptance bullet)
# ---------------------------------------------------------------------------


def test_content_hash_does_not_depend_on_mapping_order():
    a = ts.RoundTraceV3(
        **_valid_trace_kwargs(
            alpha_by_channel={"charge": 0.5, "pair": 0.5},
            beta_by_channel={"charge": 0.18, "pair": 0.22},
        )
    )
    b = ts.RoundTraceV3(
        **_valid_trace_kwargs(
            alpha_by_channel={"pair": 0.5, "charge": 0.5},
            beta_by_channel={"pair": 0.22, "charge": 0.18},
        )
    )
    assert ts.compute_round_trace_v3_content_hash(a) == ts.compute_round_trace_v3_content_hash(b)
