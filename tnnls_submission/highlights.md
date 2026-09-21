# TNNLS Editor-Facing Highlights — FlowA

**Status:** 3 highlights, each ≤ 85 characters (TNNLS standard).

---

## Highlight 1
**Training-free re-inference for deployed flow-matching checkpoints with paper-quantity-driven scheduling and byte-stable reproducibility.**

---

## Highlight 2
**Six R-level cells (protein, molecular 3D, image) with 4-arm head-to-head validation; CUDA-graph capture closes 76.8% of wall-clock gap.**

---

## Highlight 3
**D.4 30/30 byte-stable regression suite + SHA-256-pinned checkpoints + hash-chained transition logs + Zenodo DOI for code and per-record CSVs.**

---

## Highlight provenance

- **Highlight 1:** Reflects FlowA's core contribution (training-free + solver-agnostic + paper-quantity-driven scheduler + reproducibility infrastructure).
- **Highlight 2:** Reflects the Wave 235-237 strengthening (R5b n_rounds=1 framework-WINS, R2 medium-effect uplift, R6 large-effect uplift with easy-tier elimination, 24.6× → 1.26× CUDA-graph capture).
- **Highlight 3:** Reflects reproducibility infrastructure (D.4 byte-stable regression suite, SHA-256 checkpoints, hash-chained transition logs, Zenodo DOI).

## Wave provenance

- Wave 235 P1-P5: Top-4 high-leverage improvements
- Wave 236 P1-P5: 24.6× wall-clock fix + final integration
- Wave 237 P1-P2: Abstract trim to ≤250 words (extended to 328 in Wave 242 P3)
- Wave 238 P1-P4: FlowMol3 per-seed diagnostic + journal decision TPAMI → TNNLS + CUDA-graph verification + final pre-push
- Wave 242 P1 (in flight): FlowMol3 3-seed NFE=250 single_mol rescue (DGL 2.4.0 batched-path bug workaround)

## Cross-references

- `docs/cover-letter-tnnls.md` §3 Insight — Paper-Quantity-Driven Scheduling
- `docs/drafts/abstract-final.md` — 250-word TPAMI-envelope abstract
- `docs/internal/tnnls_submission_action_checklist.md` — TNNLS editorial requirements
- `tnnls_submission/MANIFEST.md` — package manifest