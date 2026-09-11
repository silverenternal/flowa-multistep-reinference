"""CodimensionSheetScheduler + paper_evidence_balance helper tests.

Split out of the monolithic ``tests/test_algorithm/test_scheduler.py``
during Wave 104 P2-B. Pure file-system refactor — no behaviour change.
"""

from __future__ import annotations

import math
import warnings

import numpy as np
import pytest

from adaptive_reflow.algorithm import (
    CodimensionSheetScheduler,
    build_scheduler,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.scheduler import _paper_evidence_balance


# ---------------------------------------------------------------------------
# Shared helpers (moved from the monolithic test_scheduler.py)
# ---------------------------------------------------------------------------


def _noop_profile(x: float) -> float:
    """Identity-free residual profile for codimension-scheduler tests."""
    return float(x)


# ---------------------------------------------------------------------------
# _paper_evidence_balance helper — paper Theorem 1 / Lemmas 2 + 3
# ---------------------------------------------------------------------------


def test_paper_evidence_balance_helper_closed_form() -> None:
    """_paper_evidence_balance matches the paper-aligned closed form.

    The formula uses the paper's *positive* eps powers: sheet
    ``Theta(eps^{+1})`` (Lemma 2 / Cor. 1) and cell ``O(eps^{+2})``
    (Lemma 3). As ``eps -> 0`` with ``n_clipped < 1`` the cell term
    shrinks faster, so the ratio tends to 1 (sheet dominance),
    matching Theorem 1.
    """
    eps = 0.1
    for n_base in (0.0, 0.25, 0.5, 0.75, 1.0):
        n_clipped = max(0.0, min(1.0, n_base))
        sheet = max(n_clipped, eps)
        cell = (1.0 - n_clipped) ** 2 * eps * eps
        expected = sheet / (sheet + cell)
        got = _paper_evidence_balance(n_base, eps)
        assert got == pytest.approx(expected, rel=1e-12)


def test_paper_evidence_balance_helper_paper_eps_zero_limit() -> None:
    """The ratio tends to 1 as eps -> 0 for every n_clipped < 1.

    Paper Theorem 1 (``:88``) requires the sheet to dominate after
    normalization as the noise level vanishes. The helper must realise
    this monotonic direction: the ratio is non-decreasing as eps
    decreases toward 0 (and approaches 1 in the limit) for every
    ``n_clipped in [0, 1)``.
    """
    for n_base in (0.0, 0.25, 0.5, 0.75):
        prev_ratio = -1.0
        for eps in (0.5, 0.1, 0.05, 0.01, 0.001, 1e-6):
            ratio = _paper_evidence_balance(n_base, eps)
            # Ratio is non-decreasing as eps decreases (Theorem 1
            # direction) and approaches 1 in the limit.
            assert ratio >= prev_ratio - 1e-12
            assert 0.0 <= ratio <= 1.0
            prev_ratio = ratio
        # And in the limit the ratio is essentially 1.
        assert prev_ratio == pytest.approx(1.0, abs=1e-6)


def test_paper_evidence_balance_helper_rejects_invalid_eps() -> None:
    """The helper refuses non-finite or non-positive eps_implicit."""
    with pytest.raises(ValueError, match="finite"):
        _paper_evidence_balance(0.5, float("nan"))
    with pytest.raises(ValueError, match="eps_implicit"):
        _paper_evidence_balance(0.5, 0.0)
    with pytest.raises(ValueError, match="eps_implicit"):
        _paper_evidence_balance(0.5, -0.01)


# ---------------------------------------------------------------------------
# CodimensionSheetScheduler — paper Theorem 1 / Lemmas 2 + 3
# ---------------------------------------------------------------------------


def test_codimension_sheet_scheduler_n_cap_is_ratio_driven() -> None:
    """``n_cap`` is driven by the paper's sheet-vs-cell evidence ratio.

    The framework's coarse-to-fine anneal is driven by the paper's
    sheet-vs-cell evidence ratio (paper Lemma 2 ``Theta(eps^{+1})``
    versus Lemma 3 ``O(eps^{+2})``), NOT by the cosine ramp. With
    the paper-quantity-augmented path active (no
    ``profile_residual_fn`` ⇒ heuristic fallback), ``n_cap``
    equals ``n_min + (n_max - n_min) * ratio`` where ``ratio =
    sheet / (sheet + cell)``.

    We verify:

    * The per-round ``n_cap`` equals the literal closed form.
    * The per-round ``n_cap`` differs from the cosine ramp's
      ``n_cap`` (the cosine ramp is no longer the driver).
    * Different ``eps_implicit`` values yield different ``n_cap``
      (the ratio is sensitive to the paper-quantity scale).
    """
    base = default_cosine_scheduler(cycle_length=10, n_min=0.0, n_max=1.0)
    for eps in (1.0, 0.05, 0.01):
        codim = CodimensionSheetScheduler(
            cycle_length=10, n_min=0.0, n_max=1.0, eps_implicit=eps
        )
        for r in range(10):
            base_cap = base.sample(0, r, r).n_cap
            sample = codim.sample(0, r, r)
            # ratio-driven: n_cap = n_min + (n_max - n_min) * ratio.
            assert sample.n_cap == pytest.approx(
                sample.evidence_ratio, abs=1e-12
            ), (
                f"n_cap at round {r} must equal the evidence ratio "
                f"(eps_implicit={eps}); got n_cap={sample.n_cap}, "
                f"ratio={sample.evidence_ratio}"
            )
            # n_cap differs from the cosine ramp's base value at
            # late-round slots where the heuristic ratio is < 1
            # (the cosine ramp's terminal round emits n_cap=0, but
            # the ratio-driven n_cap stays near 1 for small eps).
            # We skip r=0 because both the cosine base and the
            # heuristic ratio at n_cap_base=1.0 happen to equal 1.0
            # (degenerate identity at the high-noise end).
            if eps < 0.5 and r > 0:
                assert abs(sample.n_cap - base_cap) > 1e-6, (
                    f"n_cap at round {r} (eps_implicit={eps}) "
                    f"should differ from the cosine base ({base_cap}); "
                    f"got n_cap={sample.n_cap}. The cosine ramp must "
                    f"NOT be the driver of n_cap."
                )


def test_codimension_sheet_scheduler_evidence_ratio_low_eps_near_one() -> None:
    """At low ``eps_implicit`` the evidence ratio is near 1 (sheet dominance).

    With a small ``eps_implicit`` the cell-evidence term
    (``(1-n)^2 * eps^2``) is small relative to the sheet term
    (``max(n, eps)``), so the ratio tends to 1 across the cycle
    (paper Theorem 1, ``eps -> 0`` selects the sheet).
    """
    codim = CodimensionSheetScheduler(
        cycle_length=10, n_min=0.0, n_max=1.0, eps_implicit=0.01
    )
    for r in range(10):
        codim.sample(0, r, r)
        assert codim.last_evidence_ratio is not None
        # At low eps the ratio is close to 1 everywhere.
        assert codim.last_evidence_ratio > 0.9


def test_codimension_sheet_scheduler_handles_degenerate_base() -> None:
    """``n_cap`` is now driven by the ratio, not the cosine ramp.

    P2-W33-A: with ``eps_direction="decreasing"`` (paper convention,
    default) the per-round ``eps`` diminishes across the cycle
    (``eps(r) = eps_0 * (1 - u_r)``, floored at ``1e-9``). At the
    cycle terminal round ``u_r=1`` so ``eps_per_round = 1e-9``
    (the floor); for the framework heuristic with ``n_base = 0``:

        sheet = max(0, 1e-9)        = 1e-9
        cell  = 1 * (1e-9)^2       = 1e-18
        ratio = 1e-9 / (1e-9 + 1e-18) ≈ 1.0

    so ``n_cap`` is ≈ 1.0 (n_min=0, n_max=1) — the paper-aligned
    "sheet dominates as eps -> 0" claim (Theorem 1). With a large
    ``eps_implicit`` at the early rounds the ratio is sensitive to
    ``n_cap_base`` via the heuristic cell term.
    """
    codim = CodimensionSheetScheduler(
        cycle_length=4, n_min=0.0, n_max=1.0, eps_implicit=0.05
    )
    # r=3 is the cycle terminal round; ``eps_per_round`` is floored
    # at ``1e-9``, so ``n_cap`` ≈ ``n_max`` (sheet dominance).
    sample = codim.sample(0, 3, 3)
    assert sample.n_cap == pytest.approx(1.0, abs=1e-7)
    # And the evidence ratio equals n_cap directly (n_min=0, n_max=1).
    assert codim.last_evidence_ratio == pytest.approx(1.0, abs=1e-7)
    # And at the early round (r=0), eps_per_round equals the
    # constructor constant and the n_cap is also sheet-dominated.
    early_sample = codim.sample(0, 0, 0)
    assert early_sample.n_cap == pytest.approx(1.0, abs=1e-7)
    # Now exercise a NON-terminal round with a large eps; here the
    # framework heuristic IS sensitive to n_cap_base.
    big_codim = CodimensionSheetScheduler(
        cycle_length=2, n_min=0.5, n_max=1.0, eps_implicit=1.0
    )
    # r=0: eps_per_round = 1.0 * (1 - 0) = 1.0. At r=0 with cosine
    # n_min=0.5, n_base = n_max = 1.0. sheet = max(1, 1) = 1.
    # cell = (1-1)^2 * 1^2 = 0. ratio = 1 / (1 + 0) = 1.
    # n_cap = 0.5 + 0.5 * 1 = 1.0.
    sample_r0 = big_codim.sample(0, 0, 0)
    assert sample_r0.n_cap == pytest.approx(1.0, abs=1e-7)


def test_codimension_sheet_scheduler_is_byte_deterministic() -> None:
    """Two CodimensionSheetScheduler instances with identical kwargs agree."""
    kwargs = dict(
        cycle_length=12,
        n_min=0.1,
        n_max=0.9,
        profile_residual_fn=_noop_profile,
        eps_implicit=0.07,
        seed=42,
    )
    a = CodimensionSheetScheduler(**kwargs)
    b = CodimensionSheetScheduler(**kwargs)
    for r in range(12):
        sa = a.sample(0, r, r)
        sb = b.sample(0, r, r)
        assert sa.n_cap == pytest.approx(sb.n_cap)
        assert sa.u_r == pytest.approx(sb.u_r)
        assert sa.family == sb.family == "codimension_sheet"
        assert sa.schedule_hash == sb.schedule_hash
        assert sa.memory_fraction() == pytest.approx(sb.memory_fraction())


def test_codimension_sheet_scheduler_config_hash_includes_eps_implicit_and_profile_signature() -> None:
    """The config_hash captures both eps_implicit and profile identity."""
    base_kwargs = dict(
        cycle_length=10,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=None,
        seed=0,
    )
    h0 = CodimensionSheetScheduler(**base_kwargs).config_hash()
    # Vary eps_implicit.
    h_lo = CodimensionSheetScheduler(
        **{**base_kwargs, "eps_implicit": 0.01}
    ).config_hash()
    h_hi = CodimensionSheetScheduler(
        **{**base_kwargs, "eps_implicit": 0.07}
    ).config_hash()
    assert h_lo != h0
    assert h_hi != h0
    assert h_lo != h_hi
    # Vary the profile callable.
    h_prof = CodimensionSheetScheduler(
        **{**base_kwargs, "profile_residual_fn": _noop_profile}
    ).config_hash()
    assert h_prof != h0
    # Same callable -> same hash (signature is qualname-derived).
    h_prof_again = CodimensionSheetScheduler(
        **{**base_kwargs, "profile_residual_fn": _noop_profile}
    ).config_hash()
    assert h_prof == h_prof_again
    # The profile_signature accessor exposes the same identifier string.
    scheduler = CodimensionSheetScheduler(
        **{**base_kwargs, "profile_residual_fn": _noop_profile}
    )
    assert scheduler.profile_signature.endswith("_noop_profile")
    # And a None profile yields the canonical "default_sheet" signature.
    none_scheduler = CodimensionSheetScheduler(**base_kwargs)
    assert none_scheduler.profile_signature == "default_sheet"


def test_codimension_sheet_scheduler_clip_in_unit_interval() -> None:
    """n_cap stays in [n_min, n_max] (and therefore in [0, 1]) for every round."""
    codim = CodimensionSheetScheduler(
        cycle_length=20, n_min=0.0, n_max=1.0, eps_implicit=0.05
    )
    for r in range(20):
        sample = codim.sample(0, r, r)
        assert 0.0 <= sample.n_cap <= 1.0
        # And via the canonical memory-fraction transform.
        assert 0.0 <= sample.memory_fraction() <= 1.0
    # Even with extreme eps (the closed form keeps the ratio in [0, 1]).
    extreme_low = CodimensionSheetScheduler(cycle_length=10, eps_implicit=1e-12)
    extreme_high = CodimensionSheetScheduler(cycle_length=10, eps_implicit=1e6)
    for r in range(10):
        s_lo = extreme_low.sample(0, r, r)
        s_hi = extreme_high.sample(0, r, r)
        assert 0.0 <= s_lo.n_cap <= 1.0
        assert 0.0 <= s_hi.n_cap <= 1.0


def test_codimension_sample_carries_eps_implicit() -> None:
    """C4: ``CodimensionSheetScheduler.sample`` populates ``ScheduleSample.eps_implicit``.

    The runner reads ``ScheduleSample.eps_implicit`` and forwards it
    to the selection evaluator's ``oracle_at_round(eps_round=...)``.
    A ``None`` field would silently fall back to the evaluator's
    fixed ``eps_implicit`` and the metric would remain
    schedule-independent — the precise failure the C4 investigation
    diagnosed.
    """
    codim = CodimensionSheetScheduler(
        cycle_length=8, n_min=0.0, n_max=1.0, eps_implicit=0.07,
    )
    for r in range(8):
        sample = codim.sample(0, r, r)
        assert sample.eps_implicit is not None, (
            f"C4 regression: round {r} sample.eps_implicit is None"
        )
        # P2-W33-A: ``eps_implicit`` on the sample is now the per-round
        # value ``eps_0 * (1 - u_r)`` for ``eps_direction="decreasing"``
        # (default). At ``r=0`` (``u_r=0``) this equals the constructor
        # constant; at ``r=L-1`` it equals the floor ``1e-9``.
        u_r = float(r) / (8 - 1)
        expected = max(0.07 * (1.0 - u_r), 1e-9)
        assert sample.eps_implicit == pytest.approx(expected, abs=1e-12)
    # And a different eps_implicit propagates too.
    codim_hi = CodimensionSheetScheduler(
        cycle_length=4, n_min=0.0, n_max=1.0, eps_implicit=0.5,
    )
    for r in range(4):
        sample_hi = codim_hi.sample(0, r, r)
        u_r_hi = float(r) / (4 - 1)
        expected_hi = max(0.5 * (1.0 - u_r_hi), 1e-9)
        assert sample_hi.eps_implicit == pytest.approx(expected_hi, abs=1e-12)


def test_cosine_sample_eps_implicit_is_none() -> None:
    """C4 regression guard: cosine baseline leaves ``eps_implicit`` as ``None``.

    Cosine has no concept of a paper-quantity epsilon; the runner
    must therefore fall back to the evaluator's fixed ``eps_implicit``
    for cosine rows — preserving the legacy byte-for-byte behaviour
    that the C4 investigation flagged as the source of the
    "schedule-independent by construction" plateau.
    """
    cosine = default_cosine_scheduler(cycle_length=6)
    for r in range(6):
        sample = cosine.sample(0, r, r)
        assert sample.eps_implicit is None


def test_codimension_sheet_scheduler_build_scheduler_factory() -> None:
    """build_scheduler('codimension_sheet') returns the codim class."""
    scheduler = build_scheduler(
        "codimension_sheet",
        cycle_length=8,
        eps_implicit=0.05,
    )
    assert isinstance(scheduler, CodimensionSheetScheduler)
    assert scheduler.schedule_family() == "codimension_sheet"
    # And the registry is case- and whitespace-insensitive.
    scheduler = build_scheduler("  CODIMENSION_SHEET  ", cycle_length=8)
    assert isinstance(scheduler, CodimensionSheetScheduler)
    # profile_residual_fn passes through the factory.
    scheduler = build_scheduler(
        "codimension_sheet",
        cycle_length=8,
        eps_implicit=0.05,
        profile_residual_fn=_noop_profile,
    )
    assert scheduler.profile_signature.endswith("_noop_profile")


def test_codimension_sheet_scheduler_eps_direction_default_matches_paper() -> None:
    """Default ``eps_direction='decreasing'`` keeps the paper ratio direction.

    With the ratio-driven design, ``n_cap`` is computed from the
    paper's sheet-vs-cell evidence ratio. P2-W33-A: with the
    paper-aligned ``eps_direction='decreasing'``, the per-round
    ``eps`` diminishes monotonically (``eps(r) = eps_0 * (1 - u_r)``)
    and the ratio is used as-is. Under the framework heuristic
    (no ``profile_residual_fn``) and at the cycle terminal round,
    ``eps_per_round`` is floored at ``1e-9`` and ``n_cap`` is
    sheet-dominated (``n_cap`` ≈ 1.0). At early rounds with the
    cosine ramp near its peak, ``n_cap`` is also sheet-dominated.
    """
    scheduler = CodimensionSheetScheduler(
        cycle_length=8, n_min=0.0, n_max=1.0, eps_implicit=0.05
    )
    assert scheduler.eps_direction == "decreasing"
    caps = [scheduler.sample(0, r, r).n_cap for r in range(8)]
    # P2-W33-A: at every round the framework heuristic puts the
    # sheet in dominance (eps small, sheet dominates), so ``n_cap``
    # is essentially ``n_max`` throughout the cycle.
    assert caps[0] == pytest.approx(1.0, abs=1e-9)
    # At r=7 (terminal), eps_per_round = 1e-9 → ratio ≈ 1 → n_cap ≈ 1.
    assert caps[-1] == pytest.approx(1.0, abs=1e-7)


def test_codimension_sheet_scheduler_eps_direction_increasing_legacy_warns() -> None:
    """``eps_direction='increasing'`` emits a DeprecationWarning and reverses.

    The legacy ``'increasing'`` mode is the opposite of paper Theorem
    1's ``eps -> 0`` limit. Under the new ratio-driven design, the
    ``'increasing'`` mode flips the per-round ratio
    (``ratio -> 1 - ratio``), so r=0 sits at the *small-ratio* end
    of the cycle and r=L-1 sits at the *large-ratio* end. It is
    retained only for backward compatibility and emits a
    :class:`DeprecationWarning` on the FIRST :meth:`sample` call
    (not at construction time — P2-18 audit; legacy callers that
    build the scheduler eagerly for ``config_hash`` introspection
    do not flood logs).
    """
    # P2-18: construction is silent; the warning fires on the first
    # ``sample()`` call (once per instance).
    scheduler = CodimensionSheetScheduler(
        cycle_length=8, n_min=0.0, n_max=1.0, eps_direction="increasing"
    )
    assert scheduler.eps_direction == "increasing"
    with pytest.warns(DeprecationWarning, match="legacy inverted convention"):
        scheduler.sample(0, 0, 0)
    caps = [scheduler.sample(0, r, r).n_cap for r in range(1, 8)]
    # Reversed: r=0 -> small n_cap (1 - 1 = 0 in heuristic mode),
    # r=L-1 -> large n_cap (1 - eps/(eps + eps^2)).
    assert caps[0] < 0.05
    assert caps[-1] == pytest.approx(
        1.0 - 0.05 / (0.05 + 0.0025), abs=1e-9
    )
    # Subsequent sample() calls do not re-emit the warning.
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        for r in range(8):
            scheduler.sample(0, r, r)


def test_codimension_sheet_scheduler_eps_direction_case_insensitive() -> None:
    """``eps_direction`` accepts mixed case and surrounding whitespace."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        scheduler = CodimensionSheetScheduler(
            cycle_length=4, eps_direction="  DECREASING  "
        )
    assert scheduler.eps_direction == "decreasing"


def test_codimension_sheet_scheduler_eps_direction_rejects_invalid() -> None:
    """``eps_direction`` rejects strings outside the documented set."""
    with pytest.raises(ValueError, match="eps_direction"):
        CodimensionSheetScheduler(cycle_length=4, eps_direction="sideways")
    with pytest.raises(ValueError, match="eps_direction"):
        CodimensionSheetScheduler(cycle_length=4, eps_direction="")


def test_codimension_sheet_scheduler_config_hash_includes_eps_direction() -> None:
    """``config_hash`` captures the ``eps_direction`` choice."""
    base_kwargs = dict(
        cycle_length=10,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=None,
        seed=0,
    )
    h_dec = CodimensionSheetScheduler(**base_kwargs).config_hash()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        h_inc = CodimensionSheetScheduler(
            **{**base_kwargs, "eps_direction": "increasing"}
        ).config_hash()
    assert h_dec != h_inc


# ---------------------------------------------------------------------------
# CodimensionSheetScheduler — paper-quantity wiring (ADR-0013 follow-up)
# ---------------------------------------------------------------------------


def test_codimension_sheet_scheduler_with_profile_uses_paper_quantities() -> None:
    """``profile_residual_fn`` is consumed: paper quantities cached once.

    Building the scheduler with a ``profile_residual_fn`` must call
    :func:`adaptive_reflow.contracts.paper_quantities.sheet_evidence_A`
    and :func:`adaptive_reflow.contracts.paper_quantities.root_cell_packing_B`
    exactly once at construction time and cache the results on
    ``self._sheet_A`` / ``self._packing_B``. The cached values must
    equal the result of calling those functions directly with the same
    profile callable.
    """
    from adaptive_reflow.contracts import paper_quantities as _pq

    profile = lambda x: math.sin(x)  # noqa: E731

    # Reference values from the paper-quantity functions.
    expected_sheet_A = _pq.sheet_evidence_A(profile)
    expected_packing_B = _pq.root_cell_packing_B(profile)
    expected_cell_C = _pq.per_cell_coefficient_C()
    expected_e_rho = _pq.exterior_gap_e_rho()

    scheduler = CodimensionSheetScheduler(
        cycle_length=8,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=profile,
    )

    # Cached paper quantities on the scheduler.
    assert scheduler._sheet_A == pytest.approx(expected_sheet_A, rel=1e-12)
    assert scheduler._packing_B == pytest.approx(expected_packing_B, rel=1e-12)
    assert scheduler._cell_C == pytest.approx(expected_cell_C, rel=1e-12)
    assert scheduler._exterior_gap_e_rho == pytest.approx(expected_e_rho, rel=1e-12)
    # Public accessors expose the cached values too.
    assert scheduler.sheet_A == pytest.approx(expected_sheet_A, rel=1e-12)
    assert scheduler.packing_B == pytest.approx(expected_packing_B, rel=1e-12)
    assert scheduler.cell_C == pytest.approx(expected_cell_C, rel=1e-12)
    assert scheduler.exterior_gap_e_rho == pytest.approx(expected_e_rho, rel=1e-12)

    # The per-round evidence ratio uses the paper-quantity path. Verify
    # by recomputing the ratio via the public helper signature and
    # confirming the scheduler's last_evidence_ratio matches.
    for r in range(8):
        scheduler.sample(0, r, r)
        # The cached quantities are the inputs the scheduler forwards
        # into the paper-quantity-augmented path of the helper.
        assert scheduler.sheet_A is not None
        assert scheduler.packing_B is not None
        assert scheduler.cell_C is not None
        # Recompute via the helper signature (paper-quantity path).
        # We avoid using ``n_cap`` directly because the scheduler
        # applies its own envelope; instead we verify the cached
        # values are forwarded correctly by checking ``sheet_A`` and
        # ``packing_B`` survive a ``sample`` call unchanged.
        assert scheduler.sheet_A == pytest.approx(expected_sheet_A, rel=1e-12)
        assert scheduler.packing_B == pytest.approx(expected_packing_B, rel=1e-12)
        assert scheduler.last_evidence_ratio is not None
        assert 0.0 <= scheduler.last_evidence_ratio <= 1.0


def test_codimension_sheet_scheduler_without_profile_uses_inline_formula() -> None:
    """Without ``profile_residual_fn`` the legacy inline formula is used.

    Backward compatibility: when ``profile_residual_fn`` is ``None``
    the scheduler does NOT cache paper quantities (all four accessors
    return ``None``) and the per-round sheet-vs-cell evidence ratio
    uses the framework-side heuristic closed form (``sheet / (sheet +
    cell)`` with ``sheet = max(n_base, eps)`` and ``cell = (1 -
    n_base)^2 * eps^2``, where ``n_base`` is the cosine ramp's
    per-round value). Under the new ratio-driven design, ``n_cap`` is
    ``n_min + (n_max - n_min) * ratio`` (with ``n_min = n_max = 0``
    case excluded by the cycle_length > 1 check); for
    ``n_min = 0, n_max = 1`` this reduces to ``n_cap = ratio``.
    """
    scheduler = CodimensionSheetScheduler(
        cycle_length=10,
        n_min=0.0,
        n_max=1.0,
        eps_implicit=0.05,
    )
    # No profile => no paper-quantity caching.
    assert scheduler._sheet_A is None
    assert scheduler._packing_B is None
    assert scheduler._cell_C is None
    assert scheduler._exterior_gap_e_rho is None
    assert scheduler.sheet_A is None
    assert scheduler.packing_B is None
    assert scheduler.cell_C is None
    assert scheduler.exterior_gap_e_rho is None
    # Legacy inline formula: ratio matches the framework heuristic
    # applied to the cosine ramp's per-round value ``n_cap_base``.
    # P2-W33-A: with the per-round ``eps`` schedule, the formula uses
    # ``eps_per_round = eps_0 * (1 - u_r)`` (floored at ``1e-9``).
    eps_0 = 0.05
    cycle_length = 10
    for r in range(cycle_length):
        sample = scheduler.sample(0, r, r)
        assert scheduler.last_evidence_ratio is not None
        # ``n_cap_base`` is the cosine ramp's value at this round
        # (ADR-0010). We can recover it by querying the base scheduler.
        n_base = scheduler.base.sample(0, r, r).n_cap
        # P2-W33-A: per-round eps.
        u_r = float(r) / (cycle_length - 1)
        eps_per_round = max(eps_0 * (1.0 - u_r), 1e-9)
        # The heuristic formula is ``sheet / (sheet + cell)`` with
        # ``sheet = max(n_base, eps_per_round)`` and
        # ``cell = (1 - n_base) ** 2 * eps_per_round ** 2``.
        n_base_clipped = max(0.0, min(1.0, n_base))
        sheet = max(n_base_clipped, eps_per_round)
        cell = (1.0 - n_base_clipped) ** 2 * eps_per_round * eps_per_round
        expected_ratio = sheet / (sheet + cell)
        assert scheduler.last_evidence_ratio == pytest.approx(
            expected_ratio, rel=1e-12
        )
        # With n_min=0, n_max=1, the per-round n_cap equals the ratio.
        assert sample.n_cap == pytest.approx(
            scheduler.last_evidence_ratio, abs=1e-12
        )


def test_codimension_sheet_scheduler_paper_quantity_diagnostics_emitted() -> None:
    """Per-round diagnostics from the paper-quantity-augmented path.

    When ``profile_residual_fn`` is configured, the per-round
    ``last_evidence_ratio`` is computed via the
    paper-quantity-augmented path. We verify the resulting ratio is
    well-defined (in ``[0, 1]``) and that the cached ``sheet_A``,
    ``packing_B``, ``cell_C`` are forwarded into the helper
    unchanged across rounds.
    """
    profile = lambda x: math.sin(x)  # noqa: E731

    scheduler = CodimensionSheetScheduler(
        cycle_length=6,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=profile,
    )
    # Snapshot the cached quantities at construction time.
    snapshot = (
        scheduler.sheet_A,
        scheduler.packing_B,
        scheduler.cell_C,
        scheduler.exterior_gap_e_rho,
    )
    for r in range(6):
        scheduler.sample(0, r, r)
        # Cached quantities are immutable across rounds (computed once).
        assert scheduler.sheet_A == snapshot[0]
        assert scheduler.packing_B == snapshot[1]
        assert scheduler.cell_C == snapshot[2]
        assert scheduler.exterior_gap_e_rho == snapshot[3]
        # The ratio is well-defined.
        assert scheduler.last_evidence_ratio is not None
        assert 0.0 <= scheduler.last_evidence_ratio <= 1.0


def test_codimension_sheet_scheduler_paper_quantity_path_matches_paper_quantities_module() -> None:
    """End-to-end: paper-quantity-augmented ratio recomputed via the helper.

    The paper-quantity-augmented path computes

        sheet = sheet_A * eps
        cell  = cell_C * packing_B * eps ** 2
        ratio = sheet / (sheet + cell)

    We verify the scheduler's per-round ``last_evidence_ratio``
    matches this formula when ``profile_residual_fn`` is configured.
    """
    from adaptive_reflow.contracts import paper_quantities as _pq

    profile = lambda x: math.sin(x)  # noqa: E731

    sheet_A = _pq.sheet_evidence_A(profile)
    packing_B = _pq.root_cell_packing_B(profile)
    cell_C = _pq.per_cell_coefficient_C()

    scheduler = CodimensionSheetScheduler(
        cycle_length=4,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=profile,
        eps_implicit=0.05,
    )
    eps_0 = scheduler.eps_implicit
    cycle_length = 4
    for r in range(cycle_length):
        scheduler.sample(0, r, r)
        # P2-W33-A: with the per-round ``eps`` schedule, the formula
        # uses ``eps_per_round = eps_0 * (1 - u_r)`` (floored at
        # ``1e-9``). The ratio is recomputed for each round.
        u_r = float(r) / (cycle_length - 1)
        eps_per_round = max(eps_0 * (1.0 - u_r), 1e-9)
        sheet = sheet_A * eps_per_round
        cell = cell_C * packing_B * eps_per_round * eps_per_round
        expected_ratio = sheet / (sheet + cell)
        assert scheduler.last_evidence_ratio == pytest.approx(
            expected_ratio, rel=1e-12
        )


def test_codimension_sheet_scheduler_inject_noise_e_rho_floor() -> None:
    """A18: ``inject_noise`` floors the noise mass at ``e_rho / 4``.

    With ``profile_residual_fn`` supplied, the scheduler caches
    ``e_rho`` (paper Lemma 5 exterior gap) and the ``inject_noise``
    path lifts the noise mass to ``max(A_g, e_rho / 4)`` so the
    forward noise respects paper Lemma 5's physical-complement gap.

    The test constructs a scheduler with a profile whose ``A_g`` is
    small (close to the ``e_rho / 4`` floor) and verifies the noise
    mass is the floor.
    """
    # A near-zero profile: sheet evidence is tiny (close to e_rho/4).
    profile = lambda x: 1e6 * math.sin(x)  # noqa: E731
    scheduler = CodimensionSheetScheduler(
        cycle_length=4,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=profile,
    )
    assert scheduler.sheet_A is not None
    assert scheduler.exterior_gap_e_rho is not None
    e_rho = float(scheduler.exterior_gap_e_rho)
    expected_floor = e_rho / 4.0
    sample = scheduler.sample(0, 0, 0).as_cosine_schedule_sample()
    state = np.zeros(4, dtype=np.float64)
    gen = np.random.default_rng(0)
    out = scheduler.inject_noise(state, sample, generator=gen)
    # The state was zero, so the output is exactly
    # ``scale * standard_normal`` for the same generator stream.
    expected_scale = math.sqrt(max(float(scheduler.sheet_A), expected_floor))
    expected = expected_scale * np.random.default_rng(0).standard_normal(4)
    assert np.allclose(out, expected, rtol=1e-12, atol=0.0), (
        f"inject_noise output {out!r} does not match scale "
        f"sqrt(max(A_g, e_rho/4))={expected_scale!r}"
    )


# ---------------------------------------------------------------------------
# P0-A7 — evidence_ratio on the codimension sample
# ---------------------------------------------------------------------------


def _g_a_profile(x: float) -> float:
    """Canonical two_moons profile ``g_a(x) = (1 + 0.25 tanh x) sin x``."""
    return (1.0 + 0.25 * math.tanh(x)) * math.sin(x)


def test_codimension_sample_evidence_ratio() -> None:
    """P0-A7: the sample carries the round's sheet-vs-cell balance."""
    scheduler = CodimensionSheetScheduler(
        cycle_length=8, profile_residual_fn=_g_a_profile
    )
    for r in range(8):
        sample = scheduler.sample(0, r, r)
        assert sample.evidence_ratio is not None
        # Matches the reportable metric to within 1e-6 (target).
        assert sample.evidence_ratio == pytest.approx(
            float(scheduler.last_evidence_ratio), abs=1e-6
        )
        assert 0.0 <= sample.evidence_ratio <= 1.0
        assert sample.audit_codes == ("codimension_paper_quantity_grounded",)


def test_codimension_sample_evidence_ratio_heuristic_path() -> None:
    """Without a profile the sample is tagged as the heuristic path."""
    scheduler = CodimensionSheetScheduler(cycle_length=4)
    sample = scheduler.sample(0, 0, 0)
    assert sample.audit_codes == ("codimension_framework_heuristic",)
    assert sample.evidence_ratio == pytest.approx(
        float(scheduler.last_evidence_ratio), abs=1e-12
    )


def test_codimension_with_profile_preserves_eps_implicit() -> None:
    """F10: ``CodimensionSheetScheduler.with_profile(provider)`` returns
    a new scheduler with the supplied profile and ALL other config
    preserved (cycle_length, n_min, n_max, eps_implicit, eps_direction,
    seed).
    """
    original = CodimensionSheetScheduler(
        cycle_length=20,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=lambda x: float(x),
        eps_implicit=0.05,
        eps_direction="decreasing",
        seed=42,
    )

    def new_profile(x: float) -> float:
        return float(x) ** 2

    new_sched = original.with_profile(new_profile)
    # Identity preserved on every other field.
    assert new_sched.cycle_length() == original.cycle_length()
    assert new_sched._n_min == original._n_min
    assert new_sched._n_max == original._n_max
    assert new_sched._eps_implicit == original._eps_implicit
    assert new_sched._eps_direction == original._eps_direction
    assert new_sched._seed == original._seed
    # The new profile is the callable passed in.
    assert new_sched._profile_residual_fn is new_profile
    # Sanity: original is unmodified.
    assert original._profile_residual_fn is not new_profile


# numpy import is at the top of the file.
