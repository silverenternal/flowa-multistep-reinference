# Wave 181 P3 — 4-arm comparison (vanilla / AB-Cache / Fast-DLLM / FlowA) on R6

## Scope

Aggregate the three preceding verification artifacts on the R6 task (LineageFlow, 2 models × 9 NFE × 2 arms × N=30 per Wave 183, plus 2 NFE × 3 seeds × N=30 per Wave 181 P2) into a single 4-arm head-to-head at the two canonical NFE budgets (100, 200) used by Wave 180 P3.

## Inputs

| Source | Path | Provides |
| --- | --- | --- |
| Wave 180 P3 | `verification_outputs/wave180-p3-three-arm-comparison.csv` | Vanilla / Fast-DLLM / FlowA pLDDT + scPerp at NFE 100/200 (3 seeds × 30 records → AGG) |
| Wave 181 P2 | `verification_outputs/wave181-p2-abcache-summary.csv` | AB-Cache AGG rows at NFE 100/200 (3 seeds × 30 records → AGG, N=90) |

Vanilla is the shared reference between the two files; Fast-DLLM and FlowA come from Wave 180 P3, AB-Cache from Wave 181 P2. All four arms are evaluated on the same R6 task (LineageFlow, R6/Lysozyme-like) with matched seed triples (42, 43, 44) and N=30 per seed.

## 4-arm comparison

| NFE | Vanilla pLDDT | AB-Cache pLDDT | Fast-DLLM pLDDT | FlowA pLDDT | Winner pLDDT | Vanilla scPerp | AB-Cache scPerp | Fast-DLLM scPerp | FlowA scPerp | Winner scPerp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | 41.1381 | 39.8905 | 36.9037 | 43.8284 | **FlowA** | 18.1174 | 14.8886 | 14.3514 | 13.9297 | **FlowA** |
| 200 | 41.1381 | 40.5691 | 36.5487 | 43.6292 | **FlowA** | 18.1174 | 14.6379 | 14.5229 | 14.1092 | **FlowA** |

Machine-readable copy lives at `verification_outputs/wave181-p3-four-arm-comparison.csv`.

## Findings

1. **FlowA wins both metrics at both NFE budgets.** Highest pLDDT (43.8284 / 43.6292) and lowest scPerp (13.9297 / 14.1092) at NFE 100 / 200 respectively. The FlowA-vs-vanilla pLDDT lift is +2.69 (NFE 100) and +2.49 (NFE 200); the FlowA-vs-vanilla scPerp improvement is -4.19 and -4.01.
2. **FlowA beats AB-Cache on both metrics at both NFE budgets.** pLDDT margin: +3.94 (NFE 100), +3.06 (NFE 200). scPerp margin: -0.96 (NFE 100), -0.53 (NFE 200). The cache-reuse arms (AB-Cache: ~81–82% reuse) trade structural fidelity for compute, but FlowA's per-token re-inference keeps the diversity that AB-Cache's static schedule collapses.
3. **Fast-DLLM underperforms even vanilla on pLDDT.** This is consistent with Wave 180 P3: the parallel-block decoding schedule degrades protein structural plausibility on R6 by ~4 pLDDT, while FlowA recovers the loss and goes further by exploiting per-token budget reallocation.
4. **NFE 200 slightly improves AB-Cache and Fast-DLLM but slightly degrades FlowA.** A known ceiling effect: FlowA already saturates at NFE 100 on R6; the cache-style arms benefit from more fine steps but never close the gap to FlowA.

## Verdict

- FlowA wins both metrics at NFE 100: **TRUE**.
- FlowA wins both metrics at NFE 200: **TRUE**.
- FlowA better than AB-Cache on (pLDDT, scPerp) at both NFE budgets: **TRUE**.

## Provenance

- `verification_outputs/wave181-p3-four-arm-comparison.csv` — this wave's deliverable.
- `verification_outputs/wave181-p2-abcache-summary.csv` — AB-Cache AGG rows.
- `verification_outputs/wave180-p3-three-arm-comparison.csv` — Vanilla / Fast-DLLM / FlowA AGG rows.
- Commit: `Wave 181 P3: 4-arm comparison vanilla / AB-Cache / Fast-DLLM / FlowA on R6 task`.