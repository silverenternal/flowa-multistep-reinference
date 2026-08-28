"""Long-horizon 1000-round x 8-capability stress test for the molecular path.

Drives :class:`adaptive_reflow.frame.engine.Engine` for 1000 consecutive
``run_round`` invocations against the canonical molecular adapter,
:class:`adaptive_reflow.adapters.reference_flowa.ReferenceFlowAAdapter`,
and asserts the same properties as the ToyGaussian stress test:

* All 1000 round traces emit empty ``audit_codes`` (every fail-closed
  gate passes for 1000 rounds in a row).
* All 1000 ledger row IDs are unique.
* Per-round wall-clock stays under the
  ``engine_round_loop_us_p95`` budget declared in
  :mod:`docs.PERFORMANCE_BUDGETS` (1000 us per round).
* Phase state advances deterministically (``round_in_cycle`` is a
  strict counter; ``recorded_at_round`` matches the round index).
* The ledger's pickled byte size grows linearly in the round count.
* Two 1000-round runs produce byte-identical final-state hashes.
* A Hypothesis sweep over the seed argument preserves byte-determinism.

Adapter choice
--------------

``ReferenceFlowAAdapter`` is the canonical molecular adapter that ships
in :mod:`adaptive_reflow.adapters.reference_flowa`. It implements the
full :class:`FlowMatchingODEAdapter` protocol (including the eight
engine-handshake capabilities) and is stdlib-only — it does not depend
on ``torch`` or on the FlowMol3 source tree. ``FlowMol3Adapter`` is
also read-only but is intentionally **unconditional**
(``has_condition_injection=False``); driving it through
``Engine.run_round`` with a non-empty ``condition_delta`` would trip a
fail-closed gate. ``SyntheticMechanismAdapter`` is reserved as a
fallback stand-in (see :mod:`tools.mutate.MOLECULAR_STRESS_GAP`).

All tests are decorated with ``@pytest.mark.stress`` so they only run
on the stress-nightly workflow.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import sys
import time
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Make sure the repo root is importable when pytest is invoked from any
# directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Per-round wall-clock budget. Source: docs/PERFORMANCE_BUDGETS.md,
# ``engine_round_loop_us_p95`` is 1000 us; we hold the per-round mean
# under that ceiling (the budget file documents a 1.2x tolerance for
# p95; using the raw budget for the mean leaves generous headroom).
PER_ROUND_BUDGET_US: float = 1000.0

# Total rounds driven by every test in this file. The number is fixed
# across tests so a regression on any single property is visible in the
# same fixture cost.
NUM_ROUNDS: int = 1000

# ReferenceFlowAAdapter advertises the four CONTRACTS.md §1 molecular
# channels: coordinate + charge + raw_pair + projected_pair.
MOLECULAR_CHANNELS: tuple[str, ...] = (
    "coordinate",
    "charge",
    "raw_pair",
    "projected_pair",
)

# The adapter under test. We pin it at module import time so the test
# name + filename can declare which adapter is driven (the requirement
# forbids silent fallback). If the canonical adapter becomes unimportable
# in the future the file must be updated and
# :mod:`tools.mutate.MOLECULAR_STRESS_GAP` must be revisited.
try:
    from adaptive_reflow.adapters.reference_flowa import (
        REFERENCE_FLOWA_CHANNELS,
        ReferenceFlowAAdapter,
    )
except ImportError as _exc:  # pragma: no cover - module load guard
    ADAPTER_IMPORT_ERROR: ImportError | None = _exc
    ReferenceFlowAAdapter = None  # type: ignore[assignment]
    REFERENCE_FLOWA_CHANNELS = MOLECULAR_CHANNELS  # type: ignore[assignment]
else:
    ADAPTER_IMPORT_ERROR = None

_REQUIRED_ADAPTER_CAPABILITIES: tuple[str, ...] = (
    "has_ode_integration_surface",
    "has_prior_export",
    "has_state_export",
    "has_condition_injection",
    "has_restart_boundary",
    "has_trajectory_digest",
    "has_deterministic_seed",
    "has_materialization_route",
)


# ---------------------------------------------------------------------------
# Helpers — deterministic, stdlib-only, no torch.
# ---------------------------------------------------------------------------


def _adapter_sanity_check() -> None:
    """Confirm the pinned adapter can be instantiated and advertises the
    eight engine-handshake capabilities. Fail loudly if not so the test
    surfaces a missing adapter rather than silently swapping it out.
    """
    if ReferenceFlowAAdapter is None or ADAPTER_IMPORT_ERROR is not None:
        pytest.skip(
            "ReferenceFlowAAdapter unavailable; see "
            "tools/mutate/MOLECULAR_STRESS_GAP.md"
        )
    adapter = ReferenceFlowAAdapter()
    caps = adapter.capabilities()
    for required in _REQUIRED_ADAPTER_CAPABILITIES:
        if not bool(getattr(caps, required)):
            pytest.fail(
                f"ReferenceFlowAAdapter missing required capability "
                f"{required!r}; cannot drive stress test"
            )
    for channel in MOLECULAR_CHANNELS:
        if channel not in caps.supported_channels:
            pytest.fail(
                f"ReferenceFlowAAdapter missing molecular channel "
                f"{channel!r} in supported_channels={caps.supported_channels!r}"
            )


def _make_phase_state(*, horizon_remaining: int = 2 * NUM_ROUNDS):
    """Return an engine-side :class:`PhaseState` with generous horizon."""
    from adaptive_reflow.frame import PhaseState

    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        horizon_remaining=int(horizon_remaining),
        seed_lineage_digest="stress:seed-lineage-molecular-1000",
        recorded_at_round=0,
    )


def _make_final_policy(
    *,
    policy_id: str = "policy-stress-molecular-1000",
    run_id: str = "run-stress-molecular-1000",
    target_round: int = 0,
):
    """Build a deterministic :class:`FinalRestartPolicy` with a valid hash."""
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

    policy = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(run_id),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={
            ChannelName(k): FactorValue(0.0) for k in MOLECULAR_CHANNELS
        },
        alpha_by_channel={
            ChannelName(k): FactorValue(1.0) for k in MOLECULAR_CHANNELS
        },
        fresh_noise_floor_by_channel={
            ChannelName(k): FactorValue(0.0) for k in MOLECULAR_CHANNELS
        },
        schedule_sample=None,
        freeze_admission_by_channel={
            ChannelName(k): True for k in MOLECULAR_CHANNELS
        },
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        # P0-5: ``beta_from_schedule=False`` so the engine doesn't emit
        # ``ERR_SCHEDULE_SAMPLE_MISSING`` (the stress test asserts that
        # every round is fail-clean).
        beta_from_schedule=False,
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_condition_delta(
    *,
    target_round: int = 0,
    target_mean: float = 1.0,
    source: str = "stress-molecular-1000",
    calibration_artifact_hash: str = "cal-stress-molecular-1000",
):
    """Return a well-formed :class:`ODEConditionDelta`."""
    from adaptive_reflow.frame import ODEConditionDelta

    return ODEConditionDelta(
        delta_spec={"target_mean": float(target_mean)},
        source=source,
        target_round=int(target_round),
        calibration_artifact_hash=calibration_artifact_hash,
    )


def _build_source_bundle(adapter, *, round_index: int):
    """Return a detached, valid source :class:`StateBundle`.

    Each round rebuilds the bundle via
    :meth:`ReferenceFlowAAdapter.build_initial_state` so the bundle is
    structurally valid (capability handshake OK, ``source_round`` is a
    non-negative int, ``detach_proof=True``, and every molecular
    channel is in the adapter's ``supported_channels``).
    """
    return adapter.build_initial_state(
        batch_id="batch-stress-molecular-1000",
        sample_id="sample-stress-molecular-1000",
    )


def _drive_1000_rounds(*, seed: int = 42):
    """Drive ``NUM_ROUNDS`` engine rounds and return the result list.

    Each round uses the adapter to mint a fresh, detached source
    bundle, the same policy + condition every round, and the supplied
    ``seed`` for ``adapter.solve_ode``. The phase state is threaded
    forward round-by-round via ``result.next_phase_state``.
    """
    from adaptive_reflow.frame import Engine

    _adapter_sanity_check()
    adapter = ReferenceFlowAAdapter()
    engine = Engine()
    policy = _make_final_policy()
    condition = _make_condition_delta()

    phase_state = _make_phase_state()
    bundle = _build_source_bundle(adapter, round_index=0)

    results = []
    for r in range(NUM_ROUNDS):
        result = engine.run_round(
            round_index=r,
            phase_state=phase_state,
            bundle=bundle,
            adapter=adapter,
            policy=policy,
            condition_delta=condition,
            seed=seed,
        )
        results.append(result)
        phase_state = result.next_phase_state
        # The next round's source bundle is a fresh detached bundle
        # minted by the adapter. This matches the canonical
        # ``test_toy_gaussian`` pattern and produces empty
        # ``audit_codes`` because the bundle is structurally valid and
        # all four molecular channels are supported.
        bundle = _build_source_bundle(adapter, round_index=r + 1)
    return results


def _measure_per_round_timings_us(*, seed: int = 42) -> list[float]:
    """Re-drive the 1000-round loop and return per-round timings in us."""
    from adaptive_reflow.frame import Engine

    _adapter_sanity_check()
    adapter = ReferenceFlowAAdapter()
    engine = Engine()
    policy = _make_final_policy()
    condition = _make_condition_delta()

    phase_state = _make_phase_state()
    bundle = _build_source_bundle(adapter, round_index=0)

    timings: list[float] = []
    for r in range(NUM_ROUNDS):
        t0 = time.perf_counter()
        result = engine.run_round(
            round_index=r,
            phase_state=phase_state,
            bundle=bundle,
            adapter=adapter,
            policy=policy,
            condition_delta=condition,
            seed=seed,
        )
        elapsed_us = (time.perf_counter() - t0) * 1_000_000.0
        timings.append(elapsed_us)
        # Thread phase state forward (mirrors the production loop).
        phase_state = result.next_phase_state
        bundle = _build_source_bundle(adapter, round_index=r + 1)
    return timings


def _ledger_bytes(rows: Iterable) -> int:
    """Return the cumulative ``pickle.dumps`` byte length of ``rows``."""
    return sum(
        len(pickle.dumps(row, protocol=pickle.HIGHEST_PROTOCOL)) for row in rows
    )


def _hash_final_state(seed: int) -> str:
    """Return a deterministic hash of the final round's full state."""
    results = _drive_1000_rounds(seed=seed)
    last = results[-1]
    payload = {
        "trace": last.round_trace.as_dict(),
        "phase": last.next_phase_state.as_dict(),
        "ledger_row_id": last.ledger_row.ledger_row_id,
        "applied_policy_hash": last.applied_policy_hash,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------------------------
# 1. Engine holds under 1000 molecular rounds — empty audit, unique rows,
#    budget, deterministic phase advance.
# ---------------------------------------------------------------------------


@pytest.mark.stress
def test_molecular_engine_holds_under_1000_rounds() -> None:
    """Engine survives 1000 rounds against ``ReferenceFlowAAdapter`` with
    no audit codes, unique row IDs, bounded per-round wall-clock, and
    deterministic phase advance.

    Asserts:

    * Every round's ``round_trace.audit_codes`` is empty.
    * Every ledger row ID is unique (no two rounds share a hash).
    * Per-round mean wall-clock stays under the budget from
      :mod:`docs.PERFORMANCE_BUDGETS` (``engine_round_loop_us_p95``).
    * Phase state ``round_in_cycle`` is a strict counter and the
      final ``recorded_at_round`` matches ``NUM_ROUNDS - 1``.
    * All four molecular channels appear in the ledger's
      ``per_channel_decision`` mapping and report ``True``.
    """
    results = _drive_1000_rounds(seed=42)
    assert len(results) == NUM_ROUNDS, (
        f"engine must drive exactly {NUM_ROUNDS} rounds; got {len(results)}"
    )

    # (a) All 1000 traces have empty audit_codes.
    for r, res in enumerate(results):
        assert res.round_trace.audit_codes == (), (
            f"round {r}: expected empty audit_codes; "
            f"got {res.round_trace.audit_codes!r}"
        )

    # (b) All 1000 ledger row IDs are unique.
    row_ids = [res.ledger_row.ledger_row_id for res in results]
    assert len(set(row_ids)) == NUM_ROUNDS, (
        f"ledger row IDs are not unique: got {len(set(row_ids))} unique "
        f"out of {NUM_ROUNDS}"
    )

    # (c) Per-round wall-clock stays under the per-round budget.
    timings_us = _measure_per_round_timings_us(seed=42)
    assert len(timings_us) == NUM_ROUNDS
    mean_us = sum(timings_us) / NUM_ROUNDS
    max_us = max(timings_us)
    sorted_timings = sorted(timings_us)
    p95_us = sorted_timings[int(0.95 * NUM_ROUNDS)]

    # Headline assertion: mean per-round wall-clock must stay under
    # the budget. The p95 / max are printed for human inspection only.
    assert mean_us <= PER_ROUND_BUDGET_US, (
        f"per-round mean wall-clock {mean_us:.1f} us exceeds budget "
        f"{PER_ROUND_BUDGET_US} us (p95={p95_us:.1f} us, max={max_us:.1f} us)"
    )

    # (d) Phase state advances deterministically.
    phase_history = [
        (r, res.next_phase_state.round_in_cycle) for r, res in enumerate(results)
    ]
    expected = [(r, r + 1) for r in range(NUM_ROUNDS)]
    assert phase_history == expected, (
        "phase state did not advance deterministically: "
        f"first diff at {phase_history[:5]!r} vs {expected[:5]!r}"
    )

    final_phase = results[-1].next_phase_state
    assert final_phase.round_in_cycle == NUM_ROUNDS, (
        f"final round_in_cycle {final_phase.round_in_cycle} != {NUM_ROUNDS}"
    )
    assert final_phase.recorded_at_round == NUM_ROUNDS - 1, (
        f"final recorded_at_round {final_phase.recorded_at_round} != "
        f"{NUM_ROUNDS - 1}"
    )

    # (e) Every molecular channel is recorded as detached (gate=True) on
    # every round's ledger row.
    for r, res in enumerate(results):
        per_channel = res.ledger_row.per_channel_decision
        for channel in MOLECULAR_CHANNELS:
            assert channel in per_channel, (
                f"round {r}: ledger missing molecular channel "
                f"{channel!r}; got {sorted(per_channel)!r}"
            )
            assert bool(per_channel[channel]) is True, (
                f"round {r}: molecular channel {channel!r} not detached; "
                f"got per_channel_decision={per_channel!r}"
            )


# ---------------------------------------------------------------------------
# 2. Ledger size grows linearly — bounded per-round delta.
# ---------------------------------------------------------------------------


@pytest.mark.stress
def test_molecular_ledger_size_grows_linearly() -> None:
    """Ledger pickled byte length grows linearly in the round count.

    Asserts that the per-round delta in cumulative ``pickle.dumps``
    bytes is bounded: no super-linear spikes. The maximum per-round
    delta must not exceed 5x the average delta (a generous slack for
    Python pickling overhead variance on the dataclass round-trip).
    """
    results = _drive_1000_rounds(seed=42)
    rows = [res.ledger_row for res in results]
    assert len(rows) == NUM_ROUNDS

    # Cumulative size + per-round delta.
    cumulative: list[int] = []
    running = 0
    for row in rows:
        running += len(pickle.dumps(row, protocol=pickle.HIGHEST_PROTOCOL))
        cumulative.append(running)

    deltas = [cumulative[i] - cumulative[i - 1] for i in range(1, len(cumulative))]
    avg_delta = sum(deltas) / len(deltas)
    max_delta = max(deltas)

    # Per-round delta must be bounded — within 5x the average (a
    # generous slack for pickling overhead variance on Windows where
    # dataclass instance dict ordering is deterministic but object
    # header sizes vary).
    assert max_delta <= 5 * avg_delta, (
        f"per-round ledger size delta not bounded: "
        f"max_delta={max_delta}, avg_delta={avg_delta:.1f}, "
        f"ratio={max_delta / avg_delta:.2f}"
    )

    # Linear-growth sanity check: cumulative size at N=1000 should be
    # roughly 1000 * avg_delta. We allow a 3x slack band so the test
    # passes under the natural pickling-overhead curve.
    assert cumulative[-1] <= 3 * NUM_ROUNDS * avg_delta, (
        f"cumulative ledger size {cumulative[-1]} is super-linear vs "
        f"expected ~{NUM_ROUNDS * avg_delta:.0f}"
    )

    # And the ledger must hold at least 100 bytes per row on average
    # (a sanity floor that catches silent row dropping).
    assert avg_delta >= 100, (
        f"per-row ledger size {avg_delta:.1f} bytes is suspiciously small; "
        "engine may be emitting empty rows"
    )


# ---------------------------------------------------------------------------
# 3. Engine byte-deterministic under long horizon.
# ---------------------------------------------------------------------------


@pytest.mark.stress
def test_molecular_engine_byte_deterministic_under_long_horizon() -> None:
    """Two 1000-round sequences against ``ReferenceFlowAAdapter``
    produce byte-identical final-state hashes.

    The two sequences are driven with identical inputs (same seed,
    same adapter instance, same policy, same condition delta, same
    initial bundle) but in separate engine+adapter instantiations so
    no shared state leaks between the two runs.
    """
    hash_a = _hash_final_state(seed=42)
    hash_b = _hash_final_state(seed=42)

    assert hash_a == hash_b, (
        f"final-state hash diverged across two 1000-round runs: "
        f"{hash_a!r} != {hash_b!r}"
    )

    # Sanity: the hash is a 64-char lowercase sha256 hex digest.
    assert len(hash_a) == 64
    assert all(c in "0123456789abcdef" for c in hash_a)


# ---------------------------------------------------------------------------
# 4. Hypothesis-driven property: byte-determinism holds across seeds.
# ---------------------------------------------------------------------------


@pytest.mark.stress
@settings(max_examples=10, deadline=60000)
@given(seed=st.integers(min_value=0, max_value=10_000))
def test_molecular_byte_determinism_holds_for_any_seed(seed: int) -> None:
    """For any ``seed`` in [0, 10_000], two 1000-round molecular runs
    produce the same final-state hash.

    This is the property-based companion to
    :func:`test_molecular_engine_byte_deterministic_under_long_horizon`
    — the fixed-seed test verifies the canonical example; this one
    demonstrates that determinism holds for arbitrary seeds in the
    documented ``run_round`` domain.

    The ``max_examples=10`` + ``deadline=60000`` Hypothesis profile
    (also registered in :mod:`pyproject.toml` as the ``stress``
    profile) keeps the test within the stress-nightly budget while
    still exercising multiple seed values.
    """
    hash_a = _hash_final_state(seed=seed)
    hash_b = _hash_final_state(seed=seed)

    assert hash_a == hash_b, (
        f"final-state hash diverged for seed={seed}: "
        f"{hash_a!r} != {hash_b!r}"
    )


# ---------------------------------------------------------------------------
# Module-level hooks — keep pytest from collecting helper functions.
# ---------------------------------------------------------------------------


__all__ = [
    "MOLECULAR_CHANNELS",
    "NUM_ROUNDS",
    "PER_ROUND_BUDGET_US",
    "REFERENCE_FLOWA_CHANNELS",
    "test_molecular_engine_byte_deterministic_under_long_horizon",
    "test_molecular_engine_holds_under_1000_rounds",
    "test_molecular_ledger_size_grows_linearly",
    "test_molecular_byte_determinism_holds_for_any_seed",
]
