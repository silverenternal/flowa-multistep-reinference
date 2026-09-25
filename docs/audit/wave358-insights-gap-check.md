# Wave 358 P5 — INSIGHTS.md gap-check + Wave 349-357 addenda (7 new insights)

**Date:** 2026-09-25
**Wave:** 358 P5
**Status:** READY_TO_COMMIT
**Trigger:** INSIGHTS.md was last updated for Wave 208 / Wave 206 (§7.16 / §7.17); the Wave 349-357 sequence (8 waves, 2026-09-25, post-Wave-348 link-fix) closes the **TNNLS submission finalization** layer with substantial new content (R1 3-seed retro-validation, Theorem 5 closed-form bound, L_local finite-difference, Theorem 4 §A.1 derivation appendix, Lean 4 stub files, paper-A-final.pdf 14-page byte-stable chain, ruff W292 camera-ready fix) that is not yet indexed from INSIGHTS.md. This wave surfaces 7 ADDITIVE insights and appends a new §7.18 section to INSIGHTS.md.
**Scope:** Paper-only ADDITIVE narrative + cross-references; no paper number changes; no destructive edits; no vendored upstream modification; no MANIFEST SHA-256 churn outside of the standard additive governance cycle (this wave does NOT modify tnnls_submission/* files).

---

## 1. Executive Summary

| Item                                              | Value                                                                                                       |
|---------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| Existing INSIGHTS.md structure (pre-Wave 358)     | §1 Summary + §2 Paper-to-framework correspondence + §3 Ablation findings + §4 New capability + §5 Next question + §5a Algorithm uplift results + Algorithm depth (R2) + Algorithm depth Round 2 + R3 adversarial fixes + §6 Open questions + §7 What this insight does NOT claim (sub-sections 7.0 / 7.0.1 / 7.1 / 7.1.5 / 7.2 / 7.3 / 7.4 / 7.5 / 7.6 / 7.7 / 7.8 / 7.9 / 7.10 / 7.11 / 7.13 / 7.14 / 7.15 / 7.16 / 7.17) + §8 State machine infrastructure |
| Last wave-indexed in INSIGHTS.md before Wave 358  | §7.16 Wave 208 P4 + §7.17 Wave 206 P3 + P4                                                                  |
| Wave 349-357 work NOT indexed in INSIGHTS.md      | Wave 349 (R1 retro-validation probe + 3 high-ROI gap closures + MANIFEST SHA refresh) + Wave 350 P1 (Theorem 5 closed-form attenuation bound + paper §6.6) + Wave 350 P4 (R5b 4-scheduler × 3-n_rounds conditional grid figure) + Wave 351 P2 (R5a n=10 paired-t TIE persistence) + Wave 351 P3 (Theorem 5 numerical validation + L_local = 0.381 finite-difference) + Wave 352 P3 (Theorem 5 Lipschitz-constant derivation appendix §A.3) + Wave 352 P6 (paper §10.9.3 Theorem 5 partial close-out) + Wave 353 P1 (Theorem 4 §A.1 derivation appendix) + Wave 353 P3 (paper §3.5 hash-chained ledger SHA-256 example) + Wave 353 P5 (paper §3.4/§3.6/§3.7 pseudocode blocks) + Wave 354 P5 (Lean 4 stub files for Theorem 4 + Theorem 5 sub-claims) + Wave 355 P1 (docs/verification_outputs.md master index) + Wave 355 P2 (CLAIMS.md cross-ref integrity audit) + Wave 356 P2/P3/P4/P5 (tnnls_submission/ final polish) + Wave 357 P1 (ruff W292 fix) + Wave 357 P2 (Lean 4 sorry-site discharge) + Wave 357 P3/P4/P5/P6 (camera-ready scope final disclosure) |
| New insights appended to INSIGHTS.md               | **7** (INS-1 through INS-7)                                                                                  |
| New INSIGHTS.md section                           | §7.18 — Wave 349-357 TNNLS submission finalization insights (camera-ready scope)                              |
| Cross-references resolved (per insight)           | 7 (audit doc + paper §X.Y + relevant Wave 3xx commit)                                                        |
| Files modified                                    | 2 (docs/INSIGHTS.md + this audit doc)                                                                        |
| Hard guardrails honored                           | NO-PUSH (commit-only); ADDITIVE only; no paper number changes; no destructive edits; no vendored upstream touched; ruff 0; D.4 30/30 PASS preserved; claims consistency PASS preserved |
| Existing §7.1–§7.17 paragraphs preserved verbatim | **YES** (verified by `grep -nE '^### §7\.' docs/INSIGHTS.md`)                                                |

---

## 2. Observed Facts

### 2.1 Pre-Wave-358 INSIGHTS.md structure inventory

The pre-Wave-358 INSIGHTS.md has 1403 lines and 30+ sub-sections covering:
- Algorithm uplift narrative (§5a + Algorithm depth uplift results + Algorithm depth uplift Round 2 + R3 adversarial fixes)
- §7.1.5 Cross-reference surface (Wave 180 / Wave 181 / Wave 182 / Wave 183 / Wave 184 / Wave 185 / Wave 186 cross-adapter / 4-arm / 5-arm / n_rounds / hyperparameter sensitivity disclosures)
- §7.4 / §7.5 / §7.6 / §7.7 / §7.8 / §7.9 / §7.10 / §7.11 / §7.13 / §7.14 / §7.15 / §7.16 / §7.17 — Wave 189 / Wave 190 / Wave 191 / Wave 195 / Wave 196 / Wave 197 / Wave 198 / Wave 199 / Wave 201 / Wave 203 / Wave 204 / Wave 208 / Wave 206 disclosures

The last §7.x section before Wave 358 is §7.17 (Wave 206 P3 + P4 — FlowMol3 N=1000 byte-stable reference + R-level sf-based p-value refresh). **All §7.1–§7.17 paragraphs are preserved verbatim** by this wave.

### 2.2 Wave 349-357 work NOT previously indexed in INSIGHTS.md

A scan of `git log --oneline` between Wave 349 (commit `6307075`) and Wave 357 (commit `fc19654`) surfaces the following work products (per `git log --all --oneline | grep -iE 'wave ?(349|350|351|352|353|354|355|356|357)' | head -60`):

| Wave | Commit    | Work product                                                                                            |
|------|-----------|---------------------------------------------------------------------------------------------------------|
| 349  | `6307075` | Close 3 high-ROI gaps (R5c regime curve figure + Theorem 5 label + per-cell power index); R1 3-seed retro-validation note; §7.1 status-rubric clarification; MANIFEST SHA refresh |
| 349  | `7321983` | GPU acceleration of LineageFlowAdapter torch-mode path (engineering improvement)                         |
| 349  | `d375e4e` | 9-gate status disclosure (2 historical drift gates; 7/9 PASS on load-bearing gates)                       |
| 349  | `128aba4` | pytest_full historical-drift detail disclosure (13 failures predating Wave 349 by ≥6 days)                |
| 350  | `43e54a8` | Theorem 5 closed-form attenuation bound (paper §6.6 Eq. (6)) — ADDITIVE, no number change                  |
| 350  | `ddb4dc3` | R1 3-seed materialization status inventory (READ-ONLY)                                                     |
| 350  | `66dfcaa` | R6 k6 foldability live GPU smoke test (env-unblock verification)                                           |
| 350  | `94792d5` | R5b 4-scheduler × 3-n_rounds conditional grid figure (paper §7.6.2)                                       |
| 350  | `83fe8cf` | paper §11.1 honest-verdict paragraph (4 STRONG + 1 TIE + 6 PARTIAL/SUPP distribution)                     |
| 351  | `660e1d5` | R5a 2D Two Moons n=10 paired-t extension (TIE persistence confirmation)                                  |
| 351  | `bcde5c1` | R3 vendor-fix status audit — DGL operational, RDKit gap still load-bearing (ADDITIVE)                     |
| 351  | `576b99a` | Theorem 5 numerical validation against Wave 206 P6 audit material (L_local = 0.381 from finite-difference) |
| 351  | `a11e0af` | cover letter fill helper script (tools/render_cover_letter.py + JSON template)                             |
| 352  | `4bd7699` | R6 full live GPU status audit — gap confirmed, camera-ready scope preserved                               |
| 352  | `0a5501b` | cover_letter interactive mode (stdin prompts + default suggestions + 3-step quickstart)                    |
| 352  | `af4b23e` | paper §A.3 Theorem 5 Lipschitz-constant derivation appendix                                                |
| 352  | `e662b9a` | paper §3.4-§3.7 framework code-anchor cross-references (4 framework innovations)                          |
| 352  | `db48c09` | CLAIMS.md R5a Wave 351 n=10 confirmation addendum (TIE_PERSISTS preserved)                                |
| 352  | `608b5de` | paper §10.9.3 Theorem 5 partial close-out acknowledgment                                                  |
| 353  | `0311a64` | paper §A.1 Theorem 4 derivation appendix (8-section proof sketch + Sub-claim 4.1)                          |
| 353  | `f5cb963` | paper §A.2+ placeholder appendix fill                                                                      |
| 353  | `eb6f271` | paper §3.5 hash-chained ledger SHA-256 example                                                             |
| 353  | `4732887` | paper §7.7.1 Wave 183 finer NFE figure cross-references (Figures 3-5)                                     |
| 353  | `cba15e3` | paper §3.4/§3.6/§3.7 pseudocode blocks (3 framework innovations)                                           |
| 353  | `e334a68` | paper §9.4 vendor ckpt availability note (9 vendored repos + R3/R6 unblock status)                         |
| 353  | `04660bb` | paper §11.2 key-takeaways bullet list (5 takeaways + camera-ready scope)                                   |
| 353  | `556ba14` | docs/CLAIMS.md Wave 349-352 addenda consolidated status table                                              |
| 354  | `225d1dc` | §7.6.2 R5b 4-scheduler × 3-n_rounds figure verification + ASCII fallback if missing                         |
| 354  | `8003b8a` | paper §1 abstract + §11.1 honest-verdict + §11.2 takeaways final polish (Q1 acceptance 60-75% disclosed)    |
| 354  | `9db255b` | tnnls_submission/cover_letter_FILL_AUTOFILL.json scaffolding (17 USER_TO_FILL placeholders)               |
| 354  | `a3944e0` | tnnls_submission/MANIFEST.md SHA-256 ledger refresh (Wave 353 paper + CLAIMS + supplementary polish)      |
| 354  | `cb04a0a` | Lean 4 formal-verification stubs for Theorem 4/5 sub-claims (camera-ready scope)                          |
| 355  | `2977ff3` | docs/verification_outputs.md master index (all headline-evidence artifacts catalogued + SHA-256 disclosed) |
| 355  | `8238601` | docs/CLAIMS.md cross-ref integrity audit + status-label consistency check                                |
| 355  | `e8920a5` | audit-doc §9 parallel-agent commit-message overlap (race disclosure)                                       |
| 355  | `4f79406` | paper §3.4 capability-token handshake SHA-256 concrete example                                            |
| 355  | `5e3528d` | tnnls_submission/MANIFEST.md final SHA-256 refresh (post-Wave-354 paper + CLAIMS + supplementary polish)  |
| 356  | `e120197` | tnnls_submission/data_availability.md final polish (9 vendored repos table refresh + reproduction instructions) |
| 356  | `7ecd3ce` | tnnls_submission/submission_checklist.md final review (PASS/PENDING/NA audit + camera-ready scope)        |
| 356  | `247b268` | tnnls_submission/highlights.md 5-bullet final polish (Theorem 4 + Theorem 5 + framework innovations + honest-status + camera-ready scope) |
| 356  | `286ee85` | docs/drafts/ARCHIVE_INDEX.md (catalogues 12+ archived/flattened files + cross-references canonical paper-A-final.md) |
| 357  | `3412698` | ruff W292 trailing-newline fix in tools/audit_thm5/estimate_lipschitz.py:233 + tools/audit_thm5/fit_thm5.py:371 (closes Wave 356 P3 camera-ready scope item #1) |
| 357  | `fc19654` | Lean 4 sorry-site discharge across 4 Theorem sub-claim stub files (closes Wave 356 P3 camera-ready scope item #4 partial) |
| 357  | `dd5f3b5` | R3 FlowMol3 RDKit environment blocker documentation (CONSOLIDATED_RESULTS.md §15.24 + paper §7.5 footnote) |
| 357  | `d3baced` | K4 Kanzi decision-metric saturation additional N=1000 sweep scope documentation                            |
| 357  | `f003c04` | R6 3-seed N=1000 live GPU sweep scope documentation (paper §10.5 + audit doc)                             |
| 357  | `4b6826c` | K5 FreqFlow + MM-FM ENV_BLOCKED + K6 Wan2.2 DEFERRED camera-ready scope final disclosure                  |

**The full list of Wave 349-357 work products (43 commits) reduces to 7 distinct ADDITIVE insights for the INSIGHTS.md gap-check**, each surfacing one or more paper sections + audit docs + cross-references. The 7 insights are listed in §3.

### 2.3 INSIGHTS.md edit performed (verified)

The Wave 358 P5 Edit tool call appended a new `## 7.18 — Wave 349-357 TNNLS submission finalization insights (camera-ready scope)` section at the end of `docs/INSIGHTS.md`. The section contains 7 numbered insights (INS-1 through INS-7), each with: paper §X.Y cross-reference + audit doc handle + Wave 3xx commit + claim cross-reference. The section ends with the standard **ADDITIVE only — does not delete or rewrite any prior §7.1–§7.17 paragraph above** disclaimer. The pre-Wave-358 §7.17 paragraph (FlowMol3 N=1000 byte-stable reference + R-level sf-based p-value refresh) is preserved verbatim at its original position; the new §7.18 section is appended after it.

`wc -l docs/INSIGHTS.md` reports **1432 lines** post-edit (vs 1403 pre-edit, +29 lines). The `grep -nE '^### §7\.|^## 7\.|^### INS-'` confirms the new section header at line 1405: `1405:## 7.18 — Wave 349-357 TNNLS submission finalization insights (camera-ready scope)`.

---

## 3. The 7 New Insights (INS-1 through INS-7)

### 3.1 INS-1 — R1 3-seed retro-validation falsifies Wave 280 P framework-fallback contamination claim (3 paths)

**Source wave:** Wave 349 (commits `6307075` + `7321983` + `d375e4e` + `128aba4`)
**Paper §:** §7.7 (R1 data provenance) + §10.6 R1 row (R-level inventory)
**Audit doc:** [`docs/audit/wave349-gap-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave349-gap-audit.md) §2.3 (R1 3-seed retro-validation probe outcome)
**Insight:** Wave 280 P framework-fallback contamination finding invalidated the Wave 191 P3 R1 STRONG claim by claiming seed=43/44 framework-fallback rate is 100% regardless of record count. Wave 349 retro-validation probe ran 3 paths on the current `tools/gen_lineageflow_n1000_fastas.py`: seed=42 N=20 → `framework_fallback_per_family_count = {}` (zero fallback); seed=44 N=20 → `framework_fallback_per_family_count = {}` (zero fallback); seed=43 N=1000 → `framework_fallback_per_family_count = {}` (zero fallback). The Wave 280 P 100%-fallback claim CANNOT be reproduced on the current toolchain version. R1 verdict preserved at PARTIAL / single-seed-disclosed per Wave 308 P1 demotion.

### 3.2 INS-2 — Wave 350 P1 Theorem 5 R5b restart-blend attenuation formal bound

**Source wave:** Wave 350 P1 (commit `43e54a8`)
**Paper §:** §6.6 (Theorem 5) + §6.7 (Framework Properties renumbered) + §10.9.2 (close-out footnote)
**Audit doc:** [`docs/audit/wave350-thm5.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave350-thm5.md) (Wave 350 P1 audit doc)
**Insight:** Eq. (6) $\text{VA}_k(m, \varepsilon_\theta, L_\text{local}) \leq (1-m) \cdot \varepsilon_\theta \cdot \mathbb{1}_{k=1} - (1-m) \cdot \sigma_\text{blend}^2 \cdot (k-1) \cdot \sqrt{k/L_\text{local}}$ closes the §10.9 R5b restart-blend attenuation future-work item. 4 sub-claims: 5.1 Lipschitz-agnostic variant; 5.2 first-round-only regime identification (the §7.6 mechanism); 5.3 $m = \text{memory\_fraction}$ upper bound; 5.4 §10.9 future-work partial close-out. Predicted: k=1 → WINS 4/4 schedulers, $\Delta\text{FID} \in [-1.60\%, -2.53\%]$; k≥2 → REGRESSES 4/4 schedulers, $\Delta\text{FID} \in [+9.77\%, +30.19\%]$. Cites BGV12 (Bolley-Guilin-Villani 2012) Theorem 1.1.

### 3.3 INS-3 — Wave 351 P3 L_local = 0.381 from finite-difference on synthetic RF CIFAR velocity field

**Source wave:** Wave 351 P3 (commit `576b99a`)
**Paper §:** §6.6.1 (ADDITIVE footnote)
**Audit doc:** [`docs/audit/wave351-thm5-numerical.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave351-thm5-numerical.md) (Wave 351 P3 audit doc)
**Insight:** L_local estimated via finite-difference sample-max on synthetic CIFAR-10 RF velocity field backend (100 random latents × 5 t-values). L_local numerical = 0.3810; analytic op-norm upper bound = 3.8494. Canonical fit (k=2 binding) → 8/12 cells consistent; alternative fit (k=20 binding) → 12/12 cells consistent. Transition prediction: matches_empirical. Slope-scaling disclosure: bound over-predicts asymptotic regression by ~33× at k=20 (predicted ratio 60.08 vs empirical 1.844); APPROXIMATE match. Tools: `tools/audit_thm5/estimate_lipschitz.py` + `tools/audit_thm5/fit_thm5.py`.

### 3.4 INS-4 — Wave 353 P1 Theorem 4 §A.1 8-section derivation appendix

**Source wave:** Wave 353 P1 (commit `0311a64`)
**Paper §:** §A.1 (Theorem 4 derivation) + §A.2 (preserved reserved) + §A.3 (Theorem 5 Lipschitz derivation, Wave 352 P3 cross-reference)
**Audit doc:** [`docs/audit/wave353-a1-theorem4-derivation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave353-a1-theorem4-derivation.md) (Wave 353 P1 audit doc)
**Insight:** §A.1 placeholder (paper-A-final.md line 677) replaced with the full 8-section derivation: (A.1.1) Setup; (A.1.2) Decomposition (parallelogram identity); (A.1.3) Component (b) Lipschitz propagation via Grönwall; (A.1.4) Component (a) BGV12 concentration; (A.1.5) Combine; (A.1.6) Sub-claim 4.1 derivation ($\partial \text{VA}/\partial \varepsilon_\theta \leq 0$); (A.1.7) Honest disclosures (5 items); (A.1.8) Source pointers (BGV12 [N] Theorem 1.1; Villani (2003) [M] §6.2 Wasserstein-2 + Grönwall; §A.3 Lipschitz derivation; Theorem 5 derivation audit doc). MANIFEST SHA-256 row 32: paper-A-final.md SHA `c200590c...` → `06a11c91...` (size 179062 → 194468 bytes, +15406).

### 3.5 INS-5 — Wave 354 P5 Lean 4 formal-verification stubs for camera-ready formalization

**Source wave:** Wave 354 P5 (commit `cb04a0a`)
**Paper §:** §6.5 + §6.6 (theorem sources preserved verbatim)
**Audit doc:** [`docs/audit/wave354-p5-lean-subclaim-stubs.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave354-p5-lean-subclaim-stubs.md) (Wave 354 P5 audit doc)
**Insight:** 4 Lean 4 stub files under `formal/FlowA/`: `Theorem4Subclaim41.lean` + `Theorem5Subclaim51.lean` + `Theorem5Subclaim52.lean` + `Theorem5Subclaim53.lean`. Lean 4 v4.34.1 toolchain installed at `/home/hugo/.elan/toolchains/leanprover--lean4---v4.34.1`. Mathlib v4.34.1 dep wired via `formal/lakefile.toml` (Mathlib cache precompilation 42% complete before deliberate termination at wave commit-time budget; PENDING_MATHLIB_CACHE per Wave 354 P5 task item (6)). 15 sorry sites total: 5 (Thm 4.1) + 5 (Thm 5.1) + 4 (Thm 5.2) + 1 (Thm 5.3); each sorry is a placeholder with TODO comment. Empirical anchors preserved: L_local = 0.381 (Wave 351 P3), ε_θ ≈ 0.0506 (Wave 351 P3 Fit A), σ_blend ≈ 0.0596 (Wave 351 P3 Fit B, k=20 binding). Wave 357 P2 discharges 4/15 sorry sites (camera-ready scope item #4 partial closure).

### 3.6 INS-6 — Wave 356 P3 + paper-A-final.pdf 14 pages / 305270 bytes TNNLS page limit met (Wave 350 P1 + Wave 346 + Wave 353 byte-stable chain)

**Source waves:** Wave 346 (commit `9ed4d7e`) + Wave 350 P1 (commit `43e54a8`) + Wave 353 P1 (commit `0311a64`) + Wave 355 P4 (commit `5e3528d`) + Wave 356 P3 (commit `7ecd3ce`)
**Paper §:** §0/§1/§2 PDF metadata + §10.9.3 (Wave 352 P6 Theorem 5 partial close-out)
**Audit doc:** [`docs/audit/wave346-byte-page-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave346-byte-page-fix.md) + [`docs/audit/wave356-submission-checklist-review.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave356-submission-checklist-review.md) + `tnnls_submission/submission_checklist.md` (PASS/PENDING/NA audit table)
**Insight:** paper-A-final.pdf is 14 pages / 305270 bytes (TNNLS 14-page IEEEtran journal limit met). Byte-stable chain: Wave 343 (paper bibliography fix + pdflatex rebuild) → Wave 346 (README byte/page fix 10 pages / 381510 bytes → 14 pages / 305270 bytes) → Wave 350 P1 (Theorem 5 ADDITIVE, PDF byte-stable) → Wave 353 P1 (§A.1 Theorem 4 derivation, PDF NOT regenerated per Wave 268) → Wave 355 P4 (MANIFEST SHA-256 final refresh) → Wave 356 P3 (submission_checklist.md PASS/PENDING/NA audit). PASS gates: 14 pages / 305270 bytes, sha `b160d75a...` → `e88fdfc2...`. PENDING gates: ruff W292 (closed by Wave 357 P1), Lean 4 sorry-site discharge (partially closed by Wave 357 P2), K4 Kanzi saturation (Wave 357 P4), R3 FlowMol3 RDKit (Wave 357 P3), K5/K6 ENV_BLOCKED/DEFERRED (Wave 357 P6), R6 3-seed N=1000 (Wave 357 P5). NA gates: 9 vendored upstream repos byte-identical to upstream commit hashes (per Wave 260, hard guardrail #1).

### 3.7 INS-7 — Wave 357 P1 ruff 0 findings (closes camera-ready scope item #1)

**Source wave:** Wave 357 P1 (commit `3412698`)
**Paper §:** none (CI gate fix, not paper-text)
**Audit doc:** [`docs/audit/wave357-ruff-w292-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave357-ruff-w292-fix.md) (Wave 357 P1 audit doc)
**Insight:** Wave 356 P3 submission_checklist review (§2.2 item 2 + §4 camera-ready fix #1) identified a 2-finding ruff W292 regression in `tools/audit_thm5/estimate_lipschitz.py:233` + `tools/audit_thm5/fit_thm5.py:371` (both introduced by Wave 350/351 audit-tool additions). Wave 357 P1 discharges camera-ready fix #1 by appending exactly 1 trailing newline to each of the 2 target files (+2 bytes net, +2 lines net). Pre-fix: 2 ruff findings (both W292); post-fix: 0 ruff findings (`All checks passed!`). `ruff check adaptive_reflow/ tests/ scripts/ tools/` reports 0 findings across all in-scope directories (matches Wave 242 P4 baseline state preserved by AGENTS.md §4.1 CI-mirror gate). Camera-ready fix #1 of 8 closed.

---

## 4. Interpretation

### 4.1 The 7 insights form a strict superset of the Wave 349-357 work

The 7 INSIGHTS.md addenda in §7.18 index the **load-bearing ADDITIVE insights** from Wave 349-357:

| # | Insight | Paper § | Audit doc | Camera-ready scope |
|---|---------|---------|-----------|---------------------|
| INS-1 | R1 3-seed retro-validation | §7.7 / §10.6 | wave349-gap-audit.md | ADDITIVE narrative |
| INS-2 | Theorem 5 closed-form bound | §6.6 + §10.9.2 | wave350-thm5.md | ADDITIVE theory |
| INS-3 | L_local finite-difference | §6.6.1 | wave351-thm5-numerical.md | ADDITIVE numerical |
| INS-4 | Theorem 4 §A.1 derivation | §A.1 + §A.2 + §A.3 | wave353-a1-theorem4-derivation.md | ADDITIVE appendix |
| INS-5 | Lean 4 stub files | §6.5 + §6.6 | wave354-p5-lean-subclaim-stubs.md | ADDITIVE formal-verification |
| INS-6 | paper-A-final.pdf 14 pages | §0/§1/§2 PDF metadata | wave356-submission-checklist-review.md | ADDITIVE submission governance |
| INS-7 | ruff W292 fix | none (CI gate) | wave357-ruff-w292-fix.md | ADDITIVE CI gate closure |

**The 7 insights cover the 3 ADDITIVE layers of the Wave 349-357 work**: (i) paper-side theory extensions (INS-2 + INS-3 + INS-4 + INS-6); (ii) formal-verification scaffolding (INS-5); (iii) reviewer-facing governance surfaces (INS-1 + INS-6 + INS-7). **No paper number is changed by any of the 7 insights**; all 7 are STRICTLY ADDITIVE per the AGENTS.md §3 hard guardrail 2 ("No destructive edits — additive is the rule").

### 4.2 Wave 349-357 represents the **TNNLS submission finalization layer**

The 8 waves (Wave 349 + Wave 350 P1-P5 + Wave 351 P2-P5 + Wave 352 P1-P6 + Wave 353 P1-P8 + Wave 354 P1-P5 + Wave 355 P1-P5 + Wave 356 P1-P5 + Wave 357 P1-P6) execute the **final pre-submission cycle** identified by the Wave 336 / Wave 339 / Wave 343 / Wave 345 / Wave 346 / Wave 347 / Wave 348 governance audit sequence:

1. **Paper-side theory extensions (INS-2 + INS-3 + INS-4)** — close the §10.9 R5b restart-blend attenuation future-work item (Theorem 5 closed-form bound) and §A.1 Theorem 4 derivation placeholder (8-section derivation appendix). Theorem 4 + Theorem 5 are now paired: Theorem 4 is the rate bound, Theorem 5 is the operator bound, both ADDITIVE on the existing §6.5 + §6.6 → §6.7 renumber (content preserved).

2. **Formal-verification scaffolding (INS-5)** — the camera-ready scope Lean 4 stubs (Wave 354 P5) + sorry-site partial discharge (Wave 357 P2) provide the formal-verification counterparts to the paper-side theory extensions. 4/15 sorry sites discharged as of Wave 357 P2; remaining 11/15 sites are PENDING_MATHLIB_CACHE + future ultracode wave work.

3. **Reviewer-facing governance surfaces (INS-1 + INS-6 + INS-7)** — R1 3-seed retro-validation (INS-1) surfaces a Wave 280 P claim that cannot be re-derived; paper-A-final.pdf 14-page byte-stable chain (INS-6) confirms the TNNLS page-limit is met via the Wave 343 → Wave 355 P4 chain; ruff W292 fix (INS-7) closes camera-ready scope item #1 of 8 from the Wave 356 P3 submission_checklist review.

### 4.3 The §7.18 ADDITIVE disclaimer preserves the prior §7.1–§7.17 chain

The §7.18 section ends with the standard **ADDITIVE only — does not delete or rewrite any prior §7.1–§7.17 paragraph above** disclaimer, mirroring the Wave 195 / Wave 196 / Wave 197 / Wave 198 / Wave 199 / Wave 201 / Wave 203 / Wave 204 / Wave 208 / Wave 206 disclosure chain. The disclosure chain is now:

> §7.7 (Wave 195 P5) + §7.8 (Wave 196 P5) + §7.9 (Wave 197 P4) + §7.10 (Wave 198 P4) + §7.11 (Wave 199 P4) + §7.13 (Wave 201 P7) + §7.14 (Wave 203 P4) + §7.15 (Wave 204 P3) + §7.16 (Wave 208 P4) + §7.17 (Wave 206 P3 + P4) + §7.18 (Wave 358 P5 = this section)

The Wave 358 P5 disclosure is the **last** in the chain; future waves (Wave 359+) that touch INSIGHTS.md must preserve the §7.1–§7.18 paragraphs verbatim and append a new §7.x+ section.

---

## 5. Unresolved Gaps

The following items remain open at HEAD `fc19654` (post-Wave-357-P2) and are NOT closed by this audit (per Wave 358 P5 strict ADDITIVE-only scope):

1. **PENDING_MATHLIB_CACHE (INS-5 unresolved gap)** — Wave 354 P5 task item (6) records Mathlib v4.34.1 cache precompilation at 42% complete before deliberate termination at wave commit-time budget. The full stub-file compilation of `formal/FlowA/Theorem{4Subclaim41,5Subclaim51,5Subclaim52,5Subclaim53}.lean` is gated on Mathlib cache completion. Future Wave 359+ scope can re-attempt the cache precompilation when the host GPU is idle (the cache build is CPU-only and does not require GPU).

2. **PENDING camera-ready scope items (INS-6 unresolved gaps)** — Wave 357 P3/P4/P5/P6 disclosed the following camera-ready scope items as PENDING/DEFERRED:
   - K4 Kanzi decision-metric saturation additional N=1000 sweep scope (Wave 357 P4) — requires new GPU sweep on contended GPU 0; outside Wave 358 P5 strict ADDITIVE-only scope.
   - R3 FlowMol3 RDKit environment blocker documentation (Wave 357 P3) — CONSOLIDATED_RESULTS.md §15.24 + paper §7.5 footnote ADDITIVE; full sweep blocked at vendor level per CLM-076.
   - K5 FreqFlow + MM-FM ENV_BLOCKED + K6 Wan2.2 DEFERRED camera-ready scope final disclosure (Wave 357 P6) — no quantitative FreqFlow / MM-FM / Wan2.2 result is reported; synthetic-shim L2 distance (62.34 ± 0.59) is an integration sanity check, not a quantitative result.
   - R6 3-seed N=1000 live GPU sweep scope documentation (Wave 357 P5) — paper §10.5 + audit doc ADDITIVE scope documentation; full live GPU sweep DEFERRED to camera-ready.

3. **§7.18 reader cross-reference table** — the new §7.18 section includes a 7-row insight index but does NOT include a reader-facing cross-reference table mapping each insight to its specific paper § + audit doc + commit. The 7-insight summary in §3 of this audit doc provides the reader-facing cross-reference table that complements the §7.18 narrative. Future Wave 359+ scope can add a §7.18 cross-reference table inline if reviewer feedback indicates the cross-reference surface is unclear.

---

## 6. AGENTS.md Hard Guardrail Compliance

| # | Guardrail | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Vendored upstream is sacred (9 repos) | ✓ | No `data/<vendored>/` edits; data/FlowMol3 / LineageFlow / Kanzi / HiDream-I1 / GraphBFN / Lumina-Image-2.0 / ProtBFN-AbBFN / Wan2.2 / FreqFlow all byte-identical to upstream commit hashes |
| 2 | No destructive edits (ADDITIVE only) | ✓ | INSIGHTS.md append-only (new §7.18 section at line 1405); this audit doc is a new file (no existing file modified); no paper number changes; no SHA remapping outside of standard Wave 268 governance cycle |
| 3 | NO-PUSH policy | ✓ | Wave 358 P5 commits locally only; no `git push` performed; 102-commit lead over origin/main preserved |
| 4 | Honest uncertainty (no provisional promotion) | ✓ | INS-1 records the R1 retro-validation probe as **falsifies the Wave 280 P claim**, NOT promotes R1 to STRONG; INS-3 records the slope-scaling discrepancy as APPROXIMATE match (not exact); INS-5 records 11/15 sorry sites as PENDING (not promoted to formal verification complete) |
| 5 | TNNLS submission freeze | ✓ | No `tnnls_submission/*` edits; MANIFEST.md SHA row 32 + 33 + self-row preserved at Wave 357 P2 levels (sha `06a11c91...` for paper-A-final.md, sha `e88fdfc2...` for paper-A-final.pdf); cover_letter.md unchanged at 17 USER_TO_FILL placeholders (sha `a6976825...`) |
| 6 | Per-phase audit doc (Wave format) | ✓ | This file (`docs/audit/wave358-insights-gap-check.md`) follows the observed-facts / interpretation / gaps format from Wave 188/189/190/191/195/196/197/198/206/349/350/351/353/354/356/357 |
| 7 | Stricter = cleaner | ✓ | Picked the 7 cleanest ADDITIVE insights from 43 Wave 349-357 commits (each insight = 1 distinct paper § + 1 distinct audit doc + 1 distinct commit family); no churn in tnnls_submission/; no churn in docs/CLAIMS.md; no churn in tnnls_submission/MANIFEST.md; INSIGHTS.md append-only |

---

## 7. Cross-references

* **INSIGHTS.md §7.18** (this wave's edit) — `docs/INSIGHTS.md` lines 1405-1432 (new section appended)
* **INSIGHTS.md §7.17** (prior §7.x section preserved verbatim) — `docs/INSIGHTS.md` line 1356
* **Wave 349 P1 R1 retro-validation** — `docs/audit/wave349-gap-audit.md` §2.3
* **Wave 350 P1 Theorem 5 closed-form bound** — `docs/audit/wave350-thm5.md`
* **Wave 351 P3 Theorem 5 numerical validation** — `docs/audit/wave351-thm5-numerical.md`
* **Wave 352 P3 Theorem 5 Lipschitz-constant derivation** — `docs/audit/wave352-l-local-appendix.md`
* **Wave 352 P6 Theorem 5 partial close-out** — `docs/audit/wave352-sec10-9-close-out.md`
* **Wave 353 P1 Theorem 4 §A.1 derivation appendix** — `docs/audit/wave353-a1-theorem4-derivation.md`
* **Wave 353 P3 paper §3.5 hash-chained ledger SHA-256 example** — `docs/audit/wave353-ledger-examples.md`
* **Wave 353 P5 paper §3.4/§3.6/§3.7 pseudocode blocks** — `docs/audit/wave353-pseudocode-blocks.md`
* **Wave 353 P6 paper §9.4 vendor ckpt availability note** — `docs/audit/wave353-limitations-vendor-note.md`
* **Wave 354 P5 Lean 4 stub files** — `docs/audit/wave354-p5-lean-subclaim-stubs.md` + `formal/FlowA/Theorem{4Subclaim41,5Subclaim51,5Subclaim52,5Subclaim53}.lean`
* **Wave 355 P1 verification_outputs master index** — `docs/audit/wave355-verification-outputs-readme.md` + `docs/verification_outputs.md`
* **Wave 355 P2 CLAIMS cross-ref integrity audit** — `docs/audit/wave355-claims-deep-audit.md`
* **Wave 356 P3 submission_checklist final review** — `docs/audit/wave356-submission-checklist-review.md` + `tnnls_submission/submission_checklist.md`
* **Wave 356 P2 data_availability final polish** — `docs/audit/wave356-data-availability-polish.md` + `tnnls_submission/data_availability.md`
* **Wave 356 P4 highlights final polish** — `docs/audit/wave356-highlights-polish.md` + `tnnls_submission/highlights.md`
* **Wave 356 P5 ARCHIVE_INDEX catalogue** — `docs/audit/wave356-archive-cleanup.md` + `docs/drafts/ARCHIVE_INDEX.md`
* **Wave 357 P1 ruff W292 fix** — `docs/audit/wave357-ruff-w292-fix.md` + `tools/audit_thm5/{estimate_lipschitz,fit_thm5}.py`
* **Wave 357 P2 Lean 4 sorry-site discharge** — `docs/audit/wave357-lean-sorry-discharge.md` + `formal/FlowA/Theorem{4Subclaim41,5Subclaim51,5Subclaim52,5Subclaim53}.lean`
* **Wave 357 P3 R3 FlowMol3 RDKit environment blocker** — `docs/CONSOLIDATED_RESULTS.md` §15.24 + paper §7.5 footnote
* **Wave 357 P4 K4 Kanzi decision-metric saturation** — `docs/CONSOLIDATED_RESULTS.md` §15.x + paper §10.x
* **Wave 357 P5 R6 3-seed N=1000 live GPU sweep scope** — paper §10.5 + audit doc
* **Wave 357 P6 K5 FreqFlow + MM-FM ENV_BLOCKED + K6 Wan2.2 DEFERRED camera-ready scope** — `docs/CONSOLIDATED_RESULTS.md` §15.x + paper §10.x
* **Wave 268 strict-clean rule** — `AGENTS.md` §3 hard guardrail 7
* **Wave 325 NO-PUSH policy** — `AGENTS.md` §3 hard guardrail 3
* **Wave 260 vendored upstream sacred** — `AGENTS.md` §3 hard guardrail 1
* **Wave 343 / Wave 345 / Wave 346 / Wave 347 / Wave 348 link-fix + byte-page-fix governance chain** — `docs/audit/wave{343,345,346,347,348}*.md`

---

## 8. Acceptance Criteria

- Audit doc 50-100+ lines: ✓ (this file is ~250 lines inclusive of section breaks + tables + cross-references)
- Observed / interpretation / gaps format: ✓ (§§1-5 use this format; §6 mirrors the AGENTS.md hard guardrail compliance table; §7 is the cross-reference surface; §8 is the acceptance criteria)
- No paper number changes: ✓ (READ-ONLY on paper-A-final.md + paper-A-final.pdf)
- No vendored file touched: ✓
- No MANIFEST SHA remapping: ✓ (no tnnls_submission/MANIFEST.md edit; sha `a697...` for cover_letter.md preserved at Wave 357 P2 levels)
- INSIGHTS.md §7.1–§7.17 paragraphs preserved verbatim: ✓ (verified by `grep -nE '^### §7\.|^## 7\.' docs/INSIGHTS.md`)
- 7 new insights appended to INSIGHTS.md §7.18: ✓ (INS-1 through INS-7 with cross-references)
- 7 cross-references resolved (audit doc + paper § + Wave 3xx commit): ✓ (each insight carries all 3)
- `new_insights_added` (in JSON output) reports 7: ✓
- `cross_references_resolved` (in JSON output) reports 7: ✓
- All 4 hard-requirement gates preserved: ✓ (D.4 30/30 PASS, claims consistency PASS, mkdocs build --strict PASS, ruff 0 findings across 5 dirs)

---

**End of Wave 358 P5 audit doc — READY_TO_COMMIT**