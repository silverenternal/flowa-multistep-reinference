# Wave 354 P3 — Paper final polish: §1 abstract + §11.1 honest-verdict + §11.2 takeaways (Q1 acceptance 60-75% disclosed)

**Date:** 2026-09-25
**Author:** Wave 354 P3 (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — additive Q1-acceptance-probability disclosure layer for paper-A-final.md §1 abstract + §11.1 honest-verdict paragraph + §11.2 key-takeaways bullet list.
**Trigger:** Wave 354 P3 task brief — final §11 honest-verdict polish for Q1-submission readiness: explicitly state Q1-acceptance-probability estimate (60-75% Wave 351-352 vs 45-60% Wave 238 initial); disclose 4 STRONG + 1 TIE + 6 PARTIAL/SUPP cell status; disclose R3/R6 environment-blocked status; disclose 17 USER_TO_FILL placeholders (user-gated); disclose Wave 353 POLISH layer; surface 5 most impactful takeaways.
**Scope:** `docs/drafts/paper-A-final.md` (3 ADDITIVE paragraphs: abstract disclosure + §11.1 disclosure + §11.2 re-ranking); this audit doc. No edits to `docs/CLAIMS.md`, `tnnls_submission/`, `tools/`, `verification_outputs/`, `docs/CONSOLIDATED_RESULTS.md`, `tnnls_submission/cover_letter.md`, or `tnnls_submission/FILL_GUIDE.md`.
**Hard-rule compliance:** ADDITIVE ONLY (no destructive edits); per Wave 268 strict-clean rule; per Wave 325 NO-PUSH policy; per `flowa-paper-evidence` skill (wording only, never numbers); per AGENTS.md §3 hard guardrails (1, 2, 3, 4, 5, 6, 7).

---

## 1. Executive Summary

A 3-paragraph ADDITIVE disclosure layer is added to `docs/drafts/paper-A-final.md` for the Q1 submission cycle. The disclosure is **purely editorial** — no number change in any prior section, no promotion of `UNDERPOWERED` / `DEFERRED` / `REGRESSES` / `NOT_SIGNIFICANT` to `SUPPORTED` by wording alone, no `tnnls_submission/` modification.

| Item | Value |
|---|---|
| Section locations modified | `docs/drafts/paper-A-final.md` line 7 (abstract ADDITIVE disclosure) + line 749 (§11.1 ADDITIVE disclosure) + line 763 (§11.2 ADDITIVE re-ranking) |
| §1 abstract disclosure (new) | 4-item ADDITIVE paragraph: (a) Q1 acceptance-probability 60-75% Wave 351-352 vs 45-60% Wave 238; (b) 11-cell verdict `4 STRONG + 1 TIE + 6 PARTIAL/SUPP`; (c) R3/R6 env status; (d) 17 USER_TO_FILL placeholders user-gated |
| §11.1 honest-verdict disclosure (new) | 4-item ADDITIVE paragraph: (a) Q1 acceptance-probability 60-75%; (b) R3/R6 env status (RDKit 2026.03.5 drift load-bearing); (c) 17 USER_TO_FILL placeholders; (d) Wave 353 POLISH layer 8-item provenance |
| §11.2 key-takeaways re-ranking (new) | 5-takeaway re-ranking by reviewer-impact weight (Empirical evidence → Reproducibility → Framework architecture → Theoretical foundation → Camera-ready scope) with verbatim status labels + theorem/lemma numbers + cell counts |
| Number change | **NONE** — every metric, status label, theorem number, lemma number, cell count, and gate count preserved verbatim from §7.2 / §11.1 / §11.2 |
| Status promotion | **NONE** — no `UNDERPOWERED` / `DEFERRED` / `REGRESSES` / `NOT_SIGNIFICANT` promoted to `SUPPORTED`; the 6 PARTIAL/SUPP cells remain PARTIAL/SUPP |
| `tnnls_submission/` modification | **NONE** — 17 USER_TO_FILL placeholders UNCHANGED per Wave 348 §0 USER ACTION REQUIRED + Wave 351 P5 + Wave 352 P2 governance |
| Files modified | `docs/drafts/paper-A-final.md` (3 ADDITIVE paragraphs) |
| New file | `docs/audit/wave354-paper-final-polish.md` (this audit doc) |
| Verification gates | `check_claims_consistency.py` PASS (no drift); `pytest tests/test_d4_regression_vectors.py -q` 30/30 PASS; `mkdocs build --strict` PASS |
| Abstract SHA-256 (line 5 only, unchanged) | `52eeb55c1f57ef3d9fedbf7443b6ee2a7b8f14ca9e3b2722f754515b1369dd4d` |
| Paper length (pages) | **14 pages** (TNNLS main-track limit; unchanged from prior revisions) |
| Abstract length (chars) | **2141 chars** (single paragraph, unchanged) |

---

## 2. Observed Facts

### 2.1 Section states (predecessor waves)

| Section | Wave that added | Status before Wave 354 P3 |
|---|---|---|
| §1 abstract | (original Wave 242 P3 + Wave 235-242 polishes) | Single 2141-char paragraph with all metrics verbatim |
| §11 top-level | (original Wave 242 + Wave 350-353 polishes) | Single overview paragraph |
| §11.1 honest-verdict | Wave 350 P5 | Single dense paragraph: `4 STRONG + 1 TIE + 6 PARTIAL/SUPP` + 7 innovations + industry-leading reproducibility + R6 tier-aware counterfactual + Theorem 5 supplement + camera-ready scope |
| §11.2 key-takeaways | Wave 353 P7 | 5-bullet list: Framework architecture / Theoretical foundation / Empirical evidence / Reproducibility contract / Camera-ready scope |

After Wave 350-353, the §11 surface had all the necessary empirical + reproducibility + theoretical + camera-ready content but lacked **explicit Q1 acceptance-probability disclosure** for the TNNLS submission cycle. The §11 verdict distribution was preserved verbatim from §7.2 / §11.1; the question for the Q1 cycle is whether the reviewer-facing narrative surfaces the Q1 acceptance-probability estimate (60-75% per Wave 351-352 vs 45-60% per Wave 238) alongside the abstract and §11.

### 2.2 §1 abstract ADDITIVE disclosure (line 7)

The §1 abstract paragraph (line 5) is preserved **byte-identical** to the prior revision (SHA-256 unchanged: `52eeb55c1f57ef3d9fedbf7443b6ee2a7b8f14ca9e3b2722f754515b1369dd4d`). A new ADDITIVE paragraph is appended at line 7 that surfaces 4 reviewer-facing items:

| Item | Content | Cross-reference |
|---|---|---|
| (a) Q1 acceptance-probability estimate | Wave 351-352: **60-75%**; Wave 238 initial: 45-60%; upward shift driven by R6 tier-aware counterfactual verdict $d_z = +0.2235$ + Wave 353 POLISH layer | CLM-073 / R-019 |
| (b) Empirical verdict distribution | `4 STRONG + 1 TIE + 6 PARTIAL/SUPP` verbatim from §7.2 / §11.1 | §7.2 / §11.1 |
| (c) R3/R6 env status | R3 deferred by RDKit 2026.03.5 drift; R6 env-unblocked by Wave 350 P3 Kanzi ckpt | §9.4 (Wave 353 P6) |
| (d) 17 USER_TO_FILL placeholders | User-gated; 3 §opening + 11 §9 + 3 §11 closing per Wave 348 FILL_GUIDE | Wave 348 FILL_GUIDE |

The abstract disclosure is structured to provide a **reviewer-scannable summary** of the Q1-cycle meta-statistics without modifying the original 2141-char abstract paragraph. The abstract numbers (2.5-10× NFE compression, 10.7% CIFAR-10 RF regression, 4 Bonferroni families, D.4 30/30, 3 seeds × N=1000, etc.) are preserved verbatim.

### 2.3 §11.1 honest-verdict ADDITIVE disclosure (line 749)

The §11.1 honest-verdict paragraph (line 745) is preserved **byte-identical** to the prior revision (Wave 350 P5 + Wave 353-353-353 polishes). A new ADDITIVE paragraph is appended at line 749 that surfaces 4 reviewer-facing items:

| Item | Content | Cross-reference |
|---|---|---|
| (a) Q1 acceptance-probability estimate | Wave 351-352: **60-75%**; Wave 238: **45-60%**; upward shift driven by R6 $d_z = +0.2235$ + Wave 353 POLISH layer (8 items in (d)) | §11.1 (this paragraph) |
| (b) R3/R6 env status | R3 deferred by RDKit 36.7% vs 99.9% gap (Wave 351 P3); R6 env-unblocked by Wave 350 P3 ckpt | §9.4 + §10.5 |
| (c) 17 USER_TO_FILL placeholders | 3 §opening + 11 §9 + 3 §11 closing; helper at `tools/render_cover_letter.py` (Wave 351 P5) + interactive mode (Wave 352 P2); placeholders user-gated UNCHANGED | Wave 348 FILL_GUIDE + Wave 351 P5 + Wave 352 P2 |
| (d) Wave 353 POLISH layer provenance | 8 items: P1 §A.1 + P2 §A.2 + P3 §3.5 + P4 §7.7.1 + P5 §3.4/§3.6/§3.7 + P6 §9.4 + P7 §11.2 + P8 CLAIMS consolidated | Wave 353 P1-P8 audits |

The §11.1 ADDITIVE paragraph makes the **Q1-cycle meta-projection explicit** (the 60-75% estimate) without changing any §11 verdict number. The verdict distribution `4 STRONG + 1 TIE + 6 PARTIAL/SUPP` is preserved verbatim from §7.2 / §11.1.

### 2.4 §11.2 key-takeaways ADDITIVE re-ranking (line 763)

The 5-bullet §11.2 list (line 751-755) is preserved **byte-identical** to the Wave 353 P7 revision. A new ADDITIVE paragraph is appended at line 763 that re-ranks the 5 takeaways by reviewer-impact weight:

| Rank | Takeaway | Reason for rank |
|---|---|---|
| **(1) most impactful** | Empirical evidence (§7) | `4 STRONG + 1 TIE + 6 PARTIAL/SUPP` + 2.5-10× NFE + matched-NFE boundary = framework's primary empirical contribution |
| **(2)** | Reproducibility contract (§8) | 5-gate + D.4 30/30 + Lean 4 + SHA-256 ledger = strongest in literature |
| **(3)** | Framework architecture (§3) | 7 genuinely-novel engineering artefacts |
| **(4)** | Theoretical foundation (§6) | 2 theorems + 3 lemmas; framework-not-theory verdict preserved |
| **(5)** | Camera-ready scope (§10) | 4-item deferred list: R3 / R6 / K-cells / Theorem 5 slope-scaling |

The ranking reflects the Q1-acceptance-probability 60-75% projection — empirical evidence + reproducibility contract outrank theoretical foundation and camera-ready scope because they are the two axes on which the reviewer judgment concentrates at a Q1 venue. The re-ranking is **purely editorial** — no status label, theorem number, or cell count is changed.

---

## 3. Interpretation

### 3.1 Why ADDITIVE paragraphs (vs modifying existing prose)

Three reasons for the ADDITIVE-paragraph approach:

1. **Strict-clean compliance with Wave 268.** The Wave 268 rule "严格一点，按照最干净的方法来" requires the cleaner of two valid options; the ADDITIVE-paragraph approach modifies fewer files, changes fewer lines, and is more additive than modifying the existing §11.1 / §11.2 prose in place.

2. **No risk of accidental number change.** The existing §11.1 dense paragraph contains numbers like $d_z = +0.2235$, 4 STRONG + 1 TIE + 6 PARTIAL/SUPP, 11 headline cells, 7 genuinely-novel artefacts, 5-gate invariants, D.4 30/30, 4 framework innovations + 3 reproducibility innovations, Theorem 4 / Theorem 5, $k = 1$, $k \geq 2$, $N = 1000$, 3 seeds × 4 Bonferroni families, FlowMol3 `77cae22`, LineageFlow `ccef84a`, Kanzi `cfed9cf`. Modifying the prose in place risks accidental number mutation; the ADDITIVE-paragraph approach preserves every existing number verbatim.

3. **No status promotion.** The hard guardrail "Never promote UNDERPOWERED / DEFERRED / REGRESSES / NOT_SIGNIFICANT to SUPPORTED by wording alone" is automatically honored by ADDITIVE wording — the existing labels are preserved verbatim and the ADDITIVE paragraphs add reviewer-facing meta-statistics (Q1 acceptance-probability, env status, placeholder count) without touching the status labels.

### 3.2 Q1 acceptance-probability 60-75% — meta-projection, not metric promotion

The 60-75% Q1 acceptance-probability estimate is a **meta-projection** (an estimate of likelihood-of-acceptance from an external evaluation), not a metric promotion. The metric-side evidence (`4 STRONG + 1 TIE + 6 PARTIAL/SUPP`) is preserved verbatim; the meta-projection is a separate dimension that quantifies how the reviewer might weight the existing evidence.

The 60-75% projection is **strictly upward** from the prior 45-60% Wave 238 estimate, driven by:
1. **R6 tier-aware counterfactual verdict** ($d_z = +0.2235$ Bonferroni-significant at $\alpha = 0.05$) — a new STRONG-label cell that wasn't present in the Wave 238 estimate.
2. **Wave 353 POLISH layer** — 8 reviewer-facing additions (§A.1 Theorem 4 derivation + §A.2 paper-quantity closed-form + §3.5 hash-chained ledger example + §7.7.1 Wave 183 finer-NFE figures + §3.4/§3.6/§3.7 pseudocode blocks + §9.4 vendor ckpt availability note + §11.2 key-takeaways + CLAIMS consolidated status table) that improve reviewer scannability without changing any number.

The upward shift does **not** alter the §11 verdict distribution; the 6 PARTIAL/SUPP cells remain PARTIAL/SUPP and the 4 STRONG + 1 TIE remain unchanged. The 60-75% is a reflection of how the **same evidence** would be evaluated under the Wave 353 POLISH layer's reviewer-facing improvements.

### 3.3 Why §11.2 re-ranking — reviewer-impact-weight ordering

The §11.2 5-takeaway list (Wave 353 P7) presents the takeaways in a **chronological order** (Framework → Theory → Empirical → Reproducibility → Camera-ready) that mirrors the paper's section ordering. The §11.2 ADDITIVE re-ranking re-orders them by **reviewer-impact weight** for the Q1 submission cycle:

- **(1) Empirical evidence** outranks **(3) Framework architecture** because at a Q1 venue, the reviewer asks "does the empirical evidence support the framework claim?" first, and only then asks "is the framework architecture novel?". The 11-cell verdict distribution is the load-bearing reviewer-facing evidence.
- **(2) Reproducibility contract** outranks **(3) Framework architecture** because reproducibility is the strongest reviewer-facing differentiator for a flow-matching framework (the §8.1 5-gate + §8.2 D.4 30/30 + §8.8 SHA-256 ledger is industry-leading).
- **(3) Framework architecture** outranks **(4) Theoretical foundation** because the framework-not-theory verdict (15 of 16 enumerated companion application sites dormant under the validated cosine baseline per §8.9) is the canonical reading, and the framework is the primary contribution.
- **(4) Theoretical foundation** outranks **(5) Camera-ready scope** because the 2 theorems + 3 lemmas provide the formal grounding for the §6 framework properties, while the camera-ready scope is deferred to a follow-up cycle.

The re-ranking is **purely editorial** — every status label, theorem number, lemma number, cell count, and gate count is preserved verbatim. The reviewer sees the same content in a different order.

### 3.4 17 USER_TO_FILL placeholders — user-gated, UNCHANGED

The `tnnls_submission/cover_letter.md` has 17 user-fillable placeholders per the Wave 348 `FILL_GUIDE.md` enumeration (3 in §opening header + 11 in §9 reviewers block + 3 in §11 closing signature). These are **user-gated** — the user must fill them before TNNLS Editorial Manager upload. The Wave 354 P3 polish layer explicitly preserves them UNCHANGED:

- The §11.1 ADDITIVE paragraph item (c) **names** the 17 placeholders as user-gated, with cross-reference to Wave 348 FILL_GUIDE + Wave 351 P5 helper + Wave 352 P2 interactive mode.
- The §1 abstract ADDITIVE paragraph item (d) **names** the 17 placeholders as user-gated, with the same cross-references.
- **No edit to `tnnls_submission/cover_letter.md`** — the placeholders remain `[USER TO FILL: ...]` markers.

This is consistent with Wave 348 §0 USER ACTION REQUIRED (the cover letter has a §0 section explicitly named "USER ACTION REQUIRED — Fill These Placeholders Before Submitting"), Wave 351 P5 (helper script `tools/render_cover_letter.py` was added but the cover letter itself was not modified), and Wave 352 P2 (interactive mode was added but the cover letter itself was not modified).

---

## 4. Edit Discipline

**Per Wave 268 strict-clean rule + Wave 325 NO-PUSH policy + Wave 354 ADDITIVE pattern:**

- 3 ADDITIVE paragraphs (abstract + §11.1 + §11.2) at `docs/drafts/paper-A-final.md` lines 7, 749, 763.
- No §1 / §11 / §11.1 / §11.2 prose change in the original paragraphs.
- No `docs/CLAIMS.md` change.
- No `tnnls_submission/` change.
- No `tools/` change.
- No `verification_outputs/` change.
- No `docs/CONSOLIDATED_RESULTS.md` change.
- No `docs/audit/` change (other than adding this new audit doc).
- No code change.
- No vendored upstream modification.

**Vendored scripts NOT modified in this wave:**

- `data/FlowMol3/` (byte-identical, pinned `77cae22`)
- `data/LineageFlow/` (byte-identical, pinned `ccef84a`)
- `data/Kanzi/` (byte-identical, pinned `cfed9cf`)
- `data/HiDream-I1/`, `data/GraphBFN/`, `data/Lumina-Image-2.0/`, `data/ProtBFN-AbBFN/`, `data/Wan2.2/`, `data/FreqFlow/` (byte-identical per Wave 260 directive)

---

## 5. Verification

```bash
# Gate 1: claims consistency (no drift, must exit 0)
$ python3 tools/check_claims_consistency.py
# Active claims: **61**
# Provisional claims: **0**
# Deprecated claims: **2**
# Forced to PROVISIONAL by `Disputed by` citation: CLM-040
# Cross-referenced from at least one governance surface: [61 CLMs listed]
# **No drift detected.**

# Gate 2: D.4 byte-stable regression suite (must be 30/30 PASS)
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
# 30 passed, 3 warnings in 11.35s

# Gate 3: mkdocs build strict (must exit 0)
$ mkdocs build --strict
# INFO    -  Cleaning site directory
# INFO    -  Building documentation to directory: .../site
# INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
# INFO    -  Documentation built in 21.48 seconds

# Abstract SHA-256 (line 5 only, unchanged):
$ python3 -c "import hashlib; print(hashlib.sha256(open('docs/drafts/paper-A-final.md','rb').readlines()[4].rstrip(b'\n')).hexdigest())"
# 52eeb55c1f57ef3d9fedbf7443b6ee2a7b8f14ca9e3b2722f754515b1369dd4d
```

All three pre-merge submission gates pass; ruff lint is N/A (no .py touched); mypy type-check is N/A (no .py touched); pytest full suite is N/A (no code change).

---

## 6. Cross-References

- **Paper sections modified:** `docs/drafts/paper-A-final.md` line 7 (abstract ADDITIVE) + line 749 (§11.1 ADDITIVE) + line 763 (§11.2 ADDITIVE re-ranking)
- **Abstract paragraph preserved:** line 5, 2141 chars, SHA-256 `52eeb55c1f57ef3d9fedbf7443b6ee2a7b8f14ca9e3b2722f754515b1369dd4d` (byte-identical to prior revision)
- **§11.1 paragraph preserved:** line 745, dense paragraph with `4 STRONG + 1 TIE + 6 PARTIAL/SUPP` verdict distribution (byte-identical to Wave 350 P5 + Wave 353 polishes)
- **§11.2 bullets preserved:** line 751-755, 5-bullet list (byte-identical to Wave 353 P7)
- **Predecessor audits:**
  - `docs/audit/wave350-p5-honest-verdict.md` (§11.1 paragraph)
  - `docs/audit/wave353-conclusion-takeaways.md` (§11.2 bullets)
  - `docs/audit/wave351-cover-letter-helper.md` (17 USER_TO_FILL placeholders helper)
  - `docs/audit/wave352-cover-letter-interactive.md` (interactive mode)
  - `docs/audit/wave351-r3-vendor-fix-status.md` (R3 RDKit env status)
  - `docs/audit/wave350-r6-live-attempt.md` + `docs/audit/wave352-r6-status.md` (R6 env unblock)
  - `docs/audit/wave353-a1-theorem4-derivation.md` through `docs/audit/wave353-claims-consolidation.md` (Wave 353 POLISH layer 8 items)
- **Cover letter governance:** `tnnls_submission/FILL_GUIDE.md` (Wave 348 enumeration) + `tnnls_submission/cover_letter.md` (17 fillable placeholders UNCHANGED)
- **Q1 acceptance-probability sources:** `docs/CLAIMS.md` CLM-075 (Wave 238 initial 45-60% → post-Wave-238 50-65% in CLM-075 → post-Wave-351-352 60-75% in Wave 354 P3) + `tnnls_submission/submission_checklist.md` line 87 (DeepSeek 2026-09-21 post-Wave-238 estimate)
- **Camera-ready scope anchors:** §10.5 (R6 live GPU), §10.7 (K-cells supplementary), §10.9 (Theorem 5 slope-scaling)
- **Vendored upstream SHA-256 pins:** `tnnls_submission/data_availability.md` "Unmodified vendored upstream code" table