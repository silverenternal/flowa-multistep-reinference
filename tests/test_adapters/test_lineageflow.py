"""LineageFlow test split — thin re-export shim (Wave 104 P1-B).

The original 1589-LOC ``test_lineageflow.py`` was split into three
test-discovery-eligible sub-files plus this shim:

* :mod:`test_lineageflow_smoke`        — 26 tests (capability handshake,
  Protocol check, build/solve/observe, condition injection, restart
  boundary, export_trajectory, inject_forward_noise, Heun, registry,
  default factory, weights-path resolver, torch_is_available,
  mechanism_id, install_checkpoint_compat_shim, F-4 dtype boundary)
* :mod:`test_lineageflow_conformance`  — 21 tests (classifier-aware
  restart policy, perturbation policies, observe() typed surface,
  _StubLineageFlow signature, real EsmModel load,
  CapabilityMissingError on load failure, defensive state=None guard)
* :mod:`test_lineageflow_metrics`      — 11 tests (per-position
  entropy-reduction metric evaluation: calibration anchors,
  determinism, reference_theta mode, shared helper delegation,
  public-symbol export, observe(... POSITION_ENTROPY_REDUCTION)
  byte-stable equality)

This shim file contains NO ``def test_*`` functions on purpose: a
re-export shim would double-count the test_* items (pytest walks every
imported module's namespace for ``test_*`` attributes). Keeping the
shim empty guarantees ``pytest --collect-only`` shows exactly the same
57 test count as before the split.

Wave 104 P1-B: pure file-system refactor. NO test_* function is
deleted, renamed, or modified.
"""
from __future__ import annotations

# No ``def test_*`` here on purpose. See module docstring.
__all__: list[str] = []
