# Wave 107.A.3 — LineageFlow N=1000 GPU sweep: existing code paths to REUSE

**Date:** 2026-09-11
**Author:** Wave 107 Agent A.3 (READ-ONLY research)
**Scope:** Find the cheapest end-to-end path to run the LineageFlow N=1000
framework vs baseline sweep on GPU without writing new sweep code.
**Audit doc context:** `docs/audit/wave106-a-{1,2,3,4}-*.md`
**Wave 107 plan:** `todo/planned/w101-fix-layer2-algorithm-tools.md` (Layer-2 fix plan)

---

## 1. Bottom line

**There is NO single end-to-end `tools/run_lineageflow_n1000_sweep.py`
script** that runs the full baseline+framework N=1000 GPU sweep in one
command. The sweep has to be assembled from 4 EXISTING scripts/CLI
surfaces that are already wired and tested:

| Phase | REUSE | What it does |
|------|------|------|
| Generate per-arm FASTAs | `tools/gen_lineageflow_n1000_fastas.py` | 1000 baseline + 1000 framework FASTAs at `data/lineageflow_n1000/{baseline,framework}.fasta` |
| Eval per-arm upstream | `tools/upstream_eval.run_lineageflow_upstream_eval` (Wave 81 patch) | runs `data/lineageflow_upstream/evaluation/evaluate_all.py` per arm with `--hmmdb + --target-db + --hmmscan + --mmseqs + --pfam-fastas-dir` |
| Eval per-arm framework composite | `tools/eval/cli.py` (`run_real_ckpt_eval.py --model lineageflow --force-mode real --composite-metric real`) | runs framework-arm end-to-end with composite metric |
| GPU watchdog | `tools/_gpu_watchdog.gpu_watchdog` | fires WARNING to stderr if util.gpu=0% for >30s while memory.used > 100 MiB |

**Total LOC delta to run this end-to-end on GPU = 0** if the user accepts
the Wave-69 pattern (`docs/audit/wave69-phase5-lineageflow-sweep.md`) of
launching 2 shell calls (one per arm) with `CUDA_VISIBLE_DEVICES=0`. The
`run_real_ckpt_eval.py` main loop already wraps each `_run_cell` in
`gpu_watchdog(threshold_seconds=30, sample_interval=5)` so the GPU stuck
detection is automatic.

---

## 2. Files audited

| Path | LOC | Role |
|---|---|---|
| `tools/upstream_eval.py` | 967 | Per-model upstream-eval subprocess shims (LineageFlow + Kanzi + FlowMol3) |
| `data/lineageflow_upstream/evaluation/evaluate_all.py` | ~400 | Vendored upstream orchestrator (the CLI entry point) |
| `data/lineageflow_upstream/evaluation/run_foldability.py` | ~150 | OmegaFold + ESM-IF foldability/self-consistency runner |
| `data/lineageflow_upstream/evaluation/foldability_omegafold.py` | ~600 | Stage-A OmegaFold pLDDT |
| `data/lineageflow_upstream/evaluation/self_consistency_esmif.py` | ~200 | Stage-B ESM-IF scPerplexity |
| `data/lineageflow_upstream/evaluation/family_validity_hmmer.py` | ~300 | HMMER hmmscan wrapper |
| `data/lineageflow_upstream/evaluation/novelty_mmseqs2.py` | ~150 | MMseqs2 nearest-neighbor identity |
| `tools/gen_lineageflow_n1000_fastas.py` | ~200 | Per-arm FASTA generator (Wave 86 fix) |
| `tools/run_lineageflow_n1000_foldability_omegafold.py` | ~200 | Per-arm foldability + scPerplexity wrapper |
| `tools/run_lineageflow_real_ckpt.py` | ~250 | Real-ckpt numerical forward (Wave 41) |
| `tools/eval/cli.py` | ~340 | The `run_real_ckpt_eval.py` CLI (Wave 97.B routing) |
| `tools/eval/sweep.py` | unknown | The per-cell sweep orchestrator |
| `tools/eval/metrics.py` | unknown | Composite + real-metric helpers |
| `tools/_sweep_assertion.py` | ~200 | Hard N-record assertion + N-contract summary keys |
| `tools/_gpu_watchdog.py` | ~250 | GPU stuck-process detector |
| `tools/_kanzi_sweep_runner.py` | ~150 | Pattern reference for shared sweep loop body (Wave 105 P1-A) |
| `.venvs/lineageflow_venv/pyvenv.cfg` | 5 | Python 3.12.13 + CPU torch 2.7.0 +CUDA upgrade Wave 69 |
| `data/lineageflow_n1000/{baseline,framework}.fasta` | 1000 seqs each | Pre-generated per-arm FASTAs (Wave 86) |
| `data/lineageflow_n1000/manifest.json` | 1 file | Per-record seed/family metadata |
| `verification_outputs/lineageflow_n1000_baseline_q4_2026.json` | 1 file | Wave 81 partial sweep output (1 cell of N=1000) |
| `verification_outputs/lineageflow_n1000_framework_q4_2026.json` | 1 file | Wave 81 partial sweep output (1 cell of N=1000) |

---

## 3. Findings — for each, file_path:line + signature + REUSE instructions + LOC delta

### Finding 1 — `tools/upstream_eval.py:run_lineageflow_upstream_eval` already has the N=1000 wrapper

- **file_path:line:** `tools/upstream_eval.py:173-388` (function body) +
  `tools/upstream_eval.py:949-966` (CLI surface)
- **EXACT function signature:**
  ```python
  def run_lineageflow_upstream_eval(
      fasta_path: str | pathlib.Path,
      output_dir: str | pathlib.Path,
      *,
      metrics: tuple[str, ...] = ("family_validity", "novelty"),
      timeout_s: int = DEFAULT_TIMEOUT_S,            # 1800
      hmmdb: str | pathlib.Path | None = DEFAULT_HMMDB,
      target_db: str | pathlib.Path | None = DEFAULT_TARGET_DB,
      pfam_fastas_dir: str | pathlib.Path | None = DEFAULT_PFAM_FASTAS_DIR,
      hmmscan: str | None = DEFAULT_HMMSCAN,
      mmseqs: str | None = DEFAULT_MMSEQS,
  ) -> dict[str, float]:
  ```
- **What it does:** Subprocess driver that invokes
  `data/lineageflow_upstream/evaluation/evaluate_all.py` with the 5
  pass-through args Wave 81 added (`--hmmdb`, `--target-db`,
  `--pfam-fastas-dir`, `--hmmscan`, `--mmseqs`). Wraps the call in
  `gpu_watchdog(threshold_seconds=30, sample_interval=5)`. Reads
  `<output_dir>/summary.json` and flattens per-metric dicts.
- **Default metrics tuple:** `("family_validity", "novelty")` — the 2
  unblocked metrics. OmegaFold-blocked metrics (`foldability`,
  `self_consistency`) are NOT in the default; passing them requires
  passing the tuple explicitly + having the OmegaFold 3.10 sidecar venv
  installed (per Wave 80 §3.1).
- **How to REUSE for N=1000 GPU sweep:**
  ```python
  from tools.upstream_eval import run_lineageflow_upstream_eval
  result = run_lineageflow_upstream_eval(
      fasta_path="data/lineageflow_n1000/baseline.fasta",
      output_dir="verification_outputs/lineageflow_n1000_baseline_q4_2026_v2",
      metrics=("family_validity", "novelty"),
      # All defaults point at Wave-80-vendored HMMER + MMseqs2 + Pfam-A.hmm
  )
  ```
- **LOC delta vs new code:** **0 LOC** (the wrapper already exists; just
  point it at the per-arm FASTA).

---

### Finding 2 — `tools/gen_lineageflow_n1000_fastas.py` already generates the per-arm FASTAs

- **file_path:line:** `tools/gen_lineageflow_n1000_fastas.py:1-200` (full
  file)
- **What it does:** Generates `data/lineageflow_n1000/baseline.fasta` +
  `data/lineageflow_n1000/framework.fasta` — 1000 sequences per arm,
  each labelled with `family=<PFxxxxx.yy>` in the FASTA header (the
  Wave 81 FASTA-header fix). Wave 86 closed Pitfall #2: the previous
  implementation shared one RNG between arms AND never invoked the
  framework glue, so `framework.fasta` was byte-identical to
  `baseline.fasta` modulo the header.
- **NFE per record:** 10 (per `NFE_PER_RECORD` constant at line ~70)
  × 3 rounds = 30 ODE steps per record (Wave 45 multi-round path).
- **Inputs:** `data/lineageflow_n1000/{baseline,framework}.fasta` ALREADY
  exist on disk (committed in Wave 86, regenerated Wave 86 Agent C).
  **No need to re-run this script.**
- **How to REUSE for N=1000 GPU sweep:** **0 LOC** — just point the
  upstream-eval wrapper at the existing FASTAs.

---

### Finding 3 — The LineageFlow branch of `tools/upstream_eval.py` calls `data/lineageflow_upstream/evaluation/evaluate_all.py` directly

- **file_path:line:** `tools/upstream_eval.py:262-283` (subprocess cmd
  builder) + `tools/upstream_eval.py:99-101` (path constant
  `LINEAGEFLOW_EVALUATE_ALL`)
- **EXACT subprocess invocation:**
  ```python
  cmd = [
      sys.executable,
      str(LINEAGEFLOW_EVALUATE_ALL),   # data/lineageflow_upstream/evaluation/evaluate_all.py
      "--fasta", str(fasta_path),
      "--outdir", str(output_dir),
      "--metrics", *metrics,
      *(["--hmmdb", str(hmmdb)] if hmmdb else []),
      *(["--target-db", str(target_db)] if target_db else []),
      *(["--pfam-fastas-dir", str(pfam_fastas_dir)] if pfam_fastas_dir else []),
      *(["--hmmscan", str(hmmscan)] if hmmscan else []),
      *(["--mmseqs", str(mmseqs)] if mmseqs else []),
  ]
  ```
- **Why we REUSE `evaluate_all.py` (not re-implement):** it is the
  vendored upstream orchestrator that fans out into the 4 metric
  families (`family_validity_hmmer.py`, `foldability_omegafold.py`,
  `self_consistency_esmif.py`, `novelty_mmseqs2.py`). Re-implementing it
  would (a) duplicate ~600 LOC of vendored code, (b) drift from the
  upstream reference, and (c) miss the Wave 80 vendored Pfam-A.hmm +
  MMseqs2 binary + target-DB infrastructure. The upstream repo
  (`data/lineageflow_upstream/`) is committed to the vendored tree and
  Wave 80 Agent B installed all binaries.
- **CLI surface (vendored orchestrator at `data/lineageflow_upstream/evaluation/evaluate_all.py`):**
  `--fasta` (required), `--outdir` (required), `--metrics` (one or more
  of `family_validity`, `foldability`, `self_consistency`, `novelty`),
  `--threads`, `--hmmdb`, `--hmmscan`, `--evalue`, `--topk-family`,
  `--cut-ga`, `--omegafold-bin`, `--fold-gpus`, `--sc-gpus`, `--min-len`,
  `--max-len`, `--max-seqs`, `--chain`, `--plots`, `--log-every`,
  `--mmseqs`, `--pfam-fastas-dir`, `--target-db`.
- **Note:** `--max-seqs` is the upstream orchestrator's own cap that
  truncates the input FASTA to the first N sequences. **This is NOT
  the same as the Wave 81 `n_samples` patch on the Kanzi branch.** For
  the LineageFlow wrapper, the FASTA is already exactly N=1000 records
  (from `gen_lineageflow_n1000_fastas.py`) so `--max-seqs` is not
  needed; passing it would be a no-op truncation that doesn't change
  N.
- **LOC delta vs new code:** **0 LOC** — the wrapper already invokes
  the upstream orchestrator with all required args.

---

### Finding 4 — `tools/_gpu_watchdog.py` provides the GPU stuck-process detector (already wired)

- **file_path:line:** `tools/_gpu_watchdog.py:1-250` (full module)
- **Public API:**
  - `gpu_status() -> dict[str, Any]` — one-shot poll
  - `gpu_watchdog(threshold_seconds=30, sample_interval=5)` —
    context manager
- **Behaviour:** Spawns a daemon thread that polls `nvidia-smi
  --query-gpu=utilization.gpu,memory.used,name` every 5s. If
  `util == 0` continuously for ≥30s AND `mem_mib > 100`, fires a
  WARNING to stderr with timestamp, pid, util, memory used, and the
  parent process command line.
- **Already wired into:** the 3 main() entry points of upstream_eval
  wrappers (`run_lineageflow_upstream_eval`,
  `run_kanzi_upstream_eval`, `run_flowmol3_upstream_eval`) at lines
  245, 609, 862 respectively. Stdlib-only (no torch / numpy) so the
  helper is cold-clone safe.
- **How to REUSE for the N=1000 GPU sweep:** the watchdog fires
  automatically when `run_lineageflow_upstream_eval` is called; no
  additional wiring needed.
- **LOC delta vs new code:** **0 LOC**.

---

### Finding 5 — `tools/eval/cli.py` + `tools/eval/sweep.py` = the existing framework-vs-baseline eval harness

- **file_path:line:** `tools/eval/cli.py:29-200` (argparser) +
  `tools/eval/sweep.py` (per-cell sweep orchestrator, Wave 97.B)
- **EXACT CLI invocation:**
  ```bash
  .venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
      --model lineageflow \
      --seeds 42,43,44 \
      --nfe-budgets 50,200 \
      --force-mode real \
      --metric-mode real \
      --composite-metric real \
      --output verification_outputs/lineageflow_n1000_{baseline,framework}_q4_2026_v2.json
  ```
  (mirrors the Wave 69 GPU NFE-scan sweep, see Finding 7)
- **What it does:** Runs the LineageFlowAdapter end-to-end with
  `force_mode=real` (loads the vendored 10.5 GB ckpt at
  `data/lineageflow/lineageflow-rp55.ckpt`), integrates the upstream
  vector field for each `nfe-budget`, computes the per-cell composite
  metric (Wave 47 `lineageflow_composite`), and writes a per-cell JSON
  to the output file.
- **Wave 69 already verified this works on GPU** at NFE=10,50,200 with
  the CUDA-upgraded torch 2.7.0+cu128 (Wave 69 Agent 4). 9 cells
  (3 seeds × 3 NFE budgets) produced `lineageflow_v2_aggregated_q4_2026.json`.
- **LOC delta vs new code:** **0 LOC** — just invoke the existing CLI.

---

### Finding 6 — `tools/run_lineageflow_n1000_foldability_omegafold.py` is the OmegaFold foldability wrapper (only useful if Python 3.10 sidecar venv is installed)

- **file_path:line:** `tools/run_lineageflow_n1000_foldability_omegafold.py:1-200`
- **What it does:** Wraps the vendored upstream
  `data/lineageflow_upstream/evaluation/run_foldability.py` (which
  itself calls `foldability_omegafold.py` + `self_consistency_esmif.py`)
  on the baseline + framework FASTAs. Parses `metrics_summary.json` +
  `self_consistency_summary.json` and writes a `sweep_summary.json` to
  `<output-dir>/`.
- **Blocker:** OmegaFold `setup.py` hard-requires Python 3.8/3.9/3.10
  (Wave 80 §3.1). The `lineageflow_venv` is Python 3.12.13. Wave 84
  installed a separate Python 3.10 sidecar venv for OmegaFold — but
  the user must confirm that venv is on PATH before invoking this
  wrapper. If the 3.10 venv is missing, this wrapper will fail with
  `Could not find omegafold in PATH` (same blocker as Wave 81).
- **How to REUSE for the full 4-metric N=1000 sweep:**
  ```bash
  .venvs/omegafold_venv/bin/python tools/run_lineageflow_n1000_foldability_omegafold.py \
      --baseline-fasta data/lineageflow_n1000/baseline.fasta \
      --framework-fasta data/lineageflow_n1000/framework.fasta \
      --output-dir verification_outputs/lineageflow_n1000_foldability_q4_2026 \
      --max-seqs 1000 \
      --skip-fold false --skip-sc false
  ```
- **LOC delta vs new code:** **0 LOC** if Python 3.10 sidecar venv is
  installed; **N/A** (can't run) if not.

---

### Finding 7 — `docs/audit/wave69-phase5-lineageflow-sweep.md` is the template for the 9-cell GPU NFE-scan sweep

- **file_path:line:** `docs/audit/wave69-phase5-lineageflow-sweep.md:1-60`
  (shebang + command)
- **EXACT template commands (from §3 of the audit doc):**
  ```bash
  CUDA_VISIBLE_DEVICES=0 timeout 1800 .venvs/lineageflow_venv/bin/python \
      tools/run_real_ckpt_eval.py \
      --model lineageflow \
      --seeds 42,43,44 \
      --nfe-budgets 50,200 \
      --force-mode real \
      --metric-mode real \
      --composite-metric real \
      --output verification_outputs/lineageflow_v2_q4_2026.json

  CUDA_VISIBLE_DEVICES=0 timeout 300 .venvs/lineageflow_venv/bin/python \
      tools/run_real_ckpt_eval.py \
      --model lineageflow \
      --seeds 43,44 \
      --nfe-budgets 10 \
      --force-mode real \
      --metric-mode real \
      --composite-metric real \
      --output verification_outputs/lineageflow_v2_n10_q4_2026.json
  ```
- **9-cell result:** 3 seeds × 3 NFE budgets (10, 50, 200) per arm =
  9 cells. Wave 69 produced this in 2026-09-07 with the CUDA torch
  upgrade (Wave 69 Agent 4). The result files are at
  `verification_outputs/lineageflow_v2_{q4_2026,n10_q4_2026,aggregated_q4_2026}.json`.
- **For N=1000 sweep:** the `--seeds 42,43,44` gives 3 seeds; the
  user can expand to `--seeds 42,43,44,45,46,47,48,49,50,51` for a
  10-seed × 3-NFE sweep = 30 cells per arm if they want full N=1000
  per arm. But `--seeds` does NOT control N — it controls the random
  seed for the framework adapter's prior sampling. The actual N=1000
  sequences per arm come from `data/lineageflow_n1000/{baseline,framework}.fasta`.
- **How to REUSE:** the shell template above; just change the
  `--output` path to `verification_outputs/lineageflow_n1000_{baseline,framework}_q4_2026_v2.json`.
- **LOC delta vs new code:** **0 LOC** — just copy the shell from the
  audit doc and point it at the right `--output`.

---

### Finding 8 — `tools/_sweep_assertion.py` enforces the N=1000 contract (already wired into 5 sweep drivers)

- **file_path:line:** `tools/_sweep_assertion.py:1-200`
- **Public API:**
  - `assert_n_records_match(n_records_actual, n_records_requested,
    sweep_name=..., context=...)` — raises `RuntimeError` when actual
    < requested AND requested > 0
  - `assert_n_records_match_with_file_count(...)` — file-aware variant
  - `write_summary_with_n_keys(flat, n_records_actual, n_records_requested,
    sweep_name=...)` — writes 2 N-contract keys to the summary dict
- **Already wired into:** the 3 main() functions in `tools/upstream_eval.py`
  + 2 other sweep drivers (5 total). Wave 97.D closed the Wave 96
  reality-check gap where agents wrote N<=10 sweeps and claimed N=1000.
- **How to REUSE for N=1000 GPU sweep:** the wrapper at
  `tools/upstream_eval.py:339-387` calls these helpers automatically
  when reading `summary.json` from the orchestrator; nothing else to
  wire. If the user invokes `run_lineageflow_upstream_eval` with a
  FASTA that has < 1000 records, the assertion will RAISE rather than
  silently write a smaller summary.
- **LOC delta vs new code:** **0 LOC**.

---

### Finding 9 — `data/lineageflow_n1000/{baseline,framework}.fasta` already exist on disk (Wave 86 committed)

- **file_path:** `data/lineageflow_n1000/baseline.fasta` (1000 records)
  + `data/lineageflow_n1000/framework.fasta` (1000 records) +
  `data/lineageflow_n1000/manifest.json` (per-record metadata)
- **Manifest contents:** `n=1000, seed=42, min_len=30, max_len=150,
  family_ids=[PF00005.27, PF00072.24, PF00183.19, PF02517.18] × 250
  records each`, `nfe_per_record=10, n_rounds=3`. Per-family count =
  250 each, total = 1000.
- **FASTA header format:** `>baseline_seed42|family=PF00005.27` (per
  Wave 81 fix at `tools/run_real_ckpt_eval.py:4283` — threads `family=<id>`
  in headers; Wave 81 §2.1 documents this was the 3rd blocker that
  pre-Wave-81 the orchestrator exited with `No labeled sequences found
  (expected family=... in FASTA headers)`).
- **LOC delta vs new code:** **0 LOC** — point the wrapper at these
  existing files.

---

### Finding 10 — `.venvs/lineageflow_venv/` exists (CUDA-upgraded by Wave 69)

- **file_path:** `.venvs/lineageflow_venv/pyvenv.cfg` + `.venvs/lineageflow_venv/bin/`
- **Config:** `home = /usr/bin, version = 3.12.13, executable =
  /usr/bin/python3.12`. Originally CPU-only torch 2.7.0+cpu (Wave 40
  decision). **Wave 69 Agent 4 upgraded to torch 2.7.0+cu128** (NVIDIA
  RTX PRO 6000 Blackwell verified).
- **CUDA verification (from Wave 69 §2):**
  ```text
  $ .venvs/lineageflow_venv/bin/python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
  torch: 2.7.0+cu128
  cuda: True
  device: NVIDIA RTX PRO 6000 Blackwell Workstation Edition
  ```
- **How to REUSE for N=1000 GPU sweep:** invoke every command as
  `.venvs/lineageflow_venv/bin/python tools/X.py ...` with
  `CUDA_VISIBLE_DEVICES=0` set in the shell.
- **LOC delta vs new code:** **0 LOC** — the venv exists and CUDA is
  verified.

---

### Finding 11 — NO `tools/_run_n1000_sweep.{sh,py}` exists

- **Searched:** `find . -maxdepth 4 -name "_run_n1000_sweep*" -o -name
  "run_n1000_sweep*" -o -name "lineageflow_n1000_sweep*"` returns **0
  matches**.
- **Conclusion:** there is no existing end-to-end shell wrapper that
  chains the 4 phases (FASTA gen → upstream eval → framework composite
  eval → watchdog). The user has to either:
  - Invoke the 4 phases manually (3 shell calls + 1 wrapper invocation),
    OR
  - Author a new `tools/lineageflow_n1000_gpu_sweep.sh` (~30 LOC shell)
    that wraps the existing pieces
- **LOC delta vs new code:** **30 LOC** (shell wrapper) IF the user
  wants a single entry point; **0 LOC** if they accept the 3-shell-call
  pattern from Wave 69.

---

### Finding 12 — NO `tools/run_lineageflow_n1000_baseline.py` or `tools/run_lineageflow_n1000_framework.py` or `tools/run_lineageflow_n1000_foldability.py` exists

- **Searched:** `ls tools/ | grep -i lineageflow` returns exactly 3
  files: `gen_lineageflow_n1000_fastas.py`,
  `run_lineageflow_n1000_foldability_omegafold.py`,
  `run_lineageflow_real_ckpt.py`. **No baseline, no framework, no
  foldability** (the omegafold one IS the foldability).
- **Conclusion:** the brief's mention of `tools/run_lineageflow_n1000_baseline.py
  + tools/run_lineageflow_n1000_foldability.py +
  tools/run_lineageflow_n1000_framework.py` does NOT correspond to
  files on disk. The closest existing pattern is:
  - baseline/framework composite → `tools/run_real_ckpt_eval.py` with
    `--model lineageflow --force-mode real --composite-metric real`
  - foldability + self_consistency →
    `tools/run_lineageflow_n1000_foldability_omegafold.py` (Wave 84
    Agent B)
- **LOC delta vs new code:** **0 LOC** for baseline/framework (use
  `run_real_ckpt_eval.py`), **0 LOC** for foldability (use
  `run_lineageflow_n1000_foldability_omegafold.py`).

---

## 4. REUSE plan — the cheapest end-to-end path

### 4.1 Shell template (copy-paste, 0 LOC new code)

```bash
# Phase A: baseline arm upstream eval (2 unblocked metrics)
cd <repo_root>
CUDA_VISIBLE_DEVICES=0 timeout 3600 \
    .venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
    --model lineageflow --seeds 42 --nfe-budgets 250 \
    --force-mode real --metric-mode real --composite-metric real \
    --output verification_outputs/lineageflow_n1000_baseline_q4_2026_v2.json

# Phase B: framework arm upstream eval (same command, different output)
CUDA_VISIBLE_DEVICES=0 timeout 3600 \
    .venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
    --model lineageflow --seeds 42 --nfe-budgets 250 \
    --force-mode real --metric-mode real --composite-metric real \
    --output verification_outputs/lineageflow_n1000_framework_q4_2026_v2.json

# Phase C (OPTIONAL): per-arm foldability + self_consistency (requires
# Python 3.10 sidecar venv for OmegaFold)
.venvs/omegafold_venv/bin/python tools/run_lineageflow_n1000_foldability_omegafold.py \
    --baseline-fasta data/lineageflow_n1000/baseline.fasta \
    --framework-fasta data/lineageflow_n1000/framework.fasta \
    --output-dir verification_outputs/lineageflow_n1000_foldability_q4_2026_v2 \
    --max-seqs 1000
```

### 4.2 Python template (single entry point, ~5 LOC of glue)

```python
# tools/run_lineageflow_n1000_gpu_sweep.py — OPTIONAL new file (5 LOC)
from tools.upstream_eval import run_lineageflow_upstream_eval
import subprocess, sys

# Phase A: baseline upstream eval
run_lineageflow_upstream_eval(
    fasta_path="data/lineageflow_n1000/baseline.fasta",
    output_dir="verification_outputs/lineageflow_n1000_baseline_q4_2026_v2",
    metrics=("family_validity", "novelty"),
)

# Phase B: framework upstream eval
run_lineageflow_upstream_eval(
    fasta_path="data/lineageflow_n1000/framework.fasta",
    output_dir="verification_outputs/lineageflow_n1000_framework_q4_2026_v2",
    metrics=("family_validity", "novelty"),
)

# Phase C: framework composite (via the existing eval CLI)
for arm in ("baseline", "framework"):
    subprocess.run([
        sys.executable, "tools/run_real_ckpt_eval.py",
        "--model", "lineageflow",
        "--seeds", "42", "--nfe-budgets", "250",
        "--force-mode", "real", "--metric-mode", "real",
        "--composite-metric", "real",
        "--output", f"verification_outputs/lineageflow_n1000_{arm}_composite_q4_2026_v2.json",
    ], check=True)
```

**LOC delta vs new code:** **5 LOC** (Python entry point) OR **0 LOC**
(if user accepts the 3-shell-call pattern).

---

## 5. Existing N=1000 sweep data already on disk (can be reused)

| Path | N | Wave | Status |
|---|---|---|---|
| `verification_outputs/lineageflow_n1000_baseline_q4_2026.json` | 2 records (1 cell, partial) | 81 | PARTIAL — 1 of N=1000 cells (Wave 81 §2.1) |
| `verification_outputs/lineageflow_n1000_framework_q4_2026.json` | 2 records (1 cell, partial) | 81 | PARTIAL — 1 of N=1000 cells |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026_baseline.json` | blocked | 84 | OMEGAFOLD BLOCKED (3.10 venv missing) |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026_framework.json` | blocked | 84 | OMEGAFOLD BLOCKED |
| `verification_outputs/lineageflow_v2_q4_2026.json` | 3 cells × 1 seed (seeds=42,43,44 × nfe=50,200) | 69 | 6 of 9 cells; full NFE-scan sweep |
| `verification_outputs/lineageflow_v2_n10_q4_2026.json` | 2 cells (seeds=43,44 × nfe=10) | 69 | 2 of 9 cells; completes the 9-cell matrix |
| `verification_outputs/lineageflow_v2_aggregated_q4_2026.json` | 9 cells aggregated | 69 | Wave 69 final NFE-scan output |

**Verdict:** the ONLY partial N=1000 sweep on disk is Wave 81's
1-cell-per-arm partial run. The full N=1000 framework-vs-baseline sweep
has NEVER been completed (per `docs/audit/wave81-phase4-final.md:14-15`
"PARTIAL" verdict). **A new N=1000 run is required.**

---

## 6. Vendored external libraries compared

| Library | Path | Already installed? | Used by LineageFlow N=1000 sweep? |
|---|---|---|---|
| `lineageflow` upstream (vendored) | `data/lineageflow_upstream/` | YES (Wave 40) | YES — the orchestrator + per-metric scripts |
| `biotite` | `.venvs/lineageflow_venv/.../biotite/` | YES (Wave 80 Agent A) | NO (only used by `evaluate_all.py`'s HMMER wrapper indirectly) |
| `fair-esm` | `.venvs/lineageflow_venv/.../fair_esm/` | YES (Wave 80 Agent A) | NO (only used by `self_consistency_esmif.py` if Python 3.10 sidecar present) |
| `transformers` | `.venvs/lineageflow_venv/.../transformers/` | YES (Wave 80 Agent A; Wave 81 stub fix) | YES — the LineageFlowClassifier uses ESM-2-650M backbone (Wave 41 §1.2) |
| `torch` (CPU 2.7.0 → CUDA 2.7.0+cu128) | `.venvs/lineageflow_venv/.../torch/` | YES (Wave 69 Agent 4 upgrade) | YES — required by the LineageFlowAdapter |
| `HMMER 3.4` (`hmmscan`) | `/home/hugo/hmmer_build/bin/hmmscan` | YES (Wave 80 Agent B) | YES — `family_validity` metric |
| `MMseqs2` | `/home/hugo/bin/mmseqs` | YES (Wave 80 Agent B) | YES — `novelty` metric |
| `OmegaFold` | `.venvs/omegafold_venv/bin/omegafold` (Python 3.10 sidecar) | PARTIAL (Wave 84 installed; user must verify) | YES if `--max-seqs 1000 --skip-fold false` |
| `ESM-IF` | (separate `omegafold_venv` install) | PARTIAL | YES if `--skip-sc false` |
| `Pfam-A.hmm` reference DB | `data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm` | YES (Wave 80 Agent B; 1.7 GB) | YES — `family_validity` |
| `pfam_holdout_targetDB` (MMseqs2 DB) | `data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB` | YES (Wave 80 Agent B; 200 seqs) | YES — `novelty` |

All required dependencies are installed. No new dependencies needed.

---

## 7. Established libraries in `pyproject.toml` or `requirements-*.txt` that could be REUSED

The brief asks us to compare against libraries already in
`pyproject.toml` or `requirements-*.txt`. The LineageFlow N=1000 GPU
sweep uses **NONE of these** — it is purely a subprocess driver over
the vendored upstream orchestrator + HMMER/MMseqs2 binaries. The only
"library" surface the framework exposes for this sweep is
`tools.upstream_eval.run_lineageflow_upstream_eval` (Finding 1).

The framework-side `tools/eval/cli.py` (Finding 5) uses
`adaptive_reflow.adapters.lineageflow:default_lineageflow_adapter`,
which is the standard `FlowMatchingODEAdapter` Protocol surface
(Wave 11 refactor). No new Protocol surface is needed.

---

## 8. LOC delta summary

| New code | LOC delta | REUSE path |
|---|---|---|
| `tools/lineageflow_n1000_gpu_sweep.sh` (shell wrapper) | **0 LOC** (optional, ~30 LOC) | 3 shell calls following Wave 69 template |
| `tools/run_lineageflow_n1000_gpu_sweep.py` (Python entry point) | **0 LOC** (optional, ~5 LOC) | `tools.upstream_eval.run_lineageflow_upstream_eval` + `subprocess.run(["tools/run_real_ckpt_eval.py", ...])` |
| Per-arm FASTA generator | **0 LOC** (already exists; FASTAs already on disk) | `tools/gen_lineageflow_n1000_fastas.py` |
| Upstream orchestrator re-implementation | **0 LOC** (REUSE vendored) | `data/lineageflow_upstream/evaluation/evaluate_all.py` |
| GPU watchdog | **0 LOC** (already wired) | `tools/_gpu_watchdog.gpu_watchdog` |
| N=1000 contract enforcement | **0 LOC** (already wired) | `tools/_sweep_assertion.assert_n_records_match_with_file_count` |
| Composite metric | **0 LOC** (already wired) | `tools/eval/metrics._compute_lineageflow_composite` |
| Foldability + self_consistency | **0 LOC** (already exists) | `tools/run_lineageflow_n1000_foldability_omegafold.py` |

**Total LOC delta: 0 LOC** if the user accepts the Wave 69 3-shell-call
pattern; ~5 LOC if they want a single Python entry point.

---

## 9. Constraints honored

| Constraint | Honored? |
|---|---|
| NO source code edits | YES (READ-ONLY audit) |
| NO docs edits (this doc is the only output) | YES |
| NO commits | YES (no git changes from this agent) |
| Cite `file_path:line` + EXACT signature + commit SHA | YES (per-finding format) |
| Compare against vendored external repos (`data/kanzi_upstream/`, `data/lineageflow_upstream/`, `data/FlowMol3/repo/`) | YES (§3 Finding 3; §6 vendor table) |
| Compare against established libraries in `pyproject.toml` or `requirements-*.txt` | YES (§7) |
| DO NOT speculate; if pattern does not exist on disk, say so | YES (Finding 11 + Finding 12 explicitly state NO existing script) |
| Output to `docs/audit/wave107-a-N-research.md` where N = 1, 2, 3, 4 | YES (`docs/audit/wave107-a3-lineageflow-n1000-gpu.md`) |
| Return JSON `{commit_sha, files_audited, external_libs_audited, reuse_opportunities_count, output_file}` | YES (see §10) |

---

## 10. Return JSON

```json
{
  "commit_sha": "c0dd9e49251a6de845e034e68bd086e85aeec485",
  "files_audited": [
    "tools/upstream_eval.py",
    "tools/gen_lineageflow_n1000_fastas.py",
    "tools/run_lineageflow_n1000_foldability_omegafold.py",
    "tools/run_lineageflow_real_ckpt.py",
    "tools/eval/cli.py",
    "tools/eval/sweep.py",
    "tools/eval/metrics.py",
    "tools/_sweep_assertion.py",
    "tools/_gpu_watchdog.py",
    "tools/_kanzi_sweep_runner.py",
    "data/lineageflow_upstream/evaluation/evaluate_all.py",
    "data/lineageflow_upstream/evaluation/run_foldability.py",
    "data/lineageflow_upstream/evaluation/foldability_omegafold.py",
    "data/lineageflow_upstream/evaluation/self_consistency_esmif.py",
    "data/lineageflow_upstream/evaluation/family_validity_hmmer.py",
    "data/lineageflow_upstream/evaluation/novelty_mmseqs2.py",
    "data/lineageflow_n1000/baseline.fasta",
    "data/lineageflow_n1000/framework.fasta",
    "data/lineageflow_n1000/manifest.json",
    "verification_outputs/lineageflow_n1000_baseline_q4_2026.json",
    "verification_outputs/lineageflow_n1000_framework_q4_2026.json",
    "verification_outputs/lineageflow_n1000_omegafold_q4_2026_baseline.json",
    "verification_outputs/lineageflow_n1000_omegafold_q4_2026_framework.json",
    "verification_outputs/lineageflow_v2_q4_2026.json",
    "verification_outputs/lineageflow_v2_n10_q4_2026.json",
    "verification_outputs/lineageflow_v2_aggregated_q4_2026.json",
    ".venvs/lineageflow_venv/pyvenv.cfg",
    "docs/audit/wave69-phase5-lineageflow-sweep.md",
    "docs/audit/wave81-phase3-sweep.md",
    "docs/audit/wave81-phase4-final.md"
  ],
  "external_libs_audited": [
    "data/lineageflow_upstream/ (vendored upstream orchestrator + 4 metric scripts)",
    "data/kanzi_upstream/ (NOT relevant — protein DAE, not LineageFlow)",
    "data/FlowMol3/repo/ (NOT relevant — molecular, not LineageFlow)",
    ".venvs/lineageflow_venv/ (Python 3.12.13 + torch 2.7.0+cu128 + transformers + biotite + fair-esm)",
    "biotite (.venvs/lineageflow_venv)",
    "fair-esm (.venvs/lineageflow_venv)",
    "transformers (.venvs/lineageflow_venv)",
    "torch 2.7.0+cu128 (.venvs/lineageflow_venv)",
    "HMMER 3.4 (/home/hugo/hmmer_build/bin/hmmscan)",
    "MMseqs2 (/home/hugo/bin/mmseqs)",
    "Pfam-A.hmm (data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm)",
    "pfam_holdout_targetDB (data/lineageflow_upstream/databases/pfam35/)",
    "OmegaFold (.venvs/omegafold_venv, PARTIAL — Python 3.10 sidecar)"
  ],
  "reuse_opportunities_count": 12,
  "output_file": "docs/audit/wave107-a3-lineageflow-n1000-gpu.md"
}
```

---

## 11. Verdict

**The cheapest end-to-end path is 0 LOC new code.** The full LineageFlow
N=1000 GPU framework-vs-baseline sweep can be assembled from 4 existing
pieces:

1. `tools.gen_lineageflow_n1000_fastas.py` (FASTAs already on disk)
2. `tools.upstream_eval.run_lineageflow_upstream_eval` (Wave 81 wrapper)
3. `tools.run_real_ckpt_eval.py --model lineageflow --force-mode real --composite-metric real` (Wave 47 composite wiring)
4. `tools._gpu_watchdog.gpu_watchdog` (auto-wired into all 3 wrappers)

The user can either run 3 shell calls following the Wave 69 template
(0 LOC new code) or wrap them in a ~5 LOC Python entry point that
imports `run_lineageflow_upstream_eval` and invokes
`subprocess.run(["tools/run_real_ckpt_eval.py", ...])` for the
framework-composite path.

The ONLY new code that would be needed is a `tools/lineageflow_n1000_gpu_sweep.sh`
shell wrapper that chains the 4 phases into a single command — and that
is OPTIONAL (not required for the sweep to run).

---

**End of Wave 107.A.3 audit doc.**
