"""Wave 25 F.6 per-subsystem floor targeted tests.

Addresses the 4 actionable theory-subsystem SM/TF survivors catalogued
in `docs/mutation_audit_q4_2026.md` §5.1 (theory 0.500 -> >= 0.625):

* SM @ ``adaptive_reflow/theory/checkers.py:143`` -- the
  ``or`` branch inside ``Theorem1Statement.__post_init__``
  (``not isinstance(v, (int, float)) or isinstance(v, bool)``)
  survives the existing test battery because the happy-path
  Theorem1Statement constructors never pass a Python ``bool``.
  With the SM mutation ``or -> and``, ``isinstance(True, int)``
  returns ``True`` so the ``not isinstance`` half is ``False``
  and the raise is skipped; a bool then silently coerces via
  ``float(True) = 1.0`` downstream.

* SM @ ``adaptive_reflow/theory/checkers.py:146`` -- the
  ``or`` branch inside ``Theorem1Statement.__post_init__``
  (``fv != fv or fv in (float("inf"), float("-inf"))``)
  survives because no existing fixture passes ``NaN``. With
  the SM mutation ``or -> and``, both halves must be true; for
  ``NaN`` only the first half is true (``NaN != NaN``) so the
  raise is skipped and ``NaN`` propagates downstream.

* TF @ ``adaptive_reflow/theory/f_side_validator.py:94`` --
  the ``>=`` inside ``d <= 0.0 or rho >= d / 4.0`` survives
  because no existing fixture exercises a VALID ``rho < d/4``
  tuple on the public ``validate_f_side`` entrypoint that
  the audit runs. With the TF mutation ``>= -> <=``, every
  rho that satisfies the Lemma 5 disjoint-cell constraint
  (``rho < d/4``) would now incorrectly trip the
  ``rho_must_be_lt_d_over_4`` code.

* TF @ ``adaptive_reflow/theory/f_side_validator.py:97`` --
  the ``>`` inside ``rho > 0.25`` survives because every
  existing fixture uses ``rho <= 0.25``. With the TF
  mutation ``> -> <``, every valid ``rho < 0.25`` would
  incorrectly trip the ``rho_must_be_le_1_over_4`` code.

These four must-pass fixtures turn the audit's four SM/TF
survivors into kills, lifting the theory subsystem from
0.500 to 0.625 (or 0.750 if the round-robin sampler picks
up additional mutants from the same files).

Paper anchors:

* ``Theorem1Statement.__post_init__`` invariants -- the
  dataclass is the unified Theorem 1 witness
  (``docs/theory/theorem1_rate_bound.md``, Theorem 1 line 87-92).
* ``validate_f_side`` -- the F-side hypothesis validator
  (``docs/mutation_audit_q4_2026.md`` §5 item 1;
  ``adaptive_reflow/theory/f_side_validator.py`` paper
  anchors to line 22-26 and Lemma 5 line 135-138).
"""
from __future__ import annotations

import math

import pytest

from adaptive_reflow.theory.checkers import Theorem1Statement
from adaptive_reflow.theory.f_side_validator import validate_f_side


# ---------------------------------------------------------------------------
# SM survivors (BoolOp -> and/or swap) in Theorem1Statement.__post_init__
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_theorem1_statement_rejects_bool_for_bl_distance():
    """SM @ checkers.py:143 -- ``or``->``and`` lets ``bool`` slip past __post_init__.

    With the SM mutation, ``not isinstance(v, (int, float)) and isinstance(v, bool)``
    evaluates to ``False`` for ``v=True`` because
    ``isinstance(True, (int, float)) is True`` (Python's ``bool`` is a
    subclass of ``int``); the raise is skipped, ``float(True) = 1.0``
    coerces silently, and the dataclass accepts a Python ``bool`` that
    downstream code will treat as a numeric.
    """
    with pytest.raises(ValueError, match=r"_must_be_real_number"):
        Theorem1Statement(bl_distance=True, root_cell_mass=0.5, posterior_evidence=2.0)


@pytest.mark.slow
def test_theorem1_statement_rejects_bool_for_root_cell_mass():
    """SM @ checkers.py:143 -- same BoolOp swap, exercised via root_cell_mass.

    Confirms the validator fires for *every* of the three numeric
    fields, not just ``bl_distance``. Mirrors the bl_distance fixture
    to catch a mutation that happens to live on a different field.
    """
    with pytest.raises(ValueError, match=r"_must_be_real_number"):
        Theorem1Statement(bl_distance=0.1, root_cell_mass=False, posterior_evidence=2.0)


@pytest.mark.slow
def test_theorem1_statement_rejects_nan_for_bl_distance():
    """SM @ checkers.py:146 -- ``or``->``and`` lets ``NaN`` slip past __post_init__.

    With the SM mutation, ``fv != fv and fv in (inf, -inf)`` evaluates
    to ``False`` for ``NaN`` because ``NaN not in (inf, -inf)``;
    the raise is skipped and ``NaN`` propagates through Theorem 1
    downstream (BL-distance comparisons would all silently fail).
    """
    with pytest.raises(ValueError, match=r"_must_be_finite"):
        Theorem1Statement(
            bl_distance=float("nan"),
            root_cell_mass=0.5,
            posterior_evidence=2.0,
        )


@pytest.mark.slow
def test_theorem1_statement_rejects_positive_infinity():
    """SM @ checkers.py:146 -- ``or``->``and`` lets ``+inf`` slip past __post_init__.

    ``+inf in (float("inf"), float("-inf"))`` is True and
    ``inf != inf`` is False, so the AND-mutation skips the raise
    for ``+inf`` -- but the original code's OR catches it because
    at least one half is True. Locks the ``or`` semantics by
    asserting that ``+inf`` is also rejected.
    """
    with pytest.raises(ValueError, match=r"_must_be_finite"):
        Theorem1Statement(
            bl_distance=float("inf"),
            root_cell_mass=0.5,
            posterior_evidence=2.0,
        )


# ---------------------------------------------------------------------------
# TF survivors (Compare -> <=/>= flip) in validate_f_side
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_validate_f_side_accepts_strictly_lt_d_over_4():
    """TF @ f_side_validator.py:94 -- ``>=``->``<=`` rejects VALID rho<d/4.

    With the TF mutation ``rho >= d/4`` -> ``rho <= d/4``, a valid
    input like ``d=1.0, rho=0.1`` (rho << d/4=0.25) would now
    trigger ``rho_must_be_lt_d_over_4``. The canonical ``validate_f_side``
    smoke test uses this exact tuple, so this is the must-pass
    fixture that kills the TF survivor.
    """
    ok, errors = validate_f_side(d=1.0, c=1.0, rho=0.1, eta=0.1)
    assert ok is True
    assert errors == ()


@pytest.mark.slow
def test_validate_f_side_rejects_only_actual_violation_of_rho_lt_d_over_4():
    """TF @ f_side_validator.py:94 -- bound is STRICT, not non-strict.

    The Lemma 5 disjoint-cell constraint is ``rho < d/4`` (strict).
    With the TF mutation flipping the operator, ``rho == d/4`` would
    become acceptable. This fixture asserts that ``rho == d/4`` (the
    boundary) STILL triggers the violation, locking the STRICT
    inequality semantics. With a >= flipped to <=, this case would
    incorrectly pass.
    """
    ok, errors = validate_f_side(d=0.4, c=1.0, rho=0.1, eta=0.1)
    assert ok is False
    assert "rho_must_be_lt_d_over_4" in errors


@pytest.mark.slow
def test_validate_f_side_accepts_rho_below_one_quarter():
    """TF @ f_side_validator.py:97 -- ``>``->``<`` rejects VALID rho<0.25.

    With the TF mutation ``rho > 0.25`` -> ``rho < 0.25``, every
    valid ``rho`` strictly below 0.25 would trigger
    ``rho_must_be_le_1_over_4``. The canonical smoke test
    ``(d=1.0, rho=0.1)`` exercises this exact case, so this
    must-pass fixture kills the TF survivor.
    """
    ok, errors = validate_f_side(d=1.0, c=1.0, rho=0.1, eta=0.1)
    assert ok is True
    assert "rho_must_be_le_1_over_4" not in errors


@pytest.mark.slow
def test_validate_f_side_boundary_rho_exactly_one_quarter_admissible():
    """TF @ f_side_validator.py:97 -- ``>`` flips to ``<``; boundary must still hold.

    The cell-radius upper bound is ``rho <= 1/4`` (non-strict). A
    ``rho`` of exactly ``0.25`` is admissible. With the TF mutation
    flipping ``>`` to ``<``, ``rho == 0.25`` would no longer be
    flagged -- but this is actually the EXPECTED behavior. So this
    fixture asserts the boundary semantics is preserved: ``rho=0.25``
    is admissible but ``rho=0.25+epsilon`` is rejected. Combined with
    the previous fixture, this locks the strict-vs-non-strict split.
    """
    # rho = 0.25 must be admissible (cell radius upper bound is <= 1/4).
    ok_25, errors_25 = validate_f_side(d=10.0, c=1.0, rho=0.25, eta=0.1)
    assert ok_25 is True
    assert errors_25 == ()
    # rho = 0.25 + epsilon must be rejected with the le_1_over_4 code.
    ok_above, errors_above = validate_f_side(d=10.0, c=1.0, rho=0.26, eta=0.1)
    assert ok_above is False
    assert "rho_must_be_le_1_over_4" in errors_above
