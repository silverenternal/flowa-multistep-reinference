# r17 Phase-A: Molecular Model Comparison (FlowMol3 + GraphBFN)

Phase-A end-to-end smoke comparison between the FlowMol3 (3D flow-matching) and GraphBFN (Bayesian Flow Network, hierarchical) adapters, each run in two modes:

- **Baseline** -- single-pass generation, no re-inference scheduler.
- **Framework** -- FlowA re-inference scheduler wrapping the same adapter (`CosineAnnealScheduler` for FlowMol3, cosine scheduler + real restart blend for GraphBFN).

Both runs use the `--weights synthetic` adapter backend and `--n-mols 8 --n-rounds 2 --seed 0`. Outputs live under `/tmp/phase_a_smoke/{flowmol3,graphbfn}/`. JSON summaries are `summary.json`; per-arm pkl metrics are `baseline_molecules.pkl` / `framework_molecules.pkl`.

## 1. Metrics table (paired baseline vs framework, per model)

All numbers are produced by the Phase-A smoke harness with **synthetic weights**; see §3 for why the chemistry-side metrics are not yet paper-comparable.

### 1.1 FlowMol3 (3D small-molecule flow matching, GEOM-DRUGS)

| Metric | Baseline (250 NFE) | Framework (2 x 125 NFE) | Paired delta | Direction |
|---|---:|---:|---:|:---:|
| validity | 0.0000 | 0.0000 | +0.0000 | higher is better |
| qed | nan | nan | nan | higher is better |
| sa | nan | nan | nan | lower is better |
| logp | nan | nan | nan | neutral (raw) |
| fcd | nan | nan | nan | lower is better |

- Wall clock: baseline 0.2 s, framework 0.1 s (CPU; synthetic velocity field).
- `fcd` is `NaN` because the `fcd` Python package is not installed; the JSON records `missing_dependencies=["fcd"]` and `fcd_unavailable` stderr notes. Install with `uv pip install fcd` to populate.
- Adapter signature: `state_shape=(3,)`, channels=`('coordinate', 'charge', 'raw_pair')`.

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

Paired delta = `framework - baseline` on the same `(seed, weight-backend, n_mols)` draw. Signs follow the `Direction` column (higher-is-better vs lower-is-better). The Phase-A smoke deltas are NOT informative about real chemistry: both arms run the synthetic backend, so any divergence between baseline and framework reflects scheduler-side noise on synthetic output, not paper-claimed gains.

The harness is correct; the inputs are not yet the real weights. Re-run with `--weights <real-checkpoint>` (once those land; see §3) to populate this table with paper-comparable numbers.

## 3. Synthetic-smoke honest framing

> **Note -- synthetic weights.** Both `data/flowmol3/weights/` and `data/graphbfn/weights/` are empty of real checkpoints. FlowMol3 has only README/HTML scrape artifacts in `data/flowmol3/weights/` (no `.pt`/`.pth`/`ckpt` payload); GraphBFN has no published checkpoint available to us at all (the adapter's torch loader raises `NotImplementedError`). Both Phase-A runs therefore used the deterministic NumPy backends inside each adapter. The harness paths are validated end-to-end (adapter -> endpoint -> RDKit glue -> metrics JSON); the chemistry is not. This smoke run is a plumbing check, not a chemistry comparison.

Real-weight placeholder:

- FlowMol3: drop the Pitt/Koes checkpoint into `data/flowmol3/weights/`, then `python tools/run_sota_flowmol3_v2_adapter_experiment.py --weights <ckpt> --n-mols 1000 --n-rounds 4 --output-dir data/flowmol3/runs/real/ --seed 0`. Until that lands the chemistry-side cells (qed/sa/logp/fcd/validity) in §1.1 stay at zero/NaN.
- GraphBFN: no checkpoint URL confirmed at Phase-A time. The synthetic row in §1.2 will remain the only populated row until either (a) a checkpoint is obtained or (b) the torch loader is finished and a public checkpoint is located.

## 4. Pointer to paper-claimed numbers

Paper PDFs are downloaded locally (Phase A prerequisite complete):

- **FlowMol3**: `data/flowmol3/paper.pdf` (arXiv:2508.12629, Dunn & Koes, U. Pittsburgh, 26 pages). Table for paper-claimed validity / QED / SA / logP / FCD lives in the main text; pull values from §5 / Tables there when cross-referencing the §1.1 placeholder row.
- **GraphBFN**: `data/graphbfn/paper.pdf` (arXiv:2510.10211v1, Xiong et al.). Paper Table 1 reports validity / uniqueness / FCD / NSPDK MMD on QM9; only the first three are reachable in Phase A (NSPDK is Phase B).

When the real-weight runs land, populate a "paper-claimed vs framework-reproduced" column here using `data/<model>/paper.pdf` Table values as the reference. Until then, treat §1 as "pipeline works, chemistry pending".

## 5. Repro commands

```bash
# Phase-A smoke (synthetic weights)
python tools/run_sota_flowmol3_v2_adapter_experiment.py \
    --weights synthetic --n-mols 8 --n-rounds 2 \
    --output-dir /tmp/phase_a_smoke/flowmol3 --seed 0

python tools/run_sota_graphbfn_experiment.py \
    --weights synthetic --n-mols 8 --n-rounds 2 \
    --output-dir /tmp/phase_a_smoke/graphbfn --seed 0
```

Each harness writes its own `comparison.md` (single-model table with honest-framing notes) plus `summary.json`; this document consolidates both.
