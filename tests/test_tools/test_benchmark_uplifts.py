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
* The deep-uplift mode (``--deep``) emits a 5-section report at
  ``docs/benchmark-deep-uplifts.md`` with section 1 (framework-
  internal uplifts), section 2 (framework-external uplifts),
  section 3 (pluggable design tests), section 4 (the 22-row
  ablation), and section 5 (the totals + ablation row count).
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
DEEP_OUT: Path = REPO_ROOT / "docs" / "benchmark-deep-uplifts.md"
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

#: Sections required for the deep-uplift (``--deep``) report. See
#: ``docs/algorithm-deep-uplift-plan.md`` for the layout contract.
EXPECTED_DEEP_SECTIONS: tuple[str, ...] = (
    "## Section 1: Framework-internal uplifts",
    "## Section 2: Framework-external uplifts",
    "## Section 3: Pluggable design tests",
    "## Section 4: Ablation (extended table)",
    "## Section 5: Summary",
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


@pytest.fixture()
def benchmark_deep_out(tmp_path: Path) -> Path:
    """Return a fresh output path under ``tmp_path`` for the deep-uplift
    report."""
    return tmp_path / "benchmark-deep-uplifts.md"


# ---------------------------------------------------------------------------
# Import-time checks (no subprocess)
# ---------------------------------------------------------------------------
# NOTE (Wave 62): ``test_benchmark_module_imports_clean`` was deleted.
# The other tests in this file already import ``tools.benchmark_uplifts``
# (via ``importlib.import_module``) and exercise every function in
# the assertion set below; a separate smoke test that only asserts
# ``hasattr(module, name)`` is duplicate coverage. Pytest collection
# itself fails if the module fails to import, so the smoke was redundant.


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


def test_external_uplifts_return_rows() -> None:
    """``measure_external_uplifts`` returns the framework-external rows."""

    import tools.benchmark_uplifts as benchmark

    rows = benchmark.measure_external_uplifts()
    assert len(rows) > 0, "measure_external_uplifts returned empty"
    for r in rows:
        assert "algorithm" in r, f"missing algorithm in row {r}"
        assert "uplift" in r, f"missing uplift in row {r}"
        assert "metric" in r, f"missing metric in row {r}"
        assert "baseline" in r, f"missing baseline in row {r}"
        assert "current" in r, f"missing current in row {r}"
        assert "achieved" in r, f"missing achieved in row {r}"
    # Should at minimum cover the integrator families (rk4 / dopri5 /
    # dpm_solver / unipc / heun) + coverage + energy + lipschitz +
    # wilson + OT + W2. Search both the metric and uplift fields so
    # the test is robust to label renames.
    metric_ids = {r["metric"] for r in rows}
    uplift_ids = {r["uplift"] for r in rows}
    all_texts = metric_ids | uplift_ids
    assert any(
        "step-count reduction" in t or "step-count used" in t
        for t in all_texts
    ), (
        "measure_external_uplifts must include a step-count reduction row"
    )
    assert any("sampler accuracy" in t for t in all_texts), (
        "measure_external_uplifts must include a sampler-accuracy row"
    )
    assert any(
        "sparse-vs-dense separation" in t for t in all_texts
    ), "measure_external_uplifts must include a Voronoi-coverage row"
    assert any(
        "95% CI relative width" in t for t in all_texts
    ), (
        "measure_external_uplifts must include an energy-distance CI row"
    )
    assert any(
        "bounded-Lipschitz" in t or "Lipschitz" in t for t in all_texts
    ), (
        "measure_external_uplifts must include a Lipschitz row"
    )


def test_pluggable_design_tests_return_rows() -> None:
    """``measure_pluggable_design_tests`` returns pluggable-invariant rows."""

    import tools.benchmark_uplifts as benchmark

    rows = benchmark.measure_pluggable_design_tests()
    assert len(rows) > 0, "measure_pluggable_design_tests returned empty"
    protocols = {r["algorithm"] for r in rows}
    # Must cover all four plug-in protocol surfaces.
    expected_protocols = {
        "SchedulerProtocol",
        "PolicyDriverProtocol",
        "MergeOperatorProtocol",
        "RestartBlenderProtocol",
        "IntegratorProtocol",
        "W2EstimatorProtocol",
    }
    missing = expected_protocols - protocols
    assert not missing, f"missing plug-in rows for: {sorted(missing)}"
    # All rows must carry a metric and a target.
    for r in rows:
        assert "metric" in r, f"missing metric in row {r}"
        assert "target" in r, f"missing target in row {r}"


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


# NOTE (Wave 62): ``test_benchmark_uplifts_help_exits_zero`` was
# deleted. The end-to-end ``test_benchmark_uplifts_runs_and_emits_markdown``
# (above) already invokes the script via subprocess and asserts the
# three-section markdown structure is emitted. The standalone
# ``--help`` smoke that only checked ``"benchmark" in completed.stdout.lower()``
# added no unique contract coverage -- every ``--help`` banner contains
# the program name by argparse convention.


# ---------------------------------------------------------------------------
# Deep-uplift (--deep) section
# ---------------------------------------------------------------------------


def test_benchmark_deep_uplifts_emits_five_sections(
    _venv_python: Path,
    benchmark_deep_out: Path,
) -> None:
    """Run ``--deep --skip-ablation`` and assert the 5-section structure.

    The deep-uplift end-to-end test exercises the full CLI surface
    (including the new ``measure_external_uplifts`` and
    ``measure_pluggable_design_tests`` functions and the
    ``format_deep_markdown`` emitter) and confirms the rendered report
    carries all five sections + the ablation row count.
    """

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    completed = subprocess.run(
        [
            str(_venv_python),
            str(SCRIPT_PATH),
            "--deep",
            "--skip-ablation",
            "--out",
            str(benchmark_deep_out),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert completed.returncode == 0, (
        f"benchmark_uplifts --deep exited with code "
        f"{completed.returncode}; stderr:\n{completed.stderr}\n"
        f"stdout:\n{completed.stdout}"
    )
    assert benchmark_deep_out.exists(), (
        f"expected markdown at {benchmark_deep_out} but it was not "
        f"created; stdout:\n{completed.stdout}"
    )
    text = benchmark_deep_out.read_text(encoding="utf-8")

    # 1. Top-level heading + the 5-section list.
    assert "# Algorithm Deep Uplift Benchmark" in text
    section_indices = [text.index(s) for s in EXPECTED_DEEP_SECTIONS]
    assert section_indices == sorted(section_indices), (
        f"deep-uplift sections out of order; got: {section_indices}"
    )

    # 2. The framework-internal section uses the canonical 9-column
    #    header.
    internal_header = (
        "| Algorithm | Uplift | Metric | Baseline | Current | Delta | "
        "% Change | Target | Achieved |"
    )
    assert internal_header in text, (
        "framework-internal section missing canonical 9-column header"
    )

    # 3. The pluggable-design table uses the column the task brief
    #    specifies (Protocol | Implementation | config_hash stability
    #    | from_config round-trip | audit_codes emission).
    plug_header = (
        "| Protocol | Implementation | Metric | Before | After | "
        "Delta | % Change | Target | Achieved |"
    )
    assert plug_header in text, (
        "pluggable-design section missing canonical 9-column header"
    )

    # 4. The ablation section uses the canonical W2 / coverage /
    #    selection_ratio / ledger_chain_integrity header.
    ablation_header = (
        "| Config | Target | Final W2 | Mean W2 | Final Coverage | "
        "Mean Coverage | Selection Ratio | Ledger Chain Integrity |"
    )
    assert ablation_header in text, (
        "deep-uplift ablation section missing canonical header"
    )

    # 5. The summary block carries the deep-uplift-specific line items
    #    (Total uplifts measured, Framework-internal, Framework-
    #    external, Pluggable design tests, Uplifts achieving target,
    #    Regressions, Neutral, Ablation rows). Match both top-level
    #    bullets and indented sub-bullets (the deep-uplift report
    #    uses ``  - <label>: **<value>** (see Section N)`` for the
    #    per-section counts).
    counters: dict[str, int] = {}
    for line in text.splitlines():
        m = re.match(
            r"^\s*-\s*(?P<label>[^*]+?)\s*:\s*\*\*\s*(?P<value>[0-9]+)"
            r"\s*\*\*",
            line,
        )
        if m is not None:
            label = m.group("label").strip()
            counters[label] = int(m.group("value"))
    assert "Total uplifts measured" in counters, (
        f"deep-uplift summary missing 'Total uplifts measured'; "
        f"got counters={list(counters)!r}"
    )
    assert counters["Total uplifts measured"] > 0
    # The task brief requires sections 1-3 to be present and
    # populated; the deep-uplift report must therefore carry at least
    # one measurement per section. The sub-items have a parenthesised
    # suffix (e.g. ``Framework-internal: **36** (see Section 1)``);
    # we use ``startswith`` so the suffix does not defeat the match.
    found_internal = any(
        k == "Framework-internal" or k.startswith("Framework-internal")
        for k in counters
    )
    found_external = any(
        k == "Framework-external" or k.startswith("Framework-external")
        for k in counters
    )
    found_pluggable = any(
        k == "Pluggable design tests"
        or k.startswith("Pluggable design tests")
        for k in counters
    )
    assert found_internal, (
        "deep-uplift summary missing Framework-internal counter"
    )
    assert found_external, (
        "deep-uplift summary missing Framework-external counter"
    )
    assert found_pluggable, (
        "deep-uplift summary missing Pluggable design tests counter"
    )
    # Counter-partition invariant.
    measured = counters["Total uplifts measured"]
    achieving = counters["Uplifts achieving target"]
    regressed = counters["Regressions"]
    neutral = counters.get(
        "Neutral / no-change / NaN comparisons", 0
    )
    assert achieving + regressed + neutral == measured, (
        f"deep-uplift counters do not partition the measured total: "
        f"measured={measured}, achieving={achieving}, "
        f"regressed={regressed}, neutral={neutral}"
    )
    # Ablation row count from the cached docs/ABLATION.md.
    assert counters["Ablation rows"] >= 22, (
        f"expected at least 22 ablation rows in deep report; "
        f"got {counters['Ablation rows']}"
    )


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
