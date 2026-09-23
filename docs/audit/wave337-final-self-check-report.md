# Wave 337 — Final Self-Check Verification Report

**Date:** 2026-09-23
**Scope:** Wave 336 Phase-1/3/4/5 deliverables into paper-A-final.md, paper terminology hygiene (H7), abbreviation coverage (H8), numerical consistency (B6)
**Working file:** `/home/hugo/codes/flowa-multistep-reinference/docs/drafts/paper-A-final.md` (529 lines)
**Verdict:** **NOT-READY-FOR-PUSH** — multiple P0/P1 gaps, user authorization gating remaining

---

## 1. Executive Summary

| Category | Total | Passed | Failed | Pending | User-Action |
|---|---|---|---|---|---|
| Wave 336 explicit items (T4 / R6-live / R5c / R1 / C5) | 5 | 1 (partial) | 4 | 0 | 4 |
| H7 — Terminology Leakage Audit | 1 verdict | 0 | 1 (DIRTY) | 0 | 1 |
| H8 — Abbreviations Audit | 1 verdict | 1 (PASS-WITH-CAVEATS) | 0 | 15 sub-items | 1 |
| B6 — Numerical Cross-Consistency | 25 numbers | 24 | 1 (R5a d_s) | 0 | 1 |
| **TOTAL** | **32** | **26** | **6** | **15** | **7+** |

**Single most-load-bearing gap:** the R5a Two-Moons d_s value (`+0.460` in paper §7.2) does not match either raw (`+0.610`) or Hedges-corrected (`+0.488`) recomputation from `verification_outputs/wave189-p2-sota-2d-rerun/`. Plus paper-body is polluted with ~40 internal `Wave NNN` references and internal repo paths.

**Verdict rationale:** Wave 337 cannot push to TNNLS upload portal until (a) R5a d_s re-derived from a defensible source, (b) H7 body-text sanitization run, and (c) Wave 336 missing items (T4, R6-live, R1 3-seed, C5-abstract) are explicitly re-decided by user.

---

## 2. Per-Section Breakdown (A–H)

### Section A — Wave 336 New-Item Insertion Status

| Field | Requested | Actual | Status |
|---|---|---|---|
| `theorem4InSection6` | Theorem 4 statement in §6 | §6 contains only Lemmas 1/2/3 (lines 231/255/271). Theorem 4 absent. | **FAIL** |
| `r6LiveInSection63` | Live GPU measurement in §6.3 | §6.3 is Lemma 2 (state-machine byte-determinism), not R6 results. Counterfactual d_z=+0.2235 unchanged at §7.2 line 309. | **FAIL** |
| `r5cRegimeCurveInSection76` | R5c regime curve in §7.6 | Curve IS present (epochs 1/2/3 table) but at §7.8 lines 352-356 (NOT §7.6). §7.6.1 cross-reference at line 342 points to §7.8. | **PARTIAL** (content exists at alternate location) |
| `r13SeedFixInSection71` | R1 3-seed fix in §7.1 | R1 remains PARTIAL / single-seed-disclosed (d_z=+0.182 < 0.8 STRONG-promotion bar; seed-43/44 contaminated). No STRONG promotion. | **FAIL** |
| `c5AbstractNoK` | C5 abstract K-level removal | Abstract line 5 still reads "K-level cells (K1, K4, K5, K7) are reported in §10 supplementary with honest disclosure of statistical limitations". | **FAIL** |

**Score: 1/5 passed (R5c partial only), 4/5 failed. NO auto-fix applied.**

### Section B — Numerical Consistency (B6 cross-doc)

- 25 critical claims cross-checked against `verification_outputs/` artifacts
- 24 PASS, 1 FAIL
- **FAIL item:** R5a Two Moons d_s=+0.460 (paper) vs +0.610 (raw Cohen's d_s from per-seed CSV, n=3+3) vs +0.488 (Hedges' g small-sample correction). The paper's +0.460 does not match either computation. Aggregate JSON `wave189-p2-post-cd70821-two_moons.json` reports `framework_w2_mean=0.075930` while per-seed CSVs report `framework_w2_mean=0.068891` — the two candidate sources DISAGREE on framework w2, suggesting different scheduler runs or aggregation windows. **Either an independent aggregated source survives, or the +0.460 is wrong and must be re-derived.**

### Section C — Theorem 4 (Lemmas vs Theorem structure)

- §6 framework properties are structured around three lemmas + proof sketch only
- No "Theorem 4" candidate statement exists; closest analog is Lemma 3 at line 271
- Wave 336 Phase 1 (Theorem 4 addition) was a no-op — schema field captured the absence honestly
- **Open question:** was Wave 336's "Theorem 4" a misnomer for an existing lemma consolidation? User clarification required.

### Section D — R6 Live GPU Disambiguation

- §6.3 currently occupied by Lemma 2 (state-machine byte-determinism, FP/I-O/RNG/wall-clock/set-iteration proof, line 259-291)
- §7.2 R6 narrative remains counterfactual-only (line 309: `tier-aware-arm counterfactual d_z = +0.2235`)
- Wave 336 Phase 3 (live GPU measurement) was a no-op; no live numerical replacement applied
- **Wave 336 should be re-run only if user wants R6 promoted from COUNTERFACTUAL to LIVE before push.**

### Section E — R1 3-Seed Disambiguation

- R1 status remains PARTIAL / single-seed-disclosed (cross-wave residual from Wave 280 P §7.2 disclosure)
- d_z=+0.182 < 0.8 STRONG-promotion bar
- 3-seed pool invalidated by seed-43/44 framework-fallback contamination
- Wave 336 Phase 4 (R1 fix) was a no-op
- **User must explicitly decide** whether to (a) attempt seed-pool cleansing and run fresh n=3, (b) keep single-seed-disclosed framing and rewrite §7.2 R1 cell, or (c) defer R1 demotion to §10 supplementary and present only R2/R3/R5 in §7.

### Section F — C5 Abstract K-Level Reframing

- Abstract line 5 still names K-level cells (K1, K4, K5, K7)
- Wave 336 Phase 5 (abstract trimming) was a no-op
- **User must decide** whether to (a) drop K-cell mention from abstract entirely, (b) soften to "supplementary tables", or (c) preserve and rely on §10 honest-disclosure block.

### Section G — H7 Terminology Leakage

- Verdict: **DIRTY** — body-text internal-jargon leak
- 40+ occurrences of `Wave NNN` numeric refs across 19 unique lines (Abstract line 5, §1 intro 23, §3.8 147, §5.3 211, §6 247, §7.2 303/309/311/313/422/476, §7.8 358, §8.4 382, §8.5 394, §10.7 470)
- 4 internal CLM-NNN claim IDs (lines 394/398/402)
- 8 `docs/audit/...md` and `docs/CLAIMS.md` path references (lines 53/340/350/394/398/402/480/484)
- 2 internal tool paths (`tools/check_claims_consistency.py` line 53, `tools/wave87_n1000_sweep.py` line 313)
- 4 SHA-1/SHA-256 commit hashes (lines 394/398/470/350)
- 1 internal git tag `v3.0-tnnls-ready` (line 398)
- 1 `git log --follow` invocation leak (line 394)
- 2 `wfNNN-...` workflow-identifier leaks (lines 470/350)
- "Wave-Based Audit Chain" terminology at line 398
- **User authorization required to apply body-text sanitization pass before camera-ready.**

### Section H — H8 Abbreviations Audit

- Verdict: **PASS-WITH-MINOR-CAVEATS**
- 35/50 abbreviations defined at first use (PASS)
- 15 undefined at first use — all minor-impact:

**P0 (reviewer-visible, 2 items):**
- `pLDDT` (14x, line 309) — never expanded
- `scPerplexity` (8x, line 309) — never expanded

**P1 (TNNLS reviewer readable, 8 items):**
- `HSM` (3x, line 131) — Hierarchical State Machine
- `HMMER` (8x, line 181) — bioinformatics tool
- `RDKit` (4x, line 23) — cheminformatics toolkit
- `FDR-BH` (1x, line 326) — Benjamini-Hochberg
- `DGL` (2x, line 313) — Deep Graph Library
- `JWT` (3x, line 51) — JSON Web Token
- `FP` (3x, line 259) — ambiguous (likely Floating-Point)
- `DLLM` (4x, line 19) — Diffusion Language Model

**P2 (cosmetic, 5 items — paper-citation names):**
- `AB-Cache`, `LeDiFlow`, `Fast-DLLM`, `EDM`, `UniPC`

**Cross-doc consistency:** PASS (NFE/FID/CIFAR/pLDDT/scPerplexity/Bonferroni proportional across paper + CLAIMS.md + audit/*.md).

---

## 3. Failed Items List

| # | Section | Item | Severity | Why failing |
|---|---|---|---|---|
| 1 | A | Theorem 4 absent in §6 | P1 | §6 has 3 lemmas only; no 4th theorem statement |
| 2 | A | R6 live GPU in §6.3 | P0 | §6.3 is Lemma 2; counterfactual d_z=+0.2235 at line 309 unchanged |
| 3 | A | R1 3-seed fix in §7.1 | P0 | d_z=+0.182 < 0.8 STRONG bar; seed-43/44 invalidated; status PARTIAL |
| 4 | A | C5 abstract no-K | P2 | Abstract line 5 still mentions K-level cells |
| 5 | G | H7 terminology leak | P0 | 40+ Wave NNN refs + 4 CLM-NNN IDs + 8 docs paths + SHAs + git tags |
| 6 | B | R5a d_s inconsistency | P0 | +0.460 paper vs +0.610 raw / +0.488 Hedges; aggregate sources disagree |

---

## 4. Pending Items List

| # | Section | Item | Severity | Disposition |
|---|---|---|---|---|
| 1 | H | pLDDT expand-at-first-use | P0 | Insert "predicted Local Distance Difference Test" at line 309 |
| 2 | H | scPerplexity expand-at-first-use | P0 | Insert "single-cell Perplexity" at line 309 |
| 3 | H | HSM expand (line 131) | P1 | Insert "Hierarchical State Machine" at first use |
| 4 | H | HMMER expand (line 181) | P1 | Insert "Profile Hidden Markov Model-based homology search engine" |
| 5 | H | RDKit expand (line 23) | P1 | Insert "Open-Source Cheminformatics Toolkit" |
| 6 | H | FDR-BH expand (line 326) | P1 | Insert "False Discovery Rate — Benjamini-Hochberg" |
| 7 | H | DGL expand (line 313) | P1 | Insert "Deep Graph Library" |
| 8 | H | JWT expand (line 51) | P1 | Insert "JSON Web Token" |
| 9 | H | FP clarify (line 259) | P1 | Insert "(Floating-Point)" at first use |
| 10 | H | DLLM expand (line 19) | P1 | Insert "Diffusion Language Model" |
| 11 | H | AB-Cache citation format (line 19) | P2 | Add [Author/Surname et al., Year] format |
| 12 | H | LeDiFlow citation format (line 19) | P2 | Add citation format |
| 13 | H | Fast-DLLM citation format (line 19) | P2 | Add citation format |
| 14 | H | EDM expand (line 19) | P2 | Expand at first use despite being cited as [4] |
| 15 | H | UniPC expand (line 19) | P2 | Expand at first use |

---

## 5. USER Action Checklist (pre-push)

In order of priority — none of these can be auto-resolved by the framework.

### 5.1 P0 BLOCKERS (do before any push)

- [ ] **(B-1) Decide R6 disposition.** Run live GPU R6 measurement AND replace counterfactual d_z=+0.2235 in §7.2 line 309, OR explicitly keep counterfactual framing and add "Counterfactual-only" note to §7.2. Either path requires rerunning Wave 336 Phase 3 OR issuing a "keep counterfactual" wave directive.
- [ ] **(B-2) Resolve R5a d_s=+0.460 inconsistency.** Re-derive from a defensible source (likely a 3rd aggregated file), or update §7.2 R5a d_s to +0.610 (raw) or +0.488 (Hedges), or add a footnote explaining the +0.460 source. Investigate the disagreement between aggregate JSON (framework_w2_mean=0.075930) and per-seed CSV (framework_w2_mean=0.068891).
- [ ] **(B-3) Apply body-text sanitization pass for H7.** Strip all 40+ `Wave NNN` refs → "the audit pass" / "the canonical byte-stable reference"; remove all CLM-NNN claim IDs; remove all `docs/audit/...md` + `docs/CLAIMS.md` + `tools/...py` paths; remove all SHA-1/SHA-256 commit hashes; remove `v3.0-tnnls-ready` git tag and `git log --follow` invocation; rephrase "Wave-Based Audit Chain" → "append-only reproducibility ledger"; remove all `wfNNN-` workflow identifiers.
- [ ] **(B-4) Decide R1 disposition.** Run fresh n=3 seed pool with seed-43/44 excluded, OR keep PARTIAL / single-seed-disclosed framing and add §7.2 R1 disclosure, OR demote R1 to §10 supplementary only.

### 5.2 P1 SHOULD-FIX

- [ ] **(S-1) Decide Theorem 4 in §6.** Add a 4th theorem statement, or document that Wave 336's "Theorem 4" was an alias for "Lemma 3 consolidation at §6.2.3". Cross-wave drift suspected — clarify in user message.
- [ ] **(S-2) Expand 8 P1 abbreviations at first use** (HSM/HMMER/RDKit/FDR-BH/DGL/JWT/FP/DLLM).
- [ ] **(S-3) Apply C5 abstract trimming.** Drop "K1, K4, K5, K7" mention from abstract line 5, or soften to "supplementary tables" / "extended validation".

### 5.3 P2 NICE-TO-HAVE

- [ ] **(N-1) Expand 2 P0 abbreviations** (pLDDT, scPerplexity) at first R6 occurrence.
- [ ] **(N-2) Fix 5 P2 citation formats** (AB-Cache, LeDiFlow, Fast-DLLM, EDM, UniPC) to Author/Year format.
- [ ] **(N-3) Add List of Abbreviations** subsection before §1 (alternative to per-line expansion).

### 5.4 Submission logistics (must complete before TNNLS upload portal)

- [ ] **(L-1) Fill cover letter** with editor + reviewer suggestions.
- [ ] **(L-2) Fill authors block** with affiliations + ORCIDs + corresponding author.
- [ ] **(L-3) Register TNNLS submission account** if not yet done.
- [ ] **(L-4) Pay TNNLS submission fee** (if applicable for the chosen track).
- [ ] **(L-5) Compile supplementary archive** (zip of `docs/audit/`, `verification_outputs/`, code, configs).
- [ ] **(L-6) Verify PDF regen succeeds** with current paper-A-final.md state (run `tools/regen_pdf.sh` or equivalent, append SHA to freeze manifest).
- [ ] **(L-7) Resolve CLAIMS.md + docs/CLAIMS.md sync** with paper-A-final.md (currently 287 NFE / 118 pLDDT / 64 scPerplexity references in CLAIMS.md vs 56/14/8 in paper — confirms auto-sync is wired but thresholds need re-check).

---

## 6. Verification Artifacts

- **This report:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave337-final-self-check-report.md`
- **Inputs consulted:**
  - `/home/hugo/codes/flowa-multistep-reinference/docs/drafts/paper-A-final.md` (529 lines, modified by Wave 336)
  - `/home/hugo/codes/flowa-multistep-reinference/docs/CLAIMS.md` (cross-doc consistency)
  - `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave336-r5b-mechanism.md` (new audit)
  - `/home/hugo/codes/flowa-multistep-reinference/docs/audit/mnist/wf334-r5c-regime-curve.md` (R5c regime curve)
  - `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave189-p2-post-cd70821-two_moons.json` (R5a source-candidate)
  - `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave189-p2-sota-2d-rerun/two_moons_*.csv` (R5a source-candidate, alt)
  - 50+ files in `docs/audit/*.md` (terminology-leak search corpus)

---

## 7. Cross-Wave Residuals Carried Forward

1. **R1 "3-seed pool invalidated by seed-43/44 framework-fallback contamination"** — carried as PARTIAL since Wave 280 P (§7.2 line 311)
2. **K7 "direction INVERTED"** — carried as PARTIAL since Wave 306/307 (§10.7 line 476)
3. **C5 abstract K-cell mention** — carried since Wave 328 (Abstract line 5)
4. **R6 counterfactual-only** — carried since Wave 233 P3 (§7.2 line 309)
5. **R5c regime curve location mismatch** (§7.8 vs expected §7.6) — Wave 336 partial alignment

These are persistent cross-wave residuals; Wave 337 cannot auto-fix them — they require USER disposition.

---

## 8. Final Verdict

**Status: NOT-READY-FOR-PUSH.**

The paper body is structurally sound and methodologically defensible, but it is NOT camera-ready:

- 4/5 Wave 336 explicit items not applied (only R5c partial pass)
- ~40 internal-jargon leaks in paper body (H7 DIRTY)
- 1 numerical inconsistency in R5a d_s (B6 FAIL)
- 15 undefined abbreviations at first use (H8 PASS-WITH-CAVEATS)
- 6 P0 user-action blockers across (B-1, B-2, B-3, B-4)

Recommended next wave: **Wave 338** — user-driven disposition wave. Each P0 block resolved by a single user-authorized wave: (a) H7 body-text sanitization, (b) R5a d_s re-derivation, (c) R1 single-seed-disclosed rewrite, (d) R6 counterfactual framing decision, (e) H8 P0+P1 abbreviation expansion, (f) C5 abstract trimming.

— END OF REPORT —
