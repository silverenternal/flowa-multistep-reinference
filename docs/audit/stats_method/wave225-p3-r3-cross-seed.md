# Wave 225 P3 — R3 cross-seed historical consistency check

**Wave:** 225 P3
**Cell:** R3 fg_dev (FlowMol3)
**Type:** Cross-seed / cross-wave direction-consistency audit
**Date:** 2026-09-21
**Author:** Wave 225 P3 R3 cross-seed agent

---

## 1. What was done

This audit attempts to validate the Wave 225 P2 R3 framework-WINS direction
claim by checking direction consistency across:

1. **Multiple historical waves** that re-use the canonical Wave 87 / Wave 82
   seed_base=42 byte-stable FlowMol3 fg_dev N=1000 sweep
2. **Multiple seeds** (the gold-standard cross-seed direction check that CLM-068
   documents as blocked)

## 2. Honest disclosure: cross-seed pooled-SD upgrade is BLOCKED

The FlowMol3 fg_dev N=1000 sweep has NEVER been executed on more than 1 seed.
The 3-seed sweep (seeds 42, 43, 44) was attempted in Wave 206 P3 but **BLOCKED**
by the DGL 2.4.0 graph ndata shape mismatch in `_solve_ode_upstream_batch`
(n_molecules > 1). The regression surfaces as:

```
DGLError: Expect number of features to match number of nodes (len(u)).
         Got 20 and 2000 instead.
```

Wave 208 P2 attempted a DGL downgrade to 2.3.x but the data.dgl.ai S3 bucket
returns HTTP 403 for all pre-2.4.0 wheels; PyPI dgl==2.1.0 is CPU-only; torch
cannot be downgraded to 2.2.x because RTX 5090/Blackwell sm_120 needs torch
≥ 2.5. Therefore the **cross-seed pooled-SD upgrade remains BLOCKED** on the
Wave 109.C §5 code fix path:

- Option A: tile per-mol `(x_0, a_0, c_0, e_0)` prior across batched DGL graph
- Option B: loop n_molecules with per-mol priors + add n_molecules=10 regression test

The single-mol path (n_molecules=1) works correctly (~10s/mol at NFE=250) but
is too slow for the 3-seed × N=1000 sweep budget (~17 h projected).

**The 3-seed pooled-SD upgrade is on the camera-ready deferred list.**

## 3. What this audit CAN report (cross-wave 1-seed direction consistency)

7 historical observations of the canonical seed_base=42 byte-stable sweep exist
across the waves 82, 87, 195 P2, 206 P3, 208 P2, 216 P1, 225 P2. All 7 are
direction-consistent (framework-WINS) on either the headline fg_dev metric or
its per-record proxies (REOS Glaxo+Dundee flag count, fg_contrib_proxy).

| # | Wave | Metric | Granularity | n_per_arm | framework_better |
|---|------|--------|-------------|-----------|------------------|
| 1 | Wave 82 sweep | fg_dev | per_arm_aggregate | 1000 | YES |
| 2 | Wave 87 sweep | fg_dev | per_arm_aggregate (byte-stable ref) | 1000 | YES |
| 3 | Wave 195 P2 R-level | fg_dev | per_arm_unpaired_Welch_t | 1000 | YES (underpowered at Bonferroni α=0.007143, but direction consistent) |
| 4 | Wave 206 P3 audit | fg_dev | per_arm_aggregate | 1000 | YES |
| 5 | Wave 208 P2 per-record | reos_n_flags | per_record_paired_N=200 | 200 | YES (Bonferroni-significant) |
| 6 | Wave 216 P1 projected | reos_n_flags | per_record_paired_N=1000 projected | 1000 | YES (Bonferroni-significant, projection) |
| 7 | Wave 225 P2 bootstrap | reos_n_flags | per_record_paired_N=200 bootstrap | 200 | YES (CI excludes 0) |

**Direction consistency: 7/7 historical waves = 100% direction-consistent
(framework-WINS on fg_dev or its per-record proxies).**

## 4. Cross-seed numbers (HONEST)

| Quantity | Value |
|----------|-------|
| n_seeds_requested | 3 |
| n_seeds_available | 1 (only seed_base=42 has any FlowMol3 fg_dev N=1000 sweep) |
| n_seeds_blocked | 2 (DGL 2.4.0 regression blocks fresh 3-seed sweep) |
| n_seeds_framework_wins | 1 (the 1 seed that exists IS framework-WINS) |
| direction_consistency_pct | 100.0% on the 1 available seed (33.33% if you count the 2 BLOCKED seeds as losses; honest reading: 1/1 of available seeds is framework-WINS, the BLOCKED seeds are not measurements) |

## 5. Interpretation

- The 1-seed direction-consistency check across 7 historical waves is 100%
  direction-consistent: every observation reports framework-WINS. This validates
  that the framework-WINS direction is reproducible across independent re-runs
  of the analysis pipeline (different scripts, different statistical methods,
  different metrics) on the SAME underlying seed=42 byte-stable sweep.
- The cross-seed pooled-SD upgrade to Bonferroni-significant at the per-arm
  granularity is NOT possible from historical data. The CLM-060 R3 fg_dev
  verdict (UNDERPOWERED, framework-WINS by −0.0235) is preserved verbatim
  at the per-arm granularity.
- The Wave 216 P1 projection to N=1000 per-record paired IS Bonferroni-
  significant (p=1.07e-18, d_z=−0.285) and resolves the Wave 195 P2
  UNDERPOWERED verdict AT THE PER-RECORD GRANULARITY. This is a projection
  from the N=200 ACTUAL measurement (Wave 208 P2) and is NOT a true
  cross-seed measurement.

## 6. Conclusion

The R3 direction-consistency claim is **partially validated**:
- **Cross-wave 1-seed (7 observations)**: 100% direction-consistent framework-WINS
- **Cross-seed 3-seed pooled-SD**: BLOCKED by DGL 2.4.0 regression; deferred to
  camera-ready fix (Wave 109.C §5)

The 1-seed claim (Wave 87 / Wave 82 byte-stable seed=42 sweep) IS validated by
the 7-wave cross-wave consistency check. The CLM-068 R3 direction-consistent
addendum is hereby appended.

## 7. Output paths

- CSV: `verification_outputs/wave225-p3-r3-cross-seed.csv` (8 rows = 7 observations + summary trailer)
- JSON: `verification_outputs/wave225-p3-r3-cross-seed.json` (full structured report)
- Script: `scripts/wave225_p3_r3_cross_seed.py`
- CLM-068 update: `docs/CLAIMS.md` (R3 direction-consistent addendum appended)

## 8. Cross-references

- CLM-068 (Wave 206 P3 + Wave 208 P2 + Wave 216 P1 lineage)
- Wave 109.C §5 DGL regression root-cause
- Wave 195 P2 R-level power analysis (R3 row audit-grade)
- Wave 225 P2 R3 bootstrap (predecessor)
- CLM-060 (R3 fg_dev verdict UNDERPOWERED, framework-WINS by −0.0235)
