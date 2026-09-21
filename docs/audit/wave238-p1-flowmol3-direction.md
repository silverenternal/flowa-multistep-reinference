# Wave 238 P1 — FlowMol3 Per-seed Direction Diagnostic

## TL;DR

| Item | Value |
|---|---|
| Direction verdict | **INCONSISTENT** (sign reversal at aggregate fg_dev) |
| Seed 42 (Wave 87, NFE=250, N=1000) | mean_diff = **-0.0235** (framework BETTER) |
| Seed 43 (Wave 235 P4, NFE=100, N=500) | mean_diff = **+0.0188** (framework WORSE) |
| Seed 44 (Wave 235 P4, NFE=100, N=500) | mean_diff = **+0.0126** (framework WORSE) |
| Wave 87 1-seed per-record REOS d_z | **-0.285** (framework has fewer REOS flags) |
| 2-new-seed pooled per-record REOS d_z | **NaN** (degenerate, sd=0) |
| 2-new-seed pooled per-seed paired-t d_z | **+3.625** (n=2 seeds, df=1, p_raw=0.123) |
| NFE confound (seed 42 vs seeds 43/44) | **YES** (250 vs 100) |
| N record confound (seed 42 vs seeds 43/44) | **YES** (1000 vs 500) |
| Graph path confound (single_mol vs batched) | **YES** (Wave 235 single_mol fallback) |
| Final verdict | **INCONSISTENT — disclose in Limitations** |

## Honest finding

The 3-seed expansion DISCONFIRMS the Wave 87 1-seed framework-WINS direction.
The sign of mean_diff is **reversed** between seed 42 (Wave 87 NFE=250) and
seeds 43, 44 (Wave 235 P4 NFE=100):

- **Seed 42** (Wave 87, NFE=250, N=1000, batched): framework reduces
  fg_dev by -0.0235 (BETTER).
- **Seed 43** (Wave 235 P4, NFE=100, N=500, single_mol): framework
  increases fg_dev by +0.0188 (WORSE).
- **Seed 44** (Wave 235 P4, NFE=100, N=500, single_mol): framework
  increases fg_dev by +0.0126 (WORSE).

The 1-seed Wave 87 d_z=-0.285 (per-record REOS) does NOT generalise
to the 2 new seeds at NFE=100/N=500. The per-record REOS test is
degenerate at the 3-seed pooled level (sd=0 → NaN). The honest
scientific reading is that the framework-WINS direction is **not
reproducible across NFE/N/seed conditions**.

## Per-seed fg_dev table

| Seed | baseline fg_dev | framework fg_dev | mean_diff (f-b) | Direction | N | NFE | Source |
|---|---:|---:|---:|---|---:|---:|---|
| 42 | 0.6381 | 0.6146 | **-0.0235** | framework_better | 1000 | 250 | Wave 87 byte-stable |
| 43 | 0.6583 | 0.6771 | **+0.0188** | framework_worse  | 500  | 100 | Wave 235 P4 single_mol |
| 44 | 0.6612 | 0.6738 | **+0.0126** | framework_worse  | 500  | 100 | Wave 235 P4 single_mol |

Note: baseline fg_dev across all 3 seeds ranges 0.6381..0.6612
(small drift across seeds; framework fg_dev across seeds ranges
0.6146..0.6771 (much larger drift). The framework arm is **less
stable** across seeds than the baseline arm — this is consistent
with the framework's perturbation_sigma=0.05 being a stochastic
prior-perturbation that interacts with seed-dependent RNG paths.

## Direction pattern verdict

- Sign of mean_diff: seed 42 = **negative**, seed 43 = **positive**,
  seed 44 = **positive**.
- All 3 same direction? **NO** (sign reversal between seed 42 and seeds 43/44).
- 2-of-3 majority? YES (seeds 43/44 same direction; seed 42 opposite).
- Honest label: **inconsistent** (the 1-seed Wave 87 framework-WINS
  direction does NOT reproduce at the 3-seed pooled level; the 2
  new seeds reverse the sign).

The "2-of-3 majority" framing is misleading because the 1 minority
seed (42) uses **different conditions** (NFE=250 vs 100, N=1000 vs 500,
batched vs single_mol). The honest framing is: **at NFE=250/N=1000,
seed 42 shows framework-WINS; at NFE=100/N=500, seeds 43+44 show
framework-WORSE**. This is a **conditional boundary** on NFE, not
a reproducible framework-WINS effect.

## Confound analysis

Three confounds prevent a clean read of the direction inconsistency:

### 1. NFE confound (seed 42 vs seeds 43/44) — REAL CONFOUND

- Seed 42: **NFE=250** (Wave 87 paper-parity sweep).
- Seeds 43, 44: **NFE=100** (Wave 235 P4 partial-sweep fallback to
  fit the 2-day budget).

The 2 new seeds use NFE=100 because NFE=250 × N=500 would have cost
~3× the wall-clock (~150 minutes per arm) and exceeded the Wave 235
P4 budget per the DeepSeek brief. **NFE=100 means the ODE integrator
takes larger steps, which is known to bias fg_dev upward** (lower
NFE → worse numerical fidelity → higher fg_dev). The framework's
prior-perturbation may not be net-positive at NFE=100 even if it is
at NFE=250.

### 2. N record confound (seed 42 vs seeds 43/44) — POWER ASYMMETRY

- Seed 42: **N=1000** records per arm.
- Seeds 43, 44: **N=500** records per arm.

Half the records means 2× higher SEM on fg_dev. The Wave 87
statistical_power calculation (fg_dev_sem=0.00577, mdd=0.016 at
α=0.05/β=0.2) was for N=1000. At N=500, the mdd is ~√2× larger
(~0.023), so the test is genuinely underpowered at the per-seed
level. The 2-new-seed pooled test is on n=2 (df=1), so it cannot
reject even a moderate effect size.

### 3. Graph traversal path confound (single_mol vs batched) — REAL CONFOUND

- Seed 42: batched DGL path (n_molecules=10 batches per Wave 87).
- Seeds 43, 44: **single_mol path** (n_molecules=1 per Wave 235 P4
  partial-sweep fallback).

The single_mol path bypasses the DGL 2.4.0+cu124 batched-path bug
(Wave 109.C) but **is a different computational graph traversal**.
The framework's restart-blend prior perturbation is applied at a
different graph-traversal position, which may not be
representative of the batched path.

**Bottom line:** The direction inconsistency is **confounded** by
NFE (250 vs 100), N (1000 vs 500), and graph path (batched vs
single_mol). It is NOT a clean seed-dependent effect.

## Honest disclosure for paper Limitations section

Proposed wording (verbatim, to add to `section-2-method.md` §Limitations
or §Experimental Setup):

> "FlowMol3 R3 fg_dev results show seed-dependent behavior. The
> Wave 87 1-seed per-record REOS analysis (d_z = -0.285, NFE=250,
> N=1000, batched) showed framework improvement, but the Wave 235
> P4 2-seed expansion at NFE=100, N=500, single_mol graph path
> (seeds 43, 44) reversed the sign of mean_diff (+0.0188, +0.0126).
> The 3-seed pooled effect is TIE (per-record REOS degenerate;
> per-seed pooled d_z = +3.625 at n=2 seeds, df=1, p_raw=0.123).
> The direction inconsistency is confounded by NFE (250 vs 100),
> N (1000 vs 500), and graph traversal path (batched vs single_mol),
> so it cannot be cleanly attributed to seed-dependent framework
> behavior. The 1-seed Wave 87 framework-WINS result is best read
> as a **conditional boundary at NFE≥250**, not a generalisable
> claim."

## What this means for paper

1. **Drop the strong "framework WINS on R3 fg_dev across seeds"
   claim.** Replace with "framework wins on R3 fg_dev at NFE≥250
   (Wave 87 N=1000, 1 seed); effect reverses at NFE=100 (Wave 235
   P4 N=500, 2 seeds); 3-seed pooled effect is TIE".
2. **Disclose the confound structure** in §Limitations: the direction
   inconsistency is confounded by NFE/N/graph-path, so the per-seed
   pattern does NOT establish seed-dependent framework behavior.
3. **Do NOT paper over** the sign reversal as "direction-consistent".
   The 1-seed Wave 87 framework-WINS is a **conditional** result
   (NFE≥250, N=1000, batched), not a generalisable result.
4. **Wave 235 P4 verdict="TIE"** is the honest script-level verdict.
   The 2-seed expansion DISCONFIRMS generalisability; the per-seed
   pooled test is UNDERPOWERED (n=2, df=1).

## Reproducibility

```bash
# Per-seed diagnostic (this doc):
.venvs/flowmol3_venv/bin/python -c "
import csv
with open('verification_outputs/wave235-p4-flowmol3-3seed.csv') as f:
    r = list(csv.DictReader(f))[0]
    print('seed_42_b:', r['w87_seed_42_baseline_fg_dev'])
    print('seed_42_f:', r['w87_seed_42_framework_fg_dev'])
    print('seed_43_b:', r['per_seed_baseline_fg_dev'].split(',')[0])
    print('seed_43_f:', r['per_seed_framework_fg_dev'].split(',')[0])
    print('seed_44_b:', r['per_seed_baseline_fg_dev'].split(',')[1])
    print('seed_44_f:', r['per_seed_framework_fg_dev'].split(',')[1])
"

# D.4 byte-stable check (unchanged from Wave 87):
.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header
# Expected: 30 passed
```

## Source artefacts

- `verification_outputs/wave235-p4-flowmol3-3seed.csv` (per-seed fg_dev
  values + pooled test statistics)
- `verification_outputs/wave235-p4-flowmol3-3seed.json` (same data in JSON)
- `verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json` (seed 42 reference)
- `verification_outputs/wave235-p4-flowmol3-seed43-{baseline,framework}.json`
- `verification_outputs/wave235-p4-flowmol3-seed44-{baseline,framework}.json`
- `docs/audit/wave235-p4-flowmol3-3seed.md` (prior audit doc — this
  doc supersedes the "Verdict" section)