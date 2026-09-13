"""Property-based tests for the Wave 125 restart-policy gate (H1 fix).

Coverage targets
----------------
* :func:`should_skip_restart_small_sigma` — the H1 gate added in Wave 125
  Phase 2 to short-circuit the per-round restart when the trajectory
  endpoint lives in a tiny neighborhood of the prior (the canonical
  σ=1e-3 FSQ-collapse pathology described in
  ``todo/algo-improvement-restart-policy-collapse-fix.md``).

Properties verified:

* **Lower-bound regime fires**: when ``sigma`` is strictly below the
  threshold (default ``1e-2``) AND ``current_n_restarts > 0``, the gate
  MUST return ``True`` (skip the restart blend).
* **First-restart guard**: when ``current_n_restarts == 0``, the gate
  MUST return ``False`` regardless of ``sigma`` — the framework has no
  prior trajectory to "trust" on the very first restart.
* **Above-threshold does not fire**: when ``sigma >= threshold``, the
  gate MUST return ``False`` for any ``current_n_restarts``.
* **Fail-closed on non-finite sigma**: ``+inf``, ``-inf`` and ``NaN``
  sigma values MUST NOT silently flip the gate; the helper coerces
  them and the gate returns ``False`` so the framework proceeds with
  its normal restart path.
* **Threshold kwarg is honoured**: when a custom ``threshold`` is
  supplied, the boundary moves accordingly — i.e. the gate fires for
  ``sigma < threshold`` (with positive ``current_n_restarts``) and not
  for ``sigma >= threshold``.

Seed policy: the helper is deterministic; ``@settings(derandomize=True)``
pins a regression to a byte-identical shrunk counter-example across
runs (Research 4 mitigation).
"""

from __future__ import annotations

import pytest

# hypothesis is only present in test/dev venvs.
# Skip the entire module when missing so the rest of the suite still collects.
_hypothesis_spec = pytest.importorskip(
    "hypothesis",
    reason="hypothesis not in venv (install via `uv pip install hypothesis`)",
)

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.algorithm import (
    DEFAULT_RESTART_SIGMA_THRESHOLD,
    should_skip_restart_small_sigma,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Pin every test to a deterministic strategy so a regression surfaces the
# exact same shrunk counter-example across runs.
_PROPERTY_SETTINGS = settings(
    max_examples=50,
    deadline=2000,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)


#: Sigma in the "tiny neighborhood" regime — STRICTLY less than 1e-2
#: so the gate fires when current_n_restarts > 0. We pick a strictly
#: positive lower bound (1e-6) so the test never exercises the
#: non-finite fail-closed branch (that branch has its own dedicated
#: property below). The upper bound sits a hair below the threshold
#: to keep the inequality ``sigma < threshold`` strict (the gate
#: returns False when sigma == threshold by construction).
_SMALL_SIGMA = st.floats(
    min_value=1e-6,
    max_value=DEFAULT_RESTART_SIGMA_THRESHOLD - 1e-12,  # < 1e-2
    allow_nan=False, allow_infinity=False,
)
#: Sigma in the "above-threshold" regime — STRICTLY greater than the
#: default gate threshold.
_LARGE_SIGMA = st.floats(
    min_value=DEFAULT_RESTART_SIGMA_THRESHOLD + 1e-6,  # > 1e-2
    max_value=1.0,
    allow_nan=False, allow_infinity=False,
)
#: Sigma anywhere in the [1e-6, 1.0] band (covers both regimes).
_ANY_SIGMA = st.floats(
    min_value=1e-6, max_value=1.0,
    allow_nan=False, allow_infinity=False,
)
#: Strictly-positive current_n_restarts (gate is armed).
_POS_RESTARTS = st.integers(min_value=1, max_value=32)
#: Zero restarts (first restart — gate must NOT fire).
_ZERO_RESTARTS = st.just(0)
#: Non-positive restarts (first restart / never restarted — gate must NOT fire).
_NON_POS_RESTARTS = st.integers(min_value=0, max_value=0)


# ---------------------------------------------------------------------------
# H1 core property — gate fires when sigma < threshold AND n_restarts > 0
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(sigma=_SMALL_SIGMA, n_restarts=_POS_RESTARTS)
def test_restart_policy_decision_property(sigma: float, n_restarts: int) -> None:
    """For sigma < 1e-2 AND n_restarts > 0, the gate must return True.

    This is the headline H1 fix property: the framework's per-round
    restart blend is short-circuited when the trajectory endpoint lives
    in a tiny neighborhood of the prior (the FSQ / quantizer collapse
    pathology). Without this gate, every restart round would push
    through the same collapsed codebook index, defeating the
    exploration-vs-refinement intent.
    """
    result = should_skip_restart_small_sigma(
        sigma=sigma, current_n_restarts=n_restarts
    )
    assert result is True, (
        f"Gate must fire for sigma={sigma} < threshold and n_restarts={n_restarts}>0"
    )


# ---------------------------------------------------------------------------
# First-restart guard — gate MUST NOT fire when no prior restarts exist
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(sigma=_ANY_SIGMA)
def test_restart_policy_first_restart_always_permitted(sigma: float) -> None:
    """For current_n_restarts == 0, the gate MUST return False.

    The framework has no prior trajectory to "trust" on the very first
    restart round; the gate therefore stays disarmed and the framework
    proceeds with its normal restart blend. This guards against an
    accidental regression that would over-skip restarts and freeze the
    trajectory at the initial sample.
    """
    result = should_skip_restart_small_sigma(sigma=sigma, current_n_restarts=0)
    assert result is False


# ---------------------------------------------------------------------------
# Above-threshold regime — gate MUST NOT fire when sigma >= threshold
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(sigma=_LARGE_SIGMA, n_restarts=_POS_RESTARTS)
def test_restart_policy_above_threshold_does_not_skip(
    sigma: float, n_restarts: int
) -> None:
    """For sigma >= threshold (with positive restarts), the gate is OFF.

    The tiny-neighborhood pathology requires a STRICTLY-subthreshold
    sigma; once the trajectory endpoint lives in a non-trivial
    neighborhood (sigma >= 1e-2), the framework's restart blend is
    meaningful and MUST proceed.
    """
    result = should_skip_restart_small_sigma(
        sigma=sigma, current_n_restarts=n_restarts
    )
    assert result is False


# ---------------------------------------------------------------------------
# Threshold kwarg — custom threshold moves the gate boundary
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(sigma=_ANY_SIGMA, n_restarts=_POS_RESTARTS)
def test_restart_policy_custom_threshold_moves_boundary(
    sigma: float, n_restarts: int
) -> None:
    """Custom ``threshold`` kwarg MUST shift the gate boundary accordingly.

    For a custom threshold ``T``, the gate fires iff
    ``sigma < T and current_n_restarts > 0``. We pick ``T = 0.5``
    (sitting comfortably above the default 1e-2 but below the test
    sigma upper bound 1.0) and assert: when ``sigma < 0.5`` the gate
    fires; when ``sigma >= 0.5`` it does not.
    """
    custom_threshold = 0.5
    result = should_skip_restart_small_sigma(
        sigma=sigma,
        current_n_restarts=n_restarts,
        threshold=custom_threshold,
    )
    expected = sigma < custom_threshold
    assert result is expected, (
        f"Custom threshold={custom_threshold}: sigma={sigma} -> result={result}, "
        f"expected={expected}"
    )


# ---------------------------------------------------------------------------
# Fail-closed on non-finite sigma
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    sigma=st.one_of(
        st.just(float("inf")),
        st.just(float("-inf")),
        st.just(float("nan")),
    ),
    n_restarts=_POS_RESTARTS,
)
def test_restart_policy_nonfinite_sigma_fails_closed(
    sigma: float, n_restarts: int
) -> None:
    """Non-finite sigma (inf, -inf, NaN) MUST cause the gate to fail CLOSED.

    The helper coerces non-finite values to a fail-closed ``False``
    response — i.e. the framework proceeds with the restart it would
    have done without this check. This guards against a silent flip
    that would freeze the trajectory at the initial sample when the
    sigma estimate is corrupted.
    """
    result = should_skip_restart_small_sigma(
        sigma=sigma, current_n_restarts=n_restarts
    )
    assert result is False


# ---------------------------------------------------------------------------
# Idempotency — the helper is pure; same inputs always yield same output
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(sigma=_ANY_SIGMA, n_restarts=_POS_RESTARTS)
def test_restart_policy_idempotent(sigma: float, n_restarts: int) -> None:
    """Calling the gate twice with the same args yields the same answer."""
    a = should_skip_restart_small_sigma(sigma=sigma, current_n_restarts=n_restarts)
    b = should_skip_restart_small_sigma(sigma=sigma, current_n_restarts=n_restarts)
    assert a == b
