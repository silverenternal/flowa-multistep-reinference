"""Byte-determinism regression test for :meth:`Engine.run_round`.

Regression test for the engine's byte-determinism contract: two
identical ``run_round`` calls (same inputs, same adapter instance, same
seed) must produce byte-identical :class:`RoundTrace` projections.

This is the structural invariant for the writer-side
audit-bytes-determinism property (ADR-0006 §3.2). The check is
parameterised over:

* the **happy path** (well-formed bundle / policy / condition_delta
  the synthetic adapter accepts),
* **fail-closed paths** (missing ``bundle`` / ``policy`` /
  ``condition_delta`` and a non-int ``round_index``).

Each parameterisation runs the engine twice on identical inputs and
asserts that :meth:`RoundTrace.as_dict` is byte-identical
(``json.dumps(..., sort_keys=True, default=str)`` SHA-256).

Stdlib + pytest. No hypothesis.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

# Make the repository importable when pytest is launched from the
# project root without any package metadata.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adaptive_reflow.adapters import SyntheticContinuousAdapter
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
    Engine,
    ODEConditionDelta,
    PhaseState,
    StateBundle,
    TensorRef,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tensor_ref(name: str) -> TensorRef:
    """Return a deterministic placeholder :class:`TensorRef` for tests."""
    return TensorRef(f"test://{name}")


def _make_state_bundle() -> StateBundle:
    """Return a well-formed :class:`StateBundle` for the synthetic adapter."""
    adapter = SyntheticContinuousAdapter()
    caps = adapter.capabilities()
    return StateBundle(
        channels={name: _tensor_ref(name) for name in caps.supported_channels},
        masks={"freeze": _tensor_ref("freeze")},
        batch_id="batch-det",
        sample_id="sample-det",
        reference_frame="pocket_centered",
        normalization="per_atom_std",
        source_round=0,
        detach_proof=True,
        native_state_digest="native-digest-det",
        provenance=("test_determinism",),
        capability_token=caps,
    )


def _make_phase_state() -> PhaseState:
    """Return a deterministic :class:`PhaseState`."""
    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        horizon_remaining=8,
        seed_lineage_digest="seed-lineage-det",
        recorded_at_round=0,
    )


def _make_final_policy() -> FinalRestartPolicy:
    """Return a deterministic :class:`FinalRestartPolicy`."""
    adapter = SyntheticContinuousAdapter()
    caps = adapter.capabilities()
    channel_names = [ChannelName(c) for c in caps.supported_channels]
    policy = FinalRestartPolicy(
        policy_id=PolicyId("policy-det"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("run-det"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={ch: FactorValue(0.0) for ch in channel_names},
        alpha_by_channel={ch: FactorValue(1.0) for ch in channel_names},
        fresh_noise_floor_by_channel={ch: FactorValue(0.0) for ch in channel_names},
        schedule_sample=None,
        freeze_admission_by_channel={ch: True for ch in channel_names},
        ledger_row_id=LedgerRowId("ledger-det"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        # P0-5: disable the schedule-derived beta override; the
        # determinism tests assert byte-for-byte parity on the inline
        # ``beta_by_channel`` value, not on the schedule-derived one.
        beta_from_schedule=False,
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_condition_delta() -> ODEConditionDelta:
    """Return a well-formed :class:`ODEConditionDelta`."""
    return ODEConditionDelta(
        delta_spec={"temperature": 1.0, "memory_fraction": 0.1},
        source="rest_memory",
        target_round=0,
        calibration_artifact_hash="calibration-det",
    )


def _digest(payload: object) -> str:
    """Return a deterministic sha256 digest for ``payload``."""
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scenario",
    (
        "happy_path",
        "bundle_none",
        "policy_none",
        "condition_delta_none",
        "round_index_str",
        "round_index_negative",
        "source_round_float",
        "feature_disabled",
    ),
)
def test_engine_byte_determinism(scenario: str) -> None:
    """``Engine.run_round`` is byte-deterministic across two identical
    invocations on the same inputs.

    Each scenario runs the engine twice on identical arguments; the two
    :meth:`RoundTrace.as_dict` projections must be byte-identical (i.e.
    their SHA-256 hashes match).
    """
    engine = Engine()
    adapter = SyntheticContinuousAdapter()
    bundle = _make_state_bundle()
    phase_state = _make_phase_state()
    policy = _make_final_policy()
    condition_delta = _make_condition_delta()
    round_index: object = 0

    if scenario == "happy_path":
        pass  # Defaults are well-formed.
    elif scenario == "bundle_none":
        bundle = None  # type: ignore[assignment]
    elif scenario == "policy_none":
        policy = None  # type: ignore[assignment]
    elif scenario == "condition_delta_none":
        condition_delta = None
    elif scenario == "round_index_str":
        round_index = "abc"  # type: ignore[assignment]
    elif scenario == "round_index_negative":
        round_index = -1
    elif scenario == "source_round_float":
        # Malformed source_round on a non-empty bundle.
        bundle = replace(
            _make_state_bundle(),
            source_round=1.5,  # type: ignore[arg-type]
        )
    elif scenario == "feature_disabled":
        engine = Engine(feature_flag=False)
    else:  # pragma: no cover - regression
        raise AssertionError(f"unknown scenario: {scenario!r}")

    result_a = engine.run_round(
        round_index=round_index,  # type: ignore[arg-type]
        phase_state=phase_state,
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=condition_delta,
    )
    result_b = engine.run_round(
        round_index=round_index,  # type: ignore[arg-type]
        phase_state=phase_state,
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=condition_delta,
    )

    dict_a = result_a.round_trace.as_dict()
    dict_b = result_b.round_trace.as_dict()
    digest_a = _digest(dict_a)
    digest_b = _digest(dict_b)
    assert digest_a == digest_b, (
        f"byte-determinism violated for scenario {scenario!r}: "
        f"first digest={digest_a[:16]}..., second digest={digest_b[:16]}..."
    )
    # And structurally: the two dicts must be == (Python's structural
    # equality on dicts is the same as byte-equality for json-stable
    # representations).
    assert dict_a == dict_b, (
        f"structural equality violated for scenario {scenario!r}: "
        f"keys differ or values differ"
    )


__all__ = ["test_engine_byte_determinism"]
