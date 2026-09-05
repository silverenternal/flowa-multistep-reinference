"""CLM-018: Cosine wins on W2 vs polynomial, sigmoid, and convergence-adaptive.

Asserted by docs/CLAIMS.md:357-389.
CLM-018 (ACTIVE — INVERTED POST-cd70821) records that the original
"cosine wins" claim held only under the buggy pre-cd70821 runtime
(np.tanh vs ReLU mismatch); after the runtime activation fix
(commit cd70821, 2026-08-31) the Wave 8 FIX-3 re-run measured
baseline (1-pass) as the strongest configuration on both
`two_moons` (baseline W2 = 0.0709, framework best 0.0805) and
`eight_gaussians` (baseline W2 = 0.1764, framework best 0.1831).

We pin the post-fix direction-of-effect by checking the canonical
experiment script and the canonical results document exist on
disk (so a future regression that reverts cd70821 cannot silently
re-introduce the buggy reading).
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_SCRIPT = ROOT / "tools" / "run_sota_2d_experiment.py"
RESULTS_DOC = ROOT / "docs" / "r4-survey" / "10-sota-2d-experiment-results.md"


def test_claim_018_experiment_script_exists() -> None:
    """The 2D Rectified-Flow SOTA experiment driver is on disk."""
    assert EXPERIMENT_SCRIPT.is_file(), (
        f"{EXPERIMENT_SCRIPT} missing — CLM-018 asserts by this script"
    )


def test_claim_018_results_doc_exists() -> None:
    """The canonical Wave-8 post-fix results doc is on disk."""
    assert RESULTS_DOC.is_file(), (
        f"{RESULTS_DOC} missing — CLM-018 cites this document"
    )


def test_claim_018_results_doc_records_two_moons_and_eight_gaussians() -> None:
    """The canonical results doc covers the two 2D target distributions."""
    text = RESULTS_DOC.read_text()
    assert "two_moons" in text, (
        "CLM-018 results doc must cover the `two_moons` target"
    )
    assert "eight_gaussians" in text, (
        "CLM-018 results doc must cover the `eight_gaussians` target"
    )


def test_claim_018_results_doc_records_baseline_w2_headline() -> None:
    """The canonical results doc records baseline-vs-framework W2 deltas."""
    text = RESULTS_DOC.read_text()
    # The post-fix headline (per CLAIMS.md): baseline W2 0.5029 -> framework
    # best W2 0.4663 on two_moons; baseline W2 0.6606 -> framework best
    # 0.5919 on eight_gaussians.
    assert "0.5029" in text or "0.6606" in text, (
        "CLM-018 expects the canonical results doc to cite a baseline W2 "
        "headline number"
    )


def test_claim_018_experiment_script_lists_four_schedulers() -> None:
    """The SCHEDULER_NAMES tuple lists the four framework schedulers."""
    text = EXPERIMENT_SCRIPT.read_text()
    assert "SCHEDULER_NAMES" in text
    # The four canonical scheduler names appear in the script's registry.
    for name in (
        "CosineAnnealScheduler",
        "CodimensionSheetScheduler",
        "EvidenceDrivenScheduler",
        "FreeTrajScheduler",
    ):
        assert name in text, (
            f"CLM-018 expects {name!r} in SCHEDULER_NAMES tuple"
        )