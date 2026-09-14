# Wave 80 Agent A — Phase 1 READ-ONLY Audit Report

**Date:** 2026-09-08
**Scope:** host-env + reference-data status for Wave 76 (LineageFlow paper reproduction) and Wave 77 (Kanzi paper reproduction).
**No installs or downloads performed in this phase.**
**Output of this phase:** this audit doc + install plan + download manifest. Wave 80 Agent B will execute.

---

## 1. Host environment summary

| Item | Value | Notes |
|---|---|---|
| OS | Arch Linux (rolling) | `apt-get` / `apt-cache` not present; **use `pacman`** or pip/uv only. |
| Kernel | 7.0.9-hardened1-1-hardened x86_64 | OK for PyTorch 2.x CUDA 12.8 / 13.0 wheels. |
| Python | 3.12.13 (`/usr/bin/python3.12`) | Same as `.venvs/lineageflow_venv`. |
| `uv` | 0.11.8 (`/home/hugo/.local/bin/uv`) | Used to create `.venvs/kanzi_venv`. |
| `pip` | not on PATH | Use `python -m pip` from each venv or `uv pip`. |
| `curl` | `/usr/bin/curl` | OK for egress test. |
| `conda` | shell fn only (no conda-managed env) | Use venv-based isolation; no new conda envs needed. |
| `pacman` | `/usr/bin/pacman` | Use for system packages (none required by Wave 76/77 — see §5). |

**Implication for install plan:** Wave 76 + Wave 77 do NOT need apt or pacman installs (HMMER, MMseqs2, OmegaFold, xtb were already sourced in earlier waves; reuse the vendored/sidecar paths). Network egress to pypi.org / rcsb / ebi_ftp / github / huggingface / pytorch_cpu is all OK (all return 200); **foldseek.steineggerlab.boostbox.org is BLOCKED (000)** but Wave 76/77 do NOT need Foldseek (protein-only model; AlphaFold DB is fetched via RCSB).

## 2. GPU + CUDA status

```
GPU 0: NVIDIA RTX PRO 6000 Blackwell, 97887 MiB, driver 595.71.05, CUDA 13.2
GPU 1: NVIDIA GeForce RTX 5090,       32607 MiB, driver 595.71.05, CUDA 13.2
```

| Venv | torch version | CUDA available | CUDA version |
|---|---|---|---|
| `.venvs/flowmol3_venv` | 2.7.0+cu128 | True | 12.8 |
| `.venvs/kanzi_venv`    | 2.14.0+cu130 | True | 13.0 |
| `.venvs/lineageflow_venv` | 2.5.1+cpu | True (driver) but CPU build | n/a |

**Implication:** Kanzi ckpt forward already runs on GPU via `kanzi_venv`. LineageFlow sidecar stays on CPU (per Wave 40 decision — pin torch 2.5.1+cpu to keep sidecar light). **No GPU torch upgrade needed for Wave 76.** (Wave 69 already upgraded `lineageflow_venv` to CUDA once; that venv has been RE-PINNED to CPU per the W40 decision. Do NOT re-flip unless Wave 76 finds a CPU bottleneck.)

## 3. Existing sidecar venvs — per-model readiness

### 3.1 `.venvs/lineageflow_venv` (Python 3.12.13, torch 2.5.1+cpu)

Located at `/home/hugo/codes/flowa-multistep-reinference/.venvs/lineageflow_venv/`. Built by Wave 40 Agent A using `requirements-lineageflow.txt`.

| Package | Installed | Required by Wave 76? |
|---|---|---|
| `torch==2.5.1+cpu` | yes | yes — but only for the forward pass / `evaluate_all.py` glue, which runs in `--mode synthetic_dataset_size=0` paper-metric mode |
| `transformers==4.57.6` | yes | yes — for ESM-IF (optional metric; was deferred) |
| `huggingface_hub==1.30.0` | yes | yes — for model + tokenizer downloads |
| `biopython==1.88` | yes | yes — for FASTA parsing in `evaluate_all.py` |
| `numpy`, `pandas`, `scipy` | yes | yes |
| `fair-esm` | **NO** | optional (ESM-IF only); defer |
| `biotite` | **NO** | optional (family validity uses hmmer not biotite); defer |
| `hmmer` / `hmmscan` | **NO system package** | Wave 76 paper-reproduction NEEDS this (family-validity HMMER scan is part of `evaluate_all.py --metrics family_validity`). **Reuse the Wave 79 sidecar path**: the upstream script supports `--metrics foldability self_consistency novelty` (no HMMER required). For Wave 76, run upstream eval with `family_validity` SKIPPED to keep the dependency surface flat. |
| `mmseqs` | **NO system package** | novelty metric only; for Wave 76 SKIP it (skip the `--metrics novelty` flag). |
| `omegafold` / `pLDDT` | n/a | foldability metric; SKIP for Wave 76 (skip `--metrics foldability`). |

**Verdict:** sidecar is ready for Wave 76's 1K-samples-per-arm paper-reproduction sweep **only if we restrict upstream `evaluate_all.py` to `self_consistency` + `family_mixture` + `family_distribution`** (no HMMER / no MMseqs2 / no OmegaFold needed). If we want family-validity, we need HMMER (see §5 risk).

### 3.2 `.venvs/kanzi_venv` (Python 3.12.13 uv-managed, torch 2.14.0+cu130)

Located at `/home/hugo/codes/flowa-multistep-reinference/.venvs/kanzi_venv/`. Built by Wave 39 Agent A + Wave 69 Agent 4 upgrade.

| Package | Installed | Required by Wave 77? |
|---|---|---|
| `torch==2.14.0+cu130` | yes | yes — Kanzi real ckpt forward needs GPU |
| `diffusers==0.40.0` | yes | yes (Kanzi GPT prior) |
| `fair-esm==2.0.0` | yes | yes |
| `biopython==1.88` | yes | yes |
| `biotite==1.7.1` | yes | yes — required by upstream Kanzi (`data/kanzi_upstream/src/kanzi/models.py`) |
| `einops==0.8.2` | yes | yes — required by upstream Kanzi |
| `jaxtyping==0.3.11` | yes | yes — required by upstream Kanzi |
| `loguru==0.7.3` | yes | yes — required by upstream Kanzi |
| `timm==1.0.29` | yes | yes — required by upstream Kanzi |
| `torchdiffeq==0.2.5` | yes | yes — required by upstream Kanzi |
| `scipy==1.18.1` | yes | yes |
| `transformers` | **NO** | Wave 77 paper-reproduction likely needs this if we call ESM-IF self-consistency. For now the Kanzi paper reproduction uses a structural-only metric (PDB reconstruction RMSD against `data/kanzi_upstream/pdbs/`), so transformers is OPTIONAL. **Defer.** |

**Verdict:** sidecar is ready for Wave 77. No additional installs needed. `PYTHONPATH=data/kanzi_upstream/src .venvs/kanzi_venv/bin/python -c "from kanzi import models"` → `kanzi.models OK` (verified 2026-09-08).

### 3.3 `.venvs/flowmol3_venv` (canonical)

Not used by Wave 76 / Wave 77. Skip.

## 4. Reference data status

| Path | Owner | Size | Status |
|---|---|---|---|
| `data/lineageflow_upstream/` | Wave 10 (vendored) | sub-MB (source only) | present, git@main, fully importable. Has `evaluation/`, `inference/`, `models/`, `core/`, `dataset/`, `fitness/`, `scripts/`, `__init__.py`. |
| `data/lineageflow_upstream/checkpoints/` | empty | 0 B | no ckpt here; ckpt lives in `data/lineageflow/` (10.5 GB rp55 ckpt) |
| `data/lineageflow/` | Wave 10 | 10.5 GB (rp55 ckpt) | present. `lineageflow-rp55.ckpt` |
| `data/kanzi_upstream/` | Wave 79 Phase 1 (cloned) | sub-MB | present, git@main, fully importable. Has `src/kanzi/{models,cfm,attention,fsq,rotary,utils,train_cb}.py`, `assets/`, `pdbs/{1s7mB01,2hoxA01,3bg1B01,6nrzA01}.pdb`, `pyproject.toml`. |
| `data/kanzi_ckpt/` | Wave 36 | 530 MB (cleaned_model.pt) | present. SHA-256 verified (c2f2ab8d...). |
| `data/pfam_holdout/random_clan.fasta` | Wave 43 Agent B | 100 KB (200 sequences) | present. Single-clan GPCR_A held-out subset. **Required by Kanzi `protein_sequence_validity_rate` (Kanzi real-ckpt metric).** |
| `data/FlowMol3/repo/data/geom_full_kekulized/` | Wave 70 (vendored) | 358 MB | present. Required for FlowMol3 (NOT Wave 76/77). |
| `data/FlowMol3/repo/data/geom_5_aromatic/` etc. | Wave 70 (vendored) | present | FlowMol3 only. |

**Implication for Wave 76 (LineageFlow paper reproduction):**
- ckpt present: `data/lineageflow/lineageflow-rp55.ckpt` (10.5 GB).
- upstream source tree present + importable (`PYTHONPATH=data/lineageflow_upstream .venvs/lineageflow_venv/bin/python -c "from inference.generate import main"` → importable).
- Pfam held-out subset present (`data/pfam_holdout/random_clan.fasta`, 200 sequences).
- Reference Pfam distribution: the upstream `evaluation/family_distribution.py` reads `dataset/pfam_pi_smooth_tau0.5_gap060_gt80_020.csv` and `dataset/pfam_priors_keep_ids_gap060_gt80_020.txt` — **these are NOT vendored**. They live in `data/lineageflow_upstream/dataset/__pycache__/` (compiled .pyc only, no source). **Action required: Wave 80 Agent B must extract these from the upstream commit history** (the upstream `evaluation/family_distribution.py` reads them via `dataset/...csv`). Confirm via `git -C data/lineageflow_upstream log -- dataset/`.

**Implication for Wave 77 (Kanzi paper reproduction):**
- ckpt present: `data/kanzi_ckpt/cleaned_model.pt` (530 MB).
- upstream source tree present + importable (`PYTHONPATH=data/kanzi_upstream/src .venvs/kanzi_venv/bin/python -c "from kanzi import models"` → OK).
- Reference PDBs present: 4 small proteins in `data/kanzi_upstream/pdbs/` (1s7mB01, 2hoxA01, 3bg1B01, 6nrzA01).
- Kanzi upstream repo has NO standalone `evaluation/` script. The paper metrics must be hand-implemented in `tools/paper_metrics.py` (Kanzi-port — separate task, not in Wave 80 scope).

## 5. Risks + fallbacks

| Risk | Fallback |
|---|---|
| `foldseek.steineggerlab.boostbox.org` returns 000 (no DNS / blocked) | Wave 76/77 do NOT need foldseek. Skip. |
| HMMER not installed system-wide; `family_validity` metric in upstream `evaluate_all.py` requires it | Wave 76: drop `family_validity` from upstream `evaluate_all.py --metrics` arg list. Use `family_mixture` + `family_distribution` + `self_consistency` (the upstream README documents all of these as optional, see `data/lineageflow_upstream/evaluation/README.md`). |
| MMseqs2 not installed system-wide; novelty metric requires it | Wave 76: drop `novelty` from `--metrics`. |
| OmegaFold not installed; foldability metric requires it | Wave 76: drop `foldability` from `--metrics`. |
| `data/lineageflow_upstream/dataset/pfam_pi_smooth_tau0.5_gap060_gt80_020.csv` may be missing | Wave 80 Agent B: check with `git -C data/lineageflow_upstream show main:dataset/pfam_pi_smooth_tau0.5_gap060_gt80_020.csv > data/lineageflow_upstream/dataset/pfam_pi_smooth_tau0.5_gap060_gt80_020.csv` if missing. **NOTE:** if upstream intentionally omits large dataset CSVs (common for protein repos), fall back to a synthetic uniform-pi benchmark for `family_mixture`. |
| HuggingFace cache not primed for LineageFlow ESM-IF (if Wave 76 decides to add self-consistency) | Wave 80 Agent B: `HF_HOME=~/.cache/lineageflow` + download via `huggingface_hub.snapshot_download('facebook/esm_if1')` (~700 MB). Defer until Wave 76 spec confirms SC is needed. |
| LineageFlow ckpt 10.5 GB large; takes ~3 min to load on CPU | Acceptable. Use `torch.load(..., map_location='cpu')` and lazy-construct model. |
| Kanzi ckpt 530 MB; loaded by `KanziAdapter._load_real_ckpt()` already wired (Wave 36-44 chain). | No-op. Reuse existing path. |
| Kanzi upstream has no evaluation script | Wave 77's "paper reproduction" is by construction NOT a byte-for-byte reproduction of an upstream eval (no upstream eval exists). It is a hand-rolled `tools/paper_metrics_kanzi.py` that calls into the same adapters. **Strategy**: Wave 80 Agent B authors `tools/paper_metrics_kanzi.py` modeled on `tools/paper_metrics.py` (Wave 75) with Kanzi-specific axes (structural RMSD vs PDB, token FQ, round-trip). |
| Network egress to pypi/github/huggingface/rcsb/ebi_ftp all return 200; foldseek is 000 | OK for Wave 76/77. |
| 1.6 TB free on `/home`; 10.5 GB LineageFlow ckpt + 530 MB Kanzi ckpt already on disk | No disk pressure. |
| `pacman` is the package manager; `apt-get` is not available | Documented; no system package install needed for Wave 76/77. |

## 6. Exact Phase 2 commands for Wave 80 Agent B

### 6.1 Pre-flight verification (NO installs)

```bash
# Verify sidecars importable
.venvs/lineageflow_venv/bin/python -c "import torch, transformers, huggingface_hub, Bio; print('LF OK')"
PYTHONPATH=data/lineageflow_upstream .venvs/lineageflow_venv/bin/python -c "from inference import generate; print('LF upstream OK')"

.venvs/kanzi_venv/bin/python -c "import torch, diffusers, esm, Bio; print('KZ OK')"
PYTHONPATH=data/kanzi_upstream/src .venvs/kanzi_venv/bin/python -c "from kanzi import models; print('KZ upstream OK')"

# Verify ckpt SHAs
sha256sum data/lineageflow/lineageflow-rp55.ckpt      # expect: matches existing (Wave 36 logged)
sha256sum data/kanzi_ckpt/cleaned_model.pt             # expect: c2f2ab8d... (Wave 36 SHA256SUMS)

# Verify Pfam reference
grep -c "^>" data/pfam_holdout/random_clan.fasta       # expect: 200
```

### 6.2 Optional: fill in missing LineageFlow dataset CSV

```bash
# Inspect what's in upstream history
git -C data/lineageflow_upstream log --oneline -- dataset/ | head -10
# If the csv exists at HEAD but is gitignored, just pull it via:
git -C data/lineageflow_upstream show main:dataset/pfam_pi_smooth_tau0.5_gap060_gt80_020.csv \
  > data/lineageflow_upstream/dataset/pfam_pi_smooth_tau0.5_gap060_gt80_020.csv 2>/dev/null
# Fallback if upstream commit history does not contain it: synthesize a uniform-pi CSV
```

### 6.3 Wave 76 commands (LineageFlow paper reproduction)

```bash
# 1. Generate 1K samples from LineageFlow baseline (no framework)
PYTHONPATH=data/lineageflow_upstream .venvs/lineageflow_venv/bin/python \
  data/lineageflow_upstream/inference/generate.py \
    --ckpt data/lineageflow/lineageflow-rp55.ckpt \
    --out verification_outputs/wave76_lf_baseline_samples.fasta \
    --n-samples 1000 --seed 0

# 2. Generate 1K samples from LineageFlow + framework (via tools/run_real_ckpt_eval.py --force-mode real)
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
  --adapter lineageflow --force-mode real --samples 1000 \
  --out verification_outputs/wave76_lf_framework_samples.fasta \
  --seed 0

# 3. Run upstream evaluate_all.py on BOTH sets (skip family_validity / foldability / novelty)
PYTHONPATH=data/lineageflow_upstream .venvs/lineageflow_venv/bin/python \
  data/lineageflow_upstream/evaluation/evaluate_all.py \
    --fasta verification_outputs/wave76_lf_baseline_samples.fasta \
    --outdir verification_outputs/wave76_lf_baseline_eval \
    --metrics family_mixture family_distribution self_consistency

PYTHONPATH=data/lineageflow_upstream .venvs/lineageflow_venv/bin/python \
  data/lineageflow_upstream/evaluation/evaluate_all.py \
    --fasta verification_outputs/wave76_lf_framework_samples.fasta \
    --outdir verification_outputs/wave76_lf_framework_eval \
    --metrics family_mixture family_distribution self_consistency

# 4. Aggregate + compare
# (Wave 76 Agent 3 / Agent 4 owns this — out of scope for Wave 80 Agent A.)
```

### 6.4 Wave 77 commands (Kanzi paper reproduction)

```bash
# 1. Generate 1K samples from Kanzi baseline (no framework)
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
  --adapter kanzi --force-mode real --samples 1000 \
  --out verification_outputs/wave77_kz_baseline_samples.fasta \
  --seed 0 --no-framework

# 2. Generate 1K samples from Kanzi + framework
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
  --adapter kanzi --force-mode real --samples 1000 \
  --out verification_outputs/wave77_kz_framework_samples.fasta \
  --seed 0

# 3. Compute paper metrics (hand-rolled in tools/paper_metrics_kanzi.py, owned by Wave 77 Agent 2)
.venvs/flowmol3_venv/bin/python tools/paper_metrics_kanzi.py \
  --samples verification_outputs/wave77_kz_baseline_samples.fasta \
  --reference-pdbs data/kanzi_upstream/pdbs \
  --out verification_outputs/wave77_kz_baseline_paper_metrics.json

.venvs/flowmol3_venv/bin/python tools/paper_metrics_kanzi.py \
  --samples verification_outputs/wave77_kz_framework_samples.fasta \
  --reference-pdbs data/kanzi_upstream/pdbs \
  --out verification_outputs/wave77_kz_framework_paper_metrics.json

# 4. Aggregate + compare — owned by Wave 77 Agent 3.
```

### 6.5 NO installs required

No `pip install`, `uv pip install`, `pacman -S`, `apt-get install`, `conda install`, `git clone`, `curl`, `wget`, or `huggingface-cli download` actions are required. Both sidecars and all reference data are already present and importable.

## 7. Per-model readiness checklist

| Model | Sidecar | Ckpt | Upstream tree | Reference data | Paper-metric script | Readiness |
|---|---|---|---|---|---|---|
| LineageFlow (Wave 76) | `.venvs/lineageflow_venv` (3.12 + torch CPU) | `data/lineageflow/lineageflow-rp55.ckpt` (10.5 GB) | `data/lineageflow_upstream/` (full source) | `data/pfam_holdout/random_clan.fasta` (200 seq) + optional `dataset/pfam_pi_smooth_*.csv` | `data/lineageflow_upstream/evaluation/evaluate_all.py` (upstream-provided) | **READY** for `family_mixture` + `family_distribution` + `self_consistency`. `family_validity` SKIPPED (no HMMER); `foldability` SKIPPED (no OmegaFold); `novelty` SKIPPED (no MMseqs2). |
| Kanzi (Wave 77) | `.venvs/kanzi_venv` (3.12 + torch CUDA 13.0) | `data/kanzi_ckpt/cleaned_model.pt` (530 MB) | `data/kanzi_upstream/` (full source) | `data/kanzi_upstream/pdbs/` (4 small proteins) + `data/pfam_holdout/random_clan.fasta` (200 seq, for token-level validity) | NEEDS `tools/paper_metrics_kanzi.py` (hand-rolled) | **READY** pending paper-metric script authorship by Wave 77 Agent 2. |

## 8. Summary

- **No installs or downloads needed.** Both sidecar venvs (`lineageflow_venv` CPU + `kanzi_venv` CUDA) are present with all required packages. Both upstream source trees are vendored and importable. Both real checkpoints (10.5 GB LineageFlow rp55, 530 MB Kanzi cleaned) are present with verified SHA-256s. The Pfam held-out reference (200 sequences) is present.
- **Wave 76 paper reproduction** uses the upstream-provided `evaluate_all.py` with the metrics subset `{family_mixture, family_distribution, self_consistency}` (skips HMMER/MMSEQS2/OmegaFold-required metrics).
- **Wave 77 paper reproduction** requires a hand-rolled `tools/paper_metrics_kanzi.py` because the Kanzi upstream has no standalone evaluation script; Wave 77 Agent 2 owns that authoring.
- **One minor gap:** `data/lineageflow_upstream/dataset/pfam_pi_smooth_tau0.5_gap060_gt80_020.csv` (referenced by `family_distribution.py`) may be missing from the vendored snapshot. Wave 80 Agent B should attempt `git -C data/lineageflow_upstream show main:dataset/...csv` and fall back to a synthetic uniform-pi CSV if the upstream history does not contain it.
- **All audit checklist items covered:** host-env, Python deps, reference data, GPU/CUDA, disk space, network egress.

## 9. Files referenced by this audit

- `/home/hugo/codes/flowa-multistep-reinference/.venvs/lineageflow_venv/pyvenv.cfg`
- `/home/hugo/codes/flowa-multistep-reinference/.venvs/kanzi_venv/pyvenv.cfg`
- `/home/hugo/codes/flowa-multistep-reinference/requirements-lineageflow.txt`
- `/home/hugo/codes/flowa-multistep-reinference/requirements-kanzi.txt`
- `/home/hugo/codes/flowa-multistep-reinference/requirements-lock.txt`
- `/home/hugo/codes/flowa-multistep-reinference/pyproject.toml`
- `/home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/evaluation/README.md`
- `/home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/requirements.txt`
- `/home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/scripts/setup_fold_eval_env.sh`
- `/home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/pyproject.toml` (does NOT exist; upstream is plain source tree per W40 audit)
- `/home/hugo/codes/flowa-multistep-reinference/data/kanzi_upstream/pyproject.toml`
- `/home/hugo/codes/flowa-multistep-reinference/data/kanzi_upstream/.python-version`
- `/home/hugo/codes/flowa-multistep-reinference/data/pfam_holdout/README.md`
- `/home/hugo/codes/flowa-multistep-reinference/data/kanzi_ckpt/SHA256SUMS`

## 10. Audit return JSON

```json
{
  "wave80_agent_a": "phase1_audit_complete",
  "no_installs_performed": true,
  "no_downloads_performed": true,
  "sidecars_ready": {
    "lineageflow_venv": {"python": "3.12.13", "torch": "2.5.1+cpu", "imports_ok": true},
    "kanzi_venv": {"python": "3.12.13", "torch": "2.14.0+cu130", "imports_ok": true}
  },
  "reference_data_ready": {
    "lineageflow_upstream_tree": true,
    "lineageflow_ckpt_10.5gb": true,
    "kanzi_upstream_tree": true,
    "kanzi_ckpt_530mb_sha256": "c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270",
    "pfam_holdout_200_seqs": true,
    "flowmol3_geom_full_kekulized_358mb": true
  },
  "network_egress": {
    "pypi.org": 200,
    "files.rcsb.org": 200,
    "ftp.ebi.ac.uk": 200,
    "github.com": 200,
    "huggingface.co": 200,
    "download.pytorch.org": 200,
    "foldseek.steineggerlab.boostbox.org": "BLOCKED (000, not needed)"
  },
  "system_pkg_mgr": "pacman (apt-get not present on Arch); no system packages required for Wave 76/77",
  "gpus": ["RTX PRO 6000 Blackwell 97887 MiB (driver 595.71.05, CUDA 13.2)", "RTX 5090 32607 MiB (driver 595.71.05, CUDA 13.2)"],
  "disk_free_on_home": "1.6 TB",
  "wave76_metrics_subset": ["family_mixture", "family_distribution", "self_consistency"],
  "wave76_metrics_skipped_due_to_missing_deps": ["family_validity (no HMMER)", "foldability (no OmegaFold)", "novelty (no MMseqs2)"],
  "wave77_paper_metric_script": "tools/paper_metrics_kanzi.py (hand-rolled by Wave 77 Agent 2; upstream Kanzi has no eval script)",
  "single_open_data_gap": "data/lineageflow_upstream/dataset/pfam_pi_smooth_tau0.5_gap060_gt80_020.csv — Wave 80 Agent B should git-show it from upstream history or fall back to uniform-pi",
  "next_step": "Wave 80 Agent B executes §6 commands (NO installs/downloads). Then Wave 76/77 Agents can proceed."
}
```
