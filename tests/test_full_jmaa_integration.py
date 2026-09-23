"""End-to-end integration test for the full JMAA theory activation (Wave 296 P5).

This test file locks down the Wave 296 P5 invariant:

    When ``Engine(enable_full_jmaa_theory=True)`` is constructed with
    an ACTIVE ``PaperQuantitiesCache`` (i.e. ``profile_residual_fn is
    not None``) AND the framework caller invokes BOTH the A-class
    framework hook (``Engine.consume_a_class_sites``) AND the B-class
    framework hook (``Engine.consume_b_class_sites``), the cache's
    activation log records **all 16 JMAA application sites** from the
    Wave 292 P1 inventory.

When the flag is OFF (the default — byte-identical to the pre-Wave-296
cosine baseline), the cache is ``None`` and **zero sites** are
activated: the cosine-baseline path is preserved.

The end-to-end runner path (``ReInferenceRunner.run``) invokes the
B-class framework hook automatically when the flag is on AND the
cache is active; the A-class framework hook is a separate
caller-side operation (per ``docs/audit/wave296-p3-a-class-wired.md``
§2.2: "Caller invokes ``engine.consume_a_class_sites()`` — the
framework's hook for wiring the A-class dormant sites.").

Backward compatibility
----------------------

The default ``Engine()`` constructor produces a cache-less engine
(``paper_quantities_cache is None``); ``consume_a_class_sites()`` and
``consume_b_class_sites()`` both return 0 — the cosine-baseline path
is byte-identical to the pre-Wave-296 path. The D.4 30/30
byte-stability gate is preserved by construction.

The 16 sites (canonical set)
----------------------------

**A-class (8 cache entries — Wave 296 P3):**

1. ``solver_hint`` — Site 2 — Solver-level paper-quantity hint
2. ``dt_floor`` — Site 4 — Dynamics dt floor
3. ``alpha_floor`` — Site 4b — Dynamics alpha floor
4. ``noise_bias`` — Site 5 — Theorem1DynamicNoiseBias
5. ``merge_floor`` — Site 6 — BoundedMergeOperator exterior_gap
6. ``policy_C`` — Site 7 — AdaptivePolicyDriver per_cell_C
7. ``profile`` — Site 13 — adapter-level profile_residual_fn
8. ``fid`` — Site 9 — InceptionV3TheoremAlignedFIDEvaluator

**B-class (8 cache entries — Wave 296 P4):**

1. ``mfpqa`` — Site 3 — Integrator MFPQA (EulerStep → MultiFidelityPaperQuantityStep)
2. ``evidence`` — Site 8 — Evidence-driven scheduler family
3. ``lipschitz`` — Site 10 — Lipschitz diagnostic live caller
4. ``evaluator`` — Site 11 — Posterior selection evaluator (sheet/cell)
5. ``checker`` — Site 12 — Theorem1StatementChecker snapshot
6. ``sheet_cell`` — Site 14 — Sheet-vs-cell heuristic
7. ``regime`` — Site 15 — Regime selector wrap
8. ``derivation`` — Site 16 — Solver derivation companion

Total = 16 cache entries → 16 distinct activation-log entries.

The task spec counts Sites 4/4b as a single "Dynamics dt/alpha floor"
site, so the spec reports **15 logical sites**. The engine consumes
**16 cache entries** (8 A-class + 8 B-class) via the activation log.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import pytest

from adaptive_reflow.frame.engine import Engine
from adaptive_reflow.framework.paper_quantities_cache import (
    PAPER_QUANTITIES_SITE_NAMES,
    PaperQuantitiesCache,
)

# ---------------------------------------------------------------------------
# Canonical site set (locked down by the activation-log contract)
# ---------------------------------------------------------------------------

# The 8 A-class sites from Wave 296 P3 §3.2.
A_CLASS_SITES: tuple[str, ...] = (
    "solver_hint",
    "dt_floor",
    "alpha_floor",
    "noise_bias",
    "merge_floor",
    "policy_C",
    "profile",
    "fid",
)

# The 8 B-class sites from Wave 296 P4 §3.2.
B_CLASS_SITES: tuple[str, ...] = (
    "mfpqa",
    "evidence",
    "lipschitz",
    "evaluator",
    "checker",
    "sheet_cell",
    "regime",
    "derivation",
)

# All 16 JMAA application sites (A-class + B-class).
ALL_16_SITES: tuple[str, ...] = A_CLASS_SITES + B_CLASS_SITES

# Backward-compatible single 'profile_residual_fn' that drives an
# ACTIVE cache. Chosen as ``math.sin`` because it is non-trivial
# (multiple sign changes in ``[0, 2*pi]``) so the four paper quantities
# exercise their full lazy-memo machinery without being trivial zeros.
_REAL_PROFILE_RESIDUAL: Callable[[float], float] = math.sin


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def twodim_adapter(twodim_fm_weights_path: Path):
    """Return a single :class:`TwoDimFMAdapter` instance for the integration run.

    Reuses the canonical Wave 18 weights fixture (``twodim_fm_weights_path``)
    so the integration test exercises the same adapter path as the
    D.4 byte-stability gate.
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    return TwoDimFMAdapter(
        weights_path=twodim_fm_weights_path,
        target="two_moons",
    )


@pytest.fixture
def active_cache() -> PaperQuantitiesCache:
    """Return an ACTIVE :class:`PaperQuantitiesCache`.

    An active cache has ``is_active is True`` (``profile_residual_fn is
    not None``). The cache's four paper quantities are computed lazily
    on first access; ``cache.activated_sites`` is empty until a caller
    invokes :meth:`consume`.
    """
    return PaperQuantitiesCache(profile_residual_fn=_REAL_PROFILE_RESIDUAL)


@pytest.fixture
def dormant_cache() -> PaperQuantitiesCache:
    """Return a DORMANT :class:`PaperQuantitiesCache`` (``profile_residual_fn=None``).

    A dormant cache has ``is_active is False``; every property returns
    ``None`` and :meth:`consume` is a no-op.
    """
    return PaperQuantitiesCache()


@pytest.fixture
def engine_with_flag(active_cache: PaperQuantitiesCache) -> Engine:
    """Return an :class:`Engine` with ``enable_full_jmaa_theory=True`` + active cache."""
    return Engine(
        enable_full_jmaa_theory=True,
        paper_quantities_cache=active_cache,
    )


# ---------------------------------------------------------------------------
# 1. End-to-end integration: runner + engine + cache → 16 sites active
# ---------------------------------------------------------------------------


class TestAllSitesActiveWithFlag:
    """End-to-end integration: 16 sites active when flag=True + active cache.

    The test instantiates a real :class:`ReInferenceRunner` with a
    :class:`TwoDimFMAdapter`, runs **1 round** with the JMAA-theory
    flag ON, and verifies that the cache's activation log records
    **all 16 sites** (8 A-class + 8 B-class) after the runner invokes
    the framework hooks.
    """

    def test_runner_one_round_activates_all_sixteen_sites(
        self,
        twodim_adapter: object,
        active_cache: PaperQuantitiesCache,
    ) -> None:
        """Runner.run() + framework hooks → all 16 sites in cache.activated_sites.

        Wave 296 P5 — the canonical end-to-end integration test. Builds
        an :class:`Engine` with ``enable_full_jmaa_theory=True`` and an
        active :class:`PaperQuantitiesCache`, wires the engine into a
        :class:`ReInferenceRunner`, runs 1 round, and verifies that
        the activation log contains exactly 16 distinct site names
        after both the A-class and B-class framework hooks are
        invoked.

        Why both helpers are called manually:

        * The runner's :meth:`run` auto-invokes the B-class helper
          (``consume_b_class_sites``) when the flag is on AND the
          cache is active. The A-class helper is a separate
          caller-side operation (see Wave 296 P3 §2.2).
        * To exercise the FULL 16-site activation, the test invokes
          ``engine.consume_a_class_sites()`` after ``run()`` returns.
          The combined activation log is the union of A-class and
          B-class sites.
        """
        from adaptive_reflow.algorithm.runner import (
            ReInferenceConfig,
            ReInferenceRunner,
        )

        engine = Engine(
            enable_full_jmaa_theory=True,
            paper_quantities_cache=active_cache,
        )
        assert engine.enable_full_jmaa_theory is True
        assert engine.paper_quantities_cache is active_cache
        assert active_cache.is_active is True

        runner = ReInferenceRunner(adapter=twodim_adapter, engine=engine)
        config = ReInferenceConfig(
            n_rounds=1,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=("xy",),
        )
        # Run 1 round — this auto-consumes the 8 B-class sites via
        # ``engine.consume_b_class_sites()``.
        result = runner.run(config)
        assert len(result.round_traces) == 1

        # The B-class helper consumed 8 sites through runner.run().
        # Now invoke the A-class helper explicitly (the framework-caller's
        # responsibility per Wave 296 P3 §2.2) to consume the remaining 8.
        a_class_activated = engine.consume_a_class_sites()
        assert a_class_activated == 8, (
            f"expected 8 A-class sites consumed; got {a_class_activated}"
        )

        # B-class is already consumed by runner.run() (idempotent → returns 0).
        b_class_activated = engine.consume_b_class_sites()
        assert b_class_activated == 0, (
            f"expected 0 new B-class sites (idempotent); got {b_class_activated}"
        )

        # The activation log must contain all 16 sites.
        activated = set(active_cache.activated_sites)
        assert len(activated) == 16, (
            f"expected 16 distinct sites; got {len(activated)}: "
            f"{sorted(active_cache.activated_sites)}"
        )
        missing = set(ALL_16_SITES) - activated
        assert not missing, f"missing sites: {missing}"

    def test_runner_one_round_paper_quantities_computed(
        self,
        twodim_adapter: object,
        active_cache: PaperQuantitiesCache,
    ) -> None:
        """All four paper quantities are computed after one round.

        Verifies that the cache's ``stats()`` reports every lazy-memo
        slot as computed (the A-class and B-class framework hooks
        materialise every slot via ``cache.get(site_name)``).
        """
        from adaptive_reflow.algorithm.runner import (
            ReInferenceConfig,
            ReInferenceRunner,
        )

        engine = Engine(
            enable_full_jmaa_theory=True,
            paper_quantities_cache=active_cache,
        )
        runner = ReInferenceRunner(adapter=twodim_adapter, engine=engine)
        config = ReInferenceConfig(
            n_rounds=1,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=("xy",),
        )
        runner.run(config)
        engine.consume_a_class_sites()
        engine.consume_b_class_sites()

        stats = active_cache.stats()
        assert stats["is_active"] == 1
        assert stats["activated_count"] == 16
        # All four paper quantities are computed (lazy-memo slots
        # materialised by the framework hooks).
        assert stats["sheet_A_computed"] == 1
        assert stats["packing_B_computed"] == 1
        assert stats["cell_C_computed"] == 1
        assert stats["e_rho_computed"] == 1

    def test_runner_one_round_cache_stats_snapshot(
        self,
        twodim_adapter: object,
        active_cache: PaperQuantitiesCache,
    ) -> None:
        """Cache stats snapshot: is_active=1, activated_count=16, all 4 quantities.

        This is the audit-doc-style snapshot expected by
        ``docs/audit/wave296-p1-architecture.md`` §6 ("observability
        contract"). Verifies the exact dict shape.
        """
        from adaptive_reflow.algorithm.runner import (
            ReInferenceConfig,
            ReInferenceRunner,
        )

        engine = Engine(
            enable_full_jmaa_theory=True,
            paper_quantities_cache=active_cache,
        )
        runner = ReInferenceRunner(adapter=twodim_adapter, engine=engine)
        config = ReInferenceConfig(
            n_rounds=1,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=("xy",),
        )
        runner.run(config)
        engine.consume_a_class_sites()
        engine.consume_b_class_sites()

        stats = active_cache.stats()
        assert stats == {
            "is_active": 1,
            "activated_count": 16,
            "sheet_A_computed": 1,
            "packing_B_computed": 1,
            "cell_C_computed": 1,
            "e_rho_computed": 1,
        }


# ---------------------------------------------------------------------------
# 2. Default flag=False → 0 sites active (cosine-baseline byte-stability)
# ---------------------------------------------------------------------------


class TestOnlyZeroSitesActiveWithoutFlag:
    """Flag=False (default) → zero sites active.

    Verifies the cosine-baseline byte-stability invariant: when the
    flag is off (the pre-Wave-296 default), the cache is ``None`` and
    zero sites are activated.
    """

    def test_default_engine_zero_sites(self) -> None:
        """Default ``Engine()`` → cache is None → 0 sites activated."""
        engine = Engine()
        assert engine.paper_quantities_cache is None
        assert engine.enable_full_jmaa_theory is False
        assert engine.consume_a_class_sites() == 0
        assert engine.consume_b_class_sites() == 0

    def test_default_engine_runner_zero_sites(
        self,
        twodim_adapter: object,
    ) -> None:
        """``Runner.run()`` with default Engine → 0 sites activated end-to-end.

        Verifies that the runner's full data flow (with the default
        flag-off engine) does NOT activate any JMAA application site —
        the cosine baseline path is preserved end-to-end.
        """
        from adaptive_reflow.algorithm.runner import (
            ReInferenceConfig,
            ReInferenceRunner,
        )

        engine = Engine()  # default: flag=False, cache=None
        runner = ReInferenceRunner(adapter=twodim_adapter, engine=engine)
        config = ReInferenceConfig(
            n_rounds=1,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=("xy",),
        )
        result = runner.run(config)
        assert len(result.round_traces) == 1
        # Engine.paper_quantities_cache is None → runner sees no cache.
        assert engine.paper_quantities_cache is None
        # Neither helper activates any site (cache is None → no-op).
        assert engine.consume_a_class_sites() == 0
        assert engine.consume_b_class_sites() == 0

    def test_flag_true_dormant_cache_zero_sites(self) -> None:
        """Flag=True + dormant cache (no profile) → 0 sites activated.

        When the caller enables the flag but does NOT supply a
        profile_residual_fn, the engine constructs a DORMANT cache.
        Every framework hook returns 0 (the dormant cache is a
        byte-stable no-op).
        """
        engine = Engine(enable_full_jmaa_theory=True)  # no cache supplied
        assert engine.paper_quantities_cache is not None
        assert engine.paper_quantities_cache.is_active is False
        assert engine.consume_a_class_sites() == 0
        assert engine.consume_b_class_sites() == 0

    def test_flag_false_with_supplied_cache_treated_as_none(self) -> None:
        """Flag=False + supplied cache → engine IGNORES the cache (cache is None).

        The cache is silently ignored when the flag is off; this
        preserves the cosine-baseline byte-stability invariant for
        callers that mistakenly pass a cache without enabling the flag.
        """
        cache = PaperQuantitiesCache(profile_residual_fn=_REAL_PROFILE_RESIDUAL)
        engine = Engine(paper_quantities_cache=cache)  # flag=False (default)
        assert engine.paper_quantities_cache is None  # cache IGNORED
        assert engine.consume_a_class_sites() == 0
        assert engine.consume_b_class_sites() == 0


# ---------------------------------------------------------------------------
# 3. Site count consistency — 16 = expected site set
# ---------------------------------------------------------------------------


class TestSitesCountConsistent:
    """Site-count consistency: A-class (8) + B-class (8) = 16 = all sites.

    Verifies that the union of A-class and B-class sites is exactly
    the 16-entry canonical set documented in
    ``PAPER_QUANTITIES_SITE_NAMES``.
    """

    def test_paper_quantities_site_names_has_sixteen(self) -> None:
        """``PAPER_QUANTITIES_SITE_NAMES`` has exactly 16 entries."""
        assert len(PAPER_QUANTITIES_SITE_NAMES) == 16

    def test_a_class_site_names_equals_eight(self) -> None:
        """A-class sites = 8 cache entries (per Wave 296 P3 spec)."""
        assert len(A_CLASS_SITES) == 8

    def test_b_class_site_names_equals_eight(self) -> None:
        """B-class sites = 8 cache entries (per Wave 296 P4 spec)."""
        assert len(B_CLASS_SITES) == 8

    def test_all_sixteen_sites_match_paper_quantities_site_names(self) -> None:
        """ALL_16_SITES = PAPER_QUANTITIES_SITE_NAMES (set equality)."""
        assert set(ALL_16_SITES) == set(PAPER_QUANTITIES_SITE_NAMES)

    def test_a_class_and_b_class_disjoint(self) -> None:
        """A-class and B-class sites are disjoint."""
        a_class = set(A_CLASS_SITES)
        b_class = set(B_CLASS_SITES)
        assert a_class.isdisjoint(b_class)

    def test_engine_consume_a_class_returns_eight(
        self,
        engine_with_flag: Engine,
        active_cache: PaperQuantitiesCache,
    ) -> None:
        """``engine.consume_a_class_sites()`` returns 8 (matches A-class size)."""
        activated = engine_with_flag.consume_a_class_sites()
        assert activated == 8
        # Verify exactly the A-class set was added.
        activated_set = set(active_cache.activated_sites)
        assert set(A_CLASS_SITES).issubset(activated_set)

    def test_engine_consume_b_class_returns_eight(
        self,
        engine_with_flag: Engine,
        active_cache: PaperQuantitiesCache,
    ) -> None:
        """``engine.consume_b_class_sites()`` returns 8 (matches B-class size)."""
        activated = engine_with_flag.consume_b_class_sites()
        assert activated == 8
        # Verify exactly the B-class set was added.
        activated_set = set(active_cache.activated_sites)
        assert set(B_CLASS_SITES).issubset(activated_set)

    def test_engine_a_class_and_b_class_combined_returns_sixteen(
        self,
        engine_with_flag: Engine,
        active_cache: PaperQuantitiesCache,
    ) -> None:
        """A-class + B-class helpers together → 16 sites in activation log."""
        a_count = engine_with_flag.consume_a_class_sites()
        b_count = engine_with_flag.consume_b_class_sites()
        assert a_count + b_count == 16
        # Verify the activation log contains exactly the 16-site set.
        activated = set(active_cache.activated_sites)
        assert activated == set(ALL_16_SITES)
        assert len(activated) == 16

    def test_engine_a_class_count_attribute_is_eight(self) -> None:
        """``Engine._A_CLASS_SITE_NAMES`` has 8 entries (canonical)."""
        assert len(Engine._A_CLASS_SITE_NAMES) == 8

    def test_engine_b_class_count_attribute_is_eight(self) -> None:
        """``Engine._B_CLASS_SITE_NAMES`` has 8 entries (canonical)."""
        assert len(Engine._B_CLASS_SITE_NAMES) == 8


# ---------------------------------------------------------------------------
# 4. Per-site enumeration — every site reachable
# ---------------------------------------------------------------------------


class TestPerSiteEnumeration:
    """Per-site enumeration — verify every site is individually reachable.

    Each test instantiates a fresh engine + active cache and verifies
    that the corresponding cache entry is consumed by the framework
    hook (A-class or B-class).
    """

    @pytest.mark.parametrize("site_name", A_CLASS_SITES)
    def test_a_class_site_is_consumed(
        self,
        engine_with_flag: Engine,
        active_cache: PaperQuantitiesCache,
        site_name: str,
    ) -> None:
        """Each of the 8 A-class sites is consumed by ``consume_a_class_sites``."""
        activated = engine_with_flag.consume_a_class_sites()
        assert site_name in set(active_cache.activated_sites)
        assert site_name in set(Engine._A_CLASS_SITE_NAMES)
        assert activated == 8

    @pytest.mark.parametrize("site_name", B_CLASS_SITES)
    def test_b_class_site_is_consumed(
        self,
        engine_with_flag: Engine,
        active_cache: PaperQuantitiesCache,
        site_name: str,
    ) -> None:
        """Each of the 8 B-class sites is consumed by ``consume_b_class_sites``."""
        activated = engine_with_flag.consume_b_class_sites()
        assert site_name in set(active_cache.activated_sites)
        assert site_name in set(Engine._B_CLASS_SITE_NAMES)
        assert activated == 8


# ---------------------------------------------------------------------------
# 5. Idempotency — repeated runs don't double-activate
# ---------------------------------------------------------------------------


class TestActivationIdempotency:
    """Activation log is idempotent: repeated runs don't double-activate.

    Verifies that ``cache.consume`` is idempotent across multiple
    runner.run() invocations AND across multiple direct helper
    invocations — the activation log is a SET semantics (insertion
    order + dedup).
    """

    def test_double_run_keeps_sixteen_sites(
        self,
        twodim_adapter: object,
        active_cache: PaperQuantitiesCache,
    ) -> None:
        """Two runner.run() calls keep 16 sites (no double-activation)."""
        from adaptive_reflow.algorithm.runner import (
            ReInferenceConfig,
            ReInferenceRunner,
        )

        engine = Engine(
            enable_full_jmaa_theory=True,
            paper_quantities_cache=active_cache,
        )
        runner = ReInferenceRunner(adapter=twodim_adapter, engine=engine)
        config = ReInferenceConfig(
            n_rounds=1,
            outer_cycle_id=0,
            target_round=0,
            seed=42,
            channels=("xy",),
        )
        # First run + A-class helper.
        runner.run(config)
        first_a = engine.consume_a_class_sites()
        # Second run + A-class helper (idempotent).
        runner.run(config)
        second_a = engine.consume_a_class_sites()

        assert first_a == 8
        assert second_a == 0  # idempotent: already consumed
        # Activation log still has exactly 16 distinct sites.
        assert len(active_cache.activated_sites) == 16
        assert set(active_cache.activated_sites) == set(ALL_16_SITES)

    def test_cache_clear_then_reactivate(
        self,
        engine_with_flag: Engine,
        active_cache: PaperQuantitiesCache,
    ) -> None:
        """``cache.clear()`` resets the activation log; re-activation is fresh."""
        # First activation: 16 sites.
        engine_with_flag.consume_a_class_sites()
        engine_with_flag.consume_b_class_sites()
        assert len(active_cache.activated_sites) == 16

        # Clear the activation log.
        active_cache.clear()
        assert active_cache.activated_sites == ()

        # Re-activation: 16 sites again.
        a_count = engine_with_flag.consume_a_class_sites()
        b_count = engine_with_flag.consume_b_class_sites()
        assert a_count == 8
        assert b_count == 8
        assert len(active_cache.activated_sites) == 16


# ---------------------------------------------------------------------------
# 6. Cache stats — observability contract
# ---------------------------------------------------------------------------


class TestCacheStatsObservability:
    """Cache stats() returns the audit-doc snapshot.

    Verifies the dict shape returned by :meth:`PaperQuantitiesCache.stats`
    matches the audit-doc snapshot from
    ``docs/audit/wave296-p4-b-class-wired.md`` §7.
    """

    def test_stats_dormant_cache(self, dormant_cache: PaperQuantitiesCache) -> None:
        """Dormant cache: is_active=0, activated_count=0, no quantities computed."""
        stats = dormant_cache.stats()
        assert stats == {
            "is_active": 0,
            "activated_count": 0,
            "sheet_A_computed": 0,
            "packing_B_computed": 0,
            "cell_C_computed": 0,
            "e_rho_computed": 0,
        }

    def test_stats_active_cache_no_consume(
        self, active_cache: PaperQuantitiesCache
    ) -> None:
        """Active cache, no consume() → all 4 quantities computed on touch."""
        # Touch each property to materialise the lazy-memo slot.
        _ = active_cache.sheet_A
        _ = active_cache.packing_B
        _ = active_cache.cell_C
        _ = active_cache.e_rho
        stats = active_cache.stats()
        assert stats["is_active"] == 1
        assert stats["activated_count"] == 0  # no consume() calls yet
        assert stats["sheet_A_computed"] == 1
        assert stats["packing_B_computed"] == 1
        assert stats["cell_C_computed"] == 1
        assert stats["e_rho_computed"] == 1

    def test_stats_active_cache_with_full_consume(
        self,
        engine_with_flag: Engine,
        active_cache: PaperQuantitiesCache,
    ) -> None:
        """Active cache + full consume → activated_count=16, all 4 quantities."""
        engine_with_flag.consume_a_class_sites()
        engine_with_flag.consume_b_class_sites()
        stats = active_cache.stats()
        assert stats == {
            "is_active": 1,
            "activated_count": 16,
            "sheet_A_computed": 1,
            "packing_B_computed": 1,
            "cell_C_computed": 1,
            "e_rho_computed": 1,
        }
