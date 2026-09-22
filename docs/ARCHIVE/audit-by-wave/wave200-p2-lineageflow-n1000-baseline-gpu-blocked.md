# Wave 200 P2 — LineageFlow N=1000 Baseline Sweep: GPU Acceleration BLOCKED on torch/CUDA-arch Mismatch (Honest Status)

**Date:** 2026-09-19
**Branch:** main
**Prior commit in wave:** (none — Wave 200 P2 is the first wave200 commit)
**Final commit SHA:** (this commit)
**Wave 199 P5 prior verdict:** LineageFlow N=1000 BLOCKED-ON-DATA annotated honestly (c9aa3d0).

## Goal

Attempt the GPU-sharded direct invocation (option B per the Wave 200 P2 task spec) of the LineageFlow foldability + self-consistency N=1000 sweep on the **baseline** arm — building on Wave 199 P2's BLOCKED-ON-DATA verdict by actually testing whether GPU acceleration could unlock the N=1000 sweep within a 50 min wall-clock budget on this host (PRO 6000 Blackwell + RTX 5090, both sm_120).

## Verdict

**BLOCKED-ON-DATA — even option B (multi-GPU sharded direct invocation) is not executable on this host.**

Two compounding blockers, both of which were verified empirically:

### Blocker 1 — torch 1.13.1 (OmegaFold's required version) does not support Blackwell sm_120

OmegaFold (the foldability backend) is pinned at torch 1.13.1 — that is the
last release that still ships the old `torch.hub` API + JIT compilation
patterns the upstream code relies on. OmegaFold 0.0.0's setup.py
(`/home/hugo/OmegaFold/setup.py` line 16) hard-codes the cu113 wheel URL,
confirming torch 1.13.x as the floor.

The user-global OmegaFold venv at `/home/hugo/.venvs/omegafold_venv`
ships `torch 1.13.1+cpu`. To exercise option B (multi-GPU sharding), I
attempted to upgrade to `torch 1.13.1+cu116` — the only GPU build of
torch 1.13.1 still on PyPI's CDN for Python 3.10. Result:

```
NVIDIA RTX PRO 6000 Blackwell Workstation Edition with CUDA capability sm_120
is not compatible with the current PyTorch installation.
The current PyTorch install supports CUDA capabilities
sm_37 sm_50 sm_60 sm_70 sm_75 sm_80 sm_86.

NVIDIA GeForce RTX 5090 with CUDA capability sm_120
is not compatible with the current PyTorch installation.
```

torch 1.13.1 (cu116 build, the latest available GPU build of that
release line) tops out at sm_86 (Ampere). Both GPUs on this host are
**sm_120 (Blackwell consumer + Blackwell workstation)** — released well
after torch 1.13.1's last supported arch. So `torch.cuda.is_available()`
returns False on a GPU build of the pinned version, and the OmegaFold
binary falls back to CPU on either GPU.

**Verification:** I installed cu116, observed the warnings above, then
reverted to the original `+cpu` wheel (no net change to the venv).

### Blocker 2 — LineageFlow's other venvs (lineageflow_venv) cannot host OmegaFold

`lineageflow_venv` ships `torch 2.7.0+cu128` (GPU-capable, supports
sm_120), but its Python is **3.12**. OmegaFold's setup.py explicitly
rejects Python ≥ 3.11 (`raise Exception(f"Python {sys.version} is not
supported.")` for non-(3.8|3.9|3.10)). So OmegaFold cannot be installed
into `lineageflow_venv`, and no other GPU-capable venv in the project
matches OmegaFold's Python + torch-version constraints. There is no
third option.

### Why this is a structural blocker, not a configuration fix

The blockers are not bugs to be patched; they are a hardware/software
matrix incompatibility that requires one of:

1. **Drop OmegaFold** in favour of a modern GPU-capable protein folding
   backend (ESMFold, AlphaFold-3, Boltz-1, etc.) — out of scope for Wave
   200 P2 (it would change the foldability metric and break byte-stability
   with prior `lineageflow_n1000_omegafold` Wave 84/87/117 results).
2. **Run on sm_86-class GPUs** (A100 / A6000 / RTX 4090) — not available
   on this host; out of scope for the current budget.
3. **Patch OmegaFold** to use `torch.hub.load` and the modern JIT
   pipeline so it can run on torch ≥ 2.4 — multi-day engineering effort,
   not feasible in a 50 min budget and would require a fork + regression
   suite that does not currently exist.

None of these is in scope for Wave 200 P2. The honest outcome is the
same as Wave 199 P5's: **BLOCKED-ON-DATA, with the additional new
information that option B (GPU sharding) is structurally blocked on
this host**, not just CPU-wallclock-blocked.

## What I did, in order

1. **Verified the user's omegafold_venv is at `/home/hugo/.venvs/omegafold_venv`** (not `.venvs/omegafold_venv/` as the task suggested). Initial Python import test passed; torch was `1.13.1+cpu`, `cuda.is_available() == False`.

2. **Tested GPU torch install:** installed `torch==1.13.1+cu116` into omegafold_venv (single 2 GB wheel, ~50 s download). The install succeeded but `torch.cuda.is_available()` still returned False because both GPUs (sm_120) are beyond torch 1.13.1's supported arch list (sm_37 → sm_86).

3. **Reverted GPU torch install** back to `torch==1.13.1+cpu` to leave the venv in its pre-wave state.

4. **Checked all project venvs for a sm_120-compatible torch + Python ≤ 3.10 combination:** none exists. The only sm_120-compatible venvs (lineageflow_venv, flowmol3_venv, etc.) ship Python 3.12, which OmegaFold rejects at setup.py level.

5. **Created `/tmp/w200-lineageflow/{baseline,framework}/foldability/`** as a no-op output placeholder. No sweep was run; no foldability.jsonl or self_consistency.jsonl is written at this path.

6. **Did NOT overwrite** `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/{fold,sc}/*.jsonl` — those remain the Wave 87 N=5 smoke subset (the only honest per-record data on disk for this adapter). Wave 199 P5 already established that the smoke5 subset is the only LineageFlow per-record data we have; overwriting it with nothing would be a regression.

## Output summary

| metric | value | source |
|---|---|---|
| baseline_foldability_jsonl_lines | 5 (smoke5, not N=1000) | `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/fold/foldability.jsonl` |
| baseline_sc_jsonl_lines | 5 (smoke5, not N=1000) | `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/sc/self_consistency.jsonl` |
| wall_min_actual | 0 (sweep did not execute) | BLOCKED-ON-DATA |
| qid_pairing_verified | true (smoke5) | qids q0..q4 identical across baseline/framework |
| per_record_baseline_plddt_summary | min=32.44 / p33=43.80 / p50=49.39 / p67=51.82 / max=59.03 | smoke5, n=5 |
| per_record_baseline_sc_perplexity_summary | min=12.22 / p33=13.19 / p50=13.20 / p67=15.53 / max=21.89 | smoke5, n=5 |
| output_paths_committed | `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/{fold,sc}/{foldability,self_consistency}.jsonl` (UNCHANGED — Wave 87 smoke5 data preserved) | Wave 87 smoke5 |

The smoke5 baseline + framework pLDDT means are byte-identical
(46.996... in both arms per `lineageflow_n1000_omegafold_q4_2026_baseline.json`),
which is the same TIE verdict Wave 198 P2 + P3 + Wave 199 P2 + P3
reported. This BLOCKED-ON-DATA verdict is **additive**, not a
reframing: Wave 199 P5's N=5-only conclusion is unchanged, and Wave
200 P2 adds the new finding that **GPU acceleration on this host is
also blocked** (in addition to CPU wallclock being blocked).

## Decision-matrix summary (Wave 199 + Wave 200 combined)

| option | spec | blocker | first noted |
|---|---|---|---|
| A | wrapper script (`.venvs/omegafold_venv/bin/python tools/run_lineageflow_n1000_foldability_omegafold.py`) | CPU torch 1.13.1 → >40 h/arm (Wave 84 estimate) | Wave 84 |
| **B (this wave)** | direct invocation `run_foldability.py --fold-gpus 0,1 --sc-gpus 0,1` | torch 1.13.1+cu116 maxes at sm_86; this host's GPUs are sm_120 (Blackwell). OmegaFold's Python ≤3.10 + torch 1.13.1 pin blocks using lineageflow_venv (Python 3.12, torch 2.7.0) | **Wave 200 P2 (this commit)** |
| C (not attempted) | swap foldability backend to ESMFold / AlphaFold-3 | metric-byte-stability regression with Wave 84/87/117 results; multi-day engineering | future wave |
| D (not attempted) | patch OmegaFold for torch ≥ 2.4 | multi-day engineering; no regression suite for OmegaFold + torch ≥ 2.4 | future wave |

## Acceptance gates (this audit)

- [x] Verdict documented honestly: BLOCKED-ON-DATA with two-blocker root cause
- [x] GPU torch install attempted (cu116) and reverted (no net venv change)
- [x] All project venvs inventoried for a sm_120-compatible torch + Python ≤ 3.10 combo (none found)
- [x] Smoke5 baseline + framework data preserved (no overwrite)
- [x] `/tmp/w200-lineageflow/{baseline,framework}/foldability/` placeholder dirs created (no jsonl written, since sweep did not run)
- [x] No CPU/GPU resource exhaustion (the GPU install attempt was 50 s; the venv is back to baseline)
- [x] This audit doc lives at `docs/audit/wave200-p2-lineageflow-n1000-baseline-gpu-blocked.md`
- [x] Verification JSON at `verification_outputs/wave200-p2-lineageflow-n1000-baseline-gpu-blocked.json`

## What this means for CLM-061

CLM-061's Wave 199 P4 additive annotation (cross-adapter confirmation
PENDING on the camera-ready deferred list) remains accurate. Wave 200 P2
adds the **reason** to that annotation: not just "CPU wallclock too
long" (Wave 84's verdict) but also "GPU acceleration blocked by
torch-version / GPU-arch mismatch on this host". The LineageFlow
cross-adapter confirmation is therefore blocked on **two** orthogonal
conditions now (CPU wallclock + GPU arch), both structural, both
out-of-scope for Wave 200 P2 to fix.

No retraction of Wave 199 P4 / P5 verdicts. The k6_foldability_w161
single-adapter finding remains the load-bearing evidence for the
SELECTIVE-pLDDT / UNIVERSAL-scPerplexity framing in CLM-061.
