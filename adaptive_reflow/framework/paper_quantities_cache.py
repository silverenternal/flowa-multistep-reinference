"""Lazy-memoized cache for the four JMAA Theorem 1 paper quantities (Wave 296 P2).

This module declares :class:`PaperQuantitiesCache`, a typed cache carrier
that activates the 15 dormant JMAA application sites inventoried in
``docs/audit/wave292-p1-pipeline-inventory.md`` when supplied to the
:mod:`adaptive_reflow.frame.engine.Engine` via the
``enable_full_jmaa_theory=True`` opt-in flag.

**Why this module exists**

Per the Wave 292 P1 inventory, **15 of 16 JMAA application sites are
dormant under the cosine-baseline deployment** (e.g. Site 6
``BoundedMergeOperator(exterior_gap_e_rho=...)`` is constructed with
``exterior_gap_e_rho=None``; Site 9 ``InceptionV3TheoremAlignedFIDEvaluator``
is never instantiated). The fix is the single opt-in flag plus this
typed cache that, when supplied, threads the four paper quantities
``A_g, B_g, C_g, e_rho`` through every dormant site while keeping the
cosine-baseline byte-stable for callers that opt out.

**Activation semantics**

* :attr:`is_active` is ``True`` iff ``profile_residual_fn is not None``.
  When ``False`` the cache is a **dormant carrier**: every property
  returns ``None`` and every :meth:`get` site returns ``None``. The
  activation log (:meth:`consume`) is a no-op.
* When :attr:`is_active` is ``True`` the four paper quantities are
  computed lazily on first access via :func:`_LazyMemo.get`. Two reads
  after the first evaluation return the same float object (byte-stable).

**Backward compatibility**

The cache is stdlib-only (no torch, no numpy, no IO); it imports only
from :mod:`adaptive_reflow.theory.paper_quantities` and
:mod:`adaptive_reflow.contracts.dynamic_noise_bias`. The default
constructor (``PaperQuantitiesCache()``) constructs a dormant cache
(``is_active = False``) at zero math cost — one bool + four ``None``
slots + the ``profile_residual_fn`` slot. Existing Engine callers
that do NOT pass ``enable_full_jmaa_theory=True`` see byte-identical
behaviour.

**Site-aware dispatch (:meth:`get`)**

The cache returns the canonical value each of the 15 dormant sites
consumes:

==========================  ===========================================
``"solver_hint"``           :attr:`e_rho` (Site 2)
``"dt_floor"``              :attr:`e_rho` (Site 4)
``"alpha_floor"``           :attr:`e_rho` (Site 4b)
``"merge_floor"``           :attr:`e_rho` (Sites 6, 6b)
``"policy_C"``              :attr:`cell_C` (Site 7)
``"noise_bias"``            ``(sheet_A, packing_B, cell_C, e_rho)`` tuple (Site 5)
``"mfpqa"``                 :class:`PaperQuantitiesSnapshot` (Site 3)
``"evidence"``              :class:`PaperQuantitiesSnapshot` (Site 8)
``"fid"``                  :class:`PaperQuantitiesSnapshot` (Site 9)
``"lipschitz"``            :class:`PaperQuantitiesSnapshot` (Site 10)
``"evaluator"``             ``(sheet_A, cell_C)`` (Site 11/14)
``"checker"``               :class:`PaperQuantitiesSnapshot` (Site 12)
``"profile"``               :attr:`profile_residual_fn` (Site 13)
``"regime"``                :attr:`e_rho` (Site 15)
``"derivation"``            :attr:`e_rho` (Site 16)
==========================  ===========================================

Unknown site names raise :class:`ValueError`. When the cache is dormant
(:attr:`is_active` is ``False``), every ``get`` returns ``None`` (no
exception).

**Byte-stability**

The cache is pure-functional. Two caches constructed from the same
``profile_residual_fn`` and F-side constants ``(rho, c, d, eta)`` return
bit-identical floats across processes. The :class:`PaperQuantitiesSnapshot`
constructed inside :meth:`get` is the frozen carrier declared in
:mod:`adaptive_reflow.contracts.dynamic_noise_bias`.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from adaptive_reflow.contracts.dynamic_noise_bias import PaperQuantitiesSnapshot
from adaptive_reflow.theory.paper_quantities import (
    exterior_gap_e_rho,
    per_cell_coefficient_C,
    root_cell_packing_B,
    sheet_evidence_A,
)

__all__ = [
    "PaperQuantitiesCache",
    "PAPER_QUANTITIES_CACHE_DEFAULT_ETA",
    "PAPER_QUANTITIES_CACHE_DEFAULT_RHO",
    "PAPER_QUANTITIES_CACHE_DEFAULT_C",
    "PAPER_QUANTITIES_CACHE_DEFAULT_D",
    "PAPER_QUANTITIES_SITE_NAMES",
]

# Module-level F-side defaults (Wave 296 P2 invariant; byte-stable).
# Mirrors the cosine-baseline ``enable_paper_uplift_27`` defaults from
# ``docs/audit/wave292-p1-pipeline-inventory.md`` §0 so the cache, when
# activated with a profile_residual_fn, reproduces the legacy numerical
# constants byte-identically.
PAPER_QUANTITIES_CACHE_DEFAULT_RHO: float = 0.1
PAPER_QUANTITIES_CACHE_DEFAULT_C: float = 1.0
PAPER_QUANTITIES_CACHE_DEFAULT_D: float = 1.0
PAPER_QUANTITIES_CACHE_DEFAULT_ETA: float = 0.1

# Sentinel site names documented in the module docstring. Sites that
# return the four-tuple ``(sheet_A, packing_B, cell_C, e_rho)`` are
# noise-bias consumers; sites that return the ``(sheet_A, cell_C)``
# tuple are posterior-selection evaluator consumers.
PAPER_QUANTITIES_SITE_NAMES: frozenset[str] = frozenset(
    {
        "solver_hint",
        "dt_floor",
        "alpha_floor",
        "merge_floor",
        "policy_C",
        "noise_bias",
        "mfpqa",
        "evidence",
        "fid",
        "lipschitz",
        "evaluator",
        "checker",
        "sheet_cell",
        "profile",
        "regime",
        "derivation",
    }
)


# ---------------------------------------------------------------------------
# LazyMemoCachedEvaluationCost — internal helper for first-access memoization.
# ---------------------------------------------------------------------------


class _LazyMemoCachedEvaluationCost:
    """Per-quantity lazy-memo slot.

    Implements the canonical ``_LazyMemoCachedEvaluationCost`` pattern:
    stores a sentinel ``_NOT_COMPUTED`` constant and lazily evaluates
    the producer callable on first read. Two reads after the first
    evaluation return the same float object.

    The class name mirrors the Wave 296 P1 audit doc
    (``docs/audit/wave296-p1-architecture.md`` §1.6) which documents
    the canonical pattern. The slot holds a single float value; the
    producer callable is set once at construction and never mutated.

    Attributes
    ----------
    _value
        The cached float, or the ``_NOT_COMPUTED`` sentinel until
        first access.
    _producer
        The zero-arg callable that materialises the value on first
        access. Set once at construction; never mutated.
    """

    # Module-private sentinel — equality holds only by identity so two
    # slots that have not been computed yet are distinguishable from
    # any legitimate float (incl. ``0.0``, ``None``, and ``False``).
    _NOT_COMPUTED: object = object()

    __slots__ = ("_value", "_producer")

    def __init__(self, producer: Callable[[], float]) -> None:
        self._value: Any = self._NOT_COMPUTED
        self._producer: Callable[[], float] | None = producer

    def get(self) -> float:
        """Return the lazily-computed value (computed once).

        The first call invokes ``self._producer()``, stores its float
        return in ``self._value``, and returns the float. Subsequent
        calls return the same float object.
        """
        if self._value is self._NOT_COMPUTED:
            assert self._producer is not None
            self._value = float(self._producer())
        return self._value

    def is_computed(self) -> bool:
        """Return ``True`` iff the value has been computed at least once."""
        return self._value is not self._NOT_COMPUTED


# ---------------------------------------------------------------------------
# PaperQuantitiesCache
# ---------------------------------------------------------------------------


class PaperQuantitiesCache:
    """Lazy-memoized cache for the four JMAA Theorem 1 quantities.

    Stores :math:`A_g` (sheet evidence, Proposition 3 / line 161),
    :math:`B_g` (root-cell packing, Lemma 5 / line 159), :math:`C_g`
    (per-cell coefficient, Lemma 3 / line 191), and :math:`e_rho`
    (exterior gap, Lemma 5 / line 128) computed from a single
    ``profile_residual_fn`` callable. When ``profile_residual_fn is
    None`` the cache is a **dormant carrier** (:attr:`is_active` =
    ``False``); every property returns ``None`` and every
    :meth:`get` returns the site-specific sentinel.

    Parameters
    ----------
    profile_residual_fn
        Optional callable mapping a real ``x`` to ``g(x)``. When
        ``None`` (the default), the cache is dormant and every
        accessor returns ``None``. When supplied, the cache is active
        and the four paper quantities are computed lazily on first
        access.
    rho
        F-side ``rho`` parameter (paper line 128). Default
        ``0.1`` matches the cosine-baseline
        ``enable_paper_uplift_27`` default.
    c
        F-side ``simplicity_c`` parameter (paper line 117). Default
        ``1.0`` matches the legacy CIFAR baseline.
    d
        F-side ``separation_d`` parameter (paper line 124). Default
        ``1.0``.
    eta
        F-side ``eta`` parameter (paper line 128). Default ``0.1``
        matches the CIFAR baseline.

    Notes
    -----
    **Byte-stability.** The cache is pure-functional: the four quantities
    are computed exactly once at first access, the result is stored,
    and subsequent accessors return the same float object. Two caches
    constructed from the same profile return bit-identical floats
    across processes.

    **Activation semantics.** :attr:`is_active` is ``True`` iff
    ``profile_residual_fn is not None``. Sites that consume the cache
    MUST check :attr:`is_active` before reading any property; an
    inactive cache returns ``None`` for every property access and
    :meth:`consume` is a no-op.
    """

    __slots__ = (
        "_profile_residual_fn",
        "_rho",
        "_c",
        "_d",
        "_eta",
        "_sheet_A_memo",
        "_packing_B_memo",
        "_cell_C_memo",
        "_e_rho_memo",
        "_activated_sites",
    )

    def __init__(
        self,
        *,
        profile_residual_fn: Callable[[float], float] | None = None,
        rho: float = PAPER_QUANTITIES_CACHE_DEFAULT_RHO,
        c: float = PAPER_QUANTITIES_CACHE_DEFAULT_C,
        d: float = PAPER_QUANTITIES_CACHE_DEFAULT_D,
        eta: float = PAPER_QUANTITIES_CACHE_DEFAULT_ETA,
    ) -> None:
        if profile_residual_fn is not None and not callable(profile_residual_fn):
            raise TypeError(
                "profile_residual_fn must be callable or None, "
                f"got {profile_residual_fn!r}"
            )
        if rho <= 0.0 or rho >= 1.0:
            raise ValueError(f"rho must be in (0, 1), got {rho!r}")
        if c <= 0.0:
            raise ValueError(f"c must be positive, got {c!r}")
        if d <= 0.0:
            raise ValueError(f"d must be positive, got {d!r}")
        if eta <= 0.0:
            raise ValueError(f"eta must be positive, got {eta!r}")
        self._profile_residual_fn: Callable[[float], float] | None = (
            profile_residual_fn
        )
        self._rho: float = float(rho)
        self._c: float = float(c)
        self._d: float = float(d)
        self._eta: float = float(eta)

        # Lazy-memo slots. The producers close over ``profile_residual_fn``;
        # when the cache is dormant (profile is None) the slots stay
        # in the _NOT_COMPUTED state forever (no producer invocation).
        if profile_residual_fn is not None:
            self._sheet_A_memo: _LazyMemoCachedEvaluationCost = (
                _LazyMemoCachedEvaluationCost(
                    lambda: sheet_evidence_A(profile_residual_fn)
                )
            )
            self._packing_B_memo: _LazyMemoCachedEvaluationCost = (
                _LazyMemoCachedEvaluationCost(
                    lambda: root_cell_packing_B(
                        profile_residual_fn, separation_d=self._d
                    )
                )
            )
        else:
            # Dormant slots — no producer; get() would assert-fail but
            # the property accessors short-circuit on is_active first.
            self._sheet_A_memo = _LazyMemoCachedEvaluationCost(
                lambda: 0.0  # unreachable; is_active guard returns None
            )
            self._packing_B_memo = _LazyMemoCachedEvaluationCost(
                lambda: 0.0  # unreachable; is_active guard returns None
            )
        # cell_C and e_rho are F-side-only (do NOT consume profile).
        self._cell_C_memo: _LazyMemoCachedEvaluationCost = (
            _LazyMemoCachedEvaluationCost(
                lambda: per_cell_coefficient_C(rho=self._rho, c=self._c)
            )
        )
        self._e_rho_memo: _LazyMemoCachedEvaluationCost = (
            _LazyMemoCachedEvaluationCost(
                lambda: exterior_gap_e_rho(rho=self._rho, eta=self._eta)
            )
        )

        # Activation log. Stores site names as strings in insertion
        # order; callers (Engine + adapters) append via consume().
        self._activated_sites: list[str] = []

    # ------------------------------------------------------------------
    # Activation flag + F-side parameters (read-only properties)
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """Return ``True`` iff ``profile_residual_fn is not None``.

        Sites that consume the cache MUST check this property before
        reading any paper quantity; when ``False``, every property
        returns ``None`` and :meth:`get` returns ``None``.
        """
        return self._profile_residual_fn is not None

    @property
    def profile_residual_fn(self) -> Callable[[float], float] | None:
        """Return the cached ``profile_residual_fn`` (or ``None``)."""
        return self._profile_residual_fn

    @property
    def rho(self) -> float:
        """Return the configured F-side ``rho`` parameter."""
        return self._rho

    @property
    def c(self) -> float:
        """Return the configured F-side ``c`` parameter."""
        return self._c

    @property
    def d(self) -> float:
        """Return the configured F-side ``d`` parameter."""
        return self._d

    @property
    def eta(self) -> float:
        """Return the configured F-side ``eta`` parameter."""
        return self._eta

    # ------------------------------------------------------------------
    # The four paper quantities (lazy-memoized)
    # ------------------------------------------------------------------

    @property
    def sheet_A(self) -> float | None:
        """Return cached :math:`A_g` (paper Proposition 3, line 161).

        Returns ``None`` when :attr:`is_active` is ``False``. Computed
        lazily on first access via
        :func:`adaptive_reflow.theory.paper_quantities.sheet_evidence_A`
        on the cached ``profile_residual_fn``.
        """
        if not self.is_active:
            return None
        return float(self._sheet_A_memo.get())

    @property
    def packing_B(self) -> float | None:
        """Return cached :math:`B_g` (paper Lemma 5, line 159).

        Returns ``None`` when :attr:`is_active` is ``False``. Computed
        lazily on first access via
        :func:`adaptive_reflow.theory.paper_quantities.root_cell_packing_B`
        on the cached ``profile_residual_fn``, with the cached
        :attr:`d` as the separation-diameter.
        """
        if not self.is_active:
            return None
        return float(self._packing_B_memo.get())

    @property
    def cell_C(self) -> float | None:
        """Return cached :math:`C_g` (paper Lemma 3, line 191).

        Returns ``None`` when :attr:`is_active` is ``False``. Computed
        lazily on first access via
        :func:`adaptive_reflow.theory.paper_quantities.per_cell_coefficient_C`
        with the cached F-side :attr:`rho` and :attr:`c`. Independent
        of ``profile_residual_fn``.
        """
        if not self.is_active:
            return None
        return float(self._cell_C_memo.get())

    @property
    def e_rho(self) -> float | None:
        """Return cached :math:`e_rho` (paper Lemma 5, line 128).

        Returns ``None`` when :attr:`is_active` is ``False``. Computed
        lazily on first access via
        :func:`adaptive_reflow.theory.paper_quantities.exterior_gap_e_rho`
        with the cached F-side :attr:`rho` and :attr:`eta`. Independent
        of ``profile_residual_fn``.
        """
        if not self.is_active:
            return None
        return float(self._e_rho_memo.get())

    # ------------------------------------------------------------------
    # Site-aware dispatch
    # ------------------------------------------------------------------

    def get(self, site_name: str) -> Any:
        """Return the cache value appropriate for ``site_name``.

        Site-aware dispatch — returns the canonical value each of the
        15 dormant sites consumes:

        * ``"solver_hint"``, ``"dt_floor"``, ``"alpha_floor"``,
          ``"merge_floor"``, ``"regime"``, ``"derivation"`` →
          :attr:`e_rho`.
        * ``"policy_C"`` → :attr:`cell_C`.
        * ``"noise_bias"`` → ``(sheet_A, packing_B, cell_C, e_rho)``
          tuple (Site 5).
        * ``"mfpqa"``, ``"evidence"``, ``"fid"``, ``"lipschitz"``,
          ``"checker"`` → :class:`PaperQuantitiesSnapshot`.
        * ``"evaluator"`` → ``(sheet_A, cell_C)`` tuple (Site 11/14).
        * ``"profile"`` → :attr:`profile_residual_fn` (Site 13, the
          cache-activation trigger).

        Returns ``None`` when :attr:`is_active` is ``False``. Unknown
        site names raise :class:`ValueError`.
        """
        if site_name not in PAPER_QUANTITIES_SITE_NAMES:
            raise ValueError(
                f"unknown paper-quantities site: {site_name!r}; "
                f"expected one of {sorted(PAPER_QUANTITIES_SITE_NAMES)}"
            )
        if not self.is_active:
            return None
        if site_name in ("solver_hint", "dt_floor", "alpha_floor",
                         "merge_floor", "regime", "derivation"):
            return self.e_rho
        if site_name == "policy_C":
            return self.cell_C
        if site_name == "noise_bias":
            return (self.sheet_A, self.packing_B, self.cell_C, self.e_rho)
        if site_name == "evaluator":
            return (self.sheet_A, self.cell_C)
        if site_name == "sheet_cell":
            # Wave 296 P4 — the sheet-vs-cell heuristic site. Same
            # value as ``"evaluator"`` but a distinct cache name so the
            # :class:`Engine` activation log records both B-class sites
            # separately. The two names collapse to one cache dispatch
            # by design; they are two distinct *sites* in the B-class
            # inventory (one is the framework's
            # :class:`PosteriorSelectionEvaluator`, the other is the
            # module-level ``sheet_evidence`` / ``cell_evidence``
            # heuristic helpers in
            # ``adaptive_reflow.eval.posterior_selection_evaluator``).
            return (self.sheet_A, self.cell_C)
        if site_name == "profile":
            return self.profile_residual_fn
        # "mfpqa", "evidence", "fid", "lipschitz", "checker" → snapshot
        return PaperQuantitiesSnapshot(
            sheet_A=float(self.sheet_A),
            packing_B=float(self.packing_B),
            cell_C=float(self.cell_C),
            exterior_gap_e_rho=float(self.e_rho),
        )

    # ------------------------------------------------------------------
    # Activation log (idempotent; observable via activated_sites)
    # ------------------------------------------------------------------

    @property
    def activated_sites(self) -> tuple[str, ...]:
        """Return the immutable tuple of activated site names.

        Order is insertion order. A site is added to the tuple at most
        once even if :meth:`consume` is called multiple times for the
        same name. When :attr:`is_active` is ``False`` the tuple is
        always empty.
        """
        return tuple(self._activated_sites)

    def consume(self, site_name: str) -> bool:
        """Mark ``site_name`` as activated; return whether it was first-time.

        Idempotent: a second call with the same ``site_name`` returns
        ``False``. The activation log is observable via
        :attr:`activated_sites`. Callers (Engine and adapter sites)
        use this to populate ``RoundTrace.audit_codes`` and
        ``LedgerRow.audit_codes`` with per-site activation codes.

        Returns ``False`` (no-op) when :attr:`is_active` is ``False``.
        Returns ``False`` for an unknown site name (without raising —
        audit sites should never break the data path).
        """
        if not self.is_active:
            return False
        if site_name not in PAPER_QUANTITIES_SITE_NAMES:
            return False
        if site_name in self._activated_sites:
            return False
        self._activated_sites.append(site_name)
        return True

    # ------------------------------------------------------------------
    # Stats + clear
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, int]:
        """Return activation-log + quantity-computed counters (audit-doc snapshot).

        Keys:

        * ``"is_active"`` — ``int(self.is_active)`` (0 or 1).
        * ``"activated_count"`` — number of distinct sites that have
          called :meth:`consume` at least once.
        * ``"sheet_A_computed"``, ``"packing_B_computed"``,
          ``"cell_C_computed"``, ``"e_rho_computed"`` — whether the
          four lazy-memo slots have been computed at least once.
        """
        return {
            "is_active": int(self.is_active),
            "activated_count": len(self._activated_sites),
            "sheet_A_computed": int(self._sheet_A_memo.is_computed()),
            "packing_B_computed": int(self._packing_B_memo.is_computed()),
            "cell_C_computed": int(self._cell_C_memo.is_computed()),
            "e_rho_computed": int(self._e_rho_memo.is_computed()),
        }

    def clear(self) -> None:
        """Reset the activation log (does not drop the cached quantities).

        Used between runs to isolate audit counters. The four
        lazy-memo slots are NOT invalidated — a cache that has
        computed :math:`A_g` retains the value across ``clear()`` calls.
        """
        self._activated_sites.clear()
