"""Thin shim — FlowA framework engine entry point.

The canonical runner lives at :mod:`adaptive_reflow.algorithm.runner.runner`.
This ``engine`` module is a re-export shim that lets reviewers invoke the
framework via ``python -m adaptive_reflow.framework.engine`` as documented
in ``RELEASE-NOTES-v3.0.md`` §Quick reference and the TPAMI submission
``Dockerfile``.

The re-export covers the three public surface classes:

* :class:`ReInferenceConfig` — input config (n_rounds, seed, channels).
* :class:`ReInferenceResult` — output bundle (round traces, endpoints,
  metrics, algorithm signatures).
* :class:`ReInferenceRunner` — orchestrator.

A future release may add a ``main()`` CLI entry point here (currently the
``engine`` module defers all execution to the canonical
``ReInferenceRunner.run(...)`` API; callers invoke it programmatically).

This module is intentionally small (re-export only) and does not own
any algorithm logic. See :mod:`adaptive_reflow.algorithm.runner.runner`
for the full implementation.
"""

from __future__ import annotations

from adaptive_reflow.algorithm.runner.runner import (
    FORWARD_NOISE_INJECTED,
    ReInferenceConfig,
    ReInferenceResult,
    ReInferenceRunner,
)

__all__ = [
    "FORWARD_NOISE_INJECTED",
    "ReInferenceConfig",
    "ReInferenceResult",
    "ReInferenceRunner",
]