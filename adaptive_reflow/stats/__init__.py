"""Statistical helpers for equivalence, meta-analysis, and trend tests.

Public surface re-exports the dataclasses and functions from
:mod:`adaptive_reflow.stats.equivalence`. Designed for paper-equivalence
claims (Wave 234 P1) and tightly integrated with the framework's
byte-stable audit gates — the fallbacks here are pure NumPy / SciPy
so they run in any sandbox.
"""
from __future__ import annotations

from adaptive_reflow.stats.equivalence import (
    BayesFactorResult,
    EquivalenceResult,
    JonckheereResult,
    MetaAnalysisResult,
    NonInferiorityResult,
    bf01_paired,
    has_pingouin,
    has_statsmodels,
    jonckheere_terpstra,
    meta_random_effects,
    non_inferiority,
    tost_paired,
)

__all__ = [
    "BayesFactorResult",
    "EquivalenceResult",
    "JonckheereResult",
    "MetaAnalysisResult",
    "NonInferiorityResult",
    "bf01_paired",
    "has_pingouin",
    "has_statsmodels",
    "jonckheere_terpstra",
    "meta_random_effects",
    "non_inferiority",
    "tost_paired",
]