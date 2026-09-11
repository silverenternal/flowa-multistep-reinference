"""FlowMol3 v1 (placeholder hash-stub) test split — thin re-export shim (Wave 104 P1-B).

The original 1573-LOC ``test_flowmol3_adapter.py`` was split into three
test-discovery-eligible sub-files plus this shim:

* :mod:`test_flowmol3_adapter_smoke`        — 14 tests (TestFlowMol3Capabilities,
  TestFlowMol3Lifecycle, TestFlowMol3FailClosed, TestFlowMol3ByteStable,
  TestFlowMol3InjectForwardNoise)
* :mod:`test_flowmol3_adapter_conformance`  — 71 tests (TestFlowMol3AtomTypeEntropyRestartPolicy,
  TestFlowMol3PolicyWiring, TestFlowMol3PublicSurface, TestFlowMol3ForceModeFactory,
  TestFlowMol3NfeAdaptiveRestartGate, TestFlowMol3RestartBumpsSourceRound,
  TestFlowMol3ObserveProtocol, TestFlowMol3Wave54V1Protocol)
* :mod:`test_flowmol3_adapter_metrics`      — 9 tests (TestFlowMol3EntropyMetric,
  TestFlowMol3BugCMetricSeedIsCellKey)

This shim file contains NO ``def test_*`` functions on purpose: a
re-export shim would double-count the test_* items (pytest walks every
imported module's namespace for ``test_*`` attributes). Keeping the
shim empty guarantees ``pytest --collect-only`` shows exactly the same
94 test count as before the split.

Wave 104 P1-B: pure file-system refactor. NO test_* function is
deleted, renamed, or modified.
"""
from __future__ import annotations

# No ``def test_*`` here on purpose. See module docstring.
__all__: list[str] = []
