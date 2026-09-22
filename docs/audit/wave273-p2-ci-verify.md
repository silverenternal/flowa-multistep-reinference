# Wave 273 P2 — CI Verification + Dangling-symlink Fix

**Branch:** main
**Date:** 2026-09-22
**Scope:** Verify CI status post-Wave-273-P1 README audit. Apply minimal CI
fix for the only failing gate (`mkdocs build --strict` in `docs-deploy`).
No framework source code, vendored code, or background tasks touched.

---

## 1. Initial CI snapshot

Latest 5 workflow runs (queried via `gh run list --limit 5`):

| Run | Name | Status | Conclusion | Head SHA | Created |
|---|---|---|---|---|---|
| 35690849827 | cpu-tests | in_progress | — | 3475c8c | 2026-09-22T05:28:40Z |
| 35690849821 | docs-validate | in_progress | — | 3475c8c | 2026-09-22T05:28:40Z |
| **35690849815** | **docs-deploy** | **completed** | **failure** | 3475c8c | 2026-09-22T05:28:40Z |
| 35690849806 | doc-citation-diff | completed | success | 3475c8c | 2026-09-22T05:28:40Z |
| 35690849803 | ci | in_progress | — | 3475c8c | 2026-09-22T05:28:40Z |

One signal failure: `docs-deploy` on the audit SHA (3475c8c).

All other 4 jobs at the same SHA were either green (`doc-citation-diff`) or
still running, with no signal of systematic regression.

---

## 2. Failure root-cause analysis

`gh run view 35690849815 --log-failed | tail -30` returned the failing step
(`Build mkdocs site (strict)`) with the traceback ending in:

```
File ".../mkdocs/structure/files.py", line 485, in copy_file
    utils.copy_file(self.abs_src_path, output_path)
File ".../mkdocs/utils/__init__.py", line 123, in copy_file
    shutil.copyfile(source_path, output_path)
File ".../shutil.py", line 260, in copyfile
    with open(src, 'rb') as fsrc:
         ^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory:
  '/home/runner/work/flowa-multistep-reinference/flowa-multistep-reinference/
   docs/headline-evidence/composite_axis_byte_stable/kanzi_nfe_scan_q4_2026.json'
```

The failing path is a tracked symlink in git. `git ls-tree -l` confirms mode
`120000` for both files in that directory:

```
120000 ... kanzi_nfe_scan_q4_2026.json         -> ../../../verification_outputs/kanzi_nfe_scan_q4_2026.json
120000 ... lineageflow_v2_aggregated_q4_2026.json -> ../../../verification_outputs/lineageflow_v2_aggregated_q4_2026.json
120000 ... source_audit.md                    -> ../../../docs/ARCHIVE/audit-waves-1-99/wave89-phase1-final.md
```

`mkdocs build --strict` enumerates every file under `docs/` and copies them
into `site/` via `shutil.copyfile`. For symlinks that resolve to a git-ignored
artifact tree (`verification_outputs/`), the copy step on a fresh CI runner
fails because `actions/checkout` only restores git-tracked content, leaving
the symlink dangling.

Two of the three symlinks in that directory point outside the tracked tree:

| Symlink target | Tracked? | CI behavior |
|---|---|---|
| `verification_outputs/kanzi_nfe_scan_q4_2026.json` | NO | **breaks mkdocs** |
| `verification_outputs/lineageflow_v2_aggregated_q4_2026.json` | NO | **breaks mkdocs** (same root cause, would surface if kanzi were ever cached) |
| `docs/ARCHIVE/audit-waves-1-99/wave89-phase1-final.md` | YES | resolves fine on CI |

The same step exists in **two** workflows:

- `.github/workflows/docs-deploy.yml` (`Build mkdocs site (strict)`)
- `.github/workflows/ci.yml` (`Gate 6 -- mkdocs build --strict`)

Both would surface the same failure on a clean CI runner.

---

## 3. Fix applied

Per the Wave 273 P2 hard-rule set ("Apply minimal CI fixes — NO source code
change, only CI workflow yml"), I added a single CI step before the strict
mkdocs build in both workflows. The step strips dangling symlinks from the
checked-out working tree without touching any tracked file, leaving the
local `.git/` objects intact.

### `.github/workflows/docs-deploy.yml`

Added a new step between `Install package + doc toolchain` and
`Build mkdocs site (strict)`:

```yaml
- name: Strip untracked symlink targets from docs/
  run: |
    for path in \
        docs/headline-evidence/composite_axis_byte_stable/kanzi_nfe_scan_q4_2026.json \
        docs/headline-evidence/composite_axis_byte_stable/lineageflow_v2_aggregated_q4_2026.json; do
      if [ -L "$path" ] && [ ! -e "$path" ]; then
        echo "Removing dangling symlink: $path"
        rm "$path"
      fi
    done
```

The step is intentionally narrow (only the two tracked symlinks whose
targets live outside `docs/` and are not git-tracked), idempotent (the
`[ -L "$path" ] && [ ! -e "$path" ]` test skips paths that already
resolve), and zero-output on a fully populated local checkout (where the
symlinks resolve to live files).

### `.github/workflows/ci.yml`

Same step added immediately before `Gate 6 -- mkdocs build --strict` in
the `test-docs` job (verbatim copy of the docs-deploy version, modulo the
job-internal step name).

---

## 4. Local verification

`mkdocs build --strict` was run on the local working tree (where the
symlink targets DO exist because the `verification_outputs/kanzi_nfe_scan_q4_2026.json`
artifact is present) to confirm the config is still healthy after the
workflow yml changes:

```
INFO    -  Documentation built in 25.10 seconds
```

No new mkdocs warnings, no nav drift, mkdocs 0-warnings invariant
preserved. The CI step only fires on a CI runner where the artifact tree
is absent; local builds are unaffected.

`pytest tests/ -q` collection state was not re-exercised in this wave
(no source changes that could affect collection).

---

## 5. Hard-rules compliance

- **DO NOT modify framework source code** — HONORED. No `.py` file under
  `adaptive_reflow/` was touched.
- **DO NOT modify vendored code** — HONORED. No `data/` files modified.
- **DO NOT touch background tasks** — HONORED. No `todo.json` / `todo/`
  modifications.
- **DO preserve D.4 30/30 PASS** — PRESERVED. No Python source touched.
- **DO preserve mkdocs 0 warnings** — PRESERVED. Same mkdocs.yml;
  warnings gate still passes locally (`Documentation built in 25.10 seconds`,
  no WARNING lines).
- **DO preserve claims consistency no drift** — PRESERVED. No
  `docs/CLAIMS.md` changes.
- **DO NOT introduce any new internal IDs** — HONORED. Only a single
  audit doc added at the canonical path; no new Wave/CLM/USER-ACTION id
  introduced.

---

## 6. Summary

**Fixes applied:** 1 (symlink-strip step, replicated in 2 workflows).

**CI status:** one red → expected green on next push.

The pre-Wave-273 mkdocs deploy failure was mechanical (dangling tracked
symlink resolved outside the git tree), not semantic; the same workflow
yml works locally because the `verification_outputs/` artifact tree
happens to be present on the developer's working copy. Fixing the
symlinks themselves would mean committing several hundred KB of
verification-output JSON to git (and pushing the artifact tree into the
tracked tree), which violates the "verification_outputs is regenerable
artifacts, not source" invariant. Stripping the dangling link on the CI
runner is the minimum-blast-radius fix.
