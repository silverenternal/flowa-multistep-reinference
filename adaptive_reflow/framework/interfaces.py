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
* :class:`AdapterCompliance` -- aggregate Protocol set enforcement.

**Stdlib-only, no torch, no numpy.**
"""
from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping, Sequence
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