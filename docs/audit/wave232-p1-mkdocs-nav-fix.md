# Wave 232 P1 — mkdocs Nav Fix Audit

**Wave:** 232 P1 (mkdocs strict-build nav fix)
**Date:** 2026-09-21
**Author:** Wave 232 P1 agent
**Branch:** `main`
**Status:** DONE

---

## §1 Problem

`mkdocs build --strict` aborted with one warning:

```
WARNING - The following pages exist in the docs directory, but are not
included in the "nav" configuration:
  - tpami_submission_action_checklist.md
```

The file was added in Wave 231 P5 (commit `729b183`) as a USER-only
operational checklist (six steps for the corresponding author to push
the submission bundle through the TPAMI Editorial Manager). It is
deliberately internal — it should NOT be part of the published mkdocs
site.

## §2 Fix

Move the file to a dedicated internal directory and silence it via the
existing `not_in_nav` allowlist.

1. **Create** `docs/internal/` (did not exist).
2. **Move** `docs/tpami_submission_action_checklist.md` →
   `docs/internal/tpami_submission_action_checklist.md` via
   `git mv` so git tracks the rename.
3. **Update** `mkdocs.yml` `not_in_nav` block — add
   `internal/*.md` and `internal/**/*.md` so any future internal
   docs land in the same exclusion bucket.
4. **Update** all cross-doc references:
   - `docs/audit/wave231-p5-submission-package.md` (5 references)
   - `docs/audit/wave231-p6-final-verify.md` (1 reference)
   - `scripts/wave231_push_to_github.sh` (1 reference)
5. **Re-run** `mkdocs build --strict` → success, 0 warnings.

## §3 Files Touched This Wave

| Path | Action |
|------|--------|
| `docs/internal/tpami_submission_action_checklist.md` | created (via `git mv`) |
| `docs/tpami_submission_action_checklist.md` | deleted (via `git mv`) |
| `mkdocs.yml` | added `internal/*.md` + `internal/**/*.md` to `not_in_nav` |
| `docs/audit/wave231-p5-submission-package.md` | 5 path updates |
| `docs/audit/wave231-p6-final-verify.md` | 1 path update |
| `scripts/wave231_push_to_github.sh` | 1 path update |
| `docs/audit/wave232-p1-mkdocs-nav-fix.md` | this audit doc |

## §4 Verification

```bash
$ timeout 30 mkdocs build --strict 2>&1 | tail -5
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 23.14 seconds
```

Build succeeds. No `WARNING` lines emitted. The only stderr noise is
the Material for MkDocs team's banner about future MkDocs 2.0
backward-incompatible changes (not a build warning — printed at
session start regardless of config).

```bash
$ grep -rn 'tpami_submission_action_checklist' \
    docs/ scripts/ mkdocs.yml 2>/dev/null
docs/audit/wave231-p5-submission-package.md:8:`docs/internal/tpami_submission_action_checklist.md`)
docs/audit/wave231-p5-submission-package.md:33:| `docs/internal/tpami_submission_action_checklist.md` | …
docs/audit/wave231-p5-submission-package.md:132:`docs/internal/tpami_submission_action_checklist.md` enumerates …
docs/audit/wave231-p5-submission-package.md:190:- `docs/internal/tpami_submission_action_checklist.md` (created)
docs/audit/wave231-p5-submission-package.md:197:items are documented in `docs/internal/tpami_submission_action_checklist.md`
docs/audit/wave231-p6-final-verify.md:31:  - tpami_submission_action_checklist.md
docs/audit/wave231-p6-final-verify.md:68:`tpami_submission_action_checklist.md` (now at `docs/internal/tpami_submission_action_checklist.md`
scripts/wave231_push_to_github.sh:116:echo " Detailed action list: docs/internal/tpami_submission_action_checklist.md"
```

All actionable references updated. The two remaining `wave231-p6-final-verify.md`
mentions at lines 31 + 68 are historical — line 31 quotes the original
mkdocs warning (file was at `docs/tpami_submission_action_checklist.md`
when the warning was emitted), and line 68 notes the Wave 232 P1
relocation parenthetically.

## §5 Conclusion

mkdocs strict build is green. The internal USER-only action checklist
is no longer flagged as a missing nav entry. No source code changed.
