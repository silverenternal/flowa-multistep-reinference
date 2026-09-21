# TPAMI Submission Action Checklist — Wave 231 P5

**For:** Corresponding author
**Date prepared:** 2026-09-21
**Status:** READY (subject to completing the six USER action items below)

This checklist enumerates the six steps the corresponding author must
execute to push the Wave 231 P5 submission bundle from the local
freeze-marker commit through the TPAMI Editorial Manager. Each step
has a checkbox so progress is tracked at a glance.

The Wave 231 audit chain (P1 B_g paper fix → P2 real 4-arm paper fix
→ P3 wording fix → P4 L_emp vs A_g citation → P5 submission
package) is complete on `main`; everything downstream of this
checklist is operational, not technical.

---

- [ ] **STEP 1 — Fill cover letter placeholders.**
  Open `docs/cover-letter-tpami.md`. Locate every `[USER TO FILL: …]`
  marker with:
  ```bash
  grep -n 'USER TO FILL' docs/cover-letter-tpami.md
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

- [ ] **STEP 2 — Generate the three upload PDFs.**
  Compile each Markdown source to a PDF in the project's standard
  typeset pipeline (LaTeX or Typst, double-column 14-page TPAMI
  format):
  - `docs/drafts/paper-flattened-draft.md` → `paper-flattened-draft.pdf`
  - `supplementary.md` → `supplementary.pdf`
  - `docs/cover-letter-tpami.md` → `cover-letter-tpami.pdf` (after
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
  commits (the Wave 229–231 audit chain), asks for an explicit
  `y/N` confirmation, and runs `git push origin main`. The script
  then prints the next-step checklist (public toggle, Zenodo DOI,
  Editorial Manager upload).

- [ ] **STEP 4 — Make the GitHub repository public.**
  GitHub → `flowa-multistep-reinference` → **Settings** →
  **General** → scroll to **Danger Zone** → **Change repository
  visibility** → **Public**. Confirm the visibility change. This is
  required so that the TPAMI reviewers can access the source code
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
    `5b21cca`. Use the release tag `tpami-v3.0` to match the Docker
    image name in §8 of the cover letter.
  - Trigger Zenodo DOI generation. Zenodo will mint two DOIs: one
    for the source-code archive, one for the per-record CSV bundle
    on the Zenodo-side deposit draft in `docs/zenodo-release/`.
  - Add both DOIs to the **Data Availability** section of the paper
    (currently a stub in `docs/drafts/paper-flattened-draft.md`).

- [ ] **STEP 6 — Submit to the TPAMI Editorial Manager.**
  - Log in to the TPAMI Editorial Manager
    (<https://ieee.atyponrex.com/journal/tpami>).
  - **New Submission** → select the manuscript type (Regular
    Research Paper).
  - Upload the three PDFs from Step 2:
    - `paper-flattened-draft.pdf` (the main manuscript)
    - `supplementary.pdf` (S1–S8)
    - `cover-letter-tpami.pdf` (the cover letter, post-Step 1)
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
      `docs/tpami_submission_checklist.md` for the full §5
      acceptance-gate rubric.
  - Submit. The Editorial Manager will return a manuscript ID; record
    it in `docs/audit/wave231-p5-submission-package.md` as the
    **Manuscript ID** field.

---

## After Submission

- The Editor-in-Chief's office assigns a Handling Associate Editor
  (typically within 2–4 weeks). Record the assigned AE and the
  manuscript ID in a follow-up `wave231-p6-editor-assignment.md`
  audit document under `docs/audit/`.
- Reviewer comments are returned with the AE's decision (Accept /
  Minor / Major / Reject). The Wave 232 wave will integrate reviewer
  feedback; the L1–L8 limitations draft in
  `docs/drafts/limitations-flattened-draft.md` is the starting point
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
- **TPAMI EM submission:** withdraw the submission via the Editorial
  Manager and start a new submission. Reviewers' assigned IDs reset.