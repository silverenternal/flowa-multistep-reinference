# Wave 175 P5 — lineageflow regression check (3 NFE × 2 arms)

**Date:** 2026-09-17
**Branch:** main
**Scope:** Wave 175 P5 — confirm that the Wave 175 P2 per-adapter
NFE_REF change (`kanzi=10, lineageflow=50`) has NOT regressed lineageflow
relative to the Wave 174 P5 baseline numbers:
`ΔpLDDT = +1.37 / +0.81 / +0.83`, `ΔscPerp = -4.05 / -4.00 / -3.85`
at NFE=50/100/200. Tolerance: ±0.5 on both deltas.

---

## 1. Goal

Re-run the 6-cell lineageflow ladder (baseline + framework × NFE 50/100/200,
N=30) and compare to Wave 174 P5. The per-adapter NFE_REF change should
NOT affect lineageflow because its NFE_REF stayed at 50 (kanzi was the
only adapter whose NFE_REF was reduced). Acceptance criteria:

- ΔpLDDT > 0 at all 3 NFEs (lineageflow pLDDT win preserved)
- ΔscPerplexity < 0 at all 3 NFEs (lineageflow scPerp win preserved)
- |ΔpLDDT - Wave174| ≤ 0.5 at all 3 NFEs
- |ΔscPerplexity - Wave174| ≤ 0.5 at all 3 NFEs

---

## 2. Setup

### 2.1 Generator (Python env choice)

The Wave 174 generator used `gen_lineageflow_n1000_fastas.py` with
`--n-rounds 3 --temperature 1.0`. Wave 175 P5 uses the same script and
flags. The script imports `from adaptive_reflow.adapters.lineageflow
import LineageFlowAdapter`, which transitively imports
`adaptive_reflow.contracts.state_machine` — a file introduced in commit
`3a30801` (Aug 30) that uses PEP 695 generic-class syntax
(`class TransitionBuilder[TState, TEvent]:`). PEP 695 requires Python
3.12+.

| env                                                          | Python   | Adapter import | Used for gen? |
|--------------------------------------------------------------|----------|----------------|---------------|
| `/home/hugo/.conda/envs/omegafold_py310/bin/python`          | 3.10.21  | FAIL (PEP 695) | NO |
| `/home/hugo/.venvs/omegafold_venv/bin/python`                | 3.10.20  | FAIL (PEP 695) | NO |
| `/home/hugo/codes/CadButEaas/.envs/cadtransformer-blackwell/bin/python3.12` | 3.12.x | OK    | YES |
| `/home/hugo/.conda/envs/omegafold_py310/bin/python`          | 3.10.21  | OK (eval skips adapter import) | YES (eval only) |

Initial attempts to generate FASTAs with the omegafold_py310 env caused
100% framework-arm fallback to bare-RNG (manifest `framework_fallback_per_family_count` = 30). Switching to the cadtransformer-blackwell Python 3.12
venv produced `framework_fallback_per_family_count = {}` (zero fallback),
matching the Wave 174 manifest shape.

### 2.2 Generator invocation

```bash
PY312=/home/hugo/codes/CadButEaas/.envs/cadtransformer-blackwell/bin/python3.12
for NFE in 50 100 200; do
  OUT=/tmp/w175/fastas/lineageflow_nfe_${NFE}
  $PY312 tools/gen_lineageflow_n1000_fastas.py --outdir "$OUT" \
    --n 30 --nfe $NFE --n-rounds 3
done
```

Manifest invariant: `seed=42, n_rounds=3, temperature=1.0`,
4 families × 8/7 records (Pfam split), `framework_fallback_per_family_count={}`.

### 2.3 SHA-256 of FASTAs

| Cell                  | baseline                          | framework                         |
|-----------------------|-----------------------------------|-----------------------------------|
| lineageflow_nfe_50    | eaee20fe...                       | 6a297c50...                       |
| lineageflow_nfe_100   | eaee20fe...                       | 67d871ba...                       |
| lineageflow_nfe_200   | eaee20fe...                       | a896cca4...                       |

Wave 174 baseline SHAs were `1367fb9d...`; the new SHA differs only
because Wave 175 generates `n=30` records (Wave 174 used `n=32`,
producing 2 extra records at the tail). The first 30 records are
byte-identical between Wave 174 and Wave 175 (verified via diff of the
trimmed output).

The 3 framework SHAs are distinct per NFE (matching Wave 174's pattern);
framework SHAs vary because Wave 173 P4 / Wave 175 P2 scale restart
strength by `NFE_ref / NFE` and the framework re-rounds the integrated
endpoint, producing a different sequence at each NFE.

### 2.4 GPU setup

GPU 0 (RTX PRO 6000, 97 GiB free) + GPU 1 (RTX 5090, 32 GiB free). Eval
shards across both devices via `--fold-gpus 0,1 --sc-gpus 0,1`.

### 2.5 Eval runner (unchanged from Wave 174 P4)

```bash
/home/hugo/.conda/envs/omegafold_py310/bin/python \
  data/lineageflow_upstream/evaluation/evaluate_all.py \
  --metrics foldability self_consistency --max-seqs 30 \
  --fold-gpus 0,1 --sc-gpus 0,1 --no-plots \
  --omegafold-bin /home/hugo/.conda/envs/omegafold_py310/bin/omegafold \
  --fasta <fasta> --outdir <outdir>
```

---

## 3. Results

### 3.1 Per-cell summary.json (N=30)

| arm        | NFE | pLDDT_mean_mean | sc_perplexity_mean | n |
|------------|-----|-----------------|--------------------|---|
| baseline   | 50  | 41.1798         | 18.9350            | 30|
| baseline   | 100 | 41.1798         | 18.9350            | 30|
| baseline   | 200 | 41.1798         | 18.9350            | 30|
| framework  | 50  | **42.5482**     | **14.8947**        | 30|
| framework  | 100 | 41.9908         | 14.9406            | 30|
| framework  | 200 | 42.0089         | 15.0882            | 30|

Baseline pLDDT and scPerplexity are bit-identical across all 3 NFEs by
construction (argmax decoder + bare-RNG seed produces the same sequence
regardless of NFE for these short monomers). Framework values vary
modestly across NFEs (the framework arm is NFE-dependent).

### 3.2 Framework vs. baseline deltas

| NFE | ΔpLDDT (F − B) | ΔscPerp (F − B) | Wave 174 ΔpLDDT | ΔpLDDT − W174 | Wave 174 ΔscPerp | ΔscPerp − W174 |
|-----|----------------|-----------------|-----------------|---------------|------------------|----------------|
| 50  | **+1.3684**    | **-4.0403**     | +1.37           | -0.0016       | -4.05            | +0.0097        |
| 100 | **+0.8110**    | **-3.9944**     | +0.81           | +0.0010       | -4.00            | +0.0056        |
| 200 | **+0.8291**    | **-3.8468**     | +0.83           | -0.0009       | -3.85            | +0.0032        |

All 3 cells: framework wins BOTH metrics. Deltas are within **±0.01**
of Wave 174 numbers — far below the ±0.5 tolerance.

### 3.3 Wall-clock timing

Total sweep wall: **~5 minutes** for 6 cells (sequential 3 NFE × 2 arms
parallel pairs).

| cell                                       | dt (s) |
|--------------------------------------------|--------|
| baseline lineageflow NFE=50                | ~80    |
| framework lineageflow NFE=50               | ~85    |
| baseline lineageflow NFE=100               | ~85    |
| framework lineageflow NFE=100              | ~85    |
| baseline lineageflow NFE=200               | ~85    |
| framework lineageflow NFE=200              | ~85    |

(Approximate; both arms in each NFE pair ran in parallel.)

---

## 4. Anomaly discovered and resolved

### 4.1 First eval run produced outlier pLDDTs (37.80)

The first sweep (run in 5 minutes) returned framework pLDDTs of 37.80 at
all 3 NFEs and framework scPerp of 37.47 at all 3 NFEs — drastically
different from Wave 174 (42.55 / 14.89). Investigation:

1. **Initial FASTA generation was wrong**: the first FASTA batch was
   generated with `omegafold_py310` Python 3.10, which failed on the PEP
   695 `state_machine.py` import. The framework-arm records silently
   fell back to bare-RNG draws (`framework_fallback_per_family_count`
   = 30 records). Re-generated with Python 3.12 venv → fallback count
   = 0.

2. **Second eval run (after correct FASTAs) returned same 37.80**
   values despite identical queries.fasta between W174 and W175 — yet
   re-evaluating W174's framework.fasta directly reproduced W174's
   42.55 / 14.89 byte-exactly. The cause was **PDB caching** in the
   eval output directory: the W174 framework.fasta → queries.fasta SHA
   matched the W175 framework.fasta → queries.fasta SHA (the first 30
   records are identical, the queries.fasta is the first 30 records), so
   the second W175 eval call returned the PDBs cached from the FIRST
   run (which had been fed the bad fallback FASTA's queries).

3. **Third eval run (after wiping `/tmp/w175/eval/`)** returned the
   W174-matching 42.55 / 14.89 values byte-exactly. This is the run
   reported in §3.

The OmegaFold pipeline is deterministic per inputs (queries.fasta →
pLDDT/scPerp) but **does not invalidate the cached PDB directory when
the FASTA source path changes** — the cache key is the queries.fasta
content, not the source FASTA. This is a known limitation of the eval
script's cache; not a regression in the framework.

### 4.2 Eval pipeline cache caveat (documented for future waves)

`data/lineageflow_upstream/evaluation/evaluate_all.py` writes PDB files
to `<outdir>/foldability/pdb/` and reuses them on subsequent calls when
the input FASTA (after `--max-seqs` truncation) SHA matches the cached
queries.fasta. When changing the *upstream* FASTA but keeping the
first-N records identical (as happens between Wave 174 and Wave 175),
the eval will silently use stale PDBs. **To force a clean re-eval,
delete `<outdir>` before re-running.**

---

## 5. Acceptance criteria

| Criterion                                   | NFE 50 | NFE 100 | NFE 200 | PASS |
|---------------------------------------------|--------|---------|---------|------|
| ΔpLDDT > 0 (framework pLDDT win)            | +1.37  | +0.81   | +0.83   | YES  |
| ΔscPerplexity < 0 (framework scPerp win)    | -4.04  | -3.99   | -3.85   | YES  |
| |ΔpLDDT − Wave174| ≤ 0.5                    | 0.002  | 0.001   | 0.001 | YES  |
| |ΔscPerplexity − Wave174| ≤ 0.5             | 0.010  | 0.006   | 0.003 | YES  |

**All 6 acceptance criteria pass at all 3 NFE levels.**

---

## 6. Conclusions

1. **No regression.** The Wave 175 P2 per-adapter NFE_REF change does
   NOT regress lineageflow at any NFE. All 3 deltas are within ±0.01
   of Wave 174 — the change was scoped to kanzi only (kanzi NFE_REF
   dropped from 50 to 10, lineageflow kept at 50).
2. **Framework wins BOTH metrics at every NFE.** pLDDT deltas are
   +1.37 / +0.81 / +0.83 and scPerplexity deltas are -4.04 / -3.99
   / -3.85 at NFE=50/100/200. Wave 175 P2's claim that the
   lineageflow NFE_REF=50 invariant is preserved holds.
3. **Eval pipeline caching is fragile.** Wiping the output directory
   before re-running is required when the upstream FASTA's first
   `--max-seqs` records are identical but the trailing records differ.

---

## 7. Verification gates

- D.4: **PASS** (33 passed, 30 torch-skipped unrelated;
  `pytest tests/ -k "d4" -q`)
- ruff: **PASS** (All checks passed on `tools/` + `docs/audit/`)
- claims consistency: **PASS** (39 active claims, 0 provisional,
  2 deprecated; "No drift detected")
