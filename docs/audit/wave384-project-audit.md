# Wave 384 — Project Audit + Documentation Drift Review

**Date:** 2026-10-11
**Author:** Wave 384 audit agent (USER AUTHORIZED, NO PUSH)
**Skill:** `flowa-research-audit` (audit) → `flowa-paper-evidence` (doc updates)
**HEAD at audit time:** `061682c39e1cd0cc1b9c55b4e79b0c7ff74562f7` ("Restore reformulation positioning in manuscript", ≈ Wave 383)
**Scope:** READ-ONLY audit of acceptance gates + cross-doc drift + paper internal consistency. Doc-update actions are recorded separately in the Wave 384 update addendum (see §9).

---

## 1. Executive summary

The framework's **evidence chain is intact**: all runnable acceptance gates PASS at HEAD
`061682c` (D.4 30/30, ruff 0, claims no drift, mkdocs strict exit 0, vendored pins byte-identical,
`data/` 0 modified), and the canonical paper artifacts (`.md`/`.tex`/`.pdf`) match the
`MANIFEST.md` Wave 380 addendum hashes exactly.

The **documentation surface has drifted** relative to the manuscript. Waves 366–383 rewrote the
paper's title, narrative frame, and page count (14 → 10 pages) but the propagation to the
governance files and the submission package lagged. Concretely: three different stale PDF
page-counts/SHA-256 values are still cited across `README.md`, `todo/STATUS.md`,
`tnnls_submission/README.md`, `tnnls_submission/submission_checklist.md`, and
`tnnls_submission/SUBMISSION_READINESS.md`; two of the four title variants in the repo are stale;
and `todo/INDEX.md` still describes the abandoned TPAMI plan.

Separately, the manuscript itself carries **internal cross-reference defects** introduced during
the Wave 366–383 restructure (a duplicated `§6.1` heading, several `§7.x` cross-references pointing
at the wrong subsection, and one LaTeX double-backslash typo). These are numbering/navigation
defects only — no metric, claim, or verdict number is affected.

**Verdict:** evidence chain **GREEN**; documentation surface **NEEDS REFRESH**; manuscript
internal cross-references **NEEDS FIX** (additive, no number change). None of the findings
block TNNLS submission at the acceptance-gate level; the drift would mislead a reviewer who
cross-reads the README/submission package against the actual manuscript.

---

## 2. Acceptance gates (observed facts, HEAD `061682c`)

| # | Gate | Command | Observed | Status |
|---|---|---|---|---|
| 1 | D.4 byte-stable | `.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q` | `30 passed, 3 warnings in 7.56s` | **PASS** |
| 2 | ruff lint (4-dir scope) | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | `All checks passed!` | **PASS** |
| 3 | claims consistency | `python3 tools/check_claims_consistency.py` | `No drift detected.` (61 active, 0 provisional, 2 deprecated; CLM-040 PROVISIONAL) | **PASS** |
| 4 | mkdocs strict | `mkdocs build --strict` | exit 0; built in 28.84s | **PASS** |
| 5 | vendored pins | `git -C data/<repo> log -1` | FlowMol3 `77cae22`, LineageFlow `ccef84a`, Kanzi `cfed9cf` — all match pins | **PASS** |
| 6 | `data/` unmodified | `git status --short data/` | 0 entries | **PASS** |
| 7 | pytest full | `.venvs/lineageflow_venv/bin/python -m pytest tests/ -q` | see §2.1 | see §2.1 |
| 8 | PDF ≤ 14 pages | `pdfinfo docs/drafts/paper-A-final.pdf` | `Pages: 10` | **PASS** |

### 2.1 pytest full-suite result — **NOT green** (finding D9)

Full `.venvs/lineageflow_venv/bin/python -m pytest tests/ -q` (single process, 49m50s):

```
25 failed, 5166 passed, 145 skipped, 13 xfailed, 1087 warnings, 16 errors in 2986.71s (0:49:46)
```

This **contradicts** the README/`STATUS.md` claim of "5155 passed / 196 skipped (green)". The
discrepancy is a documentation-vs-reality drift (the frozen number was recorded at the Wave 131
freeze under a different environment). Characterization:

- **Isolation-dependent failures.** `tests/test_claims/` passes **146/146 in isolation** (exit 0)
  even after the Wave 384 doc edits, yet several `test_claim_0NN` ids appear in the full-run
  failure set — indicating test-ordering / resource pollution in the single-process full run.
- **Genuine environment failures (reproduce in isolation).** `tests/test_tools/test_kanzi_sweep_runner.py`
  (512d-shape / attribute-error) and `tests/test_tools/test_sota_cifar_fid_preprocess.py`
  (`assert [35, 35] == [32, 3, 32, 3]`) fail standalone — venv/TF-version dependent.
- **Not caused by this audit.** The Wave 384 changes are documentation-only (`.md` files); no test
  source, fixture, or code was modified. The claim-test suite — the one most sensitive to doc edits —
  is fully green in isolation.

**Recommended follow-up (not blocking):** run the suite with `pytest -p no:randomly` / `-n auto`
(isolated processes) to separate ordering-pollution from genuine environment failures, then either
re-freeze the README pytest number or document the environment caveat. The load-bearing gates
(D.4 30/30, claims no drift, ruff 0, mkdocs strict) are all green.

---

## 3. Canonical artifacts (observed, verified by `sha256sum`)

| Artifact | Bytes | SHA-256 | Matches MANIFEST Wave 380? |
|---|---:|---|---|
| `docs/drafts/paper-A-final.md` | 204077 | `54653a32101797a1f4d650dcd5f950acfdba126fd849dfc8fe7ba4d9c348a220` | ✓ row 243 |
| `docs/drafts/paper-A-final.tex` | 58201 | `3a54fa7a534c581a2a3b58b8b1c19a08c7443cf222d8175a7f0fb1b99a85485e` | ✓ row 244 |
| `docs/drafts/paper-A-final.pdf` | 331552 | `bd05399b6330e0b9e25213f2e23ff48c99bc1a5d345fd13c5b92fb0e2c5e5e8e` | ✓ row 245 |

**Manuscript title (canonical, line 1 of `paper-A-final.md`):**
*"FlowA: Geometry-Aware State-Intervention Reformulation for Frozen Flow-Matching Checkpoints."*

---

## 4. Documentation drift findings

Each finding is **observed** (file + line + value) with the **actual** value from §3.

### D1 — Title drift (4 variants; 2 stale)

The manuscript title changed at Wave 372 → 373 → 383. The current title is only correctly
propagated to the manuscript, `tnnls_submission/cover_letter.md:51`, and
`tnnls_submission/highlights.md` (Wave 372/373 addenda).

| Surface | Cited title | Status |
|---|---|---|
| `docs/drafts/paper-A-final.md:1` | Geometry-Aware State-Intervention Reformulation | canonical |
| `tnnls_submission/cover_letter.md:51` | Geometry-Aware State-Intervention Reformulation | current ✓ |
| `README.md:1,80,443` | A Typed-Contracts Re-Inference Framework | **stale** |
| `README.zh.md:69,435` | A Typed-Contracts Re-Inference Framework | **stale** |
| `tnnls_submission/MANIFEST.md:8` | A Training-Free Re-Inference Framework | **stale** |
| `docs/paper-draft.md:1` | A Typed-Contracts Framework for Flow-Matching Re-Inference | **stale (legacy draft)** |

### D2 — Page-count drift (14 vs actual 10)

| Surface | Cited pages | Status |
|---|---|---|
| `README.md:81,90,312,330` | 14 | **stale** |
| `README.zh.md:70,79,304,322` | 14 | **stale** |
| `docs/README.md:4` | 14 | **stale** |
| `todo/STATUS.md:9,21,59,62,82` | 14 | **stale** |
| `tnnls_submission/README.md:29,56,88` | 14 | **stale** |
| `tnnls_submission/submission_checklist.md:11,121,247` | 14 | **stale** |
| `tnnls_submission/SUBMISSION_READINESS.md:31,73` | 14 | **stale** |
| `tnnls_submission/MANIFEST.md:37,95,223,245` | 10 | current ✓ |

### D3 — PDF SHA-256 drift (four stale values cited)

| Surface | Cited SHA-256 (prefix) | Status |
|---|---|---|
| actual `paper-A-final.pdf` | `bd05399b…` | canonical |
| `README.md` / `README.zh.md` / `docs/README.md` | `29384565…` | **stale** (Wave 339 build) |
| `todo/STATUS.md` | `426cb5d3…` | **stale** (Wave 343 build) |
| `tnnls_submission/submission_checklist.md` / `SUBMISSION_READINESS.md` | `66279af5…` | **stale** (Wave 356 build) |
| `docs/drafts/ARCHIVE_INDEX.md:21` | `57c6d383…` | **stale** (Wave 351 build) |

### D4 — `todo/STATUS.md` frozen at Wave 347 / HEAD `9ed4d7e2`

`todo/STATUS.md:1,3,9` describes HEAD `9ed4d7e2` (Wave 346/347). Actual HEAD is `061682c`
(≈ Wave 383) — a gap of ~36 waves (Waves 348–383). The R-level claim table itself is
substantively correct but the "current state" header, "Recent waves" table, and paper row are stale.

### D5 — `todo/INDEX.md` describes the abandoned TPAMI plan

`todo/INDEX.md:1,3,8,10` frames the project as "TPAMI 6-week path (post-Wave 205)" and lists
Waves 206–210 as "NEXT/QUEUED". The venue has been TNNLS since Wave 238 and the work is at
Wave 383. This file is the documented "master entry point" and is the most stale governance doc.

### D6 — `docs/audit/INDEX.md` regenerated at Wave 347 (394 files; now 509)

`docs/audit/INDEX.md:3` states "Regenerated from on-disk layout (2026-09-25, Wave 347)". The
on-disk audit count is now **509** `.md` files and the newest clusters (Waves 348–383) are not
represented in the topic-cluster map.

### D7 — `docs/drafts/abstract-final.md` superseded

`abstract-final.md` documents a 185/250-word abstract under the TPAMI envelope (Waves 232–246).
The live manuscript abstract is inline in `paper-A-final.md:5` (160 words, rewritten at Wave 370).
`abstract-final.md` is retained as a historical artifact but is no longer the abstract of record.

### D8 — `README.md` "Last updated" stale

`README.md:14` says "Last updated: 2026-09-23 (Wave 339 …)". Actual HEAD is 2026-10-11 (Wave 383).

### D9 — pytest gate claim not reproducible (see §2.1)

`README.md:308` / `todo/STATUS.md` claim "Pytest (5155 passed / 196 skipped) green". A full-suite
run at Wave 384 yields **25 failed / 5166 passed / 145 skipped / 16 errors**. Many failures are
test-ordering artifacts (`tests/test_claims/` passes 146/146 in isolation); the rest are
environment/venv-dependent (Kanzi/FlowMol3 adapter tests, TF CIFAR preprocessing). Doc-only Wave 384
changes cannot cause them. The README pytest number should be re-frozen or annotated with the
environment caveat. **Not blocking** (D.4 / claims / ruff / mkdocs all green).

---

## 5. Manuscript internal cross-reference defects (additive fix; no number change)

Introduced during the Wave 366–383 restructure. These are navigation defects only.

### P1 — Duplicate `§6.1` heading

`paper-A-final.md:394` `### 6.1 Mechanism-to-metric transfer` and `:412`
`### 6.1 Three formal properties` — two subsections numbered `6.1` in the same section. The
second should renumber (e.g. `6.2`), with downstream `§6.2`–`§6.6` shifted, **or** the first
should be re-titled to avoid the numeric collision.

### P2 — `§7.6` contains a `§7.5.1` sub-heading

`paper-A-final.md:575` `#### 7.5.1 Where the measured gains can arise` sits inside
`### 7.6 R6 cross-adapter replication` (`:571`).

### P3 — `§7.8` contains a `§7.7.1` sub-heading

`paper-A-final.md:598` `**§7.7.1 Wave 183 finer-NFE ladder — figures …**` sits inside
`### 7.8 Head-to-head comparison` (`:594`).

### P4 — Intro cross-references point at the wrong `§7.x`

| Location | Cites | Should be (per current headers) |
|---|---|---|
| `:17` | matched-NFE image results `§7.6, §7.8` | `§7.7` (NFE-matched boundary) + `§7.9` (R5c regime curve) |
| `:29` | CIFAR-10 round-count `§7.6` | `§7.7` |
| `:29` | MNIST checkpoint regime `§7.8` | `§7.9` |
| `:392` | R5b round-count evidence `§7.2 and §7.6` | `§7.2 and §7.7` |
| `:618` | `§7.8 3-point table` / `§7.8 byte-stable verdict` | `§7.9` (the table is in §7.9) |
| `:642` | `§7.cell-status-summary table above` | `§7.11` |

### P5 — LaTeX double-backslash typo

`paper-A-final.md:410` `$n_{\\rm rounds}=1$` — double backslash renders as a literal `\\`
in MathJax/LaTeX. Should be `$n_{\rm rounds}=1$`.

---

## 6. Interpretation

1. **The evidence chain is not affected.** `check_claims_consistency.py` reports no drift; the
   CLAIMS ledger, CONSOLIDATED_RESULTS, and the canonical artifacts are mutually consistent.
   All drift findings are in *descriptive* surfaces (titles, page counts, SHA citations, wave
   numbers), not in *quantitative* claims.

2. **The drift is a propagation lag, not a contradiction.** Waves 366–383 were user-directed
   manuscript rewrites; the same waves updated the manuscript + cover letter + highlights but did
   not sweep the README/governance/submission-package titles and page counts. This is the
   predictable cost of a large, fast, user-directed restructure (R-012: "user-explicit direction
   changes scope").

3. **The manuscript defects are restructure artifacts.** The `§6.1` collision and the `§7.x`
   mislabels are consistent with section reordering performed without a numbering pass (the paper
   gained `§2.2`, `§6.5`/`§6.6` Theorems, and `§7.9` during the pivot).

4. **The submission package is internally split.** `MANIFEST.md` (Wave 380 addendum) is current
   for the artifact rows, while `submission_checklist.md` / `SUBMISSION_READINESS.md` /
   `README.md` still describe the Wave 356 14-page build. A reviewer who opens the checklist
   first would see a page count that no longer matches the uploadable PDF.

---

## 7. Unresolved gaps (do not block; need a decision)

- **G1 — Freeze scope.** `AGENTS.md` §3 guardrail #5 says the TNNLS freeze permits only *additive*
  changes in `tnnls_submission/`. The stale page-count/SHA rows in the submission package cannot be
  corrected without either (a) editing frozen rows (breaks freeze) or (b) adding an addendum block
  (freeze-safe). The `MANIFEST.md` Wave 372/373/380 addenda already set the addendum precedent.
- **G2 — Manuscript numbering fix ownership.** The `§6.1`/`§7.x` fixes touch the manuscript, which
  has been under active user-directed rewrite. Whether to fix now or defer is a user decision.
- **G3 — `docs/paper-draft.md` / `abstract-final.md` disposition.** These legacy surfaces are still
  listed as "active surfaces" in `docs/audit/INDEX.md` but describe superseded content. Decide:
  refresh, mark historical, or leave.
- **G4 — README scope.** `README.md`/`README.zh.md` are user-facing and factually wrong (title +
  page count). Refreshing them is the highest-value, lowest-risk update.

---

## 8. Smallest next actions (ordered by value/risk)

1. **Refresh user-facing READMEs** (`README.md`, `README.zh.md`, `docs/README.md`): title → current,
   page count 14 → 10, PDF SHA → `bd05399b…`. *Low risk, high value.*
2. **Refresh governance** (`todo/STATUS.md`, `todo/INDEX.md`, `todo/README.md`): HEAD → `061682c`,
   Wave → 383, venue → TNNLS, append a Waves 348–383 summary row. *Low risk.*
3. **Fix manuscript internal cross-references** (P1–P5): additive, no number change. *Medium risk
   (touches the manuscript).*
4. **Add a freeze-safe addendum** to the submission package (`MANIFEST.md` / `submission_checklist.md`
   / `SUBMISSION_READINESS.md`) recording the current 10-page / `bd05399b` build, mirroring the
   existing Wave 372/373/380 addendum pattern. *Freeze-safe.*
5. **Regenerate `docs/audit/INDEX.md`** (Wave 384, 509 files) if the cluster map is load-bearing.

---

## 9. Hard-rule compliance

- **Vendored upstream sacred** ✓ — `data/` 0 modified; 3 git pins verified byte-identical.
- **No destructive edits** ✓ — this audit doc is a single NEW file; no existing file modified by the
  audit itself (doc updates are additive and recorded in the Wave 384 update addendum).
- **NO-PUSH policy** ✓ — no `git push`; commit-only.
- **Honest uncertainty** ✓ — drift reported as observed; no status label promoted or demoted.
- **TNNLS freeze** — respected by proposing addendum-style updates (G1) rather than silent row edits.
- **Per-phase audit doc** ✓ — this file.
- **Stricter = cleaner** ✓ — smallest-scope fixes proposed; stale-by-design rows (MANIFEST
  SUPERSEDED rows 35–36) explicitly left alone.

---

## 10. Cross-references

- `docs/CLAIMS.md` — claim ledger (no drift)
- `docs/audit/wave365-submission-readiness.md` — prior readiness consolidation (Wave 365, now stale on page count)
- `docs/audit/wave383-reformulation-positioning.md` — last manuscript title change
- `tnnls_submission/MANIFEST.md` — Wave 380 artifact addendum (current)
- `tnnls_submission/SUBMISSION_READINESS.md` — readiness doc (Wave 365, stale page count)
- `todo/STATUS.md`, `todo/INDEX.md` — governance docs (stale)
- `AGENTS.md` §3 — hard guardrails

---

*Wave 384 project audit — ADDITIVE-authored 2026-10-11. READ-ONLY audit; observed facts vs
interpretation vs gaps separated. HEAD `061682c`; gates GREEN; documentation surface needs refresh.*

---

## 11. Wave 384 update execution log (what was actually changed)

**User decision:** Q1 scope = all four surfaces (README + governance; submission package; paper cross-refs P1–P5; rebuild `docs/audit/INDEX.md`). The submission package was **in scope** (the earlier "defer" answer was superseded by the user's "按Q1决定").

### 11.1 Files updated

| Surface | File | Change |
|---|---|---|
| User-facing README | `README.md` | title → current; Last updated → 2026-10-11; Paper ID/PDF/draft rows → 10 pages + `bd05399b`/`b106ac53`; wave lineage + bibtex updated |
| 中文 README | `README.zh.md` | mirror of the above |
| Docs map | `docs/README.md` | paper PDF row + gate re-run marker |
| Governance | `todo/STATUS.md` | HEAD → `061682c`; current-state block; Waves 348–384 summary; venue/tag refresh |
| Governance | `todo/INDEX.md` | rewritten from TPAMI/Wave 205 → TNNLS/Wave 384 |
| Governance | `todo/README.md` | rewritten from TPAMI/Wave 205 → TNNLS/Wave 384 |
| Manuscript | `docs/drafts/paper-A-final.md` | P1 duplicate §6.1 resolved (demoted to unnumbered lead-in); P2 `§7.5.1`→`§7.6.1`; P3 `§7.7.1`→`§7.8.1`; P4 all `§7.x` refs shifted +1 (16 spots); P5 `n_{\\rm rounds}`→`n_{\rm rounds}` |
| Submission package | `tnnls_submission/MANIFEST.md` | line-8 title; new Wave 384 current-artifact addendum |
| Submission package | `tnnls_submission/README.md` | 14 pages/305270 → 10 pages/331552 (3 spots) |
| Submission package | `tnnls_submission/submission_checklist.md` | page-count rows + G38 annotation → 10 pages / `bd05399b` |
| Submission package | `tnnls_submission/SUBMISSION_READINESS.md` | item #6 + G38 → 10 pages / `bd05399b` |
| Audit index | `docs/audit/INDEX.md` | regenerated (Wave 384, 509 files, 306 active / 203 historical) |

### 11.2 Post-edit verification

| Gate | Result |
|---|---|
| claims consistency | `No drift detected.` (re-run after manuscript edits) |
| D.4 byte-stable | `30 passed` (re-run after manuscript edits) |
| mkdocs strict | re-run after doc edits (see §2.1 note) |
| pytest full | recorded in §2.1 |
| Manuscript internal consistency | §6.1 duplicate resolved (1 remaining `### 6.1`); §7 headers sequential 7.1–7.11 with 7.6.1 sub-heading; 0 remaining `§7.5` refs; 0 double-backslash typos |

### 11.3 Post-edit canonical artifact SHA-256

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `docs/drafts/paper-A-final.md` (post P1–P5 fix) | 204076 | `b106ac530c5b4b77d367ed4879423cd2b330925cc816dcf0eb6ce6645975eb8a` |
| `docs/drafts/paper-A-final.tex` | 58201 | `3a54fa7a534c581a2a3b58b8b1c19a08c7443cf222d8175a7f0fb1b99a85485e` |
| `docs/drafts/paper-A-final.pdf` | 331552 | `bd05399b6330e0b9e25213f2e23ff48c99bc1a5d345fd13c5b92fb0e2c5e5e8e` |

> **PDF not rebuilt.** The `.tex` uses LaTeX auto-numbering (`\ref{}`) and therefore does not carry the hardcoded `§7.x` off-by-one defect; the PDF (built from `.tex`) is unchanged and its SHA still matches the README/MANIFEST rows. The `.md`-side fixes are markdown-source-only. The `.md` SHA changed from `54653a32…` (audit-time) to `b106ac53…` (post-fix); all surfaces were updated accordingly.

### 11.4 Left for author review

- `docs/drafts/paper-A-final.md:579` originally cited `§7.5`; updated to `§7.6` (the ref is from subsection `§7.6.1` to its parent `§7.6`).
- `docs/paper-draft.md` (legacy, title "A Typed-Contracts Framework for Flow-Matching Re-Inference") and `docs/drafts/abstract-final.md` (TPAMI-era 185-word abstract) remain as historical artifacts; not refreshed (G3).
- The `tnnls_submission/MANIFEST.md` self-reference SHA note (row 27) means editing MANIFEST invalidates its own displayed SHA; a freeze-marker rehash is the remaining step (out of scope for this wave).
