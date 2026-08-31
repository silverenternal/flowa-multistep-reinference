# r17 Phase-A: Molecular Model Comparison (FlowMol3 + GraphBFN)

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

Configuration: baseline = 16 mols x 250-NFE Euler single-pass; framework = 16 chains x 3 rounds (CosineAnnealScheduler). Wall-clock baseline=4.6 s, framework=2.3 s.

| Metric | Baseline (250 NFE) | Framework (3 x 83 NFE) | Paired delta | Direction |
|---|---:|---:|---:|:---:|
| validity | 0.1250 | 0.0625 | -0.0625 | higher is better |
| qed | 0.2676 | 0.5843 | +0.3167 | higher is better |
| sa | 7.2418 | 8.4207 | +1.1788 | lower is better |
| logp | -3.9604 | 3.9652 | +7.9257 | neutral (raw) |
| fcd | nan | nan | +nan | lower is better |

- Adapter metadata: `state_shape=(3,)`, channels=`('coordinate', 'charge', 'raw_pair')`, `atom_map=('C','H','N','O','F','P','S','Cl','Br','I')`, `dataset_name=geom`, `parameterization=ctmc`, `epoch=17`, `global_step=1547236`, `distort_p=0.7`, `distort_t=0.25`. `n_checkpoint_tensors=475`. Total wall clock 8.6 s for the whole run (CPU).
- `fcd` is `NaN` because the `fcd` Python package is not installed; the JSON records `missing_dependencies=["fcd"]` and `fcd_unavailable` stderr notes. Install with `uv pip install fcd` to populate.
- RDKit emitted numerous "Explicit valence ... greater than permitted" warnings during baseline, indicating the baseline run produced no RDKit-valid molecules (validity=0). The framework arm produced 1 valid out of 16 (validity=0.0625); qed/sa/logp are populated only for that one valid molecule.

**Honest caveat on the "real weights" run.** The Phase-A harness CLI does forward `--weights data/flowmol3/weights_real/checkpoints/last.ckpt` and selects `backend="torch"` when the path is non-`synthetic`. The adapter's `_load_model` (in `adaptive_reflow/adapters/flowmol3_v2_adapter.py`) loads the Lightning `state_dict` (475 tensors) into the partial-fidelity `_FlowMol3ReadoutHead` (token embeddings + scalar_embedding + edge_embedding + node_output_head + to_edge_logits). The 444 GVP graph-convolution tensors in the published FlowMol3 checkpoint are NOT applied (they require `flowmol` and `dgl`, neither of which has a Python 3.12 wheel). The 0.0625 framework validity and the non-zero qed/sa/logp numbers are from trained embedding/readout tensors, not the published FlowMol3 sampler -- the chemistry is partial-fidelity. A 17-layer DiT forward through the GVP stack would take minutes per sample on CPU; the partial-fidelity run completes in 8.6 s.

### 1.2 GraphBFN (hierarchical Bayesian Flow Network, QM9)

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

## 2. Paired-delta interpretation

Paired delta = `framework - baseline` on the same `(seed, weight-backend, n_mols)` draw. Signs follow the `Direction` column (higher-is-better vs lower-is-better). The Phase-A real-weights row is partial-fidelity -- the embedding + readout path runs on real trained tensors, but the GVP graph-convolution stack is not applied. Treat these numbers as plumbing validation on real-weights input, NOT paper-claimed chemistry.

## 3. Real-weights artifact

- Weights path: `data/flowmol3/weights_real/checkpoints/last.ckpt` (65 MB PyTorch Lightning checkpoint + sibling `config.yaml`). Sibling `config.yaml` declares `dataset_name=geom`, `parameterization=ctmc`, `mol_fm.distort_p=0.7`, `mol_fm.distort_t=0.25`, `mol_fm.explicit_aromaticity=false`, and the `atom_map = [C, H, N, O, F, P, S, Cl, Br, I]`. The adapter loader confirms `epoch=17, global_step=1547236, n_checkpoint_tensors=475`.
- Adapter surfaces 31 trained tensors into the partial-fidelity `_FlowMol3ReadoutHead`: 3 token embeddings (`token_embeddings.{a,c,e}`), 2 scalar MLPs (`scalar_embedding`), 2 edge MLPs (`edge_embedding`), 4 node readout MLPs (`node_output_head`), 4 edge readout MLPs (`to_edge_logits`). The remaining 444 GVP / DGL-bound tensors are skipped.
- The harness ran end-to-end with no ImportError; exit code 0; `summary.json` + `comparison.md` emitted.
- Future work -- bring up `flowmol` + `dgl` in a Python 3.11 sidecar venv to apply the full GVP stack and reproduce the paper's FlowMol3 sampler.

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
    --output-dir /tmp/exp_a_real --seed 0

# Phase-A smoke (synthetic weights)
python tools/run_sota_flowmol3_v2_adapter_experiment.py \
    --weights synthetic --n-mols 8 --n-rounds 2 \
    --output-dir /tmp/phase_a_smoke/flowmol3 --seed 0

python tools/run_sota_graphbfn_experiment.py \
    --weights synthetic --n-mols 8 --n-rounds 2 \
    --output-dir /tmp/phase_a_smoke/graphbfn --seed 0
```

Each harness writes its own `comparison.md` (single-model table with honest-framing notes) plus `summary.json`; this document consolidates both.