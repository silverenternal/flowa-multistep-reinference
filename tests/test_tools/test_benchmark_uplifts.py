"""Smoke + structure tests for ``tools.benchmark_uplifts``.

The benchmark script (``tools/benchmark_uplifts.py``) generates a
structured markdown report at ``docs/benchmark-uplifts.md``. This test
suite guards against silent drift:

* The script is importable as ``tools.benchmark_uplifts`` and its
  public measurement functions all return non-empty lists.
* The script's ``main`` runs end-to-end (in ``--skip-ablation`` mode
  so the wall-clock stays bounded) and emits a markdown artifact with
  the three expected sections (per-uplift quantitative results, the
  22-row ablation table, and the summary block).
* The summary block contains the four numeric counters the task brief
  requires (measured / achieving / regressions / neutral) plus the
  ablation row count.
"""
from __future__ import annotations

import importlib
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
SCRIPT_PATH: Path = REPO_ROOT / "tools" / "benchmark_uplifts.py"
DEFAULT_OUT: Path = REPO_ROOT / "docs" / "benchmark-uplifts.md"
ABLATION_OUTPUT: Path = REPO_ROOT / "docs" / "ABLATION.md"
VENV_PYTHON: Path = REPO_ROOT / ".venv" / "Scripts" / "python.exe"

#: Sections that must appear in the rendered benchmark markdown. The
#: task brief mandates three top-level sections (per-uplift results,
#: ablation comparison, summary); we assert each header is present.
EXPECTED_SECTIONS: tuple[str, ...] = (
    "## Section 1: Per-uplift quantitative results",
    "## Section 2: Ablation comparison (22 rows)",
    "## Section 3: Summary",
)

#: Numeric counters the summary block must carry. Each line follows
#: the ``"- <label>: **<value>**"`` pattern.
SUMMARY_PATTERN = re.compile(
    r"^-\s*(?P<label>[A-Za-z ()/_-]+?)\s*:\s*\*\*\s*(?P<value>[0-9]+)\s*\*\*\s*$"
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
def benchmark_out(tmp_path: Path) -> Path:
    """Return a fresh output path under ``tmp_path`` so the test does not
    overwrite the canonical ``docs/benchmark-uplifts.md``."""
    return tmp_path / "benchmark-uplifts.md"


# ---------------------------------------------------------------------------
# Import-time checks (no subprocess)
# ---------------------------------------------------------------------------


def test_benchmark_module_imports_clean() -> None:
    """The benchmark script is importable as ``tools.benchmark_uplifts``.

    All five measurement functions are exposed and have non-None
    callables.
    """
    module = importlib.import_module("tools.benchmark_uplifts")
    assert hasattr(module, "main"), "main() must be exposed"
    for name in (
        "measure_scheduler_uplifts",
        "measure_driver_merge_blender_uplifts",
        "measure_metric_uplifts",
        "measure_paper_quantity_uplifts",
        "measure_sequential_uplifts",
        "format_markdown",
        "_parse_ablation_rows",
    ):
        assert hasattr(module, name), f"missing public function {name!r}"
        fn = getattr(module, name)
        assert callable(fn), f"{name} must be callable"


def test_measurement_functions_return_non_empty_rows() -> None:
    """Every measurement function returns a non-empty list of row dicts.

    A regression in any of the five sections would surface as an
    empty list; we guard against that here so the smoke test below
    sees a non-trivial table.
    """
    import tools.benchmark_uplifts as benchmark

    rows_scheduler = benchmark.measure_scheduler_uplifts()
    assert len(rows_scheduler) > 0
    for r in rows_scheduler:
        assert "algorithm" in r and "uplift" in r and "metric" in r
        assert "baseline" in r and "current" in r
        assert "achieved" in r

    rows_dmb = benchmark.measure_driver_merge_blender_uplifts()
    assert len(rows_dmb) > 0
    for r in rows_dmb:
        assert "algorithm" in r and "achieved" in r

    rows_metric = benchmark.measure_metric_uplifts()
    assert len(rows_metric) > 0
    for r in rows_metric:
        assert "algorithm" in r

    rows_paper = benchmark.measure_paper_quantity_uplifts()
    assert len(rows_paper) > 0
    for r in rows_paper:
        assert "algorithm" in r

    rows_seq = benchmark.measure_sequential_uplifts()
    assert len(rows_seq) > 0
    for r in rows_seq:
        assert "algorithm" in r


def test_summary_counts_partitions_total() -> None:
    """The summary counts (achieved + regressed + neutral) sum to the total."""

    import tools.benchmark_uplifts as benchmark

    rows: list[dict[str, object]] = []
    rows.extend(benchmark.measure_scheduler_uplifts())
    rows.extend(benchmark.measure_driver_merge_blender_uplifts())
    rows.extend(benchmark.measure_metric_uplifts())
    rows.extend(benchmark.measure_paper_quantity_uplifts())
    rows.extend(benchmark.measure_sequential_uplifts())
    counts = benchmark._summary_counts(rows)  # noqa: SLF001 — internal API
    total = counts["achieved"] + counts["regressed"] + counts["neutral"]
    assert total == len(rows), (
        f"summary counts {counts} must partition the row set "
        f"(got total={total}, len(rows)={len(rows)})"
    )


# ---------------------------------------------------------------------------
# End-to-end smoke test (subprocess)
# ---------------------------------------------------------------------------


def test_benchmark_uplifts_runs_and_emits_markdown(
    _venv_python: Path,
    benchmark_out: Path,
) -> None:
    """Run the benchmark with ``--skip-ablation`` and assert structure.

    The end-to-end test exercises the CLI surface (argparse, the
    measurement functions, and the markdown emission). It uses
    ``--skip-ablation`` so the wall-clock stays under the smoke-test
    budget; the cached ``docs/ABLATION.md`` is parsed for the
    22-row ablation table.
    """
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    completed = subprocess.run(
        [
            str(_venv_python),
            str(SCRIPT_PATH),
            "--skip-ablation",
            "--out",
            str(benchmark_out),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, (
        f"benchmark_uplifts exited with code {completed.returncode}; "
        f"stderr:\n{completed.stderr}\nstdout:\n{completed.stdout}"
    )
    assert benchmark_out.exists(), (
        f"expected markdown at {benchmark_out} but it was not created; "
        f"stdout:\n{completed.stdout}"
    )
    text = benchmark_out.read_text(encoding="utf-8")

    # 1. The top-level heading is present.
    assert "# Algorithm Uplift Benchmark" in text

    # 2. All three sections are rendered in order.
    section_indices = [text.index(s) for s in EXPECTED_SECTIONS]
    assert section_indices == sorted(section_indices), (
        f"sections out of order; got: {section_indices}"
    )

    # 3. The per-uplift table header is the canonical 9-column header.
    header = (
        "| Algorithm | Uplift | Metric | Baseline | Current | Delta | "
        "% Change | Target | Achieved |"
    )
    assert header in text

    # 4. The ablation table header carries the required W2 / coverage /
    #    selection_ratio / ledger_chain_integrity columns.
    ablation_header = (
        "| Config | Target | Final W2 | Mean W2 | Final Coverage | "
        "Mean Coverage | Selection Ratio | Ledger Chain Integrity |"
    )
    assert ablation_header in text

    # 5. The summary block has the four required numeric counters and
    #    the ablation row count line.
    counters: dict[str, int] = {}
    for line in text.splitlines():
        m = SUMMARY_PATTERN.match(line)
        if m is not None:
            counters[m.group("label")] = int(m.group("value"))
    assert "Uplifts measured" in counters
    assert "Uplifts achieving target" in counters
    assert "Regressions" in counters
    assert "Ablation rows" in counters
    assert counters["Uplifts measured"] > 0
    assert counters["Ablation rows"] >= 22, (
        f"expected at least 22 ablation rows; got {counters['Ablation rows']}"
    )
    # Counter partition invariant (mirrors the direct-import check).
    measured = counters["Uplifts measured"]
    achieving = counters["Uplifts achieving target"]
    regressed = counters["Regressions"]
    neutral = counters.get("Neutral (no change / NaN)", 0)
    assert achieving + regressed + neutral == measured, (
        f"counters do not partition the measured total: "
        f"measured={measured}, achieving={achieving}, "
        f"regressed={regressed}, neutral={neutral}"
    )


def test_benchmark_uplifts_help_exits_zero(_venv_python: Path) -> None:
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
    assert "benchmark" in completed.stdout.lower()


# ---------------------------------------------------------------------------
# Direct-import sanity
# ---------------------------------------------------------------------------


def test_parse_ablation_rows_parses_canonical_md() -> None:
    """The parser recognises the canonical 22-row ablation markdown."""
    import tools.benchmark_uplifts as benchmark

    if not ABLATION_OUTPUT.exists():
        pytest.skip(f"ABLATION.md missing at {ABLATION_OUTPUT}")
    text = ABLATION_OUTPUT.read_text(encoding="utf-8")
    rows = benchmark._parse_ablation_rows(text)  # noqa: SLF001 — test seam
    assert len(rows) >= 22, (
        f"expected >= 22 rows in canonical ablation table; got {len(rows)}"
    )
    for r in rows[:3]:
        for key in ("config", "target", "fw2", "mw2", "fcov", "mcov"):
            assert key in r, f"missing key {key!r} in parsed row {r!r}"
