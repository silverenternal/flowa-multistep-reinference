# Wave 40 Agent A — LineageFlow upstream clone + real-ckpt numerical forward

**Date:** 2026-09-05
**Wave:** 40 Agent A
**Repo:** flowa-multistep-reinference
**Scope:** Clone the LineageFlow upstream source, stand up a CPU-only
sidecar venv, and run a real numerical forward through the released
10.5 GB checkpoint — closing the last PHASE-4 LineageFlow blocker.

**Outcome: SUCCESS.** The released checkpoint loads into the real
upstream model with **0 missing and 0 unexpected keys**, the denoiser
forward runs, and the real base-flow ODE solver integrates without NaN.

---

## 1. What this closes

Wave 36 Agent C found the upstream repo at
`github.com/Jinx-byebye/LineageFlow` (the earlier "NOT FOUND" was a
case/suffix mismatch: `jinxbye` on HF vs `Jinx-byebye` on GitHub) and
identified `_install_checkpoint_compat()` as the pickle-loading
workaround. Wave 39 Agent B mirrored that 5-LOC shim into
`adaptive_reflow/adapters/lineageflow.py`, which unblocked
`torch.load`.

The residual blocker was the **runtime** side: our adapter does not ship
the upstream `core` / `models` packages, so nothing could actually
consume the loaded tensors. This wave clones those packages and runs the
numerical forward for the first time.

| Blocker | Status before Wave 40 | Status after |
|---|---|---|
| Upstream source located | Wave 36 (URL only) | cloned at `ccef84ad` |
| ckpt pickle unpickles | Wave 39 (shim) | unchanged, confirmed |
| Model class available | **BLOCKED** | `LineageFlowClassifier` on `sys.path` |
| Weights actually load | **NEVER RUN** | 576/576 tensors, 0 missing, 0 unexpected |
| Denoiser forward | **NEVER RUN** | `(4, 64, 20)` logits, 0.46 s CPU |
| ODE solver | **NEVER RUN** | 8 Euler steps, 45.7 s CPU, no NaN |

## 2. Environment

| Item | Value |
|---|---|
| Upstream clone | `data/lineageflow_upstream/` (gitignored) |
| Upstream commit | `ccef84adff421fcb6b855285bc1860e1f9a94f59` ("Prepare LineageFlow public release", 2026-05-21) |
| License | MIT |
| Sidecar venv | `.venvs/lineageflow_venv/` (gitignored), Python 3.12.13 |
| Pins | `requirements-lineageflow.txt` (tracked) |
| torch | `2.5.1+cpu` (upstream pins `>=2.1,<2.6`) |
| transformers | `4.57.6` |
| Backbone | `facebook/esm2_t33_650M_UR50D`, HF cache |
| Device | CPU only. No CUDA kernels exercised. |

### 2.1 The upstream is NOT pip-installable

`github.com/Jinx-byebye/LineageFlow` ships **no** `setup.py`,
`pyproject.toml`, or `setup.cfg`. It is a plain source tree whose modules
import each other as *top-level* packages (`from core.vector_field import
c_h`, `from models.model import LineageFlowClassifier`). `pip install -e
data/lineageflow_upstream/` therefore fails.

The runner instead does `sys.path.insert(0, "data/lineageflow_upstream")`.
This is recorded in the output JSON under
`upstream.install_method` so the deviation from the task's original
"`pip install -e`" plan is not silently buried.

### 2.2 Deps deliberately omitted

Upstream's `requirements.txt` also lists `matplotlib`, `fair-esm`, and
`biotite`. Those are used only by `evaluation/` (HMMER / OmegaFold /
MMseqs2 scoring), never by the forward pass, so they are not installed.
`biopython` and `scipy` are installed per the task brief.

## 3. Checkpoint

| Item | Value |
|---|---|
| Path | `data/lineageflow/lineageflow-rp55.ckpt` |
| Size | 10,509,468,119 bytes (9.79 GiB) |
| SHA-256 | `f0b4b25e626878be5c26da9e65d44c2e1551a076652d416f955b1357cde54a2b` |
| Expected (from `todo/models/lineageflow.md`) | identical — **match** |
| Format | PyTorch-Lightning checkpoint |
| `state_dict` tensors | 576 |

> **Path correction.** The Wave 40 task brief named the checkpoint
> `data/lineageflow_ckpt/lineageflow-rp55.ckpt`. That directory does not
> exist; the file has lived at `data/lineageflow/lineageflow-rp55.ckpt`
> since Wave 10. The runner uses the real path.

### 3.1 Model configuration is pinned by the state dict

The checkpoint contains no `family_embed`, `input_proj`, or
`prior_weight_proj` tensors, and `out_head.weight` is `(20, 1280)`. That
pins the plain default `FlowTransformerConfig()`:

- `family_embed_dim = 0` (no family conditioning)
- `use_esm_token_embedding_expectation = True`
- `use_prior_weight_channel = False`
- `alpha_max = 16.0`, which equals upstream's default `--t-max 16.0`

No config guessing was required.

## 4. Results

Command:

```bash
.venvs/lineageflow_venv/bin/python tools/run_lineageflow_real_ckpt.py
```

Output: `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json`
(gitignored).

### 4.1 Weight load — exact

| Metric | Value |
|---|---|
| Parameters | **657,626,281** |
| `state_dict` tensors offered | 576 |
| `missing_keys` | **0** |
| `unexpected_keys` | **0** |

657.6 M matches the 657 M figure in the paper. A zero/zero load is the
strongest available evidence that the architecture reconstruction is
correct — every released tensor found a home and every parameter was
initialised from the checkpoint. Nothing is running on random weights.

### 4.2 Denoiser forward

Inputs: `B=4`, `L=64`, `K=20`, `x_simplex` softmax-normalised, `t=1.0`,
all positions valid, no gaps, seed 42.

| Metric | Value |
|---|---|
| Output shape | `(4, 64, 20)` |
| Elapsed | 0.46 s (CPU) |
| NaN / Inf | none |
| Deterministic across two calls | yes (`model.eval()`, bitwise equal) |

### 4.3 Wave 33 decision metric — non-saturated

| Metric | Value |
|---|---|
| Per-position mean entropy | **2.266096** |
| Upper bound `log(20)` | 2.995732 |
| Saturated? | **no** |

This is the point of the Wave 33 (`P2-W33-C`) metric change. The old
`family_validity` metric returned 1.0 in *both* arms of the Wave 10
comparison — a structural tie carrying no signal. The entropy metric
lands at 2.266 against a 2.996 ceiling, i.e. strictly interior, so a
framework-vs-baseline gap on real weights would be measurable rather
than degenerate.

The formula in the runner is inlined rather than imported (the sidecar
venv has no `adaptive_reflow`). Parity was verified numerically against
`tools/run_controlled_audit._per_position_entropy`: **bit-identical** on
`(4,64,20)` and `(8,16,33)` random inputs.

### 4.4 Vector field + ODE integration

The real `compute_family_vector_field` and `integrate_base_flow` were
run, not reimplemented.

| Metric | Value |
|---|---|
| `max abs(sum_K v)` (simplex tangency) | 1.771e-08 |
| Euler steps | 8, `t0=1.0 → t1=4.0` |
| Integration elapsed | 45.7 s (8 network calls, CPU) |
| Simplex entropy, start → end | 2.565861 → **2.415161** |
| Simplex residual `max abs(sum-1)` | 1.458e-07 |
| NaN / Inf in endpoint | none |

Two sanity properties hold. The vector field sums to ~0 along the
amino-acid axis (1.8e-08), i.e. it is tangent to the simplex — it moves
probability mass around rather than creating it. And the endpoint still
sums to 1 to 1.5e-07 after 8 Euler steps, so the solver stays on the
manifold.

The entropy **drops** by 0.1507 over the integration. That is the
expected direction: the base flow concentrates the per-position
distribution toward family-plausible residues. It is also the first
evidence that the metric responds to real dynamics rather than to the
synthetic stub's noise.

## 5. Limitations — read before citing this run

These are recorded verbatim in the output JSON's `limitations` array.

1. **The family prior `alpha_h` is synthetic.** Upstream distributes
   family priors and gap rates as separate JSON assets (`--prior` /
   `--gap`) which are *not* part of the released checkpoint and are not
   in this repo. The runner builds a smooth Dirichlet-style prior with
   concentration 10 purely so the vector-field and solver paths can be
   exercised. **The model weights are real; the prior is not.**
2. **No biological quality metric was computed.** family_validity,
   foldability, self-consistency and novelty need HMMER, OmegaFold,
   MMseqs2 and ESM-IF respectively. None are installed. No claim about
   the paper's 95.3% family validity follows from this run.
3. **This is a numerical smoke, not a sampling run.** 8 Euler steps over
   `t ∈ [1, 4]` against the paper's 200+200 steps over `t ∈ [0, 16]`.
4. **CPU only.** Chosen for machine burden per the task brief.
5. **No framework-vs-baseline comparison was run here.** This wave
   establishes that the real forward *works*. Wiring the real model into
   `tools/run_controlled_audit.py` (which currently uses
   `force_mode="synthetic"` for LineageFlow) is separate follow-up work.

## 6. Files

| Path | Status |
|---|---|
| `data/lineageflow_upstream/` | NEW, gitignored (upstream clone) |
| `.venvs/lineageflow_venv/` | NEW, gitignored (sidecar venv) |
| `requirements-lineageflow.txt` | NEW, tracked |
| `tools/run_lineageflow_real_ckpt.py` | NEW, tracked |
| `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json` | NEW, gitignored |
| `docs/audit/wave40-lineageflow-real-ckpt-forward.md` | NEW, tracked (this file) |

No file outside this scope was touched. `adaptive_reflow/`, `tests/`,
the scheduler, and other adapters are unmodified.

## 7. Suggested follow-up

1. Wire `LineageFlowAdapter` to an optional real-model backend that
   imports from `data/lineageflow_upstream/` when present, so
   `tools/run_controlled_audit.py` can drop `force_mode="synthetic"`.
2. Obtain or reconstruct a real Pfam family prior + gap-rate pair so
   limitation (1) can be lifted.
3. With (1) and (2) done, re-run the Wave 10 baseline-vs-framework
   comparison on real weights. The entropy metric is now known to be
   non-saturated on real logits (§4.3), so that comparison should
   finally produce a signal instead of the Wave 10 tie.

---

**Agent A conclusion:** LineageFlow's real-checkpoint forward pass is
**unblocked and verified**. The 657.6 M-parameter released model loads
with zero missing and zero unexpected keys, the denoiser and the real
ODE solver both run clean on CPU, and the Wave 33 entropy metric reads
2.266 against a 2.996 ceiling — non-saturated, and responsive to the
real dynamics (−0.151 across the integration). The remaining gap to a
publishable LineageFlow result is the family prior and the external
scoring tools, not the model.
