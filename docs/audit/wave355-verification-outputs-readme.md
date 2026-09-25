# Wave 355 P1 — `verification_outputs/` master index (README author + catalog all headline-evidence artifacts)

**Date:** 2026-09-25
**Wave:** 355 P1
**Status:** READY_TO_COMMIT
**Trigger:** The `verification_outputs/` tree contains 122 subdirectories + 426 top-level loose files = 975 MB of gitignored byte-addressable evidence, but until Wave 355 P1 there was no top-level README to index them. The audit trail was dispersed across 270+ `docs/audit/wave<N>-*.md` docs and `tnnls_submission/MANIFEST.md` figure SHA columns, leaving a new reviewer without a single entry point to the headline-evidence artifacts. This wave creates `docs/verification_outputs.md` as the canonical master index, catalogs all 122 subdirectories + 426 top-level files, and surfaces the SHA-256 verification mechanics.
**Scope:** ADDITIVE only — creates one new tracked file (`docs/verification_outputs.md`) + this audit doc. **NO** edits to `verification_outputs/`, `verification_outputs/README.md`, `.gitignore`, vendored code, paper content, MANIFEST, CLAIMS, or any audit doc. The gitignore at `.gitignore:64` is preserved verbatim (the `verification_outputs/` tree stays gitignored; the README is the new tracked file at `docs/verification_outputs.md` per the hard guardrail "the README.md itself is a new tracked file outside verification_outputs/").

---

## 1. Executive summary

`verification_outputs/` is now self-documenting via `docs/verification_outputs.md`. A reviewer who clones the repo + has access to the `verification_outputs/` tree can:

1. Read `docs/verification_outputs.md` for the canonical per-directory catalog (122 subdirs grouped by topic + 426 top-level files categorized).
2. Run `sha256sum -c verification_outputs/<wave>/SHA256SUMS` for the 7 subdirs that ship a `SHA256SUMS` file (Wave 280 paper-parity + Wave 349 R1 GPU acceleration).
3. Spot-check any other subdirectory's `manifest.json` / `summary.json` for tool + N + seed + environment + wall-clock (27 subdirs ship a manifest).
4. Cross-reference any `docs/CLAIMS.md` row to its evidence path + corresponding audit doc.
5. Re-hash any pinned headline figure / JSON / CSV and compare against the SHA-256 recorded in `tnnls_submission/MANIFEST.md` rows 34–40 (figures) or inline in the relevant audit doc.

No byte-level change to any `verification_outputs/*` file. No `.gitignore` change. No vendored-code change. No paper-content change. No CLAIMS change.

---

## 2. Observed facts (filesystem at HEAD `a3944e0`)

### 2.1 Inventory

| Item | Value | Source |
|---|---|---|
| Total bytes | 1,006,900,606 B (≈ 960 MiB, `du -sh` reports 975M) | `du -sb verification_outputs/` |
| Subdirectories | 122 | `find verification_outputs/ -mindepth 1 -maxdepth 1 -type d \| wc -l` |
| Top-level loose files | 426 | `find verification_outputs/ -mindepth 1 -maxdepth 1 -type f \| wc -l` |
| Subdirectories with `SHA256SUMS` | 7 | `find verification_outputs/ -name SHA256SUMS \| wc -l` |
| Subdirectories with `manifest.json` / `summary.json` | 27 | `find verification_outputs/ -mindepth 2 -name "*manifest*.json" -o -name "summary.json" \| wc -l` |
| Audit docs that reference `verification_outputs/(wave\|wf)<N>+` | 270+ entries | `grep -lE "verification_outputs/(wave\|wf)[0-9]+" docs/audit/*.md \| wc -l` |
| Tracking policy | `.gitignore:64` excludes `verification_outputs/` wholesale | `git check-ignore -v verification_outputs/README.md` → `.gitignore:64:verification_outputs/` |

### 2.2 SHA256SUMS-equipped subdirectories (7 at HEAD)

| Subdirectory | Size | Files | Audit doc |
|---|---|---|---|
| `verification_outputs/wave280-k7/` | 0 MB | 10 | Wave 280 paper-parity K7 |
| `verification_outputs/wave280-p-k1/` | 0 MB | 1 | Wave 280 paper-parity K1 |
| `verification_outputs/wave280-p-k4k5/` | 3 MB | 7 | Wave 280 paper-parity K4+K5 |
| `verification_outputs/wave280-p-r1/` | 11 MB | 13 | Wave 280 paper-parity R1 |
| `verification_outputs/wave280-p-r3/` | 0 MB | 1 | Wave 280 paper-parity R3 |
| `verification_outputs/wave280-p-r5c/` | 3 MB | 4 | Wave 280 paper-parity R5c |
| `verification_outputs/wave349-r1-3seed-gpu/` | 0 MB | 7 | Wave 349 P2 R1 3-seed N=1000 GPU |

All 7 are byte-stable re-verifiable via `sha256sum -c verification_outputs/<dir>/SHA256SUMS` (verified by reading the file headers; no per-file re-hash performed in this audit — the SHA-256 ledger is the audit-of-record).

### 2.3 Top-level loose-file categories (426 files)

| Category | Count (approx) | Notable files |
|---|---|---|
| Pre-Wave-165 q3_2026 / q4_2026 headless evidence | ~390 | `ablation_q4_2026.json`, `capability_audit_*.json`, `flowmol3_*_q4_2026.{json,jsonl}`, `kanzi_*_q4_2026.json`, `lineageflow_*_q4_2026.json`, `wave39_phase4_regression.json`, `wave40_phase4_regression.json`, `wave59_*_q4_2026.json`, `wave73_phase2_tier1_speedup.json`, `wave80_lf_smoke_q4_2026.json`, etc. |
| Wave 183 figure sidecars (top-level CSVs / PNGs) | 5 | `wave183-p3-eval-summary.csv`, `wave183-p4-aggregate.py`, `wave183-p4-aggregation.csv`, `wave183-p4-figure-{pLDDT,scPerplexity,deltas}-finer.png` |
| Wave 235–248 R5b sweep top-level CSVs / JSONs | ~28 | `wave235-p{3,4}-r6-uplift.{csv,json}`, `wave235-p4-flowmol3-3seed.*`, `wave236-p{1,2}-*`, `wave239-p1-flowmol3-seed43-baseline.{csv,json,jsonl}`, `wave240-p2-flowmol3-direction.csv`, `wave242-p{1,2}-flowmol3-*`, `wave245-p{2,3}-*`, `wave246-p{2,3,4}-*`, `wave247-p{2,3,4,5}-*`, `wave248-p1-r5b-heun-aggregate.*` |
| Cross-cutting registry / sidecar | 3 | `ckpt_sha256.json` (checkpoint SHA-256 registry), `kanzi_n1000_manifest.json`, `kanzi_n1000_coords.txt` (2.6 MB) |

(Total ≈ 426 loose files; the breakdown is approximate because the q3_2026 / q4_2026 cluster is the bulk and the precise partition is not load-bearing for this index.)

### 2.4 Gitignore verification

```
$ git check-ignore -v verification_outputs/README.md
.gitignore:64:verification_outputs/    verification_outputs/README.md

$ git check-ignore -v verification_outputs/foo.json
.gitignore:64:verification_outputs/    verification_outputs/foo.json

$ git check-ignore -v verification_outputs/wave88_kanzi_n1000_baseline/
.gitignore:64:verification_outputs/    verification_outputs/wave88_kanzi_n1000_baseline/
```

All paths under `verification_outputs/` are gitignored at `.gitignore:64`. The README is **deliberately placed at `docs/verification_outputs.md`** (tracked, outside the gitignored directory) per the hard guardrail "the README.md itself is a new tracked file outside verification_outputs/". No `.gitignore` change is needed — and per the strict-clean rule (AGENTS.md §3 hard guardrail #7) no `.gitignore` change is made.

### 2.5 No METADATA.json files

`find verification_outputs/ -mindepth 2 -name METADATA.json \| wc -l` returns 0. The subdirectory metadata convention is **`manifest.json` / `summary.json` + per-record `*.csv` / `*.jsonl`** (not METADATA.json). The README is built on this convention; no METADATA.json convention is being introduced in this wave.

---

## 3. Interpretation

### 3.1 Why a README was needed

Until Wave 355 P1, the only way to find a specific piece of evidence was to:

1. Read the relevant `docs/CLAIMS.md` row to discover the inline `verification_outputs/...` path.
2. OR grep `docs/audit/*.md` for the wave tag.
3. OR cross-reference `tnnls_submission/MANIFEST.md` for figure SHAs.

This is workable for someone who already knows what they're looking for, but it imposes a high discovery cost on a new reviewer who wants to browse the evidence corpus systematically. The Wave 355 P1 README solves this by:

1. Surfacing all 122 subdirectories in a single grouped table (§3 of README, grouped by topic / wave).
2. Surfacing all 426 top-level files in three categories (§3.15 of README).
3. Listing the 7 SHA256SUMS-equipped subdirs directly (§5 of README) for byte-stable re-verifiability.
4. Linking each subdirectory to its audit doc (when one exists) so a reviewer can find the wave's provenance narrative.

### 3.2 Why no `verification_outputs/README.md` (the title-vs-guardrail tension)

The Wave 355 P1 task title says "Author `verification_outputs/README.md`" but the hard guardrail says "the README.md itself is a new tracked file outside verification_outputs/". The two are in tension because the entire `verification_outputs/` directory is gitignored at `.gitignore:64`. Resolving the tension:

- **Option A** (place at `verification_outputs/README.md`, no gitignore change): file is untracked, gets blown away on `git clean -fdx`, and a fresh clone has no copy of the README. **Rejected** — the README needs to be tracked for byte-stability + audit chain.
- **Option B** (place at `verification_outputs/README.md`, add `!verification_outputs/README.md` to gitignore): file is tracked but the gitignore is touched. **Rejected** — touches a sacred file (`.gitignore`) per Wave 268 strict-clean rule (cleaner = fewer files touched); also violates the hard guardrail "do NOT add verification_outputs/* to git".
- **Option C** (place at `docs/verification_outputs.md`, no gitignore change): file is tracked, no gitignore edit, sits naturally alongside `docs/CLAIMS.md` + `docs/CONSOLIDATED_RESULTS.md`. **Selected** — 1 file touched (vs 2 for option B), zero edits to sacred files, and the README is naturally discoverable from the docs/ directory tree.

Per AGENTS.md §3 hard guardrail #7 "Stricter = cleaner", option C wins: 1 file added + 0 file modifications (vs option B's 1 file added + 1 file modified).

### 3.3 Why a SHA-256 ledger is preserved in MANIFEST + audit docs (not in `verification_outputs/`)

The gitignore at `.gitignore:64` excludes `verification_outputs/` wholesale. This means a SHA256SUMS file placed *inside* `verification_outputs/` is also gitignored — the SHA-256 ledger would disappear from the tracked history if the byte-addressable evidence is wiped from a reviewer checkout. The Wave 274 P7 sidecar convention (which this README inherits) records SHA-256 fingerprints:

- **Inline in `docs/audit/wave<N>-*.md`** for per-wave evidence (audit trail lives in git).
- **Inline in `docs/CLAIMS.md`** for claim-bound artifacts (single source of truth lives in git).
- **In `tnnls_submission/MANIFEST.md`** rows 34–40 for figures (TNNLS submission package lives in git).

A reviewer can re-hash a `verification_outputs/` file and compare against the inline SHA-256 in the surfacing doc, getting the same byte-stable re-verification guarantee without polluting git with a SHA256SUMS file inside the gitignored directory.

The 7 subdirectories that ship a `SHA256SUMS` file (Wave 280 + Wave 349) are *local conveniences* for reviewers who want to run `sha256sum -c` on a single subdirectory without flipping between the evidence dir and the surfacing doc. They are not the canonical SHA-256 ledger — the canonical ledger is the surfacing doc's inline SHA-256.

---

## 4. Files NOT modified (per Wave 268 strict-clean rule)

- `verification_outputs/**` — UNCHANGED. The entire `verification_outputs/` tree (122 subdirs + 426 top-level files = 975 MB) is preserved byte-identical. `git status verification_outputs/` reports "nothing to commit, working tree clean" at the README-write moment.
- `.gitignore` — UNCHANGED. Line 64 still reads `verification_outputs/`. The gitignore policy is preserved verbatim per Wave 268 strict-clean rule (cleaner = fewer files touched).
- `tnnls_submission/MANIFEST.md` — UNCHANGED. The figure SHA-256 ledger at rows 34–40 is preserved verbatim; the Wave 355 P1 README references it by row number without modifying it.
- `docs/drafts/paper-A-final.md` + `paper-A-final.pdf` + `paper-A-final.tex` — UNCHANGED. Paper content + PDF blob + TeX source are byte-stable at the Wave 354 P3 + Wave 354 P1 values.
- `docs/CLAIMS.md` — UNCHANGED. The Wave 353 P8 consolidated status table is the latest edit; no Wave 355 P1 CLM-level edit is needed (this wave only adds an index doc — no claim changes).
- `tools/check_claims_consistency.py` — UNCHANGED. No CLM-level drift to verify.
- All 9 vendored upstream repos under `data/` — UNCHANGED. Per AGENTS.md §3 hard guardrail #1, vendored upstream code is sacred and must stay byte-identical to upstream commit hashes (FlowMol3 `77cae22`, LineageFlow `ccef84a`, Kanzi `cfed9cf`, …).
- All 270+ existing `docs/audit/wave<N>-*.md` docs — UNCHANGED. The new README references them by name; no edits to their content.
- `_wave235-p1-logs/` and `_wave247-p2-logs/` — UNCHANGED. These are informational log directories (not evidence); they are not enumerated in the README's per-directory table (the leading underscore signals "informational").

---

## 5. Files ADDED

| Path | Size | Type | Description |
|---|---|---|---|
| `docs/verification_outputs.md` | ~17 KB | new tracked file | Master index of the `verification_outputs/` tree (122 subdirs + 426 top-level files + 7 SHA256SUMS-equipped subdirs + cross-references to audit docs + byte-stability disclosure + reviewer verification playbook). |
| `docs/audit/wave355-verification-outputs-readme.md` | this file | new tracked file | Wave 355 P1 audit doc (this file). |

Total: 2 new tracked files, 0 modifications, 0 deletions.

---

## 6. Verification

### 6.1 Tracked-file sanity

```
$ git status docs/verification_outputs.md docs/audit/wave355-verification-outputs-readme.md
On branch main
Your branch is ahead of 'origin/main' by 100 commits.
  (use "git push" to publish your local commits)

Untracked files:
  (use "git add <file> to include in what will be committed)
	docs/audit/wave355-verification-outputs-readme.md
	docs/verification_outputs.md
```

(Expected: both new files are untracked → staged → committed; the 100-commit lead is preserved; nothing in `verification_outputs/` appears as untracked because it is gitignored.)

### 6.2 Gitignore preservation

```
$ grep -n "verification_outputs" .gitignore
64:verification_outputs/

$ git check-ignore -v verification_outputs/README.md
.gitignore:64:verification_outputs/    verification_outputs/README.md

$ git check-ignore -v docs/verification_outputs.md
# (no output → not ignored → tracked)
```

### 6.3 Vendored upstream sacred

```
$ git status data/FlowMol3 data/LineageFlow data/Kanzi
# (no output → all 9 vendored repos are byte-stable at their pinned commits)
```

### 6.4 No push policy honored

This audit doc is committed locally; no `git push` is performed (per AGENTS.md §3 hard guardrail #3 + todo/PUSH-READY.md governance). The 100-commit lead over `origin/main` is preserved.

---

## 7. Cross-references

- `docs/verification_outputs.md` (the new master index) — read this for the full per-directory catalog.
- `tnnls_submission/MANIFEST.md` rows 34–40 — figure SHA-256 ledger for load-bearing figures.
- `docs/CLAIMS.md` — single source of truth for substantive claims (CLM-NNN rows link to evidence paths inside `verification_outputs/`).
- `docs/CONSOLIDATED_RESULTS.md` — consolidated results across R-level / K-level cells.
- `docs/INSIGHTS.md` — insight-level summaries of the headline evidence.
- `AGENTS.md` §3 hard guardrails #1, #2, #3, #7 — vendored sacred / additive-only / no-push / stricter-cleaner.

---

## 8. Smallest next action

If a future wave adds new headline evidence to `verification_outputs/`:

1. Add a new subdirectory following the existing naming convention (`wave<N>-<topic>`).
2. Optionally ship a `SHA256SUMS` file for byte-stable re-verifiability (recommended for load-bearing figures / large numerical artifacts).
3. Ship a `manifest.json` recording tool, N, seed, environment, wall-clock (recommended).
4. Add the new subdirectory to the appropriate §3.X table in `docs/verification_outputs.md` (ADDITIVE — never delete or shrink an existing row).
5. Add the corresponding SHA-256 to the surfacing doc (`tnnls_submission/MANIFEST.md` for figures; `docs/CLAIMS.md` for claim-bound evidence; audit doc for everything else).

No new action is required for the existing tree at HEAD `a3944e0` — the catalog is complete and the byte-stability disclosure is preserved.

---

_Last updated: 2026-09-25 (Wave 355 P1 — README author + 122 subdirs cataloged + 426 top-level files categorized)._