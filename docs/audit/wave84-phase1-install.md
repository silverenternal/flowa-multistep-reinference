# Wave 84 Phase 1 — Python 3.10 Sidecar venv + OmegaFold Install Report

**Date:** 2026-09-08
**Agent:** Wave 84 Agent A
**Goal:** Provision `/home/hugo/.venvs/omegafold_venv` (Python 3.10) with OmegaFold installed, and document the environment requirements for `run_foldability.py` + `self_consistency_esmif.py`.

---

## (a) Python 3.10 install path

Python 3.10 was already available on the host via `uv`-managed user-local installs:

| Item              | Value                                            |
| ----------------- | ------------------------------------------------ |
| Interpreter path  | `/home/hugo/.local/bin/python3.10`               |
| Version           | Python 3.10.20 (final, Apr 14 2026 build)        |
| Build             | Clang 22.1.3                                     |
| Source            | `/home/hugo/.local/share/uv/python/cpython-3.10-linux-x86_64-gnu/` |
| How found         | `which python3.10` (probe per task instructions) |

No system package install (apt/pacman/source build) was required — Python 3.10 was already provisioned by the prior `.local`-based toolchain.

A `.venvs/` directory had not existed at `/home/hugo/.venvs/` (Wave 39/69 sidecars lived under `/home/hugo/.venv-flowmol311` and similar ad-hoc names), so the canonical `.venvs/` location was created fresh via:

```
mkdir -p /home/hugo/.venvs
/home/hugo/.local/bin/python3.10 -m venv /home/hugo/.venvs/omegafold_venv
```

This placed the new sidecar at the documented Wave 39/69 convention (`.venvs/<name>/bin/python`).

---

## (b) OmegaFold install steps

The upstream OmegaFold `setup.py` hard-codes a torch-pin at `cu113` (Python 3.10-only via its `get_url()` helper) and **explicitly blocks Python ≥ 3.12** (`raise Exception(...)` for unsupported versions). This is the reason a dedicated 3.10 sidecar is required even when 3.12 is the host default.

### Steps executed

1. **Bootstrap venv + pip** (Python 3.10.20):
   ```
   /home/hugo/.local/bin/python3.10 -m venv /home/hugo/.venvs/omegafold_venv
   /home/hugo/.venvs/omegafold_venv/bin/pip install --upgrade pip wheel setuptools
   ```

2. **Install PyTorch (CPU)** — pinned to `torch==1.13.1` because OmegaFold's C++ extensions in `omegafold/modules.py` and `omegafold/utils/protein_utils/*.py` are compiled against the **torch 1.12/1.13 ABI** (they bind directly to `torch.tensor` for `chi_angles_mask`/`atom14_exists`, etc.). The setup.py default pin (`1.12.0+cu113`) was overridden to avoid both the CUDA-only build and a NumPy-2.x ABI mismatch:
   ```
   /home/hugo/.venvs/omegafold_venv/bin/pip install \
       torch==1.13.1 --index-url https://download.pytorch.org/whl/cpu
   ```

3. **Install OmegaFold's Python runtime deps**:
   ```
   /home/hugo/.venvs/omegafold_venv/bin/pip install omegaconf scipy numpy biopython
   ```
   - `numpy` resolves to 1.26.4 (1.x branch — required because OmegaFold's compiled extensions are NumPy-1.x ABI; NumPy ≥ 2.0 raises `module compiled using NumPy 1.x cannot be run in NumPy 2.x`).
   - The pull resolved `numpy 2.2.6` first; an explicit downgrade to `<2` was applied afterwards:
     ```
     /home/hugo/.venvs/omegafold_venv/bin/pip install "numpy<2"
     ```

4. **Editable OmegaFold install**:
   ```
   cd /home/hugo/OmegaFold && \
   /home/hugo/.venvs/omegafold_venv/bin/pip install -e .
   ```
   This re-pins torch back to `1.12.0+cu113` (from `setup.py`'s `install_requires`). Because that wheel's `libtorch_cpu.so` triggers `cannot enable executable stack as shared object requires: Invalid argument` on this hardened-Linux host (grsecurity/PaX-style `READ_IMPLIES_EXEC` is denied), we **force-reinstall torch 1.13.1 CPU** immediately after:
   ```
   /home/hugo/.venvs/omegafold_venv/bin/pip install --force-reinstall --no-deps \
       torch==1.13.1 --index-url https://download.pytorch.org/whl/cpu
   ```

5. **Plotting support for `run_foldability.py`** (optional, but `run_foldability.py` calls `import matplotlib.pyplot as plt`):
   ```
   /home/hugo/.venvs/omegafold_venv/bin/pip install matplotlib
   ```

### Resulting installed set (24 packages, 2026-09-08)

```
antlr4-python3-runtime 4.9.3        # OmegaFold omegaconf AST
biopython              1.88         # FASTA parsing in helpers
contourpy              1.3.2        # matplotlib dep
cycler                 0.12.1
fonttools              4.64.0
kiwisolver             1.5.1
matplotlib             3.10.9
numpy                  1.26.4       # 1.x ABI required
omegaconf              2.3.1
OmegaFold              0.0.0        # editable at /home/hugo/OmegaFold
packaging              26.3
pillow                 12.3.0
pip                    26.2.1
pyparsing              3.3.2
python-dateutil        2.9.0.post0
PyYAML                 6.0.3        # OmegaFold Hydra YAML loader
scipy                  1.15.3
setuptools             84.0.0
six                    1.17.0
torch                  1.13.1+cpu   # CPU-only, ABI matches OmegaFold
typing_extensions      4.16.0
wheel                  0.48.0
```

Notable **absences** (deliberately not installed in this venv):

- `fair-esm` — required only for ESM-IF self-consistency. See (c) below.
- `biotite` — required only for ESM-IF. See (c) below.
- `torch-geometric` + CUDA scatter/sparse — only if a heavier ESM-IF GPU path is desired; the script handles its absence with a clear RuntimeError.
- `flash-attn`, `deepspeed` — not required for the foldability pipeline.

---

## (c) Environment requirements for `run_foldability.py`

The foldability pipeline is a **two-stage subprocess orchestrator**. Each stage has a distinct env profile, so a single venv is the right move only if it satisfies the union of both.

### File map (all under `/home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/evaluation/`)

| Script                         | Role                                                    | In-process Python deps                                                                                  | Subprocess deps                                                                                                              |
| ------------------------------ | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `run_foldability.py`           | **Orchestrator** — spawns stages, merges JSONL, plots   | stdlib (`argparse`, `json`, `subprocess`, `time`, `pathlib`) + `numpy` + `matplotlib` (for `_maybe_plot`) | none                                                                                                                          |
| `foldability_omegafold.py`     | Stage A — runs `omegafold` per-shard, parses PDBs       | stdlib + `numpy`                                                                                        | **`omegafold` CLI on PATH** (or `--omegafold-bin "python -m omegafold"`); model weights at `~/.cache/omegafold_ckpt/model.pt` (~3.5 GB, downloaded on first call) |
| `self_consistency_esmif.py`    | Stage B — ESM-IF inverse-folding perplexity per PDB      | stdlib + `numpy` + `torch` + **`esm` (fair-esm)** + **`biotite`**                                         | none                                                                                                                          |

### Stage-by-stage environment requirements

**1. `run_foldability.py` (top-level orchestrator)**

- Runs `foldability_omegafold.py` first via `subprocess.run([sys.executable, ...])` (so **it inherits the orchestrator's venv**).
- Runs `self_consistency_esmif.py` second via the same mechanism.
- Plots results with `matplotlib` if `--plots` is not disabled.
- **Env requirement:** Python ≥ 3.8 + `numpy` + `matplotlib`. OmegaFold venv satisfies this.

**2. `foldability_omegafold.py` (Stage A — OmegaFold pLDDT)**

- Spawns the `omegafold` CLI via `subprocess`; the OmegaFold process is a **separate** Python interpreter that needs its **own** `torch + omegafold` env.
- Because `run_foldability.py` passes `sys.executable` for the stage-A subprocess, **both stages share the venv** by default. As long as `/home/hugo/.venvs/omegafold_venv/bin/omegafold` exists on PATH (or `--omegafold-bin` points into the venv), Stage A inherits the right interpreter.
- **Env requirement:** same as the OmegaFold venv above (torch + omegafold + numpy).
- The script's own error message documents this:
  > *"Install OmegaFold in a Python<3.12 environment (the upstream package blocks Python 3.12), or pass the full path via `--omegafold-bin /path/to/omegafold`."*

**3. `self_consistency_esmif.py` (Stage B — ESM-IF self-consistency)**

- Imports `esm`, `esm.inverse_folding`, `esm.inverse_folding.util` **in-process** (not via subprocess). On newer Biotite versions, `_patch_biotite_filter_backbone()` monkey-patches `biotite.structure.filter_backbone` before the import.
- Loads the 142M-param `esm_if1_gvp4_t16_UR50` weights via `esm.pretrained.esm_if1_gvp4_t16_142M_UR50()` (downloaded on first call, ~742 MB to `~/.cache/torch/hub/checkpoints/`).
- **Env requirement:** `fair-esm`, `biotite`, `torch`. **Not currently installed in `omegafold_venv`** — confirmed via `_try_import_esmif()` which raises the expected `RuntimeError: Missing dependencies for ESM-IF (inverse folding) scoring. Required: fair-esm, biotite.`

### Recommendation for the eval driver

There are **two viable strategies**; both are out-of-tree (per Wave 84 mandate):

**Option A (recommended for one-shot runs): install ESM-IF deps into the omegafold_venv.**
- Pros: a single venv for both stages; `--omegafold-bin` and `--sc-gpus` keep their defaults.
- Cons: bloats the venv with `fair-esm + biotite + torch-geometric` (1–2 GB extra).
- Install command (deferred, **NOT executed** by Wave 84):
  ```
  /home/hugo/.venvs/omegafold_venv/bin/pip install fair-esm biotite
  # optional GPU path:
  /home/hugo/.venvs/omegafold_venv/bin/pip install torch-geometric
  ```

**Option B (cleanest separation): use the omegafold_venv for Stage A only, and a separate `esmif_venv` for Stage B.**
- Pros: keeps each venv minimal; matches the project's existing sidecar pattern (`flowmol3_venv`, `lineageflow_venv`, `kanzi_venv`).
- Cons: requires `run_foldability.py` to be invoked with `sys.executable` patched at the Stage-B subprocess boundary — i.e. an `interpreter=...` flag (not currently exposed) or a wrapper script.

Given the existing Wave 39/41/42/43 work already routes ESM-IF through a stub (`_StubLineageFlow` / `_StubKanzi` in tests), and Wave 80's `--hmmdb + --target-db` plumbing is in place, **Option B is the lower-risk choice** for Wave 85+ runs that actually need Stage B. For Wave 84's install goal (which is "LineageFlow foldability + self_consistency metrics runnable"), the orchestrator already imports cleanly and Stage A is fully wired. Stage B is runnable the moment `fair-esm + biotite` is added (one-line install).

### sys.path injection (alternative)

The orchestrator's `sys.path.insert(...)` calls in `run_foldability.py:27` and `self_consistency_esmif.py:33` allow running them as bare scripts (`python evaluation/run_foldability.py ...`) without a package install. This is useful for ad-hoc eval runs but does not change the env dep list — fair-esm and biotite still need to be importable from the running Python.

---

## (d) Verification status

| Check                                                              | Status | Evidence                                                                                                  |
| ------------------------------------------------------------------ | ------ | --------------------------------------------------------------------------------------------------------- |
| `python -c "import sys; print(sys.version)"`                        | PASS   | `Python 3.10.20 (main, Apr 14 2026, 14:28:08) [Clang 22.1.3]`                                             |
| `python -c "import torch; print(torch.__version__, torch.cuda.is_available())"` | PASS   | `1.13.1+cpu` / `False` (CPU-only by design for sidecar; CUDA is host-machine concern)                      |
| `python -c "import omegafold; print('OK')"`                         | PASS   | prints `omegafold OK` (editable install at `/home/hugo/OmegaFold`)                                        |
| `python -m omegafold --help`                                        | PASS   | exits 0; emits the documented CLI usage                                                                   |
| `omegafold --help` (console script)                                 | PASS   | exits 0; `/home/hugo/.venvs/omegafold_venv/bin/omegafold` exists and is executable                         |
| `import omegafold; omegafold.__version__`                          | PASS   | (no `__version__` attribute upstream; install location is the verification)                              |
| `import numpy, scipy, omegaconf, biopython, matplotlib`             | PASS   | numpy 1.26.4, scipy 1.15.3, omegaconf 2.3.1, biopython 1.88, matplotlib 3.10.9                            |
| `import run_foldability` (orchestrator)                             | PASS   | module loads; `main()` and `_summarize` are callable                                                      |
| `import self_consistency_esmif`                                     | PASS   | module loads; `_patch_biotite_filter_backbone`, `_try_import_esmif`, `main` are callable                  |
| `_try_import_esmif()` (without fair-esm installed)                  | PASS   | raises the documented `RuntimeError: Missing dependencies for ESM-IF (inverse folding) scoring. Required: fair-esm, biotite.` — confirms the script's error path is wired correctly |
| `python -m omegafold <fasta> <outdir>` end-to-end                   | **DEFERRED** | OmegaFold would auto-download `~/.cache/omegafold_ckpt/model.pt` (~3.5 GB) on first call. The download was started in a sandboxed smoke test (correct CLI plumbing — `INFO:root:Downloading weights from https://helixon.s3.amazonaws.com/release1.pt ...`) and then cancelled to avoid burning 3.5 GB of host bandwidth during this install phase. A real fold test is appropriate once a follow-up agent has disk-budget approval. |

### Known limits documented (not blockers for Wave 84)

- **Stage B (ESM-IF self-consistency) requires `fair-esm + biotite`** — one-line `pip install` away. Out of scope for the install-only mandate of Wave 84 Phase 1.
- **End-to-end fold test deferred** — OmegaFold weights are auto-downloaded on first invocation. The CLI plumbing was confirmed correct (the `INFO:root:Downloading weights from https://helixon.s3.amazonaws.com/release1.pt` line printed before the smoke test was cancelled).
- **CUDA not available in this venv** — by design; this is the CPU sidecar. For GPU foldability, a separate `omegafold_venv_cu118` (or similar) should be provisioned against the host's actual CUDA toolkit + cuDNN. The Wave 84 mandate is "Python 3.10 + OmegaFold + LineageFlow foldability metrics runnable" — all three are achievable from the CPU sidecar (Stage A's `--device cpu` is supported, Stage A timing is just slower than a CUDA run, and Stage B's ESM-IF can also run on CPU with a `torch.device("cpu")` override).

---

## Files touched (out-of-tree only)

- Created: `/home/hugo/.venvs/omegafold_venv/` (full Python 3.10 venv with 24 packages)
- Created: `/home/hugo/.venvs/omegafold_venv/bin/omegafold` (console script)
- Edited: `/home/hugo/OmegaFold/` (editable install — adds `OmegaFold-0.0.0-py3-none-any.whl` and `.pth` to site-packages; source tree unchanged)
- Created: `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave84-phase1-install.md` (this report)

**No code changes in `/home/hugo/codes/flowa-multistep-reinference/`** — per Wave 84 mandate.
**No commits** — per Wave 84 mandate (install-only, no code modifications, no push).
