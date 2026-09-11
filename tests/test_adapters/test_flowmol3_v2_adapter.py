"""FlowMol3 v2 (real integration) test split — thin re-export shim (Wave 104 P1-B).

The original 1332-LOC ``test_flowmol3_v2_adapter.py`` was split into
three test-discovery-eligible sub-files plus this shim:

* :mod:`test_flowmol3_v2_adapter_smoke`        — 14 top-level test_*
  (capabilities handshake, build/solve/observe, validation paths,
  factory use_upstream wiring)
* :mod:`test_flowmol3_v2_adapter_conformance`  — 21 tests across 4
  classes (TestFlowMol3V2ExportSampledMolecules,
  TestFlowMol3V2NMoleculesBatch, TestFlowMol3V2SeedThreading,
  TestFlowMol3V2ObserveProtocol) plus 2 trailing top-level
  test_* (model-load + stub install)
* :mod:`test_flowmol3_v2_adapter_metrics`      — empty (no v2
  Tier-3 paper-metric test_* functions at this time; the per-position
  entropy metric evaluation lives in
  :mod:`test_flowmol3_adapter_metrics` instead)

This shim file contains NO ``def test_*`` functions on purpose: a
re-export shim would double-count the test_* items (pytest walks every
imported module's namespace for ``test_*`` attributes). Keeping the
shim empty guarantees ``pytest --collect-only`` shows exactly the same
35 test count as before the split.

Wave 104 P1-B: pure file-system refactor. NO test_* function is
deleted, renamed, or modified.
"""
from __future__ import annotations

# No ``def test_*`` here on purpose. See module docstring.
__all__: list[str] = []
