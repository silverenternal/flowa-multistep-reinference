# Reproduction Guide

This document is the single-command reproduction recipe for every headline
number reported in the paper. A reviewer with the listed hardware can
re-derive the headline evidence from a clean checkout in five steps.

## Hardware requirements

| Component | Minimum | Recommended |
|---|---|---|
| GPU | NVIDIA RTX 5090 (32 GB VRAM) | RTX PRO 6000 Blackwell (98 GB VRAM) |
| VRAM | 24 GB | 32 GB+ |
| CPU | 8 cores / 16 threads | 16 cores / 32 threads |
| RAM | 64 GB | 128 GB |
| Disk (free) | 100 GB | 200 GB SSD |
| Network | outbound HTTPS (HF Hub, PyPI, EBI Pfam) | — |

The headline evidence spans four 2D synthetic benchmarks (CPU-only,
laptop-grade), one CIFAR-10 Rectified Flow cell (mid-range GPU), and two
molecular flow-matching cells (≥ 16 GB VRAM). The protein cell also
requires an HMMER + Pfam database install (≈ 30 GB additional disk).

## Software requirements

| Component | Version | Notes |
|---|---|---|
| Python (primary) | 3.11+ | matches `.venvs/flowmol3_venv/` (Python 3.12.13) |
| Python (LineageFlow) | 3.10+ | required by the protein adapter + HMMER stack |
| CUDA | 13.0+ | driver ≥ 580; matches torch 2.7.0+cu128 |
| PyTorch | 2.5+ | canonical lock at torch 2.7.0+cu128 |
| dgl | 2.4.0+ | required by the molecular message-passing adapters |
| Git | 2.30+ | for the clone + submodule step |
| HMMER | 3.4+ | only for the protein cell (`hmmscan` on PATH) |
| MMseqs2 | 14+ | only for the protein cell |

The canonical pinned dependency set is in `requirements-lock.txt`
(torch 2.7.0+cu128, dgl 2.4.0+cu124). The Dockerfile in the repo root
builds the full release container in one command.

## Step 1 — Clone and setup

```bash
git clone https://github.com/silverenternal/flowa-multistep-reinference.git
cd flowa-multistep-reinference

python3.11 -m venv .venvs/review
source .venvs/review/bin/activate
python -m pip install -U pip wheel
```

The clone carries the framework source, the paper draft, and the
pre-aggregated headline-evidence CSVs/JSONs under `verification_outputs/`.
No submodules are required.

## Step 2 — Install dependencies

```bash
pip install -r requirements-lock.txt
```

The lockfile pins every transitive dependency used to produce the headline
numbers (torch 2.7.0+cu128, dgl 2.4.0+cu124, biopython 1.88,
torchvision 0.22.0+cu128, torchmetrics 1.9.0, rdkit 2026.03.5). For the
protein cell only, additionally install HMMER + Pfam:

```bash
conda install -c bioconda hmmer
# Plus a Pfam-A.hmm download from EBI (https://www.ebi.ac.uk/interpro/download/pfam/)
```

## Step 3 — Verify all gates

```bash
python3 tools/verify_submission_readiness.py
```

The expected final line is one of:

```
READY: all gates passed
```

or, if `mypy` is not on PATH (sandbox-only condition):

```
READY_WITH_SKIPS: mypy_0
```

The verifier runs nine reviewer-facing acceptance gates in sequence:
the byte-stable D.4 regression suite (30 tests), ruff, mypy,
claims-consistency drift check, paper.pdf warning budget, the 12 R1-R6
JSON/CSV sha256 anchor files, the K1 RC5 wording check, the audit-trail
drift check, and the two framework N=1000 sweep JSONs.

## Step 4 — Run all R-level cells

```bash
bash scripts/reproduce_r1_to_r6.sh
```

By default the script **prints the per-cell CLI plan** and exits — the
individual Python invocations inside the file are commented out for safety.
To actually re-run a cell, open `scripts/reproduce_r1_to_r6.sh` and
uncomment the section for the cell you want to re-execute. The script
supports per-cell skipping via `SKIP_Rn=1` environment variables and a
`--help` flag.

Cumulative wallclock on a single machine:

| Cell | Hardware | Wallclock |
|---|---|---|
| R4 + R5 (2D synthetic) | CPU only | ≈ 1 hour total |
| R3 + R6 (image FID math) | 1× GPU | 1–2 hours total |
| R2 (molecular flow) | 1× GPU | 3–4 hours |
| R1 (protein HMMER) | CPU + HMMER | 30–50 hours |
| **All six cells** | 1 host | **≈ 36–56 hours** |

## Step 5 — Confirm headline numbers

After each cell completes, the headline numbers are written to
`verification_outputs/` as JSON or CSV files. Confirm them with a
single grep pass:

```bash
# R1 — LineageFlow HMMER total hits (N=1000)
grep -E 'hmmscan_total_hits' verification_outputs/lineageflow_n1000_*_q4_2026.json

# R2 — FlowMol3 fg_dev (N=1000)
grep -E '"fg_dev"' verification_outputs/flowmol3_n1000_*_q4_2026.json

# R3 — CIFAR-10 Rectified Flow FID (N=250)
grep -E '"fid"|"delta_fid_pct"' verification_outputs/baseline_comparison_q4_2026.json

# R4 — 2D Two Moons Wasserstein-2 (matched NFE 500)
grep -E 'target,w2' verification_outputs/noise_injection_two_moons_*.csv
awk -F, 'NR>1 && $2==0.0 {w2[$4","$5]+=$7; n[$4","$5]++} END {for (k in w2) print k, w2[k]/n[k]}' \
    verification_outputs/noise_injection_two_moons_baseline.csv

# R5 — 2D Eight Gaussians Wasserstein-2 (matched NFE 500)
awk -F, 'NR>1 && $2==0.0 {w2[$4","$5]+=$7; n[$4","$5]++} END {for (k in w2) print k, w2[k]/n[k]}' \
    verification_outputs/noise_injection_eight_gaussians_baseline.csv

# R5b — CIFAR-10 Rectified Flow n_rounds=1 (3 seeds)
grep -E '"verdict"|"delta_fid_pct"' verification_outputs/wave247-p2-r5b-multiseed.json

# R6 — MNIST FM FID (N=1000)
grep -E '"fid"' verification_outputs/mnist_fm_*_fid_report.json
```

## Expected output

After a successful full reproduction, the headline numbers should match
the following within the documented precision:

| Cell | Metric | Baseline | Framework | Δ | Tolerance |
|---|---|---:|---:|---:|---|
| R1 | `hmmscan_total_hits` | 158 | 342 | +184 (+116.46%) | exact (byte-stable) |
| R2 | `fg_dev` | 0.6381 | 0.6146 | -0.0235 (4.05σ) | exact (byte-stable) |
| R3 | FID | 218.87 | 122.18 | -96.69 (-44.17%) | ±0.5 (InceptionV3 noise) |
| R4 | `w2` | 0.5029 | 0.4663 | -0.0366 (-7.28%) | ±0.005 (3-seed mean) |
| R5 | `w2` | 0.6606 | 0.5919 | -0.0687 (-10.40%) | ±0.005 (3-seed mean) |
| R5b | FID (n_rounds=1) | per-seed | framework-WINS | d_z +4.37 to +4.73 | d_z > 0 across all 3 seeds |
| R6 | FID | 409.18 | 347.75 | -61.43 (-15.01%) | ±1.0 (InceptionV3 noise) |

All headline numbers are within the per-cell σ-band documented in the
paper's §7.6 verdict table. The R1 + R2 + R5b rows are byte-stable across
re-runs (exact match within Δ < 1e-9); R3 / R4 / R5 / R6 carry small
InceptionV3 / Wasserstein-2 sample-noise bands.

## Troubleshooting

If any step above fails:

| Failing step | First check |
|---|---|
| Step 2 (pip install) | `python -V` matches Python 3.11+; CUDA driver ≥ 580 |
| Step 3 (gate verifier) | `docs/audit/` for the matching gate name |
| Step 4 (reproduce script) | `bash scripts/reproduce_r1_to_r6.sh --help` |
| Step 5 (headline grep) | `docs/headline-evidence/<R-cell>/SOURCE.md` for the per-cell provenance |

The audit directory under `docs/audit/` is the per-step audit trail: every
gate verifier, every R-cell sweep, and every reproducibility record has a
matching audit document that records the command, the observed output,
and the expected output. Search there for the failing step's keyword.

The release container (Dockerfile at the repo root) builds the canonical
reproduce environment in one command and is the recommended starting
point if any host-installation step fails:

```bash
docker build -t flowa:tpami-v3.0 .
docker run --gpus '"device=0"' -it --rm \
    -v /home/hugo/codes/flowa-multistep-reinference:/workspace/flowa \
    flowa:tpami-v3.0 --help
```
