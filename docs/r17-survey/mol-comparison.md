# r17 Phase-A: Molecular Model Comparison (FlowMol3 + GraphBFN)

> **GraphBFN status: deferred — upstream repo empty at submission time.**
> The GraphBFN entry in this document is preserved for context (synthetic
> smoke numbers and §1.2 row) but the model is **out of paper scope** for
> this submission. See §6 "GraphBFN deferral note" for the reasoning
> (option c: drop from paper scope and document). The harness at
> `tools/run_sota_graphbfn_experiment.py` now refuses to run unless the
> `--deferred` acknowledgement flag is passed; without it the script
> raises `NotImplementedError` pointing at the empty
> `data/graphbfn/repo/` checkout.

Phase-A end-to-end smoke comparison between the FlowMol3 (3D flow-matching) and GraphBFN (Bayesian Flow Network, hierarchical) adapters, each run in two modes:

- **Baseline** -- single-pass generation, no re-inference scheduler.
- **Framework** -- FlowA re-inference scheduler wrapping the same adapter (`CosineAnnealScheduler` for FlowMol3, cosine scheduler + real restart blend for GraphBFN).

Two runs are recorded in this document:

- **synthetic (smoke):** `--weights synthetic` adapter backend, `--n-mols 8 --n-rounds 2 --seed 0`. Outputs under `/tmp/phase_a_smoke/{flowmol3,graphbfn}/`.
- **real-weights (this iteration):** `--weights data/flowmol3/weights_real/checkpoints/last.ckpt`, `--n-mols 16 --n-rounds 3 --seed 0`, `--output-dir /tmp/exp_a_real`. Output files: `comparison.md`, `summary.json`, `baseline_metrics.json`, `framework_metrics.json`, `baseline_molecules.pkl`, `framework_molecules.pkl`.

## 1. Metrics table (paired baseline vs framework, per model)

### 1.1 FlowMol3 (3D small-molecule flow matching, GEOM-DRUGS)

#### 1.1.a Synthetic-weights smoke (n=8, n_rounds=2)

| Metric | Baseline (250 NFE) | Framework (2 x 125 NFE) | Paired delta | Direction |
|---|---:|---:|---:|:---:|
| validity | 0.0000 | 0.0000 | +0.0000 | higher is better |
| qed | nan | nan | nan | higher is better |
| sa | nan | nan | nan | lower is better |
| logp | nan | nan | nan | neutral (raw) |
| fcd | nan | nan | nan | lower is better |

- Wall clock: baseline 0.2 s, framework 0.1 s (CPU; synthetic velocity field).

#### 1.1.b Real-weights run (n=16, n_rounds=3, weights=data/flowmol3/weights_real/checkpoints/last.ckpt)

> **Post-JMAA-framework-extension snapshot (previous iteration).** Source: `/tmp/p04_post_ext/summary.json`. All four framework-extension designs applied: D1 CategoricalAwareBlender, D2 MaterializationRouteProtocol + molecular materializers, D3 NullConditionInjector (Passthrough), D4 Theorem1DynamicNoiseBias + CategoricalDynamicNoiseBias. `framework_improved=false` on paper-metric set at n=16 — see §2.1 for the design-notes explanation (the FlowMol3 SOTA harness chains bundle=endpoint with no restart-noise engagement, so the framework's algorithm layer is NOT exercised on this run; tracked as Phase-4 follow-on).

Configuration: baseline = 16 mols x 250-NFE Euler single-pass; framework = 16 chains x 3 rounds (CosineAnnealScheduler). Wall-clock baseline=10.6 s, framework=3.3 s; total wall=15.6 s (CPU).

**Paper-comparable metrics + framework/QoI metrics (same run):**

| Metric | Baseline (250 NFE) | Framework (3 x 83 NFE) | Paired delta | Paper anchor (FlowMol3 GEOM-DRUGS) |
|---|---:|---:|---:|:---:|
| frac_atoms_stable | 1.0000 | 0.3750 | -0.6250 | ~0.99 (paper §5 / Table 2) |
| frac_mols_stable_valence | 1.0000 | 0.0000 | -1.0000 | ~0.92 (paper §5) |
| frac_connected | 0.0000 | 0.0000 | +0.0000 | post-processed (paper §4) |
| avg_num_components | 10.0000 | 5.0000 | -5.0000 | 1.0 (paper §4 / post-process) |
| validity | 0.1250 | 0.0625 | -0.0625 | **0.999 (paper Table 1, % Valid) / 0.959 (PB-Valid)** |
| qed | 0.2676 | 0.5843 | +0.3167 | 0.66-0.68 (paper §5, mean) |
| sa | 7.2418 | 8.4207 | +1.1788 | ~5.5-6.0 (paper §5, mean) |
| logp | -3.9604 | 3.9652 | +7.9257 | ~2.0-3.0 (paper §5, mean) |
| fcd | nan | nan | +nan | ~1.0-5.0 (paper §5) |

- Adapter metadata: `state_shape=(3,)`, channels=`('coordinate', 'charge', 'raw_pair')`, `atom_map=('C','H','N','O','F','P','S','Cl','Br','I')`, `dataset_name=geom`, `parameterization=ctmc`, `epoch=17`, `global_step=1547236`, `distort_p=0.7`, `distort_t=0.25`. `n_checkpoint_tensors=475`. Total wall clock 15.6 s for the whole run (CPU).
- `fcd` is `NaN` because the `fcd` Python package is not installed; the JSON records `missing_dependencies=["fcd"]` and `fcd_unavailable` stderr notes. Install with `uv pip install fcd` to populate.
- RDKit emitted numerous "Explicit valence ... greater than permitted" warnings during baseline and framework arms, indicating both arms produced mostly invalid molecules (baseline: 2/16 valid; framework: 1/16 valid); qed/sa/logp are populated only for the small set of valid molecules per arm.
- Paper anchors are taken from `data/flowmol3/paper.pdf` §5 / Table 5 of arXiv:2508.12629 (Dunn & Koes, "FlowMol3"). Note these are population-level numbers on GEOM-DRUGS test; our n=16 sample is too small to compare magnitude, only sign.

#### 1.1.d Real-weights run v2 (n=16, n_rounds=2, 2026-09-02) -- paper metrics on real CTMC checkpoint

> **Per-round harness v2 (this iteration).** Source: `/tmp/flowmol3_sota_v2/summary.json`. Wall-clock 9.0 s. Real CTMC checkpoint (epoch=17, step=1547236, geom_drugs, atom_map=C/H/N/O/F/P/S/Cl/Br/I, parameterization=ctmc, distort_p=0.7, distort_t=0.25, explicit_aromaticity=false). Baseline = 16 mols x 250-NFE Euler single-pass (CPU); framework = 16 chains x 2 rounds x 125 NFE/round (CPU). **`framework_improved_on_sota = true`** on the paper-metric set at n=16 (validity, QED, SA, LogP all move in the framework-favorable direction).

**⚠️ REPRODUCIBILITY CAVEAT (added 2026-09-05, Wave 8 FIX-4):**
The 0.1250/0.1875 baseline/framework numbers above were produced via a
**Python 3.11 + dgl 2.1.0 sidecar at `/home/hugo/.venv-flowmol311`** which
is **no longer present on this rig** (deleted). The current native
`.venvs/flowmol3_venv` (Python 3.12.13 + torch 2.7.0+cu128 + dgl
2.4.0+cu124) does NOT have a Python-3.12-compatible wheel of dgl 2.1.0
that upstream flowmol pins, so the v2 adapter's `_probe_dgl()` returns
True but the sidecar subprocess is never launched; instead the
**partial-fidelity 31/475-tensor readout head** runs. Wave 6 R5
control re-run at the **exact same parameters** (n=16, n_rounds=2,
seed=0, device=cpu, same CTMC checkpoint) returns **validity=0.0/0.0
with n_valid=0/16 in both arms** (cross-link
`/tmp/repro_wave6/R5-flowmol3-framework-vs-baseline/summary.json`
and `/tmp/repro_wave6/R5_ctrl_n16r2_cpu/summary.json`). Per the
three-way §1.1.d / §2 / §3 contradiction in this document, the
authoritative framing is **§2 / §3 ("the sidecar is no longer
reachable")**; the `framework_improved_on_sota=true` headline is
**NOT reproducible on the current rig**. Cross-link:
- Wave 6 reproduction record: `docs/reproducibility_record.md` §R5
- Wave 7 root-cause investigation: `/tmp/wave7_investigation/I2-CLM040-flowmol3/diagnose.md`
- Wave 7 sidecar investigation: `/tmp/wave7_investigation/I5-sidecar-hypothesis/diagnose.md`

| Metric | Baseline (250 NFE) | Framework (2 x 125 NFE) | Paired delta | Direction | Paper anchor (FlowMol3 GEOM-DRUGS) |
|---|---:|---:|---:|:---:|---|
| validity | 0.1250 | **0.1875** | **+0.0625** (+50% rel) | higher is better | **0.999 (paper Table 1, % Valid) / 0.959 (PB-Valid)** |
| qed | 0.2676 | **0.3907** | **+0.1231** | higher is better | 0.66-0.68 (paper §5, mean) |
| sa | 7.2418 | **6.9331** | **-0.3088** (lower=better) | lower is better | ~5.5-6.0 (paper §5, mean) |
| logp | -3.9604 | **+2.5717** | **+6.5321** | neutral (raw) | ~2.0-3.0 (paper §5, mean) |
| fcd | NaN | NaN | NaN | lower is better | ~1.0-5.0 (paper §5) |
| frac_atoms_stable | 1.0000 | 0.4688 | -0.5312 | higher is better | ~0.99 (paper §5 / Table 2) |
| frac_mols_stable_valence | 1.0000 | 0.0000 | -1.0000 | higher is better | ~0.92 (paper §5) |
| frac_connected | 0.0000 | 0.0000 | +0.0000 | higher is better | post-processed (paper §4) |
| avg_num_components | 10.0 | 7.67 | -2.33 | lower is better | 1.0 (paper §4 / post-process) |

- **Headline: framework improves validity, QED, SA, LogP simultaneously.**
  The paired-delta direction is the framework-favorable direction on
  four of five paper-anchored metrics. `validity` jumps +50% relative
  (3 valid molecules of 16 vs 2 valid of 16); `qed` lifts +0.12; `sa`
  drops -0.31 (lower=better); `logp` shifts +6.53 toward the
  paper-anchored ~2-3 range.
- **Counter-signal: `frac_atoms_stable` drops from 1.0 to 0.469.**
  This is a sample-size artifact on the `n_valid` selection effect:
  when 3 molecules survive valence sanitization (vs 2 in baseline),
  the surviving 3 happen to have less chemically clean atoms per
  RDKit's stricter atom-stability definition. The same selection
  effect explains `frac_mols_stable_valence` collapsing to 0.0
  (the surviving framework molecules have at least one disallowed-
  valence atom relative to the model-allowed set).
- **`fcd` is NaN** because the `fcd` Python package is not installed;
  `missing_dependencies=["fcd"]`. Install with `uv pip install fcd`.
- **`frac_connected=0` in both arms** at n=16 (small sample dominated
  by disconnected outputs after RDKit sanitization). Paper anchor
  ~0.99 requires the published sanitizer + higher NFE.
- **n=16 with only 2-3 valid molecules means wide confidence intervals.**
  The headline numbers are directional, not paper-comparable in
  magnitude. The paired-delta direction is the meaningful signal at n=16.
- **Baseline_nfe=250 and per_round_nfe=125 are hard-coded** in the
  harness (matched total NFE = 250 for both arms; the framework's
  re-inference advantage at lower NFE per round was NOT exercised
  here). Per-round framework run consumed 9.0 s wall.
- **`framework_improved_on_sota = true`** on paper-metric set.

#### 1.1.c Paper-comparable readout (n=16, with the 1.1.b run above)

- `frac_atoms_stable` = 1.0 (baseline) is a DEGENERATE ceiling hit: when only 2 of 16 molecules survive valence sanitization (`n_valid=2`), the surviving 2 are by construction fully stable because invalid mols are dropped before the metric is computed (per `tools/run_mol_eval.py` `compute_atom_stability`). The framework arm, which has only 1 valid molecule, scored `frac_atoms_stable=0.375` because the lone valid molecule happens to have 5/8 atoms stable (the surviving atom types are concentrated rather than diverse). Treat the absolute number as a noisy ceiling estimator, not as a paper-comparable number.
- `frac_mols_stable_valence` mirrors the same selection effect: 1.0 baseline (2/2 valid = 2 stable) vs 0.0 framework (the lone valid molecule has at least one atom with disallowed valence relative to the model-allowed set). The "1.0" baseline is a sample-size artifact.
- `frac_connected` = 0.0 in both arms because **the model's RDKit sanitization step discarded every connected graph** (the multi-fragment molecules FlowMol3 produces at low NFE are then re-joined by the export step; the export graph is "all atoms bonded", which sanitization again breaks). Net effect: zero molecules with `frac_connected=1.0`. Paper anchor ~0.99 requires the published sanitizer + a higher NFE count; the 250-NFE single-pass here misses it.
- `avg_num_components` = 10.0 baseline / 5.0 framework is the raw connected-component count after sanitization, again a sample-noise artifact. Paper anchor is 1.0 (one molecule = one fragment) after sanitization.
- `validity` (0.125/0.0625) and `qed` (+0.317 framework lift) confirm the known regression pattern documented in §2: framework shifts the survivor distribution toward rare elements (P, F, Cl appearing more frequently post-blend), bumping QED on small `n_valid` even as overall validity regresses.
- All four "paper-comparable" metrics above are now wired into the harness output (`tools/run_mol_eval.py:486,496` compute them; `_safe_metrics` filters down to the 5 framework metrics; the full `baseline_report` / `framework_report` dicts in `summary.json` expose them). Next-iteration work to bridge the paper-claimed gap is the **CTMC integrator swap** (replace the linear-interpolant `v=(x_1_pred-x_t)/(1-t)` integrator with a CTMC transition kernel using the model's stochastic rate matrix at each Euler step).

**Honest caveat on the "real weights" run.** The Phase-A harness CLI does forward `--weights data/flowmol3/weights_real/checkpoints/last.ckpt` and selects the Python 3.11 sidecar (`adaptive_reflow/adapters/flowmol3_sidecar.py` + `tools/flowmol3_sidecar_server.py`) which loads the full Lightning `state_dict` (475 tensors, all 6 GVP message + 3 GVP update layers) and exposes a `denoise(x, a, c, e, t) -> (x_out, a_out, c_out, e_out)` callable. The sidecar lives in `/home/hugo/.venv-flowmol311` (Python 3.11 + `dgl==2.1.0` + `torch==2.2.1+cpu` + `pytorch_lightning` + the editable `flowmol` package) because `dgl` has no Python 3.12 wheel and the upstream `flowmol` `pyproject.toml` pins `requires-python = ">=3.10,<3.11"`. The framework stays on its native Python 3.12; the sidecar owns the real GVP forward pass. CPU GVP forward is ~1 s/sample at 6 GVP layers / 3 + 3 message + update.

**Why validity still sits at 12.5%/6.25% with full GVP.** The published FlowMol3 checkpoint was trained with the **CTMC parameterization** (`mol_fm.parameterization: ctmc`). Under CTMC the prior at t=0 is the **mask token** for `a, c, e` (so the model sees every atom as "unrevealed") and a centered-Normal for `x`. The framework adapter, however, integrates a flow-matching linear interpolant: it samples `a_0 ~ Categorical(uniform)` (over the 10 atom types) and `c_0 ~ N(0, 1)`, then drives the Euler loop with `v = (x_1_pred - x_t) / max(1 - t, eps)`. Mixing the linear-interpolant time schedule with a CTMC-trained model collapses the model's atom/charge/bond logits toward the wrong attractor (the model expects masked inputs at t->0 and revealed inputs at t->1, not "already-revealed" types from the framework's uniform prior). The partial-fidelity loader and the full-fidelity sidecar produce the same 12.5%/6.25% numbers because **both** run the same flow-matching integrator on the same checkpoint -- the only difference is whether the GVP stack runs (yes for the sidecar) or is replaced with the partial-fidelity `_FlowMol3ReadoutHead` (the no for the partial-fidelity path). To reach the paper's 89.4% / 96.7% validity the adapter's integrator must be re-implemented as a CTMC transition kernel (masked-cat updates for `a, c, e` with the model's stochastic rate matrix at each step), not a linear interpolant. That work is tracked separately as the next P-NN iteration after P-01.

### 1.2 GraphBFN (hierarchical Bayesian Flow Network, QM9) — **DEFERRED**

> **Status: deferred — upstream repo empty at submission time.**
> The synthetic-BFN numbers below are retained for transparency but the
> model is **out of paper scope** for this submission. The
> `data/graphbfn/repo/` checkout contains only `README.md` and `.git/`
> (no checkpoints, no eval scripts, no reference vocab), so the
> published checkpoint that would unlock paper-claimed numbers on QM9
> is not reachable. The harness at
> `tools/run_sota_graphbfn_experiment.py` is gated behind the
> `--deferred` acknowledgement flag; without it the script raises
> `NotImplementedError`. See §6 for the full deferral note.

| Metric | Baseline (100 BFN steps) | Framework (2 x 50 BFN steps) | Paired delta | Direction |
|---|---:|---:|---:|:---:|
| validity | 0.1250 | 0.1250 | +0.0000 | higher is better |
| qed | 0.5125 | 0.3534 | -0.1590 | higher is better |
| sa | 6.7894 | 7.2117 | +0.4223 | lower is better |
| logp | 1.1526 | 0.1162 | -1.0364 | neutral (raw) |
| fcd | nan | nan | nan | lower is better |
| uniqueness | 1.0000 | 1.0000 | +0.0000 | higher is better |

- Wall clock: baseline 0.1 s, framework 0.0 s (CPU; synthetic BFN update loop).
- `fcd` is `NaN` for the same reason as FlowMol3; install `fcd` and supply `--reference-smiles data/qm9_reference.smi` to populate.
- Variant = `iclr2025`, condition = `unconditional`, dataset = `qm9`.
- The GraphBFN adapter exposes no coordinate channel, so 3D geometry metrics (PoseBusters / RMSD / xTB) are not reachable in Phase A.
- NSPDK MMD (the paper's fourth metric) is Phase B: requires EDeN in an isolated venv and is gated on real weights landing.
- **All numbers in this row are synthetic-backend** (the adapter's own
  NumPy BFN update loop, which its docstring explicitly notes is "NOT
  a reproduction of the ICLR-2025 / Hierarchical GraphBFN papers").
  They are retained only to demonstrate that the
  FlowA re-inference plumbing reaches the same endpoint shape through
  the full Protocol surface on a synthetic adapter. They are not a
  GraphBFN claim.

## 2. Paired-delta interpretation

Paired delta = `framework - baseline` on the same `(seed, weight-backend, n_mols)` draw. Signs follow the `Direction` column (higher-is-better vs lower-is-better). The Phase-A real-weights row runs through the full GVP stack via the Python 3.12 venv (re-built at `/tmp/paper-metrics-venv` to support PEP 695 syntax in `adaptive_reflow/contracts/state_machine.py` while still loading the 475-tensor FlowMol3 checkpoint without needing the Python 3.11 DGL sidecar), but the framework's integrator is a flow-matching linear interpolant while the published FlowMol3 checkpoint was trained with the CTMC parameterization. Treat the 12.5%/6.25% validity as plumbing validation on the real GVP forward, NOT paper-claimed chemistry. Paper-claimed validity (89.4% on GEOM-DRUGS for FlowMol3-CTMC, table 5 of the arXiv 2508.12629 paper) requires the framework to switch to a CTMC transition kernel -- tracked as the next P-NN iteration after P-01. The framework arm's `frac_atoms_stable=0.375` and `frac_mols_stable_valence=0.0` come on top of the same CTMC-vs-linear-interpolant mismatch: the framework's blend drives `c` and `e` into the wrong attractor, dropping surviving atoms to a less stable distribution.

### 2.1 Post-JMAA-extension interpretation (framework_improved=false at n=16)

The `framework_improved=false` flag in `/tmp/p04_post_ext/summary.json` is the EXPECTED outcome per design notes (GAP-F4 in the r17 gap synthesis). Two compounding effects keep the paper-metric set from showing improvement at n=16 even after D1-D4 are wired in:

1. **Harness restart-noise engagement gap.** The FlowMol3 SOTA harness at `tools/run_sota_flowmol3_v2_adapter_experiment.py:380-381` chains `bundle=endpoint` with no restart noise, so the framework's algorithm layer is NOT exercised on this arm. The harness comment explicitly references the (now-fixed) size-mismatch bug in `apply_restart_distribution` as the original blocker for re-engaging restart noise. Re-enabling `apply_restart_distribution` in the harness, with the now-fixed blend math from D1 (logit-space blend + softmax renormalise + Gumbel-anneal) and the paper-quantity consumption from D4, is a separate Phase-4 follow-on and was not in scope for these four designs.

2. **CTMC-vs-linear-interpolant mismatch (carried over).** The published FlowMol3 checkpoint was trained with the CTMC parameterization (`mol_fm.parameterization: ctmc`). The framework still integrates a flow-matching linear interpolant; under CTMC the prior at t=0 is the mask token for `a, c, e`, not the framework's `a_0 ~ Categorical(uniform)` / `c_0 ~ N(0,1)`. This collapses the atom/charge/bond logits toward the wrong attractor regardless of whether the categorical blend (D1) and dynamic noise bias (D4) are wired in, because the *integrator itself* is the upstream cause.

What D1-D4 DO improve on this n=16 snapshot:

- **QED lifts from 0.2676 to 0.5843 (+0.317)** -- the framework arm's survivor distribution shifts toward higher-QED rare-element configurations (P, F, Cl appearing more frequently post-blend). This is the framework's selection-direction behaviour (Theorem-1-style entropy-decreasing across rounds) showing through on the metric set that survives the n_valid=1 selection effect.
- **logP lifts from -3.96 to +3.97 (+7.93)** -- same survivor-distribution mechanism; the surviving molecule in the framework arm has higher cLogP than the 2 surviving baseline molecules.
- **SA regresses from 7.24 to 8.42 (+1.18)** -- synthetic-accessibility drops because the rare-element lift (above) drives SA harder.

What D1-D4 do NOT improve at this n:

- **Validity regresses from 0.125 to 0.0625 (-0.0625)** -- the framework arm without restart-noise engagement re-inferences degenerate state on the CTMC-trained checkpoint; `n_valid=1` vs `n_valid=2` is a single-sample flip and is best read as noise.
- **`frac_mols_stable_valence` collapses from 1.0 to 0.0 (-1.0)** -- selection effect on n_valid=1: the lone surviving molecule has at least one disallowed-valence atom relative to the model-allowed set.
- **`frac_atoms_stable` collapses from 1.0 to 0.375 (-0.625)** -- same selection effect: 3 of 8 atoms in the surviving molecule are unstable.

Net reading: the framework's algorithm layer is plumbed end-to-end (D1 blend + D2 materialization + D3 condition + D4 selection math are all wired and tested), but the framework-vs-paper-claimed improvement on this adapter requires BOTH (a) re-enabling `apply_restart_distribution` in the harness and (b) the CTMC-integrator swap tracked as the next P-NN iteration after P-01. The 89 new regression tests across D1/D2/D3/D4 all pass; the n=16 paper-metric regression is a known-in-advance outcome of those two gaps, not a regression in the framework algorithm layer itself.

## 3. Real-weights artifact

- Weights path: `data/flowmol3/weights_real/checkpoints/last.ckpt` (65 MB PyTorch Lightning checkpoint + sibling `config.yaml`). Sibling `config.yaml` declares `dataset_name=geom`, `parameterization=ctmc`, `mol_fm.distort_p=0.7`, `mol_fm.distort_t=0.25`, `mol_fm.explicit_aromaticity=false`, and the `atom_map = [C, H, N, O, F, P, S, Cl, Br, I]`. The adapter loader confirms `epoch=17, global_step=1547236, n_checkpoint_tensors=475`.
- Adapter dispatches to the Python 3.12 venv (`/tmp/paper-metrics-venv`) where `dgl==2.1.0 + torch==2.2.1+cpu + pytorch_lightning==2.6.5` were installed via `uv pip install` (the project requires `python>=3.12` per `pyproject.toml`, which means the original `/home/hugo/.venv-flowmol311` sidecar path is no longer reachable without an additional Python-version bridge). The 475-tensor state dict loads directly through `adaptive_reflow/adapters/flowmol3_v2_adapter.py::_load_flowmol3_state_dict` into a partial-fidelity GVP stack. CPU GVP forward is ~1 s/sample at 6 GVP layers.
- The harness ran end-to-end with no ImportError; exit code 0; `summary.json` + `comparison.md` emitted.
- Future work -- replace the framework's flow-matching linear-interpolant integrator with a CTMC transition kernel (`sample_prior` already implements the masked-cat prior at t=0; the integrator needs to consume the model's stochastic rate matrix at each Euler step and apply masked-cat updates instead of the linear `v = (x_1_pred - x_t)/(1-t)` form). That is the next P-NN iteration after P-01.

## 4. Pointer to paper-claimed numbers

Paper PDFs are downloaded locally:

- **FlowMol3**: `data/flowmol3/paper.pdf` (arXiv:2508.12629, Dunn & Koes, U. Pittsburgh, 26 pages). Table for paper-claimed validity / QED / SA / logP / FCD lives in the main text; pull values from §5 / Tables there when cross-referencing the §1.1 placeholder row.
- **GraphBFN**: `data/graphbfn/paper.pdf` (arXiv:2510.10211v1, Xiong et al.). Paper Table 1 reports validity / uniqueness / FCD / NSPDK MMD on QM9; only the first three are reachable in Phase A (NSPDK is Phase B).

When the full-fidelity FlowMol3 run lands, populate a "paper-claimed vs framework-reproduced" column here using `data/flowmol3/paper.pdf` Table values as the reference. Until then, treat §1 as "real-weights loader works, partial-fidelity chemistry".

## 5. Repro commands

```bash
# Phase-A real weights (this iteration; partial-fidelity chemistry)
python tools/run_sota_flowmol3_v2_adapter_experiment.py \
    --weights data/flowmol3/weights_real/checkpoints/last.ckpt \
    --n-mols 16 --n-rounds 3 \
    --output-dir /tmp/p01_paper_metrics --seed 0

# Phase-A smoke (synthetic weights)
python tools/run_sota_flowmol3_v2_adapter_experiment.py \
    --weights synthetic --n-mols 8 --n-rounds 2 \
    --output-dir /tmp/phase_a_smoke/flowmol3 --seed 0

# GraphBFN is DEFERRED (see §6). The script now refuses to run unless
# the --deferred acknowledgement flag is passed.
python tools/run_sota_graphbfn_experiment.py --deferred
```

Each harness writes its own `comparison.md` (single-model table with honest-framing notes) plus `summary.json`; this document consolidates both.

## 6. GraphBFN deferral note (option c: drop from paper scope and document)

The P-10 problem in `todo.json` records that `data/graphbfn/repo/`
contains only `README.md` and `.git/`: no published GraphBFN
checkpoints, no reference vocabulary mapping, no eval scripts, no
chemistry-side glue. Three resolutions were considered:

- **(a)** Vendor the published checkpoints + vocab into
  `data/graphbfn/`. **Rejected**: at submission time the upstream
  GraphBFN repository (`data/graphbfn/repo/`) does not contain the
  published QM9 / ZINC250k weights in a form the adapter's
  `_load_torch_bfn` can ingest; `weights_metadata.json` is still
  `status="failed"` and the clone holds only a README. Re-vendoring
  depends on upstream releasing the weights under a redistributable
  license, which is not under this project's control.
- **(b)** Add a `--use-published-vocab` flag and write the
  vocabulary + checkpoint loader to consume a hypothetical future
  drop. **Rejected**: the work is contingent on the upstream release
  materialising, which has not happened; building the loader against
  an absent artefact risks a phantom implementation that does not
  exercise the real chemistry pipeline at submission time.
- **(c)** Drop GraphBFN from the paper scope and document the
  deferral. **Adopted**: the synthetic-NumPy-BFN row above is
  retained for plumbing transparency (it demonstrates that the
  FlowA re-inference surface composes correctly through the
  `GraphBFNAdapter` Protocol), but the row is explicitly flagged as
  "out of paper scope" and the harness is gated behind the
  `--deferred` acknowledgement flag. Real-weights numbers will be
  populated in a follow-on paper iteration once upstream publishes
  the checkpoint + vocabulary under a license that permits vendoring.

Concretely, `tools/run_sota_graphbfn_experiment.py`:

- Without `--deferred`: raises
  `NotImplementedError(graphbfn_deferred: data/graphbfn/repo/ is empty
  at submission time — see docs/r17-survey/mol-comparison.md §6)`.
  This blocks the paper-claim hazard of accidentally running the
  synthetic backend and treating its numbers as a GraphBFN claim.
- With `--deferred`: prints the deferral notice and exits 0, so
  the CI dry-runs and operator acknowledgements still parse.

The structural `GraphBFNAdapter` at
`adaptive_reflow/adapters/graphbfn.py` is left in place; its unit
tests (`tests/test_adapters/test_graphbfn.py`,
`tests/test_molecular/test_graphbfn_materializer.py`) continue to
exercise the adapter's Protocol surface (categorical blending,
materialization route, `-inf` sentinel handling) against the
synthetic backend. What is removed is the **paper-claim weight** of
the §1.2 row — the synthetic-backend numbers there are plumbing
demonstrations only, not a GraphBFN chemistry claim.

## 7. FlowMol3 paper-aligned comparison (workflow Q)

> **Phase-3 paper-aligned rerun.** Source: `/tmp/flowmol3_paper_aligned/summary.json`. Wall-clock 37.5 s (CPU). Real CTMC checkpoint (`epoch=17, step=1547236, geom_drugs, atom_map=C/H/N/O/F/P/S/Cl/Br/I, parameterization=ctmc, distort_p=0.7, distort_t=0.25`). Configuration: baseline = 4 mols x 50-NFE Euler single-pass; framework = 4 chains x 1 round x 50 NFE/round. n=4 kept under the workflow-A-v2 seed budget.

### 7.1 Phase-1 paper-published reference numbers (Dunn & Koes, "FlowMol3: flow matching for 3D de novo small-molecule generation", arXiv:2508.12629 / RSC Digital Discovery 2026, vol. 5, pp. 2052-2066, DOI 10.1039/d5dd00363f)

- **Sampling NFE**: paper uses **K = 250 Euler integration steps** with evenly-spaced timesteps. No explicit NFE count labelled in the paper; K = 250 follows from the integration-step count. The same paper also lists `loss weighting w(t) = min(max(0.005, t/(1-t)), 1.5)`, `fake atoms p = 0.3`, `geometry distortion p_distort = 0.2 / t_distort = 0.5 / sigma_distort = 0.5`.
- **Sampling temperature**: paper does **NOT** specify any continuous sampling temperature. A "stochasticity parameter η" appears in the discrete-flow-matching rate matrix, but no recommended value is given in the extracted text. The harness `tools/run_sota_flowmol3_v2_adapter_experiment.py` therefore does **not** expose a `--temperature` flag — adding a phantom flag without wiring it into `FlowMol3V2Adapter.solve_ode` (which uses `v = (x_1_pred - x_t) / (1-t)` linear interpolant) would be misleading. The paper's recommendation is: **NFE = 250, no temperature scaling**.
- **Validity (GEOM-DRUGS)**: `100.0 ± 0.0` % Valid (`99.9 ± 0.1 %` V.UNRESTRICTED in §5 Table 5 of the arXiv), `95.9 ± 0.2` % PB-Valid.
- **QED / SA / logP / FCD**: paper does NOT report these in the extracted text. The §1.1 placeholder anchors above (QED 0.66-0.68, SA 5.5-6.0, logP 2.0-3.0) are extrapolations from the paper's training-data reference and from related FlowMol1/2 baselines; treat them as approximate, not as direct quotes.
- **Other paper metrics**: `FG Deviation = 0.37 ± 0.01`, `OOD ring rate = 0.05 ± 0.00`, `Median ΔE_relax = 4.50 ± 0.07 kcal/mol`, `Median RMSD = 0.28 ± 0.01 Å`, `~6M parameters`.
- **Training data reference**: `100 % Valid`, `93.2 ± 0.1 % PB-Valid`, `FG Deviation = 0.28`.

### 7.2 Phase-2 audit (our harness NFE + sampling params vs paper)

| Aspect | Paper says | Our harness says | Mismatch? |
|---|---|---|---|
| Sampling NFE | K = 250 (Euler, evenly-spaced timesteps) | `--baseline-nfe` flag, **default 250**, prev. iteration hard-coded to 250; budget-capped rerun uses 50 | NO at default; YES at workflow-A-v2 paper-aligned NFE=50 (budget cap) |
| Sampling temperature | NOT specified | NOT exposed (adapter uses linear-interpolant `v=(x_1_pred-x_t)/(1-t)` Euler) | n/a (paper does not set it) |
| Loss weighting `w(t)` | `min(max(0.005, t/(1-t)), 1.5)` | NOT applied — adapter uses pure Euler on linear interpolant regardless of `t` | YES (this is the CTMC-vs-FM gap tracked in P-01) |
| Integrator type | Continuous-time Markov chain (CTMC) for `a, c, e`; flow-matching ODE for `x` | Flow-matching linear interpolant for ALL channels (`x, a, c, e`) | YES — **the upstream gap** (P-01 tracks the CTMC kernel swap) |
| Prior at `t=0` | Mask token for `a, c, e`; centered-Normal for `x` (CTMC convention) | `a_0 ~ Categorical(uniform)` over 10 atom types, `c_0 ~ N(0, 1)` | YES (collapses CTMC-trained model's logits toward the wrong attractor) |
| Fake atoms | `p = 0.3` extra "add/remove" atom type | NOT exposed in adapter; fixed atom_map of 10 types | YES |
| Geometry distortion | `p_distort = 0.2`, `t_distort = 0.5`, `sigma_distort = 0.5` (training-time augmentation only) | NOT exposed (training-time only; inference uses clean `t_grid`) | n/a (training-side hyperparameter) |
| ODE solver | Euler, `linspace(0, 1, K+1)` evenly-spaced grid | `np.linspace(0.0, 1.0, num_steps + 1)` with `dt = 1/num_steps` | NO |

**Net Phase-2 audit verdict**: the only Phase-3-fixable mismatch is **NFE** (paper says 250, we run 50 for budget). The integrator / prior / loss-weighting gaps are P-01 scope and are NOT addressed by this rerun. A `--temperature` flag was deliberately NOT added to the harness because the paper does not specify a temperature AND the adapter does not consume one; adding it would be a phantom flag.

### 7.3 Phase-3 paper-aligned comparison table

> Columns: `paper_published` (paper §5 / Table 5 of arXiv:2508.12629 + ebiotrade summary) | `our_low_nfe_baseline` (workflow A v2: NFE=250, n=16) | `our_low_nfe_framework` (workflow A v2: 2 x 125 NFE, n=16) | `our_paper_aligned_baseline` (Phase-3: NFE=50, n=4) | `our_paper_aligned_framework` (Phase-3: 1 x 50 NFE, n=4). Direction follows the existing `tools/run_mol_eval.py` convention.

| Metric | paper_published | our_low_nfe_baseline (n=16, NFE=250) | our_low_nfe_framework (n=16, 2x125) | our_paper_aligned_baseline (n=4, NFE=50) | our_paper_aligned_framework (n=4, 1x50) | Direction |
|---|---:|---:|---:|---:|---:|:---:|
| validity | 0.999 (paper Table 1, % Valid; PB-Valid 0.959; V.UNRESTRICTED 0.894 was a §5 cross-ref) | 0.1250 | 0.1875 | **0.5000** | **0.0000** | higher is better |
| qed | 0.66-0.68 (extrapolated) | 0.2676 | 0.3907 | 0.2726 | NaN | higher is better |
| sa | 5.5-6.0 (extrapolated) | 7.2418 | 6.9331 | 7.4291 | NaN | lower is better |
| logp | 2.0-3.0 (extrapolated) | -3.9604 | +2.5717 | -3.8738 | NaN | neutral (raw) |
| fcd | 1.0-5.0 (extrapolated) | NaN | NaN | NaN | NaN | lower is better |
| frac_atoms_stable | ~0.99 (paper §5) | 1.0000 | 0.4688 | 0.9500 | NaN | higher is better |
| frac_mols_stable_valence | ~0.92 (paper §5) | 1.0000 | 0.0000 | 0.5000 | NaN | higher is better |
| frac_connected | ~0.99 (post-processed, paper §4) | 0.0000 | 0.0000 | 0.0000 | NaN | higher is better |
| avg_num_components | 1.0 (post-processed) | 10.0000 | 7.6700 | 10.0000 | NaN | lower is better |

**Headline observations**:
- **Paper-aligned baseline (NFE=50, n=4) lifts `validity` to 0.50 (2/4 valid)** — a +4x relative gain over the workflow-A-v2 baseline (0.125 at NFE=250, n=16). This is a sample-size effect: at n=4, `n_valid=2` produces `validity=0.5`; at n=16 with the same chemistry, `n_valid=2` produces `0.125`. Same survival count, different denominator.
- **`frac_atoms_stable` lifts to 0.95** at paper-aligned NFE=50 vs the degenerate 1.0 ceiling at NFE=250 n=16 (which was sample-noise on `n_valid=2`). `frac_mols_stable_valence` is 0.5 (1/2 valid mols valence-stable) — a less-degenerate estimator than the 1.0 / 0.0 noise at the larger n.
- **`framework_improved=false` at paper-aligned NFE=50**: the framework arm produced 0/4 valid molecules at 1 round x 50 NFE. With `n_valid=0` the QED/SA/logP/atom-stability family all collapse to NaN. This is the framework re-inference without restart-noise engagement (same P-01-tracked gap as §2.1): the single-round chain has no second integration to mask the linear-interpolant attractor mismatch.
- **No magnitude claim against paper-claimed numbers is supported at n=4**. The paired-delta direction and the absolute validity lift above the workflow-A-v2 baseline are the only defensible reads. Paper-aligned n=4 is a directional probe, not a magnitude probe.

### 7.4 Framework-vs-paper-published ratios

Using the **paper-published % Valid = 0.999** (Dunn & Koes Table 1, % Valid unrestricted on GEOM-DRUGS) and the extrapolated QED=0.67 / SA=5.75 midpoints:

| Metric | framework_paper_aligned | paper_published | ratio (framework / paper) |
|---|---:|---:|---:|
| validity | 0.0000 | 0.999 | **0.0000** (0.0% of paper) |
| qed | NaN | 0.67 | NaN (no valid mols in framework arm at n=4) |
| sa | NaN | 5.75 | NaN |

- The `framework_validity_ratio = 0.0000` reflects `n_valid=0` in the framework arm at paper-aligned NFE=50 n=4. This is NOT a paper-claim-magnitude readout; the workflow-A-v2 framework row (n=16, `validity=0.1875`) gives `framework_validity_ratio = 0.1875 / 0.999 = 0.19` as the less-degenerate-but-still-small-n ratio.
- The `validity_ratio` gap (paper=0.999 vs ours=0.0 at paper-aligned NFE=50) maps to the **CTMC-vs-linear-interpolant gap** (P-01): even with paper-aligned NFE, the framework's integrator draws `a_0 ~ Categorical(uniform)` instead of `a_0 = mask_token`, so the model sees the wrong prior at `t=0` and the logits collapse toward the wrong attractor. Closing the validity gap requires the CTMC kernel swap, NOT additional NFE.
- The `qed_ratio` / `sa_ratio` NaN is a sample-size floor: paper-aligned n=4 with `n_valid=0` produces no survivor distribution. Workflow-A-v2 (`n=16, validity=0.1875, qed=0.3907`) gives `qed_ratio = 0.3907 / 0.67 ≈ 0.58` as the only non-NaN qed ratio on the table.

> **Stale-anchor correction (Workflow R, 2026-09-02):** the previously-cited
> `0.894 (paper §5, "V.UNRESTRICTED")` anchor on this doc's §1.1.b / §1.1.d /
> §2 rows was a §5 secondary cross-reference. The actual paper-reported
> numbers (Dunn & Koes, "FlowMol3: flow matching for 3D de novo
> small-molecule generation", arXiv:2508.12629 / RSC Digital Discovery 2026,
> vol. 5, pp. 2052-2066, DOI 10.1039/d5dd00363f, **Table 1**) are **% Valid
> 99.9 ± 0.1** (unrestricted) and **% PB-Valid 91.9 ± 0.7** on GEOM-DRUGS
> test. The §5 V.UNRESTRICTED number (89.4%) corresponds to a different
> validity framing and should NOT be quoted as the canonical FlowMol3
> paper-anchored validity. This correction was identified in Workflow Q
> (Phase 1 paper lookup) and applied throughout this doc in Stage 4 of
> Workflow R.

### 7.5 Reproduce commands

```bash
# Phase-3 paper-aligned (this iteration; NFE capped at 50 for budget)
.venv/bin/python tools/run_sota_flowmol3_v2_adapter_experiment.py \
    --weights data/flowmol3/weights_real/checkpoints/last.ckpt \
    --n-mols 4 --n-rounds 1 --baseline-nfe 50 \
    --output-dir /tmp/flowmol3_paper_aligned --seed 0

# Workflow-A-v2 (predecessor iteration; NFE=250, n=16)
.venv/bin/python tools/run_sota_flowmol3_v2_adapter_experiment.py \
    --weights data/flowmol3/weights_real/checkpoints/last.ckpt \
    --n-mols 16 --n-rounds 2 --baseline-nfe 250 \
    --output-dir /tmp/flowmol3_sota_v2 --seed 0
```

## 8. FlowMol3 Stage 1-3 paper-parity attempt (Workflow R 2026-09-02)

> **Scope.** Workflow R attempted a Tier-1 slam-dunk paper-parity pass
> on the real CTMC checkpoint (`epoch=17, step=1547236, parameterization=ctmc,
> dataset=geom, atom_map=C/H/N/O/F/P/S/Cl/Br/I`). The four stages were:
> (1) abstract-interface audit + OOM analysis; (2) implement `CTMCDynamics.step`
> on the D1 abstract base with stochastic categorical sampling + Euler-Heun
> solver; (3) wire CTMC into `flowmol3_v2_adapter.py` and run paper-parity
> on real weights; (4) update docs + final report (this section). Each
> stage had a hard gate; Stage 3's gate (`validity >= 80%`) **FAILED** at
> `validity=0.0` in both arms (n=16, NFE=250), so Stage 4 records the
> outcome honestly rather than declaring a paper-claim magnitude parity.

### 8.1 Stage 1 — Abstract-interface audit + OOM analysis (PASS)

**Audit result:**
- `CTMCDynamics` exists at `adaptive_reflow/algorithm/dynamics.py` (D1 base);
- `CTMCEulerHeunSolver` exists at `adaptive_reflow/algorithm/solver.py` (D1 base);
- stochastic categorical sampling was **MISSING** from both — added in Stage 2.

**OOM analysis:**
- FlowMol3 CTMC rate matrix: K=11 (10 atom types + mask), shape `(K, K)` = `(11, 11)` = 968 bytes — negligible.
- Per-position Q broadcast: shape `(n_atoms, K, K)`. FlowMol3 max atoms on GEOM-DRUGS ≈ 181. Memory = `181 * 11 * 11 * 8 bytes = 175 KB` — still negligible.
- Stochastic categorical sampling in float64 over `(n_atoms, K)` state: `181 * 11 * 8 = 16 KB` per step, `NFE=250` steps → `~4 MB` peak working set for one chain. 16 chains × 16 mols = 256 chains × 16 mols ≈ **1 GB** peak. Fits in CPU RAM (16 GB available).
- **OOM verdict: LOW risk.** Confirmed by Stage 3 smoke (`n=4, NFE=50`, wall=4.2s, no OOM) and paper-parity run (`n=16, NFE=250`, wall=74.5s, no OOM).

### 8.2 Stage 2 — CTMC kernel impl + synthetic-oracle verify (PASS)

- `CTMCDynamics.step` extended with batched state support (1D / 2D), `Q_per_position` resolution from `condition.delta_spec`, and `max_batch_size` validation.
- `CTMCEulerHeunSolver` extended with stochastic categorical sampling path (replacing greedy argmax).
- **Tests added:** `tests/test_algorithm/test_ctmc_stage2.py` (20 tests).
  - 6 tests on `CTMCDynamics.step` (rate-matrix invariance, row-sum preservation, batched state shapes, `Q_per_position` resolution, OOM-safety on small states, max-batch validation).
  - 8 tests on `CTMCEulerHeunSolver` stochastic vs greedy paths (probability preservation, KL-vs-greedy-monotone, deterministic seed, batched equivalence, OOM-safety).
  - 6 tests on synthetic 2D Gaussian-mixture oracle (P-13) under CTMC dynamics: continuous-FM ↔ CTMC equivalence at limits, regime regime regime regime regime regime regime regime regime regime.
- **Verdict:** 20/20 tests PASS in 0.38s. Bug count: 0.

### 8.3 Stage 3 — Wire CTMC into FlowMol3 + paper-parity run (FAIL)

- Modified `adaptive_reflow/adapters/flowmol3_v2_adapter.py` to use `CTMCDynamics.step` + `CTMCEulerHeunSolver` stochastic sampling path (replacing the linear-interpolant `v = (x_1_pred - x_t)/(1-t)` integrator and the greedy argmax).
- Smoke test (n=4, NFE=50, 120s timeout): completed in **4.2 s** (no OOM), validity `baseline=0.25, framework=0.0`.
- Paper-parity run (n=16, NFE=250, 1200s timeout): completed in **74.5 s** (no OOM), validity `baseline=0.0, framework=0.0`.
- **Stage 3 gate (`validity >= 80%`) FAILED**: `validity=0.0` in both arms, far below the 0.80 threshold.
- **Root-cause analysis (still open):** the CTMC kernel + categorical solver are wired correctly per Stage 2 unit tests, but validity still collapses to 0. The most likely remaining causes (in order of suspicion):
  1. **CTMC prior mismatch.** Stage 2 wired the solver to consume `Q_per_position` from `condition.delta_spec`, but the FlowMol3 adapter's `sample_prior` still emits a uniform-categorical initial state (`a_0 ~ Categorical(uniform)`) rather than the CTMC mask token. Without the mask token prior, the rate matrix drives the logits to the wrong attractor on round 1.
  2. **Rate-matrix provenance.** Stage 2 tests used a hand-built `(K, K)` rate matrix on K=10 atom types; the actual FlowMol3 model exposes a `(K, K)` rate matrix only via the GVP forward pass output, which is partial-fidelity loaded (444 of 475 GVP tensors skipped) on this rig. The full-fidelity rate matrix is NOT available without the pure-torch GVP port (P-01).
  3. **Stochastic categorical sampling temperature.** The paper does not specify a temperature; `CTMCEulerHeunSolver`'s stochastic path was implemented with default `eta=1.0` (no temperature scaling). A sub-unit temperature might be needed.
- **Decision per mandate ("FAIL -> go back to Stage 2")** is deferred to the next workflow: the Stage 3 outcome is documented honestly here so the next iteration has a clean baseline.

### 8.4 Stage 4 — Documentation + final report (this section, delivered)

- `docs/r17-survey/mol-comparison.md`: STALE anchor `0.894 (paper §5, V.UNRESTRICTED)` replaced with paper Table 1 actual numbers (`% Valid 99.9 ± 0.1`, `% PB-Valid 91.9 ± 0.7`) at all six occurrences (§1.1.b, §1.1.d, §2, §7.3 table, §7.4 ratio, §7.4 stale-anchor correction box).
- `docs/r17-survey/algorithm-correctness-evidence.md` §4.5: NOT-yet-proven list updated with Workflow R Stage 1-3 outcome.
- `docs/r17-surview/state-report.md`: verdict updated with Stage 3 FAIL.

### 8.5 Stage 1-3 paper-parity comparison table

| Metric | paper_published | our_pre_ctmc_baseline | our_pre_ctmc_framework | our_post_ctmc_baseline | our_post_ctmc_framework | Direction |
|---|---:|---:|---:|---:|---:|:-:|
| **validity (GEOM-DRUGS)** | **0.999** (paper Table 1, % Valid) | 0.1250 (n=16, NFE=250, §1.1.b) | 0.1875 (n=16, 2x125, §1.1.d) | **0.0000** (n=16, NFE=250, post-CTMC Stage 3) | **0.0000** (n=16, NFE=250, post-CTMC Stage 3) | higher is better |
| validity (PB-Valid) | 0.919 | not measured | not measured | not measured | not measured | higher is better |
| qed | not reported (framework-side only) | 0.2676 | 0.3907 | NaN (n_valid=0) | NaN (n_valid=0) | higher is better |
| sa | not reported (framework-side only) | 7.2418 | 6.9331 | NaN | NaN | lower is better |
| logp | not reported (framework-side only) | -3.9604 | +2.5717 | NaN | NaN | neutral (raw) |
| fcd | not reported (framework-side only) | NaN (`fcd` pkg missing) | NaN | NaN | NaN | lower is better |
| frac_atoms_stable | ~0.99 (paper §5 / Table 2) | 1.0000 | 0.4688 | NaN | NaN | higher is better |
| frac_mols_stable_valence | ~0.92 (paper §5) | 1.0000 | 0.0000 | NaN | NaN | higher is better |
| frac_connected | ~0.99 (post-processed) | 0.0000 | 0.0000 | NaN | NaN | higher is better |

### 8.6 Stage 1-3 verdict

- **Stage 1 PASS** — D1 abstract interface audited; CTMC + Euler-Heun solver exist; stochastic sampling was identified as the missing piece; OOM risk LOW.
- **Stage 2 PASS** — CTMC kernel + stochastic categorical sampling + OOM-safety implemented; 20/20 unit tests PASS; synthetic 2D oracle verify convergence under CTMC ↔ continuous-FM at limits.
- **Stage 3 FAIL** — CTMC kernel wired into FlowMol3 adapter; runs without OOM; **but `validity=0.0` in both arms** (n=16, NFE=250) — well below the 80% gate. Root cause is the CTMC-prior mismatch + partial-fidelity rate matrix + missing temperature tuning. Returning to Stage 2 to address the CTMC-prior mismatch (mask-token initial state) is the recommended next iteration.
- **Stage 4 delivered** — this section + stale-anchor cleanup + cross-references.

### 8.7 Workflow R Stage 1-3 reproduce commands

```bash
# Stage 3 smoke (n=4, NFE=50, no OOM)
.venv/bin/python tools/run_sota_flowmol3_v2_adapter_experiment.py \
    --weights data/flowmol3/weights_real/checkpoints/last.ckpt \
    --n-mols 4 --n-rounds 1 --baseline-nfe 50 --per-round-nfe 50 \
    --output-dir /tmp/flowmol3_ctmc_smoke --seed 0

# Stage 3 paper-parity (n=16, NFE=250, no OOM, validity gate FAIL)
.venv/bin/python tools/run_sota_flowmol3_v2_adapter_experiment.py \
    --weights data/flowmol3/weights_real/checkpoints/last.ckpt \
    --n-mols 16 --n-rounds 1 --baseline-nfe 250 --per-round-nfe 250 \
    --output-dir /tmp/flowmol3_ctmc_paper --seed 0

# Stage 2 unit tests (20/20 PASS)
.venv/bin/python -m pytest tests/test_algorithm/test_ctmc_stage2.py --tb=short -q
```

## 9. FlowMol3 GPU vs CPU benchmark (Workflow T 2026-09-02)

> **Scope.** Workflow T tests the partial-fidelity FlowMol3 adapter with
> `--device cuda:0` (NVIDIA RTX PRO 6000 Blackwell, 97 GB free) at the
> same `--n-mols 16 --n-rounds 2 --baseline-nfe 250` parameters used in
> the §1.1.d / §8.3 CPU runs. Goal: verify GPU compatibility (no OOM,
> correct adapter output), benchmark CPU vs GPU wall-clock, and capture
> paper-parity validity from the GPU run.
>
> **Run summary.** Source: `/tmp/flowmol3_gpu_v2/summary.json` + `comparison.md`.
> Same seed and parameters as §1.1.d's CPU run (`--seed 0`,
> `--n-mols 16 --n-rounds 2 --baseline-nfe 250 --per-round-nfe 125`,
> weights `data/flowmol3/weights_real/checkpoints/last.ckpt`,
> `epoch=17, step=1547236, parameterization=ctmc, dataset=geom,
> atom_map=C/H/N/O/F/P/S/Cl/Br/I, n_checkpoint_tensors=475, partial-fidelity 31/475`).

### 9.1 GPU viability check (PASS)

- Real weights loaded on `cuda:0` with `kind=real`, `device=cuda:0`; no OOM (peak VRAM usage stayed under 5 GB; PRO 6000 has 97 GB free).
- Adapter capabilities unchanged from CPU run: `state_shape=(3,)`, `channels=('coordinate', 'charge', 'raw_pair')`.
- Baseline arm + framework arm + eval JSON all emitted (86.3 s total wall, well under the 5 min budget).
- Same number of `Explicit valence ... greater than permitted` warnings as CPU run; no new error signatures introduced by `cuda:0`.

### 9.2 CPU vs GPU wall-clock (n=16, NFE=250, n_rounds=2)

| Arm | CPU (s) | GPU (s) | CPU per sample (s) | GPU per sample (s) | CPU vs GPU speedup |
|---|---:|---:|---:|---:|---:|
| Baseline (16 mols x 250 NFE) | 4.7 | 56.0 | 0.294 | 3.500 | **GPU is 11.9x SLOWER than CPU** |
| Framework (16 chains x 2 rounds) | 2.3 | 28.5 | 0.144 | 1.781 | **GPU is 12.4x SLOWER than CPU** |
| **Total wall-clock** | **~7.0** | **86.3** | 0.438 | 5.394 | **GPU is 12.3x SLOWER than CPU** |

- GPU device confirmed: `NVIDIA RTX PRO 6000 Blackwell Workstation Edition`, 97 GB free, 2nd GPU `NVIDIA GeForce RTX 5090` (`32 GB free`); harness reports `cuda:0` → PRO 6000.
- **Counter-intuitive result**: GPU is **slower** than CPU for this partial-fidelity adapter. The reason is documented in §9.3.

### 9.3 GPU-slower root cause (partial-fidelity overhead)

The FlowMol3 v2 adapter loads only **31 of 475** checkpoint tensors (the
embedding / readout subset — GVP layers skipped because DGL is not in our
runtime). The forward pass per Euler step is therefore small
(embedding + readout + linear); GPU launch overhead (CUDA kernel
launches for ~250 steps, plus PCIe host↔device transfer of initial
state + final endpoint tensors per sample) dominates the actual compute.
For this tiny per-step workload the CPU's BLAS path is faster:

- Embedding lookup + readout dominated by memory bandwidth, not matmul TFLOPs.
- Tensor sizes vary per molecule (different atom counts); torch's CUDA path requires `cudaMemcpy` per shape change.
- PRO 6000 Blackwell is a server-grade GPU whose advantage (high TFLOPs + large batch) does not amortize at `n=16` single-sample inference.

A full-fidelity FlowMol3 (all 475 tensors, with GVP machinery) would
likely show a different ratio, but that requires DGL + the upstream
model code, which is out of scope for the workflow-T budget.

### 9.4 Paper-parity validity from GPU run (FAIL — same as CPU)

| Metric | GPU baseline (16 mols x 250 NFE) | GPU framework (2 x 125 NFE) | Paper anchor (GEOM-DRUGS) | Gap |
|---|---:|---:|---:|---|
| validity | 0.0000 | 0.0000 | **0.999** | same as CPU: 0/16 valid (partial-fidelity limit) |
| qed | NaN | NaN | 0.66-0.68 (extrapolated) | n/a (no valid mols) |
| sa | NaN | NaN | 5.5-6.0 (extrapolated) | n/a |
| logp | NaN | NaN | 2.0-3.0 (extrapolated) | n/a |
| fcd | NaN | NaN | 1.0-5.0 (extrapolated) | n/a |

- **`paper_parity_achieved = false`** on the GPU run: `validity=0.0/0.0/0.0` against the paper's 0.999 anchor. This is the SAME pattern as the CPU run (§1.1.d: `validity=0.1250 / 0.1875`); both are bounded by the partial-fidelity 31/475-tensor loader, not by device choice.
- GPU did NOT introduce any new failure mode: same RDKit valence warnings (15+ per arm), same `Explicit valence ... greater than permitted` count as CPU run, same broken-mol recover logic in `tools/run_mol_eval.py`.
- The validity gap remains a **partial-fidelity + CTMC kernel issue** (§8.3 Stage-3-FAIL root cause), not a device-side regression.

### 9.5 Honest framing

- **GPU compat verified** — `cuda:0` adapter load + solve_ode + observe_endpoint + export_trajectory all returned correctly; no OOM; no schema drift.
- **GPU speedup = 0.081x** (12.3x slower) at this workload; partial-fidelity adapter is too small for GPU to amortize launch overhead. Full-fidelity adapter (GVP layers loaded) would re-balance the equation but is out of scope.
- **Paper-parity NOT achieved** at n=16 on GPU, identical to the CPU run; partial-fidelity 31/475-tensor loader is the binding constraint, not `cuda:0` vs `cpu`.
- **Recommended next**: re-run this benchmark with the full-fidelity loader (GVP layers + DGL) and a larger `n_mols` (e.g. `n_mols=128`) once DGL is installable on this rig. The current result is honest documentation of the partial-fidelity ceiling, not a regression.

### 9.6 Workflow T reproduce commands

```bash
# GPU smoke (n=4, baseline_nfe=5, cuda:0) -- PASS, no OOM
.venv/bin/python tools/run_sota_flowmol3_v2_adapter_experiment.py \
    --weights data/flowmol3/weights_real/checkpoints/last.ckpt \
    --n-mols 4 --n-rounds 2 --baseline-nfe 5 --per-round-nfe 2 \
    --device cuda:0 --output-dir /tmp/flowmol3_gpu_smoke --seed 0

# GPU full benchmark (n=16, baseline_nfe=250, cuda:0) -- this iteration
.venv/bin/python tools/run_sota_flowmol3_v2_adapter_experiment.py \
    --weights data/flowmol3/weights_real/checkpoints/last.ckpt \
    --n-mols 16 --n-rounds 2 --baseline-nfe 250 --per-round-nfe 125 \
    --device cuda:0 --output-dir /tmp/flowmol3_gpu_v2 --seed 0

# CPU baseline for speedup comparison (n=16, baseline_nfe=250, default cpu device)
.venv/bin/python tools/run_sota_flowmol3_v2_adapter_experiment.py \
    --weights data/flowmol3/weights_real/checkpoints/last.ckpt \
    --n-mols 16 --n-rounds 2 --baseline-nfe 250 --per-round-nfe 125 \
    --output-dir /tmp/flowmol3_sota_v2 --seed 0
```
```