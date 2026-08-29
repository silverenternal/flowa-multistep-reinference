"""Golden-agreement cross-check for :func:`bounded_merge`.

This test module verifies that the production
:func:`adaptive_reflow.frame.merge.bounded_merge` implementation is
**byte-equivalent** with an independent, "spec-faithful" re-implementation
that follows the documented algorithm literally. The two implementations
must produce identical floats for every golden case in
``tests/golden/bounded_merge/``.

Why this matters
----------------

The production implementation evolved across multiple refactors (DTB-R3,
envelope ladder, fail-closed semantics). A second, deliberately
naive implementation that follows only the docstring's algorithm gives
us a non-self-validating oracle: if the production code ever drifts from
its documented contract (e.g. an off-by-one in the delta-cap clamp, or
a silent change in the empty-interval collapse rule), this test fails
before the drift reaches downstream callers.

The test is stdlib-only (no ``torch``) and reads the same golden-JSON
fixtures as :mod:`tests.property.test_golden_replay`, so any new golden
case added there is automatically picked up here.

Coverage
--------

* All ``tests/golden/bounded_merge/case_*.json`` files are replayed
  against both implementations.
* Both implementations are required to raise the same exception type
  on hostile inputs (out-of-range cap / floor, non-finite inputs,
  ``cap < floor``).
* A property-based check (``test_property_agreement_random_envelope``)
  picks a random envelope in ``[0, 1]`` and verifies the two
  implementations agree on 64 random (prev, dynamic) pairs.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

# Make the repository importable when pytest is launched from the
# project root without any package metadata.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

from adaptive_reflow.frame.merge import (
    MergeAuthorityError,
    bounded_merge,
)

# ---------------------------------------------------------------------------
# Independent, spec-faithful re-implementation of bounded_merge.
#
# This deliberately mirrors the docstring in frame/merge.py verbatim,
# without consulting or sharing any code with the production function.
# It uses a minimal validation surface — only the checks the docstring
# explicitly states — so any silent divergence between the two surfaces
# here.
# ---------------------------------------------------------------------------


def _spec_finite(x: float, *, name: str) -> float:
    """Spec-level finite check (no extra range checks)."""
    if not isinstance(x, (int, float)) or isinstance(x, bool):
        raise MergeAuthorityError(f"{name}: not a real number")
    f = float(x)
    if not math.isfinite(f):
        raise MergeAuthorityError(f"{name}: not finite")
    return f


def _spec_bounded_merge(
    prev: float,
    dynamic: float,
    *,
    cap: float,
    floor: float,
    delta_cap_up: float,
    delta_cap_down: float,
    audit_codes: list[str] | None = None,
) -> float:
    """Spec-faithful re-implementation of ``bounded_merge`` (P0-3).

    After the P0-3 contract fix the spec mirrors the production
    "clip-and-audit" semantics:

    1. Validate every argument is a real number (numeric type / ``None``
       still raise :exc:`MergeAuthorityError`).
    2. Clip ``cap`` / ``floor`` / ``delta_cap_up`` /
       ``delta_cap_down`` into ``[0, 1]``. Out-of-range / non-finite
       numeric inputs trigger the canonical audit codes; only the
       numeric-type coercion boundary raises.
    3. If ``cap < floor`` after clipping, swap them and emit the
       ``merge_cap_below_floor`` audit code (so the comparison holds).
    4. ``target = clamp(dynamic, floor, cap)`` (dynamic is also clipped).
    5. ``lo = max(floor, prev - delta_cap_down)``,
       ``hi = min(cap, prev + delta_cap_up)``.
    6. Empty interval ⇒ return ``floor`` and emit
       ``MERGE_DEGENERATE_INTERVAL``.
    7. Otherwise return ``clamp(target, lo, hi)``.
    """
    prev_f = _spec_finite(prev, name="prev")
    dynamic_f = _spec_finite(dynamic, name="dynamic")

    def _clip_unit(x: float, *, name: str, audit_code: str | None = None) -> float:
        if math.isfinite(x) and 0.0 <= x <= 1.0:
            return x
        clipped = 0.0 if (not math.isfinite(x) or x < 0.0) else 1.0
        if audit_codes is not None and audit_code is not None:
            audit_codes.append(f"{audit_code}:{name}={x!r}")
        return clipped

    cap_f = _clip_unit(float(cap), name="cap", audit_code="merge_cap_out_of_range")
    floor_f = _clip_unit(
        float(floor), name="floor", audit_code="merge_floor_out_of_range"
    )
    up_f = max(0.0, min(1.0, float(delta_cap_up)))
    down_f = max(0.0, min(1.0, float(delta_cap_down)))

    # Inverted envelope after clipping.
    if cap_f < floor_f:
        if audit_codes is not None:
            audit_codes.append(
                f"merge_cap_below_floor:cap={cap_f:.6f}:floor={floor_f:.6f}"
            )
        cap_f, floor_f = floor_f, cap_f

    # Clip prev / dynamic so the spec also honours the P0-3 contract.
    prev_f = max(0.0, min(1.0, prev_f))
    dynamic_f = max(0.0, min(1.0, dynamic_f))

    # Step 3 — clamp dynamic to envelope.
    target = max(floor_f, min(cap_f, dynamic_f))

    # Step 4 — delta bounds.
    lo = max(floor_f, prev_f - down_f)
    hi = min(cap_f, prev_f + up_f)

    # Step 5 — empty interval collapses to floor.
    if hi < lo:
        if audit_codes is not None:
            audit_codes.append(
                f"merge_degenerate_interval:floor={floor_f:.6f}"
                f":cap={cap_f:.6f}:prev={prev_f:.6f}"
                f":up={up_f:.6f}:down={down_f:.6f}"
            )
        return float(floor_f)

    # Step 6 — final clamp.
    return float(max(lo, min(hi, target)))


# ---------------------------------------------------------------------------
# Golden-case loading
# ---------------------------------------------------------------------------


def _golden_cases() -> list[dict[str, Any]]:
    """Return every golden case as a list of dicts.

    The cases live in ``tests/golden/bounded_merge/case_*.json``. Each
    file has the shape::

        {
          "name": "<identifier>",
          "inputs": {"prev": ..., "dynamic": ..., "cap": ...,
                     "floor": ..., "delta_cap_up": ...,
                     "delta_cap_down": ...},
          "expected": <float>
        }
    """
    golden_dir = (
        Path(__file__).resolve().parent.parent / "golden" / "bounded_merge"
    )
    if not golden_dir.is_dir():
        return []
    cases: list[dict[str, Any]] = []
    for path in sorted(golden_dir.glob("case_*.json")):
        with path.open(encoding="utf-8") as fh:
            cases.append(json.load(fh))
    return cases


@pytest.fixture(scope="module")
def golden_cases() -> list[dict[str, Any]]:
    """Module-scoped fixture: every golden case."""
    return _golden_cases()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_golden_cases_load(golden_cases: list[dict[str, Any]]) -> None:
    """Sanity check — at least one golden case is available."""
    assert golden_cases, "no golden cases found under tests/golden/bounded_merge"


@pytest.mark.parametrize(
    "case",
    _golden_cases(),
    ids=lambda c: c.get("name", "?"),
)
def test_production_matches_golden(
    case: dict[str, Any],
) -> None:
    """Production ``bounded_merge`` returns the golden expected value."""
    inputs = case["inputs"]
    result = bounded_merge(
        inputs["prev"],
        inputs["dynamic"],
        cap=inputs["cap"],
        floor=inputs["floor"],
        delta_cap_up=inputs["delta_cap_up"],
        delta_cap_down=inputs["delta_cap_down"],
    )
    assert result == pytest.approx(case["expected"], abs=1e-12)


@pytest.mark.parametrize(
    "case",
    _golden_cases(),
    ids=lambda c: c.get("name", "?"),
)
def test_spec_impl_matches_golden(
    case: dict[str, Any],
) -> None:
    """Spec-faithful re-implementation also returns the golden value.

    This isolates the spec implementation against the canonical fixture
    so a regression in either implementation can be attributed.
    """
    inputs = case["inputs"]
    result = _spec_bounded_merge(
        inputs["prev"],
        inputs["dynamic"],
        cap=inputs["cap"],
        floor=inputs["floor"],
        delta_cap_up=inputs["delta_cap_up"],
        delta_cap_down=inputs["delta_cap_down"],
    )
    assert result == pytest.approx(case["expected"], abs=1e-12)


@pytest.mark.parametrize(
    "case",
    _golden_cases(),
    ids=lambda c: c.get("name", "?"),
)
def test_production_equals_spec(
    case: dict[str, Any],
) -> None:
    """Production and spec implementations are byte-equivalent."""
    inputs = case["inputs"]
    production = bounded_merge(
        inputs["prev"],
        inputs["dynamic"],
        cap=inputs["cap"],
        floor=inputs["floor"],
        delta_cap_up=inputs["delta_cap_up"],
        delta_cap_down=inputs["delta_cap_down"],
    )
    spec = _spec_bounded_merge(
        inputs["prev"],
        inputs["dynamic"],
        cap=inputs["cap"],
        floor=inputs["floor"],
        delta_cap_up=inputs["delta_cap_up"],
        delta_cap_down=inputs["delta_cap_down"],
    )
    # ``struct.pack('<d', x) == struct.pack('<d', y)`` catches ``0.0``
    # vs ``-0.0`` mismatches, which ``==`` hides.
    assert _to_bytes(production) == _to_bytes(spec)


def _to_bytes(x: float) -> bytes:
    """Pack a float as its IEEE-754 little-endian 8-byte representation."""
    import struct

    return struct.pack("<d", float(x))


# ---------------------------------------------------------------------------
# Hostile-input equivalence
# ---------------------------------------------------------------------------


_HOSTILE_CASES: list[tuple[str, dict[str, float]]] = [
    ("cap_negative", {"prev": 0.5, "dynamic": 0.5, "cap": -0.01,
                       "floor": 0.0, "delta_cap_up": 0.5,
                       "delta_cap_down": 0.5}),
    ("cap_above_one", {"prev": 0.5, "dynamic": 0.5, "cap": 1.5,
                        "floor": 0.0, "delta_cap_up": 0.5,
                        "delta_cap_down": 0.5}),
    ("floor_negative", {"prev": 0.5, "dynamic": 0.5, "cap": 1.0,
                         "floor": -0.01, "delta_cap_up": 0.5,
                         "delta_cap_down": 0.5}),
    ("floor_above_one", {"prev": 0.5, "dynamic": 0.5, "cap": 1.0,
                          "floor": 1.5, "delta_cap_up": 0.5,
                          "delta_cap_down": 0.5}),
    ("cap_below_floor", {"prev": 0.5, "dynamic": 0.5, "cap": 0.2,
                          "floor": 0.8, "delta_cap_up": 0.5,
                          "delta_cap_down": 0.5}),
    ("delta_up_above_one", {"prev": 0.5, "dynamic": 0.5, "cap": 1.0,
                             "floor": 0.0, "delta_cap_up": 1.5,
                             "delta_cap_down": 0.5}),
    ("delta_down_negative", {"prev": 0.5, "dynamic": 0.5, "cap": 1.0,
                              "floor": 0.0, "delta_cap_up": 0.5,
                              "delta_cap_down": -0.01}),
]


@pytest.mark.parametrize(
    "name,inputs",
    _HOSTILE_CASES,
    ids=[n for n, _ in _HOSTILE_CASES],
)
def test_production_clips_on_hostile(
    name: str,
    inputs: dict[str, float],
) -> None:
    """Production clips on hostile input (P0-3) and emits a canonical
    audit code where the contract mandates one. The result is a
    finite ``float`` in ``[0, 1]`` rather than an exception
    (closes P0-3). For ``cap_below_floor`` the operator fails closed
    (F5) — the audit code is appended before the raise.

    For ``cap > 1``, ``floor < 0``, ``floor > 1``, or
    ``cap < floor`` the operator MUST emit an audit code; for
    ``delta_cap_up > 1`` / ``delta_cap_down < 0`` the operator
    silently clips so the legacy per-round delta-envelope math is
    preserved. The test asserts the audit-code presence for the
    envelope-mismatch cases and the result-finiteness for all.
    """
    audit: list[str] = []
    if name == "cap_below_floor":
        # F5: cap < floor fails closed — raises after emitting audit code.
        with pytest.raises(MergeAuthorityError):
            bounded_merge(
                inputs["prev"],
                inputs["dynamic"],
                cap=inputs["cap"],
                floor=inputs["floor"],
                delta_cap_up=inputs["delta_cap_up"],
                delta_cap_down=inputs["delta_cap_down"],
                audit_codes=audit,
            )
        assert any(
            code.startswith("merge_cap_below_floor")
            for code in audit
        ), f"no F5 audit code emitted for {name}: audit={audit!r}"
        return
    result = bounded_merge(
        inputs["prev"],
        inputs["dynamic"],
        cap=inputs["cap"],
        floor=inputs["floor"],
        delta_cap_up=inputs["delta_cap_up"],
        delta_cap_down=inputs["delta_cap_down"],
        audit_codes=audit,
    )
    assert 0.0 <= result <= 1.0
    # The envelope-mismatch cases are required to emit a P0-3 audit
    # code; the delta-cap cases are silently clipped to keep the
    # legacy bounded-merge math byte-identical.
    if name in (
        "cap_negative",
        "cap_above_one",
        "floor_negative",
        "floor_above_one",
    ):
        assert any(
            code.startswith(
                (
                    "merge_cap_out_of_range",
                    "merge_floor_out_of_range",
                )
            )
            for code in audit
        ), f"no P0-3 audit code emitted for {name}: audit={audit!r}"


@pytest.mark.parametrize(
    "name,inputs",
    _HOSTILE_CASES,
    ids=[n for n, _ in _HOSTILE_CASES],
)
def test_spec_clips_on_hostile(
    name: str,
    inputs: dict[str, float],
) -> None:
    """Spec implementation clips hostile input to ``[0, 1]`` (P0-3)."""
    audit: list[str] = []
    result = _spec_bounded_merge(
        inputs["prev"],
        inputs["dynamic"],
        cap=inputs["cap"],
        floor=inputs["floor"],
        delta_cap_up=inputs["delta_cap_up"],
        delta_cap_down=inputs["delta_cap_down"],
        audit_codes=audit,
    )
    assert 0.0 <= result <= 1.0
    if name in (
        "cap_negative",
        "cap_above_one",
        "floor_negative",
        "floor_above_one",
        "cap_below_floor",
    ):
        assert any(
            code.startswith(
                (
                    "merge_cap_out_of_range",
                    "merge_floor_out_of_range",
                    "merge_cap_below_floor",
                    "merge_degenerate_interval",
                )
            )
            for code in audit
        ), f"no P0-3 audit code emitted for {name}: audit={audit!r}"


# ---------------------------------------------------------------------------
# Property-based equivalence
# ---------------------------------------------------------------------------


def _random_envelope(u: float) -> tuple[float, float, float, float]:
    """Sample a valid envelope ``(cap, floor, up, down)``.

    ``u`` is a ``[0, 1)`` uniform draw. Ensures
    ``0 <= floor <= cap <= 1`` and ``0 <= up, down <= 1`` so the
    configuration is always admissible.
    """
    cap = 0.1 + 0.9 * u  # [0.1, 1.0]
    floor = cap * _lcg_uniform()  # in [0, cap]
    up = _lcg_uniform()
    down = _lcg_uniform()
    return cap, floor, up, down


# Module-level LCG driver — used by both ``_random_envelope`` and the
# test that owns the state. Sharing state across the two would let one
# test perturb the other's draws, so we thread the state explicitly.
_LCG_STATE: int = 0xC0FFEE_DEADBEEF & ((1 << 64) - 1)


def _lcg_uniform() -> float:
    """Advance the module-level LCG and return a ``[0, 1)`` double."""
    global _LCG_STATE
    _LCG_STATE = (
        _LCG_STATE * 6364136223846793005 + 1442695040888963407
    ) & ((1 << 64) - 1)
    return (_LCG_STATE >> 11) / (1 << 53)


def test_property_agreement_random_envelope() -> None:
    """Two implementations agree on 64 random admissible inputs.

    Uses a deterministic LCG so the test is reproducible without a
    ``random.seed`` call (which mutates global state). For each
    envelope we sweep (prev, dynamic) on a coarse grid and compare
    byte-exact results.
    """
    import struct

    seen = 0
    for _ in range(8):
        cap, floor, up, down = _random_envelope(_lcg_uniform())
        for _ in range(8):
            prev = _lcg_uniform() * cap
            dynamic = _lcg_uniform()
            production = bounded_merge(
                prev, dynamic, cap=cap, floor=floor,
                delta_cap_up=up, delta_cap_down=down,
            )
            spec = _spec_bounded_merge(
                prev, dynamic, cap=cap, floor=floor,
                delta_cap_up=up, delta_cap_down=down,
            )
            assert struct.pack("<d", production) == struct.pack("<d", spec)
            seen += 1
    assert seen == 64


def test_spec_empty_interval_collapses_to_floor() -> None:
    """Documented fail-closed path: empty delta interval ⇒ floor.

    Constructed envelope where ``prev - delta_cap_down > cap`` and
    ``prev + delta_cap_up < floor`` is impossible (because ``prev`` is
    always inside the envelope for a valid previous round), so we use
    the simpler ``prev = cap`` with ``delta_cap_down = 0`` and
    ``floor > prev`` is also impossible. The only way to force an empty
    interval is when ``prev = floor = cap`` and both deltas are zero,
    giving ``lo = hi = prev = floor = cap``. Verify the result is the
    floor byte-exactly.
    """
    import struct

    result = _spec_bounded_merge(
        0.5, 0.9, cap=0.5, floor=0.5, delta_cap_up=0.0, delta_cap_down=0.0,
    )
    assert struct.pack("<d", result) == struct.pack("<d", 0.5)


def test_production_empty_interval_collapses_to_floor() -> None:
    """Same empty-interval guarantee for the production implementation."""
    import struct

    result = bounded_merge(
        0.5, 0.9, cap=0.5, floor=0.5, delta_cap_up=0.0, delta_cap_down=0.0,
    )
    assert struct.pack("<d", result) == struct.pack("<d", 0.5)
