"""Per-family scheduler subpackage.

Aggregates the canonical scheduler surface (``_core`` — the legacy
``adaptive_reflow.algorithm.scheduler`` module, here renamed to
``scheduler._core``) with the new per-family modules shipped with
the round-3 framework (C4 — ``EvidenceDrivenScheduler``; A1 —
``FreeTrajScheduler``).

The legacy scheduler module (``_core``) preserves its full public
surface so existing imports
``from adaptive_reflow.algorithm.scheduler import CosineAnnealScheduler``
continue to work; the per-family modules in this package contribute
the new ``evidence_driven`` / ``freetraj`` families.

Public surface
--------------

* The canonical :class:`SchedulerProtocol`, :class:`CosineAnnealScheduler`,
  and friends (``_core`` re-export).
* :class:`EvidenceDrivenScheduler` — C4, closes Loop 2
  (paper-quantities → scheduler feedback) via a PID-lite controller
  driven by ``evidence_ratio``.
* :class:`FreeTrajScheduler` — A1, training-free trajectory control on
  a rectified-flow model (arXiv:2507.10532).
"""

from __future__ import annotations

from ._core import (
    SCHEDULER_REGISTRY,
    CodimensionSheetScheduler,
    ConstantScheduler,
    ConvergenceAdaptiveScheduler,
    CosineAnnealScheduler,
    CosineScheduleConfig,
    ExponentialScheduler,
    LinearScheduler,
    PolynomialScheduler,
    SchedulerProtocol,
    ScheduleSample,
    ScheduleSampleProtocol,
    SigmoidScheduler,
    _coerce_int_nonneg,
    _paper_evidence_balance,
    build_scheduler,
    build_scheduler_from_config,
    default_cosine_scheduler,
)
from .evidence_driven import (
    EVIDENCE_PID_ADJUSTED,
    EVIDENCE_PID_SATURATED,
    EVIDENCE_RATIO_MISSING,
    EvidenceDrivenScheduler,
)
from .freetraj import FREETRAJ_SUBSTEP_AUDIT, FreeTrajScheduler

__all__ = [
    "EVIDENCE_PID_ADJUSTED",
    "EVIDENCE_PID_SATURATED",
    "EVIDENCE_RATIO_MISSING",
    "EvidenceDrivenScheduler",
    "FREETRAJ_SUBSTEP_AUDIT",
    "FreeTrajScheduler",
    "SCHEDULER_REGISTRY",
    "CodimensionSheetScheduler",
    "ConstantScheduler",
    "ConvergenceAdaptiveScheduler",
    "CosineAnnealScheduler",
    "CosineScheduleConfig",
    "ExponentialScheduler",
    "LinearScheduler",
    "PolynomialScheduler",
    "ScheduleSample",
    "ScheduleSampleProtocol",
    "SchedulerProtocol",
    "SigmoidScheduler",
    "_coerce_int_nonneg",
    "_paper_evidence_balance",
    "build_scheduler",
    "build_scheduler_from_config",
    "default_cosine_scheduler",
]
