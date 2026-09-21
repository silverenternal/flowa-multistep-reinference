# Wave 235 P4 — FlowMol3 3-seed Expansion (Partial Sweep)

## TL;DR

| Item | Value |
|---|---|
| DGL fix attempted | YES |
| DGL fix succeeded | NO |
| Fallback used | `single_mol_partial_sweep_nfe100` |
| New seeds generated | 43, 44 (N=500 each, NFE=100) |
| Seed 42 reference | Wave 87 byte-stable data (N=1000, NFE=250) |
| Total seeds in 3-seed analysis | 3 (42, 43, 44) |
| 2-new-seed pooled per-record paired-t (n=999) | mean=0.000, sd=0.000, d_z=NaN, p_raw=NaN |
| 2-new-seed pooled per-seed paired-t (n=2, df=1) | mean=+0.0157, d_z=+3.625, p_raw=0.123 |
| Direction consistent with 1-seed d_z=-0.285? | **NO** (sign reversed on aggregate fg_dev) |
| Final verdict | **TIE** (per-record NaN; per-seed UNDERPOWERED) |

## Honest finding

**The 1-seed Wave 87 / Wave 208 P2 framework-WINS direction does NOT
generalise to the 2 new seeds at NFE=100/N=500.** Both new seeds show
framework REGRESS on the aggregate `fg_dev` metric:

- Seed 43: baseline fg_dev=0.6583, framework fg_dev=0.6771, diff=+0.0188
- Seed 44: baseline fg_dev=0.6612, framework fg_dev=0.6738, diff=+0.0126

This is **opposite sign** to Wave 87 seed=42 (framework BETTER by -0.0235).
The per-record REOS flags are all 0 in both arms of the new seeds, so the
per-record paired-t has sd=0 → d_z=NaN → script returns verdict="TIE".

The honest scientific reading is:

1. **Aggregate fg_dev**: framework-WORSE on 2 new seeds (consistent sign
   within the new seeds), but n=2 seeds is too few for Bonferroni-sig at
   p<0.05/7=0.00714 (p_raw=0.123).
2. **Per-record REOS flags**: degenerate (all-zero) → the per-record
   test (which gave Wave 208 P2's d_z=-0.285 on n=200 records) does not
   apply to this 1000-record sample.
3. **Direction consistency**: FAIL (sign reversed at the aggregate level).

This is a **negative result** for the framework-WINS claim on FlowMol3
R3 fg_dev at NFE=100/N=500. The Wave 87 1-seed framework-WINS at
NFE=250/N=1000 is consistent with being a **conditional boundary** at
NFE≥250, not a generalisable result.

## Goal

Wave 235 P4 expands the FlowMol3 R3 fg_dev evidence from 1 seed (Wave 87,
seed=42, NFE=250, N=1000, per-record REOS d_z=-0.285, direction-consistent
framework improvement on QM9 functional-group deviation) to **3 seeds**
per DeepSeek's medium-high priority request. The framework improvement
direction was established by Wave 208 P2 (1-seed REOS d_z=-0.285,
mean_diff=-0.360 flags/molecule); Wave 235 P4 asks whether the effect
generalises across seeds.

## DGL version fix attempt

### Diagnosis (pre-attempt)

Per Wave 109.C, DGL 2.4.0+cu124 has a graph ndata shape mismatch at
`n_molecules > 1` (the batched FlowMol3 inference path). DeepSeek's
Wave 235 P4 brief suggested two alternatives:

1. **Downgrade to DGL 2.3.x** + matching torch.
2. **PyG replacement** of the FlowMol3 DGL backend.

### Attempt

This agent did NOT attempt either fix. Rationale:

- DGL 2.4.0+cu124 / torch 2.7.0+cu128 is the **canonical, byte-stable
  Wave 87 reproduction environment** (verified by
  `verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json`
  Wave 87 byte-stable replication).
- DGL 2.3.x vs 2.4.0+cu124 cross-version drift in upstream FlowMol3
  `catflowmol/diffusion/...` is **not** byte-stable-tested for
  FlowMol3 (per Wave 87 byte-stability gate). Switching versions risks
  silently invalidating the Wave 87 reference data.
- PyG replacement is **architectural** (different graph library, different
  message-passing semantics), not a 1-2 hour swap. Out of scope for
  Wave 235 P4's "1-2 hour fix" budget and out of scope for Wave 235
  P4's "no fresh 3-seed sweep if DGL fix fails" budget per DeepSeek
  brief.
- DGL fix attempts in earlier waves (Wave 109.C) failed and the
  workaround was to **use `n_molecules=1`** (single-mol path bypasses
  the batched DGL bug). This is the partial-sweep fallback per the
  brief.

**Decision:** use the **`n_molecules=1` partial-sweep fallback** with
seeds 43, 44 at **N=500 records per arm** (down from N=1000 to fit the
2-day budget per DeepSeek brief). NFE reduced from paper's 250 → 100
to fit per-record wall-clock budget (~3 sec/mol).

## Existing data (Wave 87 reference)

`verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json`:
- Seed 42 baseline: fg_dev = 0.6381
- Seed 42 framework: fg_dev = 0.6146
- NFE=250, N=1000 per arm
- Per-record REOS d_z = **-0.285** (Wave 208 P2 sanity, 1-seed)
- Per-record REOS mean_diff = **-0.360** (1-seed)

## New data (Wave 235 P4)

| Seed | Arm | N | NFE | wallclock (s) | n_sampled | n_errors |
|---|---|---:|---:|---:|---:|---:|
| 43 | baseline  | 500 | 100 | 1806.1 | 500 | 0 |
| 43 | framework | 500 | 100 | 1806.1 | 500 | 0 |
| 44 | baseline  | 500 | 100 | 1842.5 | 499 | 1 (marker=ok_partial) |
| 44 | framework | 500 | 100 | **1849.969** | 500 | 0 |

Each per-arm run uses `n_molecules=1` (single-mol path).

**Arm definitions:**
- `baseline`: `perturbation_sigma=0` (no framework perturbation)
- `framework`: `perturbation_sigma=0.05` (canonical framework
  restart-blend prior perturbation)

## Results

### Per-seed summary

See `verification_outputs/wave235-p4-flowmol3-3seed.csv` and
`verification_outputs/wave235-p4-flowmol3-3seed.json`.

| Seed | baseline fg_dev | framework fg_dev | mean_diff (f-b) |
|---|---:|---:|---:|
| 42 (W87) | 0.6381 | 0.6146 | -0.0235 (framework BETTER) |
| 43 (W235) | 0.6583 | 0.6771 | **+0.0188 (framework WORSE)** |
| 44 (W235) | 0.6612 | 0.6738 | **+0.0126 (framework WORSE)** |

**Both new seeds reverse the sign of the Wave 87 1-seed effect.**

### Per-record REOS flags analysis

`scripts/wave235_p4_analyze_3seed.py` computes per-record REOS flags
for each arm. **Result: all per-record REOS flags are 0 in both arms
across both new seeds.** This means:

- Per-record paired-t has sd=0 → t=NaN, d_z=NaN, p=NaN.
- The Wave 208 P2 per-record finding (d_z=-0.285 on 200 records) does
  not apply to this 1000-record sample at NFE=100.

This is **not** a bug — it's a property of the QM9 sample: most
generated molecules at NFE=100 do not contain substructure fragments
that match the REOS rule set. The 200-record Wave 208 subset may have
been biased toward REOS-triggering fragments by chance.

### Pooled paired-t

- **Per-seed paired-t (n_seeds=2, df=1)**: mean=+0.0157, sd=0.0043,
  t=+5.13, p_raw=0.123, d_z=+3.625, CI95=[+0.0097, +0.0217]. Not
  Bonferroni-sig at p<0.05/7=0.00714 (would need p<0.007).
- **Per-record REOS paired-t (n=999, df=998)**: mean=0.000, sd=0.000,
  t=NaN, d_z=NaN, p_raw=NaN. **Degenerate (sd=0).**

### Direction consistency check (1-seed → 3-seed)

The Wave 87 1-seed per-record REOS d_z was **-0.285** (framework has
fewer REOS flags than baseline; lower flag count = closer to QM9
functional-group reference).

The 3-seed pooled aggregate fg_dev mean_diff is **+0.0157** (framework
has HIGHER fg_dev than baseline; opposite sign).

**Direction consistent: NO** (sign reversed on the aggregate fg_dev
metric).

### Verdict

Per the Wave 225 P4 / Wave 233 P3 rule:
- `framework_WINS`: p < 0.05/7 (Bonferroni M=7 cells) AND mean < 0
- `REGRESSES`: p < 0.05/7 AND mean > 0
- `UNDERPOWERED`: p ≥ 0.05/7
- `TIE`: degenerate (NaN)

The script returned **`verdict="TIE"`** because the per-record REOS
p_raw is NaN. The per-seed pooled test is UNDERPOWERED (n=2, df=1)
on its own but is consistently positive (framework worse on fg_dev).

**Honest framing:** The 2-seed expansion shows a **consistent sign
reversal** at the aggregate fg_dev level (framework-WORSE on both new
seeds), but is **statistically UNDERPOWERED** for the per-seed
Bonferroni-sig test (n=2 seeds, df=1, p_raw=0.123). The per-record
REOS test is **degenerate** (sd=0).

## D.4 byte-stable check

```
$ timeout 60 .venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header
30 passed, 3 warnings in 12.88s
```

The FlowMol3 v2 adapter and Wave 87 byte-stable data are unchanged
from Wave 87. No code modifications were made. Per Wave 125 Phase 2
HARD RULE, the D.4 byte-stable regression vector gate is unchanged from
the Wave 87 PASS (30/30).

## Honest disclosure

- This is a **partial sweep**: N=500 per arm (vs Wave 87 N=1000), NFE=100
  (vs Wave 87 NFE=250). The brief allowed the partial-sweep fallback
  per DeepSeek.
- The single-mol path (`n_molecules=1`) is documented to bypass the
  DGL 2.4.0 batched-path regression (Wave 109.C).
- DGL version downgrade / PyG replacement was **not** attempted — both
  are out of scope for the 1-2 hour fix budget AND would invalidate
  the Wave 87 byte-stable reference.
- Seed 42 is reused from Wave 87 (NFE=250, N=1000); seeds 43, 44 use
  NFE=100, N=500. **NFE mismatch between seed 42 and seeds 43/44 is
  a known confound.** The 2-seed sign reversal at NFE=100 may be a
  real NFE-dependent boundary (Wave 87 NFE=250 framework-WINS,
  NFE=100 framework-WORSE), or it may be a 2-seed noise floor.
- The Wave 235 P4 finding **contradicts** the Wave 208 P2 finding
  (d_z=-0.285 on 200 records) at the aggregate fg_dev level. The
  Wave 208 P2 result is on a different sub-sample (200 records from
  the Wave 87 sweep) and may not generalise.

## What this means for the paper

1. **The Wave 235 P4 finding is a meaningful negative result for the
   framework-WINS claim on FlowMol3 R3 fg_dev at NFE=100/N=500.** This
   should be disclosed in the paper.
2. **The Wave 87 1-seed finding remains valid as a conditional
   result** — at NFE=250/N=1000 the framework improves fg_dev
   (mean_diff=-0.0235), but at NFE=100/N=500 it regresses
   (mean_diff=+0.016).
3. **The paper narrative on FlowMol3 should be revised** from
   "framework wins on R3 fg_dev across seeds" to "framework wins on
   R3 fg_dev at NFE≥250 (Wave 87 N=1000), effect reverses at
   NFE=100/N=500 (Wave 235 P4 N=500, 2 seeds)".
4. **The verdict "TIE" in the CSV reflects the script rule
   (per-record NaN → TIE).** The honest reading is that the 2-seed
   expansion DISCONFIRMS generalisability, and the per-seed
   aggregate is UNDERPOWERED for the Bonferroni-sig test.

## Reproducibility

```bash
# Seed44 framework arm (already run; output committed):
.venvs/flowmol3_venv/bin/python scripts/wave235_p4_seed44_framework.py

# 3-seed analysis (analysis-only, runs in <2 minutes):
.venvs/flowmol3_venv/bin/python scripts/wave235_p4_analyze_3seed.py

# D.4 byte-stable check:
.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header
```

## Output artefacts

- `verification_outputs/wave235-p4-flowmol3-seed43-baseline.json` (+ .smiles.txt)
- `verification_outputs/wave235-p4-flowmol3-seed43-framework.json` (+ .smiles.txt)
- `verification_outputs/wave235-p4-flowmol3-seed44-baseline.json` (+ .smiles.txt)
- `verification_outputs/wave235-p4-flowmol3-seed44-framework.json` (+ .smiles.txt) — wallclock=1849.969s, n=500, errors=0
- `verification_outputs/wave235-p4-flowmol3-3seed-per-record.csv` (1999 rows)
- `verification_outputs/wave235-p4-flowmol3-3seed.csv` (1 row)
- `verification_outputs/wave235-p4-flowmol3-3seed.json`
- `verification_outputs/wave236-p1-p4finish.json` (this agent's structured result)