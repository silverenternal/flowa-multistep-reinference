"""Property-based tests for :mod:`adaptive_reflow.algorithm.batched_runner`.

B.7 property-based testing — ``framework-internal-metrics.md`` rev 2 §1.

Coverage targets
----------------
* :class:`BatchedRunnerConfig` — defaults are positive integers in
  sensible ranges; ``cycle_length >= 1``.
* :func:`_config_hash` — distinct configs produce distinct hashes;
  same config produces the same hash.
* :func:`_w2_to_mode_centres` — ``f(X, X) == 0``; finiteness.

Seed policy (Research 4 mitigation): batched-runner helpers are
deterministic; Hypothesis varies only the input tuples.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

# hypothesis is only present in test/dev venvs.
# Skip the entire module when missing so the rest of the suite still collects.
_hypothesis_spec = pytest.importorskip(
    "hypothesis",
    reason="hypothesis not in venv (install via `uv pip install hypothesis`)",
)

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.algorithm.batched_runner import (
    BatchedRunnerConfig,
    _config_hash,
    _w2_to_mode_centres,
)


_PROPERTY_SETTINGS = settings(
    max_examples=20,
    deadline=2000,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


_CYCLE = st.integers(min_value=1, max_value=64)
_TRAJ = st.integers(min_value=1, max_value=32)
_EPT = st.integers(min_value=1, max_value=32)
_SEED = st.integers(min_value=0, max_value=1_000_000)


# ---------------------------------------------------------------------------
# BatchedRunnerConfig defaults.
# ---------------------------------------------------------------------------


def test_batched_runner_config_defaults() -> None:
    """Defaults match the B5 design (cycle=20, T=8, K=16)."""
    cfg = BatchedRunnerConfig()
    assert cfg.cycle_length == 20
    assert cfg.trajectories_per_round == 8
    assert cfg.endpoints_per_trajectory == 16


@_PROPERTY_SETTINGS
@given(
    cycle=_CYCLE,
    traj=_TRAJ,
    ept=_EPT,
    seed=_SEED,
)
def test_batched_runner_config_stores_inputs(
    cycle: int, traj: int, ept: int, seed: int
) -> None:
    """Constructor stores every argument verbatim."""
    cfg = BatchedRunnerConfig(
        cycle_length=cycle,
        trajectories_per_round=traj,
        endpoints_per_trajectory=ept,
        seed=seed,
    )
    assert cfg.cycle_length == cycle
    assert cfg.trajectories_per_round == traj
    assert cfg.endpoints_per_trajectory == ept
    assert cfg.seed == seed


# ---------------------------------------------------------------------------
# _config_hash: distinct configs produce distinct hashes.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    cycle1=_CYCLE,
    traj1=_TRAJ,
    ept1=_EPT,
    cycle2=_CYCLE,
    traj2=_TRAJ,
    ept2=_EPT,
)
def test_config_hash_distinct_for_distinct_inputs(
    cycle1: int, traj1: int, ept1: int,
    cycle2: int, traj2: int, ept2: int,
) -> None:
    """Distinct (cycle, traj, ept) tuples produce distinct hashes."""
    cfg1 = BatchedRunnerConfig(
        cycle_length=cycle1, trajectories_per_round=traj1,
        endpoints_per_trajectory=ept1,
    )
    cfg2 = BatchedRunnerConfig(
        cycle_length=cycle2, trajectories_per_round=traj2,
        endpoints_per_trajectory=ept2,
    )
    h1 = _config_hash(cfg1)
    h2 = _config_hash(cfg2)
    if (cycle1, traj1, ept1) == (cycle2, traj2, ept2):
        assert h1 == h2
    else:
        assert h1 != h2


# ---------------------------------------------------------------------------
# _w2_to_mode_centres: self-distance is 0 and is finite for non-empty inputs.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    n=st.integers(min_value=1, max_value=16),
)
def test_w2_to_mode_centres_self_distance_zero(n: int) -> None:
    """``_w2_to_mode_centres(X, X) == 0``."""
    rng = np.random.default_rng(0)
    x = rng.standard_normal((n, 2))
    out = _w2_to_mode_centres(x, x)
    assert math.isclose(out, 0.0, abs_tol=1e-9)


@_PROPERTY_SETTINGS
@given(
    n=st.integers(min_value=1, max_value=16),
)
def test_w2_to_mode_centres_finite(n: int) -> None:
    """``_w2_to_mode_centres`` returns a finite float for finite inputs."""
    rng = np.random.default_rng(0)
    x = rng.standard_normal((n, 2))
    y = rng.standard_normal((n, 2))
    out = _w2_to_mode_centres(x, y)
    assert math.isfinite(out)
    assert out >= -1e-9