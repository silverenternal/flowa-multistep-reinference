# Wave 101 — Layer-4 Docs + Config Hygiene Fix Plan

Companion to `docs/audit/wave101-review-layer4-docs-config.md`. READ-ONLY audit
identified 7 issues; this plan describes the **execution order** to close them.

## Section 1 — Goal

Add 7 additive docs / nav entries that improve the discoverability + project
hygiene of `docs/`, `pyproject.toml`, `requirements*.txt`, and the `git` working
tree. **No deletions, no source code changes.**

Constraints:
* **Zero source code changes** — Layer 4 is docs + config only
* **No D.4 byte-stable vector changes** (no source touched)
* All additive changes (no removal of legacy docs)
* `mkdocs build --strict` must remain exit 0

## Section 2 — Priorities

### P0 (must-do, zero risk)
* **P0-A**: Fix #4 — add dep pinning rationale comment to `pyproject.toml`. 5 LOC.
* **P0-B**: Fix #5 — add `ARCHIVED.md` note to `r4/r5/r17-survey/` dirs. 30 LOC total.

### P1 (additive docs)
* **P1-A**: Fix #1 — author `docs/audit/INDEX.md` (per-wave table). 300 LOC.
* **P1-B**: Fix #2 — add "current verdict" callouts to `CONSOLIDATED_RESULTS.md`. 50 LOC.
* **P1-C**: Fix #3 — audit + update `docs/environments.md` (VENV_MATRIX). 30 LOC.

### P2 (git hygiene)
* **P2-A**: Fix #7 — `git add` curated subset of untracked `docs/audit/wave*.md` files.
* **P2-B**: Fix #6 — audit + extend `mkdocs.yml` nav for Wave 39-100 docs.

## Section 3 — Fix order (doc additive → mkdocs → git add)

1. **P0-A** (pyproject.toml comment). `git diff pyproject.toml` should show only +5 LOC comment.
2. **P0-B** (3 ARCHIVED.md files). Pure docs additions.
3. **P1-C** (VENV_MATRIX update). Verify `docs/environments.md` covers 11 venvs.
4. **P1-B** (CONSOLIDATED_RESULTS callouts). Add 4 callouts.
5. **P1-A** (audit INDEX). Largest single doc addition (~300 LOC).
6. **P2-B** (mkdocs nav). Verify all Wave 39-100 docs are reachable.
7. **P2-A** (`git add` wave101 audit + curated prior waves). Verifies P1-A's INDEX has stable commit reference.

**Rationale**: docs additive first (zero risk), git add last (so the new docs get committed in their own atomic commits).

## Section 4 — Acceptance checklist

Per-commit:
- [ ] `mkdocs build --strict` → exits 0
- [ ] `git status --short docs/` shows expected untracked-after-add count
- [ ] `pytest tests/ -q` → no test failures (no source change)
- [ ] `python tools/capability_audit.py` → G-MASTER 7/7 unchanged

Per-fix additional:
- [ ] **P1-A**: `docs/audit/INDEX.md` has one row per wave (Wave 32 → Wave 101) with 1-5 audit doc filenames + status.
- [ ] **P1-B**: `CONSOLIDATED_RESULTS.md` has a "current verdict" callout at top of §7 (Tier 3 results), §15 (Wave 86-93), §18 (NFE-adaptive).
- [ ] **P1-C**: `docs/environments.md` lists all 11 venvs with activation matrix (which tool → which venv).
- [ ] **P2-B**: `mkdocs.yml` nav contains entries for the new audit docs.

## Section 5 — Do NOT do (scope guard)

1. **DO NOT delete any doc file**. Even `r*-survey/` legacy dirs — preserve for historical reference.
2. **DO NOT rewrite `paper-draft.md`**. The 5270-LOC size is necessary; per-model §7 sub-sections are core Tier 3 story.
3. **DO NOT consolidate `audit/` files**. Each wave's audit docs are deliverables; future waves may need to reference them.
4. **DO NOT change `pyproject.toml` dep versions**. Only add a comment explaining the existing per-model pinning.
5. **DO NOT touch `requirements-lock.txt`** (the lockfile is canonical).
6. **DO NOT touch any source code** (Layer 4 is docs + config only).
7. **DO NOT run `mkdocs serve` or `mkdocs gh-deploy`** — only `mkdocs build --strict` to verify.
8. **DO NOT commit unrelated changes**. Each commit has a single Wave 101 Layer-4 message.

## Section 6 — Estimated effort

* P0-A: 5 minutes (1 comment block)
* P0-B: 15 minutes (3 ARCHIVED.md files)
* P1-A: 60 minutes (per-wave table, ~90 rows × 3-5 fields)
* P1-B: 20 minutes (4 callout blocks)
* P1-C: 20 minutes (audit 11-venv matrix + edit)
* P2-A: 15 minutes (curated `git add`)
* P2-B: 20 minutes (audit + extend mkdocs nav)

**Total**: ~2.5 hours across 7 commits.

## Section 7 — Commit plan

1. `wave101-p0a-pyproject-pinning-comment` (P0-A)
2. `wave101-p0b-r-survey-archived-notes` (P0-B)
3. `wave101-p1c-venv-matrix-update` (P1-C)
4. `wave101-p1b-consolidated-callouts` (P1-B)
5. `wave101-p1a-audit-index` (P1-A, largest)
6. `wave101-p2b-mkdocs-nav-wave39-100` (P2-B)
7. `wave101-p2a-git-add-audit-docs` (P2-A)

Each commit has a single audit-doc reference in its body and `mkdocs --strict: PASS` footer.

---

Status: AUDIT COMPLETE (archive/config checks recorded; remaining external-resource items deferred).
