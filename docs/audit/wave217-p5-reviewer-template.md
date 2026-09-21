# Wave 217 P5 — TPAMI E3 Reviewer Template (email + affiliation + COI)

**Date:** 2026-09-21
**Wave:** Wave 217 P5
**Owner:** framework maintainer
**Source directive:** DeepSeek TPAMI pre-submission checklist
(priority E3 — "Cover letter 5 reviewers 邮箱 + 领域 + 无利益冲突确认").

## Goal

The TPAMI cover letter §9 already enumerates five suggested reviewers
with affiliation suggestions and email placeholders. To make the
submission workflow unambiguous (and to satisfy the DeepSeek E3
"邮箱 + 领域 + 无利益冲突" requirement), this audit document
consolidates those placeholders into a structured table with explicit
fields and adds an explicit **Conflict of Interest (COI) disclosure
statement** the corresponding author can copy verbatim into the
Editorial Manager submission.

All placeholders below remain placeholders; the corresponding author
will confirm or substitute concrete names, affiliations, and email
addresses at submission time using the TPAMI Editorial Manager
reviewer-suggestion interface.

## Source

`docs/cover-letter-tpami.md` §9 (lines 322–411 in the
post-Wave-217-P4 revision). The cover letter text uses inline
"reviewer N — expertise ... affiliation suggested" prose; this audit
doc restates the same information as a table for templating.

## Reviewer template table

| # | Name (placeholder) | Affiliation (placeholder) | Email format | Expertise (audit anchor) |
|---|---|---|---|---|
| 1 | **ProbFlow / flow-matching theory expert** (Lipman group or equivalent) | Meta AI Research (ProbFlow team) **or** Weizmann Institute of Science | `reviewer1.theory@<institution>.edu` | Theorem 1 self-contained statement (Lemmas 2–5), the g-independent rate corollary, the four paper quantities $(A_g, B_g, C_g, e_\rho)$ and their typed evaluators in `adaptive_reflow/theory/paper_quantities.py`; FM convergence bound |
| 2 | **Convergence bound / BL-distance expert** (Vialard or Chewi group or equivalent) | Université Gustave Eiffel / LIGM (Vialard) **or** Yale University (Chewi) | `reviewer2.convergence@<institution>.edu` | BL upper bound `BL(μ_{g,ε}, ν_g) ≤ A_g · exp(−NFE / B_g) + C_g · e_ρ`; g-independent rate `BL(μ_{g,ε}, ν_g) ≤ ε · √(2/π)`; bounded-Lipschitz / Wasserstein convergence theory |
| 3 | **ODE solver / NFE-efficiency expert** (Lu DPM-Solver group or equivalent) | Stanford University (Lu group) **or** Peking University | `reviewer3.solver@<institution>.edu` | Solver-agnostic stack (Euler, Heun, DPM-Solver++, Dormand–Prince RK45, CTMC, BFN); 2.5–10× cross-budget NFE compression claim (CLM-046); matched-NFE = 50 regression (§7 boundary) |
| 4 | **Protein generation expert** (ESM-IF / LineageFlow / Kanzi author lists or equivalent) | Meta AI (ESM-IF / EvolutionaryScale LineageFlow) **or** Westlake University / Microsoft Research (Kanzi) | `reviewer4.protein@<institution>.edu` | Protein-axis R-cells (R1 LineageFlow HMMER, R2 Kanzi inv-proj, R6 k6 foldability pLDDT + scPerplexity); cluster-robust Pfam-family re-analysis (df_cluster=3, ICC=0.041, N_eff=89.6); cross-adapter monotone `hard > medium > easy` pLDDT pattern (k6 hard d_z = +1.189, LineageFlow hard d_z = +1.840) |
| 5 | **Statistical rigor expert** (applied statistics / pre-registration / multiple-testing) | A statistics department with a computational-statistics / causal-inference / meta-analysis focus (university to be confirmed) | `reviewer5.stats@<institution>.edu` | 12-column audit-grade per-row reporting (`n_paired, mean_diff, sd_diff, t, df, p_raw, CI95_low, CI95_high, d_z, test_type, family, α_bonferroni, bonf_sig`); four pre-registered Bonferroni families (k=7 / k=6 / k=16 / k=5); cluster-robust re-analysis; effect-size sign consistency across adapters (k6 d_z range [−1.077, −1.138]; LineageFlow d_z range [−1.002, −1.044]) |

### Notes on placeholder names

All five reviewer slots are listed as **expertise-based placeholders**
in the table above; the corresponding author will substitute concrete
names (drawn from the suggested author groups: Lipman, Vialard, Chewi,
Lu, ESM-IF / LineageFlow / Kanzi authors, and a statistics department
of the author's choosing) before submission. The placeholder wording
"Peer X from the Y group or equivalent" preserves anonymity in this
template while still anchoring each reviewer to the appropriate
research community.

### Notes on email format

The `reviewer<N>.<expertise>@<institution>.edu` pattern is a
deliberate placeholder convention — these are NOT real email
addresses. The corresponding author will replace both `<N>` and
`<institution>` with concrete values from the Editorial Manager
reviewer-suggestion interface at submission time. No real contact
information is leaked in this audit document.

## Conflict of Interest (COI) disclosure statement

The following COI statement is intended to be copied verbatim into the
TPAMI Editorial Manager submission form (in the field labelled
"Conflict of interest for suggested reviewers"). It supplements the
shorter COI paragraph already present in `docs/cover-letter-tpami.md`
§9 (lines 402–411).

> **Conflict of interest disclosure (for suggested reviewers).** The
> corresponding author has reviewed the suggested reviewer list against
> the following COI criteria, as required by the TPAMI Editorial
> Manager submission form:
>
> 1. **No co-authorship.** None of the five suggested reviewers is a
>    co-author of the present manuscript, of any companion paper by
>    the corresponding author, or of any paper currently in
>    preparation with the corresponding author.
> 2. **No recent collaboration (past 24 months).** None of the five
>    suggested reviewers has co-authored a paper, a workshop
>    proceedings, a publicly archived preprint, or a funded grant
>    proposal with the corresponding author within the 24 months
>    preceding submission.
> 3. **No advisor / advisee relationship.** None of the five suggested
>    reviewers is, or has ever been, the doctoral or postdoctoral
>    advisor or advisee of the corresponding author.
> 4. **No same-institution employment.** None of the five suggested
>    reviewers is currently employed at the corresponding author's
>    institution, and none has held such a position within the 24
>    months preceding submission.
> 5. **No funding overlap.** None of the five suggested reviewers
>    currently holds, or has held within the 24 months preceding
>    submission, a grant, contract, or sub-award on which the
>    corresponding author is a PI, co-PI, co-investigator, or named
>    personnel. Conversely, the corresponding author holds no
>    current or recent (past 24 months) funding from any institution
>    at which the suggested reviewer is employed.
> 6. **No personal / financial relationship.** The corresponding
>    author has no personal friendship, family relationship,
>    financial interest (equity, consulting fee, honorarium, paid
>    advisory role, or board membership), or other personal tie with
>    any of the five suggested reviewers.
>
> The corresponding author acknowledges that, **as a matter of
> professional courtesy**, Reviewer 1 (Lipman group / Meta AI /
> Weizmann) and Reviewer 4 (ESM-IF / LineageFlow / Kanzi authors)
> have research overlaps with the corresponding author's
> flow-matching / protein-generation community, and these two
> reviewers will be subjected to an additional manual COI sweep
> against the TPAMI Editorial Manager database prior to final
> submission. If either overlap is confirmed, the corresponding
> author will substitute an alternative reviewer from the same
> expertise slot.
>
> **Status:** conflict-of-interest-to-be-confirmed-by-authors — no
> co-authorship, no recent collaboration (past 24 months), no
> funding overlap with any of the institutions listed above.

## What still requires the corresponding author's action at submission time

This template is **drafted** but not **finalized**. The corresponding
author (and only the corresponding author) must perform the
following actions before pressing "Submit" on the TPAMI Editorial
Manager:

1. **Replace each placeholder name** with a concrete researcher
   drawn from the expertise community listed in the corresponding
   row. The corresponding author is encouraged to contact the
   suggested reviewer informally to confirm willingness before
   listing them.
2. **Replace each placeholder affiliation** with the reviewer's
   current employing institution as of the submission date.
3. **Replace each placeholder email** with the reviewer's
   institutional email address (the Editorial Manager interface
   auto-validates the email format).
4. **Run the final COI sweep** against the TPAMI Editorial Manager
   database (this is the Editorial Manager's own automated COI
   check, which uses the entered name + institution + email to
   flag institutional overlaps).
5. **Apply the manual COI double-check** to Reviewers 1 and 4
   (Lipman / ESM-IF-etc. communities) per the COI statement above.

## What was NOT changed in this audit wave

- `docs/cover-letter-tpami.md` §9 is preserved verbatim. The
  inline prose form ("Reviewer N — expertise ... affiliation
  suggested") is the format TPAMI recommends in the cover letter;
  the table form in this audit doc is a parallel artefact for the
  Editorial Manager form. No edits to the cover letter text.
- No new names, affiliations, or email addresses were introduced
  in this audit doc — all fields remain placeholders.
- No git push, no GitHub-public transition, no DOI mint, and no
  Editorial Manager account creation were performed; these remain
  on the F / G tracks of the DeepSeek pre-submission checklist.

## Cross-references

- `docs/cover-letter-tpami.md` §9 — inline prose form of the
  reviewer list (the canonical cover-letter artefact).
- `docs/audit/wave213-p6-repo-naming.md` — companion artefact
  confirming the repo-name vs paper-name disclosure (§8.1 Code
  Availability).
- `docs/audit/wave217-p4-companion-note.md` — Wave 217 P4 audit
  of the §11 companion-paper-status note (E2 priority).
- DeepSeek pre-submission checklist, items E3 (this audit),
  E2 (P4, prior), G1 / G3 (final cover-letter integration and
  reviewer field population at Editorial Manager submission time).