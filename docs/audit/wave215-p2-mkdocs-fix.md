# Wave 215 P2: mkdocs strict-mode cross-ref warning fix

## Problem

`mkdocs build --strict` aborted with 2 warnings, both from
`docs/cover-letter-tpami.md`:

```
WARNING - mkdocs_autorefs: cover-letter-tpami.md: Could not find cross-reference target 'Affiliation'
WARNING - mkdocs_autorefs: cover-letter-tpami.md: Could not find cross-reference target 'Date'
Aborted with 2 warnings in strict mode!
```

Root cause: the signature block at the end of the cover letter used bare
bracketed tokens (`[Corresponding author]`, `[Affiliation]`, `[Email]`,
`[Date]`) as **submission-time template placeholders** for the user to
fill in. mkdocs-autorefs interprets any `[Token]` as a reference-style
link target and warns when the target is not defined elsewhere in the
docset.

## Fix

Wrap each signature placeholder in inline code (backticks) so they are
rendered as literal text and not parsed as cross-reference targets.

### Diff (4 lines changed)

```diff
 Sincerely,

-[Corresponding author]
-[Affiliation]
-[Email]
-[Date]
+`[Corresponding author]`
+`[Affiliation]`
+`[Email]`
+`[Date]`
```

## Reviewer placeholder investigation

The task spec also asked about reviewer-section italic labels at lines
342, 354, 368, 382, 397 (e.g. `*Affiliation:* e.g., Meta AI Research
(ProbFlow team) / Weizmann Institute — *to be confirmed at
submission.*`).

Empirical check: mkdocs-autorefs does **not** interpret italic
`*...*` markup as cross-reference targets. After applying only the
signature-block fix, `mkdocs build --strict` reports 0 warnings — the
italic reviewer placeholders do not contribute to the warning set, so
they were left unchanged to minimise diff. If stylistic consistency
with the signature block is later desired, a follow-up sweep can
convert `*Affiliation:*` → `` `Affiliation:` `` and
`*to be confirmed at submission.*` → `` `to be confirmed at submission.` ``,
but this is cosmetic and out of scope for the strict-mode fix.

## Verification

```
$ mkdocs build --strict --clean 2>&1 | tail -5
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: .../site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 23.96 seconds
```

- Warnings before: 2
- Warnings after: 0
- Build status: success (in 23.96s)

## Scope summary

- 1 file modified: `docs/cover-letter-tpami.md`
- 4 lines changed (signature placeholders wrapped in inline code)
- 0 reviewer-placeholder changes (not required by strict mode)
- 1 commit (Wave 215 P2)
