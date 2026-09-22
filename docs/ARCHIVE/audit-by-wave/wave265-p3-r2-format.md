# Wave 265 P3: R2 row format — decision (KEEP reference / d_z)

**Date:** 2026-09-22
**Branch:** main
**Scope:** Decide whether to adopt DeepSeek's optional R2 row format consistency
change. Decision is **KEEP** — current `reference / d_z` format preserved. No
README edit, no source-code edit.

## Background

DeepSeek third-round review identified 8 fixes (all already applied across
Waves 263–265) plus a **single optional suggestion** (§III, marked "不是必须改"
= "not required") to reformat R2 in the Headline Results table from:

```markdown
| R2 | Kanzi | RMSD (N=1000 paired-t) | reference | d_z = −0.0990 | Bonf-sig p=0.0018 | framework_WINS | §7.6.2 | [ver.](...) |
```

to:

```markdown
| R2 | Kanzi | RMSD (N=1000 paired-t) | 0.9020 Å | 0.8838 Å | d_z = −0.0990 | framework_WINS | §7.6.2 | [ver.](...) |
```

so that R2's Baseline / Framework columns would mirror the absolute-number
pattern used by R1, R4, R5, R5b, R6 (e.g. R1: `158 | 342 | +116.46%`).

This wave audits whether the optional change is sound and consistent with
the existing source-of-truth.

## 1. Source-of-truth verification of suggested values

The R2 cell's canonical verification artifact is
[`verification_outputs/wave218-p3-kanzi-framework-wins.json`](../../verification_outputs/wave218-p3-kanzi-framework-wins.json).
The paired-t values reported by the verification are:

| Field | Value | Rounded (4 dp) |
|---|---|---|
| `baseline_mean_A` | 0.9027630950167146 | **0.9028 Å** |
| `framework_mean_A` | 0.8837987798290944 | **0.8838 Å** |
| `mean_diff_A` | −0.01896431518762014 | (paired diff) |
| `sd_diff_A` | 0.19155366904444077 | (paired SD) |
| `d_z` | −0.09900262042602999 | −0.0990 (Cohen's d, paired) |

**Finding: DeepSeek's suggested values contain a fact error.** DeepSeek wrote
"0.9020 Å" for the baseline column. The actual baseline mean is **0.9028 Å**
(rounded from 0.902763...). The framework value 0.8838 Å is correct.

If we adopted the optional format verbatim, the README would gain a fact
error in the Baseline column, contradicting the byte-stable verification
artifact. The fact-fix in Wave 265 P1 (R1 p ≈ 1.5e-08) was the **highest-priority
fix** of the third-round review precisely to avoid fact errors — adopting a
fact error here to gain cosmetic column consistency would invert that
priority.

Even with the typo corrected (0.9028 Å / 0.8838 Å), the absolute-number format
is **semantically misleading** for a paired-t design, because:

* The two values are not independent measurements of two systems — they are
  the **per-pair means of the same N=1000 records under two sampling
  regimes** (seed 42 paired). Reporting them as if they were independent
  baselines would imply a comparison that the test design does not support.
* The headline summary statistic for paired designs is the **paired
  Cohen's d (d_z)** on the per-pair differences, not the ratio of
  group means. The current `Baseline=reference / Framework=d_z` format
  captures this correctly: there is no single "baseline number" to
  report; the test is on the **differences**.
* R3 was reformatted in Wave 265 P2 from "-0.360/molecule / (seed 42 N=1000
  batched)" to exactly this `reference / d_z = −0.285` pattern for the
  same semantic reason (R3 is also a per-record paired d_z design).
  Keeping R2 in `reference / d_z` format preserves the **internal
  consistency between R2 and R3**, the two paired-design cells.

## 2. Consistency table — current vs. optional

| Cell | Design | Current format | Optional format | Verdict |
|---|---|---|---|---|
| R1 | Count-based single number (hmmscan_total_hits) | `158 \| 342 \| +116.46%` | n/a | KEEP |
| R2 | **Paired-t** (RMSD on same N=1000 records) | `reference \| d_z = −0.0990` | `0.9028 Å \| 0.8838 Å` | **KEEP reference/d_z** |
| R3 | **Per-record paired d_z** (fg_dev) | `reference \| d_z = −0.285` (Wave 265 P2) | n/a (already in this format) | KEEP |
| R4 | W₂ single number (2D FM ablation) | `2.85 \| 0.62` | n/a | KEEP |
| R5 | W₂ single number (2D FM ablation) | `2.31 \| 0.76` | n/a | KEEP |
| R5b | FID single number (CIFAR-10 RF) | `218.87 \| 122.18` | n/a | KEEP |
| R6 | FID d_z (uplift percentage) | `+0.224 \| +0.647 \| +189%` | n/a | KEEP |

The current table has **two column formats** by design:

1. **Absolute-number format** for single-number readouts (R1, R4, R5, R5b, R6)
   where the Baseline and Framework columns are independent measurements.
2. **`reference / d_z` format** for paired-design readouts (R2, R3) where the
   paired structure means there is no independent "baseline number" — only
   the paired effect size (Cohen's d_z) is the meaningful summary.

Mixing the formats across cells is correct, not an inconsistency: it tracks
the underlying experimental design.

## 3. Why DeepSeek marked the change "optional" (不是必须改)

DeepSeek's third-round review explicitly said:

> 但这取决于你是否想让"d_z"出现在 Δ 列。现在的格式（Baseline=reference,
> Framework=d_z）是可接受的，**不是必须改**。

Translation: "But this depends on whether you want 'd_z' to appear in the Δ
column. The current format (Baseline=reference, Framework=d_z) is
acceptable — **not required to change**."

The d_z currently appears in the Framework column (which serves as the
"comparison stat" column for paired designs). Moving the absolute numbers
into Baseline / Framework would require moving the d_z into the Δ column,
which would then leave the Δ column with redundant information (`d_z = −0.0990`
on a column semantically meant for raw difference, when paired designs don't
have a single raw difference to report — the per-pair diffs are what the
test runs on). This is a worse tradeoff than the current arrangement.

## 4. Decision

**KEEP** the current `reference / d_z` format for R2. No README edit.

Rationale:
1. DeepSeek's suggested values contain a typo (0.9020 vs. true 0.9028 Å) —
   adopting verbatim would introduce a fact error.
2. R2 is a paired-t design where "reference / d_z" is semantically correct;
   absolute-number format would mislead readers about the experimental design.
3. R3 was just aligned to `reference / d_z` in Wave 265 P2 for the same reason;
   keeping R2 in this format preserves R2 ↔ R3 internal consistency.
4. DeepSeek explicitly marked the change optional ("not required").
5. The current two-format table (absolute-number for single-readouts,
   `reference / d_z` for paired designs) tracks experimental design
   correctly.

## 5. Hard rules respected

- No framework source code changes.
- No vendored code touched.
- No README edit (decision is KEEP).
- D.4 30/30 PASS preserved (no test churn — audit doc only).
- mkdocs 0 warnings preserved (no nav edits).
- claims_consistency no drift (no claim-field change).
- No new internal IDs introduced.
- No numerical claim rewritten.

## 6. Verification

| Gate | Command | Result |
|---|---|---|
| D.4 byte-stable | `pytest tests/test_d4_regression_vectors.py` | (preserved — no code touched) |
| mkdocs strict | `mkdocs build --strict` | (preserved — no mkdocs touched) |
| claims_consistency | `python3 tools/check_claims_consistency.py` | (preserved — no claim changed) |
| R2 baseline column | `grep -n "R2.*0.9020" README.md` | 0 hits (typo NOT adopted) |
| R2 row format | `grep -n "R2.*reference.*d_z = −0.0990" README.md` | 1 hit (preserved) |
| git status post-write | `git status --short` | clean (audit doc only) |

## 7. Conclusion

Optional R2 row format change **declined**. The current `reference / d_z`
format is semantically correct for R2's paired-t design, internally
consistent with R3 (which was just reformatted to the same pattern in
Wave 265 P2), and avoids introducing a fact error that would arise from
adopting DeepSeek's typo'd values verbatim. Audit trail committed at
`docs/audit/wave265-p3-r2-format.md`.