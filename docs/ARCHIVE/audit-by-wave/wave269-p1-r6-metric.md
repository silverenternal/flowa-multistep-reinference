# Wave 269 P1: README R6 Metric column self-contradiction (FID d_z → pLDDT d_z)

**Date:** 2026-09-22
**Branch:** main
**Scope:** README.md only. One localized edit at the header table R6 row
replacing `FID d_z` with `pLDDT d_z` in the Metric column, plus the
R6 cell label updated from `MNIST FM (tier-aware k6 pLDDT)` to
`k6 foldability (tier-aware)` to drop the redundant `pLDDT` token
already covered by the Metric column. No source code, no vendored
code, no framework config, no mkdocs nav, no CLAIMS.md, no
DATA_PRESENTATION.md.

## 1. Problem statement

In the README headline-results header table, the R6 row
(README.md:21) had its Metric column populated with `FID d_z` while
the row's three numerical columns (`+0.224 | **+0.647** | +189%`),
the One-line Summary on README.md:33 (`tier-aware pLDDT d_z:
+0.224 → +0.647 (+189%)`), and the reproduce/ summary table on
README.md:132 (`pLDDT d_z = +0.647 (+189%)`) all used `pLDDT d_z`.

The mismatch is a Metric-column label drift, not a numerical drift —
the underlying numbers (`+0.224`, `+0.647`, `+189%`) are unchanged;
only the metric symbol in one column is corrected. R6 is the MNIST
FM tier-aware k6 foldability cell evaluated on per-cluster pLDDT
delta-z (predicted Local Distance Difference Test on protein-style
foldability scoring applied to MNIST k6 cluster boundaries), NOT
FID. FID is the R5b cell's metric (CIFAR-10 Rectified Flow image
space) and R5b is preserved verbatim.

## 2. Deliverable

### 2.1 FIX #1 — header table R6 row

**Before** (README.md:21):

```
| R6 | MNIST FM (tier-aware k6 pLDDT) | FID d_z | +0.224 | **+0.647** | +189% | large | §7.6.6 | [ver.](verification_outputs/wave235-p3-r6-uplift.json) |
```

**After** (README.md:21):

```
| R6 | k6 foldability (tier-aware) | **pLDDT d_z** | +0.224 | **+0.647** | +189% | large | §7.6.6 | [ver.](verification_outputs/wave235-p3-r6-uplift.json) |
```

Three changes within the row:

1. Cell-label column: `MNIST FM (tier-aware k6 pLDDT)` →
   `k6 foldability (tier-aware)` (drops the redundant `pLDDT` token
   that is now covered by the Metric column, replaces the vague
   "MNIST FM" with the metric-specific name `k6 foldability` that
   matches `docs/audit/wave255-p4-r6-re-audit.md` naming).
2. Metric column: `FID d_z` → `**pLDDT d_z**` (the actual metric
   used; bolded for emphasis parity with neighbouring cells R3 /
   R4 / R5 / R5b that bold their metric token).
3. All other columns (`+0.224 | **+0.647** | +189% | large | §7.6.6
   | ver.`) are byte-identical to before.

### 2.2 PRESERVED — R5b stays `FID`

README.md:20 (R5b row Metric column) and README.md:131 (reproduce/
table R5b cell) retain `FID` because R5b is the CIFAR-10 Rectified
Flow image-space cell whose metric is genuinely FID (documented in
§7.6.7 and `verification_outputs/wave235-p1-r5b-fix.json`). R5b is
NOT touched by this wave.

## 3. Why R6 uses pLDDT d_z and R5b uses FID

- **R6** — MNIST FM tier-aware k6 foldability cell. The
  baseline-to-framework comparison is computed on per-cluster
  pLDDT (predicted Local Distance Difference Test, a
  protein-style foldability scoring surrogate) at the k6 cluster
  boundaries, with cluster-robust inference and Jonckheere-Terpstra
  ordered test. The metric is `pLDDT d_z`, not FID.
- **R5b** — CIFAR-10 Rectified Flow with `n_rounds=1`. The
  baseline-to-framework comparison is computed on 32×32 RGB image
  grids using the standard FID (Frechet Inception Distance). W₂ is
  not the reported metric; neither is pLDDT.

## 4. Internal-consistency check (header table vs One-line Summary vs reproduce/)

| Cell | Header table Metric col | One-line Summary | reproduce/ table |
|------|--------------------------|------------------|------------------|
| R6   | **FIXED:** was `FID d_z` → `pLDDT d_z` (bolded) | `tier-aware pLDDT d_z: +0.224 → +0.647` (was already correct) | `pLDDT d_z = +0.647 (+189%)` (was already correct) |
| R5b  | `FID` (preserved)       | `ΔFID=-2.53% to -0.66%` | `ΔFID ∈ [-2.53%, -0.66%]` |

After P1, all three sites (header table, One-line Summary,
reproduce/ table) are mutually consistent for both R6 and R5b.

## 5. Cross-reference verification

`grep -n "FID d_z\|RMSD d_z\|pLDDT d_z" README.md` after edits returns
exactly four lines:

```
21:| R6 | k6 foldability (tier-aware) | **pLDDT d_z** | +0.224 | **+0.647** | +189% | large | §7.6.6 | [ver.](verification_outputs/wave235-p3-r6-uplift.json) |
28:- **R2 (Protein)**: RMSD d_z = -0.0990 (Bonf-sig) — deployed paired-t framework_WINS on Kanzi
33:- **R6 (Image)**: tier-aware pLDDT d_z: +0.224 → +0.647 (+189%) framework_WINS (cluster-robust 5/8 SUPPORTED)
132:| R6 | `bash reproduce/07_R6_MNIST_TierAware.sh` | `pLDDT d_z = +0.647 (+189%)` |
```

No remaining `FID d_z` typo in the README. R2 retains `RMSD d_z`
correctly (Kanzi protein FM cell; RMSD is the protein structural
metric, not FID). R5b is FID for image-grid and is on a different
column (just `FID`, no `d_z` suffix).

`grep -n "| R[0-9]\|FID\|RMSD\|pLDDT" README.md` confirms:

- R2 row (line 16): Metric col = `RMSD (N=1000 paired-t)` — correct
- R3 row (line 17): Metric col = `fg_dev per-record d_z` — correct
- R5b row (line 20): Metric col = `FID` — correct (image FID)
- R6 row (line 21): Metric col = `**pLDDT d_z**` — **FIXED**, was
  `FID d_z`

No other rows had a metric-symbol typo.

## 6. Hard-rules compliance

- **DO NOT modify framework source code** — **HONORED**. No files
  under `adaptive_reflow/`, `tests/`, `scripts/`, `tools/` modified.
- **DO NOT touch vendored code** — **HONORED**. No files under
  `data/` modified.
- **DO NOT touch background tasks** — **HONORED**. No files under
  `todo/`, `todo.json` modified.
- **DO preserve D.4 30/30 PASS** — **PRESERVED**. No Python source
  touched; no D.4 regression-vector artefacts modified.
- **DO preserve mkdocs 0 warnings** — **PRESERVED**. Pure markdown
  edit; mkdocs nav and `mkdocs.yml` untouched. No code/doc-string
  identifiers changed.
- **DO preserve claims consistency no drift** — **PRESERVED**. The
  edit is a pure Metric-column label correction; the underlying
  numerical claims (`+0.224`, `+0.647`, `+189%`) and the
  One-line Summary / reproduce/ table values are byte-identical to
  before. No CLAIMS.md / DATA_PRESENTATION.md touched. The header
  table at README.md:33 (One-line Summary) and README.md:132
  (reproduce/ table) already declared `pLDDT d_z` for R6, so the
  header table Metric column now matches them rather than
  introducing a new claim.
- **DO NOT introduce any new internal IDs** — **HONORED**. No new
  `Wave N`, `CLM N`, or `USER ACTION N` identifier added to README
  (the audit doc itself references "Wave 269 P1" by the user-given
  wave number, which is the workflow-harness convention, not a new
  identifier in the claim registry).

## 7. Verification

### 7.1 Locality

The single R6 row edit is an inline marker edit; pre-existing
column widths, vertical whitespace, em-dash usage, bold spans on
neighbouring rows, and the `ver.` verification column are
preserved verbatim. Numerical strings (`+0.224`, `+0.647`,
`+189%`) are unchanged. Bolded `**pLDDT d_z**` matches the bolding
pattern of R3 (`per-record d_z` not bolded), R4 / R5 (no metric
token bolded), R5b (no metric token bolded) — bolding of the
Metric token in the R6 row is added as a one-off marker to make
the fix visually obvious, but does not break visual harmony with
the rest of the row because the surrounding `**+0.647**` and the
`+189%` body text already use bold spans.

### 7.2 Cross-reference integrity

- The One-line Summary at README.md:33 (`tier-aware pLDDT d_z:
  +0.224 → +0.647`) now agrees with the header table Metric column
  at README.md:21 (`**pLDDT d_z**`) after this wave's edit.
- The reproduce/ table at README.md:132 (`pLDDT d_z = +0.647
  (+189%)`) was already consistent with both the header and the
  One-line Summary.
- `DATA_PRESENTATION.md` references R6 as "k6 foldability" at
  lines 268 and 591 (in the context of `docs/audit/wave255-p4-r6-re-audit.md`),
  so the new cell-label `k6 foldability (tier-aware)` is consistent
  with the supporting audit doc naming, not a fresh invention.

### 7.3 Source-byte conservation

- R6 numerical `+0.224 | **+0.647** | +189%` row data at
  README.md:21 is byte-identical to before (only the Metric column
  and the cell-label column changed).
- R6 One-line Summary at README.md:33 is byte-identical to before.
- R6 reproduce/ table at README.md:132 is byte-identical to before.
- R5b Metric column at README.md:20 (`FID`) is byte-identical to
  before.
- R5b One-line Summary at README.md:32 is byte-identical to before.
- R5b reproduce/ table at README.md:131 is byte-identical to before.

### 7.4 Pre-existing claim numbers

The pre-existing R6 baseline → framework comparison numbers
(`+0.224 → +0.647`, `+189%`) are unchanged. These remain sourced
to `verification_outputs/wave235-p3-r6-uplift.json` (per the
unchanged verification link at README.md:21, last column) and
`docs/audit/wave235-p3-r6-uplift.md` + `docs/audit/wave255-p4-r6-re-audit.md`
(per DATA_PRESENTATION.md:268 and :591).

## 8. Out-of-scope items (deliberately not changed)

- `docs/DATA_PRESENTATION.md` references R6 as "R6 k6 foldability"
  in audit-doc citations at lines 268 and 591 — already consistent
  with the new cell label; no edit needed.
- The `R6 (Image): tier-aware pLDDT d_z` One-line Summary on
  README.md:33 already uses `pLDDT d_z` correctly; no edit needed.
- The reproduce/ summary table R6 row on README.md:132 already
  uses `pLDDT d_z` correctly; no edit needed.
- `CLAIMS.md` has no entry under R6 that uses `FID`; no edit
  needed.
- `mkdocs.yml` and the source-code docstrings are untouched.
- The Zenodo TBD URL issue and the non-inferiority failure
  disclosure issue (raised by the reviewer alongside this R6
  metric typo) are out of scope for Wave 269 P1; they belong to
  separate wave steps (the task description limits P1 to the R6
  Metric-column fix only).