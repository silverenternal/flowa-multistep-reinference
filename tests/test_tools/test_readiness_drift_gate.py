"""Pins the fail-closed branch of the readiness drift gate.

``gate_drift_33`` shells out to ``grep -rn "33/33 PASS" docs/`` and treats an
empty hit list as "no drift".  ``grep`` exits 1 when it finds nothing, which is
the clean case, but it exits 2 when the scan could not run at all -- an
unreadable ``docs/``, a missing binary.  The original code mapped every status
other than 0 and 1 to ``[]``, so a scan that never happened reported the same
"0 unintended occurrences" as a scan that found nothing.  That is the mypy
gate's failure mode (``docs/audit/mypy-gate-restoration.md``) in a second
place: a gate that cannot see what it claims to check.
"""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "verify_submission_readiness.py"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("verify_submission_readiness", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # @dataclass resolves its fields through sys.modules[cls.__module__].
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fake_run(returncode: int, stdout: str = "", stderr: str = ""):
    def run(*args, **kwargs):  # noqa: ANN001, ANN002
        return subprocess.CompletedProcess(
            args=args[0] if args else [],
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    return run


def test_clean_scan_passes(tool, monkeypatch) -> None:
    """grep exits 1 when there is nothing to find; that is the passing case."""
    monkeypatch.setattr(tool.subprocess, "run", _fake_run(1))
    result = tool.gate_drift_33(tool.GateReport())
    assert result.passed is True
    assert result.skipped is False


def test_a_scan_that_could_not_run_fails(tool, monkeypatch) -> None:
    monkeypatch.setattr(
        tool.subprocess,
        "run",
        _fake_run(2, stderr="grep: docs: No such file or directory"),
    )
    result = tool.gate_drift_33(tool.GateReport())
    assert result.passed is False
    assert "could not" in result.detail or "did not run" in result.detail
    assert "No such file" in (result.error or "")
