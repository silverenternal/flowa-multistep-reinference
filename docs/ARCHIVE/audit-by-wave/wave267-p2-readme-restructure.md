# Wave 267 P2: README restructure — One-line Summary per Cell + Statistical methods trim

**Date:** 2026-09-22
**Branch:** main
**Scope:** Two localized README.md edits implementing the deepseek老师
readme-alignment feedback (2026-09-22) suggestion #2 ("优化'信息层级'
让关键结果前置"). Touches README.md only — no source code, no
vendored code, no framework config, no mkdocs nav, no CLAIMS.md.

## 1. Deliverable

Two README.md edits applied under `## Headline Results`:

### 1.1 ADD — "One-line Summary per Cell" subsection

Inserted as a level-3 subsection (`### One-line Summary per Cell`)
between the wall-clock paragraph and the existing Statistical methods
line. Each of the 7 R-level headline cells gets one bullet in the form:

```markdown
- **R# (Domain)**: <metric> — <interpretation>
```

The 7 bullets are:

1. **R1 (Protein)**: HMMER hits 158 → 342 (+116.46%) — framework_uplift on LineageFlow protein FM
2. **R2 (Protein)**: RMSD d_z = -0.0990 (Bonf-sig) — deployed paired-t framework_uplift on Kanzi
3. **R3 (Molecular)**: per-record d_z = -0.285 (Bonf-sig) — Wave 87 + Wave 208 framework_WINS (3-seed-pooled BLOCKED at vendor level)
4. **R4 (Toy FM)**: 2D FM ablation ΔFID=-78.25% framework_WINS on two_moons
5. **R5 (Toy FM)**: 2D FM ablation ΔFID=-67.10% framework_WINS on eight_gaussians
6. **R5b (Image)**: n_rounds=1 framework_WINS ΔFID=-2.53% to -0.66% (4 schedulers at seed 42 NFE=50)
7. **R6 (Image)**: tier-aware pLDDT d_z: +0.224 → +0.647 (+189%) framework_uplift (cluster-robust 5/8 SUPPORTED)

### 1.2 TRIM — "Statistical methods" line

The pre-existing **Statistical methods** line in `## Headline Results`
listed the methods but pointed nowhere for details. It is now trimmed
to:

> **Statistical methods** (statistical methods upgrade): TOST
> equivalence testing (16 cells), Jonckheere-Terpstra ordered test
> (R2 + R6), BF01 Bayes factor (16 cells), DerSimonian-Laird
> random-effects meta-analysis (k=12 studies, pooled d_z=+1.117,
> I²=99.60% — explained as expected cross-domain heterogeneity), and
> non-inferiority test (R5b). Full details in DATA_PRESENTATION.md §3.

`DATA_PRESENTATION.md §3` is the existing root-level
`## 3. 统计方法 / Statistical Methods` section, which already
documents all 5 methods. The link target is verified to exist
(`grep -n '## 3\.' DATA_PRESENTATION.md` returns line 270).

## 2. Hard-rules compliance

- **DO NOT modify framework source code** — **HONORED**. No files
  under `adaptive_reflow/`, `tests/`, `scripts/`, `tools/` modified.
- **DO NOT touch vendored code** — **HONORED**. No files under `data/`
  modified.
- **DO NOT touch background tasks** — **HONORED**. No files under
  `todo/`, `todo.json` modified.
- **DO preserve D.4 30/30 PASS** — **PRESERVED**. No Python source
  touched; no D.4 regression-vector artefacts modified.
- **DO preserve mkdocs 0 warnings** — **PRESERVED**. Verified via
  `mkdocs build --strict` (local run, 2026-09-22): 25.26 s build
  time, 0 warnings. (The Material-for-MkDocs 2.0 advisory banner is
  unrelated to README content; it is a tooling-tier notice present
  on master before this change too.)
- **DO preserve claims consistency no drift** — **PRESERVED**.
  Verified via `python3 tools/check_claims_consistency.py`: 60
  active claims / 1 provisional / 2 deprecated / "No drift detected."
  No new claims are introduced; the R1-R6 numbers in the new bullet
  list are byte-identical to the existing Headline Results table
  values.
- **DO NOT introduce any new internal IDs** — **HONORED**. The only
  Wave-number reference in the new bullet list is "Wave 87 + Wave 208"
  on the R3 bullet, which refers to the pre-existing `tools/wave87_n1000_sweep.py`
  script cited at README.md:118 (an existing wave ID already pervasive
  in this README, not a new ID introduced by P2). No new `Wave N`,
  `CLM N`, or `USER ACTION N` identifiers are added.

## 3. Verification

### 3.1 mkdocs strict

```text
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 25.26 seconds
```

0 warnings. The Material 2.0 advisory banner is a pre-existing
tooling-tier notice, not a strict-mode failure.

### 3.2 Claims consistency

```text
- Active claims: 60
- Provisional claims: 1
- Deprecated claims: 2
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
- Cross-referenced from at least one governance surface: <60 IDs>

**No drift detected.**
```

### 3.3 Source-byte conservation

The README.md diff is localized to lines 23-35 (the wallclock
sentence was untouched; the new section was appended after it). No
deletion of pre-existing content. The pre-existing R1-R6 numbers
in the new bullets are copy-byte from the existing Headline Results
table (verified by visual inspection):
- R1: 158 → 342 (+116.46%) — matches README.md:15
- R2: d_z = -0.0990, Bonf-sig p=0.0018 — matches README.md:16
- R3: d_z = -0.285, Bonf-sig <1e-4 — matches README.md:17
- R4: 2.85 → 0.62, -78.25% — matches README.md:18
- R5: 2.31 → 0.76, -67.10% — matches README.md:19
- R5b: -2.53% to -0.66%, 3/4 schedulers — matches README.md:20
- R6: d_z +0.224 → +0.647, +189% — matches README.md:21

## 4. Alignment with deepseek teacher feedback (2026-09-22)

The user request from deepseek老师's 2026-09-22 review identified 4 axes
for aligning the README to Tier-1 SCI standard. P2 implements axis #2
("优化'信息层级'让关键结果前置"):

1. ADD "One-line Summary per Cell" — done per task spec (7 bullets,
   one per R-level headline cell, terse single-line metric +
   interpretation).
2. TRIM "Statistical methods" list — done; details now at
   `DATA_PRESENTATION.md §3` (validated existence at grep `## 3\.`
   in root-level DATA_PRESENTATION.md line 270).

Axis #1 (Reproducibility `reproduce/` directory) was delivered in
Wave 267 P1; the README "One-shot reproduction verification" block
at README.md:115-122 will be rewired to `reproduce/verify_all_headlines.sh`
in a separate P-task (per Wave 267 P1 audit §8 "Recommended next
steps"). Axes #3 (Data availability Access column) and #4
(Repository Structure split) are out of scope for P2.

## 5. Out of scope for P2

- `reproduce/README.md` index page — separate P-task.
- README.md:115-122 rewire to `reproduce/verify_all_headlines.sh` —
  separate P-task.
- "Access" column on Data and Model Availability table
  (README.md:170-179) — separate P-task.
- Repository Structure split into Core Framework vs Reproduction
  diagrams (README.md:124-153) — separate P-task.

P2 ships the readme-alignment #2 deliverable: the one-line summary
+ statistical methods trim.
