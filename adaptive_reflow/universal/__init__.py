"""Universal core — model-family-agnostic kernel.

This subpackage is the canonical home for the Flow Matching ODE
re-inference *kernel* — the universal, stdlib-only, no-molecule-vocabulary
contracts that any model family (molecular pocket-conditioned 3D flow
matching, graph flow, image flow, sequence flow) can implement without
ever reaching into molecule-specific code.

Module boundary
---------------

* ``universal/state.py`` — ``TensorRef``, ``StateBundle``,
  ``ODEConditionDelta``, ``ODEIntegratorTrace`` (no molecule-specific
  channel names).
* ``universal/adapter.py`` — ``FlowMatchingODEAdapter`` Protocol +
  ``AdapterCapabilities`` (with per-adapter ``channel_domains``; no
  hardcoded ``DOMAIN_BY_CHANNEL`` table).
* ``universal/envelope.py`` — ``EnvelopeCriterion`` +
  ``EnvelopeClassification`` (no molecule-specific observable names).
* ``universal/evaluator.py`` — ``Evaluator`` Protocol (no GNINA / QED /
  ADMET / PoseBusters assumptions).
* ``universal/mixer.py`` — ``RestartMixer`` Protocol (no (N, 3)
  coordinate shape hardcoding).
* ``universal/validators.py`` — single point of entry for all
  universal validators.

Public surface
--------------

Pure-data carriers
    :class:`StateBundle`
    :class:`ODEConditionDelta`
    :class:`ODEIntegratorTrace`
    :class:`AdapterCapabilities`
    :class:`EnvelopeCriterion`
    :class:`EnvelopeClassification`

NewType aliases
    :data:`TensorRef`
    :data:`ChannelName`
    :data:`ChannelDomain`
    :data:`Predicate`
    :data:`ArtifactHash`
    :data:`BundleId`
    :data:`ComplementBlockerCode`

Protocols
    :class:`FlowMatchingODEAdapter`
    :class:`Evaluator`
    :class:`RestartMixer`

Exceptions
    :class:`CapabilityMissingError`
    :class:`CapabilityMismatchError`

Validators
    :func:`validate_state_bundle`
    :func:`validate_condition_delta`
    :func:`validate_integrator_trace`
    :func:`validate_capabilities`
    :func:`validate_envelope_criterion`
    :func:`validate_envelope_classification`
    :func:`validate_evaluator_artifact_hash`
    :func:`validate_blend_inputs`
    :func:`validate_unit_factor`
    :func:`validate_unit_float`
    :func:`validate_positive_int`
    :func:`validate_nonneg_int`

Tasks satisfied:

* ``DTB-G1`` — public Flow Matching ODE re-inference engine + adapter
  contract.
* ``DTB-NC1`` / ``DTB-NC2`` — generic envelope contract.
* ``DTB-R7`` — universal evaluator contract.
* ``DTB-L3`` / ``DTB-L4`` — universal restart mixer contract.
"""
from __future__ import annotations

from typing import Any

from .adapter import (
    AdapterCapabilities,
    CapabilityMismatchError,
    CapabilityMissingError,
    ChannelDomain,
    FlowMatchingODEAdapter,
    RestartPolicy,
    validate_capabilities,
)
# D8: typed Condition discriminated union.
#
# Import the submodule lazily via ``__getattr__`` to break the
# ``universal`` → ``contracts.__init__`` → ``envelope`` →
# ``molecular.envelope`` → ``molecular.__init__`` →
# ``molecular.calibration_protocols`` → ``universal`` re-entry cycle.
# The ``__getattr__`` resolver below (registered as the LAST block of
# this module) evaluates ``adaptive_reflow.contracts.condition`` on
# first lookup, AFTER ``adaptive_reflow.universal`` has finished its
# own init. ``state.py`` already uses this lazy-import pattern for
# the same reason.
from .condition_injection import (
    AugmentingConditionInjector,
    ConditionInjectionProtocol,
    ConditionInjectorKind,
    NullConditionInjector,
    PassthroughConditionInjector,
    default_null_injector,
    validate_condition_injector,
)
from .envelope import (
    ArtifactHash,
    BundleId,
    ComplementBlockerCode,
    EnvelopeClassification,
    EnvelopeCriterion,
    Predicate,
    validate_envelope_classification,
    validate_envelope_criterion,
)
from .evaluator import (
    ArtifactHash as EvaluatorArtifactHash,
)
from .evaluator import (
    Evaluator,
    validate_evaluator_artifact_hash,
)
from .materialization import (
    EnvelopeState,
    HeterogeneousCategoricalMaterializer,
    LossTolerance,
    MATERIALIZER_NOOP_DIGEST,
    MaterializationRouteProtocol,
    MaterializerHandle,
    NativeStateBundle,
    NoOpMaterializer,
    default_materializer,
)
from .mixer import (
    DiscreteIdentityMixer,
    LatentConvexMixer,
    NoOpMixer,
    RestartMixer,
    TensorRef,
    validate_blend_inputs,
)
from .state import (
    NORMALIZATION_KINDS,
    REFERENCE_FRAMES,
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    validate_condition_delta,
    validate_integrator_trace,
    validate_state_bundle,
)
from .validators import (
    ValidationResult,
    validate_nonneg_int,
    validate_positive_int,
    validate_unit_factor,
    validate_unit_float,
)

__all__ = [
    # Pure-data carriers — state
    "ODEConditionDelta",
    "ODEIntegratorTrace",
    "StateBundle",
    # Pure-data carriers — adapter
    "AdapterCapabilities",
    # Pure-data carriers — envelope
    "EnvelopeClassification",
    "EnvelopeCriterion",
    # Pure-data carriers — materialization (D2)
    "EnvelopeState",
    "NativeStateBundle",
    # String enums
    "NORMALIZATION_KINDS",
    "REFERENCE_FRAMES",
    # NewType aliases — state
    "ChannelName",
    "TensorRef",
    # NewType aliases — adapter
    "ChannelDomain",
    "RestartPolicy",
    # NewType aliases — envelope
    "ArtifactHash",
    "BundleId",
    "ComplementBlockerCode",
    "Predicate",
    # NewType aliases — evaluator (alias)
    "EvaluatorArtifactHash",
    # NewType aliases — materialization (D2)
    "LossTolerance",
    "MATERIALIZER_NOOP_DIGEST",
    "MaterializerHandle",
    # Protocols
    "Condition",
    "ConditionInjectionProtocol",
    "ConditionInjectorKind",
    "ConditionKind",
    "Evaluator",
    "FlowMatchingODEAdapter",
    "MaterializationRouteProtocol",
    "RestartMixer",
    # Concrete condition kinds (D8)
    "BFNInpaintCondition",
    "CFGCondition",
    "CONDITION_KINDS",
    "InpaintingCondition",
    "MappingConditionAdapter",
    "NullCondition",
    "PropertyCondition",
    "condition_kind_of",
    "condition_to_mapping",
    "wrap_condition",
    # Concrete condition injectors (D3)
    "AugmentingConditionInjector",
    "NullConditionInjector",
    "PassthroughConditionInjector",
    "default_null_injector",
    # Concrete materializers (D2)
    "HeterogeneousCategoricalMaterializer",
    "NoOpMaterializer",
    "default_materializer",
    # Standard concrete mixers
    "DiscreteIdentityMixer",
    "LatentConvexMixer",
    "NoOpMixer",
    # Exceptions
    "CapabilityMismatchError",
    "CapabilityMissingError",
    # Validators — state / adapter
    "validate_capabilities",
    "validate_condition",
    "validate_condition_delta",
    "validate_condition_injector",
    "validate_integrator_trace",
    "validate_state_bundle",
    # Validators — envelope
    "validate_envelope_classification",
    "validate_envelope_criterion",
    # Validators — evaluator / mixer
    "validate_blend_inputs",
    "validate_evaluator_artifact_hash",
    # Validators — numeric
    "ValidationResult",
    "validate_nonneg_int",
    "validate_positive_int",
    "validate_unit_factor",
    "validate_unit_float",
]


# ---------------------------------------------------------------------------
# Lazy re-exports for the typed Condition discriminated union (D8).
#
# ``adaptive_reflow.contracts.condition`` is stdlib-only and depends on no
# other ``adaptive_reflow`` module, so a direct eager import is fine for
# NORMAL call sites. But importing the ``contracts`` package would
# trigger its eager ``__init__`` chain
# (``envelope`` → ``molecular.envelope`` → ``molecular.__init__`` →
# ``molecular.calibration_protocols`` → ``universal`` re-entry), which
# creates a circular import when ``molecular`` is mid-init. We resolve
# the cycle by importing the ``condition`` submodule DIRECTLY here
# AFTER all the other eager imports are settled — at this point the
# ``contracts`` package's __init__ may not have run yet, but importing
# ``adaptive_reflow.contracts.condition`` evaluates only that module
# (since Python resolves submodules lazily), bypassing the contracts
# package init chain entirely.
# ---------------------------------------------------------------------------

try:
    from adaptive_reflow.contracts import condition as _condition_module  # noqa: E402

    # Re-bind names into the universal namespace.
    BFNInpaintCondition = _condition_module.BFNInpaintCondition  # noqa: F811
    CFGCondition = _condition_module.CFGCondition  # noqa: F811
    CONDITION_KINDS = _condition_module.CONDITION_KINDS  # noqa: F811
    Condition = _condition_module.Condition  # noqa: F811
    ConditionKind = _condition_module.ConditionKind  # noqa: F811
    InpaintingCondition = _condition_module.InpaintingCondition  # noqa: F811
    MappingConditionAdapter = _condition_module.MappingConditionAdapter  # noqa: F811
    NullCondition = _condition_module.NullCondition  # noqa: F811
    PropertyCondition = _condition_module.PropertyCondition  # noqa: F811
    condition_kind_of = _condition_module.condition_kind_of  # noqa: F811
    condition_to_mapping = _condition_module.condition_to_mapping  # noqa: F811
    validate_condition = _condition_module.validate_condition  # noqa: F811
    wrap_condition = _condition_module.wrap_condition  # noqa: F811
    del _condition_module
except ImportError:
    # The contracts module may not be importable when ``adaptive_reflow`` is
    # partially initialized (e.g., mid-circular-import from ``molecular``).
    # In that case we provide a ``__getattr__`` shim that re-attempts the
    # import on first attribute access — this matches the
    # ``state.py``/``adapter.py`` lazy-import pattern already used elsewhere.
    _LAZY_CONDITION_NAMES = frozenset(
        {
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
        }
    )

    def __getattr__(name: str) -> Any:
        if name in _LAZY_CONDITION_NAMES:
            from adaptive_reflow.contracts import condition as _cond_mod

            value = getattr(_cond_mod, name)
            globals()[name] = value
            return value
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        )
