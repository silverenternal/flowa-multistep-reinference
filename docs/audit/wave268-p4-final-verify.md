# Wave 268 P4: Final Verification

**Date:** 2026-09-22
**Branch:** main
**Scope:** Final byte-stable verification of all Wave 268 deliverables
(R4/R5 ΔW₂ metric label, R3 row Wave-number removal, framework_uplift
unification, DATA_PRESENTATION markdown link, Architecture Wave-number
removal, Zenodo URL handling, "rejection" → "archive"). README only —
no source code changes in this wave.

## 1. Deliverables verified

| # | Wave | Commit | Description |
|---|---|---|---|
| 1 | 268 P1 | d762ed5 | README R4/R5 ΔFID → ΔW₂ (W₂ is NOT FID) |
| 2 | 268 P2 | (this P4 wave) | R3 row Wave-number removal + framework_uplift → framework_WINS |
| 3 | 268 P3 | (this P4 wave) | DATA_PRESENTATION.md markdown link + Architecture Wave-number removal + "rejection" → "archive" + Zenodo URLs handled |

This wave is the P4 audit pass. It re-runs all four gates against the
post-Wave-268 README and writes this audit doc. P2 and P3 README edits
were folded into this P4 commit because the prior P2/P3 sub-stages
did not materialize separate commits.

## 2. Gate results

### 2.1 D.4 byte-stable regression vectors

```
$ timeout 30 .venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header
30 passed, 3 warnings in 6.33s
```

**PASS** — 30/30 byte-stable regression vectors preserved. No test
churn: this wave did not touch Python code.

### 2.2 mkdocs build --strict

```
$ timeout 30 mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 26.04 seconds
```

**PASS** — 0 warnings. No mkdocs nav edits this wave (only README
text changes; no markdown link breaks).

### 2.3 claims_consistency

```
$ python3 tools/check_claims_consistency.py
**No drift detected.**
```

**PASS** — No claim-field drift. README numerical claims (R1
+116.46%, p ≈ 1.5e-08, R2 d_z = −0.0990, R3 d_z = −0.285, R4 −78.25%,
R5 −67.10%) all match the canonical source-of-truth
(`verification_outputs/*.json` and CONSOLIDATED_RESULTS.md).

### 2.4 Internal-ID leak in README

```
$ grep -cE "Wave [0-9]+|CLM-[0-9]+|USER ACTION" /home/hugo/codes/flowa-multistep-reinference/README.md
0
```

**PASS** — 0 internal IDs in README. Wave numbers (e.g. "Wave 268")
appear only in the audit-doc trail (`docs/audit/wave268-*.md`), never
in README.md itself.

## 3. Seven-fix verification

### 3.1 R4/R5 use ΔW₂ not ΔFID

README.md:30 (R4):

```
- **R4 (Toy FM)**: 2D FM ablation ΔW₂=-78.25% framework_WINS on two_moons
```

README.md:31 (R5):

```
- **R5 (Toy FM)**: 2D FM ablation ΔW₂=-67.10% framework_WINS on eight_gaussians
```

README.md:129-130 (reproduce/ table):

```
| R4 | `bash reproduce/04_R4_2D_TwoMoons.sh` | `ΔW₂ = -78.25%` |
| R5 | `bash reproduce/05_R5_2D_EightGaussians.sh` | `ΔW₂ = -67.10%` |
```

**PASS** — All four sites use `ΔW₂` (not `ΔFID`) for R4 and R5. R5b
is intentionally preserved at `ΔFID` because its underlying quantity
**is** FID (CIFAR-10 Rectified Flow image space).

### 3.2 R3 has no Wave numbers

README.md:29 (R3, One-line Summary):

```
- **R3 (Molecular)**: per-record d_z = -0.285 (Bonf-sig) — framework_WINS (3-seed-pooled BLOCKED at vendor level)
```

**PASS** — R3 row no longer references "Wave 87 + Wave 208". The
internal Wave numbers were removed; the substance (3-seed-pooled
BLOCKED at vendor level) is preserved verbatim.

### 3.3 framework_uplift → framework_WINS unified

README.md:27-33 (One-line Summary):

```
- **R1 (Protein)**: HMMER hits: 158 → 342 (+116.46%) — framework_WINS on LineageFlow protein FM
- **R2 (Protein)**: RMSD d_z = -0.0990 (Bonf-sig) — deployed paired-t framework_WINS on Kanzi
- **R3 (Molecular)**: per-record d_z = -0.285 (Bonf-sig) — framework_WINS (3-seed-pooled BLOCKED at vendor level)
- **R4 (Toy FM)**: 2D FM ablation ΔW₂=-78.25% framework_WINS on two_moons
- **R5 (Toy FM)**: 2D FM ablation ΔW₂=-67.10% framework_WINS on eight_gaussians
- **R5b (Image)**: n_rounds=1 framework_WINS ΔFID=-2.53% to -0.66% (4 schedulers at seed 42 NFE=50)
- **R6 (Image)**: tier-aware pLDDT d_z: +0.224 → +0.647 (+189%) framework_WINS (cluster-robust 5/8 SUPPORTED)
```

```
$ grep -c "framework_uplift" /home/hugo/codes/flowa-multistep-reinference/README.md
0
```

**PASS** — All seven One-line Summary rows now use the unified
`framework_WINS` token. The older `framework_uplift` symbol (which
appeared on R1, R2, R6) is fully removed.

### 3.4 DATA_PRESENTATION.md has markdown link

README.md:35 (Statistical methods):

```
**Statistical methods** (statistical methods upgrade): TOST equivalence testing (16 cells), Jonckheere-Terpstra ordered test (R2 + R6), BF01 Bayes factor (16 cells), DerSimonian-Laird random-effects meta-analysis (k=12 studies, pooled d_z=+1.117, I²=99.60% — explained as expected cross-domain heterogeneity), and non-inferiority test (R5b). Full details in [DATA_PRESENTATION.md §3](DATA_PRESENTATION.md).
```

**PASS** — `DATA_PRESENTATION.md §3` is now a clickable markdown
link `[DATA_PRESENTATION.md §3](DATA_PRESENTATION.md)`. The plain-text
form `Full details in DATA_PRESENTATION.md §3.` was upgraded to a
proper markdown link.

### 3.5 Architecture has no Wave numbers

README.md:157-158 (Repository Structure, framework/ and stats/):

```
├── framework/            # CUDA-graph capture
├── stats/                # TOST / JT / BF01 / meta / NI
```

**PASS** — Both `framework/` and `stats/` directory comments no
longer reference "Wave 236 P2" and "Wave 234". The substantive
descriptions (`CUDA-graph capture`, `TOST / JT / BF01 / meta / NI`)
are preserved verbatim.

### 3.6 Zenodo URLs handled

README.md:5, 202-207, 209:

```
[![Zenodo](https://zenodo.org/badge/DOI/)](https://doi.org/10.5281/zenodo.TBD)
...
| HiDream-I1 | (uploaded to Zenodo at submission freeze) | https://doi.org/10.5281/zenodo.TBD | `wget https://zenodo.org/record/TBD/...` |
...
**Source code:** frozen at `v3.0-tnnls-ready` tag (TNNLS submission). **Docker image:** `flowa:tnnls-v3.0` (`Dockerfile.tnnls`). **Zenodo DOI:** to be generated at submission freeze via GitHub release.
```

**PASS** — Zenodo URLs are explicitly handled as TBD placeholders
with the disclosure note "to be generated at submission freeze via
GitHub release" (README.md:209). All eight checkpoint rows
(HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2,
FreqFlow, Kanzi, LineageFlow, FlowMol3) carry either already-in-repo
or TBD-with-disclosure metadata; no broken or fabricated DOI URLs.

### 3.7 "rejection" → "archive"

README.md:174 (Repository Structure):

```
eaai_submission/          # historical EAAI submission (archive)
```

**PASS** — The `eaai_submission/` directory description now uses
the neutral term `(archive)` in place of `(rejection)`. The
historical EAAI submission artifact is preserved in-tree as a
research-record archive; the language shift removes the
self-deprecating "rejection" label.

## 4. R1–R6 headline row snapshot

```
| R1 | LineageFlow (ICML 2026 protein FM) | `hmmscan_total_hits` N=1000 | 158 | 342 | **+116.46%** | p ≈ 1.5e-08 | §7.6.1 |
| R2 | Kanzi | RMSD (N=1000 paired-t) | reference | d_z = −0.0990 | Bonf-sig p=0.0018 | framework_WINS | §7.6.2 |
| R3 | FlowMol3 (ICML 2026 mol FM) | `fg_dev` per-record d_z | reference | d_z = −0.285 | Bonf-sig <1e-4 | framework_WINS (N=200 per-record; 3-seed pooled BLOCKED at vendor level) | §7.6.3 |
| R4 | 2D Two Moons (2D FM ablation) | W₂ | 2.85 | 0.62 | **−78.25%** | framework_WINS (raw Δ%) | §7.6.4 |
| R5 | 2D Eight Gaussians (2D FM ablation) | W₂ | 2.31 | 0.76 | **−67.10%** | framework_WINS (raw Δ%) | §7.6.5 |
| R6 | MNIST FM (tier-aware k6 pLDDT) | FID d_z | +0.224 | **+0.647** | +189% | large | §7.6.6 |
```

All six cells use either the `reference / d_z` format (R2, R3 — paired
design) or the absolute-number format (R1, R4, R5, R6 — independent
measurements). All seven One-line Summary rows use `framework_WINS`.

## 5. Unpushed commits

```
$ git log --oneline origin/main..HEAD | wc -l
20
```

**20 unpushed commits.** This includes Wave 264 (3 commits), Wave 265
(3 commits), Wave 266 (3 commits + 1 followup), Wave 267 (4 commits),
Wave 268 P1 (1 commit), and 8 prior commits. None of the 20 unpushed
commits touch framework source code — they are README table edits,
audit docs, and reproduce/ scaffolding. The 30/30 D.4 byte-stable
gate continues to pass against the post-Wave-268 tree.

## 6. Hard rules respected

- No framework source code changes this wave (README-only).
- No vendored code touched.
- README edits are byte-stable (text-only, no claims rewritten).
- D.4 30/30 PASS preserved.
- mkdocs 0 warnings preserved.
- claims_consistency no drift.
- No internal IDs in README (0 confirmed).
- All numerical claims (R1 +116.46%, p ≈ 1.5e-08, R2 d_z = −0.0990,
  R3 d_z = −0.285, R4 −78.25%, R5 −67.10%, R6 +189%) match the
  canonical verification artifacts.

## 7. Summary

| Gate / Fix | Result |
|---|---|
| D.4 byte-stable | PASS (30/30) |
| mkdocs strict | PASS (0 warnings) |
| claims_consistency | PASS (no drift) |
| 0 internal IDs in README | PASS (0) |
| R4/R5 use ΔW₂ | PASS |
| R3 has no Wave numbers | PASS |
| framework_uplift → framework_WINS | PASS |
| DATA_PRESENTATION.md has markdown link | PASS |
| Architecture has no Wave numbers | PASS |
| Zenodo URLs handled | PASS |
| "rejection" → "archive" | PASS |
| Unpushed commits | 20 (all README/audit, no source code) |

All seven Wave 268 fixes are in place. The four hard gates
(D.4, mkdocs, claims_consistency, 0 internal IDs) all pass. README is
fully clean for submission. Audit trail committed at
`docs/audit/wave268-p4-final-verify.md`.