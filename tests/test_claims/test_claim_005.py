"""CLM-005: Cosine annealing is the canonical implementation of paper Lemma 2.

Asserted by docs/CLAIMS.md:99-106.
Claim:
    n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))

We pin three anchors via CosineAnnealScheduler.sample:
    r = 0       -> n_cap = n_max      (cos(0) = 1)
    r = L - 1   -> n_cap = n_min      (cos(pi) = -1)
    r = (L-1)/2 -> n_cap = midpoint   (cos(pi/2) = 0)
"""
from __future__ import annotations

import math

from adaptive_reflow.algorithm.scheduler._core import default_cosine_scheduler


def test_claim_005_round_zero_yields_n_max() -> None:
    sch = default_cosine_scheduler(cycle_length=20, n_min=0.05, n_max=1.0)
    sample = sch.sample(outer_cycle_id=0, round_in_cycle=0, target_round=0)
    assert math.isclose(float(sample.n_cap), 1.0, abs_tol=1e-9)


def test_claim_005_last_round_yields_n_min() -> None:
    sch = default_cosine_scheduler(cycle_length=20, n_min=0.05, n_max=1.0)
    sample = sch.sample(outer_cycle_id=0, round_in_cycle=19, target_round=19)
    assert math.isclose(float(sample.n_cap), 0.05, abs_tol=1e-9)


def test_claim_005_midpoint_is_average_of_endpoints() -> None:
    """At r = (L-1)/2 the cosine formula yields (n_min + n_max) / 2."""
    sch = default_cosine_scheduler(cycle_length=21, n_min=0.0, n_max=1.0)
    sample = sch.sample(outer_cycle_id=0, round_in_cycle=10, target_round=10)
    assert math.isclose(float(sample.n_cap), 0.5, abs_tol=1e-9)
