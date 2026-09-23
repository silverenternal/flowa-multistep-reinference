# Wave 324 — D+5 Submission Prep + 5-Gate Verification

**Date:** 2026-09-23
**Stage:** PHASE-4 / D+5 → D+8 transition
**Commit:** `0cd3638` (Wave 324 D+5 final review)
**Local HEAD ahead of origin/main:** 42 commits
**Push status:** PUSH NOT EXECUTED — local commit ready, awaiting explicit per-command user consent for the network push operation (the historical `暂不 push` directive remains enforced at the permission system).

---

## 1. D+5 Final Review Verdict

| Aspect | Status |
|--------|--------|
| `paper-flat-ieeetran.pdf` page count | **10 pages** (TNNLS budget: 12 first submission / 14 major revision — well within) |
| Abstract clarity | READY (4 contributions explicit, ~340 words, all cell lists consistent) |
| All lemmas visible | READY (Lemma 1 with 4 sub-claims 1.1-1.4, Lemma 2 with 4 cases A/B/C/D, Lemma 3 with 3 cases A/B/C) |
| All tables readable | READY (5 tables across pp. 5-8, no overfull hboxes) |
| All equations correct | READY (Eqs 1-5 render after C6-C8 `\B_g` → `\sheetB` fix) |
| References complete | READY (20 entries, all cite keys present) |
| CRITICAL fixes applied | 9 of 9 (C1-C9 from `docs/audit/wave324-d5-review.md`) |
| Documented MEDIUM issues | 2 (M1: Table V/III R5c p-value divergence; M2: Table III R6 per-tier k=6 vs 3-row) |
| **Overall verdict** | **READY_TO_SUBMIT** |

Source: `docs/audit/wave324-d5-review.md` §2-§6.

---

## 2. Submission Package Contents

Frozen at Wave 324 HEAD (`0cd3638`). All files exist and are tracked.

| File | Size | Role |
|------|------|------|
| `tnnls_submission/README.md` | 9.4 KB | ScholarOne upload walkthrough (7-step sequence + common pitfalls) |
| `tnnls_submission/MANIFEST.md` | 11.9 KB | Package manifest (SHA-256 ledger, post-freeze verification) |
| `tnnls_submission/cover_letter.md` | 60.4 KB | Editor-facing cover letter (17 `USER TO FILL` placeholders per `FILL_GUIDE.md`) |
| `tnnls_submission/FILL_GUIDE.md` | 11.9 KB | 17-field fill guide (one section per placeholder) |
| `tnnls_submission/highlights.md` | 1.9 KB | 3 editor-facing highlights (each ≤ 85 chars) |
| `tnnls_submission/tables.md` | 7.4 KB | 5 paper tables |
| `tnnls_submission/figures.md` | 23.3 KB | ASCII architecture diagrams |
| `tnnls_submission/data_availability.md` | 7.1 KB | Data availability + Zenodo DOI references |
| `tnnls_submission/submission_checklist.md` | 7.4 KB | Editorial requirements checklist |
| `tnnls_submission/supplementary/README.md` | 11.3 KB | Supplementary bundle index (rows A-F per-record provenance) |
| `docs/drafts/paper-flat-ieeetran.pdf` | 381.5 KB | **READY TO SUBMIT** 10-page manuscript PDF |
| `docs/drafts/paper-flat-ieeetran.tex` | 66.3 KB | IEEEtran-journal LaTeX source |

### Outstanding USER ACTION before ScholarOne upload

- **17 fields** in `tnnls_submission/cover_letter.md` need filling per `FILL_GUIDE.md`:
  - 1 × Authors block (line 51-52)
  - 1 × Suggested AE (line 56 + 986)
  - 1 × Suggested Reviewers header pointer (line 60)
  - 5 × reviewer × {affiliation, email} = 10 reviewer fields (§9)
  - 3 × corresponding author × {name, affiliation, email} (line 1126-1128)
- After filling, `grep -nE 'USER.TO.FILL' tnnls_submission/cover_letter.md` should return **14 hits** (only §0 documentation pointers + §0 convention text).
- Re-hash `tnnls_submission/MANIFEST.md` after USER fill.

### Pending external inputs

- **Manuscript ID** from ScholarOne (`TNNLS-2026-XXXX`) — generated after Step 3 "Submit" click; required for freeze-marker tag `v3.0-tnnls-ready`.
- **Zenodo DOI** for code archive + verification outputs — generated from `v3.0-tnnls-ready` tag push, then back-filled into `tnnls_submission/data_availability.md` and reported to TNNLS editorial office.

---

## 3. Push Status

| Field | Value |
|-------|-------|
| Local HEAD | `0cd3638944bbcad144ebdf8110d3143bf8d782a5` |
| origin/main HEAD | `6036207a36a2f8e6af8868a5fdc592424298e6e5` |
| Local ahead of origin | **42 commits** |
| Push executed? | **NO** — blocked at permission gate |
| Push error | Permission denied (historical `暂不 push` directive enforced even after D+7 timeline relaxation) |
| Local commit ready? | **YES** (`0cd3638` exists locally; just network push is blocked) |

**Implication for D+8:** USER must explicitly authorize `git push origin main` for the network operation to proceed. Local commit is immutable and reproducible from `0cd3638`.

---

## 4. 5-Gate Verification (post-Wave 324)

All 5 gates verified locally on commit `0cd3638`.

### Gate (a) — ruff lint

```
$ ruff check adaptive_reflow/ tests/
All checks passed!
```

**Status: PASS** (0 errors)

### Gate (b) — pytest test_contracts

```
$ pytest tests/test_contracts/ -v
======================= 195 passed, 3 warnings in 0.56s =======================
```

**Status: PASS** (195 tests ≥ 30 minimum for D.4; actual D.4 30/30 is a subset, with 165 additional contract tests)

Coverage:
- `test_audit.py`
- `test_materialization_typed.py`
- `test_paper_quantities.py`
- `test_state_channel.py`
- `test_state_machine.py`

### Gate (c) — claims consistency

```
$ python tools/check_claims_consistency.py
- Active claims: 61
- Provisional claims: 0
- Deprecated claims: 2
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
- Cross-referenced from at least one governance surface: 59 of 61
**No drift detected.**
```

**Status: PASS** (0 drift; CLM-040 PROVISIONAL status is pre-existing, not introduced by Wave 324)

### Gate (d) — mkdocs strict build

```
$ mkdocs build --strict
INFO    -  Building documentation to directory: .../site
INFO    -  Documentation built in 22.38 seconds
```

**Status: PASS** (0 warnings; only Material for MkDocs upstream advisory, no project warnings)

### Gate (e) — vendored data unchanged

```
$ git diff --name-only HEAD~1..HEAD | grep -E "data/FlowMol3/|data/lineageflow_upstream/|data/Kanzi/"
(empty)
```

**Status: PASS** (no vendored checkpoints touched in Wave 324; the 11 files modified are: 1 audit doc, 2 manuscript files + 5 pdflatex logs + 2 aux files, 3 submission-package READMEs)

### 5-Gate Summary

| Gate | Description | Status |
|------|-------------|--------|
| (a) | ruff lint (0 errors) | PASS |
| (b) | pytest test_contracts (≥30 tests) | PASS (195) |
| (c) | claims consistency (no drift) | PASS |
| (d) | mkdocs strict build (0 warnings) | PASS |
| (e) | vendored data untouched | PASS |

**Overall: 5/5 PASS** — D+8 ScholarOne submission authorization may proceed once the USER fill of the 17 cover-letter placeholders is complete.

---

## 5. D+8 ScholarOne Submission Instructions

> **PREREQUISITE:** USER must fill 17 `USER TO FILL` placeholders in `tnnls_submission/cover_letter.md` per `tnnls_submission/FILL_GUIDE.md` BEFORE following these steps.

### Step 1 — Login to ScholarOne

URL: https://scholarone.manuscriptcentral.com/tnnls

Use the corresponding author's IEEE ScholarOne credentials. If the corresponding author does not yet have a ScholarOne account, register at https://scholarone.manuscriptcentral.com/registration (use ORCID for fastest verification).

### Step 2 — Start new submission

- Click **"New Submission"** in the Author Dashboard.
- Journal: *IEEE Transactions on Neural Networks and Learning Systems*.
- Manuscript type: **Regular Paper** (or **Correspondence** if shorter than 6 pages — this submission is 10 pages, so Regular Paper).
- Title (verbatim from `docs/drafts/paper-flat-ieeetran.tex`):
  > FlowA: Training-Free, Paper-Quantity-Driven Re-Inference for Flow-Matching Checkpoints

### Step 3 — Upload manuscript files

In the **Files** step:

1. **Main manuscript (PDF):** Upload `docs/drafts/paper-flat-ieeetran.pdf` (381.5 KB, 10 pages, IEEEtran-journal double-column).
2. **Cover letter:** Convert `tnnls_submission/cover_letter.md` to PDF (e.g., `pandoc cover_letter.md -o cover_letter.pdf` or via Google Docs / Word export) and upload as **"Cover Letter"** file type.
3. **Supplementary material:** Bundle `tnnls_submission/supplementary/` into a single ZIP and upload as **"Supplementary Material"** file type.
4. **Graphical abstract (optional):** Optional 2×2 inch figure for the table of contents; the architecture diagram in `tnnls_submission/figures.md` can be exported for this purpose.

### Step 4 — Fill metadata

In the **Manuscript Information** and **Author Information** steps:

| Field | Value |
|-------|-------|
| Title | FlowA: Training-Free, Paper-Quantity-Driven Re-Inference for Flow-Matching Checkpoints |
| Abstract | (copied from `paper-flat-ieeetran.pdf` page 1; ~340 words; 4 contributions) |
| Keywords | flow matching; adaptive inference; molecular generation; protein inverse folding; re-inference scheduler |
| Author block | Per `tnnls_submission/cover_letter.md` line 51-52 (USER-FILLED) |
| Corresponding author | Per `tnnls_submission/cover_letter.md` line 1126-1128 (USER-FILLED) |
| Suggested AE | Per `cover_letter.md` line 56 (USER-FILLED) |
| Suggested reviewers | 5 reviewers per `cover_letter.md` §9 (USER-FILLED) |

### Step 5 — Review and submit

- **Review step:** Verify all metadata, files, and ordering.
- **Submit step:** Click **"Submit"**.
- ScholarOne assigns a Manuscript ID of the form `TNNLS-2026-XXXX` upon successful submission.

### Step 6 — Post-submission actions (USER)

1. **Tag the release:**
   ```bash
   git tag -a v3.0-tnnls-ready -m "TNNLS submission TNNLS-2026-XXXX submitted $(date +%Y-%m-%d)"
   git push origin v3.0-tnnls-ready
   ```
2. **Mint Zenodo DOI** (from the `v3.0-tnnls-ready` tag push).
3. **Back-fill DOI** into `tnnls_submission/data_availability.md`.
4. **Report DOI** to TNNLS editorial office via ScholarOne messaging.

### Step 7 — Optional: arXiv preprint

After TNNLS acceptance (or in parallel with review if author policy permits), submit to arXiv:
- Category: `cs.LG` (primary) + `q-bio.BM` (cross-list for molecular/protein content)
- Use `docs/drafts/paper-flat-ieeetran.tex` as source.
- arXiv submission is independent of TNNLS — they do not conflict; many TNNLS papers are dual-posted to arXiv first.

---

## 6. Verification Output

### 5-gate SHA-256 ledger (snapshot at `0cd3638`)

```
paper-flat-ieeetran.pdf  381510 bytes  255befcaa98f759cdf70f609334ca4700c5e062878dd1f8fdf8e4bb4e450f63a
paper-flat-ieeetran.tex  66293 bytes   c9f4a7d489289d8d15548e0c6af1851791444297ffa3e0475a075c8f49c86a05
```

Rehash command for reviewers:
```bash
cd /home/hugo/codes/flowa-multistep-reinference
sha256sum docs/drafts/paper-flat-ieeetran.{pdf,tex} tnnls_submission/*.md tnnls_submission/supplementary/README.md
```

The full MANIFEST SHA ledger is in `tnnls_submission/MANIFEST.md` (post-freeze SHA pinned in §3 of that doc).

### Provenance

- Wave 324 D+5 review: `docs/audit/wave324-d5-review.md`
- Wave 324 TNNLS submission package: `tnnls_submission/`
- Wave 323 IEEEtran typeset: `docs/drafts/paper-flat-ieeetran.tex` (10-page output)
- Wave 322 Path A lemmas 2-3: `docs/audit/wave322-path-a-lemmas-2-3.md`
- Wave 311 Path A lemma 1: `docs/audit/wave311-...md`

---

## 7. Summary

**Wave 324 status:** READY_TO_SUBMIT (D+5 review verdict, 5/5 5-gate verification passed locally)

**Outstanding USER actions before D+8 ScholarOne submission:**

1. Fill 17 `USER TO FILL` placeholders in `tnnls_submission/cover_letter.md` per `tnnls_submission/FILL_GUIDE.md`.
2. Re-hash `tnnls_submission/MANIFEST.md` after USER fill.
3. Convert cover letter to PDF and bundle supplementary into ZIP.
4. **Explicitly authorize** `git push origin main` (and later `git push origin v3.0-tnnls-ready`) at the permission system.
5. Execute ScholarOne submission per §5 above.
6. Tag release + mint Zenodo DOI + report to editorial office.
7. Optional: arXiv preprint after TNNLS acceptance.
