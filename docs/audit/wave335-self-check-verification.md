# Wave 335 Self-Check Verification Report

**Date:** 2026-09-23T13:58:21Z
**Author:** Wave 335 Phase 5 verification agent
**Scope:** Wave 332 (176c6d4) HEAD — paper-A-final.{md,pdf,log} freeze state
**Purpose:** Final pre-submission gap audit before TNNLS upload

---

## 1. Executive Summary

| Status     | Count | Notes                                                |
|------------|-------|------------------------------------------------------|
| PASS       | 50    | Verified, no action required                         |
| FAIL       | 4     | Blockers — must fix before camera-ready submission   |
| PENDING    | 3     | USER action items (cover letter, TNNLS account)      |
| PARTIAL    | 2     | Acceptable but flagged for reviewer-side disclosure  |
| **TOTAL**  | **59**| Per-section: A+B=16, C+D=14, E+F=13, G+H=16         |

**Submission readiness:** Paper is **NOT** ready for TNNLS upload in current state. Four FAIL items
(A1, A4, A6, C5) block camera-ready. Two PARTIAL items (G7, H8) require reviewer-facing
disclosure language in cover letter. Three PENDING items require USER input (cannot be filled
by agents).

**Critical blockers (FAIL, must fix):**
1. **A1 (R6 live GPU re-run)** — `verification_outputs/wave280-p-r6/` does NOT exist. Only counterfactual data is present.
2. **A4 (R5c regime-dependent curve)** — No continuous regime curve; aggregate compares 2 discrete ckpts.
3. **A6 (ML pipeline comparison table)** — Paper §2 lacks §2.4 ML pipeline comparison table.
4. **C5 (Abstract K-level cells)** — Abstract mentions K-level cells by name; strict reading fails "Abstract不提K-level cells" criterion.

**Items already passed and frozen (do not touch in Wave 334):**
- All Wave 332 DeepSeek final-pass fixes (Lemma 2 Case D, R5a citation, References dedup, R3 disclaimer, LaTeX escape).
- All 5 D.4 byte-stable regression vectors + 30/30 pytest green.
- All 5 5-gate CI checks green (ruff, mkdocs, claims, vendored, D.4).
- SHA-256 chain §7 (Wave 328) intact: 0a65d20b → 8e7367a0 → c99192dc.

---

## 2. Per-Section Breakdown

### 2.1 Section A — Empirical R-level provenance (7 items)

| Item                       | Status | Severity |
|----------------------------|--------|----------|
| a1R6Live                   | FAIL   | HIGH     |
| a2R6Matches                | PASS   | —        |
| a3R5cSweep                 | PASS   | —        |
| a4R5cCurve                 | FAIL   | HIGH     |
| a5R5cFlipExplained         | PASS   | —        |
| a6MLPipelineTable          | FAIL   | HIGH     |
| a7Sha256                   | PASS   | —        |

**Section A summary:** 4 PASS, 3 FAIL. Three R-level provenance FAILs are all camera-ready blockers
because they touch §7 headline numbers and §2 background framing.

### 2.2 Section B — Paper writing quality (9 items)

| Item                       | Status | Severity |
|----------------------------|--------|----------|
| b1K4Typo                   | PASS   | —        |
| b2K7Reframe                | PASS   | —        |
| b3LaTeXGarbled             | PASS   | —        |
| b4Lemma2Wording            | PASS   | —        |
| b5ReferencesDedup          | PASS   | —        |
| b6NumbersConsistent        | PASS   | —        |
| b7R3Labels                 | PASS   | —        |
| b8R1Labels                 | PASS   | —        |
| b9R5cLabels                | PASS   | —        |

**Section B summary:** 9/9 PASS. Wave 332 DeepSeek final-pass closed all 9 writing-quality
gates. Section B is fully frozen; Wave 334 should not re-edit any of these locations.

### 2.3 Section C — Honest disclosure (8 items)

| Item                       | Status | Severity |
|----------------------------|--------|----------|
| c1KcellsSupplementary       | PASS   | —        |
| c2RcellsPositive           | PASS   | —        |
| c3R5b                      | PASS   | —        |
| c4R6                       | PASS   | —        |
| c5AbstractNoK              | FAIL   | MEDIUM   |
| c6Contributions4           | PASS   | —        |
| c73Lemmas                  | PASS   | —        |
| c85Gate                    | PASS   | —        |

**Section C summary:** 7 PASS, 1 FAIL. C5 (Abstract mentions K-level cells) is borderline: K-cells
are listed in the 11-cell enumeration but are NOT promoted to STRONG. Charitable reading: PASS.
Strict reading: FAIL. Decision deferred to Wave 334 based on reviewer-risk tolerance.

### 2.4 Section D — Reproducibility infrastructure (6 items)

| Item                       | Status | Severity |
|----------------------------|--------|----------|
| d1D4                       | PASS   | —        |
| d2CI                       | PASS   | —        |
| d3Dockerfile               | PASS   | —        |
| d4Reproduce                | PASS   | —        |
| d5VendoredUnmodified       | PASS   | —        |
| d6Sha256                   | PASS   | —        |

**Section D summary:** 6/6 PASS. Reproducibility infrastructure is complete: Dockerfile present,
reproduce/ has 8 scripts, all 5 gates green, vendored untouched, SHA-256 coverage on headline
verification_outputs. **No creation needed.**

### 2.5 Section E — Statistical rigor (5 items)

| Item                       | Status | Severity |
|----------------------------|--------|----------|
| e1BonferroniPreregistered  | PASS   | —        |
| e2ClusterRobust            | PASS   | —        |
| e3SfPath                   | PASS   | —        |
| e4CI95                     | PASS   | —        |
| e5EffectSize               | PASS   | —        |

**Section E summary:** 5/5 PASS. Statistical method is rigorous: 4 pre-registered Bonferroni
families, cluster-robust Pfam-family unit, stats.t.sf path only (no 1-norm.cdf anti-pattern),
95% CIs in 12-column audit row, Cohen's d_z/d_s on every cell.

### 2.6 Section F — Reviewer-prediction pre-empts (8 items)

| Item                       | Status | Severity |
|----------------------------|--------|----------|
| f1R3Projection             | PASS   | —        |
| f2R6Counterfactual         | PASS   | —        |
| f3ONNX                     | PASS   | —        |
| f4Theory                   | PASS   | —        |
| f5KcellsSupp               | PASS   | —        |
| f6R5b                      | PASS   | —        |
| f7R5c                      | PASS   | —        |
| f8R1                       | PASS   | —        |

**Section F summary:** 8/8 PASS. All 8 reviewer-prediction pre-empts are present in paper body
(R3 projection, R6 counterfactual, ONNX comparison, theory companion, K-cells supplementary,
R5b matched-NFE boundary, R5c direction-flip, R1 single-seed demotion).

### 2.7 Section G — TNNLS submission package (8 items)

| Item                       | Status     | Severity |
|----------------------------|------------|----------|
| g1CoverLetter              | PASS       | —        |
| g2Abstract                 | PASS       | —        |
| g3Paper                    | PASS       | —        |
| g4Highlights               | PASS       | —        |
| g5Reviewers                | PENDING    | USER     |
| g6Author                   | PENDING    | USER     |
| g7Supplementary            | PARTIAL    | LOW      |
| g8TNNLSAccount             | PENDING    | USER     |

**Section G summary:** 4 PASS, 3 PENDING (USER action), 1 PARTIAL. The submission package is
structurally complete; what remains is filling in author/reviewer/TNNLS-account fields.

### 2.8 Section H — Final verification gates (8 items)

| Item                       | Status     | Severity |
|----------------------------|------------|----------|
| h1D4                       | PASS       | —        |
| h2Mkdocs                   | PASS       | —        |
| h3Claims                   | PASS       | —        |
| h4Ruff                     | PASS       | —        |
| h5Vendored                 | PASS       | —        |
| h6Pdf                      | PASS       | —        |
| h7Terminology              | PASS       | —        |
| h8Abbreviations            | PARTIAL    | LOW      |

**Section H summary:** 7 PASS, 1 PARTIAL. pLDDT is not expanded on first use (line 287 §7.1 R6).
Domain-standard abbreviation in AlphaFold/protein-FM community; TNNLS reviewers in
generative-models+protein-FM will recognize. Decision: leave as-is (expanding "predicted Local
Distance Difference Test" adds noise without aiding comprehension).

---

## 3. Critical Gap Items (FAIL — must fix before submission)

### Gap G-A1 — R6 live GPU re-run missing

- **Severity:** HIGH (camera-ready blocker)
- **Current state:** `verification_outputs/wave280-p-r6/` does NOT exist. Only counterfactual
  data (`wave233-p3-tier-aware-r6.{csv,json}` and `wave235-p3-r6-uplift.json`) is present.
- **What is required:** A real N=1000 paired live GPU sweep on R6 MNIST FM TierAwareCodimension
  producing fresh `verification_outputs/wave280-p-r6/` with seed42/seed43/seed44 cs.npz +
  sweep_summary.json + aggregate.json.
- **Estimated cost:** ~6 hours GPU (3 seeds × 1000 paired × 50 NFE × 4 schedulers).
- **Owner:** Wave 334 GPU re-run agent.

### Gap G-A4 — R5c regime-dependent curve missing

- **Severity:** HIGH (camera-ready blocker — paper §7 line 285 reports per-seed d_z but no
  regime curve)
- **Current state:** `wave280-p-r5c/` has 3 seeds (42/43/44) with 200-record samples, but no
  per-epoch (epoch 1/2/3) breakdown. `aggregate.json` compares smoke_ckpt_baseline vs
  production_ckpt as 2 discrete ckpts, not a continuous regime curve.
- **What is required:** Per-epoch regime curve figure (PDF/SVG/PNG) showing d_z as function of
  training progress, plus per-epoch summary in supplementary.
- **Estimated cost:** ~30 min analysis + figure generation (data already exists, just needs
  curve plotting).
- **Owner:** Wave 334 figure agent.

### Gap G-A6 — §2.4 ML pipeline comparison table missing

- **Severity:** HIGH (paper §2 has only 2.1, 2.2, 2.3 — no §2.4)
- **Current state:** Paper §2.1 (Flow matching inference paradigms), §2.2 (Convergence theory),
  §2.3 (Typed ML systems). No §2.4.
- **What is required:** New §2.4 with ML pipeline comparison table (PyTorch + torch.compile,
  JAX/XLA, ONNX Runtime, TVM, FlowA typed-contracts) covering axes: integration time,
  optimization pass, telemetry, byte-stability, capability tokens, vendor-friendliness.
- **Estimated cost:** ~2 hours (table authoring + cross-reference to §3.4-3.5 innovations).
- **Owner:** Wave 334 paper-write agent.

### Gap G-C5 — Abstract mentions K-level cells

- **Severity:** MEDIUM (borderline; depends on reviewer-risk tolerance)
- **Current state:** Abstract sentence: "4 K-cells (K1 FlowMol3 RDKit, K4 LineageFlow
  hmmscan_total_hits (Pfam-A coverage), K5 LineageFlow hmmscan_total_hits delta
  (framework-vs-baseline), K7 LineageFlow novelty)". K-cells are listed in the 11-cell
  enumeration but NOT promoted as primary result.
- **What is required (strict reading):** Rewrite abstract to list only R-level cells in
  enumeration, defer K-cells to supplementary §10 mention only.
- **What is required (charitable reading):** Add disclosure language clarifying K-cells are
  supplementary (not headline).
- **Owner:** Wave 334 paper-write agent (decision: which reading to adopt).

---

## 4. Items Needing USER Action (PENDING — cannot fill by agents)

### Gap G-5 — Reviewer slot filling

- **Severity:** HIGH (cannot submit without 5 reviewers)
- **Current state:** All 10 reviewer placeholders in `tnnls_submission/cover_letter.md` §9
  (affiliations + emails × 5) are `[USER TO FILL: ...]`.
- **What is required:** USER fills in 5 reviewer name + affiliation + email triples.
- **Reference:** `tnnls_submission/FILL_GUIDE.md` §4-§8.

### Gap G-6 — Author block filling

- **Severity:** HIGH (cannot submit without author block)
- **Current state:** Authors block at line 51 of `cover_letter.md` is
  `[USER TO FILL: Authors block — full author list, affiliations, and corresponding-author
  email]`. 3 corresponding-author fields at §11 (lines 1126-1128) also pending.
- **What is required:** USER fills in author list + affiliations + corresponding-author name/
  affiliation/email.
- **Reference:** `tnnls_submission/FILL_GUIDE.md` §3.

### Gap G-8 — TNNLS Editorial Manager account

- **Severity:** HIGH (cannot submit without active EM account)
- **Current state:** Cannot verify from repo state.
- **What is required:** USER confirms TNNLS Editorial Manager account active + ScholarOne
  upload via 7-step `tnnls_submission/README.md` walkthrough.
- **Reference:** `tnnls_submission/README.md` + `submission_checklist.md` G4.

---

## 5. Partial Items (PARTIAL — disclose in cover letter)

### Gap G-7 — Supplementary is index-only, not bundled

- **Severity:** LOW (TNNLS upload is per-file, not zipped per README.md walkthrough)
- **Current state:** `tnnls_submission/supplementary/` contains only `README.md` (11283 bytes,
  SHA-256 66986c3b...) indexing per-cell SOURCE.md provenance + cross-doc audit trail +
  verification outputs + Lemma proofs + Theorem 1 package. No packed/zip bundle.
- **What is required:** Confirm with USER that TNNLS upload is per-file (not zipped). If zipped,
  create `supplementary_bundle.zip` aggregating all index entries.
- **Reference:** `tnnls_submission/README.md` 7-step walkthrough.

### Gap H-8 — pLDDT not expanded on first use

- **Severity:** LOW (domain-standard abbreviation; TNNLS reviewers will recognize)
- **Current state:** pLDDT first use line 287 §7.1 R6 cell. NOT explicitly expanded.
- **What is required:** Optional — add `(predicted Local Distance Difference Test)` after first
  pLDDT mention in §7.1.
- **Decision:** Leave as-is (expanding adds noise).

---

## 6. Wave 334 / Post-Wave-334 Action Plan

### Wave 334 ownership (paper edits)

1. **G-C5 (Abstract):** Decide strict-vs-charitable reading. If strict, rewrite abstract to
   defer K-cell enumeration to supplementary.
2. **G-A6 (§2.4):** Author new ML pipeline comparison table covering PyTorch, JAX/XLA, ONNX
   Runtime, TVM, FlowA on 5-6 axes.
3. **G-A4 (R5c curve):** Generate per-epoch regime curve figure + per-epoch summary.

### Wave 335+ GPU re-run ownership

1. **G-A1 (R6 live GPU):** Trigger `tools/wave280-p-r6/` N=1000 paired live sweep on 3 seeds
   (42/43/44), ~6 hours GPU. Output: `verification_outputs/wave280-p-r6/seed{42,43,44}/cs.npz +
   sweep_summary.json + aggregate.json`.

### USER ownership (cannot be filled by agents)

1. **G-5 (Reviewers):** Fill 10 placeholders in cover_letter.md §9.
2. **G-6 (Authors):** Fill author block line 51 + corresponding-author fields §11.
3. **G-8 (TNNLS EM):** Confirm account active, run 7-step README.md walkthrough upload.

### Optional disclosures (low priority)

1. **G-7 (Supplementary bundle):** Confirm TNNLS per-file upload is acceptable; bundle if not.
2. **H-8 (pLDDT expansion):** Optional first-use expansion in §7.1.

---

## 7. Items Verified PASS That Wave 334 Must NOT Touch

To prevent regression, Wave 334 paper-edit agent must NOT modify:

- **B1-B9 (Writing quality):** All 9 items frozen at Wave 332 DeepSeek final-pass.
- **C1, C2, C3, C4, C6, C7, C8 (Honest disclosure):** All 7 items present and frozen.
- **D1-D6 (Reproducibility):** All 6 items present (Dockerfile, reproduce/, D.4 30/30, etc.).
- **E1-E5 (Statistical rigor):** All 5 items present (4 Bonferroni families, cluster-robust,
  t.sf path, CIs, effect sizes).
- **F1-F8 (Reviewer-prediction):** All 8 items present in paper body.
- **H1-H7 (Final verification):** All 7 items green (pytest, mkdocs, claims, ruff, vendored,
  pdf, terminology).

**Total frozen:** 47/59 items. Wave 334 should only touch FAIL/PARTIAL items and not regress
any of the 47 PASS items.

---

## 8. SHA-256 Chain Audit

Self-referential manifest chain §7 (Wave 328) intact:

```
0a65d20b → 8e7367a0 → c99192dc → ... → 176c6d4 (HEAD)
```

Verification: `git -C /home/hugo/codes/flowa-multistep-reinference log --format='%H' -4`
yields the expected chain. SHA-256SUMS sidecars present on 6 expected wave280 headline
directories: `wave280-p-r1/`, `wave280-p-r3/`, `wave280-p-r5c/`, `wave280-p-k1/`,
`wave280-p-k4k5/`, `wave280-k7/`. The 7th (`wave280-p-r6/`) is missing per G-A1.

---

## 9. Reproduction Verification

Master verification script: `reproduce/verify_all_headlines.sh`
Per-cell scripts: `reproduce/01_R1_LineageFlow.sh` through `reproduce/07_R6_MNIST_TierAware.sh`
+ `verify_all_headlines.sh` (8 scripts total). All scripts present, byte-stable against
`verification_outputs/` artifacts. Live re-execution commands commented out due to 30min-50h cost.

Last known execution: HEAD ~176c6d4 (Wave 332 freeze).

---

## 10. Final Verdict

**Submission readiness:** NOT READY (4 FAIL blockers).

**Blockers summary:**
- 2 empirical-execution gaps (G-A1 R6 live GPU, G-A4 R5c curve figure)
- 2 paper-writing gaps (G-A6 §2.4 table, G-C5 abstract)

**Path to ready:**
1. Wave 334 paper-edit agent closes G-A6 + G-C5 (~2-3 hours).
2. Wave 335+ GPU agent closes G-A1 (~6 hours GPU).
3. Wave 335 figure agent closes G-A4 (~30 min, data already exists).
4. USER fills G-5 + G-6 + G-8 (cover letter + TNNLS account).
5. Re-run D.4 + 5-gate CI to confirm no regression.
6. Upload via TNNLS Editorial Manager.

**Estimated total time to ready:** ~8-10 hours (parallel: GPU + Wave 334 + USER).

---

**END OF WAVE 335 PHASE 5 VERIFICATION REPORT**