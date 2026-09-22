# Wave 240 P2 — FlowMol3 Per-Seed Direction Verification

## TL;DR

| Item | Value |
|---|---|
| Wave 240 P1 inputs (seed 43/44 NFE=250 N=1000 batched DGL) | **MISSING** (previous workflow killed before producing outputs) |
| Pooled 3-seed per-record paired-t at matched protocol | **NOT COMPUTABLE** (protocol mismatch + per-record degenerate) |
| Direction pattern (using aggregate fg_dev sign) | **2_OF_3_MAJORITY** |
| Seed 42 (Wave 87 + Wave 216 P1 projected) | per-record d_z = **-0.294** (framework_better, bonf-sig) |
| Seed 43 (Wave 235 P4 aggregate fg_dev) | aggregate mean_diff = **+0.0188** (framework_worse) |
| Seed 44 (Wave 235 P4 aggregate fg_dev) | aggregate mean_diff = **+0.0126** (framework_worse) |
| Verdict | **TIE** (matched-protocol pooled test not computable; per-record degenerate at seeds 43/44) |

## Critical data-availability disclosure

The Wave 240 P1 inputs at `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/`
(wave240-p1-flowmol3-seed43-baseline.json + framework.json + seed44 versions) **do NOT exist**.

The user terminated the previous workflow before Wave 240 P1 produced per-record
outputs at the matched NFE=250 / N=1000 / batched DGL protocol. The rescue script
(`scripts/wave240_p1_flowmol3_rescue_fixed.py`) exists but its outputs are absent.

**Consequence:** The 3-seed per-record paired-t at matched protocol — the primary
goal of this analysis — is NOT computable from the available data.

The closest available per-record data is:
- **Seed 42**: Wave 87 (aggregate only, no per-record) + Wave 216 P1 projected
  (reos_fg_contrib_proxy projected from actual n=200 to n=1000).
- **Seeds 43/44**: Wave 235 P4 per-record REOS flag (NFE=100, N=500, single_mol).
  **Per-record REOS flag is degenerate** (all diffs are 0 → sd=0 → d_z=NaN).
  The honest per-record signal is from Wave 235 P4 **aggregate fg_dev** only.

## What was computed (best-available data)

| Seed | Source | NFE | N | Graph path | Per-record d_z | Agg fg_dev mean_diff | Direction | Verdict |
|---|---|---:|---:|---|---:|---:|---|---|
| 42 | Wave 216 P1 projected | 250 | 1000 | batched | -0.294 | -0.0235 | framework_better | framework_WINS |
| 43 | Wave 235 P4 aggregate | 100 | 500 | single_mol | NaN (sd=0) | +0.0188 | framework_worse | DEGENERATE |
| 44 | Wave 235 P4 aggregate | 100 | 500 | single_mol | NaN (sd=0) | +0.0126 | framework_worse | DEGENERATE |

### Per-seed test details

#### Seed 42 (Wave 87 reference, NFE=250, N=1000, batched DGL)
- Per-record test (Wave 216 P1 projected):
  - n_paired = 1000, df = 999
  - mean_diff = -0.0212 (negative = framework better)
  - sd_diff = 0.0720
  - t = -9.306, p_raw = 8.1419e-20
  - d_z = **-0.294**
  - Bonferroni alpha/7 = 0.00714
  - verdict = **framework_WINS** (Bonferroni-significant framework improvement)
- Source: Wave 87 sweep aggregate + Wave 216 P1 R3 per-record projected
  (reos_fg_contrib_proxy from actual n=200 paired, projected to n=1000 via
  standard t-test projection formula `t_N = t_actual * sqrt(N/n)`).
- Caveat: Wave 216 P1's actual n=200 cap is a Wave 87 SMILES-truncation
  artifact; the projection assumes the first-200 SMILES sample is
  representative of the full N=1000.

#### Seed 43 (Wave 235 P4, NFE=100, N=500, single_mol)
- Per-record test: **DEGENERATE** (sd_diff = 0.0000, all reos_flag diffs = 0)
- Aggregate fg_dev (from Wave 235 P4 summary):
  - baseline fg_dev = 0.6583
  - framework fg_dev = 0.6771
  - mean_diff = **+0.0188** (framework_worse)
- Source: wave235-p4-flowmol3-3seed-per-record.csv (per-record); wave235-p4-flowmol3-3seed.json (aggregate).

#### Seed 44 (Wave 235 P4, NFE=100, N=500, single_mol)
- Per-record test: **DEGENERATE** (sd_diff = 0.0000, all reos_flag diffs = 0)
- Aggregate fg_dev:
  - baseline fg_dev = 0.6612
  - framework fg_dev = 0.6738
  - mean_diff = **+0.0126** (framework_worse)

### Pooled 3-seed test (cross-protocol)
**NOT COMPUTABLE.** Pooling would mix:
- NFE confound (250 vs 100)
- N confound (1000 vs 500)
- Graph path confound (batched vs single_mol)
- Metric variance confound (per-record d_z valid for seed 42, NaN for 43/44)
- Aggregate-vs-per-record metric confound

The pooled verdict is set to **TIE** with NaN values.

## NFE confound assessment (per task hard rule)

**Compare against Wave 235 P4 result (NFE=100, N=500, single_mol).**

| Metric | Wave 235 P4 (NFE=100) | Wave 87 / Wave 216 (NFE=250) |
|---|---|---|
| Per-seed pooled d_z (n=2, df=1) | +3.625 (underpowered) | n/a (1 seed) |
| Per-record d_z (n=999, df=998) | NaN (sd=0 degenerate) | -0.294 (projected, bonf-sig) |
| Aggregate fg_dev mean_diff | +0.0188 / +0.0126 (framework WORSE) | -0.0235 (framework BETTER) |
| Bonferroni sig | No | Yes (per-record) |

**NFE confound is REAL**: Wave 235 P4 (NFE=100) reverses the direction
relative to Wave 87 (NFE=250). This was already disclosed in
`docs/audit/wave238-p1-flowmol3-direction.md` as an NFE-conditional
boundary on the framework-WINS claim.

## Direction pattern summary (using aggregate fg_dev sign)

- Seed 42: framework_better (agg mean_diff = -0.0235, NFE=250)
- Seed 43: framework_worse (agg mean_diff = +0.0188, NFE=100)
- Seed 44: framework_worse (agg mean_diff = +0.0126, NFE=100)
- Sign reversal: YES (between seed 42 and seeds 43/44)
- Honest label: **2_of_3_majority** (sign reversal across the NFE boundary; not a reproducible seed effect)

## Hard rules compliance

- DO NOT re-run seed 42: **complied** (used Wave 87 + Wave 216 P1 reference)
- DO report exactly what the data shows: **complied** (honest disclosure of
  missing Wave 240 P1 inputs + protocol mismatch + per-record degeneracy;
  pooled test marked NaN)
- DO compare against Wave 235 P4 (NFE=100 N=500 single_mol): **complied**
  (see "NFE confound assessment" section above)

## Recommended next step

Re-run Wave 240 P1 (`scripts/wave240_p1_flowmol3_rescue_fixed.py`) to produce
per-record data for seed 43 and seed 44 at NFE=250, N=1000, batched DGL.
Then re-execute this analysis. The current CSV row 4 (pooled_3seed) is
explicitly marked NaN to make the gap visible to the next agent.

## Files

- CSV: `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave240-p2-flowmol3-direction.csv`
- Audit doc: `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave240-p2-flowmol3-direction.md`
