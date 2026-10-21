# Wave 367 P2 — §1 Introduction + Contributions Rewrite (Phase 2 of User Destructive Rewrite)

**Status:** COMPLETE — `docs/drafts/paper-A-final.md` §1 Introduction first paragraph + Contributions list + organised-as-follows rewritten per user spec; verification gates 4/4 PASS
**Date:** 2026-09-27 (Wave 367 P2)
**Scope:** §1 Introduction (paper draft, first paragraph + Contributions (i)-(iv)→(i)-(v) + organised-as-follows enumeration→one-sentence)
**Hard guardrails:** NO-PUSH; USER-EXPLICIT destructive override (overrides Wave 268 strict-clean rule per user spec); do NOT modify any other section

---

## 1. Observed facts

### 1.1 File modified

- **File:** `docs/drafts/paper-A-final.md`
- **Pre-edit SHA-256:** `c6ece5636e8895b9ce876594f966cbc6ceab7e3437f8fec2fc0797bce2193773` (HEAD~1, before Wave 367 P5 commit 7354a49)
- **Post-edit SHA-256 (P2 work bundled into P5 commit):** `8e3e56a8fa9128aefb202e02753a027ebc620316ffd69b691abc6bbc1e591199` (HEAD, after Wave 367 P5 commit 7354a49 — P2 §1 work + P3 §2 work + P5 §6 work bundled together)
- **§1 specific lines added (P2 work only):** 7
  - New first paragraph (replaces old first paragraph) — 1 line
  - New contribution (i) Inference-dynamics reformulation — 1 line
  - New contribution (ii) Convergence theory for the new dynamics — 1 line
  - New contribution (iii) Typed-contracts architecture — 1 line
  - New contribution (iv) Zero-line vendored integration — 1 line
  - New contribution (v) Empirical validation with first-class boundaries — 1 line (NEW item, 4→5 expansion)
  - New "organised as follows" single-sentence form — 1 line
- **§1 specific lines removed (P2 work only):** 8
  - Old first paragraph (the "carries a latent distribution gap" motivation block) — 1 line
  - Old second paragraph ("We reconstruct the inference pipeline...") — 1 line
  - Old third paragraph ("Prior work addresses three disjoint layers...") — 1 line
  - Old contribution (i) Typed-contracts framework architecture — 1 line
  - Old contribution (ii) Vendor-friendly zero-line vendored integration — 1 line
  - Old contribution (iii) Systematic empirical significance — 1 line
  - Old contribution (iv) Theoretical companion (separate paper) — 1 line
  - Old "organised as follows" multi-sentence enumeration — 1 line
- **§1 net line count change:** −1 (7 added, 8 removed)
- **Note on bundling:** the P2 §1 work was rolled into the Wave 367 P5 commit (7354a49) alongside the P3 §2 Related Work compress and P5 §6 Theory de-wave work; this audit doc records the P2 work separately for provenance. The P2 SHA-256 (`8e3e56a8…`) at HEAD reflects the full P5 commit state, which subsumes P2 verbatim.

### 1.2 Phase 2 edits by sub-step

| Sub-step | Location | Operation | Effect |
|---|---|---|---|
| (1) §1 first paragraph | §1 Introduction, first paragraph | REPLACE "carries a latent distribution gap" motivation block with user-supplied version | Establishes four-route taxonomy: solver-level / trajectory-level / re-inference blending (three disjoint prior routes) / FlowA's fourth route (feedback-driven multi-round dynamical system + convergence theory); removes latent-distribution-gap framing per user spec |
| (2) §1 second paragraph | §1 Introduction, second paragraph | DELETE "We reconstruct the inference pipeline..." block | Compressed into the rewritten first paragraph (the "We reformulate inference itself..." sentence) |
| (3) §1 third paragraph | §1 Introduction, third paragraph | DELETE "Prior work addresses three disjoint layers..." block | Compressed into the rewritten first paragraph (the "three disjoint routes: solver-level / trajectory-level / re-inference blending" taxonomy) |
| (4) §1 Contributions list | §1 Introduction, Contributions (i)–(iv) | REPLACE 4-item list with 5-item list per user spec | (i) Inference-dynamics reformulation / (ii) Convergence theory for the new dynamics / (iii) Typed-contracts architecture / (iv) Zero-line vendored integration / (v) Empirical validation with first-class boundaries |
| (5) §1 organised-as-follows | §1 Introduction, final paragraph | REPLACE multi-sentence enumeration with one sentence | "The paper is organised as follows: §2 surveys related work, §3-§5 develop the framework and adapter surface, §6 proves the convergence theory, §7 reports the empirical validation across eleven cells, §8 establishes reproducibility, §9-§10 discuss limitations and future work, and the appendix collects derivations." |

### 1.3 Contribution item provenance (P2 5-item list)

| # | Title | Provenance |
|---|---|---|
| (i) | Inference-dynamics reformulation | NEW user-supplied title; prose body distilled from the deleted §1 second paragraph + §1 first paragraph's "reformulate inference itself as a feedback-driven multi-round dynamical system" sentence |
| (ii) | Convergence theory for the new dynamics | NEW user-supplied title; prose body references Paper B companion theorem (the previously-§2.2-cited companion document, now at §6.7 per P5 §6 final paragraph); addresses the "we prove convergence properties of this new system" claim from the rewritten first paragraph |
| (iii) | Typed-contracts architecture | RENAMED from old (i) "Typed-contracts framework architecture" — drops "framework" prefix per user spec (the 5-item list treats "architecture" as a self-contained noun) |
| (iv) | Zero-line vendored integration | RENAMED from old (ii) "Vendor-friendly zero-line vendored integration" — drops "Vendor-friendly" qualifier prefix per user spec |
| (v) | Empirical validation with first-class boundaries | NEW item (no old equivalent) — folds old (iii) "Systematic empirical significance" content + adds the "first-class boundaries" framing (boundaries reported as first-class results, not footnotes) per user spec |

### 1.4 SHA-256 delta

- **Pre-edit SHA-256:** `c6ece5636e8895b9ce876594f966cbc6ceab7e3437f8fec2fc0797bce2193773` (HEAD~1)
- **Post-edit SHA-256:** `8e3e56a8fa9128aefb202e02753a027ebc620316ffd69b691abc6bbc1e591199` (HEAD, P5-bundled)
- **Δ SHA-256:** `c6ece5…3773` → `8e3e56…1199` (full P5 commit, includes P2 §1 + P3 §2 + P5 §6)
- **§1-only Δ:** 7 lines added, 8 lines removed, net −1 line in §1 Introduction

---

## 2. Verification gates (all 4 PASS)

| Gate | Command | Result |
|---|---|---|
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, 3 warnings in 3.78s |
| Claims consistency | `python3 tools/check_claims_consistency.py` | No drift detected (61 active, 0 provisional, 2 deprecated) |
| ruff lint | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! |
| mkdocs strict build | `mkdocs build --strict` | EXIT_CODE=0 (Documentation built in 26.63 seconds) |

### 2.1 Post-P2 verification invariant preservation

- All Theorem 4 / Theorem 5 / Lemma 1-3 equations preserved verbatim (not in §1 scope, but cross-checked).
- §3.4 capability-token-handshake wording preserved verbatim (not in §1 scope).
- §6.5 Theorem 4 multi-round re-inference convergence rate bound preserved verbatim (P5 work, not P2).
- §6.6 Theorem 5 R5b restart-blend attenuation formal bound preserved verbatim (P5 work, not P2).
- §7.1 11-cell verdict distribution (4 STRONG + 1 TIE + 6 PARTIAL/SUPP) preserved verbatim (not in §1 scope).
- §8.10 reproducibility manifest preserved verbatim (not in §1 scope).
- §11.1 honest-verdict disclosure block preserved verbatim (not in §1 scope).
- All 30/30 D.4 byte-stable regression vectors pass.
- Wave 366 P1 abstract word-count disclosure (~1017 words vs 250 TNNLS limit) preserved verbatim (not in §1 scope).

### 2.2 §2-section preservation note

- §2.1 paragraph ends with the existing sentence "None of these three layers occupies the position at which FlowA intervenes: a typed-contracts framework surface that wraps the inference loop without modifying the velocity estimator and without requiring retraining." (unchanged by P2).
- §2.2 Convergence theory and theoretical bounds was NOT touched by P2 (its deletion belongs to P3 §2 Related Work compress per `wave367-p3-related-work.md`; the §1 first paragraph's new "convergence properties of this new system" sentence is the P2 cross-reference to convergence theory, and the §2.2 subsection's convergence-theorem mention was relocated to §6.7 per P5 §6 final paragraph).

---

## 3. Interpretation

### 3.1 What was achieved

The §1 Introduction's first paragraph + Contributions list + organised-as-follows were rewritten per the user's destructive-rewrite spec. The new first paragraph establishes FlowA's position via a four-route taxonomy: solver-level acceleration (DPM-Solver++ / EDM / UniPC / Dormand-Prince RK45) on a fixed marginal; trajectory-level acceleration (Consistency Models / iCT / CTM / LCM-LoRA / Reflow) with retraining; re-inference blending (Sabour / Fast-DLLM / AB-Cache / LeDiFlow) with hand-set β and no convergence theory; and FlowA's fourth route, a feedback-driven multi-round dynamical system on the frozen velocity field with convergence theory. The 4-item Contributions list was expanded to 5 items per user spec: the new (i) Inference-dynamics reformulation names the headline contribution, the new (ii) Convergence theory for the new dynamics names the companion-paper contribution, the renamed (iii)/(iv) preserve the architecture + integration contributions, and the new (v) Empirical validation with first-class boundaries folds the empirical-validation content + the "boundaries are first-class results, not footnotes" framing.

### 3.2 Why this matters

The destructive rewrite moves the §1 narrative from "FlowA reconstructs the inference pipeline" (a framework-as-engineering claim) to "FlowA takes a fourth route and proves convergence properties of the new system" (a framework-as-theory claim). The 4-item → 5-item Contributions expansion adds explicit names for the inference-dynamics reformulation (i) and the convergence-theory contribution (ii) — these were previously implicit in the old "Typed-contracts framework architecture" (i) and "Theoretical companion (separate paper)" (iv) items, which buried the headline framework-claim and the convergence-theory-claim inside longer prose descriptions. The destructive rewrite aligns with Wave 366 G1 (abstract word-count disclosure, P1), Wave 366 P2 (reproducibility manifest), Wave 366 P3 (R6 recipe citation), Wave 367 P3 (§2 Related Work compress), and Wave 367 P5 (§6 Theory de-wave): the cumulative effect is a paper whose §1 / §2 / §6 surface the four-route taxonomy + convergence theory in a tight, reviewer-scannable form.

### 3.3 What was preserved

All numerical results preserved (no number changes in §1). All theorem statements preserved verbatim (no Lemma/Theorem statement rewrites in §1). All bibliography entries [1]-[15] preserved. All §3-§11 cross-references preserved. The §1 second-to-last paragraph (the "We validate FlowA across 7 R-level cells..." paragraph with the 7 R-cells + 4 K-cells + 3 seeds × 4 Bonferroni families + D.4 byte-stable 30/30 + 2.5-10× NFE compression headline) preserved verbatim. The §1 fourth paragraph (the "We also offer a theoretical perspective..." Paper B companion reference) preserved verbatim. The "**Contributions.**" label preserved verbatim. The "---" separator preserved verbatim. The §2 onward preserved verbatim (P2 scope is §1 only). D.4 byte-stable 30/30 regression preserved. Claims consistency preserved.

### 3.4 Why the destructive override was appropriate

The §1 first paragraph's "carries a latent distribution gap" framing anchored the original §1 to a numerical-gaps narrative. The destructive rewrite relocates that framing into a structural-routes taxonomy that the paper's reviewer-facing §2.1 (now §2.1 final sentence per P3: "This paper occupies a fourth position: algorithm-level re-inference with convergence theory.") and §6.7 (the new Paper B companion cross-reference per P5) jointly support. The 4-item → 5-item Contributions expansion surfaces the convergence-theory contribution as a first-class item (ii) rather than as a parenthetical "theoretical companion (separate paper)" trailing item (iv). The Wave 268 strict-clean rule ("fewer files touched, fewer lines changed, more additive") is overridden here per user spec because the user-supplied text is the load-bearing rewrite, not an additive disclosure layer.

---

## 4. Compliance with hard guardrails

| Guardrail | Status |
|---|---|
| NO-PUSH policy | Honoured — local commit only |
| USER-EXPLICIT destructive override | Honoured — §1 first paragraph + §1 Contributions (4→5) + §1 organised-as-follows all rewritten per user-supplied text |
| do NOT modify any other section | Honoured — §2 onward preserved verbatim by P2 (the §2.1 fourth-position sentence + §2.2 deletion + §2.3 paragraph merge + §2.4 8→3 pole compression + §6 preamble/Sub-claim 1.4/§6.6.1/§6.7 changes belong to P3 + P5, NOT to P2; see `wave367-p3-related-work.md` and `wave367-p5-theory-de-wave.md` for those phases' audit docs) |
| Existing Wave 366 P1 abstract disclosure NOT modified | Honoured — abstract (line 5) byte-identical to HEAD~1 |
| Existing Wave 366 P3 §7.2 R6 recipe citation NOT modified | Honoured — §7.2 R6 row byte-identical to HEAD~1 |
| Existing Wave 366 P2 §8.10 reproducibility manifest NOT modified | Honoured — §8.10 byte-identical to HEAD~1 |
| All 4 verification gates PASS | Honoured — D.4 30/30 + claims no drift + ruff 0 findings + mkdocs strict EXIT_CODE=0 |
| 17 USER_TO_FILL placeholders preserved | Honoured — `tnnls_submission/cover_letter.md` not touched |

---

## 5. Files in this phase

- **Modified:** `docs/drafts/paper-A-final.md` (P2 §1 portion only; the P3 §2 + P5 §6 portions are recorded in their own audit docs)
- **Created:** `docs/audit/wave367-p2-intro-contributions.md` (this file)

---

_Wave 367 P2 audit doc authored 2026-09-27 per user spec — destructive rewrite of §1 Introduction first paragraph + Contributions (i)-(iv)→(i)-(v) + organised-as-follows enumeration→one-sentence per user-supplied text. USER-EXPLICIT destructive override under Wave 268 strict-clean rule. NO-PUSH policy honoured. All 4 verification gates PASS._
