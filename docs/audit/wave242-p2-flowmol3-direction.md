# Wave 242 P2 — FlowMol3 Per-Seed Direction Verification

## TL;DR

| Item | Value |
|---|---|
| Wave 242 P1 inputs (seed 43/44 NFE=250 N=200 single_mol) | **MISSING** (rescue script never executed) |
| Pooled 3-seed per-record paired-t at matched protocol | **NOT COMPUTABLE** (P1 inputs absent + protocol mismatch) |
| Direction pattern | **inconsistent** (seed 42 framework_better; seeds 43/44 unknown) |
| Seed 42 (Wave 87 + Wave 216 P1 projected) | per-record d_z = **-0.294** (framework_better, bonf-sig) |
| Seed 43 (Wave 242 P1 NFE=250 N=200 single_mol) | **FAIL_INPUT_MISSING** |
| Seed 44 (Wave 242 P1 NFE=250 N=200 single_mol) | **FAIL_INPUT_MISSING** |
| Verdict | **TIE** (Wave 242 P1 inputs missing) |
| Rescue successful | **false** |

## CRITICAL data-availability disclosure (HARD STOP)

Per Wave 242 P2 hard rule #1, this analysis **STOPS** because the Wave 242 P1 inputs
are missing on disk:

```
ls /home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave242-* :
  (no matches)

ls /home/hugo/codes/flowa-multistep-reinference/docs/audit/wave242-* :
  (no matches)
```

Required inputs that DO NOT exist:

1. `verification_outputs/wave242-p1-flowmol3-seed43-baseline.json` — MISSING
2. `verification_outputs/wave242-p1-flowmol3-seed43-framework.json` — MISSING
3. `verification_outputs/wave242-p1-flowmol3-seed44-baseline.json` — MISSING
4. `verification_outputs/wave242-p1-flowmol3-seed44-framework.json` — MISSING
5. `docs/audit/wave242-p1-flowmol3-rescue.md` — MISSING

The Wave 242 P1 rescue script **exists** at
`/home/hugo/codes/flowa-multistep-reinference/scripts/wave242_p1_flowmol3_rescue_single_mol.py`
(4.4 KB; written 2026-09-21 21:02) but was **NEVER EXECUTED** before this P2
agent was launched. The script targets:

- `--nfe 250` (FlowMol3 paper default; matches Wave 87)
- `--n-total 200` (reduced from Wave 87's 1000 due to single_mol path slowness; ~33 min/arm vs 2.78 h/arm)
- `--nfe-batch 1` (single_mol path; bypasses DGL 2.4.0 batched-path bug)
- `--device cuda:0` (single GPU only)
- `--seed 43` and `--seed 44` (seed=42 is Wave 87 reference; do NOT re-run)

## Consequence

The primary goal of Wave 242 P2 — a 3-seed per-record paired-t at the
single_mol matched protocol — is **NOT COMPUTABLE** from the available data.

The closest available per-record data:

- **Seed 42**: Wave 87 (aggregate only) + Wave 216 P1 projected
  (reos_fg_contrib_proxy projected from actual n=200 to n=1000).
- **Seeds 43/44**: **DO NOT EXIST**. No per-record data is available at any
  NFE/N/path. Cannot compute fg_dev paired-t, cannot compute mean_diff,
  cannot compute d_z.

## What was computed (best-available data)

| Seed | Source | NFE | N | Graph path | Per-record d_z | Agg fg_dev mean_diff | Direction | Verdict |
|---|---|---:|---:|---|---:|---:|---|---|
| 42 | Wave 87 + Wave 216 P1 projected | 250 | 1000 | batched | -0.294 | -0.0235 | framework_better | framework_WINS |
| 43 | **MISSING** | 250 | 200 | single_mol | **NA (FAIL_INPUT_MISSING)** | **NA** | **NA** | **FAIL_INPUT_MISSING** |
| 44 | **MISSING** | 250 | 200 | single_mol | **NA (FAIL_INPUT_MISSING)** | **NA** | **NA** | **FAIL_INPUT_MISSING** |

### Per-seed test details

#### Seed 42 (Wave 87 reference, NFE=250, N=1000, batched DGL)

Computed (same as Wave 240 P2; carry-over from prior waves):

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

#### Seed 43 (Wave 242 P1, NFE=250, N=200, single_mol)

**FAIL_INPUT_MISSING.** The expected output file
`verification_outputs/wave242-p1-flowmol3-seed43-baseline.json` (and
`-framework.json`) does NOT exist on disk. The Wave 242 P1 rescue script
`scripts/wave242_p1_flowmol3_rescue_single_mol.py` was never executed.

#### Seed 44 (Wave 242 P1, NFE=250, N=200, single_mol)

**FAIL_INPUT_MISSING.** Same as seed 43.

### Pooled 3-seed test

**NOT COMPUTABLE.** Pooling is blocked by:

1. Seed 43/44 inputs **MISSING** (cannot compute per-record paired-t for n=200).
2. Even if present, pooling would mix NFE confound (250/250 OK; seed 42 vs 43/44 same NFE),
   N confound (1000 vs 200 — seed 42 weighted ~5x more).
3. Graph path confound (batched DGL vs single_mol — DIFFERENT path).

The pooled verdict is set to **TIE** with NaN values.

## Comparison with prior waves

### Compare against Wave 235 P4 (NFE=100, N=500, single_mol)

Wave 235 P4 found:

- Per-seed pooled d_z (n=2, df=1) = +3.625 (underpowered, framework_worse)
- Per-record d_z (n=999, df=998) = NaN (sd=0 degenerate; reos_flag is binary)
- Aggregate fg_dev mean_diff = +0.0188 / +0.0126 (framework WORSE)

Wave 235 P4 was the closest previous FlowMol3 direction analysis but at NFE=100.

### Compare against Wave 240 P2 (NFE=250, N=1000, batched; P1 failed)

Wave 240 P2 reported:

- Pooled 3-seed per-record paired-t at matched protocol: NOT COMPUTABLE
  (Wave 240 P1 inputs also missing).
- Direction pattern (using aggregate fg_dev sign): **2_OF_3_MAJORITY** (sign
  reversal across the NFE boundary; seed 42 framework_better at NFE=250,
  seeds 43/44 framework_worse at NFE=100).
- Verdict: **TIE**.

Wave 242 P2 inherits the same Wave 240 P2 conclusion structure but cannot
even compute per-record paired-t at the single_mol matched protocol because
the rescue script was not executed.

## NFE confound assessment (per task hard rule)

**NFE confound: UNRESOLVABLE in Wave 242.**

- Wave 87 seed=42 reference (NFE=250, N=1000, batched DGL): framework_better
  per-record d_z = -0.294, bonf-sig.
- Wave 235 P4 seeds 43/44 (NFE=100, N=500, single_mol): framework_worse
  per-record d_z = NaN (sd=0); aggregate fg_dev mean_diff +0.0188 / +0.0126.
- Wave 242 P2 seeds 43/44 (NFE=250, N=200, single_mol): MISSING.

Without the Wave 242 P1 outputs, we cannot test whether NFE=250 at the
single_mol matched protocol resolves the NFE confound. The honest claim
boundary remains: "framework improves FlowMol3 at NFE=250/N=1000/batched"
with sign reversal at NFE=100/N=500/single_mol.

`nfe_was_main_confound`: **NA (cannot test without Wave 242 P1 data)**

## Direction pattern summary

- Seed 42: framework_better (agg mean_diff = -0.0235, NFE=250, batched)
- Seed 43: **UNKNOWN (inputs missing)**
- Seed 44: **UNKNOWN (inputs missing)**
- Sign reversal at seeds 43/44: **NOT TESTABLE**
- Honest label: **inconsistent** (seed 42 says framework_better; seeds 43/44
  unknown; cannot establish direction_pattern = all_consistent)

`direction_pattern`: **inconsistent**
`rescue_successful`: **false**

## Hard rules compliance

- DO NOT re-run seed 42: **complied** (used Wave 87 + Wave 216 P1 reference)
- DO NOT re-run seed 43/44: **complied** (STOPPED at hard rule #1 — inputs missing)
- DO report exactly what the data shows: **complied** (honest disclosure of
  missing Wave 242 P1 inputs; pooled test marked NaN; verdict = TIE; rescue_successful = false)
- DO compare against Wave 235 P4 result (NFE=100 N=500 single_mol): **complied**
  (see "Compare against Wave 235 P4" section above)
- DO compare against Wave 240 P2 result (P1 failed; TIE 0/0): **complied**
  (Wave 242 P2 inherits Wave 240 P2's FAIL_INPUT_MISSING structure)
- DO report rescue_successful=true iff direction_pattern == "all_consistent":
  **complied** (direction_pattern = "inconsistent"; rescue_successful = false)
- DO NOT pretend Wave 242 matches Wave 87 protocol: **complied** (seed 42 N=1000
  batched vs seeds 43/44 N=200 single_mol — protocol mismatch explicitly disclosed)

## Recommended next step

1. **Execute Wave 242 P1**:
   ```
   python scripts/wave242_p1_flowmol3_rescue_single_mol.py --seed 43
   python scripts/wave242_p1_flowmol3_rescue_single_mol.py --seed 44
   ```
   Each invocation runs `tools/wave87_n1000_sweep.py` with strict args:
   `--seed-base 43|44 --nfe 250 --n-total 200 --nfe-batch 1 --device cuda:0`.
   Wall-clock budget: ~33 min/arm × 2 seeds × 2 arms = ~2.2 h total.

2. **Verify outputs**:
   ```
   ls verification_outputs/wave242-p1-flowmol3-seed{43,4}-{baseline,framework}.json
   ```
   Each JSON must contain n_records ≥ 200 per arm.

3. **Write rescue audit**: `docs/audit/wave242-p1-flowmol3-rescue.md` documenting
   the single_mol path rescue and per-record metrics.

4. **Re-execute this P2 analysis**: Re-run Wave 242 P2 with the new inputs.
   The pooled_3seed verdict will be evaluable at N=200 (pooled n=1400, df=1399).

## Files

- CSV: `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave242-p2-flowmol3-direction.csv`
- Audit doc: `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave242-p2-flowmol3-direction.md`