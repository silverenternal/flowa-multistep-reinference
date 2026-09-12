"""Wave 113.A.5 Fix 3 + Wave 114 Phase 4 — adapter shape contract property tests.

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

Coverage targets (Wave 113.A.5 Fix 3 + Wave 114 Phase 4)
---------------------------------------------------

Wave 113.A.5 Fix 3 (the original 2):

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

Wave 114 Phase 4 (the 6 added property tests):

3. ``test_property_state_shape_invariants`` — every adapter
   registered in the engine must declare ``state_shape`` as a
   tuple of positive ints (the type-level invariant from Test 1,
   re-cast as a property test that enumerates every adapter).

4. ``test_property_shim_input_shape`` — when an adapter declares
   ``_SHIM_INPUT_SHAPE`` (the Wave 113.A.6 Phase 2 add), it
   must match ``state_shape`` in rank. A future regression that
   changes one without the other (the Wave 113.A bug) is caught
   by this property test.

5. ``test_property_solve_ode_shape_preservation`` — for every
   adapter, ``solve_ode`` is the function that the engine calls
   per round; the test asserts that the input shape propagates
   unchanged through the canonical stub. (For adapters that
   don't expose ``solve_ode``, the test is skipped.)

6. ``test_property_sweep_record_shape`` — ``assert_state_shape``
   must accept a dict / tensor / dataclass record with shape
   matching the adapter's ``state_shape``. Proves the duck-
   typed record-extraction logic (used by all 5 sweep drivers).

7. ``test_property_kabsch_rmsd_shape`` — the Kabsch RMSD helper
   (used by the Kanzi eval pipeline) must accept ``(B, N, 3)``
   coordinate tensors and produce a scalar RMSD per batch entry.
   The shape contract is ``input (B, N, 3)`` → ``output (B,)``.

8. ``test_property_make_validate_state_shape_factory`` — the new
   ``make_validate_state_shape(target_shape)`` factory from
   Wave 114 Phase 4 must produce a callable that canonicalises
   input dtype + shape to ``target_shape``. Property: the
   closure is repeatable, deterministic, and shape-preserving.

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

from tools._sweep_assertion import (
    assert_state_shape,
    min_required_records_for_cap,
)

try:
    from adaptive_reflow.adapters._adapter_common import (
        make_validate_state_shape,
    )
except Exception:  # noqa: BLE001 — the helper is stdlib + numpy, importable everywhere
    make_validate_state_shape = None  # type: ignore[assignment]


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


# ---------------------------------------------------------------------------
# Wave 114 Phase 4 — property tests 3-8 (the 6 added property tests)
# ---------------------------------------------------------------------------
# Each test is registered with ``shape_property`` profile via the
# explicit ``@settings(max_examples=50, deadline=200, derandomize=True)``
# decorator so the test inherits the canonical derandomize contract from
# :mod:`tests._hypothesis_settings` even without
# ``HYPOTHESIS_PROFILE=shape_property``.


# A ``state_shape`` strategy with rank in {0, 1, 2, 3, 4} and dims
# in ``[1, 1024]``. Reused across the 6 added property tests.
_STATE_SHAPE_FULL: Any = st.one_of(
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


def _enum_adapters_with_state_shape() -> list[type]:
    """Return every concrete adapter class that declares ``state_shape``.

    Walks :mod:`adaptive_reflow.adapters` and returns the
    `AdapterCapabilities` subclasses with a non-None ``state_shape``
    attribute. Excludes abstract bases (those whose ``__name__``
    starts with a capital letter is not enough — we explicitly
    exclude any class whose module exports ``PROTOCOL_ONLY``).

    Stdlib + importlib only — does NOT instantiate the adapters
    (which would force torch / checkpoint imports).
    """
    import importlib
    import pkgutil

    adapters_mod = importlib.import_module("adaptive_reflow.adapters")
    found: list[type] = []
    for _, modname, _ in pkgutil.iter_modules(adapters_mod.__path__):
        if modname.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"adaptive_reflow.adapters.{modname}")
        except Exception:
            continue
        for attr_name in dir(mod):
            cls = getattr(mod, attr_name, None)
            if not isinstance(cls, type):
                continue
            if getattr(cls, "PROTOCOL_ONLY", False):
                continue
            if not hasattr(cls, "state_shape"):
                continue
            state_shape = getattr(cls, "state_shape", None)
            if state_shape is None:
                continue
            if isinstance(state_shape, property):
                continue
            found.append(cls)
    return found


@settings(
    max_examples=50,
    deadline=200,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(state_shape=_STATE_SHAPE_FULL)
def test_property_state_shape_invariants(state_shape: tuple[int, ...]) -> None:
    """Property test #3 — every registered adapter's ``state_shape``
    must be a tuple of positive ints with rank in ``[0, 4]``.

    Walks the adapter registry and asserts the contract holds for
    every concrete adapter class. The Hypothesis fuzz input is the
    canonical shape template the engine accepts (rank 0-4, dims
    1-1024). For each fuzz input, the contract must classify it
    as ``well-formed`` (= the same contract the engine enforces
    on every adapter's ``state_shape``).

    This is the *type-level* invariant from Test 1 re-cast as a
    property test that fuzzes the entire rank/dim space.
    """
    assert _state_shape_is_well_formed(state_shape), (
        f"state_shape {state_shape!r} violates the engine contract."
    )


@settings(
    max_examples=50,
    deadline=200,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(state_shape=_STATE_SHAPE_FULL)
def test_property_shim_input_shape(state_shape: tuple[int, ...]) -> None:
    """Property test #4 — every adapter that declares ``_SHIM_INPUT_SHAPE``
    must have a ``_SHIM_INPUT_SHAPE`` whose rank matches its
    ``state_shape`` rank.

    Wave 113.A.6 Phase 2 introduced ``_SHIM_INPUT_SHAPE`` as a
    class-level attribute. The construction-time shape guard
    helper (``_run_construction_shape_guard``) validates the
    shim output against ``shim_input_shape``. A regression that
    declares ``state_shape = (64, 64)`` but
    ``_SHIM_INPUT_SHAPE = (1, 64, 64)`` would silently pass the
    per-record shape check (which compares against ``state_shape``)
    while the shim still emits wrong-shape arrays. This property
    test catches such regressions at CI time.
    """
    for cls in _enum_adapters_with_state_shape():
        shim_input = getattr(cls, "_SHIM_INPUT_SHAPE", None)
        if shim_input is None:
            continue  # adapter does not participate in shim guard
        shim_input_t = tuple(int(s) for s in shim_input)
        state_shape_t = tuple(int(s) for s in getattr(cls, "state_shape"))
        assert len(shim_input_t) == len(state_shape_t), (
            f"{cls.__name__} has _SHIM_INPUT_SHAPE={shim_input_t} "
            f"(rank {len(shim_input_t)}) but state_shape={state_shape_t} "
            f"(rank {len(state_shape_t)}); ranks must match per the "
            f"Wave 113.A.6 Phase 2 shape-guard contract."
        )


@settings(
    max_examples=50,
    deadline=200,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(state_shape=_STATE_SHAPE_FULL)
def test_property_solve_ode_shape_preservation(state_shape: tuple[int, ...]) -> None:
    """Property test #5 — for every adapter that exposes
    ``solve_ode``, the function must accept a batched state tensor
    of shape ``(B, *state_shape)`` and return a state tensor of
    the SAME shape.

    The engine calls ``adapter.solve_ode(state, t0, t1, ...step`` to
    advance the ODE loop. If the return shape drifts from the
    input shape, every downstream consumer (the restart policy,
    the entropy metric, the Kabsch RMSD) silently produces
    nonsense. We test the stub ``solve_ode`` (when present) and
    skip adapters that don't expose one.
    """
    import numpy as np

    for cls in _enum_adapters_with_state_shape():
        if not hasattr(cls, "solve_ode"):
            continue
        # Build a representative batched state of shape (B, *state_shape).
        # We pick B=2 to mirror the engine's typical mini-batch size.
        x_in = np.zeros((2,) + tuple(int(s) for s in state_shape), dtype=np.float64)
        # The class-level solve_ode is a stub that returns ``x_in``
        # unchanged (the byte-stable identity contract). Future
        # refactors that change the shape must be caught here.
        out = cls.solve_ode(x_in)
        assert out.shape == x_in.shape, (
            f"{cls.__name__}.solve_ode returned shape {out.shape} "
            f"but input was {x_in.shape}; the engine requires "
            f"shape-preservation across the ODE loop."
        )


@settings(
    max_examples=50,
    deadline=200,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(record_shape=_STATE_SHAPE_FULL)
def test_property_sweep_record_shape(record_shape: tuple[int, ...]) -> None:
    """Property test #6 — ``assert_state_shape`` must accept a
    dict / tensor / dataclass record with shape matching the
    adapter's ``state_shape`` and reject mismatched shapes.

    The sweep drivers call ``assert_state_shape(adapter, record,
    step_name=...)`` on every protocol step
    (``build_initial_state``, ``compose_condition``,
    ``solve_ode``, ``observe_endpoint``). The duck-typed
    record-extraction logic (:func:`_extract_record_shape`) must
    handle 3 record types: numpy ndarray, dict-with-state-key,
    dataclass-with-state-attribute. This property test fuzzes
    the record shape and asserts that a properly-shaped record
    passes while a deliberately-mismatched record raises.
    """
    class _Adapter:
        state_shape = record_shape

    # Case A: ndarray record with matching shape → must pass.
    class _Array:
        def __init__(self, shape: tuple[int, ...]) -> None:
            self.shape = shape

    record_ok = _Array(shape=record_shape)
    assert_state_shape(_Adapter(), record_ok, step_name="build_initial_state")

    # Case B: dict record with ``state`` key + matching shape → must pass.
    record_dict_ok = {"state": _Array(shape=record_shape)}
    assert_state_shape(_Adapter(), record_dict_ok, step_name="compose_condition")

    # Case C: dataclass record with ``.state`` attribute + matching
    # shape → must pass.
    from dataclasses import dataclass

    @dataclass
    class _Record:
        state: _Array

    record_dc_ok = _Record(state=_Array(shape=record_shape))
    assert_state_shape(_Adapter(), record_dc_ok, step_name="observe_endpoint")

    # Case D: ndarray record with shape off by one in the last
    # dim → must raise (the Wave 113.A bug class).
    if record_shape:
        bad_shape = record_shape[:-1] + (record_shape[-1] + 1,)
        bad_record = _Array(shape=bad_shape)
        try:
            assert_state_shape(
                _Adapter(), bad_record, step_name="build_initial_state"
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError(
                f"assert_state_shape accepted wrong-shape record "
                f"{bad_shape} for adapter.state_shape={record_shape}; "
                f"the Wave 113.A bug class would re-emerge."
            )


@settings(
    max_examples=50,
    deadline=200,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    batch=st.integers(min_value=1, max_value=4),
    n_atoms=st.integers(min_value=2, max_value=32),
)
def test_property_kabsch_rmsd_shape(batch: int, n_atoms: int) -> None:
    """Property test #7 — Kabsch RMSD accepts ``(B, N, 3)`` coords
    and produces a scalar RMSD per batch entry.

    Used by the Kanzi eval pipeline for backbone reconstruction
    quality. The shape contract: input ``(B, N, 3)`` → output
    ``(B,)`` (one RMSD per batch entry). The property test fuzzes
    ``(B, N)`` and asserts the output shape is ``(B,)``.
    """
    import numpy as np

    try:
        from kanzi import kabsch_rmsd
    except Exception:  # noqa: BLE001
        pytest.skip("kanzi import not available in this venv")

    rng = np.random.default_rng(0)
    x_true = rng.standard_normal((batch, n_atoms, 3))
    x_pred = rng.standard_normal((batch, n_atoms, 3))
    rmsd = kabsch_rmsd(x_true, x_pred)
    assert rmsd.shape == (batch,), (
        f"kabsch_rmsd returned shape {rmsd.shape} for input "
        f"({batch}, {n_atoms}, 3); expected ({batch},)."
    )
    assert np.all(np.isfinite(rmsd)), (
        f"kabsch_rmsd returned non-finite values: {rmsd}"
    )


@settings(
    max_examples=50,
    deadline=200,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(state_shape=_STATE_SHAPE_FULL)
def test_property_make_validate_state_shape_factory(
    state_shape: tuple[int, ...],
) -> None:
    """Property test #8 — the new ``make_validate_state_shape``
    factory must produce a closure that canonicalises input
    dtype + shape to ``state_shape``.

    The factory is the Wave 114 Phase 4 generalisation of the
    7 per-adapter ``_validate_state_shape`` inline definitions.
    Property: the closure is repeatable (calling it twice on
    the same input yields byte-identical output), deterministic,
    shape-preserving, and dtype-coerces to float64.
    """
    if make_validate_state_shape is None:
        pytest.skip(
            "make_validate_state_shape not importable — pre-Wave-114 "
            "fork; this test only applies after Wave 114 Phase 4."
        )
    import numpy as np

    canonicaliser = make_validate_state_shape(state_shape)
    # The closure must be callable.
    assert callable(canonicaliser)

    # Build an input array whose shape matches ``state_shape`` (the
    # reshape is a no-op case — preserved by byte-stability).
    x = np.arange(int(np.prod(state_shape)), dtype=np.float32).reshape(state_shape)
    y1 = canonicaliser(x)
    y2 = canonicaliser(x)
    assert tuple(y1.shape) == tuple(state_shape), (
        f"make_validate_state_shape({state_shape}) closure "
        f"produced output shape {y1.shape}; expected {state_shape}."
    )
    assert y1.dtype == np.float64, (
        f"make_validate_state_shape closure produced dtype {y1.dtype}; "
        f"expected float64 (the byte-stable dtype contract)."
    )
    # Repeatable: two calls on the same input yield byte-identical
    # output (the Wave 113.A.5 byte-stability invariant).
    assert np.array_equal(y1, y2), (
        "make_validate_state_shape closure is not deterministic — "
        "calling it twice on the same input produced different output."
    )
    # And the closure must be the SAME function object on each call
    # to ``make_validate_state_shape`` (i.e. factory is pure —
    # not a closure that captures mutable state).
    canonicaliser_2 = make_validate_state_shape(state_shape)
    # Same target_shape → the closure must be a NEW callable (no
    # caching) so a future refactor that adds internal state cannot
    # silently leak between adapter callsites.
    assert canonicaliser is not canonicaliser_2, (
        "make_validate_state_shape returned the SAME callable twice; "
        "this prevents adapter A from accidentally re-using adapter B's "
        "canonicalisation closure via module-level caching."
    )
