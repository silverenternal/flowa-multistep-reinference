"""Metrics tests for :class:`FlowMol3V2Adapter` (Wave 104 P1-B split).

This file is the **metrics** partition of the original
``test_flowmol3_v2_adapter.py`` (1332 LOC). It is created for symmetry
with the :mod:`test_flowmol3_v2_adapter_smoke` +
:mod:`test_flowmol3_v2_adapter_conformance` split.

At the time of the Wave 104 P1-B split, no Tier-3 paper-metric
``test_*`` function lives in this file. The 2 final ``test_*``
functions (``test_solve_ode_forces_model_load_before_dispatch`` and
``test_upstream_stub_does_not_shadow_real_posebusters``) are
**conformance** tests (model-load + stub install) and live in
:mod:`test_flowmol3_v2_adapter_conformance`. Per-position entropy
metric evaluation lives in :mod:`test_flowmol3_adapter_metrics`
(the v1 placeholder) — which exercises the shared
:func:`per_position_entropy_reduction` helper used by all
``compute_*_metric`` family functions.

If a future wave adds a v2 paper-metric test (PB-xtb validity,
energy-distribution Kolmogorov–Smirnov, etc.), it goes here. Until
then, this file is intentionally empty of ``def test_*`` functions.

Wave 104 P1-B: pure file-system refactor. No test_* function is
deleted (the original 35 tests are split across
:mod:`test_flowmol3_v2_adapter_smoke` and
:mod:`test_flowmol3_v2_adapter_conformance`).
"""
from __future__ import annotations

# No test functions — see module docstring.
__all__: list[str] = []
