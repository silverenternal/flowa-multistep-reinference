# Composite axis byte-stable improvements (3/3 Tier 3 models)

**Summary:** Framework improves internal composite axis on ALL 3 Tier 3 models with
byte-stable reproducibility.

| Model | Composite | N (cells) | sigma within seed | Source |
|---|---|---:|---:|---|
| Kanzi | +0.1695 | 18 (3 seeds x 6 NFE 10-2000) | 0.000000 | verification_outputs/kanzi_nfe_scan_q4_2026.json |
| LineageFlow | +0.2083 | 8 (3 seeds x 3 NFE 10-200) | byte-stable | verification_outputs/lineageflow_v2_aggregated_q4_2026.json |
| FlowMol3 | +0.1182 | 3 (byte-identical runs) | 0 | Wave 74 F5 (3-run byte-identical at seed=42, NFE=50, n_molecules=10) |

**Composite axis definition (per docs/CONSOLIDATED_RESULTS.md):**
composite = 0.40 * phi1_entropy_reduction_normalised + 0.35 * phi2_max_prob_delta + 0.25 * phi3_argmax_turnover_signed

**Wave 89 verdict:** Framework value-add lives on this axis, NOT always on the paper-metric axis.
**Wave 89 cross-reference:** docs/audit/wave89-phase1-final.md (per-paper-claim FINAL verdict table).
