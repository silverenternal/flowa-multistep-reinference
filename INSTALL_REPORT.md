# INSTALL_REPORT.md — FlowA Reproducibility Install State

**Status:** Restored 2026-09-11 (Wave 106.C.4)
**Author:** Wave 106.C.4 Agent
**Original task:** Wave 80 Agent B task #1169 (marked complete in todo/)
**Original commit:** never landed on disk; file was absent at both `/INSTALL_REPORT.md` and `docs/INSTALL_REPORT.md`
**Repo state:** HEAD `883d6fd` (post Wave 106.C.3 + Wave 80-100 stack)
**Total repo commits:** 566
**Unpushed vs origin/main:** 30 commits (local Wave 106 hygiene + audit fixes — no algorithm/source-code edits)

---

## 1. Why this file exists

Wave 106.A.4 path-consistency audit (finding #5, HIGH severity) reported that task
#1169 ("Author INSTALL_REPORT.md + commit (no push)") was marked `completed` in the
todo/ tracker but the file was absent on disk at both repo-root and `docs/`. The
file had never landed in git history. Wave 106.C.4 recreates it from current env
state.

The Wave 80 stack (Agent A through D) audit-trail lives at:
- `docs/audit/wave80-phase1-audit.md` — sidecar venv inventory + missing deps
- `docs/audit/wave80-phase2-install.md` — HMMER + MMseqs2 + OmegaFold + LineageFlow/Kanzi Python deps + Pfam-A.hmm reference DB + MMseqs2 target DB
- `docs/audit/wave80-phase3-verify.md` — D.4 byte-stable regression + end-to-end smoke test
- `docs/audit/wave80-phase4-final.md` — paper §7.3/§7.4/§7.6 update + synthesis

The current file is the **state-preserving restatement** of what Wave 80 produced,
**as of 2026-09-11** (HEAD `883d6fd`).

---

## 2. Repo metadata

- **Repo:** `/home/hugo/codes/flowa-multistep-reinference`
- **Branch:** `main`
- **HEAD SHA:** `883d6fd1a855f8c7f7a69c03437c6de1d4e17bd0`
- **Commit count:** 566
- **Python (project venv):** Python 3.12.13 (per `env_hash.txt`)
- **Project venv:** `.venv/` (stdlib-only framework; `tests/test_universal/test_no_molecular_import.py` guards `universal/` ⊄ molecules)

---

## 3. Pinned environment (env_hash.txt, lock_hash)

```
lock_hash=983f7707e7207ed6dee1972cc1fb9306448ad6367963edefd612f88b76519092
python_version=Python 3.12.13
torch_version=torch:2.7.0+cu128+cuda12.8
adapter_deps_hash=dd86845312d820dadbf18d0dce6fa7d062c6d45a197e361977c58fbdd550e363
rdkit_version=rdkit:2026.03.5
biopython_version=biopython:1.88
transformers_version=transformers:not-installed
diffusers_version=diffusers:0.40.0
torchvision_version=torchvision:0.22.0+cu128
torch_geometric_version=torch_geometric:not-installed
```

### 3.1 Caveat on env_hash drift (Wave 106.A.4 finding #11)

Five different `composite_hash` values exist across the env_hash variants
(see audit doc finding #11 for the table). They are NOT bug drift — they
are intentional per-Wave-provenance snapshots:

- `env_hash.txt` → "lock_hash" (full pinned env state)
- `env_hash_R2.txt`, `env_hash_R3.txt`, `env_hash_R6.txt` → Wave 2 / 3 / 6 repro-env snapshots
- `env_hash_R5.txt` → Wave 5 GPU experiment snapshot
- `env_hash_host_fingerprint.json` → Wave 38+ host fingerprint (post-F.5 env_hash infrastructure)

The single source of truth for the **current** pinned env is
`env_hash.txt::lock_hash` = `983f7707...9092`.

---

## 4. Twelve venvs (1 project + 11 model)

Per `docs/environments.md` (Wave 102 P1-C, frozen 2026-09-11):

| Tier | Venv | Owner model | Python | torch |
|---|---|---|---|---|
| project | `.venv` | project (stdlib-only framework) | 3.12.13 | (none) |
| model | `.venvs/flowmol3_venv` | FlowMol3 (Pitt pretrained, partial-fidelity GVP) | 3.12.13 | 2.2.0+cu121 |
| model | `.venvs/kanzi_venv` | Kanzi (ICLR 2026 protein flow-AE) | 3.12.13 | 2.7.0+cu128 |
| model | `.venvs/lineageflow_venv` | LineageFlow (ICML 2026 protein) | 3.12.13 | 2.7.0+cu128 |
| model | `.venvs/hidream_venv` | HiDream-I1 (17B Dev, HF safetensors) | 3.12.13 | 2.7.0+cu128 |
| model | `.venvs/lumina_venv` | Lumina-Image 2.0 (HF LFS, ~52 GB) | 3.12.13 | 2.7.0+cu128 |
| model | `.venvs/wan2_2_venv` | Wan2.2-T2V-A14B (HF LFS, ~130 GB) | 3.12.13 | 2.7.0+cu128 |
| model | `.venvs/protbfn_venv` | ProtBFN / AbBFN | 3.12.13 | 2.7.0+cu128 |

Note: `docs/environments.md` lists 7 model venvs; the activation matrix extends
this with 4 additional 2026-SOTA-2 venvs (per Wave 102 P1-C update). For
canonical 12-cell activation patterns, see `docs/environments.md` §"Venv
Activation Matrix (frozen 2026-09-11, Wave 102)".

### 4.1 Driver / hardware

- **Driver:** NVIDIA 595.71.05, CUDA Version 13.2 (driver-level cap)
- **GPU 0:** NVIDIA RTX PRO 6000 Blackwell, sm_120, 98 GB
- **GPU 1:** NVIDIA GeForce RTX 5090, sm_120, 32 GB
- **FlowMol3 caveat:** `.venvs/flowmol3_venv` is the exception (torch
  2.2.0+cu121, arch_list capped at sm_50-sm_90, no sm_120). Closing this
  gap requires a `uv pip install --upgrade torch==2.7.0+cu128 ...` rerun.

---

## 5. Vendored checkpoints (G1 SHA-256 ckpt verification)

Per `verification_outputs/ckpt_sha256.json` (Wave 106.C.1, commit `d7daf90`):

| Model | Path | SHA-256 |
|---|---|---|
| FlowMol3 | `data/flowmol3/weights_real/checkpoints/last.ckpt` | `0e949b56b54c1d2fcbded4f0c9857bfd33dbde86bcc9db2f82572628f7f9f5b5` |
| Kanzi | `data/kanzi_ckpt/cleaned_model.pt` | `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270` |
| Kanzi | `data/kanzi_ckpt/kanzi_encoder.pt` | `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270` |
| LineageFlow | `data/lineageflow/lineageflow-rp55.ckpt` | `f0b4b25e626878be5c26da9e65d44c2e1551a076652d416f955b1357cde54a2b` |

A reviewer can re-verify with:

```bash
sha256sum data/flowmol3/weights_real/checkpoints/last.ckpt \
          data/kanzi_ckpt/cleaned_model.pt \
          data/kanzi_ckpt/kanzi_encoder.pt \
          data/lineageflow/lineageflow-rp55.ckpt
```

and compare against `verification_outputs/ckpt_sha256.json`.

---

## 6. Vendored upstream snapshots (G4)

| Model | Commit | Path |
|---|---|---|
| LineageFlow | `ccef84a` ("Prepare LineageFlow public release") | `data/lineageflow_upstream/` |
| Kanzi | `cfed9cf` | `data/kanzi_upstream/` |
| FlowMol3 | `77cae22` ("Update readme.md") | `data/FlowMol3/repo/` |

**Reviewer caveat (Wave 106.A.4 finding #12/14):** Kanzi + FlowMol3 commit SHAs
are NOT verifiable from any tracked file (no `.git` folder inside the vendored
dirs). Only LineageFlow's `ccef84a` is verifiable from
`verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json:36`.

---

## 7. System binaries (Wave 80 install)

| Binary | Source | Verified at |
|---|---|---|
| HMMER (`hmmpress`, `hmmscan`) | system package | Wave 80 Phase 2 |
| MMseqs2 | system package | Wave 80 Phase 2 |
| OmegaFold | git clone (`.venvs/omegafold_clone/`) | Wave 80 Phase 2 |
| xtb | system package | Wave 74 F3 |
| RDKit | PyPI (rdkit:2026.03.5) | env_hash.txt |
| BioPython | PyPI (biopython:1.88) | env_hash.txt |

---

## 8. Reference databases (Wave 80 install)

| Database | Path | Source |
|---|---|---|
| Pfam-A.hmm | `data/lineageflow_upstream/databases/Pfam-A.hmm` | Pfam release 35.0 (Wave 80) |
| MMseqs2 target DB | `data/lineageflow_upstream/databases/targetDB` | Wave 80 |
| PB config | `data/FlowMol3/repo/fm3_evals/posebusters/pb_config_with_energy_ratio.yaml` | FlowMol3 upstream commit `77cae22` (Wave 82 vendor) |
| Energy dist | `data/FlowMol3/repo/fm3_evals/posebusters/energy_dist.npz` | Wave 74 F4 vendor |

---

## 9. Current test counts (post Wave 106.C.3 fix F-05)

Per `pytest_results.txt` at HEAD `883d6fd`:

```
3 failed, 2165 passed, 9 skipped, 39 warnings in 517.49s
```

- **D.4 byte-stable regression vectors:** **72/72 PASS** (33 in `tests/test_d4_regression_vectors.py` + 39 in `tests/test_adapters/test_regression_vectors.py`); see `docs/GATES.md` "D.4 byte-stable regression vectors" section (single source of truth).
- **3 pre-existing FAILED tests** (unrelated to framework logic; tracked in `docs/audit/wave48-pytest-pre-push-fixes.md`):
  - `test_exp2_stochastic_fm_w2_ratio_reproduces_25pct_reduction`
  - `test_check_docs_against_code.py::test_no_false_positives_on_current_repo`
  - `test_check_docs_against_code.py::test_self_test_quiet_mode_returns_zero_exit`

---

## 10. D.4 status

- **Status:** 72/72 PASS (Wave 106.C.3 F-06a standardization)
- **Last green:** commit `f97ec1c` (Wave 106.C.2 final synthesis); re-verified
  green at every commit through Wave 106.C.3 (`9e3aea5`) and the Wave 106.C.4
  authoring commit

---

## 11. Reviewer cross-references

- `docs/environments.md` — 12-venv activation matrix (Wave 102 P1-C)
- `docs/GATES.md` — D.4 byte-stable regression vectors (single source of truth)
- `docs/audit/wave80-phase{1,2,3,4}-final.md` — Wave 80 install audit trail
- `verification_outputs/ckpt_sha256.json` — 3-model SHA-256 pin manifest
- `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json` — LineageFlow commit `ccef84a` audit
- `verification_outputs/kanzi_real_ckpt_forward_q4_2026.json` — Kanzi ckpt forward audit
- `docs/audit/wave106-a-4-path-consistency.md` finding #5 — original audit that flagged this file as missing

---

## 12. D.4 claim (Wave 106.A.4 finding #18)

The D.4 figure cited throughout this submission package is **72/72 PASS** for
the full D.4 regression suite (per `docs/GATES.md`). The legacy "33/33 PASS"
figure (used in historical audit docs and Wave 38-39 commit messages) referred
ONLY to the Wave 38-39 first-batch subset (`tests/test_d4_regression_vectors.py`,
30 + 3 in `test_adapters/test_regression_vectors.py` = 33 in the original
file count; the test count expanded in Wave 32-33 batches 2/3/4). See
`docs/audit/wave106-c3-fix-summary.md` F-06 for the standardization history.

---

**End of INSTALL_REPORT.md**
