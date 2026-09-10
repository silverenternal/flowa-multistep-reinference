"""Wave 97.D — unit tests for :mod:`tools._sweep_assertion`.

Covers the Wave 96 reality-check hard assertion + summary-JSON contract:

1. :func:`assert_n_records_match` raises the Wave-96 message when the
   cap was explicitly set (>0) and the sweep produced fewer records.
2. No-op when ``n_records_requested`` is ``0`` / ``None`` (debug /
   smoke runs are not blocked — agents can pass ``--max-records=5``).
3. No-op when ``n_records_actual >= n_records_requested``.
4. :func:`assert_n_records_match_with_file_count` is file-aware:
   no-op when the file had fewer records than requested (file is
   the binding cap), fires only when the file had >= N records
   but the sweep processed fewer.
5. :func:`write_summary_with_n_keys` adds the 4 contract keys to the
   summary dict (``sweep_n_records_actual``,
   ``sweep_n_records_requested``, ``sweep_n_records_match``,
   ``sweep_name``).

Stdlib-only (no torch / numpy / pytest fixtures) so the tests are
cold-clone safe + CI-friendly.
"""
from __future__ import annotations

import importlib
import json
import os
import pathlib
import sys

import pytest

_HELPER = "tools._sweep_assertion"


def _import_helper() -> object:
    """Lazy-import ``tools._sweep_assertion`` so module-level side
    effects never run before this fixture."""
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", ".."),
    )
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    return importlib.import_module(_HELPER)


def test_assert_n_records_match_passes_when_meeting_cap() -> None:
    """Cap is set and the sweep met it — no raise."""
    helper = _import_helper()
    # Should not raise.
    helper.assert_n_records_match(
        n_records_actual=1000,
        n_records_requested=1000,
        sweep_name="test_sweep",
    )
    helper.assert_n_records_match(
        n_records_actual=2000,
        n_records_requested=1000,
        sweep_name="test_sweep",
    )


def test_assert_n_records_match_passes_when_no_cap_set() -> None:
    """``n_records_requested=None`` (= no cap) → no-op, debug mode
    is not blocked. Agents can still pass ``--max-records=5`` for
    fast feedback without tripping the assertion."""
    helper = _import_helper()
    helper.assert_n_records_match(
        n_records_actual=5,
        n_records_requested=None,
        sweep_name="test_sweep",
    )
    helper.assert_n_records_match(
        n_records_actual=0,
        n_records_requested=0,
        sweep_name="test_sweep",
    )
    helper.assert_n_records_match(
        n_records_actual=10,
        n_records_requested=0,
        sweep_name="test_sweep",
    )


def test_assert_n_records_match_raises_when_actual_below_cap() -> None:
    """Cap was set and the sweep silently produced fewer records —
    the Wave-96 reality-check must raise the explicit message.

    The message must reference Wave 96 so the failure mode is
    self-documenting (so a CI log can grep for "Wave 96" to
    surface all such failures).
    """
    helper = _import_helper()
    with pytest.raises(RuntimeError) as excinfo:
        helper.assert_n_records_match(
            n_records_actual=10,
            n_records_requested=1000,
            sweep_name="kanzi_n1000_sweep",
        )
    msg = str(excinfo.value)
    assert "N=10" in msg, (
        f"actual N missing from RuntimeError message: {msg!r}"
    )
    assert "N=1000" in msg, (
        f"expected N missing from RuntimeError message: {msg!r}"
    )
    assert "Aborting" in msg, (
        f"RuntimeError must use the Wave 96 'Aborting' wording: {msg!r}"
    )
    assert "Wave 96" in msg, (
        f"RuntimeError must reference Wave 96 for audit grep: {msg!r}"
    )
    assert "kanzi_n1000_sweep" in msg, (
        f"sweep name must appear in the error so the agent can locate "
        f"the offending driver from the traceback: {msg!r}"
    )


def test_assert_n_records_match_with_file_count_skips_when_file_short() -> None:
    """File-aware variant: when the file has fewer records than the
    requested cap, the file is the binding cap and the assertion
    must be a no-op. This is the case for tools/upstream_eval.py
    Kanzi/LineageFlow wrappers where the per-cell coords file has
    only a handful of records but the user passes
    ``--upstream-n-samples 1000``.
    """
    helper = _import_helper()
    helper.assert_n_records_match_with_file_count(
        n_records_actual=2,  # what the sweep actually processed
        n_records_requested=1000,  # user-requested N
        file_record_count=2,  # file has only 2 records
        sweep_name="run_kanzi_upstream_eval",
    )
    helper.assert_n_records_match_with_file_count(
        n_records_actual=1,
        n_records_requested=1000,
        file_record_count=1,
        sweep_name="run_flowmol3_upstream_eval",
    )


def test_assert_n_records_match_with_file_count_fires_when_file_long_enough() -> None:
    """File-aware variant: when the file has >= N records (file
    should have been able to provide N) and the sweep produced fewer,
    the assertion fires — this is the Wave 96 reality-check.
    """
    helper = _import_helper()
    with pytest.raises(RuntimeError) as excinfo:
        helper.assert_n_records_match_with_file_count(
            n_records_actual=10,
            n_records_requested=1000,
            file_record_count=1000,
            sweep_name="run_kanzi_upstream_eval",
            context={
                "sequences_path": "/tmp/coords.txt",
                "n_samples_effective": 1000,
            },
        )
    msg = str(excinfo.value)
    assert "N=10" in msg
    assert "N=1000" in msg
    assert "Wave 96" in msg
    # Context is serialised into the error so the agent can debug.
    assert "sequences_path" in msg, (
        f"context must be included in the error for debugging: {msg!r}"
    )


def test_assert_n_records_match_with_file_count_skips_when_no_cap() -> None:
    """File-aware variant + no requested cap → no-op (debug mode)."""
    helper = _import_helper()
    helper.assert_n_records_match_with_file_count(
        n_records_actual=0,
        n_records_requested=0,
        file_record_count=1000,
        sweep_name="test_sweep",
    )
    helper.assert_n_records_match_with_file_count(
        n_records_actual=0,
        n_records_requested=None,
        file_record_count=1000,
        sweep_name="test_sweep",
    )


def test_min_required_records_for_cap_handles_unset_cap() -> None:
    """``min_required_records_for_cap`` returns 0 for unset caps
    (debug mode is never blocked) and the cap value for positive ints."""
    helper = _import_helper()
    assert helper.min_required_records_for_cap(None) == 0
    assert helper.min_required_records_for_cap(0) == 0
    assert helper.min_required_records_for_cap(-1) == 0
    assert helper.min_required_records_for_cap(5) == 5
    assert helper.min_required_records_for_cap(1000) == 1000


def test_write_summary_with_n_keys_adds_4_contract_keys() -> None:
    """``write_summary_with_n_keys`` adds 4 keys: actual N, requested N,
    match boolean, sweep name. Downstream consumers key on these to
    verify the N contract was honored without re-parsing the loop."""
    helper = _import_helper()
    summary: dict[str, object] = {"tool": "test_sweep"}
    out = helper.write_summary_with_n_keys(
        summary,
        n_records_actual=1000,
        n_records_requested=1000,
        sweep_name="kanzi_n1000_sweep",
    )
    assert out is summary, "must return same dict for chaining"
    assert summary["sweep_n_records_actual"] == 1000
    assert summary["sweep_n_records_requested"] == 1000
    assert summary["sweep_n_records_match"] is True
    assert summary["sweep_name"] == "kanzi_n1000_sweep"
    # When no cap was set (0 / None), ``match`` is still True.
    helper.write_summary_with_n_keys(
        summary,
        n_records_actual=5,
        n_records_requested=0,
        sweep_name="debug_sweep",
    )
    assert summary["sweep_n_records_match"] is True
    assert summary["sweep_n_records_requested"] == 0
    # When actual < requested, ``match`` flips to False (informational
    # — the assertion itself is responsible for raising).
    helper.write_summary_with_n_keys(
        summary,
        n_records_actual=10,
        n_records_requested=1000,
        sweep_name="kanzi_n1000_sweep",
    )
    assert summary["sweep_n_records_actual"] == 10
    assert summary["sweep_n_records_requested"] == 1000
    assert summary["sweep_n_records_match"] is False


def test_write_summary_with_n_keys_handles_none_requested() -> None:
    """``n_records_requested=None`` is normalized to 0 in the summary."""
    helper = _import_helper()
    summary: dict[str, object] = {}
    helper.write_summary_with_n_keys(
        summary,
        n_records_actual=5,
        n_records_requested=None,
        sweep_name="debug_sweep",
    )
    assert summary["sweep_n_records_requested"] == 0
    assert summary["sweep_n_records_match"] is True


def test_helper_module_all_exports() -> None:
    """``__all__`` includes the 4 public symbols so callers can key
    on the public API and importlib.reload is safe across
    sweeps."""
    helper = _import_helper()
    expected = {
        "assert_n_records_match",
        "assert_n_records_match_with_file_count",
        "write_summary_with_n_keys",
        "min_required_records_for_cap",
    }
    assert expected.issubset(set(helper.__all__)), (
        f"missing exports in __all__: {expected - set(helper.__all__)}"
    )


def test_helper_module_is_stdlib_only() -> None:
    """The helper must NOT import torch / numpy / h5py etc. —
    sweep drivers in cold-clone contexts (e.g. the kanzi sidecar
    venv) need the helper to import cleanly even when the heavy
    scientific stack is unavailable. We verify this by reading the
    source file and asserting no heavy imports are present.
    """
    helper_path = pathlib.Path(__file__).parent.parent.parent / "tools" / "_sweep_assertion.py"
    assert helper_path.is_file(), f"helper module missing at {helper_path}"
    src = helper_path.read_text(encoding="utf-8")
    heavy_imports = ("import torch", "import numpy", "import h5py",
                     "from torch", "from numpy", "import scipy")
    for heavy in heavy_imports:
        assert heavy not in src, (
            f"helper module must be stdlib-only but contains {heavy!r}: {src!r}"
        )


def test_helper_module_no_external_io() -> None:
    """Sanity: helper does NOT open files / make network calls. The
    only stdlib imports allowed are json / typing. This guards
    against future drift that would break the kanzi sidecar venv
    cold-import path."""
    helper_path = pathlib.Path(__file__).parent.parent.parent / "tools" / "_sweep_assertion.py"
    src = helper_path.read_text(encoding="utf-8")
    forbidden_io = ("open(", ".read_text(", ".write_text(", "urlopen",
                    "requests.", "httpx.")
    for token in forbidden_io:
        assert token not in src, (
            f"helper must not perform IO but contains {token!r}"
        )