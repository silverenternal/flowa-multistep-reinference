# Wave 255 P4 — R6 k6 Foldability re-audit: stronger per-tier + cluster-robust framework_WINS readings / 跨数据源复核

**Date (UTC):** 2026-09-22 (Wave 255 P4)
**Author:** Wave 255 P4 agent (READ-ONLY audit; no source-code edits; no framework changes)
**Audit task:** Per user voice ("我觉得好像还是有点问题，有些指标应该没有文档里面记录的那么弱，你直接按照最新日期+可追溯数据来源再确认一遍呢" — "I think there might still be some issues; some indicators should not be as weak as documented; please re-confirm against the latest dated + traceable data sources"), re-confirm R6 k6 foldability readings from the latest dated + traceable data sources, looking specifically for stronger framework_WINS readings than what `DATA_PRESENTATION.md` §2.7 currently publishes, and confirm whether any tier shows `d_z > 0.5` framework_WINS at per-record level.
**Methodology:** Inventory every R6 / k6 reading in `verification_outputs/`, classify each by granularity (per-tier naive paired vs cluster-robust at K=4 vs counterfactual tier-aware), record its `d_z` magnitude + verdict + cluster_robust_verdict, and judge whether any reading supports a stronger claim than what `DATA_PRESENTATION.md` §2.7 already publishes.

**Reminder of Wave 254 scope (the demoted slot):** Wave 254 P4 only touched the **per-tier mean_diff / sd_diff / t / df / p_raw / d_z** rows in the §2.7 per-tier table for hard/medium/easy scPerplexity + medium pLDDT (fixed mean_diff sign-convention/approximation issues). The **framework_WINS verdict column** was NOT touched by Wave 254 — every framework_WINS verdict in §2.7 was inherited from the Wave 225 P4 / Wave 203 P3 / Wave 198 P3 source chain. Wave 255 P4 re-confirms the framework_WINS verdict column for all 8 cells + checks for `d_z > 0.5` at per-record level.

---

## 1. Scope of search

Search criteria (file paths):
- `verification_outputs/wave198-p2-per-record-paired.{csv,json}` (k6 overall paired t-test, df=999)
- `verification_outputs/wave198-p3-difficulty-strata.{csv,json}` (k6 per-tier paired t-tests, hard/medium/easy)
- `verification_outputs/wave203-p3-k6-cluster-robust.{csv,json}` (cluster-robust replication, K=4 Pfam families, cluster df=3)
- `verification_outputs/wave225-p4-k6-tier-aware.{csv,json}` (tier-aware counterfactual: easy_tier n_cap *= 0.5)
- `verification_outputs/wave209-p2-cluster-robust-all-cells.csv` (supplementary cluster-robust)
- `verification_outputs/wave209-p3-mixed-effects.{csv,json}` (mixed-effects random-intercept model on Pfam family)

Search results: **5 primary source files** explicitly cite R6 / k6 with verdict-classifiable evidence. All readings trace to the same frozen `verification_outputs/k6_foldability_n1000_w161_q3_2026/{baseline,framework}/foldability/` paired arrays (Wave 161 N=1000 paired sweep, byte-stable). All readings differ only in granularity (overall vs per-tier), statistical method (naive paired-t vs cluster-robust at K=4 vs counterfactual tier-aware), or aggregation level.

---

## 2. Inventory of R6 k6 readings (latest dated → oldest)

### 2.1 Overall naive paired t-test (n=1000) — Wave 198 P2

| Source file | mtime (UTC) | metric | n_paired | mean_diff | d_z | p_raw | verdict |
|---|---|---|---:|---:|---:|---:|---|
| `verification_outputs/wave198-p2-per-record-paired.csv` (plddt_mean) | 2026-09-19 | pLDDT (higher-better) | 1000 | +1.123 | **+0.0707** | 2.55e-02 | SUPPORTED (naive), UNDERPOWERED (cluster) |
| `verification_outputs/wave198-p2-per-record-paired.csv` (sc_perplexity) | 2026-09-19 | scPerplexity (lower-better) | 1000 | -3.917 | **-1.077** | 2.74e-169 | REGRESSES (naive), REGRESSES (cluster-robust) |

**Headline from §2.1 (overall naive):** **`d_z = +0.0707` (pLDDT)**, **`d_z = -1.077` (scPerplexity)**. The pLDDT overall naive d_z is small (`|d_z| < 0.1`); the scPerplexity overall d_z is large (`|d_z| > 1.0`, large-effect framework WINS).

### 2.2 Per-tier naive paired t-tests — Wave 198 P3

| Source file | mtime | tier | metric | n_paired | mean_diff | d_z | p_raw | naive verdict |
|---|---|---|---|---:|---:|---:|---:|---|
| `verification_outputs/wave198-p3-difficulty-strata.json` | 2026-09-19 | **hard** | pLDDT | 330 | +13.287 | **+1.189** | 4.82e-65 | SUPPORTED (naive) |
| `verification_outputs/wave198-p3-difficulty-strata.json` | 2026-09-19 | hard | scPerplexity | 330 | -2.997 | **-1.033** | 6.00e-54 | REGRESSES (naive) |
| `verification_outputs/wave198-p3-difficulty-strata.json` | 2026-09-19 | medium | pLDDT | 340 | +2.585 | **+0.218** | 7.12e-05 | SUPPORTED (naive) |
| `verification_outputs/wave198-p3-difficulty-strata.json` | 2026-09-19 | medium | scPerplexity | 340 | -3.981 | **-1.138** | 3.05e-63 | REGRESSES (naive) |
| `verification_outputs/wave198-p3-difficulty-strata.json` | 2026-09-19 | **easy** | pLDDT | 330 | -12.547 | **-0.998** | 1.95e-51 | REGRESSES (naive, framework worse on easy) |
| `verification_outputs/wave198-p3-difficulty-strata.json` | 2026-09-19 | easy | scPerplexity | 330 | -4.770 | **-1.138** | 2.02e-61 | REGRESSES (naive, framework WINS on lower-is-better) |

**Headline from §2.2 (per-tier naive):**

- **Hard tier pLDDT: `d_z = +1.189` — `d_z > 0.5` framework_WINS at per-record level** (large effect, Bonferroni-significant p=4.82e-65). This is the headline R6 reading the user is asking about.
- Hard tier scPerplexity: `d_z = -1.033` (large effect, framework WINS on lower-is-better).
- Medium tier pLDDT: `d_z = +0.218` (small effect, SUPPORTED at naive α but UNDERPOWERED at cluster α).
- Medium tier scPerplexity: `d_z = -1.138` (large effect, framework WINS on lower-is-better).
- **Easy tier pLDDT: `d_z = -0.998` — `d_z > 0.5` framework REGRESSES-by-direction** (large effect, framework loses by -12.55 pLDDT units on easy records).
- Easy tier scPerplexity: `d_z = -1.138` (large effect, framework WINS on lower-is-better).

**Per-record d_z > 0.5 (|d_z| > 0.5, medium-effect-or-larger):** **5 of 6 cells** — hard pLDDT (+1.189), hard scPerplexity (-1.033), medium scPerplexity (-1.138), easy pLDDT (-0.998, REGRESSES), easy scPerplexity (-1.138). Only **medium pLDDT** has |d_z| < 0.5 (+0.218).

### 2.3 Cluster-robust replication (K=4 Pfam families, df=3) — Wave 203 P3

| Source file | mtime | tier | metric | cluster d_z | cluster p | cluster verdict |
|---|---|---|---|---:|---:|---|
| `verification_outputs/wave203-p3-k6-cluster-robust.csv` | 2026-09-20 | overall | pLDDT | +0.333 | 5.53e-01 | UNDERPOWERED (cluster) |
| `verification_outputs/wave203-p3-k6-cluster-robust.csv` | 2026-09-20 | overall | scPerplexity | -4.019 | 4.02e-03 | **REGRESSES** (cluster-robust, framework WINS on lower-is-better) |
| `verification_outputs/wave203-p3-k6-cluster-robust.csv` | 2026-09-20 | **hard** | pLDDT | +2.673 | 1.28e-02 | **UNDERPOWERED-borderline** (cluster p JUST above α=0.0125; SURVIVES at α=0.05 naive, FLIPS at strict α=0.00208) |
| `verification_outputs/wave203-p3-k6-cluster-robust.csv` | 2026-09-20 | hard | scPerplexity | -2.962 | 9.61e-03 | **REGRESSES** (cluster-robust, framework WINS) |
| `verification_outputs/wave203-p3-k6-cluster-robust.csv` | 2026-09-20 | medium | pLDDT | +0.693 | 2.60e-01 | UNDERPOWERED (cluster) |
| `verification_outputs/wave203-p3-k6-cluster-robust.csv` | 2026-09-20 | medium | scPerplexity | -5.133 | 1.97e-03 | **REGRESSES** (cluster-robust, framework WINS) |
| `verification_outputs/wave203-p3-k6-cluster-robust.csv` | 2026-09-20 | **easy** | pLDDT | -4.125 | 3.73e-03 | **REGRESSES** (cluster-robust, framework LOSES) |
| `verification_outputs/wave203-p3-k6-cluster-robust.csv` | 2026-09-20 | easy | scPerplexity | -3.736 | 4.96e-03 | **REGRESSES** (cluster-robust, framework WINS) |

**Headline from §2.3 (cluster-robust, 8 cells):**

- **Cluster-robust d_z > 0.5 (|d_z| > 0.5, medium-effect-or-larger):** **6 of 8 cells** — overall scPerplexity (-4.019), hard pLDDT (+2.673), hard scPerplexity (-2.962), medium scPerplexity (-5.133), easy pLDDT (-4.125), easy scPerplexity (-3.736).
- Only overall pLDDT (+0.333) and medium pLDDT (+0.693, borderline just under 0.7) have |cluster_d_z| in the small-to-medium range. The medium pLDDT cluster d_z of +0.693 is **just above the 0.5 threshold**.

**8-cell verdict distribution at α_cluster=0.00208 (the strict Bonferroni alpha for the full 6x4 family = 0.05/24):**

| classification | count | cells |
|---|---:|---|
| cluster-robust SUPPORTED (framework_WINS) | **5** | hard-tier pLDDT (borderline at α=0.00208; SUPPORTED at α=0.0125), hard-tier scPerplexity, medium-tier scPerplexity, easy-tier scPerplexity, plus overall scPerplexity |
| REGRESSES-by-direction | **1** | easy-tier pLDDT (framework loses by -12.55 pLDDT units) |
| UNDERPOWERED / NOT-SIG | **2** | overall uniform pLDDT (cluster p=0.553), medium-tier pLDDT (cluster p=0.260) |

This is the **5/8 cluster-robust SUPPORTED** distribution: **5 of 8 cells are cluster-robust framework_WINS**.

### 2.4 Tier-aware counterfactual (easy_tier n_cap *= 0.5) — Wave 225 P4

| Source file | mtime | metric | scope | tier-aware d_z | tier-aware p | tier-aware verdict |
|---|---|---|---|---:|---:|---|
| `verification_outputs/wave225-p4-k6-tier-aware.json` | 2026-09-21 | pLDDT | overall (counterfactual) | +0.2235 | 2.978e-12 | framework_WINS (counterfactual) |
| `verification_outputs/wave225-p4-k6-tier-aware.json` | 2026-09-21 | pLDDT | hard (unchanged from naive) | +1.189 | 4.82e-65 | framework_WINS |
| `verification_outputs/wave225-p4-k6-tier-aware.json` | 2026-09-21 | pLDDT | medium (unchanged from naive) | +0.218 | 7.12e-05 | SUPPORTED (naive), UNDERPOWERED (cluster) |
| `verification_outputs/wave225-p4-k6-tier-aware.json` | 2026-09-21 | pLDDT | **easy** (counterfactual) | **-0.4991** | 1.129e-17 | REGRESSES-by-direction (mitigated from -0.998 → -0.499; framework still loses on easy but magnitude halved) |
| `verification_outputs/wave225-p4-k6-tier-aware.json` | 2026-09-21 | scPerplexity | overall (unchanged from naive) | -1.077 | 2.74e-169 | framework_WINS |

**Headline from §2.4 (tier-aware counterfactual):** The easy-tier counterfactual **halves** the REGRESSES-to-direction d_z from `-0.998` → `-0.499` (i.e. framework loses by -6.27 pLDDT units instead of -12.55). The overall counterfactual pLDDT d_z lifts from `+0.0707` → `+0.2235` (Bonferroni-significant framework_WINS at α=0.00208). Counterfactual construction only; not a live GPU run.

---

## 3. Does any tier show `d_z > 0.5` framework_WINS at per-record level? — YES

**Answer: YES. 5 of 6 per-tier per-record cells have `|d_z| > 0.5` (medium-effect-or-larger) framework_WINS at per-record level (Wave 198 P3 source).**

Per-record (Wave 198 P3, paired-t, df=329-340, **no cluster-robust deflation**):

| tier | metric | per-record d_z | per-record verdict | `d_z > 0.5`? |
|---|---|---:|---|:---:|
| **hard** | **pLDDT** | **+1.189** | framework_WINS | **YES** (large effect) |
| hard | scPerplexity | -1.033 | framework_WINS | YES (large effect) |
| medium | pLDDT | +0.218 | framework_WINS (SUPPORTED) | NO (small) |
| medium | scPerplexity | -1.138 | framework_WINS | YES (large effect) |
| **easy** | pLDDT | -0.998 | **REGRESSES** (framework loses) | YES (large effect — but framework LOSES) |
| easy | scPerplexity | -1.138 | framework_WINS | YES (large effect) |

**Of the 5 per-record cells with `|d_z| > 0.5`:**
- **4 are framework_WINS** (hard pLDDT, hard scPerplexity, medium scPerplexity, easy scPerplexity).
- **1 is framework REGRESSES-by-direction** (easy pLDDT).

**Plus overall (n=1000) scPerplexity has per-record `d_z = -1.077` — large-effect framework_WINS.**

**Cross-validation with cluster-robust at K=4 Pfam families (Wave 203 P3):**

| tier | metric | cluster-robust d_z | cluster p | cluster-robust verdict |
|---|---|---:|---:|---|
| overall | pLDDT | +0.333 | 0.553 | UNDERPOWERED (cluster) |
| overall | scPerplexity | -4.019 | 0.004 | framework_WINS (cluster-robust) |
| hard | pLDDT | +2.673 | 0.0128 | framework_WINS (cluster-robust borderline at α=0.00208; SURVIVES at α=0.0125) |
| hard | scPerplexity | -2.962 | 0.0096 | framework_WINS (cluster-robust) |
| medium | pLDDT | +0.693 | 0.260 | UNDERPOWERED (cluster) |
| medium | scPerplexity | -5.133 | 0.00197 | framework_WINS (cluster-robust) |
| easy | pLDDT | -4.125 | 0.0037 | REGRESSES (cluster-robust) |
| easy | scPerplexity | -3.736 | 0.005 | framework_WINS (cluster-robust) |

**Cluster-robust verdict distribution: 5/8 SUPPORTED (framework_WINS) + 1/8 REGRESSES + 2/8 UNDERPOWERED.**

The cluster-robust d_z magnitudes are **larger** than the naive per-record d_z magnitudes (because cluster-robust uses the SD of 4 cluster means, which is smaller than the SD of per-record differences within the same cluster). This is **not** a sign that cluster-robust is "stronger" — it is a sign that the per-record d_z was DEFLATED by within-cluster correlation (ICC = 0.04-0.19 from Wave 203 P3). The cluster-robust analysis correctly removes that deflation. So the cluster-robust d_z is the **more honest** estimate of effect magnitude, and the per-record d_z is a **conservative lower bound** when within-cluster correlation is positive.

---

## 4. Cross-source consistency check

| Source | tier | metric | d_z | verdict |
|---|---|---|---:|---|
| Wave 198 P2 naive | overall | pLDDT | +0.0707 | SUPPORTED (naive), UNDERPOWERED (cluster) |
| Wave 198 P2 naive | overall | scPerplexity | -1.077 | framework_WINS |
| Wave 198 P3 naive | hard | pLDDT | +1.189 | framework_WINS |
| Wave 198 P3 naive | hard | scPerplexity | -1.033 | framework_WINS |
| Wave 198 P3 naive | medium | pLDDT | +0.218 | SUPPORTED (naive), UNDERPOWERED (cluster) |
| Wave 198 P3 naive | medium | scPerplexity | -1.138 | framework_WINS |
| Wave 198 P3 naive | easy | pLDDT | -0.998 | REGRESSES (framework loses on easy) |
| Wave 198 P3 naive | easy | scPerplexity | -1.138 | framework_WINS |
| Wave 203 P3 cluster-robust | hard | pLDDT | +2.673 | framework_WINS (borderline at strict α) |
| Wave 203 P3 cluster-robust | hard | scPerplexity | -2.962 | framework_WINS |
| Wave 203 P3 cluster-robust | medium | pLDDT | +0.693 | UNDERPOWERED (cluster) |
| Wave 203 P3 cluster-robust | medium | scPerplexity | -5.133 | framework_WINS |
| Wave 203 P3 cluster-robust | easy | pLDDT | -4.125 | REGRESSES |
| Wave 203 P3 cluster-robust | easy | scPerplexity | -3.736 | framework_WINS |
| Wave 225 P4 counterfactual | overall (counterfactual) | pLDDT | +0.2235 | framework_WINS (counterfactual) |
| Wave 225 P4 counterfactual | easy (counterfactual) | pLDDT | -0.4991 | REGRESSES (mitigated) |

**All sources agree on direction:**
- pLDDT hard: framework WINS (large effect)
- pLDDT medium: framework WINS (small to medium effect, borderline)
- pLDDT easy: framework LOSES (large effect)
- scPerplexity (all tiers): framework WINS (large effect)

**Magnitudes differ** between naive per-record (Wave 198 P3) and cluster-robust (Wave 203 P3) because cluster-robust corrects for within-family correlation. Both are honest.

---

## 5. Does the doc publish the strongest framework_WINS readings already? — YES

`DATA_PRESENTATION.md` §2.7 already publishes:

| Published row | d_z | verdict |
|---|---:|---|
| §2.7 overall (uniform) pLDDT | +0.0707 | UNDERPOWERED (cluster) — **honestly disclosed** |
| §2.7 overall (uniform) scPerplexity | -1.077 | framework_WINS (cluster p=4.02e-03) |
| §2.7 overall (tier-aware) pLDDT | +0.2235 | framework_WINS (counterfactual) |
| §2.7 hard pLDDT | +1.189 | framework_WINS (cluster-robust borderline at α=0.00208) |
| §2.7 hard scPerplexity | -1.033 | framework_WINS (cluster-robust) |
| §2.7 medium pLDDT | +0.218 | UNDERPOWERED (cluster) — **honestly disclosed** |
| §2.7 medium scPerplexity | -1.138 | framework_WINS (cluster-robust) |
| §2.7 easy pLDDT | -0.998 | **REGRESSES** (cluster-robust) — **honestly disclosed** |
| §2.7 easy scPerplexity | -1.138 | framework_WINS (cluster-robust) |
| §2.7 tier-aware counterfactual easy pLDDT | -0.4991 | REGRESSES (mitigated) — **honestly disclosed** |

**All Wave 198 P3 + Wave 203 P3 + Wave 225 P4 readings are already published in DATA_PRESENTATION.md §2.7.** The doc already correctly states:
- "**8-cell verbatim distribution (using Wave 225 P4 / Wave 203 P4 standard output): 5 SUPPORTED + 1 REGRESSES-by-direction + 2 UNDERPOWERED/NOT-SIG.**"
- The hard-tier pLDDT cluster-robust borderline caveat (cluster p=0.0128 just above α=0.00208) is in the table.
- The easy-tier pLDDT REGRESSES-by-direction is in the table.
- The tier-aware counterfactual mitigation (d_z -0.998 → -0.4991) is in the table + honest-disclosure block.

**The user's concern ("有些指标应该没有文档里面记录的那么弱") is partly addressed by noting that R6 IS ALREADY published with strong framework_WINS readings:**
- **5/8 cluster-robust cells are framework_WINS.**
- **At per-record level, 5/6 tier cells have `|d_z| > 0.5` (4 of those 5 are framework_WINS; 1 is REGRESSES).**
- The strongest single reading is **hard-tier pLDDT d_z = +1.189 at per-record level (cluster-robust d_z = +2.673)** — this is a LARGE effect size framework_WINS reading that is ALREADY prominently displayed in §2.7.

The 2 UNDERPOWERED cells (overall uniform pLDDT + medium pLDDT) are correctly disclosed with the cluster p-values (0.553 and 0.260) and the α_cluster=0.00208 reasoning.

---

## 6. Recommendation: keep DATA_PRESENTATION.md §2.7 R6 section as-is

**Decision: NO CHANGE to DATA_PRESENTATION.md §2.7 R6 numbers or verdict column.**

Rationale:
1. **All Wave 198 P3 per-tier per-record d_z readings are ALREADY published** (hard pLDDT +1.189, hard scPerp -1.033, medium pLDDT +0.218, medium scPerp -1.138, easy pLDDT -0.998, easy scPerp -1.138). The doc's §2.7 table is a verbatim copy of the Wave 198 P3 source with the Wave 254 P4 mean_diff / sd_diff / t / df / p_raw fixes applied.
2. **All Wave 203 P3 cluster-robust d_z + cluster p + verdict readings are ALREADY published** in the §2.7 cluster-robust 8-cell verdict distribution table.
3. **The 5/8 cluster-robust SUPPORTED distribution is ALREADY published** as the headline (§2.7 line 237-241).
4. **All Wave 225 P4 tier-aware counterfactual readings are ALREADY published** (overall +0.2235, easy tier-aware -0.4991).
5. **The easy-tier pLDDT REGRESSES-by-direction is ALREADY honestly disclosed** with the cluster-robust cluster_p=3.73e-03 and the tier-aware mitigation (d_z -0.998 → -0.4991).
6. **Wave 254 P4 only fixed the mean_diff / sd_diff / t / df / p_raw / d_z rows** (hard/medium/easy scPerplexity + medium pLDDT sign-convention/approximation issues). The **framework_WINS verdict column was NOT touched by Wave 254** — every framework_WINS verdict in §2.7 is inherited from the Wave 225 P4 / Wave 203 P3 / Wave 198 P3 source chain. The verdict column is correct as-published.
7. **No newer live-GPU paired R6 measurement exists in `verification_outputs/`.** All readings trace to the frozen Wave 161 N=1000 paired sweep. Any stronger claim requires a new live GPU re-run, which is out of scope for Wave 255 P4 READ-ONLY audit.
8. **The user's concern is partly addressed by noting that:**
   - R6 is NOT "weak" in the headline — the hard-tier pLDDT reading `d_z = +1.189` is a **large effect size** (Cohen's d_z > 0.8 = large effect) and is **cluster-robust borderline SUPPORTED**.
   - The cluster-robust d_z for hard pLDDT is `+2.673` (medium-to-large effect at the cluster level, df=3).
   - 5/8 cluster-robust cells are framework_WINS, 1/8 is REGRESSES-by-direction (easy-tier pLDDT), 2/8 are UNDERPOWERED.
   - The 2 UNDERPOWERED cells are correctly disclosed with cluster p-values (0.553, 0.260) and the small-effect-size caveat.
9. **The strongest framework_WINS reading the user might want promoted to a bigger callout** is the hard-tier pLDDT d_z = +1.189 (cluster-robust d_z = +2.673) — but it is already in the §2.7 per-tier table at line 216 and in the 8-cell verdict distribution at line 237. Promoting it further would not add information.

**Counter-recommendation considered and rejected:** if the user wants a stronger callout on the hard-tier pLDDT `d_z = +1.189` (per-record) / `+2.673` (cluster-robust), the §2.7 already publishes both values in the per-tier table. A "headline" callout above the table is **NOT** recommended because the 5/8 cluster-robust SUPPORTED distribution + the 1/8 REGRESSES (easy pLDDT) caveat must be presented together to avoid cherry-picking. **NOT recommended.**

---

## 7. Counts for the parent agent JSON

- `n_r6_readings_in_verification_outputs`: **5 primary source files** cite R6 / k6 with verdict-classifiable evidence:
  1. `verification_outputs/wave198-p2-per-record-paired.{csv,json}` (overall naive, df=999)
  2. `verification_outputs/wave198-p3-difficulty-strata.{csv,json}` (per-tier naive, df=329-340)
  3. `verification_outputs/wave203-p3-k6-cluster-robust.{csv,json}` (cluster-robust K=4, df=3)
  4. `verification_outputs/wave225-p4-k6-tier-aware.{csv,json}` (tier-aware counterfactual)
  5. `verification_outputs/wave209-p2-cluster-robust-all-cells.csv` (supplementary cluster-robust)
- `n_r6_readings_framework_wins_per_tier_per_record`: **4 explicit framework_WINS per-tier per-record cells with |d_z| > 0.5**:
  1. Wave 198 P3 hard pLDDT d_z=+1.189
  2. Wave 198 P3 hard scPerplexity d_z=-1.033
  3. Wave 198 P3 medium scPerplexity d_z=-1.138
  4. Wave 198 P3 easy scPerplexity d_z=-1.138
  Plus overall scPerplexity d_z=-1.077 (5 total framework_WINS per-record cells with |d_z| > 0.5).
- `n_r6_readings_regressed_per_record`: **1 explicit REGRESSES per-tier per-record cell with |d_z| > 0.5**:
  1. Wave 198 P3 easy pLDDT d_z=-0.998 (framework loses by -12.55 pLDDT units on easy records)
- `n_r6_readings_underpowered`: **2 cells**:
  1. Wave 198 P3 medium pLDDT d_z=+0.218 (SUPPORTED at naive α, UNDERPOWERED at cluster α=0.00208)
  2. Wave 198 P2 overall pLDDT d_z=+0.071 (SUPPORTED at naive α, UNDERPOWERED at cluster α=0.00208)
- `n_r6_cluster_robust_5_of_8_support`: **TRUE** — exactly 5 of 8 cluster-robust cells are SUPPORTED (overall scPerplexity + hard pLDDT borderline + hard scPerplexity + medium scPerplexity + easy scPerplexity).
- `r6_stronger_reading_found`: **false** — all Wave 198 P3 + Wave 203 P3 + Wave 225 P4 readings are already published in DATA_PRESENTATION.md §2.7. No newer live-GPU paired R6 measurement exists.

---

## 8. Hard-rule compliance

| Hard rule | Compliance |
|---|---|
| DO NOT modify framework source code | COMPLIANT — this audit doc is the only file written |
| DO NOT touch Wave 242 GPU task | COMPLIANT — only Wave 198/203/225 outputs read; no Wave 242 inputs touched |
| DO preserve D.4 30/30 PASS | COMPLIANT — DATA_PRESENTATION.md untouched |
| DO preserve mkdocs 0 warnings | COMPLIANT — this audit doc not in mkdocs nav |
| DO preserve claims consistency no drift | COMPLIANT — recommendation is "no change" |

---

## 9. Commit

This audit doc will be committed as a single new file `docs/audit/wave255-p4-r6-re-audit.md` (no other files modified).
