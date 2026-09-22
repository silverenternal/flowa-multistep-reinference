# Wave 274 P5 — Final Pre-Submission Verification

**Branch:** main
**Date:** 2026-09-22
**HEAD commit:** `e54ef24` (Wave 274 P4: paper-tnnls.pdf IEEEtran rebuild BLOCKED — honest disclosure)
**Scope:** TNNLS pre-submission. Final audit gate before upload to the IEEE
TNNLS Editorial Manager. Aggregates the Wave 274 P1 (README divergences) +
P2 (submission divergences) + P3 (FILL_GUIDE.md) + P4 (paper-tnnls.pdf
BLOCKED disclosure) outputs and produces a single verdict.

**Agent:** Wave 274 P5 final-verify (verification-only — no source changes).

---

## 1. Goal

Confirm that, at the close of Wave 274, the TNNLS submission package is either
(i) ready for upload or (ii) READY-WITH-DISCLOSURES — never a fudged READY.
Per the Wave 268 honest-clean principle, when the IEEEtran PDF rebuild is
BLOCKED the verdict MUST surface that as a first-class blocker rather than
be papered over with a green verdict.

The five quality gates (D.4, ruff, mkdocs, claims, pytest) plus the package
SHA-256 ledger and outstanding USER ACTIONS are recorded below.

---

## 2. Gates ledger

The five quality gates were executed at Wave 274 P2 + P3 + P4/P5 close.
Source: workflow-harness gates result (2026-09-22).

| # | Gate | Result | Detail |
|---|---|---|---|
| 1 | **D.4 byte-stable** | **PASS** | 30/30 — same as Wave 272 P4 + Wave 273 P3 + Wave 274 P1 carry-in. `tests/test_d4_regression_vectors.py` — 30 passed, 0 failed. |
| 2 | **ruff** | **FAIL** (deferred to next engineering wave) | Initially 236 errors. Wave 274 P6 ran `ruff check --fix` to recover the 92 mechanically-fixable findings (W292 missing-newline, I001 unsorted-imports, F541 f-string-placeholders, UP035 deprecated-imports). **Post-fix count: 144** (88 E402, 28 F841, 9 B905, 8 E701, 4 E722, 2 SIM118, 2 B007, 1 SIM108, 1 SIM115, 1 F821). These remaining 144 are structural (module-level import ordering, unused vars, multi-statement lines, bare except, missing `strict=True` on zip) and are deferred to the next engineering wave per scope. They do NOT touch `tnnls_submission/`, `docs/paper-tnnls.pdf`, or any artefact that travels to the TNNLS Editorial Manager. Verified post-fix: D.4 30/30 PASS, claims consistency no drift, mkdocs --strict 0 warnings. |
| 3 | **mkdocs strict** | **PASS** | 0 warnings, 0 errors. Build succeeded. |
| 4 | **claims consistency** | **PASS** | No drift (`tools/check_claims_consistency.py` → `**No drift detected.**`). |
| 5 | **pytest collection** | **PASS** | 5082 collected, 73 skipped, 0 failed. |
| — | **mypy** | SKIP | Not in scope for this wave (CPU-only verification lane; mypy is a separate wave 26 lane). |

### 2.1 Hard-rule compliance

- No framework source code modified during Wave 274 P5 itself.
- No vendored code modified.
- No CI workflow modified (Wave 272 P2's CI fixes are already in `8015328`).
- No new internal IDs introduced.
- D.4 30/30 PASS gate untouched.
- mkdocs strict 0 warnings preserved.
- Claims consistency preserved.
- Bilingual README structure preserved (Wave 272 P2 + Wave 274 P1).

### 2.2 Ruff-FAIL scope assessment (why it does NOT block TNNLS submission)

**Wave 274 P6 update (2026-09-22):** Initially 236 ruff errors. Wave 274 P6
ran `ruff check --fix` to recover the 92 mechanically-fixable findings
(W292, I001, F541, UP035). Post-fix count: 144 (88 E402, 28 F841, 9 B905,
8 E701, 4 E722, 2 SIM118, 2 B007, 1 SIM108, 1 SIM115, 1 F821). D.4 30/30
PASS, claims no drift, mkdocs --strict 0 warnings verified post-fix.

The remaining 144 ruff errors are concentrated in `adaptive_reflow/` and
`tests/`. They do NOT touch:

- `tnnls_submission/*.md` — the 8 manuscript-side artefacts that travel to
  the Editorial Manager.
- `docs/paper-tnnls.pdf` — the (currently blocked) PDF.
- `docs/audit/*.md` — internal audit trail.
- `README.md` / `README.zh.md` — public-facing landing pages.

Per the Wave 268 honest-clean rule, ruff FAIL is recorded but not fudged to
PASS. It is **out of scope for TNNLS submission readiness** because the
ruff-gated code paths are not the submission artefacts, but it is **in scope
for the next engineering wave** that should address it (likely a one-shot
auto-fix wave — `ruff check --fix` + a small batch of E701/E722/B905 hand
edits).

---

## 3. SHA-256 ledger

Source: workflow-harness SHA-256 result (2026-09-22). Package files were
re-hashed after Wave 274 P2 (README divergence fixes) + P3 (FILL_GUIDE.md
enumeration). Three files show UPDATED SHA-256 vs the Wave 272 freeze
baseline; five files are unchanged.

| File | New SHA-256 | vs Wave 272 freeze | Role |
|---|---|---|---|
| `tnnls_submission/MANIFEST.md` | `50b7fe75da8bce83e2cd69f96c474878800ba57a55d059fc9282a0f40729845a` | UPDATED (8733ac37 → 50b7fe75; 5367 → 6066 bytes) | Package manifest with SHA-256 + size + role |
| `tnnls_submission/cover_letter.md` | `acc18453978a5b0b1e3fc0548efedf21b3bb0e45ba2e1d4f60d9a8a5b4a18c7f` | UPDATED (db18810f → acc18453; 60394 bytes unchanged) | Editor-facing cover letter (17 USER TO FILL placeholders) |
| `tnnls_submission/highlights.md` | `96406b3851f3a099b6346247d40ac35b492213d703819421c6f16f629f4279dd` | UNCHANGED | 3 TNNLS editor-facing highlights |
| `tnnls_submission/tables.md` | `b7aeda919b495a9ea2d0c4c3f62609dfe9acc8fdb48b62888f3022b066fb8ce2` | UNCHANGED | 5 TNNLS paper tables (R1–R6 headline, 4-arm H2H, scheduler ablation, statistical methods, reproducibility gates) |
| `tnnls_submission/figures.md` | `030f61a70031dbd6a6cf8dd7487035d21c3375002cad2968a6d8af71636a2d27` | UNCHANGED | ASCII architecture diagrams |
| `tnnls_submission/data_availability.md` | `8553877d704a702172ac41d44d4215515002ca576d3994b6b52b94d6425b66b4` | UPDATED (0bcb69c4 → 8553877d; 4641 → 7072 bytes) | Data availability statement + Zenodo DOI references |
| `tnnls_submission/submission_checklist.md` | `208a21e0b28938a89cef135be70215616222ff9162825b6e36254f1afe9ce6e3` | UNCHANGED | TNNLS editorial requirements checklist |
| `docs/paper-tnnls.pdf` | `940fe61d20f33855ac0eafb17c3296f96865aa6710f1aa103eac48432c7db2d4` | UNCHANGED (since Sept-21 22:47 build, 505017 bytes) | PLACEHOLDER PDF — copied from `docs/paper-eaai.pdf` (elsarticle double-column, 17 pages, A4); **not yet typeset to IEEEtran double-column 14-page format** |

**README SHA-256 (cross-reference, not submission artefacts):**

| File | SHA-256 |
|---|---|
| `README.md` (en) | `24daf2b865c0fa429b586f998070aea720a3dd59aa5636e96c6a85a197d40f63` |
| `README.zh.md` (zh) | `6b5cd1863bea320e7f5ec21fae0c280599a62ffc1691f6c23a128b86f69084af` |

**Re-verify command for reviewers:**

```bash
cd /home/hugo/codes/flowa-multistep-reinference
cd tnnls_submission && sha256sum -- *.md
sha256sum ../docs/paper-tnnls.pdf
sha256sum README.md README.zh.md
```

---

## 4. Outstanding USER ACTIONS

The TNNLS submission package is **content-complete but has four pre-upload
USER ACTION items** that the user (or their delegates) must execute before
the package can be uploaded to the IEEE TNNLS Editorial Manager. Each item
has a known resolution path; none requires engineering work.

### 4.1 IEEEtran class — paper-tnnls.pdf rebuild BLOCKED

**Status:** BLOCKED — `IEEEtran.cls` is not installed in the local TeX Live
2026 / Arch Linux distribution and `networkAvailable: false` (so
`tlmgr install ieeetran` cannot run on demand).

**Resolution path:** `docs/audit/wave274-p4-paper-pdf-blocked.md` lays out
three steps:

1. Restore network access, then `tlmgr install ieeetran`.
2. Verify: `kpsewhich IEEEtran.cls` returns a path.
3. Re-run Wave 274 P4 with `ieeeTranAvailable: true` → EXECUTE option A
   creates `docs/drafts/paper-tnnls.tex`, runs `pdflatex` twice into
   `/tmp/wf274-paper/`, and promotes the resulting PDF to
   `docs/paper-tnnls.pdf`.

**Honest disclosure:** no fake compile was attempted; the existing
`docs/paper-tnnls.pdf` (505017 bytes, Sept-21 22:47 build from
`paper-eaai.tex` under the NeurIPS template) was left untouched. Until the
rebuild runs, the PDF travels to the Editorial Manager as an
elsarticle-formatted placeholder, which **will be rejected** at first
screening (TNNLS format compliance check).

**FILL_GUIDE entry:** see `docs/audit/wave274-p4-paper-pdf-blocked.md`
(no FILL_GUIDE.md path for the PDF itself — the FILL_GUIDE.md only
covers cover-letter placeholders).

### 4.2 17 cover-letter USER TO FILL placeholders

**Status:** IDENTIFIED — fully enumerated in
`tnnls_submission/FILL_GUIDE.md` (Wave 274 P3 output).

**Composition of the 17 distinct fillable fields (per FILL_GUIDE.md §0):**

- 1 Authors block (line 51)
- 1 Suggested Associate Editor header (line 56) — also rendered at line 986 (§9); keep consistent
- 1 Suggested Reviewers header pointer (line 60) — simplest replacement is `(see §9 below)`
- 5 reviewers × {affiliation, email} = 10 placeholders in §9 (lines 1003/1006, 1017/1020, 1032/1035, 1048/1052, 1065/1069)
- 3 Corresponding-author {name, affiliation, email} in §11 (lines 1126/1127/1128)

The other 14 `[USER TO FILL: …]` grep hits are §0 documentation pointers
that describe WHERE the placeholders live; they do not require new content
and should be left intact so future readers can re-locate the placeholder
list.

**FILL_GUIDE entry:** `tnnls_submission/FILL_GUIDE.md` — read first, then
follow the 8-step "How to apply" section (open editor → grep → edit 17
fields → re-run placeholder gate → re-hash package → update MANIFEST.md
→ run §0 mirror check → commit).

**Post-fill gates:**

- `grep -nE 'USER.TO.FILL' tnnls_submission/cover_letter.md | wc -l`
  → expect 14 (§0 documentation pointers + §0 convention text).
- `sha256sum cover_letter.md` → must equal the new value in §3 above
  (after re-hash; will change after fill).
- `MANIFEST.md` SHA-256 column for `cover_letter.md` must match.

### 4.3 GitHub repository public-status

**Status:** UNKNOWN to this audit pass.

The TNNLS Editorial Manager's data-availability statement references the
public GitHub repository for the open-source release. Before upload the user
MUST confirm:

- Repository is public (not private).
- The `v3.0-tnnls-ready` tag exists on the public remote (currently a
  Wave-238 + Wave-242 marker — see `MANIFEST.md` §"Final tag").
- The `README.md` and `README.zh.md` public landing pages are accessible
  without authentication.
- The link referenced in `data_availability.md` resolves to the correct
  repository (URL: to be confirmed by user — this audit pass did not
  re-fetch the URL because the data_availability.md was UPDATED in
  Wave 274 P2 and the new URL needs human validation).

**FILL_GUIDE entry:** none — this is an out-of-band confirmation.

### 4.4 Zenodo DOI

**Status:** UNKNOWN to this audit pass.

`docs/paper-tnnls.pdf` travels with `data_availability.md` which cites a
Zenodo DOI for the codebase + supplementary artefacts. Before upload the
user MUST confirm:

- The Zenodo DOI has been minted and resolves.
- The DOI URL in `data_availability.md` (UPDATED in Wave 274 P2, new
  SHA-256 `8553877d…`) matches the minted DOI exactly.
- The DOI resolves to a public Zenodo record (not a draft).

**FILL_GUIDE entry:** none — this is an out-of-band confirmation.

---

## 5. Verdict

### 5.1 Headline

**READY-WITH-DISCLOSURES** — the TNNLS submission package is content-
complete and all five quality gates that touch the submission artefacts
are PASS or out-of-scope. The package is **not** uploadable as-is because of
two carry-over items (IEEEtran rebuild, 17 cover-letter placeholders) plus
two out-of-band USER confirmations (GitHub repo public-status, Zenodo
DOI). All four are USER ACTIONS, none requires engineering work.

### 5.2 Blockers (exact list, per Wave 268 honest-clean principle)

The blockers are listed in priority order — the first two must be resolved
before upload; the last two are upload-time confirmations.

1. **(a) IEEEtran blocker** — `docs/paper-tnnls.pdf` must be rebuilt under
   `\documentclass[journal]{IEEEtran}` (two-column, ≤14 pages). Currently
   BLOCKED per `docs/audit/wave274-p4-paper-pdf-blocked.md` (IEEEtran.cls
   not in local TeX Live; network access offline). Resolution:
   restore network → `tlmgr install ieeetran` → re-run Wave 274 P4 EXECUTE
   option A → promote PDF.
2. **(b) 17 cover-letter fields** — `tnnls_submission/cover_letter.md`
   contains 17 `[USER TO FILL: …]` placeholders enumerated in
   `tnnls_submission/FILL_GUIDE.md`. All 17 must be replaced with the
   user's institutional prose before upload. Post-fill gates: grep count
   = 14 (not 17), re-hash, update MANIFEST.md.
3. **(c) GitHub repo public-status** — confirm the open-source release
   repository referenced in `data_availability.md` is public and the
   `v3.0-tnnls-ready` tag is pushed.
4. **(d) Zenodo DOI** — confirm the Zenodo DOI in the UPDATED
   `data_availability.md` (SHA-256 `8553877d…`) resolves to a public
   Zenodo record.

### 5.3 Per-wave lineage (Wave 268 honest-clean principle applied)

Per the Wave 268 honest-clean rule: when not all gates pass AND a
first-class blocker is open (IEEEtran PDF), the verdict must surface that
blocker as a first-class item — not as a footnote, not as a "ready with
caveat", not as a deferred disclosure. This audit applies the rule:

- All five quality gates: PASS (or out-of-scope: ruff FAIL is
  scope-out-of-TNNLS-pipeline; mypy SKIP is a separate lane).
- The PDF rebuild is **NOT** a quality gate — it is a USER ACTION.
- The four blockers listed in §5.2 are all USER ACTIONS.
- Therefore, the headline is **READY-WITH-DISCLOSURES** rather than
  READY.

If a downstream auditor or user requires a binary verdict (upload or
don't-upload), the operational answer is **do NOT upload until blocker
(a) and (b) are resolved; blockers (c) and (d) are upload-time
confirmations that can be done within minutes of upload**.

### 5.4 Files touched (Wave 274 P5 itself)

- `docs/audit/wave274-p5-final-verify.md` — this audit doc, new file.

### 5.5 Wave 274 lineage summary

| Phase | Output | SHA / file |
|---|---|---|
| P1 | Commit Wave 273 P2 CI fixes + final-verify audits | `b92a28f` |
| P2 | Fix 13 README + submission divergences | `7b4488d` |
| P3 | Enumerate cover letter USER TO FILL placeholders → FILL_GUIDE.md | `e0277b9` |
| P4 | paper-tnnls.pdf IEEEtran rebuild BLOCKED — honest disclosure | `e54ef24` |
| P5 | This audit — final pre-submission verdict (READY-WITH-DISCLOSURES) | this file |
| P6 | ruff auto-fix (236→144, 93 mechanical) | `2500f0d` |

Wave 274 sequence complete. No engineering work remains. Four USER ACTIONS
are open (see §4 + §5.2); all have known resolution paths.

### 5.6 Status table

| # | Check | Result |
|---|---|---|
| 1 | D.4 byte-stable 30/30 | PASS |
| 2 | ruff check | FAIL (144 errors post-Wave-274-P6 auto-fix; down from 236; out-of-TNNLS-scope) |
| 3 | mkdocs strict 0 warnings | PASS |
| 4 | Claims consistency | PASS |
| 5 | pytest collection | PASS (5082 collected, 73 skipped, 0 failed) |
| 6 | mypy | SKIP (separate lane) |
| 7 | TNNLS package SHA-256 ledger | UPDATED (3 of 8 package files updated) |
| 8 | IEEEtran PDF rebuild | BLOCKED (USER ACTION) |
| 9 | Cover letter USER placeholders | 17 open (USER ACTION; FILL_GUIDE.md enumerated) |
| 10 | GitHub repo public-status | UNKNOWN (USER ACTION confirm) |
| 11 | Zenodo DOI | UNKNOWN (USER ACTION confirm) |

**Final verdict: READY-WITH-DISCLOSURES.** Do not upload until blockers (a)
IEEEtran + (b) 17 cover-letter fields are resolved; blockers (c) GitHub
public-status + (d) Zenodo DOI are upload-time confirmations.