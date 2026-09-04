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
* :class:`Theorem1StatementChecker` -- unified Theorem 1 statement.
* :class:`PosteriorEvaluator` -- planar BL distance on ``R^2``.
* :class:`AdapterCompliance` -- aggregate Protocol set enforcement.

**Stdlib-only, no torch, no numpy.**
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from adaptive_reflow.theory.paper_quantities import PhysicalComplement

__all__ = [
    "ChannelwiseBlender",
    "ChannelwiseMemoryFractionPolicy",
    "IntegratorProtocol",
    "NoiseInjectionProtocol",
    "MergeOperatorProtocol",
    "SheetSchedulerProtocol",
    "SelectionRatioWitness",
    "Theorem1StatementChecker",
    "PosteriorEvaluator",
    "AdapterCompliance",
    "implements",
    "assert_adapter_compliance",
    "MissingProtocolError",
]


class MissingProtocolError(TypeError):
    """Raised when an adapter fails to satisfy a declared Protocol."""
    pass


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


def implements(*protocols: type) -> Callable[[type], type]:
    """Class decorator that declares which Protocols the class satisfies.

    Usage::

        @implements(ChannelwiseBlender, IntegratorProtocol)
        class MyAdapter:
            ...

    Stores the Protocol set on the class as ``__protocols__``. The
    set is consulted by :func:`assert_adapter_compliance`. This
    decorator is purely declarative (no runtime checks at decoration
    time); call :func:`assert_adapter_compliance` to enforce.

    Returns the class unchanged.
    """
    for protocol in protocols:
        if not isinstance(protocol, type):
            raise TypeError(
                f"implements() expects Protocol *type* arguments, got {protocol!r}"
            )
    # Filter to runtime_checkable Protocols (the only kind we can
    # structurally check); pass-through non-Protocol types are stored
    # as opaque markers.
    proto_set = tuple(protocols)

    def decorator(cls: type) -> type:
        existing = getattr(cls, "__protocols__", ())
        # Union, dedup, preserve order.
        merged: list[type] = list(existing)
        for p in proto_set:
            if p not in merged:
                merged.append(p)
        cls.__protocols__ = tuple(merged)  # type: ignore[attr-defined]
        return cls

    return decorator


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
            continue
        if not isinstance(adapter_cls, protocol):
            missing.append(protocol)
    if missing:
        names = ", ".join(p.__name__ for p in missing)
        raise MissingProtocolError(
            f"{adapter_cls.__name__} does not satisfy declared Protocols: {names}"
        )