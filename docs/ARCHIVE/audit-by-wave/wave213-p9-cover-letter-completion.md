# Wave 213 P9 — Cover Letter Completion Audit

**Date:** 2026-09-21
**Agent:** Wave 213 P9 cover-letter-completion
**Working dir:** <repo_root>
**Cover letter path:** docs/cover-letter-tpami.md
**Prior state:** §1 Opening · §2 Insight · §3 Validation Scope ·
§4 Headline Numbers · §5 Boundary Disclosure · §6 Reproducibility ·
§7 Suggested AE and Reviewers · §8 Statement of Significance
(8 sections; reviewers listed as 4 anonymised placeholders with no
affiliation or email)

## 1. Scope of this audit

This audit documents the four-section completion of
`docs/cover-letter-tpami.md` requested by the Wave 213 P9 task:
(1) Suitability for TPAMI, (2) Distinction from prior work,
(3) Recommended reviewers (3–5 with affiliations + email
placeholders), (4) Companion-paper status note. The audit also
records the section-renumbering side-effect (cover-letter §2–§8
shifts to §3–§10, and two new sections appear as §2 and §4, with
the companion-paper note appearing as §11) and the reviewer
expansion (4 → 5).

## 2. Sections added

### 2.1 §2 Suitability for TPAMI (NEW, was §2)

Three independent axes aligned with TPAMI's stated mission:

1. **Mathematical foundations of flow matching.** The closed-form
   BL bound (Theorem 1, four-lemma derivation, four paper
   quantities $(A_g, B_g, C_g, e_\rho)$) is the paper's core
   mathematical contribution. TPAMI's history of publishing
   methodological work at the intersection of probability theory,
   optimisation, and generative modelling makes the bound a
   natural fit.

2. **Cross-domain empirical validation.** Six R-level cells
   spanning three generative domains (protein, molecular 3D,
   image) with audit-grade 12-column per-row reporting under
   four pre-registered Bonferroni families, and a first-class
   matched-NFE = 50 boundary disclosure in §7 of the cover
   letter.

3. **Reproducible artifact release.** SHA-256-pinned source-code
   archive (`5b21cca`), Docker recipe (`flowa:tpami-v3.0`),
   Zenodo deposits, 33 D.4 byte-stable regression vectors,
   hash-chained transition log spanning 5155 pytest tests.

The §2 text is ~42 lines (lines 46–90 of the updated
`cover-letter-tpami.md`) and explicitly frames FlowA as "a new
*training-free re-inference* methodological primitive" — the
core positioning claim required by the task.

### 2.2 §4 Distinction from Prior Work (NEW, inserted between §3 Insight and §5 Validation Scope)

Four comparison axes:

1. **Consistency models (CM, sCM, CTM)** — distillation at
   training time vs FlowA's training-free re-inference layer;
   complementary rather than competing approaches.

2. **Reflow / trajectory distillation** — both share with CM the
   training-side investment; FlowA's training-free property puts
   it in a distinct cost class and reframes the optimisation
   target from per-sample trajectory shape to cross-round
   allocation.

3. **Solver-only methods (DPM-Solver++, EDM, UniPC, DEIS)** —
   these optimise per-sample step count; FlowA optimises
   noise-and-step allocation across restart rounds via
   `CodimensionSheetScheduler` (consuming $A_g, B_g, C_g$ →
   `n_cap`), `BoundedMergeOperator` (consuming $e_\rho$ → merge
   envelope noise floor), and `EvidenceDrivenScheduler` (consuming
   the full quadruple → per-cell restart probability).
   Solver-methods have no analogue of the four-quadruple coupling.

4. **Knowledge distillation / step-count compression (DDIM,
   progressive distillation, latent consistency models)** —
   compress step count of a single trajectory; FlowA compresses
   aggregate NFE budget across restart rounds with the paper
   quantities as a regulariser on perturbation magnitude.

The §4 text explicitly states FlowA is "the **first training-free
re-inference framework that consumes convergence-theory paper
quantities as scheduler inputs**" — the load-bearing novelty
claim required by the task.

### 2.3 §9 Suggested Associate Editor and Reviewers (EXPANDED)

Previously: 4 anonymised placeholders with no affiliations or
email addresses. Now: 5 named reviewers with topic, suggested
affiliation, and email placeholder. Each reviewer's mandate is
scoped to a specific empirical or theoretical axis of the
manuscript.

| # | Topic | Suggested affiliation example | Email placeholder |
|---|-------|------------------------------|-------------------|
| 1 | ProbFlow / FM theory (Lipman group) | Meta AI Research / Weizmann | `reviewer1.theory@[institution].edu` |
| 2 | Convergence bound / BL-distance (Vialard / Chewi groups) | Université Gustave Eiffel / LIGM or Yale | `reviewer2.convergence@[institution].edu` |
| 3 | ODE solver / NFE efficiency (Lu DPM-Solver group) | Stanford or Peking University | `reviewer3.solver@[institution].edu` |
| 4 | Protein generation (ESM-IF / LineageFlow / Kanzi authors) | Meta AI / Westlake / Microsoft Research | `reviewer4.protein@[institution].edu` |
| 5 | Statistical rigor | Statistics department with computational-statistics / causal-inference / meta-analysis focus | `reviewer5.stats@[institution].edu` |

The COI section is extended to flag that Reviewer 1 (Lipman
group) and Reviewer 4 (ESM-IF / LineageFlow / Kanzi authors)
overlap with co-author networks in the flow-matching /
protein-generation community, and a final COI sweep will be run
against the TPAMI Editorial Manager database prior to submission.

### 2.4 §11 Companion Paper Status (NEW, before signature)

> The corresponding author is preparing an extended mathematical
> exposition of the bounded-Lipschitz distance bound introduced
> in Theorem 1 of the present manuscript, intended for a separate
> theoretical venue (currently in JMAA / QTDS submission
> deliberation). The companion paper is **not** a prerequisite for
> the present submission: the present manuscript is
> self-contained, and Theorem 1 is restated in §2 of the
> manuscript with a full proof sketch (Lemmas 2–5) and explicit
> computation of the four paper quantities $(A_g, B_g, C_g, e_\rho)$.
> The companion paper will contain only additional theoretical
> depth — sharper rates under weaker assumptions, an
> information-theoretic lower bound, and the connection to
> log-Sobolev and transport-cost inequalities — and will not
> introduce new empirical claims that would alter the present
> paper's headline numbers. The corresponding author will declare
> the companion-paper status in the submission cover sheet and
> on the title page footnote to keep the editorial record
> transparent.

## 3. Section renumbering (side-effect of insertion)

| Old § | New § | Title |
|-------|-------|-------|
| §1 | §1 | Opening — Problem Framing |
| — | §2 | **Suitability for TPAMI** *(NEW)* |
| §2 | §3 | Insight — Paper-Quantity-Driven Scheduling |
| — | §4 | **Distinction from Prior Work** *(NEW)* |
| §3 | §5 | Validation Scope — Six R-Level Cells |
| §4 | §6 | Headline Numbers |
| §5 | §7 | Boundary Disclosure — Matched-NFE = 50 |
| §6 | §8 | Reproducibility — GitHub + Zenodo + Docker |
| §6.1 | §8.1 | Code Availability |
| §7 | §9 | Suggested Associate Editor and Reviewers |
| §8 | §10 | Statement of Significance |
| — | §11 | **Companion Paper Status** *(NEW)* |

All in-cover-letter cross-references were updated: the header
"see §7 below" pointers for AE and reviewers now read "see §9
below", matching the new location of the suggested-AE /
suggested-reviewers block. The §9 reviewer's prose reference to
"the matched-NFE = 50 regression disclosed in §7" intentionally
points to cover-letter §7 (Boundary Disclosure) and is
unambiguous in context. The remaining "§X of the manuscript"
references in §2, §4, and §11 point to the **actual paper**
sections (Theorem 1 lives in manuscript §2; matched-NFE
disclosure lives in manuscript §5; CLM-046 / CLM-057 / 2.5–10×
NFE claim live in manuscript §6) and are correct as written.

## 4. Sanity checks

- `grep -n "^## §" docs/cover-letter-tpami.md` returns 11
  top-level sections + 1 subsection (§8.1), matching the
  renumbering table in §3 above.
- All 5 reviewers appear with explicit topic, suggested
  affiliation, and `reviewerN.topic@[institution].edu` email
  placeholder (verified via `grep -n "Reviewer [1-5] —\|Affiliation:\|Email placeholder:"`).
- The companion-paper note (§11) explicitly names JMAA / QTDS
  as the deliberated venues and states that the present paper is
  self-contained (Theorem 1 restated in manuscript §2 with full
  proof sketch).
- The novelty claim in §4 — "FlowA is the **first training-free
  re-inference framework that consumes convergence-theory paper
  quantities as scheduler inputs**" — appears verbatim in the
  cover letter as required.

## 5. Commit

A single commit will be made capturing the cover-letter completion:

- File: `docs/cover-letter-tpami.md` — added §2, §4, §11;
  expanded §9 to 5 named reviewers with affiliations + email
  placeholders; renumbered §2–§8 → §3–§10; updated header
  cross-references.
- File: `docs/audit/wave213-p9-cover-letter-completion.md` —
  this audit document.
- Commit message:
  `Wave 213 P9: cover letter completion — suitability, distinction, 5 reviewers, companion-paper note`

## 6. Acceptance summary

- `tpami_suitability_section_added`: **true** (new §2)
- `distinction_from_prior_work_section_added`: **true** (new §4)
- `n_recommended_reviewers`: **5** (was 4)
- `reviewers_have_affiliations`: **true** (all 5 have an
  `*Affiliation:*` line with named-institution example and
  "*to be confirmed at submission*" caveat)
- `companion_paper_status_note_added`: **true** (new §11,
  JMAA / QTDS venue named, self-containment of present paper
  stated)
- `cover_letter_path`: `docs/cover-letter-tpami.md`
- `audit_doc_path`: `docs/audit/wave213-p9-cover-letter-completion.md`
