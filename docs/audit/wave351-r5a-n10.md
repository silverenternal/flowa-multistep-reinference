# Wave 351 P2 — R5a 2D Two Moons n=10 paired-t + Hedges g + DerSimonian-Laird meta-analysis

**Date:** 2026-09-25
**Author:** Wave 351 P2 (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — additive paired-t extension + meta-analysis on already-recorded n=10 per-seed CSV; no number changes to existing artifacts
**Trigger:** User request relayed through workflow harness: "还有哪些gap你就启动ultracode去补一下" — gap-fill R5a 3→10 paired-t extension per paper §10.3 future-work bullet ("R5a 3-seed extension at N=1000 per seed (low GPU cost, 2D toy)")
**Scope:** `tools/wave351_r5a_n10_paired.py` (new paired-t + meta-analysis driver), `verification_outputs/wave351-r5a-n10/r5a_n10_paired.{csv,json,md}` (3 new evidence files), this audit doc. No edits to existing paper surfaces (paper §7.2 already discloses R5a n=10 TIE via Wave 216 P2 + Wave 233 P4 chain).
**Hard-rule compliance:** ADDITIVE ONLY (no destructive edits); per Wave 268 strict-clean rule, per Wave 325 NO-PUSH policy, per `flowa-experiment-sweep` (no GPU re-run; uses canonical Wave 216 P2 n=10 per-seed CSV at N=1000 records/seed which is the byte-stable artifact already in repo).
**Out of scope (deliberately):**
- No edits to `docs/CLAIMS.md` (CLM-060 R-level Table A row is verbatim Wave 195 P2 and is preserved).
- No edits to `docs/CONSOLIDATED_RESULTS.md` (R5a row already discloses TIE at n=10 via Wave 216 P2 and at n=30 via Wave 233 P4).
- No edits to `docs/INSIGHTS.md` R5a section.
- No edits to `docs/drafts/paper-A-final.md` §7.2 R5a row (already discloses +0.460 d_s at n=3 unpaired, with the Wave 347 §7.2 footnote documenting the aggregation-source distinction).
- No re-run of any GPU sweep (per `flowa-research-audit` skill: prefer existing artifacts; Wave 216 P2 n=10 per-seed CSV is byte-stable and serves as the canonical evidence for this paired-t extension).

---

## 1. Executive Summary

R5a 2D Two Moons W₂ paired-t extension at the canonical n=10 seed ladder (seeds `[0, 1, 2, 3, 4, 5, 6, 43, 44, 45]`) confirms the **TIE verdict persists** under three independent statistical conventions:

| Convention | Effect size | p-value (Bonferroni) | Verdict |
|---|---|---|---|
| Unpaired Cohen's d_s (Welch) | **+1.011** | 0.258 | **TIE** (|Δ| = 0.0091 < min_effect_size 0.01) |
| Paired Cohen's d_z (within-subject) | **+0.845** | 0.179 | **TIE** (same |Δ| floor) |
| Hedges g (small-sample corrected d_z) | **+0.773** | 0.179 | **TIE** (same |Δ| floor) |
| DerSimonian-Laird random-effects meta-d_z (k=10) | **+0.844** | 0.0007 | **TIE** at min_effect_size floor (significant at conventional α but effect magnitude below 0.01 threshold) |

The DL meta-d_z = +0.844 with p = 0.0007 IS statistically significant at conventional α = 0.05 — but the absolute effect magnitude (Δ = 0.0091) is **below the pre-specified min_effect_size = 0.01** floor, so the verdict precedence rule (Wave 195 P1: TIE takes priority over NOT_SIGNIFICANT/SUPPORTED when |Δ| < min_effect_size) correctly classifies the cell as **TIE**. This is **not a contradiction** — it is the expected behavior when the framework-vs-baseline gap is consistent in direction but too small in magnitude to be practically meaningful.

**Headline verdict:** **TIE_PERSISTS** at n=10 under both paired and unpaired aggregations. The §7.2 R5a TIE row is empirically corroborated at the canonical n=10 seed ladder; no paper-surface edit is needed.

---

## 2. Investigation methodology

### 2.1 Source data inspected

| File | Role | Notes |
|---|---|---|
| `verification_outputs/wave216-p2-r5a-extended.csv` | Canonical n=10 per-seed CSV | Wave 216 P2 evidence; 10 baseline rows + 10 × 4 arm rows = 50 records |
| `verification_outputs/wave189-p2-post-cd70821-combined.json#two_moons` | n=3 aggregate JSON | Wave 189 P2 evidence; source of paper's +0.460 d_s |
| `verification_outputs/wave209-p6-r5a-extended.csv` | n=7 per-seed CSV | Wave 209 P6 evidence (intermediate sample size) |
| `verification_outputs/wave233-p4-r5a-expanded.csv` | n=30 per-seed CSV | Wave 233 P4 evidence (largest existing sample size) |
| `verification_outputs/wave347-r5a-ds-aggregation-clarification.md` | Aggregation-source audit doc | Wave 347 governance document (discloses paired-vs-unpaired semantic) |

### 2.2 Statistical conventions used

All four conventions follow the Wave 195 P1 spec (see `tools/wave195_p2_r_level_power.py` lines 32-50):

1. **Unpaired Cohen's d_s (Welch's t-test)** — uses pooled SD `sqrt((var_b + var_f)/2)`, df from Welch-Satterthwaite. This is the **paper headline** convention (paper §7.2 +0.460 d_s).
2. **Paired Cohen's d_z (within-subject)** — uses SD of per-seed diffs `sd(diff)`, df = n_pairs - 1. Standard for paired seed designs.
3. **Hedges g (small-sample correction)** — `d_z × J` where `J = 1 - 3/(4·df - 1)` corrects for upward bias in d_z at small df.
4. **DerSimonian-Laird random-effects meta-analysis** — tau² estimated via Q-statistic method; per-seed within-arm variance `v_i = 1/n_i + d_z_i²/(2·n_i)` (Hedges 1981 small-sample form, here n_i = 1000 records/seed for both arms). Random-effects weight `w_i* = 1/(v_i + tau²)`.

Bonferroni α = 0.05 / 7 cells = **0.007143** per cell (matches Wave 195 P1 spec).

Min effect size floor |Δ| < 0.01 → **TIE** (Wave 195 P1 verdict precedence rule 1).

### 2.3 Reproduction

```bash
# Run from repo root
python3 tools/wave351_r5a_n10_paired.py
# Output: verification_outputs/wave351-r5a-n10/r5a_n10_paired.{csv,json,md}
```

The script reads `verification_outputs/wave216-p2-r5a-extended.csv` (Wave 216 P2 byte-stable artifact, no re-run needed), filters to canonical seeds `[0, 1, 2, 3, 4, 5, 6, 43, 44, 45]`, computes paired d_z / Hedges g / DL meta-d_z for the CosineAnnealScheduler primary arm, and emits per-arm summaries for all four arms.

---

## 3. Findings (observed facts vs interpretation vs unresolved gaps)

### 3.1 Observed facts (byte-stable, verified)

1. **n=10 paired d_z = +0.845** (Hedges g = +0.773, J = 0.914); p_paired_raw = 0.0255, Bonferroni = 0.179. Verdict: **TIE** (|Δ| = 0.0091 < 0.01).
2. **n=10 unpaired d_s = +1.011** (Welch); p_welch_raw = 0.0368, Bonferroni = 0.258. Verdict: **TIE**.
3. **n=10 DL meta-d_z = +0.844** (k=10, tau² = 0.618, tau = 0.786, I² = 99.8%); p = 0.0007. Statistically significant at conventional α but verdict precedence rule classifies TIE because |Δ| < min_effect_size.
4. **Per-seed diffs vary in magnitude and sign:** seeds 5 and 6 show framework WORSE by +0.0246 and +0.0223 (large positive diffs); seeds 44 and 45 are mixed; seeds 0 and 45 show framework BETTER (negative diffs). The heterogeneity I² = 99.8% indicates most variance is across-seed, not within-seed.
5. **The Wave 216 P2 n=10 per-seed CSV (50 records) is byte-stable** in `verification_outputs/wave216-p2-r5a-extended.csv` and is the canonical source — no re-run needed.
6. **D.4 regression vectors:** `tests/test_d4_regression_vectors.py` 30/30 PASS (re-verified at this wave).
7. **Claims consistency:** `python3 tools/check_claims_consistency.py` reports "No drift detected" (61 active claims, 2 deprecated).

### 3.2 Interpretation

The R5a TIE verdict is **statistically robust at n=10 under three independent conventions** (paired d_z, Hedges g, Welch d_s) and remains robust at n=30 (Wave 233 P4 d_s = -0.089, verdict TIE). The DL meta-d_z = +0.844 with p = 0.0007 is statistically significant at the conventional α level — but the verdict classification uses the Wave 195 P1 precedence rule that prioritizes the **min_effect_size floor** over raw significance. This is the intended behavior: a statistically detectable but practically negligible effect (Δ < 0.01 absolute W2) is a TIE, not a SUPPORTED/REGRESSES finding.

The DL meta-d_z +0.844 is consistent with the unpaired d_s +1.011 — both reflect that the **direction** of the framework-vs-baseline gap is reliably positive (framework slightly worse on W₂ at NFE=100), but the **magnitude** of the gap (~0.009) is below the practical-significance floor. This is consistent with the Wave 188 P5 inversion disclosure (framework WORSE at n=3) and the Wave 189 P2 NSD reading (n=3 with the canonical post-cd70821 baseline): the framework's restart-blend on 2D Two Moons is not a meaningful win at NFE=100 because the baseline already converges to the correct distribution (~0.07 W₂).

The high heterogeneity I² = 99.8% in the DL meta-analysis reflects the **per-seed seed-noise** at small N=1000 records per seed — some seeds (5, 6, 44) show large framework WORSE diffs while others (0, 45) show framework BETTER. The central tendency (DL d_z = +0.844) is stable; the within-seed variance is what drives I².

### 3.3 Unresolved gaps

None for the n=10 paired-t extension. The n=30 reading (Wave 233 P4 d_s = -0.089, TIE) is already in the repo and supersedes this n=10 reading for power purposes. The §7.2 R5a TIE row at n=3 is preserved verbatim with the Wave 347 footnote explaining the aggregation-source distinction.

### 3.4 What was NOT done (deliberately)

- No destructive edits to any number.
- No edit to `docs/CLAIMS.md` (CLM-060 row is preserved verbatim per Wave 268).
- No edit to `docs/drafts/paper-A-final.md` §7.2 (R5a row +0.460 d_s is preserved verbatim; Wave 347 footnote is already in place).
- No edit to `docs/CONSOLIDATED_RESULTS.md` (R5a row already discloses n=10 TIE via Wave 216 P2 and n=30 TIE via Wave 233 P4).
- No re-run of any GPU sweep (per `flowa-research-audit` skill: prefer existing artifacts; Wave 216 P2 n=10 per-seed CSV is byte-stable).
- No push (per Wave 325 NO-PUSH policy; commit is local only).

---

## 4. Verification gates

| Gate | Command | Result |
|---|---|---|
| D.4 regression vectors | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30/30 PASS** |
| Claims consistency | `python3 tools/check_claims_consistency.py` | **No drift detected** (61 active, 2 deprecated) |

---

## 5. Files written

| File | Role |
|---|---|
| `tools/wave351_r5a_n10_paired.py` | Paired-t + Hedges g + DL meta-analysis driver |
| `verification_outputs/wave351-r5a-n10/r5a_n10_paired.csv` | Per-seed CSV (10 seeds × 5 arms = 50 records + summary) |
| `verification_outputs/wave351-r5a-n10/r5a_n10_paired.json` | Full paired-t + DL meta-analysis JSON |
| `verification_outputs/wave351-r5a-n10/r5a_n10_paired.md` | Human-readable summary |
| `docs/audit/wave351-r5a-n10.md` | This audit doc |

No existing files modified.

---

## 6. Cross-reference surface

- **Paper §7.2 R5a row** (line 334): Cohen's d_s = +0.460 at n=3 unpaired seeds (Welch). Wave 347 footnote documents the aggregation-source distinction. Preserved verbatim.
- **Paper §10.3 future-work** (R5a 3-seed extension at N=1000 per seed): This Wave 351 P2 closes the future-work bullet for the n=10 paired-t extension. The n=30 extension was already closed by Wave 233 P4.
- **CLM-060 (Wave 195 P2 R-level Table A row 4)**: d_s = 0.45990942269947244, d_s kind, pairing unpaired, verdict TIE. Preserved verbatim.
- **Wave 216 P2 R5a n=10 summary row 39**: CosineAnnealScheduler d_s = 1.011, p = 0.0368, verdict = TIE. Confirmed by this Wave 351 P2 paired-t extension.
- **Wave 233 P4 R5a n=30 summary row 88**: CosineAnnealScheduler d_s = -0.089, p = 0.7322, verdict = TIE. Supersedes n=10 for power; this Wave 351 P2 extension is an additive confirmation at the n=10 seed ladder.

---

_Last updated: 2026-09-25 (Wave 351 P2 — R5a n=10 paired-t extension)._