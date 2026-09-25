# Wave 352 P2 — Cover letter `--interactive` mode (stdin prompts + default suggestions)

**Date:** 2026-09-25
**Author:** Wave 352 P2 (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — additive infrastructure extension; no number / no claim change; canonical `tnnls_submission/cover_letter.md` byte-stable until user explicitly overwrites.
**Trigger:** User request relayed through workflow harness: "还有哪些gap你就启动ultracode去补一下" — gap-fill the Wave 351 P5 cover-letter helper with an interactive stdin-driven fill mode so the 17 USER_TO_FILL placeholders can be filled with minimal friction.
**Scope:** New `--interactive` mode in `tools/render_cover_letter.py` (extension of Wave 351 P5 baseline), `INTERACTIVE_DEFAULTS` + `FIELD_PROMPTS` dicts, `_interactive_prompt_one` + `_interactive_collect` helpers, new `docs/CONTRIBUTING-cover-letter.md` 3-step quickstart, this audit doc. **No edits to `tnnls_submission/cover_letter.md`, `tnnls_submission/FILL_GUIDE.md`, `tnnls_submission/MANIFEST.md`, `docs/CLAIMS.md`, or `docs/drafts/paper-A-final.md`.**
**Hard-rule compliance:** ADDITIVE ONLY (no destructive edits); per Wave 268 strict-clean rule, per Wave 325 NO-PUSH policy, per `flowa-paper-evidence` skill (helper owns only `tools/` and `docs/`).

---

## 1. Executive Summary

The Wave 351 P5 cover-letter helper (`tools/render_cover_letter.py`) required the user to **manually edit a JSON config file** (`/tmp/cover_letter_data.json`) with 17 fields and then invoke `--config <path>`. This was workable but required the user to know the JSON schema and to type all 17 values by hand. Wave 352 P2 closes this gap with an **`--interactive` mode** that walks the user through the 17 fields via stdin prompts, showing a sensible default suggestion (e.g., `Hugo Huang, MIT CSAIL, hugo@example.com`) that the user can accept by pressing **Enter** or override by **typing any value**.

The interactive mode:

1. Reads `/tmp/cover_letter_data.template.json` as the schema + any pre-filled values.
2. Prompts the user for each empty field with the appropriate default.
3. Saves the collected JSON config to `/tmp/cover_letter_data.filled.json` for re-runs.
4. Renders the cover letter draft to `/tmp/cover_letter_filled.md` (NOT the canonical file).
5. Prints the diff summary: "Replaced 17 USER_TO_FILL placeholders; render saved to /tmp/cover_letter_filled.md. To apply: cp /tmp/cover_letter_filled.md tnnls_submission/cover_letter.md".

| Artifact | Role | Notes |
|---|---|---|
| `tools/render_cover_letter.py` | Extended with `--interactive` mode (and `--template`, `--save-config` flags) | Wave 352 P2 helper; `--config` path unchanged (Wave 351 P5 baseline) |
| `docs/CONTRIBUTING-cover-letter.md` | 3-step quickstart for filling the cover letter | New contributor-facing doc |
| This audit doc | Documents the helper extension, the schema, and the §R.5 reproducibility footnote | Wave 352 P2 governance doc |

| Acceptance gate | Result |
|---|---|
| `python3 -c "import tools.render_cover_letter; print('import OK')"` | **import OK** |
| `python3 tools/render_cover_letter.py --help` shows `--interactive` | **PASS** |
| `ruff check tools/render_cover_letter.py` | **All checks passed!** |
| `python3 tools/check_claims_consistency.py` | **No drift detected.** |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30 passed** (byte-stable regression preserved) |
| Interactive end-to-end (PTY + 17 inputs) substitutes 17/17 placeholders | **PASS** (14 USER_TO_FILL hits in rendered file = §0 docs only) |
| Canonical `tnnls_submission/cover_letter.md` SHA-256 byte-stable | **PASS** (unchanged: `a6976825...`) |
| Round-trip `--interactive` → JSON → `--config` → byte-identical render | **PASS** (SHA256 `d5aa2279f20626bf...` matches) |
| Rendered draft line 56 (header) vs line 986 (§9) AE consistency | **PASS** (Prof. Ming Li in both places, no duplication) |
| Rendered draft line 1126-1128 (corresponding author) | **PASS** (Hugo Huang, MIT CSAIL, hugo@example.com) |

---

## 2. The 17 prompts (per FILL_GUIDE.md + INTERACTIVE_DEFAULTS)

The interactive mode walks the 17 fields in canonical order (header → §9 → §11). Each prompt shows the section + line number so the user knows where the content will land.

| # | JSON key | Section | Line(s) | Default in `INTERACTIVE_DEFAULTS` |
|---:|---|---|---|---|
| 1 | `authors_block` | §opening header | 51–52 | Hugo Huang, MIT CSAIL, 32 Vassar St, Cambridge, MA, USA, hugo@example.com + corresponding-author line |
| 2 | `editor_header` | §opening header | 56 | Prof. Ming Li, Department of ECE, University of Example, mli@example.edu |
| 3 | `reviewers_header` | §opening header | 60 | (see §9 below — five reviewers listed with affiliations and emails) |
| 4 | `editor_section9` | §9 | 986 | Ming Li, Department of ECE, University of Example, mli@example.edu (line template prepends "Prof.") |
| 5 | `reviewer1_affiliation` | §9 | 1003 | Meta AI Research (ProbFlow team) — to be confirmed at submission |
| 6 | `reviewer1_email` | §9 | 1006 | reviewer1.theory@example.com |
| 7 | `reviewer2_affiliation` | §9 | 1017 | Université Gustave Eiffel / LIGM (Vialard group) — to be confirmed at submission |
| 8 | `reviewer2_email` | §9 | 1020 | reviewer2.convergence@univ-eiffel.fr |
| 9 | `reviewer3_affiliation` | §9 | 1032 | Stanford University (Lu DPM-Solver group) — to be confirmed at submission |
| 10 | `reviewer3_email` | §9 | 1035 | reviewer3.solver@stanford.edu |
| 11 | `reviewer4_affiliation` | §9 | 1048 | Meta AI (ESM-IF / EvolutionaryScale LineageFlow) — to be confirmed at submission |
| 12 | `reviewer4_email` | §9 | 1052 | reviewer4.protein@meta.com |
| 13 | `reviewer5_affiliation` | §9 | 1065 | Department of Statistics, University of Example (computational-statistics focus) — to be confirmed at submission |
| 14 | `reviewer5_email` | §9 | 1069 | reviewer5.stats@example.edu |
| 15 | `corresponding_author_name` | §11 closing | 1126 | Hugo Huang |
| 16 | `corresponding_author_affiliation` | §11 closing | 1127 | MIT CSAIL, 32 Vassar St, Cambridge, MA, USA |
| 17 | `corresponding_author_email` | §11 closing | 1128 | hugo@example.com |

The defaults are **illustrative only** — they are reasonable exemplars taken from the FILL_GUIDE.md `EXAMPLE_OR_HINT` lines. Most users will override at least the corresponding-author email and the 5 reviewer emails.

The `editor_header` and `editor_section9` defaults are intentionally **different** to avoid duplication: line 56 has no `Prof.` prefix in the template (the user types `Prof. Ming Li, ...`), while line 986 has `Prof. ` as a hardcoded prefix (the user types just `Ming Li, ...`). With these defaults, both rendered lines show `Prof. Ming Li, Department of ECE, University of Example, mli@example.edu` — consistent without duplication.

---

## 3. Helper design (additive to Wave 351 P5 baseline)

### 3.1 CLI — `--interactive` mode

```bash
python3 tools/render_cover_letter.py \
    --interactive \
    --canonical tnnls_submission/cover_letter.md \
    --output /tmp/cover_letter_filled.md \
    --save-config /tmp/cover_letter_data.filled.json \
    --template /tmp/cover_letter_data.template.json
```

Flags (new in Wave 352 P2):
- `--interactive` (mutually exclusive with `--config`): walks the 17 fields via stdin prompts.
- `--template PATH` (default `/tmp/cover_letter_data.template.json`): pre-fill from this JSON template (any non-empty value becomes the new default on re-runs).
- `--save-config PATH` (default `/tmp/cover_letter_data.filled.json`): where to write the collected JSON config (for re-runs via `--config <path>`).

The `--config` flag (Wave 351 P5 baseline) is preserved and is the recommended mode for non-TTY contexts (CI, scripts, batch fills).

### 3.2 Interactive prompt flow

For each of the 17 fields, the helper:

1. Prints the section label: `--- line 51-52 (§opening header) ---`
2. Prints the prompt + default suggestion: `[?] Authors block (...) [Hugo Huang, MIT CSAIL, ...]: `
3. Reads one line from stdin.
5. **Empty line (just Enter)** → accept the default.
6. **Non-empty line** → use the user input as the override.
7. **EOF (Ctrl-D)** → accept the default (graceful termination).

If the JSON template at `--template` has a non-empty value for the field, that value becomes the new default (so re-runs surface the prior answer rather than the static `INTERACTIVE_DEFAULTS[key]`).

### 3.3 Why a TTY is required

The interactive mode calls `sys.stdin.isatty()` to detect whether the user is at a terminal. If not, it exits 2 with a clear error message:

```
ERROR: --interactive requires a TTY (stdin must be a terminal).
For non-interactive use, write a JSON config and use --config.
See docs/CONTRIBUTING-cover-letter.md for the 3-step guide.
```

This fail-closed policy prevents the helper from silently reading garbage from a piped input or from `/dev/null`. For batch fills, the user uses `--config <path>` with a JSON file.

### 3.4 Substitution engine (unchanged from Wave 351 P5)

The substitution engine — `FIELDS` regexes + `render()` function + `REQUIRED_FIELDS` assertion — is **byte-identical to Wave 351 P5**. The interactive mode is purely a UX layer above the same substitution engine. This means:

- The 17 field regexes still match `[USER TO FILL: ...]` placeholders.
- The fail-closed policy (exit 1 on any unmatched placeholder) still applies.
- The schema-drift detection (warnings → exit 1) is unchanged.

### 3.5 Why the helper does not write to `tnnls_submission/cover_letter.md` directly

Per Wave 348 §0 "USER ACTION REQUIRED" preamble and the Wave 268 strict-clean rule (additive only; never destructive without explicit user gating), the canonical cover letter stays byte-stable until the user has visually confirmed the rendered draft. The user invokes the helper in `--interactive` mode, answers the 17 prompts, reads the rendered draft at `/tmp/cover_letter_filled.md`, and then `cp /tmp/cover_letter_filled.md tnnls_submission/cover_letter.md` to commit. This two-step workflow is auditable and prevents accidental canonical-file corruption.

### 3.6 What the helper does NOT do

- It does NOT edit `tnnls_submission/MANIFEST.md` SHA-256 column.
- It does NOT validate institutional email format or COI status.
- It does NOT write to `docs/CLAIMS.md`.
- It does NOT touch vendored upstream code or any pinned-commit file.
- It does NOT push to remote (NO-PUSH policy per Wave 325).

---

## 4. End-to-end verification

### 4.1 PTY simulation

A PTY was used to simulate a TTY (so `sys.stdin.isatty()` returns True) and the test fed 17 inputs (1 multi-line override for `authors_block` + 16 Enters to accept defaults):

```
$ python3 /tmp/test_w352p2.py
Exit code: 0
Rendered draft USER_TO_FILL count: 14 (expect 14)
Saved JSON keys: 17 (expect 17)
authors_block (overridden): 'Hugo Huang, MIT CSAIL, hugo@example.com\nCorresponding author: Hugo Huang (hugo@example.com)'
corresponding_author_email (default accepted): 'hugo@example.com'
Canonical USER_TO_FILL count (unchanged): 31 (expect 31)
Round-trip exit code: 0
Interactive output SHA256: d5aa2279f20626bf
Config output SHA256:      d5aa2279f20626bf
Match: True
```

The 14 remaining `USER TO FILL` hits in the rendered draft are **exactly** the §0 documentation pointers (FILL_GUIDE.md §0 says "14 grep hits are NOT user-fillable" — 11 in lines 24-31 + 3 in lines 7/9/36 of the convention/grep-example text). The 17 actual fillable fields are all replaced.

### 4.2 Round-trip via `--config`

The saved JSON config at `/tmp/w352p2_interactive_save.json` was re-invoked via `--config <path>` and produced a byte-identical render (SHA256 `d5aa2279f20626bf...` matches). This proves the interactive mode's collected JSON is wire-compatible with the Wave 351 P5 `--config` baseline.

### 4.3 Canonical byte-stability

The canonical `tnnls_submission/cover_letter.md` SHA-256 was verified **unchanged** across the end-to-end run: `a6976825d19276c4fbb98efb167cadac24ed94cc4013796e0961580ca3ebf6f1` (matches the pre-wave hash). The helper writes only to `--output` and `--save-config` (both under `/tmp/`).

### 4.4 Line 56 vs line 986 AE consistency

The two AE placeholders (`editor_header` on line 56 and `editor_section9` on line 986) were verified to render identically in the draft:

- Line 56: `**Suggested Associate Editor:** \`Prof. Ming Li, Department of ECE, University of Example, mli@example.edu\` (see §9 below)`
- Line 986: `- Prof. \`Ming Li, Department of ECE, University of Example, mli@example.edu\` (TNNLS AE specializing in learning systems /`

Both render with `Prof. Ming Li, Department of ECE, University of Example, mli@example.edu` — the "Prof." comes from line 986's hardcoded template prefix, and the rest comes from the substituted value. **No duplication.** FILL_GUIDE.md §2 hint ("keep them consistent") is satisfied.

### 4.5 Line 1126-1128 corresponding author

The three corresponding-author placeholders were verified to render correctly in the closing signature:

```
Sincerely,

`Hugo Huang`
`MIT CSAIL, 32 Vassar St, Cambridge, MA, USA`
`hugo@example.com`
2026-09-21
```

---

## 5. Documentation: `docs/CONTRIBUTING-cover-letter.md`

A new contributor-facing doc was added at `docs/CONTRIBUTING-cover-letter.md` with:

1. **3-step quickstart** — run `--interactive`, review `/tmp/cover_letter_filled.md`, `cp` into place.
2. **Field reference table** — the 17 prompts in canonical order with section + line + default.
3. **Pre-fill workflow** — how to use `--template` for re-runs after partial fills.
4. **Non-interactive / CI usage** — the Wave 351 P5 `--config` baseline is preserved.
5. **What the helper does NOT do** — Wave 268 strict-clean + Wave 260 vendored-up + Wave 325 no-push.
6. **Acceptance gates** — all 8 gates listed with PASS verdicts.

The doc is linked from the helper's `--help` output (under the `--interactive` flag description) and is the single source of truth for "how to fill the cover letter" UX.

---

## 6. §R.5 — Reproducibility footnote (cover-letter interactive helper)

**§R.5 — Wave 352 P2 cover-letter interactive helper (2026-09-25).** The Wave 351 P5 `tools/render_cover_letter.py` is extended with a `--interactive` mode that walks the 17 USER_TO_FILL placeholders in `tnnls_submission/cover_letter.md` via stdin prompts with `INTERACTIVE_DEFAULTS` as the default suggestion for each field (Press Enter to accept; type to override). Saves the rendered draft to `--output` (default `/tmp/cover_letter_filled.md`) and the collected JSON to `--save-config` (default `/tmp/cover_letter_data.filled.json`). 3-step quickstart at `docs/CONTRIBUTING-cover-letter.md`. Subset of the Wave 351 P5 substitution engine — no schema or regex changes; the `--config` path remains the non-TTY baseline. Documented at `docs/audit/wave352-cover-letter-interactive.md`.

---

## 7. Files modified (additive only)

| Path | Role | Action |
|---|---|---|
| `tools/render_cover_letter.py` | Cover letter fill helper | EXTENDED (added `--interactive` mode + `INTERACTIVE_DEFAULTS` + `FIELD_PROMPTS` + `_interactive_prompt_one` + `_interactive_collect`; `--config` path unchanged) |
| `docs/CONTRIBUTING-cover-letter.md` | 3-step contributor quickstart | NEW |
| `docs/audit/wave352-cover-letter-interactive.md` | This audit doc | NEW (Wave 352 P2 governance) |

**No edits** to:
- `tnnls_submission/cover_letter.md` (canonical, byte-stable)
- `tnnls_submission/FILL_GUIDE.md` (canonical, byte-stable)
- `tnnls_submission/MANIFEST.md` (no SHA-256 column change; canonical cover letter not re-hashed)
- `docs/CLAIMS.md` (no claim status change)
- `docs/CONSOLIDATED_RESULTS.md`, `docs/INSIGHTS.md`, `docs/drafts/paper-A-final.md` (no paper-surface change)
- `adaptive_reflow/**`, `tests/**` (no code/test change)
- `tools/render_cover_letter.py` core substitution engine (`FIELDS`, `REQUIRED_FIELDS`, `load_config`, `render`) — UNCHANGED

---

## 8. Acceptance gates (all PASS)

| Gate | Result |
|---|---|
| (1) Helper imports cleanly | PASS (`import tools.render_cover_letter; print('import OK')` → `import OK`) |
| (2) `--help` shows `--interactive` flag | PASS |
| (3) `ruff check tools/render_cover_letter.py` | PASS (0 findings) |
| (4) Interactive end-to-end (PTY + 17 inputs) substitutes 17/17 placeholders | PASS (14 USER_TO_FILL hits in rendered file = §0 docs only) |
| (5) Rendered draft line 56 (header) vs line 986 (§9) AE consistency | PASS (`Prof. Ming Li, Department of ECE, University of Example, mli@example.edu` in both) |
| (6) Rendered draft line 1126-1128 (corresponding author) | PASS |
| (7) Helper writes only to `--output` and `--save-config` (canonical file SHA-256 byte-stable) | PASS (`a6976825...` unchanged) |
| (8) Round-trip `--interactive` → JSON → `--config` → byte-identical render | PASS (SHA256 `d5aa2279f20626bf...` matches) |
| (9) `python3 tools/check_claims_consistency.py` | PASS (no drift) |
| (10) `pytest tests/test_d4_regression_vectors.py -q` | PASS (30/30) |
| (11) `tnnls_submission/MANIFEST.md` SHA-256 column unchanged | PASS (no submission-package change) |
| (12) ADDITIVE only (no destructive edits to canonical files) | PASS |
| (13) NO-PUSH policy (commit only, no push) | PASS (per Wave 325; user-gated push) |

---

## 9. Next-step action for the user

1. `python3 tools/render_cover_letter.py --interactive` — answer the 17 prompts.
2. Visually review `/tmp/cover_letter_filled.md` (especially line 56 vs line 986 — must be identical; reviewer affiliations + emails; corresponding-author {name, affiliation, email} on lines 1126-1128).
3. Run COI sweep against the 5 reviewers (per FILL_GUIDE.md §4-§8 hints; reviewer 4 is highest-risk for protein-axis COI).
4. When satisfied: `cp /tmp/cover_letter_filled.md tnnls_submission/cover_letter.md`
5. Re-hash the package: `cd tnnls_submission && sha256sum -- *.md` and update `MANIFEST.md` SHA-256 column.
6. Commit (per Wave 348 procedure: `git commit -m "Wave XXX: fill cover_letter USER placeholders"`).
7. Repeat the Wave 348 acceptance gates: `grep -nE 'USER.TO.FILL' tnnls_submission/cover_letter.md | wc -l` must return 14 (only §0 documentation pointers + §0 convention text).
8. See `docs/CONTRIBUTING-cover-letter.md` for the 3-step quickstart.

---

**ADDITIVE only — does not delete or rewrite any prior wave audit doc.** Wave 351 P5 (cover letter helper baseline) and all prior waves remain in place; Wave 352 P2 is purely additive UX infrastructure.