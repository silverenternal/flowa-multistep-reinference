"""The two master reproduction verifiers must stay green.

`reproduce/verify_all_headlines.sh` (7 R-level cells, 8 scripts) and
`reproduce/09_verify_all_cell_recipes.sh` (11 paper cells) are what a reviewer
runs first. They are pure artifact reads (no GPU, <1 s), so they belong in the
default test run: `05_R5_2D_EightGaussians.sh` was broken from Wave 308 to
2026-10-29 because nothing executed it.

These tests skip when the frozen `verification_outputs/` tree is absent.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "reproduce" / "verify_all_headlines.sh"
CELLS = ROOT / "reproduce" / "09_verify_all_cell_recipes.sh"

pytestmark = pytest.mark.skipif(
    not (ROOT / "verification_outputs").is_dir(),
    reason="verification_outputs/ not present",
)


def _run(script: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )


def test_master_headline_verifier_passes() -> None:
    proc = _run(MASTER)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    assert "OK: All 8/8 reproduction checks verified" in proc.stdout


def test_master_does_not_count_the_other_master() -> None:
    """`reproduce/[0-9]*.sh` also matched 09_verify_all_cell_recipes.sh.

    That made the master report 8/9 and print a hardcoded "[i/7]" prefix.
    """
    proc = _run(MASTER)
    assert proc.returncode == 0
    assert "09_verify_all_cell_recipes.sh" not in proc.stdout
    assert "[1/8] 01_R1_LineageFlow.sh" in proc.stdout


def test_every_cell_script_is_exercised() -> None:
    """A new per-cell script must be added to the master, not just dropped in."""
    proc = _run(MASTER)
    assert proc.returncode == 0
    for script in sorted((ROOT / "reproduce").glob("0[1-8]_*.sh")):
        assert script.name in proc.stdout, f"{script.name} not run by the master"


def test_cell_recipe_verifier_passes() -> None:
    proc = _run(CELLS)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    assert "OK: All 11/11 paper cell recipes verified" in proc.stdout
