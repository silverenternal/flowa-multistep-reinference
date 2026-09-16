# Wave 168 P2: 8-cell NFE-curve FASTA generation (N=100 records each)

**Branch:** main
**Wave:** 168 (rebuild from Wave 167 honesty findings)
**Scope:** Generate 8 FASTA files at NFE=50/100/200/500 x {baseline, framework}
with N=100 records each (4 families x 25 records per family). All 8 cells land
in `/tmp/w168/fastas/` and the diversity of the generated sequences is verified
to confirm `--nfe` propagates through the framework arm.

**Status:** COMPLETE. 8/8 cells generated. Diversity verified.

---

## 1. CRITICAL correction to the P2 task description (same as Wave 167 P2)

The P2 task description (`STEP 2`..`STEP 5`) references a CLI flag
(`--output-dir`, `--n-records-per-family`) that **does not exist** in the actual
CLI. Wave 168 P1 added `--nfe` but did not change the existing CLI surface.
The actual flag is `--outdir` and the total record count is `--n` (the script
distributes records across the 4 families via `family_ids[i % len(family_ids)]`).

### 1a. Empirical confirmation

```
$ python tools/gen_lineageflow_n1000_fastas.py --output-dir /tmp/w168/fastas/nfe_50/ --n-records-per-family 25 --nfe 50
usage: gen_lineageflow_n1000_fastas.py [-h] [--outdir OUTDIR] [--n N]
                                       [--seed SEED] [--min-len MIN_LEN]
                                       [--max-len MAX_LEN] [--nfe NFE]
gen_lineageflow_n1000_fastas.py: error: unrecognized arguments:
    --output-dir /tmp/w168/fastas/nfe_50/ --n-records-per-family 25
```

### 1b. Actual CLI surface used in P2

| Flag | Value | Meaning |
|------|-------|---------|
| `--outdir` | `/tmp/w168/fastas/nfe_{50,100,200,500}/` | Single output dir for BOTH `baseline.fasta` + `framework.fasta` + `manifest.json` |
| `--n` | 100 | Total records = 4 families x 25 records per family |
| `--nfe` | 50/100/200/500 | Per-record NFE budget for the framework arm (Wave 168 P1) |
| `--seed` | 42 (default) | Master seed |

---

## 2. Per-cell status (8/8 generated)

Each invocation writes BOTH `baseline.fasta` + `framework.fasta` + `manifest.json`
in one call (Wave 167 P2 finding: no need for `--arm` flag, the script writes
both arms atomically).

| NFE | Arm | Records | Manifest `nfe_per_record` | Status |
|-----|-----|---------|---------------------------|--------|
| 50  | baseline | 100 | 50 | OK |
| 50  | framework | 100 | 50 | OK |
| 100 | baseline | 100 | 100 | OK |
| 100 | framework | 100 | 100 | OK |
| 200 | baseline | 100 | 200 | OK |
| 200 | framework | 100 | 200 | OK |
| 500 | baseline | 100 | 500 | OK |
| 500 | framework | 100 | 500 | OK |

All 8 cells generated successfully. Manifest records the requested `nfe_per_record`.

---

## 3. SHA256 fingerprints (per-cell byte signature)

```
8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137  /tmp/w168/fastas/nfe_50/baseline.fasta
4147a6b4a09178066a1ea47c2a1c743f57c2c3ea9c35d88a1807e820592b0c43  /tmp/w168/fastas/nfe_50/framework.fasta
8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137  /tmp/w168/fastas/nfe_100/baseline.fasta
9a75eee04969575e510ed0fa27740c9dea4a9f68111b320d0c11c195bdbd5f1f  /tmp/w168/fastas/nfe_100/framework.fasta
8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137  /tmp/w168/fastas/nfe_200/baseline.fasta
2075710ce923654eb20ec6e3eb1017bc681e7faf514c5a03d2b73fa397c3c804  /tmp/w168/fastas/nfe_200/framework.fasta
8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137  /tmp/w168/fastas/nfe_500/baseline.fasta
0c050127203bf74266a65833132ac0e0c1d5860318f78a9af9a4f07d1f8de3c4  /tmp/w168/fastas/nfe_500/framework.fasta
```

**Observation:** All 4 baseline FASTAs are byte-identical (sha256 = `8fa3...b137`).
This is expected and correct — the baseline arm uses bare RNG over per-family
AA bias and does NOT consume the NFE flag (NFE only affects framework arm).
The 4 framework FASTAs differ across NFE levels, confirming `--nfe` propagates.

---

## 4. Sequence diversity check (proves `--nfe` genuinely affects framework)

### 4a. Baseline arm across NFE levels (expected: identical)

```
NFE=50  baseline seq0 (first 30 aa): DQFDDQNPCDEPNQQKMFWRDLFERDHHHF  (len=111)
NFE=100 baseline seq0 (first 30 aa): DQFDDQNPCDEPNQQKMFWRDLFERDHHHF  (len=111)
NFE=200 baseline seq0 (first 30 aa): DQFDDQNPCDEPNQQKMFWRDLFERDHHHF  (len=111)
NFE=500 baseline seq0 (first 30 aa): DQFDDQNPCDEPNQQKMFWRDLFERDHHHF  (len=111)
All baseline seq0 identical: True
```

Confirmed — baseline is identical across NFE (as expected; NFE only affects
framework).

### 4b. Framework arm across NFE levels (expected: different)

```
NFE=50  framework seq0 (first 30 aa): LLGPCMFGKNCPFGCDGGSLMHHFATEFEH  (len=64)
NFE=100 framework seq0 (first 30 aa): LLGPCMFGKNCPFGCDGGSLMHHFATEFEH  (len=64)
NFE=200 framework seq0 (first 30 aa): LLGPCMFGKNCPFGCDGGSLMHHFATEFEH  (len=64)
NFE=500 framework seq0 (first 30 aa): LLGPCMFGKNCPFGCDGGSLMHHFATEFEH  (len=64)
All framework seq0 identical: False (want False)
```

### 4c. Aggregate diversity across 100 records x 6 pairwise comparisons

```
Total differing positions across 100 records x 6 pairwise comparisons: 674
Mean differing positions per record-pair: 1.123
Records where NFE=50 != NFE=500: 98 / 100
```

98/100 records differ between NFE=50 and NFE=500. Average ~1.12 position
differences per record-pair across the 6 pairwise comparisons. The framework
sequences ARE sensitive to NFE — different Euler step sizes produce different
trajectories, which produces slightly different endpoint AAs at each position.

### 4d. Why the diversity is small per-position

Each framework record has length ≤147 aa (capped at `LINEAGEFLOW_MAX_LENGTH = 256`
and trimmed to the per-record `length` drawn from `[min_len, max_len]`). The
position-level differences are small (mean 1.12) because:
1. The synthetic velocity field is deterministic and largely convergent
   (positions far from integration boundaries are unaffected by step-size change).
2. The argmax over the 20-AA categorical at the endpoint is a hard threshold —
   small velocity deltas often do not flip the argmax.

The aggregate diversity (98/100 records differ) is the meaningful signal for
the downstream evaluation: the framework arm produces *systematically* different
sequences at different NFE, even if the per-position divergence is small.

---

## 5. Total wall time

```
Start: Wed Sep 16 02:25:48 PM CST 2026
End:   Wed Sep 16 02:27:56 PM CST 2026
Wall:  128 seconds (~2 min) for 4 invocations x 100 records x 2 arms
```

Per-invocation: ~30s. The dominant cost is the `solve_ode` -> `export_endpoint`
-> `apply_restart_distribution` chain running `n_rounds=3` rounds per record
(N=100 records x 3 rounds = 300 ODE solves per arm, at NFE=500 the
largest).

---

## 6. Files touched

- `tools/gen_lineageflow_n1000_fastas.py` — unchanged in P2 (P1 already wired
  `--nfe` through `global NFE_PER_RECORD`).
- `docs/audit/wave168-fasta-generation.md` — this file.

LOC added in P2: ~150 (this audit doc only; no source code changes).

---

## 7. Gates (STEP 10)

```
$ pytest tests/ -k "d4" -q --tb=line | tail -3
33 passed, 31 skipped, 5020 deselected, 9 warnings in 2.59s

$ ruff check adaptive_reflow/ tests/ scripts/ tools/ | tail -3
All checks passed!

$ python tools/check_claims_consistency.py | tail -3
**No drift detected.**
```

---

## 8. Next steps (Wave 168 P3+)

P3 (single-cell evaluation) can now run foldability + scPerplexity on each
of the 8 cells. The P3 eval pipeline already accepts an NFE parameter and
will read the per-cell `nfe_per_record` from the manifest, so the evaluation
budget matches what was used to generate the sequences.