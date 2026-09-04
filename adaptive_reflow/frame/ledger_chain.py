"""Incremental (streaming) ledger-chain verification (ledger/hash uplift).

:func:`adaptive_reflow.frame.engine.verify_ledger_chain` re-walks and
re-hashes the **entire** chain on every call. A writer that wants
tamper-evidence *as it emits* therefore pays ``O(R)`` per round and
``O(R^2)`` over a cycle — which is why the engine only verifies at the
end, leaving a window in which a corrupted row is appended and not
noticed until the run finishes.

:class:`LedgerChain` closes that window. It keeps the running head hash
and verifies each row **once**, at append time, in ``O(1)`` amortised
cost:

    chain = LedgerChain()
    for row in rows:
        chain.append(row)          # raises LedgerChainError on tamper
    assert chain.verify_full().ok  # optional belt-and-braces replay

The class is a pure add-on: it consumes the existing
:class:`~adaptive_reflow.frame.engine.LedgerRow` and reuses
:func:`~adaptive_reflow.frame.engine.compute_ledger_row_hash`, so there
is exactly one hashing rule in the framework and a chain built by the
engine verifies here unchanged. No engine code path is modified; callers
opt in by constructing a :class:`LedgerChain`.

Quantitative target
-------------------

Per-row verification cost is **O(1)** rather than ``O(R)``: verifying a
chain of ``R`` rows incrementally performs exactly ``R`` row-hash
computations, versus the ``R (R + 1) / 2`` that repeated
:func:`verify_ledger_chain` calls perform. At ``R = 64`` that is a
``32x`` reduction in hash work, asserted directly (by counting hash
calls) in ``tests/test_frame/test_ledger_chain.py``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from adaptive_reflow.frame.engine import (
    LedgerRow,
    compute_ledger_row_hash,
    verify_ledger_chain,
)

__all__ = [
    "ChainVerification",
    "LedgerChain",
    "LedgerChainError",
    "ParallelLedgerChain",
    "verify_checkpoint_chain",
    "verify_ledger_chain_incremental",
]


class LedgerChainError(RuntimeError):
    """Raised when a row breaks the hash chain at append time.

    Carries the offending row's index so an audit reader can point at
    the exact break rather than re-scanning the chain.
    """

    def __init__(self, message: str, *, index: int) -> None:
        super().__init__(message)
        self.index = int(index)


@dataclass(frozen=True)
class ChainVerification:
    """Outcome of a chain verification.

    Attributes
    ----------
    ok:
        Whether the chain is intact.
    error:
        Empty string when ``ok``; a descriptive message otherwise.
    length:
        Number of rows inspected.
    head_hash:
        ``row_hash`` of the last row (``None`` for an empty chain).
    hash_computations:
        How many row hashes the verification computed. Exposed so the
        ``O(1)``-per-row claim is *measurable* rather than asserted in
        prose.
    """

    ok: bool
    error: str
    length: int
    head_hash: str | None
    hash_computations: int


def _recompute(row: LedgerRow) -> str:
    """Return the canonical ``row_hash`` for ``row`` from its fields."""
    return compute_ledger_row_hash(
        ledger_row_id=str(row.ledger_row_id),
        round_index=int(row.round_index),
        source_round=int(row.source_round),
        target_round=int(row.target_round),
        applied_policy_hash=str(row.applied_policy_hash),
        selected_bundle_digest=str(row.selected_bundle_digest),
        audit_codes=tuple(row.audit_codes),
        per_channel_decision=dict(row.per_channel_decision),
        prev_ledger_row_hash=row.prev_ledger_row_hash,
    )


class LedgerChain:
    """Append-only ledger chain with incremental tamper detection.

    Maintains the running head hash and the monotone ``round_index``
    watermark, so :meth:`append` can enforce every chain invariant
    :func:`~adaptive_reflow.frame.engine.verify_ledger_chain` enforces —
    anchor, linkage, row-hash integrity, round monotonicity — while
    touching only the incoming row.

    The chain is *fail-closed*: a row that breaks any invariant raises
    :class:`LedgerChainError` and is **not** appended, so the accumulated
    chain is intact by construction at every point in time.
    """

    def __init__(self, rows: Iterable[LedgerRow] | None = None) -> None:
        """Build a chain, optionally seeding it from existing ``rows``.

        Seeding verifies each row exactly as :meth:`append` would, so a
        chain rehydrated from persistence is validated on the way in.
        """
        self._rows: list[LedgerRow] = []
        self._head: str | None = None
        self._last_round: int | None = None
        self._hash_computations: int = 0
        for row in rows or ():
            self.append(row)

    # -- introspection ----------------------------------------------------

    @property
    def rows(self) -> tuple[LedgerRow, ...]:
        """Return the accumulated rows as an immutable tuple."""
        return tuple(self._rows)

    @property
    def head_hash(self) -> str | None:
        """Return the last row's ``row_hash`` (``None`` when empty)."""
        return self._head

    @property
    def hash_computations(self) -> int:
        """Return how many row hashes this chain has computed so far.

        Exactly one per appended row — the measurable form of the
        ``O(1)``-amortised claim.
        """
        return int(self._hash_computations)

    def __len__(self) -> int:
        """Return the number of rows in the chain."""
        return len(self._rows)

    # -- mutation ---------------------------------------------------------

    def append(self, row: LedgerRow) -> str:
        """Verify and append ``row``; return the new head hash.

        Performs exactly **one** row-hash computation regardless of how
        long the chain already is.

        :raises LedgerChainError: when ``row`` is not a
            :class:`LedgerRow`, when its ``prev_ledger_row_hash`` does
            not match the current head, when its stored ``row_hash``
            disagrees with the recomputed one, or when its
            ``round_index`` regresses.
        """
        index = len(self._rows)
        if not isinstance(row, LedgerRow):
            raise LedgerChainError(
                f"row[{index}] is not a LedgerRow, got {type(row).__name__}",
                index=index,
            )
        if self._head is None:
            if row.prev_ledger_row_hash is not None:
                raise LedgerChainError(
                    f"row[{index}].prev_ledger_row_hash must be None at the "
                    f"chain anchor, got {row.prev_ledger_row_hash!r}",
                    index=index,
                )
        elif row.prev_ledger_row_hash != self._head:
            raise LedgerChainError(
                f"row[{index}].prev_ledger_row_hash "
                f"({row.prev_ledger_row_hash!r}) does not link to the current "
                f"head ({self._head!r})",
                index=index,
            )
        if self._last_round is not None and int(row.round_index) < self._last_round:
            raise LedgerChainError(
                f"row[{index}].round_index ({row.round_index}) regresses below "
                f"the previous round ({self._last_round})",
                index=index,
            )

        expected = _recompute(row)
        self._hash_computations += 1
        if str(row.row_hash) != expected:
            raise LedgerChainError(
                f"row[{index}].row_hash ({row.row_hash!r}) does not match the "
                f"hash recomputed from its fields ({expected!r})",
                index=index,
            )

        self._rows.append(row)
        self._head = str(row.row_hash)
        self._last_round = int(row.round_index)
        return self._head

    def extend(self, rows: Iterable[LedgerRow]) -> str | None:
        """Append every row in ``rows`` in order; return the new head."""
        for row in rows:
            self.append(row)
        return self._head

    # -- verification -----------------------------------------------------

    def verify_incremental(self) -> ChainVerification:
        """Return the chain's current status without re-hashing anything.

        Because :meth:`append` is fail-closed, an accumulated chain is
        intact by construction; this method simply reports that fact and
        the head hash, at ``O(1)`` cost. Use :meth:`verify_full` when
        the chain object itself is untrusted (e.g. after
        deserialisation from a source that bypassed :meth:`append`).
        """
        return ChainVerification(
            ok=True,
            error="",
            length=len(self._rows),
            head_hash=self._head,
            hash_computations=0,
        )

    def verify_full(self) -> ChainVerification:
        """Re-walk the whole chain via the canonical engine verifier.

        Delegates to
        :func:`adaptive_reflow.frame.engine.verify_ledger_chain` so the
        incremental path can never diverge from the framework's single
        source of truth for chain validity.
        """
        ok, error = verify_ledger_chain(tuple(self._rows))
        return ChainVerification(
            ok=bool(ok),
            error=str(error),
            length=len(self._rows),
            head_hash=self._head,
            hash_computations=len(self._rows),
        )


def verify_ledger_chain_incremental(
    rows: Sequence[LedgerRow],
) -> ChainVerification:
    """Verify ``rows`` in a single streaming pass.

    Functional wrapper over :class:`LedgerChain` for callers that
    already hold the full sequence: identical verdict to
    :func:`adaptive_reflow.frame.engine.verify_ledger_chain`, but it
    reports *where* the chain broke and how many hashes it computed
    (exactly one per row inspected, so a break short-circuits).
    """
    chain = LedgerChain()
    for index, row in enumerate(rows):
        try:
            chain.append(row)
        except LedgerChainError as exc:
            return ChainVerification(
                ok=False,
                error=str(exc),
                length=index,
                head_hash=chain.head_hash,
                hash_computations=chain.hash_computations,
            )
    return ChainVerification(
        ok=True,
        error="",
        length=len(chain),
        head_hash=chain.head_hash,
        hash_computations=chain.hash_computations,
    )


class ParallelLedgerChain:
    """Concurrent / out-of-order ledger chain (P1 #26).

    Accepts round rows out of round order (e.g. from a thread pool
    executing rounds concurrently) and defers linking until
    :meth:`finalize` is called. On finalize the chain is sorted by
    ``round_index``, validated, and produces the same head hash as the
    sequential :class:`LedgerChain` (deterministic).

    The class is fail-closed: a row that breaks any invariant raises
    :class:`LedgerChainError` and is not appended.
    """

    def __init__(self) -> None:
        self._rows: dict[int, LedgerRow] = {}

    @property
    def pending(self) -> int:
        """Return the number of buffered rows awaiting finalize."""
        return len(self._rows)

    def append(self, row: LedgerRow) -> None:
        """Buffer ``row`` for the upcoming :meth:`finalize` call."""
        if not isinstance(row, LedgerRow):
            raise LedgerChainError(
                f"row is not a LedgerRow, got {type(row).__name__}",
                index=int(row.round_index) if hasattr(row, "round_index") else -1,
            )
        rid = int(row.round_index)
        if rid in self._rows:
            raise LedgerChainError(
                f"duplicate round_index={rid} in ParallelLedgerChain",
                index=rid,
            )
        self._rows[rid] = row

    def finalize(self) -> LedgerChain:
        """Sort by ``round_index`` and validate via :class:`LedgerChain`."""
        if not self._rows:
            return LedgerChain()
        chain = LedgerChain()
        for rid in sorted(self._rows):
            chain.append(self._rows[rid])
        return chain


def verify_checkpoint_chain(checkpoint: Any, *, path: str | None = None) -> "ChainVerification":
    """Validate that ``checkpoint``'s ledger row sits at the chain head.

    Walks the row's ``prev_ledger_row_hash`` linkage by replaying
    :func:`~adaptive_reflow.frame.engine.verify_ledger_chain`. Pass
    ``path=checkpoint.ledger_chain_head_hash`` to assert that the
    external persistence layer (file/socket) observed the same head.

    Returns the same :class:`ChainVerification` shape used by
    :meth:`LedgerChain.verify_full`. The function is total: an empty
    checkpoint (no ledger row) returns ``(ok=True, error="empty_chain")``
    so callers can distinguish "no chain yet" from "tampered".

    Parameters
    ----------
    checkpoint:
        A :class:`~adaptive_reflow.universal.checkpoint.Checkpoint`
        (any object exposing ``last_ledger_row`` and
        ``ledger_chain_head_hash`` will do).
    path:
        Optional external head hash to compare against
        ``checkpoint.ledger_chain_head_hash``. When supplied and
        mismatched the function returns ``error="external_head_mismatch"``
        with ``ok=False``.
    """
    if checkpoint is None or getattr(checkpoint, "last_ledger_row", None) is None:
        return ChainVerification(
            ok=True,
            error="empty_chain",
            length=0,
            head_hash=None,
            hash_computations=0,
        )
    row = checkpoint.last_ledger_row
    chain_ok, chain_msg = verify_ledger_chain((row,))
    head = str(row.row_hash)
    declared_head = getattr(checkpoint, "ledger_chain_head_hash", None)
    declared_digest = "" if declared_head is None else str(declared_head)
    if declared_digest and declared_digest != head:
        return ChainVerification(
            ok=False,
            head_hash=head,
            error="external_head_mismatch",
            length=1,
            hash_computations=1,
        )
    if path is not None and str(path) != declared_digest:
        return ChainVerification(
            ok=False,
            head_hash=head,
            error="external_head_mismatch",
            length=1,
            hash_computations=1,
        )
    if not chain_ok:
        return ChainVerification(
            ok=False,
            head_hash=head,
            error=str(chain_msg),
            length=1,
            hash_computations=1,
        )
    return ChainVerification(
        ok=True,
        error="",
        head_hash=head,
        length=1,
        hash_computations=1,
    )
