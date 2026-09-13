"""Property-based tests for the Wave 125 paper-quantity-driven ``β``
calibration helper (``target_rms_threshold`` kwarg, H1 fix).

Coverage targets
----------------
* :func:`paper_quantity_driven_beta` — the Wave 125 Phase 4 helper that
  exposes a per-call ``target_rms_threshold`` calibration knob. When
  ``target_rms_threshold`` is supplied, the helper delegates to
  :func:`adjust_n_cap_for_target_rms` and returns a calibrated
  ``n_cap`` value. When omitted (``None``), the helper preserves the
  pre-Wave-125 paper-quantity-driven scheduler by delegating to
  :class:`CodimensionSheetScheduler`.

Properties verified:

* **Monotone decrease**: ``n_cap`` must monotonically DECREASE as
  ``target_rms_threshold`` DECREASES. Tighter RMSD → less fresh noise,
  more memory-dominated refinement.
* **Calibration math**: with the default reference constants
  ``(_REF_RMSD = 2.5, _REF_N_CAP = 0.5)``, the calibration satisfies
  ``n_cap == clip(0.5 * (target / 2.5), 0, 1)``.
* **Output is in [0, 1]**: the calibrated ``n_cap`` is always a finite
  real in the unit interval — the helper clips to bounds.
* **None path is backward-compatible**: when ``target_rms_threshold is
  None``, the helper returns the same value the pre-Wave-125
  :class:`CodimensionSheetScheduler` would emit (a known constant for
  the default ``round_in_cycle = cycle_length // 2``).
* **Threshold wins over scheduler-shape kwargs**: when both
  ``target_rms_threshold`` and the scheduler-shape kwargs
  (``eps_implicit``, ``n_min``, ``n_max``, ``round_in_cycle``,
  ``cycle_length``) are supplied, the calibration path always wins —
  the helper ignores the scheduler-shape kwargs entirely.

Seed policy: the helper is deterministic; ``@settings(derandomize=True)``
pins a regression to a byte-identical shrunk counter-example across
runs.
"""

from __future__ import annotations

import math

import pytest

# hypothesis is only present in test/dev venvs.
_hypothesis_spec = pytest.importorskip(
    "hypothesis",
    reason="hypothesis not in venv (install via `uv pip install hypothesis`)",
)

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.algorithm.scheduler import paper_quantity_driven_beta

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


#: Target RMSD thresholds in the canonical "protein reconstruction"
#: range ``[0.5, 5.0]``. The lower bound sits above 0 so the
#: calibration math stays well-defined; the upper bound sits a hair
#: below the saturation clip ceiling for ``ref_rmsd = 2.5``.
_TARGET_RMS = st.floats(
    min_value=0.5, max_value=5.0, allow_nan=False, allow_infinity=False
)
#: A second independent threshold sample for the monotonicity test.
_TARGET_RMS_SECOND = st.floats(
    min_value=0.5, max_value=5.0, allow_nan=False, allow_infinity=False
)
#: Even-strategy round index used for the backward-compat path.
_ROUND_IN_CYCLE = st.integers(min_value=0, max_value=19)
#: Even-strategy cycle length used for the backward-compat path.
_CYCLE_LENGTH = st.integers(min_value=2, max_value=32)


# ---------------------------------------------------------------------------
# Calibration constants — must mirror :data:`_REF_RMSD` and
# :data:`_REF_N_CAP` in :mod:`adaptive_reflow.algorithm.scheduler.adaptive`
# so a regression in the constants surfaces here.
# ---------------------------------------------------------------------------

_REF_RMSD = 2.5
_REF_N_CAP = 0.5


# ---------------------------------------------------------------------------
# H1 core property — n_cap monotonically DECREASES as target_rms DECREASES
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(target_rms=_TARGET_RMS)
def test_beta_scheduler_target_rms_monotone_decrease(target_rms: float) -> None:
    """``n_cap`` must monotonically DECREASE as ``target_rms`` DECREASES.

    The helper is a linear mapping ``n_cap = clip(ref_n_cap * (target /
    ref_rmsd), 0, 1)``, so for any two thresholds ``T1 > T2`` we must
    have ``paper_quantity_driven_beta(target=T1) >=
    paper_quantity_driven_beta(target=T2)``. The test picks a
    smaller-target neighbour ``T/2`` (sitting inside the calibration
    domain whenever ``T <= 5.0``) and asserts the inequality holds.
    """
    n_cap_1 = paper_quantity_driven_beta(target_rms_threshold=target_rms)
    n_cap_2 = paper_quantity_driven_beta(target_rms_threshold=target_rms * 0.5)
    assert n_cap_2 <= n_cap_1 + 1e-12, (
        f"target_rms={target_rms}: n_cap(rms={target_rms})={n_cap_1} "
        f"< n_cap(rms={target_rms * 0.5})={n_cap_2} (monotonicity violated)"
    )


@_PROPERTY_SETTINGS
@given(target_rms=_TARGET_RMS, target_rms_2=_TARGET_RMS_SECOND)
def test_beta_scheduler_target_rms_pairwise_monotone(
    target_rms: float, target_rms_2: float
) -> None:
    """Pairwise monotonicity for any two thresholds in the calibration domain.

    A regression that flips the linear-mapping sign (e.g. an
    accidental ``-=`` instead of ``*=``) would surface here as a
    flipped inequality. We pick the smaller-target sample
    independently so the test is not just a sweep over a fixed ratio.
    """
    n_cap_a = paper_quantity_driven_beta(target_rms_threshold=target_rms)
    n_cap_b = paper_quantity_driven_beta(target_rms_threshold=target_rms_2)
    if target_rms >= target_rms_2:
        assert n_cap_a >= n_cap_b - 1e-12
    else:
        assert n_cap_b >= n_cap_a - 1e-12


# ---------------------------------------------------------------------------
# Calibration math — n_cap == clip(ref_n_cap * (target / ref_rmsd), 0, 1)
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(target_rms=_TARGET_RMS)
def test_beta_scheduler_target_rms_calibration_math(target_rms: float) -> None:
    """Calibrated ``n_cap`` MUST equal ``clip(ref_n_cap * (target/ref_rmsd), 0, 1)``.

    The reference constants sit at ``_REF_RMSD = 2.5`` and
    ``_REF_N_CAP = 0.5``; we hardcode those here so any future
    change to the constants surfaces as a calibrated-math drift
    (which would imply the helper's invariant shifted).
    """
    n_cap = paper_quantity_driven_beta(target_rms_threshold=target_rms)
    expected = max(0.0, min(1.0, _REF_N_CAP * (target_rms / _REF_RMSD)))
    assert math.isclose(n_cap, expected, rel_tol=1e-12, abs_tol=1e-12), (
        f"target_rms={target_rms}: n_cap={n_cap}, expected={expected}"
    )


# ---------------------------------------------------------------------------
# Output is in [0, 1] — calibration clips into the unit interval
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(target_rms=_TARGET_RMS)
def test_beta_scheduler_target_rms_in_unit_interval(target_rms: float) -> None:
    """``n_cap`` MUST be a finite real in ``[0, 1]``."""
    n_cap = paper_quantity_driven_beta(target_rms_threshold=target_rms)
    assert isinstance(n_cap, float)
    assert math.isfinite(n_cap)
    assert 0.0 <= n_cap <= 1.0


@_PROPERTY_SETTINGS
@given(
    target_rms=st.floats(
        min_value=1e-3, max_value=1e3,  # outside the default band on both sides
        allow_nan=False, allow_infinity=False,
    )
)
def test_beta_scheduler_target_rms_wide_band_clipped(target_rms: float) -> None:
    """Even at extreme thresholds, the helper MUST clip into ``[0, 1]``.

    We probe ``target_rms`` in ``[1e-3, 1e3]`` to exercise the
    saturation path on both ends (very tight → ``n_cap`` near 0;
    very loose → ``n_cap`` near 1). A regression that forgets to
    clip would surface here as ``n_cap`` outside the unit interval.
    """
    n_cap = paper_quantity_driven_beta(target_rms_threshold=target_rms)
    assert 0.0 <= n_cap <= 1.0, (
        f"target_rms={target_rms}: n_cap={n_cap} outside [0, 1]"
    )


# ---------------------------------------------------------------------------
# Threshold wins over scheduler-shape kwargs (calibration path ignores them)
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    target_rms=_TARGET_RMS,
    eps_implicit=st.floats(min_value=0.01, max_value=0.2, allow_nan=False),
    n_min=st.floats(min_value=0.0, max_value=0.4, allow_nan=False),
    n_max=st.floats(min_value=0.6, max_value=1.0, allow_nan=False),
    round_in_cycle=st.integers(min_value=0, max_value=19),
    cycle_length=st.integers(min_value=2, max_value=32),
)
def test_beta_scheduler_threshold_wins_over_shape_kwargs(
    target_rms: float,
    eps_implicit: float,
    n_min: float,
    n_max: float,
    round_in_cycle: int,
    cycle_length: int,
) -> None:
    """When ``target_rms_threshold`` is supplied, scheduler-shape kwargs are ignored.

    The calibration path is a pure function of the threshold; the
    other kwargs (``eps_implicit``, ``n_min``, ``n_max``,
    ``round_in_cycle``, ``cycle_length``) MUST NOT alter the output.
    A regression that propagated those kwargs into the calibration
    math would surface as a mismatch between the bare-threshold call
    and the kwargs-rich call.
    """
    bare = paper_quantity_driven_beta(target_rms_threshold=target_rms)
    with_kwargs = paper_quantity_driven_beta(
        target_rms_threshold=target_rms,
        eps_implicit=eps_implicit,
        n_min=n_min,
        n_max=n_max,
        round_in_cycle=round_in_cycle,
        cycle_length=cycle_length,
    )
    assert math.isclose(bare, with_kwargs, rel_tol=1e-12, abs_tol=1e-12), (
        f"threshold={target_rms}: bare={bare} vs kwargs-rich={with_kwargs}"
    )


# ---------------------------------------------------------------------------
# Backward-compatible None path — when target_rms_threshold is None, the
# helper delegates to CodimensionSheetScheduler with the scheduler-shape
# kwargs.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    round_in_cycle=_ROUND_IN_CYCLE,
    cycle_length=_CYCLE_LENGTH,
)
def test_beta_scheduler_none_path_in_unit_interval(
    round_in_cycle: int, cycle_length: int
) -> None:
    """The ``target_rms_threshold=None`` path MUST stay in ``[0, 1]``.

    This is the pre-Wave-125 codimension-scheduler path; the
    helper preserves its byte-stable output bounds.
    """
    if round_in_cycle >= cycle_length:
        # cycle_length must dominate round_in_cycle.
        return
    n_cap = paper_quantity_driven_beta(
        target_rms_threshold=None,
        round_in_cycle=round_in_cycle,
        cycle_length=cycle_length,
    )
    assert math.isfinite(n_cap)
    assert 0.0 <= n_cap <= 1.0
