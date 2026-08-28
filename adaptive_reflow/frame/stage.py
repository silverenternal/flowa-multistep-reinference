"""Stage Protocol + ``STAGE_REGISTRY`` for pluggable pipeline composition.

The algorithm-deep-uplift plan calls out a Stage Protocol as a P0
framework-level improvement: every stage of the
:class:`AdaptiveReflowPolicyOrchestrator` (run, calibration, claim
gate, promotion) becomes a pluggable :class:`Stage` implementation
registered in :data:`STAGE_REGISTRY`. The orchestrator then composes
the stages by reading the registry so each stage is independently
testable and the pipeline order is config-driven.

Module boundary
---------------

* stdlib-only.
* Each :class:`Stage` is a pure-data carrier (frozen dataclass) with
  a single ``stage_family`` identifier and ``run(input_state) ->
  output_state`` semantics.
* Fail-closed: bad / unknown family raises ``KeyError`` with the
  registered family list.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar, Protocol, runtime_checkable

from adaptive_reflow.contracts import hash_artifact


@runtime_checkable
class StageProtocol(Protocol):
    """Abstract pipeline stage.

    Implementations expose :attr:`stage_family` (a stable identifier),
    :attr:`config_hash` (a deterministic digest of the stage config),
    and :meth:`run(input_state) -> output_state` (the stage's
    transformation).
    """

    stage_family: str

    def config_hash(self) -> str: ...

    def run(self, input_state: Mapping[str, Any]) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# Concrete stages
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunStage:
    """Stage that executes one re-inference run."""

    stage_family: ClassVar[str] = "run"

    n_rounds: int = 20
    seed: int = 0
    adapter_family: str = "twodim_fm"
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.n_rounds, int) or isinstance(self.n_rounds, bool):
            raise ValueError(
                f"n_rounds must be int, got {self.n_rounds!r}"
            )
        if int(self.n_rounds) < 1:
            raise ValueError(
                f"n_rounds must be >= 1, got {self.n_rounds!r}"
            )
        if not isinstance(self.adapter_family, str):
            raise ValueError(
                "adapter_family must be str, got "
                f"{type(self.adapter_family).__name__}"
            )

    def config_hash(self) -> str:
        return str(
            hash_artifact(
                {
                    "stage_family": self.stage_family,
                    "n_rounds": int(self.n_rounds),
                    "seed": int(self.seed),
                    "adapter_family": str(self.adapter_family),
                    "extra": dict(self.extra),
                }
            )
        )

    def run(self, input_state: Mapping[str, Any]) -> dict[str, Any]:
        # The actual run is performed by the orchestrator wiring; this
        # stub returns a typed output that downstream stages can
        # consume.
        return {
            "stage": self.stage_family,
            "input_keys": sorted(input_state.keys()),
            "n_rounds": int(self.n_rounds),
            "seed": int(self.seed),
            "adapter_family": str(self.adapter_family),
            "config_hash": self.config_hash(),
        }


@dataclass(frozen=True)
class CalibrationStage:
    """Stage that runs calibration on the latest run output."""

    stage_family: ClassVar[str] = "calibration"

    n_buckets: int = 5
    confidence: float = 0.95

    def __post_init__(self) -> None:
        if not isinstance(self.n_buckets, int) or isinstance(self.n_buckets, bool):
            raise ValueError(
                f"n_buckets must be int, got {self.n_buckets!r}"
            )
        if int(self.n_buckets) < 1:
            raise ValueError(
                f"n_buckets must be >= 1, got {self.n_buckets!r}"
            )
        if (
            not isinstance(self.confidence, (int, float))
            or isinstance(self.confidence, bool)
        ):
            raise ValueError(
                f"confidence must be a real number, got {self.confidence!r}"
            )
        cf = float(self.confidence)
        if not (0.0 < cf < 1.0):
            raise ValueError(
                f"confidence must be in (0, 1), got {cf!r}"
            )

    def config_hash(self) -> str:
        return str(
            hash_artifact(
                {
                    "stage_family": self.stage_family,
                    "n_buckets": int(self.n_buckets),
                    "confidence": float(self.confidence),
                }
            )
        )

    def run(self, input_state: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "stage": self.stage_family,
            "n_buckets": int(self.n_buckets),
            "confidence": float(self.confidence),
            "config_hash": self.config_hash(),
            "input_keys": sorted(input_state.keys()),
        }


@dataclass(frozen=True)
class ClaimGateStage:
    """Stage that evaluates the promotion claim gate."""

    stage_family: ClassVar[str] = "claim_gate"

    min_w2: float = 0.05
    min_coverage: float = 0.8
    min_selection_ratio: float = 0.7

    def __post_init__(self) -> None:
        for nm, val in (
            ("min_w2", self.min_w2),
            ("min_coverage", self.min_coverage),
            ("min_selection_ratio", self.min_selection_ratio),
        ):
            if (
                not isinstance(val, (int, float))
                or isinstance(val, bool)
            ):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not (0.0 <= fv <= 1.0):
                raise ValueError(
                    f"{nm} must lie in [0, 1], got {fv!r}"
                )

    def config_hash(self) -> str:
        return str(
            hash_artifact(
                {
                    "stage_family": self.stage_family,
                    "min_w2": float(self.min_w2),
                    "min_coverage": float(self.min_coverage),
                    "min_selection_ratio": float(self.min_selection_ratio),
                }
            )
        )

    def run(self, input_state: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "stage": self.stage_family,
            "min_w2": float(self.min_w2),
            "min_coverage": float(self.min_coverage),
            "min_selection_ratio": float(self.min_selection_ratio),
            "config_hash": self.config_hash(),
            "input_keys": sorted(input_state.keys()),
        }


@dataclass(frozen=True)
class PromotionStage:
    """Stage that finalises a promotion decision based on prior outputs."""

    stage_family: ClassVar[str] = "promotion"

    policy_version: str = "v0.0.0"
    route: str = "default"

    def __post_init__(self) -> None:
        if not isinstance(self.policy_version, str) or not self.policy_version:
            raise ValueError(
                f"policy_version must be non-empty str, got {self.policy_version!r}"
            )
        if not isinstance(self.route, str) or not self.route:
            raise ValueError(
                f"route must be non-empty str, got {self.route!r}"
            )

    def config_hash(self) -> str:
        return str(
            hash_artifact(
                {
                    "stage_family": self.stage_family,
                    "policy_version": str(self.policy_version),
                    "route": str(self.route),
                }
            )
        )

    def run(self, input_state: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "stage": self.stage_family,
            "policy_version": str(self.policy_version),
            "route": str(self.route),
            "config_hash": self.config_hash(),
            "input_keys": sorted(input_state.keys()),
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


STAGE_REGISTRY: dict[str, type[Any]] = {
    "run": RunStage,
    "calibration": CalibrationStage,
    "claim_gate": ClaimGateStage,
    "promotion": PromotionStage,
}
"""Mapping from stage family to its implementation class.

Each stage is a frozen dataclass implementing :class:`StageProtocol`.
Callers compose a pipeline by reading
``STAGE_REGISTRY[family](...)`` for each stage in their pipeline
order.
"""


# Module-level Stage base class for downstream subclasses (ABC
# alternative to the runtime_checkable Protocol).
class Stage(ABC):
    """ABC base class for Stages (alternative to the Protocol surface)."""

    stage_family: ClassVar[str] = ""

    @abstractmethod
    def config_hash(self) -> str:
        ...

    @abstractmethod
    def run(self, input_state: Mapping[str, Any]) -> dict[str, Any]:
        ...


def build_stage(family: str, **kwargs: Any) -> Any:
    """Return a fresh :class:`Stage` instance for ``family``."""
    if not isinstance(family, str):
        raise ValueError(f"family must be str, got {family!r}")
    if family not in STAGE_REGISTRY:
        raise KeyError(
            f"unknown stage family {family!r}; "
            f"registered families: {sorted(STAGE_REGISTRY)!r}"
        )
    cls = STAGE_REGISTRY[family]
    return cls(**kwargs)


__all__ = [
    "CalibrationStage",
    "ClaimGateStage",
    "PromotionStage",
    "RunStage",
    "STAGE_REGISTRY",
    "Stage",
    "StageProtocol",
    "build_stage",
]
