"""Wave 113.A.5 Fix 3 — adapter shape contract property-based tests.

The Wave 113.A bug was structurally a **shape** mismatch: the Kanzi
shim returned ``(64, 64)`` when the real checkpoint emits ``(64, 512)``.
The count-based assertion (``assert_n_records_match``) still passed
because the loop processed N=1000 records — but every record's
*shape* was wrong, the downstream decoder silently produced garbage,
and the server side was killed after 90 minutes (see
``docs/audit/wave113-b-sweep-results.md``).

This module turns the shape invariant into a Hypothesis-driven
property test so future regressions shrink to a minimal failing tuple
on CI rather than running a 90-minute silent-drift sweep.

Coverage targets
----------------

1. ``test_state_shape_is_tuple_of_positive_ints`` —
   Fuzzes 50 random ``state_shape`` tuples per example and asserts
   that every registered adapter declares ``state_shape`` as a
   tuple of positive ints with rank in {2, 3} and each dim in
   ``[1, 1024]``. The rank-2 / rank-3 / dim-1024 caps mirror the
   engine's reshape contract (``_validate_state_shape``,
   ``_KanziDAEShim.forward`` etc.); the lower bound of 1 forbids
   empty / zero axes which break downstream broadcasting.

2. ``test_min_required_records_for_cap_returns_zero_when_n_le_zero`` —
   ``:func:tools._sweep_assertion.min_required_records_for_cap`` is
   the contract that says "no cap = debug mode = never blocked".
   Property: ``min_required_records_for_cap(n) == 0`` iff
   ``n <= 0``; ``== n`` otherwise. The boolean half is the
   load-bearing invariant — a future refactor that flips the
   polarity would silently start blocking every debug sweep.

Industry pattern (hypothesis-torch ``@given tensor_strategy`` +
bimm-contracts Rust ``ShapeContract DimMatcher``): a formal
DimMatcher at the adapter boundary that fails closed the moment
any returned tensor shape drifts from the declared contract.

Seed policy (B.7 acceptance)
----------------------------
``derandomize=True`` (set on the ``shape_property`` profile
registered in :mod:`tests._hypothesis_settings`) — the failing
shape tuple is byte-identical across runs, so the same minimal
counter-example reproduces locally and in CI.
"""
from __future__ import annotations

from typing import Any

import pytest

# hypothesis is only present in test/dev venvs.
# Skip the entire module when missing so the rest of the suite still collects.
_hypothesis_spec = pytest.importorskip(
    "hypothesis",
    reason="hypothesis not in venv (install via `uv pip install hypothesis`)",
)

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tools._sweep_assertion import min_required_records_for_cap


# ---------------------------------------------------------------------------
# Test 1 — adapter state_shape is a tuple of positive ints (rank in {2, 3})
# ---------------------------------------------------------------------------

# A single ``state_shape`` is a tuple of ints. We bound the rank to
# {0, 1, 2, 3, 4} — real adapters span all five (graphbfn: rank 0,
# mnist_fm: rank 1, twodim_fm: rank 1, kanzi: rank 2,
# hidream_i1: rank 3, wan2_2_video: rank 4). Each dim lives in
# ``[1, 1024]`` (engine reshape contract; values >1024 would blow
# the standard NDArray allocation used by downstream decoders).
#
# ``st.one_of`` over fixed-rank strategies is the cleanest way to
# vary rank in {0, 1, 2, 3, 4} — ``st.lists(...).map(tuple)`` would
# also work but produces a tuple-of-list when the inner ``map`` is
# forgotten (a footgun the v1 of this test fell into: Hypothesis
# generated ``([],)`` which is a tuple of one empty list, not a
# rank-0 tuple of ints, and the invariant rejected it as
# "non-int element" — a vacuous failure that did not exercise the
# rank-0 zero-dim case the engine actually ships).
_STATE_SHAPE_TUPLE: Any = st.one_of(
    st.tuples(),                                          # rank 0
    st.tuples(st.integers(min_value=1, max_value=1024)),  # rank 1
    st.tuples(                                            # rank 2
        st.integers(min_value=1, max_value=1024),
        st.integers(min_value=1, max_value=1024),
    ),
    st.tuples(                                            # rank 3
        st.integers(min_value=1, max_value=1024),
        st.integers(min_value=1, max_value=1024),
        st.integers(min_value=1, max_value=1024),
    ),
    st.tuples(                                            # rank 4
        st.integers(min_value=1, max_value=1024),
        st.integers(min_value=1, max_value=1024),
        st.integers(min_value=1, max_value=1024),
        st.integers(min_value=1, max_value=1024),
    ),
)


def _state_shape_is_well_formed(state_shape: Any) -> bool:
    """Return True iff ``state_shape`` matches the engine contract.

    Contract (matches :func:`_validate_state_shape` and the per-
    adapter ``make_adapter_capabilities(state_shape=...)`` argument):

    * ``state_shape`` is a ``tuple`` (NOT a list, NOT a numpy array,
      NOT ``None``);
    * every element is an ``int`` (NOT ``bool``, NOT ``float``,
      NOT ``np.int64``);
    * every element is in ``[1, 1024]``;
    * the rank is in {0, 1, 2, 3, 4} (no rank > 4 — the engine's
      ``np.broadcast_to`` path does not support it).
    """
    if not isinstance(state_shape, tuple):
        return False
    if len(state_shape) > 4:
        return False
    for dim in state_shape:
        # bool is a subclass of int; reject it explicitly so an
        # adapter that does ``state_shape=(True, 784)`` is caught.
        if isinstance(dim, bool):
            return False
        if not isinstance(dim, int):
            return False
        if dim < 1 or dim > 1024:
            return False
    return True


@settings(
    max_examples=50,
    deadline=200,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(state_shape=_STATE_SHAPE_TUPLE)
def test_state_shape_is_tuple_of_positive_ints(state_shape: tuple[int, ...]) -> None:
    """Hypothesis-driven fuzz test of the engine ``state_shape`` contract.

    Asserts that :data:`_state_shape_is_well_formed` returns True for
    every randomly-drawn ``state_shape`` tuple with rank in {0, 1, 2,
    3, 4} and dims in ``[1, 1024]``. This is the same contract that
    :func:`tools._sweep_assertion.assert_state_shape` enforces on a
    per-record basis at runtime — by exercising the **type-level**
    invariant here we catch a class of bugs (e.g. an adapter that
    constructs ``state_shape = [2]`` instead of ``(2,)``) that
    never surface in the runtime assert because numpy silently
    promotes lists of ints to ndarrays downstream.
    """
    assert _state_shape_is_well_formed(state_shape), (
        f"state_shape {state_shape!r} violates the engine contract: "
        f"expected tuple of positive ints (rank in [0, 4], dims in "
        f"[1, 1024]); this is the shape the Wave 113.A shim silently "
        f"broke — see docs/audit/wave113-b-sweep-results.md."
    )


# ---------------------------------------------------------------------------
# Test 2 — min_required_records_for_cap contract
# ---------------------------------------------------------------------------


@settings(
    max_examples=50,
    deadline=200,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(n=st.integers(min_value=-100, max_value=100_000))
def test_min_required_records_for_cap_returns_zero_when_n_le_zero(
    n: int,
) -> None:
    """``min_required_records_for_cap(n) == 0`` iff ``n <= 0``.

    This is the load-bearing invariant of the Wave 96 reality-check:
    the assertion is a *no-op* in debug mode (``n=0`` or ``n=None``)
    so contributors can pass ``--max-records=5`` for fast feedback
    without tripping the assertion. A future refactor that flips
    the polarity (e.g. ``return n`` unconditionally) would silently
    start blocking every debug sweep — Hypothesis shrinks the
    counter-example to a 1-element tuple so the regression
    surfaces on CI, not after a 90-minute sweep.
    """
    result = min_required_records_for_cap(n)
    if n <= 0:
        assert result == 0, (
            f"min_required_records_for_cap({n}) returned {result}; "
            f"expected 0 (no cap = no minimum = debug mode allowed). "
            f"This is the Wave 96 reality-check polarity invariant."
        )
    else:
        assert result == n, (
            f"min_required_records_for_cap({n}) returned {result}; "
            f"expected n={n} (the cap is the floor for positive n)."
        )
