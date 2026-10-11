# Push unblock — 147.1 MB supplementary_bundle.zip exceeds GitHub's 100 MB blob limit

**Date:** 2026-10-11
**Status:** READY_TO_COMMIT
**Trigger:** `git push origin main` (192 commits, user-authorized) rejected by GitHub's
pre-receive hook:
`remote: error: File tnnls_submission/supplementary_bundle.zip is 147.10 MB; this exceeds
GitHub's file size limit of 100.00 MB` / `GH001: Large files detected` / `pre-receive hook declined`.
**Scope:** Remove the oversized blob from local history (it was never pushed — `origin/main`
did not contain any of the 192 commits), keep the file on disk unchanged (SHA-256 stable),
gitignore it, and reword the two GitHub blob-URL references so they no longer 404. NO paper
content change, NO number change, NO verdict change, NO vendored code change.

---

## Observed facts

### Blocker

- `tnnls_submission/supplementary_bundle.zip` = **154,249,954 bytes (147.1 MB)** on disk;
  blob SHA-256 `d1b5ba24a55a9336e7b65cee7bea652482943932181ddfdd6a8d6a9e5c758f3e` (matches
  `MANIFEST.md` row 52).
- It was the **only** blob >50 MB in the `origin/main..HEAD` range.
- It was added by a **single commit** — the pre-rewrite `e654581` (Wave 344, the 61st of the
  192 commits); 131 commits sat on top of it.
- **`origin/main` (`6036207`) contained none of the 192 commits** — verified
  (`git cat-file -e origin/main:tnnls_submission/supplementary_bundle.zip` → "exists on disk,
  but not in 'origin/main'"). The history had never been pushed, so rewriting it is a
  **local-only** operation: no force-push against shared history, no risk to other clones.

### Why a forward `git rm --cached` is insufficient

Deleting the path in a new commit leaves the blob inside the pre-rewrite `e654581` tree; GitHub
rejects any push containing the object. The blob must be purged from the 131-commit chain (or
migrated to Git LFS).

### Tooling

- `git-filter-repo` was not installed; installed via `uv tool install git-filter-repo` (2.47.0).
  (`pip install` was blocked by PEP 668 externally-managed-environment.)
- `git-lfs` was not installed.

---

## Actions taken

1. **Backup + SHA pin** — `cp` the zip to `/tmp/supplementary_bundle.zip.bak`; recorded
   `d1b5ba24…` (matches MANIFEST row 52). Restored byte-identically after the rewrite.
2. **History purge** —
   `git filter-repo --force --path tnnls_submission/supplementary_bundle.zip --invert-paths`.
   - 61 commits (below the Wave-344 commit) keep their SHAs; the 131 commits from the Wave-344
     commit upward were rewritten. The Wave-344 commit `e654581` → **`6db899b`** (same message,
     zip absent from its tree).
   - Post-rewrite scan: **no blob >50 MB anywhere in local history**.
   - filter-repo removed the `origin` remote as a safety measure; re-added
     `https://github.com/silverenternal/flowa-multistep-reinference.git` and
     `git fetch origin main` (restored `origin/main` = `6036207`; ahead count back to 192).
3. **Restore + gitignore** — restored the zip from backup (SHA `d1b5ba24…`, 154,249,954 bytes
   unchanged) and added `tnnls_submission/supplementary_bundle.zip` to `.gitignore` (with a
   comment explaining the 100 MB limit). `git check-ignore` confirms it is ignored; the file is
   untracked.
4. **Dead-URL fixes** — the archive is now distributed out-of-band, so the two
   `github.com/.../blob/main/tnnls_submission/supplementary_bundle.zip` links would 404:
   - `tnnls_submission/MANIFEST.md` row 92 → plain-text path + "Distributed out-of-band" note
     pointing at the SHA-256 ledger row.
   - `tnnls_submission/supplementary/README.md` line 201 → plain-text path + out-of-band note
     pointing at the SHA-256 below.
5. **SHA-256 ledger refresh** (TNNLS freeze — SHAs regenerated, numbers unchanged):
   - Row 39 (`supplementary/README.md`): 25990 / `01354661…` → **26031 / `d30fd61a…`** (exact).
   - Row 31 (`MANIFEST.md` self-row): 46891 / `d3f130f0…` → **55862 / `f76bb996…`** (the
     pre-edit actual, per the self-referencing-SHA convention); the audit-doc link list was
     extended with `docs/audit/push-unblock-large-blob.md`.
   - Row 52 (`supplementary_bundle.zip`): **unchanged** — `d1b5ba24…` / 154249954 (file bytes
     byte-stable; only its git-tracking status changed).

---

## Interpretation

The push failure was a **packaging** problem, not a content problem: a single 147 MB archive
exceeded GitHub's hard limit while the surrounding 191 commits were ordinary and well within
size. Because the archive's **file bytes are unchanged** (SHA `d1b5ba24…`), the MANIFEST row 52
pin — and therefore the reviewer re-verification contract (`sha256sum -c SHA256SUMS`) — remains
intact; only the delivery channel changes (out-of-band instead of a repo blob).

Purging the blob is the cleanest of the three candidate fixes (vs. Git LFS migration, vs.
leaving the archive out entirely and rebuilding it): it adds **no new dependency**, requires
**no remote configuration**, and — because the history had never been pushed — needs **no
force-push**. The 131 rewritten commits were local-only; `origin/main` was untouched throughout.

The `.gitignore` entry prevents the archive from being re-added by a future `git add -A` (the
Wave-344 packaging commit is exactly how it entered history the first time).

---

## Gaps / follow-ups

- **Archive delivery is now manual.** Reviewers obtain the bundle out-of-band (e.g. a Zenodo /
  institutional-transfer link) and verify against the MANIFEST row 52 SHA-256. If a first-class
  in-repo delivery is later required, Git LFS is the alternative — tracked in `todo/RISK-REGISTER.md`.
- **No paper number moved.** `docs/CLAIMS.md` is untouched; `tools/check_claims_consistency.py`
  returns "No drift detected".
- **Self-row lag is by design.** Row 31 displays the pre-edit actual `f76bb996…`; the post-edit
  actual `d1fc6d40…` (size 56136) is pinned here and is what reviewers should re-hash against.

---

## Verification

```bash
# 1. No oversized blob anywhere in local history
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '$1=="blob" && $3>50000000 {print $3, $4}'
# (empty)

# 2. Archive on disk is byte-stable
sha256sum tnnls_submission/supplementary_bundle.zip
# d1b5ba24a55a9336e7b65cee7bea652482943932181ddfdd6a8d6a9e5c758f3e

# 3. Archive is untracked / ignored
git check-ignore tnnls_submission/supplementary_bundle.zip   # -> path (ignored)

# 4. No dead GitHub blob URL for the archive remains
git grep -n "blob/main/tnnls_submission/supplementary_bundle.zip" -- .   # (none)

# 5. Ledger row 39 matches actual bytes
sha256sum tnnls_submission/supplementary/README.md
# d30fd61a35d6862dde0d0673405792422a4864bac27848e814ea656853b77a8c

# 6. Post-edit self-row actual (pinned here; becomes row 31's displayed value next refresh)
sha256sum tnnls_submission/MANIFEST.md
# d1fc6d40f1eb38701d80e265eae6c640be6cb8a87c290e30210c483039a700d5 (size 56136)

# 7. Claims consistency
python3 tools/check_claims_consistency.py   # No drift detected
```

---

## Files modified

- `.gitignore` — new entry `tnnls_submission/supplementary_bundle.zip` (+ comment).
- `tnnls_submission/MANIFEST.md` — row 92 URL reword; row 39 SHA/size refresh; row 31 self-row
  SHA/size refresh + audit-doc link append.
- `tnnls_submission/supplementary/README.md` — line 201 URL reword.
- `docs/audit/push-unblock-large-blob.md` — NEW audit doc (this file).

## History rewritten (local only, never pushed)

- 131 commits from the Wave-344 packaging commit upward (pre-rewrite `e654581` → `6db899b`).
- `origin/main` (`6036207`) untouched; the archive bytes on disk unchanged.
