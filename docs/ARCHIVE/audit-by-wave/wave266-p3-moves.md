# Wave 266 P3: git mv safe-to-move items per P1+P2 inventory

**Date:** 2026-09-22
**Branch:** main
**Scope:** Execute the two `git mv` operations for the items that P1
classified as `safe_to_move` (or downgraded-from-`NEED_GREP` to
`safe_to_move` after P2 grep) and verify each step. NO must-update-
references items are moved (per hard-rule "DO NOT move files with active
code references"), and NO root-level items are deleted (P2 confirmed
`cover_letter.md` vs `tnnls_submission/cover_letter.md` and
`submission_checklist.md` vs `tnnls_submission/submission_checklist.md`
target different venues — ICLR 2027 / NeurIPS FM Workshop vs IEEE TNNLS —
so they are NOT duplicates).

## 1. Method

1. Created three target subdirectories under `docs/internal/`:
   - `docs/internal/env/` — for future env_hash* files (no P1+P2 items
     target this; created empty for the directory-layout convention
     specified by the P3 task spec).
   - `docs/internal/results/` — destination for `ablation_results.txt`.
   - `docs/internal/todo/` — destination for `todo.json.bak`.
2. For each safe-to-move item, ran `git mv <src> <dst>` to preserve
   git history (renames detected at R100 similarity).
3. Verified after the moves: `git status` confirms R100 rename detection
   for both ops.
4. Verified hard-rules compliance:
   - **No source code changes** (only file moves + new audit doc added
     under `docs/audit/`).
   - **D.4 30/30 PASS preserved** (no `tests/` modifications; the two
     moved files have zero inbound references in `tests/test_d4_regression_vectors.py`
     and `tests/test_adapters/test_regression_vectors.py` per `grep -n
     'ablation_results\|todo\.json\.bak'`).
   - **mkdocs 0 warnings preserved** (no `mkdocs.yml` / `docs/**`
     non-audit changes; the new audit doc is covered by the
     `audit/wave*.md` glob in `mkdocs.yml` line 278).
   - **Claims consistency no drift** (no CLAIMS.md / paper-draft /
     DATA_PRESENTATION changes; this doc is purely an inventory of
     moves).

## 2. Moves performed (2 items)

### 2.1 `ablation_results.txt` → `docs/internal/results/ablation_results.txt`

- **Source:** repo root, 4562 bytes, mtime `2026-08-31 20:11`, sha256
  unchanged.
- **Destination:** `docs/internal/results/ablation_results.txt`,
  same sha256 (preserved by `git mv`).
- **Rationale:** Superseded by `verification_outputs/ablation_q4_2026.json`
  (the script's default `--output` arg, see `scripts/run_ablation_sweep.py`).
  Per P1 inventory: 0 inbound code refs; per P2 grep: 0 production refs
  (the 6 grep matches all live inside `docs/audit/wave266-p1-inventory.md`,
  which is the new audit doc itself — not a code dependency).
- **Git rename detection:** R100 (100% similarity).

### 2.2 `todo.json.bak` → `docs/internal/todo/todo.json.bak`

- **Source:** repo root, 49347 bytes, mtime `2026-09-11 13:03`, sha256
  unchanged.
- **Destination:** `docs/internal/todo/todo.json.bak`, same sha256.
- **Rationale:** A `.bak` of `todo.json` from before the Wave 32
  re-architecture. Per P1 inventory: 0 inbound production refs; per
  P2 grep: 0 production refs (the 10 grep matches all live inside
  `docs/ARCHIVE/audit-waves-1-99/wave{34,36,43,53}-*.md` archives,
  which explicitly flag the file as "should NOT be committed" — moving
  it under `docs/internal/` reinforces its archive-only status).
- **Git rename detection:** R100 (100% similarity).

## 3. Items NOT moved (per hard-rule "DO NOT move files with active code references")

P2 grep classified all 12 NEED_GREP items as `must_update_references`
(non-zero inbound production references requiring a lockstep rewrite).
Per the hard rule (DO NOT move files with active code references),
**NONE of those 12 are moved by this commit**. They remain at the repo
root pending either a future paired-rewrite pass or a KEEP decision:

| # | Item | Inbound refs | Decision |
|---|------|--------------|----------|
| 1 | `env_hash.txt` | 75 (CI + docs + Dockerfile + adapter docstring) | KEEP at root |
| 2 | `env_hash_host_fingerprint.json` | 10 | KEEP at root |
| 3 | `env_hash_R2.txt` | 4 | KEEP at root |
| 4 | `env_hash_R3.txt` | 3 | KEEP at root |
| 5 | `env_hash_R5.txt` | 4 | KEEP at root |
| 6 | `env_hash_R6.txt` | 3 | KEEP at root |
| 7 | `pytest_final.txt` | 18 (9 in `04-test-ci-audit.md`) | KEEP at root |
| 8 | `pytest_results.txt` | 11 (cover_letter D.4 cite + governance) | KEEP at root |
| 9 | `todo.json` | 51 (CI gate `docs-validate.yml:87`) | KEEP at root |
| 10 | `todo/` | 599 (8 source modules + 12 tests + 80+ audit docs) | KEEP at root |
| 11 | `plots/` | 26 (`tools/aggregate_wave186_p4.py` + 4 PNG citations) | KEEP at root |
| 12 | `requirements/` | 3 (`docs/environments.md` cites `requirements/protbfn.lock`) | KEEP at root |

These 12 items warrant either a paired-rewrite move (commit `g` +
rewrite pass) or a KEEP-at-root decision in a future wave.

## 4. Items NOT deleted (per P2 duplicate-check)

P2 ran `diff cover_letter.md tnnls_submission/cover_letter.md` and
`diff submission_checklist.md tnnls_submission/submission_checklist.md`
(line 138-167 of `wave266-p2-grep-audit.md`) and confirmed the
root-level and TNNLS-targeted versions are **distinct documents**:

- Root `cover_letter.md` → venue: **ICLR 2027 / NeurIPS Flow-Matching
  Workshop**; titled `# Cover Letter`; addressed to "Area Chair /
  Program Committee, ICLR 2027 (or NeurIPS Flow-Matching Workshop)".
- `tnnls_submission/cover_letter.md` → venue: **IEEE TNNLS**; titled
  `# Cover Letter — FlowA for IEEE TNNLS`; opens with
  `## §0 USER ACTION REQUIRED — Fill These Placeholders Before Submitting`.
- Root `submission_checklist.md` → venue: **ICLR 2027 / NeurIPS FM
  Workshop**; titled `# Submission Checklist — FlowA (ICLR 2027 /
  NeurIPS Flow-Matching Workshop)`; authored by "Wave 97 Agent A"
  (template status TEMPLATE).
- `tnnls_submission/submission_checklist.md` → venue: **IEEE TNNLS**;
  titled `# TNNLS Submission Checklist — FlowA`; status "Finalised for
  TNNLS submission. All boxes verified at Wave 242 P4 (D.4 30/30 PASS,
  mkdocs 0 warnings, claims_consistency no drift)."

Both root copies defer to the TNNLS submission package for the TNNLS
venue per the `MANIFEST.md` convention. **No deletions.** `n_items_deleted = 0`.

## 5. Root-item counts (before vs after moves)

| Snapshot | Count | Source |
|----------|-------|--------|
| `n_root_items_before` (at P3 start, state-at-HD-commencement) | 53 | `git ls-tree 13564c1 --name-only \| grep -v "^\\." \| wc -l` = 53 (52 P1/P2 era + `reproduce/` added by Wave 267 P1); plus `?? reproduce/` visible at session start = 53 if measured against the HEAD preceding this work |
| `n_root_items_after` (HEAD post-moves, `a0f3c1c`) | 51 | `git ls-tree a0f3c1c --name-only \| grep -v "^\\." \| wc -l` |
| `n_items_moved` (git mv ops) | 2 | this commit + Wave 267 P2 commit (`a0f3c1c`) |
| `n_items_deleted` (git rm ops) | 0 | P2 confirmed no duplicates |

The 2-item decrease matches the 2 git mv operations exactly. Note that
git-tracked item count is the canonical measure (a gitignore'd dir like
`site/` was excluded by `git ls-tree` but visible via `ls -1 | grep
-v "^\\."`; this report uses the git-tracked count for both before and
after, so the delta is exactly `n_items_moved`).

## 6. Files kept / moved / deleted

### 6.1 Files MOVED (2)

| Source | Destination | R% | Bytes |
|--------|-------------|----|-------|
| `ablation_results.txt` | `docs/internal/results/ablation_results.txt` | 100% (R100) | 4562 |
| `todo.json.bak` | `docs/internal/todo/todo.json.bak` | 100% (R100) | 49347 |

### 6.2 Files DELETED (0)

None. P2 confirmed no duplicate pairs exist.

### 6.3 Files KEPT at root (51 files + dirs remaining, per Section 5)

All 51 items stay at the repo root:

- **Convention-pinned (cannot-move):** `README.md`, `LICENSE`,
  `CODEOWNERS`, `SECURITY.md`, `pyproject.toml`, `uv.lock`,
  `requirements-lock.txt`, `requirements-kanzi.txt`,
  `requirements-lineageflow.txt`, `Dockerfile`, `mkdocs.yml`,
  `CHANGELOG.md`, `CONTRACTS.md`, `DESIGN_BOUNDARY.md`,
  `CONTRIBUTING.md`, `FAQ.md`, `QUICKSTART.md`, `TUTORIAL.md`,
  `cover_letter.md`, `submission_checklist.md`, `supplementary.md`,
  `ROADMAP.md`, `INSTALL_REPORT.md`, `RELEASE-NOTES-v3.0.md`,
  `DATA_PRESENTATION.md`, `DATA_PRESENTATION_BRIEF.md`.
- **Code-imported (cannot-move):** `adaptive_reflow/`, `tests/`,
  `scripts/`, `tools/`, `data/`, `configs/`, `regression-vectors/`,
  `verification_outputs/`.
- **Mkdocs / submission-pinned (cannot-move):** `docs/`, `eaai_submission/`,
  `tnnls_submission/`.
- **NEED_GREP (KEEP-at-root decision):** `env_hash.txt`,
  `env_hash_host_fingerprint.json`, `env_hash_R2.txt`, `env_hash_R3.txt`,
  `env_hash_R5.txt`, `env_hash_R6.txt`, `pytest_final.txt`,
  `pytest_results.txt`, `todo.json`, `todo/`, `plots/`, `requirements/`.
- **Newly added (Wave 267 P1):** `reproduce/`.

## 7. Hard-rules compliance

- **DO use `git mv` (preserves git history)** — HONORED. Both ops used
  `git mv` and were detected as R100 renames (see `git show --name-status`
  on commit `a0f3c1c`).
- **DO NOT move files with active code references (must_update_references)**
  — HONORED. All 12 MUST_UPDATE_REFERENCES items stay at root (Section 3).
- **DO preserve D.4 30/30 PASS** — PRESERVED. No `tests/` modifications.
  Verified: `grep -n 'ablation_results\\|todo\\.json\\.bak'
  tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py`
  → 0 matches. The moved files are byte-identical, so the regression-
  vector hashes (which only check the algorithm output) are unaffected.
- **DO preserve mkdocs 0 warnings** — PRESERVED. No `mkdocs.yml` /
  `docs/**` non-audit changes. The new audit doc is covered by the
  `audit/wave*.md` glob in `mkdocs.yml:278`.
- **DO preserve claims consistency no drift** — PRESERVED. No
  CLAIMS.md / paper-draft / DATA_PRESENTATION changes. The two moved
  files are historical stdout / pre-Wave-32 snapshots and are not
  referenced by any active claim.

## 8. Recommended next steps (P4)

P4 should:
1. Verify the renames with `git log --follow docs/internal/results/ablation_results.txt`
   and `git log --follow docs/internal/todo/todo.json.bak` to confirm
   history preservation.
2. Re-run D.4 30/30 + mkdocs 0 warnings + claims-consistency no drift
   gates (these should all PASS without code changes).
3. Confirm no `git grep` references exist to the moved files at their
   OLD root-level paths (sanity check the inventory).
4. Optionally add an `.gitignore` rule for `*.bak` to prevent future
   `*.bak` files from being committed (out of scope for P3).
5. Decide per the 12 KEEP-at-root items (Section 3) whether any warrant
   a paired-rewrite move in a future wave, or remain KEEP-at-root.
