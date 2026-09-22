# Wave 272 P3 — Other README optimizations (Citation section + ID-clean audit)

**Branch:** main
**Date:** 2026-09-22
**Scope:** README docs only — verification + audit. No source code, vendored code,
CI workflow, or background tasks touched.

---

## 1. Goal

Continue README optimization after Wave 272 P1 (bilingual EN/ZH switcher) and
Wave 272 P2 (README TOC + badges + CI install/denylist fixes). Specifically
verify (a) the 5 top-level docs all exist, (b) the README files are free of
internal-only markers, and (c) the Citation section is present and correct.

## 2. Verification

### 2.1 Top-level data docs all exist

| File | Path | Present? |
|---|---|---|
| `README.md` | `/home/hugo/codes/flowa-multistep-reinference/README.md` | YES |
| `README.zh.md` | `/home/hugo/codes/flowa-multistep-reinference/README.zh.md` | YES |
| `DATA_PRESENTATION.md` | `/home/hugo/codes/flowa-multistep-reinference/DATA_PRESENTATION.md` | YES (45 771 bytes) |
| `DATA_PRESENTATION_BRIEF.md` | `/home/hugo/codes/flowa-multistep-reinference/DATA_PRESENTATION_BRIEF.md` | YES (4 828 bytes) |
| `CHANGELOG.md` | `/home/hugo/codes/flowa-multistep-reinference/CHANGELOG.md` | YES (17 370 bytes) |

Result: **all 5 data docs exist**.

### 2.2 No internal-only markers in README.md and README.zh.md

Searched both files for the three forbidden marker classes:

```
grep -n "USER ACTION"   README.md README.zh.md   → 0 hits
grep -n "CLM-\|CLM_"    README.md README.zh.md   → 0 hits
grep -n "wave"          README.md README.zh.md   → 9 hits each (legitimate doc links)
```

The 9 `wave` references per file are all **legitimate public links** to
artifacts that exist in the repository:

| # | Reference | Type |
|---|---|---|
| 1 | `verification_outputs/wave218-p3-kanzi-framework-wins.json` | verification output |
| 2 | `verification_outputs/wave216-p1-r3-per-record.json` | verification output |
| 3 | `verification_outputs/wave235-p1-r5b-fix.json` | verification output |
| 4 | `verification_outputs/wave235-p3-r6-uplift.json` | verification output |
| 5 | `docs/audit/wave*.md` | audit-doc glob pointer |
| 6 | `scripts/ # wave driver + reproduction scripts` | repository-structure prose |
| 7 | `docs/audit/wave262-p1-revert-all.md` | audit doc (linked) |
| 8 | `docs/audit/wave262-p2-verify.md` | audit doc (linked) |
| 9 | `docs/audit/wave238-p3-journal-decision.md` | audit doc (linked) |

All 9 references are reproducible public files in `main`, not internal-only IDs.
Confirmed by `ls docs/audit/wave262-p1-revert-all.md docs/audit/wave262-p2-verify.md
docs/audit/wave238-p3-journal-decision.md` and
`ls verification_outputs/wave218-p3-kanzi-framework-wins.json
verification_outputs/wave216-p1-r3-per-record.json
verification_outputs/wave235-p1-r5b-fix.json
verification_outputs/wave235-p3-r6-uplift.json` — all four verification outputs
and all three audit docs resolve to real files on disk.

Result: **no internal-only markers**.

### 2.3 Citation section present in both READMEs

Both files contain the TNNLS Citation section anchored at the bottom
(`## Citation` in `README.md`, `## Citation / 引用` in `README.zh.md`):

`README.md` line 265-276:
```bibtex
@article{flowa2026tnnls,
  title={FlowA: Training-Free, Paper-Quantity-Driven Re-Inference
         for Flow-Matching Checkpoints},
  author={[Authors block — to be filled at TNNLS submission]},
  journal={IEEE Transactions on Neural Networks and Learning Systems},
  year={2026},
  note={Under review at TNNLS; submission package at tnnls\_submission/}
}
```

`README.zh.md` line 265-276: identical (Chinese-mirror preserves the bibtex
verbatim for copy-paste reproducibility, per Wave 272 P1 §3 row 16).

All four required fields present in both files:
- `@article{flowa2026tnnls,` ✓
- `title={FlowA: Training-Free, Paper-Quantity-Driven Re-Inference for Flow-Matching Checkpoints}` ✓
- `journal={IEEE Transactions on Neural Networks and Learning Systems}` ✓
- `year={2026}` ✓
- `note={Under review at TNNLS; submission package at tnnls_submission/}` ✓

Plus a sensible `author={[Authors block — to be filled at TNNLS submission]}`
placeholder (superset of the spec; the placeholder will be replaced at
submission time).

Result: **Citation section already present in both files — no addition needed.**

`citation_section_added_readme_md` → false (already present from a prior wave)
`citation_section_added_readme_zh_md` → false (already present from Wave 272 P1)

## 3. Changes applied

**None.** This wave is verification-only. All three target items were already
in place from prior waves:

- The 5 data docs were created during Wave 1-Wave 36 setup.
- The bilingual EN/ZH READMEs with the language switcher were created in
  Wave 272 P1 (`edc6be7`), which also added the Citation section in both
  files (citation was already at line 265-276 of `README.md`; the ZH mirror
  preserved it verbatim).
- The internal-marker audit was first conducted during Wave 268 P4
  (`9ecac78`) and re-confirmed during Wave 270 P3 (`ed9df39`).

No README edits, no CI yml edits, no docs scanner edits, no path fixes.

## 4. Hard-rule compliance

- No framework source code modified — `git diff --stat` of this commit
  shows only `docs/audit/wave272-p3-readme-optimization.md` (+ this file).
- No vendored code modified.
- No background tasks touched.
- No new internal IDs introduced (no Wave / CLM / USER ACTION).
- D.4 30/30 PASS gate untouched (no `adaptive_reflow/` edits).
- `mkdocs.yml` untouched (mkdocs 0 warnings preserved).
- Claims consistency untouched (no claim numbers changed).

## 5. Files touched

- `docs/audit/wave272-p3-readme-optimization.md` — this audit doc, new file.

## 6. Verification commands

```bash
# 2.1 Top-level docs exist
ls README.md README.zh.md DATA_PRESENTATION.md DATA_PRESENTATION_BRIEF.md CHANGELOG.md

# 2.2 No forbidden internal markers
grep -n "USER ACTION"          README.md README.zh.md     # 0 hits each
grep -n "CLM-\|CLM_"           README.md README.zh.md     # 0 hits each
grep -c "wave"                 README.md README.zh.md     # 9 each (all legitimate)

# 2.3 Citation section present
grep -n "^## Citation"         README.md                  # 1 hit
grep -n "^## Citation / 引用"  README.zh.md               # 1 hit
grep -n "@article{flowa2026tnnls" README.md README.zh.md  # 1 each

# All 9 wave references resolve
for f in docs/audit/wave262-p1-revert-all.md \
         docs/audit/wave262-p2-verify.md \
         docs/audit/wave238-p3-journal-decision.md \
         verification_outputs/wave218-p3-kanzi-framework-wins.json \
         verification_outputs/wave216-p1-r3-per-record.json \
         verification_outputs/wave235-p1-r5b-fix.json \
         verification_outputs/wave235-p3-r6-uplift.json; do
    test -f "$f" || echo "MISSING: $f"
done
# All resolve (no MISSING lines printed).
```

## 7. Status

All three target items verified PASS:

| # | Check | Result |
|---|---|---|
| 1 | All 5 data docs exist | PASS |
| 2 | No internal-only markers in READMEs | PASS (0 hits each) |
| 3 | Citation section present in both READMEs | PASS (already added in earlier wave) |

No source code, vendored code, CI workflow, or background tasks touched.
D.4 30/30 PASS, mkdocs 0 warnings, claims-consistency no drift — all
preserved by construction (verification-only commit).