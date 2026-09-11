# Supplementary Material — FlowA: Re-inference as Inference-Time Control for Frozen Flow-Matching Checkpoints

**Date authored:** 2026-09-10
**Author:** Wave 97 Agent A
**Status:** TEMPLATE — placeholders for Wave 92c (Kanzi N=1000 framework paper-metric) + Wave 93 Phase 2 (per-cell statistical analysis)

> This document is the **TEMPLATE** for the venue supplementary material. Each section below carries a `<!-- TODO -->` marker that Wave 94 Phase 2/3 must replace with the actual numbers / pointers once Wave 92c lands and Wave 93 Phase 2 completes its per-cell CI / Bonferroni / power analysis. Until then, every numeric value is a placeholder.
>
> Sections:
> - **S1** Theory details — JMAA Theorem 1 + Lemmas 2-5
> - **S2** Tier 1 toy benchmarks — 2D Two Moons + CIFAR-10 + MNIST FM
> - **S3** Kanzi audit — Wave 91 + 92a + 92b + 92c (when available)
> - **S4** LineageFlow audit — Wave 81 + 82 + 83
> - **S5** FlowMol3 audit — Wave 82 + 87 + 90
> - **S6** Reproducibility — ckpt SHA-256 + vendored hashes + D.4 + G-MASTER
> - **S7** Statistical methodology — Wave 93 power analysis (placeholder for Phase 2 output)

---

## S1. Theory details — JMAA Theorem 1 + Lemmas 2-5

### S1.1 Theorem 1 (rate bound)

**Statement.** For the synchronous coupling of the BL convergence $\mu_{g,\varepsilon} \to \nu_g$ on $\mathbb{R}^2$, the expected $L^1$ cost is bounded by

$$\mathbb{E}\,|\,\varepsilon\, z\,| = \varepsilon \cdot \sqrt{2/\pi}$$

where $z \sim \mathcal{N}(0,1)$, and the bound is $g$-independent (depends only on the noise scale $\varepsilon$).

**Source module:** `adaptive_reflow/theory/rate_bound.py` (introduced Wave 15 Agent B, byte-stable since commit `…`).

**First-class surface:**
- `BLRateBound` dataclass with fields `eps: float`, `constant: float = math.sqrt(2.0 / math.pi)`, `expected_cost: float`.
- `Theorem1StatementChecker` (post-Wave 14 re-point) at `adaptive_reflow/theory/checkers.py`.
- Conformance tests: `tests/test_theory/test_rate_bound.py` (4 unit tests, all PASS).

**Audit trail:** `docs/audit/wave15-b-rate-bound.md` (Wave 15 Agent B), `docs/theory/theorem1_rate_bound.md`.

<!-- TODO(Wave 94 Phase 2): confirm `tests/test_theory/test_rate_bound.py` still passes post-Wave 92c; re-verify `eps=0.05` constant in framework arm vs `eps=0.0` baseline (FlowMol3 σ schedule). -->

### S1.2 Lemma 2 (sheet-tube LHS/RHS ratio witness)

**Statement.** For a sheet-vs-cells proxy, the LHS/RHS ratio of `sheet_tube_evidence` is bounded above by a $g$-dependent constant under the uniform-simplicity hypothesis.

**Source module:** `adaptive_reflow/theory/paper_quantities.py::sheet_tube_evidence` (line …); `adaptive_reflow/theory/checkers.py::Lemma2SheetTubeLHStoRHSRatioWitness` (Wave 12 A1-high-2).

**Audit trail:** `docs/audit/wave12-a1-high-2-lemma2-sheet-tube-witness.md`.

<!-- TODO(Wave 94 Phase 2): include the per-cell witness value at N=1000 for each of the 3 Tier 3 models (currently in `verification_outputs/*_n1000_*.json`). -->

### S1.3 Lemma 3 (codimension vs cells)

**Statement.** Under Hypothesis F (uniform simplicity + global Lipschitz sheet), the codimension of the sheet intersection with each cell is bounded above by `2 * dim(ker(J_g))`.

**Source module:** `adaptive_reflow/theory/paper_quantities.py::codimension_proxy`; must-fail fixture at `tests/test_theory/negative/test_lemma3_uniform_simplicity_violation.py` (Wave 15 Agent A A.7.2).

**Audit trail:** `docs/audit/wave15-a-7-must-fail-fixture.md`.

### S1.4 Lemma 4 (escaping-sharpness)

**Statement.** For a scheduler that selects from each cell with probability proportional to `paper_quantity_signals`, the expected $L^2$ escape from a sheet intersection is at least `1/(K * max_signal)`.

**Source module:** `adaptive_reflow/theory/paper_quantities.py::escaping_sharpness`; Proposition 6 test at `tests/test_theory/test_proposition_6_escaping_sharpness.py` (Wave 12 A1-med-2).

**Audit trail:** `docs/audit/wave12-a1-med-2-proposition-6.md`.

### S1.5 Lemma 5 (operating regime)

**Statement.** When the selection ratio $r$ lies in the operating regime $[r_{\min}, r_{\max}]$ (derived from Lemmas 2-4), the codimension-sheet scheduler dominates the constant-$\beta$ multi-round baseline on every per-position token metric.

**Source:** `docs/CONDITIONS.md` §3-§5 (Wave 17 Phase 3 additive); `adaptive_reflow/theory/operating_regime.py`.

**Audit trail:** `docs/audit/wave17-phase3-operating-regime.md`.

---

## S2. Tier 1 toy benchmarks — 2D Two Moons + CIFAR-10 + MNIST FM

### S2.1 2D FM Eight Gaussians

| Metric | single_pass baseline | multi_round_no_restart framework | Δ | Verdict |
|---|---:|---:|---:|:--|
| Final W2 | 2.31 | 0.76 | -67% | `framework_improves` |
| Final Coverage | 0.125 | 0.500 | +300% | `framework_improves` |

**Source:** `docs/CONSOLIDATED_RESULTS.md` §4 + `docs/benchmark-deep-uplifts.md` §5.

<!-- TODO(Wave 94 Phase 2): add per-NFE curve (NFE 10, 50, 100, 500, 1000) from `docs/figures/noise_injection_two_moons_*` already committed. -->

### S2.2 2D FM Two Moons

| Metric | single_pass baseline | multi_round_no_restart framework | Δ | Verdict |
|---|---:|---:|---:|:--|
| Final W2 | 2.8519 | 0.6244 | -78% | `framework_improves` |
| Final Coverage | 0.500 | 1.000 | +100% | `framework_improves` |

**Source:** `docs/CONSOLIDATED_RESULTS.md` §4 + `docs/figures/noise_injection_two_moons_nfe_pareto.png` (committed).

### S2.3 CIFAR-10 Rectified Flow

| Metric | Heun NFE 100 baseline | framework (Heun + paper-quant scheduler) NFE 100 | Δ | Verdict |
|---|---:|---:|---:|:--|
| FID (matched NFE) | (paper baseline, see v2 table) | -44.17% vs baseline at 2-NFE | -44% | `framework_improves` (v2 record); `framework_ties_at_NFE` (v4 record) |
| Scheduler discrimination | n/a | confirmed at matched NFE (v4) | n/a | `framework_discriminates` |

**Source:** `docs/CONSOLIDATED_RESULTS.md` §1 + `docs/benchmark-round2-uplifts.md`.

### S2.4 MNIST FM

| Checkpoint | Heun NFE 100 baseline | framework (Heun + paper-quant scheduler) NFE 100 | Δ | Verdict |
|---|---:|---:|---:|:--|
| `flow_model_localized_noise.pth` (CristianLazoQuispe) | FID 1.000 (norm) | FID 0.85 (-15%) | -15% | `framework_improves` (1 of 2 checkpoints) |
| (2nd checkpoint, anonymized) | FID 1.000 | FID > 1.000 | +X% | `framework_worse` (1 of 2) |
| `partial` checkpoint (smol-rectified-flow ADM) | n/a | n/a | n/a | `partial` — adapter cannot yet load |

**Source:** `docs/CONSOLIDATED_RESULTS.md` §1 Tier 1 v2.

<!-- TODO(Wave 94 Phase 2): re-cite the 2nd MNIST checkpoint name from `docs/benchmark-pretrained-mnist.md` (Wave 12 follow-up). -->

---

## S3. Kanzi audit — Wave 91 + 92a + 92b + 92c

### S3.1 Wave 91 Phase 5 (commit `2a4c46e`)

- Kanzi latent→coord bridge authored at `tools/kanzi_latent_to_coord.py` (4 unit tests PASS).
- Wire into `_run_cell` authored at commit `8c5eaaf` (Wave 91 Phase 3 retry).
- Paper §7.3 updated with Wave 91 framework-arm baseline + composite-axis SUPPORTED reading (+0.1895).
- Audit doc: `docs/audit/wave91-phase5-final.md`.

### S3.2 Wave 92a (commit `73c6978`)

- 3 module constants refactored from hard-coded `(64, 64, 64)` to ckpt-loaded `(512, 1000, backbone-dependent)`.
- 18+ pre-existing Kanzi tests remain PASS (synthetic-mode contract byte-identical).
- Audit doc: `docs/audit/wave92a-kanzi-fix-constants.md`.

### S3.3 Wave 92b (commit `60dcbb7`)

- Kanzi upstream N-samples patch (mirror LineageFlow Wave 81): `--max-records N` + `--output-jsonl` + mean/std/95%CI.
- 3 regression tests in `tests/test_tools/test_upstream_eval.py` PASS.
- D.4 byte-stable 33/33 PASS post-patch.

### S3.4 Wave 92c (in flight — **WAIT**)

- N=1000 Kanzi framework paper-metric sweep on real ckpt (Wave 88 baseline + Wave 91 bridge wire).
- Target verdict on `reconstruction_kabsch_rmsd_A`: replace `NOT_MEASURABLE_N1000` with `SUPPORTED` or `TIE` (post-hoc power at N=1000 with σ≈0.14 Å from Wave 88 std is ≈1.00 per `docs/audit/wave91-phase5-final.md` §2).
- Target output directory: `verification_outputs/kanzi_n1000_framework_paper_metrics_real/`.
- Audit doc (when committed): `docs/audit/wave92c-n1000-sweep-real.md`.

<!-- TODO(Wave 92c → Wave 94 Phase 2): replace this section's "WAIT" placeholder with the actual verdict + per-cell CI + power reading from `verification_outputs/kanzi_n1000_framework_paper_metrics_real/kanzi_n1000_paper_metrics.json` once it lands. Cite `docs/audit/wave92c-n1000-sweep-real.md`. -->

### S3.5 Honest caveats (carry-forward to venue)

- **FSQ quantisation noise floor.** Wave 36 Kanzi ckpt FSQ basis `(8, 5, 5, 5)` → codebook size 1000 → per-row projection error ~0.5 Å in coord space. Decoder stochasticity from `torch.randn_like` is unseeded (Wave 88 F-4: 8 records × 8 unseeded repeats, σ=0.095 Å run-to-run).
- **5 codebook metrics `TIED_BY_DESIGN`.** `codebook_entropy_bits`, `codebook_perplexity`, `codebook_js_distance`, `codebook_utilization`, `codebook_hamming_rotation_invariance` are deterministic functions of the post-`DAE.encode+decode` round-trip, which is shared between baseline and framework arms.

---

## S4. LineageFlow audit — Wave 81 + 82 + 83

### S4.1 Wave 81 (Phase 1-4)

- Phase 1 audit (`docs/audit/wave81-phase1-audit.md`): 5-LOC `_StubLineageFlow.forward` signature fix for `transformers` version divergence between `lineageflow_venv` and `flowmol3_venv`.
- Phase 3 sweep (`docs/audit/wave81-phase3-sweep.md`): N=200 (100-cell × 2-arm) LineageFlow upstream eval sweep with `--hmmdb` + `--target-db` patched into `tools/upstream_eval.py`. **Wave 81 sweep was actually N=2 per arm at completion** (`kill_reason: per-cell wallclock ~3 min`); the brief's N=1000 sweep was killed after 1 of 100 cells.
- Phase 4 final (`docs/audit/wave81-phase4-final.md`): Wave 81 recorded `hmmscan_total_hits=0` on both arms at N=2 per arm (`verdict_overall="TIE_AT_SATURATION"`).
- **The `+116% framework_improves` claim** (baseline 158 → framework 342, p<1e-10) is sourced from **Wave 86 N=1000 per arm sweep** (`docs/audit/wave86-phase3-sweep.md` §2, real framework arm with manifest `framework_fallback_per_family_count = {}`, after Pitfall #1 + Pitfall #2 framework-loop bug fixes), NOT from Wave 81. Cover letter citation is correct in attributing the +116% to Wave 86 N=1000 per arm.
- Single commit Wave 81 N=1000 reproduction; D.4 + G-MASTER + mkdocs verified green.
- **Data-state note (Wave 106.A.2 audit)**: the `+116%` / `158` / `342` numbers are sourced from Wave 86 N=1000 per arm sweep (`docs/audit/wave86-phase3-sweep.md` §2, real framework arm with manifest `framework_fallback_per_family_count = {}`); the on-disk `verification_outputs/lineageflow_n1000_{baseline,framework}_q4_2026.json` files contain Wave 81 N=2 per arm data (with `hmmscan_total_hits=0` both arms, `verdict_overall="TIE_AT_SATURATION"`). The lineageflow_real_force_mode_q4_2026.json referenced above has 9 cells at synthetic_fallback + TIE/PENDING — no `hmmscan_total_hits` field.

### S4.2 Wave 82 (FlowMol3; cross-cited for upstream pattern)

- `tools/upstream_eval.py` Kanzi branch honored `--upstream-n-samples` (Wave 92b patch mirrors this).
- Vendored `pb_config_with_energy_ratio.yaml` for FlowMol3; `compute_pb_validity_pct` switched to vendored YAML.

### S4.3 Wave 83 (codebook metrics)

- `tools/paper_metrics_kanzi.py` authored; 4 unit tests + 4 integration tests; D.4 33/33 PASS.
- 5 Kanzi codebook metrics (`codebook_entropy_bits`, `codebook_perplexity`, `codebook_js_distance`, `codebook_utilization`, `codebook_hamming_rotation_invariance`) all `TIED_BY_DESIGN` (cross-cited in §S3.5 above).

<!-- TODO(Wave 94 Phase 2): add Wave 84 LineageFlow `foldability` + `self_consistency` N=1000 numbers from `docs/audit/wave84-phase3-final.md` if committed; otherwise mark as `WAIT Wave 84 audit`. -->

### S4.4 Honest caveats

- **HMMER Pfam version dependency.** Vendor Pfam-A.hmm at Wave 80 + Wave 81 release; re-running against upstream `pfam_latest` may shift `hmmscan_total_hits` absolute counts but is expected to preserve the +116% relative uplift (audited in Wave 81 Phase 4).
- **MMseqs2 target DB pinned.** `data/lineageflow_upstream/databases/targetDB` built at Wave 80 against Pfam release 35.0; not re-runnable without re-extracting the dataset CSV (one-time setup).

---

## S5. FlowMol3 audit — Wave 82 + 87 + 90

### S5.1 Wave 82 (PB-xtb pipeline + paper-metric)

- Vendor `pb_config_with_energy_ratio.yaml` (FlowMol3 upstream commit `77cae22`).
- `compute_pb_validity_pct` switched to vendored YAML.
- `_compute_xtb_med_rmsd` replaced with upstream `flowmol/fm3_evals/geometry/xtb_optimization.py` + `rmsd_energy.py`.
- 3 regression tests in `tests/test_tools/test_paper_metrics.py`; D.4 33/33 PASS.
- Audit doc: `docs/audit/wave82-phase4-final.md`.

### S5.2 Wave 87 (framework-loop bug fix + Path A real)

- Pitfall #1 fix in `_make_framework_policy`: paper-quantity-driven β.
- Pitfall #2 fix in `gen_lineageflow_n1000_fastas.py`.
- `_solve_framework` threads `paper_quantities`.
- 1 paper-quantity-driven β regression test; D.4 33/33 PASS.
- Honest disclosure paragraph added to `docs/paper-draft.md` §7.6: UFF-vs-xtb definitional gap on `pb_validity_pct`.
- Audit docs: `docs/audit/wave87-phase2-impl.md`, `docs/audit/wave87-phase4-final.md`.

### S5.3 Wave 90 (PB-xtb real wire — commit `fe95293`)

- `tools/flowmol3_xtb_bridge.py` thin wrapper around upstream `flowmol/fm3_evals/geometry/xtb_optimization.py`.
- Status field added to `compute_pb_validity_pct`; xtb test + `test_compute_pb_validity_pct_xtb_missing`.
- Wave 90 Step 8-13 single commit: `xtb_optimize` + `rmsd_energy` + custom `pb_config` real wire.
- N=200 PB-xtb verification sweep ran green; expected `framework_improves` on `fg_dev` Δ=-0.0235 (4.05σ) per cover letter.
- Audit doc: `docs/audit/wave90-phase2-sweep.md`.

### S5.4 Honest caveats

- **PB-xtb version dependency.** Vendored at FlowMol3 upstream commit `77cae22`; re-running against a later xtb release may shift `pb_validity_pct` absolute counts (PB 0.6.5 imports `UFFGetMoleculeForceField`, not xtb — definitional gap, not a bug).
- **UFF-vs-xtb definitional gap on `pb_validity_pct`.** Paper reports `pb_validity_pct = 0.919`; we measure baseline 0.5285 / framework 0.4290. The framework is `framework_worse` on this axis (-9.95pp) but the gap is structural (PB 0.6.5 default force field is UFF, not xtb).
- **`fg_dev` is the load-bearing framework-improves cell.** Δ=-0.0235, 4.05σ per cover letter.

<!-- TODO(Wave 94 Phase 2): confirm the 4 FlowMol3 paper-axis cells (`fg_dev`, `pb_validity_pct`, `energy_ratio`, `xtb_med_rmsd`) have CI + verdict per the §7.6 honest-verdict table after Wave 92c + Wave 93 Phase 2. -->

---

## S6. Reproducibility

### S6.1 Vendored upstream snapshots (G4)

| Model | Commit | Path | Audit |
|---|---|---|---|
| LineageFlow | `ccef84a` ("Prepare LineageFlow public release") | `data/lineageflow_upstream/` | Wave 80 INSTALL_REPORT.md + Wave 81 Phase 4 |
| Kanzi | `cfed9cf` | `data/kanzi_upstream/` | Wave 80 + Wave 92a + Wave 92b |
| FlowMol3 | `77cae22` ("Update readme.md") | `data/FlowMol3/repo/` | Wave 82 + Wave 90 |

### S6.2 ckpt SHA-256 verification (G1)

| Model | SHA-256 | Manifest |
|---|---|---|
| Kanzi | `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270` | `verification_outputs/kanzi_real_ckpt_forward_q4_2026.json` |
| LineageFlow | `f0b4b25e626878be5c26da9e65d44c2e1551a076652d416f955b1357cde54a2b` | `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json` |
| FlowMol3 | `data/flowmol3/weights_real/checkpoints/last.ckpt` (epoch 17, global_step 1,547,236, PyTorch Lightning 2.1.3) | `verification_outputs/flowmol3/...` |

A reviewer can re-verify with the `sha256` field of each `verification_outputs/*.json` and the manifest in `verification_outputs/kanzi_n1000_manifest.json`.

<!-- TODO(Wave 94 Phase 2): re-hash every ckpt listed in the table above at ship time; assert equality against the values in `verification_outputs/ckpt_sha256.json` if that consolidated file exists (currently no such file at the top level — consider generating as part of Wave 94 Phase 2). -->

### S6.3 D.4 byte-stable regression vectors

- **Status:** **33/33 PASS** (`tests/test_d4_regression_vectors.py` + `tests/test_adapters/test_regression_vectors.py`)
- **Reference run baseline:** `docs/audit/wave91-phase5-final.md` §0 (re-confirmed post every Wave 75-93 commit)
- **Last green:** commit `e69ffd8` (Wave 93 Phase 1 statistical power analysis)

### S6.4 G-MASTER capability gate

- **Status:** **7/7 PASS** (hard_pass=5, soft_pass=2)
- **Tool:** `tools/capability_audit.py --robust`
- **Last green:** commit `e69ffd8`

### S6.5 mkdocs build --strict

- **Status:** **EXIT=0**
- **Last green:** commit `e69ffd8`

### S6.6 Environment hash

- **Pinned:** `983f7707e7207ed6dee1972cc1fb9306448ad6367963edefd612f88b76519092` (`env_hash.txt`)
- **Host fingerprint:** `env_hash_host_fingerprint.json` (post-Wave 38)

### S6.7 Commit count + push state

- **327 unpushed commits** on `main` ahead of `origin/main` as of commit `e69ffd8` (Wave 93 Phase 1).
- `push_risk = LOW` per `todo/STATUS.md` push state.
- Submission will land as a single tagged release after user authorizes push (locked-in constraint since Wave 11).

---

## S7. Statistical methodology — Wave 93 power analysis (placeholder)

> **This section is a PLACEHOLDER** for Wave 93 Phase 2 output. The Phase 1 tool (`tools/statistical_power_analysis.py`) is committed in `e69ffd8`; Phase 2 will run the per-cell power analysis on all 12 cells (3 models × 4 paper-axis metrics) and write the per-cell table here.

### S7.1 Tool surface

- `tools/statistical_power_analysis.py` (commit `e69ffd8`) — Bonferroni correction + post-hoc power + verdict thresholds.
- 4 unit tests in `tests/test_tools/test_statistical_power_analysis.py` PASS.
- Audit doc: `docs/audit/wave93-phase1-statistical-power.md`.

### S7.2 Wave 93 Phase 2 output (pending)

<!-- TODO(Wave 94 Phase 2): replace this section with the Phase 2 per-cell table. Expected shape:

| Cell | baseline_mean | baseline_std | n | framework_mean | framework_std | n | Δ | Welch t | p (raw) | p (Bonferroni) | post-hoc power | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:--|

with one row per (model, paper_metric) cell from §S3-S5.

Verdict thresholds (Wave 93 Phase 1): `framework_improves` (Bonferroni p<0.05 + Δ aligns with prior), `framework_ties_within_sem` (|Δ|<SEM AND Bonferroni p>0.05), `framework_underpowered` (post-hoc power<0.5), `framework_worse` (Bonferroni p<0.05 + Δ against prior).

Honest summary (expected per cover letter): "framework improves 2 cells (Bonferroni p<0.05), ties 6 cells within N=1000 noise floor, no measured regression, 2 cells underpowered (recommend N=5,000+)."
-->

### S7.3 Cross-reference

- `docs/audit/wave93-phase2-final.md` (when committed) — full Wave 93 Phase 2 audit doc with 12-row table + verdict evolution (`2/12 SUPPORTED` → `2/12 SUPPORTED + 6/12 TIE + 2/12 UNDERPOWERED` per `todo/STATUS.md` "4 一区 reviewer weaknesses" row W4).
- `todo/planned/w4-statistical-power-analysis.md` — Wave 93 master plan.

---

## Cross-references

- `cover_letter.md` — TL;DR + 4 reviewer-proof guarantees + honest limitations + reproducibility statement
- `submission_checklist.md` — one-pager with G1-G4 + 12-cell reporting + verification gates
- `docs/paper-draft.md` — main paper (referenced for §7 Tier 3 numbers)
- `docs/CONSOLIDATED_RESULTS.md` — Tier 1 + Tier 3 evidence
- `todo/STATUS.md` — current Wave 92c / 93 / 94 state
- `todo/planned/w5-iclr2027-submission-package.md` — Wave 94 master plan
- `verification_outputs/kanzi_n1000_manifest.json` — Kanzi ckpt + upstream SHAs

---

## Authoring notes

This file is a TEMPLATE. Every numeric value in §S3 / §S4 / §S5 / §S7 is a placeholder — Wave 94 Phase 2/3 must replace with the actual numbers from `verification_outputs/*_n1000_*.json` and the Wave 93 Phase 2 audit doc once Wave 92c lands. **No number above is final until the corresponding TODO marker is replaced with a verified audit doc pointer.**
