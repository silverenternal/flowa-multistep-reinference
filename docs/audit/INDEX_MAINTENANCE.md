# `docs/audit/INDEX.md` Maintenance Pattern

**Date authored:** 2026-09-25 (Wave 358 P3, USER AUTHORIZED, NO PUSH)
**Scope:** Self-documenting the maintenance pattern that regenerates `docs/audit/INDEX.md` from the on-disk layout. The companion regen script is `/tmp/regen_index.py` (Wave 347 governance refresh). This file is intended to make the regen logic legible without reading Python.

> **Hard guardrail (preserved verbatim):** Cluster boundaries (`CLUSTERS` list in `/tmp/regen_index.py`) and the active-surface list (`ACTIVE_SURFACES` + `TNNLS_SURFACES`) are **frozen** for the duration of the v3.0-tnnls-ready submission. This doc only **documents** the pattern — it does **not** modify the regen logic or the list contents.

---

## 1. What INDEX.md actually is

`docs/audit/INDEX.md` is a **topic-cluster map** of all `docs/audit/*.md` files (394 files across 24 clusters as of 2026-09-25, Wave 347 baseline). It is **regenerated**, not hand-edited:

- Per-wave audit files live in cluster subdirectories (`docs/audit/<cluster>/waveNNN-*.md`). Wave filenames are preserved (so `git log --follow` continues to work and the per-wave audit trail is intact).
- Flat files at the top level (e.g. `docs/audit/EPSILON_DIRECTION.md`) are classified into clusters by filename + first-30-line content scan.
- Each file gets an **Active** or **Historical** flag based on whether it is cited from any reviewer-facing surface.

Reviewers answer *"what does the project claim about X?"* by reading the cluster summary for X. The per-wave table (also titled `INDEX.md` at the root of each wave) is authoritative for *"what did Wave N do?"*; this topic-cluster index is authoritative for *"what does the project claim about X?"* — they are complementary, not duplicates.

---

## 2. How a new audit file is classified into a cluster

The regen script (`/tmp/regen_index.py`) walks `docs/audit/` recursively. For every `.md` file except `INDEX.md`, it runs two passes:

### 2.1 Pass 1 — filename keyword scan (primary signal)

For each cluster `CLUSTERS[i] = (cluster_id, topic_label, mode, keyword_list)`, the script checks whether any of the cluster's keywords (lowercased) appear in the **filename** (lowercased). First match wins.

- **`mode='fname'`** clusters (per-model clusters like `cifar`, `kanzi`, `flowmol3`, `lineageflow`, `freqflow`, `mnist`, `brai`, `2d_toy`, `self_flow`, `hidream`, `graphbfn`, `lumina`, `protbfn_abbfn`, `wan2_2`) use **filename-only** matching. The cluster's `keyword_list` is short (3-7 entries) and model-specific (e.g. `kanzi` → `['kanzi']`). A file lands in `kanzi` only if its filename contains `kanzi`.
- **`mode='any'`** clusters (activity clusters like `engineering`, `reproducibility`, `data_packaging`, `push_state`, `algorithm_4arm`, `sweep_eval`, `stats_method`, `paper_claims`, `final_verify`, `governance`, `web_research`) use filename OR content matching.

### 2.2 Pass 2 — content keyword scan (fallback)

If Pass 1 finds no match, the script reads the first 40 lines of the file and re-runs the keyword check against `text_lc = (filename + '\n' + first_40_lines).lower()`. This pass is run **only for `mode='any'` clusters** (`fname`-mode clusters are excluded to avoid cross-contamination between model clusters). First match wins.

### 2.3 Fallback cluster

If neither pass matches, the file is assigned to **`governance`** (the catch-all cluster).

### 2.4 Practical guidance for adding a new audit file

- **Preferred placement:** `docs/audit/<cluster>/waveNNN-<topic>.md`. Choose the cluster whose `keyword_list` most clearly matches the file's filename. Examples:
  - `wave358-cifar-sweep-result.md` → `cifar/`
  - `wave358-ruff-cleanup.md` → `engineering/` (filename contains `ruff`)
  - `wave358-r5b-fix.md` → `stats_method/` (filename contains `r5b`)
  - `wave358-final-verify.md` → `final_verify/` (filename contains `final-verify`)
- **If the filename is generic** (e.g. `wave358-summary.md`), inspect the first 40 lines — content keywords are the fallback. A summary of an R-level fix will land in `stats_method` because `r5b` or `r6` likely appears in the body.
- **If the file lands in the wrong cluster** (filename keyword was ambiguous), rename the file to include a more specific keyword. This is preferred over hand-editing `INDEX.md` because the regen script will be re-run on the next governance wave and the hand-edits would be lost.

---

## 3. How Active vs Historical is determined

The regen script maintains a single **`cited` set** built by reading every active surface file:

```python
ACTIVE_SURFACES = [22 reviewer-facing docs under docs/]
TNNLS_SURFACES  = [8 files under tnnls_submission/]
all_surfaces    = ACTIVE_SURFACES + TNNLS_SURFACES
```

For each surface that exists on disk, the script reads it and extracts every regex match of `audit/([A-Za-z0-9_.\-/]+\.md)`. Both relative paths (`audit/<cluster>/file.md`) and bare basenames (`file.md` — flat files at the top level) are accepted.

For each audit file, the active flag is set as:

```python
is_active = (rel in cited) or (os.path.basename(rel) in cited)
```

A file is **Active** iff it is referenced (by relative or bare basename) from **at least one** reviewer-facing surface or any `tnnls_submission/*.md`. A file is **Historical** otherwise — preserved for the per-wave audit trail but skipped on first read.

### 3.1 What counts as a reviewer-facing surface

`ACTIVE_SURFACES` (22 paths) are the docs an external reviewer opens first. As of Wave 347 this includes `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `docs/METRIC_LEDGER.md`, `docs/INSIGHTS.md`, `docs/ARCHITECTURE.md`, `docs/README.md`, `docs/paper-draft.md`, `docs/cover-letter-tnnls.md`, `docs/push-ready-summary.md`, plus 13 other Tier-1 reviewer-facing docs (full list at line 20-43 of `/tmp/regen_index.py`).

`TNNLS_SURFACES` (8 paths) are the files in `tnnls_submission/` — the TNNLS submission package. They cite audit docs that document the reproducibility / data-availability / figure-generation claims.

**Hard guardrail:** The contents of `ACTIVE_SURFACES` and `TNNLS_SURFACES` are **frozen** for the duration of the v3.0-tnnls-ready submission. Adding a new reviewer-facing doc does NOT require editing this list — if a new top-level doc emerges, it is added in a follow-up wave and `ACTIVE_SURFACES` is updated then.

---

## 4. How to re-run the regen script

The regen script is at `/tmp/regen_index.py`. It is not committed to the repo (it lives in `/tmp/`) and is regenerated by hand for each governance wave. Re-run protocol:

```bash
# 1. Activate the flowmol3_venv (or any venv with stdlib; no third-party deps)
source .venvs/flowmol3_venv/bin/activate

# 2. Dry-run: print cluster sizes without writing
python3 /tmp/regen_index.py

# 3. Confirm the dry-run counts match expectations
#    - Total files: 394 (Wave 347 baseline)
#    - Active + Historical = Total
#    - No new clusters (cluster_order unchanged)

# 4. The script writes docs/audit/INDEX.md in-place. Diff against HEAD:
git diff --stat docs/audit/INDEX.md

# 5. If the diff is plausible, commit (NO-PUSH per Wave 325):
git add docs/audit/INDEX.md
git commit -m "Wave NNN: docs/audit/INDEX.md regenerated by /tmp/regen_index.py (USER AUTHORIZED, NO PUSH)"
```

The script writes `docs/audit/INDEX.md` atomically (single `fh.write(content)` call at line 475). There is no partial-state risk; if the script crashes mid-run, the file is left at its previous contents.

---

## 5. Edge cases and constraints

- **Cluster order is preserved.** The `cluster_order` list at line 361 of the regen script matches `CLUSTERS` declaration order at line 60. Reordering `CLUSTERS` would shift all cluster entries in `INDEX.md` — do not reorder unless intentionally re-organizing the audit surface.
- **Empty clusters are skipped.** Clusters with zero files (`brai`, `self_flow`, `hidream`, `graphbfn`, `lumina`, `protbfn_abbfn`, `wan2_2`, `web_research`) still appear in the cluster-map table at the top of `INDEX.md` but are skipped in the per-cluster detail section. This is by design — the cluster map preserves the slot so a future audit doc can fill it without re-shuffling the table.
- **Flat files at the top level are sorted under their cluster** but listed with their basename (the leading `<cluster>/` is stripped by `short = f.split('/', 1)[1]` at line 449). Example: `docs/audit/algorithm_4arm/algorithm-gap-investigation.md` is listed as `algorithm-gap-investigation.md` under the `algorithm_4arm` cluster.
- **Subdir files are sorted with cluster-prefix files last** by the key `(not x.startswith(c + '/'), x)` at line 434. This puts the canonical cluster-prefixed files (e.g. `cifar/cifar-reference-availability.md`) before flat-name files (e.g. `cifar/wave280-p-cifar-sweep-result.md`).
- **The regen script does not check git state.** It writes whatever is on disk. Running it with uncommitted audit files will produce a diff that includes both the new files AND the regenerated INDEX.

---

## 6. What this doc does NOT do

- **Does not modify the regen script.** `/tmp/regen_index.py` is the source of truth. This doc only describes its behavior.
- **Does not modify cluster boundaries.** `CLUSTERS` list (24 entries) is frozen.
- **Does not modify ACTIVE_SURFACES or TNNLS_SURFACES.** Both lists are frozen for the v3.0-tnnls-ready submission.
- **Does not introduce a new cluster.** Adding a new cluster would require modifying `CLUSTERS` in the regen script, which is out of scope for Wave 358 P3.

---

## 7. Observed facts (Wave 358 P3)

- The INDEX.md total file count at Wave 347 governance refresh is 394 (active: 258, historical: 136).
- The INDEX.md total cluster count is 24 (16 per-model + 8 activity).
- The ACTIVE_SURFACES list has 22 entries (21 under `docs/` + `docs/push-ready-summary.md`).
- The TNNLS_SURFACES list has 8 entries (8 under `tnnls_submission/`).
- The regen script is at `/tmp/regen_index.py` (not in the repo).
- This maintenance doc (`docs/audit/INDEX_MAINTENANCE.md`) is the first non-INDEX top-level file added to `docs/audit/` since the Wave 347 baseline. It will be classified as `governance` by the next regen run (cluster fallback), which is acceptable — it is a governance doc about the index itself.

---

## 8. Interpretation

The audit INDEX is now **self-documenting**: a reviewer reading `docs/audit/INDEX.md` can read this file to understand how the index was generated, what the Active/Historical flags mean, and how to add a new audit file. The previous state (regen logic only in `/tmp/regen_index.py` + a 4-line "Maintenance" section at the bottom of `INDEX.md`) was opaque to anyone who hadn't seen the regen script. This file closes that gap.

The 4-line "Maintenance" section at the bottom of `INDEX.md` remains (it points to `/tmp/regen_index.py`); this doc expands on it and lives as a separate file so it can be deep-linked, grep'd, and evolved independently.

---

## 9. Unresolved gaps (none blocking)

- The regen script lives at `/tmp/regen_index.py` (outside the repo). A future wave could commit it under `tools/` for reproducibility — but that is a follow-up governance decision and is not Wave 358 P3 scope.
- The ACTIVE_SURFACES / TNNLS_SURFACES lists are frozen for the v3.0-tnnls-ready submission. A future governance refresh (post-submission) may revisit these lists and reduce them (e.g. drop `paper-final-neurips.md` after submission).

---

_Wave 358 P3 — additive maintenance-pattern documentation. No destructive edits. NO-PUSH policy preserved. Cluster boundaries and ACTIVE_SURFACES list unchanged._