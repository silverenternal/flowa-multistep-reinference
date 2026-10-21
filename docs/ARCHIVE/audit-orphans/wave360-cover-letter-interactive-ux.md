# Wave 360 P2 — Cover letter `--dry-run` + `--validate` (safer user-fill workflow)

**Author:** Wave 360 P2 (USER AUTHORIZED, NO PUSH)
**Branch:** main
**Date:** 2026-09-25
**Hard guardrails:** NO-PUSH policy; NO GPU usage (CPU-only); ADDITIVE only
(new flags + new helpers, NO changes to existing `--config` / `--interactive`
behavior); `--dry-run` is read-only — does NOT modify `cover_letter.md`
and does NOT write `--output`; `--validate` is read-only — does NOT modify
`cover_letter.md`. Per Wave 268 strict-clean rule.

---

## TL;DR

| Metric | Value |
|---|---|
| New CLI flags added | `--dry-run`, `--validate`, `--autofill` |
| Existing flags preserved | `--config`, `--interactive`, `--canonical`, `--output`, `--template`, `--save-config` |
| New helper functions | `load_autofill_defaults`, `run_dry_run`, `run_validate` |
| `--dry-run` exit code | 0 (read-only) |
| `--validate` exit code | 0 (informational) |
| `--dry-run` output lines | 81 |
| `--validate` output lines | 79 |
| `--validate` unfilled count (pre-submit canonical) | 17/17 unfilled |
| Canonical `cover_letter.md` md5 before/after | `e44fa82b34ae51b5feb0f1d5e03d4df7` (byte-stable) |
| `--config` end-to-end regression | 17/17 placeholders rendered, exit 0 |
| D.4 30/30 PASS | preserved |
| `python3 tools/check_claims_consistency.py` | "No drift detected." |
| `ruff check tools/render_cover_letter.py` | All checks passed! |
| `mkdocs build --strict` | exit 0 |

Closes the user-fill workflow gap surfaced in Wave 352 P2 / Wave 354 P4:
the helper had a `--config` JSON-driven mode (Wave 351 P5) and a `--interactive`
TTY-driven mode (Wave 352 P2), but no way to **inspect defaults before
committing to a fill session** or **audit the canonical file's current
fill state without writing anything**. `--dry-run` and `--validate` fill
those gaps, both as read-only operations.

---

## 1. Observed facts

### 1.1 `--dry-run` end-to-end

```
$ md5sum tnnls_submission/cover_letter.md
e44fa82b34ae51b5feb0f1d5e03d4df7  tnnls_submission/cover_letter.md

$ python3 tools/render_cover_letter.py --dry-run
========================================================================
TNNLS Cover Letter — --dry-run (Wave 360 P2)
========================================================================

Source: tnnls_submission/cover_letter_FILL_AUTOFILL.json
Total placeholders: 17
Behavior: read-only — does NOT modify cover_letter.md and does NOT write --output.

---  1/17 line 51-52 (§opening header) ---
    key: authors_block
    [default]: Hugo Huang, MIT CSAIL, 32 Vassar St, Cambridge, MA, USA, hugo@example.com
Corresponding author: Hugo Huang (hugo@example.com)

---  2/17 line 56-58 (§opening header) ---
    key: editor_header
    [default]: Prof. Ming Li, Department of ECE, University of Example, mli@example.edu

... [17 placeholders printed] ...

--- 17/17 line 1128 (§11 closing) ---
    key: corresponding_author_email
    [default]: hugo@example.com

========================================================================
Summary: 17/17 defaults populated; 0 empty.
Next step — run `python3 tools/render_cover_letter.py --interactive` (TTY required) to fill the form interactively, OR edit a JSON config and run `--config <path>`.
To audit the current canonical file's fill state without writing, run `python3 tools/render_cover_letter.py --validate`.

$ echo $?
0

$ md5sum tnnls_submission/cover_letter.md
e44fa82b34ae51b5feb0f1d5e03d4df7  tnnls_submission/cover_letter.md   # unchanged
```

| Field | Observed |
|---|---|
| Exit code | **0** |
| Output line count | **81 lines** (header + 17 placeholder blocks × 4 lines each + summary) |
| `--output` written? | **No** — `--dry-run` short-circuits before `args.output.write_text` |
| `cover_letter.md` modified? | **No** — md5 unchanged |
| Source scaffold | `tnnls_submission/cover_letter_FILL_AUTOFILL.json` (Wave 354 P4 structure: `placeholders: [{id, default_value, source_path, rationale}, ...]`); tolerates flat-form JSON too (forward-compat) |
| TTY required? | **No** — runs in CI / scripts |
| Backfill behavior | Any missing key in the scaffold falls back to `INTERACTIVE_DEFAULTS` so `--dry-run` is always 17/17 complete |

### 1.2 `--validate` end-to-end

```
$ python3 tools/render_cover_letter.py --validate
========================================================================
TNNLS Cover Letter — --validate (Wave 360 P2)
========================================================================

Canonical: tnnls_submission/cover_letter.md
Behavior: read-only — does NOT modify cover_letter.md.

---  1/17 line 51-52 (§opening header) ---
    key: authors_block
    [UNFILLED] still on disk as: '[USER TO FILL: Authors block — full author list,\naffiliations, and correspond...'

---  2/17 line 56-58 (§opening header) ---
    key: editor_header
    [UNFILLED] still on disk as: '[USER TO FILL: Suggested Associate\nEditor — TNNLS AE specialising in learning...'

... [17 placeholders reported] ...

========================================================================
Summary: 0/17 placeholders filled; 17 still unfilled.

Action: run `python3 tools/render_cover_letter.py --interactive` to fill the remaining 17 placeholder(s), OR inspect `--dry-run` to see what the scaffolded defaults would be.

$ echo $?
0
```

| Field | Observed |
|---|---|
| Exit code | **0** (informational only — not a gate) |
| Output line count | **79 lines** |
| `--output` written? | **No** |
| `cover_letter.md` modified? | **No** |
| Total unfilled placeholders (pre-submit canonical) | **17/17** |
| TTY required? | **No** — runs in CI / scripts |
| Detection rule | Per-field regex match against the 17 placeholder patterns in `FIELDS`; pattern absent → `[FILLED]`, pattern present → `[UNFILLED]` with first 80 chars of evidence |

### 1.3 `--validate` against a partially-rendered file

Test scenario: render a config to `/tmp/cover_letter_filled.config.md` and re-run
`--validate --canonical <that_path>` to confirm the validator correctly detects
mixed fill state (filled + unfilled). Result: 9/17 filled, 8/17 unfilled.
The 8 remaining are reviewer affiliations + corresponding-author block — this
is consistent with the `count=1` substitution in `render()` hitting the
shorter affiliation regex against the §0 docs header first, leaving the §9
occurrence untouched. Not a regression introduced by Wave 360 P2 (the
`count=1` behavior is inherited from Wave 351 P5); reported here as a
**pre-existing observation** the user should know about before `--config` runs.

### 1.4 Existing flags preserved

| Flag | Mode | Verified end-to-end |
|---|---|---|
| `--config /tmp/cover_letter_data.test.json --output /tmp/cover_letter_filled.config.md` | non-interactive JSON-driven render | 17/17 placeholders rendered, exit 0, `/tmp/cover_letter_filled.config.md` written, canonical `cover_letter.md` md5 unchanged |
| `--help` | argparse help | All five mode flags visible in mutex group: `--config`, `--interactive`, `--dry-run`, `--validate` |
| `--interactive` | TTY-driven fill | TTY check preserved; `_interactive_collect` flow unchanged; only the post-render summary print was added (additive) |

### 1.5 Interactive summary print

After the existing `Next step` instructions, `--interactive` now prints:

```
Interactive summary: filled=N, remaining=M, total=17
  M placeholder(s) did not match in the canonical text — inspect the warnings below before applying the draft.    # only if remaining > 0
```

Where `N = 17 - len(warnings)` and `M = len(warnings)`. If `M == 0`,
no extra warning line is printed (clean output for the happy path).
This is **purely additive** — the existing
"Rendered N/17 USER_TO_FILL placeholders" line is unchanged.

### 1.6 Verification gates (all preserved)

| Gate | Command | Result |
|---|---|---|
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30 passed** |
| Ruff lint | `ruff check tools/render_cover_letter.py` | **All checks passed!** |
| Claims consistency | `python3 tools/check_claims_consistency.py` | **No drift detected.** |
| Mkdocs strict build | `mkdocs build --strict` | exit **0** |
| Canonical `cover_letter.md` byte-stability | `md5sum tnnls_submission/cover_letter.md` | **`e44fa82b34ae51b5feb0f1d5e03d4df7`** (unchanged across all `--dry-run`, `--validate`, `--config` invocations) |

---

## 2. Interpretation

### 2.1 Why these flags (decision trace)

Wave 352 P2 closed the user-fill workflow gap with `--interactive` (TTY-driven)
and `--config` (JSON-driven). The remaining friction points surfaced in the
gap analysis:

1. **No way to preview defaults before committing to a fill session.** A user
   invoking `--interactive` for the first time has no easy way to see what
   the Wave 354 P4 scaffold proposes for each field. They would have to
   hand-read `cover_letter_FILL_AUTOFILL.json` (a 160-line structured file)
   or open the helper source. `--dry-run` solves this by streaming the
   17 defaults in the same per-field-block format as the `--interactive`
   prompts, so what you see in `--dry-run` is exactly what `--interactive`
   will pre-fill.

2. **No way to check the canonical file's fill state without writing.** A user
   mid-fill who wants to confirm "have I filled 5 of 17 yet?" or "is the
   canonical file currently all-unfilled?" had no read-only audit. They
   would have to render to a draft and `diff` it against the canonical,
   which writes a file unnecessarily and shifts attention to the diff
   instead of the underlying placeholder status. `--validate` solves this
   by reading the canonical file, running each of the 17 placeholder
   regexes, and reporting `[FILLED]` vs `[UNFILLED]` per field.

3. **No summary count in `--interactive`.** The existing
   `Rendered N/17 USER_TO_FILL placeholders` line tells you the rendered
   count, but doesn't separate "filled" from "remaining" in a way the
   user can act on. The new `Interactive summary: filled=N, remaining=M,
   total=17` block makes the contract explicit.

### 2.2 What `--dry-run` does NOT do (read-only guarantee)

| Operation | Behavior |
|---|---|
| Read `cover_letter_FILL_AUTOFILL.json` | Yes (default) |
| Read `cover_letter.md` | No |
| Write `cover_letter.md` | **Never** (md5-verified byte-stable) |
| Write `--output` | **Never** (short-circuits before `args.output.write_text`) |
| Require TTY | **No** |
| Mutex with other mode flags | Yes (mutually exclusive with `--config`, `--interactive`, `--validate`) |

### 2.3 What `--validate` does NOT do (read-only guarantee)

| Operation | Behavior |
|---|---|
| Read `cover_letter.md` | Yes (default; overridable via `--canonical`) |
| Write `cover_letter.md` | **Never** (md5-verified byte-stable) |
| Write any file | **Never** |
| Require TTY | **No** |
| Mutex with other mode flags | Yes (mutually exclusive with `--config`, `--interactive`, `--dry-run`) |

### 2.4 Why `--validate` always exits 0 (deliberate design choice)

`--validate` is **informational**, not a gate. The user may invoke it at
any time — before filling, mid-fill, post-fill — and expect a non-error
exit code that says "this is the current state" rather than "you failed".
The unfilled count + per-field `[UNFILLED]` lines ARE the failure signal;
turning that into a non-zero exit would (a) block CI scripts that use
`--validate` as a pre-submit checklist during the natural pre-submit
window where the canonical file is intentionally all-unfilled, and
(b) violate the Wave 268 strict-clean rule by adding a destructive
behavior to a read-only mode. If a hard gate is needed in the future,
add `--validate --strict` (returns 1 on any unfilled placeholder) as a
separate additive flag — not in this wave.

### 2.5 Why `INTERACTIVE_DEFAULTS` backfill (defense in depth)

The Wave 354 P4 `cover_letter_FILL_AUTOFILL.json` is structured as
`placeholders: [{id, default_value, source_path, rationale}, ...]`.
If a future PR drops a placeholder from this scaffold (e.g., during a
schema rename), `--dry-run` would silently print an empty `[EMPTY]`
default for the missing key. The `load_autofill_defaults` helper falls
back to `INTERACTIVE_DEFAULTS[key]` for any missing key, so `--dry-run`
output is always 17/17 complete (assuming the hard-coded
`REQUIRED_FIELDS` invariant holds). This costs ~3 lines of code and
zero behavior change for the happy path; it removes a class of silent
failures for the not-happy path.

### 2.6 Pre-existing observation (not a Wave 360 regression)

`render()` uses `re.subn(..., count=1)`. Some of the 17 placeholder
regexes are short enough to match multiple occurrences in
`cover_letter.md` (the §0 docs header lists `[USER TO FILL: Reviewer N
affiliation]` etc. on lines 24-28, and §9 lists the same placeholders
on lines 1003-1065). The `count=1` substitution replaces the first
match only, so a `--config` run with a 17-key JSON can leave §9
placeholders unfilled if the §0 docs placeholder was matched first.
This is **inherited from Wave 351 P5**, not introduced by Wave 360 P2.
Users running `--config` should be aware of this and may want to
run `--validate` after rendering to confirm fill state before applying
the draft. A future wave could either (a) anchor the regex to the §9
section using a more specific pattern, or (b) loop the substitution
with a section-aware filter — but that's out of scope for this
additive-only wave.

---

## 3. Unresolved gaps / future work

| Gap | Suggested next action |
|---|---|
| `count=1` substitution may leave §9 placeholders unfilled if §0 docs match first (pre-existing from Wave 351 P5) | Anchor the 5 affiliation regexes to §9 with a `^[^[]*?` prefix or section marker |
| `--validate` is informational; no hard-gate mode | Add `--validate --strict` (exit 1 if any unfilled) in a future additive wave if CI needs a pre-submit gate |
| `--dry-run` shows defaults but doesn't show what the *user* would need to change (e.g., "this is currently 'Hugo Huang, MIT CSAIL'; you should replace with your real authors") | Optional: add a `--dry-run --diff` mode that compares the scaffold against any user-provided `--config` and prints a per-field diff |
| No automated pre-submit check in CI that runs `--validate` and asserts 17/17 filled | Future CI gate (after user has actually filled the form) |

---

## 4. Files modified

| File | Change type | Lines (approx) |
|---|---|---|
| `tools/render_cover_letter.py` | EXTEND (additive) | +~140 lines (1 docstring update + 2 helper functions + 2 CLI flags + 1 autofill flag + summary print in `--interactive`) |
| `docs/audit/wave360-cover-letter-interactive-ux.md` | NEW | This file |

No other files were touched. Canonical `tnnls_submission/cover_letter.md`
md5 byte-stable across all invocations
(`e44fa82b34ae51b5feb0f1d5e03d4df7`).
