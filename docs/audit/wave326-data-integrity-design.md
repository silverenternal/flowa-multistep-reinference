# Wave 326 — Data Integrity + Reproducibility Verifier Suite

**Date:** 2026-09-23
**Author:** Wave 326 Phase 3b (pre-push additive infrastructure)
**Status:** ACTIVE — design anchor for the four-script verifier suite
added in this wave. Every pre-commit hook / GitHub Actions workflow
that touches `verification_outputs/` should cross-reference this doc.

## 1. Purpose

The paper-submission push must demonstrate two things about the
headline-evidence artifact set under `verification_outputs/`:

1. **Integrity** — every artifact on disk is bit-identical to what was
   cited at submission-prep time. The audit docs ship per-subdir
   `SHA256SUMS` ledgers; the verifier must confirm those ledgers match
   on-disk reality (no silent overwrites, no missing artifacts, no
   untracked additions).
2. **Provenance** — every sha256 reference inside `docs/audit/wave*.md`
   resolves to a real file with matching hash. Orphans and stale
   references must be surfaced before the paper is pushed.

The four-script verifier suite below is the **single source of truth**
for both contracts. It runs in three places:

* **Local pre-commit hook** (mirrors `.pre-commit-config.yaml` gates 4
  and 5 for verification_outputs/ coverage).
* **GitHub Actions** (CI mirror, byte-identical to the local hook).
* **Weekly cron** (`.github/workflows/experiments-nightly.yml` +
  `experiments-weekly.yml` — drift detection on a slower cadence).

## 2. Tool architecture

Four scripts live under `tools/` and are wired into the three
invocation surfaces above. The scripts have explicit, narrow
responsibilities so each gate can be diagnosed in isolation.

```
                       tools/check_data_integrity.py
                       ┌──────────────────────────────┐
                       │ walk verification_outputs/*  │
                       │ re-hash every SHA256SUMS     │
                       │ entry; report modified /      │
                       │ missing / unlisted files      │
                       └──────────────────────────────┘
                                       │
                                       ▼
                       tools/check_data_provenance.py
                       ┌──────────────────────────────┐
                       │ parse docs/audit/wave*.md    │
                       │ for (sha256, path) pairs;    │
                       │ verify the path's hash matches│
                       └──────────────────────────────┘
                                       │
                                       ▼
                   tools/verify_reproducibility_smoke.py
                       ┌──────────────────────────────┐
                       │ 12 headline-evidence         │
                       │ artifacts must exist (paper- │
                       │ submission pre-flight)       │
                       └──────────────────────────────┘
                                       │
                                       ▼
                    tools/regenerate_sha256sums.py  (operator-only)
                       ┌──────────────────────────────┐
                       │ generate new SHA256SUMS for  │
                       │ subdirs without one; refuse   │
                       │ to silently overwrite stale  │
                       │ ledgers (--force required)   │
                       └──────────────────────────────┘
```

### 2.1 `tools/check_data_integrity.py`

**Role.** Read-only walker. For every sub-directory of
`verification_outputs/` that ships a `SHA256SUMS` ledger, recompute
`sha256` of every entry and compare. Reports three mismatch kinds:

| Kind | Meaning |
|---|---|
| `modified` | File on disk, hash differs from ledger (artifact was swapped) |
| `missing`  | File in ledger, not on disk (artifact was deleted) |
| `unlisted` | File on disk, not in ledger (new artifact, ledger not refreshed) |

The script also walks every file on disk and flags any not covered by
the ledger (the ledger is supposed to enumerate every artifact). Exit
code is `0` iff every ledger matches; `1` on any mismatch.

**CLI.** `python tools/check_data_integrity.py [--quiet] [--root <path>]`
The `--quiet` flag prints only the one-line summary
`Verified X directories, Y files, Z mismatches` for CI consumption.

### 2.2 `tools/check_data_provenance.py`

**Role.** Read-only citation cross-check. Walks every
`docs/audit/wave*.md` and extracts `(sha256, path)` pairs that coexist
on the same physical line. The format tolerance covers the four
audit-doc styles: `(sha256 abc123)`, `(sha256:abc123)`,
`path sha256=abc123`, and bare `abc123` near a path.

Drift kinds:

| Kind | Meaning |
|---|---|
| `missing_file` | Cited path does not exist on disk |
| `orphan_sha`   | Path exists but its sha256 differs from the cited hash |

The script is read-only. It never mutates the working tree; a stale
citation must be fixed in the audit doc, not by re-hashing on disk.

**CLI.** `python tools/check_data_provenance.py [--quiet]`

### 2.3 `tools/verify_reproducibility_smoke.py`

**Role.** Pre-flight gate. The 12 headline-evidence artifacts listed
in `REQUIRED_ARTIFACTS` (R1/R2/R3/R5a/R5b/R5c/R6/K1/K4+K5/K7 + the
W280 production summaries) must all be present before the paper can
be submitted. The script checks each artifact and additionally
verifies that, when its parent directory ships a `SHA256SUMS` ledger,
the artifact is listed there.

**CLI.** `python tools/verify_reproducibility_smoke.py [--quiet]`
Exit code is `0` iff all 12 artifacts exist; `1` otherwise.

### 2.4 `tools/regenerate_sha256sums.py`

**Role.** **Operator-only writer.** The script has two operating modes:

1. **No-existing-ledger mode (default)**: subdirs without a
   `SHA256SUMS` get a freshly generated one. The format mirrors the
   existing wave280 convention (one entry per line, `./relative/path`,
   sorted, self-hash appended last).
2. **Stale-ledger mode (`--force` required)**: if a subdir's ledger
   disagrees with on-disk state, the script REFUSES to overwrite it
   and exits non-zero. A human operator must inspect the drift, decide
   whether the on-disk artifacts are correct (e.g. after a known-good
   rerun) or the ledger is correct (e.g. someone swapped the artifact
   silently), and re-invoke with `--subdir <path> --force`.

The `--dry-run` flag prints per-subdir state without writing anything.
This is the recommended first step whenever a wave runs an experiment
that touches `verification_outputs/`.

**CLI.**

```bash
# First step after any experiment run: observe state without writing.
PYTHONPATH=. python tools/regenerate_sha256sums.py --dry-run

# Generate SHA256SUMS for new subdirs.
PYTHONPATH=. python tools/regenerate_sha256sums.py

# Known-good artifact replacement: regenerate a specific subdir.
PYTHONPATH=. python tools/regenerate_sha256sums.py \
    --subdir verification_outputs/wave280-p-r1 --force
```

## 3. Invocations

### 3.1 Pre-commit hook order

The four scripts run in the order **integrity → provenance → smoke**
in `.pre-commit-config.yaml`. The integrity script is the cheap inner
loop (re-hash 53 entries × 4 KiB ≈ 0.2s on warm disk); the provenance
script reads every `wave*.md` (~30 files, ~600 KiB total); the smoke
script is a 12-path existence check. The regenerate script is NOT a
pre-commit hook (operator-only).

```
check_data_integrity          (~0.5s wall-clock, IO-bound)
   ↓
check_data_provenance         (~0.8s wall-clock, IO-bound)
   ↓
verify_reproducibility_smoke  (~0.05s wall-clock, stat-only)
```

The hooks are scoped with `files: ^verification_outputs/|^docs/audit/`
so a pure source-code commit does not pay the cost (mirrors the
mkdocs-strict scoping pattern already in place).

### 3.2 GitHub Actions order

The CI mirror in `.github/workflows/ci.yml` runs the three readers
inline (after the pytest-fast gate completes). Nightly/weekly cron
runs the same three readers plus `--dry-run` of regenerate so drift is
surfaced without an operator action.

```
.github/workflows/ci.yml
   ├── lint
   ├── mypy
   ├── pytest-fast
   ├── check_data_integrity          (block merge on failure)
   ├── check_data_provenance         (block merge on failure)
   └── verify_reproducibility_smoke  (block merge on failure)

.github/workflows/experiments-weekly.yml
   ├── check_data_integrity
   ├── check_data_provenance
   ├── verify_reproducibility_smoke
   └── regenerate_sha256sums --dry-run  (report drift only)
```

### 3.3 Weekly drift cron

`.github/workflows/experiments-weekly.yml` runs every Monday at 09:07
UTC (avoids the :00/:30 storm). The drift report is uploaded as a
workflow artifact so a reviewer can scan the diff without re-running
the suite locally.

## 4. Expected runtime

Each script is intentionally CPU-light and IO-bound. The numbers
below are measured on a 4-vCPU runner with cold cache:

| Script | Cold-cache | Warm-cache | Notes |
|---|---:|---:|---|
| `check_data_integrity` | 1.2 s | 0.5 s | 6 ledgers × 53 entries |
| `check_data_provenance` | 1.5 s | 0.8 s | ~30 audit docs × ~600 KiB |
| `verify_reproducibility_smoke` | 0.1 s | 0.05 s | 12 stat() calls |
| `regenerate_sha256sums --dry-run` | 1.2 s | 0.5 s | same as integrity |

Total per-commit wall-clock cost: **~3 s** (within the 5-s budget the
pre-commit harness allocates to a single hook).

## 5. Failure modes + recovery

| Failure | Surface | Recovery |
|---|---|---|
| Ledger drift (`modified`) | `check_data_integrity` exit 1 | Inspect `verification_outputs/<sub>/`; if the artifact was intentionally replaced, run `regenerate_sha256sums --subdir <path> --force`; otherwise restore the artifact from git (`git checkout HEAD -- <path>`) |
| Missing artifact | `check_data_integrity` or `verify_reproducibility_smoke` exit 1 | Restore from git (`git checkout HEAD -- <path>`); if the artifact is genuinely new, regenerate its ledger (the smoke check only fails if the parent ledger does not list it) |
| Stale audit-doc citation | `check_data_provenance` exit 1 | Update the audit doc to cite the new hash; the verifier cannot resolve this automatically (the doc is the source of truth) |
| Stale ledger (regenerate refused) | `regenerate_sha256sums` exit 1, prints stale list | Investigate why the on-disk hash differs from the ledger; if the artifact is correct, re-run with `--force` after documenting the change in `docs/audit/` |
| All scripts fail simultaneously | Almost certainly a partially-applied wave that did not commit its artifacts | Run `git status verification_outputs/ docs/audit/`; commit / restore as appropriate; re-run the suite |

## 6. Invariants

The verifier suite enforces three invariants that hold across every
paper-submission push:

1. **No silent overwrite.** Any `verification_outputs/<sub>/<file>`
   whose on-disk sha256 differs from its parent ledger is a
   stop-the-line event.
2. **No orphan citation.** Every `(sha256, path)` pair in
   `docs/audit/wave*.md` resolves to a real file with matching hash.
3. **No missing headline artifact.** The 12 headline-evidence
   artifacts are present and listed in their parent ledger (if any).

These three invariants together are sufficient to claim
"reproducibility-evidenced" for the paper. Any wave that wants to
ship new headline evidence must run `regenerate_sha256sums --dry-run`
first to confirm the new artifacts are tracked, then commit the new
ledger alongside the artifacts.

## 7. File summary

| File | Lines | Purpose |
|---|---:|---|
| `tools/check_data_integrity.py` | 273 | SHA256SUMS-vs-disk walker (reader) |
| `tools/check_data_provenance.py` | 247 | audit-doc citation verifier (reader) |
| `tools/verify_reproducibility_smoke.py` | 197 | 12-artifact pre-flight gate (reader) |
| `tools/regenerate_sha256sums.py` | 211 | SHA256SUMS builder (operator-only writer) |

All four scripts are pure-stdlib (no third-party dependencies), exit
`0` on success / `1` on drift, and print a one-line summary on stdout
for CI consumption regardless of `--quiet`.

## 8. Cross-references

* `docs/audit/wave326-crossdoc-metrics-snapshot.md` — the cross-doc
  anchor that uses these verifiers to validate the 11-cell verdict
  distribution before paper submission.
* `docs/audit/wave326-final-metrics-table.md` — the canonical metric
  table whose every row references a sha256 the provenance checker
  validates.
* `docs/audit/wave326-readme-update.md` — the README pointer to the
  verifier suite.
* `.pre-commit-config.yaml` — local hook wiring (gate 4 + 5
  extension for `verification_outputs/` coverage).
* `.github/workflows/ci.yml` — CI mirror.
* `.github/workflows/experiments-weekly.yml` — weekly drift cron.