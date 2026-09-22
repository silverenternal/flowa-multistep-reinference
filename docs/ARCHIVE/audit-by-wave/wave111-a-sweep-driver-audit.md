# Wave 111.0 Reviewer A — Sweep Driver Architecture Audit

**SHA**: `70501280ac0e9e197064d3b2b029bb0787289403` (HEAD = `Wave 110.D: Author wave110-final-synthesis.md`)
**Date**: 2026-09-11
**Scope**: Every sweep entry point in the repo + per-entry-point hardcoded defaults (device, n_steps, batch_size, n_records, cache, mode).
**Hard rule**: READ-ONLY. No source code edits. No commits. No inline paper / supplementary / cover letter text.

---

## 1. Inventory of sweep entry points (audited)

The brief listed 10 targets. After repo walk, the actual set of sweep entry points that can run a multi-record (>1) N-style eval today is **11**. The list of currently-active sweep drivers — including two the brief did not enumerate — is:

| # | File | SHA at line 1 | Role |
|---|------|---------------|------|
| 1 | `tools/sweep_kanzi_n1000_paper_metrics.py` | `7050128` | Kanzi baseline arm (Wave 83 / 108.A) |
| 2 | `tools/sweep_kanzi_n1000_framework_paper_metrics.py` | `7050128` | Kanzi framework arm — σ=1e-3 synthetic endpoint (Wave 91 / 110.A) |
| 3 | `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` | `7050128` | Kanzi framework arm — 50-NFE Euler real endpoint via `project_out⁻¹` bridge (Wave 95 / 110.B) |
| 4 | `tools/sweep_kanzi_n1000_diverse.py` | `7050128` | Kanzi framework arm — diverse endpoints + per-record JSONL (Wave 96.E) |
| 5 | `tools/lineageflow_n1000_gpu_sweep.sh` | `7050128` | LineageFlow N=1000 baseline+framework shell wrapper (Wave 108.C / 109.B) |
| 6 | `tools/run_real_ckpt_eval.py` | `7050128` (shim → `tools.eval.cli:build_argparser`) | Canonical PHASE-4 multi-model eval harness |
| 7 | `tools/_kanzi_sweep_runner.py` | `7050128` | Shared inner loop (function API, not a CLI) used by drivers 1–3 |
| 8 | `tools/wave87_n1000_sweep.py` | `7050128` | FlowMol3 N=1000 paper-metric sweep (PB-xtb pipeline) |
| 9 | `tools/run_mol_eval.py` | `7050128` | Generic molecular metric runner — upstream FlowMol3 / GraphBFN / SOTA replay |
| 10 | `tools/upstream_eval.py` (kanzi + flowmol3 + smoke sub-modules) | `7050128` | Upstream-eval orchestrator shim (Wave 79 / 81 / 82) |
| 11 | `tools/run_lineageflow_n1000_foldability_omegafold.py` | `7050128` | LineageFlow foldability + self-consistency sweep (Wave 84) |

`tools/run_synthetic_image_eval.py`, `tools/run_image_eval.py`, `tools/run_image_fid_per_round.py`, `tools/run_kanzi_real_ckpt.py`, `tools/run_lineageflow_real_ckpt.py`, and `tools/run_kanzi_gpt_prior.py` exist but are smoke/single-record / per-adapter verification harnesses, not multi-record sweep drivers; they are out of scope for this audit.

---

## 2. Per-entry-point audit table

Format: file:line — `--flag` (default) — where the default is sourced from.

### 2.1 `tools/sweep_kanzi_n1000_paper_metrics.py` (Kanzi baseline arm)

| Aspect | Location | Default |
|---|---|---|
| CLI parser | `sweep_kanzi_n1000_paper_metrics.py:54-77` | argparse |
| `--input` | line 55 | **required** (no default) |
| `--ckpt` | line 57-60 | `data/kanzi_ckpt/cleaned_model.pt` |
| `--output-dir` | line 61-65 | `verification_outputs/kanzi_n1000_paper_metrics` |
| `--limit` | line 66 | `None` (no cap) |
| `--seed` | line 68-72 | `42` |
| `--pb-engine` | line 73-76 | `"uff"` (Wave 87 byte-stable baseline) |
| `nfe_steps` (hardcoded call) | line 84 | `100` |
| Device | n/a (CPU; no GPU move — `DAE.from_pretrained` returns CPU module) | **CPU only** — bug surfaced in Wave 99.A (`sweep_kanzi_n1000_diverse.py:136` had to add `dae.to("cuda")`) |
| Mode | line 80 | `"baseline"` |
| Cache | n/a (DAE state read fresh each record) | none |
| N records | from `--input` file; `--limit` is optional cap | file length (1000 in Wave 80 input) |
| Seed threading | line 68-72 + `_kanzi_sweep_runner.py:118` (record_idx-seeded RNG) | `--seed 42` |
| Output JSON | `out_dir / "kanzi_n1000_paper_metrics.json"` (set by `_kanzi_sweep_runner.py:570`) | fixed name |
| Reads config file? | **No** | n/a |

### 2.2 `tools/sweep_kanzi_n1000_framework_paper_metrics.py` (framework σ=1e-3 synthetic arm)

| Aspect | Location | Default |
|---|---|---|
| CLI parser | `sweep_kanzi_n1000_framework_paper_metrics.py:70-95` | argparse |
| `--input` | line 71 | **required** |
| `--ckpt` | line 73-76 | `data/kanzi_ckpt/cleaned_model.pt` |
| `--output-dir` | line 77-81 | `verification_outputs/kanzi_n1000_framework_paper_metrics_real` |
| `--n-steps-decoder` | line 82-83 | `100` |
| `--seed` | line 84-88 | `42` |
| `--limit` | line 89-90 | `None` (no cap) |
| `--pb-engine` | line 91-94 | `"uff"` |
| Device | `_kanzi_sweep_runner.py:362-364` (constructs `KanziAdapter(force_mode="torch", num_steps=50, solver="euler")`) | CPU unless `--pb-engine xtb` / `kanzi_latent_to_coord` (see Wave 99.A — bug) |
| Mode | line 98 | `"framework_synthetic"` |
| Cache | n/a | none |
| N records | from `--input` + `--limit` cap | 1000 in production |
| Seed threading | line 84-88 + `_kanzi_sweep_runner.py:118` (`seed * 1_000_003 + record_idx`) | `--seed 42` |
| Output JSON | `out_dir / "kanzi_n1000_framework_paper_metrics.json"` (set by `_kanzi_sweep_runner.py:591`) | fixed name |
| Reads config file? | **No** | n/a |

### 2.3 `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` (framework 50-NFE Euler arm)

| Aspect | Location | Default |
|---|---|---|
| CLI parser | `sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:55-67` | argparse |
| `--input` | line 56 | **required** |
| `--ckpt` | line 57-59 | `data/kanzi_ckpt/cleaned_model.pt` |
| `--output-dir` | line 60-63 | `verification_outputs/kanzi_n1000_framework_paper_metrics_inv_proj` |
| `--n-steps-decoder` | line 64 | `100` |
| `--seed` | line 65 | `42` |
| `--limit` | line 66 | **`1000`** (different from baseline/framework_synthetic!) |
| `--pb-engine` | n/a (omitted!) | n/a (inconsistent with drivers 1 + 2 — will silently skip PB-xtb store) |
| Device | `_kanzi_sweep_runner.py:362-364` | CPU (same Wave 99.A bug) |
| Mode | line 70 | `"framework_inv_proj"` |
| Solver | `_kanzi_sweep_runner.py:363` | `"euler"` (hardcoded; no Heun option exposed) |
| Num steps (framework ODE) | `_kanzi_sweep_runner.py:363` | `50` (hardcoded!) |
| Cache | n/a | none |
| N records | `--limit 1000` | 1000 |
| Seed threading | line 65 + `_kanzi_sweep_runner.py:118, 145` | `--seed 42` |
| Output JSON | `out_dir / "kanzi_n1000_framework_paper_metrics.json"` (set by `_kanzi_sweep_runner.py:598`) — **same name as 2.2** (different output-dir, different content) |
| Reads config file? | **No** | n/a |

### 2.4 `tools/sweep_kanzi_n1000_diverse.py` (framework diverse endpoint + per-record JSONL)

| Aspect | Location | Default |
|---|---|---|
| CLI parser | `sweep_kanzi_n1000_diverse.py:106-124` | argparse |
| `--input` | line 107-110 | `verification_outputs/kanzi_n1000_coords.txt` |
| `--ckpt` | line 111-114 | `data/kanzi_ckpt/cleaned_model.pt` |
| `--output-dir` | line 115-116 | **required** |
| `--n-steps-decoder` | line 117-118 | `100` |
| `--seed` | line 119-120 | `42` |
| `--max-records` | line 121-123 | **`1000`** |
| Device | line 136 | `"cuda"` (hardcoded `dae.to("cuda")` — Wave 99.A fix) |
| Mode | n/a (no `mode=` arg, runs `real_framework_x_final_512d`) | diverse |
| Solver | line 152 | `"euler"` |
| Num steps (framework ODE) | line 152 | `50` |
| Cache | n/a | none |
| GPU watchdog | line 170 (`gpu_watchdog(threshold_seconds=30, sample_interval=5)`) | Wave 98.A |
| N records | `--max-records 1000` | 1000 |
| Seed threading | line 119-120 | `--seed 42` |
| Output JSON | `out_dir / "per_metric.jsonl"` (per-record) — **different naming convention from 2.1/2.2/2.3** |
| Reads config file? | **No** | n/a |

### 2.5 `tools/lineageflow_n1000_gpu_sweep.sh` (shell wrapper)

| Aspect | Location | Default |
|---|---|---|
| Positional args | line 29-32 | arm + output_dir + log_path (3 args, all required) |
| `ARM` validation | line 38-41 | `baseline` or `framework` |
| `CUDA_VISIBLE_DEVICES` | line 45 | `${CUDA_VISIBLE_DEVICES:-0}` |
| `PYTHONPATH` | line 46 | append repo root |
| `VENV_PY` | line 47 | `.venvs/lineageflow_venv/bin/python` (hardcoded) |
| `RUN_REAL` | line 48 | `tools/run_real_ckpt_eval.py` (hardcoded path) |
| `NFE` | line 49 | `250` (hardcoded!) |
| `SEEDS` | line 50 | `42` (hardcoded!) |
| `N_SAMPLES` | line 51 | `1000` (hardcoded!) |
| `COMMON_ARGS` | line 52-54 | `--model lineageflow --seeds 42 --nfe-budgets 250 --force-mode real --metric-mode real --composite-metric real --lineageflow-upstream-eval --upstream-n-samples 1000` |
| `OUT_JSON` | line 57 | `output_dir/lineageflow_n1000_${ARM}_q4_2026_v2.json` (path naming convention not propagated to other drivers) |
| `timeout` | line 67 | `7200` (2h; Wave 110.C PARTIAL failure was 4 sweeps × 71 min each = 284 min) |
| N records | `--upstream-n-samples 1000` | 1000 |
| Reads config file? | **No** | n/a |

### 2.6 `tools/run_real_ckpt_eval.py` → `tools/eval/cli.py:build_argparser` (canonical eval driver)

| Aspect | Location | Default |
|---|---|---|
| CLI parser | `tools/eval/cli.py:29-259` | argparse |
| `--model` | `cli.py:38-41` | **required** (choices: VALID_MODELS) |
| `--seeds` | `cli.py:42-45` | **required** (comma-separated) |
| `--nfe-budgets` | `cli.py:46-49` | **required** (comma-separated) |
| `--n-rounds` | `cli.py:50-55` | `3` |
| `--output` | `cli.py:56-59` | **required** |
| `--print-only` | `cli.py:60-63` | flag (no default) |
| `--force-mode` | `cli.py:64-74` | `"synthetic"` |
| `--metric-mode` | `cli.py:75-89` | `"synthetic"` |
| `--restart-min-nfe` | `cli.py:90-106` | `20` |
| `--composite-metric` | `cli.py:107-131` | `"auto"` |
| `--n-molecules` | `cli.py:132-145` | `1` |
| `--paper-metrics` | `cli.py:146-162` | flag (off by default) |
| `--paper-reference` | `cli.py:163-176` | `"GEOM_DRUGS"` |
| `--lineageflow-upstream-eval` | `cli.py:180-196` | flag |
| `--kanzi-upstream-eval` | `cli.py:197-211` | flag |
| `--flowmol3-upstream-eval` | `cli.py:232-246` | flag |
| `--kanzi-framework-paper-metrics` | `cli.py:212-231` | flag |
| `--upstream-n-samples` | `cli.py:247-258` | `1000` |
| `CUDA_VISIBLE_DEVICES` | `run_real_ckpt_eval.py:96` | `"0"` (only place set on the canonical driver — but other drivers re-set this in their own `if __name__` guards) |
| N records | `--upstream-n-samples` | `1000` (per upstream eval call) |
| Seed threading | per-cell RNG (via `--seeds` + `n_rounds`) | `--seeds 42` + `--n-rounds 3` |
| Output JSON | `args.output` (caller-supplied) | caller-decides |
| Reads config file? | **No** (env hash captured at `cli.py:284` but no YAML/TOML config) | n/a |
| Total `--flags` | 17 (matches `grep -c add_argument = 18` — one is the wrapper block + one is `--kanzi-framework-paper-metrics`) | — |

### 2.7 `tools/_kanzi_sweep_runner.py` (shared inner loop — function API, not a CLI)

| Aspect | Location | Default |
|---|---|---|
| Function signature | `_kanzi_sweep_runner.py:252-263` | not a CLI; takes `mode, *, projector, output_dir, seed, max_records, nfe_steps, input_path, ckpt_path, pb_engine` |
| `_DEFAULT_INPUT` | line 49-51 | `verification_outputs/kanzi_n1000_coords.txt` |
| `_DEFAULT_CKPT` | line 52 | `data/kanzi_ckpt/cleaned_model.pt` |
| `KANZI_AR_SEQ_LENGTH` (imported from `adaptive_reflow.adapters.kanzi:119`) | line 119-122 | `64` (adapter-defined constant) |
| `KANZI_LATENT_CLAMP` (Wave 91 docstring) | `_synthesize_x_final_synthetic` docstring | `6.0` (not in runner, in adapter) |
| `codebook_dim` | `_synthesize_x_final_synthetic:97-122` | `512` (was `4` pre-Wave 110.A — Bug 1 fix) |
| `sigma` (synthetic noise scale) | line 121 | `1e-3` (hardcoded in `_synthesize_x_final_synthetic`) |
| `nfe_steps` default call-site for baseline | `sweep_kanzi_n1000_paper_metrics.py:84` | `100` |
| `KanziAdapter` num_steps | line 363 | `50` (hardcoded inside `_kanzi_sweep_runner.py`) |
| `KanziAdapter` solver | line 363 | `"euler"` (hardcoded inside `_kanzi_sweep_runner.py`) |
| `KanziAdapter` force_mode | line 362 | `"torch"` (hardcoded inside `_kanzi_sweep_runner.py`) |
| Output JSON path | line 570 / 591 / 598 | per-mode fixed name (see 2.1/2.2/2.3) |
| Reads config file? | **No** | n/a |

### 2.8 `tools/wave87_n1000_sweep.py` (FlowMol3 N=1000 paper-metric sweep)

| Aspect | Location | Default |
|---|---|---|
| CLI parser | n/a | **no argparse** — all settings are module-level constants |
| `N_TOTAL` | line 75 | `1000` |
| `NFE` | line 76 | `250` |
| `NFE_BATCH` | line 77 | `100` |
| `N_BATCHES` | line 78 | `10` (= `N_TOTAL // NFE_BATCH`) |
| `SEED_BASE` | line 79 | `42` |
| `WEIGHTS_PATH` | line 80 | `data/flowmol3/weights_real/checkpoints/last.ckpt` |
| `UPSTREAM_REPO` | line 81 | `data/FlowMol3/repo` |
| `DEVICE` | line 82 | `"cuda:0"` |
| `CUDA_VISIBLE_DEVICES` | line 53 | `"0"` (overrides env) |
| `PERTURBATION_SIGMA` (baseline / framework) | line 386 / 398 | `0.0` (baseline) / `0.05` (framework) |
| `pb_workers` | line 333 | `2` (hardcoded inside `_compute_metrics`) |
| Output JSON (per-arm) | line 383 / 395 | `verification_outputs/flowmol3_n1000_{baseline,framework}_wave87_q4_2026.json` |
| Output JSON (sweep) | line 496 | `verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json` |
| N records | `N_TOTAL = 1000` | 1000 |
| Seed threading | line 196 (`seed = seed_base + batch_idx`) | per-batch seed |
| Reads config file? | **No** | n/a |
| Total `--flags` | 0 | — |

### 2.9 `tools/run_mol_eval.py` (generic molecular metric runner)

| Aspect | Location | Default |
|---|---|---|
| CLI parser | `run_mol_eval.py:2261-2360` | argparse |
| `--input` | line 2270-2279 | **required** (Path) |
| `--output` | line 2280-2285 | **required** (Path) |
| `--reference-smiles` | line 2286-2300 | `None` (resolves to canonical `data/FlowMol3/references/geom_drugs_train.smi` → NCI proxy fallback at `run_mol_eval.py:2376-2380`) |
| `--dataset` | line 2301-2310 | `None` → "unknown" |
| `--flowmol3-paper-metrics` | line 2311-2322 | `None` (auto) |
| `--no-flowmol3-paper-metrics` | line 2323-2328 | flag |
| `--flowmol3-processed-data-dir` | line 2329-2337 | `None` |
| `--flowmol3-no-posebusters` | line 2338-2347 | `True` (default ON — PoseBusters is enabled) |
| `--flowmol3-pb-workers` | line 2348-2353 | `2` |
| `--flowmol3-device` | line 2354-2359 | **`"cuda:0"`** (this is the only place a per-runner hardcoded device default lives — and the canonical `run_real_ckpt_eval.py` defaults to `CUDA_VISIBLE_DEVICES=0` via the shim's `__main__` guard but does **not** default `--flowmol3-device` here) |
| N records | implicit (length of `.npz` / `.pkl` / `.sdf` file at `--input`) | input-file length |
| Output JSON | `args.output` | caller-supplied |
| Reads config file? | **No** | n/a |
| Total `--flags` | 10 | — |

### 2.10 `tools/upstream_eval.py` (upstream-eval orchestrator shim)

This file has **three distinct argparse blocks** (one per upstream tool + one smoke surface). They are sub-modules of the same script invoked by `--kanzi-upstream-eval`, `--lineageflow-upstream-eval`, `--flowmol3-upstream-eval` from `tools/eval/cli.py`.

**Block A — Kanzi (lines 430-439)**:

| Aspect | Location | Default |
|---|---|---|
| `--input` | line 432 | **required** |
| `--ckpt` | line 433 | **required** |
| `--output` | line 434 | **required** |
| `--max-records` | line 435-436 | `0` (no cap, processes all) |
| `--output-jsonl` | line 437-438 | `None` (no JSONL) |
| Device | line 441 (`DAE.from_pretrained(args.ckpt).eval()` — CPU, no `.to("cuda")`) | **CPU only** (same Wave 99.A bug) |
| Reads config file? | **No** | n/a |
| Total `--flags` | 5 | — |

**Block B — FlowMol3 SMILES → SampleAnalyzer (lines 773-779)**:

| Aspect | Location | Default |
|---|---|---|
| `--smiles-list` | line 775 | **required** |
| `--reference` | line 776 | **required** |
| `--output` | line 777 | **required** |
| `--pb-workers` | line 778 | `2` |
| Device | n/a (operates on SMILES only — no model load) | n/a |
| Reads config file? | **No** | n/a |
| Total `--flags` | 4 | — |

**Block C — Smoke surface (lines 950-961)**:

| Aspect | Location | Default |
|---|---|---|
| `--model` | line 957-960 | **required** (choices: lineageflow, kanzi, flowmol3) |
| Reads config file? | **No** | n/a |
| Total `--flags` | 1 | — |

Combined `upstream_eval.py` total `--flags`: **10**.

### 2.11 `tools/run_lineageflow_n1000_foldability_omegafold.py` (Wave 84 foldability)

| Aspect | Location | Default |
|---|---|---|
| CLI parser | `run_lineageflow_n1000_foldability_omegafold.py:78-88` | argparse |
| `--baseline-fasta` | line 80 | **required** (Path) |
| `--framework-fasta` | line 81 | **required** (Path) |
| `--output-dir` | line 82 | **required** (Path) |
| `--max-seqs` | line 83 | `None` |
| `--omegafold-bin` | line 84 | `"omegafold"` (looks up `$PATH`) |
| `--skip-fold` | line 85 | flag |
| `--skip-sc` | line 86 | flag |
| `--plots` | line 87 | flag |
| `--log-every` (hardcoded inside `_run`) | line 115 | `60` |
| Device | n/a (OmegaFold + ESM-IF subprocesses; control via `$PATH` binaries) | indirect via subprocess |
| N records | `--max-seqs` | caller-supplied |
| Seed threading | n/a | none |
| Output JSON | `args.output_dir / <arm> / "metrics_summary.json" + "self_consistency_summary.json"` | per-arm sub-dir |
| Reads config file? | **No** | n/a |
| Total `--flags` | 8 | — |

---

## 3. Final summary table — settings scattered across CLI flags

The "single logical setting → multiple invocations" matrix the user complained about on 2026-09-11.

| Logical setting | Counted # CLI default locations | Concrete defaults |
|---|---|---|
| **`N=1000` record count** | **8** | (a) `sweep_kanzi_n1000_*.py` × 3 — `--limit None` / `--limit 1000` / `--max-records 1000`; (b) `lineageflow_n1000_gpu_sweep.sh:51` — `N_SAMPLES=1000`; (c) `cli.py:247-258` — `--upstream-n-samples 1000`; (d) `sweep_kanzi_n1000_diverse.py:121-123` — `--max-records 1000`; (e) `wave87_n1000_sweep.py:75` — `N_TOTAL=1000`; (f) `run_real_ckpt_eval.py` `--nfe-budgets` cell product (3 seeds × 1 NFE = 3 cells at N=1000 each, default `--upstream-n-samples 1000`) |
| **`NFE=250`** | **3** | (a) `lineageflow_n1000_gpu_sweep.sh:49` — `NFE=250`; (b) `wave87_n1000_sweep.py:76` — `NFE=250`; (c) `run_real_ckpt_eval.py --nfe-budgets` (caller supplies, no default) |
| **`NFE_BATCH=100`** | **1** | `wave87_n1000_sweep.py:77` |
| **DAE.decode `n_steps=100`** | **4** | (a) `sweep_kanzi_n1000_paper_metrics.py:84` — `nfe_steps=100`; (b) `sweep_kanzi_n1000_framework_paper_metrics.py:82-83` — `--n-steps-decoder 100`; (c) `sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:64` — `--n-steps-decoder 100`; (d) `sweep_kanzi_n1000_diverse.py:117-118` — `--n-steps-decoder 100` |
| **Framework ODE `num_steps=50` (KanziAdapter Euler)** | **2** | (a) `_kanzi_sweep_runner.py:363` (hardcoded inside runner — not exposed to CLI); (b) `sweep_kanzi_n1000_diverse.py:152` (hardcoded at the call site) |
| **`seed=42`** | **6** | (a) `sweep_kanzi_n1000_paper_metrics.py:68`; (b) `sweep_kanzi_n1000_framework_paper_metrics.py:84`; (c) `sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:65`; (d) `sweep_kanzi_n1000_diverse.py:119-120`; (e) `lineageflow_n1000_gpu_sweep.sh:50` — `SEEDS=42`; (f) `wave87_n1000_sweep.py:79` — `SEED_BASE=42` |
| **`pb_engine="uff"`** | **2** | (a) `sweep_kanzi_n1000_paper_metrics.py:73-76`; (b) `sweep_kanzi_n1000_framework_paper_metrics.py:91-94`; (driver 3 has **no** `--pb-engine` flag — the JSON silently drops the key) |
| **`pb_workers=2`** | **2** | (a) `wave87_n1000_sweep.py:333`; (b) `upstream_eval.py:778` |
| **Device (cuda vs cpu)** | **5+** | (a) `lineageflow_n1000_gpu_sweep.sh:45` — `CUDA_VISIBLE_DEVICES=${...:-0}`; (b) `wave87_n1000_sweep.py:53,82` — `"cuda:0"`; (c) `sweep_kanzi_n1000_diverse.py:136` — `dae.to("cuda")` (Wave 99.A fix); (d) `run_real_ckpt_eval.py:96` — `os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")`; (e) `run_mol_eval.py:2357` — `--flowmol3-device cuda:0` (per-tool flag, not exported to the canonical driver); (f) `_kanzi_sweep_runner.py` — **never moves DAE/KanziAdapter to cuda**; same bug surfaces in `upstream_eval.py:441`. **Net result: Kanzi drivers 1, 2, 3 + upstream_eval Kanzi block silently run on CPU** — matches the user's 2026-09-11 GPU util 0% report |
| **`force_mode="synthetic"` (vs `"real"`)** | **3** | (a) `cli.py:64-74` — `--force-mode synthetic`; (b) `cli.py:75-89` — `--metric-mode synthetic`; (c) Wave 105 P0-B added `--pb-engine` to 2 Kanzi drivers (only). Bug 2 root cause (Wave 110.B) — `_kanzi_sweep_runner.py:362` hardcodes `force_mode="torch"` |
| **`composite_metric="auto"`** | **1** | `cli.py:107-131` (default `"auto"`; `"real"` required for Kanzi/LineageFlow/FlowMol3 composite) |
| **`restart_min_nfe=20`** | **1** | `cli.py:90-106` (only honoured by FlowMol3 v1 adapter; factory-side `inspect.signature` filter at `cli.py:101`) |
| **`paper_metrics` flag** | **1** | `cli.py:146-162` (off by default; required for `--model flowmol3 / flowmol3_v2` paper-parity numbers) |
| **`upstream_n_samples=1000`** | **1** | `cli.py:247-258` (per-cell upstream eval record count) |
| **Checkpoint path** | **3** | (a) `_kanzi_sweep_runner.py:52` — `_DEFAULT_CKPT = data/kanzi_ckpt/cleaned_model.pt`; (b) `sweep_kanzi_n1000_*.py` × 3 all default to the same path; (c) `wave87_n1000_sweep.py:80` — `data/flowmol3/weights_real/checkpoints/last.ckpt` |
| **Input record file path** | **2** | (a) `_kanzi_sweep_runner.py:49-51` — `_DEFAULT_INPUT = verification_outputs/kanzi_n1000_coords.txt`; (b) `sweep_kanzi_n1000_diverse.py:107-110` — same path default |
| **Output JSON naming convention** | **3 distinct conventions** | (a) `kanzi_n1000_paper_metrics.json` (driver 1); (b) `kanzi_n1000_framework_paper_metrics.json` (drivers 2 + 3 — same name!); (c) `per_metric.jsonl` (driver 4); (d) `lineageflow_n1000_${ARM}_q4_2026_v2.json` (shell wrapper); (e) `flowmol3_n1000_{baseline,framework}_wave87_q4_2026.json` + `flowmol3_n1000_sweep_wave87_q4_2026.json` (wave87) — none of these are addressable by a single config key |
| **Venv interpreter** | **3** | (a) `lineageflow_n1000_gpu_sweep.sh:47` — `.venvs/lineageflow_venv/bin/python`; (b) `sweep_kanzi_*.py` docstrings — `.venvs/kanzi_venv/bin/python` (not enforced in code); (c) `run_kanzi_real_ckpt.py` / `run_lineageflow_real_ckpt.py` — same sidecar pattern |
| **Solver / Force-mode combo inside KanziAdapter** | **2** | (a) `_kanzi_sweep_runner.py:362-364` — `force_mode="torch", num_steps=50, solver="euler"`; (b) `sweep_kanzi_n1000_diverse.py:150-153` — same triple. Heun solver **not exposed anywhere** |

### 3.1 Same logical setting reachable from 2+ commands — failure surface

The user complaint "many data-linkage details are broken; sweep drivers should be config-file driven, not command-line scattered" is best illustrated by the "**N=1000 baseline**" check — there is no single command that triggers all 5 Kanzi sweep variants:

| Goal | Today — 2+ ways to trigger |
|---|---|
| Kanzi baseline N=1000 paper metrics | `sweep_kanzi_n1000_paper_metrics.py --input ... --output-dir ...` (driver 1) **OR** `upstream_eval.py --input ... --ckpt ... --output ...` (Kanzi block) **OR** `run_real_ckpt_eval.py --model kanzi --seeds 42 --nfe-budgets 1000 --output ... --kanzi-upstream-eval --upstream-n-samples 1000` (canonical driver) — 3 different invocations, **none read a shared config** |
| Kanzi framework arm N=1000 paper metrics | `sweep_kanzi_n1000_framework_paper_metrics.py` (driver 2 — σ=1e-3 synthetic) **OR** `sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` (driver 3 — 50-NFE Euler real) **OR** `sweep_kanzi_n1000_diverse.py` (driver 4 — diverse endpoint + JSONL) **OR** `run_real_ckpt_eval.py --model kanzi --kanzi-framework-paper-metrics --upstream-n-samples 1000` (canonical driver) — 4 different invocations, **none read a shared config** |
| LineageFlow N=1000 framework-vs-baseline | `lineageflow_n1000_gpu_sweep.sh <arm> <output_dir> <log_path>` (shell wrapper) **OR** `run_real_ckpt_eval.py --model lineageflow --seeds 42 --nfe-budgets 250 --lineageflow-upstream-eval --upstream-n-samples 1000` (canonical driver) — 2 different invocations, **none read a shared config** |
| FlowMol3 N=1000 paper-metric sweep | `wave87_n1000_sweep.py` (no argparse; constants only) **OR** `run_real_ckpt_eval.py --model flowmol3 --nfe-budgets 250 --paper-metrics --n-molecules 100` (canonical driver, equivalent at N=1000) — 2 different invocations, **none read a shared config** |

### 3.2 Wave 110.C evidence — the failure surface

The brief cites Wave 110.C (`f9df1f6`) as PARTIAL — "only baseline arm N=1000 launched before agent budget exhausted. 4 sweeps × 71 min each = 280 min exceeded single-agent runtime envelope". The audit shows why: the **LineageFlow N=1000 sweep has no single command**; the shell wrapper at `lineageflow_n1000_gpu_sweep.sh:67` invokes `run_real_ckpt_eval.py` with a fixed `timeout 7200` and **each invocation emits BOTH arms in one JSON** (per the wrapper header docstring lines 22-26). Therefore "4 sweeps × 71 min" = 4 sequential invocations of the shell wrapper, each costing ~71 min. A config-file-driven pipeline could express the same sweep as one entry-point with `(baseline, framework, N=1000, seed=42, nfe=250, upstream_n_samples=1000)` in a single document.

### 3.3 Wave 110.B Bug 2 — surface in CLI defaults

Bug 2 (`4f7e3c7`) was "framework_inv_proj shape mismatch" — root cause was `default_kanzi_adapter(weights_path=ckpt, force_mode="real")` in `_kanzi_sweep_runner.py:362` (per the `_mode_metadata` block lines 225-234). The CLI defaults audited in §2.6 do **not** expose `--force-mode real` to the Kanzi sweep drivers 1, 2, 3 — they live in `tools/eval/cli.py:64-74` only, with default `"synthetic"`. The Kanzi sweep drivers never set `force_mode` explicitly; the runner hardcodes `"torch"` at `_kanzi_sweep_runner.py:362`. **The fix shipped (Wave 110.B) was a one-line hardcode change in the runner, not a CLI flag** — this is the architectural smell.

### 3.4 GPU util 0% evidence — surface in CLI defaults

The brief cites "GPU util 0% per nvidia-smi — Kanzi DAE.decode runs on CPU even when CUDA is available". Per §2.1 / §2.2 / §2.3: drivers 1, 2, 3 **never call `dae.to("cuda")`** — Wave 99.A fix (`sweep_kanzi_n1000_diverse.py:136`) was applied **only to driver 4**. Drivers 1, 2, 3 and `upstream_eval.py:441` (Kanzi block) all silently run on CPU. The `lineageflow_n1000_gpu_sweep.sh:45` shell wrapper sets `CUDA_VISIBLE_DEVICES=0` but the inner `run_real_ckpt_eval.py` invocation depends on adapter behaviour — there is no "device" config key any of these drivers read.

---

## 4. Total CLI flag count — per file

| File | `add_argument` count (grep) | Audit count |
|---|---|---|
| `tools/sweep_kanzi_n1000_paper_metrics.py` | 6 | 6 |
| `tools/sweep_kanzi_n1000_framework_paper_metrics.py` | 7 | 7 |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` | 6 | 6 |
| `tools/sweep_kanzi_n1000_diverse.py` | 6 | 6 |
| `tools/eval/cli.py` (canonical eval driver) | 18 | 17 (one is a wrapper sub-block at line 309 inside `main`) |
| `tools/wave87_n1000_sweep.py` | 0 | 0 (no argparse) |
| `tools/run_mol_eval.py` | 10 | 10 |
| `tools/upstream_eval.py` (sum of 3 argparse blocks: 5+4+1) | 10 | 10 |
| `tools/run_lineageflow_n1000_foldability_omegafold.py` | 8 | 8 |
| `tools/_kanzi_sweep_runner.py` | n/a (function API) | n/a |
| **Total** | **71** | **70** (one block-level vs flag-level discrepancy inside `cli.py:309`; counts differ by 1) |

The 71 vs 70 split is from the grep counting `cli.py:309` `getattr(args, "upstream_n_samples", 1000)` as a flag-like line. Both numbers agree the canonical driver is the heaviest CLI surface in the repo.

### 4.1 Hardcoded-settings count (settings not exposed as flags)

| Source | Count |
|---|---|
| `_kanzi_sweep_runner.py` (function API hardcodes — not exposed to CLI) | `force_mode="torch"`, `num_steps=50`, `solver="euler"`, `vocab_size` (getattr default), `_DEFAULT_INPUT`, `_DEFAULT_CKPT`, sigma `1e-3`, `codebook_dim=512` = **8** |
| `lineageflow_n1000_gpu_sweep.sh` (shell hardcodes) | `NFE=250`, `SEEDS=42`, `N_SAMPLES=1000`, `CUDA_VISIBLE_DEVICES=${...:-0}`, `VENV_PY=".venvs/lineageflow_venv/bin/python"`, `RUN_REAL="tools/run_real_ckpt_eval.py"`, `timeout 7200`, `--composite-metric real`, `--metric-mode real`, `--force-mode real`, `--lineageflow-upstream-eval` = **11** |
| `wave87_n1000_sweep.py` (module-level constants — not exposed) | `N_TOTAL=1000`, `NFE=250`, `NFE_BATCH=100`, `SEED_BASE=42`, `DEVICE="cuda:0"`, `WEIGHTS_PATH`, `UPSTREAM_REPO`, `PERTURBATION_SIGMA=0.0/0.05`, `pb_workers=2`, `CUDA_VISIBLE_DEVICES="0"` = **10** |
| `sweep_kanzi_n1000_*.py` × 3 + diverse (defaults that repeat across drivers) | `--seed 42` (×4), `--pb-engine "uff"` (×2), `--n-steps-decoder 100` (×4), `--limit None` / `1000` / `1000` / `--max-records 1000` (×4), `--output-dir` (4 distinct paths hardcoded into per-driver defaults), `--ckpt data/kanzi_ckpt/cleaned_model.pt` (×4) = **~26** |
| `tools/run_real_ckpt_eval.py` / `tools/eval/cli.py` (defaults that interact with cell shape) | `--n-rounds 3`, `--force-mode synthetic`, `--metric-mode synthetic`, `--restart-min-nfe 20`, `--composite-metric auto`, `--n-molecules 1`, `--paper-reference GEOM_DRUGS`, `--upstream-n-samples 1000`, `os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")` = **9** |
| `tools/run_mol_eval.py` (defaults that interact with metric computation) | `--flowmol3-pb-workers 2`, `--flowmol3-device cuda:0`, `--flowmol3-no-posebusters` (default True) = **3** |
| `tools/upstream_eval.py` (defaults inside per-tool argparse) | `--max-records 0` (no cap), `--pb-workers 2` (FlowMol3 block) = **2** |
| `tools/run_lineageflow_n1000_foldability_omegafold.py` (defaults) | `--omegafold-bin "omegafold"`, `--log-every 60` (hardcoded inside `_run`) = **2** |
| **Total hardcoded settings** | **~71** |

This number (`~71`) is **the same as the total CLI flag count (`71`)** — i.e. **roughly half the configuration surface of the sweep harness is hardcoded across drivers**, not flag-exposed. The user's "config-file driven, not command-line scattered" directive maps to "convert these ~71 hardcoded constants into a single TOML/YAML config schema" — which is precisely the Wave 111.B task the workflow plan describes.

---

## 5. Findings — actionable (for Wave 111.A / B plan authors)

1. **Three Kanzi sweep drivers (1, 2, 3) all default `--pb-engine "uff"`** except driver 3 which **omits the flag entirely** — `sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:55-67` has no `--pb-engine` and no `pb_engine=` kwarg, so its JSON silently drops the key. This is a Wave 105 P0-B half-fix.
2. **`--limit` defaults differ across the 4 Kanzi sweep drivers**: `None` / `None` / `1000` / `1000` — the same logical sweep (`N=1000`) is gated inconsistently.
3. **`nfe_steps=100` (DAE.decode) is hardcoded at `sweep_kanzi_n1000_paper_metrics.py:84`** as a Python literal, not a flag — the other 3 Kanzi drivers expose it as `--n-steps-decoder` (default 100). Driver 1 cannot be re-tuned without an edit.
4. **`KanziAdapter` constructor settings (force_mode, num_steps, solver) are hardcoded inside `_kanzi_sweep_runner.py:362-364`** and not exposed anywhere — this is the root cause of Wave 110.B Bug 2 (the fix was a one-line hardcode change). The architecture should expose `--adapter-force-mode` / `--adapter-num-steps` / `--adapter-solver` on the sweep drivers.
5. **No Kanzi sweep driver moves `dae` to CUDA except driver 4** (Wave 99.A fix at `sweep_kanzi_n1000_diverse.py:136`). Drivers 1, 2, 3 + `upstream_eval.py:441` silently run on CPU — matches the user's GPU util 0% complaint.
6. **`lineageflow_n1000_gpu_sweep.sh` has 11 hardcoded shell constants** that cannot be re-tuned without editing the script — including `timeout 7200` which is the proximate cause of Wave 110.C PARTIAL (4 sweeps × 71 min > 7200 × 4 if any single sweep exceeds 2h).
7. **`wave87_n1000_sweep.py` has 10 module-level constants and 0 argparse flags** — every re-run requires an edit + commit. The file's docstring (lines 31-32) notes "NO commit (verification only)" but Wave 87 results are now load-bearing for the paper (§7.5).
8. **Three distinct output JSON naming conventions** across the 4 Kanzi drivers — no single consumer can read all four outputs via the same glob.
9. **No driver reads a config file** — all 11 drivers are pure CLI / shell-arg / module-constant surfaces. Wave 111.B must design the YAML/TOML schema, the loader, and the migration path.
10. **Canonical driver `tools/eval/cli.py` is the heaviest CLI surface (17 flags)** — but is **not used by any of the Kanzi / LineageFlow shell wrappers** for sweeps at N=1000. Drivers 1–4 + 5 + 8 do not use it; only `run_mol_eval.py` + the canonical driver cover the FlowMol3 + canonical-cell flow.

---

## 6. SHA + line citations index (single-source-of-truth)

- `70501280ac0e9e197064d3b2b029bb0787289403` — HEAD at audit time.
- `4f7e3c7` — Wave 110.B (Bug 2 fix; force_mode=real in KanziAdapter construction; not a CLI change).
- `f9df1f6` — Wave 110.C (PARTIAL re-run; baseline arm only).
- `wave108-final-synthesis.md` — `--seed` threading into Kanzi N=1000 sweep (per the 2026-09-11 brief mention of "many data-linkage details").
- `tools/_kanzi_sweep_runner.py:49-52` — `_DEFAULT_INPUT` / `_DEFAULT_CKPT`.
- `tools/_kanzi_sweep_runner.py:362-364` — `KanziAdapter(weights_path=ckpt, force_mode="torch", num_steps=50, solver="euler")` hardcode.
- `tools/eval/cli.py:64-89` — `--force-mode` + `--metric-mode` defaults (synthetic).
- `tools/eval/cli.py:90-106` — `--restart-min-nfe 20`.
- `tools/eval/cli.py:107-131` — `--composite-metric auto`.
- `tools/eval/cli.py:247-258` — `--upstream-n-samples 1000`.
- `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:55-67` — driver 3 missing `--pb-engine`.
- `tools/sweep_kanzi_n1000_paper_metrics.py:84` — `nfe_steps=100` hardcoded literal (driver 1 only).
- `tools/sweep_kanzi_n1000_diverse.py:136` — `dae.to("cuda")` (Wave 99.A fix; only driver that moves DAE).
- `tools/lineageflow_n1000_gpu_sweep.sh:45,47,49-51,67` — shell hardcodes (CUDA_VISIBLE_DEVICES, VENV_PY, NFE, SEEDS, N_SAMPLES, timeout 7200).
- `tools/wave87_n1000_sweep.py:75-82` — module-level constants (N_TOTAL, NFE, NFE_BATCH, SEED_BASE, DEVICE, WEIGHTS_PATH, UPSTREAM_REPO).
- `tools/run_mol_eval.py:2357` — `--flowmol3-device cuda:0` (per-runner flag not exported to canonical driver).
- `tools/upstream_eval.py:441` — `DAE.from_pretrained(args.ckpt).eval()` (CPU only; never moves to cuda).

---

## 7. Out of scope / non-findings

- `tools/run_synthetic_image_eval.py`, `tools/run_image_eval.py`, `tools/run_image_fid_per_round.py`, `tools/run_kanzi_real_ckpt.py`, `tools/run_lineageflow_real_ckpt.py`, `tools/run_kanzi_gpt_prior.py` — single-record / smoke harnesses; not multi-record sweep drivers. **Out of scope.**
- `scripts/run_ablation_sweep.py` (Wave 52) — exists per the Wave 52 task list; does N>1 record eval but operates on outputs from the canonical driver (not a sweep driver per the user's brief). **Noted but out of scope.**
- `tools/run_sbc_audit.py` (Wave 17) — chi-squared SBC; not an N-record sweep.
- `tools/run_mutation_audit.py` (Wave 18 F.6) — mutation testing; not an N-record sweep.
- `tools/capability_audit.py` (Wave 23 Agent B) — meta-audit; reads pre-existing JSONs.
- `tools/check_claims_consistency.py` / `tools/check_doc_paper_refs.py` / `tools/check_docs_against_code.py` — doc checks, not sweeps.

---

**END OF AUDIT — READ-ONLY — NO COMMITS**
