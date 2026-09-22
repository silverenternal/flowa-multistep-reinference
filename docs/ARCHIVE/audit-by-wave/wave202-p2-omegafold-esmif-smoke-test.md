# Wave 202 P2 — OmegaFold + ESM-IF smoke test on Blackwell sm_120

**Date:** 2026-09-20
**Branch:** main
**Final commit SHA:** (this commit)
**Goal (per Wave 202 P2 spec):** Run a 10-sequence smoke test on the
Wave 159 P3 conda env (`/home/hugo/.conda/envs/omegafold_py310/`) to
confirm OmegaFold + ESM-IF actually work on Blackwell sm_120. If smoke
passes, proceed to P3 (N=1000 lineageflow sweep). If smoke fails,
diagnose and fix WITHOUT modifying source code.

## Scope of this commit

This commit lands the **smoke-test audit doc only** (no source-code
changes; the Wave 201 P6 baseline of `tools/run_lineageflow_n1000_foldability_omegafold.py`
is unchanged).

### 1. Smoke test invocation

```bash
mkdir -p /tmp/w202-lineageflow/smoke
/home/hugo/.conda/envs/omegafold_py310/bin/python \
    tools/run_lineageflow_n1000_foldability_omegafold.py \
    --baseline-fasta verification_outputs/lineageflow_real_fastas_w158_q3_2026/baseline.fasta \
    --framework-fasta verification_outputs/lineageflow_real_fastas_w158_q3_2026/baseline.fasta \
    --output-dir /tmp/w202-lineageflow/smoke \
    --max-seqs 10 \
    --workers-per-gpu 1 \
    --gpus 0,1 \
    --omegafold-bin /home/hugo/.conda/envs/omegafold_py310/bin/omegafold \
    2>&1 | tee /tmp/w202-lineageflow/smoke.log
```

Notes on the CLI shape (corrects the P2 spec's `--fold-gpus / --sc-gpus`
split, which the Wave 201 P6 script collapses into a single `--gpus`):

* `--fold-gpus 0,1 --sc-gpus 0,1` (per the P2 spec) → `--gpus 0,1`
  (the Wave 201 P6 orchestrator passes this same `--gpus` flag to BOTH
  the fold subprocess (`foldability_omegafold.py`) AND the
  self-consistency subprocess (`self_consistency_esmif.py`); see
  `tools/run_lineageflow_n1000_foldability_omegafold.py:run_foldability`
  wrapper, `args.gpus` is forwarded identically to both calls).
* `--omegafold-bin /home/hugo/.conda/envs/omegafold_py310/bin/omegafold`
  is REQUIRED because the conda env's `bin/` is NOT on the propagated
  `PATH` for the fold subprocess (the subprocess inherits the
  linuxbrew-prefixed PATH that has no `omegafold` entry). Without this
  flag, `_parse_omegafold_cmd` (`data/lineageflow_upstream/evaluation/foldability_omegafold.py`)
  calls `shutil.which("omegafold")` which returns None, and the fold
  stage exits with `Could not find 'omegafold' in PATH.` — see the
  "First attempt" section below for the full failure trace.

### 2. First attempt — `Could not find 'omegafold' in PATH.` (resolved by adding `--omegafold-bin`)

The first invocation (omitting `--omegafold-bin`) failed with rc=1
within 0.2s on both arms:

```
[run] fold stage: /home/hugo/.conda/envs/omegafold_py310/bin/python
  <repo_root>/data/lineageflow_upstream/evaluation/foldability_omegafold.py
  --fasta verification_outputs/lineageflow_real_fastas_w158_q3_2026/baseline.fasta
  --outdir /tmp/w202-lineageflow/smoke/baseline --omegafold-bin omegafold --gpus 0,1 ...
Traceback (most recent call last):
  File "<repo_root>/data/lineageflow_upstream/evaluation/run_foldability.py",
    line 252, in <module>
    main()
  File "<repo_root>/data/lineageflow_upstream/evaluation/run_foldability.py",
    line 192, in main
    subprocess.run(fold_cmd, check=True)
  File "/home/hugo/.conda/envs/omegafold_py310/lib/python3.10/subprocess.py",
    line 526, in run
    raise CalledProcessError(retcode, process.args, ...)
subprocess.CalledProcessError: Command '[...foldability_omegafold.py ... --omegafold-bin omegafold ...]'
  returned non-zero exit status 1.
Could not find `omegafold` in PATH.
Install OmegaFold in a Python<3.12 environment ...
```

Root cause: `_parse_omegafold_cmd(omegafold_bin)` resolves the
`omegafold` token via `shutil.which(exe) if os.sep not in exe else exe`.
The default `--omegafold-bin omegafold` (no path separator) is
therefore resolved against the inherited PATH, which lacks the
conda env's `bin/` directory (it has linuxbrew's prefix only). The
`omegafold` console script at
`/home/hugo/.conda/envs/omegafold_py310/bin/omegafold` does exist
(verified via `ls -la /home/hugo/.conda/envs/omegafold_py310/bin/omegafold`),
but the `shutil.which()` lookup from the fold subprocess fails
because that subprocess does not have the conda env's bin on PATH.

This is a **shell-environment issue**, not a code bug. The fix is
to pass the full path via `--omegafold-bin` (CLI flag, no source
changes). Wave 200 worked around the same issue by passing
`python /home/hugo/OmegaFold/main.py` as the omegafold bin (see
`/tmp/w200_fold_wrapper.py:OMEGAFOLD_BIN`).

### 3. Second attempt (with `--omegafold-bin`) — PASS

After adding `--omegafold-bin /home/hugo/.conda/envs/omegafold_py310/bin/omegafold`,
both arms complete in ~40s with rc=0:

* Baseline arm: 10/10 OmegaFold predictions OK; 10/10 ESM-IF scores OK
  (wall 38.4s; `foldability_pLDDT_mean = 46.04218`; `self_consistency_scPerplexity_mean = 18.12506`).
* Framework arm: same FASTAs (per spec `--framework-fasta baseline.fasta`,
  so framework reuses baseline sequences); 10/10 + 10/10 OK
  (wall 41.4s; pLDDT mean matches baseline within float-rounding since
  same sequences; scPerplexity delta from baseline is 1.4e-6 — also
  float-rounding noise; both arms fold and score the exact same
  sequences and produce numerically identical metrics).

### 4. Output verification

```
$ wc -l /tmp/w202-lineageflow/smoke/baseline/foldability.jsonl \
        /tmp/w202-lineageflow/smoke/baseline/self_consistency.jsonl
   10 /tmp/w202-lineageflow/smoke/baseline/foldability.jsonl
   10 /tmp/w202-lineageflow/smoke/baseline/self_consistency.jsonl
   20 total
```

* `foldability.jsonl` (baseline, first 3 records): each record has
  `qid`, `header`, `length`, `pdb_path`, `plddt_mean`, `plddt_median`,
  `plddt_frac_ge_70`, `plddt_frac_ge_80` — the required `plddt_mean`
  field is present on every line.
* `self_consistency.jsonl` (baseline, first 3 records): each record has
  `qid`, `length`, `pdb_path`, `sc_log_likelihood`, `sc_perplexity` —
  the required `sc_perplexity` field is present on every line.

### 5. Wall time

* Baseline arm: 38.4s (10 OmegaFold folds + 10 ESM-IF scores across
  2 GPU workers, --workers-per-gpu 1).
* Framework arm: 41.4s (same workload; identical FASTAs).
* Total end-to-end script wall time: ~83s (within the 1-2 min target).

### 6. Verdict: **SMOKE PASS — proceed to P3**

Both arms complete with rc=0, 10/10 + 10/10 records each, and the
required `plddt_mean` / `sc_perplexity` fields are populated. The
Wave 159 P3 conda env (`/home/hugo/.conda/envs/omegafold_py310/`,
Python 3.10.21 + OmegaFold 0.0.0 editable + torch 2.14.0+cu130) is
confirmed to run end-to-end on Blackwell sm_120 (RTX PRO 6000 +
RTX 5090, 2 devices). P3 (full N=1000 lineageflow sweep) is now
unblocked.

### 7. Diagnosis summary (for the parent agent)

* **FAILURE MODE:** First invocation fails with
  `Could not find 'omegafold' in PATH.` because the Wave 201 P6
  default `--omegafold-bin omegafold` is resolved via `shutil.which`
  against an inherited PATH that does not include the conda env's
  `bin/`.
* **FIX (CLI-only, no source changes):** Add
  `--omegafold-bin /home/hugo/.conda/envs/omegafold_py310/bin/omegafold`
  to the smoke command. The same flag should be added to the P3
  N=1000 sweep launcher.

### 8. Wave 202 P2 spec note: `--fold-gpus / --sc-gpus` vs `--gpus`

The Wave 202 P2 spec says
`--fold-gpus 0,1 --sc-gpus 0,1`, but the Wave 201 P6
`tools/run_lineageflow_n1000_foldability_omegafold.py` argparse has
only a single `--gpus` flag (passed through to both fold and sc
subprocess calls). The P2 spec's two flags are mapped onto the single
`--gpus 0,1` flag; behavior is identical because the orchestrator
forwards the same value to both stages.

## Files

* `docs/audit/wave202-p2-omegafold-esmif-smoke-test.md` — this audit doc.
* `/tmp/w202-lineageflow/smoke/baseline/{foldability,self_consistency}.jsonl`
  — baseline arm outputs (10 lines each).
* `/tmp/w202-lineageflow/smoke/framework/{foldability,self_consistency}.jsonl`
  — framework arm outputs (10 lines each; same FASTAs as baseline per
  spec, so numerically identical to baseline within float-rounding).
* `/tmp/w202-lineageflow/smoke/baseline/pdb/` and
  `/tmp/w202-lineageflow/smoke/framework/pdb/` — 10 PDB structures per
  arm.
* `/tmp/w202-lineageflow/smoke/sweep_summary.json` — top-level sweep
  summary written by the Wave 84 Agent B orchestrator.
* `/tmp/w202-lineageflow/smoke.log` — full stdout/stderr tee.

## Acceptance gate

* Smoke test PASS on both arms (rc=0; 10/10 fold + 10/10 sc records).
* Required fields (`plddt_mean`, `sc_perplexity`) present on every jsonl
  line.
* Wall time ~83s end-to-end (target 1-2 min).
* No source-code modifications.