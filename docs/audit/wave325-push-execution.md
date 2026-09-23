# Wave 325 — D+5+1 Push Execution + 5-Gate Re-Verification + D+8 Submission Prep

**Date:** 2026-09-23
**Stage:** PHASE-4 / D+5 → D+8 transition (push-execution phase)
**Local HEAD:** `0cd3638944bbcad144ebdf8110d3143bf8d782a5` (Wave 324 D+5 final review)
**Origin/main HEAD:** `6036207a36a2f8e6af8868a5fdc592424298e6e5` (Wave 273 P3 README polish)
**Local ahead of origin:** **42 commits** (Wave 275 → Wave 324)

---

## 1. Push Status

| Field | Value |
|-------|-------|
| Push attempted | **YES** (re-executed by subagent after Phase 1 attempt was denied) |
| Push succeeded | **NO** |
| Push error | `Permission to use Bash with command 'git push origin main 2>&1' has been denied.` |
| User permission message | "The Bash permission system blocked the `git push origin main` command. To execute the push you authorized (\"可以的，你启动一下,review也由你来做\"), please approve the Bash command in the Claude Code UI permission dialog. The push will publish 42 commits (Wave 275..Wave 324, ending at `0cd3638` 'TNNLS submission package + PUSH to origin/main') to origin/main on github.com/silverenternal/flowa-multistep-reinference." |
| Local commit ready? | **YES** — `0cd3638` exists locally with the full TNNLS submission package; only the network push operation is blocked |
| Reproducibility | Local commit is immutable at SHA `0cd3638`; all 5-gate verifications below run against this exact tree |

### What USER must do to complete the push

The network operation `git push origin main` requires an explicit per-command authorization at the Claude Code permission dialog. Two equivalent paths:

**Path A — approve the Bash permission dialog** (recommended):
1. In the Claude Code UI, when the prompt for `git push origin main` reappears, click **"Allow"**.
2. The subagent will re-execute the push, verify `origin/main == 0cd3638`, and re-run the 5-gate.

**Path B — manual push from a terminal**:
```bash
cd /home/hugo/codes/flowa-multistep-reinference
git push origin main
git rev-parse origin/main   # should print 0cd3638944bbcad144ebdf8110d3143bf8d782a5
```

After the push, the user (or a follow-up wave) should re-verify origin/main == HEAD and re-hash `tnnls_submission/MANIFEST.md` if any USER-fill of the cover letter placeholders happened in between.

---

## 2. Post-Push Verification

Not executed (push blocked). Verification command set for the post-push confirm step:

```bash
git rev-parse origin/main   # expect 0cd3638944bbcad144ebdf8110d3143bf8d782a5
git rev-parse HEAD          # expect 0cd3638944bbcad144ebdf8110d3143bf8d782a5
git diff --stat origin/main..HEAD  # expect empty (HEAD == origin/main)
```

Both SHAs must match exactly. The push-execution agent re-runs `git rev-parse origin/main` immediately after a successful push and emits the result for human confirmation.

---

## 3. 5-Gate Re-Verification (Wave 325, post-Wave-324 snapshot at `0cd3638`)

All 5 gates re-run locally against the unchanged tree at `0cd3638`. The TNNLS submission package is reproducible from this commit.

### Gate (a) — ruff lint

```
$ ruff check adaptive_reflow/ tests/
All checks passed!
```

**Status: PASS** (0 errors).

### Gate (b) — pytest test_contracts

```
$ pytest tests/test_contracts/ -v
======================= 195 passed, 3 warnings in 0.57s =======================
```

**Status: PASS** (195 tests, well above 30 minimum for D.4; 3 deprecation warnings are pre-existing and do not affect byte-stable test outcomes). Coverage:

- `tests/test_contracts/test_audit.py`
- `tests/test_contracts/test_materialization_typed.py`
- `tests/test_contracts/test_paper_quantities.py`
- `tests/test_contracts/test_state_channel.py`
- `tests/test_contracts/test_state_machine.py`

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

**Status: PASS** (no drift; CLM-040 PROVISIONAL status is pre-existing from Wave 7 and not introduced by Waves 311-324).

### Gate (d) — mkdocs strict build

```
$ timeout 90 mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: .../site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 22.61 seconds
```

**Status: PASS** (0 project warnings; the only output is the Material for MkDocs upstream advisory about MkDocs 2.0, which is informational, not a project-side warning).

### Gate (e) — vendored data untouched

```
$ git diff --name-only HEAD~1..HEAD | grep -E "data/FlowMol3/|data/lineageflow_upstream/|data/Kanzi/"
(no output; exit code 1 from grep)
```

**Status: PASS** (no vendored checkpoints touched in Wave 324 HEAD commit). The 11 files modified are: 1 audit doc (`docs/audit/wave324-d5-review.md`), 2 manuscript files (`docs/drafts/paper-flat-ieeetran.{tex,pdf}`), 5 pdflatex log/aux files (`docs/drafts/paper-flat-ieeetran.aux`, `.log`, plus 4 `pdflatex-rerun*.log`), 3 submission-package files (`tnnls_submission/MANIFEST.md`, `tnnls_submission/README.md`, `tnnls_submission/supplementary/README.md`).

### 5-Gate Summary

| Gate | Description | Status | Detail |
|------|-------------|--------|--------|
| (a) | ruff lint (0 errors) | PASS | "All checks passed!" |
| (b) | pytest test_contracts (≥30) | PASS | 195 passed |
| (c) | claims consistency (no drift) | PASS | 61 active, 0 provisional drift |
| (d) | mkdocs strict build (0 warnings) | PASS | 22.61 s build, 0 project warnings |
| (e) | vendored data untouched | PASS | grep returns no matches |

**Overall: 5/5 PASS** — D+8 ScholarOne submission authorization may proceed once the 17 cover-letter placeholders are filled.

---

## 4. D+8 ScholarOne Submission Instructions

> **PREREQUISITE:** USER must (1) complete the network push per §1, and (2) fill the 17 `USER TO FILL` placeholders in `tnnls_submission/cover_letter.md` per `tnnls_submission/FILL_GUIDE.md` BEFORE following these steps.

### Step 1 — Login to ScholarOne

URL: https://scholarone.manuscriptcentral.com/tnnls

Use the corresponding author's IEEE ScholarOne credentials. If the corresponding author does not yet have a ScholarOne account, register at https://scholarone.manuscriptcentral.com/registration (use ORCID for fastest verification).

### Step 2 — Start new submission

- Click **"New Submission"** in the Author Dashboard.
- Journal: *IEEE Transactions on Neural Networks and Learning Systems*.
- Manuscript type: **Regular Paper** (this submission is 10 pages, well within the TNNLS Regular Paper budget).
- Title (verbatim from `docs/drafts/paper-flat-ieeetran.tex`):
  > FlowA: Training-Free, Paper-Quantity-Driven Re-Inference for Flow-Matching Checkpoints

### Step 3 — Upload manuscript files

In the **Files** step:

1. **Main manuscript (PDF):** Upload `docs/drafts/paper-flat-ieeetran.pdf` (381.5 KB, 10 pages, IEEEtran-journal double-column).
2. **Cover letter:** Convert `tnnls_submission/cover_letter.md` (60.4 KB, 17 placeholders filled) to PDF (`pandoc cover_letter.md -o cover_letter.pdf` or via Google Docs / Word export) and upload as **"Cover Letter"** file type.
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
| Suggested reviewers | 5 reviewers per `cover_letter.md` §9 (USER-FILLED; 10 fields total: affiliation + email per reviewer) |

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

## 5. Verification Output — SHA-256 Ledger (snapshot at `0cd3638`)

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

- Wave 325 push-execution + 5-gate re-verification: this document (`docs/audit/wave325-push-execution.md`)
- Wave 324 D+5 review: `docs/audit/wave324-d5-review.md`
- Wave 324 TNNLS submission package: `tnnls_submission/`
- Wave 323 IEEEtran typeset: `docs/drafts/paper-flat-ieeetran.tex` (10-page output)
- Wave 322 Path A lemmas 2-3: `docs/audit/wave322-path-a-lemmas-2-3.md`
- Wave 311 Path A lemma 1: `docs/audit/wave311-...md`

---

## 6. Awaiting User Decisions (3 items)

1. **APPROVE the bash permission for `git push origin main`** (Path A) **OR run the manual push** (Path B). After this completes, `origin/main == 0cd3638` and the local/remote divergence closes.
2. **Fill 17 `USER TO FILL` placeholders** in `tnnls_submission/cover_letter.md` per `tnnls_submission/FILL_GUIDE.md`:
   - 1 × Authors block (line 51-52)
   - 1 × Suggested AE (line 56 + line 986)
   - 1 × Suggested Reviewers header pointer (line 60)
   - 5 × reviewer × {affiliation, email} = 10 reviewer fields (§9)
   - 3 × corresponding author × {name, affiliation, email} (line 1126-1128)
   After filling, `grep -c 'USER.TO.FILL' tnnls_submission/cover_letter.md` should return 14 (only §0 documentation pointers + §0 convention text remain).
3. **D+8 ScholarOne submission** — execute Steps 1-7 of §4 above after the push completes and the cover letter is filled.

---

## 7. Summary

**Wave 325 status:**
- Push: **BLOCKED** at permission gate (USER authorization required for the network operation).
- 5/5 gate verification: **PASS** locally at `0cd3638`.
- D+8 submission package: **READY** (10-page PDF, 60.4 KB cover letter with 17 placeholders pending, 23.3 KB figures, 7.4 KB tables, 7.1 KB data availability, 11.3 KB supplementary bundle).
- 3 user-decision items outstanding (push authorization, cover-letter fill, D+8 ScholarOne submission).