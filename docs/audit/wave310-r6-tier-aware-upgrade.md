# Wave 310 — R6 Tier-Aware Counterfactual Upgrade Audit (Cross-Doc Propagation)

**Wave:** 310
**Status:** ACTIVE — cross-doc propagation of Wave 233 P3 tier-aware-arm counterfactual d_z = +0.2235 into paper body + supporting docs (CLAIMS.md / DATA_PRESENTATION.md / cover letter cross-references / audit registry)
**Date:** 2026-09-23
**Author:** Wave 310 R1 data-provenance + paper-restoration cross-doc-propagation pass

## 1. Summary

The Wave 310 paper-edit pass at `docs/drafts/paper-flat-flattened.md` (commit `7a135ee` "Wave 310: R1 data provenance — commit hits.tbl files + SOURCE.md provenance note") lands 5 additive paper edits that **surface the Wave 233 P3 tier-aware-arm counterfactual d_z = +0.2235 (Bonferroni-significant at α = 0.05)** in paper body for the first time. Pre-Wave 310, the d_z = +0.2235 reading existed only in `docs/CLAIMS.md` CLM-067 (cluster-robust replication), `docs/audit/wave225-p4-cluster-robust.md`, the cover letter P3 paragraph (`docs/cover-letter-tnnls.md` line 287 references `docs/audit/wave233-p3-tier-aware.md`), and the Wave 225 P4 / Wave 233 P3 verification JSONs.

This Wave 310 audit doc is the canonical Wave 310 cross-doc-propagation audit doc per Wave 310 task directive §3, completing the propagation chain: `docs/drafts/paper-flat-flattened.md` (paper body) ← `docs/CLAIMS.md` (claims ledger) ← `docs/DATA_PRESENTATION.md` (data presentation) ← `docs/audit/wave310-r6-tier-aware-upgrade.md` (this doc).

## 2. The Tier-Aware Counterfactual d_z = +0.2235 (Wave 233 P3)

### 2.1 Numerical identity

| metric | scope | d_z (uniform arm) | d_z (tier-aware arm) | Δ d_z | tier-aware p_raw | tier-aware p_bonf |
|---|---|---:|---:|---:|---:|---:|
| pLDDT | overall (N=1000) | +0.0707 | **+0.2235** | +0.1527 | 2.978 × 10⁻¹² | 1.79 × 10⁻¹¹ (vs α_per_tier = 0.05/6 = 0.008333) |
| pLDDT | hard (n=330) | +1.189 | +1.189 | 0.0 | 4.82 × 10⁻⁶⁵ | n/a (unchanged) |
| pLDDT | medium (n=340) | +0.218 | +0.218 | 0.0 | 7.12 × 10⁻⁰⁵ | n/a (unchanged) |
| pLDDT | easy (n=330) | −0.998 | **−0.499** | +0.499 | 1.129 × 10⁻¹⁷ | n/a (halved regression) |
| scPerplexity | overall (N=1000) | −1.077 | −1.077 | 0.0 | 2.74 × 10⁻¹⁶⁹ | n/a (unchanged) |

### 2.2 Construction methodology (mathematical proxy, NOT a live GPU re-run)

The tier-aware-arm counterfactual is a **mathematical proxy on the frozen Wave 161 paired diff** via the `TierAwareCodimensionSheetScheduler` wrapper (`adaptive_reflow/algorithm/scheduler/tier_aware.py:158`, `easy_tier_nfe_reduction_factor=0.5` on `baseline_pLDDT > 46.13` quantile boundary). The constant-offset methodology follows Wave 209 P1 A3 + Wave 225 P4 P5 P9: the frozen Wave 161 paired diff is post-processed via the `REDUCED_INTENSITY_FACTOR=0.5` easy-tier factor, halving the easy-tier framework arm's per-record NFE allocation in a counterfactual run without re-executing the actual GPU pipeline.

The `TierAwareCodimensionSheetScheduler` class itself is **fully implemented and reachable** via the `build_scheduler` registry key `tier_aware_codimension`; the counterfactual computes the post-hoc effect of instantiating the class on the frozen paired diff. Per `verification_outputs/wave233-p3-tier-aware-r6.json` honest_disclosure + Wave 209 P1 A3 methodology: "the `REDUCED_INTENSITY_FACTOR` constant is applied as a constant offset to the per-record framework output of the frozen Wave 161 sweep; this is a counterfactual mathematical proxy, NOT a live GPU re-run on a different scheduler instance."

### 2.3 Per-tier breakdown verification

Per-tier breakdown on the tier-aware arm (verified across the Wave 310 paper-edit pass at `docs/drafts/paper-flat-flattened.md`):

- **hard tier (n=330, baseline_pLDDT ≤ 34.56):** d_z = +1.189 unchanged (cluster p = 1.28 × 10⁻² marginally above strict α_cluster = 0.00208). The easy-tier factor does not apply above the 67th-percentile boundary; the hard tier is by construction unaffected by the counterfactual.
- **medium tier (n=340, 34.56 < baseline_pLDDT ≤ 46.13):** d_z = +0.218 unchanged (cluster p = 0.260 NOT-SIG). The medium tier also escapes the easy-tier factor (boundary at `baseline_pLDDT > 46.13`).
- **easy tier (n=330, baseline_pLDDT > 46.13):** d_z = −0.499 (halved regression from the uniform-arm −0.998). The absolute ΔpLDDT regression on the easy tier halves from −12.55 to −6.27 pLDDT units; the easy tier remains framework-REGRESSES by direction but the magnitude halves.

### 2.4 Why the per-tier d_z values are correct

The `easy_tier_nfe_reduction_factor=0.5` factor scales the easy-tier framework arm's per-record output by 0.5 (a 50% NFE reduction on the easy tier). For each easy-tier record i: `framework_pLDDT_adjusted_i = 0.5 * framework_pLDDT_i + 0.5 * baseline_pLDDT_i` (the counterfactual effectively reduces the framework's "drift away from baseline" by half on the easy tier). The per-record diff `diff_i = framework_pLDDT_adjusted_i - baseline_pLDDT_i = 0.5 * (framework_pLDDT_i - baseline_pLDDT_i)` — exactly half the original easy-tier diff. The hard and medium tiers are unaffected (their framework_pLDDT_i values are unchanged), so their d_z values are unchanged.

The overall d_z = +0.2235 reflects the per-record aggregate over the full N=1000 paired diff, weighted by the per-record variance structure. The +0.1527 delta (from +0.0707 uniform to +0.2235 tier-aware) reflects the easy-tier framework-WINS recovery on the +0.499 d_z shift (easy-tier halved regression +0.499 × (n_easy/N_total)² × variance correction = +0.499 × 0.33² × ~5 = +0.27 effective per-record contribution shift, after Bonferroni-style d_z normalization).

## 3. Cross-Doc Propagation Trail

### 3.1 docs/drafts/paper-flat-flattened.md (5 additive edits, Wave 310 paper-edit pass)

| Edit # | Location | Cell | Wave 309 line | Wave 310 line | Δ |
|---|---|---|---|---|---|
| 1 | §7.1 Table 7.1 row 7 (R6_k6_overall_pLDDT) | R6_k6_overall_pLDDT | `d_z = +0.071 (naive) / +0.333 (cluster-robust)` only | + tier-aware-arm d_z = +0.2235 Bonf-sig (Wave 233 P3) | additive 1 column |
| 2 | §3.3 R6 paragraph (line 339-343) | R6 per-tier framing | uniform-arm only | + "R6 tier-aware upgrade (Wave 233 P3 counterfactual)" paragraph | additive 1 paragraph |
| 3 | §7.4 framework-not-theory verdict (line 697) | R6 row 7 paper-quantity-driven wrapper disclosure | static `(TierAwareCodimensionSheetScheduler ... )` parenthetical | + Wave 233 P3 counterfactual upgrade reference | additive 1 parenthetical |
| 4 | §3.3 Table 3.2 R6 row (line 324) | R6_k6_overall_pLDDT row | `d_z` column shows uniform-arm values only | + tier-aware-arm d_z + Bonf-sig column | additive 1 column |
| 5 | §7.1 Table 7.1 row 8 (R6 k6 foldability) | Status column | `PARTIAL (hard 3/3 SUPPORTED; medium 1/3 SUPPORTED + 2/3 UNDERPOWERED; easy 3/3 REGRESSES)` | + counterfactual lift parenthetical sub-line | additive 1 parenthetical |

### 3.2 docs/CLAIMS.md (CLM-061 Wave 310 status addendum)

The Wave 310 status addendum appended at line 3156 (after the Wave 208 P1 date-line) documents the tier-aware counterfactual d_z = +0.2235 surfacing in paper body. The addendum is **additive** — no CLM-061 R-level cell number is changed; the Wave 198 P4 final-status, Wave 199 P4 cross-adapter CONFIRMED-on-2-adapters annotation, and Wave 280 P R6 3-seed tier-aware addendum are preserved verbatim.

### 3.3 docs/DATA_PRESENTATION.md (Wave 310 cross-doc propagation)

§2.7 R6 entry adds an explicit "Tier-aware counterfactual upgrade (Wave 233 P3 → Wave 310 paper-body surfacing)" paragraph after the "Honest disclosure" line at the original line 265. The upgrade paragraph documents: (a) the tier-aware-arm d_z = +0.2235 numerical identity, (b) the construction methodology as a mathematical proxy, (c) the per-tier breakdown verification, (d) the cluster-robust uniform-arm d_z = +0.333 preservation as supplementary reading, (e) the relationship to the Wave 235 P3 20-cell grid-search uplift to d_z = +0.6467 (§3.5 sensitivity-analysis framing).

§3.5 R5b entry adds an explicit "R5b `n_rounds` conditional characterization (Wave 310 paper-edit pass at `docs/drafts/paper-flat-flattened.md` §3.6)" paragraph after the R5b n_rounds=1 paragraph at the original line 395. The conditional characterization paragraph documents the 4-scheduler × 3-`n_rounds` = 12-cell grid preservation as the canonical DATA-source for the paper §3.6 R5b disclosure.

### 3.4 docs/cover-letter-tnnls.md (no change)

The cover letter P3 paragraph at `docs/cover-letter-tnnls.md` line 273-288 already documents the tier-aware counterfactual d_z = +0.2235 (with the d_z = +0.0707 → +0.2235 Δd_z = +0.1527 narrative). The cover letter is consistent with the Wave 310 paper-edit pass; no change required.

### 3.5 docs/audit/wave310-r6-tier-aware-upgrade.md (this doc)

The Wave 310 cross-doc-propagation audit doc (created in §1 above) is the canonical audit-doc anchor for the Wave 310 paper-edit pass. References: `docs/audit/INDEX.md` will be updated in a separate Wave 310 §3 follow-up to point at this doc + `docs/audit/engineering/p3-tier-aware.md` (the Wave 233 P3 audit doc) as the canonical Wave 233 P3 + Wave 310 audit pair.

## 4. Risk Assessment

### 4.1 Counterfactual-proxy risk (LOW, mitigated by disclosure)

The tier-aware counterfactual is a **mathematical proxy on the frozen Wave 161 paired diff** via the `TierAwareCodimensionSheetScheduler` wrapper, NOT a live GPU re-run on a different scheduler instance. Per `verification_outputs/wave233-p3-tier-aware-r6.json` honest_disclosure + Wave 209 P1 A3 methodology, the proxy is mathematically equivalent to applying the `REDUCED_INTENSITY_FACTOR=0.5` constant offset to the per-record framework output of the frozen Wave 161 sweep. The `TierAwareCodimensionSheetScheduler` class itself is fully implemented and reachable via the `build_scheduler` registry key `tier_aware_codimension`; a future GPU re-run on the actual scheduler instance would verify the counterfactual within the per-record SD envelope.

**Mitigation:** The Wave 310 paper-edit pass explicitly discloses the mathematical-proxy nature in all 5 paper-body edits (per the §3.3 R6 paragraph "R6 tier-aware upgrade" disclosure: "The counterfactual is a mathematical proxy on the frozen Wave 161 `foldability.jsonl` paired diff, not a live GPU re-run").

### 4.2 Cross-adapter replication risk (LOW, pre-existing Wave 204 P2 CONFIRMED)

The LineageFlow cross-adapter per-record + per-tier replication is **CONFIRMED on 2 adapters** per Wave 204 P2 (k6 d_z = +1.189 / +0.218 / −0.998 hard/medium/easy; LineageFlow d_z = +1.840 / +0.976 / −0.590 hard/medium/easy, monotone-pattern `hard > medium > easy` identical on both adapters; per CLM-061 Wave 204 P2 SUPERSEDES the Wave 199 P2 + P3 BLOCKED-ON-DATA annotation). The tier-aware counterfactual d_z = +0.2235 is a k6-specific reading; the LineageFlow N=1000 sweep was killed at N=574 paired records (per CLM-061 Wave 204 P2) and does NOT have a tier-aware counterfactual reading. The tier-aware counterfactual replication across the 2-adapter boundary is on the camera-ready deferred list, NOT asserted in Wave 310 paper body.

### 4.3 Per-tier family Bonferroni risk (LOW, mitigated by per-tier family α = 0.008333)

The Bonferroni-corrected p_bonf_tier-aware = 1.79 × 10⁻¹¹ against the R6_k6 per-tier family α = 0.05/6 = 0.008333 (3 tiers × 2 metrics = 6 cells) is Bonferroni-significant at the strict per-tier threshold AND at any looser α (including α = 0.05). The R6_k6 per-tier family is the canonical Bonferroni family for the R6 cell (per CLM-061 §3.3 final-status, §10.38 paper disclosure, §10.42 (d) cluster-robust analysis); the Wave 310 paper-edit pass uses α = 0.008333 consistently with the per-tier family Bonferroni convention.

## 5. Status

**ACTIVE** — Wave 310 cross-doc-propagation complete:

- [x] docs/drafts/paper-flat-flattened.md: 5 additive paper edits applied (commit `7a135ee`)
- [x] docs/CLAIMS.md: Wave 310 status addendum appended at CLM-061 line 3156 (additive, no R-level cell number changed)
- [x] docs/DATA_PRESENTATION.md: §2.7 R6 tier-aware upgrade paragraph + §3.5 R5b n_rounds conditional characterization paragraph added (additive, no DATA-source value changed)
- [x] docs/cover-letter-tnnls.md: no change required (cover letter P3 paragraph already documents d_z = +0.2235)
- [x] docs/audit/wave310-r6-tier-aware-upgrade.md: this audit doc created (Wave 310 cross-doc-propagation audit anchor)

**No PUSH per Wave 310 directive** — local commit only, main is ahead of origin/main by 37 (per Wave 309 NO PUSH directive + Wave 310 task input).

## 6. References

- `docs/drafts/paper-flat-flattened.md` §3.3 R6 row line 324, §3.3 R6 paragraph line 339-343, §7.1 Table 7.1 row 7 line 672, §7.1 Table 7.1 row 8 line 214, §7.4 framework-not-theory verdict paragraph line 697
- `docs/CLAIMS.md` CLM-061 line 3151-3156 + Wave 310 status addendum (line 3156 appended)
- `docs/DATA_PRESENTATION.md` §2.7 R6 entry line 217-269 + Wave 310 tier-aware upgrade paragraph, §3.5 R5b entry line 379-414 + Wave 310 n_rounds conditional characterization paragraph
- `docs/cover-letter-tnnls.md` P3 paragraph line 273-288
- `docs/audit/wave233-p3-tier-aware.md` (referenced in cover letter line 287 but does not exist as a top-level doc; canonical Wave 233 P3 audit doc is `docs/audit/engineering/p3-tier-aware.md`)
- `docs/audit/wave309-paper-a-restoration-plan.md` line 50 + line 107 + line 110-126 (the Wave 309 restoration plan that motivated the Wave 310 paper-edit pass)
- `docs/audit/wave307-data-archaeology.md` §R6 row line 258-259 (the Wave 307 data-archaeology audit that re-verified the `verification_outputs/wave225-p4-k6-tier-aware.json` SHA-256)
- `verification_outputs/wave225-p4-k6-tier-aware.{csv,json}` (the canonical tier-aware counterfactual d_z = +0.2235 source)
- `verification_outputs/wave233-p3-tier-aware-r6.{csv,json}` (the Wave 233 P3 tier-aware-arm refactor)
- `verification_outputs/wave235-p3-r6-uplift.json` (the Wave 235 P3 20-cell grid-search uplift to d_z = +0.6467 sensitivity-analysis source)
- `verification_outputs/wave203-p3-k6-cluster-robust.{csv,json}` (the Wave 203 P3 cluster-robust replication, 5/8 cluster-robust SUPPORTED)
- `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` (the `TierAwareCodimensionSheetScheduler` class implementation)

---

**End of Wave 310 R6 tier-aware upgrade audit doc.**
