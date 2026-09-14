# Wave 41 Agent B — LineageFlow upstream clone + numerical forward

**Date:** 2026-09-05
**Wave:** 41 Agent B
**Repo:** flowa-multistep-reinference
**Disjoint file scope:**
- `data/lineageflow_upstream/` (gitignored clone)
- `.venvs/lineageflow_venv/` (gitignored sidecar venv)
- `requirements-lineageflow.txt`
- `tools/run_lineageflow_real_ckpt.py`
- `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json` (gitignored)
- `docs/audit/wave41-lineageflow-numerical-forward.md` (this file)

---

## 1. Why this wave exists

Per the Wave 36 Agent C investigation
(`docs/audit/lineageflow-upstream-investigation.md`), the LineageFlow
upstream tree at `github.com/Jinx-byebye/LineageFlow` ships
`_install_checkpoint_compat()` in `inference/inference.py:39-59`. That
function fabricates `core.sampler.SamplerConfig` as an *empty stub* so
`torch.load`'s safe-globals unpickling can resolve the class name in the
released `lineageflow-rp55.ckpt` (10.5 GB). The class is never
instantiated at runtime — it is a `torch.save`-time placeholder.

Wave 39 Agent B mirrored this 5-LOC shim into
`adaptive_reflow/adapters/lineageflow.py`, which unblocked the
framework-side ckpt load (confirmed via 22-test suite). The remaining gap
was the **upstream core package runtime modules** —
`FlowMatchingSampler` / `PhylogenySampler` / `flow_step` — that the
real paper-quality solver depends on. Wave 41 Agent B closes that gap by
cloning upstream, installing it in a sidecar venv, and running a real
end-to-end numerical forward on the released checkpoint.

## 2. Clone + venv state (already present at session start)

| Asset | Status |
|---|---|
| `data/lineageflow_upstream/` | **cloned at `ccef84adff421fcb6b855285bc1860e1f9a94f59`**, working tree clean, remote `origin → https://github.com/Jinx-byebye/LineageFlow` |
| `.venvs/lineageflow_venv/` | **Python 3.12.13**, `pip` 24+, `site-packages` includes torch 2.5.1+cpu, transformers 4.57.6, numpy 2.5.2, scipy 1.18.1, huggingface_hub 0.36.2, biopython 1.88 |
| `requirements-lineageflow.txt` | committed; pins `torch==2.5.1+cpu` + transformers + biopython + scipy + numpy + huggingface_hub; documents the sys.path insertion strategy in the header |
| `tools/run_lineageflow_real_ckpt.py` | committed; 430 LOC; authored by Wave 40 Agent A but never executed before this wave |
| `data/lineageflow/lineageflow-rp55.ckpt` | 10.5 GB; SHA-256 `f0b4b25e626878be5c26da9e65d44c2e1551a076652d416f955b1357cde54a2b` (verified) |

The clone was already in place from a prior agent; Wave 41 Agent B
re-verified its HEAD matches the recorded `ccef84ad` upstream commit
expected by the Wave 36 Agent C investigation, and that the
`_install_checkpoint_compat()` shim is exactly as documented.

`pip install -e data/lineageflow_upstream/` is **not** the right
install method here — the upstream tree ships no `setup.py` /
`pyproject.toml`, so it must be placed on `sys.path` directly. The
script does this via `sys.path.insert(0, str(UPSTREAM_DIR))` before
importing `inference.inference` and `models.model`.

## 3. What was executed

```bash
.venvs/lineageflow_venv/bin/python tools/run_lineageflow_real_ckpt.py
```

Outputs (printed by the script + written to JSON):

```
checkpoint: data/lineageflow/lineageflow-rp55.ckpt
  size: 10,509,468,119 bytes
  sha256: f0b4b25e626878be5c26da9e65d44c2e1551a076652d416f955b1357cde54a2b (5.8s)
  matches todo/models/lineageflow.md: True
model built: 657,626,281 params (2.9s)
load_checkpoint_state: 6.0s, 576 tensors
load_state_dict: missing=0 unexpected=0
denoiser forward: 11.14s -> (4, 64, 20)
  per-position entropy (Wave 33 metric): 2.266096
  log(K) upper bound: 2.995732
  deterministic across two calls: True
vector field: 0.78s -> (4, 64, 20)
  max |sum_K v| (simplex tangency, want ~0): 1.771e-08
integrate_base_flow(8 Euler steps): 33.6s
  simplex entropy: start=2.565861 end=2.415161
  simplex residual: max|sum-1|=1.458e-07
wrote: verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json
```

## 4. Numerical findings

| Quantity | Value | Interpretation |
|---|---|---|
| **Per-position entropy (Wave 33 metric)** | **2.266096** | 75.6% of `log(20)=2.995732` upper bound; not saturated (delta = 0.73 from saturation) |
| `load_state_dict` missing keys | 0 | flow head + ESM-2-650M weights all matched |
| `load_state_dict` unexpected keys | 0 | clean load |
| Flow head weights loaded | `True` | confirms this is a *real* ckpt load, not random init |
| Vector-field tangency: `max \|sum_K v\|` | 1.771e-08 | simplex-tangent to floating-point precision |
| Euler integration: `max \|sum x − 1\|` | 1.458e-07 | probability simplex preserved to floating-point precision |
| Determinism (two identical forward calls) | `True` | `model.eval()` + dropout off; bit-identical logits |
| NaN / Inf in any output | none | logits, vector field, ODE endpoints all finite |

### 4.1 Reproducibility check

The script was run twice in this session (once with the original
"Wave 40 Agent A" identity, once with the corrected "Wave 41 Agent B"
identity). Wall-clock times varied by 2-3x due to system load
(0.48s → 11.14s for the denoiser, 72.3s → 33.6s for 8-step Euler), but
the **numerical outputs are bit-identical**:

- per-position entropy: `2.266095558934879` (both runs)
- vector-field tangency: `1.771e-08` (both runs)
- simplex residual: `1.458e-07` (both runs)
- simplex entropy start/end: `2.565861` / `2.415161` (both runs)

This is the expected behavior for `model.eval()` + frozen RNG; it
confirms the integration path is reproducible across invocations.

### 4.2 What is exercised, and what is *not*

| Path | Exercised? | Notes |
|---|---|---|
| `load_checkpoint_state` (upstream `inference.inference`) | YES | `_install_checkpoint_compat()` shim succeeds; 576 tensors |
| `LineageFlowClassifier(...)` build | YES | 657.6 M params, default `FlowTransformerConfig` |
| Real `load_state_dict` | YES | zero missing / zero unexpected |
| Single denoiser forward `model(x_simplex, t, pad_mask, gap_flag)` | YES | 0.5-11s on CPU; per-position entropy 2.266 |
| `compute_family_vector_field` | YES | simplex-tangent to 1.8e-08 precision |
| `integrate_base_flow` (Euler, 8 steps) | YES | end-state entropy 2.415 (Δ = -0.151) |
| Full `generate_with_intervention` | NO | needs mutation kernels + resampling + multi-round scheduler (paper sampling loop) |
| `family_validity` / foldability / self-consistency | NO | needs HMMER + OmegaFold + MMseqs2 + ESM-IF (eval-only deps, not installed in sidecar) |
| GPU path | NO | CPU only; CUDA not available in sidecar |

The **family prior `alpha_h`** is **synthetic** (a smooth Dirichlet-style
array with concentration 10). Upstream ships family priors and gap
rates as separate JSON assets (`--prior` / `--gap`) that are not part of
the released checkpoint and are not in this repo. The prior is used
only so the vector-field and ODE paths can be exercised end to end.
**No family-validity or foldability claim follows from this run.**

## 5. Wave 33 metric saturation check

The Wave 33 metric (`P2-W33-C`) replaced the saturated
`family_validity` metric. The decision threshold is: a value within
`1e-6` of `log(K)` is saturated; a value below `1e-6` is collapsed.

| | Value | Saturated? |
|---|---|---|
| This run (Wave 41 B) | 2.266096 | NO (Δ = 0.730 from saturation, Δ = 2.266 from collapse) |
| `log(K=20)` upper bound | 2.995732 | (reference) |

The metric is well above collapse and well below saturation. The
"mid-entropy" reading is consistent with a trained ESM-2-650M flow head
on a random simplex input at `t=1.0` — the network is neither
mode-collapsed (would give entropy ≈ 0) nor maxed-out (would give
entropy ≈ 2.996).

## 6. File scope touched (committed in this wave)

```
tools/run_lineageflow_real_ckpt.py      # identity updated Wave 40 A → Wave 41 B
docs/audit/wave41-lineageflow-numerical-forward.md   # this doc
```

**Not touched** (per disjoint-scope contract):
- `adaptive_reflow/` — no changes
- `tests/` — no changes
- framework / scheduler / other adapters — no changes

**Not committed** (gitignored per `.gitignore`):
- `data/lineageflow_upstream/`
- `.venvs/lineageflow_venv/`
- `data/lineageflow/lineageflow-rp55.ckpt`
- `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json`

## 7. Implications for downstream PHASE-4 work

The previous PHASE-4 verdict for LineageFlow was
`partially_supported` (Wave 10 synthetic shim only). This run moves it
to **`supported` for numerical forward + vector-field + Euler
integration** on the real ckpt, while keeping the family-validity
caveat from Wave 10 in place (eval-only deps still missing).

The framework-side `adaptive_reflow/adapters/lineageflow.py` continues
to use the 5-LOC `_install_checkpoint_compat` shim mirrored by Wave 39
Agent B. The upstream sidecar venv + clone this wave established is a
**second, independent path** to the same ckpt that does not go through
the framework — useful for cross-checking framework-side numerical
output against upstream truth, and as a stepping-stone for future
waves that want the full upstream `generate_with_intervention`
mutate→select→amplify loop.

## 8. Commit

Committed as `Wave 41 Agent B: LineageFlow upstream numerical forward
end-to-end (real ckpt)`. Not pushed.
