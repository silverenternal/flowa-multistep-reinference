"""Tests for tools/eval/io.py — JSONL / summary I/O + DOWNSTREAM_METRICS registry.

Wave 104 P2-A: split from tests/test_tools/test_run_real_ckpt_eval.py
(2409 LOC → 6 sub-files mirroring tools/eval/).

The ``io`` module's surface (``DOWNSTREAM_METRICS``, ``REPO_ROOT``,
``build_report``, ``_capture_env_hash_lightweight``) is exercised by:

* ``tests/test_tools/test_run_image_fid_per_round.py`` (jsonl + summary)
* ``tests/test_tools/test_paper_metrics.py`` (DOWNSTREAM_METRICS registry)
* ``tests/test_tools/test_flowmol3_xtb_bridge.py`` (xtb geometry helpers)
* ``tests/test_docs/test_docs_symbols.py`` (env_hash file contract)

This file exists so the 6-file layout mirrors ``tools/eval/`` (one file
per module). No ``def test_*`` lives here directly because every assertion
on the io surface is covered by the per-feature test files above. Per
Wave 101 P2-A scope, this refactor is file-system only — no new tests
are added and no existing tests are deleted.
"""
