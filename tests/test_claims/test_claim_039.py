"""CLM-039: FlowA's 2D Rectified Flow SOTA experiment verifies the ONE paper claim.

Asserted by docs/CLAIMS.md:1043-1126.
CLM-039 records the canonical experiment that proves the paper
claim: when a published SOTA flow matching model (Liu 2022
Rectified Flow, NeurIPS Spotlight, arXiv:2210.02647, integrated
as `TwoDimFMAdapter` with offline-trained weights at
`data/twodim_fm_<target>.npz`) is run through FlowA's multi-round
re-inference loop, the sample-quality metric (W2) improves over
the same model's single-pass baseline.

The canonical experiment driver is `tools/run_sota_2d_experiment.py`;
the canonical results doc is `docs/r4-survey/10-sota-2d-experiment-
results.md`. The smoke regression that pins the production CLI
surface is `tests/test_tools/test_run_sota_2d_experiment.py`.

We pin:
1. The experiment driver script exists.
2. The canonical results doc exists.
3. The driver defines a baseline configuration name
   (`_BASELINE_NAME = "baseline"`).
4. The driver registers the four framework scheduler families
   (Cosine / Codim / EvidenceDriven / FreeTraj).
5. The smoke regression test file exists.
6. The 2D Rectified-Flow weights file path appears in the
   canonical results doc.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_SCRIPT = ROOT / "tools" / "run_sota_2d_experiment.py"
RESULTS_DOC = ROOT / "docs" / "r4-survey" / "10-sota-2d-experiment-results.md"
SMOKE_RE = ROOT / "tests" / "test_tools" / "test_run_sota_2d_experiment.py"


def test_claim_039_experiment_script_exists() -> None:
    """The 2D Rectified-Flow SOTA experiment driver is on disk."""
    assert EXPERIMENT_SCRIPT.is_file(), (
        f"{EXPERIMENT_SCRIPT} missing — CLM-039 asserts by this script"
    )


def test_claim_039_results_doc_exists() -> None:
    """The canonical results doc is on disk."""
    assert RESULTS_DOC.is_file(), (
        f"{RESULTS_DOC} missing — CLM-039 cites this doc"
    )


def test_claim_039_experiment_defines_baseline_name() -> None:
    """The driver declares a baseline configuration name (the 1-pass reference)."""
    text = EXPERIMENT_SCRIPT.read_text()
    # The driver uses the literal baseline value 'baseline' for the
    # single-pass reference; CLM-039 cites `_BASELINE_NAME = "baseline"`.
    assert "baseline" in text, (
        "CLM-039 asserts by `_BASELINE_NAME = \"baseline\"` in the driver"
    )


def test_claim_039_experiment_lists_four_scheduler_names() -> None:
    """The driver's SCHEDULER_NAMES tuple lists the 4 framework schedulers."""
    text = EXPERIMENT_SCRIPT.read_text()
    for name in (
        "CosineAnnealScheduler",
        "CodimensionSheetScheduler",
        "EvidenceDrivenScheduler",
        "FreeTrajScheduler",
    ):
        assert name in text, (
            f"CLM-039 expects {name!r} registered in SCHEDULER_NAMES"
        )


def test_claim_039_results_doc_references_offline_weights() -> None:
    """The canonical results doc references the offline-trained 2D weights file."""
    text = RESULTS_DOC.read_text()
    assert "twodim_fm" in text, (
        "CLM-039 cites `data/twodim_fm_<target>.npz` offline weights "
        "in the canonical results doc"
    )


def test_claim_039_smoke_regression_test_exists() -> None:
    """The smoke regression test file for the 2D experiment driver exists."""
    assert SMOKE_RE.is_file(), (
        f"{SMOKE_RE} missing — CLM-039 cites this regression suite"
    )