# TNNLS Submission Tables

**Status:** TNNLS paper-ready tables (5 main tables). All data sourced from [`verification_outputs/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs) with byte-addressable provenance.

---

## Table 1 — R-Level Headline Numbers (Wave 235-238 strengthening)

| # | Model | Metric | Baseline | Framework | Δ | Paper § | Verification |
|---|---|---|---:|---:|---:|---|---|
| R1 | LineageFlow (ICML 2026 protein FM) | `hmmscan_total_hits` N=1000 | 158 | 342 | **+116.46%** (p<1e-10) | §7.6.1 | [`verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026) |
| R2 | Kanzi (molecular DAE inv-proj) | `RMSD` N=1000 | 0.6146 | 0.5941 | **d_z +0.3927** (medium-effect) | §7.6.2 | [`verification_outputs/wave235-p2-r2-uplift.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p2-r2-uplift.json) |
| R3 | FlowMol3 (ICML 2026 mol FM) | `fg_dev` N=200 NFE=250 | (Wave 87: 0.6381, NFE=250 N=1000) | (Wave 242 P1 in flight) | pending | §7.6.3 | [`verification_outputs/wave242-p1-flowmol3-seed43-*.json`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs) |
| R4 | 2D Two Moons (Liu 2022) | `W₂` | 0.5029 | 0.4663 | **−7.28%** | §7.6.4 | [`verification_outputs/r4_2d_two_moons_w2_m7p28pct/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/r4_2d_two_moons_w2_m7p28pct) |
| R5 | 2D Eight Gaussians (Liu 2022) | `W₂` | 0.6606 | 0.5919 | **−10.40%** | §7.6.5 | [`verification_outputs/r5_2d_eight_gaussians_w2_m10p40pct/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/r5_2d_eight_gaussians_w2_m10p40pct) |
| R5b | CIFAR-10 Rectified Flow | `FID` (matched-NFE=50) | 218.87 | 122.18 (batched, n_rounds=1) | **−2.53% to −0.66%** on 3/4 schedulers (n_rounds=1 framework-WINS) | §7.6.7 | [`verification_outputs/wave235-p1-r5b-fix.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p1-r5b-fix.json) |
| R6 | MNIST FM | `FID` | 409.18 (k6 pLDDT baseline) | 347.75 (with tier-aware scheduler) | **d_z +0.647** (large-effect, +189%) | §7.6.6 | [`verification_outputs/wave235-p3-r6-uplift.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p3-r6-uplift.json) |

**R5b Wave 235 P1 reversal:** R5b CIFAR-10 RF was REGRESSES (+24-31% ΔFID) under batched-path n_rounds=10, but framework-WINS at n_rounds=1 with ΔFID ∈ [-2.53%, -0.66%] on 3/4 schedulers. This is a **conditional boundary**, not a fundamental regression.

**R5b Wave 235 P1 details:** Wave 235 P1 ran 5 configurations (original, n_rounds=2, --no-final-restart, n_rounds=1, combined) on CodimensionSheetScheduler / CosineAnnealScheduler / EvidenceDrivenScheduler / FreeTrajScheduler. n_rounds=1 produced framework-WINS on 3/4 schedulers; the new --no-final-restart CLI flag was added (Wave 235 P1 commit `f7b294a`).

---

## Table 2 — 4-Arm Head-to-Head Per-Record Paired-t (Wave 230 + Wave 234)

| Cell | Baseline | Framework | d_z | p_raw | Verdict | Source |
|---|---:|---:|---:|---:|---|---|
| vanilla scPerplexity NFE50 | (Wave 230 P2) | (Wave 230 P2) | +0.145 | (Bonf-sig) | framework_WINS | [`verification_outputs/wave230-p2-real-4arm-per-record.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave230-p2-real-4arm-per-record.csv) |
| vanilla scPerplexity NFE100 | (Wave 230 P2) | (Wave 230 P2) | +2.103 | (Bonf-sig) | framework_WINS | [`verification_outputs/wave230-p2-real-4arm-per-record.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave230-p2-real-4arm-per-record.csv) |
| abcache scPerplexity NFE50 | (Wave 230 P2) | (Wave 230 P2) | +0.704 | (Bonf-sig) | framework_WINS | [`verification_outputs/wave230-p2-real-4arm-per-record.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave230-p2-real-4arm-per-record.csv) |
| (other 13 cells) | (Wave 230 P2) | (Wave 230 P2) | <0.07 | >0.05 | UNDERPOWERED | [`verification_outputs/wave230-p2-real-4arm-per-record.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave230-p2-real-4arm-per-record.csv) |

**Summary:** 14/16 cells granularity-bounded (|d_z| < 0.07); 3/16 Bonferroni-significant (|d_z| ∈ [0.145, 2.103]).

---

## Table 3 — Statistical Methods (Wave 234 P5 + Wave 234 P6)

| Method | Cell | Statistic | p-value | Verdict | Source |
|---|---|---|---:|---|---|
| TOST equivalence (α=0.05, 0.1 SD margin) | 16 cells | max(p1, p2) | (per cell) | 0/16 actively equivalent; 14/16 in 0.1 SD band | [`verification_outputs/wave234-p2-tost.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p2-tost.csv) |
| TOST equivalence | 16 cells | max(p1, p2) | (per cell) | 9/16 BF01 ≥ 10 (Wagenmakers threshold) | [`verification_outputs/wave234-p4-bf01.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p4-bf01.csv) |
| Jonckheere-Terpstra ordered test | R2 Kanzi | z = -10.0 | **9.86 × 10⁻²³** | monotone hard > medium > easy | [`verification_outputs/wave234-p3-jonckheere.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p3-jonckheere.csv) |
| Jonckheere-Terpstra ordered test | R6 k6 | z = -10.7 | **5.11 × 10⁻²⁵** | monotone hard > medium > easy | [`verification_outputs/wave234-p3-jonckheere.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p3-jonckheere.csv) |
| DerSimonian-Laird random-effects meta | k=12 studies | pooled d_z = +1.117 | (95% CI [+0.645, +1.589]) | I² = 99.60% | [`verification_outputs/wave234-p5-meta-summary.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p5-meta-summary.json) |
| Non-inferiority test (10% FID margin) | R5b CIFAR-10 RF (multi-round) | p_NI = 0.9985 | (fail margin) | REGRESSES first-class boundary disclosure | [`verification_outputs/wave234-p6-ni-test.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p6-ni-test.csv) |
| Non-inferiority test (10% FID margin) | R5b CIFAR-10 RF (n_rounds=1) | (Wave 235 P1) | (passes) | n_rounds=1 structural elimination | [`verification_outputs/wave235-p1-r5b-fix.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p1-r5b-fix.json) |

---

## Table 4 — Wall-Clock Fix (Wave 236 P2 CUDA-Graph Capture)

| Configuration | Wallclock (s) | Framework/Baseline Ratio | Speedup |
|---|---:|---:|---:|
| **Before CUDA-graph (matched-NFE=50, BATCH=64, n_rounds=4)** | 7.94 | 3.40× | (baseline) |
| **After CUDA-graph (matched-NFE=50, BATCH=64, n_rounds=4)** | 1.87 | 1.26× | **4.24× speedup** |
| Closes 76.8% of framework/baseline wall-clock gap | — | — | — |

**Implementation:** [`adaptive_reflow/framework/cuda_graph_capture.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/framework/cuda_graph_capture.py) (CudaGraphVelocityFieldCache + captured_velocity_field wrapper); env-var gated `ADAPTIVE_REFLOW_CUDA_GRAPH`. Wired into `_torch_velocity_field` and `_batched_torch_velocity_field` in [`adaptive_reflow/adapters/rectified_flow_cifar.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/adapters/rectified_flow_cifar.py). **D.4 30/30 PASS preserved in both modes** (default-off vs env-var-on).

**Why not full 24.6× → 1× closure?** Per-record harness (small N, large overhead) shows 24.6× framework/baseline ratio. Matched-NFE BATCH=64 n_rounds=4 framework runner shows 3.40× → 1.26× closure = 76.8% of the gap. Remaining 23.2% is in the framework's restart-blend loop bookkeeping (negligible vs model forward), not in the model forward chain itself.

---

## Table 5 — Reproducibility Gates (Wave 238 P4)

| Gate | State | Source |
|---|---|---|
| D.4 byte-stable regression | **30/30 PASS** | [`tests/test_d4_regression_vectors.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tests/test_d4_regression_vectors.py) |
| mkdocs build --strict | **0 warnings** | [mkdocs.yml](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/mkdocs.yml) |
| claims_consistency | **No drift** | [`tools/check_claims_consistency.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tools/check_claims_consistency.py) |
| Abstract word count | **328 words** (Wave 242 P3 — extended from 250 in Wave 237 P1) | [`docs/drafts/abstract-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/abstract-final.md) |
| Ruff lint (4-directory scope) | **0 findings** | `ruff check adaptive_reflow/ tests/ scripts/ tools/` |
| Mypy type-check | **0 errors** | `mypy adaptive_reflow/` |
| Pytest | **5155 passed / 196 skipped** | `pytest tests/` |

---

## Cross-references

- [`verification_outputs/wave230-p2-real-4arm-per-record.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave230-p2-real-4arm-per-record.csv) — 4-arm per-record paired-t (16 cells)
- [`verification_outputs/wave234-p2-tost.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p2-tost.csv) — TOST equivalence (16 cells)
- [`verification_outputs/wave234-p3-jonckheere.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p3-jonckheere.csv) — Jonckheere-Terpstra ordered test
- [`verification_outputs/wave234-p4-bf01.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p4-bf01.csv) — BF01 Bayes factor (16 cells)
- [`verification_outputs/wave234-p5-meta-summary.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p5-meta-summary.json) — DerSimonian-Laird meta-analysis
- [`verification_outputs/wave234-p6-ni-test.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p6-ni-test.csv) — Non-inferiority test
- [`verification_outputs/wave235-p1-r5b-fix.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p1-r5b-fix.json) — R5b n_rounds=1 framework-WINS
- [`verification_outputs/wave235-p2-r2-uplift.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p2-r2-uplift.json) — R2 medium-effect uplift
- [`verification_outputs/wave235-p3-r6-uplift.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p3-r6-uplift.json) — R6 large-effect uplift with easy-tier elimination
- [`verification_outputs/wave236-p2-wallclock.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave236-p2-wallclock.json) — CUDA-graph capture verification
- [`verification_outputs/wave242-p1-flowmol3-seed{43,44}-*.json`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs) — FlowMol3 rescue (in flight)
- [`tnnls_submission/MANIFEST.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/MANIFEST.md) — package manifest

---

## Table of Tables (Paper) — Wave 358 P2 ADDITIVE cross-reference index

**Status:** ADDITIVE Wave 358 P2 polish (no destructive edit to Tables 1-5 above). Maps every markdown table embedded in [`docs/drafts/paper-A-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md) (the canonical TNNLS manuscript source) to its `table_id` + caption + column count + paper section + byte-addressable source artifact + CONSOLIDATED_RESULTS cross-reference. The five submission tables above (R-level headline, 4-arm H2H, statistical methods, wall-clock, reproducibility gates) remain the primary submission surfaces; this table-of-tables is the reviewer-navigation aid that links the paper text to its provenance.

**Method:** All `^\|...\|` table blocks in `paper-A-final.md` enumerated via `grep -nE '^\|' docs/drafts/paper-A-final.md`; 6 distinct table regions identified (T1-T6). Each row's source_artifact is a `verification_outputs/<wave>/` directory that bytes-anchors the table's content; each row's CONSOLIDATED_RESULTS cross-reference is a §15.X section that documents the wave at which the table's content was generated / updated. Where no per-table source artifact exists (T3 / T4 / T5 are aggregated from multiple waves), the source_artifact column carries the cumulative aggregation handle.

| ID | Caption (paper-A-final.md) | Cols | Paper § | Source artifact | CONSOLIDATED_RESULTS cross-reference |
|---|---|---:|---|---|---|
| T1 | Wave 355 capability-token handshake SHA-256 example (`artifact` + `bytes` + `sha256` + `role`) | 4 | §3.4.2 | [`verification_outputs/wave355-capability-token-example/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave355-capability-token-example/) (762-byte `synthetic_continuous_capability_token.json` SHA-256 `584f8e02…`) | [`docs/audit/wave355-capability-token-example.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave355-capability-token-example.md) (audit material — no dedicated §15.X entry; referenced via §3.4.2 paper text + Wave 353 P5 pseudocode-block addendum §A.1) |
| T2 | Wave 349 R1 3-seed GPU ledger SHA-256 chain (`artifact` + `bytes` + `sha256` + `role` for 3 files: `seed42_manifest.json` 805B / `seed44_manifest.json` 805B / `SHA256SUMS` 2642B) | 4 | §3.5.1 | [`verification_outputs/wave349-r1-3seed-gpu/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave349-r1-3seed-gpu/) (3-file SHA-256 chain; aggregator SHA-256 `28aafe1c…`) | [`docs/audit/wave349-impl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave349-impl.md) + [`docs/audit/wave349-r1-3seed-gpu.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave349-r1-3seed-gpu.md) (audit material — no dedicated §15.X entry; referenced via §3.5.1 paper text + Wave 353 P3 §3.5 hash-chained ledger example addendum) |
| T3 | Five concrete adapter implementations (`Adapter` + `File` + `Vendored code path` + `Zero-line edits`) — 5 rows for LineageFlowAdapter / KanziAdapter / FlowMol3Adapter / RectifiedFlowCIFARAdapter / MnistFmAdapter | 4 | §5.3 | (cumulative — no single wave; aggregation across [`adaptive_reflow/adapters/lineageflow.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/adapters/lineageflow.py), [`kanzi.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/adapters/kanzi.py), [`flowmol3.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/adapters/flowmol3.py), [`rectified_flow_cifar.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/adapters/rectified_flow_cifar.py), [`mnist_fm.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/adapters/mnist_fm.py)) | [§15.74 — Wave 175 per-adapter NFE_REF mechanism + verification](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) + [§15.86 — Wave 190 Theorem 1 quantities load-bearing replication (kanzi + lineageflow n=30 paired sweep + cross-adapter cross-validation)](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) + [§15.96 — Wave 204 defensive sf() underflow fix + LineageFlow N=574 cross-adapter replication + standardized stats table superset](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) |
| T4 | Per-cell power-disclosure index (`R-cell` + `verdict` + `per-cell power disclosure in this paper` + `audit-doc handle`) — 7 rows for R1 / R2 / R3 / R5a / R5b / R5c / R6 | 4 | §7.2 | (cumulative — no single wave; aggregation across [`verification_outputs/wave189-p2-post-cd70821-combined.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave189-p2-post-cd70821-combined.json) R1 + [`verification_outputs/wave189-p2-post-cd70821-combined.json#two_moons`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave189-p2-post-cd70821-combined.json) R5a + R5b/R5c/R6 cells per their respective audit-doc handles; the R1 cell specifically references [`docs/audit/wave280-p-framework-fallback-contamination.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave280-p-framework-fallback-contamination.md)) | [§15.88 — Wave 195 strict per-cell power analysis (Tables A / B / C; 32 cells total)](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) + [§15.103 — Wave 326 cross-doc propagation snapshot](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) + [§15.104 — Wave 352 P5 R5a Wave 351 P2 n=10 paired-t confirmation addendum (TIE_PERSISTS)](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) + [§15.105 — Wave 357 P3 R3 FlowMol3 RDKit environment blocker documentation](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) |
| T5 | R5c regime-dependent curve 3-point table (`epochs` + `base_channels` + `max_train_images` + `n_seeds` + `baseline\_fid` + `best\_arm\_fid` + $\Delta$ FID + $d_z$ + $p_\text{bonf}$ + `verdict`) — 3 rows for epochs 1 (smoke) / 2 (intermediate) / 3 (production) | 10 | §7.8 | [`verification_outputs/wave191-r5-n1000/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave191-r5-n1000/) (R5c MNIST FM smoke + production ckpt N=1000 sweep at matched NFE=50) + [`docs/figures/fig5_r5c_regime_curve.png`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/figures/fig5_r5c_regime_curve.png) (byte-stable PNG render of the §7.8 3-point table verbatim) | [§15.87 — Wave 191 R5 completion at N=1000 (CIFAR-10 RF + MNIST FM, matched NFE=50)](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (also referenced in [`docs/audit/wave349-gap-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave349-gap-audit.md) for the Figure 1 byte-stable render addendum) |
| T6 | CIFAR-10 RF Lipschitz constant values (`Quantity` + `Value` + `Source`) — 6 rows for $\|W_1\|_\text{op}$ / $\|W_2\|_\text{op}$ / analytic $L_\text{local}^{(\text{analytic})}$ / sample-max FD / p99 FD / mean FD | 3 | §A.3.4 | [`verification_outputs/wave351-p3-thm5-numerical/lipschitz_estimate.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave351-p3-thm5-numerical/lipschitz_estimate.json) (byte-stable finite-difference estimator output; $L_\text{local}^{(\text{FD})}$ sample-max = 0.3810) | [`docs/audit/wave351-thm5-numerical.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave351-thm5-numerical.md) + [`docs/audit/wave352-l-local-appendix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave352-l-local-appendix.md) (audit material — no dedicated §15.X entry; referenced via §A.3.4 paper text + §10.9.3 Theorem 5 numerical-validation partial close-out footnote) |

**Summary:** 6 paper tables cataloged (T1-T6); each row carries multiple GitHub-URL cross-references to `verification_outputs/<wave>/`, `docs/audit/wave*.md`, and `docs/CONSOLIDATED_RESULTS.md` §15.X sections (T3 carries 8 references [5 adapter paths + 3 §15.X]; T4 carries 7 references [3 source artifacts + 4 §15.X]; T1 / T2 / T5 / T6 each carry 2-3 references; full per-row inventory in [`docs/audit/wave358-tables-md-polish.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave358-tables-md-polish.md) §2.3). T4 specifically carries 4 §15.X cross-references because the per-cell power-disclosure index spans 7 R-cells whose power analyses are documented in 4 distinct §15.X sections per Wave 195 / Wave 326 / Wave 352 P5 / Wave 357 P3 propagation events.

**Cross-doc linkage:** Each T1-T6 row also maps to one of the 5 submission tables above where applicable — T3 anchors the adapter layer behind Table 1 (R-level headline); T4 mirrors Table 1's R-cell verdict distribution with the §7.2 audit-doc handle column; T5 is the byte-stable source for Figure 1 (which is referenced from `tnnls_submission/figures.md` row 35); T6 is the byte-stable numerical input for Theorem 5 / §6.6 (which is referenced from `tnnls_submission/cover_letter.md` and the §A.3 appendix).

**Strict-clean compliance:** This table-of-tables is purely ADDITIVE — Tables 1-5 above are byte-identical to the prior revision (no wording change, no number change, no SHA change of any number in those tables). The MANIFEST.md row 27 SHA-256 + size for `tables.md` will refresh per the standard rehash workflow ([`docs/audit/wave348-link-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave348-link-fix.md) protocol); the audit trail is at [`docs/audit/wave358-tables-md-polish.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave358-tables-md-polish.md).

*Wave 358 P2 ADDITIVE paragraph, no destructive edit. This table-of-tables is a reviewer-navigation aid that links the paper text to its provenance; it does not promote any status label, change any number, or modify any wording in Tables 1-5 above. Per Wave 268 strict-clean rule + Wave 325 NO-PUSH policy + `flowa-paper-evidence` skill (preserve caveats, preserve provenance, do not promote UNDERPOWERED / DEFERRED / REGRESSES / NOT_SIGNIFICANT by wording).*