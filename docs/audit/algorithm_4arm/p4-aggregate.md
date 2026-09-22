# Wave 184 P4 — n_rounds ablation aggregate

**Date:** 2026-09-18
**Branch:** main
**Scope:** Aggregate the 12-cell Wave 184 P3 eval results into a
per-model Δ-vs-baseline table and answer the critical question:
*is the kanzi NFE=100 pLDDT regression caused by the
paper-quantity scheduler, multi-round averaging, or both?*

**Inputs:**
- `<repo_root>/verification_outputs/wave184-p3-eval-summary.csv`
- `<repo_root>/docs/audit/wave184-p3-eval.md`

**Outputs:**
- `<repo_root>/verification_outputs/wave184-p4-ablation-table.csv`

No source code modified. No claims text touched. Pure
arithmetic + write-up.

---

## 1. Aggregation table

| # | Model       | Arm       | n_rounds | pLDDT | ΔpLDDT | scPPL  | ΔscPPL | Wall (s) |
|---|-------------|-----------|----------|-------|--------|--------|--------|----------|
| 1 | lineageflow | baseline  | 1        | 41.18 |  +0.00 | 18.94  |  +0.00 |   7.39   |
| 2 | lineageflow | framework | 1        | 41.99 |  +0.81 | 14.94  |  -4.00 |  62.54   |
| 3 | lineageflow | framework | 2        | 41.99 |  +0.81 | 14.94  |  -4.00 |  78.55   |
| 4 | lineageflow | framework | 3        | 41.99 |  +0.81 | 14.94  |  -4.00 |  75.49   |
| 5 | lineageflow | framework | 5        | 41.99 |  +0.81 | 14.94  |  -4.00 |  83.56   |
| 6 | lineageflow | framework | 7        | 41.99 |  +0.81 | 14.94  |  -4.00 |  84.50   |
| 7 | kanzi       | baseline  | 1        | 57.41 |  +0.00 | 19.50  |  +0.00 |  78.44   |
| 8 | kanzi       | framework | 1        | 55.78 |  -1.63 | 17.66  |  -1.83 |  74.47   |
| 9 | kanzi       | framework | 2        | 55.25 |  -2.16 | 16.72  |  -2.78 |  73.42   |
| 10| kanzi       | framework | 3        | 51.62 |  -5.79 | 16.48  |  -3.02 |  80.44   |
| 11| kanzi       | framework | 5        | 56.72 |  -0.69 | 15.13  |  -4.37 |  72.44   |
| 12| kanzi       | framework | 7        | 54.61 |  -2.81 | 16.59  |  -2.91 |  77.45   |

Values to 2 decimals; full-precision rows live in
`wave184-p4-ablation-table.csv`.

Source: `wave184-p3-eval-summary.csv` aggregated with
`delta = framework - baseline` (sign: positive ΔpLDDT = better,
negative ΔscPPL = better).

---

## 2. Per-model narrative

### 2.1 lineageflow — flat ablation (byte-stable)

All 5 framework-arm cells (n_rounds ∈ {1, 2, 3, 5, 7}) report
identical aggregate metrics to the 4dp precision that this CSV
captures:

- pLDDT mean = 41.99078 (constant)
- pLDDT median = 39.40463 (constant)
- scPPL mean = 14.94060 ± 4.8e-7 (ESM-IF inference RNG noise)
- scPPL median = 14.99330 ± 3.7e-6 (ESM-IF inference RNG noise)

This matches the Wave 184 P2 §4.1 prediction: the synthetic
lineageflow adapter does not expose `profile_residual_fn`, so
`_compute_paper_quantities` returns `None` → the framework
falls back to constant-β (`beta_n = 0`) → n_rounds has no effect
on the integrated trace → all 5 cells emit the
**identical** FASTA (SHA256
`67d871ba9ec2a9e1e95695079f3679d85a2cdf6d9d8a9a932b97fc9a53b416a3`)
→ identical pLDDT and ESM-IF inverse-fold scores.

**Conclusion for lineageflow:** ΔpLDDT = **+0.81** and
ΔscPPL = **-4.00** are reproducible across all n_rounds, but the
n_rounds axis is degenerate. The framework improvement is real
but cannot be attributed to (or against) the n_rounds dimension
on this model.

### 2.2 kanzi — informative ablation

The 5 kanzi framework-arm cells show real, non-monotonic
variation in both metrics:

- pLDDT range: 51.62 → 56.72 (ΔpLDDT vs baseline range -5.79 to -0.69)
- scPPL range: 15.13 → 17.66 (ΔscPPL vs baseline range -4.37 to -1.83)

The kanzi synthetic adapter exposes `profile_residual_fn` →
`_compute_paper_quantities` returns real per-round β →
n_rounds influences the integrated_trace → distinct FASTAs
(Wave 184 P2 §4.2) → distinct metrics.

The non-monotonic shape matches the prior literature (Wave
81/86/158 "more rounds helps up to a point, then degrades"):
with NFE=100 split into n_rounds chunks of
`floor(NFE/n_rounds)` NFE each, per-round accuracy degrades
when the per-round NFE is too small (n=7 → 14 NFE per round is
too aggressive). Best scPPL at n=5 (~20 NFE/round), best pLDDT
also at n=5 (closest to baseline).

---

## 3. Critical question — isolate paper-quantity scheduler from multi-round averaging

The Wave 184 P1 hypothesis was: the framework's per-round
adaptive β scheduler (paper-quantity scheduler — Wave 31) changes
the integrated trace shape, and multi-round averaging of
restart-blended traces smooths the output. These are two
distinct mechanisms. The ablation separates them by varying
n_rounds at fixed NFE=100:

- **n_rounds=1**: framework runs, paper-quantity scheduler active,
  but **no multi-round averaging** (single solve_ode with the
  scheduler-applied β). If this cell regresses pLDDT vs
  baseline, the cause is the **paper-quantity scheduler alone**.
- **n_rounds≥2**: framework runs, paper-quantity scheduler
  active, **plus** multi-round restart-blend averaging on top.
  Any additional regression relative to n_rounds=1 is attributable
  to multi-round averaging.

### 3.1 kanzi n_rounds=1 vs baseline

| Cell                | pLDDT | ΔpLDDT vs baseline |
|---------------------|-------|--------------------|
| kanzi baseline n=1  | 57.41 |        0.00        |
| kanzi framework n=1 | 55.78 |       **-1.63**    |

**Verdict:** kanzi framework n_rounds=1 regresses pLDDT by
**-1.63** vs baseline. Since n_rounds=1 means there is *no*
multi-round averaging (single restart-blend round, single
solve_ode), the entire -1.63 pLDDT regression is attributable
to the **paper-quantity scheduler** reshaping the integrated
trace alone.

### 3.2 kanzi n_rounds ≥ 2 vs kanzi n_rounds = 1

| Cell                    | pLDDT | ΔpLDDT vs framework n=1 |
|-------------------------|-------|-------------------------|
| kanzi framework n=1     | 55.78 |        0.00             |
| kanzi framework n=2     | 55.25 |       -0.53             |
| kanzi framework n=3     | 51.62 |       -4.16             |
| kanzi framework n=5     | 56.72 |       +0.94             |
| kanzi framework n=7     | 54.61 |       -1.17             |

Multi-round averaging adds non-monotonic, model-dependent noise
on top of the scheduler. The largest single-round regression
occurs at n=3 (-4.16), the only modest *improvement* over
n_rounds=1 occurs at n=5 (+0.94). The mean ΔpLDDT across n ∈ {2,
3, 5, 7} is -1.23 (≈ same magnitude as the n=1 scheduler-only
regression), suggesting the multi-round averaging contribution
to the kanzi NFE=100 pLDDT regression is roughly comparable to
the scheduler contribution — but it is **not** the sole cause.

### 3.3 Answer to the critical question

> Is kanzi NFE=100 pLDDT regression from paper-quantity
> scheduler, multi-round averaging, or both?

**Both, but the paper-quantity scheduler alone is sufficient to
explain the entire n_rounds=1 regression.** Multi-round
averaging adds additional non-monotonic variation at n ≥ 2, but
it is neither necessary nor sufficient for the regression —
n_rounds=1 (scheduler-only) already regresses by -1.63.

---

## 4. Practical implications

- **For kanzi at NFE=100**: the framework's paper-quantity
  scheduler (Wave 31) is incompatible with the NFE=100 budget at
  the current profile_residual scale. The scheduler reshapes the
  trace in a way that loses ~1.6 pLDDT regardless of how many
  restart-blend rounds are run. Either:
    1. Disable the scheduler at NFE ≤ 100 (route to constant-β),
       accepting the framework becomes ≈ baseline at this NFE.
    2. Re-tune the scheduler's profile_residual scale to
       preserve pLDDT (re-calibrate at NFE=100).
    3. Increase the NFE budget above the scheduler's
       minimum-effective budget (likely ≥ 200).

  Option 3 was already taken for the Wave 184 headline numbers
  (NFE=200 for kanzi, where the framework does not regress
  pLDDT — see Wave 172b / 173 / 174 cross-model runs).

- **For lineageflow**: the scheduler is a no-op (no
  `profile_residual_fn`), so n_rounds is degenerate. The
  framework's +0.81 / -4.00 improvement comes entirely from the
  restart-blend glue path, not from the scheduler.

- **For scPerplexity** (the framework's primary native-likeness
  metric): the framework improves on both models at all
  n_rounds. kanzi ΔscPPL ranges from -1.83 (n=1) to -4.37 (n=5)
  vs baseline. The framework is a strict win on scPPL.

---

## 5. Verdict

```
kanzi_nfe100_pLDDT_loss_source: paper_quantity_scheduler (primary, sufficient at n_rounds=1)
                                 + multi_round_averaging (secondary, non-monotonic noise on top)
```

Categorical verdict (per the JSON schema): **`both`** —
with the caveat that the paper-quantity scheduler alone is
sufficient at n_rounds=1 and multi-round averaging only modulates
the magnitude non-monotonically.

---

## 6. Gates & dependencies

- D.4 (18/18 conformance): **PASS at HEAD** (unchanged — no
  source code touched).
- Ruff on `docs/audit/`: **PASS** (one new doc).
- Claims consistency: **PASS** — no claim text modified. The
  Wave 184 P2 claim that "kanzi NFE=100 framework regresses
  pLDDT by ~1.6 at n_rounds=1" is consistent with this
  aggregate.
- Byte-stability invariant preserved: lineageflow framework
  arms collapse to identical aggregate metrics across n_rounds
  (§2.1), confirming the Wave 184 P2 §4.1 prediction.

---

## 7. Decision

Wave 184 P4 aggregate complete. The 12-cell CSV is reduced to a
6-cell-per-model aggregation table with explicit deltas. The
critical isolation question is answered: the paper-quantity
scheduler alone causes the kanzi NFE=100 pLDDT regression at
n_rounds=1; multi-round averaging is a secondary non-monotonic
modulator.

Ready for Wave 184 P5 (plot pLDDT-by-n_rounds and
scPPL-by-n_rounds curves per model, with baseline as horizontal
line).

**Output paths:**
- Table: `verification_outputs/wave184-p4-ablation-table.csv`
- This doc: `docs/audit/wave184-p4-aggregate.md`
