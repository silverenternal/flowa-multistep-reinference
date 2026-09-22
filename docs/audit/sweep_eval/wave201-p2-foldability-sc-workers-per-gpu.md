# Wave 201 P2 — foldability + self_consistency `--workers-per-gpu N` (CPU-only)

**Date:** 2026-09-19
**Branch:** main
**Final commit SHA:** (this commit)
**Goal (per Wave 201 P2 task spec):** Add a `--workers-per-gpu N` flag to
`foldability_omegafold.py` and `self_consistency_esmif.py` so each GPU
spawns `N` concurrent OmegaFold / ESM-IF subprocesses (per-GPU
oversubscription).

## Scope of this commit

This commit lands the **CPU-only** part of the task:

1. **Additive modifications** to two vendored-upstream scripts that live
   under `data/lineageflow_upstream/evaluation/`:
   * `foldability_omegafold.py` — `run_omegafold_sharded` gains a
     `workers_per_gpu` parameter (default 1) and the per-shard dispatch
     loop splits each GPU's slice into N round-robin sub-shards that
     spawn `N` concurrent subprocesses.
   * `self_consistency_esmif.py` — same flag added; the multiprocessing
     dispatch now spawns `N` `mp.Process` workers per GPU entry instead
     of one.
   * Both scripts also accept a top-level `--workers-per-gpu` CLI flag
     that defaults to 1, preserving the Wave 158 baseline behaviour.

   The vendored-upstream tree is excluded from the parent repo by
   `.gitignore` (`data/*`), so the script modifications live in the
   working tree only — exactly the same persistence pattern used by
   Wave 158 P2 / Wave 167 P3 / Wave 168 P3 for the same scripts.

2. **Unit tests** at `tests/test_tools/test_workers_per_gpu.py` — seven
   hermetic tests that pin the dispatch contract:
   * `test_foldability_workers_per_gpu_argparse_default` — default
     `workers_per_gpu=1` (Wave 158 backward-compat).
   * `test_foldability_workers_per_gpu_dispatches_n_subprocesses_per_gpu`
     — with 1 GPU + `--workers-per-gpu 2`, exactly 2 concurrent
     subprocesses spawned, both on GPU 0, all 10 sequences folded.
   * `test_foldability_workers_per_gpu_4_spawns_4_subprocesses` — same
     for `--workers-per-gpu 4` on 1 GPU.
   * `test_foldability_workers_per_gpu_2_faster_than_1` — wall-clock
     invariant: 2-proc run does not regress vs 1-proc run; both spawn
     concurrently.
   * `test_sc_workers_per_gpu_dispatches_n_processes_per_gpu` — ESM-IF
     script: 1 GPU + `--workers-per-gpu 2` spawns 2 processes on GPU 0,
     union of indices covers all 10 queries.
   * `test_sc_workers_per_gpu_4_spawns_4_processes` — same for
     `--workers-per-gpu 4`.
   * `test_sc_workers_per_gpu_default_one` — default behaviour is 1
     process per GPU entry (Wave 158 backward-compat).

   All 7 tests pass on CPU. The dispatch logic is hermetic — uses
   monkeypatched `subprocess.Popen` and `multiprocessing.Process`
   fakes, so no GPU / torch / OmegaFold / ESM-IF required.

## Out-of-scope (deferred / not in this commit)

* **50-sequence fold sweep with `--workers-per-gpu 1 / 2 / 4` on real
  GPU** — the task spec also asks for an empirical baseline +
  speedup measurement against the Wave 158 baseline.fasta. The
  current rig is BLOCKED-ON-DATA per Wave 200 P2: OmegaFold's pinned
  torch 1.13.1 does not support Blackwell sm_120 (PRO 6000 / RTX
  5090), so a real OmegaFold fold sweep cannot run on this host.
  The `--workers-per-gpu` plumbing is in place and unit-tested; the
  real-GPU speedup measurement is left to a future wave when the
  OmegaFold / sm_120 blocker is resolved.

* **Mypy / pre-existing ruff debt on the vendored scripts** —
  pre-existing ruff errors in `data/lineageflow_upstream/evaluation/*.py`
  are not in scope of the additive change (ruff is gated to
  `adaptive_reflow/` + `tests/` per `pyproject.toml`). All new code in
  the vendored scripts is type-hinted and ruff-clean.

## Verification

```
$ pytest tests/test_tools/test_workers_per_gpu.py -v
========================= 7 passed, 3 warnings in 8.30s =========================

$ ruff check adaptive_reflow/ tests/
All checks passed!
```

Backward-compat: with no `--workers-per-gpu` flag, both scripts behave
identically to Wave 158 (1 process / shard).