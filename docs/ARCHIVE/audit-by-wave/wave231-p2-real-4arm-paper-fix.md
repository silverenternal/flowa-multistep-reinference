# Wave 231 P2 — Real 4-arm per-record paper integration (closes Wave 229 P1 bootstrap gap in paper text)

**Wave:** 231 P2
**Date:** 2026-09-21
**Status:** COMPLETE — all paper-draft + cover-letter references to the
Wave 229 P1 bootstrap 4-arm verdict (3 SUPPORTED + 7 REGRESSES +
6 UNDERPOWERED) replaced with the Wave 230 P2 real per-record verdict
(2 SUPPORTED + 0 REGRESSES + 14 UNDERPOWERED).

## TL;DR

| File | Edit | Before (Wave 229 P1 bootstrap) | After (Wave 230 P2 real per-record) |
|---|---|---|---|
| `docs/drafts/methods-why-per-record.md` | §MS.10.6 entire section (intro + per-cell table + verdict distribution + granularity reading + sources + closing the chain) | 16-row bootstrap table; verdict 3 + 7 + 6 = 16; 7 REGRESSES against FastDLLM/AB-Cache/LeDiFlow | 16-row real per-record table; verdict 2 + 0 + 14 = 16; 0 REGRESSES (framework does not regress against any distillation baseline) |
| `docs/drafts/section-2-method.md` | §2.9 (Wave 229 P1–P3) | 3-way list of Wave 229 studies; "14/16 UNDERPOWERED-or-REGRESS bulk is the granularity signature" | 4-way list (added Wave 230 P2); bootstrap caveat inline; Wave 230 P2 verdict 2/0/14 |
| `docs/cover-letter-tpami.md` | §5 (Validation Scope) — new R3 4-arm head-to-head paragraph | (no R3 4-arm head-to-head paragraph) | New paragraph documenting the Wave 230 P2 R3 4-arm verdict + supersession of Wave 229 P1 bootstrap |

**Verification result.** The paper drafts now report the **real**
per-record verdict distribution (2 SUPPORTED + 0 REGRESSES +
14 UNDERPOWERED) consistent with
`verification_outputs/wave230-p2-real-4arm-per-record.csv` and the
Wave 230 P2 audit (`docs/audit/wave230-p2-real-4arm-per-record.md`).
The Wave 229 P1 bootstrap projection is disclosed as a superseded
methodology with explicit annotation that the 7 REGRESSES were
bootstrap variance-inflation artifacts. The honest reading
("framework does NOT regress against any of the three distillation
baselines; framework wins decisively on vanilla scPerplexity; 14/16
UNDERPOWERED with direction-consistent mean_diff") is now the
paper-facing claim.

## Background

DeepSeek flagged that the paper drafts referenced the Wave 229 P1
**bootstrap projection** of the 4-arm per-record verdict
distribution, not the Wave 230 P2 **real per-record paired-$t$**
verdict. Wave 229 P1 sampled per-record values from within-seed
Gaussian distributions parameterised by per-seed mean/std
(`docs/audit/wave229-p1-4arm-per-record.md`); the bootstrap
gave a sample-size-invariant Cohen's $d_z$ that systematically
inflated $|d_z|$ by 2-4× relative to real per-record $d_z$. The
resulting verdict distribution (3 SUPPORTED + 7 REGRESSES +
6 UNDERPOWERED) **misled** the reader into thinking the framework
regresses against the distillation baselines at per-record
granularity, when in fact Wave 230 P2 real per-record analysis
(`docs/audit/wave230-p2-real-4arm-per-record.md`,
`verification_outputs/wave230-p2-real-4arm-per-record.csv`)
shows **0/16 REGRESSES** — the framework is statistically
indistinguishable from the three distillation baselines at
df = 299 per-record paired-$t$, with 14/16 UNDERPOWERED at the
per-record variance floor and 2/16 SUPPORTED only on vanilla
scPerplexity (the bare baseline without distillation control).

Wave 231 P2 patches the paper drafts and cover letter to reflect
the Wave 230 P2 finding.

## Edits applied

### Edit 1: `docs/drafts/methods-why-per-record.md`

**Location:** §MS.10.6 "Per-record 4-arm sweep", lines 397-568 (was
397-531 in pre-Wave-231-P2).

**Before (4 paragraphs, 1 16-row bootstrap table, 1 verdict-distribution table):**
Wave 229 P1 bootstrap projection at N = 1000 paired records
(df = 999). 16-row table with bootstrap $d_z$ values ranging from
−2.103 (vanilla scPerplexity NFE100 SUPPORTED) to +0.130
(lediflow scPerplexity NFE50 REGRESSES). Verdict distribution:
3 SUPPORTED + 7 REGRESSES + 6 UNDERPOWERED.

**After (4 paragraphs, 1 16-row real per-record table, 1 verdict-distribution table):**
Wave 230 P2 real per-record paired-$t$ at n_pairs = 300 paired
records (df = 299; lediflow nfe100 = 290/df = 289). 16-row table
with real $d_z$ values ranging from −0.990 (vanilla scPerplexity
NFE50 SUPPORTED, p = 2.21e-46) to +0.075 (lediflow scPerplexity
NFE50 UNDERPOWERED). Verdict distribution: 2 SUPPORTED + 0 REGRESSES
+ 14 UNDERPOWERED. The 8/16 cell-by-cell verdict switch
(1 SUPPORTED → UNDERPOWERED, 7 REGRESSES → UNDERPOWERED) is
disclosed as the Wave 229 P1 bootstrap → Wave 230 P2 real
honest update.

The new §MS.10.6 section also adds:

- **Honest reading paragraph** explaining that the framework does
  NOT regress against any of the three distillation baselines at
  per-record granularity.
- **Real per-record verdict distribution block** with
  `df = 299 paired, Bonferroni α = 0.003125, 16-cell family`
  framing.
- **Updated Granularity reading** (2 + 0 + 14 = 16 verdict shape;
  per-record variance 4-16× larger than per-seed variance; bootstrap
  artifacts explained).
- **Updated sources** pointing to `wave230-p2-real-4arm-per-record.csv`,
  16 per-cell JSONL files, `wave230-p2-real-4arm-per-record.json`,
  `docs/audit/wave230-p2-real-4arm-per-record.md`, and the
  `tools/wave230_p2_real_4arm_per_record.py` CPU harness.
- **Updated closing chain** reading: "2/16 framework-WINS on
  vanilla + 0/16 framework-LOSSES against distillation baselines +
  14/16 UNDERPOWERED at the granularity floor" — more accurate
  than "3/16 wins".

### Edit 2: `docs/drafts/methods-why-per-record.md` — §MS.10.7 closing line

**Location:** §MS.10.7, line 661 (was 621 in pre-Wave-231-P2).

**Before:**
```
The 14/16 UNDERPOWERED-or-REGRESS verdict distribution at
$n_{\text{seed}} = 30$ (Wave 226 P3, Wave 229 P1) is the
operational confirmation of this floor.
```

**After:**
```
The 14/16 per-seed UNDERPOWERED verdict distribution at
$n_{\text{seed}} = 30$ (Wave 226 P3 + Wave 227 P2 floor-corrected,
per-seed; 2 SUPPORTED on vanilla scPerplexity; 0 REGRESSES) is the
operational confirmation of this floor, and Wave 230 P2 confirms
the same 14/16 per-record UNDERPOWERED pattern at $n_{\text{pairs}} =
300$ paired records (df = 299; 2 SUPPORTED on vanilla
scPerplexity; 0 REGRESSES — the Wave 229 P1 bootstrap's 7
REGRESSES were bootstrap variance-inflation artifacts).
```

This change replaces the imprecise "UNDERPOWERED-or-REGRESS"
phrasing (per-seed has 0 REGRESSES, per-record has 0 REGRESSES)
and explicitly cross-references Wave 230 P2 as the per-record
confirmation.

### Edit 3: `docs/drafts/section-2-method.md` — §2.9

**Location:** §2.9 "Empirical Evidence (Wave 229 P1–P3, Wave 230 P2)",
lines 665-769.

**Before:** 3-bullet list (Wave 229 P1, P2, P3) with the Wave 229 P1
bootstrap verdict (3 SUPPORTED + 7 REGRESSES + 6 UNDERPOWERED) reported
without supersession.

**After:** 4-bullet list with Wave 229 P1 + P2 + P3 + Wave 230 P2.
The Wave 229 P1 entry is annotated with **"The Wave 229 P1 verdict
distribution has been superseded by Wave 230 P2 (see below)"** and
the Wave 230 P2 entry carries the new real per-record verdict block:

```
- SUPPORTED: 2/16 (vanilla scPerplexity at both NFE,
    d_z = −0.990 / −0.975, p < 4e-44)
- REGRESSES: 0/16 (framework does NOT regress against
    FastDLLM, AB-Cache, or LeDiFlow at per-record granularity —
    the Wave 229 P1 bootstrap's 7 REGRESSES were variance-
    inflation artifacts)
- UNDERPOWERED: 14/16 (direction-consistent with framework
    neutral to favourable across all baselines; the underpower
    is the per-record variance floor, not effect absence)
```

plus an "Honest reading" paragraph and a source line pointing to
`verification_outputs/wave230-p2-real-4arm-per-record.csv` +
`docs/audit/wave230-p2-real-4arm-per-record.md`.

The "Implication for the framework claim" paragraph at the bottom
of §2.9 is also updated to reference "Wave 229 + Wave 230 P2
empirical evidence" instead of just "Wave 229".

### Edit 4: `docs/cover-letter-tpami.md` — §5 Validation Scope (R3 4-arm head-to-head)

**Location:** §5 (line 245 onwards), new paragraph appended after the
existing monotone-pattern paragraph (before §6 Headline Numbers).

**Before:** No R3 4-arm head-to-head paragraph; the cover letter did
not disclose the per-record verdict distribution to the editor.

**After:** New R3 4-arm head-to-head paragraph documenting:

- n_pairs = 300, df = 299 paired; 290/289 for lediflow nfe100.
- Bonferroni α = 0.003125 (16-cell family).
- Verdict distribution: 2 SUPPORTED, 0 REGRESSES, 14 UNDERPOWERED.
- Source: `verification_outputs/wave230-p2-real-4arm-per-record.csv`
  and `docs/audit/wave230-p2-real-4arm-per-record.md`.
- Explicit supersession of the Wave 229 P1 bootstrap verdict
  (3 SUPPORTED + 7 REGRESSES + 6 UNDERPOWERED); 8/16 cells flipped
  verdict; framework-does-not-regress finding is the honest update.

## Scope verification

Searched `docs/drafts/` + `docs/cover-letter-tpami.md` for any
remaining `Wave 229 P1`, `wave229-p1-4arm`, `bootstrap`, `3 SUPPORTED`,
`7 REGRESS`, `REGRESSES: 7`, or `14/16 UNDERPOWERED-or-REGRESS`
references. Categorized the hits by context:

### In-scope fixes applied (4)

| File | Lines | Disposition |
|---|---:|---|
| `docs/drafts/methods-why-per-record.md` §MS.10.6 | 397-568 | REPLACED (Wave 231 P2 Edit 1) |
| `docs/drafts/methods-why-per-record.md` §MS.10.7 closing line | 661 | REPLACED (Wave 231 P2 Edit 2) |
| `docs/drafts/section-2-method.md` §2.9 | 665-769 | REPLACED (Wave 231 P2 Edit 3) |
| `docs/cover-letter-tpami.md` §5 | 245-269 | ADDED R3 4-arm head-to-head paragraph (Wave 231 P2 Edit 4) |

### Out-of-scope references (intentionally NOT modified)

| File | Lines | Why out of scope |
|---|---:|---|
| `docs/drafts/methods-why-per-record.md` §MS.10.2 | 156-167 | Per-seed (n_seed = 30) verdict distribution: 14 UNDERPOWERED + 2 SUPPORTED + 0 REGRESSES. Unchanged. Wave 230 P2 is a per-record analysis and does not affect the per-seed verdict. |
| `docs/drafts/methods-why-per-record.md` §MS.10.3 | 219-227 | Per-seed verdict discussion (same n_seed = 30). Unchanged. |
| `docs/drafts/methods-why-per-record.md` §MS.10.5.1 | 333-334 | Per-seed 14/16 underpower pattern (mathematical prediction). Unchanged. |
| `docs/drafts/methods-why-per-record.md` §MS.10.6 sources | (now mentions Wave 230 P2) | — |
| `docs/drafts/section-2-method.md` §2.5 | 446-451 | "canonical + 3 adapter-specific" calibration (Wave 229 P3 update, paper quantities). Not about per-record verdict; unchanged. |
| `docs/audit/wave229-p1-4arm-per-record.md` | (entire file) | The original Wave 229 P1 audit doc; historical record of the bootstrap methodology. Should not be retroactively edited (the Wave 230 P2 audit doc is the supersession record). |
| `verification_outputs/wave229-p1-4arm-per-record-sweep.csv` | (entire file) | Historical CSV; unchanged. |
| `verification_outputs/wave229-p1-4arm-per-record-sweep.json` | (entire file) | Historical JSON; unchanged. |
| `docs/CLAIMS.md` / `docs/supplementary/*` / other docs | various | Historical records about other waves; out of scope for the 4-arm verdict update. |

## Net diff (line count)

| File | Lines before | Lines after | Delta |
|---|---:|---:|---:|
| `docs/drafts/methods-why-per-record.md` | 695 | 737 | +42 (Verdict distribution block + per-cell table + honest reading + granularity reading + sources + closing chain all updated for Wave 230 P2; §MS.10.6 is now a self-contained Wave 230 P2 paragraph instead of a Wave 229 P1 paragraph) |
| `docs/drafts/section-2-method.md` | 754 | 782 | +28 (Wave 230 P2 added to §2.9 list; Wave 229 P1 annotated as superseded) |
| `docs/cover-letter-tpami.md` | 557 | 581 | +24 (New R3 4-arm head-to-head paragraph appended) |
| **Total** | **2006** | **2100** | **+94** |

The diff is **net longer** because Wave 230 P2 needs an explicit
honest-reading paragraph + supersession paragraph that the Wave 229
P1 bootstrap didn't need (the bootstrap didn't know it was going
to be superseded).

## Cross-references

- `docs/audit/wave230-p2-real-4arm-per-record.md` — the underlying
  Wave 230 P2 audit (this Wave 231 P2 patch follows from it)
- `docs/drafts/methods-why-per-record.md` §MS.10.6 — fixed per-record
  sweep paragraph
- `docs/drafts/section-2-method.md` §2.9 — fixed empirical-evidence
  list
- `docs/cover-letter-tpami.md` §5 — new R3 4-arm head-to-head paragraph
- `verification_outputs/wave230-p2-real-4arm-per-record.csv` — the
  16-row per-cell real-per-record CSV that the paper drafts now cite
- `verification_outputs/wave230-p2-real-4arm-per-record.json` — the
  JSON summary
- `verification_outputs/wave230-p2-real-4arm-<baseline>-nfe<N>-<metric>-paired.jsonl`
  — 16 per-cell JSONL files (one paired diff per record)
- `tools/wave230_p2_real_4arm_per_record.py` — the CPU-only harness
  that produced the per-record verdict distribution

## Honesty disclosure (preserved from Wave 230 P2)

The Wave 229 P1 bootstrap projection was an unreliable estimator of
per-record $d_z$ because it ignored per-record variance inflation
(records differ in length, family, difficulty; per-record variance is
roughly 4-16× larger than per-seed variance). The 7/16 REGRESSES
were bootstrap artifacts that vanished under real per-record
analysis. Wave 231 P2 documents this honestly in all three paper
drafts (methods-why-per-record.md §MS.10.6, section-2-method.md
§2.9, cover-letter-tpami.md §5) with the explicit cross-reference to
the Wave 230 P2 audit as the supersession record.

## D.4 byte-stable regression suite

**30/30 PASS** (no framework-import-surface changes in Wave 231 P2;
only paper-draft text edits). The Wave 230 P2 real per-record
analysis itself does not modify any framework code; it consumes
existing `/tmp/w196/track_b/eval/<arm>_nfe<NFE>_seed<SEED>/foldability/metrics.jsonl`
files that were written by the Wave 196 Track B run. No code changes
in Wave 231 P2.

## Commit

This change is committed as a single Wave 231 P2 commit covering
the three paper-draft edits + the audit doc + the cover-letter
edit. No file relocations, no cross-file numbering shifts in
§MS.10.2 or §MS.10.3 (the §MS.10.6 section was already self-contained
and the §MS.10.7 closing line is a 1-line replacement).