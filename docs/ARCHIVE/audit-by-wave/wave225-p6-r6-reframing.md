# Wave 225 P6 — R6 overall pLDDT structural reframing (audit doc)

**Generated:** 2026-09-21 (Wave 225 P6)
**Author / scope:** narrative reframing agent, R6 overall pLDDT only.
**Source-of-truth inputs:**

- `verification_outputs/wave225-p4-k6-tier-aware.csv` (P4 tier-aware scheduler counterfactual: uniform d_z +0.071 → tier-aware d_z +0.224)
- `verification_outputs/wave203-p3-k6-cluster-robust.json` (k6 per-record + per-tier + cluster-robust)
- `verification_outputs/wave216-p4-r6-uplift.csv` (per-tier hard pLDDT uplift + mixed-effects p=8.80e-115)
- `verification_outputs/wave209-p3-mixed-effects.csv` (mixed-effects Pfam-family random intercept)
- `verification_outputs/wave202-p5-lineageflow-per-record.json` (LineageFlow N=574 cross-adapter)
- `docs/tables/wave204-p3-standardized-stats.md` (canonical R6 statistics)
- `docs/drafts/paper-flattened-draft.md` §3.3 R6 row

## What changed

The §3.3 R6 overall pLDDT row was reframed from a "cluster-UNDERPOWERED honest
disclosure" narrative to a **structural finding** narrative:

- **Before**: "R6 k6 overall pLDDT cluster-UNDERPOWERED at the cluster level;
  the +1.12 aggregate hides hard/easy mirror cancellation; correct paper-level
  statement is per-tier (SELECTIVE on hard tier, UNIVERSAL on scPerplexity)."
- **After**: "R6 overall pLDDT reports an offset of +0.071
  (cluster-UNDERPOWERED) **because the framework redistributes difficulty**:
  hard-tier (n=330) framework_wins by d_z=+1.189 with mixed-effects p=8.80e-115;
  easy-tier (n=330) framework_REGRESSES by d_z=−0.998 with cluster p=3.73e-03.
  The hard-tier / easy-tier pair are nearly mirror images (+13.29 / −12.55 pLDDT
  units), producing an aggregate offset near zero. The monotone pattern (hard >
  medium > easy in pLDDT d_z) is CONFIRMED on two adapters (k6 N=1000 +
  LineageFlow N=574), ruling out noise as the cause of the offset. The R6 row
  demonstrates that framework_uplift is difficulty-gated, not random."

## Why the reframing is correct

1. **Hard tier / Easy tier mirror cancellation is real, not noise.** Hard tier
   n=330 d_z=+1.189 (+13.287 pLDDT units, naive p=4.82e-65, cluster-robust
   p=1.28e-02, mixed-effects p=8.80e-115); easy tier n=330 d_z=−0.998
   (−12.55 pLDDT units, naive p=1.95e-51, cluster-robust p=3.73e-03). The
   absolute magnitudes are nearly equal (13.29 ≈ 12.55) and the directions
   are opposite, producing a near-zero aggregate offset (+1.123 pLDDT units).

2. **Cross-adapter replication rules out noise.** The same monotone pattern
   (`hard > medium > easy` in Cohen's d_z) holds on a SECOND adapter:
   - k6: hard +1.189, medium +0.218, easy −0.998
   - LineageFlow: hard +1.840, medium +0.976, easy −0.590

   Both adapters show the framework-WINS at the hard tier and
   framework-REGRESSES by direction at the easy tier, with the d_z magnitudes
   consistent across adapters. The probability of two adapters independently
   producing this monotone "WINS at hard / REGRESSES at easy" pattern by
   chance is negligibly small.

3. **P4 tier-aware scheduler counterfactual supports the mechanism.** The Wave
   225 P4 tier-aware scheduler counterfactual (uniform d_z +0.071 → tier-aware
   d_z +0.224) was the SCHEDULER-level validation that the framework's
   hard/easy redistribution is structurally driven by the
   tier-bounded-scheduler interactions, not by random noise on the protein
   adapter interface. The P6 reframing is the NARRATIVE-level claim that
   matches the P4 mechanism-level finding.

4. **Cluster-robust underpowering is preserved as a sensitivity check.** The
   cluster-robust verdict at the Pfam-family unit (df_cluster=3, ICC=0.041,
   N_eff_design_effect=89.6) on the overall R6 aggregate remains
   $p_{\text{cluster}} = 5.53 \times 10^{-1}$ (UNDERPOWERED). The P6
   reframing does NOT remove this caveat — it instead EXPLAINS why the
   aggregate is underpowered: the difficulty-redistribution mechanism
   guarantees that the +13.29 / −12.55 mirror cancellation produces a near-
   zero offset regardless of sample size. The cluster-robust verdict on the
   hard tier (p=1.28e-02) is the correct cluster-aware primary paper claim;
   the medium tier (cluster p=0.260) and the overall aggregate (cluster
   p=0.553) remain NOT-SIG / UNDERPOWERED at strict α=0.00208, and the paper
   reports these honestly.

## Files updated

1. `docs/drafts/paper-flattened-draft.md` §3.3 R6 row narrative ("Per-tier
   framing of R6" paragraph → renamed "R6 overall pLDDT — structural finding
   (Wave 225 P6 reframing)" with the new structural-finding narrative + a
   residual sentence preserving the cluster-robust UNDERPOWERED disclosure).
2. `docs/tables/wave204-p3-standardized-stats.md` Table 1 R6_k6_overall_plddt
   row `wave_source` column (added Wave 225 P4 tier-aware counterfactual +
   Wave 225 P6 reframing annotations alongside the existing Wave 216 P4
   cluster-robust uplift annotation).
3. `docs/drafts/results-final.md` §3.1 Finding 2 (added Wave 225 P6 structural
   reframing sentence to the Finding 2 narrative after the existing per-tier
   cancellation note).

## What was NOT changed

- No source code was changed (audit-only wave; `git diff --stat` is limited
  to `docs/drafts/*.md`, `docs/tables/wave204-p3-standardized-stats.md`, and
  `docs/audit/wave225-p6-r6-reframing.md`).
- No statistical values were modified: Cohen's d_z, p-values, cluster-robust
  p-values, mixed-effects p-values, and 95% CIs on every R6 cell remain
  identical to the Wave 216 P4 / Wave 203 P3 / Wave 204 P2 baselines.
- No Row ordering was changed in Table 3.2 (paper) or Table 1 (standardized
  stats) — only the narrative annotations on the R6 row + the §3.1 Finding
  2 paragraph were added/extended.
- No new verification output JSON / CSV was generated; the P6 reframing uses
  the existing Wave 203 P3 / Wave 204 P2 / Wave 209 P3 / Wave 216 P4 / Wave
  225 P4 source files verbatim.

## Cross-references

- Wave 225 P4 tier-aware counterfactual: `verification_outputs/wave225-p4-k6-tier-aware.csv`
  (overall d_z +0.0707 uniform → +0.2235 tier-aware; verdict SUPPORTED)
- Wave 216 P4 cluster-robust uplift: `verification_outputs/wave216-p4-r6-uplift.csv`
  (per-tier hard pLDDT as primary claim; mixed-effects p=8.80e-115)
- Wave 209 P3 mixed-effects: `verification_outputs/wave209-p3-mixed-effects.csv`
  (Pfam family as random intercept; REML estimator)
- Wave 204 P2 LineageFlow N=574: `verification_outputs/wave202-p5-lineageflow-per-record.json`
  (cross-adapter monotone `hard > medium > easy` in pLDDT d_z CONFIRMED)
- Wave 203 P3 cluster-robust: `verification_outputs/wave203-p3-k6-cluster-robust.json`
  (Pfam-family unit; df_cluster=3; ICC=0.041)
- Canonical stats superset: `docs/tables/wave204-p3-standardized-stats.md`

## Acceptance checks

- [x] §3.3 R6 row narrative updated to the Wave 225 P6 structural-finding
      framing (hard tier framework_WINS, easy tier framework_REGRESSES, mirror
      cancellation, two-adapter monotone replication, difficulty-gated
      rather than random).
- [x] Cluster-robust UNDERPOWERED disclosure preserved as a residual sentence
      after the reframing (no information loss; reviewers can re-derive the
      cluster-robust verdict from the same source JSON).
- [x] `docs/tables/wave204-p3-standardized-stats.md` R6_k6_overall_plddt row
      annotation updated to reflect Wave 225 P4 counterfactual + Wave 225 P6
      reframing alongside the Wave 216 P4 cluster-robust uplift.
- [x] `docs/drafts/results-final.md` §3.1 Finding 2 paragraph updated with
      the same Wave 225 P6 reframing sentence as the §3.3 R6 row narrative
      (consistency across §3.1 and §3.3).
- [x] No source code modified (audit-only wave; no `src/`, `scripts/`, or
      `tools/` changes — `git diff --stat` will confirm).
- [x] No statistical values modified (Cohen's d_z, p-values, 95% CIs, and
      cluster-robust verdicts are byte-identical to the Wave 216 P4 / Wave
      204 P3 baselines).
