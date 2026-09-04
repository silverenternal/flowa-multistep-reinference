"""Tests for ``tools/run_mol_eval_safe.py``.

The safe wrapper (commit 28e3bf9) sets an RLIMIT_AS cap via
``resource.setrlimit`` in a ``preexec_fn`` so a runaway RDKit+FCD eval
cannot exceed the configured GB. It also puts the child in its own
process group (``os.setsid``) so a hang can be killed with
``os.killpg(SIGTERM)`` then ``SIGKILL`` after a 10 s grace.

These tests cover:

* ``--help`` exits cleanly and prints the cap banner (so we know the
  argparse + banner-print path still work after future edits).
* The wrapper's stderr contains ``[run_mol_eval_safe] cap=...`` so log
  scrapers can detect whether an eval was wrapped.

The tests do NOT exercise the RLIMIT_AS enforcement itself (that
would require a fixture that intentionally allocates >1 GB, which is
expensive and out of scope for the watchdog). The N=100 happy-path RSS
check that motivated this wrapper is in the commit ``28e3bf9``
documentation (``docs/CONSOLIDATED_RESULTS.md`` §8).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
WRAPPER_PATH: Path = REPO_ROOT / "tools" / "run_mol_eval_safe.py"
RUNNER_PATH: Path = REPO_ROOT / "tools" / "run_mol_eval.py"


def test_help_flag_exits_cleanly() -> None:
    """``--help`` must exit 0 and print argparse usage."""
    result = subprocess.run(
        [sys.executable, str(WRAPPER_PATH), "--help"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"
    assert "--cap-gb" in result.stdout
    assert "--timeout-sec" in result.stdout


def test_wrapper_around_help_emits_cap_banner() -> None:
    """Running the bare ``run_mol_eval.py --help`` under the wrapper
    exits 0 and prints ``[run_mol_eval_safe] cap=4GB`` to stderr.

    Verifies that the wrapper's child-spawn path works for a trivial
    no-RDKit workload (just argparse). The 4 GB cap is well above the
    Python + numpy import footprint; 1 GB was too tight because numpy
    mmap's a large OpenBLAS region at import time and RLIMIT_AS counts
    all mappings (shared libs + mmap regions), not just RSS.

    Note: the wrapper does ``subprocess.Popen(args.rest, ...)`` with
    no explicit ``executable=``, so the first element of ``args.rest``
    must itself be executable. We pass ``sys.executable`` as the first
    element after ``--`` so the wrapper re-invokes Python on
    ``run_mol_eval.py`` rather than exec'ing the script directly.
    """
    result = subprocess.run(
        [
            sys.executable,
            str(WRAPPER_PATH),
            "--cap-gb",
            "4",
            "--",
            sys.executable,
            str(RUNNER_PATH),
            "--help",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    assert result.returncode == 0, (
        f"wrapper exited {result.returncode}; stderr: {result.stderr!r}"
    )
    assert "[run_mol_eval_safe] cap=4GB" in result.stderr, (
        f"expected cap=4GB banner in stderr; got: {result.stderr!r}"
    )
    # The wrapped child emits the runner's --help text on stdout.
    assert "--input" in result.stdout
    assert "--output" in result.stdout