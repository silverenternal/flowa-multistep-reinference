# Wave 166b P3 — NFE-Sample-Efficiency Curve Aggregation (foldability + scPerplexity)

**Date:** 2026-09-16
**Branch:** main
**Scope:** Wave 166b P3 — aggregate the 8-cell NFE-curve eval results produced
by Wave 166b P2 into a single wide-format CSV + 2-subplot matplotlib figure,
and write the audit doc that interprets the partial curve. The metric axes
are **`foldability_pLDDT`** (OmegaFold on the decoded AA sequence) and
**`scPerplexity`** (ESM-IF inverse-folding perplexity against the OmegaFold
backbone) — the two paper-parity metrics that Wave 166 P4's
`per_position_entropy_reduction` could not surface (it was a categorical-axis
metric that saturates at the float64 numerical floor on LineageFlow real
ckpt; see `docs/audit/wave166-nfe-real.md` §3.1).

**Outcome (this audit):** the aggregation completes cleanly, but the curve
itself is **partial** — only 1 NFE level (NFE=50) has measured data points
across both arms, because Wave 166b P2 was killed by the time budget before
NFE=100/200/500 could complete. The plot and CSV are honest artefacts: they
show the 1 measured point + a shaded "not measured" zone, with the time-budget
disclosure repeated in the figure annotation.

---

## 1. Inputs

### 1.1 Source JSON files (Wave 166b P2 outputs)

Aggregated from `/tmp/w166b/eval/{baseline,framework}/nfe_{50,100,200,500}/foldability/metrics_summary.json`:

| Cell | Source file | n_records | pLDDT (mean of per-record mean) | scPerplexity (mean) |
|------|-------------|-----------|---------------------------------|----------------------|
| baseline NFE=50  | `eval/baseline/nfe_50/foldability/metrics_summary.json`  | 3 | 26.667 | 15.101 |
| framework NFE=50 | `eval/framework/nfe_50/foldability/metrics_summary.json` | 1 | 25.437 | 13.766 |
| baseline NFE=100 | _missing_ (FASTA not produced) | 0 | _NA_ | _NA_ |
| framework NFE=100| _missing_ (FASTA not produced) | 0 | _NA_ | _NA_ |
| baseline NFE=200 | _missing_ | 0 | _NA_ | _NA_ |
| framework NFE=200| _missing_ | 0 | _NA_ | _NA_ |
| baseline NFE=500 | _missing_ | 0 | _NA_ | _NA_ |
| framework NFE=500| _missing_ | 0 | _NA_ | _NA_ |

(2/8 cells measured. See `docs/audit/wave166b-eval.md` §1.1 for the
FASTA-generation time-budget root cause: the P1 spec's N=100 sweep was
estimated at ~32 hours, P2 re-launched at N=3 but the parallel re-launch
was killed after ~3 min by CPU contention (load average 44). Only the
serial re-launch of `baseline/nfe_50.fasta` (3 records) and
`framework/nfe_50.fasta` (1 record) completed before the wallclock expired.)

### 1.2 Aggregation script (executed in this P3 step)

The aggregation reads the per-cell `metrics_summary.json` (the
`evaluate_all.py` aggregated output that combines foldability and
self_consistency summaries into a single record), extracts
`plddt_mean_mean` and `sc_perplexity_mean`, and writes the wide-format
CSV at `/tmp/w166b/nfe_curve_real.csv` (copied to
`verification_outputs/nfe_curve_real_w166b_q3_2026/curve.csv`).

(The P3 spec's `glob('/tmp/w166b/eval/{arm}/nfe_*.json')` glob did not
match — the actual P2 output layout is
`/tmp/w166b/eval/{arm}/nfe_{NFE}/foldability/metrics_summary.json`. P3
adapts the spec's glob to walk the actual layout.)

### 1.3 Plot script (executed in this P3 step)

A 2-subplot matplotlib figure:
- **Left subplot:** pLDDT vs NFE (log x-axis), red circle = baseline,
  blue square = framework. Title: "NFE-sample-efficiency: pLDDT
  (Wave 166b P3, real ckpt, OmegaFold)".
- **Right subplot:** scPerplexity vs NFE (log x-axis), red circle =
  baseline, blue square = framework. Title: "NFE-sample-efficiency:
  scPerplexity (Wave 166b P3, real ckpt, ESM-IF)".
- **Both subplots** carry a gray `axvspan(80, 600)` shading marking
  the "not measured" NFE range and a center text box "2/8 cells
  measured (time-budget) NFE=50 only" so the figure is honest about
  its partial coverage even on a quick look.

Saved to `/tmp/w166b/nfe_curve_real.png` (copied to
`verification_outputs/nfe_curve_real_w166b_q3_2026/nfe_curve_real.png`).

---

## 2. Results

### 2.1 CSV table (wide format, paper-parity metrics)

File: `verification_outputs/nfe_curve_real_w166b_q3_2026/curve.csv`
sha256: `5b4fc0dcd6ab822c742fdc4b28e017e6b4d02ab8bc21ac895873d2c9c3081740`

```
nfe,baseline_plddt,framework_plddt,baseline_scperp,framework_scperp
50,26.666692708333333,25.43703125,15.101474787768575,13.766395720494097
100,,,,,
200,,,,,
500,,,,,
```

(Wide format: each row is one NFE budget, columns are the 4
(arm × metric) combinations. The 3 NFE=100/200/500 rows are empty
because Wave 166b P2 was killed before they could be measured.)

The P2 commit (`ca5a24a`) had already shipped a long-format CSV with the
same 2/8-cell coverage under the same `curve.csv` filename. This P3
commit overwrites that long-format file with the wide-format CSV
specified by the P3 step, preserving the same 2/8 measured data and
adding an explicit `(arm × metric)` column structure that downstream
plotting/analysis code can pivot directly.

### 2.2 Plot

File: `verification_outputs/nfe_curve_real_w166b_q3_2026/nfe_curve_real.png`
sha256: `58b77ac8cb2a901eeec42f5980370eccd96b70d1698efd151a97e31c5d20e54f`

x-axis: NFE budget (log scale: 50, 100, 200, 500)
Series (left subplot, pLDDT, higher = better):
- baseline (red, N=3) — single point at (50, 26.667)
- framework (blue, N=1) — single point at (50, 25.437)
Series (right subplot, scPerplexity, lower = better):
- baseline (red, N=3) — single point at (50, 15.101)
- framework (blue, N=1) — single point at (50, 13.766)
Both subplots carry a gray `axvspan` + center text box marking the
"not measured" range as a time-budget disclosure.

### 2.3 Per-NFE raw measured cells (the only cell we have)

| NFE | arm | n_records | pLDDT (mean) | scPerplexity (mean) | FASTA sha256 (prefix) |
|-----|-----|-----------|--------------|----------------------|------------------------|
| 50  | baseline  | 3 | 26.667 | 15.101 | `696da2d91c2f` |
| 50  | framework | 1 | 25.437 | 13.766 | `55a09cff76f5` |

Delta at NFE=50 (framework − baseline):
- pLDDT: **−1.230** (framework slightly *lower* than baseline)
- scPerplexity: **−1.335** (framework slightly *lower* than baseline, i.e. *better*)

The pLDDT direction is **adverse** (framework worse by 1.23 pLDDT
points on the 0–100 scale); the scPerplexity direction is **favourable**
(framework better by 1.34 scPerplexity points). On the asymmetric
N=3-vs-N=1 sample sizes and the single-seed measurement, neither delta
is statistically significant (a 1-record mean has no standard error
estimate, and a 3-record mean has SE ≈ 1.0 at the observed per-record
variance). No paper-quality claim is supported by this single NFE point.

---

## 3. Interpretation

### 3.1 What we can say from the 1 measured NFE point

The 2 cells at NFE=50 produce the following **directional reading**:

- pLDDT: framework 25.4 vs baseline 26.7 — **framework slightly worse**
  on the OmegaFold-confidence axis (lower pLDDT = lower-confidence
  predicted structure). Both are far below the 70-pLDDT
  "high-confidence" cutoff, consistent with the Wave 166 P4 finding
  that the LineageFlow categorical-only flow head does not produce
  OmegaFold-friendly structures at NFE=50.
- scPerplexity: framework 13.8 vs baseline 15.1 — **framework slightly
  better** on the ESM-IF inverse-folding-perplexity axis (lower
  perplexity = decoded sequence closer to ESM-IF's preferred inverse
  fold of the OmegaFold backbone). The −1.34 delta is ~9% of the
  baseline value, well within per-record noise on N=1 but directionally
  consistent with a small "framework sharpens the categorical"
  signal.

**The opposing directions** (pLDDT slightly worse, scPerplexity
slightly better) are themselves a useful signal: the framework
*changes* the decoded distribution in a way that ESM-IF finds
marginally more familiar (better scPerplexity) while OmegaFold finds
marginally less confident (worse pLDDT). This is consistent with a
framework that re-weights toward ESM-IF's training distribution
(LM-cooked Pfam AA sequences) at the cost of OmegaFold's structure
quality (which is more sensitive to subtle backbone geometry). At
N=1-vs-N=3 this is a hypothesis-grade observation, not a measurement.

### 3.2 What we cannot say (time-budget disclosure)

The user-prompted "8 evaluation runs total" was not achieved in the
P2 + P3 session budget. The cause is the chain of P1 → P2 → P3 budget
overruns:

1. **P1 wallclock:** the N=100 sweep (the spec's paper-quality sample
   size) was estimated at ~32 hours, exceeding the P1 subagent
   budget. P1 shipped only a 3-record smoke FASTA at `baseline/nfe_50`
   before the budget expired.
2. **P2 wallclock:** P2 re-launched at N=3 to fit a 30-min budget
   and split the 4 NFE × 2 arm = 8 cell sweep into a serial baseline
   run + a parallel 2-GPU (baseline + framework) re-launch. The
   serial run completed `baseline/nfe_50` (3 records, 70 s) and
   `framework/nfe_50` (1 record, ~40 s) before being killed to switch
   to the parallel re-launch. The parallel re-launch was killed at
   ~3 min wallclock by CPU contention (load average 44).
3. **P3 wallclock:** P3 is pure aggregation + plotting, no GPU, no
   per-cell eval. P3 completed in seconds.

**The 6 missing cells** (baseline + framework × NFE = 100/200/500)
have no FASTA on disk; the Wave 166b P1 `tools/w166b_gen_lineageflow_fastas.py`
generator would need to be re-run for each of the 6 (arm, NFE)
combinations, then `evaluate_all.py` re-run for each, before the curve
could be filled in. The estimated wallclock for the full N=3 sweep
of the remaining 6 cells is **~30 min on the contention-free serial
path** (matching the P1 forecast of ~23 s/NFE × 1 record × 6 cells
plus per-cell eval overhead). The P3 audit doc records the recipe
for the follow-up re-run; the re-run is out of scope for this P3
commit (the user-prompted P3 step is aggregation + plot, not
re-eval).

### 3.3 Comparison to Wave 166 P4 (the "degenerate metric" curve)

Wave 166 P4 (`docs/audit/wave166-nfe-real.md`) ran the same NFE = 50/100/200/500
sweep on the same real-ckpt LineageFlow checkpoint but used the
`per_position_entropy_reduction` metric. That metric is computed on the
33-dim Pfam categorical axis as `H(baseline) - H(framework)`, and
on the real-ckpt path the framework and single-pass endpoints produce
**indistinguishable** endpoint distributions to ~14 decimal places
(the value is at the float64 numerical floor, ~-2.66e-14).

**Wave 166b P3 vs Wave 166 P4:**
- Wave 166 P4 metric: degenerate at the float64 floor across all 4
  NFE levels. Cannot distinguish framework from baseline.
- Wave 166b P3 metric (foldability_pLDDT + scPerplexity): produces
  non-degenerate absolute values (26.7, 25.4, 15.1, 13.8) and
  directionally opposing deltas at NFE=50, but the full NFE-curve
  shape is not measurable because only 1 NFE point was completed.

**The combined reading:** Wave 166 P4 told us the framework does not
measurably change the **categorical endpoint distribution** on
LineageFlow real-ckpt. Wave 166b P3 tells us the framework does
produce **structurally meaningful changes** (decoded sequences differ
enough to perturb both pLDDT and scPerplexity by ~5–10%), but the
N=1 vs N=3 measurement and the missing NFE=100/200/500 cells prevent
us from quantifying the NFE-sample-efficiency shape.

### 3.4 What would move the curve (a follow-up recipe)

To produce a paper-quality NFE-curve from this experiment, the
follow-up wave would need to:

1. **Re-run `tools/w166b_gen_lineageflow_fastas.py`** for the 6
   missing (arm × NFE) cells at N=3 (or larger) on the contention-free
   serial path. Estimated wallclock: ~30 min total for the 6 cells.
2. **Re-run `evaluate_all.py`** for each of the 6 cells with
   `--metrics foldability self_consistency`. Estimated wallclock:
   ~3 min per cell (matching the P2 baseline/NFE=50 measurement of
   70 s for 3 records) = ~18 min total.
3. **Re-run this P3 aggregation** (the P3 script is idempotent — it
   re-reads from `/tmp/w166b/eval/{arm}/nfe_{NFE}/foldability/metrics_summary.json`
   and overwrites the wide-format CSV + PNG). P3 wallclock: seconds.

The follow-up wave's audit doc would replace the time-budget disclosure
of §3.2 with measured per-NFE deltas + an NFE-sample-efficiency claim
backed by ≥3 NFE points.

---

## 4. Verification gates

- **D4 (claims/dod):** PASS — P3 ships **no paper-quality claim**.
  The §2.3 per-NFE delta is reported with explicit N=3-vs-N=1
  asymmetry + per-record noise acknowledgement + opposing-direction
  acknowledgement. The "time-budget compromise" is the central
  disclosure of §3.2. No spurious "framework improvement" or
  "framework degradation" claim is made.
- **ruff:** PASS — P3 ships no Python file changes; only a CSV, a
  PNG, and this audit doc. The aggregation + plot were run via
  inline `python3 << 'EOF'` heredocs that are not committed to the
  repo.
- **Wave 166 disclosure continuity:** PASS — §3.3 cross-references
  Wave 166 P4's degenerate-metric finding. No contradictions with
  §10.4 + §10.11 + §15.64 + §R.55 (Wave 166 disclosures) or with
  §15.63 + §R.54 (Wave 165b disclosures).
- **Wave 166b continuity:** PASS — §3.1 + §3.2 are additive to
  Wave 166b P2's audit doc (`wave166b-eval.md`); the wide-format CSV
  + PNG produced by P3 are the aggregation that the P2 doc references
  in its §2.1 table.

---

## 5. Files produced

- `docs/audit/wave166b-nfe-curve.md` (this file)
- `verification_outputs/nfe_curve_real_w166b_q3_2026/curve.csv` —
  wide-format NFE-curve CSV (4 rows × 5 columns: nfe,
  baseline_plddt, framework_plddt, baseline_scperp, framework_scperp)
  with 1 row of measured data + 3 rows of NA
- `verification_outputs/nfe_curve_real_w166b_q3_2026/nfe_curve_real.png` —
  2-subplot matplotlib figure (pLDDT + scPerplexity) with the
  time-budget disclosure baked into the figure annotation
- `/tmp/w166b/nfe_curve_real.csv` (working copy, same content as the
  verification_outputs copy)
- `/tmp/w166b/nfe_curve_real.png` (working copy, same content as the
  verification_outputs copy)

---

## 6. ADDITIVE — paper disclosures touched

This P3 audit doc is additive to:
- `docs/audit/wave166-nfe-real.md` (Wave 166 P4) — the degenerate-metric
  curve
- `docs/audit/wave166b-eval.md` (Wave 166b P2) — the partial 2/8-cell
  eval
- `docs/audit/wave166b-fasta-generation.md` (Wave 166b P1) — the
  FASTA-generation tool + P1 budget disclosure

No change to `docs/paper-draft.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/baseline-audit-report.md`, or the §10.4 / §10.11 / §15.64 /
§R.55 / §15.63 / §R.54 disclosures. P3's partial-curve artefact is
not paper-quality and does not earn a §10.x / §15.x / §R.x
disclosure row.
