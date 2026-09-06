"""Smoke test for ``tools.run_sota_2d_experiment``.

Guards the SOTA 2D experiment script against silent drift: if the
script stops generating the per-target comparison tables or the
``docs/r4-survey/10-sota-2d-experiment-results.md`` summary, this
test fails immediately.

The test runs the script as a subprocess in ``--quick`` mode (small
sample count, 5 rounds, 2 seeds) so the production CLI surface
(``argparse``, ``Path`` I/O, CSV/markdown emission) is exercised
end-to-end rather than via direct API calls.

Stdlib + pytest only.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH: Path = REPO_ROOT / "tools" / "run_sota_2d_experiment.py"
DEFAULT_OUT_DIR: Path = REPO_ROOT / "docs" / "r4-survey"
RESULTS_MD_NAME: str = "10-sota-2d-experiment-results.md"
VENV_PYTHON: Path = REPO_ROOT / ".venv" / "Scripts" / "python.exe"

CANONICAL_TARGETS: tuple[str, ...] = ("two_moons", "eight_gaussians")
CANONICAL_SCHEDULERS: tuple[str, ...] = (
    "CosineAnnealScheduler",
    "CodimensionSheetScheduler",
    "EvidenceDrivenScheduler",
    "FreeTrajScheduler",
)

#: Expected CSV file count per target in --quick mode (1 baseline + 4 schedulers × 2 seeds = 10).
EXPECTED_CSV_COUNT_PER_TARGET: int = (1 + len(CANONICAL_SCHEDULERS)) * 2


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
def sota_out_dir(tmp_path: Path) -> Path:
    """Return a fresh output directory under ``tmp_path``."""
    return tmp_path / "sota"


# ---------------------------------------------------------------------------
# Import + --help smoke tests
# ---------------------------------------------------------------------------
# NOTE (Wave 62): ``test_module_imports`` was deleted. The
# ``build_scheduler_returns_all_four_families`` test below (and the
# ``_build_scheduler`` indirect access) already imports the script via
# ``importlib`` and exercises ``SCHEDULER_NAMES`` / ``_build_scheduler``;
# a separate smoke test asserting only ``hasattr(module, name)`` is
# duplicate coverage. Pytest collection itself fails if the module
# fails to import, so the smoke was redundant.


# NOTE (Wave 62): ``test_help_flag_exits_cleanly`` was deleted. The
# end-to-end ``test_quick_run_produces_all_artifacts`` (below)
# invokes the script via subprocess with ``--target``, ``--output-dir``
# and exercises argparse end-to-end. The standalone ``--help`` smoke
# that only asserted rc==0 + a few flag-name substrings was duplicate
# coverage; a flag rename would surface via ``test_quick_run_produces_all_artifacts``
# before any user reported a regression.


# ---------------------------------------------------------------------------
# Scheduler factory unit tests
# ---------------------------------------------------------------------------


def test_build_scheduler_returns_all_four_families() -> None:
    """Each canonical scheduler name must build without raising."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_sota_2d_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    for name in CANONICAL_SCHEDULERS:
        scheduler = module._build_scheduler(name, rounds=5, seed=0)
        assert scheduler is not None
        sample = scheduler.sample(0, 0, 0)
        assert 0.0 <= float(sample.n_cap) <= 1.0


def test_build_scheduler_unknown_raises() -> None:
    """Unknown scheduler names must fail closed."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_sota_2d_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="unknown_scheduler"):
        module._build_scheduler("NotAScheduler", rounds=5, seed=0)


# ---------------------------------------------------------------------------
# End-to-end smoke test
# ---------------------------------------------------------------------------


def test_quick_run_produces_all_artifacts(
    _venv_python: Path, sota_out_dir: Path
) -> None:
    """``--quick --target both`` must write the per-target + summary artifacts."""
    result = subprocess.run(
        [
            str(_venv_python),
            str(SCRIPT_PATH),
            "--quick",
            "--target",
            "both",
            "--output-dir",
            str(sota_out_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=600,
    )
    assert result.returncode == 0, (
        f"stderr: {result.stderr!r}\nstdout: {result.stdout!r}"
    )

    # Per-target comparison markdown files
    for target in CANONICAL_TARGETS:
        comparison = sota_out_dir / f"{target}_comparison.md"
        assert comparison.exists(), f"missing {comparison}"

    # Per-(scheduler, seed) CSVs
    csvs = sorted(sota_out_dir.glob("*.csv"))
    assert len(csvs) == EXPECTED_CSV_COUNT_PER_TARGET * len(CANONICAL_TARGETS), (
        f"expected {EXPECTED_CSV_COUNT_PER_TARGET * len(CANONICAL_TARGETS)} "
        f"CSVs, got {len(csvs)}: {[p.name for p in csvs]}"
    )

    # Verify each CSV has the expected header and at least 1 round row
    header_pattern = re.compile(
        r"^round_index,n_cap,w2,selection_ratio,n_endpoints$"
    )
    for csv_path in csvs:
        text = csv_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        assert len(lines) >= 2, f"CSV {csv_path.name} is too short"
        assert header_pattern.match(lines[0]), (
            f"CSV {csv_path.name} header mismatch: {lines[0]!r}"
        )

    # Cross-target summary markdown
    summary = sota_out_dir / RESULTS_MD_NAME
    assert summary.exists(), f"missing {summary}"
    summary_text = summary.read_text(encoding="utf-8")
    for target in CANONICAL_TARGETS:
        assert target in summary_text, f"summary missing target {target}"
    for scheduler in CANONICAL_SCHEDULERS:
        assert scheduler in summary_text, (
            f"summary missing scheduler {scheduler}"
        )

    # HEADLINE_JSON must be on stdout (the script emits it as the
    # machine-readable summary).
    assert "HEADLINE_JSON=" in result.stdout
