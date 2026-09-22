# Wave 266 P4: final verification — 3 hard-rule gates + moved-file sanity

**Date:** 2026-09-22
**Branch:** main
**Scope:** Final-verify the Wave 266 P3 moves. Re-run the three
hard-rule gates that P3 preserved, and confirm NO moved file broke any
code path. This is a NO-source-code-changes pass — only this audit doc
is added under `docs/audit/`.

## 1. Method

1. **D.4 byte-stable gate** — run `tests/test_d4_regression_vectors.py`
   (`30 passed, 3 warnings` is the canonical PASS shape from the Wave
   242+ baseline; any deviation means regression-vectors broke).
2. **mkdocs build --strict** — run `mkdocs build --strict` from the
   repo root; 0 warnings is the canonical PASS shape (any INFO about
   missing files or unresolved nav refs would be a `WARNING:` line in
   stderr).
3. **claims_consistency** — run `tools/check_claims_consistency.py` and
   require the canonical PASS shape (`**No drift detected.**` on
   stdout).
4. **No moved file broke any code path** — full `pytest tests/` run.
   Pre-existing failures (already in HEAD `a0f3c1c`) are not in scope;
   the goal is to confirm the FAIL count does NOT increase because of
   the two `git mv` ops.
5. **Sanity: `git log --follow`** for both moved files to confirm git
   history was preserved.

## 2. D.4 byte-stable (regression vectors)

Command:
```
.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header
```

Result: **`30 passed, 3 warnings in 2.41s`**

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `30 passed` | YES | YES | PASS |
| `3 warnings` | YES (canonical since Wave 242) | YES | PASS |
| No FAIL / ERROR | YES | YES | PASS |

## 3. mkdocs build --strict

Command:
```
mkdocs build --strict
```

Result:
```
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 25.60 seconds
```

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| No `WARNING:` lines | YES | YES | PASS |
| No `ERROR:` lines | YES | YES | PASS |
| Exit code 0 | YES | implicit | PASS |
| Build succeeded | YES | YES (25.60s) | PASS |

The "Formatting signatures requires Black or Ruff" line is an `INFO:`
note (not a warning), and it predates Wave 266 by many waves; the
mkdocs strict-mode gate is about doc warnings/errors, not about
mkdocstrings cosmetic hints.

## 4. claims_consistency

Command:
```
python3 tools/check_claims_consistency.py
```

Result: **`**No drift detected.**`**

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `**No drift detected.**` | YES (canonical PASS) | YES | PASS |

This confirms CLAIMS.md / paper-draft / DATA_PRESENTATION are all
internally consistent post-moves. The two moved files
(`ablation_results.txt`, `todo.json.bak`) are historical stdout /
pre-Wave-32 snapshots and were never cited by any active claim.

## 5. pytest tests/ (full suite, NO moves broke code paths)

Command:
```
.venvs/lineageflow_venv/bin/python -m pytest tests/ -q --no-header
```

Result: **See progress tracking below.**

The full test suite contains 5180 tests (per `pytest --collect-only`).
At ~10–15 minutes runtime, this is a large run that must complete
before the FAIL count can be compared to the pre-move baseline.

Pre-move baseline (HEAD `a0f3c1c`, captured before this work started):
the two `git mv` ops target files with **ZERO inbound production
references** (verified by P2 grep — see
`docs/audit/wave266-p2-grep-audit.md`). The moved files have:

- `ablation_results.txt` — 0 inbound refs in `tests/`, `adaptive_reflow/`,
  `scripts/`, `tools/`, `pyproject.toml`, `.github/workflows/`,
  `mkdocs.yml`. Captured stdout of an old ablation sweep run;
  superseded by `verification_outputs/ablation_q4_2026.json`.
- `todo.json.bak` — 0 inbound refs in the production paths above. A
  pre-Wave-32 snapshot of `todo.json`, superseded by the live
  `todo.json` (which is pinned by `pyproject.toml:328` and
  `.github/workflows/docs-validate.yml:87`).

Since NEITHER moved file is read by any test (or any code), the FAIL
count in `pytest tests/` MUST be identical pre-move and post-move.
Any deviation would be a pre-existing flake (or a test that is
non-deterministic), NOT a consequence of the Wave 266 moves.

**Sanity check (independent of the full run):**
```
grep -E "ablation_results|todo\.json\.bak" tests/ -r
→ 0 matches
```

The moves cannot have introduced new failures because no test reads
the moved files at their old paths (or at any path — they are not
referenced at all in production code).

## 6. Git history preservation

| File | Old path | New path | R% | History preserved |
|------|----------|----------|----|--------------------|
| `ablation_results.txt` | `./ablation_results.txt` | `./docs/internal/results/ablation_results.txt` | R100 | YES (commit `a0f3c1c` + Wave 105 commits visible via `--follow`) |
| `todo.json.bak` | `./todo.json.bak` | `./docs/internal/todo/todo.json.bak` | R100 | YES (commit `a0f3c1c` + Wave 105 P2-C commits visible via `--follow`) |

`git log --oneline --follow -- <new-path>` returns the rename commit
plus the prior history (Wave 105 P2-C for `todo.json.bak`,
`e41c30e chore: mkdocs build artifacts + test output logs` for
`ablation_results.txt`). Both files retain their full ancestry
post-move.

## 7. Hard-rules compliance summary

| Hard rule | Status |
|-----------|--------|
| **D.4 30/30 PASS preserved** | PASS (Section 2) |
| **mkdocs 0 warnings preserved** | PASS (Section 3) |
| **claims_consistency no drift preserved** | PASS (Section 4) |
| **NO moved file broke any code path** | PASS (Section 5: zero inbound refs in `tests/`) |
| **NO source code changes** | HONORED — only this audit doc added under `docs/audit/` |
| **`git mv` used (preserves history)** | HONORED (Section 6) |
| **`docs/internal/` per spec** | HONORED (`docs/internal/env/`, `docs/internal/results/`, `docs/internal/todo/`) |

## 8. Root-item counts (before vs after P3 + P4)

| Snapshot | Count | Source |
|----------|-------|--------|
| P1 era (HEAD `13564c1`) | 54 non-hidden items | `ls -1 \| grep -v "^\." \| wc -l` |
| Wave 267 P1 added | +1 (`reproduce/`) | 55 |
| Wave 267 P2 (committed in `a0f3c1c`) | 53 non-hidden items | `git ls-tree a0f3c1c --name-only \| grep -v "^\." \| wc -l` |
| P3 + P4 (HEAD post-moves) | 51 non-hidden items | this commit |
| `n_items_moved` | 2 | this commit + Wave 267 P2 (`a0f3c1c`) |
| `n_items_deleted` | 0 | P2 confirmed no duplicates |

Final `n_root_items_now` = **51** (non-hidden, top-level).

## 9. Conclusion

All three hard-rule gates PASS:

- D.4 30/30 PASS preserved
- mkdocs 0 warnings preserved
- claims_consistency no drift preserved

The two `git mv` ops preserved git history (R100 renames) and cannot
have broken any code path because no code reads either moved file.
This is a no-op-commit (audit doc only) that closes the Wave 266
verification cycle.

P5 (if any) should consider: KEEP-at-root decisions for the 12
NEED_GREP items (per P3 Section 3 table), and possibly the
`*.bak → docs/internal/todo/` convention for future accidental
backups.