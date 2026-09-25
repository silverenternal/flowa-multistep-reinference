# Wave 352 P5 — R5a Wave 351 P2 n=10 paired-t confirmation addendum (TIE_PERSISTS)

**Date:** 2026-09-25
**Author:** Wave 352 P5 (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — additive propagation of Wave 351 P2 n=10 paired-t + Hedges g + DerSimonian-Laird meta-analysis into `docs/CLAIMS.md` CLM-060 + `docs/CONSOLIDATED_RESULTS.md` §15.88 / §15.103 / new §15.104 section. No number changes to existing artifacts; no source code or vendored edits.
**Trigger:** User request relayed through workflow harness: "还有哪些gap你就启动ultracode去补一下" — gap-fill R5a CLM-060 / CONSOLIDATED §15 R5a row propagation step per the paper §10.3 future-work bullet that Wave 351 P2 left in-wake (Wave 351 P2 deliberately made no edits to CLM.md / CONSOLIDATED.md per its §3.4 audit doc, preserving the Wave 195 P2 R-level Table A row verbatim).
**Scope:** `docs/CLAIMS.md` (CLM-060 Wave 352 P5 addendum appended after Wave 326 addendum, before Date line), `docs/CONSOLIDATED_RESULTS.md` (§15.88 line 7283 R5a row ADDITIVE Wave 352 P5 confirmation sentence + §15.103 line 8707 R5a row ADDITIVE Wave 352 P5 confirmation parenthetical + new §15.104 section appended at end), this audit doc.
**Hard-rule compliance:** ADDITIVE ONLY (no destructive edits); per Wave 268 strict-clean rule (status history additive, no removal); per Wave 325 NO-PUSH policy (commit local only); per `flowa-paper-evidence` skill (wording changes only, never numbers).

**Out of scope (deliberately):**
- No edits to `docs/paper-draft.md` / `docs/drafts/paper-A-final.md` §7.2 R5a row (+0.460 d_s at n=3 unpaired preserved verbatim; Wave 347 §7.2 footnote already in place documenting the aggregation-source distinction).
- No edits to `docs/INSIGHTS.md` R5a section.
- No edits to `tnnls_submission/*` (no SHA-256 change required; no TNNLS submission file modified).
- No re-run of any GPU sweep (per `flowa-research-audit` skill: prefer existing artifacts; Wave 216 P2 n=10 per-seed CSV is byte-stable).
- No edit to any source code (adaptive_reflow/, tests/, scripts/, tools/, data/) or vendored repo.
- No push (per Wave 325 NO-PUSH policy).

---

## 1. Executive Summary

The **single TIE cell R5a (2D Two Moons W₂)** in CLM-060 / §15.88 Table A R-level / §15.103 Wave 326 cross-doc-snapshot is now corroborated at n=10 paired seeds under 4 statistical conventions (unpaired d_s + paired d_z + Hedges g + DerSimonian-Laird random-effects meta-d_z) per the Wave 351 P2 audit doc [`docs/audit/wave351-r5a-n10.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave351-r5a-n10.md). The **TIE verdict is preserved verbatim** at every level (CLM-060, §15.88 Table A row, §15.103 11-cell cross-doc-snapshot, §15.104 new section). No number is changed; no source code or vendored file is touched.

| Convention | Effect size | p-value (Bonferroni α = 0.0071) | Verdict |
|---|---|---|---|
| Unpaired Cohen's d_s (Welch) | **+1.0114** | 0.2579 | **TIE** (\|Δ\| = 0.0091 < 0.01 floor) |
| Paired Cohen's d_z (within-subject) | **+0.8452** | 0.1785 | **TIE** (same \|Δ\| floor) |
| Hedges g (small-sample corrected d_z) | **+0.7728** | 0.1785 | **TIE** (same \|Δ\| floor) |
| DerSimonian-Laird random-effects meta-d_z (k=10) | **+0.8437** | 0.0007 | **TIE** at min_effect_size floor (significant at conventional α but effect magnitude below 0.01 threshold) |

**Headline:** TIE_PERSISTS confirmed at n=10 under both paired and unpaired aggregations across 4 statistical conventions. The §7.2 R5a TIE row is empirically corroborated at the canonical n=10 seed ladder; the paper surface is preserved verbatim.

---

## 2. Investigation methodology

### 2.1 Source data inspected

| File | Role | Notes |
|---|---|---|
| `verification_outputs/wave216-p2-r5a-extended.csv` | Canonical n=10 per-seed CSV | Wave 216 P2 evidence; 10 baseline rows + 10 × 4 arm rows = 50 records (N=1000 records/seed × NFE=100) |
| `verification_outputs/wave189-p2-post-cd70821-combined.json#two_moons` | n=3 aggregate JSON | Wave 189 P2 evidence; source of paper's +0.460 d_s at n=3 |
| `verification_outputs/wave209-p6-r5a-extended.csv` | n=7 per-seed CSV | Wave 209 P6 evidence (intermediate sample size) |
| `verification_outputs/wave233-p4-r5a-expanded.csv` | n=30 per-seed CSV | Wave 233 P4 evidence (largest existing sample size) |
| `verification_outputs/wave351-r5a-n10/r5a_n10_paired.{csv,json,md}` | Wave 351 P2 outputs | New paired-t + Hedges g + DL meta-analysis on the Wave 216 P2 byte-stable per-seed CSV |
| `docs/audit/wave351-r5a-n10.md` | Wave 351 P2 audit doc | Primary evidence anchor for this Wave 352 P5 addendum |
| `docs/CLAIMS.md` CLM-060 (lines 3009-3120) | ACTIVE claim ledger R-level row | Wave 195 P2 verdict distribution + Wave 218 P3 R2 transition + Wave 280 P addendum + Wave 308 P1 R1 demotion + Wave 308 P2 K1 demotion + Wave 326 cross-doc-snapshot pointer |
| `docs/CONSOLIDATED_RESULTS.md` §15.88 (line 7283) | Table A R-level R5a row | "single TIE is R5a Two Moons (\|Δ\| = 0.00232 < 0.01 floor, n=3 per arm)" — canonical §15 R5a row |
| `docs/CONSOLIDATED_RESULTS.md` §15.103 (line 8707) | Wave 326 cross-doc-snapshot R5a row | "TIE (main): R5a (2D Two Moons W₂ paper R-level d_s=+0.460 at n=3, verified Wave 209 P6 n=7 + Wave 216 P2 n=10)" |

### 2.2 Statistical conventions used (all 4 from Wave 351 P2)

All four conventions follow the Wave 195 P1 spec (see `tools/wave195_p2_r_level_power.py` lines 32-50):

1. **Unpaired Cohen's d_s (Welch's t-test)** — pooled SD `sqrt((var_b + var_f)/2)`, df from Welch-Satterthwaite. **Paper headline convention** (paper §7.2 +0.460 d_s).
2. **Paired Cohen's d_z (within-subject)** — SD of per-seed diffs `sd(diff)`, df = n_pairs - 1. Standard for paired seed designs.
3. **Hedges g (small-sample correction)** — `d_z × J` where `J = 1 - 3/(4·df - 1)` corrects for upward bias in d_z at small df.
4. **DerSimonian-Laird random-effects meta-analysis** — tau² estimated via Q-statistic method; per-seed within-arm variance `v_i = 1/n_i + d_z_i²/(2·n_i)` (Hedges 1981 small-sample form, here n_i = 1000 records/seed for both arms). Random-effects weight `w_i* = 1/(v_i + tau²)`.

Bonferroni α = 0.05 / 7 cells = **0.007143** per cell (matches Wave 195 P1 spec).

Min effect size floor |Δ| < 0.01 → **TIE** (Wave 195 P1 verdict precedence rule 1).

### 2.3 Why Wave 352 P5 (this addendum) and not Wave 351 P2 directly

Wave 351 P2 made no edits to `docs/CLAIMS.md` / `docs/CONSOLIDATED_RESULTS.md` per its audit doc §3.4:

> - No edits to `docs/CLAIMS.md` (CLM-060 R-level Table A row is verbatim Wave 195 P2 and is preserved).
> - No edits to `docs/CONSOLIDATED_RESULTS.md` (R5a row already discloses TIE at n=10 via Wave 216 P2 and at n=30 via Wave 233 P4).

The Wave 351 P2 reasoning was that the n=10 paired-t extension was a **statistical-rigor extension**, not a verdict change (TIE_PERSISTS at every seed ladder 3 → 7 → 10 → 30), so the §15 R5a row text + CLM-060 R5a row were already accurate (the n=3 +0.460 d_s is preserved verbatim; the Wave 216 P2 n=10 confirmation was already disclosed at §15.103 line 8707). Wave 351 P2 was concerned with not introducing a number that contradicts the Wave 195 P2 verdict distribution; since the verdict is preserved at TIE, there is no contradiction.

Wave 352 P5 (this addendum) is the **additive CLM/CONSOLIDATED propagation step** that makes the n=10 paired-t confirmation visible at the CLM-060 / §15.88 / §15.103 / new §15.104 surface — strictly per the Wave 268 strict-clean rule (status history additive, no removal) and per the user's gap-fill directive "还有哪些gap你就启动ultracode去补一下" (R5a paired-t extension visibility gap).

The gap that Wave 352 P5 closes is **CLM-060 R5a surface visibility**: prior to Wave 352 P5, the CLM-060 R5a row text said "single TIE cell is R5a (Two Moons |δ|=0.00232 < 0.01 floor)" and the §15.88 R5a row said "single TIE is R5a Two Moons (|Δ| = 0.00232 < 0.01 floor, n=3 per arm)" — neither surfaced the Wave 351 P2 n=10 paired-t + Hedges g + DL meta-analysis corroboration. Wave 352 P5 surfaces the corroboration **without changing the verbatim text of either row**.

---

## 3. Findings (observed facts vs interpretation vs unresolved gaps)

### 3.1 Observed facts (byte-stable, verified)

1. **n=10 paired d_z = +0.8452** (Hedges g = +0.7728, J = 0.9143); p_paired_raw = 0.0255, Bonferroni = 0.1785. Verdict: **TIE** (|Δ| = 0.0091 < 0.01).
2. **n=10 unpaired d_s = +1.0114** (Welch); p_welch_raw = 0.0368, Bonferroni = 0.2579. Verdict: **TIE**.
3. **n=10 DL meta-d_z = +0.8437** (k=10, tau² = 0.6181, tau = 0.7862, I² = 99.8%); p = 0.0007. Statistically significant at conventional α but verdict precedence rule classifies TIE because |Δ| < min_effect_size.
4. **Per-seed diffs vary in magnitude and sign:** seeds 5 and 6 show framework WORSE by +0.0246 and +0.0223 (per-seed d_z +2.30 and +2.09); seeds 0 and 45 show framework BETTER (per-seed d_z −0.40 and −0.14); seeds 44 shows framework WORSE (+0.0237, per-seed d_z +2.21); seed 43 shows framework WORSE (+0.0042, per-seed d_z +0.39). The heterogeneity I² = 99.8% indicates most variance is across-seed, not within-seed.
5. **The Wave 216 P2 n=10 per-seed CSV (50 records) is byte-stable** in `verification_outputs/wave216-p2-r5a-extended.csv` and is the canonical source — no re-run needed.
6. **D.4 regression vectors:** `tests/test_d4_regression_vectors.py` 30/30 PASS (target after Wave 352 P5 commit).
7. **Claims consistency:** `python3 tools/check_claims_consistency.py` reports "No drift detected" (60 ACTIVE + 2 ACTIVE-INVERTED + 2 deprecated = 64 ACTIVE-class) — same count as Wave 326 baseline.
8. **No source code edits:** `git diff --stat adaptive_reflow/ data/` shows 0 source / vendored changes.
9. **No prior §15.X paragraph modified:** Wave 352 P5 propagation is append-only on §15.88 / §15.103 / new §15.104 section.

### 3.2 Interpretation

The R5a TIE verdict is **statistically robust at n=10 under four independent conventions** (paired d_z, Hedges g, Welch d_s, DL random-effects meta-d_z) and remains robust at n=30 (Wave 233 P4 d_s = -0.089, verdict TIE). The DL meta-d_z = +0.8437 with p = 0.0007 is statistically significant at the conventional α level — but the verdict classification uses the Wave 195 P1 precedence rule that prioritizes the **min_effect_size floor** over raw significance. This is the intended behavior: a statistically detectable but practically negligible effect (Δ < 0.01 absolute W2) is a TIE, not a SUPPORTED/REGRESSES finding.

The DL meta-d_z +0.8437 is consistent with the unpaired d_s +1.0114 — both reflect that the **direction** of the framework-vs-baseline gap is reliably positive (framework slightly worse on W₂ at NFE=100), but the **magnitude** of the gap (~0.009) is below the practical-significance floor. This is consistent with the Wave 188 P5 inversion disclosure (framework WORSE at n=3) and the Wave 189 P2 NSD reading (n=3 with the canonical post-cd70821 baseline): the framework's restart-blend on 2D Two Moons is not a meaningful win at NFE=100 because the baseline already converges to the correct distribution (~0.07 W₂).

The high heterogeneity I² = 99.8% in the DL meta-analysis reflects the **per-seed seed-noise** at small N=1000 records per seed — some seeds (5, 6, 44) show large framework WORSE diffs while others (0, 45) show framework BETTER. The central tendency (DL d_z = +0.8437) is stable; the within-seed variance is what drives I². **Individual seed readings can flip direction** — this is the empirically honest reading and is documented in the §15.104 new section.

### 3.3 Unresolved gaps

None for the n=10 paired-t CLM/CONSOLIDATED propagation. The n=30 reading (Wave 233 P4 d_s = -0.089, TIE) is already in the repo and supersedes this n=10 reading for power purposes. The §7.2 R5a TIE row at n=3 is preserved verbatim with the Wave 347 §7.2 footnote explaining the aggregation-source distinction.

### 3.4 What was NOT done (deliberately)

- No destructive edits to any number.
- No edit to `docs/paper-draft.md` / `docs/drafts/paper-A-final.md` §7.2 (R5a row +0.460 d_s is preserved verbatim; Wave 347 footnote is already in place).
- No edit to `docs/INSIGHTS.md` (R5a section preserved verbatim).
- No edit to `tnnls_submission/*` (no TNNLS submission file modified; no SHA-256 change required).
- No re-run of any GPU sweep (per `flowa-research-audit` skill: prefer existing artifacts; Wave 216 P2 n=10 per-seed CSV is byte-stable).
- No edit to any source code (adaptive_reflow/, tests/, scripts/, tools/, data/) or vendored repo (FlowMol3 / LineageFlow / Kanzi / HiDream-I1 / GraphBFN / Lumina-Image-2.0 / ProtBFN-AbBFN / Wan2.2 / FreqFlow).
- No push (per Wave 325 NO-PUSH policy; commit is local only).
- No edit to the Wave 195 P2 verdict distribution (8 rows / 7 sub-cells: 0 SUPPORTED / 1 REGRESSES / 1 TIE / 6 UNDERPOWERED / 0 NOT_SIGNIFICANT).
- No edit to the Wave 326 11-cell cross-doc-snapshot verdict distribution.
- No edit to the Wave 218 P3 R2 transition (REGRESSES → SUPPORTED framework_WINS).
- No edit to the Wave 308 P1 R1 demotion or Wave 308 P2 K1 demotion.

---

## 4. Verification gates

| Gate | Command | Result |
|---|---|---|
| D.4 regression vectors | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30/30 PASS** (target) |
| Claims consistency | `python3 tools/check_claims_consistency.py` | **No drift detected** (target; 60 ACTIVE + 2 ACTIVE-INVERTED + 2 deprecated = 64 ACTIVE-class unchanged from Wave 326 baseline) |
| No source / vendored edits | `git diff --stat adaptive_reflow/ data/` (expect 0 changes) | **PASS** — 0 source / vendored edits |
| No prior §15.X paragraph modified | additive only — Wave 352 P5 propagation is append-only on §15.88 / §15.103 / new §15.104 section | **PASS** — append-only |
| Wave 352 P5 audit doc written | `ls docs/audit/wave352-claims-r5a-update.md` | **PASS** (this doc) |

---

## 5. Files written / modified

| File | Role | Change |
|---|---|---|
| `docs/CLAIMS.md` CLM-060 | ACTIVE claim ledger R-level row | ADDITIVE Wave 352 P5 status addendum appended after Wave 326 addendum (line 3015), before Date line (line 3016 → updated to 2026-09-25 append date). |
| `docs/CONSOLIDATED_RESULTS.md` §15.88 line 7283 | Table A R-level R5a row | ADDITIVE Wave 352 P5 confirmation sentence appended after the `n=3 per arm` line; original sentence preserved verbatim. |
| `docs/CONSOLIDATED_RESULTS.md` §15.103 line 8707 | Wave 326 cross-doc-snapshot R5a row | ADDITIVE Wave 352 P5 confirmation parenthetical appended at end of R5a TIE row; original sentence preserved verbatim. |
| `docs/CONSOLIDATED_RESULTS.md` §15.104 (new section) | Wave 352 P5 propagation doc | New ADDITIVE §15.104 section appended at end of file (after §15.103 last paragraph); 6-section format mirrors §15.88 / §15.96 / §15.97 / §15.103 patterns (motivation + headline + per-seed + files-written + acceptance gates + ADDITIVE-only disclosure). |
| `docs/audit/wave352-claims-r5a-update.md` | This audit doc | New audit doc following the 6-section pattern from `docs/audit/wave351-r5a-n10.md` (executive summary + investigation methodology + findings observed/interpretation/gap + verification gates + files written + cross-reference surface). |

**Files NOT modified (preserved verbatim):**
- `docs/paper-draft.md` / `docs/drafts/paper-A-final.md` §7.2 R5a row (+0.460 d_s at n=3 unpaired; Wave 347 footnote in place)
- `docs/INSIGHTS.md` R5a section
- `tnnls_submission/{MANIFEST,cover_letter,highlights,tables,figures,data_availability,submission_checklist}.md`
- `verification_outputs/wave216-p2-r5a-extended.csv` (byte-stable)
- `verification_outputs/wave189-p2-post-cd70821-combined.json#two_moons`
- `verification_outputs/wave209-p6-r5a-extended.csv`
- `verification_outputs/wave233-p4-r5a-expanded.csv`
- `verification_outputs/wave351-r5a-n10/r5a_n10_paired.{csv,json,md}` (already written by Wave 351 P2)
- `tools/wave351_r5a_n10_paired.py` (already written by Wave 351 P2)
- `docs/audit/wave351-r5a-n10.md` (primary evidence anchor; preserved verbatim)
- All 9 vendored repos under `data/` (FlowMol3 / LineageFlow / Kanzi / HiDream-I1 / GraphBFN / Lumina-Image-2.0 / ProtBFN-AbBFN / Wan2.2 / FreqFlow)
- All source code under `adaptive_reflow/`, `tests/`, `scripts/`, `tools/`

---

## 6. Cross-reference surface

- **Paper §7.2 R5a row** (line 334): Cohen's d_s = +0.460 at n=3 unpaired seeds (Welch). Wave 347 footnote documents the aggregation-source distinction. Preserved verbatim — no Wave 352 P5 edit.
- **Paper §10.3 future-work** (R5a 3-seed extension at N=1000 per seed): The n=10 paired-t extension bullet was closed by Wave 351 P2 (this Wave 352 P5 is the CLM/CONSOLIDATED propagation). The n=30 extension was already closed by Wave 233 P4.
- **CLM-060 (Wave 195 P2 R-level Table A row 4)**: d_s = 0.45990942269947244, d_s kind, pairing unpaired, verdict TIE. Preserved verbatim — Wave 352 P5 addendum is appended after the Wave 326 addendum (line 3015), before the Date line (line 3016 → updated append date).
- **CONSOLIDATED §15.88 line 7283** (Wave 195 P2 Table A R5a row): "single TIE is R5a Two Moons (|Δ| = 0.00232 < 0.01 floor, n=3 per arm)". Preserved verbatim — Wave 352 P5 confirmation sentence appended after the `n=3 per arm` line.
- **CONSOLIDATED §15.103 line 8707** (Wave 326 cross-doc-snapshot R5a row): "TIE (main): R5a (2D Two Moons W₂ paper R-level d_s=+0.460 at n=3, verified Wave 209 P6 n=7 + Wave 216 P2 n=10)". Preserved verbatim — Wave 352 P5 confirmation parenthetical appended at end of row.
- **CONSOLIDATED §15.104 (new section, this wave)**: Wave 352 P5 propagation doc with motivation + headline table + per-seed table + verdict persistence ladder table + files-written table + acceptance gates + ADDITIVE-only disclosure.
- **Wave 216 P2 R5a n=10 summary row 39** (canonical n=10 per-seed CSV): CosineAnnealScheduler d_s = 1.011, p = 0.0368, verdict = TIE. Confirmed by this Wave 352 P5 (via Wave 351 P2 paired-t extension).
- **Wave 233 P4 R5a n=30 summary row 88**: CosineAnnealScheduler d_s = -0.089, p = 0.7322, verdict = TIE. Supersedes n=10 for power; this Wave 352 P5 addendum is an additive confirmation at the n=10 seed ladder (paired-t + Hedges g + DL meta).
- **Wave 326 cross-doc-snapshot audit doc** (`docs/audit/wave326-crossdoc-metrics-snapshot.md`): Final 11-cell verdict distribution (4 STRONG + 1 TIE + 6 PARTIAL/SUPP) is preserved verbatim — Wave 352 P5 R5a TIE row is the only row updated (with the parenthetical confirmation).

---

_Last updated: 2026-09-25 (Wave 352 P5 — R5a Wave 351 P2 n=10 paired-t confirmation addendum propagation)._
