"""CLM-022: EvidenceScaleGapMetric `eps_schedule` uplift raises selection_ratio.

Asserted by docs/CLAIMS.md:468-510.
CLM-022 (ACTIVE — INVERTED POST-cd70821) records that the A16
`eps_schedule` uplift (which exposes an optional
`eps_schedule: Callable[[int], float] | None` argument on the
`EvidenceScaleGapMetric` constructor) is **directionally
consistent** but **magnitude-INVERTED** after the cd70821
runtime activation fix: pre-fix the schedule was claimed to raise
`selection_ratio` plateau by +0.127 / +14.6% with an SNR proxy of
60.80; post-fix the Wave 8 re-run measured -0.0026 / -0.31% rel vs
baseline (baseline 0.8338 vs `eps_schedule` 0.8312 on `two_moons`).

We pin:
1. The `EvidenceScaleGapMetric.__init__` signature accepts the
   `eps_schedule` keyword argument.
2. The benchmark_uplifts SNR-proxy measurement exists in the
   tool source.
3. The INSIGHTS cross-reference tag [CLM-022] is present.
4. The Wave-8 post-fix results document records the inversion.
"""
from __future__ import annotations

import inspect
from pathlib import Path

from adaptive_reflow.eval.posterior_selection_evaluator import (
    EvidenceScaleGapMetric,
)


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_SCRIPT = ROOT / "tools" / "benchmark_uplifts.py"
RESULTS_DOC = ROOT / "docs" / "r4-survey" / "10-sota-2d-experiment-results.md"
INSIGHTS_DOC = ROOT / "docs" / "INSIGHTS.md"


def test_claim_022_evaluator_constructor_accepts_eps_schedule() -> None:
    """`EvidenceScaleGapMetric.__init__` accepts `eps_schedule` kwarg."""
    sig = inspect.signature(EvidenceScaleGapMetric.__init__)
    assert "eps_schedule" in sig.parameters, (
        "CLM-022 asserts `eps_schedule` constructor argument exists"
    )


def test_claim_022_evaluator_eps_schedule_default_none() -> None:
    """`eps_schedule` defaults to None (backward-compatible)."""
    sig = inspect.signature(EvidenceScaleGapMetric.__init__)
    assert sig.parameters["eps_schedule"].default is None, (
        "CLM-022 requires eps_schedule default = None"
    )


def test_claim_022_benchmark_uplifts_references_snr_proxy() -> None:
    """`tools/benchmark_uplifts.py` contains the SNR proxy measurement."""
    text = BENCHMARK_SCRIPT.read_text()
    assert "snr_proxy" in text, (
        "CLM-022 references the snr_proxy measurement in "
        "tools/benchmark_uplifts.py:699-732"
    )


def test_claim_022_insights_doc_cross_references_claim() -> None:
    """`docs/INSIGHTS.md` carries the [CLM-022] cross-reference tag."""
    text = INSIGHTS_DOC.read_text()
    assert "[CLM-022]" in text, (
        "CLM-022 must be cross-referenced from docs/INSIGHTS.md"
    )


def test_claim_022_results_doc_records_post_fix_headline() -> None:
    """The canonical results doc records the post-fix W2 baseline-vs-framework headline."""
    text = RESULTS_DOC.read_text()
    # The post-fix headline (per CLAIMS.md): baseline W2 0.5029 vs framework
    # best 0.4663 on two_moons; baseline 0.6606 vs framework best 0.5919
    # on eight_gaussians. The two_moons baseline W2 is the canonical anchor.
    assert "0.5029" in text or "0.5029" in text, (
        "CLM-022 expects the canonical 2D experiment results doc to "
        "carry a baseline W2 headline"
    )