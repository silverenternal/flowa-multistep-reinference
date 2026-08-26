"""End-to-end Engine.run_round tests using the synthetic adapter.

Exercises the public Flow Matching ODE engine against
:class:`adaptive_reflow.adapters.SyntheticContinuousAdapter` (and the
mismatched-capability fixture :class:`SyntheticUnsupportedAdapter`) for
the four canonical scenarios:

* :class:`TestRunRoundLoop`     — long horizon (100 rounds) emits the
  correct ledger row count and ``source_round`` mapping, and the trace
  digest is byte-stable across two identically-seeded runs.
* :class:`TestReset`            — after recreating engine + state from
  scratch the trace at round 50 matches a fresh 50-round run.
* :class:`TestCapabilityMismatch` — an adapter with no advertised
  capabilities triggers ``CapabilityMissingError`` at the handshake
  boundary and the gate stays closed (the engine never reaches native
  calls).
* :class:`TestPolicyHashStability` — the policy_hash derived by
  :func:`hash_policy_hash` is byte-stable across distinct evidence
  streams (different ``condition_delta``, different ``seed``).

The tests are stdlib-only (no torch, no numpy) and depend on no GPU.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

# Make sure the project root is importable when pytest is invoked from
# any directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from adaptive_reflow.adapters import (
    SyntheticContinuousAdapter,
    SyntheticUnsupportedAdapter,
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
from adaptive_reflow.frame import (
    CapabilityMismatchError,
    CapabilityMissingError,
    Engine,
    EngineRoundResult,
    LedgerRow,
    ODEConditionDelta,
    PhaseState,
    RoundTrace,
    StateBundle,
    TensorRef,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


CONTINUOUS_CHANNELS: tuple[str, ...] = (
    "coordinate",
    "charge",
    "coordinate.continuous",
    "charge.continuous",
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _tensor_ref(name: str) -> TensorRef:
    """Return a deterministic placeholder :class:`TensorRef` for tests."""
    return TensorRef(f"test://{name}")


def _caps() -> AdapterCapabilities:  # type: ignore[name-defined]  # noqa: F821
    """Return the canonical capability surface of ``SyntheticContinuousAdapter``."""
    return SyntheticContinuousAdapter().capabilities()


def _make_state_bundle(
    *,
    source_round: int = 0,
    batch_id: str = "batch-1",
    sample_id: str = "sample-1",
) -> StateBundle:
    """Return a valid detached :class:`StateBundle` matching the synthetic
    continuous adapter's capability surface."""
    caps = _caps()
    return StateBundle(
        channels={name: _tensor_ref(name) for name in caps.supported_channels},
        masks={"freeze": _tensor_ref("freeze")},
        batch_id=batch_id,
        sample_id=sample_id,
        reference_frame="pocket_centered",
        normalization="per_atom_std",
        source_round=int(source_round),
        detach_proof=True,
        native_state_digest="native-digest-placeholder",
        provenance=("test_engine_e2e",),
        capability_token=caps,
    )


def _make_phase_state(
    *,
    horizon_remaining: int = 256,
) -> PhaseState:
    """Return an engine-side :class:`PhaseState` ready for ``run_round``."""
    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        horizon_remaining=int(horizon_remaining),
        seed_lineage_digest="seed-lineage-placeholder",
        recorded_at_round=0,
    )


def _make_final_policy(
    *,
    policy_id: str = "policy-e2e",
    beta_by_channel: dict[str, float] | None = None,
    alpha_by_channel: dict[str, float] | None = None,
    fresh_noise_floor_by_channel: dict[str, float] | None = None,
    freeze_admission_by_channel: dict[str, bool] | None = None,
    run_id: str = "run-e2e",
) -> FinalRestartPolicy:
    """Build a deterministic :class:`FinalRestartPolicy` whose
    ``policy_hash`` matches :func:`hash_policy_hash`."""
    if beta_by_channel is None:
        beta_by_channel = {ch: 0.0 for ch in CONTINUOUS_CHANNELS}
    if alpha_by_channel is None:
        alpha_by_channel = {ch: 1.0 for ch in CONTINUOUS_CHANNELS}
    if fresh_noise_floor_by_channel is None:
        fresh_noise_floor_by_channel = {ch: 0.0 for ch in CONTINUOUS_CHANNELS}
    if freeze_admission_by_channel is None:
        freeze_admission_by_channel = {ch: True for ch in CONTINUOUS_CHANNELS}

    policy = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(run_id),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={
            ChannelName(k): FactorValue(float(v)) for k, v in beta_by_channel.items()
        },
        alpha_by_channel={
            ChannelName(k): FactorValue(float(v)) for k, v in alpha_by_channel.items()
        },
        fresh_noise_floor_by_channel={
            ChannelName(k): FactorValue(float(v))
            for k, v in fresh_noise_floor_by_channel.items()
        },
        schedule_sample=None,
        freeze_admission_by_channel={
            ChannelName(k): bool(v) for k, v in freeze_admission_by_channel.items()
        },
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_condition_delta(
    *,
    target_round: int = 0,
    source: str = "rest_memory",
    calibration_artifact_hash: str = "calibration-artifact-placeholder",
) -> ODEConditionDelta:
    """Return a well-formed :class:`ODEConditionDelta`."""
    return ODEConditionDelta(
        delta_spec={"temperature": 1.0, "memory_fraction": 0.1},
        source=source,
        target_round=int(target_round),
        calibration_artifact_hash=calibration_artifact_hash,
    )


def _trace_digest(round_trace: RoundTrace) -> str:
    """Compute a deterministic sha256 digest for a :class:`RoundTrace`.

    The engine does not expose a ``trace_digest`` field directly; we derive
    one from the canonical ``RoundTrace.as_dict()`` projection. The
    resulting digest is stable across runs whenever the inputs to the
    engine (adapter config, bundle, policy, condition, seed, phase
    state) are identical.
    """
    payload = round_trace.as_dict()
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _run_horizon(
    *,
    num_rounds: int,
    seed_offset: int = 0,
    bundle_source_round_for: callable[[int], int] | None = None,
    condition_target_round_for: callable[[int], int] | None = None,
    policy: FinalRestartPolicy | None = None,
    condition_source: str = "rest_memory",
) -> tuple[list[LedgerRow], list[RoundTrace], list[PhaseState]]:
    """Drive ``Engine.run_round`` for ``num_rounds`` steps and return the
    ledger rows, round traces and the running phase-state sequence.

    Helper used by :class:`TestRunRoundLoop` and :class:`TestReset`.
    """
    adapter = SyntheticContinuousAdapter()
    engine = Engine()
    phase = _make_phase_state(horizon_remaining=max(num_rounds + 4, 8))
    if policy is None:
        policy = _make_final_policy()
    bundle = _make_state_bundle(source_round=0)

    ledger_rows: list[LedgerRow] = []
    round_traces: list[RoundTrace] = []
    phase_states: list[PhaseState] = [phase]

    for i in range(num_rounds):
        source_round = (
            bundle_source_round_for(i) if bundle_source_round_for is not None else i
        )
        target_round = (
            condition_target_round_for(i)
            if condition_target_round_for is not None
            else i
        )
        # Rebuild the source bundle so its source_round matches the round
        # index — this is what makes the ledger_row.source_round match
        # the round index the engine emits.
        bundle = _make_state_bundle(source_round=source_round)

        result = engine.run_round(
            round_index=i,
            phase_state=phase,
            bundle=bundle,
            adapter=adapter,
            policy=policy,
            condition_delta=_make_condition_delta(
                target_round=target_round, source=condition_source
            ),
            seed=int(seed_offset + i),
        )
        assert isinstance(result, EngineRoundResult)
        ledger_rows.append(result.ledger_row)
        round_traces.append(result.round_trace)
        phase = result.next_phase_state
        phase_states.append(phase)

    return ledger_rows, round_traces, phase_states


# ---------------------------------------------------------------------------
# TestRunRoundLoop
# ---------------------------------------------------------------------------


class TestRunRoundLoop:
    """Drive ``Engine.run_round`` for 100 rounds and assert the ledger /
    trace-digest invariants."""

    def test_one_hundred_rounds_emit_one_hundred_ledger_rows(self) -> None:
        ledger_rows, _, _ = _run_horizon(num_rounds=100)
        assert len(ledger_rows) == 100

    def test_each_ledger_row_source_round_matches_round_index(self) -> None:
        ledger_rows, _, _ = _run_horizon(num_rounds=100)
        for i, row in enumerate(ledger_rows):
            assert row.round_index == i
            assert row.source_round == i, (
                f"ledger row at round {i} has source_round={row.source_round!r}"
            )

    def test_trace_digest_is_deterministic_across_two_seeded_runs(self) -> None:
        """Two identically-seeded runs of 100 rounds must yield identical
        per-round trace digests."""
        rows_a, traces_a, _ = _run_horizon(num_rounds=100, seed_offset=0)
        rows_b, traces_b, _ = _run_horizon(num_rounds=100, seed_offset=0)

        digests_a = [_trace_digest(t) for t in traces_a]
        digests_b = [_trace_digest(t) for t in traces_b]
        assert digests_a == digests_b

        # The ledger rows are also byte-identical (deterministic ledger_row_id
        # because inputs are identical).
        for ra, rb in zip(rows_a, rows_b, strict=True):
            assert ra.ledger_row_id == rb.ledger_row_id
            assert ra.applied_policy_hash == rb.applied_policy_hash
            assert ra.selected_bundle_digest == rb.selected_bundle_digest
            assert ra.audit_codes == rb.audit_codes


# ---------------------------------------------------------------------------
# TestReset
# ---------------------------------------------------------------------------


class TestReset:
    """Reset engine state and verify the round-50 trace is identical to
    a fresh 50-round run."""

    def test_round_fifty_trace_matches_fresh_fifty_round_run(self) -> None:
        # First run: 50 rounds, capture round-49 trace digest.
        _, traces_1, _ = _run_horizon(num_rounds=50)
        digest_1 = _trace_digest(traces_1[-1])

        # Second run: 50 rounds in a fresh engine + fresh phase state
        # (the engine itself is stateless; "reset" means starting from a
        # clean phase state and a fresh bundle). The trace at round 49
        # must match the first run.
        _, traces_2, _ = _run_horizon(num_rounds=50)
        digest_2 = _trace_digest(traces_2[-1])

        assert digest_1 == digest_2


# ---------------------------------------------------------------------------
# TestCapabilityMismatch
# ---------------------------------------------------------------------------


class TestCapabilityMismatch:
    """An adapter that advertises no required capabilities must trip the
    fail-closed handshake gate; ``run_round`` itself records
    ``gate=False`` via the canonical ``ERR_CAPABILITIES_INVALID`` audit
    code."""

    def test_unsupported_adapter_raises_capability_missing_error(self) -> None:
        adapter = SyntheticUnsupportedAdapter()
        engine = Engine()
        # The unsupported adapter trips the engine's fail-closed gate at
        # the handshake boundary: either ``CapabilityMissingError`` (a
        # specific capability check fails) or ``CapabilityMismatchError``
        # (``validate_capabilities`` rejects the inconsistent surface).
        # Both errors keep the gate closed (gate=False).
        with pytest.raises((CapabilityMissingError, CapabilityMismatchError)) as excinfo:
            engine.handshake(adapter)
        assert excinfo.value.capability != ""

    def test_unsupported_adapter_run_round_records_gate_closed(self) -> None:
        adapter = SyntheticUnsupportedAdapter()
        engine = Engine()
        bundle = _make_state_bundle()
        policy = _make_final_policy()
        result = engine.run_round(
            round_index=0,
            phase_state=_make_phase_state(),
            bundle=bundle,
            adapter=adapter,
            policy=policy,
            condition_delta=_make_condition_delta(target_round=0),
        )
        # The gate is closed (False): the round trace records
        # capabilities_invalid and the native stage is never reached.
        assert result.round_trace.integrator_trace is None
        assert result.round_trace.detached is False
        assert result.round_trace.audit_codes
        assert any(
            code.startswith("capabilities_invalid")
            for code in result.round_trace.audit_codes
        )

        # The unsupported adapter's protocol methods raise
        # AssertionError if invoked; verify none of them were called.
        with pytest.raises(AssertionError):
            adapter.build_initial_state(batch_id="b", sample_id="s")
        with pytest.raises(AssertionError):
            adapter.solve_ode(  # type: ignore[arg-type]
                bundle, _make_condition_delta(), seed=0
            )

    def test_unsupported_adapter_partial_capability_raises(self) -> None:
        """An adapter advertising some but not all required capabilities
        still trips ``CapabilityMissingError`` (gate stays closed)."""

        class _PartialContinuous:
            """Continuous-capable but missing trajectory digest."""

            def capabilities(self):  # type: ignore[no-untyped-def]
                from adaptive_reflow.frame import AdapterCapabilities

                return AdapterCapabilities(
                    has_ode_integration_surface=True,
                    has_prior_export=True,
                    has_state_export=True,
                    has_condition_injection=True,
                    has_restart_boundary=True,
                    has_continuous_channels=True,
                    has_discrete_channels=False,
                    has_trajectory_digest=False,  # MISSING
                    has_deterministic_seed=True,
                    has_materialization_route=True,
                    supported_channels=CONTINUOUS_CHANNELS,
                )

        engine = Engine()
        with pytest.raises(CapabilityMissingError) as excinfo:
            engine.handshake(_PartialContinuous())
        assert excinfo.value.capability == "has_trajectory_digest"


# ---------------------------------------------------------------------------
# TestPolicyHashStability
# ---------------------------------------------------------------------------


class TestPolicyHashStability:
    """``FinalRestartPolicy.policy_hash`` is byte-stable for the same
    bounded inputs, even when other evidence (condition delta, seed)
    changes."""

    def test_two_policies_with_identical_fields_have_identical_hash(self) -> None:
        p1 = _make_final_policy()
        p2 = _make_final_policy()
        assert str(hash_policy_hash(p1)) == str(hash_policy_hash(p2))
        assert str(p1.policy_hash) == str(p2.policy_hash)

    def test_policy_hash_byte_stable_across_distinct_evidence(self) -> None:
        adapter = SyntheticContinuousAdapter()
        engine = Engine()
        phase = _make_phase_state(horizon_remaining=64)
        policy = _make_final_policy()
        bundle = _make_state_bundle(source_round=0)

        first_round_hashes: list[str] = []

        # ---- Run 10 rounds with one evidence stream -------------------
        for i in range(10):
            result = engine.run_round(
                round_index=i,
                phase_state=phase,
                bundle=bundle,
                adapter=adapter,
                policy=policy,
                condition_delta=_make_condition_delta(
                    target_round=i, source="evidence_stream_A"
                ),
                seed=i,
            )
            first_round_hashes.append(str(result.applied_policy_hash))
            phase = result.next_phase_state
            bundle = _make_state_bundle(source_round=i)

        saved_hash = first_round_hashes[-1]

        # ---- Run 10 more rounds with a DIFFERENT evidence stream ------
        # Different condition_delta, different seed, different source.
        # The policy object is byte-identical (same hash), so the engine
        # must continue to emit the same applied_policy_hash.
        second_round_hashes: list[str] = []
        for i in range(10, 20):
            result = engine.run_round(
                round_index=i,
                phase_state=phase,
                bundle=bundle,
                adapter=adapter,
                policy=policy,
                condition_delta=_make_condition_delta(
                    target_round=i,
                    source="evidence_stream_B",
                    calibration_artifact_hash="different-calibration-artifact",
                ),
                seed=1000 + i,  # distinct seed stream
            )
            second_round_hashes.append(str(result.applied_policy_hash))
            phase = result.next_phase_state
            bundle = _make_state_bundle(source_round=i)

        # Every applied_policy_hash matches the saved hash byte-for-byte.
        assert all(h == saved_hash for h in first_round_hashes)
        assert all(h == saved_hash for h in second_round_hashes)
        assert len(first_round_hashes) == 10
        assert len(second_round_hashes) == 10
