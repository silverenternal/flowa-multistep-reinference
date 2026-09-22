# Wave 268 P1: README R4/R5 ΔFID → ΔW₂ fix (W₂ is NOT FID)

**Date:** 2026-09-22
**Branch:** main
**Scope:** README.md only. Three localized string edits (4 site-level
edits) replacing the metric symbol for R4 and R5 from `ΔFID` to `ΔW₂`.
R5b is intentionally untouched because its underlying quantity **is** FID
(CIFAR-10 Rectified Flow image space). No source code, no vendored code,
no framework config, no mkdocs nav, no CLAIMS.md.

## 1. Problem statement

In the README, four sites mistakenly called R4 and R5's metric `ΔFID`.
R4 (Two Moons) and R5 (Eight Gaussians) are 2D toy FM ablation cells,
evaluated in the **2D probability-space with W₂ (Wasserstein-2)
distance**, not in image space with FID. The header table at
README.md:18-19 already says `W₂` for both cells; only the One-line
Summary subsection (README.md:30-31) and the reproduce/ summary table
(README.md:129-130) used the wrong symbol. R5b (CIFAR-10 image grid
FID) correctly uses `FID` and was preserved verbatim.

The mismatch is a metric-label drift, not a numerical drift — the
underlying numbers (`-78.25%` for R4 and `-67.10%` for R5) are
unchanged; only the label is corrected.

## 2. Deliverable

### 2.1 FIX #1 — One-line Summary R4

**Before** (README.md:30):

```
- **R4 (Toy FM)**: 2D FM ablation ΔFID=-78.25% framework_WINS on two_moons
```

**After** (README.md:30):

```
- **R4 (Toy FM)**: 2D FM ablation ΔW₂=-78.25% framework_WINS on two_moons
```

### 2.2 FIX #2 — One-line Summary R5

**Before** (README.md:31):

```
- **R5 (Toy FM)**: 2D FM ablation ΔFID=-67.10% framework_WINS on eight_gaussians
```

**After** (README.md:31):

```
- **R5 (Toy FM)**: 2D FM ablation ΔW₂=-67.10% framework_WINS on eight_gaussians
```

### 2.3 FIX #3 — reproduce/ summary table R4 row

**Before** (README.md:129):

```
| R4 | `bash reproduce/04_R4_2D_TwoMoons.sh` | `ΔFID = -78.25%` |
```

**After** (README.md:129):

```
| R4 | `bash reproduce/04_R4_2D_TwoMoons.sh` | `ΔW₂ = -78.25%` |
```

### 2.4 FIX #4 — reproduce/ summary table R5 row

**Before** (README.md:130):

```
| R5 | `bash reproduce/05_R5_2D_EightGaussians.sh` | `ΔFID = -67.10%` |
```

**After** (README.md:130):

```
| R5 | `bash reproduce/05_R5_2D_EightGaussians.sh` | `ΔW₂ = -67.10%` |
```

### 2.5 PRESERVED — R5b stays `ΔFID`

README.md:32 and README.md:131 retain `ΔFID` for R5b because R5b is the
CIFAR-10 Rectified Flow image-space cell whose metric is genuinely FID
(documented in §7.6.7 and `verification_outputs/wave235-p1-r5b-fix.json`).

## 3. Why R4/R5 use W₂ and R5b uses FID

- **R4 / R5** — 2D toy FM ablation. The baseline-to-framework
  comparison is computed on the 2D probability-space (two Moons and
  Eight Gaussians distributions) using the Wasserstein-2 distance
  (a.k.a. earth mover's distance on 2D point sets). FID is undefined
  on 2D point distributions; the label `ΔFID` was a copy-paste error
  from the image-space R5b line.
- **R5b** — CIFAR-10 Rectified Flow with `n_rounds=1`. The baseline-to-
  framework comparison is computed on 32×32 RGB image grids using
  the standard FID (Frechet Inception Distance). W₂ is not the
  reported metric for this cell.

## 4. Internal-consistency check (header table vs One-line Summary)

| Cell | Header table (line 18-20) | One-line Summary (line 30-32) | reproduce/ table (line 129-131) |
|------|--------------------------|-------------------------------|---------------------------------|
| R4   | `W₂`                     | **FIXED:** was `ΔFID` → `ΔW₂` | **FIXED:** was `ΔFID` → `ΔW₂`   |
| R5   | `W₂`                     | **FIXED:** was `ΔFID` → `ΔW₂` | **FIXED:** was `ΔFID` → `ΔW₂`   |
| R5b  | `FID`                    | `ΔFID` (preserved)            | `ΔFID` (preserved)              |

After P1, all three sites (header table, One-line Summary, reproduce/
table) are mutually consistent for each of R4/R5/R5b.

## 5. Hard-rules compliance

- **DO NOT modify framework source code** — **HONORED**. No files
  under `adaptive_reflow/`, `tests/`, `scripts/`, `tools/` modified.
- **DO NOT touch vendored code** — **HONORED**. No files under
  `data/` modified.
- **DO NOT touch background tasks** — **HONORED**. No files under
  `todo/`, `todo.json` modified.
- **DO preserve D.4 30/30 PASS** — **PRESERVED**. No Python source
  touched; no D.4 regression-vector artefacts modified.
- **DO preserve mkdocs 0 warnings** — **PRESERVED**. Pure markdown
  edits; mkdocs nav and `mkdocs.yml` untouched. No code/doc-string
  identifiers changed.
- **DO preserve claims consistency no drift** — **PRESERVED**. The
  four edits are pure metric-symbol corrections; the underlying
  numerical claims (`-78.25%`, `-67.10%`) are byte-identical to
  before. No CLAIMS.md / DATA_PRESENTATION.md touched. The header
  table at README.md:18-19 already declared `W₂` for these cells,
  so the One-line Summary and reproduce/ table now match the header
  rather than introducing a new claim.
- **DO NOT introduce any new internal IDs** — **HONORED**. No new
  `Wave N`, `CLM N`, or `USER ACTION N` identifier added to README
  (the audit doc itself references "Wave 268 P1" by the user-given
  wave number, which is the workflow-harness convention, not a new
  identifier in the claim registry).

## 6. Verification

### 6.1 Locality

All four edits are inline-marker edits; pre-existing bullet order,
vertical whitespace, bold spans, markdown table column widths, and
em-dash usage are preserved verbatim. Numerical strings
(`-78.25%`, `-67.10%`, `-2.53%`, `-0.66%`) are unchanged.

### 6.2 Cross-reference integrity

- The header table at README.md:18-19 (`W₂` for R4/R5; `FID` for R5b)
  now agrees with the One-line Summary at README.md:30-32 and the
  reproduce/ table at README.md:129-131 (after this wave's edits).
- No references to R4 / R5 / R5b elsewhere in the README were broken
  (verified by `grep -n "R4\|R5\|ΔFID\|ΔW"` after edits — every
  occurrence is accounted for by the four edits above, with R5b
  remaining on `ΔFID`).

### 6.3 Source-byte conservation

- R5b numerical `ΔFID = -2.53% to -0.66%` (README.md:32) and
  `ΔFID ∈ [-2.53%, -0.66%]` (README.md:131) are byte-identical to
  before.
- R4 numerical `W₂ | 2.85 | 0.62 | **−78.25%**` row at
  README.md:18 is byte-identical to before.
- R5 numerical `W₂ | 2.31 | 0.76 | **−67.10%**` row at
  README.md:19 is byte-identical to before.

### 6.4 Pre-existing claim numbers

The pre-existing R4 baseline → framework comparison numbers
(`2.85 → 0.62`, `−78.25%`) and R5 numbers (`2.31 → 0.76`, `−67.10%`)
are unchanged. These remain sourced to
`verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation`
(R4) and
`verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians`
(R5), per the unchanged cells in README.md:18-19.

## 7. Out-of-scope items (deliberately not changed)

- `docs/DATA_PRESENTATION.md` §3 references "non-inferiority test
  (R5b)". No R4/R5 metric-symbol reference in that doc; no edit
  needed.
- `CLAIMS.md` has no entry under R4/R5 that uses `FID`; no edit
  needed.
- `mkdocs.yml` and the source-code docstrings are untouched.
- No source code, pytest selection, or framework-internal metrics
  file was modified.
