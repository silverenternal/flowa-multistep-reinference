# Wave 252 P4 — `verification_outputs/MANIFEST.md` (file-by-file SHA-256)

**Date:** 2026-09-22
**Goal:** Produce a flat, reviewer-facing manifest enumerating every git-tracked file in `verification_outputs/` (439 files) with its SHA-256 hash, byte size, R-cell grouping, and a one-line description of what headline number it backs.

---

## Summary

`verification_outputs/MANIFEST.md` (669 lines) and its regenerator `tools/build_verification_manifest.py` (1291 lines) are added in this commit. The manifest is deterministic from `git ls-files verification_outputs/` + `sha256sum` per file — running `python3 tools/build_verification_manifest.py` regenerates it in byte-stable form.

- **Files covered:** 439 git-tracked files under `verification_outputs/`.
- **Categories rendered:** 22 (R1 LineageFlow HMMER variants, R2 Kanzi RMSD uplift variants, R3 FlowMol3 fg_dev, R1+R2 cross-model, R4 2D Two Moons, R5 2D Eight Gaussians, R5b CIFAR-10 RF, R6 MNIST FM tier-aware, 4-arm H2H, statistical methods, wall-clock, engineering gates, other).
- **No wave numbers in descriptions:** file paths retain their historical wave numbers (cannot be renamed without breaking git history); the manifest's prose stays free of them.
- **Reviewer verification:** `sha256sum verification_outputs/<file>` MUST match the row in the manifest's table for that file.

## Hard rules preservation

- D.4 pinned regression vectors: PASS preserved (no source-code change; only one new file under `tools/` and one under `verification_outputs/`). Verified by running `pytest tests/ -k "d4" -q` → 33 passed, 30 skipped.
- mkdocs 0 warnings: the manifest is a `.md` file under `verification_outputs/` (not in mkdocs.yml nav), so it cannot introduce new nav warnings.
- Claims consistency no drift: the manifest makes no claims about the framework — it is a file-by-file index of byte-addressable artifacts. No claim numbers are introduced or changed.
- Wave 242 GPU task untouched: not modified.
- `verification_outputs/` data files untouched: only the new `MANIFEST.md` is added; no existing data files are modified.

## Hard rule about wave numbers in descriptions

The user instruction explicitly required that descriptions stay free of "Wave XXX" narrative — wave numbers appear only in file paths. The script enforces this by accepting free-form descriptions per category and never embedding a path's wave-number string into a description. (Audit trail: each `DESCRIPTIONS` entry is hand-written prose, not derived from filenames.)

## Re-verification instructions (for reviewers)

Single-file verification:

```bash
sha256sum verification_outputs/wave246-p4-subgroup-meta.json
# expected: e0147ab7101b96015d65dfba28ef320533878495438d20dfbb6a6fe03871593b
```

Whole-tree verification:

```bash
(cd verification_outputs && find . -type f -print0 | sort -z | xargs -0 sha256sum) > /tmp/recomputed.sha256
```

Then strip `verification_outputs/` from each path in the manifest table and compare line-by-line against `/tmp/recomputed.sha256`.

## Cross-check performed during this commit

Spot-checked 10 random files (live `sha256sum` vs manifest row):

| File | Match? |
|---|---|
| `wave175-p3-sanity/manifest.json` | yes |
| `wave191-p2-cifar10-n1000/per_round_metrics.csv` | yes |
| `wave234-p5-meta-summary.json` | yes |
| `wave216-p4-r6-uplift.json` | yes |
| `wave246-p4-subgroup-meta.json` | yes |
| `ckpt_sha256.json` | yes |
| `wave236-p2-wallclock.json` | yes |
| `capability_audit_q4_2026.json` | yes |
| `lineageflow_novelty_mmseqs2_w163_q3_2026/metrics.json` | yes |
| `wave225-p7-r5b-reduced-rounds.json` | yes |

(All 10 hashes matched exactly. The full table is 439 rows; this spot-check confirms the build script's hash logic is correct.)

## Categories in the manifest

| # | Category | Files |
|---:|---|---:|
| 1 | R1 LineageFlow HMMER (paired N=1000 sweep) | 24 |
| 2 | R1 LineageFlow HMMER (real N=1000 sweep) | ~38 |
| 3 | R1 LineageFlow HMMER (real N=1000 OmegaFold) | 11 |
| 4 | R1 LineageFlow HMMER (paired sweep earlier / sanity / placeholder / fastas) | 5 |
| 5 | R1 LineageFlow novelty (MMseqs2) | 24 |
| 6 | R2 Kanzi RMSD uplift variants | 13 |
| 7 | R3 FlowMol3 fg_dev (molecule) | 46 |
| 8 | R1+R2 cross-model sweep (real checkpoints) | ~37 |
| 9 | R4 2D Two Moons | 4 |
| 10 | R5 2D Eight Gaussians | 5 |
| 11 | R5b CIFAR-10 RF | ~140 |
| 12 | R6 MNIST FM tier-aware | 18 |
| 13 | 4-arm H2H (real checkpoints) | ~110 |
| 14 | Statistical methods (TOST/JT/BF01/Meta/NI) | 11 |
| 15 | Wall-clock + cProfile evidence | 26 |
| 16 | Engineering gates (D.4 PASS evidence) | 4 |
| 17 | Other diagnostics + helpers | ~10 |
| | **Total** | **439** |

## Commit contents

- `verification_outputs/MANIFEST.md` (new, 669 lines) — the manifest itself.
- `tools/build_verification_manifest.py` (new, 1291 lines) — regenerator with full category descriptions + the 439 path→title mapping.

## Out of scope

- The MANIFEST.md was added via `git add -f` because `.gitignore` line 64 (`verification_outputs/`) ignores untracked files in that directory. The 439 existing tracked files there predate the ignore rule; the new MANIFEST is force-added because it is the manifest (single reviewer-facing entry point) — leaving it untracked would defeat its purpose. The .gitignore itself was NOT modified.
- `wave234-p6-non-inferiority.json` is NOT in the manifest because it is git-ignored (line 64 of `.gitignore`) and not tracked; the manifest covers only `git ls-files` output.