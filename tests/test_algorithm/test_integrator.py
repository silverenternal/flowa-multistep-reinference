"""Tests for the Wave 59 IntegratorProtocol split (Paper A MFPQA).

Wave 59 §8 — interface-first constraint: the
:class:`adaptive_reflow.algorithm.integrator.IntegratorProtocol` must
land before any new algorithm (MFPQA / BRAI) is wired into an
adapter. The tests below exercise:

* :class:`EulerStep` byte-stable legacy semantics
  (``x_next = x + base_dt * v_pred`` with ``base_dt = 0.05``).
* :class:`MultiFidelityPaperQuantityStep` per-position ``dt``
  adaptation (``dt = base_dt * (1 + alpha * sheet_A + beta * (1 -
  cell_C))``).
* Graceful fallback to fixed ``base_dt`` when ``paper_quantities`` is
  ``None`` (or missing ``sheet_A`` / ``cell_C`` accessors).
* Config round-trip (P1-1) and ``isinstance`` conformance with
  :class:`IntegratorProtocol`.

The tests do NOT touch any adapter — they live at the algorithm layer
so the contract is independent of the model-specific wiring.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.algorithm.integrator import (
    DEFAULT_BASE_DT,
    DEFAULT_MFPQA_ALPHA,
    DEFAULT_MFPQA_BETA,
    MFPQA_DT_FLOORED_TO_BASE,
    MFPQA_FALLBACK_FIELDS_MISSING,
    MFPQA_NO_PAPER_QUANTITIES,
    MFPQA_NONFINITE_QUANTITY_COERCED,
    EulerStep,
    IntegratorConfigError,
    IntegratorProtocol,
    MultiFidelityPaperQuantityStep,
    PaperQuantitiesSnapshotProtocol,
    build_integrator_from_config,
    default_euler_step,
    default_mfpqa_step,
)

# ---------------------------------------------------------------------------
# Test 1 — EulerStep preserved (byte-identical legacy behaviour)
# ---------------------------------------------------------------------------


def test_euler_step_preserved_default_base_dt() -> None:
    """EulerStep must reproduce ``x + 0.05 * v_pred`` byte-for-byte.

    This is the **legacy semantics** the framework has shipped since
    Wave 0; per-adapter composite data, regression vectors, and
    pinned metrics across every adapter depend on this arithmetic
    being preserved bit-for-bit. Wave 47 / 52 / 58 results MUST
    remain reproducible at default ``base_dt = 0.05``.
    """
    euler = EulerStep()
    assert euler.base_dt == pytest.approx(DEFAULT_BASE_DT)
    assert euler.base_dt == pytest.approx(0.05)

    x = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    v = np.array([0.1, -0.2, 0.3], dtype=np.float64)
    x_next = euler.step(x, v, t=0.0, paper_quantities=None, m=None)
    expected = x + 0.05 * v
    np.testing.assert_array_equal(x_next, expected)
    # The integrator MUST NOT mutate ``x``.
    np.testing.assert_array_equal(x, np.array([1.0, 2.0, 3.0], dtype=np.float64))


def test_euler_step_preserved_custom_base_dt() -> None:
    """EulerStep with a custom ``base_dt`` reproduces ``x + base_dt * v``."""
    euler = EulerStep(base_dt=0.02)
    x = np.array([0.0, 0.0, 0.0], dtype=np.float64)
    v = np.array([1.0, 1.0, 1.0], dtype=np.float64)
    x_next = euler.step(x, v, t=0.0, paper_quantities=None, m=None)
    np.testing.assert_allclose(x_next, np.array([0.02, 0.02, 0.02]))


def test_euler_step_isinstance_conformance() -> None:
    """EulerStep MUST pass ``isinstance(step, IntegratorProtocol)``."""
    euler = default_euler_step()
    assert isinstance(euler, IntegratorProtocol)


def test_euler_step_ignores_paper_quantities() -> None:
    """EulerStep ignores ``paper_quantities`` (legacy semantics)."""
    euler = EulerStep()
    x = np.array([1.0], dtype=np.float64)
    v = np.array([1.0], dtype=np.float64)

    class _Snapshot(PaperQuantitiesSnapshotProtocol):
        def sheet_A(self, t: float) -> float:  # pragma: no cover
            return 999.0

        def cell_C(self, t: float) -> float:  # pragma: no cover
            return -999.0

    x_with_none = euler.step(x, v, t=0.0, paper_quantities=None, m=None)
    x_with_snapshot = euler.step(x, v, t=0.0, paper_quantities=_Snapshot(), m=None)
    np.testing.assert_array_equal(x_with_none, x_with_snapshot)


def test_euler_step_validates_base_dt() -> None:
    """EulerStep rejects non-positive ``base_dt`` (closes P0-3 boundary)."""
    with pytest.raises(IntegratorConfigError):
        EulerStep(base_dt=0.0)
    with pytest.raises(IntegratorConfigError):
        EulerStep(base_dt=-0.01)
    with pytest.raises(IntegratorConfigError):
        EulerStep(base_dt=float("nan"))


def test_euler_step_config_round_trip() -> None:
    """EulerStep ``from_config(to_config())`` round-trips bit-for-bit."""
    original = EulerStep(base_dt=0.07)
    config = original.to_config()
    assert config["family"] == "euler"
    assert config["base_dt"] == pytest.approx(0.07)
    rebuilt = EulerStep.from_config(config)
    assert rebuilt.base_dt == original.base_dt
    assert rebuilt.config_hash() == original.config_hash()
    assert rebuilt.to_config() == config


def test_euler_step_config_hash_distinguishes_base_dt() -> None:
    """Two EulerStep instances with different ``base_dt`` MUST hash differently."""
    a = EulerStep(base_dt=0.05)
    b = EulerStep(base_dt=0.06)
    assert a.config_hash() != b.config_hash()


# ---------------------------------------------------------------------------
# Test 2 — MultiFidelityPaperQuantityStep per-position adaptive dt
# ---------------------------------------------------------------------------


def _membership_snapshot_dict(
    sheet_a: float, cell_C: float
) -> dict[float, float]:
    """Build a time-independent paper-quantity snapshot (Mapping shape)."""
    return {"sheet_A": sheet_a, "cell_C": cell_C}


def test_mfpqa_step_default_coefficients_match_design_doc() -> None:
    """MFPQA defaults match ``todo/two-paper-algo-design.md`` §3.2.

    Canonical formula::

        dt(r) = base_dt * (1 + alpha * sheet_A + beta * (1 - cell_C))

    with ``alpha = 0.3``, ``beta = 0.2``, ``base_dt = 0.05``.
    """
    mfpqa = default_mfpqa_step()
    assert mfpqa.base_dt == pytest.approx(DEFAULT_BASE_DT)
    assert mfpqa.alpha == pytest.approx(DEFAULT_MFPQA_ALPHA)
    assert mfpqa.alpha == pytest.approx(0.3)
    assert mfpqa.beta == pytest.approx(DEFAULT_MFPQA_BETA)
    assert mfpqa.beta == pytest.approx(0.2)


def test_mfpqa_step_per_position_dt() -> None:
    """MFPQA ``dt`` adapts to ``sheet_A`` + ``cell_C`` at each step.

    Two snapshots with different ``sheet_A`` / ``cell_C`` produce
    visibly different ``x_next`` magnitudes for the same ``v_pred``
    — high ``sheet_A`` and low ``cell_C`` yield a *larger* ``dt``
    (larger ``x_next``), high ``cell_C`` and low ``sheet_A`` yield a
    *smaller* ``dt``.
    """
    mfpqa = MultiFidelityPaperQuantityStep(
        base_dt=0.05, alpha=0.3, beta=0.2
    )

    x = np.zeros(2, dtype=np.float64)
    v = np.ones(2, dtype=np.float64)

    # Easy region: high sheet_A, low cell_C -> dt > base_dt
    pq_easy = _membership_snapshot_dict(sheet_a=1.0, cell_C=0.0)
    x_next_easy = mfpqa.step(x, v, t=0.0, paper_quantities=pq_easy, m=None)
    expected_easy_dt = 0.05 * (1.0 + 0.3 * 1.0 + 0.2 * (1.0 - 0.0))
    # expected_easy_dt = 0.05 * (1 + 0.3 + 0.2) = 0.05 * 1.5 = 0.075
    assert expected_easy_dt == pytest.approx(0.075)
    np.testing.assert_allclose(x_next_easy, expected_easy_dt * v)

    # Hard region: low sheet_A, high cell_C -> dt < base_dt
    pq_hard = _membership_snapshot_dict(sheet_a=0.0, cell_C=1.0)
    x_next_hard = mfpqa.step(x, v, t=0.0, paper_quantities=pq_hard, m=None)
    expected_hard_dt = 0.05 * (1.0 + 0.3 * 0.0 + 0.2 * (1.0 - 1.0))
    # expected_hard_dt = 0.05 * (1 + 0 + 0) = 0.05
    assert expected_hard_dt == pytest.approx(0.05)
    np.testing.assert_allclose(x_next_hard, expected_hard_dt * v)

    # The two paths MUST produce visibly different x_next magnitudes
    # (the MFPQA value-add).
    assert not np.allclose(x_next_easy, x_next_hard)
    assert abs(x_next_easy[0] - x_next_hard[0]) > 1e-6


def test_mfpqa_step_uses_callable_snapshot() -> None:
    """MFPQA reads ``sheet_A(t)`` / ``cell_C(t)`` when the snapshot is a Protocol."""

    class _CallableSnapshot(PaperQuantitiesSnapshotProtocol):
        def __init__(self, sheet_a: float, cell_C: float) -> None:
            self._sheet_a = sheet_a
            self._cell_C = cell_C

        def sheet_A(self, t: float) -> float:
            return self._sheet_a

        def cell_C(self, t: float) -> float:
            return self._cell_C

    mfpqa = MultiFidelityPaperQuantityStep(
        base_dt=0.05, alpha=0.3, beta=0.2
    )
    x = np.zeros(1, dtype=np.float64)
    v = np.ones(1, dtype=np.float64)

    snap = _CallableSnapshot(sheet_a=2.0, cell_C=0.5)
    x_next = mfpqa.step(x, v, t=0.0, paper_quantities=snap, m=None)
    # dt = 0.05 * (1 + 0.3 * 2.0 + 0.2 * (1 - 0.5))
    #    = 0.05 * (1 + 0.6 + 0.1) = 0.05 * 1.7 = 0.085
    expected_dt = 0.085
    assert expected_dt == pytest.approx(0.085)
    np.testing.assert_allclose(x_next, expected_dt * v)


def test_mfpqa_step_isinstance_conformance() -> None:
    """MultiFidelityPaperQuantityStep passes ``isinstance(step, IntegratorProtocol)``."""
    mfpqa = default_mfpqa_step()
    assert isinstance(mfpqa, IntegratorProtocol)


# ---------------------------------------------------------------------------
# Test 3 — Graceful fallback when paper_quantities is missing / partial
# ---------------------------------------------------------------------------


def test_mfpqa_fallback_no_paper_quantities() -> None:
    """MFPQA falls back to fixed ``base_dt`` when ``paper_quantities is None``."""
    mfpqa = MultiFidelityPaperQuantityStep(
        base_dt=0.05, alpha=0.3, beta=0.2
    )
    x = np.array([0.0, 0.0], dtype=np.float64)
    v = np.array([1.0, 1.0], dtype=np.float64)
    audit: list[str] = []
    x_next = mfpqa.step(
        x, v, t=0.0, paper_quantities=None, m=None, audit_codes=audit
    )
    # Fallback path MUST reproduce ``x + base_dt * v``.
    np.testing.assert_allclose(x_next, np.array([0.05, 0.05]))
    assert MFPQA_NO_PAPER_QUANTITIES in audit


def test_mfpqa_fallback_missing_fields() -> None:
    """MFPQA falls back when snapshot lacks ``sheet_A`` / ``cell_C`` accessors."""
    mfpqa = MultiFidelityPaperQuantityStep(
        base_dt=0.05, alpha=0.3, beta=0.2
    )
    x = np.zeros(1, dtype=np.float64)
    v = np.ones(1, dtype=np.float64)

    # Empty snapshot — neither ``sheet_A`` nor ``cell_C`` is exposed.
    audit: list[str] = []
    x_next = mfpqa.step(
        x, v, t=0.0, paper_quantities={}, m=None, audit_codes=audit
    )
    np.testing.assert_allclose(x_next, np.array([0.05]))
    assert MFPQA_FALLBACK_FIELDS_MISSING in audit


def test_mfpqa_fallback_silent_when_audit_codes_none() -> None:
    """MFPQA silently uses fixed ``base_dt`` when caller passes ``audit_codes=None``."""
    mfpqa = MultiFidelityPaperQuantityStep(
        base_dt=0.05, alpha=0.3, beta=0.2
    )
    x = np.zeros(1, dtype=np.float64)
    v = np.ones(1, dtype=np.float64)

    x_next = mfpqa.step(x, v, t=0.0, paper_quantities=None, m=None)
    np.testing.assert_allclose(x_next, np.array([0.05]))


def test_mfpqa_coerces_nonfinite_quantity() -> None:
    """Non-finite ``sheet_A`` / ``cell_C`` are coerced to ``0.0`` and audited."""
    mfpqa = MultiFidelityPaperQuantityStep(
        base_dt=0.05, alpha=0.3, beta=0.2
    )
    x = np.zeros(1, dtype=np.float64)
    v = np.ones(1, dtype=np.float64)

    pq = {"sheet_A": float("nan"), "cell_C": 0.0}
    audit: list[str] = []
    x_next = mfpqa.step(
        x, v, t=0.0, paper_quantities=pq, m=None, audit_codes=audit
    )
    # sheet_A coerced to 0.0 -> dt = base_dt * (1 + 0 + beta * (1 - 0))
    #                           = 0.05 * (1 + 0 + 0.2)
    expected_dt = 0.05 * 1.2
    np.testing.assert_allclose(x_next, np.array([expected_dt]))
    assert MFPQA_NONFINITE_QUANTITY_COERCED in audit


def test_mfpqa_dt_floored_to_base_when_negative() -> None:
    """Negative ``dt`` is clipped to ``base_dt`` (closes alpha<0 door)."""
    mfpqa = MultiFidelityPaperQuantityStep(
        base_dt=0.05, alpha=10.0, beta=0.0
    )
    # alpha=10, sheet_A=1 -> (1 + 10*1 + 0*(...)) = 11, OK positive.
    # We need a NEGATIVE branch — alpha=0, beta=0 with an extreme
    # override.  We emulate by patching the ``step`` via a direct
    # post-fix path: build a snapshot whose sheet_A + (1-cell_C) is
    # negative. The default coefficient enforcement (``alpha,
    # beta >= 0``) keeps the canonical path positive; we test the
    # defensive floor via a non-``Mapping`` snapshot that returns a
    # negative coefficient via a callable.
    class _BadSnapshot(PaperQuantitiesSnapshotProtocol):
        def sheet_A(self, t: float) -> float:
            # Negative sheet_A combined with alpha=10 yields dt < 0
            # only when alpha > 1/base_dt * (1 - sheet_A). For
            # alpha=10, sheet_A=-1: dt = 0.05 * (1 + 10 * -1 + 0)
            #                     = 0.05 * (1 - 10) = -0.45 < 0.
            return -1.0

        def cell_C(self, t: float) -> float:
            return 0.0

    x = np.zeros(1, dtype=np.float64)
    v = np.ones(1, dtype=np.float64)
    audit: list[str] = []
    x_next = mfpqa.step(
        x, v, t=0.0, paper_quantities=_BadSnapshot(), m=None,
        audit_codes=audit,
    )
    # dt clipped to base_dt; audit code emitted.
    np.testing.assert_allclose(x_next, np.array([0.05]))
    assert MFPQA_DT_FLOORED_TO_BASE in audit


# ---------------------------------------------------------------------------
# Test 4 — Config round-trip + polymorphic factory
# ---------------------------------------------------------------------------


def test_mfpqa_config_round_trip() -> None:
    """MFPQA ``from_config(to_config())`` round-trips bit-for-bit."""
    original = MultiFidelityPaperQuantityStep(base_dt=0.04, alpha=0.5, beta=0.1)
    config = original.to_config()
    assert config["family"] == "mfpqa"
    assert config["base_dt"] == pytest.approx(0.04)
    assert config["alpha"] == pytest.approx(0.5)
    assert config["beta"] == pytest.approx(0.1)
    rebuilt = MultiFidelityPaperQuantityStep.from_config(config)
    assert rebuilt.base_dt == original.base_dt
    assert rebuilt.alpha == original.alpha
    assert rebuilt.beta == original.beta
    assert rebuilt.config_hash() == original.config_hash()
    assert rebuilt.to_config() == config


def test_mfpqa_config_hash_distinguishes_coefficients() -> None:
    """Two MFPQA instances with different ``alpha`` MUST hash differently."""
    a = MultiFidelityPaperQuantityStep(base_dt=0.05, alpha=0.3, beta=0.2)
    b = MultiFidelityPaperQuantityStep(base_dt=0.05, alpha=0.4, beta=0.2)
    c = MultiFidelityPaperQuantityStep(base_dt=0.05, alpha=0.3, beta=0.3)
    assert a.config_hash() != b.config_hash()
    assert a.config_hash() != c.config_hash()
    assert b.config_hash() != c.config_hash()


def test_mfpqa_validates_base_dt_and_coefficients() -> None:
    """MFPQA rejects non-positive ``base_dt`` and negative coefficients."""
    with pytest.raises(IntegratorConfigError):
        MultiFidelityPaperQuantityStep(base_dt=0.0)
    with pytest.raises(IntegratorConfigError):
        MultiFidelityPaperQuantityStep(base_dt=-0.01)
    with pytest.raises(IntegratorConfigError):
        MultiFidelityPaperQuantityStep(alpha=-0.1)
    with pytest.raises(IntegratorConfigError):
        MultiFidelityPaperQuantityStep(beta=-0.1)


def test_build_integrator_from_config_euler() -> None:
    """build_integrator_from_config dispatches ``"euler"`` to :class:`EulerStep`."""
    euler = build_integrator_from_config({"family": "euler", "base_dt": 0.05})
    assert isinstance(euler, EulerStep)
    assert isinstance(euler, IntegratorProtocol)
    assert euler.base_dt == pytest.approx(0.05)


def test_build_integrator_from_config_mfpqa() -> None:
    """build_integrator_from_config dispatches ``"mfpqa"`` to MFPQA."""
    mfpqa = build_integrator_from_config(
        {"family": "mfpqa", "base_dt": 0.05, "alpha": 0.3, "beta": 0.2}
    )
    assert isinstance(mfpqa, MultiFidelityPaperQuantityStep)
    assert isinstance(mfpqa, IntegratorProtocol)
    assert mfpqa.alpha == pytest.approx(0.3)
    assert mfpqa.beta == pytest.approx(0.2)


def test_build_integrator_from_config_rejects_unknown_family() -> None:
    """build_integrator_from_config rejects unknown family names."""
    with pytest.raises(IntegratorConfigError):
        build_integrator_from_config({"family": "rk4"})


def test_build_integrator_from_config_rejects_non_dict() -> None:
    """build_integrator_from_config rejects non-dict config."""
    with pytest.raises(IntegratorConfigError):
        build_integrator_from_config("euler")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Test 5 — Math properties (sanity checks beyond the spec)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sheet_a,cell_C", [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)])
def test_mfpqa_dt_is_finite_across_unit_square(
    sheet_a: float, cell_C: float
) -> None:
    """For any ``(sheet_A, cell_C)`` in ``[0, 1]^2`` the ``dt`` is finite and >0."""
    mfpqa = MultiFidelityPaperQuantityStep(
        base_dt=0.05, alpha=0.3, beta=0.2
    )
    x = np.zeros(1, dtype=np.float64)
    v = np.ones(1, dtype=np.float64)
    audit: list[str] = []
    pq = {"sheet_A": sheet_a, "cell_C": cell_C}
    x_next = mfpqa.step(
        x, v, t=0.0, paper_quantities=pq, m=None, audit_codes=audit
    )
    # All values in [0, 1] give 1 + alpha*sheet_A + beta*(1-cell_C) in
    # [1, 1 + alpha + beta] = [1, 1.5], so dt in [0.05, 0.075].
    assert math.isfinite(x_next[0])
    assert x_next[0] >= 0.05 - 1e-12
    assert x_next[0] <= 0.05 * (1.0 + 0.3 + 0.2) + 1e-12


def test_mfpqa_step_does_not_mutate_x() -> None:
    """MFPQA ``step`` MUST NOT mutate ``x`` (fresh allocation)."""
    mfpqa = MultiFidelityPaperQuantityStep(
        base_dt=0.05, alpha=0.3, beta=0.2
    )
    x = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    v = np.array([0.5, -0.5, 0.5], dtype=np.float64)
    x_before = x.copy()
    pq = {"sheet_A": 1.0, "cell_C": 0.0}
    mfpqa.step(x, v, t=0.5, paper_quantities=pq, m=None)
    np.testing.assert_array_equal(x, x_before)


def test_mfpqa_step_does_not_mutate_paper_quantities() -> None:
    """MFPQA ``step`` MUST NOT mutate ``paper_quantities`` (read-only)."""
    mfpqa = MultiFidelityPaperQuantityStep(
        base_dt=0.05, alpha=0.3, beta=0.2
    )
    x = np.zeros(1, dtype=np.float64)
    v = np.ones(1, dtype=np.float64)
    pq = {"sheet_A": 1.0, "cell_C": 0.0}
    pq_before = dict(pq)
    mfpqa.step(x, v, t=0.5, paper_quantities=pq, m=None)
    assert pq == pq_before
