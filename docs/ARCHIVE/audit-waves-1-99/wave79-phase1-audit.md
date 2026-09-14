# Wave 79 Phase 1 — Upstream Eval Pipeline Audit (LineageFlow + Kanzi)

**Date:** 2026-09-08
**Wave:** 79 (Agent 1, READ-ONLY)
**Scope:** Verify LineageFlow upstream `evaluate_all.py` pipeline readiness + clone
Kanzi upstream (`https://github.com/rdilip/kanzi`) + document per-model readiness
table for Wave 76/77 paper-metric reproduction.

---

## 1. LineageFlow upstream readiness

### 1.1 Vendor presence

LineageFlow is already vendored at
`/home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/`
(Wave 10 commit). It is a self-contained git checkout of the upstream repo
`https://github.com/Jinx-byebye/LineageFlow.git` (master, ICML 2026).

| Artefact                                  | Status                                  |
|-------------------------------------------|-----------------------------------------|
| `evaluation/evaluate_all.py`              | PRESENT (454 lines, full orchestrator)  |
| `evaluation/family_validity_hmmer.py`     | PRESENT (20 207 bytes)                  |
| `evaluation/foldability_omegafold.py`     | PRESENT (18 289 bytes)                  |
| `evaluation/self_consistency_esmif.py`    | PRESENT (14 728 bytes)                  |
| `evaluation/novelty_mmseqs2.py`           | PRESENT (32 879 bytes)                  |
| `evaluation/run_foldability.py`           | PRESENT (OmegaFold + ESM-IF sharder)    |
| `evaluation/sample_training_matched.py`   | PRESENT (matched natural baseline)      |
| `evaluation/family_distribution.py`       | PRESENT (sampling sanity check)         |
| `evaluation/README.md`                    | PRESENT (full per-metric docs)          |
| `config/generation.json`                  | PRESENT (rp55 default, NFE=150)         |
| `citation.bib`                            | PRESENT (`liang2026lineageflow`)        |
| `requirements.txt`                        | PRESENT (Python deps only)              |
| `scripts/setup_fold_eval_env.sh`          | PRESENT (OmegaFold+ESM-IF+MMseqs2 boot) |

**4/4 metric scripts are present.** The orchestrator `evaluate_all.py` is a
single CLI entry point that fans out into the 4 metric families; it accepts
`--metrics family_validity foldability self_consistency novelty` (or
`--metrics all`).

### 1.2 Upstream entry points (file:line)

| Metric               | Entry script                                            | Heavy deps                                | Output files (per `--outdir`)                                      |
|----------------------|---------------------------------------------------------|-------------------------------------------|--------------------------------------------------------------------|
| family_validity      | `evaluation/evaluate_all.py` → `family_validity_hmmer.py:1` | HMMER (`hmmscan`)                      | `family_validity.json`, `family_validity_per_seq.jsonl`           |
| foldability          | `evaluation/evaluate_all.py` → `run_foldability.py:1` → `foldability_omegafold.py:1` | OmegaFold binary                | `foldability/metrics.jsonl`, `foldability/metrics_summary.json`   |
| self_consistency     | `evaluation/evaluate_all.py` → `run_foldability.py:1` → `self_consistency_esmif.py:1` | ESM-IF (`fair-esm`) + OmegaFold PDB | `foldability/metrics.jsonl` (sc_perplexity column)        |
| novelty              | `evaluation/evaluate_all.py` → `novelty_mmseqs2.py:1`  | MMseqs2 binary                            | `novelty.json`, `novelty_per_seq.jsonl`                           |
| family_mixture       | `evaluation/family_distribution.py:1` (sampling sanity) | (none)                                    | `family_distribution.json`                                         |

**CLI:** `python evaluation/evaluate_all.py --fasta <fasta> --outdir <dir>
--hmmdb databases/pfam35/Pfam-A.hmm --target-db results/mmseqs/...
--metrics all` (Wave 76 protocol).

### 1.3 Heavy deps status (as of Wave 79 sandbox)

| Dep                     | Source        | Status                                       |
|-------------------------|---------------|----------------------------------------------|
| `hmmscan`               | HMMER package | **NOT INSTALLED** — no `hmmscan` binary in PATH nor in `.venvs/lineageflow_venv/bin/` |
| `mmseqs`                | MMseqs2       | **NOT INSTALLED** — no `mmseqs` binary in PATH |
| `omegafold`             | OmegaFold     | **NOT INSTALLED** — no `omegafold` binary in PATH |
| `fair_esm` (ESM-IF)     | PyPI          | **NOT INSTALLED** — `pip install fair-esm` fails (`ModuleNotFoundError`) |
| `biotite`               | PyPI          | **NOT INSTALLED** — not in `lineageflow_venv` site-packages |
| `biopython`             | PyPI          | INSTALLED (v1.88) in `lineageflow_venv`       |
| `torch`                 | PyPI          | INSTALLED (v2.7.0+cu128) in `lineageflow_venv` |
| `transformers`          | PyPI          | INSTALLED (v4.57.6) in `lineageflow_venv`     |
| `numpy` / `pandas`      | PyPI          | INSTALLED (via `torch` wheel)                 |

`lineageflow_venv` has torch + transformers + biopython, but is **missing
fair_esm + biotite** (requirements.txt asks for `fair-esm>=2.0.0` and
`biotite>=0.39`) and **missing all 3 heavy system binaries**
(`hmmscan`, `mmseqs`, `omegafold`).

### 1.4 Reference data (HMM DB + MMseqs2 target DB)

| Asset                                       | Status                                  |
|---------------------------------------------|-----------------------------------------|
| `databases/pfam35/Pfam-A.hmm` (HMMER DB)    | **NOT vendored** — path does not exist on disk |
| `dataset/pfam_fastas_clean/*.fasta`         | **NOT vendored** — only `dataset/pfam_dataset.py` is present |
| `dataset/pfam_pi_smooth_tau0.5_gap060_gt80_020.csv` | **NOT vendored**                |
| `dataset/pfam_priors_asr_mad/*.prior.json`  | **NOT vendored**                         |
| `results/mmseqs/pfam_train_gap060_gt80_020` (MMseqs2 db) | **NOT vendored**           |
| `checkpoints/lineageflow-rp55.ckpt`         | **NOT vendored** in upstream tree (.gitignored), but IS present at `data/lineageflow/lineageflow-rp55.ckpt` (10.5 GB, SHA-256 verified Wave 39) |

The upstream `evaluate_all.py` defaults assume all of these are on disk.
The README's Quick Start points at Hugging Face Hub for both the ckpt
(`hf download jinxbye/LineageFlow lineageflow-rp55.ckpt`) and the Pfam assets
(`hf download jinxbye/LineageFlow-assets --repo-type dataset`).

**Reference held-out subset (local):** `data/pfam_holdout/random_clan.fasta`
(100 547 bytes, 1 file, Wave 43 download via random Pfam clan) — this is the
ONLY Pfam reference we have on disk for offline use.

### 1.5 Smoke test

A `--max-seqs 1` smoke run is **NOT attempted in this Phase-1 audit** because:

1. The 3 heavy system binaries (`hmmscan`, `mmseqs`, `omegafold`) are not on PATH.
2. The HMM database and MMseqs2 target DB are not on disk.
3. `fair_esm` is missing from `lineageflow_venv`.

A real smoke test would need:
```bash
# Install deps
pip install fair-esm biotite
# Install HMMER / MMseqs2 / OmegaFold via conda or system pkg manager
# Download HMM DB + Pfam subset
# Then run:
python data/lineageflow_upstream/evaluation/evaluate_all.py \
  --fasta <smoke_fasta> \
  --hmmdb databases/pfam35/Pfam-A.hmm \
  --target-db results/mmseqs/pfam_train_gap060_gt80_020 \
  --metrics all \
  --max-seqs 1 \
  --threads 4
```

**`smoke_test`: BLOCKED on host-env install + dataset download.** Documented
as the Wave 76 R1 critical-path dependency.

### 1.6 Wallclock estimate (per sample, 1000-2000 samples)

- **family_validity** (HMMER `hmmscan`): ~1-2 s/seq at E=1e-3 on Pfam-A,
  32 threads → 30-60 s for 1000 seqs.
- **foldability** (OmegaFold): ~10-30 s/seq on a single 5090; with 4 GPUs
  parallel via `run_foldability.py` sharder → 2500-7500 s for 1000 seqs
  (≈ 40-120 min).
- **self_consistency** (ESM-IF perplexity): ~5-10 s/seq/PDB on 5090;
  with sharder → 1250-2500 s for 1000 seqs (≈ 20-40 min).
- **novelty** (MMseqs2): ~1 s/seq against prebuilt target DB on 32 threads
  → 1000-2000 s for 1000-2000 seqs (≈ 15-30 min).

**Aggregate wallclock estimate (full 4-metric pipeline, 1000 seqs, GPU box):
~80-200 min (~1.5-3.5 h), dominated by OmegaFold + ESM-IF.**

**Aggregate wallclock estimate (2000 seqs, GPU box): ~160-400 min (~3-7 h).**

---

## 2. Kanzi upstream clone

### 2.1 Clone verification

```
git clone --depth 1 https://github.com/rdilip/kanzi.git \
  /home/hugo/codes/flowa-multistep-reinference/data/kanzi_upstream/
```

- Result: **SUCCESS**
- Size: 6.0 MB on disk
- Remote: `https://github.com/rdilip/kanzi.git` (verified via
  `data/kanzi_upstream/.git/config`)
- Branch: `main` (HEAD)

### 2.2 Kanzi upstream structure

| Path                         | LOC  | Purpose                                     |
|------------------------------|------|---------------------------------------------|
| `src/kanzi/__init__.py`      | 11   | Public API (`DAE`, `DAEConfig`, `kabsch_rmsd`) |
| `src/kanzi/models.py`        | 1106 | DAE (encoder + DiT decoder + FSQ) + GPT prior |
| `src/kanzi/attention.py`     | 264  | TransformerStack / SelfAttention (sliding-window) |
| `src/kanzi/cfm.py`           | 204  | ConditionalFlowMatcher (uniform_beta)        |
| `src/kanzi/fsq.py`           | 196  | Finite Scalar Quantization                   |
| `src/kanzi/rotary.py`        | 68   | Rotary embeddings                            |
| `src/kanzi/utils.py`         | 77   | `kabsch_rmsd()` (numpy-only reconstruction metric) |
| `src/kanzi/train_cb.py`      | 417  | Training loop + codebook metric helpers      |
| `assets/figure1.png`         | bin  | Paper figure 1 (Kanzi schematic)             |
| `pdbs/{1s7mB01,2hoxA01,3bg1B01,6nrzA01}.pdb` | bin | 4 demo PDBs                          |
| `pyproject.toml`             | text | Python ≥ 3.10; deps: torch ≥ 2.8, biotite, einops, jax, jaxtyping, loguru, timm, torchdiffeq |
| `uv.lock`                    | text | uv-pinned dep graph                          |
| `README.md`                  | text | Quick-start + reconstruction snippet         |

### 2.3 Critical observation: NO `evaluation/` directory

**Kanzi upstream has NO `evaluation/` script directory.** Repo contents:

```
data/kanzi_upstream/
├── assets/         # paper figures only
├── pdbs/           # 4 demo PDBs
├── src/kanzi/      # model + flow + FSQ + GPT + train_cb
├── .git/           # (vendored)
├── .gitignore
├── .python-version
├── README.md
├── pyproject.toml
└── uv.lock
```

There is no `evaluation/`, no `eval.py`, no `eval_*.py` — Kanzi upstream
exposes only the **reconstruction** path (`encode` → `decode` →
`kabsch_rmsd`). The paper's headline metrics (reconstruction Kabsch RMSD on
AFDB-Foldseek held-out subset) must be reproduced by writing a wrapper
around `model.encode(x) → idx → model.decode(idx) → kabsch_rmsd(decode, x)`.

### 2.4 Paper metrics reported by Kanzi (from `train_cb.py:113-133` + README)

| Metric                        | Where reported           | Notes                                  |
|-------------------------------|--------------------------|----------------------------------------|
| Reconstruction Kabsch RMSD    | `kabsch_rmsd(P, Q)` in `utils.py:5` | Paper Table 1 headline           |
| Codebook entropy              | `codebook_metrics` in `train_cb.py:113` | Tokenizer sharpness         |
| Codebook perplexity           | `codebook_metrics` (entropy → 2^entropy) | Reported in training cb     |
| Codebook JS distance          | `codebook_metrics` (pairwise JS)       | Rot-invariance proxy         |
| Codebook utilization          | `estimate_loss` (`test/cb/utilization`) | Unique tokens / vocab     |
| Hamming (rotation invariance) | `estimate_loss` (`test/cb/hamming`)    | Encoded indices match under rotation |
| Flow loss                     | `test/flow_loss` (training-only)       | Not an eval metric              |
| GPT prior loss                | `test/gpt_prior_loss` (training-only)  | Not an eval metric              |

The **paper evaluation protocol** (per arXiv:2510.00351) is:

1. Take AFDB-Foldseek held-out cluster (~500-5000 PDBs, length < 256).
2. For each PDB: extract Cα coordinates, mean-center, divide by 10 (nm).
3. Run `model.encode(x) → idx` (shallow transformer encoder + FSQ).
4. Run `model.decode(idx) → x_recon` (DiT flow-matching decoder, NFE=100).
5. Compute `kabsch_rmsd(x_recon * 10, x * 10)` in Å.

**There is no FBD, no designability, no structural validity per se.** Kanzi
is a **tokenizer**, not a generator; it does not produce de novo proteins.
Wave 77 must author the `tools/kanzi_paper_metrics.py` wrapper from scratch.

### 2.5 Heavy deps status (Kanzi)

| Dep                     | Required | Status                                |
|-------------------------|----------|---------------------------------------|
| `torch>=2.8.0`          | Yes      | `kanzi_venv` has torch CPU installed (Wave 39) |
| `biotite>=1.2.0`        | Yes      | **NOT in kanzi_venv** (need `pip install biotite`) |
| `einops>=0.8.1`         | Yes      | Likely installed via torch; not verified |
| `jax>=0.6.2`            | Yes (jax path used?) | Not in kanzi_venv           |
| `jaxtyping>=0.3.2`      | Yes      | Not in kanzi_venv                     |
| `loguru>=0.7.3`         | Yes (logger) | Not in kanzi_venv                  |
| `timm>=1.0.20`          | Yes (Mlp) | Not in kanzi_venv                    |
| `torchdiffeq>=0.2.5`    | Yes (odeint) | Not in kanzi_venv                 |
| `scipy` (for Rotation)  | Yes (sample_uniform_rotation in models.py:29) | Not in kanzi_venv |
| `fastpdb` (for `PDBFile.read`) | Yes (per README quick-start) | Not in kanzi_venv       |

**Heavy deps for Kanzi are mostly pure-Python (torch + a few PyPI packages).**
No external system binaries (no `hmmscan`, no `mmseqs`, no `omegafold`).

### 2.6 Reference data (Kanzi)

Kanzi paper uses:
- **AFDB-Foldseek clustered dataset** — not vendored; `load_from_mmap` in
  `train_cb.py:44` expects `datasets/memmaps/afdb/positions.{split}.dat` +
  `meta.test.json`. Not on disk in our sandbox.
- **`pdbs/` (4 demo PDBs)** — vendored (1s7mB01, 2hoxA01, 3bg1B01, 6nrzA01).
  These are demonstration PDBs for the README quick-start only.

**For Wave 77 paper-metric reproduction we need:**
1. A held-out subset of AFDB-Foldseek (or Pfam-held-out subset already on disk
   in `data/pfam_holdout/random_clan.fasta`).
2. The Kanzi encoder/decoder ckpt at `data/kanzi_ckpt/cleaned_model.pt`
   (530 MB, SHA-256 verified Wave 36).
3. ~50-500 PDBs to run encode/decode/Kabsch on.

### 2.7 Wallclock estimate (per sample, 1000-2000 samples)

- **encode** (shallow transformer + FSQ, batch=1): ~50-200 ms/seq on a
  single 5090 → 50-400 s for 1000 seqs.
- **decode** (DiT flow-matching, NFE=100): ~5-15 s/seq on 5090 →
  5000-15000 s for 1000 seqs (~1.5-4 h).
- **kabsch_rmsd** (numpy-only, vectorisable): <10 ms/seq → negligible.

**Aggregate wallclock estimate (1000 PDBs, GPU box): ~5000-15500 s
(~1.5-4 h), dominated by DiT decoder.**

**Aggregate wallclock estimate (2000 PDBs, GPU box): ~10000-31000 s
(~3-9 h).**

---

## 3. Per-model readiness table

| Model        | Upstream ready | Deps vendored | Reference data | Smoke test | Wallclock 1000 seqs | Wave 76/77 readiness |
|--------------|---------------|---------------|----------------|-----------|---------------------|----------------------|
| LineageFlow  | YES (vendored, all 4 metric scripts present) | PARTIAL (torch + transformers + biopython in `lineageflow_venv`; MISSING `fair_esm`, `biotite`, `hmmscan`, `mmseqs`, `omegafold`) | MISSING (Pfam-A.hmm DB, MMseqs2 target DB, Pfam FASTA dataset not vendored) | BLOCKED on host-env install + dataset download | ~80-200 min (OmegaFold+ESM-IF dominate) | Wave 76 BLOCKED until HMMER/MMseqs2/OmegaFold installed + HMM DB + MMseqs2 target DB downloaded |
| Kanzi        | YES (cloned, model code only — NO `evaluation/` dir) | PARTIAL (torch CPU in `kanzi_venv`; MISSING `biotite`, `einops`, `jaxtyping`, `timm`, `torchdiffeq`, `scipy`, `fastpdb`, `loguru`) | PARTIAL (4 demo PDBs only; AFDB-Foldseek held-out subset MISSING) | **NOT APPLICABLE** (no upstream eval script; must author wrapper) | ~1.5-4 h (DiT decode dominates) | Wave 77 BLOCKED until (a) wrapper authored, (b) AFDB-Foldseek held-out subset downloaded |

---

## 4. Critical findings for Wave 76 / Wave 77

### 4.1 LineageFlow (Wave 76 R1 critical path)

1. **Install heavy deps on the GPU host before Wave 76 R2:**
   ```bash
   # HMMER (preferred: conda-forge)
   conda install -c bioconda hmmer
   # MMseqs2
   conda install -c bioconda mmseqs2
   # OmegaFold (clone + install per upstream README)
   git clone https://github.com/HeliXonProtein/OmegaFold.git /opt/OmegaFold
   # Then expose /opt/OmegaFold as `omegafold` on PATH
   # fair-esm + biotite
   pip install fair-esm biotite
   ```
2. **Download HMM DB + Pfam assets from Hugging Face Hub:**
   ```bash
   hf download jinxbye/LineageFlow-assets --repo-type dataset --local-dir dataset
   # This gives Pfam-A.hmm (via the assets release).
   # If Pfam-A.hmm is not in the HF assets, download from EBI Pfam FTP:
   wget -O databases/pfam35/Pfam-A.hmm.gz \
     ftp://ftp.ebi.ac.uk/pub/databases/Pfam/releases/Pfam35.0/Pfam-A.hmm.gz
   gunzip databases/pfam35/Pfam-A.hmm
   hmmpress databases/pfam35/Pfam-A.hmm
   ```
3. **Build MMseqs2 target DB** from per-family Pfam FASTA files:
   ```bash
   mmseqs createdb dataset/pfam_fastas_clean/*.fasta target_db
   ```
4. **Generate a small LineageFlow sample FASTA** (already on disk at
   `data/lineageflow/lineageflow-rp55.ckpt` for the ckpt; need to call
   `inference/batch_generate.py` to produce the FASTA).
5. **Run upstream `evaluate_all.py`** end-to-end with `--max-seqs 1` first
   to verify the wiring, then scale to n=512 / n=1024 for the paper claim.

### 4.2 Kanzi (Wave 77 R1 critical path)

1. **Kanzi upstream is a tokenizer, NOT a generator.** There is no FBD, no
   novelty, no designability per se. The paper metric is **reconstruction
   Kabsch RMSD** on AFDB-Foldseek held-out. Wave 77 must author
   `tools/kanzi_paper_metrics.py` from scratch (mirror what
   `tools/paper_metrics.py` does for FlowMol3 in Wave 75).
2. **Install Kanzi's missing deps on the GPU host:**
   ```bash
   /home/hugo/codes/flowa-multistep-reinference/.venvs/kanzi_venv/bin/pip install \
     biotite einops jaxtyping loguru timm torchdiffeq scipy fastpdb
   ```
3. **Source an AFDB-Foldseek held-out subset** (or use
   `data/pfam_holdout/random_clan.fasta` as a stand-in for the Wave 77
   smoke run; for the paper claim, source the proper AFDB-Foldseek
   subset via the upstream `load_from_mmap` schema).
4. **Wire `kabsch_rmsd` + `model.encode/decode` into a wrapper script**
   that produces `reconstruction_rmsd.json` per PDB.

### 4.3 Caveat on Wave 73-74 NFE-scan overclaim (per Wave 79 brief)

The Wave 73-74 multi-tier story (§7.4 LineageFlow, §7.5 FlowMol3) reports
NFE-scan speedup numbers using **internal composite metrics** (entropy
reduction + max_prob_delta + argmax_turnover). These are NOT paper metrics.
Wave 79's deliverable is the upstream `evaluate_all.py` (LineageFlow) +
upstream Kabsch RMSD wrapper (Kanzi) so that the §7.4 / §7.5 numbers can be
cross-validated against paper-parity metrics (family validity, foldability,
self-consistency, novelty for LineageFlow; reconstruction RMSD for Kanzi).

The §7.6 honest verdict must be amended to acknowledge that the
NFE-scan speedup is on internal composite, not on paper metrics — Wave 79
closes this gap for LineageFlow + Kanzi (Wave 75 already closed it for
FlowMol3).

---

## 5. Files written

- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave79-phase1-audit.md`
  (this doc).
- `/home/hugo/codes/flowa-multistep-reinference/data/kanzi_upstream/`
  (new clone, 6.0 MB, READ-ONLY intent).

No source code was edited. No upstream files were modified. No commit was made.

---

## 6. JSON return

```json
{
  "lineageflow_upstream_ready": true,
  "lineageflow_deps_available": [
    "torch==2.7.0+cu128",
    "transformers==4.57.6",
    "biopython==1.88",
    "numpy",
    "pandas",
    "huggingface_hub",
    "matplotlib"
  ],
  "lineageflow_deps_missing": [
    "hmmscan (HMMER binary)",
    "mmseqs (MMseqs2 binary)",
    "omegafold (OmegaFold binary)",
    "fair_esm (PyPI)",
    "biotite (PyPI)"
  ],
  "lineageflow_smoke_test_pass": false,
  "lineageflow_smoke_test_blocker": "missing HMMER/MMseqs2/OmegaFold binaries + Pfam-A.hmm DB + MMseqs2 target DB",
  "kanzi_upstream_cloned": true,
  "kanzi_upstream_path": "/home/hugo/codes/flowa-multistep-reinference/data/kanzi_upstream/",
  "kanzi_paper_metrics": [
    "reconstruction_kabsch_rmsd_A",
    "codebook_entropy",
    "codebook_perplexity",
    "codebook_js_distance",
    "codebook_utilization",
    "codebook_hamming_rotation_invariance"
  ],
  "kanzi_smoke_test_pass": false,
  "kanzi_smoke_test_blocker": "no upstream evaluation/ script; must author tools/kanzi_paper_metrics.py wrapper (Wave 77 R1)",
  "per_model_readiness": {
    "lineageflow": {
      "ready": false,
      "metrics": ["family_validity", "foldability_pLDDT", "self_consistency_scPerplexity", "novelty_mmseqs2_nnIdentity"],
      "deps_status": "PARTIAL (torch+transformers+biopython OK; HMMER/MMseqs2/OmegaFold/fair_esm/biotite MISSING)",
      "smoke_test": "BLOCKED on host-env install + Pfam-A.hmm download + MMseqs2 target DB build",
      "reference_data_status": "MISSING Pfam-A.hmm, MMseqs2 target DB, Pfam FASTA dataset; HAS Pfam held-out subset (data/pfam_holdout/random_clan.fasta, Wave 43)"
    },
    "kanzi": {
      "ready": false,
      "metrics": ["reconstruction_kabsch_rmsd_A", "codebook_entropy", "codebook_perplexity", "codebook_js_distance", "codebook_utilization", "codebook_hamming_rotation_invariance"],
      "deps_status": "PARTIAL (torch CPU OK; biotite, einops, jaxtyping, loguru, timm, torchdiffeq, scipy, fastpdb MISSING)",
      "smoke_test": "BLOCKED on (a) tools/kanzi_paper_metrics.py wrapper author + (b) AFDB-Foldseek held-out subset download",
      "reference_data_status": "PARTIAL (4 demo PDBs vendored; AFDB-Foldseek held-out subset MISSING)"
    }
  },
  "per_model_wallclock_estimate_s": {
    "lineageflow": 7200,
    "kanzi": 10800
  },
  "per_model_wallclock_estimate_human": {
    "lineageflow": "1.5-3.5 h for 1000 seqs (OmegaFold+ESM-IF dominate), 3-7 h for 2000 seqs",
    "kanzi": "1.5-4 h for 1000 PDBs (DiT decode dominates), 3-9 h for 2000 PDBs"
  },
  "files_written": [
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave79-phase1-audit.md",
    "/home/hugo/codes/flowa-multistep-reinference/data/kanzi_upstream/"
  ],
  "files_cloned": [
    "/home/hugo/codes/flowa-multistep-reinference/data/kanzi_upstream/"
  ],
  "notes": [
    "LineageFlow upstream is already vendored (Wave 10); 4/4 metric scripts present; orchestrator at evaluation/evaluate_all.py:1",
    "Kanzi upstream CLONED successfully (6.0 MB, main branch); does NOT have an evaluation/ directory — must author tools/kanzi_paper_metrics.py wrapper",
    "Kanzi is a flow-AUTOENCODER (tokenizer), NOT a generator; paper metric is reconstruction Kabsch RMSD on AFDB-Foldseek held-out, not FBD or designability",
    "Both models BLOCKED on host-env install + reference-data download for Wave 76/77 paper-metric reproduction",
    "Wave 73-74 NFE-scan overclaim caveat: §7.4/§7.5 numbers are internal composite, not paper metrics; Wave 79 closes this gap for LineageFlow + Kanzi (Wave 75 closed for FlowMol3)",
    "No source code was modified; no upstream files were modified; no commit was made"
  ]
}
```
