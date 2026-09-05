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
    PaperRatioAdaptiveScheduler,
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
    default_paper_ratio_scheduler,
)
from .evidence_driven import (
    EVIDENCE_PID_ADJUSTED,
    EVIDENCE_PID_SATURATED,
    EVIDENCE_RATIO_MISSING,
    EVIDENCE_REGIME_GATED,
    EvidenceDrivenScheduler,
    REGIME_VIOLATION_WARNING,
)
from .freetraj import FREETRAJ_SUBSTEP_AUDIT, FreeTrajScheduler
from .regime_selector import (
    DEFAULT_REGIME_SLACK,
    EPS_FLOOR,
    EPS_REGIME_CLAMPED,
    EPS_REGIME_INFEASIBLE,
    EPS_REGIME_OK,
    REGIME_SELECTOR_REGISTRY,
    ConvergenceAdaptiveRegimeSelector,
    CosineAnnealRegimeSelector,
    RegimeAwareEpsSelector,
    RegimeSelection,
    build_regime_selector,
    default_e_rho_provider,
    regime_ceiling,
    regime_holds,
)

__all__ = [
    "DEFAULT_REGIME_SLACK",
    "EPS_FLOOR",
    "EPS_REGIME_CLAMPED",
    "EPS_REGIME_INFEASIBLE",
    "EPS_REGIME_OK",
    "EVIDENCE_PID_ADJUSTED",
    "EVIDENCE_PID_SATURATED",
    "EVIDENCE_RATIO_MISSING",
    "EVIDENCE_REGIME_GATED",
    "EvidenceDrivenScheduler",
    "FREETRAJ_SUBSTEP_AUDIT",
    "FreeTrajScheduler",
    "REGIME_SELECTOR_REGISTRY",
    "REGIME_VIOLATION_WARNING",
    "SCHEDULER_REGISTRY",
    "CodimensionSheetScheduler",
    "ConstantScheduler",
    "ConvergenceAdaptiveRegimeSelector",
    "ConvergenceAdaptiveScheduler",
    "CosineAnnealRegimeSelector",
    "CosineAnnealScheduler",
    "CosineScheduleConfig",
    "ExponentialScheduler",
    "LinearScheduler",
    "PolynomialScheduler",
    "RegimeAwareEpsSelector",
    "RegimeSelection",
    "SigmoidScheduler",
    "ScheduleSample",
    "ScheduleSampleProtocol",
    "SchedulerProtocol",
    "_coerce_int_nonneg",
    "_paper_evidence_balance",
    "build_regime_selector",
    "build_scheduler",
    "build_scheduler_from_config",
    "default_cosine_scheduler",
    "default_e_rho_provider",
    "default_paper_ratio_scheduler",
    "regime_ceiling",
    "regime_holds",
]
