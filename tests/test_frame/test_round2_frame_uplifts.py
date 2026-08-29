"""Round-2 frame tests: cross-channel, parallel ledger, etc."""

from __future__ import annotations

import pytest

from adaptive_reflow.frame.channel_rule_diagnostics import (
    CROSS_CHANNEL_DIRECTION,
    certify_cross_channel,
    evidence_cross_channel,
)
from adaptive_reflow.frame.ledger_chain import (
    LedgerChain,
    LedgerChainError,
    ParallelLedgerChain,
)


def _make_inputs():
    """Build a fully-valid, gate-opening set of channel-rule inputs."""
    from tests.perf.test_kernel_benchmarks import _make_channel_rule_inputs
    return _make_channel_rule_inputs()


def test_cross_channel_default_pair_certifies() -> None:
    inputs = _make_inputs()
    report = evidence_cross_channel(inputs, inputs)
    assert report.factor.startswith("cross:")
    assert report.direction in (+1, -1)


def test_cross_channel_all_factor_pairs() -> None:
    inputs = _make_inputs()
    reports = certify_cross_channel(inputs, inputs, n_points=5)
    assert set(reports) == set(CROSS_CHANNEL_DIRECTION)
    for r in reports.values():
        assert r.n_pairs > 0


def test_cross_channel_unknown_factor_pair_raises() -> None:
    inputs = _make_inputs()
    with pytest.raises(ValueError):
        evidence_cross_channel(inputs, inputs, factor_pair=("foo", "bar"))


# ---------------------------------------------------------------------------
# Parallel ledger chain
# ---------------------------------------------------------------------------


def _make_row(round_idx: int, prev_hash: str | None) -> object:
    from adaptive_reflow.frame.engine import LedgerRow, compute_ledger_row_hash

    ledger_row_id = f"row-{round_idx}"
    row_hash = compute_ledger_row_hash(
        ledger_row_id=ledger_row_id,
        round_index=int(round_idx),
        source_round=int(round_idx),
        target_round=int(round_idx),
        applied_policy_hash="policy-hash",
        selected_bundle_digest=f"digest-{round_idx}",
        audit_codes=(),
        per_channel_decision={},
        prev_ledger_row_hash=prev_hash,
    )
    return LedgerRow(
        ledger_row_id=ledger_row_id,
        round_index=int(round_idx),
        source_round=int(round_idx),
        target_round=int(round_idx),
        applied_policy_hash="policy-hash",
        selected_bundle_digest=f"digest-{round_idx}",
        audit_codes=(),
        per_channel_decision={},
        prev_ledger_row_hash=prev_hash,
        row_hash=row_hash,
    )


def test_parallel_ledger_chain_out_of_order_finalizes() -> None:
    """Out-of-order appends validate to the same head as sequential."""
    rows = [_make_row(i, None if i == 0 else None) for i in range(5)]
    # Fix the prev pointers (they were None above).
    rows = []
    chain = LedgerChain()
    for i in range(5):
        rows.append(_make_row(i, chain.head_hash))
        chain.append(rows[-1])
    head_seq = chain.head_hash

    # Now replay via ParallelLedgerChain in REVERSE order.
    par = ParallelLedgerChain()
    for r in reversed(rows):
        par.append(r)
    final = par.finalize()
    assert final.head_hash == head_seq


def test_parallel_ledger_chain_duplicate_round_raises() -> None:
    par = ParallelLedgerChain()
    par.append(_make_row(0, None))
    with pytest.raises(LedgerChainError):
        par.append(_make_row(0, None))


def test_parallel_ledger_chain_empty_finalize() -> None:
    par = ParallelLedgerChain()
    final = par.finalize()
    assert len(final) == 0
