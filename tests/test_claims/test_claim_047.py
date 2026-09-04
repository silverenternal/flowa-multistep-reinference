"""CLM-047: Stress-nightly Windows path bug closed + Python version matrix landed.

Asserted by docs/CLAIMS.md:1695-1744.
Four CI-gate issues are pinned:
    T-04.3: stress-nightly.yml uses `python` (not the Windows-only
            `.venv/Scripts/python.exe`).
    T-04.2: cpu-tests.yml references the canonical
            `test_no_molecular_import.py` (not the phantom
            `test_universal_imports_no_molecular.py`) in its `run:` step.
    T-04.5: ci.yml runs the matrix on Python `[3.12, 3.13]` on
            `lint-types` and `test-docs` jobs.

We pin these three YAML facts by extracting the `run:` command lines
(comments can mention historical filenames for context; the operative
signal is the executable command).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _read(rel: str) -> str:
    return (WORKFLOWS / rel).read_text()


_RUN_LINE_RE = re.compile(r"^\s*run:\s*(.+?)\s*$", re.MULTILINE)


def _run_commands(text: str) -> list[str]:
    """Yield each `run:` command body (concatenated continuation lines too)."""
    return _RUN_LINE_RE.findall(text)


def test_claim_047_t_04_3_stress_run_invokes_python() -> None:
    """stress-nightly.yml run step uses `python` (not `.venv/Scripts/python.exe`)."""
    cmds = " ".join(_run_commands(_read("stress-nightly.yml")))
    assert "python -m pytest" in cmds
    assert ".venv/Scripts/python.exe" not in cmds


def test_claim_047_t_04_2_cpu_tests_runs_canonical_test_path() -> None:
    """cpu-tests.yml run step targets the canonical test file."""
    cmds = " ".join(_run_commands(_read("cpu-tests.yml")))
    assert "test_no_molecular_import.py" in cmds
    assert "test_universal_imports_no_molecular.py" not in cmds


def test_claim_047_t_04_5_ci_runs_python_3_12_and_3_13_matrix() -> None:
    """ci.yml runs Python 3.12 + 3.13 matrix on lint-types and test-docs jobs."""
    text = _read("ci.yml")
    assert '"3.12"' in text
    assert '"3.13"' in text
