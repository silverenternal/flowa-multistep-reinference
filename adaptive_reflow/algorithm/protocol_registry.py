"""Central registry for every pluggable algorithm-layer Protocol.

The pluggable abstract-impl design lives here as the single source of
truth for which concrete implementations back each Protocol surface.
The framework depends only on the abstract Protocols
(:class:`SchedulerProtocol`, :class:`PolicyDriverProtocol`,
:class:`MergeOperatorProtocol`, :class:`RestartBlenderProtocol`); every
concrete implementation is dispatched through this module so callers
never have to import the concrete classes by name.

Module boundary
---------------

* stdlib-only. No ``torch``. No I/O. No global mutable state beyond
  the module-level registry dicts.
* Every public builder accepts a typed config dict (the output of
  ``to_config()`` on the corresponding concrete class) and dispatches
  on the ``family`` key against the registry.
* Bad input fails closed with a ``ValueError`` / ``KeyError`` carrying
  the supported family list so misconfigurations cannot silently fall
  back to a default.

Public surface
--------------

* :func:`build_scheduler_from_config` — polymorphic SchedulerProtocol
  factory (re-exported from :mod:`adaptive_reflow.algorithm.scheduler`).
* :func:`build_policy_driver_from_config` — polymorphic
  PolicyDriverProtocol factory.
* :func:`build_merge_operator_from_config` — polymorphic
  MergeOperatorProtocol factory.
* :func:`build_blender_from_config` — polymorphic
  RestartBlenderProtocol factory.
* :data:`PROTOCOL_REGISTRY` — flat name -> implementation registry.
* :func:`registered_families` — enumerate every registered family
  across all Protocols.
* :func:`validate_config_schema` — fail-closed schema validation.
"""
from __future__ import annotations

import contextlib
from collections.abc import Iterable, Mapping
from typing import Any, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Family-name conventions
# ---------------------------------------------------------------------------


SCHEDULER_FAMILIES: frozenset[str] = frozenset(
    {
        "cosine",
        "constant",
        "linear",
        "exponential",
        "polynomial",
        "sigmoid",
        "convergence_adaptive",
        "codimension_sheet",
        "sequential",
        "edm",
        "adaptive_pid",
        "jittered_constant",
        "warmup_linear",
        "geometric",
        "piecewise_sigmoid",
        "handoff",
        "handoff_sequential",
        "multi_channel_jittered",
    }
)

POLICY_DRIVER_FAMILIES: frozenset[str] = frozenset(
    {
        "schedule_derived",
        "constant",
        "adaptive",
        "multi_channel_constant",
        "dual_target_adaptive",
    }
)

MERGE_OPERATOR_FAMILIES: frozenset[str] = frozenset(
    {
        "bounded",
        "identity",
        "ema",
        "kalman_bounded",
        "bayesian",
        "pid_identity",
        "schedule_ema",
        "multi_source_kalman",
    }
)

BLENDER_FAMILIES: frozenset[str] = frozenset(
    {
        "linear",
        "distance_decay",
        "ot_linear",
        "multi_temperature_distance_decay",
        "joint_ot_linear",
        "barycentric",
    }
)

DYNAMICS_FAMILIES: frozenset[str] = frozenset(
    {
        "continuous_fm",
        "ctmc",
        "bfn",
        "flowmol3_composite",
        "protbfn_bfn",
    }
)

SOLVER_FAMILIES: frozenset[str] = frozenset(
    {
        "euler",
        "rk4",
        "heun",
        "adaptive_rk4",
        "ctmc_euler_heun",
        "bfn",
    }
)


# ---------------------------------------------------------------------------
# Lazy-import registry (avoids circular imports with the concrete modules)
# ---------------------------------------------------------------------------


def _build_scheduler_registry() -> dict[str, Any]:
    """Return the SchedulerProtocol family -> concrete-class registry."""
    from .scheduler._core import (
        CodimensionSheetScheduler,
        ConstantScheduler,
        ConvergenceAdaptiveScheduler,
        CosineAnnealScheduler,
        ExponentialScheduler,
        LinearScheduler,
        PolynomialScheduler,
        SigmoidScheduler,
        default_cosine_scheduler,
    )
    from .scheduler.evidence_driven import EvidenceDrivenScheduler
    from .scheduler.freetraj import FreeTrajScheduler
    from .scheduler_extra import (
        AdaptivePIDScheduler,
        EDMScheduler,
        JitteredConstantScheduler,
        MultiChannelJitteredConstantScheduler,
    )
    from .sequential_handoff import HandoffSequentialScheduler

    reg: dict[str, Any] = {
        "cosine": CosineAnnealScheduler,
        "constant": ConstantScheduler,
        "linear": LinearScheduler,
        "exponential": ExponentialScheduler,
        "polynomial": PolynomialScheduler,
        "sigmoid": SigmoidScheduler,
        "convergence_adaptive": ConvergenceAdaptiveScheduler,
        "codimension_sheet": CodimensionSheetScheduler,
        "edm": EDMScheduler,
        "adaptive_pid": AdaptivePIDScheduler,
        "jittered_constant": JitteredConstantScheduler,
        "multi_channel_jittered": MultiChannelJitteredConstantScheduler,
        "handoff_sequential": HandoffSequentialScheduler,
        "evidence_driven": EvidenceDrivenScheduler,
        "freetraj": FreeTrajScheduler,
    }
    # Cosine factory defaults live behind a kwargs API rather than the
    # bare constructor; expose it under the same family key so callers
    # can use ``build_scheduler("cosine")`` without exposing the
    # CosineScheduleConfig round-trip.
    reg["cosine_factory"] = default_cosine_scheduler
    return reg


def _build_policy_driver_registry() -> dict[str, Any]:
    from .policy_driver import (
        AdaptivePolicyDriver,
        ConstantPolicyDriver,
        DualTargetAdaptivePolicyDriver,
        MultiChannelConstantPolicyDriver,
        ScheduleDerivedPolicyDriver,
    )

    return {
        "schedule_derived": ScheduleDerivedPolicyDriver,
        "constant": ConstantPolicyDriver,
        "adaptive": AdaptivePolicyDriver,
        "multi_channel_constant": MultiChannelConstantPolicyDriver,
        "dual_target_adaptive": DualTargetAdaptivePolicyDriver,
    }


def _build_merge_operator_registry() -> dict[str, Any]:
    from .merge_operator import (
        BoundedMergeOperator,
        EMAOperator,
        IdentityOperator,
    )
    from .merge_operator_extra import (
        BayesianMergeOperator,
        KalmanBoundedMergeOperator,
        MultiSourceKalmanMergeOperator,
        PIDIdentityOperator,
        ScheduleAwareEMAOperator,
    )
    from .merge_operator_v3 import MeanFlowMergeOperator

    return {
        "bounded": BoundedMergeOperator,
        "identity": IdentityOperator,
        "ema": EMAOperator,
        "kalman_bounded": KalmanBoundedMergeOperator,
        "bayesian": BayesianMergeOperator,
        "pid_identity": PIDIdentityOperator,
        "schedule_ema": ScheduleAwareEMAOperator,
        "multi_source_kalman": MultiSourceKalmanMergeOperator,
        "meanflow": MeanFlowMergeOperator,
    }


def _build_blender_registry() -> dict[str, Any]:
    from .blender import DistanceDecayBlender, LinearBlender
    from .blender_extra import (
        BarycentricBlender,
        JointOTLinearBlender,
        MultiTemperatureDistanceDecayBlender,
        OTLinearBlender,
    )

    return {
        "linear": LinearBlender,
        "distance_decay": DistanceDecayBlender,
        "ot_linear": OTLinearBlender,
        "multi_temperature_distance_decay": (
            MultiTemperatureDistanceDecayBlender
        ),
        "joint_ot_linear": JointOTLinearBlender,
        "barycentric": BarycentricBlender,
    }


def _build_dynamics_registry() -> dict[str, Any]:
    from .dynamics import (
        BFNDynamics,
        ContinuousFMDynamics,
        CTMCDynamics,
        FlowMol3Dynamics,
        ProtBFNDynamics,
    )

    return {
        "continuous_fm": ContinuousFMDynamics,
        "ctmc": CTMCDynamics,
        "bfn": BFNDynamics,
        "flowmol3_composite": FlowMol3Dynamics,
        "protbfn_bfn": ProtBFNDynamics,
    }


def _build_solver_registry() -> dict[str, Any]:
    from .solver import (
        AdaptiveRK4Solver,
        BFNSolver,
        CTMCEulerHeunSolver,
        EulerSolver,
        HeunSolver,
        RK4Solver,
    )

    return {
        "euler": EulerSolver,
        "rk4": RK4Solver,
        "heun": HeunSolver,
        "adaptive_rk4": AdaptiveRK4Solver,
        "ctmc_euler_heun": CTMCEulerHeunSolver,
        "bfn": BFNSolver,
    }


# Module-level lazy accessor. Built lazily so concrete modules can be
# imported without triggering a circular import at package load time.
_SCHEDULER_REG_CACHE: dict[str, Any] | None = None
_POLICY_DRIVER_REG_CACHE: dict[str, Any] | None = None
_MERGE_OPERATOR_REG_CACHE: dict[str, Any] | None = None
_BLENDER_REG_CACHE: dict[str, Any] | None = None
_DYNAMICS_REG_CACHE: dict[str, Any] | None = None
_SOLVER_REG_CACHE: dict[str, Any] | None = None


def _scheduler_registry() -> dict[str, Any]:
    global _SCHEDULER_REG_CACHE
    if _SCHEDULER_REG_CACHE is None:
        _SCHEDULER_REG_CACHE = _build_scheduler_registry()
    return _SCHEDULER_REG_CACHE


def _policy_driver_registry() -> dict[str, Any]:
    global _POLICY_DRIVER_REG_CACHE
    if _POLICY_DRIVER_REG_CACHE is None:
        _POLICY_DRIVER_REG_CACHE = _build_policy_driver_registry()
    return _POLICY_DRIVER_REG_CACHE


def _merge_operator_registry() -> dict[str, Any]:
    global _MERGE_OPERATOR_REG_CACHE
    if _MERGE_OPERATOR_REG_CACHE is None:
        _MERGE_OPERATOR_REG_CACHE = _build_merge_operator_registry()
    return _MERGE_OPERATOR_REG_CACHE


def _blender_registry() -> dict[str, Any]:
    global _BLENDER_REG_CACHE
    if _BLENDER_REG_CACHE is None:
        _BLENDER_REG_CACHE = _build_blender_registry()
    return _BLENDER_REG_CACHE


def _dynamics_registry() -> dict[str, Any]:
    global _DYNAMICS_REG_CACHE
    if _DYNAMICS_REG_CACHE is None:
        _DYNAMICS_REG_CACHE = _build_dynamics_registry()
    return _DYNAMICS_REG_CACHE


def _solver_registry() -> dict[str, Any]:
    global _SOLVER_REG_CACHE
    if _SOLVER_REG_CACHE is None:
        _SOLVER_REG_CACHE = _build_solver_registry()
    return _SOLVER_REG_CACHE


# ---------------------------------------------------------------------------
# Protocol REGISTRY (flat, for tooling) — defined BEFORE the auto-populate
# hook so the mutation targets the live module-level dict.
# ---------------------------------------------------------------------------


PROTOCOL_REGISTRY: dict[str, dict[str, Any]] = {}
"""Flat registry mapping ``protocol_name -> {family_name: class_or_factory}``.

Populated at module load time via :func:`_ensure_protocol_registry` so
callers see the full registry immediately after import.
"""


def _ensure_protocol_registry() -> None:
    """Populate :data:`PROTOCOL_REGISTRY` from the per-protocol registries.

    Idempotent: re-invocations after the dict is populated are no-ops.

    Dispatches through ``adaptive_reflow.manifest`` (D1 — Hexagonal port
    set, ``docs/r3-survey/08-fix-plan.md`` §3): the legacy flat-name
    dict is now a *view* over the manifest's registered families, so the
    two surfaces can never drift. The manifest is populated lazily on
    first call so this function remains safe to call from module import
    time.
    """
    if PROTOCOL_REGISTRY:
        return
    # Lazy import to avoid a circular dependency: ``manifest`` does not
    # import this module, but the package import graph visits
    # ``manifest`` -> ``protocol_registry`` -> ``scheduler`` etc.; a
    # top-level import here would create the cycle.
    try:
        from ..manifest import register_all_default, rewire_protocol_registry_from_manifest

        # Populate the default manifest singleton with the canonical
        # stock implementations; ``register_all_default`` is idempotent
        # so re-invocations are no-ops.
        register_all_default(replace=False)
        rewire_protocol_registry_from_manifest()
    except (ImportError, AttributeError):
        # Fallback: if the manifest module is unavailable (rare import
        # edge case during package bootstrap), fall back to the legacy
        # per-protocol builders so callers always see a populated
        # ``PROTOCOL_REGISTRY``.
        PROTOCOL_REGISTRY["SchedulerProtocol"] = dict(_scheduler_registry())
        PROTOCOL_REGISTRY["PolicyDriverProtocol"] = dict(_policy_driver_registry())
        PROTOCOL_REGISTRY["MergeOperatorProtocol"] = dict(_merge_operator_registry())
        PROTOCOL_REGISTRY["RestartBlenderProtocol"] = dict(_blender_registry())
        PROTOCOL_REGISTRY["DynamicsProtocol"] = dict(_dynamics_registry())
        PROTOCOL_REGISTRY["IntegratorProtocol"] = dict(_solver_registry())


# Auto-populate PROTOCOL_REGISTRY on import so callers see the full
# registry immediately without having to call
# ``_ensure_protocol_registry`` first. Wrapped in a suppress so a
# downstream concrete-module failure doesn't break the module load.
with contextlib.suppress(Exception):
    _ensure_protocol_registry()


def registered_families() -> dict[str, tuple[str, ...]]:
    """Return ``{protocol_name: tuple(family, ...)}`` for every Protocol.

    The returned families are sorted so the output is stable across
    runs and Python versions.
    """
    _ensure_protocol_registry()
    return {
        name: tuple(sorted(reg.keys()))
        for name, reg in PROTOCOL_REGISTRY.items()
    }


# ---------------------------------------------------------------------------
# Schema validation (fail-closed)
# ---------------------------------------------------------------------------


class ProtocolRegistryError(KeyError):
    """Raised when a config refers to an unknown Protocol family.

    Subclasses :class:`KeyError` for backward compatibility with
    existing ``pytest.raises(KeyError)`` patterns; the message
    includes the full supported family list so callers can recover.
    """


def _validate_family(
    config: Mapping[str, Any],
    *,
    protocol_name: str,
    registry: Mapping[str, Any],
) -> str:
    """Return the validated ``family`` key from ``config``.

    Raises :exc:`ProtocolRegistryError` if the config is not a dict, if
    the ``family`` key is missing or not a string, or if the family is
    not present in ``registry``.
    """
    if not isinstance(config, Mapping):
        raise ProtocolRegistryError(
            f"{protocol_name}: config must be a Mapping, got "
            f"{type(config).__name__}"
        )
    family = config.get("family")
    if not isinstance(family, str):
        raise ProtocolRegistryError(
            f"{protocol_name}: config['family'] must be a string, "
            f"got {family!r}"
        )
    if family not in registry:
        raise ProtocolRegistryError(
            f"{protocol_name}: unsupported family {family!r}; "
            f"registered families: {sorted(registry)!r}"
        )
    return family


def validate_config_schema(
    config: Mapping[str, Any],
    *,
    protocol_name: str,
) -> str:
    """Validate ``config`` against the schema for ``protocol_name``.

    Returns the validated ``family`` key on success. Raises
    :exc:`ProtocolRegistryError` on bad input (fail-closed).
    """
    _ensure_protocol_registry()
    if protocol_name not in PROTOCOL_REGISTRY:
        raise ProtocolRegistryError(
            f"unknown protocol {protocol_name!r}; registered protocols: "
            f"{sorted(PROTOCOL_REGISTRY)!r}"
        )
    return _validate_family(
        config,
        protocol_name=protocol_name,
        registry=PROTOCOL_REGISTRY[protocol_name],
    )


# ---------------------------------------------------------------------------
# Polymorphic builders
# ---------------------------------------------------------------------------


def build_scheduler_from_config(config: Mapping[str, Any]) -> Any:
    """Polymorphic :class:`SchedulerProtocol` factory."""
    family = validate_config_schema(config, protocol_name="SchedulerProtocol")
    cls = PROTOCOL_REGISTRY["SchedulerProtocol"][family]
    return cls.from_config(dict(config))


def build_policy_driver_from_config(config: Mapping[str, Any]) -> Any:
    """Polymorphic :class:`PolicyDriverProtocol` factory."""
    family = validate_config_schema(config, protocol_name="PolicyDriverProtocol")
    cls = PROTOCOL_REGISTRY["PolicyDriverProtocol"][family]
    return cls.from_config(dict(config))


def build_merge_operator_from_config(config: Mapping[str, Any]) -> Any:
    """Polymorphic :class:`MergeOperatorProtocol` factory."""
    family = validate_config_schema(config, protocol_name="MergeOperatorProtocol")
    cls = PROTOCOL_REGISTRY["MergeOperatorProtocol"][family]
    return cls.from_config(dict(config))


def build_blender_from_config(config: Mapping[str, Any]) -> Any:
    """Polymorphic :class:`RestartBlenderProtocol` factory."""
    family = validate_config_schema(config, protocol_name="RestartBlenderProtocol")
    cls = PROTOCOL_REGISTRY["RestartBlenderProtocol"][family]
    return cls.from_config(dict(config))


def build_dynamics_from_config(config: Mapping[str, Any]) -> Any:
    """Polymorphic :class:`DynamicsProtocol` factory."""
    family = validate_config_schema(config, protocol_name="DynamicsProtocol")
    cls = PROTOCOL_REGISTRY["DynamicsProtocol"][family]
    return cls.from_config(dict(config))


def build_solver_from_config(config: Mapping[str, Any]) -> Any:
    """Polymorphic :class:`IntegratorProtocol` factory."""
    family = validate_config_schema(config, protocol_name="IntegratorProtocol")
    cls = PROTOCOL_REGISTRY["IntegratorProtocol"][family]
    return cls.from_config(dict(config))


def enumerate_implementations(
    protocol_name: str,
) -> Iterable[tuple[str, Any]]:
    """Yield ``(family, cls)`` pairs for every registered implementation."""
    _ensure_protocol_registry()
    if protocol_name not in PROTOCOL_REGISTRY:
        raise ProtocolRegistryError(
            f"unknown protocol {protocol_name!r}; registered protocols: "
            f"{sorted(PROTOCOL_REGISTRY)!r}"
        )
    yield from sorted(PROTOCOL_REGISTRY[protocol_name].items())


__all__ = [
    "BLENDER_FAMILIES",
    "DYNAMICS_FAMILIES",
    "MERGE_OPERATOR_FAMILIES",
    "POLICY_DRIVER_FAMILIES",
    "PROTOCOL_REGISTRY",
    "ProtocolRegistryError",
    "SCHEDULER_FAMILIES",
    "SOLVER_FAMILIES",
    "build_blender_from_config",
    "build_dynamics_from_config",
    "build_merge_operator_from_config",
    "build_policy_driver_from_config",
    "build_scheduler_from_config",
    "build_solver_from_config",
    "enumerate_implementations",
    "registered_families",
    "validate_config_schema",
]
