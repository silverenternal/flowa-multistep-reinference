"""Kanzi protein flow-AE test split — thin re-export shim (Wave 104 P1-B).

The original 1514-LOC ``test_kanzi.py`` was split into three
test-discovery-eligible sub-files plus this shim:

* :mod:`test_kanzi_smoke`        — 14 tests (capability handshake,
  Protocol check, build/solve/observe, condition injection, restart
  boundary, export_trajectory, inject_forward_noise, Heun solver,
  default factory, weights-path resolver, torch_is_available,
  load_torch_model real-ckpt, mechanism_id, edge-case ids,
  module_constants_consistent)
* :mod:`test_kanzi_conformance`  — 37 tests (gpt_prior_patch
  idempotency + kanzi availability, observe_token_indices chain-walk,
  KanziGPTPriorRestartPolicy constructor + memory_fraction_vector,
  adapter @implements decorator + assert_adapter_compliance,
  perturbation policies, observe() typed Protocol surface, defensive
  state=None guard)
* :mod:`test_kanzi_metrics`      — 1 test (observe_entropy_reduction
  via Mahalanobis — Wave 95 Phase 2.C per-position restart signal)

This shim file contains NO ``def test_*`` functions on purpose: a
re-export shim would double-count the test_* items (pytest walks every
imported module's namespace for ``test_*`` attributes). Keeping the
shim empty guarantees ``pytest --collect-only`` shows exactly the same
52 test count as before the split.

Wave 104 P1-B: pure file-system refactor. NO test_* function is
deleted, renamed, or modified.
"""
from __future__ import annotations

# No ``def test_*`` here on purpose. See module docstring.
__all__: list[str] = []
