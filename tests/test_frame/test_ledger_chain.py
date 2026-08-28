"""Incremental (streaming) ledger-chain verification."""

from __future__ import annotations

from dataclasses import replace

import pytest

from adaptive_reflow.frame.engine import (
    LedgerRow,
    build_ledger_row,
    verify_ledger_chain,
)
from adaptive_reflow.frame.ledger_chain import (
    ChainVerification,
    LedgerChain,
    LedgerChainError,
    verify_ledger_chain_incremental,
)


def _chain_rows(n: int) -> list[LedgerRow]:
    """Build a valid ``n``-row chain via the canonical engine builder."""
    rows: list[LedgerRow] = []
    prev: str | None = None
    for r in range(n):
        row = build_ledger_row(
            round_index=r,
            policy_hash=f"policy-{r}",
            bundle_digest=f"bundle-{r}",
            source_round=max(0, r - 1),
            applied_policy_hash=f"applied-{r}",
            audit_codes=("cosine_baseline",),
            per_channel_decision={"xy": True},
            prev_ledger_row_hash=prev,
        )
        rows.append(row)
        prev = row.row_hash
    return rows


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_chain_accepts_a_valid_sequence() -> None:
    rows = _chain_rows(8)
    chain = LedgerChain()
    for row in rows:
        chain.append(row)
    assert len(chain) == 8
    assert chain.head_hash == rows[-1].row_hash
    assert chain.rows == tuple(rows)


def test_chain_agrees_with_the_canonical_verifier() -> None:
    rows = _chain_rows(6)
    chain = LedgerChain(rows)
    assert chain.verify_full().ok
    assert verify_ledger_chain(tuple(rows))[0]


def test_constructor_seeding_matches_incremental_appends() -> None:
    rows = _chain_rows(5)
    seeded = LedgerChain(rows)
    appended = LedgerChain()
    appended.extend(rows)
    assert seeded.head_hash == appended.head_hash
    assert seeded.rows == appended.rows


def test_empty_chain_is_vacuously_valid() -> None:
    chain = LedgerChain()
    assert len(chain) == 0
    assert chain.head_hash is None
    assert chain.verify_incremental().ok
    assert chain.verify_full().ok


# ---------------------------------------------------------------------------
# Quantitative target: O(1) hashes per row
# ---------------------------------------------------------------------------


def test_incremental_verification_costs_one_hash_per_row() -> None:
    rows = _chain_rows(64)
    chain = LedgerChain()
    for row in rows:
        chain.append(row)
    assert chain.hash_computations == 64


def test_incremental_beats_repeated_full_verification_by_32x() -> None:
    """P2 #40 target: ``R`` hashes instead of ``R (R + 1) / 2``.

    Verifying after every append with the full walker costs the
    triangular number; the incremental chain costs ``R``. At ``R = 64``
    that is a ``32.5x`` reduction.
    """
    n_rows = 64
    rows = _chain_rows(n_rows)

    incremental = LedgerChain()
    for row in rows:
        incremental.append(row)
    incremental_hashes = incremental.hash_computations

    # Cost of verifying-after-every-append with the full walker.
    full_walk_hashes = sum(range(1, n_rows + 1))

    assert incremental_hashes == n_rows
    assert full_walk_hashes / incremental_hashes >= 32.0


def test_verify_incremental_recomputes_nothing() -> None:
    chain = LedgerChain(_chain_rows(10))
    before = chain.hash_computations
    verification = chain.verify_incremental()
    assert isinstance(verification, ChainVerification)
    assert verification.ok
    assert verification.hash_computations == 0
    assert chain.hash_computations == before


# ---------------------------------------------------------------------------
# Tamper detection
# ---------------------------------------------------------------------------


def test_tampered_payload_is_rejected_at_append_time() -> None:
    rows = _chain_rows(4)
    tampered = replace(rows[2], audit_codes=("tampered",))
    chain = LedgerChain(rows[:2])
    with pytest.raises(LedgerChainError) as excinfo:
        chain.append(tampered)
    assert excinfo.value.index == 2
    # Fail-closed: the bad row was not accepted.
    assert len(chain) == 2
    assert chain.head_hash == rows[1].row_hash


def test_broken_linkage_is_rejected() -> None:
    rows = _chain_rows(3)
    chain = LedgerChain(rows[:1])
    with pytest.raises(LedgerChainError):
        chain.append(rows[2])


def test_non_none_anchor_is_rejected() -> None:
    rows = _chain_rows(2)
    with pytest.raises(LedgerChainError):
        LedgerChain([rows[1]])


def test_round_index_regression_is_rejected() -> None:
    rows = _chain_rows(3)
    regressed = replace(rows[2], round_index=0)
    chain = LedgerChain(rows[:2])
    with pytest.raises(LedgerChainError):
        chain.append(regressed)


def test_non_ledger_row_is_rejected() -> None:
    chain = LedgerChain()
    with pytest.raises(LedgerChainError):
        chain.append("not-a-row")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Functional wrapper
# ---------------------------------------------------------------------------


def test_functional_wrapper_localises_the_break() -> None:
    rows = _chain_rows(6)
    rows[4] = replace(rows[4], selected_bundle_digest="swapped")
    result = verify_ledger_chain_incremental(rows)
    assert not result.ok
    assert result.length == 4
    assert "row[4]" in result.error
    # Short-circuits: only the rows up to and including the break were hashed.
    assert result.hash_computations == 5


def test_functional_wrapper_accepts_a_clean_chain() -> None:
    rows = _chain_rows(7)
    result = verify_ledger_chain_incremental(rows)
    assert result.ok
    assert result.error == ""
    assert result.length == 7
    assert result.hash_computations == 7
    assert result.head_hash == rows[-1].row_hash
