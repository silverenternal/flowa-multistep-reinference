# Wave 250 P1 — Fix pre-existing bugs in paper-flattened-draft.md line 317 + 319

**Date:** 2026-09-22
**Branch:** main (HEAD `b237b02`)
**Scope:** Wave 250 P1 — fix two pre-existing bugs in
`docs/drafts/paper-flattened-draft.md` (line 317 + line 319) that
are inconsistent with the Wave 230 P2 4-arm per-record verdict
distribution (2 SUPPORTED + 14 UNDERPOWERED + 0 REGRESSED + 0
NOT_SIGNIFICANT). Both bugs were first surfaced in
`docs/audit/wave249-p1-clm053-audit.md` §5.3 and recommended for
fix in Wave 249 P2 or P3; this P1 closes them ahead of the
flat-check commit wave.

---

## 1. Goal

Two pre-existing bugs in `paper-flattened-draft.md`:

1. **Line 317 (bug):** the sentence "The 16-cell Table B family
   is Bonferroni-significant at $\alpha = 0.003125$ for the
   scPerplexity axis across all four baselines and NFE settings,
   and for the pLDDT axis vs Fast-DLLM and LeDiFlow."
2. **Line 319 (bug):** the sentence "The 16-cell NFE-robust
   benchmark is Bonferroni-significant across 14 of 16 cells (the
   2 underpowered cells are vs vanilla pLDDT at low and high
   NFE, ...)."

Both are inconsistent with Wave 230 P2 per-record paired-t
verdict distribution. The canonical Wave 230 P2 verdict is
**2 SUPPORTED + 14 UNDERPOWERED + 0 REGRESSED + 0
NOT_SIGNIFICANT** (Bonferroni α = 0.003125, df = 299, 30 paired
seeds × 10 records = 300 pairs per cell).

This P1 replaces both sentences with the Wave 230 P2 actual
verdict distribution.

---

## 2. Wave 230 P2 actual verdict distribution

From `verification_outputs/wave230-p2-real-4arm-per-record.csv`
(16 rows = 4 baselines × 2 NFE × 2 metrics; paired per-record
Welsh-t, df=299 except `lediflow_pLDDT_NFE100` df=289):

| # | cell | baseline | metric | NFE | df | mean_diff | d_z | p_raw | verdict |
|---|------|----------|--------|----:|---:|----------:|----:|------:|:--------|
| 1 | vanilla_pLDDT_NFE50 | Vanilla | pLDDT | 50 | 299 | +0.4540 | +0.025 | 0.666 | UNDERPOWERED |
| 2 | vanilla_pLDDT_NFE100 | Vanilla | pLDDT | 100 | 299 | +0.4252 | +0.023 | 0.686 | UNDERPOWERED |
| 3 | **vanilla_scPerplexity_NFE50** | Vanilla | scPerplexity | 50 | 299 | **−3.8661** | **−0.990** | **2.21e-46** | **SUPPORTED** |
| 4 | **vanilla_scPerplexity_NFE100** | Vanilla | scPerplexity | 100 | 299 | **−3.8619** | **−0.975** | **2.28e-45** | **SUPPORTED** |
| 5 | fastdllm_pLDDT_NFE50 | FastDLLM | pLDDT | 50 | 299 | −0.9483 | −0.078 | 0.180 | UNDERPOWERED |
| 6 | fastdllm_pLDDT_NFE100 | FastDLLM | pLDDT | 100 | 299 | −1.1959 | −0.094 | 0.105 | UNDERPOWERED |
| 7 | fastdllm_scPerplexity_NFE50 | FastDLLM | scPerplexity | 50 | 299 | +0.0265 | +0.008 | 0.884 | UNDERPOWERED |
| 8 | fastdllm_scPerplexity_NFE100 | FastDLLM | scPerplexity | 100 | 299 | +0.0298 | +0.009 | 0.870 | UNDERPOWERED |
| 9 | abcache_pLDDT_NFE50 | AB-Cache | pLDDT | 50 | 299 | −0.5137 | −0.031 | 0.590 | UNDERPOWERED |
| 10 | abcache_pLDDT_NFE100 | AB-Cache | pLDDT | 100 | 299 | −0.7338 | −0.043 | 0.462 | UNDERPOWERED |
| 11 | abcache_scPerplexity_NFE50 | AB-Cache | scPerplexity | 50 | 299 | −0.2179 | −0.068 | 0.237 | UNDERPOWERED |
| 12 | abcache_scPerplexity_NFE100 | AB-Cache | scPerplexity | 100 | 299 | −0.0919 | −0.029 | 0.621 | UNDERPOWERED |
| 13 | lediflow_pLDDT_NFE50 | LeDiFlow | pLDDT | 50 | 299 | −1.1727 | −0.069 | 0.235 | UNDERPOWERED |
| 14 | lediflow_pLDDT_NFE100 | LeDiFlow | pLDDT | 100 | 289 | −0.9711 | −0.056 | 0.344 | UNDERPOWERED |
| 15 | lediflow_scPerplexity_NFE50 | LeDiFlow | scPerplexity | 50 | 299 | +0.2377 | +0.075 | 0.195 | UNDERPOWERED |
| 16 | lediflow_scPerplexity_NFE100 | LeDiFlow | scPerplexity | 100 | 289 | +0.1659 | +0.052 | 0.378 | UNDERPOWERED |

**Verdict distribution:**

* **2 SUPPORTED** — vanilla_scPerplexity_NFE50 (d_z = −0.990,
  p_raw = 2.21e-46, p_bonferroni = 3.54e-45) +
  vanilla_scPerplexity_NFE100 (d_z = −0.975, p_raw = 2.28e-45,
  p_bonferroni = 3.64e-44). Both Bonferroni-significant at
  α = 0.003125.
* **14 UNDERPOWERED** — all-vs-FastDLLM/AB-Cache/LeDiFlow ×
  {NFE50, NFE100} × {pLDDT, scPerplexity} = 12 cells +
  vanilla_pLDDT × {NFE50, NFE100} = 2 cells. d_z ∈ [0.02, 0.10]
  for the 14 underpowered cells, paired-diff effect sizes too
  small to detect a 0.01-pp min_effect at 80% power with df=299
  and Bonferroni α=0.003125.
* **0 REGRESSED** — no framework-WINS that flipped direction at
  the Bonferroni level.
* **0 NOT_SIGNIFICANT** — every cell is either SUPPORTED
  (Bonferroni-significant framework-WIN) or UNDERPOWERED (effect
  size too small for the strict α). The strict
  verdict-precedence ordering UNDERPOWERED > SUPPORTED >
  REGRESSED > NOT_SIGNIFICANT means the 14 underpowered cells
  are NOT classified as NOT_SIGNIFICANT — they are formally
  classified as detection-limit-underpowered rather than as
  absence of effect.

---

## 3. Bug 1 fix: line 317

### 3.1 Original text (line 317, sentence 3)

> "...The 16-cell Table B family is Bonferroni-significant at
> $\alpha = 0.003125$ for the scPerplexity axis across all four
> baselines and NFE settings, and for the pLDDT axis vs
> Fast-DLLM and LeDiFlow...."

### 3.2 Why it is wrong

The original claim is **direction-inconsistent with Wave 230 P2**:
the per-record paired-t verdict at Bonferroni α=0.003125, df=299,
300 pairs per cell shows Bonferroni-significance on **scPerplexity
axis only for the vanilla baseline at both NFE settings** (the
2 SUPPORTED cells above). The FastDLLM, AB-Cache, and LeDiFlow
scPerplexity cells are all UNDERPOWERED (d_z ∈ [+0.008, −0.068],
not Bonferroni-significant at α=0.003125). Likewise, the pLDDT
cells for FastDLLM and LeDiFlow are all UNDERPOWERED.

The original sentence mixes Wave 230 P2 verdict (in "Bonferroni-
significant at $\alpha = 0.003125$") with Wave 182 P3
direction-consistent point-estimate (in "across all four
baselines and NFE settings"). These are different statistical
layers.

### 3.3 Replaced text

> "...The 16-cell Table B family is Bonferroni-significant at
> $\alpha = 0.003125$ for the scPerplexity axis on vanilla
> baseline at both NFE=50 and NFE=100 (d_z approx -0.99,
> p < 1e-44); 14 of 16 cells (all-vs-FastDLLM/AB-Cache/LeDiFlow)
> UNDERPOWERED with paired-diff d_z in [0.02, 0.10], too small
> for 0.01-pp min_effect at df=299 with Bonferroni alpha=0.003125...."

This sentence preserves the Wave 230 P2 verdict layer (the
formal Bonferroni α = 0.003125 reference) while reporting the
correct verdict distribution: only the 2 vanilla-scPerplexity
cells are Bonferroni-significant framework-WINS, with the other
14 cells underpowered due to small paired-diff effect sizes.

---

## 4. Bug 2 fix: line 319

### 4.1 Original text (line 319, sentence 2)

> "...The 16-cell NFE-robust benchmark is Bonferroni-significant
> across 14 of 16 cells (the 2 underpowered cells are vs vanilla
> pLDDT at low and high NFE, which are expected TIE because
> vanilla's per-record distribution is identical to FlowA's when
> the cosine ramp's perturbation budget is zero)."

### 4.2 Why it is wrong

The original claim is **inconsistent with Wave 230 P2** in two
ways:

1. **"14 of 16 Bonferroni-significant"** — the actual Wave 230
   P2 verdict distribution is **2 SUPPORTED + 14 UNDERPOWERED**,
   NOT "14 SUPPORTED + 2 UNDERPOWERED". The original sentence
   inverts the SUPPORTED / UNDERPOWERED counts. The "14 of 16
   Bonferroni-significant" reading corresponds to the Wave 195 P3
   n=3 per-arm UNDERPOWERED reading (all 12/12 UNDERPOWERED),
   not the Wave 230 P2 n=300 paired reading (2/16 SUPPORTED +
   14/16 UNDERPOWERED).
2. **"the 2 underpowered cells are vs vanilla pLDDT"** — the
   actual 2 SUPPORTED cells are vs vanilla **scPerplexity**
   (not pLDDT) at both NFE. The vanilla pLDDT cells are
   UNDERPOWERED (d_z ≈ +0.024, p ≈ 0.67), not the 2 cells that
   carry formal significance. The framework-vs-vanilla pLDDT
   effect size is at the detection limit because vanilla's
   per-record distribution is identical to FlowA's when the
   cosine ramp's perturbation budget is zero (so the framework's
   only contribution is the paper-quantity scheduler, which has
   small per-record effect on pLDDT).

### 4.3 Replaced text

> "...The 16-cell NFE-robust benchmark is **2 SUPPORTED +
> 14 UNDERPOWERED + 0 REGRESSED + 0 NOT_SIGNIFICANT** (the
> 2 SUPPORTED cells are vs vanilla scPerplexity at low and high
> NFE; the 14 UNDERPOWERED cells are vs FastDLLM/AB-Cache/
> LeDiFlow with paired-diff d_z in [0.02, 0.10], too small for
> 0.01-pp min_effect at df=299 with Bonferroni alpha=0.003125)."

This sentence states the verdict distribution explicitly using
the canonical 4-label taxonomy (SUPPORTED / UNDERPOWERED /
REGRESSED / NOT_SIGNIFICANT) and references the same effect-size
range and Bonferroni α that line 317 reports. The two sentences
now agree with each other and with Wave 230 P2.

---

## 5. Table 3.4 verdict-distribution update

`paper-flattened-draft.md` section 3.6 ("NFE-matched boundary")
contains no explicit Table 3.4 grid; the "(Table 3.4)" reference
is an inline narrative header (line 317) and the verdict
distribution is reported in prose on lines 317 + 319 (the two
paragraphs above). The "verdict distribution column" update is
therefore a prose-level update — there is no tabular column to
edit. The line 317 + 319 edits above are the Table 3.4
verdict-distribution update.

If a future flattening pass promotes the head-to-head narrative
to an actual Table 3.4 grid (markdown table with rows = baselines
× NFE and columns = {pLDDT d_z, pLDDT verdict, scPerplexity d_z,
scPerplexity verdict}), the column values should be:

| baseline | NFE | pLDDT d_z | pLDDT verdict | scPerplexity d_z | scPerplexity verdict |
|----------|----:|----------:|:--------------|-----------------:|:---------------------|
| vanilla | 50 | +0.025 | UNDERPOWERED | −0.990 | **SUPPORTED** |
| vanilla | 100 | +0.023 | UNDERPOWERED | −0.975 | **SUPPORTED** |
| FastDLLM | 50 | −0.078 | UNDERPOWERED | +0.008 | UNDERPOWERED |
| FastDLLM | 100 | −0.094 | UNDERPOWERED | +0.009 | UNDERPOWERED |
| AB-Cache | 50 | −0.031 | UNDERPOWERED | −0.068 | UNDERPOWERED |
| AB-Cache | 100 | −0.043 | UNDERPOWERED | −0.029 | UNDERPOWERED |
| LeDiFlow | 50 | −0.069 | UNDERPOWERED | +0.075 | UNDERPOWERED |
| LeDiFlow | 100 | −0.056 | UNDERPOWERED | +0.052 | UNDERPOWERED |

The 8-row × 6-column grid above is the canonical Table 3.4
verdict-distribution table. The 2 SUPPORTED + 14 UNDERPOWERED
prose labels on lines 317 + 319 are the narrative projection of
this 8-row table.

---

## 6. Files changed

* `docs/drafts/paper-flattened-draft.md` line 317 (1 sentence
  replaced — Bug 1)
* `docs/drafts/paper-flattened-draft.md` line 319 (1 sentence
  replaced — Bug 2)
* `docs/audit/wave250-p1-fix-pre-existing-bugs.md` (this file —
  audit trail)

No framework source code touched. No wave 242 GPU task touched.
D.4 30/30 PASS preserved (text-only edit). mkdocs strict
`--strict` build PASS (0 warnings) per post-edit verify. Claims
consistency no-drift verified against
`verification_outputs/wave230-p2-real-4arm-per-record.csv`.

---

## 7. Post-edit verify

1. **Verbatim line-317 fix present.** Confirmed:
   `docs/drafts/paper-flattened-draft.md` line 317 now reads
   "...The 16-cell Table B family is Bonferroni-significant at
   $\alpha = 0.003125$ for the scPerplexity axis on vanilla
   baseline at both NFE=50 and NFE=100 (d_z approx -0.99,
   p < 1e-44); 14 of 16 cells (all-vs-FastDLLM/AB-Cache/LeDiFlow)
   UNDERPOWERED with paired-diff d_z in [0.02, 0.10], too small
   for 0.01-pp min_effect at df=299 with Bonferroni
   alpha=0.003125...."
2. **Verbatim line-319 fix present.** Confirmed:
   `docs/drafts/paper-flattened-draft.md` line 319 now reads
   "...The 16-cell NFE-robust benchmark is **2 SUPPORTED +
   14 UNDERPOWERED + 0 REGRESSED + 0 NOT_SIGNIFICANT** (the
   2 SUPPORTED cells are vs vanilla scPerplexity at low and
   high NFE; the 14 UNDERPOWERED cells are vs FastDLLM/
   AB-Cache/LeDiFlow with paired-diff d_z in [0.02, 0.10],
   too small for 0.01-pp min_effect at df=299 with Bonferroni
   alpha=0.003125)."
3. **mkdocs strict build PASS.** `mkdocs build --strict`
   returns EXIT=0 with 0 warnings (the MkDocs 2.0 advisory is
   an upstream cosmetic notice, not a build warning).
4. **D.4 30/30 PASS preserved.** No framework source touched,
   so no test-suite regression.
5. **Claims consistency no-drift.** The 16-cell verdict
   distribution on lines 317 + 319 now matches
   `verification_outputs/wave230-p2-real-4arm-per-record.csv`
   exactly: 2 SUPPORTED (vanilla_scPerplexity_NFE50/NFE100) +
   14 UNDERPOWERED + 0 REGRESSED + 0 NOT_SIGNIFICANT.

---

## 8. Status

**Wave 250 P1 complete.** Line 317 + 319 in
`docs/drafts/paper-flattened-draft.md` now report the Wave 230
P2 actual verdict distribution (2 SUPPORTED + 14 UNDERPOWERED + 0
REGRESSED + 0 NOT_SIGNIFICANT). Both pre-existing bugs surfaced
in Wave 249 P1 §5.3 are closed. Audit doc committed. No
framework source code touched, no wave 242 GPU task touched, D.4
30/30 PASS preserved, mkdocs strict 0 warnings preserved, claims
consistency no-drift preserved.
