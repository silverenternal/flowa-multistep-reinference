# Contributing — Filling the TNNLS Cover Letter

A 3-step guide for filling the 17 USER_TO_FILL placeholders in
`tnnls_submission/cover_letter.md` before submitting to the TNNLS Editorial
Manager.

The interactive helper was added in **Wave 352 P2** as an extension to the
Wave 351 P5 `tools/render_cover_letter.py` baseline. It walks you through
each field with a sensible default suggestion, lets you press **Enter to
accept** the default or **type any value to override**, then writes a
rendered draft you can review before overwriting the canonical file.

The canonical `tnnls_submission/cover_letter.md` is **never modified
directly by the helper** — the rendered draft is written to
`/tmp/cover_letter_filled.md` and you `cp` it into place after visual
review. This is the Wave 268 strict-clean rule (additive only; never
destructive without explicit user gating).

---

## Quickstart — 3 steps

### Step 1 — Run the helper in interactive mode

```bash
python3 tools/render_cover_letter.py --interactive
```

You will be prompted for the 17 fields in order. The helper shows the
section + line number for each prompt:

```
--- line 51-52 (§opening header) ---
[?] Authors block (one author per line: ...) [Hugo Huang, MIT CSAIL, ...]: _
--- line 56-58 (§opening header) ---
[?] Suggested Associate Editor — HEADER [Prof. Ming Li, ...]: _
...
--- line 1128 (§11 closing) ---
[?] Corresponding author email (institutional, NOT personal) [hugo@example.com]: _
```

- **Press Enter** to accept the `[default]` suggestion.
- **Type any value** to override the default.
- Pre-filled values in `/tmp/cover_letter_data.template.json` (if any)
  become the new default on re-runs.

### Step 2 — Review the rendered draft

The helper writes:

| Output | Path | Purpose |
|---|---|---|
| Rendered cover letter draft | `/tmp/cover_letter_filled.md` | Visual review before overwriting canonical |
| Collected JSON config | `/tmp/cover_letter_data.filled.json` | Re-use for `--config` runs after edits |

Open `/tmp/cover_letter_filled.md` and check the four high-risk fields:

1. **Line 56 (header) vs. line 986 (§9)** — the AE name must be
   identical in both places.
2. **Reviewer 4 (line 1048/1052)** — the protein-generation reviewer has
   the highest COI risk (Lipman / ESM-IF / LineageFlow / Kanzi author
   overlap). Confirm with the COI sweep before submission.
3. **Corresponding-author {name, affiliation, email}** on lines 1126-1128
   — must match the manuscript title-page asterisk.
4. **Institutional emails only** — no Gmail / Outlook / QQ mail.

When satisfied:

```bash
# Apply the draft to the canonical file
cp /tmp/cover_letter_filled.md tnnls_submission/cover_letter.md

# Re-hash the submission package (per FILL_GUIDE.md step 6)
cd tnnls_submission && sha256sum -- *.md
cd -

# Update MANIFEST.md SHA-256 column for cover_letter.md
# (manual edit per FILL_GUIDE.md step 7)
```

### Step 3 — Commit + verify

```bash
# Confirm the 17 actual fillable fields are all replaced
grep -nE 'USER.TO.FILL' tnnls_submission/cover_letter.md | wc -l
# Expected: 14 (the §0 documentation pointers + §0 convention text;
# the 17 actual fillable fields should now show plain prose).

# Stage and commit (NO PUSH per Wave 325)
git add tnnls_submission/cover_letter.md tnnls_submission/MANIFEST.md
git commit -m "Wave <NN>: fill cover_letter USER placeholders (17/17 replaced)"
```

---

## Field reference (the 17 prompts)

The 17 fields come from `tnnls_submission/FILL_GUIDE.md`. The interactive
helper prompts them in canonical order (header → §9 → §11):

| # | JSON key | Section | Line(s) | Default in interactive mode |
|---:|---|---|---|---|
| 1 | `authors_block` | §opening header | 51–52 | Hugo Huang, MIT CSAIL (corresponding-author email hugo@example.com) |
| 2 | `editor_header` | §opening header | 56 | Prof. Ming Li, Department of ECE, University of Example, mli@example.edu |
| 3 | `reviewers_header` | §opening header | 60 | `(see §9 below — five reviewers listed with affiliations and emails)` |
| 4 | `editor_section9` | §9 | 986 | Ming Li, Department of ECE, University of Example, mli@example.edu (line template prepends "Prof.") |
| 5 | `reviewer1_affiliation` | §9 | 1003 | Meta AI Research (ProbFlow team) |
| 6 | `reviewer1_email` | §9 | 1006 | reviewer1.theory@example.com |
| 7 | `reviewer2_affiliation` | §9 | 1017 | Université Gustave Eiffel / LIGM (Vialard group) |
| 8 | `reviewer2_email` | §9 | 1020 | reviewer2.convergence@univ-eiffel.fr |
| 9 | `reviewer3_affiliation` | §9 | 1032 | Stanford University (Lu DPM-Solver group) |
| 10 | `reviewer3_email` | §9 | 1035 | reviewer3.solver@stanford.edu |
| 11 | `reviewer4_affiliation` | §9 | 1048 | Meta AI (ESM-IF / EvolutionaryScale LineageFlow) |
| 12 | `reviewer4_email` | §9 | 1052 | reviewer4.protein@meta.com |
| 13 | `reviewer5_affiliation` | §9 | 1065 | Department of Statistics, University of Example |
| 14 | `reviewer5_email` | §9 | 1069 | reviewer5.stats@example.edu |
| 15 | `corresponding_author_name` | §11 closing | 1126 | Hugo Huang |
| 16 | `corresponding_author_affiliation` | §11 closing | 1127 | MIT CSAIL, 32 Vassar St, Cambridge, MA, USA |
| 17 | `corresponding_author_email` | §11 closing | 1128 | hugo@example.com |

The defaults are **illustrative only** — most users will override at
least the corresponding-author email and the 5 reviewer emails.

---

## Pre-fill from a saved JSON config (optional)

If you started filling and want to resume, or if a colleague has shared a
JSON config, use `--template <path>`:

```bash
# Re-render from a prior run (the helper will use the saved values as
# the new prompt defaults; press Enter to keep them, type to edit)
python3 tools/render_cover_letter.py \
    --interactive \
    --template /tmp/cover_letter_data.filled.json \
    --output /tmp/cover_letter_filled.md \
    --save-config /tmp/cover_letter_data.filled.json
```

For **non-interactive / CI use**, skip the prompts entirely:

```bash
python3 tools/render_cover_letter.py \
    --config /tmp/cover_letter_data.filled.json \
    --output /tmp/cover_letter_filled.md
```

The `--config` path is the Wave 351 P5 baseline (no TTY required). The
`--interactive` mode (Wave 352 P2) is a superset that adds the prompt
layer on top.

---

## When the helper reports a warning

The helper fails closed if any of the 17 regex patterns fail to match in
the canonical file (placeholder text drifted). If you see:

```
warnings:
  - placeholder not found: editor_header (line 56-58 (§opening header))
```

…then either:

1. Someone edited `tnnls_submission/cover_letter.md` and changed the
   `[USER TO FILL: ...]` text — re-read `tnnls_submission/FILL_GUIDE.md`
   and re-align the regex patterns in `tools/render_cover_letter.py`.
2. The canonical file has line endings or whitespace that diverges from
   what the helper expects.

The canonical file is **byte-stable** per Wave 348. Any drift means an
unintended edit was made; restore from `git` and try again.

---

## What the helper does NOT do (per Wave 268 strict-clean)

- It does NOT write to `tnnls_submission/cover_letter.md` directly.
  The user reviews the rendered draft at `/tmp/cover_letter_filled.md`
  and `cp`s it into place.
- It does NOT validate institutional email format or COI status. The
  user is responsible for COI sweeps against the TNNLS Editorial
  Manager database (per `FILL_GUIDE.md` §4-§8 hints, especially
  Reviewer 4 for protein-axis COI).
- It does NOT update `tnnls_submission/MANIFEST.md` SHA-256 column. The
  user re-runs `cd tnnls_submission && sha256sum -- *.md` and updates
  the MANIFEST column manually (per FILL_GUIDE.md step 6).
- It does NOT touch `docs/CLAIMS.md`. The cover letter is a
  submission-package artifact, not a claim ledger.
- It does NOT touch vendored upstream code (`data/FlowMol3/`,
  `data/LineageFlow/`, `data/Kanzi/`, etc.) or any pinned-commit file.
  Per Wave 260 user directive, all vendored repos stay byte-identical.
- It does NOT push to remote (NO-PUSH policy per Wave 325; user-gated
  push).

---

## Acceptance gates (Wave 352 P2 — all PASS)

| Gate | Result |
|---|---|
| `python3 -c "import tools.render_cover_letter; print('import OK')"` | PASS |
| `python3 tools/render_cover_letter.py --help` shows `--interactive` | PASS |
| `ruff check tools/render_cover_letter.py` | PASS (0 findings) |
| Interactive end-to-end (PTY + 17 Enters) substitutes 17/17 placeholders | PASS |
| Rendered draft contains correct content (line 56 / 986 / 1126-1128) | PASS |
| Canonical file SHA-256 unchanged after run | PASS |
| `python3 tools/check_claims_consistency.py` | PASS (no drift) |
| Round-trip (`--interactive` → JSON → `--config` → byte-identical render) | PASS |

The full audit trail is at
[`docs/audit/wave352-cover-letter-interactive.md`](./audit/wave352-cover-letter-interactive.md).

---

_Last updated: 2026-09-25 (Wave 352 P2)._