# Zenodo Release Manifest for FlowA v1.0 Camera-Ready

## Release Contents

| Path | Purpose | Notes |
|---|---|---|
| `adaptive_reflow/` | Source code (framework core + adapters + experiments) | Python package |
| `tests/` | Test suite (D.4 72/72 byte-stable, acyclic, byte-stability regression) | CPU-only, `pytest` |
| `scripts/` | Experiment scripts (reproducibility entry points) | Shell + Python wrappers |
| `tools/` | 9-gate verifier + claim consistency checker + audit scripts | Reviewer-facing |
| `docs/` | Paper draft + audit docs + reproducibility records + manifests | Markdown |
| `data/` | Upstream LineageFlow + adapter-side data (cifar10_inception_features, mnist_fm_train_cache, lineageflow_n1000, etc.) | Excludes large FASTA DBs |
| `README.md` | Top-level README | Quickstart + citation |

## Tarball

- **Path**: `/tmp/w165/zenodo_release/flowa-v1.0-camera-ready.tar.gz`
- **Size**: 3222798336 bytes (≈ 3.00 GiB uncompressed)
- **SHA-256**: `9699cd42161ae80b81fb385f0577ee4a61f94e04cea392d6d0281af061c430d7`

## Build Command (for reproducibility)

```bash
cd /home/hugo/codes/flowa-multistep-reinference
tar --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='.ruff_cache' \
    --exclude='node_modules' \
    --exclude='verification_outputs/*/foldability/pdb/*' \
    --exclude='verification_outputs/*/novelty_mmseqs2/*' \
    --exclude='data/lineageflow_upstream/databases/pfam_canonical/Pfam-A.fasta*' \
    -czf /tmp/w165/zenodo_release/flowa-v1.0-camera-ready.tar.gz \
    adaptive_reflow/ tests/ scripts/ tools/ docs/ data/ README.md
```

## Excluded from Release (re-include via separate means)

| Path | Reason | Re-inclusion strategy |
|---|---|---|
| `data/lineageflow_upstream/databases/pfam_canonical/Pfam-A.fasta*` | 6.27 GB FASTA DB | Re-host as a separate Zenodo dataset record, cite as a dependency |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/pdb/*` | Regenerable PDB structures | Re-run k6 foldability sweep on upload to regenerate |
| `.git/` | Version-control history | Use Zenodo's GitHub integration to link the commit SHA |
| `data/lineageflow_upstream/databases/pfam_canonical/` | FASTA databases for novelty_mmseqs2 sweep | Re-host on Zenodo as a separate dataset |

## Verification Status (gates run before commit)

- **D.4 (byte-stability tests)**: PASS — 72/72 tests pass byte-stable (Wave 33 D.4 final)
- **Ruff lint**: 0 issues across `adaptive_reflow/`, `tests/`, `scripts/`, `tools/`
- **Claim consistency**: PASS — `tools/check_claims_consistency.py` clean

## Provenance

- Built on commit `fefa0e6` (Wave 164b: paper camera-ready review)
- Branch: `main`
- Built by: Wave 165 P3 (Zenodo DOI release preparation)

## How to Upload to Zenodo

See `docs/zenodo-release/upload-instructions.md` for the step-by-step upload procedure.
