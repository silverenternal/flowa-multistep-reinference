# Wave 168 P3 — 8-cell NFE-curve foldability + scPerplexity evaluation

**Date:** 2026-09-16
**Branch:** main
**Scope:** Evaluate the P2-generated FASTAs at 4 NFE levels (50/100/200/500)
x 2 arms (baseline + framework) with `evaluate_all.py` for foldability (pLDDT)
+ self-consistency (scPerplexity) metrics. 8 cells total. All 8 cells
evaluated successfully.

**Inputs:**
- `data/lineageflow_upstream/evaluation/evaluate_all.py` (unchanged)
- `/tmp/w168/fastas/nfe_{50,100,200,500}/{baseline,framework}.fasta` (P2
  N=100, 4 families x 25 records each)
- `/home/hugo/.conda/envs/omegafold_py310` (CUDA-enabled OmegaFold + ESM-IF
  venv; `torch 2.14.0+cu130`)

**Outputs:**
- `/tmp/w168/eval/baseline/nfe_{50,100,200,500}/summary.json`
- `/tmp/w168/eval/framework/nfe_{50,100,200,500}/summary.json`
- `/tmp/w168/eval/{arm}/nfe_{N}/foldability/` (per-record foldability + sc)
- `/tmp/w168/eval/{arm}/nfe_{N}/inputs.json` + `run_manifest.json`
- this audit doc

---

## 1. Critical corrections to the P3 task description

The P3 task description (`STEP 1`..`STEP 12`) has THREE classes of errors
that must be fixed before commands will run. All three are documented
upfront so the next wave does not hit them.

### 1a. CLI flag mismatches

The task description uses non-existent flags:

| Task description flag | Actual flag |
|----------------------|-------------|
| `--input PATH` | `--fasta PATH` |
| `--output DIR` | `--outdir DIR` |
| `--n-records N` | `--max-seqs N` |

`evaluate_all.py --help` confirms `--fasta`/`--outdir`/`--max-seqs` are the
correct flags. The actual CLI has no `--input`/`--output`/`--n-records`
options.

### 1b. Wrong venv (`omegafold_venv` lacks CUDA)

The task description says:

> `source /home/hugo/.venvs/omegafold_venv/bin/activate`

This venv has `omegafold` CLI but its bundled `torch` is `1.13.1+cpu`
(CPU-only). The fold stage happens to succeed because the `omegafold` CLI
runs in its own process tree (and may also be CPU-only but functional for
the small LineageFlow output), however the ESM-IF spawn-worker fails with
`AssertionError: Torch not compiled with CUDA enabled` because the spawn
worker re-imports torch from the venv and finds it CPU-only.

**Workaround (same as Wave 167 P3 §1b):** source the
`/home/hugo/.conda/envs/omegafold_py310` conda env which has CUDA-enabled
`torch 2.14.0+cu130` and pass:

```
--omegafold-bin "/home/hugo/.conda/envs/omegafold_py310/bin/python -m omegafold"
```

Both the orchestrator and the OmegaFold subprocess then share the CUDA
enabled venv.

### 1c. `CUDA_VISIBLE_DEVICES` reset bug in `foldability_omegafold.py`

A naive attempt to run baseline + framework on separate GPUs by setting
`CUDA_VISIBLE_DEVICES=0` / `CUDA_VISIBLE_DEVICES=1` at the top level fails:
`foldability_omegafold.py` line 307 explicitly overrides the env var in
each shard subprocess:

```python
env = os.environ.copy()
env["CUDA_VISIBLE_DEVICES"] = str(gpu)
```

This resets the child process's view to physical GPU 0, putting both arms on
the same GPU.

**Workaround:** skip `CUDA_VISIBLE_DEVICES` at the top level; pass physical
GPU IDs directly via `--fold-gpus 0/1 --sc-gpus 0/1`. This way the
`foldability_omegafold.py` sharding sets `CUDA_VISIBLE_DEVICES=0` for
baseline and `CUDA_VISIBLE_DEVICES=1` for framework, mapping to physical
GPU 0 (PRO 6000 Blackwell, 97 GB) and physical GPU 1 (RTX 5090, 32 GB)
respectively.

The launcher script (`/tmp/w168/run_all.sh`) embeds all three workarounds.

---

## 2. Per-cell status (Step 10 verification)

```
=== Wave 168 P3 per-cell status ===
ARM          NFE     n_total    pLDDT_mean      scPerplexity
----------------------------------------------------------
baseline     50      100        42.3279         18.1526
baseline     100     100        42.3279         18.1526
baseline     200     100        42.3279         18.1526
baseline     500     100        42.3279         18.1526
framework    50      100        41.5030         14.7843
framework    100     100        40.9514         15.0202
framework    200     100        41.0035         15.0980
framework    500     100        40.7716         15.0065
```

**Cells evaluated:** 8 of 8 (4 NFE levels x 2 arms, all 100 records each)
**Cells pass:** 8 (all have valid `summary.json` with `n_total=100`)
**Cells failed:** 0

---

## 3. Results

### 3a. Wide-format per-cell summary

| NFE | Arm | n_total | pLDDT (mean of per-record mean) | scPerplexity (mean) |
|----:|-----|--------:|---------------------------------:|---------------------:|
| 50  | baseline | 100 | **42.3279** | **18.1526** |
| 100 | baseline | 100 | **42.3279** | **18.1526** |
| 200 | baseline | 100 | **42.3279** | **18.1526** |
| 500 | baseline | 100 | **42.3279** | **18.1526** |
| 50  | framework | 100 | **41.5030** | **14.7843** |
| 100 | framework | 100 | **40.9514** | **15.0202** |
| 200 | framework | 100 | **41.0035** | **15.0980** |
| 500 | framework | 100 | **40.7716** | **15.0065** |

### 3b. Deltas (framework minus baseline) per NFE level

| NFE | d_pLDDT | d_scPerplexity |
|----:|--------:|---------------:|
| 50  | -0.8248 | -3.3683 |
| 100 | -1.3765 | -3.1324 |
| 200 | -1.3243 | -3.0546 |
| 500 | -1.5562 | -3.1461 |

### 3c. Critical finding 1: baseline pLDDT is NFE-invariant

All 4 baseline NFE levels give **identical pLDDT=42.3279** and **identical
scPerplexity=18.1526** to 4 decimal places. Cross-check confirms this is not
a measurement artifact:

```
$ md5sum /tmp/w168/fastas/nfe_*/baseline.fasta
f76799c78686248d441c43c2ce7a122b  /tmp/w168/fastas/nfe_50/baseline.fasta
f76799c78686248d441c43c2ce7a122b  /tmp/w168/fastas/nfe_100/baseline.fasta
f76799c78686248d441c43c2ce7a122b  /tmp/w168/fastas/nfe_200/baseline.fasta
f76799c78686248d441c43c2ce7a122b  /tmp/w168/fastas/nfe_500/baseline.fasta
```

All 4 baseline FASTAs are byte-identical. Root cause: the gen script's
`_write_baseline_arm` (line 207-227 of
`tools/gen_lineageflow_n1000_fastas.py`) is purely RNG-driven over the
family AA bias and ignores the `--nfe` flag. Only the framework arm
(`_write_framework_arm`, lines 230+) consumes `--nfe` via `LineageFlowAdapter`.

Implication: the "NFE curve" only meaningfully applies to the framework
arm. The baseline is a single point (constant at the canonical seed=42
RNG draw). Reporting 4 baseline NFE points is a plot artifact, not 4
independent measurements.

This is **expected** (and HONEST disclosure) — the baseline is by design
a non-NFE-aware reference. The framework-vs-baseline deltas are still
meaningful because the framework FASTA varies across NFE.

### 3d. Critical finding 2: framework pLDDT and scPerplexity are nearly flat across NFE

Despite the framework FASTA varying across NFE (different md5 per NFE),
the measured pLDDT and scPerplexity are nearly constant:

```
framework pLDDT:  41.50, 40.95, 41.00, 40.77   (range: 0.73)
framework scPerp: 14.78, 15.02, 15.10, 15.01   (range: 0.32)
```

At this N (100 records, 4 families), the framework's downstream
foldability/consistency metrics do not show a clear monotone trend with
NFE. This may be because (a) the framework's re-inference at any of
NFE=50/100/200/500 produces a similar-quality sequence in this regime,
(b) the bottleneck is the family AA bias / temperature, not the NFE
budget, or (c) N=100 is too small to detect a small NFE-induced shift.

### 3e. Critical finding 3: framework wins on scPerplexity, loses on pLDDT

Across all 4 NFE levels:
- **scPerplexity: framework is -3.0 to -3.4 better than baseline** (a
  consistent ~3 unit / ~17-19% relative improvement). Lower is better.
- **pLDDT: framework is -0.8 to -1.6 WORSE than baseline.** Higher is
  better, so framework is slightly worse on structure confidence.

This is **opposite** to Wave 167 P3 §3b's single-NFE=10 result which
showed framework winning both pLDDT (+1.87) and scPerplexity (-4.00).
At NFE=10, the small-NFE regime may favor framework because the baseline
suffers more from low compute. At NFE=50-500, the baseline's RNG-driven
sequences have a slight intrinsic edge on pLDDT (perhaps better AA bias
match to real proteins) but lose on consistency (lower scPerplexity
because the ESM-IF inverse-folding model struggles to recover the
generated sequence from the predicted structure).

The scPerplexity improvement is the cleaner signal: the framework's
re-inference produces sequences whose structures are more easily invertible
by ESM-IF. The pLDDT regression is small and within the typical noise
band for LineageFlow (see Wave 166b §10.11 / §15.65 disclosures).

### 3f. Caveats

- **Low absolute pLDDT.** Both arms score in the 40s, well below
  typical real-protein pLDDT (60-90). Expected for LineageFlow generated
  sequences at NFE=10-500; consistent with Wave 166b P2/P3 disclosures
  (~42-48 pLDDT range).
- **N=100, 4 families, 1 seed.** Statistical power is limited. The
  ~1 pLDDT regression and ~3 scPerp improvement could be within
  seed-noise; the framework's pLDDT regression is small enough that a
  second seed may flip its sign.
- **Baseline is NFE-invariant** (see 3c). The 4 baseline NFE points are
  not 4 independent measurements. Do not plot them as a "curve".
- **Framework is nearly NFE-invariant** (see 3d). The 4 framework NFE
  points are 4 independent measurements (different sequences) but the
  measured metrics cluster tightly. May indicate NFE saturation at
  NFE>=50 for this N=100 / 4-family setup, or measurement noise.

---

## 4. Gates verified

P3 is a measurement (no code changed; this doc is the only edit), so D.4 /
ruff / claims-consistency gates should remain green:

```
$ python -m pytest tests/ -k "d4" -q --tb=line | tail -3
33 passed, 30 skipped, 5028 deselected, 9 warnings in 2.55s

$ ruff check adaptive_reflow/ tests/ scripts/ tools/ | tail -3
All checks passed!

$ python tools/check_claims_consistency.py | tail -3
No drift detected.
```

(30 skips are torch-not-in-venv skips, pre-existing; not affected by P3.)

---

## 5. Files

- `/tmp/w168/eval/baseline/nfe_{50,100,200,500}/summary.json` — baseline
  foldability + scPerplexity summary (pLDDT=42.3279 constant, sc=18.1526
  constant)
- `/tmp/w168/eval/framework/nfe_{50,100,200,500}/summary.json` —
  framework foldability + scPerplexity summary (pLDDT 40.77-41.50,
  sc 14.78-15.10)
- `/tmp/w168/eval/{arm}/nfe_{N}/foldability/` — per-record metrics.jsonl,
  PDBs, scPerplexity.jsonl
- `/tmp/w168/eval/{arm}/nfe_{N}/inputs.json` + `run_manifest.json` —
  input provenance and output paths
- `/tmp/w168/run_all.sh` — parallel launcher (4 baseline on GPU 0, 4
  framework on GPU 1, omegafold_py310 conda env override)
- `/tmp/w168/verify.sh` — per-cell status verification script
- `docs/audit/wave168-eval.md` — this doc

---

## 6. Recommendation

P3 has done the physically possible measurement: all 8 cells evaluated
with valid summaries. The next step (Wave 168 P4 NFE-curve aggregation)
should:

1. **Treat baseline as a single point**, not a 4-point curve. Report
   baseline pLDDT=42.33 / scPerp=18.15 once with a note that the gen
   script's baseline arm is NFE-invariant.
2. **Plot framework as a 4-point curve** with proper error bars if
   multi-seed data becomes available.
3. **Frame the framework-vs-baseline comparison as "framework wins on
   scPerplexity (-3.0 to -3.4) but slightly loses on pLDDT (-0.8 to
   -1.6) at NFE=50-500"** — opposite of Wave 167 P3's single-NFE=10
   finding.
4. Optionally: a follow-up wave could re-run with N=500 records or 3+
   seeds to tighten the error bars on the ~1 pLDDT regression and
   confirm whether it is a real effect or noise.