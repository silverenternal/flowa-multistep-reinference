"""Property-based tests for the Wave 125 BRAI ``magnitude`` kwarg (H2 fix).

Coverage targets
----------------
* :class:`PaperQuantityAttractorInversion.propose` — the per-call
  ``magnitude`` kwarg added in Wave 125 Phase 3 overrides the
  constructor ``eps_scale`` for a single call (without mutating the
  instance's ``eps_scale``). The wave-125 fix lets callers tune BRAI's
  push magnitude per model-family (protein, image, audio, graph)
  without having to construct a new policy instance.

Properties verified:

* **Magnitude controls scale (linearity)**: with the analytic Gaussian
  prior (``sigma = 1``) and a unit-vector saturated state, the
  perturbation vector ``out - x`` equals ``magnitude * x`` exactly
  (i.e. ``np.linalg.norm(out - x) == magnitude`` to within float
  tolerance).
* **Magnitude overrides constructor ``eps_scale``**: passing
  ``magnitude != eps_scale`` produces a perturbation scaled by
  ``magnitude``, NOT by the constructor default — the per-call kwarg
  wins.
* **Subsequent calls revert**: a call with ``magnitude`` MUST NOT
  mutate the instance's ``eps_scale``; a follow-up call without
  ``magnitude`` MUST use the constructor default again
  (backward-compatible legacy behaviour).
* **Magnitude is rejected when non-positive**: ``magnitude <= 0`` or
  non-finite raises :exc:`PerturbationConfigError` (same boundary
  contract as the constructor ``eps_scale``).

Test geometry: unit-vector saturated state along the x-axis
(``x = [1.0, 0.0, ...]``) with ``sigma = 1.0`` gives ``-grad = x / sigma^2
= x`` under the analytic Gaussian prior, so the perturbation vector
equals ``magnitude * x`` exactly.

Seed policy: the policy is deterministic (no RNG surface touched in
this code path); ``@settings(derandomize=True)`` pins a regression to
a byte-identical shrunk counter-example across runs.
"""

from __future__ import annotations

import math

import pytest

# hypothesis is only present in test/dev venvs.
_hypothesis_spec = pytest.importorskip(
    "hypothesis",
    reason="hypothesis not in venv (install via `uv pip install hypothesis`)",
)

import numpy as np
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.algorithm.perturbation import (
    DEFAULT_BRAI_EPS_SCALE,
    PaperQuantityAttractorInversion,
    PerturbationConfigError,
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


#: Strictly positive, finite magnitude in the canonical BRAI range
#: ``[0.01, 1.0]``. We avoid 0 to sidestep the rejection branch
#: (covered by a dedicated property below) and avoid the open
#: upper bound so the test never probes saturation behaviour.
_MAGNITUDE = st.floats(
    min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False
)
#: Non-positive or non-finite magnitudes — the rejection branch.
_BAD_MAGNITUDE = st.sampled_from([0.0, -0.01, -1e-3, -1.0, float("nan"), float("inf"), float("-inf")])


# ---------------------------------------------------------------------------
# Helper: build a fresh BRAI policy with the canonical default sigma=1.0
# ---------------------------------------------------------------------------


def _make_brai(eps_scale: float = DEFAULT_BRAI_EPS_SCALE) -> PaperQuantityAttractorInversion:
    """Construct a BRAI policy with the canonical sigma=1.0 Gaussian prior."""
    return PaperQuantityAttractorInversion(eps_scale=eps_scale, default_sigma=1.0)


# ---------------------------------------------------------------------------
# H2 core property — perturbation vector is ``magnitude * (-grad)``
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(magnitude=_MAGNITUDE)
def test_brai_magnitude_property(magnitude: float) -> None:
    """Output perturbation magnitude must equal input magnitude kwarg.

    With the analytic Gaussian prior (``sigma = 1``) and a unit-vector
    saturated state ``x = [1.0, 0.0]``, ``-grad = x / sigma^2 = x``,
    so the perturbation vector equals ``magnitude * x``. Therefore
    ``np.linalg.norm(out - x)`` must equal ``magnitude`` to within
    float tolerance (the canonical ``eps_scale = 0.1`` default is
    OVERRIDDEN by the per-call ``magnitude`` kwarg).
    """
    brai = _make_brai()
    x_sat = np.array([1.0, 0.0], dtype=np.float64)
    pq = {"e_rho": 1.0}
    out = brai.propose(x_sat, paper_quantities=pq, t=0.0, magnitude=magnitude)
    delta = out - x_sat
    actual_magnitude = float(np.linalg.norm(delta))
    assert math.isclose(actual_magnitude, magnitude, rel_tol=1e-9, abs_tol=1e-12), (
        f"magnitude={magnitude} -> perturbation norm={actual_magnitude}"
    )


# ---------------------------------------------------------------------------
# Magnitude kwarg overrides the constructor eps_scale (no silent override)
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(magnitude=_MAGNITUDE)
def test_brai_magnitude_overrides_eps_scale(magnitude: float) -> None:
    """``magnitude`` MUST win over the constructor ``eps_scale``.

    Constructed with the canonical ``eps_scale = 0.1``, the policy
    MUST use ``magnitude`` (not ``0.1``) when the caller passes
    ``magnitude`` to ``propose``. We compare the perturbation vector
    to the ``magnitude * x`` baseline; a silent override that ignored
    the kwarg and applied ``eps_scale = 0.1`` would fail this
    assertion for ``magnitude != 0.1``.
    """
    if magnitude == pytest.approx(DEFAULT_BRAI_EPS_SCALE):
        # Skip: at the exact crossover the two are indistinguishable;
        # the previous test already pins the magnitude control.
        return
    brai = _make_brai(eps_scale=DEFAULT_BRAI_EPS_SCALE)
    x_sat = np.array([1.0, 0.0], dtype=np.float64)
    pq = {"e_rho": 1.0}
    out = brai.propose(x_sat, paper_quantities=pq, t=0.0, magnitude=magnitude)
    expected_delta = magnitude * x_sat
    np.testing.assert_allclose(out - x_sat, expected_delta, atol=1e-12)


# ---------------------------------------------------------------------------
# Magnitude kwarg does NOT mutate the instance's eps_scale
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(magnitude=_MAGNITUDE)
def test_brai_magnitude_does_not_mutate_eps_scale(magnitude: float) -> None:
    """A ``magnitude`` kwarg MUST NOT mutate the instance's ``eps_scale``.

    The per-call override is a one-shot knob: the next call without
    ``magnitude`` must use the constructor default. This guards
    against an accidental in-place update that would make later calls
    under- or over-perturb relative to the configured default.
    """
    brai = _make_brai(eps_scale=DEFAULT_BRAI_EPS_SCALE)
    eps_before = brai.eps_scale
    x_sat = np.array([1.0, 0.0], dtype=np.float64)
    pq = {"e_rho": 1.0}
    # Call with magnitude kwarg (override).
    _ = brai.propose(x_sat, paper_quantities=pq, t=0.0, magnitude=magnitude)
    # The instance's eps_scale MUST be unchanged.
    assert brai.eps_scale == pytest.approx(eps_before), (
        f"magnitude={magnitude} mutated eps_scale: {eps_before} -> {brai.eps_scale}"
    )


# ---------------------------------------------------------------------------
# Magnitude kwarg rejection branch — non-positive / non-finite raises
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(bad_magnitude=_BAD_MAGNITUDE)
def test_brai_magnitude_rejects_non_positive(bad_magnitude: float) -> None:
    """``magnitude`` MUST reject non-positive / non-finite inputs.

    Same boundary contract as the constructor ``eps_scale``: zero
    freezes the trajectory, negative or non-finite values are
    numerically meaningless. The helper raises
    :exc:`PerturbationConfigError`.
    """
    brai = _make_brai()
    x_sat = np.array([1.0, 0.0], dtype=np.float64)
    pq = {"e_rho": 1.0}
    with pytest.raises(PerturbationConfigError):
        brai.propose(
            x_sat, paper_quantities=pq, t=0.0, magnitude=bad_magnitude
        )


# ---------------------------------------------------------------------------
# Idempotency — calling propose twice with the same args yields the same
# output. The policy is deterministic; the magnitude kwarg is pure.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(magnitude=_MAGNITUDE)
def test_brai_magnitude_idempotent(magnitude: float) -> None:
    """Calling ``propose`` twice with the same ``magnitude`` yields the same output."""
    brai = _make_brai()
    x_sat = np.array([1.0, 0.0], dtype=np.float64)
    pq = {"e_rho": 1.0}
    out_1 = brai.propose(x_sat, paper_quantities=pq, t=0.0, magnitude=magnitude)
    out_2 = brai.propose(x_sat, paper_quantities=pq, t=0.0, magnitude=magnitude)
    np.testing.assert_array_equal(out_1, out_2)
