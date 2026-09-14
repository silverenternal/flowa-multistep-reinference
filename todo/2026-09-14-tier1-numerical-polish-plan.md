# Tier-1 Numerical Polish Plan (2026-09-14)

**Date:** 2026-09-14
**Author:** Wave 145 Agent 3 (planning)
**Status:** PLANNED - awaiting user OK before launching
**Constraint:** Per user directive "不要重复跑实验", these are user-gated; this plan captures scope without launching.

## Why this plan exists

Per the latest conversation review of experimental data pretty-ness,
the current FlowA paper has strong honest-negative-surface coverage but
"mid" numerical numbers compared to Kim2025 (NeurIPS 2025). 8 numbered tables
+ 17 figures match Kim2025 footprint (good), but specific numbers within those
tables could be stronger with additional experimental work.

## Work breakdown

### Tier 1 (highest ROI, fast execution)

#### Item 1: Algorithm primitive ablation sweep (Table C - 6 h CPU)
**Why:** Table C currently has 5 rows from twodim_fm L2 to target (1.5686 / 0.6595 etc.), NOT N=1000 paper-metric numbers.
**What:** Run Wave 125 algorithm primitives (`should_skip_restart_small_sigma`, BRAI `magnitude`, `target_rms_threshold`) ablation on Kanzi N=1000 paper-metric to fill Table C with real numbers.
**Effort:** ~6 h CPU (4-5 variants × Kanzi N=1000 each).
**Benefit:** Closes the "spec-only" honest-negative disclosure in §10.4 Table C; reviewer sees actual measured ablation.

#### Item 2: Hyperparameter sensitivity sweep (Table D - 6-12 h CPU)
**Why:** Table D currently has 5 hyperparameter rows with code-default values and "covered by Wave 14 ablation / deferred" honest disclosure.
**What:** Run sensitivity sweep over 5 hyperparameters × 3-5 values = 15-25 cells on Kanzi or 2D FM.
**Effort:** ~6-12 h CPU.
**Benefit:** Closes the "spec-only" honest-negative disclosure in §10.4 Table D; reviewer sees actual measured sensitivity.

#### Item 3: CIFAR v4 matched-NFE re-investigation (5 min)
**Why:** §10.4 K3 honest-discloses CIFAR v4 matched-NFE=50 +224% REGRESSION.
**What:** Investigate whether the +224% comes from a paper-metric protocol mismatch (v4 used baseline FID 130 vs Table 9 FID 83).
**Effort:** ~5 min (audit-trail verification only).
**Benefit:** Clarifies the K3 disclosure in §10.4.

### Tier 2 (medium ROI, longer execution)

#### Item 4: PDF conversion to NeurIPS full .tex (4-6 h CPU)
**Why:** Wave 144 Phase 3 generated a placeholder PDF; full NeurIPS .tex rewrite is camera-ready scope.
**What:** Manual .tex rewrite of docs/paper-final-neurips.md → paper.tex using NeurIPS 2025 .sty + xelatex.
**Effort:** ~4-6 h CPU.
**Benefit:** Clean NeurIPS-style PDF for OpenReview upload.

### Tier 3 (low ROI, blocked)

#### Item 5: Wave 86 LineageFlow N=1000 HMMER re-run (30-50 h CPU)
**Why:** The +116% headline is in audit doc text only; raw JSON never saved to repo.
**What:** Re-run `tools/gen_lineageflow_n1000_fastas.py` to produce 1000 FASTAs/arm + HMMER scan + byte-reproducible raw JSON.
**Effort:** ~30-50 h CPU (large; ESM-2 forward pass is the bottleneck).
**Blocker:** None technically; cost is the issue.
**Benefit:** Closes K8 honest-negative disclosure in §10.4 by putting raw 158/342 numbers in repo JSON.

#### Item 6: LineageFlow foldability N=1000 re-run (OmegaFold env blocker)
**Why:** Currently N=5 only; OmegaFold requires Python ≤3.10 (host is 3.12).
**What:** Set up Python 3.10 venv + OmegaFold + re-run N=1000 foldability + self_consistency.
**Effort:** ~25 h CPU per arm (CPU wallclock at ~45 s/seq × 2000 seq).
**Blocker:** Environment incompatibility (Python 3.10).
**Benefit:** Closes LineageFlow foldability + self_consistency N=5 → N=1000 gap.

## Priority order (RO)

1. Item 3 (5 min) - audit verification of CIFAR v4 protocol mismatch
2. Item 1 (6 h) - algorithm primitive ablation on Kanzi N=1000
3. Item 2 (6-12 h) - hyperparameter sensitivity sweep
4. Item 4 (4-6 h) - full NeurIPS .tex rewrite for PDF
5. Item 5 (30-50 h) - Wave 86 LineageFlow N=1000 HMMER re-run (large)
6. Item 6 (25 h) - LineageFlow foldability N=1000 (env blocker)

## Acceptance criteria

After all Tier 1 items complete:
- 8 numbered tables all have real measured data (no "spec-only" or "deferred" disclosures)
- PDF is NeurIPS-format .tex (not placeholder)
- D.4 33/33 / ruff 0 / claims PASS preserved

After all Tier 2 items complete:
- Wave 86 N=1000 HMMER raw JSON in repo (no audit-doc-only numbers)
- LineageFlow foldability + self_consistency N=1000 (closes N=5 placeholder)

## Out-of-scope (per user "不要重复跑实验")

- mypy 988 hand-fix (camera-ready only)
- Wan2.2 / FreqFlow / MM-FM integration (no upstream ckpt)
- PB-xtb pipeline closure
- OmegaFold Python 3.10 env setup (subset of Item 6)
- LineageFlow novelty_mmseqs2 (Pfam fastas placeholder)

## Status

This plan is **PLANNED - awaiting user OK** to launch.
User said "你提到的这些点都要做" referring to these items; this plan
captures scope without launching. Each item has explicit time estimate.
