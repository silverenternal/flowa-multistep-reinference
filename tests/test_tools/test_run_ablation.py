"""Smoke test for ``tools.run_ablation``.

Exercises the ablation script in ``--quick`` mode (5 rounds instead of
20) and asserts the markdown artifact is generated with real numbers.
This guards against silent drift: if the script stops generating the
canonical ``docs/ABLATION.md`` table, this test fails immediately.

The test is stdlib + pytest only; it runs the script as a subprocess
so the production CLI surface (``argparse``, ``Path`` I/O, markdown
emission) is exercised end-to-end rather than via direct API calls.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH: Path = REPO_ROOT / "tools" / "run_ablation.py"
DEFAULT_OUT: Path = REPO_ROOT / "docs" / "ABLATION.md"
VENV_PYTHON: Path = REPO_ROOT / ".venv" / "Scripts" / "python.exe"

EXPECTED_CONFIGS: tuple[str, ...] = (
    "single_pass",
    "multi_round_constant_beta_05",
    "multi_round_cosine_anneal",
    "multi_round_no_restart",
)
EXPECTED_TARGETS: tuple[str, ...] = ("two_moons", "eight_gaussians")

TABLE_HEADER: str = "| Config | Target | Final W2 | Mean W2 | Final coverage | Mean coverage |"
ROW_PATTERN = re.compile(
    r"^\|\s*(?P<config>[a-z_0-9]+)\s*\|\s*(?P<target>[a-z_0-9]+)\s*\|"
    r"\s*(?P<fw2>[\d.]+)\s*\|\s*(?P<mw2>[\d.]+)\s*\|"
    r"\s*(?P<fcov>[\d.]+)\s*\|\s*(?P<mcov>[\d.]+)\s*\|$"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _venv_python() -> Path:
    """Return the venv python executable path; skip if missing."""
    if not VENV_PYTHON.exists():
        pytest.skip(f"venv python not found at {VENV_PYTHON}")
    return VENV_PYTHON


@pytest.fixture()
def ablation_out(tmp_path: Path) -> Path:
    """Return a fresh output path under ``tmp_path`` so the test does not
    overwrite the canonical ``docs/ABLATION.md``."""
    return tmp_path / "ABLATION.md"


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------


def test_run_ablation_quick_generates_table(
    _venv_python: Path,
    ablation_out: Path,
) -> None:
    """Run ``tools/run_ablation.py`` in ``--quick`` mode; verify the markdown table.

    The test exercises the full CLI surface: argument parsing, the
    ``Engine.run_round`` loop for every (config, target) cell, and the
    markdown emission to ``--out``.  It asserts the rendered table is
    complete (8 rows, 4 configs x 2 targets) and every numeric column
    is a real number -- not a placeholder.
    """
    env = os.environ.copy()
    # Force UTF-8 stdout on Windows so the progress prints don't choke.
    env.setdefault("PYTHONIOENCODING", "utf-8")
    completed = subprocess.run(
        [
            str(_venv_python),
            str(SCRIPT_PATH),
            "--quick",
            "--out",
            str(ablation_out),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert completed.returncode == 0, (
        f"run_ablation exited with code {completed.returncode}; "
        f"stderr:\n{completed.stderr}\nstdout:\n{completed.stdout}"
    )
    assert ablation_out.exists(), (
        f"expected markdown at {ablation_out} but it was not created; "
        f"stdout:\n{completed.stdout}"
    )
    text = ablation_out.read_text(encoding="utf-8")

    # 1. The canonical header is present and the heading hierarchy is intact.
    assert "# 2D Rectified-Flow Ablation Study" in text
    assert "## Results" in text
    assert TABLE_HEADER in text
    assert "## Findings" in text

    # 2. Every (config, target) row is present and parses to a real number.
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        m = ROW_PATTERN.match(line)
        if m is not None:
            rows.append(m.groupdict())
    expected_rows = {
        (config, target) for config in EXPECTED_CONFIGS for target in EXPECTED_TARGETS
    }
    seen = {(r["config"], r["target"]) for r in rows}
    assert seen == expected_rows, (
        f"missing rows: {expected_rows - seen}; extra rows: {seen - expected_rows}"
    )

    # 3. Every numeric column parses to a finite real number; the
    #    ``Final Coverage`` and ``Mean Coverage`` columns must lie in
    #    ``[0, 1]``.
    for r in rows:
        for col in ("fw2", "mw2", "fcov", "mcov"):
            float(r[col])  # raises ValueError on a placeholder string
        cov = float(r["fcov"])
        assert 0.0 <= cov <= 1.0, (
            f"row ({r['config']}, {r['target']}): final_coverage={cov} "
            f"outside [0, 1]"
        )
        mcov = float(r["mcov"])
        assert 0.0 <= mcov <= 1.0, (
            f"row ({r['config']}, {r['target']}): mean_coverage={mcov} "
            f"outside [0, 1]"
        )


def test_run_ablation_help_exits_zero(_venv_python: Path) -> None:
    """``--help`` exits 0 and prints the usage banner."""
    completed = subprocess.run(
        [str(_venv_python), str(SCRIPT_PATH), "--help"],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, (
        f"--help failed: stderr={completed.stderr!r}"
    )
    assert "ablation" in completed.stdout.lower()


# ---------------------------------------------------------------------------
# Direct-import sanity (no subprocess)
# ---------------------------------------------------------------------------


def test_run_one_rejects_unknown_config() -> None:
    """Direct import check: ``_run_one`` raises on an unknown config."""
    from tools import run_ablation as ablation

    with pytest.raises(ValueError, match="unknown_config"):
        ablation._run_one(  # noqa: SLF001 — test seam
            config="bogus_config",
            target="two_moons",
            weights_path=Path("dummy.npz"),
            seed=42,
            rounds=1,
            num_steps=10,
        )


def test_run_ablation_module_imports_clean() -> None:
    """The script module is importable as ``tools.run_ablation``."""
    import importlib

    module = importlib.import_module("tools.run_ablation")
    assert hasattr(module, "main")
    assert hasattr(module, "_run_one")
    assert hasattr(module, "_format_markdown")
