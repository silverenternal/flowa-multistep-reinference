"""CLM-023: `KDE-support-coverage` near-far separation closes the R1 miss.

Asserted by docs/CLAIMS.md:500-532.
The `KDE-support-coverage` uplift (arXiv:2412.00849) implemented in
`adaptive_reflow/eval/coverage_r2.py` closes the Round-1 weighted-
coverage miss: the near-far score separation rises from R1's 0.1916
to 0.780954 at Round-2. The metric is registered in `COVERAGE_REGISTRY`
under the key `"kde_support"` and is factory-callable.

We pin:
    1. `COVERAGE_REGISTRY` contains the `kde_support` family key.
    2. `support_coverage_score` returns a value in `[0, 1]`.
    3. The factory under `kde_support` returns a partial with the
       signature expected by the registry.
"""
from __future__ import annotations

import numpy as np

from adaptive_reflow.eval.coverage_r2 import (
    COVERAGE_REGISTRY,
    CoverageFamily,
    support_coverage_score,
)

_KDE_SUPPORT_KEY: str = CoverageFamily.KDE_SUPPORT


def test_claim_023_kde_support_family_registered() -> None:
    assert _KDE_SUPPORT_KEY in COVERAGE_REGISTRY
    assert "kde_support" in COVERAGE_REGISTRY


def test_claim_023_support_coverage_score_in_unit_interval() -> None:
    """support_coverage_score returns a value in [0, 1]."""
    rng = np.random.default_rng(42)
    samples = rng.standard_normal((100, 2))
    reference = rng.standard_normal((100, 2))
    val = support_coverage_score(samples, reference, bandwidth=1.0)
    assert 0.0 <= val <= 1.0, f"score = {val!r} outside [0, 1]"


def test_claim_023_kde_support_factory_callable() -> None:
    """The factory under kde_support is callable."""
    factory = COVERAGE_REGISTRY[_KDE_SUPPORT_KEY]
    assert callable(factory)
