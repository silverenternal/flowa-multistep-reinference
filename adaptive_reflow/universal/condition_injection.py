"""Condition injection protocols (D3 — concrete injectors for unconditional adapters).

Paper Theorem 1 is conditional on the implicit noise scale ``eps ->
0``; the noised profile measure ``mu_{g,eps}`` converges to the sheet
measure ``nu_g`` unconditionally of any external conditioning signal.
Unconditional models (FlowMol3 CTMC, GraphBFN) sample from ``nu_g``
directly because no class/text/pocket label is supplied to the ODE.

The condition-injection protocol surface is therefore NOT a Theorem-1
quantity — it is an INTERFACE requirement
(``docs/ADAPTER_INTERFACE_SPEC.md`` Section 6) that exists to:

1. make the per-round condition provenance auditable in the ledger;
2. preserve a place to attach dataset/variant metadata (an implicit
   condition that does not influence the model but IS consumed by the
   framework's envelope layer / ledger trace).

GAP-F4 in the unified gap analysis identifies
``has_condition_injection=False`` as the blocker preventing FlowMol3
from entering :class:`Engine.run_round`; this extension is the
simplest path to lift that blocker for unconditional adapters. The
honest paper-grounding remains pending GAP-F10 (categorical Theorem-1
analog). Until then, the framework claims for FlowMol3 are
framework-heuristic, not paper-grounded; this extension does not
change that.

Module boundary
---------------

* stdlib-only (no ``torch``, no I/O, no mutation of inputs).
* :class:`ConditionInjectionProtocol` is ``runtime_checkable`` so
  adapters can duck-type structural conformance.
* Concrete injectors preserve :class:`ODEConditionDelta` invariants
  (``target_round``, ``calibration_artifact_hash``, ``source``) so the
  engine's mismatch gate does not fire-closed (ADR-0005).

Public surface
--------------

* :class:`ConditionInjectionProtocol` (abstract)
* :class:`NullConditionInjector`
* :class:`PassthroughConditionInjector`
* :class:`AugmentingConditionInjector`
* :func:`validate_condition_injector`
* :data:`ConditionInjectorKind` (literal)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from adaptive_reflow.universal.state import (
    ODEConditionDelta,
    StateBundle,
    validate_condition_delta,
)

# ---------------------------------------------------------------------------
# Literal type for the condition-injector kind identifier
# ---------------------------------------------------------------------------

ConditionInjectorKind = Literal[
    "null",
    "passthrough",
    "augmenting",
    "text",
    "pocket",
    "class_label",
    "ctmc_rate",
]
"""Stable identifier for the condition injector kind.

Used by the audit trail to attribute per-round condition provenance
and by downstream consumers to opt-out of specific injector kinds.
"""


# ---------------------------------------------------------------------------
# Abstract protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ConditionInjectionProtocol(Protocol):
    """Abstract condition injector.

    Adapters delegate :meth:`compose_condition` to a concrete injector
    so the model-side surface is decoupled from the framework-side
    audit-trail requirements.

    Methods
    -------

    * :meth:`kind` — return the canonical kind identifier (audit token).
    * :meth:`compose_delta` — return a new :class:`ODEConditionDelta`
      that satisfies ``validate_condition_delta``. The injector MUST
      preserve ``target_round`` and ``calibration_artifact_hash`` from
      the input ``delta`` so the engine's mismatch gate
      (``engine.py:1535-1538``) does not fire-closed.
    * :meth:`audit_metadata` — return stable per-instance metadata for
      the ledger's per-round row.
    """

    def kind(self) -> ConditionInjectorKind:
        """Return the canonical kind identifier."""
        ...

    def compose_delta(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        """Return a new :class:`ODEConditionDelta`."""
        ...

    def audit_metadata(self) -> Mapping[str, Any]:
        """Return stable per-instance metadata for the ledger."""
        ...


# ---------------------------------------------------------------------------
# NullConditionInjector — for unconditional models (FlowMol3, GraphBFN v1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NullConditionInjector:
    """Canonical solution for ``has_condition_injection=True`` adapters whose native model is unconditional.

    The injector fills ``delta_spec`` with ``{'condition_kind': 'null',
    'dataset': str, 'variant': str, 'round_trace_only': True}`` so the
    engine never sees an empty ``delta_spec`` (which would fail
    ``validate_condition_delta``). The model-side is a no-op: the
    native model does not consume ``delta_spec``.

    The audit trail captures the null-condition provenance so the
    per-round ledger row records WHY no condition was applied (instead
    of the gap-failing ``CapabilityMissingError`` that FlowMol3 raises
    today).
    """

    dataset: str
    variant: str

    def __post_init__(self) -> None:
        if not isinstance(self.dataset, str) or not self.dataset:
            raise ValueError("dataset_must_be_non_empty_str")
        if not isinstance(self.variant, str) or not self.variant:
            raise ValueError("variant_must_be_non_empty_str")

    def kind(self) -> Literal["null"]:
        """Return ``"null"``."""
        return "null"

    def compose_delta(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        """Return a new delta with null-condition provenance."""
        new_spec = dict(delta.delta_spec)  # type: ignore[call-overload]
        new_spec.setdefault("condition_kind", "null")
        new_spec.setdefault("dataset", str(self.dataset))
        new_spec.setdefault("variant", str(self.variant))
        new_spec.setdefault("round_trace_only", True)
        return ODEConditionDelta(
            delta_spec=new_spec,
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    def audit_metadata(self) -> Mapping[str, Any]:
        """Return the canonical null-injector audit metadata."""
        return {
            "injector_kind": "null",
            "dataset": str(self.dataset),
            "variant": str(self.variant),
        }


# ---------------------------------------------------------------------------
# PassthroughConditionInjector — back-compat for reference_flowa.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PassthroughConditionInjector:
    """Back-compat injector for adapters that pass the delta through unchanged.

    Used by :class:`reference_flowa.ReferenceFlowAAdapter`'s
    :meth:`compose_condition`. The injector preserves
    ``target_round`` and ``calibration_artifact_hash`` and emits a
    fresh :class:`ODEConditionDelta` (new dataclass identity, equal
    content) so the engine's mismatch gate stays happy.
    """

    def kind(self) -> Literal["passthrough"]:
        """Return ``"passthrough"``."""
        return "passthrough"

    def compose_delta(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        """Return a fresh delta carrying the input ``delta_spec``."""
        return ODEConditionDelta(
            delta_spec=dict(delta.delta_spec),  # type: ignore[call-overload]
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    def audit_metadata(self) -> Mapping[str, Any]:
        """Return the canonical passthrough-injector audit metadata."""
        return {"injector_kind": "passthrough"}


# ---------------------------------------------------------------------------
# AugmentingConditionInjector — back-compat for mnist_fm.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AugmentingConditionInjector:
    """Back-compat injector for adapters that augment the delta_spec with defaults.

    Used by :class:`mnist_fm.MNISTFMAdapter`'s :meth:`compose_condition`.
    The injector sets defaults from :attr:`defaults` for any key NOT
    already present in the input ``delta_spec`` (does not overwrite
    existing keys). Preserves ``target_round`` and
    ``calibration_artifact_hash``.
    """

    defaults: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.defaults, Mapping):
            raise ValueError("defaults_must_be_mapping")

    def kind(self) -> Literal["augmenting"]:
        """Return ``"augmenting"``."""
        return "augmenting"

    def compose_delta(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        """Return a fresh delta with ``defaults`` populated (no overwrite)."""
        new_spec = dict(delta.delta_spec)  # type: ignore[call-overload]
        for k, v in self.defaults.items():
            new_spec.setdefault(str(k), v)
        return ODEConditionDelta(
            delta_spec=new_spec,
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    def audit_metadata(self) -> Mapping[str, Any]:
        """Return the canonical augmenting-injector audit metadata."""
        return {
            "injector_kind": "augmenting",
            "defaults_keys": tuple(sorted(str(k) for k in self.defaults)),
        }


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def validate_condition_injector(
    inj: ConditionInjectionProtocol,
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``inj`` is a well-formed condition injector."""
    errors: list[str] = []
    if not isinstance(inj, ConditionInjectionProtocol):
        return (False, ("condition_injector_must_implement_protocol",))
    try:
        kind_value = inj.kind()
    except Exception:
        return (False, ("condition_injector_kind_must_be_total",))
    valid_kinds = ("null", "passthrough", "augmenting", "text", "pocket", "class_label", "ctmc_rate")
    if kind_value not in valid_kinds:
        errors.append(f"condition_injector_kind_unknown:{kind_value}")
    try:
        meta = inj.audit_metadata()
    except Exception:
        errors.append("audit_metadata_must_be_total")
    else:
        if not isinstance(meta, Mapping):
            errors.append("audit_metadata_must_be_mapping")
    return (not errors, tuple(errors))


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------


def default_null_injector(
    *, dataset: str = "default", variant: str = "v1"
) -> ConditionInjectionProtocol:
    """Return the canonical :class:`NullConditionInjector` factory."""
    return NullConditionInjector(dataset=dataset, variant=variant)


__all__ = [
    "AugmentingConditionInjector",
    "ConditionInjectionProtocol",
    "ConditionInjectorKind",
    "NullConditionInjector",
    "PassthroughConditionInjector",
    "default_null_injector",
    "validate_condition_injector",
]
