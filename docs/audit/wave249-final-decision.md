# Wave 249 Final Decision — 5 CLMs × Paper Integration

**Date:** 2026-09-22
**Branch:** main (HEAD `00aae73`)
**Scope:** Wave 249 P6 — single decision document consolidating the 5
Wave 249 audit docs (P1–P5) into a per-CLM go/no-go table, with cross-
CLM consistency summary, final recommendation, and verification gates.

**Source audits (read in full):**

- `docs/audit/wave249-p1-clm053-audit.md` (CLM-053 vs Wave 230 P2 4-arm)
- `docs/audit/wave249-p2-clm057-058-audit.md` (CLM-057 + CLM-058)
- `docs/audit/wave249-p3-clm054-audit.md` (CLM-054 hyperparameter envelope)
- `docs/audit/wave249-p4-clm062-wave191-audit.md` (CLM-062 12-cell + Wave 191 P3)
- `docs/audit/wave249-p5-cross-clm-consistency.md` (F1–F4 cross-CLM)

---

## 1. Per-CLM decision table

| CLM id | Verdict | Reason | Where to add | Wording adjustment |
|--------|---------|--------|--------------|---------------------|
| **CLM-053** | **NOT_OK** | Direction-consistent at every cell with Wave 230 P2, but Wave 230 P2's canonical verdict (2 SUPPORTED + 14 UNDERPOWERED at Bonferroni α=0.003125, df=299) supersedes CLM-053's "all 16 WINS" point-estimate framing (no formal test). Adding the "FlowA wins on all 16 cells" framing would re-introduce the Wave 229 P1 bootstrap-projection problem and conflict with the existing §3.6 Table 3.4 narrative. Only the per-token (FlowA) vs per-family (LeDiFlow) granularity insight survives — that belongs in §3.5 with explicit disclosure that Wave 230 P2 is UNDERPOWERED on the LeDiFlow cells. | n/a (not added) | n/a |
| **CLM-054** | **WORDING_ADJUST** | 17 perturbation cells (β_base × restart_min_nfe × nfe_ref × seed) on LineageFlow synthetic at NFE=100 are byte-stable to ~4dp on pLDDT and scPerplexity; seed axis is the load-bearing sensitivity axis (5-seed ensemble +0.96 pLDDT / −1.69 scPerplexity). The finding is a positive robustness result that supports the solver-agnostic + training-free headline. **Disjoint axes from tier-aware overfit concern** (CLM-054 sweeps non-tier-aware global scheduler constants; tier-aware overfit concerns `easy_factor` / `hard_intensity`). | §3 supplementary robustness paragraph after §3.5 (Option A from P3 audit §4.2) | Explicit honest disclosure: byte-stability conditional on LineageFlow synthetic + NFE=100 regime (kanzi adapter and NFE=10/500 not covered); tier-aware HPs (`easy_factor`, `hard_intensity`) addressed separately by Wave 245 P2 / Wave 246 P2 audits. Frame as "hyperparameter envelope negative control at the global-constant level", NOT as a tier-aware overfit response. |
| **CLM-057** | **WORDING_ADJUST** | Kanzi n=30 paired seeds confirms paper-quantity scheduler L2=0.459±0.014 vs cosine 97.97±3.24 (Cohen's d_z=−30.15 on L2 axis, d_z=+10.24 on entropy axis, both p<1e-300). PROVISIONAL flag already removed in Wave 214 P3 (byte-stability fix restored). **CLM-057 numbers are already in §3.5 paragraph 4** — the question is sign-convention consistency. | §3.5 main text (paragraph 4, preserve verbatim) | Fix `d = +10.24` sign convention: CLM-057 verbatim assigns d_z=+10.24 to the entropy axis and d_z=−30.15 to the L2 axis; the current §3.5 quote cites d=+10.24 on the L2 axis magnitude (sign-flipped convention). Either align with CLM-057 verbatim or explicitly note the sign convention. |
| **CLM-058** | **WORDING_ADJUST** | Cross-adapter Theorem-1 confirmation at n=30 paired seeds. Entropy axis Bonferroni-significant on BOTH adapters (kanzi d_z=+10.24 p<1e-4; lineageflow d_z=+0.642 p_bonf=0.00293 — both significant). L2 axis scale-dependent (kanzi d_z=−30.15; lineageflow d_z=+0.093 p=0.615 NULL because the field's natural scale ≈5 leaves the cosine arm nothing to over-perturb). **Enhances, not weakens** the Theorem-1-quantities-as-load-bearing headline with a scope qualifier. | §3.5 main text (NEW paragraph 5, after current CLM-057 paragraph) | Qualify "regulariser" with "where the cosine arm over-perturbs the latent" (kanzi 213× gentler) and add "posterior-shape sharpener universally (entropy axis Bonferroni-significant on both kanzi and LineageFlow at n=30)". Explicit honest disclosure that L2 regularisation is kanzi-specific. |
| **CLM-062** | **WORDING_ADJUST** | 12-cell Theorem-1 load-bearing per-cell power analysis (2 adapters × 3 arm comparisons × 2 axes), Bonferroni α=0.05/12=0.004167 per cell, n=30 paired seeds, verdict-precedence distribution is **1 SUPPORTED / 0 REGRESSES / 8 TIE / 3 UNDERPOWERED / 0 NOT_SIGNIFICANT**. Single SUPPORTED cell is C-K-L2-CvB (kanzi L2 cosine-vs-baseline, Cohen's d_z=−11.15, p_bonf=4.14e-31, Δ=−16.88). 3 UNDERPOWERED cells are kanzi × {L2-PvC, ΔS-PvC, ΔS-CvB} where observed d_z ∈ [10.24, 30.15] but post-hoc power at the 1.0 L2 / 0.01 ΔS practical floor is below 0.5. **Cherry-picking risk LOW**: full 12-cell matrix reported, decision-honest verdict precedence applied. | §3.5 main text (NEW paragraph 6, after CLM-058) | Name the 12-cell setup (2 adapters × 3 arm comparisons × 2 axes), Bonferroni correction (α=0.05/12=0.004167 per cell), full verdict distribution (1/0/8/3/0), single SUPPORTED cell (C-K-L2-CvB), and 3 UNDERPOWERED cells. Explain the n=30 paired design's budget ceiling honestly (post-hoc power at the practical floor is below 0.5 even when observed effect is 30×–100× the floor). Reconcile with CLM-057's C-K-DS-PvC framing (CLM-062 labels it UNDERPOWERED; CLM-057 reports observed d_z=+10.24 — both honest, complementary framings). |
| **Wave 191 P3 MNIST (CLM-059)** | **WORDING_ADJUST** | MNIST FM framework-vs-baseline sweep at N=1000, matched NFE=50 on smoke-materialized checkpoint (epochs=1, base_channels=8, max_train_images=6000, sha256=ded1fa70...); framework WINS −28.43% on best arm (Cohen's d_z=−13.18, Bonferroni p=3.95e-11). PROVISIONAL pending production-ckpt re-run (epochs=3, base_channels=16, full 60K images). **Production-ckpt rerun: NOT AVAILABLE** — PROVISIONAL carried forward verbatim from Wave 191 P3 through Wave 191 P5 to current HEAD. | §3.3 Table 3.2 R5c row (already integrated) | Add inline "PROVISIONAL" or "pending production-ckpt re-run" flag on the R5c row. Currently the PROVISIONAL status lives only in CLM-059 + CONSOLIDATED_RESULTS §15.87 + INSIGHTS §7.6 + paper-draft §10.42 limitations — NOT cited inline in §3.3 Table 3.2. |

---

## 2. Cross-CLM consistency summary

| Axis | Verdict |
|------|---------|
| **CLM-053 vs Wave 230 P2 4-arm** | Direction-consistent at every cell; NOT formally equivalent (CLM-053 has no formal test; Wave 230 P2 has strict Bonferroni at α=0.003125, df=299). Wave 230 P2 canonical verdict (2 SUPPORTED + 14 UNDERPOWERED) supersedes CLM-053's "all 16 WINS" framing. |
| **CLM-057 + CLM-058 narrative** | Both argue Theorem-1-quantities-as-load-bearing. CLM-058's L2 axis scale-dependent qualifier is a scope refinement (universal sharpener, kanzi-specific regulariser), NOT a contradiction. Load-bearing claim survives and is strengthened by CLM-058. |
| **CLM-054 vs tier-aware overfit** | Disjoint axes. CLM-054 sweeps non-tier-aware global scheduler constants (`β_base`, `restart_min_nfe`, `nfe_ref`); tier-aware overfit concerns `easy_tier_nfe_reduction_factor` × `hard_tier_nfe_intensity`. CLM-054 is a **hyperparameter envelope negative control at the global-constant level**, NOT a direct tier-aware overfit response. |
| **CLM-057 ∩ CLM-058** | CLM-058 includes the kanzi cells CLM-057 quotes. The two are **additive**, not contradictory. CLM-057 quotes one cell; CLM-058 reports that cell + lineageflow extension. |
| **CLM-058 ∩ CLM-062** | CLM-062's 12-cell matrix includes all cells CLM-058 quotes. CLM-058 is a **subset claim** of CLM-062's matrix (CLM-058 reports 4 cells: kanzi/lineageflow × {L2, ΔS} on paper-vs-cosine axis; CLM-062 reports all 12). |
| **CLM-057 ∩ CLM-062** | CLM-062 reports the C-K-DS-PvC cell (kanzi ΔS paper-vs-cosine, d_z=+10.24) — the SAME Cohen's d_z CLM-057 quotes. CLM-062 frames this as UNDERPOWERED (post-hoc power at the 1.0 L2 / 0.01 ΔS practical floor is below 0.5 even though the observed effect is 30× the floor); CLM-057 frames it as the headline load-bearing finding. These two framings are **decision-honest complementary** and must coexist when both are added to §3.5. |
| **Wave 191 P3 vs others** | Orthogonal (MNIST FM smoke ckpt is a different adapter + different claim axis from the Theorem-1 protein evidence). |

**No internal contradictions across the 5 CLMs.** All overlaps are additive or complementary after reconciliation. Pre-existing paper bugs to fix alongside integration (per P1 audit §5.3): `paper-flattened-draft.md` line 317 + line 319 Bonferroni-significance claims are inconsistent with Wave 230 P2.

---

## 3. Final recommendation

**Net outcome: 1 NOT_OK + 5 OK with wording adjustment. Wave 250 paper append is recommended with reduced scope (5 of 6 CLMs added, CLM-053 dropped).**

### 3.1 CLMs to add (5)

- **CLM-054** → §3 supplementary robustness paragraph (after §3.5)
- **CLM-057** → §3.5 paragraph 4 (verbatim, with sign-convention fix)
- **CLM-058** → §3.5 paragraph 5 (new, additive)
- **CLM-062** → §3.5 paragraph 6 (new, additive)
- **Wave 191 P3 MNIST (CLM-059)** → §3.3 Table 3.2 R5c row (inline PROVISIONAL flag)

### 3.2 CLMs to skip (1)

- **CLM-053** — NOT OK to add as a standalone claim; only the per-token-vs-per-family granularity insight can be added to §3.5 (with Wave 230 P2 UNDERPOWERED disclosure on LeDiFlow cells).

### 3.3 CLMs to delay

- None. All 5 OK-to-add CLMs are ready for Wave 250 paper integration with the wording adjustments specified in §1.

### 3.4 Recommended Wave 250 task ordering

1. Fix pre-existing bugs in `paper-flattened-draft.md` line 317 + 319 (replace incorrect Bonferroni-significance claims with honest 2 SUPPORTED + 14 UNDERPOWERED verdict distribution).
2. §3.5 paragraph 4 (CLM-057): preserve verbatim, fix `d = +10.24` sign convention.
3. §3.5 paragraph 5 (CLM-058, new): cross-adapter LineageFlow confirmation + scope qualifier.
4. §3.5 paragraph 6 (CLM-062, new): 12-cell Theorem 1 load-bearing power analysis.
5. §3 supplementary robustness paragraph after §3.5 (CLM-054): hyperparameter envelope negative control.
6. §3.3 Table 3.2 R5c row: add inline PROVISIONAL flag (Wave 191 P3).
7. 4-gate verify: D.4 30/30 PASS, mkdocs 0 warnings, claims_consistency no drift, abstract word count ≤ 250.

### 3.5 Wave numbers to strip on integration

When integrating to paper, replace wave-numbered references with paper-readable text:

- "Wave 182" → "5-arm comparison"
- "Wave 230" → "per-record paired-t 4-arm analysis"
- "Wave 186" → "hyperparameter envelope sensitivity analysis"
- "Wave 195" → "12-cell Theorem 1 load-bearing power analysis"
- "Wave 190" → "n=30 paired Theorem-1-quantities sweep"
- "Wave 191" → "MNIST FM smoke-checkpoint reading"
- "Wave 235" → "tier-aware HP grid search"
- "Wave 245" → "tier-aware overfit audit"
- "Wave 246" → "tier-aware overfit R1 audit"
- "Wave 214" → "byte-stability fix" (CLM-057 disclosure)
- "Wave 249" → drop entirely (this is the audit series; not a paper reference)

The `verification_outputs/wave*-p*-*.{csv,json}` filenames should be replaced with paper-readable references like "Table B (16-cell 4-arm analysis)" or "Table C (12-cell Theorem 1 power analysis)".

---

## 4. Verification gates

| # | Gate | Status | Output |
|---|------|--------|--------|
| 1 | D.4 byte-stable 30/30 PASS | PASS | see §4.1 |
| 2 | mkdocs 0 warnings | unchanged | (no source code touched) |
| 3 | claims_consistency no drift | PASS | see §4.2 |
| 4 | abstract word count ≤ 250 | unchanged | (no paper modifications) |
| 5 | 5 audit docs (P1–P5) read in full | PASS | all read; see source list above |
| 6 | per-CLM decision table | PASS | §1 |
| 7 | cross-CLM consistency summary | PASS | §2 |
| 8 | final recommendation enumerated | PASS | §3 |
| 9 | pre-existing paper bugs identified | PASS | line 317 + 319 (per P1 §5.3) |

### 4.1 D.4 byte-stable 30/30 PASS

Command:
```
timeout 30 .venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header 2>&1 | tail -3
```
Result: D.4 30/30 PASS (unchanged — no source code touched, only
audit doc additions).

### 4.2 claims_consistency no drift

Command:
```
python3 tools/check_claims_consistency.py 2>&1 | tail -3
```
Result: no drift (no claim text modified in `docs/CLAIMS.md` or
`docs/drafts/paper-flattened-draft.md`; only audit docs added).

### 4.3 Hard rules respected

- **DO NOT modify paper** — respected (audit doc only; no paper edit).
- **DO preserve D.4 30/30 PASS** — respected (no source code changes).
- **DO preserve mkdocs 0 warnings** — respected (no doc edits affecting mkdocs).
- **DO preserve claims consistency** — respected (no claim text changes).

---

## 5. Output JSON

```json
{
  "clm_053_decision": "NOT_OK",
  "clm_054_decision": "WORDING_ADJUST",
  "clm_057_decision": "WORDING_ADJUST",
  "clm_058_decision": "WORDING_ADJUST",
  "clm_062_decision": "WORDING_ADJUST",
  "wave_191_p3_decision": "WORDING_ADJUST",
  "n_decision_OK": 0,
  "n_decision_wording_adjust": 5,
  "n_decision_NOT_OK": 1,
  "d4_pass": true,
  "claims_consistency": "ok",
  "next_wave_recommendation": "Wave 250 paper append with 5 CLMs (drop CLM-053; add CLM-054, CLM-057, CLM-058, CLM-062, Wave 191 P3 with wording adjustments)",
  "audit_doc_path": "docs/audit/wave249-final-decision.md",
  "commit_sha": "<to be filled at commit time>"
}
```

---

## 6. Files added this phase

| Path | Description |
|------|-------------|
| `docs/audit/wave249-final-decision.md` | This decision doc (single source of truth for Wave 249 P6 outcome) |

No source code, paper draft, CLAIMS.md, or verification output modifications.

---

## 7. Status

**Wave 249 P6 complete.** Single decision document consolidates the 5
prior audit docs into a per-CLM go/no-go table:

- 1 CLM NOT OK to add (CLM-053, Wave 230 P2 supersedes).
- 5 CLMs OK to add with wording adjustment (CLM-054, CLM-057,
  CLM-058, CLM-062, Wave 191 P3 MNIST).

**Next wave:** Wave 250 paper append — apply the 5 wording-adjustment
adds in the order specified in §3.4, plus fix pre-existing bugs in
`paper-flattened-draft.md` line 317 + 319, plus 4-gate verify.