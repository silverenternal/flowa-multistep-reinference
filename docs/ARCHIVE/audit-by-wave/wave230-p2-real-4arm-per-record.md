# Wave 230 P2 — Real 4-arm per-record paired analysis (closes Wave 229 P1 gap)

**Date:** 2026-09-21
**Branch:** main (HEAD `5fefe77`)
**Goal:** Produce REAL per-record paired-t for all 16 4-arm cells (4 baselines x
2 NFE x 2 metrics), superseding Wave 229 P1's bootstrap projection.

## 1. Background: Why Wave 229 P1 needed a replacement

DeepSeek flagged that Wave 229 P1's "16/16 closes" used **bootstrap projection**,
not real per-record paired data. Specifically:

* Wave 229 P1 sampled per-record values from within-seed Gaussian distributions
  parameterized by the per-seed mean and std in the existing trackb CSVs.
* This bootstrap gave a per-record d_z that equaled the per-seed d_z (sample-
  size-invariant Cohen's d_z).
* The result was a closing rate that **overstated** the framework's per-record
  effects.

Specifically, Wave 229 P1 reported:

| Bootstrap verdict (Wave 229 P1) | n cells |
|---------------------------------|---------|
| SUPPORTED | 3 |
| REGRESSES | 7 |
| UNDERPOWERED | 6 |
| TIE | 0 |

The 7 REGRESSES were particularly concerning because they implied framework
LOSSES at per-record granularity against FastDLLM, AB-Cache, LeDiFlow.

## 2. New data source (no fresh GPU sweep required)

During the audit, we discovered that Wave 196 Track B actually **wrote
per-record metrics.jsonl files** to:

```
/tmp/w196/track_b/eval/<arm>_nfe<NFE>_seed<SEED>/foldability/metrics.jsonl
```

Each file contains 10 rows (q0..q9) with one record per row:

```json
{
  "qid": "q0",
  "header": "framework_seed0|family=PF00005.27",
  "length": 64,
  "plddt_mean": 41.85,
  "sc_perplexity": 11.56,
  ...
}
```

* 5 arms x 2 NFE x 30 seeds = 300 cells (10 records/seed = 3000 records)
* lediflow_nfe100_seed65 missing (empty foldability/ directory)
  -> 299 cells = 2990 records (290 records for lediflow nfe100 cells)
* Records are paired across arms by `(seed, qid)` — same Pfam family + length
  profile across arms (verified: vanilla q0 = flowa q0 = fastdllm q0 = ...
  = PF00005.27 family).

This is real OmegaFold foldability + ESM-IF self-consistency per-record data
from the Wave 196 Track B run. **No GPU sweep was needed for this Wave 230 P2.**

## 3. Methodology

Per-record pairing strategy: pair baseline_arm (vanilla/fastdllm/abcache/
lediflow) and framework_arm (FlowA) by `(seed, qid)`. Each pair contributes one
`paired_diff = framework_value - baseline_value` to the per-record array.

Statistical test: two-sided paired t-test on per-record paired diffs
(`framework - baseline`). df = n_pairs - 1.

Per-cell:
* n_pairs = up to 30 seeds x 10 records = 300 (290 for lediflow nfe100)
* df = n_pairs - 1 = 299 (or 289)
* Bonferroni alpha = 0.05 / 16 = 0.003125

Verdict precedence (matches Wave 229 P1):

1. TIE — |d_z| < 1e-9 (zero effect)
2. SUPPORTED — Bonferroni p < alpha AND d_z in framework-WINS direction
3. REGRESSES — Bonferroni p < alpha AND d_z in framework-LOSS direction
4. UNDERPOWERED — fallback (p >= alpha)

## 4. Per-cell results (real per-record)

| cell | verdict | n_pairs | d_z | mean_diff | p_bonf |
|------|---------|---------|------|-----------|--------|
| vanilla_pLDDT_NFE50 | UNDERPOWERED | 300 | +0.0249 | +0.45 | 1.0 |
| vanilla_pLDDT_NFE100 | UNDERPOWERED | 300 | +0.0234 | +0.43 | 1.0 |
| vanilla_scPerplexity_NFE50 | **SUPPORTED** | 300 | **-0.990** | **-3.87** | **3.5e-45** |
| vanilla_scPerplexity_NFE100 | **SUPPORTED** | 300 | **-0.975** | **-3.86** | **3.6e-44** |
| fastdllm_pLDDT_NFE50 | UNDERPOWERED | 300 | -0.078 | -0.95 | 1.0 |
| fastdllm_pLDDT_NFE100 | UNDERPOWERED | 300 | -0.094 | -1.20 | 1.0 |
| fastdllm_scPerplexity_NFE50 | UNDERPOWERED | 300 | +0.008 | +0.03 | 1.0 |
| fastdllm_scPerplexity_NFE100 | UNDERPOWERED | 300 | +0.009 | +0.03 | 1.0 |
| abcache_pLDDT_NFE50 | UNDERPOWERED | 300 | -0.031 | -0.51 | 1.0 |
| abcache_pLDDT_NFE100 | UNDERPOWERED | 300 | -0.043 | -0.73 | 1.0 |
| abcache_scPerplexity_NFE50 | UNDERPOWERED | 300 | -0.068 | -0.22 | 1.0 |
| abcache_scPerplexity_NFE100 | UNDERPOWERED | 300 | -0.029 | -0.09 | 1.0 |
| lediflow_pLDDT_NFE50 | UNDERPOWERED | 300 | -0.069 | -1.17 | 1.0 |
| lediflow_pLDDT_NFE100 | UNDERPOWERED | 290 | -0.056 | -0.97 | 1.0 |
| lediflow_scPerplexity_NFE50 | UNDERPOWERED | 300 | +0.075 | +0.24 | 1.0 |
| lediflow_scPerplexity_NFE100 | UNDERPOWERED | 290 | +0.052 | +0.17 | 1.0 |

**Verdict distribution (REAL per-record):**
* SUPPORTED: **2/16** (vanilla scPerplexity at both NFE; p < 1e-44)
* REGRESSES: **0/16**
* UNDERPOWERED: **14/16**

## 5. Comparison with Wave 229 P1 bootstrap

The 7 REGRESSES from the bootstrap projection were **bootstrap artifacts**, not
real per-record effects. The bootstrap d_z values were systematically 2-4x
larger than real per-record d_z values, because:

1. Bootstrap projects per-seed d_z to per-record by sampling within-seed noise
   with the per-seed d_z preserved (sample-size-invariant Cohen's d_z).
2. The bootstrap underestimates per-record variance (it treats within-seed
   noise as the per-record noise).
3. Real per-record variance is much higher than within-seed variance because
   records differ in length, family, and difficulty.

| cell | d_z (bootstrap) | d_z (real) | verdict_229 | verdict_230 |
|------|----------------|------------|-------------|-------------|
| vanilla_pLDDT_NFE50 | -0.012 | +0.025 | UNDERPOWERED | UNDERPOWERED |
| vanilla_pLDDT_NFE100 | -0.016 | +0.023 | UNDERPOWERED | UNDERPOWERED |
| vanilla_scPerplexity_NFE50 | **-2.082** | -0.990 | SUPPORTED | SUPPORTED |
| vanilla_scPerplexity_NFE100 | **-2.103** | -0.975 | SUPPORTED | SUPPORTED |
| fastdllm_pLDDT_NFE50 | **-0.247** | -0.078 | REGRESSES | UNDERPOWERED |
| fastdllm_pLDDT_NFE100 | **-0.289** | -0.094 | REGRESSES | UNDERPOWERED |
| abcache_pLDDT_NFE50 | **-0.127** | -0.031 | REGRESSES | UNDERPOWERED |
| abcache_pLDDT_NFE100 | **-0.161** | -0.043 | REGRESSES | UNDERPOWERED |
| abcache_scPerplexity_NFE50 | -0.145 | -0.068 | SUPPORTED | UNDERPOWERED |
| lediflow_pLDDT_NFE50 | **-0.250** | -0.069 | REGRESSES | UNDERPOWERED |
| lediflow_pLDDT_NFE100 | **-0.216** | -0.056 | REGRESSES | UNDERPOWERED |
| lediflow_scPerplexity_NFE50 | +0.130 | +0.075 | REGRESSES | UNDERPOWERED |

**Verdict switch count: 8/16 cells** (1 SUPPORTED → UNDERPOWERED, 7 REGRESSES →
UNDERPOWERED). Bootstrap was an unreliable estimator of per-record d_z because
it ignored per-record variance inflation.

## 6. Honest interpretation

* **Framework vs Vanilla (no distillation control):** Framework wins on
  scPerplexity at per-record granularity (d_z ≈ -0.99, p < 1e-44, both NFE).
  Framework is statistically indistinguishable from Vanilla on pLDDT
  (d_z ≈ +0.025, UNDERPOWERED). This is the same conclusion as Wave 196 P2
  per-seed analysis but with much stronger statistical evidence (df=299 vs df=29).

* **Framework vs FastDLLM / AB-Cache / LeDiFlow:** Framework is statistically
  indistinguishable on both metrics at per-record granularity. The 14
  UNDERPOWERED cells are NOT framework LOSSES; they're cells where the
  framework effect (if any) is too small to detect at df=299. This is more
  honest than the bootstrap's "7 REGRESSES" reading.

* **Per-record variance inflation:** The 2-4x larger d_z in bootstrap vs real
  per-record data is consistent with per-record variance being roughly 4-16x
  larger than per-seed variance (since records differ in length, family,
  difficulty). This is a known issue with per-seed aggregate → per-record
  reframing that Wave 228 P1 documented.

## 7. Output files

* `verification_outputs/wave230-p2-real-4arm-per-record.csv` — 16-row per-cell
  table with `data_kind = "real_per_record_paired"`.
* `verification_outputs/wave230-p2-real-4arm-per-record.json` — full payload with
  per-row detail and methodology block.
* `verification_outputs/wave230-p2-real-4arm-<baseline>-nfe<N>-<metric>-paired.jsonl`
  — 16 per-cell per-record paired diffs (one row per record).
* `tools/wave230_p2_real_4arm_per_record.py` — the analyzer script.

## 8. Paper implications

* **CLM-061 (FlowA vs vanilla):** Strengthened. Real per-record data confirms
  the per-seed finding (vanilla scPerplexity SUPPORTED, p < 1e-44 with df=299).

* **CLM-061 (FlowA vs FastDLLM/AB-Cache/LeDiFlow):** **Updated**. The 7
  REGRESSES from Wave 229 P1 bootstrap are bootstrap artifacts and should be
  removed. Real per-record data shows the framework is statistically
  indistinguishable from these baselines on per-record metrics. Honest reading:
  "framework-does-not-regress" (not "framework-wins-on-most-cells").

* **Paper §6 "per-record analysis" claim:** Now backed by REAL per-record data,
  not bootstrap projection. The bootstrap's 16/16 closure was misleading.

* **A_g / L_emp gap (DeepSeek critique #3):** Not affected. This Wave 230 P2
  addresses only the per-record gap (DeepSeek critique #1).

## 9. Limitations and follow-up

* **N=1000 sweep was NOT needed** — the existing Wave 196 Track B metrics.jsonl
  files provided sufficient per-record data (300 records per cell, df=299).
  The bootstrap projection's "12-20 GPU-h deferred" recommendation was based on
  the assumption that per-record data did not exist; this Wave 230 P2 shows
  it does exist.

* **Coverage gap:** lediflow nfe100 has 29/30 seeds (n=290 pairs, df=289) due
  to missing seed65. All other cells use all 30 seeds (n=300 pairs, df=299).

* **Open questions (not addressed by this Wave):**
  - B_g = 0.0 implementation bug (DeepSeek critique #2)
  - A_g vs L_emp 41x gap theoretical explanation (DeepSeek critique #3)
  - These are out of scope for Wave 230 P2; assigned to Wave 230 P3 and P4.

## 10. Wall-time accounting

* Real per-record extraction from existing JSONL: ~5 seconds (pure I/O)
* Per-record paired-t computation: <1 second (numpy + scipy)
* JSONL output write: <1 second
* Total: ~10 seconds (CPU-only)

This is significantly less than the 12-20 GPU-h originally estimated for a
fresh per-record sweep, because the data already existed in the Wave 196
Track B eval pipeline.

## 11. References

* Wave 196 P2 — trackb CSVs from per-seed aggregates of 10 records each
  (`docs/audit/wave196-p2-4arm-n30.md`)
* Wave 228 P1 — per-record coverage check that documented the gap
  (`verification_outputs/wave228-p1-4arm-per-record-coverage.json`)
* Wave 229 P1 — bootstrap projection that this Wave 230 P2 supersedes
  (`verification_outputs/wave229-p1-4arm-per-record-sweep.json`)
* Cohen 1988 §2.4 — paired t-test post-hoc power
* Bonferroni 1935 — multiple-testing correction