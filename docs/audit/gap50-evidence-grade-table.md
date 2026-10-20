# GAP-50 — evidence-grade table (status, N, seeds, CI, artifact)

**Date:** 2026-10-19
**Author:** GAP-50 agent (USER AUTHORIZED, NO PUSH)
**Purpose:** one page that states, for every headline cell, **what was measured**,
**at what N / seed count**, **with what uncertainty**, and **what status label
the evidence supports**. Frozen surfaces untouched.
**Companions:** `docs/audit/gap55-code-level-hardening.md` (the driver-defect
audit that produced the 2026-10-19 rows).

Status vocabulary (from `AGENTS.md` §2.1):
`SUPPORTED` = significant + powered; `NOT_SIGNIFICANT` = powered but n.s.;
`UNDERPOWERED` = too few records to call; `REGRESSES` = framework hurts;
`DEFERRED` = env-blocked or compute-deferred.

---

## 1. Main table

| Cell | Model | Metric (direction) | N / seeds | Effect | 95% CI | p | Status | Artifact |
|---|---|---|---|---:|---|---:|---|---|
| **R1** | LineageFlow | `hmmscan_total_hits` (↑) | 1000 × 3 | +184 hits vs 158 (+116%) | — | p_bonf 1.0e-7 (single-seed era) | **UNDERPOWERED / config-conditional** | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/` |
| **R1 (gate-open)** | LineageFlow | hits (↑) | 1000 × 3 | legacy mean 257 vs baseline 158 | — | `d_z=4.97`; car `d_z=8.77`, p_bonf=1.0 | **NOT_SIGNIFICANT at R-level** | `docs/audit/gap40-lineageflow-classifier-aware-restart.md` |
| **R1 (NFE=150)** | LineageFlow | hits (↑) | **1000 × 1** | **+117 hits (+74.1 %)**; per-record **+0.1170** | **[+0.073, +0.160]** | paired bootstrap excludes 0 | **POWERED, single-seed; mechanism-unattributed** (GAP-45 pending) | `verification_outputs/gap55-r1-nfe150-n1000/` |
| **R2** | Kanzi | RMSD (↓) | 1000 × 1 | `d_z=−0.0990` | — | p_bonf 0.0018 | **SUPPORTED (small)** | `verification_outputs/wave218-p3-kanzi-framework-wins.json` |
| **R3** | FlowMol3 | `fg_dev` (↓) | **1000 × 1** | **−0.061** | **[−0.117, −0.001]** | 0.043 (boot); R-level α=0.00714 | **NOT_SIGNIFICANT (single seed)** | `verification_outputs/gap55-r3-full-smiles/` |
| **R3 (proxy, historical)** | FlowMol3 | REOS flag count (↓) | 200 → projected 1000 | `d_z=−0.285` (projected) | — | projected | **RETIRED** (proxy does not track `fg_dev`; observed +0.0021, p=0.25) | `verification_outputs/wave216-p1-r3-per-record.json` |
| **R5a** | 2D FM | W₂ (↓) | 10 seeds | \|δ\|=0.0091 | — | — | **TIE** (\|δ\| < 0.01 floor) | `verification_outputs/g1_deep_dive_q3_2026.json` |
| **R5b** | CIFAR-10 RF | FID (↓) | 200 × 3 | +52.33% (framework worse) | — | p_bonf 2.97e-3 | **REGRESSES** (honest negative) | `docs/audit/wave280-p-cifar-sweep-result.md` |
| **R5c** | MNIST FM | projection-FID (↓) | **1000 × 3** | **+9.52 %** (cosine); codim +12.87, evid +10.34 | record-level boot excludes 0 in 9/9 | — | **REGRESSES at true NFE=50** | `verification_outputs/gap57-equal-nfe-ladder-n1000/` |
| **R5c (boundary)** | MNIST FM, `w16e1_5k` | projection-FID (↓) | **1000 × 3** | **−9.37 %** (cosine); codim/evid tie | excludes 0, 3/3 draws | — | **SUPPORTED at matched NFE, model-conditional** (baseline FID 24.5) | same |
| **R5c (historical)** | MNIST FM | projection-FID (↓) | 1000 × 1 | −28.43% | — | 3.95e-11 | **RETIRED** (smoke ckpt; arms at 25/48/25 NFE) | `verification_outputs/wave191-p3-mnist-n1000.json` |
| **R6 (scPerp)** | LineageFlow | scPerplexity (↓) | **3000 × 3** | **−3.68** | — | `d_z=−0.8393` | **SUPPORTED** (3/3 seeds, all tiers) | `verification_outputs/gap31-r6-live-uplift/gap31_summary.json` |
| **R6 (pLDDT, hard)** | LineageFlow | pLDDT (↑) | 990 × 3 | +15.01 | — | `d_z=+1.1211` | **SUPPORTED (tier-conditional)** | same |
| **R6 (pLDDT, pooled)** | LineageFlow | pLDDT (↑) | 3000 × 3 | +2.64 | — | `d_z=+0.1466` | **NOT_SIGNIFICANT** | same |
| **R6 (counterfactual)** | LineageFlow | pLDDT (↑) | 1000 | +0.2235 | — | 2.98e-12 | **RETIRED as headline** (not a live run) | `verification_outputs/wave225-p4-k6-tier-aware.json` |
| **K1** | FlowMol3 | pb_validity (↑) | 200 × 3 | real-blend `d=+0.92` | — | 0.252 | **NOT_SIGNIFICANT** | `docs/audit/gap39-flowmol3-real-restart-blend.md` |
| **K4** | LineageFlow | hits (long-bias) | 100 × 3 | 12–22 non-zero | — | — | **POWERED** | `docs/audit/wave280-p-k4k5-sweep-result.md` |
| **K5** | LineageFlow | hits (uniform prior) | 100 × 3 | +1.33 hits (+8.9%) | — | 0.184 | **SUPPORTED-WITH-CAVEAT** | same |
| **K7** | LineageFlow | novelty | 1000 × 3 | 12.6× **less** novel | — | — | **REGRESSES (direction inverted)** | `docs/audit/gap48-k7-two-arm-novelty.md` |

---

## 2. What changed on 2026-10-19 (GAP-55)

Three rows moved from "weak positive" to a defensible label:

1. **R5c → REGRESSES.** Equalising the total NFE to 50 on the production
   checkpoint makes all three arms significantly worse. The old −28.43% was
   the smoke checkpoint with arms at 25/48/25 NFE. This is now an honest
   negative, not a win.
2. **R3 → measured, single-seed nominal.** The N=1000 `fg_dev` is −0.061 with
   a CI that excludes 0, but p=0.043 does not clear the R-level Bonferroni
   floor. The historical `d_z=−0.285` was a projection of a 200-record proxy
   whose sign does not even match the aggregate metric.
3. **R6 → live axis.** The counterfactual `+0.2235` is retired as the
   headline; the live scPerplexity `d_z=−0.84` (3 seeds, N=3000, all tiers) is
   the evidence.

## 3. Honest reading
- **One tier-conditional positive:** R6 hard-tier pLDDT.
- **One small significant positive:** R2 (`d_z=−0.099`).
- **Two honest negatives:** R5b (CIFAR), R5c (MNIST at true NFE=50).
- **One near-miss awaiting seeds:** R3 (−0.061, CI excludes 0, 1 seed).
- **Everything else** is NOT_SIGNIFICANT, UNDERPOWERED, or direction-inverted.

The paper's defensible core is therefore: the **framework/system contribution**
(typed contracts, byte-stable gates, theory) plus **one live large-effect cell**
(R6 scPerplexity) plus **one tier-conditional mechanism result** (R6 hard-tier
pLDDT), with the negative cells reported as boundaries. It is not a SOTA table.

## 4. Artifact index

```
verification_outputs/gap55-r5c-equal-nfe/sweep_summary.json
verification_outputs/gap55-r3-full-smiles/flowmol3_n1000_sweep_gap55r3_q4_2026.json
verification_outputs/gap55-r3-full-smiles/per_record_fg_dev.json
verification_outputs/gap55-r1-gate-open-n200/seed42/manifest.json
verification_outputs/gap55-r1-nfe150-n1000/          (in flight)
verification_outputs/gap31-r6-live-uplift/gap31_summary.json
verification_outputs/wave225-p4-k6-tier-aware.json
verification_outputs/wave191-p3-mnist-n1000.json
verification_outputs/wave216-p1-r3-per-record.json
```
