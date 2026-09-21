# TNNLS Submission Action Checklist — Wave 238 P3

**For:** Corresponding author
**Date prepared:** 2026-09-21
**Status:** READY (subject to completing the six USER action items below)
**Venue decision (Wave 238 P3):** IEEE TNNLS (overrides the Wave 224
P4 TPAMI decision; see `docs/audit/wave238-p3-journal-decision.md` for
rationale — TNNLS's broader neural-networks + learning-systems scope
better fits the cross-domain solver-agnostic FM framework contribution
than TPAMI's image/video primary scope).

This checklist enumerates the six steps the corresponding author must
execute to push the Wave 238 P3 submission bundle from the local
freeze-marker commit through the TNNLS Editorial Manager. Each step
has a checkbox so progress is tracked at a glance.

The Wave 231 / 235 / 236 / 237 / 238 audit chain (P1 B_g paper fix
→ P2 real 4-arm paper fix → P3 wording fix → P4 L_emp vs A_g citation
→ P5 submission package → Wave 235 P1–P4 top-4 high-leverage
improvements → Wave 236 P2 24.6× → 1.26× wall-clock fix → Wave 237 P1
abstract trim → Wave 238 P1 FlowMol3 honest disclosure → Wave 238 P2
CUDA-graph measurement-conditions disclosure → Wave 238 P3 journal
decision) is complete on `main`; everything downstream of this
checklist is operational, not technical.

---

- [ ] **STEP 1 — Fill cover letter placeholders.**
  Open `docs/cover-letter-tnnls.md`. Locate every `[USER TO FILL: …]`
  marker with:
  ```bash
  grep -n 'USER TO FILL' docs/cover-letter-tnnls.md
  ```
  The §0 section at the top of the cover letter enumerates the 11
  fields: authors block, suggested Associate Editor, suggested
  Reviewers (×1 group), Reviewer 1–5 affiliation (×5), corresponding
  author name / affiliation / email (×3). Replace each with real
  values. The `[Date]` placeholder in the closing block has already
  been replaced with `2026-09-21`; the date in the opening header
  is also `2026-09-21`. After filling, re-run the grep — it must
  return no matches before the cover letter is uploaded to the
  Editorial Manager.

  Suggested reviewer pool for a TNNLS submission should pull from
  the learning-systems / neural-networks community rather than the
  image/multimedia community. Five reviewer angles that fit TNNLS:
  flow-matching theory (Lipman group or equivalent), convergence
  bound / BL-distance expert (Vialard, Chewi, or equivalent),
  ODE solver / NFE-efficiency expert (Lu DPM-Solver group or
  equivalent), protein-FM adapter expert (LineageFlow / Kanzi / ESM-IF
  author lists), and a statistical-rigor expert for the audit-grade
  reporting and Bonferroni families.

- [ ] **STEP 2 — Generate the three upload PDFs.**
  Compile each Markdown source to a PDF in the project's standard
  typeset pipeline (LaTeX or Typst, double-column 14-page TNNLS
  format):
  - `docs/drafts/paper-flattened-draft.md` → `paper-flattened-draft.pdf`
  - `supplementary.md` → `supplementary.pdf`
  - `docs/cover-letter-tnnls.md` → `cover-letter-tnnls.pdf` (after
    Step 1)
  Verify each PDF is byte-stable by hashing it and recording the
  SHA-256 in a sibling `.sha256` file. The Markdown source remains
  the canonical review artefact; the PDFs are the upload artefacts.

- [ ] **STEP 3 — Push to GitHub.**
  Run the push script:
  ```bash
  bash scripts/wave231_push_to_github.sh
  ```
  The script verifies the working tree is clean, lists unpushed
  commits (the Wave 229–238 audit chain, currently 87 unpushed
  commits ahead of `origin/main` per `git status`), asks for an
  explicit `y/N` confirmation, and runs `git push origin main`. The
  script then prints the next-step checklist (public toggle, Zenodo
  DOI, Editorial Manager upload).

- [ ] **STEP 4 — Make the GitHub repository public.**
  GitHub → `flowa-multistep-reinference` → **Settings** →
  **General** → scroll to **Danger Zone** → **Change repository
  visibility** → **Public**. Confirm the visibility change. This is
  required so that the TNNLS reviewers can access the source code
  archive referenced from §8.1 of the cover letter without an
  account-share dance. The freeze-marker commit `5b21cca` will then
  be world-readable.

- [ ] **STEP 5 — Mint a Zenodo DOI for the submission bundle.**
  - Log in to <https://zenodo.org> using the **Log in with GitHub**
    button.
  - Navigate to **GitHub** → enable the
    `flowa-multistep-reinference` repository (one-time setup; Zenodo
    will then auto-listen for new releases).
  - Create a new Zenodo release pinned to the freeze-marker commit
    `5b21cca`. Use the release tag `tnnls-v3.0` to match the Docker
    image name in §8 of the cover letter (`flowa:tnnls-v3.0`).
  - Trigger Zenodo DOI generation. Zenodo will mint two DOIs: one
    for the source-code archive, one for the per-record CSV bundle
    on the Zenodo-side deposit draft in `docs/zenodo-release/`.
  - Add both DOIs to the **Data Availability** section of the paper
    (currently a stub in `docs/drafts/paper-flattened-draft.md`).

- [ ] **STEP 6 — Submit to the TNNLS Editorial Manager.**
  - Log in to the TNNLS Editorial Manager
    (<https://ieee.atyponrex.com/journal/tnnls>).
  - **New Submission** → select the manuscript type (Regular
    Research Paper).
  - Upload the three PDFs from Step 2:
    - `paper-flattened-draft.pdf` (the main manuscript)
    - `supplementary.pdf` (S1–S8)
    - `cover-letter-tnnls.pdf` (the cover letter, post-Step 1)
  - Fill the Editorial Manager metadata:
    - Title: "FlowA: Training-free, paper-quantity-driven
      re-inference for Flow Matching checkpoints"
    - Suggested Associate Editor: the value filled into §9 of the
      cover letter.
    - Suggested Reviewers (excluding conflicts of interest): the
      five values filled into §9 of the cover letter.
    - Data Availability: the two Zenodo DOIs minted in Step 5.
    - Reproducibility checklist: tick "Code available",
      "Container available", "Per-record data available",
      "Statistical analysis script available" — see
      `docs/tnnls_submission_checklist.md` (the old TPAMI
      checklist at `docs/tpami_submission_checklist.md` should be
      treated as a legacy reference; the journal-facing acceptance
      rubric is unchanged in spirit) for the full §5
      acceptance-gate rubric.
  - Submit. The Editorial Manager will return a manuscript ID; record
    it in `docs/audit/wave238-p3-journal-decision.md` as the
    **TNNLS Manuscript ID** field (the Wave 231 P5 audit
    `docs/audit/wave231-p5-submission-package.md` is the
    pre-Wave-238-P3 reference if the TPAMI EM was already used).

---

## After Submission

- The Editor-in-Chief's office assigns a Handling Associate Editor
  (typically within 2–4 weeks). Record the assigned AE and the
  manuscript ID in a follow-up `wave238-p6-tnnls-editor-assignment.md`
  audit document under `docs/audit/`.
- Reviewer comments are returned with the AE's decision (Accept /
  Minor / Major / Reject). A follow-up wave will integrate
  reviewer feedback; the Limitations draft in the paper (§4 K1–K9
  including the new K9 FlowMol3 3-seed direction inconsistency
  disclosed in §7 of the cover letter) is the starting point
  for the response letter.

## Rollback

If a step fails, all artifacts are reversible:

- **Cover letter placeholders:** re-grep and re-fill — no git
  history impact.
- **PDF generation:** re-compile from the Markdown source — the
  Markdown is the canonical artefact.
- **Push to GitHub:** if the push fails, the local freeze-marker
  commit is unchanged. Re-run the script after fixing the
  underlying issue.
- **Public-visibility toggle:** revert via the same Danger Zone
  panel.
- **Zenodo DOI:** Zenodo DOIs are immutable once minted; if the
  bundle must change after the DOI is minted, mint a new release
  with a new DOI and update the Data Availability statement before
  the camera-ready deadline.
- **TNNLS EM submission:** withdraw the submission via the Editorial
  Manager and start a new submission. Reviewers' assigned IDs reset.

## Journal decision provenance

This checklist is filed under the **tnnls_submission_action_checklist.md**
name (renamed from the prior Wave 231 `tpami_submission_action_checklist.md`
via `git mv`) as part of the Wave 238 P3 journal decision. The full
decision rationale — TNNLS chosen over TPAMI because TNNLS's broader
neural-networks + learning-systems scope better fits the cross-domain
solver-agnostic FM framework contribution than TPAMI's image/video
primary scope — is in `docs/audit/wave238-p3-journal-decision.md`.

If for any reason the venue is later switched back to TPAMI (e.g.,
TNNLS reviewers reject across multiple rounds and a re-submission
to a sibling venue is desired), the original
`docs/tpami_submission_checklist.md` (un-tracked draft at the time
of this rewrite) and the pre-Wave-238-P3 `git log` for
`docs/internal/tpami_submission_action_checklist.md` (HEAD before
this `git mv`) preserve the prior TPAMI checklist content; the
contents can be restored with `git mv` in reverse.
