# SOTA Experiment Protocol + Runbook

**Date:** 2026-08-30
**Protocol version:** v1
**Framework version required:** post-`3a30801` (commit hash `3a30801` introduces the state-machine infrastructure that `EvidenceDrivenScheduler` consumes; the protocol's "Loop 2" wiring relies on it)
**Author:** Agent B (runbook); paper-claim owner is the framework author
**Audience:** a fresh user (you) with one pre-trained flow-matching checkpoint, a CPU or GPU machine, and one afternoon to spare

---

## §1. Goal

### The single claim under test

> **When a published SOTA flow-matching model is run through FlowA's multi-round re-inference loop, the resulting sample-quality metric (FID for images, W2 for synthetic 2D, selection ratio for paper-Theorem-1 witnesses, etc.) improves over the same model's single-pass baseline on the same checkpoint, same task, same evaluator.**

That is the entire SOTA claim from `docs/paper-plan.md` §4. This protocol is the **runbook** that lets you verify it on a checkpoint of your choice.

### Why this protocol exists

The sandbox where FlowA was developed cannot download gated HuggingFace weights, cannot access Google Drive, has no GPU, and has no torch in its framework venv. The sandbox *can* ship: (a) the framework, (b) the protocol, (c) the adapter template, and (d) the FID harness (`flowa_fid_env`). The *experiment* must run on a machine that has your checkpoint and a torch-capable environment. This document is the bridge — it tells you, step by step, how to wire the framework to your checkpoint and produce a single comparison table that, if the claim is true, will show a framework-side metric strictly better than the baseline.

### What "improvement" means here

- **FID:** strictly lower (`framework_FID < baseline_FID`); publishable threshold is roughly ≥ 5 % relative reduction.
- **W2:** strictly lower; for 2D synthetic targets the Li-2024 selection mechanism (paper Theorem 1) predicts W2 should fall as `eps_implicit` shrinks.
- **selection_ratio:** should rise toward 1.0 (paper Theorem 1 direction); the published 2D RF baseline is 0.8061, framework result is 0.988+.
- **honesty clause:** the framework is allowed to underperform for some schedulers. Report all four honestly; the paper claim is "framework *can* improve", not "framework *always* improves".

---

## §2. Prerequisites

| # | Item | Notes |
|---|---|---|
| 1 | **Python 3.12** + the framework venv at `./.venv` (created by `uv sync` or `python -m venv .venv && pip install -e .`) | The framework is stdlib + numpy at runtime. PyTorch is **not** required for the framework itself. |
| 2 | **One pre-trained flow-matching checkpoint** that **you** provide | The framework is inference-only. Your model is the contribution. Options: (a) your own published checkpoint, (b) `huggan/cifar10-resnet-flow-matching` if you have an HF token, (c) gnobitab CIFAR-10 RF from Google Drive. Anything that maps `noise → data` deterministically works. |
| 3 | **Standard test set** for the checkpoint's original task | e.g. CIFAR-10 test set (10K images), MNIST test set (10K), or a 2D synthetic ground-truth sampler (`two_moons`, `eight_gaussians`, …). |
| 4 | **An InceptionV3 FID computation environment** | We use the isolated venv at `C:/Users/31472/AppData/Local/Temp/flowa_fid_env` (`torch==2.4.1+cpu` + `pytorch-fid`). The InceptionV3 weights download once on first run (~95 MB) from `github.com/mseitzer/pytorch-fid/releases/download/...`. If torch is unavailable on your machine, the framework ships a NumPy random-projection FID that is less accurate but works on any machine — see §5. |
| 5 | **Disk space** ~ 2 GB for InceptionV3 cache + your generated sample `.npz` files | Generated samples are stored under `/tmp/{model_name}_*.npz` by convention. |
| 6 | **Time budget** ~ 1–4 hours per checkpoint (CPU) or 10–30 min (GPU) | 1000 samples × 20 rounds × 4 schedulers = 80 K forward passes. On CPU at ~4 samples/s that's ~5.5 hours; bump `n_samples` down to 250 for a faster smoke pass. |

---

## §3. Step-by-step protocol

The protocol is **seven steps**. Steps 1–3 are one-time per checkpoint; steps 4–7 produce the comparison table.

### Step 1 — Inspect the checkpoint

Open a Python REPL and answer five questions about your checkpoint. Record the answers; you'll need them in Step 2.

```python
>>> import numpy as np
>>> data = np.load("/path/to/your_checkpoint.npz")
>>> list(data.keys())          # what weight tensors does it have?
>>> {k: data[k].shape for k in data.files}  # what is each tensor's shape?
```

Record:

| Question | Your answer |
|---|---|
| **Model class** (UNet / MLP / DiT / …) | |
| **Input shape** (the noise tensor shape fed to the model) | e.g. `(1, 3, 32, 32)` for CIFAR-10 UNet |
| **Output shape** (the model's `v(x, t)` shape) | usually matches input |
| **Sampling steps** (how many `solve_ode` calls the original codebase uses) | e.g. 50 / 100 / 250 |
| **Original task** + **original metric** | e.g. CIFAR-10 image generation, FID |

If your checkpoint has no NumPy `.npz` (e.g. a `safetensors` / PyTorch `state_dict` / Equinox `.eqx`), translate the weights to a NumPy `.npz` once with `torch.load(...).state_dict()` → `tensor.cpu().numpy()` per key. Save the resulting file under `data/your_model.npz`; the adapter template assumes NumPy access.

### Step 2 — Implement a thin adapter inheriting `FlowMatchingODEAdapter`

Copy the template from §4 into `adaptive_reflow/adapters/your_model.py`, then fill in 4–5 methods (marked **TODO**). The other 3–4 methods have sensible defaults and usually need no edits. Reference: `adaptive_reflow/adapters/twodim_fm.py` is the canonical pattern — the `TwoDimFMAdapter` (line 469) implements all 8 methods end-to-end against a tiny velocity-field MLP; your adapter is the same shape, sized up to your model's input/output dimensions.

Minimal working adapter for a CIFAR-10 UNet checkpoint:

```python
# adaptive_reflow/adapters/your_model.py — see §4 for the full template
from adaptive_reflow.universal import (
    FlowMatchingODEAdapter, AdapterCapabilities, NoOpMixer,
)
import numpy as np

class YourModelAdapter(FlowMatchingODEAdapter):
    def __init__(self, weights_path, num_steps=50):
        self._weights = load_your_weights(weights_path)
        self._num_steps = int(num_steps)
        self._caps = AdapterCapabilities(
            has_ode_integration_surface=True,
            has_prior_export=True, has_state_export=True,
            has_condition_injection=True, has_restart_boundary=True,
            has_continuous_channels=True, has_discrete_channels=False,
            has_trajectory_digest=True, has_deterministic_seed=True,
            has_materialization_route=True,
            supported_channels=("rgb",),  # or whatever your model emits
            channel_domains={"rgb": "continuous"},
            required_mixer=NoOpMixer,
            native_config_hash="your_model:cfg:v1",
            native_config_version="0.1.0",
        )

    def capabilities(self):
        return self._caps

    def build_initial_state(self, *, batch_id, sample_id):
        x0 = np.random.default_rng(hash((batch_id, sample_id)) & 0xffffffff).standard_normal((3, 32, 32))
        # ... build StateBundle (see §4)

    def solve_ode(self, state, condition, *, seed):
        # integrate your model forward for self._num_steps
        ...

    def observe_endpoint(self, trace, state):
        # read final state, build a new StateBundle (see §4)
        ...

    def export_endpoint(self, state):
        return state

    def detach_and_validate_endpoint(self, bundle):
        # default implementation: assert detach_proof and re-validate
        ...
```

Three methods that need filling (per the §4 template):

1. `build_initial_state(batch_id, sample_id)` → sample `x0` from the prior your checkpoint expects (usually `N(0, I)`) and return a `StateBundle`.
2. `solve_ode(state, condition, *, seed)` → integrate the velocity field using your checkpoint's native solver (Euler / Heun / RK4 / whatever the original codebase used). Return an `ODEIntegratorTrace` with a stable `native_state_digest` and `integrator_config_hash`.
3. `observe_endpoint(trace, state)` → read the final trajectory point, build a fresh `StateBundle` with `detach_proof=True` and a fresh `native_state_digest`.
4. `export_endpoint(state)` → typically a no-op identity, but if you want to project the native tensor into a canonical form do it here.
5. (optional) `inject_forward_noise(bundle, delta)` → only needed if you want the runner's Loop-4 forward-noise step to actually perturb the bundle. The 2D adapter does not implement this; it is a no-op.

Three methods that already have sensible defaults (copy from §4 verbatim):

- `apply_restart_distribution(state, policy)` — blend the prior endpoint with fresh `x0 ~ N(0, I)` using `memory_fraction = 1 - beta`. The 2D adapter's implementation is a copy-paste template.
- `compose_condition(bundle, delta)` — typically passes through `delta` with `target_distribution` and `integrator_config_hash` set as `delta_spec` defaults.
- `capabilities()` — return your constructed `AdapterCapabilities`.

### Step 3 — Validate the adapter

Two checks before you trust the adapter on a long run:

**(3a) Capability handshake.**

```python
from adaptive_reflow.frame.engine import Engine
from adaptive_reflow.adapters.your_model import YourModelAdapter

adapter = YourModelAdapter(weights_path="data/your_model.npz", num_steps=50)
engine = Engine()
caps = engine.handshake(adapter)
print("OK", caps.supported_channels, caps.has_ode_integration_surface)
```

If this raises `CapabilityMissingError` or `CapabilityMismatchError`, fix the capability declaration in `__init__` before proceeding — the engine will fail closed otherwise.

**(3b) 10-round smoke test.**

```python
from adaptive_reflow.algorithm.runner import ReInferenceRunner, ReInferenceConfig

runner = ReInferenceRunner(adapter=adapter)
result = runner.run(ReInferenceConfig(n_rounds=10, seed=0, channels=("rgb",)))

assert np.isfinite(result.endpoints).all(), "NaN/Inf in endpoints!"
assert (result.ledger_rows[-1].row_hash is not None), "ledger chain broken!"
print("smoke OK; endpoint shape:", result.endpoints.shape)
```

Three checks the smoke test must pass:
- `np.isfinite(result.endpoints).all()` — no NaN / Inf in any of the 10 endpoints.
- `verify_ledger_chain(result.ledger_rows)` returns `(True, "")` — ledger integrity holds (the runner calls this automatically; an `AssertionError` aborts).
- `result.endpoints.shape == (10, …)` — one row per round, shape matches your model's output.

If the smoke test fails on any of these, jump to §5 "Common pitfalls" before continuing.

### Step 4 — Compute the baseline single-pass metric

This is the **same model, same checkpoint, same task, single-pass inference** (no FlowA re-inference). The framework's evaluator computes the metric so the comparison is apples-to-apples.

For an image generation model:

```python
import numpy as np
from your_model_code import your_sampling_function   # your model's native sample loop

# 1. Sample N=1000 images with the original codebase (single pass)
images = []
for i in range(1000):
    x = your_sampling_function(checkpoint, num_steps=50, seed=i)
    images.append(x)
images = np.stack(images)                           # (1000, 3, 32, 32)
np.savez("/tmp/your_model_baseline.npz", samples=images)

# 2. Compute FID against the test set reference
#    (or W2 if the task is 2D synthetic)
import subprocess, sys
subprocess.run([sys.executable, "C:/Users/31472/AppData/Local/Temp/flowa_fid_env/compute_mnist_fid.py",
                "--gen", "/tmp/your_model_baseline.npz",
                "--ref", "data/your_test_set.npz",
                "--out", "/tmp/your_model_baseline_fid.txt"], check=True)

BASELINE_FID = float(open("/tmp/your_model_baseline_fid.txt").read().strip())
print(f"BASELINE FID: {BASELINE_FID}")
```

Record `BASELINE_FID` (or `BASELINE_W2`, `BASELINE_selection_ratio`, etc.). This is the row "baseline (single-pass)" in the §3 Step 7 table.

**Important:** keep the `num_steps` and seed schedule identical to what your model's original sampling code uses — the baseline is *that* sampling loop, not something FlowA invented. FlowA's job is to improve on it via multi-round re-inference.

If `num_steps` is small (≤ 10) the framework can match the original in one round. If `num_steps` is large (≥ 100) the framework may need to chunk the integration or run a smaller per-round `num_steps` — this is an open tuning parameter; record the value you actually used.

### Step 5 — Run FlowA multi-round with the four schedulers

The framework ships four schedulers, each wired to a different re-inference strategy:

| Scheduler | What it does | Where to import from |
|---|---|---|
| `default_cosine_scheduler` | CosineAnneal: `n_cap` decays from `n_max` to `n_min` over `n_rounds`. ADR-0010. | `adaptive_reflow.algorithm.scheduler` |
| `CodimensionSheetScheduler` | Paper-grounded: per-round `evidence_ratio` derived from sheet-A / packing-B / cell-C quantities (Lemma 2 + Lemma 3). | `adaptive_reflow.algorithm.scheduler` |
| `EvidenceDrivenScheduler` | PID-lite on `selection_ratio` (paper Theorem 1 direction). Requires `selection_evaluator`. | `adaptive_reflow.algorithm.scheduler` |
| Model-specific (you choose) | For CIFAR-10: `FreeTrajScheduler` (per-round free-trajectory budget). For molecules: bond-length cap scheduler. For 2D: `default_cosine_scheduler` (already covered). | `adaptive_reflow.algorithm.scheduler` |

Driver loop (run for each scheduler):

```python
import numpy as np
from adaptive_reflow.algorithm.runner import ReInferenceRunner, ReInferenceConfig
from adaptive_reflow.algorithm.scheduler import (
    default_cosine_scheduler, CodimensionSheetScheduler, EvidenceDrivenScheduler,
)
from adaptive_reflow.eval.posterior_selection_evaluator import PosteriorSelectionEvaluator

# (a) CosineAnnealScheduler — the canonical baseline
cosine = ReInferenceRunner(adapter=adapter, scheduler=default_cosine_scheduler())
result_cos = cosine.run(ReInferenceConfig(n_rounds=20, seed=42, channels=("rgb",)))
np.savez("/tmp/your_model_framework_cosine.npz",
         samples=result_cos.endpoints,        # (20, 3, 32, 32) — per-round endpoints
         metrics=result_cos.per_round_metrics)  # dict[r] -> {W2, n_cap, beta, ...}

# (b) CodimensionSheetScheduler — paper-grounded
codim = ReInferenceRunner(adapter=adapter, scheduler=CodimensionSheetScheduler(...))
result_codim = codim.run(ReInferenceConfig(n_rounds=20, seed=42, channels=("rgb",)))
np.savez("/tmp/your_model_framework_codim.npz", samples=result_codim.endpoints)

# (c) EvidenceDrivenScheduler — paper-Theorem-1 feedback
sel_eval = PosteriorSelectionEvaluator(...)
evid = ReInferenceRunner(adapter=adapter, scheduler=EvidenceDrivenScheduler(...),
                         evaluator=sel_eval)
result_evid = evid.run(ReInferenceConfig(n_rounds=20, seed=42, channels=("rgb",),
                                         selection_evaluator=sel_eval))
np.savez("/tmp/your_model_framework_evid.npz", samples=result_evid.endpoints)

# (d) Model-specific — for CIFAR-10: FreeTrajScheduler
freetraj = ReInferenceRunner(adapter=adapter, scheduler=FreeTrajScheduler(...))
result_free = freetraj.run(ReInferenceConfig(n_rounds=20, seed=42, channels=("rgb",)))
np.savez("/tmp/your_model_framework_freetraj.npz", samples=result_free.endpoints)
```

**Per-round metric recording:** every `result.per_round_metrics[r]` dict already carries `W2`, `n_cap`, `beta`, `memory_fraction`, `selection_ratio` (when `selection_evaluator` is configured), and the per-round `paper_quantity_diagnostics` (when `paper_quantities_provider` is configured). For plotting trajectories you don't need to recompute anything — the runner emits the time series.

**Per-scheduler file naming convention:** `/tmp/{model_name}_framework_{scheduler}.npz` where `{scheduler}` is one of `cosine` / `codim` / `evid` / `freetraj`. Use the convention verbatim; §6 expects these filenames.

### Step 6 — Compute per-scheduler metric (FID or W2)

The runner emits per-round *endpoints* (final trajectory points), but for image models we need *samples* — the per-round endpoint is the final generated image, one per round. To compare fairly against the baseline, we use **round 19 (the last round) endpoints** as the "framework multi-round sample set" — they represent the result of 20 rounds of re-inference on a single trajectory.

```python
import numpy as np, subprocess, sys
FID_SCRIPT = "C:/Users/31472/AppData/Local/Temp/flowa_fid_env/compute_mnist_fid.py"
TEST_REF   = "data/your_test_set.npz"

def fid(framework_npz, label):
    data = np.load(framework_npz)
    # Use the LAST round's endpoints as the multi-round sample set.
    # If n_rounds < sample count, repeat the last endpoint (or upsample).
    samples = data["samples"][-1] if data["samples"].ndim == 4 else data["samples"]
    if samples.shape[0] < 1000:
        # Pad by repeating; alternative: run multiple seeds and concatenate.
        samples = np.tile(samples, (1000 // samples.shape[0] + 1, 1, 1, 1))[:1000]
    out = f"/tmp/{label}_fid.txt"
    np.savez("/tmp/_tmp.npz", samples=samples)
    subprocess.run([sys.executable, FID_SCRIPT, "--gen", "/tmp/_tmp.npz",
                    "--ref", TEST_REF, "--out", out], check=True)
    return float(open(out).read().strip())

baseline_fid = fid("/tmp/your_model_baseline.npz", "baseline")
cosine_fid   = fid("/tmp/your_model_framework_cosine.npz",   "cosine")
codim_fid    = fid("/tmp/your_model_framework_codim.npz",    "codim")
evid_fid     = fid("/tmp/your_model_framework_evid.npz",     "evid")
freetraj_fid = fid("/tmp/your_model_framework_freetraj.npz", "freetraj")

print(f"baseline   FID = {baseline_fid:.4f}")
print(f"cosine     FID = {cosine_fid:.4f}   Δ = {cosine_fid - baseline_fid:+.4f}")
print(f"codim      FID = {codim_fid:.4f}   Δ = {codim_fid - baseline_fid:+.4f}")
print(f"evidence   FID = {evid_fid:.4f}   Δ = {evid_fid - baseline_fid:+.4f}")
print(f"freetraj   FID = {freetraj_fid:.4f}   Δ = {freetraj_fid - baseline_fid:+.4f}")
```

Three honest notes:

1. The "last-round endpoint" is one trajectory's worth of refinement, not a population. For a publishable table, run **N ≥ 1000 parallel trajectories** (each with the same scheduler / seed pattern) and pool the last-round endpoints; this averages out per-trajectory stochasticity.
2. The framework's FID uses the same InceptionV3 weights as the baseline's FID — never mix FID implementations between baseline and framework rows.
3. If a scheduler crashes or fails closed, the row stays as `NaN` in `result.endpoints`; the runner emits `endpoint_export_failed=1.0` in the per-round metric dict. Report this honestly; do not drop the row.

### Step 7 — Fill the comparison table

| Scheduler | Mean FID | Std FID | Delta vs Baseline | % Change |
|---|---|---|---|---|
| baseline (single-pass) | **X** | std | — | — |
| CosineAnnealScheduler | | | | |
| CodimensionSheetScheduler | | | | |
| EvidenceDrivenScheduler | | | | |
| FreeTrajScheduler (or model-specific) | | | | |

**Mean / Std** are over 3 seeds (the paper-plan §4.1 statistical recipe). For each scheduler, re-run Steps 5–6 with `seed ∈ {42, 43, 44}` and pool the FID numbers. The "Δ vs Baseline" is `framework_FID - baseline_FID` (negative = improvement); "% Change" is `100 * Δ / baseline_FID`.

**Honest framing:** if only 1–2 schedulers beat the baseline, report it that way. The paper claim is "framework *can* improve"; the table is the evidence, not a claim that all four schedulers always win. The Li 2026 paper-quantity-driven schedulers (Codim / Evidence) have a theoretical reason to improve on Theorem-1-style metrics; the heuristic ones (Cosine / FreeTraj) are ablation rows.

---

## §4. Adapter template (code)

This is the **complete** adapter template. Copy it verbatim, fill in the **TODO** blocks, and you have a working `FlowMatchingODEAdapter`. Reference implementation: `adaptive_reflow/adapters/twodim_fm.py:469` (the `TwoDimFMAdapter` class).

```python
"""YourModelAdapter — thin wrapper around a pre-trained flow-matching checkpoint.

Implements the eight methods of :class:`FlowMatchingODEAdapter` against a
user-supplied checkpoint (NumPy .npz). The adapter is inference-only;
training is the user's contribution.

This template is byte-stable: the ``TwoDimFMAdapter`` (see
:mod:`adaptive_reflow.adapters.twodim_fm`) is the canonical reference
implementation. Read it before filling in the TODOs.
"""
from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.universal import (
    AdapterCapabilities, CapabilityMissingError,
    ChannelDomain, FlowMatchingODEAdapter, NoOpMixer,
)
from adaptive_reflow.universal.state import (
    ChannelName, ODEConditionDelta, ODEIntegratorTrace,
    StateBundle, TensorRef, validate_state_bundle,
)

# --- Module-level constants (your model) ---------------------------

YOUR_MODEL_CHANNELS: tuple[ChannelName, ...] = (ChannelName("rgb"),)  # TODO
YOUR_MODEL_CONFIG_HASH: str = "your_model:cfg:v1"                     # TODO
YOUR_MODEL_CONFIG_VERSION: str = "0.1.0"                              # TODO
YOUR_MODEL_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    ChannelName("rgb"): "continuous",                                  # TODO
}
YOUR_MODEL_NUM_STEPS: int = 50                                        # TODO
YOUR_MODEL_STATE_SHAPE: tuple[int, ...] = (3, 32, 32)                 # TODO
YOUR_MODEL_CLAMP: float = 1.0                                         # TODO (or omit)

#: LRU bound on native state cache (audit A-3 — see TwoDimFMAdapter).
_NATIVE_STATES_MAXSIZE: int = 128


# --- Helpers --------------------------------------------------------

def _seed_from_ids(batch_id: str, sample_id: str, source_round: int) -> int:
    blob = repr((str(batch_id), str(sample_id), int(source_round))).encode("utf-8")
    return int(hashlib.sha256(blob).hexdigest()[:8], 16)

def _digest_state(payload: Mapping[str, Any]) -> str:
    blob = repr((sorted(payload.items(), key=lambda kv: str(kv[0])),)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()

def _make_ref(label: str, **parts: Any) -> TensorRef:
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(f"your_model:state:{hashlib.sha256(blob).hexdigest()[:16]}")

def _load_weights(path: Path) -> dict[str, NDArray[np.float64]]:
    """TODO: load your model's weights into a flat dict[str, np.ndarray]."""
    with np.load(Path(path)) as data:
        return {k: np.asarray(data[k], dtype=np.float64) for k in data.files}

def _velocity_field(weights, x, t):
    """TODO: evaluate your model's v(x, t). Mirror the original code's step."""
    raise NotImplementedError("TODO: port your model's forward step")


# --- Capabilities dataclass -----------------------------------------

@dataclass(frozen=True)
class YourModelCapabilities(AdapterCapabilities):
    def __init__(self) -> None:
        super().__init__(
            has_ode_integration_surface=True,
            has_prior_export=True, has_state_export=True,
            has_condition_injection=True, has_restart_boundary=True,
            has_continuous_channels=True, has_discrete_channels=False,
            has_trajectory_digest=True, has_deterministic_seed=True,
            has_materialization_route=True,
            supported_channels=YOUR_MODEL_CHANNELS,
            channel_domains=YOUR_MODEL_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=YOUR_MODEL_CONFIG_HASH,
            native_config_version=YOUR_MODEL_CONFIG_VERSION,
        )


# --- Adapter --------------------------------------------------------

class YourModelAdapter(FlowMatchingODEAdapter):
    """Your flow-matching model adapter.

    Implements all eight methods of :class:`FlowMatchingODEAdapter`.
    Reference: :class:`adaptive_reflow.adapters.twodim_fm.TwoDimFMAdapter`.
    """

    pinned_num_steps: int = YOUR_MODEL_NUM_STEPS

    def __init__(
        self,
        *,
        weights_path: Path,
        num_steps: int = YOUR_MODEL_NUM_STEPS,
        seed_offset: int = 0,
    ) -> None:
        self._weights_path = Path(weights_path)
        self._weights = _load_weights(self._weights_path)
        self._num_steps = int(num_steps)
        self._seed_offset = int(seed_offset)
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._caps = YourModelCapabilities()

    # --- 1. capabilities (always required) ---

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    # --- 2. build_initial_state (TODO; required by has_prior_export=True) ---

    def build_initial_state(self, *, batch_id: str, sample_id: str) -> StateBundle:
        # TODO: sample x0 ~ N(0, I) in YOUR_MODEL_STATE_SHAPE and build a StateBundle.
        # Reference: TwoDimFMAdapter.build_initial_state (twodim_fm.py:630).
        seed = _seed_from_ids(str(batch_id), str(sample_id), int(self._seed_offset) + 0)
        rng = np.random.default_rng(seed)
        x0 = rng.standard_normal(YOUR_MODEL_STATE_SHAPE).astype(np.float64)
        digest = _digest_state({
            "kind": "initial", "batch_id": str(batch_id), "sample_id": str(sample_id),
            "x0": x0.tolist(),
        })
        self._native_states[digest] = {"x0": x0, "source_round": 0}
        bundle = StateBundle(
            channels={ChannelName("rgb"): _make_ref("initial", batch=batch_id, sample=sample_id)},
            masks={}, batch_id=str(batch_id), sample_id=str(sample_id),
            reference_frame="world", normalization="none", source_round=0,
            detach_proof=True, native_state_digest=digest,
            provenance=("your_model@v1",), capability_token=self.capabilities(),
        )
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise AssertionError(f"placeholder_state_invalid:{errs}")
        return bundle

    # --- 3. export_endpoint (default; pass-through) ---

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError("validate_state_bundle", context=",".join(errs))
        return state

    # --- 4. detach_and_validate_endpoint (default) ---

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        if bundle.detach_proof is not True:
            raise CapabilityMissingError("detach_proof_must_be_true")
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError("detach_proof_must_be_true", context=",".join(errs))
        return bundle

    # --- 5. apply_restart_distribution (default; blend prior with fresh noise) ---

    def apply_restart_distribution(self, state: StateBundle, policy: RestartPolicy) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError("validate_state_bundle", context=",".join(errs))
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError("missing_native_state", context=state.native_state_digest)
        beta_raw = policy.beta_by_channel.get(ChannelName("rgb"))
        if beta_raw is None:
            beta, memory_fraction = 0.5, 0.5
        else:
            beta = float(beta_raw)
            memory_fraction = 1.0 - beta
        prior_x0 = np.asarray(prior_entry["x0"], dtype=np.float64)
        next_round = int(state.source_round) + 1
        restart_seed = int(hashlib.sha256(
            repr((str(policy.policy_hash), next_round)).encode("utf-8")
        ).hexdigest()[:8], 16)
        fresh_x0 = np.random.default_rng(restart_seed).standard_normal(
            YOUR_MODEL_STATE_SHAPE
        ).astype(np.float64)
        m_clipped = max(0.0, min(1.0, float(memory_fraction)))
        blended_x0 = (m_clipped * prior_x0 + (1.0 - m_clipped) * fresh_x0).astype(np.float64)
        next_digest = _digest_state({
            "kind": "restart", "src_digest": state.native_state_digest,
            "policy_hash": str(policy.policy_hash), "source_round": next_round,
            "memory_fraction": float(memory_fraction),
            "blended_x0": blended_x0.tolist(),
        })
        self._native_states[next_digest] = {
            "x0": blended_x0, "source_round": next_round,
        }
        return StateBundle(
            channels={ChannelName("rgb"): _make_ref(
                "restart", src_digest=state.native_state_digest,
                source_round=next_round, x0=blended_x0.tolist(),
            )},
            masks=dict(state.masks), batch_id=str(state.batch_id),
            sample_id=str(state.sample_id), reference_frame=str(state.reference_frame),
            normalization=str(state.normalization), source_round=int(next_round),
            detach_proof=True, native_state_digest=str(next_digest),
            provenance=tuple(state.provenance) + ("your_model_restart_blend",),
            capability_token=self.capabilities(),
        )

    # --- 6. compose_condition (default; pass-through with metadata) ---

    def compose_condition(self, bundle: StateBundle, delta: ODEConditionDelta) -> ODEConditionDelta:
        del bundle
        new_spec = dict(delta.delta_spec)
        new_spec.setdefault("integrator_config_hash", YOUR_MODEL_CONFIG_HASH)
        return ODEConditionDelta(
            delta_spec=new_spec, source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    # --- 7. solve_ode (TODO; required by has_ode_integration_surface=True) ---

    def solve_ode(self, state: StateBundle, condition: ODEConditionDelta, *, seed: int) -> ODEIntegratorTrace:
        # TODO: integrate v(x, t) over YOUR_MODEL_NUM_STEPS using YOUR_MODEL's
        # native solver. Return an ODEIntegratorTrace with a stable
        # native_state_digest and integrator_config_hash.
        # Reference: TwoDimFMAdapter.solve_ode (twodim_fm.py:857).
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError("validate_state_bundle", context=",".join(errs))
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError("missing_native_state", context=state.native_state_digest)
        x0 = np.asarray(prior_entry["x0"], dtype=np.float64)
        num_steps = int(condition.delta_spec.get("num_steps", self._num_steps))
        t_grid = np.linspace(0.0, 1.0, num_steps + 1, dtype=np.float64)
        x_cur = x0.copy()
        for i in range(1, t_grid.size):
            t_cur, t_next = float(t_grid[i - 1]), float(t_grid[i])
            h = float(t_next - t_cur)
            # TODO: replace the placeholder Euler step with YOUR model's step.
            v = _velocity_field(self._weights, x_cur, t_cur)
            x_cur = x_cur + h * v
        traj = x_cur.reshape(YOUR_MODEL_STATE_SHAPE)
        if YOUR_MODEL_CLAMP is not None:
            traj = np.clip(traj, -YOUR_MODEL_CLAMP, YOUR_MODEL_CLAMP)
        traj_digest = _digest_state({
            "kind": "trajectory", "src_digest": state.native_state_digest,
            "num_steps": int(num_steps), "shape": list(traj.shape),
            "x0": x0.tolist(),
        })
        self._native_states[traj_digest] = {"x_final": traj, "t_final": 1.0}
        cfg_blob = repr(("your_model_config", int(num_steps), int(seed))).encode("utf-8")
        return ODEIntegratorTrace(
            steps=int(num_steps), accept_rate=1.0,
            native_state_digest=str(traj_digest),
            integrator_config_hash=hashlib.sha256(cfg_blob).hexdigest(),
        )

    # --- 8. observe_endpoint (TODO; always required) ---

    def observe_endpoint(self, trace: ODEIntegratorTrace, state: StateBundle) -> StateBundle:
        # TODO: read the final trajectory point, build a fresh StateBundle with
        # detach_proof=True. Reference: TwoDimFMAdapter.observe_endpoint (twodim_fm.py:968).
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError("validate_state_bundle", context=",".join(errs))
        traj_entry = self._native_states.get(trace.native_state_digest)
        if traj_entry is None:
            raise CapabilityMissingError("missing_native_state", context=trace.native_state_digest)
        x_final = np.asarray(traj_entry["x_final"], dtype=np.float64)
        endpoint_digest = _digest_state({
            "kind": "endpoint", "traj_digest": trace.native_state_digest,
            "src_digest": state.native_state_digest, "x_final": x_final.tolist(),
            "t_final": 1.0,
        })
        self._native_states[endpoint_digest] = {"x": x_final, "t": 1.0}
        next_round = int(state.source_round) + 1
        return StateBundle(
            channels=dict(state.channels), masks=dict(state.masks),
            batch_id=str(state.batch_id), sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame), normalization=str(state.normalization),
            source_round=int(next_round), detach_proof=True,
            native_state_digest=str(endpoint_digest),
            provenance=tuple(state.provenance) + ("your_model_observed",),
            capability_token=self.capabilities(),
        )
```

**Which methods you actually fill in:**

| # | Method | Need to fill? |
|---|---|---|
| 1 | `capabilities` | No — return `self._caps`. |
| 2 | `build_initial_state` | **YES** — sample x0, build the StateBundle (digest, channels, etc.). |
| 3 | `export_endpoint` | No — pass-through identity. |
| 4 | `detach_and_validate_endpoint` | No — assert + re-validate. |
| 5 | `apply_restart_distribution` | No — blend prior + fresh (template above is canonical). |
| 6 | `compose_condition` | No — pass-through with metadata. |
| 7 | `solve_ode` | **YES** — port your model's forward step. |
| 8 | `observe_endpoint` | **YES** — read the final point, build the StateBundle. |

Three methods **must** be filled (`build_initial_state`, `solve_ode`, `observe_endpoint`); one method (`export_endpoint`) is a no-op identity; one optional (`inject_forward_noise`) only if you want Loop-4 forward-noise to actually perturb the bundle. The other three have sensible defaults from the template above and can be copied verbatim.

---

## §5. Common pitfalls

Six categories of failure that bite a fresh adapter. Diagnose with the symptom in the table; fix per the remedy.

| # | Pitfall | Symptom | Remedy |
|---|---|---|---|
| 1 | **Capability mismatch** — adapter claims `has_ode_integration_surface=True` but uses a different solver family the engine doesn't recognise | `CapabilityMissingError: has_ode_integration_surface` raised by `engine.handshake()` in Step 3a | Set the corresponding `has_*` flag in your `AdapterCapabilities` ctor to match what your adapter *actually* implements. False advertising fails closed; missing capability is the most common cause. |
| 2 | **State shape mismatch** — adapter reports `(3, 32, 32)` but model expects `(1, 3, 32, 32)` batched | `result.endpoints.shape` is `(20,)` instead of `(20, 3, 32, 32)`, or `np.broadcast` warnings | Always return the *batched* shape from `build_initial_state` / `solve_ode`; the engine flattens for you. Match `YOUR_MODEL_STATE_SHAPE` to your model's output, not its input. |
| 3 | **Non-determinism in `solve_ode`** — `solve_ode` reseeds RNG per call, so round r and round r+1 with the same `seed` produce different trajectories | `result.endpoints.std(axis=0)` is nonzero across rounds for the same input | The `seed` kwarg is consumed *once* per round; pass it through to your solver's `torch.manual_seed` / `numpy.random.default_rng` exactly once. Do not reseed inside the integrator loop. |
| 4 | **NaN / Inf in long round chains** | `np.isnan(result.endpoints).any()` returns True after round 10+ | (a) Check `YOUR_MODEL_CLAMP` is set; (b) ensure your model outputs finite values for the input range; (c) the runner emits `endpoint_export_failed=1.0` in `per_round_metrics[r]` — look at the round index where NaN first appears and inspect that round's input. |
| 5 | **FID computation fails on a torch-less machine** | `ModuleNotFoundError: No module named 'torch'` when running the FID script | Use the framework's `flowa_fid_env` (the isolated venv) — it has `torch==2.4.1+cpu` already installed. Alternatively, the framework ships a NumPy random-projection FID (`mnist_fid.py`) that works on any machine but is less accurate (lower precision, biased toward large features). |
| 6 | **InceptionV3 weights won't download** (corporate firewall blocks github.com) | First FID run times out fetching `pt_inception-2015-12-05-6726825d.pth` (95 MB) | Pre-download the file with `curl -L https://github.com/mseitzer/pytorch-fid/releases/download/fid_weights/pt_inception-2015-12-05-6726825d.pth -o ~/.cache/torch/hub/checkpoints/pt_inception-2015-12-05-6726825d.pth` once, then re-run. |

Two more that bite less often:

- **Per-round metric dict missing keys** — if `selection_ratio` doesn't appear in `per_round_metrics[r]`, you forgot to pass `selection_evaluator=...` to `ReInferenceConfig`. Add it back; `EvidenceDrivenScheduler` needs it.
- **Ledger chain breaks after round 5** — usually a non-deterministic source_round or a mutated `policy_hash`. The runner emits `AssertionError: ledger_chain_integrity_check_failed:...` with the exact round index. Re-run that round's adapter inputs in isolation; the issue is almost always a non-pure `apply_restart_distribution`.

---

## §6. Expected output

The protocol produces **four artifacts per published SOTA model**:

### Artifact 1 — The 5-row comparison table

For each model you evaluate, fill this table (one row per scheduler + one baseline row). Compute mean / std over 3 seeds.

| Scheduler | Mean FID | Std FID | Δ vs Baseline | % Change |
|---|---|---|---|---|
| baseline (single-pass) | X | std | — | — |
| CosineAnnealScheduler | | | | |
| CodimensionSheetScheduler | | | | |
| EvidenceDrivenScheduler | | | | |
| FreeTrajScheduler (or model-specific) | | | | |

For 2D synthetic targets, replace "FID" with "W2" (2-Wasserstein distance) or "selection_ratio" depending on the published metric.

### Artifact 2 — Per-round trajectory plot (per scheduler)

One figure per scheduler, x-axis = round index (0–19), y-axis = metric. Use the per-round numbers from `result.per_round_metrics[r]['W2']` (or `selection_ratio`). Plotting recipe:

```python
import matplotlib.pyplot as plt
def plot_trajectory(result, title):
    rounds = sorted(result.per_round_metrics.keys())
    metrics = [result.per_round_metrics[r]["W2"] for r in rounds]
    plt.plot(rounds, metrics, marker="o", label=title)
    plt.xlabel("round"); plt.ylabel("W2"); plt.title(title); plt.grid(True); plt.show()
plot_trajectory(result_cos,   "CosineAnnealScheduler")
plot_trajectory(result_codim, "CodimensionSheetScheduler")
plot_trajectory(result_evid,  "EvidenceDrivenScheduler")
plot_trajectory(result_free,  "FreeTrajScheduler")
```

The paper-plan §4.1 Figure 5 is the canonical version of this plot on the 2D RF baseline.

### Artifact 3 — Per-sample visualisation (8×8 grid)

For image models, save an 8×8 PNG of generated vs reference images side by side.

```python
import matplotlib.pyplot as plt, numpy as np
fig, axes = plt.subplots(2, 8, figsize=(16, 4))
gen   = np.load("/tmp/your_model_framework_cosine.npz")["samples"][-1][:8]   # last round, 8 samples
ref   = np.load("data/your_test_set.npz")["samples"][:8]
for i in range(8):
    axes[0, i].imshow(gen[i].transpose(1, 2, 0) * 0.5 + 0.5)  # de-normalize [-1, 1] -> [0, 1]
    axes[1, i].imshow(ref[i].transpose(1, 2, 0) * 0.5 + 0.5)
    axes[0, i].axis("off"); axes[1, i].axis("off")
plt.suptitle("Generated (top) vs Reference (bottom)"); plt.savefig("/tmp/your_model_grid.png")
```

For 2D synthetic, replace with a 2D scatter plot (paper-plan Figure 6).

### Artifact 4 — Selection-ratio trajectory (Theorem 1 witness)

If you configured `selection_evaluator=PosteriorSelectionEvaluator(...)` in Step 5, `result.per_round_metrics[r]["selection_ratio"]` carries the per-round evidence ratio. Plot it on a 0-to-1 scale; the paper Theorem 1 direction is monotone non-decreasing toward 1.0. The published baseline is 0.8061; framework target is 0.988+.

### What success looks like

- **At least 1–2 of the 4 schedulers** show strictly better metric than the baseline. Reporting 0/4 is a publishable negative result (the paper claim is "can improve", not "always improves").
- **Selection ratio** (where applicable) trends monotonically toward 1 as rounds progress.
- **No NaN / Inf** in any per-round endpoint.
- **Ledger chain** verifies intact (`verify_ledger_chain(result.ledger_rows) == (True, "")`).
- **Adapter validates** the capability handshake on the first try.

---

## §7. Sandbox limitations

The sandbox where FlowA was developed **cannot run this experiment end-to-end**. Read this carefully before you wonder why the sandbox isn't producing FID numbers.

| # | Limitation | Consequence | Workaround |
|---|---|---|---|
| 1 | **Gated HuggingFace models blocked** — `huggan/cifar10-resnet-flow-matching` requires an HF token the sandbox does not have | Cannot download the most common CIFAR-10 RF checkpoint | User downloads on their own machine with their token, then drops the `.npz` weights into `data/`. |
| 2 | **No Google Drive access** — gnobitab's CIFAR-10 RF is hosted there | Cannot fetch the published Rectified Flow MNIST/CIFAR weights either | User downloads via their browser, exports to `.npz`. |
| 3 | **No GPU** — only CPU cores available | 3.8 samples/s for the framework's existing MNIST UNet (FID 173.48 record); SOTA models run slower still | User runs on GPU; protocol is identical. |
| 4 | **Framework venv has no torch** — by design (stdlib + numpy only) | Cannot run InceptionV3 FID in the framework's own venv | Use the isolated `flowa_fid_env` venv (already pre-built in `C:/Users/31472/AppData/Local/Temp/flowa_fid_env`) for FID. |
| 5 | **No published SOTA weights** | The sandbox cannot produce the §6 comparison table by itself | Sandbox ships the protocol + adapter template + reproduction recipe; user runs the experiment on their machine. |
| 6 | **Slower per-round wall-clock** on CPU (~10 s/round for the 2D adapter at 100-step RK4) | A full 4-scheduler × 20-round × 1000-sample run takes ~5 hours | User can parallelise across seeds; framework's `run` is single-process per call. |

**What the sandbox *does* ship:**

1. The framework (`adaptive_reflow/`) at commit post-`3a30801`, with the four-loop orchestration, the 17 state machines, the paper-quantity-driven schedulers (CodimensionSheet, EvidenceDriven), and the BoundedMergeOperator.
2. The 8 concrete adapters — `TwoDimFMAdapter`, `MnistFmAdapter`, `StochasticFMAdapter`, `FlowMol3Adapter`, `ReferenceFlowAAdapter`, `ToyGaussianAdapter`, `ToyLinearAdapter`, `SyntheticAdapter` — to verify the protocol against (Steps 1–3) before plugging in a SOTA checkpoint.
3. This protocol (§1–§8 of this document).
4. The adapter template (§4).
5. The FID harness (`flowa_fid_env` venv + `tools/generate_mnist_samples.py` + `tools/extract_mnist_test.py`).

**What the user provides:**

1. The checkpoint (in `.npz` form).
2. A machine (CPU or GPU; CPU is fine but slow).
3. Run time (~1–4 hours per checkpoint on CPU).
4. Patience for honest reporting when some schedulers underperform.

The sandbox cannot answer the question "does FlowA improve SOTA FID?" — it can only ship the framework and protocol that lets you answer it on your machine.

---

## §8. Versioning

| Field | Value |
|---|---|
| **Protocol version** | v1 (2026-08-30) |
| **Framework version at time of writing** | post-`3a30801` (commit hash `3a30801`) |
| **State-machine infrastructure** | 17 state machines, 333 transitions (commit `456a406` parent) |
| **EvidenceDrivenScheduler requirement** | requires state-machine infrastructure (post-`3a30801`) for the per-round `eps_implicit` propagation; the older pre-`3a30801` framework cannot run this scheduler |
| **Forward compatibility** | the protocol's interface (`AdapterCapabilities`, `FlowMatchingODEAdapter`, `ReInferenceRunner`) is stable across `3a30801` and later; pre-`3a30801` framework versions require a backport of the state-machine wrappers |
| **InceptionV3 FID weights** | `pt_inception-2015-12-05-6726825d.pth` (95 MB); cache at `~/.cache/torch/hub/checkpoints/`; first-run download only |

### Changelog

| Version | Date | Change |
|---|---|---|
| v1 | 2026-08-30 | Initial protocol; references post-`3a30801` framework; covers four schedulers (CosineAnneal, CodimensionSheet, EvidenceDriven, FreeTraj-or-model-specific); 8-method adapter template; 7-step runbook. |

---

## References

- `docs/paper-plan.md` — paper structure and the ONE claim (§4.1–§4.5).
- `docs/r4-survey/01-modern-statemachine-research.md` — state-machine context for EvidenceDrivenScheduler.
- `docs/r4-survey/06-mnist-inceptionv3-fid.md` — the FID harness (FID 173.48 vs noise 370.55, 2.14× better) this protocol extends.
- `adaptive_reflow/adapters/twodim_fm.py` — canonical adapter (`TwoDimFMAdapter`, line 469); pattern reference for all 8 methods.
- `adaptive_reflow/algorithm/runner.py` — `ReInferenceRunner` (line 391), `ReInferenceConfig` (line 137), `ReInferenceResult` (line 215).
- `adaptive_reflow/frame/engine.py` — `Engine.run_round` (line 1016), capability handshake (line 896), ledger chain verification (line 491).
- `flowa_fid_env` — isolated InceptionV3 venv at `C:/Users/31472/AppData/Local/Temp/flowa_fid_env`.
- Li 2026 — paper Theorem 1 (BL-convergence; quantities `A_g, B_g, C_g, e_ρ`); selection mechanism.
- Liu 2022 NeurIPS Spotlight — 2D Rectified Flow.
