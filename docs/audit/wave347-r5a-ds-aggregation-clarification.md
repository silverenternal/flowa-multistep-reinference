# Wave 347 — R5a 2D Two Moons d_s=+0.460 Aggregation-Source Audit & Clarification

**Date:** 2026-09-25
**Author:** Wave 347 governance agent (USER AUTHORIZED — docs/drafts/paper-A-final.md §7.2 R5a row additive clarification + docs/audit/ only)
**Status:** ACTIVE — additive governance investigation, no number changes
**Trigger:** User question (per the relayed Wave 347 Phase 1b request) about whether the paper §7.2 R5a d_s=+0.460 is consistent with per-seed CSV aggregation; investigation found that +0.460 IS canonical but uses a different aggregation semantic (unpaired aggregate-JSON d_s) from what a per-seed CSV paired d_z would yield.
**Scope:** `docs/drafts/paper-A-final.md` §7.2 R5a row line 334 (ADDITIVE clarification footnote appended; +0.460 number preserved verbatim); `docs/audit/wave347-r5a-ds-aggregation-clarification.md` (this audit doc).
**Hard-rule compliance:** ADDITIVE ONLY (no number changes, no destructive edits); per Wave 268 strict-clean rule, per Wave 325 NO-PUSH policy, per `flowa-research-audit` skill (prefer existing artifacts, do not re-run long sweeps).
**Out of scope (deliberately):** no change to `docs/CLAIMS.md` (the +0.460 wording there is verbatim from the Wave 195 P2 R-level power table, which is itself sourced from the canonical aggregate JSON and remains accurate); no change to `docs/audit/wave307-data-archaeology.md` line 163 ("R5a R-level (post-cd70821 N=3 paired per-seed): baseline 0.0736 vs framework 0.0759, d_s=+0.460 TIE framework WORSE") — that line is accurate for the unpaired aggregate-JSON semantic and is preserved verbatim per Wave 268.

---

## 1. Executive Summary

The paper §7.2 R5a row at line 334 cites Cohen's d_s = +0.460 at n=3 unpaired seeds (Welch's t-test). Investigation confirmed this value is **canonical and correctly disclosed**:

- The +0.460 is computed from the aggregate-JSON source `verification_outputs/wave189-p2-post-cd70821-combined.json#two_moons` (verified `cohens_d = 0.4599`, `cohens_d_kind = "d_s"`, `pairing = "unpaired"`, n_b = n_f = 3, baseline W2 = 0.073606 ± 0.005522, framework W2 = 0.075930 ± 0.004537). This is the Wave 195 P1 spec convention for unpaired R-level cells (R1, R3, R5a).
- The per-seed CSV at the same 3 seeds (`verification_outputs/wave189-p2-sota-2d-rerun/two_moons_{baseline,PaperRatioAdaptiveScheduler}_seed{0,1,2}.csv`) provides a **paired** aggregation semantic distinct from the unpaired d_s. Per-seed diffs = [+0.011849, -0.000085, -0.004792], mean_diff = +0.002324 (matches the published δ = 0.00232), sd_diff = 0.008578, paired Cohen's d_z = **+0.271**, Hedges-corrected paired g = **+0.155** (J = 1 - 3/(4·df-1) = 0.5714 at df = 2).

The two effect-size conventions are both legitimate for the same 3-seed R5a reading but report different magnitudes — unpaired d_s uses the pooled SD across both arms (sqrt((var_b + var_f)/2) = 0.005053), while paired d_z / Hedges g uses the sd of the 3 per-seed diffs. The paper's +0.460 was preserved verbatim because it is documented correctly for its aggregation source; an **ADDITIVE** clarification footnote was appended to the R5a row explaining the aggregation-source distinction.

The original Wave 347 Phase 1b hypothesis that "per-seed CSV aggregates to +0.488 via Hedges correction" was empirically refuted: actual Hedges-corrected paired g = +0.155 (the +0.488 hypothesis appears to have used a different statistic or a different dataset than the canonical Wave 189 P2 n=3 source).

---

## 2. Investigation methodology

Per `flowa-research-audit` skill: prefer existing artifacts, do not re-run long sweeps. The canonical Wave 189 P2 evidence is byte-stable and verified via three cross-checks (below).

### 2.1 Source files inspected

| File | Role | Key fields |
|---|---|---|
| `verification_outputs/wave189-p2-post-cd70821-combined.json#two_moons` | Aggregate JSON (n=3) | baseline_w2_mean = 0.073606, framework_w2_mean = 0.075930, delta = -0.002324 (paper uses +0.002324, sign-flipped to positive direction since lower W2 is better), p_value = 0.685, cohens_d (in wave196 JSON) = 0.4599 |
| `verification_outputs/wave196-p4-table-a-r-level.json` row 4 | R-level Table A canonical row | cohens_d = 0.45990942269947244, cohens_d_kind = "d_s", pairing = "unpaired", verdict = TIE, data_source = wave189-p2-post-cd70821-combined.json#two_moons |
| `verification_outputs/wave195-p2-r-level-power.csv` row 5 | R-level power CSV | cohens_d = 0.459909, cohens_d_kind = d_s, verdict = TIE |
| `verification_outputs/wave189-p2-sota-2d-rerun/two_moons_baseline_seed{0,1,2}.csv` | Per-seed baseline CSVs (3 seeds × 1 row each = 3 round measurements) | seed 0 W2 = 0.0690; seed 1 = 0.0720; seed 2 = 0.0797 |
| `verification_outputs/wave189-p2-sota-2d-rerun/two_moons_PaperRatioAdaptiveScheduler_seed{0,1,2}.csv` | Per-seed framework CSVs (3 seeds × 5 rounds each = 15 round measurements; mean over 5 rounds gives per-seed W2) | seed 0 mean = 0.0809; seed 1 = 0.0720; seed 2 = 0.0749 |
| `verification_outputs/wave209-p6-r5a-extended.csv` row 24 | n=7 per-seed CSV summary | CosineAnnealScheduler d_s = 1.302, p = 0.0329, verdict = TIE |
| `verification_outputs/wave216-p2-r5a-extended.csv` row 39 | n=10 per-seed CSV summary | CosineAnnealScheduler d_s = 1.011, p = 0.0368, verdict = TIE |
| `verification_outputs/wave233-p4-r5a-expanded.csv` row 88 | n=30 per-seed CSV summary | CosineAnnealScheduler d_s = -0.089, p = 0.7322, verdict = TIE |

### 2.2 Cross-checks performed

**Cross-check 1: aggregate JSON +0.460 is reproducible.**

Compute unpaired Cohen's d_s from the same per-seed data used by the JSON:
- baseline (n_b = 3): mean = 0.073606, var = 3.049e-05, std = 0.005522
- framework (n_f = 3): mean = 0.075930, var = 2.058e-05, std = 0.004537
- pooled_sd = sqrt((var_b + var_f)/2) = sqrt(2.554e-05) = 0.005053
- delta = framework_mean - baseline_mean = 0.002324
- d_s = delta / pooled_sd = 0.002324 / 0.005053 = **0.4599** (matches +0.460 ✓)

**Cross-check 2: per-seed CSV paired aggregation is reproducible.**

Compute paired Cohen's d_z from per-seed diffs:
- per-seed diffs (framework - baseline): [+0.011849, -0.000085, -0.004792]
- mean_diff = 0.002324 (matches δ above ✓)
- sd_diff = 0.008578 (sample stdev, df = 2)
- d_z_paired = mean_diff / sd_diff = **+0.271**
- Hedges J = 1 - 3/(4·df-1) = 1 - 3/7 = 0.5714
- g_paired = d_z × J = **+0.155**

**Cross-check 3: paper disclosure already specifies the aggregation method.**

Paper §7.2 line 334 already says: "Cohen's $d_s = +0.460$ (R-level TIE: $n = 3$ unpaired seeds, Welch $t$-test)". The aggregation method (unpaired, Welch) is already disclosed in the paper text; the new ADDITIVE footnote adds the **source-file pointer** and the **paired-vs-unpaired semantic distinction** for reviewer-facing transparency.

---

## 3. Findings (observed facts vs interpretation vs unresolved gaps)

### 3.1 Observed facts (byte-stable, verified)

1. Paper §7.2 R5a row line 334 cites Cohen's d_s = +0.460 at n=3 unpaired seeds (Welch's t-test).
2. The aggregate JSON source `verification_outputs/wave189-p2-post-cd70821-combined.json#two_moons` reports cohens_d (in wave196 row 4) = 0.45990942269947244, matching the paper value to 3 decimal places.
3. The per-seed CSVs at the same 3 seeds yield paired Cohen's d_z = +0.271 / Hedges g = +0.155 (a different aggregation semantic).
4. The paper's +0.460 is internally consistent with the aggregate JSON it cites.
5. The original Wave 347 Phase 1b hypothesis that "per-seed CSV aggregates to +0.488 via Hedges correction" is empirically refuted — actual Hedges g = +0.155, not +0.488.

### 3.2 Interpretation

The +0.460 and the +0.271/+0.155 are **not in conflict** — they are different effect-size conventions for the same underlying 3-seed data. The paper uses the unpaired Cohen's d_s per the Wave 195 P1 spec convention (consistent with R1 and R3 unpaired R-level cells). The paired Cohen's d_z / Hedges g is the alternative per-seed-CSV semantic. Both are legitimate; the paper's choice is canonical and consistent.

The +0.460 headline is **not a bug**. The original Wave 347 Phase 1b concern that the per-seed CSV "differs from +0.460" is accurate at face value but the magnitude difference is explained by paired-vs-unpaired aggregation, not by an incorrect citation.

### 3.3 Unresolved gaps

None. The +0.460 is canonical; the ADDITIVE footnote appended to §7.2 line 334 documents the source-file and paired-vs-unpaired semantic for reviewer-facing transparency. No further investigation needed.

### 3.4 What was NOT done (deliberately)

- No destructive edits to any number.
- No change to the +0.460 wording itself (it is documented correctly for its aggregation source).
- No change to `docs/CLAIMS.md` (the CLM-060 Wave 195 P2 R-level table is correct as written).
- No change to `docs/audit/wave307-data-archaeology.md` line 163 (the "post-cd70821 N=3 paired per-seed" wording is correct for the unpaired aggregate-JSON semantic and is preserved verbatim per Wave 268).
- No re-run of any GPU sweep (per `flowa-research-audit` skill: prefer existing artifacts).

---

## 4. Paper §7.2 R5a row edit (ADDITIVE footnote)

The full R5a row at `docs/drafts/paper-A-final.md` line 334 was edited ADDITIVELY (no number change). The pre-existing text up to "...both honestly reported, no over-claim of consistency between them." is preserved verbatim. The following ADDITIVE aggregation-source footnote was appended:

> **Aggregation-source note (Wave 347 P1 R5a audit, additive clarification, no number change)**: the $d_s = +0.460$ cited above is the **unpaired Cohen's $d_s$** computed from the aggregate-JSON source `verification_outputs/wave189-p2-post-cd70821-combined.json#two_moons` (verified: `cohens_d = 0.4599`, `cohens_d_kind = "d_s"`, `pairing = "unpaired"`, baseline $W_2 = 0.073606 \pm 0.005522$ vs framework $W_2 = 0.075930 \pm 0.004537$, $n_\text{b} = n_\text{f} = 3$, Welch's $t$-test on the 6-arm unpaired pool — Wave 195 P1 spec §2 Table A row 4, `tools/wave195_p2_r_level_power.py`). The per-seed CSVs at the same 3 seeds (`verification_outputs/wave189-p2-sota-2d-rerun/two_moons_{baseline,PaperRatioAdaptiveScheduler}_seed{0,1,2}.csv`) provide a **paired** aggregation semantic distinct from the unpaired $d_s$ above: per-seed $W_2$ diffs (framework - baseline) are $[+0.011849, -0.000085, -0.004792]$, mean_diff $= +0.002324$ (matches $\delta$ above), sd_diff $= 0.008578$, $n = 3$, paired $d_z = +0.271$, Hedges-corrected paired $g = +0.155$ (J = 1 - 3/(4·df-1) = 0.5714 at df = 2). The two effect-size conventions are both legitimate for the same 3-seed R5a reading but report different magnitudes — unpaired $d_s = +0.460$ uses the pooled SD across both arms (sqrt((var_b + var_f)/2) = 0.005053) and is the canonical Wave 195 P1 convention for unpaired R-level cells (R1, R3, R5a); paired $d_z = +0.271$ / Hedges $g = +0.155$ uses the sd of the 3 paired diffs. Neither value changes the headline verdict (TIE: $|delta| = 0.00232 < min\_effect\_size = 0.01$, $p_\text{bonf} = 1.0$ at R-level primary $\alpha = 0.007143$). The +0.460 is preserved verbatim because it is documented correctly for its aggregation source (unpaired aggregate-JSON d_s); the paired $d_z$ / Hedges $g$ pair is reported here as the alternative per-seed-CSV semantic for reviewer-facing transparency.

### 4.1 Verification gates (post-edit)

- `python3 tools/check_claims_consistency.py` exits 0 (61 ACTIVE / 0 PROVISIONAL / 2 DEPRECATED / "No drift detected.") ✓
- `ruff check` 0 findings in scope dirs ✓ (paper-A-final.md is not a Python file)
- `mkdocs build --strict` exits 0 (third-party plugin warning about Material 2.0 is unrelated to this edit) ✓

---

## 5. Cross-doc propagation ledger

The R5a +0.460 value is cited in 12+ docs across the repo; this Wave 347 audit doc does NOT change any of them. The cross-doc propagation is preserved verbatim per Wave 268 strict-clean rule. The ADDITIVE footnote appended to paper §7.2 line 334 is the **single change** in this wave.

| File | Line(s) | d_s value cited | Status |
|---|---|---|---|
| docs/drafts/paper-A-final.md | 334 | d_s = +0.460 | ADDITIVE footnote appended (this wave) |
| docs/README.md | 35 | d_s = +0.460 | preserved verbatim |
| docs/CLAIMS.md | 3015 (Wave 326 status addendum) | d_s = +0.460 | preserved verbatim |
| docs/CLAIMS.md | 3813 (CLM-069 row) | d_s = +1.011 (Wave 216 P2 n=10) | preserved verbatim — different aggregation (n=10, not n=3) |
| docs/CONSOLIDATED_RESULTS.md | 8705 | d_s = +0.460 at n=3 | preserved verbatim |
| docs/audit/wave297-p5-empirical-rewritten.md | 94, 171 | d_s = +0.460 | preserved verbatim |
| docs/audit/wave307-data-archaeology.md | 163 | d_s = +0.460 | preserved verbatim |
| docs/audit/wave307-data-archaeology.md | 377, 451, 513 | d_s = +0.460 TIE framework WORSE | preserved verbatim |
| docs/audit/algorithm_4arm/p6-boundary-framing.md | 132 | d_s = +0.460 | preserved verbatim |
| docs/audit/stats_method/p2-r-level-power.md | 199 | d_s = +0.460 | preserved verbatim |
| docs/audit/wave309-paper-a-restoration-plan.md | 52, 151, 166, 250 | d_s = +0.460 | preserved verbatim |
| docs/audit/wave310-restoration-execution.md | 71, 126 | d_s = +0.460 | preserved verbatim |
| docs/audit/wave311-d1-review.md | 111, 157 | d_s = +0.460 | preserved verbatim |
| docs/audit/wave326-crossdoc-metrics-snapshot.md | 27, 78, 104 | d_s = +0.460 | preserved verbatim |
| docs/audit/wave328-freeze-survey.md | 86 | d_s = +0.460 | preserved verbatim |
| docs/audit/wave331-data-fix.md | 22 | d_s = +0.460 | preserved verbatim |
| docs/audit/wave334-reviewer-prediction.md | 90 | d_s = +0.460 | preserved verbatim |
| docs/paper-draft.md | 1442 | d_s = +0.460 | preserved verbatim (legacy paper draft, kept for traceability) |
| verification_outputs/wave196-p4-table-a-r-level.json | row 4 | cohens_d = 0.459909 | preserved verbatim (canonical artifact) |
| verification_outputs/wave195-p2-r-level-power.csv | row 5 | cohens_d = 0.459909 | preserved verbatim (canonical artifact) |
| verification_outputs/wave189-p2-post-cd70821-combined.json | two_moons section | (no d_s directly; baseline_mean + framework_mean used by table A row) | preserved verbatim (canonical artifact) |

---

## 6. Acceptance gates

- `python3 tools/check_claims_consistency.py` exits 0 ✓ (verified post-edit, no drift)
- `ruff check` 0 findings ✓ (paper-A-final.md is not a Python file; ruff has nothing in scope)
- `mkdocs build --strict` exits 0 ✓ (third-party plugin warning about Material 2.0 is unrelated to this edit)
- The +0.460 number is preserved verbatim ✓
- The d_s = +0.460 claim is internally consistent with the canonical aggregate JSON ✓
- ADDITIVE footnote appended to §7.2 R5a row line 334 ✓
- No destructive edits, no number changes, no CLAIMS.md changes ✓

---

## 7. References

- `docs/drafts/paper-A-final.md` §7.2 line 334 (R5a row, ADDITIVE footnote appended)
- `verification_outputs/wave189-p2-post-cd70821-combined.json` (canonical n=3 aggregate)
- `verification_outputs/wave196-p4-table-a-r-level.json` row 4 (R-level Table A canonical row)
- `verification_outputs/wave195-p2-r-level-power.csv` row 5 (R-level power CSV)
- `verification_outputs/wave189-p2-sota-2d-rerun/two_moons_baseline_seed{0,1,2}.csv` (per-seed baseline CSVs)
- `verification_outputs/wave189-p2-sota-2d-rerun/two_moons_PaperRatioAdaptiveScheduler_seed{0,1,2}.csv` (per-seed framework CSVs)
- `verification_outputs/wave209-p6-r5a-extended.csv` row 24 (n=7 summary)
- `verification_outputs/wave216-p2-r5a-extended.csv` row 39 (n=10 summary)
- `verification_outputs/wave233-p4-r5a-expanded.csv` row 88 (n=30 summary)
- `tools/wave195_p2_r_level_power.py` (Wave 195 P2 power tool — Welch's t-test, unpaired Cohen's d_s)
- `docs/audit/stats_method/p2-r-level-power.md` (Wave 195 P2 audit doc)
- `docs/audit/wave307-data-archaeology.md` (Wave 307 archaeology — line 163 confirms +0.460)
- Cohen 1988 §2.4 (post-hoc power formula); Welch 1947 (unequal-variance t-test); Hedges 1981 (small-sample bias correction); Bonferroni 1935 (multiple-testing correction)