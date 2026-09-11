"""CLM-010: Bounded noise floor prevents escape from the fibre.

Asserted by docs/CLAIMS.md:177-191.
SchedulerProtocol.config.n_min > 0 and BoundedMergeOperator's
MERGE_FLOOR_FALLBACK implement paper Lemma 4's bounded-noise
guarantee: a non-zero noise floor is the structural guarantee that the
posterior stays on the fibre.

We pin:
    1. CosineAnnealScheduler's `n_min` config field is positive.
    2. Sampling at round L-1 (the cycle end) yields `n_cap = n_min`.
    3. `n_min` is preserved through `to_config`/`from_config` round-trip.
"""
from __future__ import annotations
from tests.test_claims._claim_template import default_cosine_scheduler
import math

def test_claim_010_cosine_scheduler_config_carries_positive_n_min() -> None:
    """`_config.n_min` is the structural noise-floor guarantee."""
    sch = default_cosine_scheduler(cycle_length=10, n_min=0.05, n_max=1.0)
    n_min_value = float(sch._config.n_min)
    assert n_min_value > 0.0, f"n_min = {n_min_value!r} not positive"
    assert math.isclose(n_min_value, 0.05, abs_tol=1e-9)

def test_claim_010_last_round_n_cap_equals_n_min() -> None:
    """At round L-1 the cosine ramp reaches its `n_min` floor."""
    sch = default_cosine_scheduler(cycle_length=10, n_min=0.07, n_max=1.0)
    sample = sch.sample(outer_cycle_id=0, round_in_cycle=9, target_round=9)
    assert math.isclose(float(sample.n_cap), 0.07, abs_tol=1e-9)
    # Sample carries `n_min` explicitly for audit.
    assert math.isclose(float(sample.n_min), 0.07, abs_tol=1e-9)

def test_claim_010_n_min_survives_round_trip_via_config() -> None:
    """`n_min` is preserved through `to_config`/`from_config` round-trip."""
    sch = default_cosine_scheduler(cycle_length=8, n_min=0.12, n_max=0.95)
    cfg = sch.to_config()
    sch2 = type(sch).from_config(cfg)
    assert math.isclose(float(sch2._config.n_min), 0.12, abs_tol=1e-9)
