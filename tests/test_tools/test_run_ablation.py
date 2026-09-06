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
    "multi_round_polynomial_schedule_derived",
    "multi_round_sigmoid_schedule_derived",
    "multi_round_convergence_adaptive_schedule_derived",
    "multi_round_cosine_adaptive_driver",
)
#: The two ADR-0013 paper-grounded configurations. They only run
#: against :data:`PAPER_GROUNDED_TARGET`.
EXPECTED_PAPER_CONFIGS: tuple[str, ...] = (
    "multi_round_codimension_sheet_posterior_selection",
    "multi_round_cosine_posterior_selection",
    # C4 fix (``docs/r3-survey/09-c4-investigation.md``): the new
    # evidence-driven row exercises the PID-lite scheduler and is
    # the only ablation cell with a *schedule-sensitive*
    # ``selection_ratio`` curve.
    "multi_round_evidence_driven_posterior_selection",
)
#: The two post-infrastructure-fix (commit ``e5e38fc``) configurations
#: added in the post-P0/P1 ablation. Both run against both canonical
#: targets (one batched-trajectory row + one identity-merge row).
EXPECTED_INFRASTRUCTURE_FIX_CONFIGS: tuple[str, ...] = (
    "batched_cosine_forward_noise_hash_chained",
    "multi_round_cosine_anneal_identity_merge",
)
EXPECTED_TARGETS: tuple[str, ...] = ("two_moons", "eight_gaussians")
PAPER_GROUNDED_TARGET: str = "two_moons"
#: Total row count: ``8 * 2 + 2 + 2 * 2 = 22`` cells (8 canonical
#: configs x 2 targets + 2 paper-grounded rows on ``two_moons`` + 2
#: post-infrastructure-fix rows x 2 targets).
EXPECTED_ROW_COUNT: int = (
    len(EXPECTED_CONFIGS) * len(EXPECTED_TARGETS)
    + len(EXPECTED_PAPER_CONFIGS)
    + len(EXPECTED_INFRASTRUCTURE_FIX_CONFIGS) * len(EXPECTED_TARGETS)
)

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
    complete (18 rows: 8 canonical configs x 2 targets plus the 2
    ADR-0013 paper-grounded rows on ``two_moons``) and every numeric
    column is a real number -- not a placeholder.
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
    } | {
        (config, PAPER_GROUNDED_TARGET) for config in EXPECTED_PAPER_CONFIGS
    } | {
        (config, target)
        for config in EXPECTED_INFRASTRUCTURE_FIX_CONFIGS
        for target in EXPECTED_TARGETS
    }
    seen = {(r["config"], r["target"]) for r in rows}
    assert seen == expected_rows, (
        f"missing rows: {expected_rows - seen}; extra rows: {seen - expected_rows}"
    )

    # 2a. The 8 x 2 + 2 + 2 x 2 = 22 rows should all be present (the
    # canonical smoke test count for the post-infrastructure-fix
    # paper-grounded ablation).
    assert len(rows) == EXPECTED_ROW_COUNT, (
        f"expected {EXPECTED_ROW_COUNT} rows (8 configs x 2 targets + 2 "
        f"paper-grounded rows + 2 infrastructure-fix configs x 2 "
        f"targets), got {len(rows)}"
    )

    # 2b. The ADR-0013 selection-ratio table is present and both
    #     paper-grounded rows report a ratio in ``[0, 1]``.
    assert "## Selection ratio (paper Theorem 1, ADR-0013)" in text
    assert "## New findings: posterior selection (ADR-0013)" in text
    for config in EXPECTED_PAPER_CONFIGS:
        ratio_line = next(
            (
                line
                for line in text.splitlines()
                if line.startswith(f"| {config} |") and line.count("|") == 5
            ),
            None,
        )
        assert ratio_line is not None, (
            f"no selection-ratio row for {config}; text:\n{text}"
        )
        cells = [c.strip() for c in ratio_line.strip("|").split("|")]
        for value in cells[1:]:
            assert 0.0 <= float(value) <= 1.0, (
                f"{config}: selection_ratio {value} outside [0, 1]"
            )

    # 2c. The post-infrastructure-fix ablation section is present
    #     and reports ``ledger_chain_integrity = True`` for every
    #     new row (commit ``e5e38fc`` verified the hash-chained
    #     ledger on every emit).
    assert "## Post-infrastructure-fix ablation (22 rows)" in text
    assert "## Reproducibility" in text
    for config in EXPECTED_INFRASTRUCTURE_FIX_CONFIGS:
        for target in EXPECTED_TARGETS:
            assert (config, target) in seen, (
                f"post-infrastructure-fix row ({config}, {target}) "
                f"missing from the canonical results table; seen: {seen}"
            )
    infra_section = text.split("## Post-infrastructure-fix ablation (22 rows)")[1]
    # Every infrastructure-fix row in the new metrics table must
    # have ``ledger_chain_integrity = True`` (the hash chain is
    # verified on every run by ``verify_ledger_chain`` for the
    # ``ReInferenceRunner`` and by the batched runner's own
    # recompute).
    for line in infra_section.splitlines():
        if not line.startswith("|"):
            continue
        # Skip the header row.
        if "ledger_chain_integrity" in line:
            continue
        for config in EXPECTED_INFRASTRUCTURE_FIX_CONFIGS:
            if line.startswith(f"| {config} |"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                # Last cell is the ledger_chain_integrity flag.
                assert cells[-1] == "True", (
                    f"{config}: ledger_chain_integrity must be True "
                    f"after e5e38fc; got {cells[-1]!r} on row: {line}"
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


# ---------------------------------------------------------------------------
# C4 — evidence-driven ablation row emits schedule-sensitive selection_ratio
# ---------------------------------------------------------------------------


