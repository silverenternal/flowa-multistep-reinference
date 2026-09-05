"""CLM-008: Framework's heuristic `selection_ratio` is NOT a paper quantity.

Asserted by docs/CLAIMS.md:143-158.
EvidenceScaleGapMetric is a framework-internal heuristic for monitoring
the sheet-vs-cell evidence scale gap; it is NOT a paper quantity, and
convergence to 1 is NOT a paper claim.

We pin:
    1. EvidenceScaleGapMetric class lives in the eval package.
    2. The docstring explicitly states the framework-internal nature.
    3. The metric accepts `eps_implicit` as a tunable parameter (NOT
       the paper's `eps`).
"""
from __future__ import annotations

import inspect

from adaptive_reflow.eval.posterior_selection_evaluator import (
    EvidenceScaleGapMetric,
)


def test_claim_008_evidence_scale_gap_metric_class_importable() -> None:
    assert EvidenceScaleGapMetric is not None


def test_claim_008_class_docstring_says_framework_internal() -> None:
    """The docstring MUST declare the framework-internal nature."""
    doc = (EvidenceScaleGapMetric.__doc__ or "").lower()
    assert "framework-internal" in doc or "framework internal" in doc, (
        "EvidenceScaleGapMetric docstring must declare framework-internal nature"
    )


def test_claim_008_eps_implicit_is_tunable_not_paper_eps() -> None:
    """`eps_implicit` is a constructor parameter (tunable, NOT paper eps)."""
    sig = inspect.signature(EvidenceScaleGapMetric.__init__)
    assert "eps_implicit" in sig.parameters
    assert sig.parameters["eps_implicit"].default is not inspect.Parameter.empty
