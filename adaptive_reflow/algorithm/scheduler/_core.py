"""Per-round capacity scheduler (re-export shim, Wave 105 P2-A).

CLM-042 derivation note: scheduler exports below retain the paper-grounded
capacity and evidence-balance implementation from the canonical submodules;
the merge-floor companion is expressed as ``e_rho / 4``.

The scheduler implementation is split across four submodules:

* :mod:`adaptive_reflow.algorithm.scheduler.protocols` — the
  :class:`ScheduleSample` dataclass + :class:`SchedulerProtocol` /
  :class:`ScheduleSampleProtocol` ``Protocol`` types + the private
  :func:`_coerce_int_nonneg` validator.
* :mod:`adaptive_reflow.algorithm.scheduler.simple` — the six
  non-adaptive families (:class:`CosineAnnealScheduler`,
  :class:`ConstantScheduler`, :class:`LinearScheduler`,
  :class:`ExponentialScheduler`, :class:`PolynomialScheduler`,
  :class:`SigmoidScheduler`) plus the canonical default factories
  (:func:`default_paper_ratio_scheduler`,
  :func:`default_cosine_scheduler`).
* :mod:`adaptive_reflow.algorithm.scheduler.adaptive` — the three
  adaptive families (:class:`ConvergenceAdaptiveScheduler`,
  :class:`CodimensionSheetScheduler`,
  :class:`PaperRatioAdaptiveScheduler`) plus the default-weight
  constants and the closed-form sheet-vs-cell evidence helper
  :func:`_paper_evidence_balance`.
* :mod:`adaptive_reflow.algorithm.scheduler.nfe_aware` — the
  :class:`NFEAwareMemoryScheduler` plus the registry / factory
  helpers (:data:`SCHEDULER_REGISTRY`, :func:`build_scheduler`,
  :func:`build_scheduler_from_config`) and the
  :func:`derive_default_*` parameter-derivation entry points.

This module re-exports every symbol the historical ``_core`` surface
exposed so all ``from adaptive_reflow.algorithm.scheduler._core import
...`` call sites (24+ across tests and tools) continue to work
without modification. The split is **purely structural** — no class /
function / module / parameter is renamed or removed, and no
scheduler / adapter / runner / merge-operator behaviour is changed.

Import order matters here. ``batched_runner`` -> ``scheduler`` is a
cycle that historically was kept closed because the partial
``_core`` module exposed ``SchedulerProtocol`` early (the original
monolithic ``_core.py`` defined the ``SchedulerProtocol`` ``Protocol``
class at line 177, *before* any import that could re-enter the
scheduler package). This shim preserves the same property by
importing :mod:`.protocols` first so that the partial module
exposes ``SchedulerProtocol`` even if the next import
(``adaptive``) re-enters the scheduler package during a
``_derivation``-side cycle.
"""

from __future__ import annotations

# Import protocols FIRST so the partial module exposes SchedulerProtocol
# (and ScheduleSample + ScheduleSampleProtocol + the private
# :func:`_coerce_int_nonneg` validator) before any later import can
# re-enter the scheduler package. This mirrors the
# SchedulerProtocol-defined-at-line-177 ordering of the original
# monolithic _core.py and keeps the batched_runner -> scheduler ->
# _derivation -> batched_runner cycle closed at module-load time.
#
# We must explicitly import :func:`_coerce_int_nonneg` here because
# leading-underscore names are excluded from ``import *`` semantics;
# the historical ``__init__.py`` re-exports it via the explicit
# ``from ._core import _coerce_int_nonneg`` line.
from .protocols import (  # noqa: F401
    ScheduleSample,
    ScheduleSampleProtocol,
    SchedulerProtocol,
    _coerce_int_nonneg,
)

# Re-export ``CosineScheduleConfig`` from :mod:`adaptive_reflow.contracts`
# (already imported at module top in the simple / adaptive submodules).
# Listed below so downstream modules can
# ``from adaptive_reflow.algorithm.scheduler._core import
#  CosineScheduleConfig`` via this module's surface.
from adaptive_reflow.contracts import CosineScheduleConfig  # noqa: F401

from .adaptive import _paper_evidence_balance  # noqa: F401

from .adaptive import *  # noqa: F401, F403
from .nfe_aware import *  # noqa: F401, F403
from .simple import *  # noqa: F401, F403
