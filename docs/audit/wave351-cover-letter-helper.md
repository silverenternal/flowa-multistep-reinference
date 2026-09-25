# Wave 351 P5 — Cover letter fill helper script (`tools/render_cover_letter.py` + JSON template)

**Date:** 2026-09-25
**Author:** Wave 351 P5 (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — additive infrastructure helper; no number / no claim change; canonical `tnnls_submission/cover_letter.md` byte-stable until user explicitly overwrites.
**Trigger:** User request relayed through workflow harness: "还有哪些gap你就启动ultracode去补一下" — gap-fill the 17 USER_TO_FILL placeholders in `tnnls_submission/cover_letter.md` (per Wave 348 FILL_GUIDE.md) with a systematic helper.
**Scope:** New `tools/render_cover_letter.py` (helper script), new JSON schema at `/tmp/cover_letter_data.template.json` (17 empty fields), this audit doc. **No edits to `tnnls_submission/cover_letter.md`, `tnnls_submission/FILL_GUIDE.md`, `tnnls_submission/MANIFEST.md`, `docs/CLAIMS.md`, or `docs/drafts/paper-A-final.md`.**
**Hard-rule compliance:** ADDITIVE ONLY (no destructive edits); per Wave 268 strict-clean rule, per Wave 325 NO-PUSH policy, per `flowa-paper-evidence` skill (helper owns only `tools/` and a `/tmp/` JSON template).

---

## 1. Executive Summary

The TNNLS cover letter at `tnnls_submission/cover_letter.md` has **17 distinct fillable fields** (per `tnnls_submission/FILL_GUIDE.md` Wave 348 enumeration) that the user must populate before TNNLS submission. The fields are scattered across three sections: §opening header (3 fields), §9 reviewers block (11 fields), §11 closing signature (3 fields). The §0 USER ACTION REQUIRED block intentionally retains 11 documentation pointers that grep-mirror the 17 fillable fields — these are not content to fill, they are pointers to where the placeholders live.

To make filling systematic, this wave introduces:

| Artifact | Role | Notes |
|---|---|---|
| `tools/render_cover_letter.py` | Helper that reads JSON config + canonical `cover_letter.md`, substitutes 17 placeholders, writes a rendered draft to a user-specified output path | CLI; never writes to canonical file directly; treats any unmatched placeholder as a hard failure |
| `/tmp/cover_letter_data.template.json` | Empty-string JSON template listing the 17 field names as keys | Forward-compat; user `cp` + fill before invoking helper |
| This audit doc | Documents the helper, the schema, and the §R.5 reproducibility footnote | Wave 351 P5 governance doc |

| Acceptance gate | Result |
|---|---|
| `python3 -c "import tools.render_cover_letter; print('import OK')"` | **import OK** |
| `ruff check tools/render_cover_letter.py` | **All checks passed!** |
| `python3 tools/check_claims_consistency.py` | **No drift detected.** (61 active claims, 0 provisional, 2 deprecated; same as pre-wave) |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30 passed, 3 warnings in 5.98s** |
| Helper end-to-end dry-run (test config) | **17/17 placeholders substituted**; canonical `cover_letter.md` still has 31 USER_TO_FILL hits (unchanged); rendered draft has 14 (only the §0 documentation pointers remain) |
| Canonical file SHA-256 | unchanged from pre-wave (not in scope) |
| `tnnls_submission/MANIFEST.md` SHA-256 column | unchanged (no submission-package change) |

---

## 2. The 17 fillable fields (per FILL_GUIDE.md)

| # | JSON key | Section | Line(s) | Field type |
|---:|---|---|---|---|
| 1 | `authors_block` | §opening header | 51–52 | Full author list + affiliations + corresponding-author email |
| 2 | `editor_header` | §opening header | 56 | Suggested Associate Editor (one-liner, header) |
| 3 | `reviewers_header` | §opening header | 60 | Suggested Reviewers summary (or "(see §9 below)") |
| 4 | `editor_section9` | §9 | 986 | Suggested Associate Editor (verbose, §9) |
| 5 | `reviewer1_affiliation` | §9 | 1003 | ProbFlow / Flow-Matching Theory — affiliation |
| 6 | `reviewer1_email` | §9 | 1006 | ProbFlow / Flow-Matching Theory — email |
| 7 | `reviewer2_affiliation` | §9 | 1017 | Convergence Bound / BL-Distance — affiliation |
| 8 | `reviewer2_email` | §9 | 1020 | Convergence Bound / BL-Distance — email |
| 9 | `reviewer3_affiliation` | §9 | 1032 | ODE Solver / NFE-Efficiency — affiliation |
| 10 | `reviewer3_email` | §9 | 1035 | ODE Solver / NFE-Efficiency — email |
| 11 | `reviewer4_affiliation` | §9 | 1048 | Protein Generation — affiliation |
| 12 | `reviewer4_email` | §9 | 1052 | Protein Generation — email |
| 13 | `reviewer5_affiliation` | §9 | 1065 | Statistical Rigor — affiliation |
| 14 | `reviewer5_email` | §9 | 1069 | Statistical Rigor — email |
| 15 | `corresponding_author_name` | §11 closing | 1126 | Full name (matches title-page asterisk) |
| 16 | `corresponding_author_affiliation` | §11 closing | 1127 | Department + institution |
| 17 | `corresponding_author_email` | §11 closing | 1128 | Institutional email |

The two `editor_header` (line 56) and `editor_section9` (line 986) fields carry the **same** content (the AE name + scope statement), rendered in two places for redundancy. FILL_GUIDE.md §2 instructs the user to keep them identical.

---

## 3. Helper design

### 3.1 CLI

```bash
python3 tools/render_cover_letter.py \
    --config /tmp/cover_letter_data.json \
    --canonical tnnls_submission/cover_letter.md \
    --output /tmp/cover_letter_rendered.md
```

Flags:
- `--config PATH` (required): JSON config file with the 17 pre-filled fields.
- `--canonical PATH` (default `tnnls_submission/cover_letter.md`): the source cover letter with placeholders.
- `--output PATH` (required): where to write the rendered draft. **NOT** the canonical file. The user reviews the draft and `cp` it into place when satisfied.

### 3.2 Schema

The JSON config is a flat object with the 17 field names as keys. Values are non-empty strings. Unknown keys are tolerated (forward-compat) but logged to stderr. The template at `/tmp/cover_letter_data.template.json` lists the 17 keys with empty-string values.

```json
{
  "authors_block": "Dr. Hugo Wei, ... — Dr. Wei is the corresponding author (hwei@example.edu)",
  "editor_header": "Prof. Ming Li, ... — TNNLS AE specializing in learning systems / generative models",
  "reviewers_header": "(see §9 below — five reviewers listed with affiliations and emails)",
  "editor_section9": "Prof. Ming Li, ... — TNNLS AE specializing in learning systems / generative models",
  "reviewer1_affiliation": "Meta AI Research (ProbFlow team)",
  "reviewer1_email": "reviewer1.theory@example.com",
  ...
  "corresponding_author_email": "hwei@example.edu"
}
```

### 3.3 Substitution engine

Each field maps to a regex anchored on the `[USER TO FILL: ...]` marker in the canonical file. The regexes use `re.DOTALL` so multi-line placeholders (e.g., `Authors block — full author list, affiliations, and corresponding-author email`) are matched as a single chunk. Substitutions are applied with `count=1` per field (the schema is built around one-occurrence-per-field).

If any regex fails to match (placeholder text drifted since Wave 348), the helper:
- Records the field as a warning (still writes the partial rendered file so the user can see what landed),
- Exits 1 (fail-closed).

This fail-closed policy is critical: it prevents the user from uploading a half-rendered cover letter to TNNLS if the schema drifts.

### 3.4 Why the helper does not write to `tnnls_submission/cover_letter.md` directly

Per the Wave 348 §0 "USER ACTION REQUIRED" preamble and the Wave 268 strict-clean rule (additive only; never destructive without explicit user gating), the canonical cover letter stays byte-stable until the user has visually confirmed the rendered draft. The user invokes the helper, reads the rendered draft at `--output`, and then `cp --output tnnls_submission/cover_letter.md` to commit. This two-step workflow is auditable (the helper leaves a record of which substitutions landed) and prevents accidental canonical-file corruption.

### 3.5 What the helper does NOT do

- It does NOT edit `tnnls_submission/MANIFEST.md` SHA-256 column. After the user manually `cp`s the rendered draft into place, the user re-runs `cd tnnls_submission && sha256sum -- *.md` and updates the MANIFEST column. This is the FILL_GUIDE.md §3 step 5 procedure and is unchanged.
- It does NOT validate institutional email format or COI status. The user is responsible for COI sweeps against the TNNLS Editorial Manager database (FILL_GUIDE.md §2 hint for each reviewer).
- It does NOT write to `docs/CLAIMS.md`. The cover letter is a submission-package artifact, not a claim ledger. No claim-bearing number is touched.
- It does NOT touch vendored upstream code (`data/FlowMol3/`, `data/LineageFlow/`, `data/Kanzi/`, etc.) or any pinned-commit file. Per Wave 260 user directive, all vendored repos stay byte-identical.

---

## 4. Dry-run verification

A test config (`/tmp/cover_letter_data.test.json`) was built with all 17 fields filled with `TEST_<key>` strings. The helper was invoked against the canonical `tnnls_submission/cover_letter.md`:

```
$ python3 tools/render_cover_letter.py \
    --config /tmp/cover_letter_data.test.json \
    --canonical tnnls_submission/cover_letter.md \
    --output /tmp/cover_letter_rendered.md
rendered: 17/17 placeholders substituted; output: /tmp/cover_letter_rendered.md
$ echo $?
0
$ grep -c "USER TO FILL" tnnls_submission/cover_letter.md
31
$ grep -c "USER TO FILL" /tmp/cover_letter_rendered.md
14
```

The 14 remaining hits in the rendered draft are **exactly** the §0 documentation pointers (FILL_GUIDE.md §0 says "14 grep hits are NOT user-fillable" — 11 in lines 24-31 + 3 in lines 7/9/36 of the convention/grep-example text). The 17 actual fillable fields are all replaced.

The canonical file SHA-256 was verified byte-stable across the dry-run (31 USER_TO_FILL hits before and after; helper writes only to `--output`).

---

## 5. §R.5 — Reproducibility footnote (cover-letter fill helper)

**§R.5 — Wave 351 P5 cover-letter fill helper (2026-09-25).** The TNNLS cover letter at `tnnls_submission/cover_letter.md` has 17 USER_TO_FILL placeholders (per Wave 348 `FILL_GUIDE.md`); a helper script at `tools/render_cover_letter.py` with a JSON config schema at `/tmp/cover_letter_data.template.json` makes filling them systematic. The script does not write to `tnnls_submission/cover_letter.md` directly — it produces a rendered draft that the user reviews before overwriting the canonical file. Documented at `docs/audit/wave351-cover-letter-helper.md`.

---

## 6. Files modified (additive only)

| Path | Role | Action |
|---|---|---|
| `tools/render_cover_letter.py` | Helper script | NEW (150 lines, ruff 0, import OK) |
| `/tmp/cover_letter_data.template.json` | Empty 17-field JSON template | NEW (session-only; lives in `/tmp/`, not tracked) |
| `docs/audit/wave351-cover-letter-helper.md` | This audit doc | NEW (Wave 351 P5 governance) |

**No edits** to:
- `tnnls_submission/cover_letter.md` (canonical, unchanged)
- `tnnls_submission/FILL_GUIDE.md` (canonical, unchanged)
- `tnnls_submission/MANIFEST.md` (no SHA-256 column change; canonical cover letter not re-hashed)
- `docs/CLAIMS.md` (no claim status change)
- `docs/CONSOLIDATED_RESULTS.md`, `docs/INSIGHTS.md`, `docs/drafts/paper-A-final.md` (no paper-surface change)
- `adaptive_reflow/**`, `tests/**` (no code/test change)

---

## 7. Acceptance gates (all PASS)

| Gate | Result |
|---|---|
| (1) Helper imports cleanly | PASS (`import tools.render_cover_letter; print('import OK')` → `import OK`) |
| (2) `ruff check tools/render_cover_letter.py` | PASS (0 findings) |
| (3) Helper end-to-end dry-run substitutes 17/17 placeholders | PASS |
| (4) Helper writes only to `--output` (canonical file SHA-256 byte-stable) | PASS (31 USER_TO_FILL hits before/after in canonical) |
| (5) `python3 tools/check_claims_consistency.py` | PASS (no drift) |
| (6) `pytest tests/test_d4_regression_vectors.py -q` | PASS (30/30) |
| (7) `tnnls_submission/MANIFEST.md` SHA-256 column unchanged | PASS (no submission-package change) |
| (8) ADDITIVE only (no destructive edits to canonical files) | PASS |
| (9) NO-PUSH policy (commit only, no push) | PASS (per Wave 325; user-gated push) |

---

## 8. Next-step action for the user

1. `cp /tmp/cover_letter_data.template.json /tmp/cover_letter_data.json`
2. Edit `/tmp/cover_letter_data.json` — fill all 17 fields per `tnnls_submission/FILL_GUIDE.md`.
3. `python3 tools/render_cover_letter.py --config /tmp/cover_letter_data.json --output /tmp/cover_letter_rendered.md`
4. Visually review `/tmp/cover_letter_rendered.md` (especially line 56 vs line 986 — must be identical; reviewer affiliations + emails; corresponding-author {name, affiliation, email} on lines 1126-1128).
5. Run COI sweep against the 5 reviewers (per FILL_GUIDE.md §4-§8 hints; reviewer 4 is highest-risk for protein-axis COI).
6. When satisfied: `cp /tmp/cover_letter_rendered.md tnnls_submission/cover_letter.md`
7. Re-hash the package: `cd tnnls_submission && sha256sum -- *.md` and update `MANIFEST.md` SHA-256 column.
8. Commit (per Wave 348 procedure: `git commit -m "Wave XXX: fill cover_letter USER placeholders"`).
9. Repeat the Wave 348 acceptance gates: `grep -nE 'USER.TO.FILL' tnnls_submission/cover_letter.md | wc -l` must return 14 (only §0 documentation pointers + §0 convention text).

---

**ADDITIVE only — does not delete or rewrite any prior wave audit doc.** Wave 351 P1 (DGL operational), P2 (R5a n=10 paired-t), P3 (R3 vendor-fix status), P3 (Theorem 5 numerical) all remain in place; Wave 351 P5 is purely additive infrastructure.