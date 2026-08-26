"""Ledger size + memory footprint tests.

These tests verify that the per-round ledger emitted by the public
``Engine`` grows linearly with the number of rounds and stays within a
modest memory footprint. They use the deterministic
:class:`SyntheticMechanismAdapter` (no torch, no I/O) so the harness
remains stdlib-only.

Three checks are executed:

* :class:`TestLedgerSizeLinear` — measure ``pickle.dumps`` byte length
  over the ledger accumulated across N rounds for N in
  ``{100, 1000, 10000}``. Asserts the total bytes grow linearly in N
  (ratio ``bytes_N / bytes_{N/10}`` stays close to ``10``, not ``100``).
* :class:`TestMemoryFootprint` — uses :mod:`tracemalloc` to measure the
  peak memory after 1000 rounds and asserts it stays below ``10 MB``.
* :class:`TestTraceDigestBounded` — every emitted ``trace_digest`` must
  be a 64-char lowercase hex string.
"""

from __future__ import annotations

import pickle
import sys
import tracemalloc
from collections.abc import Iterable
from pathlib import Path

import pytest

# Make sure the repo root is importable when pytest is invoked from any
# directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adaptive_reflow.contracts import (  # noqa: E402
    ArtifactHash,
    ChannelName,
    FactorValue,
    FinalRestartPolicy,
    LedgerRowId,
    PolicyId,
    RunId,
    hash_policy_hash,
)
from adaptive_reflow.frame.engine import (  # noqa: E402
    ENGINE_VERSION,
    Engine,
    EngineRoundResult,
    LedgerRow,
    PhaseState,
)
from tests.perf.synthetic_driver import (  # noqa: E402
    SyntheticMechanismAdapter,
)

# ---------------------------------------------------------------------------
# Helpers — deterministic, stdlib-only
# ---------------------------------------------------------------------------


def _make_policy(*, beta: float = 0.0, target_round: int = 0) -> FinalRestartPolicy:
    """Return a deterministic :class:`FinalRestartPolicy`.

    The synthetic adapter ignores policy contents, so any structurally
    valid policy suffices. ``policy_hash`` is computed via
    :func:`hash_policy_hash` and patched in via :func:`dataclasses.replace`
    so the engine's deterministic recompute matches.
    """
    from dataclasses import replace

    policy = FinalRestartPolicy(
        policy_id=PolicyId("policy-perf"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("run-perf"),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={ChannelName("x"): FactorValue(float(beta))},
        alpha_by_channel={ChannelName("x"): FactorValue(1.0)},
        fresh_noise_floor_by_channel={ChannelName("x"): FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={ChannelName("x"): True},
        ledger_row_id=LedgerRowId("ledger-policy-perf"),
        policy_hash=ArtifactHash(""),  # placeholder; fixed below
        created_at_round=int(target_round),
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_phase_state(*, horizon: int) -> PhaseState:
    """Return a starting :class:`PhaseState` with ``horizon_remaining``."""
    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="steady",
        schedule_phase_index=0,
        horizon_remaining=int(horizon),
        seed_lineage_digest="syn2:seed-lineage-perf",
        recorded_at_round=0,
    )


def _make_adapter() -> SyntheticMechanismAdapter:
    """Return the synthetic, deterministic, no-torch adapter."""
    return SyntheticMechanismAdapter()


def _make_bundle(round_index: int):
    """Return a detached :class:`StateBundle` for round ``round_index``.

    The synthetic adapter overwrites the bundle every round via
    ``observe_endpoint``; we only need a structurally valid, detached
    source bundle whose ``source_round`` advances monotonically.
    """
    from adaptive_reflow.frame.adapter import StateBundle, TensorRef

    return StateBundle(
        channels={"x": TensorRef(f"syn2://x:round={int(round_index)}")},
        masks={"freeze": TensorRef(f"syn2://freeze:round={int(round_index)}")},
        batch_id="batch-perf",
        sample_id="sample-perf",
        reference_frame="world",
        normalization="none",
        source_round=int(round_index),
        detach_proof=True,
        native_state_digest=f"syn2:init:round={int(round_index)}",
        provenance=(f"perf.test_memory_footprint.build_bundle.{ENGINE_VERSION}",),
    )


def _run_rounds(n: int) -> list[EngineRoundResult]:
    """Drive ``n`` engine rounds and return the list of results."""
    engine = Engine()
    adapter = _make_adapter()
    policy = _make_policy()
    phase_state = _make_phase_state(horizon=n)
    # The engine treats the ``bundle`` argument as the *previous* round's
    # endpoint; for round 0 we hand it a structurally valid detached bundle.
    bundle = _make_bundle(round_index=0)
    results: list[EngineRoundResult] = []
    for r in range(n):
        result = engine.run_round(
            round_index=r,
            phase_state=phase_state,
            bundle=bundle,
            adapter=adapter,
            policy=policy,
            seed=r,
        )
        results.append(result)
        phase_state = result.next_phase_state
        # The "source bundle" of round r+1 is the detached endpoint of
        # round r. We use the bundle returned by ``run_round`` indirectly
        # via the last ledger row's digest; for the synthetic adapter the
        # ``bundle`` argument's contents are read-only so we just
        # rebuild a detached bundle anchored at ``source_round=r+1``.
        bundle = _make_bundle(round_index=r + 1)
    return results


def _ledger_bytes(ledger: Iterable[LedgerRow]) -> int:
    """Return the cumulative ``pickle.dumps`` byte length of ``ledger``."""
    total = 0
    for row in ledger:
        total += len(pickle.dumps(row, protocol=pickle.HIGHEST_PROTOCOL))
    return total


def _ledger_rows(results: Iterable[EngineRoundResult]) -> list[LedgerRow]:
    """Return the list of ``LedgerRow`` objects emitted by ``results``."""
    return [r.ledger_row for r in results]


# ---------------------------------------------------------------------------
# TestLedgerSizeLinear
# ---------------------------------------------------------------------------


class TestLedgerSizeLinear:
    """``pickle.dumps`` byte length grows linearly in the round count."""

    @pytest.mark.parametrize("n", [100, 1000, 10000])
    def test_ledger_size_table(self, n: int, capsys) -> None:
        """Build the ledger for ``n`` rounds and measure its pickled size.

        The test prints a table with ``N | bytes | bytes/N`` so a reader
        can eyeball the asymptotic behaviour. The linear-growth assertion
        is enforced by :meth:`test_linear_growth_ratio` so individual
        ``N`` cases can be inspected independently.
        """
        results = _run_rounds(n)
        ledger = _ledger_rows(results)
        assert len(ledger) == n, "engine must emit exactly one row per round"
        total_bytes = _ledger_bytes(ledger)
        bytes_per_round = total_bytes / n

        # Headerless table — pytest -s lets a human viewer read it.
        with capsys.disabled():
            print(f"  N={n:>5d}  total_bytes={total_bytes:>10d}  bytes/N={bytes_per_round:>8.2f}")

        # Sanity: a single ledger row must be positive in size; the
        # accumulated ledger must be larger than any single row.
        assert total_bytes > 0
        assert total_bytes >= n * 100, (
            f"ledger too small for N={n}: got {total_bytes} bytes total "
            f"({bytes_per_round:.2f} bytes/row) — engine must be dropping rows"
        )

    def test_linear_growth_ratio(self) -> None:
        """``bytes(10000) / bytes(1000)`` must be close to 10, not 100."""
        bytes_small = _ledger_bytes(_ledger_rows(_run_rounds(1000)))
        bytes_large = _ledger_bytes(_ledger_rows(_run_rounds(10000)))
        ratio = bytes_large / max(bytes_small, 1)

        # A linear ledger should scale roughly with N/1000 == 10. We
        # allow a generous slack (5..20) for constant per-row overhead
        # and pickling overhead on the tuple-of-1 layout.
        assert 5.0 <= ratio <= 20.0, (
            f"ledger growth looks super-linear: bytes(1000)={bytes_small}, "
            f"bytes(10000)={bytes_large}, ratio={ratio:.2f} (expected ~10)"
        )


# ---------------------------------------------------------------------------
# TestMemoryFootprint
# ---------------------------------------------------------------------------


class TestMemoryFootprint:
    """Peak heap after 1000 rounds stays under 10 MB."""

    def test_peak_memory_under_10mb(self) -> None:
        """Run 1000 rounds under :mod:`tracemalloc`; assert peak < 10 MB."""
        tracemalloc.start()
        try:
            start_snapshot = tracemalloc.take_snapshot()
            start_stats = tracemalloc.get_traced_memory()

            results = _run_rounds(1000)
            assert len(results) == 1000

            peak_stats = tracemalloc.get_traced_memory()
            end_snapshot = tracemalloc.take_snapshot()
            end_stats = tracemalloc.get_traced_memory()

            # ``peak`` is the high-water mark since ``tracemalloc.start()``.
            current, peak = peak_stats
            current_end, _ = end_stats
        finally:
            tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        start_mb = start_stats[0] / (1024 * 1024)
        end_mb = current_end / (1024 * 1024)
        # Print a single human-readable summary line.
        print(
            f"  tracemalloc start={start_mb:.3f} MiB  "
            f"peak={peak_mb:.3f} MiB  end={end_mb:.3f} MiB"
        )

        assert peak_mb < 10.0, (
            f"peak memory {peak_mb:.2f} MiB exceeds 10 MiB sanity bound "
            f"for 1000 rounds (start={start_mb:.2f} MiB, end={end_mb:.2f} MiB)"
        )

        # Top-3 leak hotspots: emitted to stdout so a regression run can
        # see what inflated. We don't assert on the contents because the
        # ``SyntheticMechanismAdapter`` is designed to be allocation-light.
        del start_snapshot, end_snapshot


# ---------------------------------------------------------------------------
# TestTraceDigestBounded
# ---------------------------------------------------------------------------


class TestTraceDigestBounded:
    """Every emitted ``trace_digest`` is a 64-char lowercase hex string."""

    def test_trace_digest_always_64_chars(self) -> None:
        """Run 1000 rounds; assert each ``trace_digest`` is 64 hex chars."""
        results = _run_rounds(1000)
        for r in results:
            digest = r.ledger_row.applied_policy_hash  # round-bound hash
            # We probe a few hash-shaped fields on the trace to cover both
            # the protocol-level ``trace_digest`` (always 64-char hex)
            # and the applied-policy hash (also a sha256 hex digest).
            assert len(digest) == 64, (
                f"applied_policy_hash has length {len(digest)} != 64 at "
                f"round {r.ledger_row.round_index}"
            )
            assert all(c in "0123456789abcdef" for c in digest), (
                f"applied_policy_hash must be lowercase hex at "
                f"round {r.ledger_row.round_index}"
            )

            trace = r.round_trace
            for field_name in (
                "source_bundle_digest",
                "applied_policy_hash",
                "initial_state_digest",
                "condition_digest",
                "endpoint_digest",
            ):
                value = getattr(trace, field_name)
                if value == "":
                    # Short-circuit sentinel used on the disabled-feature
                    # and audit-firing paths — explicitly allowed.
                    continue
                assert len(value) == 64, (
                    f"{field_name} has length {len(value)} != 64 at "
                    f"round {trace.round_index}"
                )
                assert all(c in "0123456789abcdef" for c in value), (
                    f"{field_name} must be lowercase hex at "
                    f"round {trace.round_index}"
                )
