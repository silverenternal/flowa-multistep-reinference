"""Universal carrier types — Flow Matching ODE state (DTB-G1).

This module declares the *model-family-agnostic* pure-data carriers and
opaque-handle aliases used by the round frame. It is **stdlib-only**
(no ``torch``, no I/O, no mutation of inputs) so that tests, reference
implementations and synthetic fixtures can all be written against the
same opaque handle contract.

Module boundary
---------------

* The engine never inspects native tensors. ``TensorRef`` is just an
  opaque string identifier that adapters use to label their own native
  state; the engine treats them as opaque tokens.
* ``StateBundle.channels`` is a generic ``Mapping[ChannelName, TensorRef]``
  with no molecule-specific keys baked in. Non-molecular adapters (graph,
  image, sequence) populate their own channel names.
* The four molecule channel aliases (``coordinate`` / ``charge`` /
  ``raw_pair`` / ``projected_pair``) live in :mod:`molecular.channels`,
  not here.

Public surface
--------------

Pure-data carriers (frozen dataclasses)
    :class:`TensorRef`
    :class:`StateBundle`
    :class:`ODEConditionDelta`
    :class:`ODEIntegratorTrace`

NewType aliases
    :data:`ChannelName`

Validators
    :func:`validate_state_bundle`
    :func:`validate_condition_delta`
    :func:`validate_integrator_trace`

Tasks satisfied:

* ``DTB-G1`` — public Flow Matching ODE re-inference engine + adapter
  contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NewType

if TYPE_CHECKING:
    from adaptive_reflow.contracts.condition import (
        Condition as _Condition,
        MappingConditionAdapter as _MappingConditionAdapter,
        validate_condition as _validate_condition,
    )

    from .adapter import AdapterCapabilities

# ---------------------------------------------------------------------------
# Opaque handles + NewType aliases
# ---------------------------------------------------------------------------


TensorRef = NewType("TensorRef", str)
"""Opaque string handle to a native tensor / state. Engine never inspects."""


ChannelName = NewType("ChannelName", str)
"""Adapter-supplied channel name. Universal layer carries no canonical list."""


# ---------------------------------------------------------------------------
# Pure-data carriers
# ---------------------------------------------------------------------------


def _empty_capabilities() -> AdapterCapabilities:
    """Lazily construct the empty-capability token to break the
    :class:`StateBundle` / :class:`AdapterCapabilities` import cycle.

    The real :class:`AdapterCapabilities` lives in
    :mod:`adaptive_reflow.universal.adapter`; this helper returns a
    zero-capability token whose ``supported_channels`` is empty.

    The function is invoked by :attr:`StateBundle.capability_token`'s
    default-factory on first construction, NOT at module-import time.
    A module-level eager call would create a circular import:
    ``state.py`` ↔ ``adapter.py``.
    """
    from .adapter import AdapterCapabilities

    return AdapterCapabilities(
        has_ode_integration_surface=False,
        has_prior_export=False,
        has_state_export=False,
        has_condition_injection=False,
        has_restart_boundary=False,
        has_continuous_channels=False,
        has_discrete_channels=False,
        has_trajectory_digest=False,
        has_deterministic_seed=False,
        has_materialization_route=False,
        supported_channels=(),
        channel_domains={},
    )


@dataclass(frozen=True)
class StateBundle:
    """Pure-data carrier describing a Flow Matching ODE state (generic).

    All tensor-shaped values are opaque ``TensorRef`` handles. The engine
    never inspects the contents of these handles; it only propagates them
    and validates the structural / metadata invariants below.

    The ``channels`` mapping is keyed by an adapter-supplied
    :data:`ChannelName`; no molecule-specific keys are baked in.

    Required invariants (validated by :func:`validate_state_bundle`):

    * ``channels`` is non-empty.
    * Every channel name in ``channels`` appears in
      ``capability_token``'s ``supported_channels``.
    * ``reference_frame`` is one of a fixed tuple
      (``"pocket_centered"``, ``"world"``, ``"lattice"``).
    * ``normalization`` is one of ``"none"``, ``"per_atom_std"``,
      ``"per_pocket_std"``.
    * ``detach_proof`` is ``True`` and ``source_round`` is a non-negative
      int.
    * ``batch_id`` / ``sample_id`` are non-empty strings.
    """

    channels: Mapping[ChannelName, TensorRef]
    masks: Mapping[str, TensorRef]
    batch_id: str
    sample_id: str
    reference_frame: str
    normalization: str
    source_round: int
    detach_proof: bool
    native_state_digest: str
    provenance: tuple[str, ...]
    capability_token: AdapterCapabilities = field(
        default_factory=_empty_capabilities
    )


# ``AdapterCapabilities`` is forward-declared here so the default-factory
# type-hint resolves without a circular import. The real definition lives
# in :mod:`adaptive_reflow.universal.adapter`; importing it lazily would
# defeat the purpose of declaring the bundle carriers next to each other,
# so we use a string annotation + a lazy runtime construction pattern.


@dataclass(frozen=True)
class ODEConditionDelta:
    """Pure-data carrier for an ODE condition delta.

    A condition delta is a declarative description of how the next round's
    ODE condition differs from the source bundle's condition. The engine
    passes the ``delta_spec`` through to the adapter via
    :meth:`FlowMatchingODEAdapter.compose_condition`.

    The ``delta_spec`` is typed as :class:`~adaptive_reflow.contracts.condition.Condition`
    (D8) — a discriminated union over ``null``, ``cfg``, ``inpainting``,
    ``bfn_inpaint``, ``property``, and ``mapping`` (back-compat). Adapters
    that pass a raw ``Mapping[str, Any]`` to the constructor are
    auto-wrapped into a :class:`~adaptive_reflow.contracts.condition.MappingConditionAdapter`
    by :meth:`__post_init__`, so the type change is non-breaking for
    existing adapter code that still emits dicts.

    Required invariants (validated by :func:`validate_condition_delta`):

    * ``delta_spec`` is a non-empty :class:`~adaptive_reflow.contracts.condition.Condition`.
    * ``source`` is a non-empty string identifying the producer.
    * ``target_round`` is a non-negative integer.
    * ``calibration_artifact_hash`` is a non-empty string.
    """

    delta_spec: _Condition
    source: str
    target_round: int
    calibration_artifact_hash: str

    def __post_init__(self) -> None:
        """Auto-wrap ``Mapping`` arguments as :class:`MappingConditionAdapter`.

        Preserves the 2356-test back-compat invariant: adapters that
        still emit raw ``dict``-style delta_spec continue to work; the
        constructor coerces the dict into a typed :class:`Condition`
        (with ``condition_kind == "mapping"`` by default) so all
        downstream consumers see a uniform :class:`Condition` view.

        Import is local to avoid the
        ``state.py`` ↔ ``contracts/condition.py`` ↔ ``contracts/__init__.py``
        module-init cycle (the contracts ``__init__`` chain re-enters
        ``universal.state`` via ``dynamic_noise_bias``).
        """
        from adaptive_reflow.contracts.condition import (
            Condition as _Condition_runtime,
            MappingConditionAdapter as _MappingConditionAdapter_runtime,
        )

        if isinstance(self.delta_spec, Mapping) and not isinstance(
            self.delta_spec, _Condition_runtime
        ):
            object.__setattr__(
                self,
                "delta_spec",
                _MappingConditionAdapter_runtime.from_mapping(dict(self.delta_spec)),
            )


@dataclass(frozen=True)
class ODEIntegratorTrace:
    """Pure-data carrier for a native ODE integrator trace.

    The engine never inspects the native trajectory; it only requires the
    structural invariants below so that round traces are fail-closed
    against integrator omission.

    Required invariants:

    * ``steps`` is a positive integer.
    * ``accept_rate`` is a real number in ``[0, 1]``.
    * ``native_state_digest`` and ``integrator_config_hash`` are non-empty
      strings.
    """

    steps: int
    accept_rate: float
    native_state_digest: str
    integrator_config_hash: str


# ---------------------------------------------------------------------------
# Canonical string enums (universal; not molecule-specific)
# ---------------------------------------------------------------------------


REFERENCE_FRAMES: tuple[str, ...] = ("pocket_centered", "world", "lattice")
NORMALIZATION_KINDS: tuple[str, ...] = ("none", "per_atom_std", "per_pocket_std")


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_state_bundle(bundle: StateBundle) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``bundle`` satisfies the engine invariants.

    On failure, the returned tuple's second element is a deterministic,
    ASCII-only tuple of error codes; never raises.
    """
    errors: list[str] = []
    if bundle is None:
        return (False, ("state_bundle_must_not_be_none",))
    if not isinstance(bundle.channels, Mapping) or not bundle.channels:
        errors.append("channels_must_be_non_empty_mapping")
    if not isinstance(bundle.masks, Mapping):
        errors.append("masks_must_be_mapping")
    if not bundle.batch_id:
        errors.append("batch_id_must_be_non_empty")
    if not bundle.sample_id:
        errors.append("sample_id_must_be_non_empty")
    if bundle.reference_frame not in REFERENCE_FRAMES:
        errors.append(
            f"reference_frame_must_be_one_of_{','.join(REFERENCE_FRAMES)}"
        )
    if bundle.normalization not in NORMALIZATION_KINDS:
        errors.append(
            f"normalization_must_be_one_of_{','.join(NORMALIZATION_KINDS)}"
        )
    if not isinstance(bundle.source_round, int) or isinstance(bundle.source_round, bool):
        errors.append("source_round_must_be_int")
    elif bundle.source_round < 0:
        errors.append("source_round_must_be_non_negative")
    if bundle.detach_proof is not True:
        errors.append("detach_proof_must_be_true")
    if not bundle.native_state_digest:
        errors.append("native_state_digest_must_be_non_empty")
    if not bundle.provenance:
        errors.append("provenance_must_be_non_empty")

    # Every channel name must be in the capability token's
    # ``supported_channels``; this is the engine's contract for fail-closed
    # unknown-channel rejection.
    supported = frozenset(bundle.capability_token.supported_channels)
    if isinstance(bundle.channels, Mapping):
        for channel_name in bundle.channels:
            if channel_name not in supported:
                errors.append(f"unknown_channel:{channel_name}")
    return (not errors, tuple(errors))


def validate_condition_delta(delta: ODEConditionDelta) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``delta`` is well-formed.

    The ``delta_spec`` is now typed as :class:`Condition` (D8). The
    validator accepts either a typed :class:`Condition` (the canonical
    post-D8 form) or, for back-compat, a raw ``Mapping[str, Any]`` —
    but the :class:`ODEConditionDelta` constructor already auto-wraps
    any mapping argument into :class:`MappingConditionAdapter`, so the
    back-compat branch is rarely exercised in practice.
    """
    errors: list[str] = []
    if delta is None:
        return (False, ("condition_delta_must_not_be_none",))
    # Local import to break the module-init cycle:
    # ``state.py`` ↔ ``contracts/condition.py`` ↔ ``contracts/__init__.py``.
    from adaptive_reflow.contracts.condition import (
        Condition as _Condition,
        MappingConditionAdapter as _MappingConditionAdapter,
        validate_condition as _validate_condition,
    )

    spec = delta.delta_spec
    if isinstance(spec, _Condition):
        # Typed path (D8). Validate via the condition validator.
        # For :class:`MappingConditionAdapter` (the back-compat
        # wrapper for raw dicts), also reject empty underlying
        # mappings — ``to_mapping()`` injects a ``condition_kind``
        # key by default, but the wire form is empty.
        if isinstance(spec, _MappingConditionAdapter) and not spec._data:
            errors.append("delta_spec_must_be_non_empty_mapping")
        else:
            ok, sub_errors = _validate_condition(spec)
            if not ok:
                errors.extend(sub_errors)
    elif isinstance(spec, Mapping):
        # Back-compat path: raw mapping (should be auto-wrapped by
        # ``ODEConditionDelta.__post_init__``; this branch exists so
        # pre-D8 caller code keeps working even before the
        # auto-wrap runs).
        if not spec:
            errors.append("delta_spec_must_be_non_empty_mapping")
    else:
        errors.append("delta_spec_must_be_Condition_or_Mapping")
    if not delta.source:
        errors.append("source_must_be_non_empty")
    if not isinstance(delta.target_round, int) or isinstance(delta.target_round, bool):
        errors.append("target_round_must_be_int")
    elif delta.target_round < 0:
        errors.append("target_round_must_be_non_negative")
    if not delta.calibration_artifact_hash:
        errors.append("calibration_artifact_hash_must_be_non_empty")
    return (not errors, tuple(errors))


def validate_integrator_trace(trace: ODEIntegratorTrace) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``trace`` is well-formed."""
    errors: list[str] = []
    if trace is None:
        return (False, ("integrator_trace_must_not_be_none",))
    if not isinstance(trace.steps, int) or isinstance(trace.steps, bool):
        errors.append("steps_must_be_int")
    elif trace.steps <= 0:
        errors.append("steps_must_be_positive")
    if not isinstance(trace.accept_rate, (int, float)) or isinstance(trace.accept_rate, bool):
        errors.append("accept_rate_must_be_real_number")
    else:
        rate = float(trace.accept_rate)
        if rate < 0.0 or rate > 1.0:
            errors.append("accept_rate_must_be_in_[0,1]")
    if not trace.native_state_digest:
        errors.append("native_state_digest_must_be_non_empty")
    if not trace.integrator_config_hash:
        errors.append("integrator_config_hash_must_be_non_empty")
    return (not errors, tuple(errors))


__all__ = [
    "ChannelName",
    "NORMALIZATION_KINDS",
    # String enums
    "REFERENCE_FRAMES",
    # Pure-data carriers
    "ODEConditionDelta",
    "ODEIntegratorTrace",
    "StateBundle",
    # Handle
    "TensorRef",
    "validate_condition_delta",
    "validate_integrator_trace",
    # Validators
    "validate_state_bundle",
]
