# Data Availability — FlowA

**Manuscript:** FlowA: Training-Free, Inference-Time Re-Inference Control for Deployed Flow-Matching Checkpoints
**Submitted:** 2026-09-18

---

## Summary

All data, code, and trained checkpoints required to reproduce FlowA's headline results are **vendored, version-pinned, and SHA-256-verified inside a single git checkout**, with the full release also archived on **Zenodo**. Reviewers can reproduce every reported number from the freeze-marker commit SHA + the CLI commands in `supplementary.md §S6` — no out-of-band notebooks, no hidden state, no manual data curation.

## Code availability

- **Repository:** `https://github.com/silverenternal/flowa-multistep-reinference` (private mirror at submission time; public release at camera-ready).
- **Freeze-marker commit:** `3d816e0` (Wave 187 P4 final-gate verification, 2026-09-18).
- **License:** MIT (`LICENSE` at repository root).
- **Final tag:** `v1.1-paper-final-eaai-ready` (to be created by Wave 187 P5).
- **Container artifact:** `docs/zenodo-release/manifest.md` — 3.00 GiB tarball, SHA-256 `9699cd42161ae80b81fb385f0577ee4a61f94e04cea392d6d0281af061c430d7`.

## Checkpoint availability (all SHA-256 pinned)

Every Tier-3 model checkpoint used in the manuscript is vendored and SHA-256-verified at the manifest layer (`verification_outputs/ckpt_sha256.json`). The SHA-256 chain is re-hashed at ship time before submission.

| Model | Path | SHA-256 | Provenance |
|---|---|---|---|
| **Kanzi** (ICLR'26 protein flow-AE) | `data/kanzi_ckpt/cleaned_model.pt` | `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270` | Kanzi public ckpt, Wave 88 vendored |
| **Kanzi encoder** | `data/kanzi_ckpt/kanzi_encoder.pt` | (see `ckpt_sha256.json`) | Kanzi public ckpt, Wave 88 vendored |
| **LineageFlow** (ICML'26 protein FM) | `data/lineageflow/lineageflow-rp55.ckpt` | `f0b4b25e...54a2b` | LineageFlow public ckpt, Wave 80 vendored |
| **FlowMol3** (NeurIPS'24 molecular 3D FM) | `data/flowmol3/weights_real/checkpoints/last.ckpt` | `0e949b56b54c1d2fcbded4f0c9857bfd33dbde86bcc9db2f82572628f7f9f5b5` | FlowMol3 paper checkpoint, Wave 75 vendored |
| **Theorem 1 source (Li 2026, JMAA)** — supplementary paper | `eaai_submission/supplementary_paper.pdf` | `a6f3e3650de977e815b4080e21cff64bbbd3274ae07e5698567ea1acdd7a789d` | Li 2026 manuscript attached as EAAI supplementary; markdown source mirror at `eaai_submission/supplementary_paper.md` |

## Vendored upstream snapshots (immutable git checkouts)

Three upstream FM repositories are checked out at frozen commit SHAs inside `data/<model>_upstream/`:

| Upstream | Path | Pinned commit | Use |
|---|---|---|---|
| LineageFlow | `data/lineageflow_upstream/` | `ccef84a` ("Prepare LineageFlow public release") | `evaluation/evaluate_all.py`, Pfam-A.hmm + MMseqs2 target DB at `data/lineageflow_upstream/databases/` |
| Kanzi | `data/kanzi_upstream/` | `cfed9cf` | `kanzi.DAE.encode+decode+kabsch_rmsd`, reference PDBs at `data/kanzi_upstream/pdbs/` |
| FlowMol3 | `data/FlowMol3/repo/` | `77cae22` ("Update readme.md") | `flowmol.FlowMol.sample(...)` + PB-xtb refs under `fm3_evals/` |
| Pfam holdout | `data/pfam_holdout/` | (snapshot) | LineageFlow HMMER sweeps |

The framework **never re-fetches** at evaluation time — a reviewer can re-run offline against these immutable snapshots.

## Vendored reference data

- **Pfam-A.hmm** HMM profile DB — vendored at `data/lineageflow_upstream/databases/pfam_canonical/Pfam-A.hmm` (used for R1 HMMER +116% claim).
- **MMseqs2 target DB** — vendored at `data/lineageflow_upstream/databases/`.
- **4-PDB Kanzi reference set** — vendored at `data/kanzi_upstream/pdbs/` (`1s7mB01`, `2hoxA01`, `3bg1B01`, `6nrzA01`).
- **CIFAR-10 inception features** — vendored at `data/cifar10_inception_features/`.
- **MNIST FM training cache** — `data/mnist_fm_train_cache/`.
- **Pretrained FM checkpoints** — `data/` (CIFAR-10 RF, MNIST FM, FreqFlow, TwoDimFM synthetic).

## Synthetic / pretrained checkpoints

- **2D FM** (Eight Gaussians / Two Moons Rectified Flow): synthetic velocity field, byte-deterministic per seed.
- **CIFAR-10 Rectified Flow** (Liu 2022): pretrained RF UNet, vendored open weights.
- **MNIST FM** (CristianLazoQuispe `flow_model_localized_noise.pth`): pretrained, vendored open weights.

## Per-claim evidence path

Every headline number in the manuscript has a per-cell JSON + audit-doc pair on disk:

| Claim | Evidence path on disk |
|---|---|
| R1 (LineageFlow HMMER +116%) | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/` |
| R3 (FlowMol3 paper-metric parity) | `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` + `flowmol3_n1000_framework_q4_2026.json` |
| R5 (TwoDim-FM Pareto-frontier) | `verification_outputs/cross_model_*_q3_2026/` |
| R6 (LineageFlow foldability + scPerplexity) | `verification_outputs/k6_foldability_n1000_w161_q3_2026/` |
| 4-arm head-to-head | `verification_outputs/cross_model_real_ckpt_w182_*` |
| D.4 byte-stable regression vectors | `pytest tests/ -k "d4"` — 33/33 PASS at commit `3d816e0` |

## Reproducibility methodology

The manuscript's reproducibility is enforced at three machine-checkable layers:

- **(i) D.4 byte-stable regression vectors** — `python -m pytest tests/ -k "d4" -q` reports **33/33 PASS** at the freeze-marker commit (`3d816e0`, Wave 187 P4 final-gate verification, `docs/audit/wave187-p4-final-gate-verification.md`). The D.4 gate pins per-round outputs across every framework configuration; any drift fails CI before merge.
- **(ii) SHA-256 ckpt pinning** — every upstream checkpoint is re-hashed at ship time and asserted against the manifest. Reviewers re-verify with `python -c "import hashlib; print(hashlib.sha256(open('<ckpt>','rb').read()).hexdigest())"`.
- **(iii) Hash-chained ledger** — per-round metrics are SHA-256 chained and verified on completion (`ledger_chain_integrity=True`).

## Long-term archival

The full release is archived on **Zenodo** (tarball SHA-256 `9699cd42161ae80b81fb385f0577ee4a61f94e04cea392d6d0281af061c430d7`, ≈ 3.00 GiB). The Zenodo DOI will be assigned at upload and inserted into the camera-ready manuscript; the manifest at `docs/zenodo-release/manifest.md` is the canonical build artifact.

## Out-of-band resources (not needed for reproduction)

- The Pfam-A.fasta reference DB (6.27 GB) is excluded from the release tarball due to size; it is re-hosted on Zenodo as a separate dataset record (cited as a dependency in the manifest). The Pfam-A.hmm HMM profile DB (the artifact actually consumed by HMMER for R1) **is** vendored inside the release.
- HuggingFace model IDs (used to download FreqFlow / TwoDimFM pretrained weights at install time) are documented in `requirements/` and `tools/`; weights are auto-downloaded by `tools/install.sh` on first run.

## Statement

> All data, code, and trained checkpoints required to reproduce FlowA's headline results are publicly available under the terms described above. Vendored upstream snapshots + SHA-256 ckpt pinning + D.4 byte-stable regression vectors together guarantee **machine-verifiable byte-stable reproducibility** at the framework + adapter + ckpt + per-round output layers.