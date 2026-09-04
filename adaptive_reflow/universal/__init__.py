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

from .adapter import (
    AdapterCapabilities,
    CapabilityMismatchError,
    CapabilityMissingError,
    ChannelDomain,
    FlowMatchingODEAdapter,
    RestartPolicy,
    validate_capabilities,
)
# D8: typed Condition discriminated union (eagerly imported; the
# ``molecular -> universal.evaluator`` cycle was severed by the local
# Protocol declared in ``molecular.calibration_protocols``).
from .condition_injection import (
    AugmentingConditionInjector,
    ConditionInjectionProtocol,
    ConditionInjectorKind,
    NullConditionInjector,
    PassthroughConditionInjector,
    default_null_injector,
    validate_condition_injector,
)
from adaptive_reflow.contracts.condition import (
    BFNInpaintCondition,
    CFGCondition,
    CONDITION_KINDS,
    Condition,
    ConditionKind,
    InpaintingCondition,
    MappingConditionAdapter,
    NullCondition,
    PropertyCondition,
    condition_kind_of,
    condition_to_mapping,
    validate_condition,
    wrap_condition,
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

