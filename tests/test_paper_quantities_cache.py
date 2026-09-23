"""Tests for :mod:`adaptive_reflow.framework.paper_quantities_cache` (Wave 296 P2).

Exercises the three canonical cache states:

* :class:`TestPaperQuantitiesCacheBasic` — with ``profile_residual_fn``
  set to a real ``g``, all four quantities are populated on first
  access and :attr:`is_active` returns ``True``.
* :class:`TestPaperQuantitiesCacheNoProfile` — with
  ``profile_residual_fn=None``, :attr:`is_active` returns ``False``
  and every property returns ``None``.
* :class:`TestPaperQuantitiesCacheConsume` — :meth:`consume` increments
  the activation log idempotently.

Plus three supporting test classes that lock down the byte-stability
contract, the Engine flag integration, and the validation error path
documented in ``docs/audit/wave296-p1-architecture.md`` §2.1.

These tests are stdlib-only (no torch, no numpy) and depend on no GPU.
"""
from __future__ import annotations

import math
from typing import Any

import pytest

from adaptive_reflow.contracts.dynamic_noise_bias import PaperQuantitiesSnapshot
from adaptive_reflow.frame.engine import Engine
from adaptive_reflow.framework.paper_quantities_cache import (
    PAPER_QUANTITIES_CACHE_DEFAULT_C,
    PAPER_QUANTITIES_CACHE_DEFAULT_D,
    PAPER_QUANTITIES_CACHE_DEFAULT_ETA,
    PAPER_QUANTITIES_CACHE_DEFAULT_RHO,
    PAPER_QUANTITIES_SITE_NAMES,
    PaperQuantitiesCache,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _real_g(x: float) -> float:
    """Return ``sin(x)`` — a real, deterministic profile residual callable.

    Used as the canonical ``profile_residual_fn`` in the active-cache
    tests. Chosen for its non-trivial zeros (multiples of ``pi``) so
    :func:`root_cell_packing_B` exercises its sign-change sampler.
    """
    return math.sin(x)


# ---------------------------------------------------------------------------
# 1. Basic — with profile_residual_fn, all 4 quantities populated, is_active=True
# ---------------------------------------------------------------------------


class TestPaperQuantitiesCacheBasic:
    """Active cache: profile_residual_fn set → all 4 quantities populated."""

    def test_is_active_true_with_profile(self) -> None:
        """With profile_residual_fn set, is_active returns True."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        assert cache.is_active is True

    def test_all_four_quantities_populated(self) -> None:
        """All four paper quantities return positive finite floats."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        # Touch each property once; they should all be positive finite
        # reals (paper invariants: A_g > 0, B_g >= 0, C_g > 0, e_rho > 0).
        sheet_A = cache.sheet_A
        packing_B = cache.packing_B
        cell_C = cache.cell_C
        e_rho = cache.e_rho

        assert isinstance(sheet_A, float)
        assert isinstance(packing_B, float)
        assert isinstance(cell_C, float)
        assert isinstance(e_rho, float)
        assert 0.0 < sheet_A <= 1.0  # Proposition 3 / line 161
        assert packing_B >= 0.0  # Lemma 5 / line 159
        assert cell_C > 0.0  # Lemma 3 / line 191
        assert e_rho > 0.0  # Lemma 5 / line 128

    def test_default_f_side_constants(self) -> None:
        """Default rho=0.1, c=1.0, d=1.0, eta=0.1 (cosine-baseline parity)."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        assert cache.rho == PAPER_QUANTITIES_CACHE_DEFAULT_RHO == 0.1
        assert cache.c == PAPER_QUANTITIES_CACHE_DEFAULT_C == 1.0
        assert cache.d == PAPER_QUANTITIES_CACHE_DEFAULT_D == 1.0
        assert cache.eta == PAPER_QUANTITIES_CACHE_DEFAULT_ETA == 0.1

    def test_custom_f_side_constants(self) -> None:
        """Custom rho/c/d/eta are honoured and reflected in cell_C and e_rho."""
        cache = PaperQuantitiesCache(
            profile_residual_fn=_real_g,
            rho=0.2,
            c=2.0,
            d=0.5,
            eta=0.3,
        )
        assert cache.rho == 0.2
        assert cache.c == 2.0
        assert cache.d == 0.5
        assert cache.eta == 0.3
        # cell_C depends on (rho, c); recompute from paper_quantities and
        # assert byte-equality (cache must be byte-stable for cosine
        # baseline parity).
        from adaptive_reflow.theory.paper_quantities import per_cell_coefficient_C

        assert cache.cell_C == per_cell_coefficient_C(rho=0.2, c=2.0)
        from adaptive_reflow.theory.paper_quantities import exterior_gap_e_rho

        assert cache.e_rho == exterior_gap_e_rho(rho=0.2, eta=0.3)

    def test_byte_stability_across_caches(self) -> None:
        """Two caches with the same profile return bit-identical floats."""
        c1 = PaperQuantitiesCache(profile_residual_fn=_real_g)
        c2 = PaperQuantitiesCache(profile_residual_fn=_real_g)
        # Touch each property on c1; c2 should match byte-identically.
        c1_sheet = c1.sheet_A
        c1_packing = c1.packing_B
        c1_cell = c1.cell_C
        c1_erho = c1.e_rho
        assert c2.sheet_A == c1_sheet
        assert c2.packing_B == c1_packing
        assert c2.cell_C == c1_cell
        assert c2.e_rho == c1_erho

    def test_lazy_memo_single_computation(self) -> None:
        """Two reads of the same property return the same float object.

        The lazy-memo invariant (Wave 296 P1 §1.6) is that the
        producer is called AT MOST ONCE per quantity.
        """
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        # First read triggers computation; subsequent reads return the
        # SAME float object (id() equality).
        first = cache.sheet_A
        second = cache.sheet_A
        assert first is second
        first = cache.packing_B
        second = cache.packing_B
        assert first is second
        first = cache.cell_C
        second = cache.cell_C
        assert first is second
        first = cache.e_rho
        second = cache.e_rho
        assert first is second

    def test_stats_reports_all_computed(self) -> None:
        """stats() reports all four quantities as computed after first access."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        # Before any access: 0 quantities computed.
        s0 = cache.stats()
        assert s0["is_active"] == 1
        assert s0["activated_count"] == 0
        assert s0["sheet_A_computed"] == 0
        assert s0["packing_B_computed"] == 0
        assert s0["cell_C_computed"] == 0
        assert s0["e_rho_computed"] == 0
        # Touch each property.
        _ = cache.sheet_A
        _ = cache.packing_B
        _ = cache.cell_C
        _ = cache.e_rho
        s1 = cache.stats()
        assert s1["is_active"] == 1
        assert s1["sheet_A_computed"] == 1
        assert s1["packing_B_computed"] == 1
        assert s1["cell_C_computed"] == 1
        assert s1["e_rho_computed"] == 1

    def test_profile_residual_fn_property_round_trips(self) -> None:
        """profile_residual_fn property returns the same callable that was passed in."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        assert cache.profile_residual_fn is _real_g


# ---------------------------------------------------------------------------
# 2. Dormant — with profile_residual_fn=None, is_active=False, properties return None
# ---------------------------------------------------------------------------


class TestPaperQuantitiesCacheNoProfile:
    """Dormant cache: profile_residual_fn=None → is_active=False, all None."""

    def test_is_active_false(self) -> None:
        """Without profile_residual_fn, is_active returns False."""
        cache = PaperQuantitiesCache()
        assert cache.is_active is False

    def test_all_four_properties_return_none(self) -> None:
        """All four paper-quantity properties return None when dormant."""
        cache = PaperQuantitiesCache()
        assert cache.sheet_A is None
        assert cache.packing_B is None
        assert cache.cell_C is None
        assert cache.e_rho is None

    def test_get_returns_none_for_every_site(self) -> None:
        """Every site dispatch returns None when the cache is dormant."""
        cache = PaperQuantitiesCache()
        for site_name in PAPER_QUANTITIES_SITE_NAMES:
            assert cache.get(site_name) is None, (
                f"site {site_name!r} returned non-None on dormant cache"
            )

    def test_profile_residual_fn_returns_none(self) -> None:
        """profile_residual_fn property returns None when dormant."""
        cache = PaperQuantitiesCache()
        assert cache.profile_residual_fn is None

    def test_f_side_constants_still_exposed_when_dormant(self) -> None:
        """F-side constants (rho, c, d, eta) are still readable when dormant.

        Rationale: the F-side constants are configuration, not
        computation — they are valid even when no profile is supplied
        because cell_C and e_rho depend only on (rho, c, eta).
        """
        cache = PaperQuantitiesCache()
        assert cache.rho == PAPER_QUANTITIES_CACHE_DEFAULT_RHO
        assert cache.c == PAPER_QUANTITIES_CACHE_DEFAULT_C
        assert cache.d == PAPER_QUANTITIES_CACHE_DEFAULT_D
        assert cache.eta == PAPER_QUANTITIES_CACHE_DEFAULT_ETA

    def test_stats_reports_dormant_state(self) -> None:
        """stats() reports is_active=0 and all quantities not computed."""
        cache = PaperQuantitiesCache()
        s = cache.stats()
        assert s["is_active"] == 0
        assert s["activated_count"] == 0
        assert s["sheet_A_computed"] == 0
        assert s["packing_B_computed"] == 0
        assert s["cell_C_computed"] == 0
        assert s["e_rho_computed"] == 0

    def test_activated_sites_empty_when_dormant(self) -> None:
        """activated_sites is empty even if consume() is called on a dormant cache."""
        cache = PaperQuantitiesCache()
        assert cache.activated_sites == ()
        # consume() on dormant: no-op, returns False.
        assert cache.consume("solver_hint") is False
        assert cache.activated_sites == ()

    def test_zero_math_cost_default_construction(self) -> None:
        """Dormant construction has no math cost: producer never invoked.

        We assert via the stats() report: none of the four quantity
        slots has been computed, so the producer callables were never
        invoked. (The producer lambdas close over profile_residual_fn
        which is None for dormant — even calling them would be a bug.)
        """
        cache = PaperQuantitiesCache()
        s = cache.stats()
        for key in ("sheet_A_computed", "packing_B_computed",
                    "cell_C_computed", "e_rho_computed"):
            assert s[key] == 0, f"{key} unexpectedly computed for dormant cache"


# ---------------------------------------------------------------------------
# 3. Consume — activation log is idempotent
# ---------------------------------------------------------------------------


class TestPaperQuantitiesCacheConsume:
    """Activation log: consume() is idempotent; activated_sites is append-only."""

    def test_consume_first_time_returns_true(self) -> None:
        """consume() returns True on the first call for a given site name."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        assert cache.consume("solver_hint") is True
        assert cache.activated_sites == ("solver_hint",)

    def test_consume_second_time_returns_false(self) -> None:
        """consume() returns False on a second call for the same site name (idempotent)."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        assert cache.consume("solver_hint") is True
        assert cache.consume("solver_hint") is False
        # activated_sites does NOT duplicate the entry.
        assert cache.activated_sites == ("solver_hint",)

    def test_consume_distinct_sites_each_first_time(self) -> None:
        """Consuming N distinct sites yields N entries in activated_sites."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        for site_name in ("solver_hint", "dt_floor", "merge_floor", "policy_C"):
            assert cache.consume(site_name) is True
        # Verify tuple contains all four (insertion order preserved).
        assert cache.activated_sites == (
            "solver_hint", "dt_floor", "merge_floor", "policy_C"
        )
        # A second pass returns False for each.
        for site_name in ("solver_hint", "dt_floor", "merge_floor", "policy_C"):
            assert cache.consume(site_name) is False

    def test_consume_unknown_site_returns_false_no_raise(self) -> None:
        """consume() with an unknown site name returns False without raising.

        Rationale: audit sites must never break the data path. The
        getter :meth:`get` DOES raise on unknown sites (caller-visible
        contract); the consume() method is the soft path used by the
        audit log and must never raise.
        """
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        assert cache.consume("not_a_real_site") is False
        # activated_sites remains empty.
        assert cache.activated_sites == ()

    def test_consume_all_fifteen_sites(self) -> None:
        """All 16 site names accept consume() and populate activated_sites.

        Wave 296 P4 — added the ``"sheet_cell"`` site for the
        sheet-vs-cell heuristic (Site 14 in the B-class wiring), which
        is a distinct cache entry from ``"evaluator"`` (Site 11) per
        the task spec. The canonical site set is therefore 16 names,
        not 15; this test now checks 16. The rename preserves the
        docstring's intent (every site name accepts consume() and the
        activation log captures all of them).
        """
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        assert len(PAPER_QUANTITIES_SITE_NAMES) == 16
        for site_name in PAPER_QUANTITIES_SITE_NAMES:
            assert cache.consume(site_name) is True
        assert len(cache.activated_sites) == 16
        assert set(cache.activated_sites) == set(PAPER_QUANTITIES_SITE_NAMES)

    def test_consume_does_not_compute_quantities(self) -> None:
        """consume() is a log operation; it must NOT trigger quantity computation."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        cache.consume("solver_hint")
        cache.consume("merge_floor")
        s = cache.stats()
        # No quantity slot was triggered by the consume() calls.
        assert s["sheet_A_computed"] == 0
        assert s["packing_B_computed"] == 0
        assert s["cell_C_computed"] == 0
        assert s["e_rho_computed"] == 0
        # But activated_count is 2.
        assert s["activated_count"] == 2

    def test_clear_resets_activation_log(self) -> None:
        """clear() resets the activation log but NOT the cached quantities."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        # Compute a quantity (to memoize it).
        sheet_a_first = cache.sheet_A
        # Consume some sites.
        cache.consume("solver_hint")
        cache.consume("merge_floor")
        assert cache.activated_sites == ("solver_hint", "merge_floor")
        # Clear the activation log.
        cache.clear()
        assert cache.activated_sites == ()
        # The cached quantity is preserved.
        assert cache.sheet_A == sheet_a_first
        assert cache.sheet_A is sheet_a_first  # same object


# ---------------------------------------------------------------------------
# 4. Site-aware dispatch — get() returns the canonical value per site
# ---------------------------------------------------------------------------


class TestPaperQuantitiesCacheDispatch:
    """:meth:`get` returns the canonical value for each of the 16 sites."""

    def test_get_solver_hint_returns_e_rho(self) -> None:
        """solver_hint, dt_floor, alpha_floor, merge_floor, regime, derivation → e_rho."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        e_rho_value = cache.e_rho
        for site_name in (
            "solver_hint", "dt_floor", "alpha_floor",
            "merge_floor", "regime", "derivation",
        ):
            assert cache.get(site_name) == e_rho_value, (
                f"site {site_name!r} did not return e_rho"
            )

    def test_get_policy_c_returns_cell_c(self) -> None:
        """policy_C → cell_C."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        assert cache.get("policy_C") == cache.cell_C

    def test_get_noise_bias_returns_four_tuple(self) -> None:
        """noise_bias → (sheet_A, packing_B, cell_C, e_rho) tuple."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        nb = cache.get("noise_bias")
        assert isinstance(nb, tuple)
        assert len(nb) == 4
        assert nb == (cache.sheet_A, cache.packing_B, cache.cell_C, cache.e_rho)

    def test_get_evaluator_returns_two_tuple(self) -> None:
        """evaluator → (sheet_A, cell_C) tuple."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        ev = cache.get("evaluator")
        assert isinstance(ev, tuple)
        assert len(ev) == 2
        assert ev == (cache.sheet_A, cache.cell_C)

    def test_get_profile_returns_callable(self) -> None:
        """profile → the original profile_residual_fn callable."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        assert cache.get("profile") is _real_g

    def test_get_mfpqa_evidence_fid_lipschitz_checker_return_snapshot(
        self,
    ) -> None:
        """mfpqa, evidence, fid, lipschitz, checker → PaperQuantitiesSnapshot."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        for site_name in (
            "mfpqa", "evidence", "fid", "lipschitz", "checker",
        ):
            snapshot = cache.get(site_name)
            assert isinstance(snapshot, PaperQuantitiesSnapshot), (
                f"site {site_name!r} did not return a PaperQuantitiesSnapshot"
            )
            assert snapshot.sheet_A == cache.sheet_A
            assert snapshot.packing_B == cache.packing_B
            assert snapshot.cell_C == cache.cell_C
            assert snapshot.exterior_gap_e_rho == cache.e_rho

    def test_get_unknown_site_raises(self) -> None:
        """get() with an unknown site name raises ValueError."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        with pytest.raises(ValueError, match="unknown paper-quantities site"):
            cache.get("not_a_real_site")


# ---------------------------------------------------------------------------
# 5. Validation errors at construction time
# ---------------------------------------------------------------------------


class TestPaperQuantitiesCacheValidation:
    """Constructor rejects bad inputs at the F-side boundary."""

    def test_invalid_rho_rejected(self) -> None:
        """rho outside (0, 1) is rejected."""
        with pytest.raises(ValueError, match="rho must be in"):
            PaperQuantitiesCache(rho=0.0)
        with pytest.raises(ValueError, match="rho must be in"):
            PaperQuantitiesCache(rho=1.0)
        with pytest.raises(ValueError, match="rho must be in"):
            PaperQuantitiesCache(rho=-0.1)

    def test_invalid_c_rejected(self) -> None:
        """c <= 0 is rejected."""
        with pytest.raises(ValueError, match="c must be positive"):
            PaperQuantitiesCache(c=0.0)
        with pytest.raises(ValueError, match="c must be positive"):
            PaperQuantitiesCache(c=-1.0)

    def test_invalid_d_rejected(self) -> None:
        """d <= 0 is rejected."""
        with pytest.raises(ValueError, match="d must be positive"):
            PaperQuantitiesCache(d=0.0)

    def test_invalid_eta_rejected(self) -> None:
        """eta <= 0 is rejected."""
        with pytest.raises(ValueError, match="eta must be positive"):
            PaperQuantitiesCache(eta=0.0)

    def test_non_callable_profile_rejected(self) -> None:
        """profile_residual_fn must be callable or None."""
        with pytest.raises(TypeError, match="profile_residual_fn must be callable"):
            PaperQuantitiesCache(profile_residual_fn="not_callable")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 6. Engine flag integration — opt-in default False, byte-stable
# ---------------------------------------------------------------------------


class TestEnginePaperQuantitiesCacheFlag:
    """Engine accepts ``enable_full_jmaa_theory`` + ``paper_quantities_cache``.

    Backward-compat: ``enable_full_jmaa_theory=False`` (the default)
    leaves ``engine.paper_quantities_cache`` as ``None`` and existing
    Engine callers see byte-identical behaviour.
    """

    def test_default_engine_cache_is_none(self) -> None:
        """Default Engine has ``paper_quantities_cache is None``."""
        engine = Engine()
        assert engine.paper_quantities_cache is None

    def test_flag_false_with_cache_still_none(self) -> None:
        """flag=False + supplied cache → cache property returns None.

        The cache is IGNORED when the flag is False (preserves
        byte-stability; see W296 P1 §2.1).
        """
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        engine = Engine(paper_quantities_cache=cache)
        assert engine.paper_quantities_cache is None

    def test_flag_true_no_cache_constructs_dormant(self) -> None:
        """flag=True + no cache → engine constructs a dormant cache."""
        engine = Engine(enable_full_jmaa_theory=True)
        assert engine.paper_quantities_cache is not None
        assert engine.paper_quantities_cache.is_active is False

    def test_flag_true_with_active_cache(self) -> None:
        """flag=True + active cache → engine uses the supplied cache."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        engine = Engine(enable_full_jmaa_theory=True, paper_quantities_cache=cache)
        assert engine.paper_quantities_cache is cache

    def test_flag_true_with_dormant_cache_raises(self) -> None:
        """flag=True + dormant cache → ValueError (programming error)."""
        with pytest.raises(ValueError, match="enable_full_jmaa_theory=True"):
            Engine(
                enable_full_jmaa_theory=True,
                paper_quantities_cache=PaperQuantitiesCache(),
            )

    def test_existing_engine_kwargs_still_work(self) -> None:
        """Existing Engine kwargs (operation_steps, feature_flag, digest_cache) work."""
        e1 = Engine(operation_steps=("capabilities_handshake",))
        e2 = Engine(feature_flag=False)
        e3 = Engine(digest_cache=None)
        # None of these should raise, and all should have the new
        # property returning None (since enable_full_jmaa_theory
        # defaults to False).
        for engine in (e1, e2, e3):
            assert engine.paper_quantities_cache is None


# ---------------------------------------------------------------------------
# 7. Byte-stability — the cache must be pure-functional
# ---------------------------------------------------------------------------


class TestPaperQuantitiesCacheByteStability:
    """Lock down the byte-stability contract for the cache."""

    def test_sheet_A_matches_paper_quantity_helper(self) -> None:
        """sheet_A matches a direct call to sheet_evidence_A(profile)."""
        from adaptive_reflow.theory.paper_quantities import sheet_evidence_A

        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        assert cache.sheet_A == sheet_evidence_A(_real_g)

    def test_packing_B_matches_paper_quantity_helper(self) -> None:
        """packing_B matches a direct call to root_cell_packing_B(profile, d)."""
        from adaptive_reflow.theory.paper_quantities import root_cell_packing_B

        cache = PaperQuantitiesCache(profile_residual_fn=_real_g, d=1.0)
        assert cache.packing_B == root_cell_packing_B(_real_g, separation_d=1.0)

    def test_cell_C_matches_paper_quantity_helper(self) -> None:
        """cell_C matches a direct call to per_cell_coefficient_C(rho, c)."""
        from adaptive_reflow.theory.paper_quantities import per_cell_coefficient_C

        cache = PaperQuantitiesCache(profile_residual_fn=_real_g, rho=0.1, c=1.0)
        assert cache.cell_C == per_cell_coefficient_C(rho=0.1, c=1.0)

    def test_e_rho_matches_paper_quantity_helper(self) -> None:
        """e_rho matches a direct call to exterior_gap_e_rho(rho, eta)."""
        from adaptive_reflow.theory.paper_quantities import exterior_gap_e_rho

        cache = PaperQuantitiesCache(profile_residual_fn=_real_g, rho=0.1, eta=0.1)
        assert cache.e_rho == exterior_gap_e_rho(rho=0.1, eta=0.1)


# ---------------------------------------------------------------------------
# Helper: optional sanity check on the actual set of site names (15 total)
# ---------------------------------------------------------------------------


def test_paper_quantities_site_names_count() -> None:
    """PAPER_QUANTITIES_SITE_NAMES is exactly 16 names (Wave 296 P4 added sheet_cell)."""
    assert len(PAPER_QUANTITIES_SITE_NAMES) == 16


def test_paper_quantities_site_names_unique() -> None:
    """PAPER_QUANTITIES_SITE_NAMES has no duplicate entries."""
    assert len(PAPER_QUANTITIES_SITE_NAMES) == len(set(PAPER_QUANTITIES_SITE_NAMES))


def test_engine_module_reexports_paper_quantities_cache() -> Any:
    """The framework.engine shim re-exports PaperQuantitiesCache."""
    from adaptive_reflow.framework.engine import PaperQuantitiesCache as Reexported

    assert Reexported is PaperQuantitiesCache


# ---------------------------------------------------------------------------
# 8. Wave 296 P3 — Engine A-class site wiring smoke test
# ---------------------------------------------------------------------------


class TestEngineAClassSiteWiring:
    """Smoke test for the Wave 296 P3 A-class site wiring.

    Verifies that :meth:`Engine.consume_a_class_sites` activates all 7
    A-class sites when the engine is constructed with
    ``enable_full_jmaa_theory=True`` and a real (active) cache. Also
    verifies byte-stability: the default engine and an engine with
    ``enable_full_jmaa_theory=False`` consume ZERO sites (the
    pre-Wave-296 cosine baseline path is unchanged).
    """

    def test_a_class_sites_default_engine_no_consumption(self) -> None:
        """Default Engine (flag=False, cache=None): consume_a_class_sites returns 0.

        The D.4 byte-stability path is byte-identical to the pre-Wave-296
        engine — no A-class sites are activated.
        """
        engine = Engine()
        assert engine.paper_quantities_cache is None
        assert engine.consume_a_class_sites() == 0

    def test_a_class_sites_flag_true_no_cache_no_consumption(self) -> None:
        """flag=True with no cache → dormant cache → 0 sites consumed."""
        engine = Engine(enable_full_jmaa_theory=True)
        assert engine.paper_quantities_cache is not None
        assert engine.paper_quantities_cache.is_active is False
        assert engine.consume_a_class_sites() == 0

    def test_a_class_sites_flag_true_active_cache_all_seven_consumed(
        self,
    ) -> None:
        """flag=True + active cache → all 7 A-class sites consumed.

        The smoke test: instantiate Engine with enable_full_jmaa_theory=True
        and a real PaperQuantitiesCache (profile_residual_fn set), call
        consume_a_class_sites, verify all 7 A-class sites are activated.

        The 7 A-class sites from Wave 296 P1 §3.2:
          1. solver-level paper-quantity hint
          2. Dynamics dt/alpha floor (2 cache names: dt_floor, alpha_floor)
          3. Perturbation noise bias (Theorem1)
          4. Merge operator (BoundedMergeOperator exterior_gap)
          5. Policy driver (AdaptivePolicyDriver per_cell_C)
          6. profile_residual_fn (adapter-level)
          7. FID theorem-aligned

        The engine's _A_CLASS_SITE_NAMES tuple has 8 cache entries
        (solver_hint, dt_floor, alpha_floor, noise_bias, merge_floor,
        policy_C, profile, fid) because Sites 4/4b share one A-class
        site but use two cache dispatches. The spec counts 7 logical
        sites; the engine consumes 8 cache entries.
        """
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        engine = Engine(
            enable_full_jmaa_theory=True,
            paper_quantities_cache=cache,
        )
        assert engine.paper_quantities_cache is cache
        # The engine consumes all 8 A-class cache entries (which the
        # task spec counts as 7 A-class sites because dt_floor/alpha_floor
        # collapse to one "Dynamics dt/alpha floor" site).
        assert engine.consume_a_class_sites() == 8
        # Verify all 8 A-class cache entries are in activated_sites.
        activated = set(cache.activated_sites)
        expected = {
            "solver_hint",   # Site 2 — Solver-level paper-quantity hint
            "dt_floor",      # Site 4 — Dynamics dt floor
            "alpha_floor",   # Site 4b — Dynamics alpha floor
            "noise_bias",    # Site 5 — Theorem1DynamicNoiseBias
            "merge_floor",   # Site 6 — BoundedMergeOperator
            "policy_C",      # Site 7 — AdaptivePolicyDriver
            "profile",       # Site 13 — adapter-level profile_residual_fn
            "fid",           # Site 9 — InceptionV3TheoremAlignedFIDEvaluator
        }
        assert expected.issubset(activated), (
            f"missing sites: {expected - activated}"
        )

    def test_a_class_sites_double_call_is_idempotent(self) -> None:
        """consume_a_class_sites is idempotent: second call returns 0."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        engine = Engine(
            enable_full_jmaa_theory=True,
            paper_quantities_cache=cache,
        )
        first_count = engine.consume_a_class_sites()
        assert first_count > 0  # at least 1 site consumed
        second_count = engine.consume_a_class_sites()
        assert second_count == 0  # already consumed

    def test_a_class_sites_engine_count_is_8_or_more(self) -> None:
        """The engine consumes at least 7 sites (the canonical A-class set).

        The engine's _A_CLASS_SITE_NAMES tuple has 8 entries
        (solver_hint, dt_floor, alpha_floor, noise_bias, merge_floor,
        policy_C, profile, fid). The task spec counts Sites 4/4b as a
        single "Dynamics dt/alpha floor" site, so the spec reports 7;
        the engine's helper consumes all 8 by name.
        """
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        engine = Engine(
            enable_full_jmaa_theory=True,
            paper_quantities_cache=cache,
        )
        activated = engine.consume_a_class_sites()
        # The engine wires 8 A-class site names.
        assert activated >= 7, (
            f"expected at least 7 sites consumed; got {activated}"
        )

    def test_a_class_sites_byte_stability_default_engine(self) -> None:
        """Default engine's consume_a_class_sites is byte-stable across calls.

        Calling consume_a_class_sites on a default Engine (no cache) is a
        no-op that returns 0 deterministically.
        """
        e1 = Engine()
        e2 = Engine()
        assert e1.consume_a_class_sites() == e2.consume_a_class_sites() == 0


# ---------------------------------------------------------------------------
# 9. Wave 296 P4 — Engine B-class site wiring smoke test
# ---------------------------------------------------------------------------


class TestEngineBClassSiteWiring:
    """Smoke test for the Wave 296 P4 B-class site wiring.

    Verifies that :meth:`Engine.consume_b_class_sites` activates all 8
    B-class sites when the engine is constructed with
    ``enable_full_jmaa_theory=True`` and a real (active) cache. Also
    verifies byte-stability: the default engine and an engine with
    ``enable_full_jmaa_theory=False`` consume ZERO B-class sites (the
    pre-Wave-296 cosine baseline path is unchanged — every B-class
    opt-in switch stays off).

    The 8 B-class sites from
    ``docs/audit/wave296-p4-b-class-wired.md`` §3.2:

    1. ``mfpqa`` — Integrator MFPQA (EulerStep → MultiFidelityPaperQuantityStep)
    2. ``evidence`` — Evidence-driven scheduler family
    3. ``lipschitz`` — Lipschitz diagnostic live caller
    4. ``evaluator`` — Posterior selection evaluator (sheet/cell ratio)
    5. ``checker`` — Theorem1StatementChecker paper_quantities snapshot
    6. ``sheet_cell`` — Sheet-vs-cell heuristic (closed-form Gaussian proxy)
    7. ``regime`` — Regime selector (CosineAnnealRegimeSelector wrap)
    8. ``derivation`` — Solver derivation companion (BLConvergenceEpsilonSchedule)
    """

    def test_b_class_sites_default_engine_no_consumption(self) -> None:
        """Default Engine (flag=False, cache=None): consume_b_class_sites returns 0.

        The D.4 byte-stability path is byte-identical to the pre-Wave-296
        engine — no B-class sites are activated. This locks down the
        invariant that ``Engine()`` (the canonical default constructor)
        never activates any B-class opt-in switch.
        """
        engine = Engine()
        assert engine.paper_quantities_cache is None
        assert engine.enable_full_jmaa_theory is False
        assert engine.consume_b_class_sites() == 0

    def test_b_class_sites_flag_true_no_cache_no_consumption(self) -> None:
        """flag=True with no cache → dormant cache → 0 sites consumed.

        When the caller enables ``enable_full_jmaa_theory=True`` but
        does NOT supply a cache, the engine constructs a dormant cache
        internally (is_active=False). The B-class wiring is a no-op.
        """
        engine = Engine(enable_full_jmaa_theory=True)
        assert engine.enable_full_jmaa_theory is True
        assert engine.paper_quantities_cache is not None
        assert engine.paper_quantities_cache.is_active is False
        assert engine.consume_b_class_sites() == 0

    def test_b_class_sites_flag_true_active_cache_all_eight_consumed(
        self,
    ) -> None:
        """flag=True + active cache → all 8 B-class sites consumed.

        The smoke test: instantiate Engine with enable_full_jmaa_theory=True
        and a real PaperQuantitiesCache (profile_residual_fn set), call
        consume_b_class_sites, verify all 8 B-class sites are activated.
        """
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        engine = Engine(
            enable_full_jmaa_theory=True,
            paper_quantities_cache=cache,
        )
        assert engine.enable_full_jmaa_theory is True
        assert engine.paper_quantities_cache is cache
        # The engine consumes all 8 B-class sites.
        activated = engine.consume_b_class_sites()
        assert activated == 8, (
            f"expected 8 B-class sites consumed; got {activated}"
        )
        # Verify all 8 B-class cache entries are in activated_sites.
        activated_set = set(cache.activated_sites)
        expected = {
            "mfpqa",        # Site 3  — Integrator MFPQA
            "evidence",     # Site 8  — Evidence-driven scheduler
            "lipschitz",    # Site 10 — Lipschitz diagnostic
            "evaluator",    # Site 11 — Posterior selection evaluator
            "checker",      # Site 12 — Theorem1StatementChecker
            "sheet_cell",   # Site 14 — Sheet-vs-cell heuristic
            "regime",       # Site 15 — Regime selector
            "derivation",   # Site 16 — Solver derivation companion
        }
        assert expected.issubset(activated_set), (
            f"missing sites: {expected - activated_set}"
        )

    def test_b_class_sites_double_call_is_idempotent(self) -> None:
        """consume_b_class_sites is idempotent: second call returns 0."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        engine = Engine(
            enable_full_jmaa_theory=True,
            paper_quantities_cache=cache,
        )
        first_count = engine.consume_b_class_sites()
        assert first_count == 8
        second_count = engine.consume_b_class_sites()
        assert second_count == 0  # already consumed

    def test_b_class_sites_byte_stability_default_engine(self) -> None:
        """Default engine's consume_b_class_sites is byte-stable across calls.

        Calling consume_b_class_sites on a default Engine (no cache,
        no flag) is a no-op that returns 0 deterministically across
        two Engine instances.
        """
        e1 = Engine()
        e2 = Engine()
        assert e1.consume_b_class_sites() == e2.consume_b_class_sites() == 0

    def test_b_class_sites_count_is_8(self) -> None:
        """Engine consumes exactly 8 B-class sites (per Wave 296 P4 spec)."""
        cache = PaperQuantitiesCache(profile_residual_fn=_real_g)
        engine = Engine(
            enable_full_jmaa_theory=True,
            paper_quantities_cache=cache,
        )
        activated = engine.consume_b_class_sites()
        assert activated == 8
        # Also verify the engine's _B_CLASS_SITE_NAMES tuple size.
        assert len(engine._B_CLASS_SITE_NAMES) == 8

    def test_b_class_sites_engine_flag_property(self) -> None:
        """Engine's ``enable_full_jmaa_theory`` property reports the flag.

        The framework caller (e.g. runner's
        ``_apply_engine_paper_quantities_cache_b_class``) consults
        this property together with ``cache.is_active`` to decide
        whether to flip opt-in switches. Default engine: False; flag-
        on engine: True.
        """
        e_default = Engine()
        e_flag_on = Engine(enable_full_jmaa_theory=True)
        assert e_default.enable_full_jmaa_theory is False
        assert e_flag_on.enable_full_jmaa_theory is True
