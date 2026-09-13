"""Typed Condition discriminated union (D8 — LMAA paper §3.2).

This module declares the typed :class:`Condition` surface that replaces
:class:`ODEConditionDelta.delta_spec`'s previous untyped
``Mapping[str, Any]`` carrier. The typed surface is OPT-IN: adapters
that pass a raw ``dict`` are auto-wrapped by
:class:`MappingConditionAdapter` at :class:`ODEConditionDelta`
construction, so the 2356-test back-compat invariant holds.

Discriminator
-------------

The discriminator field is :attr:`Condition.condition_kind`. Concrete
classes are frozen dataclasses whose :attr:`condition_kind` is a
stable string literal:

* ``"null"`` — :class:`NullCondition` — round trace-only; no model-side
  effect (FlowMol3 / GraphBFN-v1 style unconditional models).
* ``"cfg"`` — :class:`CFGCondition` — text prompt + negative prompt +
  guidance scale + truncation ratio + normalization (Lumina / HiDream
  style image flow matching).
* ``"inpainting"`` — :class:`InpaintingCondition` — slot indices +
  strength + particle count + step count (ProtBFN style BFN-inpaint).
* ``"bfn_inpaint"`` — :class:`BFNInpaintCondition` — single-slot
  Bayesian-flow inpaint with separate t-grid.
* ``"property"`` — :class:`PropertyCondition` — property target kind
  ``{logp, qed, sa}`` + scalar value (GraphBFN style property
  targeting).
* ``"mapping"`` — :class:`MappingConditionAdapter` — back-compat wrapper
  for adapters that still emit raw ``dict``-style delta_spec.

The wire carrier :class:`ODEConditionDelta.delta_spec` is typed
:class:`Condition` (Protocol); the constructor auto-wraps any
``Mapping[str, Any]`` argument into a :class:`MappingConditionAdapter`,
so the change is non-breaking for existing adapter code that emits dicts.

Public surface
--------------

Protocols
    :class:`Condition`

Pure-data carriers (frozen dataclasses)
    :class:`NullCondition`
    :class:`CFGCondition`
    :class:`InpaintingCondition`
    :class:`BFNInpaintCondition`
    :class:`PropertyCondition`
    :class:`MappingConditionAdapter`

Literal set
    :data:`CONDITION_KINDS`

Validators
    :func:`validate_condition`

Helpers
    :func:`wrap_condition`
    :func:`condition_to_mapping`
    :func:`condition_kind_of`
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Literal type for the condition-kind discriminator
# ---------------------------------------------------------------------------


CONDITION_KINDS: tuple[str, ...] = (
    "null",
    "cfg",
    "inpainting",
    "bfn_inpaint",
    "property",
    "mapping",
)
"""Canonical tuple of :attr:`Condition.condition_kind` discriminator values.

The :data:`CONDITION_KINDS` tuple is the closed type universe for the
condition-kind discriminator. Adding a new kind requires a paired
acceptance test plus a ``DTB-Q`` decision.
"""


ConditionKind = Literal[
    "null",
    "cfg",
    "inpainting",
    "bfn_inpaint",
    "property",
    "mapping",
]
"""Stable discriminator literal for :attr:`Condition.condition_kind`."""


# ---------------------------------------------------------------------------
# Abstract protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Condition(Protocol):
    """Abstract typed Condition discriminated union member.

    Every concrete :class:`Condition` MUST expose a stable
    :attr:`condition_kind` discriminator string (one of
    :data:`CONDITION_KINDS`) and a :meth:`to_mapping` serialization so
    the engine's digest helpers and per-round audit ledger can persist
    the wire form without inspecting typed internals.

    The protocol is ``runtime_checkable`` so adapters can duck-type
    structural conformance (``isinstance(x, Condition)``).
    """

    condition_kind: str

    def to_mapping(self) -> Mapping[str, Any]:
        """Return a JSON-serializable mapping representation.

        The returned mapping MUST contain ``"condition_kind"`` and
        SHOULD contain every typed field as a stable string key.
        """
        ...


# ---------------------------------------------------------------------------
# NullCondition — round trace-only (unconditional models)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NullCondition:
    """Typed :class:`Condition` for round trace-only / unconditional models.

    Carries dataset + variant provenance for the audit ledger but no
    model-side effect. Used by FlowMol3, GraphBFN-v1, and any
    ``has_condition_injection=True`` adapter whose native model does
    not consume a condition.
    """

    dataset: str = "default"
    variant: str = "v1"
    round_trace_only: bool = True
    source: str = "null_condition"

    def __post_init__(self) -> None:
        if not isinstance(self.dataset, str) or not self.dataset:
            raise ValueError("dataset_must_be_non_empty_str")
        if not isinstance(self.variant, str) or not self.variant:
            raise ValueError("variant_must_be_non_empty_str")
        if not isinstance(self.round_trace_only, bool):
            raise ValueError("round_trace_only_must_be_bool")
        if not isinstance(self.source, str) or not self.source:
            raise ValueError("source_must_be_non_empty_str")

    @property
    def condition_kind(self) -> Literal["null"]:
        """Return the discriminator literal ``"null"``."""
        return "null"

    def to_mapping(self) -> Mapping[str, Any]:
        """Return the JSON-serializable mapping form."""
        return {
            "condition_kind": "null",
            "dataset": str(self.dataset),
            "variant": str(self.variant),
            "round_trace_only": bool(self.round_trace_only),
            "source": str(self.source),
        }


# ---------------------------------------------------------------------------
# CFGCondition — text-prompt CFG (Lumina / HiDream)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CFGCondition:
    """Typed :class:`Condition` for text-prompt CFG (Lumina, HiDream).

    The ``cfg_*`` fields are model-side knobs consumed by the adapter's
    native CFG application; ``rope_axes`` is opt-in for image adapters
    whose positional encoding is axis-aware.
    """

    text_prompt: str
    negative_prompt: str = ""
    guidance_scale: float = 7.5
    cfg_trunc_ratio: float = 1.0
    cfg_normalization: str = "none"
    rope_axes: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.text_prompt, str):
            raise ValueError("text_prompt_must_be_str")
        if not isinstance(self.negative_prompt, str):
            raise ValueError("negative_prompt_must_be_str")
        g = float(self.guidance_scale)
        if g < 0.0:
            raise ValueError("guidance_scale_must_be_non_negative")
        t = float(self.cfg_trunc_ratio)
        if t < 0.0 or t > 1.0:
            raise ValueError("cfg_trunc_ratio_must_be_in_[0,1]")
        if self.cfg_normalization not in ("none", "lumina", "hidream"):
            raise ValueError(
                f"cfg_normalization_must_be_one_of_none_lumina_hidream:"
                f"{self.cfg_normalization}"
            )
        if not all(isinstance(int(a), int) and int(a) > 0 for a in self.rope_axes):
            raise ValueError("rope_axes_must_be_positive_int_tuple")
        object.__setattr__(self, "guidance_scale", g)
        object.__setattr__(self, "cfg_trunc_ratio", t)

    @property
    def condition_kind(self) -> Literal["cfg"]:
        """Return the discriminator literal ``"cfg"``."""
        return "cfg"

    def to_mapping(self) -> Mapping[str, Any]:
        """Return the JSON-serializable mapping form."""
        return {
            "condition_kind": "cfg",
            "text_prompt": str(self.text_prompt),
            "negative_prompt": str(self.negative_prompt),
            "guidance_scale": float(self.guidance_scale),
            "cfg_trunc_ratio": float(self.cfg_trunc_ratio),
            "cfg_normalization": str(self.cfg_normalization),
            "rope_axes": tuple(int(a) for a in self.rope_axes),
        }


# ---------------------------------------------------------------------------
# InpaintingCondition — slot indices + strength (ProtBFN)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InpaintingCondition:
    """Typed :class:`Condition` for multi-slot inpainting (ProtBFN-style).

    ``positions`` is a tuple of slot indices that the BFN step will
    inpaint. ``strength`` ∈ [0, 1] scales the per-slot update.
    ``n_particles`` is the BFN particle count; ``num_steps`` is the
    inpaint-solver step count; ``model_family`` discriminates the
    target vocabulary (``protbfn`` / ``abbfn`` / ``abbfn2``).
    """

    positions: tuple[int, ...]
    strength: float = 1.0
    n_particles: int = 1
    num_steps: int = 50
    model_family: str = "protbfn"

    def __post_init__(self) -> None:
        if not isinstance(self.positions, tuple):
            raise ValueError("positions_must_be_tuple")
        if not all(isinstance(int(p), int) and int(p) >= 0 for p in self.positions):
            raise ValueError("positions_must_be_non_negative_int_tuple")
        s = float(self.strength)
        if s < 0.0 or s > 1.0:
            raise ValueError("strength_must_be_in_[0,1]")
        if not isinstance(int(self.n_particles), int) or int(self.n_particles) <= 0:
            raise ValueError("n_particles_must_be_positive_int")
        if not isinstance(int(self.num_steps), int) or int(self.num_steps) <= 0:
            raise ValueError("num_steps_must_be_positive_int")
        if self.model_family not in ("protbfn", "abbfn", "abbfn2"):
            raise ValueError(
                f"model_family_must_be_one_of_protbfn_abbfn_abbfn2:"
                f"{self.model_family}"
            )
        object.__setattr__(self, "strength", s)

    @property
    def condition_kind(self) -> Literal["inpainting"]:
        """Return the discriminator literal ``"inpainting"``."""
        return "inpainting"

    def to_mapping(self) -> Mapping[str, Any]:
        """Return the JSON-serializable mapping form."""
        return {
            "condition_kind": "inpainting",
            "positions": tuple(int(p) for p in self.positions),
            "strength": float(self.strength),
            "n_particles": int(self.n_particles),
            "num_steps": int(self.num_steps),
            "model_family": str(self.model_family),
        }


# ---------------------------------------------------------------------------
# BFNInpaintCondition — single-slot Bayesian-flow inpaint
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BFNInpaintCondition:
    """Typed :class:`Condition` for single-slot Bayesian-flow inpaint.

    Distinguished from :class:`InpaintingCondition` by its single-slot
    schema (the BFN variant used by GraphBFN-inpaint in the survey).
    ``t_grid_len`` overrides the default ODE step count.
    """

    slot_index: int
    strength: float = 1.0
    n_particles: int = 1
    t_grid_len: int = 32

    def __post_init__(self) -> None:
        if not isinstance(int(self.slot_index), int) or int(self.slot_index) < 0:
            raise ValueError("slot_index_must_be_non_negative_int")
        s = float(self.strength)
        if s < 0.0 or s > 1.0:
            raise ValueError("strength_must_be_in_[0,1]")
        if not isinstance(int(self.n_particles), int) or int(self.n_particles) <= 0:
            raise ValueError("n_particles_must_be_positive_int")
        if not isinstance(int(self.t_grid_len), int) or int(self.t_grid_len) <= 0:
            raise ValueError("t_grid_len_must_be_positive_int")
        object.__setattr__(self, "strength", s)

    @property
    def condition_kind(self) -> Literal["bfn_inpaint"]:
        """Return the discriminator literal ``"bfn_inpaint"``."""
        return "bfn_inpaint"

    def to_mapping(self) -> Mapping[str, Any]:
        """Return the JSON-serializable mapping form."""
        return {
            "condition_kind": "bfn_inpaint",
            "slot_index": int(self.slot_index),
            "strength": float(self.strength),
            "n_particles": int(self.n_particles),
            "t_grid_len": int(self.t_grid_len),
        }


# ---------------------------------------------------------------------------
# PropertyCondition — property-targeted scalar (GraphBFN)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PropertyCondition:
    """Typed :class:`Condition` for property targeting (GraphBFN-style).

    ``property_kind`` is one of ``{"logp", "qed", "sa"}``; the
    ``property_value`` scalar is the per-round target (logp in
    ``[-inf, inf]``, qed in ``[0, 1]``, sa in ``[1, 10]``).
    """

    property_kind: str
    property_value: float

    def __post_init__(self) -> None:
        if self.property_kind not in ("logp", "qed", "sa"):
            raise ValueError(
                f"property_kind_must_be_one_of_logp_qed_sa:{self.property_kind}"
            )
        v = float(self.property_value)
        if self.property_kind == "qed" and (v < 0.0 or v > 1.0):
            raise ValueError("property_value_for_qed_must_be_in_[0,1]")
        if self.property_kind == "sa" and (v < 1.0 or v > 10.0):
            raise ValueError("property_value_for_sa_must_be_in_[1,10]")
        object.__setattr__(self, "property_value", v)

    @property
    def condition_kind(self) -> Literal["property"]:
        """Return the discriminator literal ``"property"``."""
        return "property"

    def to_mapping(self) -> Mapping[str, Any]:
        """Return the JSON-serializable mapping form."""
        return {
            "condition_kind": "property",
            "property_kind": str(self.property_kind),
            "property_value": float(self.property_value),
        }


# ---------------------------------------------------------------------------
# MappingConditionAdapter — back-compat wrapper for raw dict delta_spec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MappingConditionAdapter:
    """Back-compat :class:`Condition` for adapters that still emit raw dicts.

    The :class:`ODEConditionDelta` constructor auto-wraps any
    ``Mapping[str, Any]`` argument into a :class:`MappingConditionAdapter`
    so the change from untyped ``delta_spec: Mapping[str, Any]`` to
    typed ``delta_spec: Condition` is non-breaking for the 2356 pytest
    suite.

    The adapter does NOT mutate the underlying mapping on construction;
    :attr:`condition_kind` returns ``"mapping"`` by default if no
    ``"condition_kind"`` key is present, and the underlying
    ``condition_kind`` value otherwise. This preserves the legacy
    contract that adapter code can pass a flat dict (without an
    explicit ``condition_kind`` key) and downstream consumers see
    ``condition_kind == "mapping"`` via the property.

    Adapters that want full typing SHOULD construct concrete
    :class:`Condition` subclasses (Null / CFG / Inpainting /
    BFNInpaint / Property) instead of :class:`MappingConditionAdapter`.
    """

    _data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self._data, Mapping):
            raise ValueError("_data_must_be_mapping")
        # NOTE: We do NOT inject a ``condition_kind: "mapping"`` key
        # into the underlying mapping — doing so would break adapter
        # code that uses ``dict.setdefault("condition_kind", ...)`` to
        # set a discriminating kind on top of an existing flat dict
        # (e.g., NullConditionInjector). The discriminator lives on
        # the ``condition_kind`` PROPERTY; ``to_mapping()`` exposes
        # the underlying dict verbatim, so adapter code that iterates
        # sees the original (possibly kind-less) keys.

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> MappingConditionAdapter:
        """Build a :class:`MappingConditionAdapter` from a raw mapping."""
        return cls(_data=dict(mapping))

    @property
    def condition_kind(self) -> str:
        """Return the discriminator literal (defaults to ``"mapping"``)."""
        kind = self._data.get("condition_kind", "mapping")
        return str(kind)

    def to_mapping(self) -> Mapping[str, Any]:
        """Return the underlying mapping as a fresh dict copy.

        The returned mapping ALWAYS contains a ``"condition_kind"`` key
        (either the underlying value if present, or the property default
        ``"mapping"`` otherwise). This makes the wire form stable across
        the API surface and satisfies the
        :func:`validate_condition` invariant
        ``condition_to_mapping_must_contain_condition_kind`` even for
        adapters that emit a flat dict without an explicit
        ``condition_kind`` key.
        """
        out = dict(self._data)
        out.setdefault("condition_kind", self.condition_kind)
        return out

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style ``get`` shim for adapter-side backward compat.

        Adapters that previously read ``condition.delta_spec.get("k")``
        can keep using that idiom when ``delta_spec`` is a
        :class:`MappingConditionAdapter` (duck-typed via this method).
        """
        return self._data.get(key, default)

    def keys(self) -> Any:
        """Dict-style ``keys`` shim for engine ``_digest_condition`` callers."""
        return self._data.keys()

    def values(self) -> Any:
        """Dict-style ``values`` shim for engine ``_digest_condition`` callers."""
        return self._data.values()

    def items(self) -> Any:
        """Dict-style ``items`` shim for engine ``_digest_condition`` callers."""
        return self._data.items()

    def __getitem__(self, key: str) -> Any:
        """Dict-style ``__getitem__`` shim for adapter-side backward compat."""
        return self._data[key]

    def __contains__(self, key: object) -> bool:
        """``in`` operator shim for adapter-side backward compat."""
        return key in self._data

    def __iter__(self) -> Any:
        """Iterate over the underlying mapping's keys."""
        return iter(self._data)

    def __len__(self) -> int:
        """Length shim so ``MappingConditionAdapter`` satisfies
        :class:`collections.abc.Mapping` ABC requirements."""
        return len(self._data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def wrap_condition(value: Condition | Mapping[str, Any]) -> Condition:
    """Coerce a raw mapping into a :class:`Condition` (no-op if already typed).

    This helper is the canonical entry-point for adapter code that
    wants to construct a fresh :class:`ODEConditionDelta.delta_spec`
    from a raw ``dict``. Idempotent: passing a typed :class:`Condition`
    returns it unchanged.

    Adapters can also rely on the :class:`ODEConditionDelta`
    constructor's auto-wrap; this helper is for adapter code that
    wants explicit control.
    """
    if isinstance(value, Condition):
        return value
    if isinstance(value, Mapping):
        wrapped = MappingConditionAdapter.from_mapping(value)
        # MappingConditionAdapter exposes condition_kind as a read-only
        # @property; the Condition protocol declares it as a settable
        # variable, so mypy flags this as incompatible. The adapter is
        # structurally conformant (it satisfies the protocol's read
        # surface via runtime_checkable), so silence the type-mismatch.
        return wrapped  # type: ignore[return-value]
    raise TypeError(
        f"condition_must_be_Condition_or_Mapping:{type(value).__name__}"
    )


def condition_to_mapping(condition: Condition) -> Mapping[str, Any]:
    """Return the JSON-serializable mapping form of a :class:`Condition`."""
    if not isinstance(condition, Condition):
        raise TypeError(
            f"condition_must_implement_Condition_protocol:{type(condition).__name__}"
        )
    return condition.to_mapping()


def condition_kind_of(value: Condition | Mapping[str, Any]) -> str:
    """Return :attr:`Condition.condition_kind` for either typed or raw input.

    For a typed :class:`Condition` returns its discriminator; for a raw
    mapping returns its ``"condition_kind"`` key (or ``"mapping"`` if
    absent). This helper lets the engine inspect the discriminator
    without first wrapping the input.
    """
    if isinstance(value, Condition):
        return str(value.condition_kind)
    if isinstance(value, Mapping):
        return str(value.get("condition_kind", "mapping"))
    raise TypeError(
        f"condition_kind_of_requires_Condition_or_Mapping:{type(value).__name__}"
    )


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_condition(
    condition: Condition | None,
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``condition`` is a well-formed :class:`Condition`.

    Validates:

    * ``condition`` is not ``None`` and implements :class:`Condition`.
    * ``condition_kind`` is a non-empty string in
      :data:`CONDITION_KINDS` (or the back-compat literal ``"mapping"``).
    * ``to_mapping()`` returns a non-empty mapping that contains a
      ``"condition_kind"`` key matching the discriminator.
    """
    errors: list[str] = []
    if condition is None:
        return (False, ("condition_must_not_be_none",))
    if not isinstance(condition, Condition):
        return (False, ("condition_must_implement_Condition_protocol",))
    try:
        kind = str(condition.condition_kind)
    except Exception:
        return (False, ("condition_kind_must_be_total",))
    if not kind:
        errors.append("condition_kind_must_be_non_empty_str")
    elif kind not in CONDITION_KINDS:
        # Allow custom kinds but record a warning-style error code;
        # the engine does NOT fail closed on unknown custom kinds.
        errors.append(f"condition_kind_unknown:{kind}")
    try:
        mapping = condition.to_mapping()
    except Exception:
        errors.append("condition_to_mapping_must_be_total")
        mapping = None
    else:
        if not isinstance(mapping, Mapping) or not mapping:
            errors.append("condition_to_mapping_must_be_non_empty_mapping")
        elif "condition_kind" not in mapping:
            errors.append("condition_to_mapping_must_contain_condition_kind")
        elif str(mapping.get("condition_kind", "")) != kind:
            errors.append("condition_to_mapping_kind_must_match_discriminator")
    return (not errors, tuple(errors))


__all__ = [
    "BFNInpaintCondition",
    "CFGCondition",
    "CONDITION_KINDS",
    "Condition",
    "ConditionKind",
    "InpaintingCondition",
    "MappingConditionAdapter",
    "NullCondition",
    "PropertyCondition",
    "condition_kind_of",
    "condition_to_mapping",
    "validate_condition",
    "wrap_condition",
]
