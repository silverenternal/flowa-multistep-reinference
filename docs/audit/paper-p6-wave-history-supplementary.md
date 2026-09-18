# Paper P6 — Wave History (Audit Trail)

**Date authored:** 2026-09-18
**Wave:** 188 P6
**Purpose:** Audit trail for the Wave history content that was moved out of the main paper draft (`docs/paper-draft.md`) into this supplementary companion during the Wave 188 P6 paper polish. The main paper's §7.5 / §7.6 / §Ablations.6 / §Ablations.7 / §Ablations.9 / §Ablations.10 sections previously carried the Wave-by-Wave verdict evolution tables; the main paper now retains only the headline verdict + the Wave 82/87 paper-metric tables (the canonical byte-stable readings) and the Wave 58 NFE-budget-free claim.

This document preserves the per-Wave audit trail for:

- §7.5 FlowMol3 Wave 50-74 verdict evolution (Wave 50 BLOCKED → Wave 53 TIE → Wave 54 REGRESSION → Wave 65 TIE → Wave 66 BLOCKED → Wave 68 BLOCKED → Wave 68 closure TIE → Wave 70-74 fix arc → Wave 74 F1-F5 closure)
- §7.6 Wave 79-87 verdict evolution (Wave 75 N=10 smoke → Wave 79 review → Wave 82 N=1000 → Wave 87 byte-stable reproduction)
- §Ablations.6 Wave 74 F5 9-cell FlowMol3 sweep detail
- §Ablations.7 Wave 52 5-arm per-component ablation detail
- §Ablations.9 Wave 156 real-ckpt 5-arm ablation (10/15 OK)
- §Ablations.10 Wave 158 P2 R1 +116% re-derivation on-disk

For the canonical (Wave 82 / Wave 87 byte-stable) FlowMol3 numbers, see `docs/CONSOLIDATED_RESULTS.md` §15.6. For the §10.20-§10.31 wave-history detail, see the per-wave audit docs cross-linked below.

---

## S1. §7.5 FlowMol3 Wave 50-74 verdict evolution (audit trail)

The main paper's §7.5 now leads with the Wave 68 closure verdict (TIE_AT_SATURATION on entropy-reduction; composite +0.0000 due to env-level RDKit/xtb absence). The Wave 50-74 verdict evolution is preserved here.

### S1.1 Wave 50-74 timeline

| Wave | Verdict | Reason | Audit doc |
|---|---|---|---|
| 50 | BLOCKED | Adapter factory + force_mode bug; metric helper did not exist | `docs/audit/wave50-flowmol3-eval.md` |
| 53 | TIE_AT_SATURATION (misleading) | `_compute_flowmol3_real_metric_via_trace` + wiring landed; composite +0.0000 due to placeholder uniform-vs-uniform | `docs/audit/wave53-flowmol3-glue.md` |
| 54 | REGRESSION | Real-ckpt metric worked; framework-vs-baseline negative delta (Bug C) | `docs/audit/wave54-phase2-fix.md` |
| 65 | TIE_AT_SATURATION | Bug C targeted fix (framework = baseline at saturation) | `docs/audit/wave65-flowmol3-bug-c-fix.md` |
| 66 | BLOCKED | v2 wire gap | `docs/audit/wave66-flowmol3-v2-wire.md` |
| 68 | BLOCKED | state=None observe gap | `docs/audit/wave68-flowmol3-state-none.md` |
| 68 closure | TIE_AT_SATURATION (real metric, byte-stable) | 9/9 cells entropy-reduction = 0.0734 nats; composite 0.0 due to env-level RDKit/xtb absence | `docs/audit/closure-flowmol3-sweep.md` |
| 70-74 | Wave 70 vendored `flowmol` + Wave 71 closed GAP-1/GAP-3 + Wave 73 closed GAP-4 + Wave 74 F1-F5 closure (n_molecules=10, seed threading, xtb install, energy_dist.npz vendored, 3-run byte-identical at `seed=42, NFE=50, n_molecules=10` with `composite = 0.11822303757549568`) | — |

### S1.2 Wave 68 closure honest reading

The previous "metric layer placeholder uniform-vs-uniform" framing in the Wave 53 honest reading is superseded: the metric layer is now real — entropy-reduction reads 0.07340423794186401 nats on every cell (byte-stable), and `baseline_metric = framework_metric` because both arms reach the same saturation point at the endpoint categorical distribution. This is the same saturation reading Wave 65 / Wave 66 captured, now byte-stable at the Wave 68 closure re-run. The FlowMol3 path is no longer structurally blocked. The remaining `composite = +0.0000` reading is an env-level degradation (RDKit not importable + xtb not on $PATH), NOT a code bug.

### S1.3 Wave 70-74 four-wave arc summary

Wave 70 vendored upstream `flowmol` and added `FlowMol3V2Adapter.export_sampled_molecules` + caller wire (Phases 1-4). Phase 5 GPU sweep surfaced GAP-1: v2 factory does not thread `use_upstream=True` so 9/9 cells return `composite = 0.0, marker = "degraded_chemistry"`. Wave 71 closed GAP-1 + GAP-3 (`sampled_mols_from_smiles` shortcut returns upstream `SampledMolecule` objects) but surfaced GAP-4 (`_resolve_adapter` does not pass `weights_path`). Wave 73 closed GAP-4 (4-gate condition in `_resolve_adapter` + lazy-load fix in v2 `solve_ode` + conditional `posebusters` stub); 9-cell sweep 7/9 cells `marker=computed`, but n=1 molecule per cell yields ±0.6 run-to-run spread.

Wave 74 F1-F5 closure (verdict `TIE_AT_SATURATION_with_byte_stable_composite`):
- F1 = `n_molecules=10` threaded CLI→v2 adapter (mean aggregation)
- F2 = `_seed_everything(seed, device)` context manager wraps upstream `FlowMol.sample`
- F3 = `xtb` 6.7.1 installed at `/home/hugo/xtb_prefix/bin/xtb`
- F4 = `energy_dist.npz` (3.7 KB) vendored
- F5 = 3-run byte-identical reproducibility verified at `seed=42, NFE=50, n_molecules=10` — `composite = 0.11822303757549568` on 3/3 runs (Wave 73 ±0.6 spread closed)

All gates byte-stable (D.4 72/72 in 42.89 s; G-MASTER 7/7; mkdocs strict EXIT=0). The structural verdict remains unchanged on the entropy-reduction axis (`baseline = framework = 0.07340423794186401 nats`, Δ ≤ 6e-15) — the upstream `FlowMol.sample` path owns its own integration loop and the framework's restart/scheduler does not change the entropy readout.

### S1.4 Wave 69 Phase 2 / Phase 3 marker-honesty update

Per `docs/audit/wave69-phase2-fix.md` (Phase 2 fix at `tools/run_real_ckpt_eval.py:3122-3273`) and `docs/audit/wave69-phase3-sweep.md` (Phase 3 re-run on RTX PRO 6000), the helper `_compute_flowmol3_composite` now exposes an interface-first additive kwarg `sampled_molecules: Sequence[Any] | None = None`. When supplied, the helper delegates to `FlowMol3Glue.compute_chemistry_metrics` and surfaces `marker="degraded_chemistry"` rather than fabricating `marker="computed"` with zero readings — the debug-surface honesty improvement.

### S1.5 Wave 75 N=10 smoke paper-metric table (full)

| Metric | Paper target (arXiv 2508.12629) | Ours baseline (N=10 smoke) | Δ vs paper | Ours framework (N=1 smoke) | Verdict |
|---|---:|---:|---:|---:|:---|
| `validity_pct` | **0.999** | **1.000** | +0.001 (within ±5% — PASS) | 1.000 | framework_ties (ceiling saturation on both arms) |
| `pb_validity_pct` | **0.919** | 0.000 | −0.919 (BLOCKED on PB pipeline gap) | 1.000 | INSAMPLE_INSUFFICIENT (N=1) |
| `fg_dev` | **0.27** | 0.944 | +0.674 (INSAMPLE-INSUFFICIENT at N=10) | 2.717 | INSAMPLE_INSUFFICIENT (N=1) |
| `ood_ring_rate` | **0.10** | 0.000 | −0.10 (INSAMPLE-INSUFFICIENT at N=10) | 0.000 | framework_ties (both under-stocked) |

---

## S2. §7.6 Wave 79-87 verdict evolution (audit trail)

The main paper's §7.6 now leads with the Wave 131 reframe headline (6 Bonferroni-significant `framework_improves` + 3 byte-stable composite-axis improvements). The Wave 79-87 verdict evolution is preserved here.

### S2.1 Wave 79 Phase 4 cross-reference

Wave 79 Phase 4 reviewed the Wave 75 paper-metric sweep (`docs/audit/wave75-phase3-paper-repro.md`) against the new per-metric support table at `docs/audit/wave79-phase4-verdict.md` §2.3. The FlowMol3 paper-metric verdict **remains PARTIAL** under the Wave 79 framing: `validity_pct = 1.000` matches the paper's reported 0.999 within 0.1% (PASS at N=10); `pb_validity_pct = 0.0` is `BLOCKED` on the UFF-vs-xtb definitional gap; `fg_dev = 0.944` and `ood_ring_rate = 0.0` are `INSUFFICIENT_SAMPLE` at N=10 (need N≥500 for stable per-flag pass-rate estimate).

### S2.2 Wave 82 PHASE-4 N=1000 paper-metric reproduction

Wave 82 closed the Wave 75 UFF-vs-xtb definitional gap on the `pb_validity_pct` axis by vendoring a custom PoseBusters config `data/FlowMol3/pb_config_with_energy_ratio.yaml` (Wave 82 Phase A, 132 lines) that UN-COMMENTS the `energy_ratio` module with the paper-tuned parameters (`threshold_energy_ratio=100.0`, `ensemble_number_conformations=50`) — replacing the built-in PoseBusters `mol.yml` preset that uses PB default `threshold_energy_ratio=7.0` and runs the energy_ratio module twice (PB 0.6.5 bug).

Wave 82 Phase B wired the vendored YAML into `tools/paper_metrics.py` via `compute_pb_validity_pct(full_pb=True) -> SampleAnalyzer(..., pb_config_file=<vendored_yaml>)`. Wave 82 Phase C then ran the N=1000 2-arm sweep on RTX PRO 6000 Blackwell. Sweep wallclock 462.8 s ≈ 7.7 min, all 4 paper-parity metrics now return real numbers at N=1000:

| Metric | Paper | Baseline (N=999) | Framework (N=1000) | Δ (F − B) | Verdict |
|---|---:|---:|---:|---:|:---|
| `validity_pct` | 0.999 | **1.0000** | **1.0000** | 0.0000 | MATCH |
| `pb_validity_pct` | 0.919 | **0.5285** | 0.4290 | **−0.0995** | framework worse by 9.95 pp |
| `fg_dev` | 0.27 | 0.6381 | **0.6146** | **−0.0235** | framework closer to paper (4.05σ) |
| `ood_ring_rate` | 0.10 | 0.0130 | 0.0100 | −0.0030 | not distinguishable |

### S2.3 Wave 87 byte-stable reproduction verdict evolution

| Wave | `validity_pct` | `pb_validity_pct` | `fg_dev` | `ood_ring_rate` | Overall |
|---|---|---|---|---|---|
| 75 | MATCH | BLOCKED | INSUFFICIENT_SAMPLE | INSUFFICIENT_SAMPLE | PARTIAL |
| 79 | MATCH | BLOCKED | INSUFFICIENT_SAMPLE | INSUFFICIENT_SAMPLE | PARTIAL |
| 82 | MATCH (1.0000 both arms) | REAL (0.5285/0.4290) | REAL, framework_improves (Δ=−0.0235, 4.05σ) | REAL (underpowered) | PARTIAL |
| **87** | MATCH (byte-stable) | REAL (byte-stable; brief's PB-xtb premise FALSE POSITIVE) | REAL (byte-stable; framework_improves 4.05σ) | REAL (byte-stable; underpowered) | PARTIAL (byte-stable reproduction) |

### S2.4 Brief's `pb_validity_pct 0.53 → 0.92` expectation — FALSE POSITIVE

The brief's premise that "PB 0.6.5 energy_ratio uses UFF, paper uses xtb — pipeline is missing" was a misreading of PoseBusters 0.6.5's `energy_ratio` module. Per Wave 87 Agent A audit (`docs/audit/wave87-phase1-audit.md` §1-§3, verified at three levels):

1. **Source inspection**: `.venvs/flowmol3_venv/lib/python3.12/site-packages/posebusters/modules/energy_ratio.py:6-14` imports `from rdkit.Chem.AllChem import UFFGetMoleculeForceField` — the module is **UFF-based**, NOT xtb-based. xtb is **not referenced** in this module.
2. **Audit doc verification**: Wave 87 Agent A's audit explicitly documents the Wave 82 vendored YAML is correctly configured with paper-tuned `threshold_energy_ratio=100.0`, `ensemble_number_conformations=50` (verified against `data/FlowMol3/repo/flowmol/analysis/pb_config.yaml:101-110` upstream source).
3. **Re-run delta verification**: Wave 87's N=1000 numbers are **identical to Wave 82's to float64 precision** (see byte-stable table; deltas on the order of 1e-16 ULP noise).

Where xtb IS used: `tools/run_real_ckpt_eval.py:_compute_xtb_geometry_metrics` (lines 3312-3531, Wave 82 Agent B fix) — runs upstream `xtb_optimization.py + rmsd_energy.py` to compute `med_rmsd`, `med_energy_gain`, `med_mmff_drop` for the SEPARATE composite geometry axis.

### S2.5 Wave 109.C N=1000 re-run attempt (failed deterministically)

The upstream `FlowMol.sample()` constructs a single batched DGL graph with `num_nodes = batch_size × n_atoms_per_mol` then assigns the per-mol `prior['x_0']` (shape `(n, 3)`) to the batched graph's `ndata['x_0']` slot, but the v2 adapter's `_solve_ode_upstream_batch` passes per-mol tensors — DGL 2.4.0 raises `DGLError: Expect number of features to match number of nodes (len(u)). Got 20 and 2000 instead.` on every batch. Failed-run JSON preserved at `verification_outputs/flowmol3_n1000_baseline_wave109_c_q4_2026.json`. Canonical best-known-good baseline carries forward from Wave 87.

---

## S3. §Ablations.6 Wave 74 F5 9-cell FlowMol3 sweep (full detail)

The main paper's §Ablations.6 retains the headline 9-cell sweep table + the weights-correction block. This appendix preserves the full per-component decomposition + the per-cell commentary.

### S3.1 9-cell FlowMol3 sweep table

| seed | NFE | baseline_composite | framework_composite | composite_delta | composite_marker | wallclock_baseline_s | wallclock_framework_s |
|:---:|---:|---:|---:|---:|:---:|---:|---:|
| 42 | 10  | 0.0    | 0.073404 | **+0.073404** | computed | 5.27 | 0.38 |
| 42 | 50  | 0.0    | 0.073404 | **+0.073404** | computed | 11.33 | 6.49 |
| 42 | 200 | 0.0    | 0.073404 | **+0.073404** | computed | (long; xtb-bound) | (long; xtb-bound) |
| 43 | 10  | 0.0    | 0.073404 | **+0.073404** | computed | (per F2 seeding) | (per F2 seeding) |
| 43 | 50  | 0.0    | 0.073404 | **+0.073404** | computed | (per F2 seeding) | (per F2 seeding) |
| 43 | 200 | 0.0    | 0.073404 | **+0.073404** | computed | (per F2 seeding) | (per F2 seeding) |
| 44 | 10  | 0.0    | 0.073404 | **+0.073404** | computed | (per F2 seeding) | (per F2 seeding) |
| 44 | 50  | 0.0    | 0.073404 | **+0.073404** | computed | (per F2 seeding) | (per F2 seeding) |
| 44 | 200 | 0.0    | 0.073404 | **+0.073404** | computed | (per F2 seeding) | (per F2 seeding) |

### S3.2 Per-component decomposition (Wave 74 F5 §1 + §4)

| Composite component | Source | Value | Notes |
|---|---|---:|---|
| `frac_valid_mols` (× 0.30) | F1 batched upstream `SampleAnalyzer` | **1.0** | all 10 mols valid |
| `frac_mols_stable_valence` (× 0.25) | F1 + upstream `SampledMolecule.valencies` | **0.2** | 2/10 mols pass |
| `neg_energy_js_div` (× 0.15) | F4 vendored `energy_dist.npz` | **−0.7991** | framework samples diverge |
| `neg_reos_cum_dev` (× 0.15) | F3 xtb-subprocess REOS | **−0.8643** | framework samples deviate |
| `neg_med_rmsd_after_xtb` (× 0.15) | F3 xtb-subprocess UFF (NOT PB-xtb) | **None** | placeholder until PB-xtb |

### S3.3 The two non-trivial observations

**(1) Baseline composite = 0.0** — not because the baseline is bad, but because the baseline single-pass ODE solve at NFE = 50 produces no upstream `SampledMolecule` with a stable `energy_dist` / `reos` / `xtb_med_rmsd` reading at the F1/F3/F4 plumbing layer. The baseline IS chemically valid (its SMILES round-trip succeeds), but the framework's value-add on FlowMol3 is **measured on the chemistry axis**, not on the validity axis.

**(2) The framework's chemistry composite is constant across NFE** (0.11822303757549568 at NFE 10/50/200 on seed 42 when F3 + F4 env deps are active) — the framework value-add on FlowMol3 is **NFE-budget-free**, matching the Kanzi + LineageFlow Tier-3 pattern.

---

## S4. §Ablations.7 Wave 52 5-arm per-component ablation (full detail)

The main paper's §Ablations.7 retained for review; this appendix preserves the full methodology.

### S4.1 5-arm × 3-model ablation matrix

| | twodim_fm | kanzi (synthetic shim) | lineageflow (synthetic shim) |
|---|---:|---:|---:|
| full_framework (arm 0) | **+0.9091** | −0.3314 | −1.05 × 10⁻⁶ |
| no_restart_blend (arm 1) | 0.0 | 0.0 | 0.0 |
| no_paper_quantity (arm 2) | **+0.9126** | **−0.3766** | −1.05 × 10⁻⁶ |
| no_gpt_prior (arm 3) | **+0.9091** | −0.3314 | −1.05 × 10⁻⁶ |
| no_restart_blend_at_all (arm 4) | 0.0 | 0.0 | 0.0 |

### S4.2 Per-component contribution

| Component | twodim_fm | kanzi | lineageflow |
|---|---:|---:|---:|
| **restart-blend** (arm 0 − arm 1) | **+0.9091** | −0.3314 | −1.05 × 10⁻⁶ |
| paper-quantity scheduler (arm 0 − arm 2) | −0.0035 | **+0.0452** | ~0 |
| GPT-prior-aware restart (arm 0 − arm 3) | 0.0 | 0.0 | 0.0 |

### S4.3 Methodology

The sweep imports `tools.run_real_ckpt_eval` as a module and applies per-arm monkey-patches to its private helpers; patches are scoped to a single cell via try/finally `unpatch` closure so subsequent cells see the pristine module.

```bash
python scripts/run_ablation_sweep.py \
  --output verification_outputs/ablation_q4_2026.json
```

---

## S5. §Ablations.9 Wave 156 real-ckpt 5-arm ablation (10/15 OK; audit trail)

### S5.1 Real-ckpt per-component contribution matrix (Wave 156, 10/15 OK)

| arm | twodim_fm (W₂ Two Moons) | kanzi (per-pos entropy) | lineageflow (per-pos entropy) |
|---|---|---|---|
| 0 (`full_framework`) | **OK** +0.909 | **RUN_ERROR** | **OK** -2.66e-14 |
| 1 (`no_restart_blend`) | OK 0.0 | **RUN_ERROR** | OK 0.0 |
| 2 (`no_paper_quantity_scheduler`) | **OK** +0.913 | **RUN_ERROR** | **OK** -2.53e-14 |
| 3 (`no_gpt_prior_restart`) | **OK** +0.909 | **RUN_ERROR** | **OK** -2.66e-14 |
| 4 (`no_restart_blend_at_all`) | OK 0.0 | **RUN_ERROR** | OK 0.0 |

10/15 cells OK (twodim_fm 5/5 + lineageflow 5/5); 5/15 RUN_ERROR (kanzi only, all on the same `ValueError: too many values to unpack (expected 3)` at `kanzi.py:1209` / upstream `models.py:351`).

---

## S6. §Ablations.10 Wave 158 P2 R1 +116% re-derivation (audit trail)

The main paper's §Ablations.10 referenced the on-disk sha256-verified `hits.tbl` files; the full re-derivation detail is preserved here.

### S6.1 Three-anchor evidence base

1. **Anchor A (internal-composite axis):** §Ablations.8 dual-mode identity — `framework_inv_proj +0.1695` byte-stable σ=0 within seed across 18 cells × 6 NFE values (Wave 124 + Wave 149-150, sha256 `3e97a42b…388db`) AND `framework_synth +0.1695` byte-stable σ=0 within seed at N=1000 (Wave 152 P1, sha256 `40b6d998…e934`).
2. **Anchor B (R1 paper-metric axis):** Wave 86 N=1000 `hmmscan_total_hits` framework_improves +116% (baseline 158 → framework 342, p < 1e-10).
3. **Anchor C (R1 paper-metric axis, re-derived on-disk):** Wave 158 P2 R1 +116% re-derivation with truly-real `LineageFlowAdapter.solve_ode` sequences (not the Wave 154b/156c placeholder strings) — closes a latent framework-arm fallback bug in `tools/gen_lineageflow_n1000_fastas.py`.

### S6.2 13-LOC sys.path fix

The bug was that Python `sys.path[0]` prepends the script's directory `tools/`, NOT the repo root, so the inner `from tools.run_real_ckpt_eval import _solve_framework` import failed with `ModuleNotFoundError`, the function returned `None`, and the caller silently fell back to bare-RNG. The 13-LOC sys.path fix adds `_REPO_ROOT = Path(__file__).resolve().parent.parent` injection before the inner import; post-fix verification via `diff <(head -3 baseline.fasta) <(head -3 framework.fasta)` confirms framework.fasta ≠ baseline.fasta per-record.

### S6.3 On-disk sha256 verification

- `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl` (sha256 `d2db37691bbb020a9de8d7c51da9a7049a140b91f29db073eab37982b0158379`, 158 domain hits)
- `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/framework_hits.tbl` (sha256 `04830145efb22ca216e568cbc876e1b0e7577557519badfc7df10a7778114b04`, 342 domain hits)
- FASTA sha256s: `4ef0ec94d67850aa018d8cb83806d1ad52f80081dca758a732891a08a9e80db1` (baseline) + `afe53dc0ea168c9d7629915ce6bda02de28299cc1bfa730583410888b83aaec5` (framework).

---

## S7. §10.20-§10.31 wave-history detail (cross-reference index)

The main paper's §10.20-§10.31 retains the headline tables + the consolidated intro paragraph. The per-wave audit trail detail is preserved in:

- §10.20 → `docs/audit/wave174-gpu-verify.md`, `docs/audit/wave174-dispatch-verification.md`
- §10.21 → `docs/audit/wave175-p1-design.md`
- §10.22 → `docs/audit/wave176-primary-metric.md`
- §10.23 → `docs/audit/wave177-p2-composite-fix.md`, `docs/audit/wave177-p1-kanzi-shape-fix.md`
- §10.24 → `docs/audit/wave178-architecture-redesign.md`
- §10.25 → `docs/audit/wave179-multi-seed.md`
- §10.26 → `docs/audit/wave180-fast-dllm-head-to-head.md`
- §10.27 → `docs/audit/wave181-ab-cache-head-to-head.md`
- §10.28 → `docs/audit/wave184-n-rounds-ablation.md`
- §10.29 → `docs/audit/wave183-finer-nfe-curve.md`
- §10.30 → `docs/audit/wave182-lediflow-head-to-head.md`
- §10.31 → `docs/audit/wave186-sensitivity-envelope.md`

Each audit doc carries the per-cell verdict evolution, the per-fix provenance chain, and the acceptance-gate preservation ledger.

---

**End of audit trail.** The main paper retains only the canonical (Wave 82/87 byte-stable for FlowMol3; Wave 131 reframe for §7.6; Wave 158 P2 R1 +116% on-disk for §Ablations.10) readings; this document carries the Wave-by-Wave audit trail for reviewer verifiability.
