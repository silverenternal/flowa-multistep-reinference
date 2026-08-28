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
    }
)

POLICY_DRIVER_FAMILIES: frozenset[str] = frozenset(
    {
        "schedule_derived",
        "constant",
        "adaptive",
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
    }
)

BLENDER_FAMILIES: frozenset[str] = frozenset(
    {
        "linear",
        "distance_decay",
        "ot_linear",
        "multi_temperature_distance_decay",
    }
)


# ---------------------------------------------------------------------------
# Lazy-import registry (avoids circular imports with the concrete modules)
# ---------------------------------------------------------------------------


def _build_scheduler_registry() -> dict[str, Any]:
    """Return the SchedulerProtocol family -> concrete-class registry."""
    from .scheduler import (
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
    from .scheduler_extra import (
        AdaptivePIDScheduler,
        EDMScheduler,
        JitteredConstantScheduler,
    )

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
        ScheduleDerivedPolicyDriver,
    )

    return {
        "schedule_derived": ScheduleDerivedPolicyDriver,
        "constant": ConstantPolicyDriver,
        "adaptive": AdaptivePolicyDriver,
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
        PIDIdentityOperator,
        ScheduleAwareEMAOperator,
    )

    return {
        "bounded": BoundedMergeOperator,
        "identity": IdentityOperator,
        "ema": EMAOperator,
        "kalman_bounded": KalmanBoundedMergeOperator,
        "bayesian": BayesianMergeOperator,
        "pid_identity": PIDIdentityOperator,
        "schedule_ema": ScheduleAwareEMAOperator,
    }


def _build_blender_registry() -> dict[str, Any]:
    from .blender import DistanceDecayBlender, LinearBlender
    from .blender_extra import (
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
    }


# Module-level lazy accessor. Built lazily so concrete modules can be
# imported without triggering a circular import at package load time.
_SCHEDULER_REG_CACHE: dict[str, Any] | None = None
_POLICY_DRIVER_REG_CACHE: dict[str, Any] | None = None
_MERGE_OPERATOR_REG_CACHE: dict[str, Any] | None = None
_BLENDER_REG_CACHE: dict[str, Any] | None = None


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
    """
    if PROTOCOL_REGISTRY:
        return
    PROTOCOL_REGISTRY["SchedulerProtocol"] = dict(_scheduler_registry())
    PROTOCOL_REGISTRY["PolicyDriverProtocol"] = dict(_policy_driver_registry())
    PROTOCOL_REGISTRY["MergeOperatorProtocol"] = dict(_merge_operator_registry())
    PROTOCOL_REGISTRY["RestartBlenderProtocol"] = dict(_blender_registry())


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
    "MERGE_OPERATOR_FAMILIES",
    "POLICY_DRIVER_FAMILIES",
    "PROTOCOL_REGISTRY",
    "ProtocolRegistryError",
    "SCHEDULER_FAMILIES",
    "build_blender_from_config",
    "build_merge_operator_from_config",
    "build_policy_driver_from_config",
    "build_scheduler_from_config",
    "enumerate_implementations",
    "registered_families",
    "validate_config_schema",
]
