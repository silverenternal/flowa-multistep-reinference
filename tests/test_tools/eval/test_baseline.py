"""Tests for tools/eval/baseline.py — baseline cold-restart + paper-quantity materialization.

Wave 104 P2-A: split from tests/test_tools/test_run_real_ckpt_eval.py
(2409 LOC → 6 sub-files mirroring tools/eval/).

The ``baseline`` module's surface (``_solve_baseline``,
``_build_initial_state_and_condition``, ``_compute_paper_quantities_for_model``,
``_parse_g_profile_source``) is exercised by:

* ``tests/test_tools/test_run_image_fid_per_round.py`` (baseline cold restart)
* ``tests/test_tools/eval/test_sweep.py`` (``_run_cell`` + ``_resolve_adapter``)

This file exists so the 6-file layout mirrors ``tools/eval/`` (one file
per module). No ``def test_*`` lives here directly because every assertion
on the baseline surface is covered by the per-feature test files above.
Per Wave 101 P2-A scope, this refactor is file-system only — no new tests
are added and no existing tests are deleted.
"""
