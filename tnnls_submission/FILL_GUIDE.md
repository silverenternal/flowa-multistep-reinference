# TNNLS Cover Letter — FILL GUIDE

**Target file:** `tnnls_submission/cover_letter.md`
**Total `[USER TO FILL: …]` occurrences (per `grep -nE 'USER.TO.FILL'`):** 31
**Distinct fillable fields (unique content the user must write):** 17
  - 1 Authors block
  - 1 Suggested Associate Editor (rendered at two lines: 56 header + 986 §9)
  - 1 Suggested Reviewers header pointer (line 60) — replaced by "see §9 below" or a compact summary; the 10 reviewer detail placeholders live in §9
  - 5 reviewers × {affiliation, email} = 10 placeholders in §9
  - 3 Corresponding-author {name, affiliation, email} in §11
**Remaining 14 grep hits are NOT user-fillable:**
  - 11 occurrences in §0 (`## §0 USER ACTION REQUIRED`) are documentation pointers — they describe WHERE the placeholders live and do not need new content. Leave them as-is so future readers can re-locate placeholders.
  - 3 occurrences in §0 (lines 7, 9, 36) are part of the "[USER TO FILL: …] convention" prose and the example `grep` command. Not fillable.

---

## 1. Authors block

- **CATEGORY:** author_block
- **SECTION:** §0 / §opening header
- **LINES:** 51–52
- **WHAT_NEEDED:** Full author list with affiliations and corresponding-author email. IEEE TNNLS author-block convention: one author per line with affiliation footnotes, plus one asterisk (or envelope icon in Editorial Manager) marking the corresponding author and their email.
- **EXAMPLE_OR_HINT:**
  > Dr. Hugo Wei, Department of Computer Science, University of Example, hwei@example.edu
  > Prof. Jane Smith, Department of Statistics, University of Example, jsmith@example.edu
  > Prof. Akira Tanaka, Tokyo Institute of Technology, atanaka@example.ac.jp
  >
  > Corresponding author: Dr. Hugo Wei (hwei@example.edu)
- **HINT:** The TNNLS Editorial Manager uploads a separate `.tex`/`.docx` for the title page, but the cover-letter authors block must still identify (i) every author, (ii) each author's affiliation, and (iii) which author is the corresponding one. Match the order exactly to the manuscript title page.
- **NUMBER OF PLACEHOLDERS IN THIS GROUP:** 1 (the §0 line-11 grep hit is a documentation pointer; do not edit).

## 2. Suggested Associate Editor

- **CATEGORY:** editor
- **SECTION:** §opening header (line 56) and §9 (line 986)
- **LINES:** 56, 986
- **WHAT_NEEDED:** One TNNLS Associate Editor whose editorial scope covers learning systems, generative models, diffusion, or flow matching. The cover letter renders the AE name in two places — the header (line 56) and §9 (line 986) — keep them consistent.
- **EXAMPLE_OR_HINT:**
  > Prof. Ming Li, Department of Electrical and Computer Engineering, University of Example, mli@example.edu
- **HINT:** TNNLS AE list rotates; if the suggested AE is unavailable or has a conflict, choose a backup from the current AE panel at https://www.ieee-cas.org/publications/tnnls/editorial-board and note the rotation rationale in §9. Confirm institutional COI before submission.
- **NUMBER OF PLACEHOLDERS IN THIS GROUP:** 2 (line 56 + line 986). The §0 line-15 grep hit is a documentation pointer.

## 3. Suggested Reviewers (header pointer)

- **CATEGORY:** reviewer
- **SECTION:** §opening header
- **LINE:** 60
- **WHAT_NEEDED:** Compact header line summarising the five reviewers. Because §9 already enumerates them in full, the simplest replacement is "(see §9 below)". Optionally, paste a one-line list (e.g., "Prof. A. Researcher, …; Prof. B. Researcher, …; …").
- **EXAMPLE_OR_HINT:**
  > (see §9 below — five reviewers listed with affiliations and emails)
- **HINT:** TNNLS prefers compact headers; pointing to §9 keeps the cover letter readable. Do NOT repeat the full reviewer block at line 60.
- **NUMBER OF PLACEHOLDERS IN THIS GROUP:** 1 header pointer. The §0 line-19 grep hit is a documentation pointer.

## 4. Reviewer 1 — ProbFlow / Flow-Matching Theory

- **CATEGORY:** reviewer
- **SECTION:** §9
- **LINES:** 1003 (affiliation), 1006 (email)
- **WHAT_NEEDED:** Senior researcher from the Y. Lipman group or equivalent (probability-flow ODEs, rectified flow, stochastic interpolants). Best fit to audit Theorem 1.
- **EXAMPLE_OR_HINT (affiliation):**
  > Meta AI Research (ProbFlow team) / Weizmann Institute of Science — *to be confirmed at submission*
- **EXAMPLE_OR_HINT (email):**
  > reviewer1.theory@meta.com
- **HINT:** Check for COI with the corresponding author (same lab, advisor lineage, recent collaboration) before submission. TNNLS allows up to two suggested AE candidates but rejects reviewers with whom any co-author has co-published in the last 5 years.

## 5. Reviewer 2 — Convergence Bound / BL-Distance Expert

- **CATEGORY:** reviewer
- **SECTION:** §9
- **LINES:** 1017 (affiliation), 1020 (email)
- **WHAT_NEEDED:** Researcher in the F.-X. Vialard or S. Chewi group (bounded-Lipschitz / Wasserstein convergence theory for sampling).
- **EXAMPLE_OR_HINT (affiliation):**
  > Université Gustave Eiffel / LIGM (Vialard) or Yale University (Chewi) — *to be confirmed at submission*
- **EXAMPLE_OR_HINT (email):**
  > reviewer2.convergence@univ-eiffel.fr
- **HINT:** Confirm institutional email (not personal Gmail). TNNLS Editorial Manager pings the email address on file.

## 6. Reviewer 3 — ODE Solver / NFE-Efficiency Expert

- **CATEGORY:** reviewer
- **SECTION:** §9
- **LINES:** 1032 (affiliation), 1035 (email)
- **WHAT_NEEDED:** Researcher from the C. Lu DPM-Solver group or equivalent (high-order ODE solvers, exponential integrators, NFE-efficient sampling).
- **EXAMPLE_OR_HINT (affiliation):**
  > Stanford University (Lu group) or Peking University — *to be confirmed at submission*
- **EXAMPLE_OR_HINT (email):**
  > reviewer3.solver@stanford.edu
- **HINT:** Pick someone with at least one paper on DPM-Solver, EDM, or consistency-model ODE integration. Avoid recent (≤24 months) FlowA-citing authors if possible.

## 7. Reviewer 4 — Protein Generation Expert

- **CATEGORY:** reviewer
- **SECTION:** §9
- **LINES:** 1048 (affiliation), 1052 (email)
- **WHAT_NEEDED:** Researcher from the ESM-IF / LineageFlow / Kanzi author lists (protein-structure generative models).
- **EXAMPLE_OR_HINT (affiliation):**
  > Meta AI (ESM-IF / EvolutionaryScale LineageFlow) or Westlake University / Microsoft Research (Kanzi) — *to be confirmed at submission*
- **EXAMPLE_OR_HINT (email):**
  > reviewer4.protein@meta.com
- **HINT:** This is the highest-risk reviewer for COI — the cover letter itself flags overlap with co-author networks in the protein-generation community. Run a manual COI sweep (last 5 years of coauthorship, advisor lineage, funding overlap) before submission.

## 8. Reviewer 5 — Statistical Rigor Expert

- **CATEGORY:** reviewer
- **SECTION:** §9
- **LINES:** 1065 (affiliation), 1069 (email)
- **WHAT_NEEDED:** Senior researcher in applied statistics, pre-registration, multiple-testing discipline (computational statistics / causal inference / meta-analysis).
- **EXAMPLE_OR_HINT (affiliation):**
  > Department of Statistics, University of Example (computational-statistics focus) — *to be confirmed at submission*
- **EXAMPLE_OR_HINT (email):**
  > reviewer5.stats@example.edu
- **HINT:** This reviewer audits the 12-column audit-grade per-row reporting (`n_paired, mean_diff, sd_diff, t, df, p_raw, CI95_low, CI95_high, d_z, test_type, family, α_bonferroni, bonf_sig`). Best fit: someone with both classical (Bonferroni / Holm) and modern (Benjamini-Hochberg, pre-registration) multiple-testing experience.

## 9. Corresponding author — name

- **CATEGORY:** corresponding_author
- **SECTION:** §11 closing
- **LINE:** 1126
- **WHAT_NEEDED:** Full name of the corresponding author (must match the asterisk-marked author on the manuscript title page).
- **EXAMPLE_OR_HINT:**
  > Dr. Hugo Wei
- **HINT:** No titles (Prof./Dr.) in the signature block — those go on the title page. Use the name as it appears on the title page.

## 10. Corresponding author — affiliation

- **CATEGORY:** corresponding_author
- **SECTION:** §11 closing
- **LINE:** 1127
- **WHAT_NEEDED:** Department + institution + (optional) mailing address.
- **EXAMPLE_OR_HINT:**
  > Department of Computer Science, University of Example, 1234 Example St, City, Country
- **HINT:** TNNLS Editorial Manager does not require a full postal address on the cover letter (it lives in the user profile), but a department + institution line keeps the printed cover letter self-contained.

## 11. Corresponding author — email

- **CATEGORY:** corresponding_author
- **SECTION:** §11 closing
- **LINE:** 1128
- **WHAT_NEEDED:** Institutional email address. Not a personal Gmail / Outlook.
- **EXAMPLE_OR_HINT:**
  > hwei@example.edu
- **HINT:** This email is what TNNLS uses for all subsequent correspondence (decision letter, reviewer comments, proofs). Use a stable, monitored institutional address — NOT a personal mailbox.

---

## How to apply

1. **Open** `tnnls_submission/cover_letter.md` in your editor.
2. **Locate each placeholder** with:
   ```bash
   grep -nE 'USER.TO.FILL' tnnls_submission/cover_letter.md
   ```
3. **Edit** only the 17 actual fillable fields (skip the §0 documentation pointers and the §0 convention/grep-example text):
   - line 51 (Authors block)
   - line 56 (Suggested Associate Editor header)
   - line 60 (Suggested Reviewers header pointer)
   - line 986 (Suggested Associate Editor §9)
   - lines 1003, 1006 (Reviewer 1 aff + email)
   - lines 1017, 1020 (Reviewer 2 aff + email)
   - lines 1032, 1035 (Reviewer 3 aff + email)
   - lines 1048, 1052 (Reviewer 4 aff + email)
   - lines 1065, 1069 (Reviewer 5 aff + email)
   - lines 1126, 1127, 1128 (Corresponding author name + affiliation + email)
4. **Run the placeholders-must-be-empty gate:**
   ```bash
   grep -nE 'USER.TO.FILL' tnnls_submission/cover_letter.md | wc -l
   ```
   Expect: 14 (the §0 documentation pointers + §0 convention text; the 17 actual fillable fields should now show no `[USER TO FILL: ...]` strings — the text you replaced them with should be plain prose).
5. **Re-hash the package** (since `cover_letter.md` changed):
   ```bash
   cd tnnls_submission && sha256sum -- *.md
   ```
6. **Update** the SHA-256 column in `tnnls_submission/MANIFEST.md` (and the cover-letter header reference if any) for `cover_letter.md`.
7. **Run the §0 documentation-mirror check** (optional but recommended): after filling, the §0 placeholder pointer list (lines 11, 15, 19, 24–31) may be left intact, OR you can update them to read "**[FILLED]**" so future readers don't grep a stale list. Either choice is acceptable as long as `grep -nE 'USER.TO.FILL' tnnls_submission/cover_letter.md` returns only the §0 documentation pointers and §0 convention text (14 hits), not 17.
8. **Commit:**
   ```bash
   git add tnnls_submission/cover_letter.md tnnls_submission/MANIFEST.md tnnls_submission/FILL_GUIDE.md
   git commit -m "Wave 274 P3: fill cover_letter USER placeholders"
   ```

---

## Verification checklist (run before upload)

- [ ] Authors block matches manuscript title page (order, affiliations, corresponding-author marker).
- [ ] Suggested Associate Editor appears identically at line 56 and line 986.
- [ ] Five reviewers each have an affiliation and an institutional email; each reviewer's expertise aligns with the audit scope described in §9.
- [ ] COI sweep run against TNNLS Editorial Manager database for all five reviewers.
- [ ] Corresponding-author {name, affiliation, email} match the manuscript title-page asterisk.
- [ ] `grep -nE 'USER.TO.FILL' tnnls_submission/cover_letter.md` returns exactly 14 hits (the §0 documentation pointers + §0 convention text).
- [ ] `MANIFEST.md` SHA-256 column for `cover_letter.md` matches `sha256sum cover_letter.md`.
- [ ] Commit message references the wave number and the action ("fill cover_letter USER placeholders").
