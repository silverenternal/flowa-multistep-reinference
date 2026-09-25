# TNNLS Submission Package — ScholarOne Upload README

**Audience:** corresponding author (and any co-author tasked with the TNNLS ScholarOne upload).

This README lists every file in the TNNLS submission package and walks through the ScholarOne upload sequence in 7 steps. **Read this top-to-bottom before opening Editorial Manager.**

---

## 0. Where the package lives

```
tnnls_submission/
├── README.md                  ← (this file)
├── MANIFEST.md                ← file-by-file SHA-256 ledger
├── cover_letter.md            ← EDITOR-FACING — fill placeholders first
├── FILL_GUIDE.md              ← how to fill `cover_letter.md` placeholders
├── highlights.md              ← 3 highlights (≤ 85 chars each)
├── tables.md                  ← 5 TNNLS paper tables
├── figures.md                 ← ASCII architecture diagrams
├── data_availability.md       ← Zenodo DOI + per-record CSV provenance
├── submission_checklist.md    ← TNNLS editorial requirements checklist
└── supplementary/             ← supplementary bundle index (see §3 below)
    └── README.md              ← per-cell SOURCE.md, audit trail, verification outputs
```

The **manuscript PDF and source** live one level up:

```
docs/drafts/paper-A-final.pdf   ← 14 pages, 305270 bytes (Wave 324 D+5, ready-to-submit)
docs/drafts/paper-A-final.tex   ← IEEEtran-journal source
docs/drafts/paper-A-final.{aux,log,out}
```

---

## 1. Pre-flight checklist (BEFORE opening ScholarOne)

Walk through these in order; each step has a single command that produces one line of "OK" output. **Do not skip any step.**

1. **Cover letter placeholders are filled.**
   ```bash
   grep -nE 'USER.TO.FILL' tnnls_submission/cover_letter.md | wc -l
   ```
   Expect: `14` (only the §0 documentation pointers + §0 convention text — see `FILL_GUIDE.md` §Verification checklist).

2. **SHA-256 ledger is current.**
   ```bash
   cd tnnls_submission && sha256sum -- *.md supplementary/README.md
   ```
   Cross-check the `MANIFEST.md` SHA-256 column matches.

3. **Manuscript compiles cleanly.**
   ```bash
   pdfinfo docs/drafts/paper-A-final.pdf | grep -E "Pages|File size"
   ```
   Expect: `Pages: 14`, `File size: 305270 bytes`.

4. **Supplementary bundle index parses.**
   ```bash
   head -1 tnnls_submission/supplementary/README.md
   ```
   Expect: `# TNNLS Submission — Supplementary Bundle Index`.

5. **Anonymous blind-review check** (paper has no author / institution visible):
   ```bash
   grep -iE "hwei|university of|institute|department" docs/drafts/paper-A-final.{tex,pdf} | head -5
   ```
   Expect: empty output (or only IEEEtran-journal boilerplate that the typesetter strips before upload).

---

## 2. ScholarOne upload sequence (7 steps)

Open `https://mc.manuscriptcentral.com/tnnls` (IEEE TNNLS Editorial
Manager). Sign in as the corresponding author, click **"New
Submission"**, and follow the 7-step wizard. Each step below names
the `tnnls_submission/` (or `docs/drafts/`) file you upload.

### Step 1 — Article Type
Select: **"Regular Paper"** (TNNLS treats the manuscript as a regular research article, not a correspondence or survey). Title and abstract go in **Step 2**.

### Step 2 — Title, Abstract, Keywords
- **Title:** paste verbatim from the manuscript, line 1 of `docs/drafts/paper-A-final.tex` (PDF page 1).
- **Abstract:** copy the body of `Abstract.` (between `\begin{abstract}` and `\end{abstract}` in the `.tex`, or page 1 of the PDF). **Do not include** the index-terms/IEEE keywords here — those live in Step 3.
- **Keywords:** copy the 9 IEEE keyword terms from `\begin{IEEEkeywords}` … `\end{IEEEkeywords}` (or the IEEEtran section in the PDF).

### Step 3 — Manuscript File
- Upload: **`docs/drafts/paper-A-final.pdf`** (14 pages, IEEEtran-journal typeset).
- The system will probe for embedded fonts and page count; both should pass.

### Step 4 — Supplementary Material
- Upload: **`tnnls_submission/supplementary/README.md`** as a text attachment.
  - The supplementary bundle is **indexed**, not bundled into a single PDF — ScholarOne accepts up to 5 supplementary files, but a single `supplementary/README.md` index that hyperlinks every cell is the cleanest delivery. Reviewers click through to the byte-addressable JSON / CSV / markdown files in the public Zenodo / GitHub mirror (see `data_availability.md`).
- **If ScholarOne rejects .md**, convert to PDF via:
  ```bash
  pandoc -o supplementary/README.pdf supplementary/README.md --pdf-engine=xelatex -V geometry:margin=1in
  ```

### Step 5 — Cover Letter
- Upload: **`tnnls_submission/cover_letter.md`** after all 17 `[USER TO FILL: ...]` placeholders are filled (see `FILL_GUIDE.md`).
- If ScholarOne only accepts PDF: `pandoc -o cover_letter.pdf tnnls_submission/cover_letter.md --pdf-engine=xelatex -V geometry:margin=1in -V fontsize=11pt`.

### Step 6 — Highlights
- Paste the three bullets from `tnnls_submission/highlights.md` (each ≤ 85 chars) into the "Manuscript Highlights" field. **Each highlight on its own line.**

### Step 7 — Suggested Reviewers / Associate Editor / COI
- Suggested Associate Editor: copy from cover letter §9.
- Suggested Reviewers (5): for each, paste the name + affiliation + institutional email from cover letter §9.
- Conflicts of interest: declare any institutional / advisor-student / recent-collaboration overlaps from cover letter §9 closing paragraph.

---

## 3. After upload (within 24 hours)

1. **Verify Editorial Manager email acknowledgement.**
   The system sends a confirmation email with the manuscript ID (e.g., `TNNLS-2026-XXXX`). Save this ID.
2. **Tag the freeze-marker commit** in your local repo (the commit whose SHA is the source for the manuscript PDF):
   ```bash
   cd /home/hugo/codes/flowa-multistep-reinference
   git log --oneline docs/drafts/paper-A-final.tex | head -1
   # Copy the commit SHA and tag:
   git tag -a v3.0-tnnls-ready <SHA> -m "TNNLS submission freeze-marker (ScholarOne ID TNNLS-2026-XXXX)"
   ```
3. **Push the tag** (DO NOT push to `origin/main` from a Wave 3+ script — push only the tag once Editorial Manager has acknowledged receipt):
   ```bash
   git push origin v3.0-tnnls-ready
   ```
4. **Generate the Zenodo deposit** from the tagged commit. Use the `docs/zenodo-release/` recipe — the deposit metadata should reference the v3.0-tnnls-ready tag, not the HEAD. Save the assigned Zenodo DOI in `tnnls_submission/data_availability.md` §Code availability.
5. **Send the Zenodo DOIs to the TNNLS editorial office** via the Editorial Manager "Reply to decision email" channel after acknowledgement (this is optional but TNNLS authors typically include it in the cover-letter-post-upload follow-up email).

---

## 4. Common upload pitfalls

| Pitfall | Fix |
|---|---|
| Editorial Manager complains about "non-standard manuscript type" | Select "Regular Paper", not "Survey" or "Correspondence" |
| PDF rejected for "missing embedded fonts" | Recompile with `\usepackage[T1]{fontenc}` (already in the IEEEtran template) |
| Cover-letter PDF exceeds 1 MB | Convert from `.md` to PDF; if still too large, drop the S1–S8 supplementary-listing appendix (it duplicates the supplementary README) |
| Highlights length check fails | Each highlight MUST be ≤ 85 chars; check with `awk '{print length, $0}' tnnls_submission/highlights.md` |
| ScholarOne rejects 5+ supplementary files | Upload only the README index; the index hyperlinks every byte-addressable artifact |

---

## 5. Quick link refcard

- ScholarOne: https://mc.manuscriptcentral.com/tnnls
- TNNLS editorial board & AE list: https://www.ieee-cas.org/publications/tnnls/editorial-board
- IEEEtran class: https://www.ctan.org/pkg/ieeetran
- TNNLS submission guidelines: https://www.ieee-cas.org/publications/tnnls/submit

---

## 6. Cross-reference to package artifacts

- `tnnls_submission/MANIFEST.md` — file-by-file SHA-256 ledger (re-hash after every edit)
- `tnnls_submission/FILL_GUIDE.md` — detailed walkthrough for `cover_letter.md` placeholders
- `tnnls_submission/supplementary/README.md` — supplementary bundle index (headline cells, audit docs, verification outputs)
- `tnnls_submission/data_availability.md` — Zenodo DOIs + per-record CSV provenance
- `tnnls_submission/highlights.md` — 3 TNNLS highlights, provenance-traced
- `tnnls_submission/tables.md` — 5 paper-ready tables (R1-R6 + 4-arm H2H + statistical + wall-clock + reproducibility)
- `tnnls_submission/figures.md` — ASCII architecture diagrams
- `tnnls_submission/submission_checklist.md` — D.4 + mkdocs + claims + pytest + acceptance gates
- `docs/audit/wave324-d5-review.md` — final D+5 review (ready-to-submit verdict, 9 CRITICAL fixes already applied)
- `docs/audit/wave323-typeset-execution.md` — IEEEtran-journal typeset execution
- `docs/audit/wave322-restoration-execution.md` — Path A Lemma 2/3 (state-machine byte-determinism + ledger tamper-evidence)
- `docs/audit/wave311-restoration-execution.md` — Path A Lemma 1 (protocol composition closure)
- `docs/audit/wave310-restoration-execution.md` — R6 STRONG tier-aware upgrade + D2 restoration
- `docs/audit/wave297-final.md` + `wave298-final.md` — paper restoration + 7-novelty catalogue
- `docs/audit/wave306-11-cell-alignment.md` + `wave307-data-archaeology.md` — 11-cell alignment
