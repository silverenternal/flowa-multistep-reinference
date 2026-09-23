# Wave 306 — DeepSeek 9-Inconsistency FIX PLAN

**Date:** 2026-09-23
**Mode:** READ-ONLY planning artifact (additive; **NO destructive edits executed**)
**Author:** Wave 306 fix-plan assembly agent
**Supplement to:** `docs/audit/wave305-day0-risk-package.md` (D0 risk package) + `docs/audit/wave304-deepseek-audit.md` (cell audits)
**Trigger:** DeepSeek reviewer's 9 inconsistency list (per `wave305-day0-risk-package.md` §0 + user request verbatim)
**CRITICAL RULES:**
- **DO NOT modify `docs/drafts/paper-flat-flattened.md`** (Wave 268 strict-clean).
- **DO NOT commit `/tmp/` → `verification_outputs/` moves** (per Wave 268 + Wave 303; require user authorization).
- This plan is **ADDITIVE planning only** — every `docs/drafts/paper-flat-flattened.md` edit below carries `requiresUserAuth=true` and is gated behind D0 sign-off.

---

## 0. TL;DR

Wave 304 cell audits revealed 9 inconsistencies between paper claims and actual data spanning **8 cells** (R1, R2, R3, R5b, R5c, K1, K4, K7) + 1 cross-cutting fix (Cell-ID + position realignment). **Every fix below is paper-text or data-migration only; no new experiments are required** (the experimental evidence is already canonical — the issue is presentation, not substance). Total estimated work: **~12 hours** if user D0 signs off all `requiresUserAuth=true` items; the data-migration sub-plan (`requiresUserAuth=true` per Wave 268) is the longest single item at ~3 hours.

**Honest disclosure — what changes vs the current paper:**
1. R2 §3.3 Table 3.2 row REGRESSION `d_z=+3.532` (one-sample t, framework_source=W196_byte_stable_fallback) → DEPLOYED `d_z=-0.0990` (paired-t, framework_source=W214-P2 byte-stable). **This is the most load-bearing fix** (DeepSeek #1 priority): §3.3 currently REPORTS R2 as REGRESSION while the canonical deployed data shows framework-WINS. The §7.1 Table 7.1 row already reports the deployed value correctly, but §3.3 Table 3.2 row 200 lines earlier contradicts it.
2. R1 §7.1 Table 7.1 row 1 d_z=+9.2/p_bonf=0.001 STRONG → 3-seed-pooled d_z=+0.6926/p_bonf=1.0 PARTIAL (seed-43/44 used 100% framework-fallback contamination per `/tmp/wf280-r1/seed{43,44}/fasta/manifest.json`). **The "d_z=+9.2" number is fabricated** (matches no actual computation).
3. K1 p_bonf=0.054 (no computational basis) → 0.5676 (K-level k=4, α=0.0125). The 0.054 figure has been propagated across `wave280-p-k1-sweep-result.md` §0/§3.3/§3.4/§4/§6 + paper §3.2/§7.1/§7.4 + CLAIMS.md line 3012.
4. K4+K5 p_bonf=0.734 → SUPP only (FAILS all 3 pre-registered alphas).
5. K7 d_z=+∞ saturated single-arm novelty vs framework vs W166 P3 (in-git) novelty inverted (framework 12.6× LESS Pfam-novel than baseline at corrected pctid<30% twilight-zone) → SUPP-only + W166 P3 cited as canonical evidence.
6. R5b conditional boundary on n_rounds: n_rounds=1 framework-WINS (ΔFID -1.60% to -2.53% on 3/4 schedulers, Wave 235 P1) vs n_rounds≥2 REGRESSES → §3.6 conditional wording per Wave 305 §4 paste-ready text block.
7. Cell-ID (R4 vs R5a) + abstract metric mis-assignment (K4 metric is hmmscan_total_hits, NOT scPerplexity) + "Kanzi k6 foldability" → "LineageFlow k6 foldability" → cross-document propagation across paper §3/§7 + `docs/headline-evidence/README.md` + `docs/CLAIMS.md`.
8. Position moves: K1+K4+K7 → SUPP per DeepSeek #4/#8 (Bonferroni-FAIL cells cannot sit in MAIN §7).
9. /tmp data → verification_outputs/: K1, K7, R1, R5c, R6, K4, R5b boundary (~50 files / ~30GB) per user "做了算法上的改进就该想办法去做实验上的验证" directive.

**Word budget impact (D1-D5 RESOLUTION pass):** approximately -1100 words net (drop K1 + K4+K5 + K7 from §7; conditional wording for R5b; R1 PARTIAL downgrade reduces STRONG/PARTIAL headline count). This **buys ~1100 words** for §2 Related Work + §8 Reproducibility + §11 Conclusion (per Wave 305 §6 5-7 day timeline). Net paper length moves from 36027 words (current) toward ~7700-word main-text target (per IEEEtran 14-page bound).

**5 STRONG/PARTIAL cells after fix:** R1 (PARTIAL/UNDERPOWERED, seed-42 single-seed + 3-seed fallback disclosure) + R5c (STRONG, smoke ckpt only with production-ckpt PARTIAL flag preserved) + R6 (PARTIAL, hard-tier pLDDT + scPerplexity cluster-robust) = **3 STRONG/PARTIAL cells** (vs current "5 STRONG + 5 PARTIAL + 1 UNDERPOWERED + 1 BLOCKED + 1 REGRESSES-boundary" framing). This is structurally important: it means the framework's primary empirical contribution is **3 not 5 cells**, with R2 + K1 + K4+K5 + K7 moving to supplementary or being honestly downgraded.

---

## 1. Issue 1: R2 paper §3.3 Table 3.2 row 319 REGRESSION vs deployed framework-WINS

**Cell:** R2 (Kanzi reconstruction_kabsch_rmsd_Å, protein flow-AE, paired N=1000)
**Priority:** CRITICAL (DeepSeek #1 priority — data integrity)
**Type:** DESTRUCTIVE on paper (replaces wrong numbers with correct numbers)
**requiresUserAuth:** **true** (paper-flat-flattened.md edit)
**Effort:** 5 min (single edit per row) + 5 min cross-doc propagation = **10 min total**

### 1.1 Background

Paper §3.3 Table 3.2 line 319 reports R2 as `one-sample t vs baseline mean | 1000 (vs baseline mean) | +0.6565 | 0.1859 | 111.69 | 999 | 0.0 | [+0.6450, +0.6680] | +3.532 (d_z) | R-level primary | 0.007143 | YES (regression by direction; lower_is_better; byte-stable)`. This is the **Wave 206 P2** data, which uses `framework_source=W196_byte_stable_fallback` (framework mean = 1.5585 Å, NOT the canonical W218 P3 framework mean = 0.8838 Å). The `+3.532 d_z` is a one-sample Cohen's d, NOT a paired t-test on per-record differences.

The deployed Wave 218 P3 paired-t data (per `verification_outputs/wave218-p3-kanzi-framework-wins.json` sha256=9b5c3b68..., 984 bytes; framework_source=verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000/kanzi_n1000_framework_paper_metrics.json sha256=971aa2d1... byte-stable 37550 bytes; baseline_source=verification_outputs/wave218-p3-kanzi-baseline-n1000/kanzi_n1000_paper_metrics.json) shows framework-WINS at d_z=-0.0990, p_raw=1.79e-3, Bonferroni-PASS at α=0.007143.

Paper §7.1 Table 7.1 row 2 (line 641) already reports the deployed value `+0.096 (Wave 196 P3 fresh paired; byte-stable σ=0 vs Wave 88 σ=0.137 Å) | 0.018 | PARTIAL (per-cell UNDERPOWERED at min_effect=0.01; framework-WINS significance preserved)` — but this uses Wave 196 P3 (different from Wave 218 P3) and the sign convention differs (+0.096 vs -0.0990). Wave 254 P1 was APPLIED to DATA_PRESENTATION.md §2.2 (correctly establishes deployed d_z=-0.0990, framework-WINS); Wave 254 P2 was scoped to fix paper-draft*.md §3.3 Table 3.2 line 319 but is **PENDING**.

### 1.2 Proposed fix — paper §3.3 Table 3.2 line 319

**Old string (verbatim from `docs/drafts/paper-flat-flattened.md` line 319):**
```
| **R2** Kanzi inv-proj rmsd_Å | 1000 (vs baseline mean) | +0.6565 | 0.1859 | 111.69 | 999 | 0.0 | [+0.6450, +0.6680] | +3.532 (d_z) | one-sample t | R-level primary | 0.007143 | **YES (regression by direction; lower_is_better; byte-stable)** |
```

**New string (proposed replacement, deployed Wave 218 P3 values):**
```
| **R2** Kanzi inv-proj rmsd_Å | 1000 (paired) | −0.0190 | 0.1916 | −3.131 | 999 | 1.79 × 10⁻³ | [−0.0309, −0.0071] | −0.0990 (d_z) | paired t | R-level primary | 0.007143 | **YES (framework-WINS; lower_is_better; byte-stable σ=0 on framework_inv_proj arm)** |
```

### 1.3 Proposed fix — paper §3.3 line 333 95% CI paragraph (same R2 contradiction)

**Old string (verbatim line 333):**
```
R2 framework REGRESSES [+0.6450, +0.6680] Å (one-sample t vs baseline mean, byte-stable)
```

**New string:**
```
R2 framework-WINS [−0.0309, −0.0071] Å (paired t-test on Wave 218 P3 paired N=1000, framework_inv_proj byte-stable σ=0)
```

### 1.4 Proposed fix — paper §7.1 Table 7.1 row 2 line 641 (sign convention alignment)

**Old string (verbatim line 641):**
```
| 2 | **R2** | Kanzi `reconstruction_kabsch_rmsd_Å` (protein flow-AE, paired N=1000) | `CosineAnnealScheduler` | +0.096 (Wave 196 P3 fresh paired; byte-stable σ=0 vs Wave 88 σ=0.137 Å) | 0.018 (R-level primary k=7) | PARTIAL (per-cell UNDERPOWERED at min_effect=0.01; framework-WINS significance preserved) |
```

**New string (replace +0.096 with Wave 218 P3 deployed value −0.0990, upgrade status from PARTIAL to STRONG since Bonferroni-PASS at α=0.007143):**
```
| 2 | **R2** | Kanzi `reconstruction_kabsch_rmsd_Å` (protein flow-AE, paired N=1000) | `CosineAnnealScheduler` | **−0.0990** (Wave 218 P3 deployed paired-t; framework_source=W214-P2 byte-stable σ=0 framework_inv_proj) | **1.79e-3** (R-level primary k=7) | **STRONG** (framework-WINS; lower_is_better; Bonferroni-PASS at α=0.007143) |
```

### 1.5 Cross-document propagation (low-effort, requiresUserAuth=false)

- `docs/CLAIMS.md` line 3012 K1 / R2 sub-clause: update d_z from +0.096 (Wave 196 P3) to -0.0990 (Wave 218 P3) — same cross-doc fix.
- `docs/CONSOLIDATED_RESULTS.md` line 8334 (Wave 235 P2 R2 row): add cross-reference to Wave 218 P3 deployed data; keep Wave 235 P2 counterfactual d_z=+0.3927 supplementary.
- `docs/audit/wave218-p3-kanzi-framework-wins.md` (if exists): add cross-reference to the R2 paper §3.3 fix at line 319.

### 1.6 Why this is DESTRUCTIVE

The old string says "regression by direction" — this is the OPPOSITE of the deployed data. Replacing it with the deployed value requires dropping the "regression" label, which the Wave 268 strict-clean rule treats as destructive. Hence `requiresUserAuth=true`.

### 1.7 Net impact

- Paper §3.3 Table 3.2 R2 row → framework-WINS (was: REGRESSION).
- Paper §7.1 Table 7.1 R2 row → STRONG (was: PARTIAL).
- §7.2 aggregate reading: 6 STRONG (R1+STRONG→PARTIAL=5, R5c, R2-NEW, R6, K7-NEW→PARTIAL=5; net 4 STRONG/PARTIAL in headline, 7 PARTIAL/UNDERPOWERED/BLOCKED/REGRESSES-boundary in supplementary).
- Word count: 0 net change (same row length).

---

## 2. Issue 2: R3 paper §7.1 Table 7.1 row 3 "N=1000 paired" mislabeling + p=1.07e-18 PROJECTED flag

**Cell:** R3 (FlowMol3 fg_dev, molecular 3D FM)
**Priority:** HIGH (DeepSeek #2)
**Type:** DESTRUCTIVE on paper (replace mislabeled with correctly-labeled)
**requiresUserAuth:** **true** (paper-flat-flattened.md edit)
**Effort:** 10 min (single edit per row + §3.6 cross-ref) = **10 min total**

### 2.1 Background

Paper §7.1 Table 7.1 row 3 line 642 reports R3 as: `FlowMol3 fg_dev (molecular 3D FM, N=1000 paired) | CosineAnnealScheduler | d_s = −0.110 (Wave 195 P2 unpaired); d_z = −0.285 (Wave 208 P2 per-record N=200); d_z = −0.285 projected at N=1000 (Wave 216 P1) | 0.014 (R-level primary k=7, unpaired); 1.07e-18 (projected N=1000 per-record paired) | PARTIAL (UNDERPOWERED at unpaired; STRONG at projected per-record paired; 3-seed pooled SD upgrade BLOCKED at vendor level per Wave 109.C DGL bug)`.

The actual data is **1-seed UNPAIRED per-arm aggregate** (n=999 baseline + n=1000 framework, 1 mol dropped due to CTMC valence artifact), NOT "N=1000 paired". The per-record paired is **n=200 ACTUAL** (data-capped at 200 by `tools/wave87_n1000_sweep.py:298`), and the n=1000 paired is **PROJECTED** via `t_N = t_actual * sqrt(N/n_actual)` scaling — NOT a real N=1000 paired measurement.

The d_z=-0.285 / p=8.03e-05 numbers are correct (n=200 ACTUAL), and the p=1.07e-18 is correct (n=1000 PROJECTED). The issue is **mislabeling** ("N=1000 paired per-record" implies an actual n=1000 paired sweep, which never happened) and **lack of "(PROJECTED from N=200 ACTUAL — not a real N=1000 paired sweep)" caveat** in the table.

### 2.2 Proposed fix — paper §7.1 Table 7.1 row 3 line 642

**Old string (verbatim line 642):**
```
| 3 | **R3** | FlowMol3 `fg_dev` (molecular 3D FM, N=1000 paired) | `CosineAnnealScheduler` | d_s = −0.110 (Wave 195 P2 unpaired); d_z = −0.285 (Wave 208 P2 per-record N=200); d_z = −0.285 projected at N=1000 (Wave 216 P1) | 0.014 (R-level primary k=7, unpaired); 1.07e-18 (projected N=1000 per-record paired) | PARTIAL (UNDERPOWERED at unpaired; STRONG at projected per-record paired; **3-seed pooled SD upgrade BLOCKED at vendor level per Wave 109.C DGL bug**) |
```

**New string (clarify granularity + add PROJECTED caveat):**
```
| 3 | **R3** | FlowMol3 `fg_dev` (molecular 3D FM, 1-seed unpaired per-arm aggregate: n=999 baseline + n=1000 framework, 1 mol dropped due to CTMC valence artifact; per-record paired ACTUAL N=200; projected N=1000) | `CosineAnnealScheduler` | d_s = −0.110 (1-seed unpaired per-arm); d_z = −0.285 (per-record ACTUAL N=200, Wave 208 P2); d_z = −0.285 (per-record PROJECTED N=1000, Wave 216 P1) | 0.014 (R-level primary k=7, unpaired); 8.03e-05 (per-record ACTUAL N=200); 1.07e-18 (per-record PROJECTED N=1000 — NOT a real N=1000 paired sweep) | PARTIAL (UNDERPOWERED at unpaired aggregate; STRONG at per-record ACTUAL N=200; framework-WINS by direction 7/7 cross-wave 1-seed; **3-seed pooled SD upgrade BLOCKED at vendor level per Wave 109.C DGL 2.4.0 incompat**) |
```

### 2.3 Why this is DESTRUCTIVE

The old string labels R3 as "N=1000 paired" implying a real paired sweep at that sample size. Replacing with the honest reading "(1-seed unpaired per-arm aggregate; per-record ACTUAL N=200; PROJECTED N=1000)" corrects a misleading table that a reviewer would interpret as actual N=1000 paired evidence. Hence `requiresUserAuth=true`.

### 2.4 Net impact

- Paper §7.1 Table 7.1 R3 row → honest granularity disclosure (was: misleading "N=1000 paired").
- Word count: +30 words (caveat text); accept.
- The d_z=-0.285 / p=8.03e-05 / p=1.07e-18 numbers are PRESERVED (no change to actual statistical values).

---

## 3. Issue 3: K1 p_bonf paper 0.054 vs actual 0.5676 (no computational basis for 0.054)

**Cell:** K1 (FlowMol3 RDKit-validity_pct)
**Priority:** CRITICAL (DeepSeek #3 — propagated wrong value)
**Type:** DESTRUCTIVE on paper + audit docs (replace wrong with correct)
**requiresUserAuth:** **true** (paper edit + 6 audit doc edits)
**Effort:** 30 min total (5 min paper + 5 min CLAIMS.md + 20 min wave280-p-k1-sweep-result.md §0/§3.3/§3.4/§4/§6 internal consistency fix)

### 3.1 Background

Per `/tmp/wf280-k1/summary.json` (sha256=af322f38..., 4260 bytes): per-seed rdkit_validity_pct = [0.535, 0.590, 0.585], mean=0.5700, std_paired=0.0304, t=2.366, df=2, p_value=0.1419, d_z=+1.3645, **p_bonf=0.5676** (K-level k=4, α=0.05/4=0.0125). Wave 280 P K1 sweep result line 178 correctly shows `p_bonf=0.5676`, but lines 26, 198, 217, 273, 387 all incorrectly cite `p_bonf=0.054`. Paper §3.2/§7.1/§7.4/§7.10 inherited the wrong value (0.054) via the wave280-p status summary.

The 0.054 figure has no mathematical basis in the actual t=2.366/df=2/p=0.1419 data — neither k=4 (0.5676) nor k=7 (0.994) computation produces 0.054. The paper also mis-categorizes K1 as "R-level primary k=7 α=0.007143" when it is a K-level cell (K-level k=4 α=0.0125 per Wave 22 metric-rev3 + Wave 292 audit).

### 3.2 Proposed fix — paper §7.1 Table 7.1 row 8 line 647

**Old string (verbatim line 647):**
```
| 8 | **K1** | FlowMol3 RDKit-validity `rdkit_validity_pct` (3 seeds × N=200) | `CosineAnnealScheduler` | d_z = +1.36 (mean=0.570 ± 0.030 CV=5.3% vs Wave 82 PB baseline 0.5285) | 0.054 (R-level primary k=7; borderline at α=0.007143; gap is N=200 sample-size limitation) | **PARTIAL / BORDERLINE STRONG** (d_z > 0.8 + reproducibility + direction-consistent 3/3) |
```

**New string:**
```
| 8 | **K1** | FlowMol3 RDKit-validity `rdkit_validity_pct` (3 seeds × N=200) | `CosineAnnealScheduler` | d_z = +1.36 (mean=0.570 ± 0.030 CV=5.3% vs Wave 82 PB baseline 0.5285; p_value=0.1419 raw) | **0.5676** (K-level k=4, α=0.0125; FAILS Bonferroni by 45.4×; gap is N=200 sample-size limitation; p_bonf invariant to k choice since 0.5676 >> 0.007143) | **PARTIAL / UNDERPOWERED** (d_z > 0.8 PASS but p_bonf FAIL at K-level α=0.0125; reproducibility STRONG + direction-consistent 3/3) |
```

### 3.3 Proposed fix — paper §3.2 line 215 (K1 row in §3.2 schedule-family table)

Per `wave280-p-k1-sweep-result.md` §3.2 line 178 (correct value 0.5676) vs paper §3.2 line 215 (wrong 0.054). Replace 0.054 with 0.5676 + K-level family attribution.

### 3.4 Proposed fix — paper §7.4 line 717

**Old string (verbatim line 717):**
```
- **K1 PARTIAL / BORDERLINE STRONG** — FlowMol3 RDKit-validity framework-WINS by +1.36 σ on 3 seeds × N=200 (Bonferroni p = 0.054 borderline at α = 0.007143; gap is N=200 sample-size limitation).
```

**New string:**
```
- **K1 PARTIAL / UNDERPOWERED** — FlowMol3 RDKit-validity framework-WINS by +1.36 σ on 3 seeds × N=200 (p_bonf = 0.5676 at K-level α=0.0125; FAILS Bonferroni by 45.4×; gap is N=200 sample-size limitation; p_value=0.1419 raw).
```

### 3.5 Proposed fix — paper §7.10 line 748 + line 731

Line 731 (`All legacy §3.3 / §3.4 / §3.6 / §3.7 / §4 / §5 content preserved verbatim`) is a meta-claim that becomes inaccurate once Issue 3 is applied — but the §7 Empirical Results is the APPENDED §7 (per Wave 297 P5), so the line can stay as-is.

Line 748 (`5 STRONG/PARTIAL cells flagged below are the headline empirical wins: R1, K1, K7, R5c, R6`) — K1 should be DROPPED from the headline roster since it FAILS Bonferroni. After Wave 306 fix, the 5 STRONG/PARTIAL cells become 3 (R5c, R6, R1-as-PARTIAL). This is the §10 Word budget impact noted in §0 above.

### 3.6 Cross-document propagation

Per audit, 0.054 is cited in:
- `docs/audit/wave280-p-k1-sweep-result.md` lines 26, 198, 217, 273, 387 (5 internal inconsistencies)
- `docs/CLAIMS.md` line 3012 K1 sub-clause
- `docs/paper-draft.md` line 1444 + 2956 (legacy draft)
- `docs/baseline-audit-report.md` line 7154

Each line replacement: 5 min × 4 docs = 20 min; 5 lines per audit doc (`wave280-p-k1-sweep-result.md`) × 1 min = 5 min. Total: 25 min for cross-doc propagation. All cross-doc edits are `requiresUserAuth=true` per Wave 268 strict-clean.

### 3.7 Why this is DESTRUCTIVE

The 0.054 figure is load-bearing for the K1 PARTIAL/BORDERLINE-STRONG claim. Replacing with 0.5676 forces the cell to be reclassified from PARTIAL/BORDERLINE-STRONG to PARTIAL/UNDERPOWERED, which removes K1 from the headline roster and is structurally destructive per Wave 268 strict-clean.

### 3.8 Net impact

- K1 status: PARTIAL/BORDERLINE-STRONG → PARTIAL/UNDERPOWERED.
- K1 removed from headline 5 STRONG/PARTIAL cells → 4 STRONG/PARTIAL cells (R1-PARTIAL, R5c-STRONG, R6-PARTIAL, R7-deferred per Issue 5).
- ~530 words freed in §7 (per Wave 305 §6 D3 trim path).

---

## 4. Issue 4: K4 p_bonf=0.734 FAIL — move from MAIN to SUPP

**Cell:** K4+K5 (LineageFlow HMMER length-bias + uniform-AA hmmscan_total_hits)
**Priority:** CRITICAL (DeepSeek #4)
**Type:** DESTRUCTIVE on paper (move K4+K5 from MAIN §7.1 Table 7.1 row 9 to supplementary)
**requiresUserAuth:** **true** (paper edit + position move)
**Effort:** 30 min (paper edits + SUPP table creation)

### 4.1 Background

Paper §7.1 Table 7.1 row 9 line 648 reports K4+K5 as: `LineageFlow length-bias + uniform-AA hmmscan_total_hits (3 seeds × N=100) | CosineAnnealScheduler | d_z = +1.15 (K5 framework-vs-baseline paired-t) | 0.734 (R-level primary k=7; n=3 paired seeds d_f=2 severely underpowered) | UNDERPOWERED (K5 raw p=0.184; K4 powered at hit-count metric 12-22/100)`.

Actual: per `/tmp/wf280-lineageflow/summary_n100.json` (sha256=f382c79a... 3655 bytes): seed42 baseline=20 framework=22 Δ=+2; seed43 baseline=12 framework=14 Δ=+2; seed44 baseline=13 framework=13 Δ=0. Aggregate baseline=15.0±3.559, framework=16.333±4.028, mean_delta=+1.333 (+8.9%), std_paired=1.155, t=2.0, d_f=2, **p_raw=0.184, d_z=+1.155, p_bonf=0.734**. FAILS at all 3 pre-registered alphas (K-level α=0.0125, R-level α=0.007143, paper-level α=0.004545).

Per-cell distinction: K4 hit-count metric is POWERED (12-22 hits/100 records across all 3 seeds, non-zero coverage); K5 paired-delta is Bonferroni-FAIL (p_bonf=0.734). Paper masks this distinction by combining "UNDERPOWERED (K5) / POWERED (K4)" into one row.

### 4.2 Proposed fix — paper §7.1 Table 7.1 row 9 line 648 → SUPP

**Old string (verbatim line 648):**
```
| 9 | **K4+K5** | LineageFlow length-bias + uniform-AA `hmmscan_total_hits` (3 seeds × N=100) | `CosineAnnealScheduler` | d_z = +1.15 (K5 framework-vs-baseline paired-t) | 0.734 (R-level primary k=7; n=3 paired seeds d_f=2 severely underpowered) | **UNDERPOWERED** (K5 raw p=0.184; K4 powered at hit-count metric 12-22/100) |
```

**New string (SUPP-only entry, replaces MAIN row):**
```
| _SUPP_ | **K4** | LineageFlow HMMER hit-count POWER (3 seeds × N=100) | `CosineAnnealScheduler` | coverage=12-22/100 non-zero hits across all 3 seeds (powered at the metric-collection level) | n/a (descriptive hit-count; not a paired-test cell) | FAIL | SUPP — descriptive metric; Bonferroni-FAIL at paired-delta level (see K5) |
| _SUPP_ | **K5** | LineageFlow HMMER framework-vs-baseline delta (3 seeds × N=100) | `CosineAnnealScheduler` | d_z = +1.155 (paired, seed-level n=3 d_f=2) | **0.734** (FAILS at K-level α=0.0125, R-level α=0.007143, paper-level α=0.004545; structural Bonferroni gap from n=3 paired seeds) | **UNDERPOWERED** (K4 hit-count powered at metric-collection level; K5 paired-delta +8.9% (+1.33 hits) visible but Bonferroni-FAIL; would require n≥7 seeds or per-record paired design to close) |
```

### 4.3 Proposed fix — paper abstract line 19/60 metric mis-assignment

Abstract line 19 cites "K4 LineageFlow scPerplexity, K5 LineageFlow pLDDT" — but actual K4 metric is `hmmscan_total_hits`, NOT scPerplexity (which is R6's metric). K5 metric is also `hmmscan_total_hits framework-vs-baseline delta`, NOT pLDDT (also R6's metric).

**Old string (abstract line 19, paraphrased from `docs/drafts/paper-flat-flattened.md`):**
```
K4 LineageFlow scPerplexity, K5 LineageFlow pLDDT
```

**New string:**
```
K4 LineageFlow HMMER length-bias (hmmscan_total_hits), K5 LineageFlow HMMER framework-vs-baseline delta on the same hmmscan_total_hits
```

### 4.4 Cross-document propagation

- `docs/CLAIMS.md` line 3012 K4/K5 sub-clause: update metric assignment to hmmscan_total_hits; mark K4/K5 as SUPP-only after Wave 306 fix.
- `docs/CONSOLIDATED_RESULTS.md` §15.x K2 row: reflect generic single-cell move to SUPP.
- `docs/headline-evidence/` directory: no updates needed (K4/K5 were never in `docs/headline-evidence/` headline roster).

### 4.5 Why this is DESTRUCTIVE

Moving K4+K5 from MAIN §7.1 to SUPP is a position reclassification that Wave 268 strict-clean treats as destructive. The cell goes from a headline cell (one of 11) to a supplementary cell.

### 4.6 Net impact

- K4+K5 → SUPP only; no longer in §7 headline roster.
- §7 headline cells: 11 → 10 (or 9 if K1 also moves to SUPP per Issue 8).
- ~280 words freed in §7 (per Wave 305 §6 D3 trim path).

---

## 5. Issue 5: K7 metric 饱和/反转 — move from MAIN to SUPP, replace with W166 P3 canonical evidence

**Cell:** K7 (LineageFlow novelty)
**Priority:** CRITICAL (DeepSeek #2 — direction inversion on canonical in-git data)
**Type:** DESTRUCTIVE on paper (replace fabricated STRONG with honest W166-P3 direction-inverted)
**requiresUserAuth:** **true**
**Effort:** 60 min (paper edits + W166 P3 cross-reference + W165 P7 zinc-finger context)

### 5.1 Background

Paper §7.1 Table 7.1 row 10 line 650 reports K7 as: `LineageFlow novelty (3 seeds × N=300) | CosineAnnealScheduler | d_z = +∞ (saturated at 1.0 because target DB is small) | <1e-300 (R-level primary k=7) | STRONG (ACTIVE; novelty saturated at 1.0 across all seeds; not informative as an effect-size measure but Bonf-significant by direction-consistency)`.

The paper itself acknowledges "not informative as an effect-size measure" but still claims STRONG. The data direction is INVERTED on the canonical in-git comparison:

- **W280 P driver** (`/tmp/wf280-k7/summary.json` sha256=9fd6fc60..., 1932 bytes): subsamples ONLY `data/lineageflow_n1000/baseline.fasta` (no framework arm); novelty vs the small 200-sequence vendored prebuilt `pfam_holdout_targetDB` (Wave 80); novelty_at_0.5/0.8/0.95 = 1.0 saturated; hits_kept=0; **no homologs**, d_z=∞, p<1e-300. This is a single-arm metric, NOT framework-vs-baseline.
- **W166 P3 canonical comparison** (`verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json` sha256=61dd70fa... 4423 bytes, IN GIT): baseline 466/1000=46.6% novel vs framework 37/1000=3.7% novel at pctid<30% twilight-zone (Rost 1999) at loose -e 100. **Framework is 12.6× LESS Pfam-novel than baseline** (baseline 466/37 = 12.6). Framework produces 425 MORE recognizable Pfam homologs (963 vs 538). **Direction is OPPOSITE of paper claim.**

### 5.2 Proposed fix — paper §7.1 Table 7.1 row 10 line 650 → SUPP + W166 P3 framing

**Old string (verbatim line 650):**
```
| 10 | **K3+R5b** | CIFAR-10 RF K3+R5b fix (Wave 280 P partial, 2 seeds × N=100) | `CosineAnnealScheduler` | d_z = +605.5 (paired-t dominated by framework constant vs baseline noise; framework FID byte-identical across seeds) | **2.97e-3** (R-level primary k=7, **Bonf-significant in REGRESSION direction**) | **REGRESSES** (STRONG-significance in regression; falsifies Wave 275 P4 hypothesis; +52.27% to +52.39% ΔFID at N=100, seed42 + seed43) |
| 11 | **K7** | LineageFlow novelty (3 seeds × N=300) | `CosineAnnealScheduler` | d_z = +∞ (saturated at 1.0 because target DB is small) | **<1e-300** (R-level primary k=7) | **STRONG** (ACTIVE; novelty saturated at 1.0 across all seeds; not informative as an effect-size measure but Bonf-significant by direction-consistency) |
```

**New string (K7 → SUPP + W166 P3 cited; remove d_z=∞/p<1e-300 numerical artifact):**
```
| 10 | **K3+R5b** | CIFAR-10 RF K3+R5b fix (Wave 280 P partial, 2 seeds × N=100) | `CosineAnnealScheduler` | d_z = +605.5 (paired-t dominated by framework constant vs baseline noise; framework FID byte-identical across seeds) | **2.97e-3** (R-level primary k=7, **Bonf-significant in REGRESSION direction**) | **REGRESSES** (STRONG-significance in regression; falsifies Wave 275 P4 hypothesis; +52.27% to +52.39% ΔFID at N=100, seed42 + seed43) |
| _SUPP_ | **K7** | LineageFlow novelty (W166 P3 N=1000 baseline-vs-framework pctid<30% twilight-zone; Rost 1999 corrected novelty metric) | `CosineAnnealScheduler` | baseline 466/1000 = 46.6% novel vs framework 37/1000 = 3.7% novel at pctid<30% twilight-zone (corrected novelty metric, loose -e 100); framework LESS Pfam-novel by 12.6× (baseline/framework ratio = 12.6); framework produces +425 recognizable Pfam homologs (963 vs 538) | n/a (descriptive pctid metric, not a paired-t Bonferroni cell) | SUPP — direction-corrected; framework recapitulates known Pfam family structure (W165 P7 zinc-finger/DNA-binding finding); honest disclosure replaces the W280 P d_z=∞ numerical saturation |
```

### 5.3 Proposed fix — paper §7.9 line 718 K7 STRONG bullet → DELETE

**Old string (verbatim line 718):**
```
- **K7 STRONG** — LineageFlow novelty saturated at 1.0 across 3 seeds × N=300 (Bonferroni p < 1e-300 on `CosineAnnealScheduler`).
```

**Action:** DELETE this bullet. Replace with empty line (preserves §7.9 bullet structure).

### 5.4 Proposed fix — paper §7.2 line 743 "STRONG cells: 3" → "STRONG cells: 2"

**Old string (verbatim line 743):**
```
- **STRONG cells:** 3 (R1, R5c, K7) — Cohen's d_z > 0.8 + Bonferroni p < α + direction-consistent
```

**New string:**
```
- **STRONG cells:** 2 (R5c smoke ckpt only; K7 demoted to SUPP per Wave 306 Issue 5 direction-inversion correction) — Cohen's d_z > 0.8 + Bonferroni p < α + direction-consistent
```

### 5.5 Proposed fix — paper §7.2 line 652 "5 STRONG cells" → "3 STRONG/PARTIAL cells"

**Old string (verbatim line 652, paraphrased):**
```
Of the 11 headline cells, the framework reports 5 STRONG cells (R1, R5c, K7 — framework-WINS with d_z > 0.8 and Bonferroni p < α) + 5 PARTIAL cells (R2, R3, R6, K1, K5 — at least one bar met but not all) + 1 UNDERPOWERED (K5) + 1 BLOCKED (R3 3-seed pooled-SD upgrade; vendor-level blocker per Wave 109.C DGL bug) + 1 REGRESSES-boundary (R5b matched-NFE CIFAR; framework value-add is cross-budget only). **The 5 STRONG cells (R1, R5c, K7) + 2 PARTIAL cells (K1, R6) constitute the framework's primary empirical contribution** in this paper
```

**New string (K1 + K7 demoted to SUPP, K4+K5 demoted to SUPP, R2 upgraded to STRONG per Issue 1, R1 PARTIAL per Issue 8):**
```
Of the 11 headline cells, the framework reports 2 STRONG cells (R5c smoke ckpt only; K7 demoted to SUPP per Wave 306 Issue 5) + 4 PARTIAL cells (R2 STRONG per Issue 1, R3, R6, R1 PARTIAL per Issue 8) + 1 UNDERPOWERED (K1 per Issue 3) + 1 REGRESSES-boundary (R5b matched-NFE CIFAR). K4+K5 + K7 + K1 moved to SUPP. **The 3 STRONG/PARTIAL cells (R5c, R2, R6) + 1 PARTIAL cell (R3) constitute the framework's primary empirical contribution** in this paper
```

### 5.6 Cross-document propagation

- `docs/CLAIMS.md` line 3012 K7 sub-clause: update with W166 P3 canonical evidence.
- `docs/CONSOLIDATED_RESULTS.md` §15.x K7 row: replace d_z=∞ with W166 P3 baseline-vs-framework numbers.
- `docs/headline-evidence/README.md` line 21 (R5 2D Eight Gaussians row): K7 was never in headline-evidence; no update.
- `docs/audit/wave280-p-k7-sweep-result.md` (audit doc): add W166 P3 cross-reference; mark d_z=∞ as numerical artifact.

### 5.7 Why this is DESTRUCTIVE

The d_z=+∞ / p<1e-300 STRONG claim is load-bearing for the K7 cell being a STRONG cell in the headline roster. Removing it and replacing with W166 P3 direction-INVERTED evidence is structurally destructive per Wave 268 strict-clean.

### 5.8 Net impact

- K7 → SUPP only; no longer in §7 headline roster.
- §7 headline cells: 11 → 8-9 (K1/K4+K5/K7 all demoted).
- ~150 words freed in §7 (per Wave 305 §6 D3 trim path).

---

## 6. Issue 6: R5b conditional boundary on n_rounds (n_rounds=1 WINS, n_rounds≥2 REGRESSES)

**Cell:** R5b (CIFAR-10 RF matched-NFE=50 FID, image RF)
**Priority:** CRITICAL (DeepSeek #6 — conditional boundary not in paper)
**Type:** DESTRUCTIVE on paper (replace single-cell REGRESSION with conditional boundary)
**requiresUserAuth:** **true**
**Effort:** 30 min (paper §3.2/§3.6/§7.1 edits + Wave 305 §4 paste-ready block)

### 6.1 Background

Paper §3.2 Table 3.2 line 322 reports R5b as: `CIFAR-10 RF NFE=50 FID | 10 (paired chunks, df=9) | +90.045 | 10.545 | 8.539 | 9 | 1.31 × 10⁻⁵ | [+69.378, +110.712] | +2.700 (d_z) | paired chunk t | R-level primary | 0.007143 | NO (REGRESSES by direction; boundary characterization)`. Paper §3.6 line 386 + §3.3 line 312 characterize R5b as "matched-NFE CIFAR-10 RF regression (+24-31%)".

Conditional boundary (data-canonical): n_rounds=1 (Wave 235 P1, N=200 paired per-record, CosineAnnealScheduler primary): ΔFID -1.60% (d_z=+4.368, t=61.77, p_raw=8.72e-132, Bonferroni PASS at α=0.007143) — **framework-WINS**. CodimensionSheet ΔFID -2.53% (d_z=+4.728), EvidenceDriven -0.12%, FreeTraj -0.66% (3/4 schedulers framework-WINS at n_rounds=1). At n_rounds=2 (Wave 225 P7, N=200 paired per-record, cosine): ΔFID +9.77% (d_z=+5.444) — REGRESSES. Matched-effective-NFE: +20.89%. n_rounds=10 no_final_restart: +30.19% (falsifies DeepSeek hypothesis that no-final-restart would mitigate regression).

### 6.2 Proposed fix — paper §3.2 line 322 (R5b row)

**Old string (verbatim line 322):**
```
| **R5b** CIFAR-10 RF NFE=50 FID | 10 (paired chunks, df=9) | +90.045 | 10.545 | 8.539 | 9 | 1.31 × 10⁻⁵ | [+69.378, +110.712] | +2.700 (d_z) | paired chunk t | R-level primary | 0.007143 | NO (REGRESSES by direction; **boundary characterization**) |
```

**New string (conditional boundary disclosure per Wave 235 P1):**
```
| **R5b** CIFAR-10 RF NFE=50 FID (CONDITIONAL on n_rounds) | 200 (paired per-record) | n_rounds=1: −0.14 (Cosine) / −0.22 (Codim); n_rounds≥2: +0.85 (cosine n_rounds=2) / +1.82 (cosine n_rounds=4) | ≈0.2 / ≈10.5 | n_rounds=1: −4.37 / n_rounds≥2: +5.44 to +8.54 | 199 / 9 | n_rounds=1: 8.72 × 10⁻¹³² / n_rounds≥2: 1.31 × 10⁻⁵ | n_rounds=1: [−0.21, −0.07] / n_rounds≥2: [+0.69, +1.11] | n_rounds=1: −4.37 / n_rounds≥2: +2.70 to +5.44 | paired t (per-record L2) | R-level primary | 0.007143 | **CONDITIONAL**: n_rounds=1 WINS (3/4 schedulers, Bonf-PASS at α=0.007143, Wave 235 P1); n_rounds≥2 REGRESSES (ΔFID +9.77% to +30.19%, falsifies DeepSeek no-final-restart hypothesis) |
```

### 6.3 Proposed fix — paper §7.1 row 5 line 644

**Old string (verbatim line 644):**
```
| 5 | **R5b** | CIFAR-10 RF matched-NFE=50 FID (image RF, N=1000 chunked paired) | `CosineAnnealScheduler` (Wave 280 P K3+R5b fix) | **d_z = +2.700** (Wave 191 P2 N=1000 chunked FID) | **9.17e-5** (R-level primary k=7, **Bonferroni-significant in REGRESSION direction**) | **REGRESSES (boundary characterization)** — framework regresses by +20.21% FID at matched NFE=50; framework's value-add is cross-budget only, not matched-NFE. Reported with the same prominence as the cross-budget headline. |
```

**New string (add conditional boundary per Wave 235 P1):**
```
| 5 | **R5b** | CIFAR-10 RF matched-NFE=50 FID (image RF, CONDITIONAL on n_rounds; N=200 paired per-record Wave 235 P1 + N=10 chunked Wave 191 P2) | `CosineAnnealScheduler` | **d_z = +2.700** (Wave 191 P2 N=10 chunked n_rounds=4); **d_z = −4.368** (Wave 235 P1 N=200 paired n_rounds=1, framework-WINS); **d_z = +5.444** (Wave 225 P7 N=200 paired n_rounds=2, REGRESSES) | **9.17e-5** (Wave 191 P2 chunked; Bonf-significant in REGRESSION at α=0.007143); **8.72e-132** (Wave 235 P1 per-record n_rounds=1, framework-WINS Bonf-PASS); **<1e-149** (Wave 225 P7 per-record n_rounds=2, REGRESSES Bonf-PASS) | **CONDITIONAL** (n_rounds=1 framework-WINS on 3/4 schedulers by ΔFID −1.60% to −2.53%; n_rounds≥2 framework-REGRESSES by ΔFID +9.77% to +30.19%; --no-final-restart falsifier at n_rounds=10 grows regression to +30.19%; framework's value-add is cross-budget only at matched-NFE) |
```

### 6.4 Proposed fix — paper §3.6 line 386 + §3.3 line 312

Both sections characterize R5b as "matched-NFE CIFAR-10 RF regression (+24-31%)" — append a conditional sentence "at n_rounds=1 (Wave 235 P1), the framework WINS by ΔFID −1.60% to −2.53% on 3/4 schedulers; the regression requires n_rounds≥2."

### 6.5 Cross-document propagation

Use Wave 305 §4 paste-ready text block verbatim for §7 / §9 Limitations. No additional cross-doc edits needed beyond what Wave 305 already documents.

### 6.6 Why this is DESTRUCTIVE

The current single-cell REGRESSION claim at §3.2 line 322 + §7.1 row 5 line 644 is replaced with a CONDITIONAL boundary. The "REGRESSES" label is preserved for n_rounds≥2 but the n_rounds=1 WINS reversal is added — this is a structural change to the cell framing per Wave 268 strict-clean.

### 6.7 Net impact

- R5b becomes CONDITIONAL (n_rounds=1 WINS, n_rounds≥2 REGRESSES) — paper §3.2 + §7.1 both updated.
- Word count: +30 words (conditional disclosure text).
- Status remains REGRESSES-boundary in headline roster.

---

## 7. Issue 7: Cell-ID 不一致（R4 vs R5a）+ abstract metric mis-assignment + "Kanzi k6 foldability" → "LineageFlow k6 foldability"

**Cell:** R5a (2D Two Moons W2) + R6 (k6 foldability)
**Priority:** MEDIUM (DeepSeek #7 + abstract mis-assignment)
**Type:** NEUTRAL on paper (no semantic change; rename for consistency)
**requiresUserAuth:** **false** (cross-document only; provenance mechanical)
**Effort:** 60 min total (paper §3.3/§7 + headline-evidence + CLAIMS.md cross-doc propagation)

### 7.1 Background

Naming inconsistencies:
- R4 (in `docs/headline-evidence/README.md` line 20 + `docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/SOURCE.md` line 1 + user task description) vs R5a (in paper §3.3 Table 3.2 line 321 + §2.9 Table 2.9 line 209 + §7.1 Table 7.1 row 4 line 643). Same physical cell, two cell-IDs.
- R5 (in `docs/headline-evidence/README.md` line 21 + `docs/headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/SOURCE.md`) vs R5a/R5b/R5c split in paper. R5 2D Eight Gaussians has no 11-cell roster counterpart.
- K4 metric (paper abstract line 19/60: "scPerplexity") vs actual data (`hmmscan_total_hits`). K5 metric (paper abstract line 19/60: "pLDDT") vs actual data (`hmmscan_total_hits framework-vs-baseline delta`).
- R6 label: "Kanzi k6 foldability" (paper §7.1 row 7 line 646) vs "LineageFlow k6 foldability" (paper §2.9 line 277, data files). k6 foldability uses LineageFlowAdapter (Pfam k6 subset via OmegaFold+ESM-IF), NOT Kanzi.

### 7.2 Proposed fix — Cell-ID: R4 → R5a in `docs/headline-evidence/`

**File:** `docs/headline-evidence/README.md` line 20
**Old string (paraphrased):**
```
R4 2D Two Moons W2 (matched seed, baseline=0.5029 → framework=0.4663, −7.28%)
```

**New string:**
```
R5a 2D Two Moons W2 (per Wave 189 P2 post-cd70821 actual data: baseline=0.0736 → framework=0.0759, +3.16% framework-WORSE; TIE per Wave 189 P2 verdict; pre-cd70821 -7.28% headline is artifact of np.tanh vs ReLU activation mismatch bug, fixed by commit cd70821 2026-08-31)
```

**File:** `docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/SOURCE.md` (entire file or rename to `r5a_2d_two_moons_w2/`)

**Action:** Rename directory `docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/` → `docs/headline-evidence/r5a_2d_two_moons_w2_postcd70821/` and update SOURCE.md to reflect post-cd70821 actual data + add cross-reference to Wave 189 P2 TIE verdict + flag the pre-cd70821 -7.28% as artifact (not reproducible).

### 7.3 Proposed fix — abstract metric mis-assignment K4 + K5

**File:** `docs/drafts/paper-flat-flattened.md` abstract line 19 + line 60

**Old string (line 19):**
```
K4 LineageFlow scPerplexity, K5 LineageFlow pLDDT
```

**New string:**
```
K4 LineageFlow HMMER length-bias (hmmscan_total_hits), K5 LineageFlow HMMER framework-vs-baseline delta on the same hmmscan_total_hits
```

### 7.4 Proposed fix — R6 "Kanzi k6 foldability" → "LineageFlow k6 foldability"

**File:** `docs/drafts/paper-flat-flattened.md` §7.1 Table 7.1 row 7 line 646 + abstract line 191/60 + §7.1 line 630 enumeration

**Old string (line 646):**
```
| 7 | **R6** | Kanzi k6 foldability `pLDDT_mean` + `scPerplexity` (protein foldability, N=1000 paired) | `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler` (only paper-quantity-driven headline) | ... |
```

**New string:**
```
| 7 | **R6** | LineageFlow k6 foldability `pLDDT_mean` + `scPerplexity` (protein foldability, N=1000 paired; Pfam k6 subset via OmegaFold+ESM-IF per Wave 161 frozen foldability.jsonl) | `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler` (only paper-quantity-driven headline) | ... |
```

### 7.5 Cross-document propagation

- `docs/CLAIMS.md` line 3040 + 3012 + 3086: rename R4 → R5a where referring to 2D Two Moons; fix K4/K5 metric assignment; fix R6 "Kanzi" → "LineageFlow".
- `docs/CONSOLIDATED_RESULTS.md` §15.x R5a row: rename R5a → confirm naming.
- `docs/audit/wave280-p-k4k5-sweep-result.md` §3.2 line 178: K4/K5 metric assignment already correct (hmmscan_total_hits); no change needed.

### 7.6 Why requiresUserAuth=false

These are mechanical renames with no semantic change to the actual statistical claims. Per Wave 268 strict-clean rule, "no semantic change" edits don't require user auth — but any edit to `docs/drafts/paper-flat-flattened.md` (Issue 7.3 + 7.4) IS `requiresUserAuth=true`. The headline-evidence rename (Issue 7.2) is `requiresUserAuth=false` because it's a cross-doc directory rename.

### 7.7 Net impact

- Cell-ID unified: R4 (headline-evidence) → R5a (paper).
- Abstract corrected: K4/K5 metrics correctly assigned.
- R6 label corrected: "LineageFlow k6 foldability" (not "Kanzi k6 foldability").
- ~50 lines changed across 4 documents; no statistical impact.

---

## 8. Issue 8: K1/K4/K7 应在 SUPP 但 paper 在 MAIN

**Cells:** K1, K4+K5, K7
**Priority:** HIGH (DeepSeek #8 — applies Issue 3, 4, 5 position reclassifications)
**Type:** NEUTRAL (subsumed by Issue 3 + 4 + 5)
**requiresUserAuth:** **true** (paper-edit position move)
**Effort:** 0 min (already counted in Issue 3, 4, 5)

### 8.1 Background

Per Issues 3, 4, 5: K1, K4+K5, K7 move from MAIN §7.1 Table 7.1 to SUPP (or stay in MAIN with corrected p_bonf for K1 per Issue 3 partial fix). DeepSeek #8 specifically flags that p_bonf-FAIL cells (K4, K7) cannot sit in MAIN §7 — they belong in supplementary.

### 8.2 Proposed fix — apply Issues 3 + 4 + 5

No additional fix beyond what Issues 3 + 4 + 5 specify. The §7 headline roster reduces from 11 to 8 cells (R1, R2, R3, R5a, R5b, R5c, R6, plus any PARTIALs the user wishes to retain) with K1/K4+K5/K7 demoted to SUPP.

### 8.3 Word budget impact

Per Wave 305 §6 line 150 ("drop ~530 words from §7 Empirical Results — defer K1 to supplementary"): K1 alone accounts for ~530 words. K4+K5 + K7 add another ~430 words combined. Total ~960 words freed from §7. Per Wave 305 §6 word budget, this overshoots the 530-word trim requirement by 430 words — sufficient buffer to also drop R1 from headline (per Issue 8 cross-ref) and add §2 Related Work (700 words) + §8 Reproducibility (600 words) + §11 Conclusion (250 words) at D3.

### 8.4 Why this is NEUTRAL

Issue 8 is a position reclassification applied via Issues 3, 4, 5. No additional standalone fix.

### 8.5 Net impact

- §7 headline cells: 11 → 8 (after K1/K4+K5/K7 demotion).
- Word count: ~960 words freed in §7.
- §7 framework-not-theory verdict (line 671) changes from "10 of 11 cosine" to "8 of 8 cosine" (since all 8 retained cells use cosine after K-cell SUPP demotion).

---

## 9. Issue 9: K1/K4 数据在 /tmp/，不在 git

**Cells:** K1, K4+K5, K7, R1, R5c, R6 (all cells with /tmp/-only data)
**Priority:** HIGH (DeepSeek #9 — data integrity for reproducibility)
**Type:** ADDITIVE (move /tmp/ files → verification_outputs/ + git add + commit)
**requiresUserAuth:** **true** (per Wave 268 — /tmp → verification_outputs moves require user auth)
**Effort:** ~3 hours total (per audit inventory)

### 9.1 Background

The following cells have data ONLY in `/tmp/` (NOT in git):
- **K1**: `/tmp/wf280-k1/summary.json` (sha256=af322f38..., 4260 bytes) + `driver.py` (63fd80e4... 13254 bytes) + `run.log` (1925 bytes)
- **K7**: `/tmp/wf280-k7/summary.json` (sha256=9fd6fc60... 1932 bytes) + `seed{42,43,44}/novelty.json` (1705 bytes each) + `seed{42,43,44}/novelty_per_seq.jsonl` (≈41 KB each)
- **R1**: `/tmp/wf280-r1/summary.json` (sha256=7b3db36d... 2592 bytes) + `seed{42,43,44}/{eval,fasta}/{framework,baseline}/...` (≈30 files, ≈3 MB)
- **R5c**: `/tmp/wf280-r5c/aggregate.json` (sha256=806da390... 4280 bytes) + `seed{42,43,44}/sweep_summary.json` (≈6000 bytes each) + 12 npz files (≈100 KB each)
- **R6**: `/tmp/wf280-r6/summary.json` (sha256=67770288... 11518 bytes) + `seed{42,43,44}/sweep_summary.json` (≈1900 bytes each)
- **K4+K5 (LineageFlow)**: `/tmp/wf280-lineageflow/summary_n100.json` (sha256=f382c79a... 3655 bytes) + `seed{42,43,44}/{fasta,hmmscan_n100}/...` (≈10 files)
- **R5b boundary (additional CIFAR-10 RF data)**: `/tmp/wf286-cifar/aggregate.json` (sha256=66c3c7ca... 3662 bytes) + `all_cells.csv` (sha256=e2829598... 2812 bytes) + per-scheduler subdirs (≈3 MB npz files)

The user's directive: "做了算法上的改进就该想办法去做实验上的验证" + "claude相关的确实不要commit" — drivers are not committed, but analysis output (summary.json + run.log) should be in git for reproducibility.

### 9.2 Proposed data migration (per-cell)

For each cell, create a `verification_outputs/wave280-p-{cell}/` directory (or `wave286-cifar/` for R5b), copy the relevant files, generate SHA-256 sidecars, and prepare for git commit.

**Per-cell schema:**
- Destination: `verification_outputs/wave280-p-{cell}/`
- Files: `{summary.json, summary_n100.json, aggregate.json, all_cells.csv, run.log}` + per-seed/per-scheduler sub-directories
- SHA-256 sidecars: `verification_outputs/wave280-p-{cell}/SHA256SUMS.txt`
- Commit message template: `Wave 306: data migration for {cell} — move /tmp/wf280-{cell}/* → verification_outputs/ for paper-A camera-ready reproducibility`

#### 9.2.1 K1 data migration (CRITICAL priority)

- **src:** `/tmp/wf280-k1/summary.json` + `driver.py` + `run.log`
- **dst:** `verification_outputs/wave280-p-k1/summary.json` + `driver.py` + `run.log`
- **effort:** 5 min (cp + sha256sum + git add)
- **commit message:** `Wave 306: data migration for K1 (FlowMol3 RDKit-validity 3-seed × N=200) — move /tmp/wf280-k1/* → verification_outputs/wave280-p-k1/ + SHA256SUMS.txt; canonical for paper §7.1 Table 7.1 row 8 + Issue 3 p_bonf=0.5676 fix`

#### 9.2.2 K4+K5 data migration (CRITICAL priority)

- **src:** `/tmp/wf280-lineageflow/summary_n100.json` + `seed{42,43,44}/{fasta,hmmscan_n100}/*`
- **dst:** `verification_outputs/wave280-p-k4k5/summary_n100.json` + `seed{42,43,44}/{fasta,hmmscan_n100}/*`
- **effort:** 10 min (multi-file cp + sha256sum + git add)
- **commit message:** `Wave 306: data migration for K4+K5 (LineageFlow HMMER length-bias + uniform-AA hmmscan_total_hits 3-seed × N=100) — move /tmp/wf280-lineageflow/* → verification_outputs/wave280-p-k4k5/ + SHA256SUMS.txt; canonical for paper §7.1 Table 7.1 row 9 SUPP + Issue 4 p_bonf=0.734 disclosure`

#### 9.2.3 K7 data migration (HIGH priority)

- **src:** `/tmp/wf280-k7/summary.json` + `seed{42,43,44}/novelty.json` + `seed{42,43,44}/novelty_per_seq.jsonl`
- **dst:** `verification_outputs/wave280-p-k7/summary.json` + `seed{42,43,44}/{novelty.json,novelty_per_seq.jsonl}`
- **effort:** 10 min (multi-file cp + sha256sum + git add)
- **commit message:** `Wave 306: data migration for K7 (LineageFlow novelty 3-seed × N=300, Wave 280 P follow-up) — move /tmp/wf280-k7/* → verification_outputs/wave280-p-k7/ + SHA256SUMS.txt; canonical SUPP for paper §7.1 row 10 + Issue 5 W166 P3 direction-inversion disclosure`

#### 9.2.4 R1 data migration (MEDIUM priority)

- **src:** `/tmp/wf280-r1/summary.json` + `seed{42,43,44}/{eval,fasta}/{framework,baseline}/{summary.json,family_validity_per_seq.jsonl,*.fasta}` (≈30 files, ≈3 MB)
- **dst:** `verification_outputs/wave280-p-r1/summary.json` + `seed{42,43,44}/{eval,fasta}/{framework,baseline}/...`
- **effort:** 20 min (multi-file cp + sha256sum + git add — large directory tree)
- **commit message:** `Wave 306: data migration for R1 (LineageFlow HMMER 3-seed sweep) — move /tmp/wf280-r1/* → verification_outputs/wave280-p-r1/ + SHA256SUMS.txt; canonical for paper §7.1 Table 7.1 row 1 + Issue 1 seed-43/44 fallback-contamination disclosure (only seed=42 single-seed evidence valid)`

#### 9.2.5 R5c data migration (MEDIUM priority)

- **src:** `/tmp/wf280-r5c/aggregate.json` + `aggregate.py` + `seed{42,43,44}/sweep_summary.json` + `seed{42,43,44}/{baseline,cosine,codimension_sheet,evidence_driven}_samples.npz` (≈15 files, ≈900 KB npz)
- **dst:** `verification_outputs/wave280-p-r5c/aggregate.json` + `aggregate.py` + `seed{42,43,44}/{sweep_summary.json,*_samples.npz}`
- **effort:** 20 min (multi-file cp + sha256sum + git add)
- **commit message:** `Wave 306: data migration for R5c (MNIST FM production-ckpt 3-seed × N=200) — move /tmp/wf280-r5c/* → verification_outputs/wave280-p-r5c/ + SHA256SUMS.txt; canonical for paper §7.1 Table 7.1 row 6 + smoke-ckpt vs production-ckpt honest disclosure (smoke STRONG; production direction-FLIPS to baseline_wins)`

#### 9.2.6 R6 data migration (MEDIUM priority)

- **src:** `/tmp/wf280-r6/summary.json` + `seed{42,43,44}/sweep_summary.json`
- **dst:** `verification_outputs/wave280-p-r6/summary.json` + `seed{42,43,44}/sweep_summary.json`
- **effort:** 10 min
- **commit message:** `Wave 306: data migration for R6 (LineageFlow k6 foldability follow-up) — move /tmp/wf280-r6/* → verification_outputs/wave280-p-r6/ + SHA256SUMS.txt; canonical for paper §7.1 Table 7.1 row 7 + counterfactual disclosure (TierAwareCodimensionSheetScheduler wrapper post-processing per Wave 225 P4 / Wave 233 P3)`

#### 9.2.7 R5b boundary data migration (HIGH priority)

- **src:** `/tmp/wf286-cifar/aggregate.json` + `all_cells.csv` + per-scheduler sub-dirs (`{cosine,codimension_sheet,convergence_adaptive,nfe_aware_memory,paper_ratio_adaptive}/seed*/...`) ≈3 MB npz
- **dst:** `verification_outputs/wave286-r5b-boundary/aggregate.json` + `all_cells.csv` + per-scheduler sub-dirs
- **effort:** 30 min (large multi-file cp + sha256sum + git add; ~30 files including ~3 MB npz files)
- **commit message:** `Wave 306: data migration for R5b boundary (CIFAR-10 RF matched-NFE=50 FID 5-scheduler × 3-seed) — move /tmp/wf286-cifar/* → verification_outputs/wave286-r5b-boundary/ + SHA256SUMS.txt; canonical for paper §3.2 line 322 + §7.1 row 5 conditional-boundary disclosure (n_rounds=1 WINS, n_rounds≥2 REGRESSES)`

#### 9.2.8 R5b byte-stable data migration (MEDIUM priority)

- **src:** `/tmp/wf296-p7-fid-compare/summary.json` (sha256=450d242a... 2226 bytes)
- **dst:** `verification_outputs/wave296-p7-r5b-byte-stable/summary.json`
- **effort:** 5 min
- **commit message:** `Wave 306: data migration for R5b byte-stable FID compare — move /tmp/wf296-p7-fid-compare/* → verification_outputs/wave296-p7-r5b-byte-stable/ + SHA256SUMS.txt; canonical for Wave 296 P7 FID Δ=0% framework robustness evidence`

#### 9.2.9 Ablation data migration (LOW priority)

- **src:** `/tmp/wf302-p5-ablation/ablation_summary.json` (sha256=f506a8c4... 3318 bytes) + per-arm sub-dirs (`A_cosine_L4/seed*/...`) ≈5 MB
- **dst:** `verification_outputs/wave302-p5-ablation/ablation_summary.json` + per-arm sub-dirs
- **effort:** 20 min
- **commit message:** `Wave 306: data migration for 5-arm ablation (Wave 302 P5) — move /tmp/wf302-p5-ablation/* → verification_outputs/wave302-p5-ablation/ + SHA256SUMS.txt; canonical for paper §3.5 cumulative-add ablation`

### 9.3 Aggregate effort

Total: 5+10+10+20+20+10+30+5+20 = **130 min ≈ 2.2 hours** for all 9 data migrations. Plus 30 min for SHA-256 sidecar generation + 10 min for git add + commit = **~3 hours total**.

### 9.4 Why requiresUserAuth=true

Per Wave 268 strict-clean rule: any data move from `/tmp/` to `verification_outputs/` requires explicit user authorization because it adds tracked files to git. This is the largest single `requiresUserAuth=true` bucket (9 items × 1 line of credit per user).

### 9.5 Net impact

- 9 data migrations completed; ~30 GB of /tmp/ data → verification_outputs/ + git.
- All 11 cells now have at least one canonical data file in git for reproducibility.
- The user's "做了算法上的改进就该想办法去做实验上的验证" directive satisfied for all 9 cells.

---

## 10. PROPOSED 5 MAIN-TEXT CLAIMS (after Wave 306 fix)

Per Wave 306 audit findings + Issues 1-9 above, the **post-fix 5 main-text claims** are:

### 10.1 Claim R1 (LineageFlow HMMER, after Issue 1 + 8 fixes)

> **R1 LineageFlow HMMER framework-WINS** by +184 hits seed=42 single-seed (Wave 158 P2, N=1000 paired per-record, Cohen's d_z=+0.182, t=5.741, p_raw=1.25e-08, CI95=[+0.121, +0.247], Bonferroni-significant at R-level α=0.007143). **3-seed-pooled sweep (Wave 280 P, seeds 42/43/44) INVALID due to seed-43/44 framework-fallback rate=100%** (per `/tmp/wf280-r1/seed{43,44}/fasta/manifest.json` framework_fallback_per_family_count=={PF00005.27: 250, PF00072.24: 250, PF00183.19: 250, PF02517.18: 250}; only seed=42 invoked the real framework). 3-seed-pooled d_z=+0.6926, p_raw=0.353, p_bonf=1.0. **Honest verdict: PARTIAL single-seed + 3-seed-pooled UNDERPOWERED.** Source: `verification_outputs/wave158-p2-lineageflow-n1000/{baseline,framework}_hits.tbl` (sha256=d2db3769/04830145, byte-stable seed=42).

### 10.2 Claim R2 (Kanzi RMSD, after Issue 1 fix)

> **R2 Kanzi reconstruction_kabsch_rmsd_Å framework-WINS** (Wave 218 P3 deployed paired-t, N=1000 paired per-record, baseline_mean=0.9028 Å → framework_mean=0.8838 Å, mean_diff=−0.0190 Å, sd_diff=0.1916, t=−3.131, df=999, p_raw=1.79e-3, CI95=[−0.0309, −0.0071], Cohen's d_z=−0.0990, Bonferroni-significant at R-level α=0.007143). **framework_source=W214-P2 byte-stable** (sha256=971aa2d1... 37550 bytes); baseline_source=W218-P3 baseline (sha256=35343d1c...). The d_z=+3.532 one-sample-t REGRESSION claim at paper §3.3 line 319 (Wave 206 P2, framework_source=W196_byte_stable_fallback) is **REMOVED**. Source: `verification_outputs/wave218-p3-kanzi-framework-wins.json` (sha256=9b5c3b68... 984 bytes) + `verification_outputs/wave218-p3-kanzi-framework-wins.csv` (536 bytes).

### 10.3 Claim R3 (FlowMol3 fg_dev, after Issue 2 fix)

> **R3 FlowMol3 fg_dev framework-WINS by direction** at 1-seed seed=42 per-record ACTUAL N=200 paired (Wave 208 P2; baseline_mean=0.6381 → framework_mean=0.6146, mean_diff=−0.0235, sd_diff=1.264, t=−4.027, df=199, p_raw=8.03e-05, Cohen's d_z=−0.285, Bonferroni-significant at R-level α=0.007143). Per-record PROJECTED N=1000 paired: p_raw=1.07e-18 (NOT a real N=1000 paired sweep — caveat added per Issue 2). 3-seed-pooled SD upgrade **BLOCKED at vendor level** (DGL 2.4.0 incompat with PyTorch 2.4 + CUDA 12.1 per Wave 109.C). 7/7 cross-wave direction-consistent at 1-seed. Per-arm aggregate UNPAIRED (n=999 baseline + n=1000 framework): d_s=−0.110, p_raw=1.42e-2, NOT Bonferroni-significant at strict α. **Honest verdict: PARTIAL single-seed per-record ACTUAL + UNPAIRED UNPAIRED aggregate UNDERPOWERED + 3-seed-POOLED BLOCKED.** Source: `verification_outputs/wave216-p1-r3-per-record.json` + `verification_outputs/wave206-p3-flowmol3-n1000.json` (sha256=caf9412e...).

### 10.4 Claim R5c (MNIST FM FID, after Issue 5 partial fix)

> **R5c MNIST FM framework-WINS** on smoke ckpt (Wave 191 P3 N=1000 paired chunk-FID, evidence_driven arm: baseline_fid=29.49 → best_arm_fid=23.39, Δ=−28.43%, Cohen's d_z=−13.175, t=−131.72, df=9, p_raw=1.32e-11, Bonferroni-significant at R-level α=0.007143). Production-ckpt (Wave 280 P 3-seed × N=200) **direction FLIPS to baseline_wins at matched-NFE=50** (per-seed cosine arm d_z=+1.546/+1.331/+1.024 all positive; aggregate Δ+10.37% framework-REGRESSES, p_bonf=0.0133). **Honest verdict: STRONG on smoke ckpt + PARTIAL on production ckpt** (direction-disclosed per Wave 305 §4 paste-ready block). Source: `verification_outputs/wave191-p3-mnist-n1000.json` (in git) + `/tmp/wf280-r5c/aggregate.json` (sha256=806da390... 4280 bytes; to be migrated to `verification_outputs/wave280-p-r5c/aggregate.json` per Issue 9.2.5).

### 10.5 Claim R6 (LineageFlow k6 foldability, after Issue 7.4 + counterfactual qualifier)

> **R6 LineageFlow k6 foldability** (Pfam k6 subset via OmegaFold+ESM-IF per Wave 161 frozen foldability.jsonl, N=1000 paired per-record) — **cluster-robust framework-WINS** on scPerplexity (overall d_z=−1.077 naive / −4.019 cluster, p_cluster=4.02e-3 Bonferroni-significant at α_cluster=0.00208) and **SELECTIVE framework-WINS on hard-tier pLDDT** (d_z=+1.189 hard / +0.218 medium / −0.998 easy, hard p_cluster = 1.28e-2 marginally above strict α_cluster=0.00208). Overall pLDDT d_z=+0.071 naive / +0.333 cluster, p_cluster=5.53e-1 **UNDERPOWERED at cluster level**. The **TierAwareCodimensionSheetScheduler wrapper** is a **COUNTERFACTUAL construction** (per Wave 225 P4 + Wave 233 P3 REDUCED_INTENSITY_FACTOR=0.5 per-record diff shift; Wave 161 foldability.jsonl is frozen; NOT a live GPU run) — only paper-quantity-driven headline scheduler on R6 (per §7.4 line 671 disclosure, 1 of 11 cells). Source: `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl` (sha256=...; in git) + `verification_outputs/wave203-p3-k6-cluster-robust.json` + `verification_outputs/wave225-p4-k6-counterfactual.json` + `verification_outputs/wave233-p3-k6-counterfactual.json`.

### 10.6 Net R-level + K-level status after Wave 306 fix

After Issues 1-9 applied:
- **STRONG cells:** 2 (R5c smoke ckpt only; R2 deployed per Issue 1)
- **STRONG/PARTIAL cells:** 4 (R1 PARTIAL, R5c STRONG, R2 STRONG, R6 PARTIAL hard-tier + scPerplexity)
- **PARTIAL cells:** 1 (R3 per-record ACTUAL + UNPAIRED UNPAIRED UNDERPOWERED)
- **REGRESSES-boundary:** 1 (R5b CONDITIONAL per Issue 6)
- **TIE:** 1 (R5a per Wave 189 P2 post-cd70821)
- **Demoted to SUPP:** 3 (K1, K4+K5, K7)
- **BLOCKED:** 1 (R3 3-seed pooled SD upgrade; vendor-level blocker per Wave 109.C DGL 2.4.0)

Headline roster (after Wave 306): **8 cells in §7** (R1, R2, R3, R5a, R5b, R5c, R6, plus any PARTIALs) — down from 11. K1/K4+K5/K7 in SUPP.

---

## 11. Word Budget Reconciliation

Per Wave 305 §6 word budget (5-7 day plan):
- Current paper: 36027 words at 1404 lines
- Target: ~7700 words (IEEEtran 14-page bound)
- Required trim: ~1100 words from §7 + §6 deletion (~520 words §6 + ~1700 words legacy §1 + §2.8 + §3.5)

**Wave 306 trim contributions:**
- Issue 1 (R2 §3.3 + §7.1 row): 0 words net change
- Issue 2 (R3 §7.1 row caveat): +30 words
- Issue 3 (K1 §7.1 row + line 717 + line 748): ~530 words freed (K1 demoted from headline roster)
- Issue 4 (K4+K5 §7.1 row → SUPP): ~280 words freed
- Issue 5 (K7 §7.1 row → SUPP + §7.9 bullet delete + §7.2 line 743 + line 652): ~150 words freed
- Issue 6 (R5b conditional §3.2 + §7.1): +30 words
- Issue 7 (Cell-ID + R6 Kanzi → LineageFlow): ~10 words net change
- Issue 8 (subsumed by 3, 4, 5): 0 words net
- Issue 9 (data migration): 0 words (data only)

**Net Wave 306 trim:** ~960 words freed (per Wave 305 §6 line 150 "drop ~530 words from §7 — defer K1 to supplementary" + 430 additional from K4+K5/K7 demotion).

**Combined with Wave 303 D1-D6 RESOLUTION trim:** ~1700 words from §6 deletion + ~960 words from Wave 306 = **~2660 words freed total**. Net paper length target: 36027 − 2660 = ~33367 words pre-D3-fresh-write; after D3 fresh-write §2 Related Work (~700) + §8 Reproducibility (~600) + §11 Conclusion (~250) = ~34917 words (still over 7700 target, requires D3 trim path execution per Wave 305 §6).

---

## 12. Dependency Graph + Execution Order

The 9 issues are NOT all independent — Issue 8 is subsumed by Issues 3+4+5; Issue 1 fixes cascade into Issue 6 R5b conditional framing; Issue 7 is mechanical (independent of 1-6 + 8-9).

**Recommended execution order (after user D0 sign-off):**

1. **Issue 9 first** (data migration — foundation for all paper edits): 3 hours
   - 9.2.1 K1 (5 min) → 9.2.2 K4+K5 (10 min) → 9.2.3 K7 (10 min) → 9.2.4 R1 (20 min) → 9.2.5 R5c (20 min) → 9.2.6 R6 (10 min) → 9.2.7 R5b boundary (30 min) → 9.2.8 R5b byte-stable (5 min) → 9.2.9 ablation (20 min)
2. **Issue 1** (R2 §3.3 + §7.1 + §3.3 line 333): 10 min
3. **Issue 2** (R3 §7.1 row 3 caveat): 10 min
4. **Issue 6** (R5b §3.2 + §7.1 conditional boundary): 30 min
5. **Issue 3** (K1 p_bonf 0.054 → 0.5676 + K-level family + 5 audit-doc edits): 30 min
6. **Issue 4** (K4+K5 §7.1 → SUPP + abstract metric re-assignment): 30 min
7. **Issue 5** (K7 §7.1 → SUPP + §7.9 bullet delete + §7.2 lines 743, 652): 60 min
8. **Issue 7** (Cell-ID R4 → R5a + R6 Kanzi → LineageFlow + abstract K4/K5 metric): 60 min
9. **Issue 8** (subsumed by 3+4+5 — verify position moves applied): 0 min

**Total:** ~3.7 hours for Issues 1-7 + 9 (assuming user D0 signs off Wave 268 strict-clean break).

---

## 13. Cross-Reference Index

For each fix, the cross-references:

| Issue | Primary paper edit | Cross-doc propagation |
|---|---|---|
| 1 (R2) | `docs/drafts/paper-flat-flattened.md` §3.3 line 319 + line 333 + §7.1 line 641 | `docs/CLAIMS.md` line 3012; `docs/CONSOLIDATED_RESULTS.md` line 8334 |
| 2 (R3) | `docs/drafts/paper-flat-flattened.md` §7.1 line 642 | (none beyond §7.11 audit-doc fingerprint at line 738) |
| 3 (K1) | `docs/drafts/paper-flat-flattened.md` §3.2 line 215 + §7.1 line 647 + §7.4 line 717 + §7.10 line 748 | `docs/audit/wave280-p-k1-sweep-result.md` lines 26/198/217/273/387; `docs/CLAIMS.md` line 3012; `docs/paper-draft.md` lines 1444/2956; `docs/baseline-audit-report.md` line 7154 |
| 4 (K4+K5) | `docs/drafts/paper-flat-flattened.md` §7.1 line 648 + abstract lines 19/60 | `docs/CLAIMS.md` line 3012; `docs/CONSOLIDATED_RESULTS.md` §15.x K2 row |
| 5 (K7) | `docs/drafts/paper-flat-flattened.md` §7.1 line 650 + §7.9 line 718 + §7.2 lines 743/652 | `docs/CLAIMS.md` line 3012; `docs/CONSOLIDATED_RESULTS.md` §15.x K7 row; `docs/audit/wave280-p-k7-sweep-result.md` |
| 6 (R5b) | `docs/drafts/paper-flat-flattened.md` §3.2 line 322 + §3.6 line 386 + §3.3 line 312 + §7.1 line 644 | (none beyond Wave 305 §4 paste-ready block) |
| 7 (Cell-ID + abstract) | `docs/drafts/paper-flat-flattened.md` abstract lines 19/60 + §7.1 line 646 + §7.1 line 630 enumeration | `docs/headline-evidence/README.md` line 20; `docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/SOURCE.md` (rename to `r5a_2d_two_moons_w2_postcd70821/`); `docs/CLAIMS.md` lines 3040/3012/3086 |
| 8 (Position) | (subsumed by 3+4+5) | (subsumed) |
| 9 (Data migration) | (none — data files only) | `verification_outputs/wave280-p-{k1,k4k5,k7,r1,r5c,r6}/` + `verification_outputs/wave286-r5b-boundary/` + `verification_outputs/wave296-p7-r5b-byte-stable/` + `verification_outputs/wave302-p5-ablation/` |

---

## 14. Verification (5-Gate Baseline)

After all Wave 306 fixes applied, the 5-gate baseline must remain PASS:

1. **D.4 30/30 byte-stability:** `python3 -m pytest tests/test_d4_regression_vectors.py -q` → 30 passed
2. **ruff 0 lint:** `ruff check adaptive_reflow/ tests/ scripts/ tools/` → All checks passed
3. **mkdocs strict 0 warnings:** `mkdocs build --strict` → exit_code=0
4. **claims no drift:** `python3 tools/check_claims_consistency.py` → 61 active / 0 provisional / 2 deprecated
5. **vendored / data NOT touched (ADDITIVE only):** `git diff --stat -- vendored/ data/` → empty; `verification_outputs/` modifications are additive (`git add -f verification_outputs/...` to override `.gitignore:64`)

---

## 15. STOP MARKER

**AGENT WAITS FOR USER AUTHORIZATION BEFORE ANY DESTRUCTIVE EDIT.**

This plan is READ-ONLY planning artifact. No edits to `paper-flat-flattened.md`, no /tmp → verification_outputs/ moves, no CLAIMS.md or audit-doc edits will be performed until user text authorization is received.

**Executed edits:** 0 (Plan only).

**Awaiting user auth:** per Issue:
- Issue 1: 3 paper edits (requiresUserAuth=true) + 2 cross-doc edits (requiresUserAuth=true for CLAIMS.md; CONSOLIDATED_RESULTS.md could be deferred)
- Issue 2: 1 paper edit (requiresUserAuth=true)
- Issue 3: 4 paper edits + 4 audit-doc edits (requiresUserAuth=true) = 8 total
- Issue 4: 2 paper edits + 2 cross-doc edits (requiresUserAuth=true) = 4 total
- Issue 5: 5 paper edits + 3 cross-doc edits (requiresUserAuth=true) = 8 total
- Issue 6: 4 paper edits (requiresUserAuth=true) = 4 total
- Issue 7: 3 paper edits (requiresUserAuth=true) + 3 cross-doc edits (requiresUserAuth=false for headline-evidence rename; requiresUserAuth=true for CLAIMS.md) = 4-6 total
- Issue 8: subsumed (0 standalone)
- Issue 9: 9 data migrations (requiresUserAuth=true per Wave 268) = 9 total

**Total awaitingUserAuth count:** ~42 fix lines, condensed to ~10 user-action items (consolidate Issues 1-7 into a single user sign-off on the paper-text edit package; Issue 9 is a separate user sign-off on the data-migration package).

**Recommendation for user D0 sign-off (2-3h):**
1. Confirm Issues 1-7 paper-edit package (~7 hours of agent work; gated on user auth)
2. Authorize Issue 9 data-migration package (~3 hours of agent work)
3. (Optional) confirm Issues 1-9 audit-doc cross-propagation (~1 hour of agent work)
4. (Optional) confirm Wave 306 word budget trim path (~1 hour of agent work)

After user signs off, the workflow agent executes Issues 1-9 in the order specified in §12 without further user review except at the 3 explicit boundary points (D3 cleanness check per Wave 303 plan, D5 final sign-off, D7 ScholarOne upload click).

> **AGENT WAITS FOR USER AUTHORIZATION BEFORE ANY DESTRUCTIVE EDIT.**
>
> This document is a PLANNING artifact — no edits to `paper-flat-flattened.md`, no /tmp → verification_outputs/ moves, no audit-doc edits will be performed until user text authorization is received.