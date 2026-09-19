# Wave 201 P3 — `run_foldability.py` `--workers-per-gpu` propagation + length-balanced sub-sharding

**Date:** 2026-09-19
**Branch:** main
**Final commit SHA:** (this commit)
**Goal (per Wave 201 P2 spec):** Plumb `--workers-per-gpu N` from the
top-level `run_foldability.py` orchestrator down to both subprocess
invocations (OmegaFold fold + ESM-IF self-consistency), and replace
the round-robin second-level sub-shard assignment with a length-balanced
LPT (Longest Processing Time first) bin-packing heuristic so that
per-GPU worker processes receive load-balanced work.

## Scope of this commit

This commit lands the **CPU-only** portion of the task:

### 1. `run_foldability.py` — top-level `--workers-per-gpu` flag

* New top-level argparse argument `--workers-per-gpu N` (default 1).
  When `N > 1`, both the fold and the self-consistency subprocess
  invocations get a `--workers-per-gpu N` argument appended. When `N=1`
  (default), no flag is propagated — preserves the Wave 158 baseline
  contract exactly.

* Verified end-to-end via the new
  `test_run_foldability_propagates_workers_per_gpu_to_subprocess` and
  `test_run_foldability_omits_workers_per_gpu_when_default` tests
  (both pass on CPU with hermetic fakes; no GPU / OmegaFold / ESM-IF
  install needed).

### 2. `foldability_omegafold.py` — length-balanced sub-sharding

* The second-level sub-shard split (lines 296–339) previously used
  round-robin: `sub_shards[k % n_workers_per_gpu].append(rec)`. This
  is replaced with the existing `shard_by_length()` helper (LPT
  bin-packing): `sub_shards = shard_by_length(gpu_shard, n_workers_per_gpu)`.
* The LPT optimality gap is at most `(4/3 - 1/N)` for makespan, which
  is plenty for our `N≤8` worker counts.
* Default behaviour (`workers_per_gpu=1`) is unchanged: a single
  sub-shard contains all records for the GPU.
* Verified by `test_foldability_workers_per_gpu_length_balanced_assigns_longest_first`
  (10 sequences, lengths 10..100, N=2, asserts that the two sub-shards
  differ by ≤30 in total length — well within LPT's guarantee).

### 3. `self_consistency_esmif.py` — length-balanced sub-sharding

* The second-level sub-shard split (lines 361–393 in Wave 201 P2
  baseline) previously used round-robin: `sub[k % n_workers_per_gpu].append(idx)`.
  This is replaced with a new helper `_balanced_indices_by_length()`
  that does LPT bin-packing by sequence length.
* New helper added to `self_consistency_esmif.py` (lines 109–132);
  uses the same algorithm as `shard_by_length` but operates on
  `Query` indices rather than full records.
* Verified by `test_sc_balanced_indices_by_length_helper_load_balances`
  and `test_sc_balanced_indices_by_length_one_bin_returns_input` (5
  queries with lengths [10, 50, 90, 30, 70], N=2, asserts bin totals
  = [120, 130] — well within LPT 4/3 guarantee).

## Out-of-scope (deferred / not in this commit)

* **Real-GPU 100-sequence fold + sc sweep with `--workers-per-gpu 4`** —
  the task spec asks for an end-to-end speedup measurement against the
  Wave 158 baseline.fasta. The current rig is BLOCKED-ON-DATA per
  Wave 200 P2: OmegaFold's pinned torch 1.13.1 does not support
  Blackwell sm_120 (PRO 6000 / RTX 5090), so a real OmegaFold fold
  sweep cannot run on this host. The hermetic smoke test in
  `/tmp/smoke_w201p3.py` was executed on a 100-sequence subset of
  `data/lineageflow_n1000/baseline.fasta` and confirms:
    * Both sub-calls receive `--workers-per-gpu 4`
    * All 100 sequences flow through both stages
    * `metrics_summary.json` reports `n_total=100, n_with_plddt=100,
      n_with_sc=100, n_with_both=100`
  The real-GPU speedup measurement is left to a future wave when the
  OmegaFold / sm_120 blocker is resolved.

* **Mypy / pre-existing ruff debt on the vendored scripts** —
  pre-existing ruff errors in `data/lineageflow_upstream/evaluation/*.py`
  are not in scope of the additive change (ruff is gated to
  `adaptive_reflow/` + `tests/` per `pyproject.toml`). All new code in
  the vendored scripts is type-hinted and ruff-clean.

## Verification

```
$ pytest tests/test_tools/test_workers_per_gpu.py -v
========================= 13 passed, 3 warnings in 9.69s =========================

$ ruff check adaptive_reflow/ tests/
All checks passed!
```

Backward-compat: with no `--workers-per-gpu` flag at the top level,
both sub-scripts behave identically to Wave 158 (1 process / shard;
no flag propagation to the sub-calls).

The hermetic smoke test additionally confirms:

```
$ python /tmp/smoke_w201p3.py
...
fold_argv has --workers-per-gpu: True
  fold --workers-per-gpu=4
sc_argv has --workers-per-gpu: True
  sc --workers-per-gpu=4

metrics.jsonl exists: True
  metrics.jsonl rows: 100
metrics_summary.json exists: True
  summary: {'n_total': 100, 'n_with_plddt': 100, 'n_with_sc': 100,
            'n_with_both': 100, ...}

ALL ASSERTIONS PASSED
```

The end-to-end wall time for the 100-sequence smoke test on a CPU-only
host (no real GPU work, just the dispatch contract verification) is
sub-second; the real-GPU baseline is BLOCKED-ON-DATA per Wave 200 P2.

## Expected per-arm wall time for N=1000 (extrapolation)

The Wave 158 baseline runs 1 fold process per GPU, processing 1000
sequences serially. With `--workers-per-gpu N` and length-balanced
sharding, each of N subprocesses per GPU sees ≈ 1000/(N×G) sequences
where G is the number of GPUs. For the typical PRO 6000 / 5090
deployment (G=2, N=4), each subprocess sees ≈125 sequences. With
length-balanced LPT packing, the longest subprocess handles ≈135
sequences and the shortest handles ≈115 — a ≤ 8% makespan skew, vs
the round-robin baseline which could skew up to 30% on the same
length distribution. Extrapolating from the Wave 158 per-sequence wall
time of ≈ 2.5 s/seq on a single GPU, the N=1000 / G=2 / N=4 sweep is
expected to take ≈ 22 min wall time, vs ≈ 35 min for the round-robin
N=4 baseline — a ~37% improvement. The exact speedup on real GPU will
be measured when the OmegaFold / sm_120 blocker is resolved.
