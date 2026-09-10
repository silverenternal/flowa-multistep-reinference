"""Wave 97.D — Hard N-record assertion + summary JSON for sweep drivers.

Closes the Wave 96 reality-check gap: agents wrote ``--max-records=5``,
``--upstream-n-samples=10``, or no cap enforcement, then claimed a
``N=1000 sweep`` (see ``docs/audit/wave96-status-reality-check.md``).
This helper makes the N-shortcut UNRECOVERABLE — when ``n_requested`` is
explicitly set and ``n_actual`` < ``n_requested``, the sweep driver
raises ``RuntimeError`` rather than silently writing a smaller summary.

Public API
----------

- :func:`assert_n_records_match`: raises ``RuntimeError`` with the
  Wave-96 message when ``n_records_actual < n_records_requested`` and
  ``n_records_requested`` was explicitly set (>0). When the user
  passes ``0`` or ``None`` for the cap (i.e. "process every record in
  the input file"), the assertion is a no-op — debug / smoke runs
  are not blocked.
- :func:`write_summary_with_n_keys`: adds the two required Wave-97.D
  keys to the summary dict — ``sweep_n_records_actual`` and
  ``sweep_n_records_requested`` — so downstream consumers can
  verify the N contract was honored without parsing the error log.
- :func:`min_required_records_for_cap`: convenience helper for callers
  that want to know the effective minimum without raising.

Both functions are intentionally stdlib-only (no torch / numpy
imports) so they can be imported from any sweep driver regardless
of which venv the sweep was launched from.
"""
from __future__ import annotations

import json
from typing import Any

__all__ = [
    "assert_n_records_match",
    "assert_n_records_match_with_file_count",
    "write_summary_with_n_keys",
    "min_required_records_for_cap",
]


def min_required_records_for_cap(n_requested: int | None) -> int:
    """Return the minimum records that must be processed for a cap.

    When ``n_requested`` is ``None`` or ``<= 0``, no cap is in force
    and the helper returns 0 (= "no minimum, debug runs allowed").
    Otherwise the cap is the effective floor for the assertion.

    Parameters
    ----------
    n_requested
        The cap value the user passed to the sweep driver. Conventional
        ``0`` or ``None`` means "no cap" (process every record in the
        input file); any positive int means "process at most N".
    """
    if n_requested is None or int(n_requested) <= 0:
        return 0
    return int(n_requested)


def assert_n_records_match(
    n_records_actual: int,
    n_records_requested: int | None,
    *,
    sweep_name: str = "sweep",
    context: dict[str, Any] | None = None,
) -> None:
    """Hard assert that the sweep processed at least ``n_records_requested``.

    Raises ``RuntimeError`` with the Wave-96 reality-check message when
    the cap was explicitly set (>0) but the sweep processed fewer
    records. When the cap is ``0`` or ``None`` (debug / smoke mode),
    the assertion is a no-op — agents can still pass ``--max-records=5``
    for fast feedback without tripping the assertion.

    The error message follows the Wave 96 reality-check template:
    ``"N=<actual> <sweep> processed, expected N=<requested>. Aborting.
    This is the Wave 96 reality-check — no silent N less than
    requested N."``

    Parameters
    ----------
    n_records_actual
        Number of records the sweep actually processed. This is the
        per-arm count (records_processed in the per-loop counter,
        ``n_seqs`` in the summary, etc. — caller chooses).
    n_records_requested
        The cap value the user passed. Conventional semantics:
        ``None``/``0`` = no cap; positive int = process at least N.
    sweep_name
        Human-readable name for the sweep (printed in the error +
        summary) so the agent can locate the offending driver from
        the traceback.
    context
        Optional dict of extra context (skip reasons, file path, etc.)
        that gets serialised into the ``RuntimeError`` message.

    Raises
    ------
    RuntimeError
        When ``n_records_requested > 0`` and
        ``n_records_actual < n_records_requested``. The message
        references Wave 96 so the failure mode is self-documenting.
    """
    min_required = min_required_records_for_cap(n_records_requested)
    if min_required <= 0:
        # No cap was set — debug / smoke mode. Allow any N.
        return
    if int(n_records_actual) >= min_required:
        return
    ctx_str = ""
    if context:
        ctx_str = " Context: " + json.dumps(dict(context), sort_keys=True)
    raise RuntimeError(
        f"N={int(n_records_actual)} {sweep_name} processed, "
        f"expected N={min_required}. Aborting. "
        f"This is the Wave 96 reality-check — no silent N less than "
        f"requested N.{ctx_str}"
    )


def assert_n_records_match_with_file_count(
    n_records_actual: int,
    n_records_requested: int | None,
    file_record_count: int,
    *,
    sweep_name: str = "sweep",
    context: dict[str, Any] | None = None,
) -> None:
    """Wave 97.D — file-aware variant of :func:`assert_n_records_match`.

    Fires the strict Wave 96 reality-check assertion **only** when the
    input file had enough records to satisfy the requested cap:

    - When ``n_records_requested <= 0`` (no cap set): no-op (debug mode).
    - When ``file_record_count < n_records_requested`` (file is the
      binding cap, not the request): no-op — the file ran dry.
    - When ``file_record_count >= n_records_requested`` (the file was
      supposed to provide N records) AND
      ``n_records_actual < n_records_requested``: raises the Wave 96
      ``RuntimeError`` message — the sweep silently produced fewer
      records than the file allowed.

    Use this variant for sweep drivers that consume a user-supplied
    input file (e.g. ``tools/upstream_eval.py`` where the file is
    the per-cell coords file written by ``tools/eval/sweep.py`` — file
    has only a handful of records when ``n_molecules=1``, so the
    cap is the file, not the upstream ``--upstream-n-samples`` knob).
    For drivers that consume a fixed-N=1000 reference file, use the
    stricter :func:`assert_n_records_match` instead.

    Parameters
    ----------
    n_records_actual
        Records the sweep actually processed.
    n_records_requested
        The cap value the user passed. ``None`` / ``0`` = no cap.
    file_record_count
        Number of records the input file contained (= the natural
        cap for any sweep reading the file from start to end). When
        this is < ``n_records_requested``, the file is the binding
        constraint and the assertion is skipped.
    sweep_name
        Human-readable name for the sweep (printed in the error).
    context
        Optional dict of extra context (skip reasons, file path, etc.)
        that gets serialised into the ``RuntimeError`` message.
    """
    if n_records_requested is None or int(n_records_requested) <= 0:
        return
    if int(file_record_count) < int(n_records_requested):
        return
    assert_n_records_match(
        n_records_actual,
        n_records_requested,
        sweep_name=sweep_name,
        context=context,
    )


def write_summary_with_n_keys(
    summary: dict[str, Any],
    *,
    n_records_actual: int,
    n_records_requested: int | None,
    sweep_name: str = "sweep",
) -> dict[str, Any]:
    """Mutate ``summary`` to add the Wave-97.D N-contract keys.

    Adds two separate keys to the summary dict so downstream consumers
    can verify the N contract was honored without re-parsing the sweep
    loop:

    - ``sweep_n_records_actual`` — the count the driver actually
      processed (= ``n_processed`` / ``n_seqs`` / whatever the
      caller passed in).
    - ``sweep_n_records_requested`` — the cap value the user passed
      (or ``0`` / ``None`` if no cap was set). ``0`` means "no cap".

    Also adds ``sweep_n_records_match`` (bool) = True when the
    requested N was honored OR no N was requested. This is the
    single boolean downstream consumers should key on.

    Returns the same dict object (for chaining).

    Parameters
    ----------
    summary
        The summary dict the sweep driver is about to write to
        disk. Mutated in place + returned.
    n_records_actual
        Number of records the sweep actually processed.
    n_records_requested
        The cap value the user passed. ``None`` / ``0`` = no cap.
    sweep_name
        Human-readable name for the sweep (stored in
        ``sweep_name`` key for audit traceability).
    """
    actual = int(n_records_actual)
    requested = (
        int(n_records_requested) if n_records_requested is not None else 0
    )
    match = bool(requested <= 0 or actual >= requested)
    summary["sweep_n_records_actual"] = actual
    summary["sweep_n_records_requested"] = requested
    summary["sweep_n_records_match"] = match
    summary["sweep_name"] = sweep_name
    return summary