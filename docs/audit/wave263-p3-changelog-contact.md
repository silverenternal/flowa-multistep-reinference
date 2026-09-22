# Wave 263 P3: README fixes — Issue 7 (CHANGELOG wave 149-244 range) + Issue 8 (Contact USER ACTION placeholders) + drift cleanup

**Date:** 2026-09-22
**Branch:** main
**Scope:** README.md final-pass patch — Issue 7 (CHANGELOG range "(waves 149 through 244)" leaked internal wave-count range), Issue 8 (Contact section's "(11 USER ACTION placeholders to be filled before upload)" leaked placeholder reminder), plus two narrative-wave-number drift cleanups that re-entered README during Wave 263 P1/P2 (Wave 87 in R3 row, Wave 262 in Numerical Stability verification line).

## Issues addressed

### Issue 7 — CHANGELOG wave range reference

**Problem.** README line 253 ended with `**See [CHANGELOG.md](CHANGELOG.md) for the per-wave development history (waves 149 through 244).**` — the parenthetical `(waves 149 through 244)` leaked the internal development wave range to reviewer audiences. CHANGELOG.md is documented in its own header paragraph as "Internal development milestones; not intended for external reviewer audiences (see [README.md](README.md) and [tnnls_submission/](tnnls_submission/) for the submission-facing material)", so the reader-facing README should not advertise a specific wave range.

**Fix.** Replaced the parenthetical:

> **See [CHANGELOG.md](CHANGELOG.md) for the development history.**

The "per-wave development history" qualifier was also dropped (it accurately describes the CHANGELOG file's nature but is redundant with the link target itself). The link to CHANGELOG.md is preserved; the wave-count range is removed.

### Issue 8 — Contact USER ACTION placeholders

**Problem.** README line 247 carried `For TNNLS review correspondence: see [`tnnls_submission/cover_letter.md`](tnnls_submission/cover_letter.md) (11 USER ACTION placeholders to be filled before upload).` — the parenthetical "(11 USER ACTION placeholders to be filled before upload)" is an internal TODO reminder, not reviewer-facing content. TNNLS upload-time placeholders are tracked in `tnnls_submission/submission_checklist.md` and `tnnls_submission/cover_letter.md` itself (both git-tracked, both linked from the paper §3 Data Availability statement); the count "11" is project-management state, not public-facing material.

**Fix.** Removed the parenthetical:

> For TNNLS review correspondence: see [`tnnls_submission/cover_letter.md`](tnnls_submission/cover_letter.md).

The link target is preserved; the internal "USER ACTION" reminder is removed.

### Drift cleanup — narrative Wave references re-introduced by Wave 263 P1/P2

**Problem.** Wave 252 P2 (`8824252`) had explicitly cleaned all 13 narrative Wave refs in README to the reviewer-facing standard `grep -nE "Wave"` returns 0 matches. Wave 263 P1 (`0d842d8`, "Numerical Stability" section rewrite) and Wave 263 P2 (`73f1e97`, "R3 row per-record d_z" insertion) re-introduced two narrative Wave refs as part of their task-specific edits:

| Line (post-Wave 263 P2) | Section | Narrative ref |
|---:|---|---|
| 17 | Headline Results R3 row | `(Wave 87 seed 42 N=1000 batched)` |
| 191 | Numerical Stability | `Verified at Wave 262 (...)` |

These drift from the Wave 252 P2 standard, and issue-specific Wave refs (Wave 87 = a specific sweep command; Wave 262 = a specific audit doc) are tracked via the audit doc path itself (e.g. `verification_outputs/wave216-p1-r3-per-record.json` for the R3 row; `docs/audit/wave262-p1-revert-all.md` for the verification) — no narrative Wave mention is needed.

**Fix.**

1. R3 row (line 17): replaced `(Wave 87 seed 42 N=1000 batched)` → `(seed 42 N=1000 batched)`. The seed and N config (the data-provenance information) is preserved; the wave prefix is removed.
2. Numerical Stability (line 191): replaced `Verified at Wave 262 (...)` → `Verified (...)`. The audit doc paths `docs/audit/wave262-p1-revert-all.md`, `docs/audit/wave262-p2-verify.md`, `docs/audit/wave262-p5-final-verify.md` are preserved unchanged (the path names themselves are git-tracked references, not narrative Wave mentions).
3. Repository Structure tree (line 140): replaced `# per-wave audit docs (wave127, wave149-244)` → `# per-wave audit docs`. The `(wave127, wave149-244)` parenthetical was another leaked wave range reference; the descriptive label "per-wave audit docs" is sufficient.

## Hard-rule compliance

| Rule | Status |
|------|--------|
| DO NOT modify framework source code | HONOURED — only `README.md` modified |
| DO NOT modify vendored code | HONOURED — no vendored file touched; matches Wave 262 P1–P5 revert state |
| DO preserve D.4 30/30 PASS | HONOURED — 30/30 PASS (verified below) |
| DO preserve mkdocs 0 warnings | HONOURED — strict build returns 0 warnings |
| DO preserve claims consistency no drift | HONOURED — no drift (verified below) |

## Gate verification

### D.4 byte-stable regression vectors

```
python -m pytest tests/test_d4_regression_vectors.py -q --no-header
→ 30 passed, 3 warnings in 1.05s
```

**Result: 30/30 PASS.** ✓

### mkdocs build --strict

```
mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 25.32 seconds
```

**Result: EXIT=0, 0 warnings.** README.md is in the `not_in_nav` exclude list (line 322 of `mkdocs.yml`); README edits do not change mkdocs visibility. ✓

### claims consistency

```
python tools/check_claims_consistency.py
→ 60 active + 1 provisional + 2 deprecated claims.
→ No drift detected.
```

**Result: 0 drift.** ✓

### README narrative-wave grep (the Wave 252 P2 standard, re-verified)

```
$ grep -nE "Wave [0-9]" README.md
(no matches)
$ grep -nE "Wave " README.md
(no matches)
$ grep -nE "waves? [0-9]" README.md
(no matches)
```

**Result: 0 narrative Wave refs.** The Wave 252 P2 reviewer-facing standard is restored after the Wave 263 P1/P2 drift. ✓

### README USER ACTION grep (defensive, after Issue 8 fix)

```
$ grep -nE "USER ACTION" README.md
(no matches)
```

**Result: 0 USER ACTION refs.** ✓

### Path grep (preserved)

```
$ grep -niE "wave" README.md
(line numbers 16, 17, 20, 21, 108, 113, 147, 152, 191, 192, 198, ...)
```

12 lowercase path references preserved (all in `verification_outputs/`, `tools/`, `docs/audit/`). Per Wave 252 P2 rule: paths are git-tracked link targets and remain unchanged.

## Files modified

| File | Lines changed | Nature |
|---|---:|---|
| `README.md` | line 17 (R3 row) | removed "Wave 87 " from "(Wave 87 seed 42 N=1000 batched)" → "(seed 42 N=1000 batched)" |
| `README.md` | line 140 (Repo tree) | removed "(wave127, wave149-244)" from `# per-wave audit docs (...)` |
| `README.md` | line 191 (Numerical Stability) | removed "at Wave 262 " from `Verified at Wave 262 (...)` → `Verified (...)` |
| `README.md` | line 247 (Contact) | removed "(11 USER ACTION placeholders to be filled before upload)" |
| `README.md` | line 253 (footer) | removed "(waves 149 through 244)" + "per-wave development history" qualifier from CHANGELOG reference |
| `docs/audit/wave263-p3-changelog-contact.md` | new file | this audit doc |

## Out-of-scope items preserved verbatim

- TL;DR (line 7) — not touched; the headline-numbers mention is preserved
- R1 + R2 + R4 + R5 + R5b + R6 rows (lines 15, 16, 18, 19, 20, 21) — not touched
- Architecture / Installation / Quick Start / Reproducing the Paper / Submission Gates / Data and Model Availability / TNNLS Submission Package / Citation / License — not touched; all preserved verbatim
- All git-tracked audit doc paths and `verification_outputs/*.json` paths — preserved verbatim

## DATA_PRESENTATION_BRIEF.md review

Reviewed per task spec ("check for similar issues"). The brief's headline-results R3 cell (line 17) and the brief's R5b/R3 commentary (lines 44, 45) carry wave refs in the form `(Wave 87 seed 42 + Wave 208 N=200 + Wave 216 N=1000 projected)` and similar — these are **data-provenance** references that pair each wave number with a specific seed/N/measurement config (e.g., `Wave 87 seed 42`, `Wave 208 P2 per-record`, `Wave 216 P1 projected`). They are not wave-range references like Issue 7 (no `(Wave X → Wave Y)` range) and not USER ACTION placeholders like Issue 8. The brief is internal technical documentation; the wave refs name specific experiment configurations that are not otherwise disambiguable from the path alone.

**Conclusion: no changes needed in DATA_PRESENTATION_BRIEF.md.** Brief wave count after this pass: 7 capital-W "Wave [0-9]" refs in technical-provenance context (lines 17, 44, 45) — unchanged from pre-pass count.

## CHANGELOG.md review

Reviewed per task spec ("remove wave numbers from final-state summary at top"). The CHANGELOG.md header is:

> # Changelog — FlowA Multi-Step Re-Inference
>
> Per-wave development history for the FlowA framework. Internal development milestones; not intended for external reviewer audiences (see [README.md](README.md) and [tnnls_submission/](tnnls_submission/) for the submission-facing material).

The header does not carry a wave range reference (no `(Wave 149 → Wave 244)`-style parenthetical). The word "Per-wave" is a descriptive adjective ("per-wave development history"), not a wave number. The body of CHANGELOG.md is intentionally a per-wave log — each section is a wave entry by design; removing wave numbers from the body would defeat the file's purpose (which is to be an internal development milestone log, explicitly excluded from reviewer audiences per its own header).

**Conclusion: no changes needed in CHANGELOG.md.** The Issue 7 wave range was confined to the README footer; CHANGELOG.md's header has no analogous range to remove.

## Conclusion

README is reconciled to the Wave 252 P2 reviewer-facing standard: 0 narrative Wave refs, 0 USER ACTION refs, 0 wave-range references. The Issue 7 CHANGELOG range and Issue 8 USER ACTION placeholder are both removed. Two narrative-Wave drifts from Wave 263 P1/P2 are cleaned up. All three acceptance gates (D.4 byte-stable 30/30, mkdocs strict 0 warnings, claims consistency no drift) pass. The framework source code, vendored upstream code, and verification_outputs are unchanged.

## Attribution

Audit doc generated by Wave 263 P3 README-fix agent.

Co-Authored-By: Claude Code <noreply@anthropic.com>