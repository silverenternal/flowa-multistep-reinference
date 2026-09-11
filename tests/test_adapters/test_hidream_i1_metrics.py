"""Metrics tests for :class:`HiDreamI1Adapter` (Wave 104 P1-B split).

This file is the **metrics** partition of the original
``test_hidream_i1.py`` (771 LOC). It is created for symmetry with the
:mod:`test_hidream_i1_smoke` + :mod:`test_hidream_i1_conformance`
split.

At the time of the Wave 104 P1-B split, HiDream-I1 does NOT drive the
per-model ``compute_*_metric`` family used by the Tier-3 eval pipeline
(the framework's paper-metric surface is reserved for protein /
molecule adapters — Kanzi, LineageFlow, FlowMol3 — that have well
defined chemical / biological downstream metrics). The HiDream-I1
adapter is text-to-image and is evaluated at the qualitative +
batched-inference level only.

If a future wave adds a HiDream-I1 paper-metric test (FID, CLIP score,
etc.), it goes here. Until then, this file is intentionally empty of
``def test_*`` functions.

Wave 104 P1-B: pure file-system refactor. No test_* function is
deleted (the original 21 tests are split across
:mod:`test_hidream_i1_smoke` and :mod:`test_hidream_i1_conformance`).
"""
from __future__ import annotations

# No test functions — see module docstring.
__all__: list[str] = []
