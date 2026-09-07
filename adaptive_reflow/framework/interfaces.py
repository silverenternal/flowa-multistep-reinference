"""Protocol surfaces for the JMAA theory-driven refactor (Wave 11).

This module declares the abstract Protocol interfaces that adapters and
algorithm layer implementations conform to. Each interface is a
``typing.Protocol`` (structural typing, not nominal inheritance), so
adapter classes satisfy conformance via :func:`assert_adapter_compliance`
without needing a base class.

**Conformance decorator:**

Adapters should declare their conformance set via the
:func:`implements` class decorator:

    >>> from adaptive_reflow.framework.interfaces import (
    ...     ChannelwiseBlender, IntegratorProtocol, implements,
    ... )
    >>> @implements(ChannelwiseBlender, IntegratorProtocol)
    ... class MyAdapter:
    ...     ...

The decorator stores the Protocol set on the class as
``__protocols__``; :func:`assert_adapter_compliance(adapter_cls)`
verifies the structural typing at import time.

**Paper-grounded interfaces:**

* :class:`ChannelwiseBlender` -- per-channel blend of prior and fresh
  state (continuous + discrete). Default impl = CategoricalAwareBlender.
* :class:`ChannelwiseMemoryFractionPolicy` -- per-channel
  ``memory_fraction = 1 - beta`` from a beta envelope + paper-quantity
  context.
* :class:`IntegratorProtocol` -- ODE integrator selection (Heun, RK4,
  DormandPrince, etc.). Replaces hand-coded Heun/RK4 helpers.
* :class:`NoiseInjectionProtocol` -- inject forward noise per channel
  using paper-quantity ``e_rho`` and ``sheet_A``.
* :class:`MergeOperatorProtocol` -- merge two cells while respecting
  ``PhysicalComplement`` and Lemma 4 ``|F_g|^2 >= e_rho``.
* :class:`SheetSchedulerProtocol` -- sheet sampling and noise injection
  scheduling per paper Proposition 3.
* :class:`SelectionRatioWitness` -- paper-grounded selection ratio
  ``sheet_A * eps / (sheet_A * eps + cell_C * packing_B * eps^2)``.
* :class:`Theorem1Statement` -- unified Theorem 1 dataclass carrying
  all three claims (``bl_distance``, ``root_cell_mass``,
  ``posterior_evidence``) together.
* :func:`emit_theorem1_statement` -- single canonical emitter that
  returns a fully populated :class:`Theorem1Statement`.
* :class:`Theorem1StatementChecker` -- unified Theorem 1 statement.
* :class:`PosteriorEvaluator` -- planar BL distance on ``R^2``.
* :class:`AdapterObservationProtocol` -- single typed observation
  surface every adapter satisfies (Wave 68). Returns a tuple of
  :class:`ObservationResult` keyed by model-agnostic
  :class:`ObservationKind` tags (NOT by per-model channel names).
* :class:`FlowMatchingODEAdapterWithObservation` -- Wave 54 Phase 2
  fix surface that makes a v1 (hash stub) FlowMol3 adapter and a v2
  (real integration) FlowMol3 adapter both first-class via a single
  structural Protocol (see :class:`AdapterObservationProtocol` for the
  underlying typed ``observe(...)`` method).
* :class:`AdapterCompliance` -- aggregate Protocol set enforcement.

**Stdlib-only, no torch, no numpy.**
"""
from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from adaptive_reflow.framework._compliance import (
    MissingProtocolError,
    implements,
)
from adaptive_reflow.theory.checkers import (
    Theorem1Statement,
    theorem1_bl_convergence_witness,
)
from adaptive_reflow.theory.paper_quantities import (
    PhysicalComplement,
    exterior_gap_e_rho,
    paper_selection_ratio,
    per_cell_coefficient_C,
    root_cell_packing_B,
    sheet_evidence_A,
)

__all__ = [
    "ChannelwiseBlender",
    "ChannelwiseMemoryFractionPolicy",
    "IntegratorProtocol",
    "NoiseInjectionProtocol",
    "MergeOperatorProtocol",
    "SheetSchedulerProtocol",
    "SelectionRatioWitness",
    "Theorem1Statement",
    "emit_theorem1_statement",
    "Theorem1StatementChecker",
    "PosteriorEvaluator",
    "AdapterObservationProtocol",
    "ObservationKind",
    "ObservationResult",
    "FlowMatchingODEAdapterWithObservation",
    "AdapterCompliance",
    "implements",
    "assert_adapter_compliance",
    "MissingProtocolError",
]


# ---------------------------------------------------------------------------
# ChannelwiseBlender
# ---------------------------------------------------------------------------


@runtime_checkable
class ChannelwiseBlender(Protocol):
    """Per-channel blend of prior and fresh state (continuous + discrete)."""

    def blend(
        self,
        prior_state: Any,
        fresh_state: Any,
        memory_fraction: Mapping[str, float],
        mask: Any | None = ...,
    ) -> Any:
        """Blend prior and fresh per channel under ``memory_fraction``."""
        ...

    def blend_family(self) -> str:
        """Return provenance string for ``config_hash`` audit trail."""
        ...


# ---------------------------------------------------------------------------
# ChannelwiseMemoryFractionPolicy
# ---------------------------------------------------------------------------


@runtime_checkable
class ChannelwiseMemoryFractionPolicy(Protocol):
    """Compute per-channel ``memory_fraction = 1 - beta`` from beta envelope."""

    def memory_fraction_for(
        self, policy: Any, channel: str
    ) -> float:
        """Return ``memory_fraction`` for ``channel`` under ``policy``."""
        ...

    def channels(self) -> tuple[str, ...]:
        """Return the channel names this policy handles."""
        ...


# ---------------------------------------------------------------------------
# IntegratorProtocol
# ---------------------------------------------------------------------------


@runtime_checkable
class IntegratorProtocol(Protocol):
    """ODE integrator selection (Heun, Euler, RK4, DormandPrince, ...)."""

    def step(
        self,
        x: Any,
        t: float,
        dt: float,
        score_fn: Callable[[Any, float], Any],
    ) -> Any:
        """Advance ``x`` by one integrator step of size ``dt`` at time ``t``."""
        ...

    def name(self) -> str:
        """Return the integrator name (``'heun'``, ``'euler'``, ...)."""
        ...


# ---------------------------------------------------------------------------
# NoiseInjectionProtocol
# ---------------------------------------------------------------------------


@runtime_checkable
class NoiseInjectionProtocol(Protocol):
    """Inject forward noise per channel using paper-quantity ``e_rho`` and ``sheet_A``."""

    def inject(
        self,
        channel: str,
        state: Any,
        paper_qty: Any,
    ) -> Any:
        """Inject forward noise into ``state`` for ``channel``."""
        ...

    def exterior_gap_floor_enabled(self) -> bool:
        """Return whether the ``e_rho/4`` envelope floor is engaged (default True)."""
        ...


# ---------------------------------------------------------------------------
# MergeOperatorProtocol
# ---------------------------------------------------------------------------


@runtime_checkable
class MergeOperatorProtocol(Protocol):
    """Merge two cells while respecting ``PhysicalComplement`` and Lemma 4 ``|F_g|^2 >= e_rho``."""

    def merge(
        self,
        left: Any,
        right: Any,
        complement: PhysicalComplement,
    ) -> Any:
        """Merge ``left`` and ``right`` under ``complement``."""
        ...

    def lemma4_floor_value(self, complement: PhysicalComplement) -> float:
        """Return the paper-derived ``e_rho`` floor (NOT the heuristic ``e_rho/4``)."""
        ...


# ---------------------------------------------------------------------------
# SheetSchedulerProtocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SheetSchedulerProtocol(Protocol):
    """Sheet sampling and noise injection scheduling per Proposition 3."""

    def sheet_density(self, g: Callable[[float], float], s: float) -> float:
        """Return the sheet density at ``s`` (paper ``q_g(s) / Q_g`` form)."""
        ...

    def inject_noise(
        self,
        state: Any,
        sheet_density: float,
        eps: float,
    ) -> Any:
        """Inject sheet-noise into ``state`` at scale ``eps``."""
        ...


# ---------------------------------------------------------------------------
# SelectionRatioWitness
# ---------------------------------------------------------------------------


@runtime_checkable
class SelectionRatioWitness(Protocol):
    """Paper-grounded selection ratio witness."""

    def paper_selection_ratio(
        self,
        sheet_A: float,
        packing_B: float,
        cell_C: float,
        eps: float,
    ) -> float:
        """Return ``sheet_A * eps / (sheet_A * eps + cell_C * packing_B * eps^2)``."""
        ...

    def heuristic_selection_ratio(
        self,
        mu: float,
        sigma: float,
        eps: float,
    ) -> float:
        """Deprecated heuristic; retained for byte-stable legacy callers."""
        ...


# ---------------------------------------------------------------------------
# Theorem1Statement + emit_theorem1_statement
# ---------------------------------------------------------------------------


def emit_theorem1_statement(
    g: Callable[[float], float],
    eps: float,
    d: float,
    c: float,
    rho: float,
    eta: float,
    *,
    n_samples: int = 1024,
    seed: int = 0,
) -> Theorem1Statement:
    """Emit the unified Theorem 1 statement combining all three claims.

    Paper Theorem 1 (line 87-92) is a SINGLE statement that combines:

    (a) BL convergence ``mu_{g,eps} --BL--> nu_g`` (line 87-89).
    (b) root-cell mass ``mu_{g,eps}(\\bigcup_z I_z) = O(eps)`` (line 90).
    (c) the bounded-Lipschitz equivalence display (line 91-92).

    Closes the A1-high-1 audit finding: the framework previously realised
    (a) only as the FID surrogate in ``eval.fid_theorem_aligned`` and
    (b)+(c) only through ``Theorem1DynamicNoiseBias.compute_noise_bias``,
    with no single module emitting a ``Theorem1Statement`` carrying all
    three claims together. This function is the canonical emitter.

    Parameters
    ----------
    g
        The profile ``R -> R``. Need not be uniformly separated (the
        caller is responsible for F-side admissibility via
        :mod:`adaptive_reflow.theory.validation`).
    eps
        The noise scale at which the three claims are evaluated. Must
        be positive.
    d
        Separation constant (Lemma 5: ``rho < d/4`` requirement).
    c
        Simplicity constant (Lemma 3: ``a = (1-rho)^2 * min(c^2, 1)``).
    rho
        Cell half-width; must lie in ``(0, 1)``.
    eta
        Physical complement constant (Lemma 5 ``e_rho = min{rho^4,
        (1-rho)^2 eta^2}``); must be positive.
    n_samples
        Monte-Carlo sample count for the BL-distance witness. Default
        ``1024``; minimum ``32`` (enforced by the witness).
    seed
        Random seed for the BL witness; controls byte-stability.

    Returns
    -------
    Theorem1Statement
        Immutable dataclass carrying all three claims populated:

        * ``bl_distance`` -- the BL convergence witness at the
          supplied ``eps`` (claim (a)).
        * ``root_cell_mass`` -- ``paper_selection_ratio(sheet_A,
          packing_B, cell_C, eps)``, the per-round sheet-dominance
          mass (claim (b) reduced to the paper formula).
        * ``posterior_evidence`` -- ``sheet_evidence_A(g) = A_g``,
          the sheet evidence floor from Proposition 3 / line 161
          (the LHS of claim (c)).

    Raises
    ------
    ValueError
        If ``eps <= 0``, ``rho not in (0, 1)``, ``eta <= 0``, ``d <= 0``
        or ``c <= 0``.

    Stdlib-only.
    """
    if eps <= 0.0:
        raise ValueError(f"eps must be positive, got {eps!r}")
    if d <= 0.0:
        raise ValueError(f"d must be positive, got {d!r}")
    if c <= 0.0:
        raise ValueError(f"c must be positive, got {c!r}")
    if rho <= 0.0 or rho >= 1.0:
        raise ValueError(f"rho must be in (0, 1), got {rho!r}")
    if eta <= 0.0:
        raise ValueError(f"eta must be positive, got {eta!r}")

    # Compute the four paper quantities from the F-side parameters.
    sheet_A = sheet_evidence_A(g)
    packing_B = root_cell_packing_B(g, separation_d=d)
    cell_C = per_cell_coefficient_C(rho=rho, c=c)
    # exterior_gap_e_rho is computed for the audit trail but is NOT one
    # of the three Theorem-1 claims (it appears in Lemma 4 only).
    _exterior = exterior_gap_e_rho(rho=rho, eta=eta)

    # (a) BL distance: run the planar witness over an eps-bracketed
    # sequence and return the value at the supplied eps. The 2x upper
    # bracket exists so the witness has two points for monotonicity
    # (the audit's monotone sanity flag).
    eps_hi = float(eps) * 2.0
    eps_lo = float(eps)
    eps_sequence: tuple[float, ...] = (eps_hi, eps_lo)
    report = theorem1_bl_convergence_witness(
        g, eps_sequence, n_samples=n_samples, seed=seed
    )
    bl_distance = float(report.bl_distance_at_eps_min)

    # (b) Root-cell mass at the supplied eps. The paper formula
    # ``sheet_A * eps / (sheet_A * eps + cell_C * packing_B * eps^2)``
    # is the per-round sheet-dominance mass from Corollary 1, line 165.
    # It converges to 1 as ``eps -> 0`` (selection dominates) and to 0
    # as ``eps -> infty`` (cells dominate).
    root_cell_mass = float(
        paper_selection_ratio(sheet_A, packing_B, cell_C, eps)
    )

    # (c) Posterior evidence: ``A_g`` from Proposition 3 / line 161.
    # This is the limiting ``eps^{-1} int_T p_eps`` value that pins the
    # normalization of the selected sheet, and is the LHS of the
    # bounded-Lipschitz equivalence display (line 91-92).
    posterior_evidence = float(sheet_A)

    return Theorem1Statement.from_parts(
        bl_distance=bl_distance,
        root_cell_mass=root_cell_mass,
        posterior_evidence=posterior_evidence,
    )


# ---------------------------------------------------------------------------
# Theorem1StatementChecker
# ---------------------------------------------------------------------------


@runtime_checkable
class Theorem1StatementChecker(Protocol):
    """Unified Theorem 1 statement emitter."""

    def check(
        self,
        g: Callable[[float], float],
        eps_sequence: Sequence[float],
        paper_qty: Any,
    ) -> Any:
        """Emit the unified Theorem 1 statement (returns a dataclass)."""
        ...

    def check_sheet_tube_evidence(
        self,
        g: Callable[[float], float],
        eps: float,
        phi: Callable[[float, float], float],
    ) -> Any:
        """Lemma 2 LHS witness at single ``eps``."""
        ...


# ---------------------------------------------------------------------------
# PosteriorEvaluator
# ---------------------------------------------------------------------------


@runtime_checkable
class PosteriorEvaluator(Protocol):
    """Planar BL distance on ``R^2`` against the paper's ``nu_g`` reference."""

    def bl_distance_planar(
        self,
        samples: Any,
        g: Callable[[float], float],
        eps: float,
    ) -> float:
        """Return ``BL(mu_{g,eps}, nu_g)`` for samples drawn from the planar posterior."""
        ...

    def nu_g_density(
        self,
        g: Callable[[float], float],
        s: float,
        t: float,
    ) -> float:
        """Return ``nu_g`` density at ``(s, t)`` (paper formula line 82-83)."""
        ...


# ---------------------------------------------------------------------------
# AdapterObservationProtocol (Wave 68)
# ---------------------------------------------------------------------------


class ObservationKind(str, Enum):
    """Model-agnostic observation tags for :class:`AdapterObservationProtocol`.

    Each tag identifies a *kind* of observation the adapter can return.
    The metric layer dispatches on the tag, NOT on the model name (Wave 67
    principle). The four kinds cover every existing per-model observation
    method (Wave 67 §3):

    * ``ENDPOINT_BUNDLE`` -- per-channel endpoint ``StateBundle``
      (was ``observe_endpoint`` on every adapter).
    * ``DISCRETE_TOKENS`` -- ``{channel: np.ndarray (L,)}`` of integer
      token indices (was ``observe_token_indices`` on Kanzi +
      LineageFlow).
    * ``POSITION_ENTROPY_REDUCTION`` -- ``{channel: float}`` Shannon
      entropy reduction ``H(theta_before) - H(theta_after)`` (was
      ``observe_entropy_reduction`` on FlowMol3 v1 + LineageFlow).
    * ``TRAJECTORY_NATIVE`` -- ``{channel: np.ndarray (T+1, ...)}`` of
      the native trajectory (was ``export_trajectory`` on the universal
      adapter).

    ``str`` mixin makes the enum JSON-serialisable without a custom
    encoder. Stdlib-only.
    """

    ENDPOINT_BUNDLE = "endpoint_bundle"
    DISCRETE_TOKENS = "discrete_tokens"
    POSITION_ENTROPY_REDUCTION = "position_entropy_reduction"
    TRAJECTORY_NATIVE = "trajectory_native"


@dataclass(frozen=True)
class ObservationResult:
    """A single tagged observation returned by ``AdapterObservationProtocol.observe``.

    Frozen dataclass (Wave 11 / Wave 59 pattern: immutable, hashable, easy
    to compare in tests). ``payload`` is typed by ``kind``:

    * ``ENDPOINT_BUNDLE`` -- a per-channel endpoint ``StateBundle``
      (opaque reference; downstream consumers re-derive whatever they
      need from the bundle).
    * ``DISCRETE_TOKENS`` -- ``numpy.ndarray`` of shape ``(L,)`` with
      integer dtype.
    * ``POSITION_ENTROPY_REDUCTION`` -- ``float`` in nats (or whatever
      units the adapter reports; see ``units``).
    * ``TRAJECTORY_NATIVE`` -- ``numpy.ndarray`` of shape ``(T+1, ...)``
      giving the full native trajectory.

    ``channel`` is the model-internal channel name (e.g. ``"discrete_idx"``
    for Kanzi, ``"amino_acid_categorical"`` for LineageFlow,
    ``"atom_type"`` for FlowMol3). It is opaque to the metric layer --
    the metric layer reads ``result.channel`` rather than importing a
    per-model constant.

    ``units`` is a free-form string ("nats", "fraction", "indices",
    "endpoint_refs", "trajectory") for human-readable debug output.

    ``metadata`` carries free-form debug context (e.g. seed, nfe, theta
    hash) without polluting the payload.

    Stdlib-only (no torch, no numpy). The ``payload`` type is
    :class:`typing.Any` because the framework core is stdlib-only; the
    adapter implementations populate ``payload`` with the appropriate
    concrete type at runtime.
    """

    kind: ObservationKind
    channel: str
    payload: Any
    units: str = ""
    # ``metadata`` is excluded from the dataclass ``__hash__`` and
    # ``__eq__`` because the default ``dict`` is unhashable AND because
    # metadata is a debug-only field that should not affect equality.
    metadata: Mapping[str, Any] = field(
        default_factory=dict,
        compare=False,
        hash=False,
    )


@runtime_checkable
class AdapterObservationProtocol(Protocol):
    """Single typed observation surface every adapter satisfies (Wave 68).

    Mirrors the Wave 59 ``IntegratorProtocol`` pattern (interface-first,
    no implementation required). Adapters opt in by adding an ``observe``
    method that returns a tuple of :class:`ObservationResult` -- one per
    observation strategy the adapter implements.

    **Why this Protocol exists.** The Wave 67 audit found three
    per-model observation methods (``observe_endpoint`` /
    ``observe_token_indices`` / ``observe_entropy_reduction``) hard-coded
    into the metric layer (``tools/run_real_ckpt_eval.py``) and chained
    via ``if model == "kanzi" / elif ...``. Adding a 5th model meant
    editing both the helper table and the dispatch chain. The
    FlowMol3 v2 wire (Wave 66) hit the resulting gap -- v2 had
    ``observe_endpoint`` only, so the metric helper returned ``BLOCKED``
    on every real-ckpt FlowMol3 cell.

    **Design.** ``observe(...)`` returns a tuple of
    :class:`ObservationResult` tagged by :class:`ObservationKind`. The
    metric layer consumes the result tuple generically:

        >>> results = adapter.observe(trace, state, paper_quantities=pq)
        >>> token_obs = next(
        ...     (r for r in results if r.kind == ObservationKind.DISCRETE_TOKENS),
        ...     None,
        ... )

    Adapters that don't carry a discrete channel skip
    ``DISCRETE_TOKENS`` (Kanzi's continuous latent has no natural
    per-position categorical). Adapters whose native state is not a
    per-position categorical skip ``POSITION_ENTROPY_REDUCTION`` (every
    protein adapter). An empty tuple is a valid response (synthetic /
    ref / non-state adapters).

    **Byte-stable migration.** The existing
    ``observe_endpoint`` / ``observe_token_indices`` /
    ``observe_entropy_reduction`` methods stay in place on every
    adapter. The new ``observe(...)`` is ADDITIVE; existing call sites
    keep working unchanged. The metric helper refactor (Wave 67 Phase D)
    replaces the ``hasattr(adapter, "observe_entropy_reduction")``
    checks with a single ``adapter.observe(...)`` call.

    **Conformance.** Adopting the protocol is opt-in, like
    :class:`IntegratorProtocol`. Use the :func:`implements` decorator
    to declare it; :func:`assert_adapter_compliance` enforces
    structural typing at import time.
    """

    def observe(
        self,
        trace: Any,
        state: Any,
        paper_quantities: Any = None,
        *,
        strategies: tuple[ObservationKind, ...] = (
            ObservationKind.ENDPOINT_BUNDLE,
            ObservationKind.DISCRETE_TOKENS,
            ObservationKind.POSITION_ENTROPY_REDUCTION,
            ObservationKind.TRAJECTORY_NATIVE,
        ),
        theta_before: Any = None,
        theta_after: Any = None,
    ) -> tuple[ObservationResult, ...]:
        """Return a tuple of :class:`ObservationResult`, one per supported strategy.

        Parameters
        ----------
        trace
            The integration trace produced by the adapter's solve step
            (opaque to the framework core; type depends on the adapter).
        state
            The integration state at t=1 (the endpoint). May be ``None``
            for adapters that materialise state lazily.
        paper_quantities
            The :class:`PaperQuantitySnapshot` (or ``None`` if not
            threaded through). Used by adapters that derive an
            observation from paper-quantity context.
        strategies
            Tuple of :class:`ObservationKind` the caller wants. The
            adapter MAY skip strategies it does not support; the result
            tuple only contains the supported subset. The default tuple
            requests all four strategies.
        theta_before, theta_after
            Optional entropy-reduction prior/posterior. Adapters that
            support :attr:`ObservationKind.POSITION_ENTROPY_REDUCTION`
            compute ``H(theta_before) - H(theta_after)`` when both are
            supplied. Missing priors return ``None`` (the metric layer
            treats ``None`` as ``BLOCKED`` and records the reason).

        Returns
        -------
        tuple[ObservationResult, ...]
            One :class:`ObservationResult` per supported strategy in
            ``strategies``. Empty tuple is valid (adapter supports
            none of the requested strategies).
        """
        ...


# ---------------------------------------------------------------------------
# FlowMatchingODEAdapterWithObservation (Wave 54 Phase 2)
# ---------------------------------------------------------------------------


@runtime_checkable
class FlowMatchingODEAdapterWithObservation(Protocol):
    """Wave 54 Phase 2 fix surface: makes v1 (hash stub) FlowMol3 first-class alongside v2.

    Captures the structural surface shared by:

    * :class:`adaptive_reflow.adapters.flowmol3.FlowMol3Adapter` (v1
      placeholder / hash stub — default behaviour, byte-stable).
    * :class:`adaptive_reflow.adapters.flowmol3_v2_adapter.FlowMol3V2Adapter`
      (v2 real CTMC / linear / upstream integration — opt-in via
      ``--force-mode real``).

    Both adapters satisfy this Protocol structurally (the methods exist
    on both, with v1 using a hash stub for ``solve_ode`` and v2 doing
    real integration). The Protocol does NOT specify integration
    semantics — it is the SHAPE of the adapter, not the underlying
    math. Downstream metric helpers can now ``isinstance``-dispatch on
    this Protocol instead of switching on ``model == "flowmol3"``.

    **Why this Protocol exists (Wave 54 review A).** The Wave 66 wire
    at :mod:`tools.run_real_ckpt_eval` routes ``force_mode in {real,
    auto}`` to v2's ``default_flowmol3adapter`` regardless of the
    registry's adapter_factory. v1 was effectively demoted to a
    synthetic-path stub with no first-class surface. Wave 54 Phase 2
    makes v1 first-class alongside v2 by giving both a single Protocol
    surface the metric layer can dispatch on; v1's hash-based
    behaviour is preserved byte-identically (the 9 D.4 regression
    vectors in ``regression-vectors/flowmol3.json`` are gated).

    **Interface-first pattern (Wave 11 / Wave 59 / Wave 68).** This
    Protocol mirrors the existing
    :class:`AdapterObservationProtocol` pattern: structural, runtime-
    checkable, additive (no method signatures change on either
    adapter). Adapters opt in via the :func:`implements` decorator;
    :func:`assert_adapter_compliance` enforces structural typing at
    import time.

    **Byte-stable guarantee.** v1's :meth:`solve_ode` continues to
    return a hash-stable ``ODEIntegratorTrace`` whose
    ``native_state_digest`` and ``integrator_config_hash`` are
    SHA-256-derived from ``(state.digest, seed, steps)`` — see the
    ``_make_tensor_ref`` helper in ``flowmol3.py:286-300``. Adding
    this Protocol changes nothing in v1's behaviour. The 9 D.4
    vectors (``flowmol3.json`` schema ``d4.v1``, pinned at git SHA
    ``ff56e55``) remain byte-stable.

    **Method list.** Combines the 8-method
    :class:`adaptive_reflow.universal.adapter.FlowMatchingODEAdapter`
    base surface (capabilities / build_initial_state / export_endpoint
    / detach_and_validate_endpoint / apply_restart_distribution /
    compose_condition / solve_ode / observe_endpoint /
    observe_token_indices / export_trajectory) with the typed
    :meth:`observe` from :class:`AdapterObservationProtocol`. Every
    method here is a structural signature only — concrete
    implementations may differ in semantics (v1 vs v2).
    """

    # --- FlowMatchingODEAdapter 8-method base -------------------------------
    def capabilities(self) -> Any: ...
    def build_initial_state(
        self, *, batch_id: str, sample_id: str
    ) -> Any: ...
    def export_endpoint(self, state: Any) -> Any: ...
    def detach_and_validate_endpoint(self, bundle: Any) -> Any: ...
    def apply_restart_distribution(
        self,
        state: Any,
        policy: Any,
        *,
        nfe_budget: int | None = ...,
    ) -> Any: ...
    def compose_condition(
        self, bundle: Any, delta: Any
    ) -> Any: ...
    def solve_ode(
        self,
        state: Any,
        condition: Any,
        *,
        seed: int,
    ) -> Any: ...
    def observe_endpoint(self, trace: Any, state: Any) -> Any: ...
    def observe_token_indices(
        self, trace: Any, paper_quantities: Any
    ) -> dict[str, Any]: ...
    def export_trajectory(self, trace: Any) -> Any | None: ...

    # --- Wave 68 typed observation surface ---------------------------------
    def observe(
        self,
        trace: Any,
        state: Any,
        paper_quantities: Any = None,
        *,
        strategies: tuple[Any, ...] = (
            ObservationKind.ENDPOINT_BUNDLE,
            ObservationKind.DISCRETE_TOKENS,
            ObservationKind.POSITION_ENTROPY_REDUCTION,
            ObservationKind.TRAJECTORY_NATIVE,
        ),
        theta_before: Any = None,
        theta_after: Any = None,
    ) -> tuple[Any, ...]: ...


# ---------------------------------------------------------------------------
# AdapterCompliance: aggregate Protocol set + implements decorator
# ---------------------------------------------------------------------------


# NOTE: ``implements`` is defined ABOVE this section (before the heavy
# ``adaptive_reflow.theory`` imports) to break the
# ``adapters.twodim_fm → framework.interfaces`` cyclic import. See the
# NOTE block at the top of this file for details.


def assert_adapter_compliance(adapter_cls: type) -> None:
    """Verify ``adapter_cls`` satisfies its declared ``__protocols__`` set.

    Iterates each Protocol in ``adapter_cls.__protocols__`` and uses
    :func:`isinstance` (which works on ``@runtime_checkable`` Protocols)
    to verify structural typing. Raises
    :class:`MissingProtocolError` with a list of the missing
    Protocols on failure.

    For non-``runtime_checkable`` Protocols, the check is silent
    (decorative-only) and emits a no-op.

    No-op if ``__protocols__`` is not set (callers should declare
    conformance via :func:`implements`).
    """
    declared = getattr(adapter_cls, "__protocols__", ())
    if not declared:
        return
    missing: list[type] = []
    for protocol in declared:
        # Only runtime_checkable Protocols can be isinstance-checked.
        if not (isinstance(protocol, type) and getattr(
            protocol, "_is_runtime_protocol", False
        )):
            # HIGH-4 fix: explicit warning when a non-runtime Protocol
            # is declared. Without this, assert_adapter_compliance
            # silently skips non-@runtime_checkable Protocols (line 514
            # `continue`), which masks real conformance gaps when a
            # future contributor adds a Protocol without the decorator.
            warnings.warn(
                f"Protocol {protocol.__name__} is not @runtime_checkable; "
                f"assert_adapter_compliance will silently skip it. "
                f"Add @runtime_checkable decorator to enforce conformance.",
                RuntimeWarning,
                stacklevel=2,
            )
            continue
        if not isinstance(adapter_cls, protocol):
            missing.append(protocol)
    if missing:
        names = ", ".join(p.__name__ for p in missing)
        raise MissingProtocolError(
            f"{adapter_cls.__name__} does not satisfy declared Protocols: {names}"
        )